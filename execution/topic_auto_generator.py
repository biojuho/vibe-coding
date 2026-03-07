"""
주제 자동 보충 스크립트.

채널별 pending 주제가 임계값 이하이면 GPT로 새 주제를 생성해 content_db에 추가.
daily_runner.py 끝에서 호출되거나 독립 실행 가능.

Usage:
    python execution/topic_auto_generator.py              # 기본 실행
    python execution/topic_auto_generator.py --dry-run    # 실제 추가 없이 미리보기
    python execution/topic_auto_generator.py --threshold 5 --count 7
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

from dotenv import load_dotenv
from execution.language_bridge import ensure_utf8_stdio

logger = logging.getLogger(__name__)

# Windows cp949 인코딩 문제 방지
ensure_utf8_stdio()

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from execution.content_db import add_topic, get_all, get_channels, get_top_performing_topics, init_db  # noqa: E402
from execution.llm_client import LLMClient  # noqa: E402

try:
    from execution.community_trend_scraper import get_community_trend_titles  # noqa: E402
    _COMMUNITY_TRENDS_OK = True
except ImportError:  # pragma: no cover — depends on optional dependency
    _COMMUNITY_TRENDS_OK = False

THRESHOLD = 3   # pending이 이 이하면 보충
GEN_COUNT = 5   # 한 번에 생성할 주제 수


def get_trending_topics(count: int = 10) -> list[str]:
    """Google Trends 실시간 인기 검색어 수집 (pytrends). 실패 시 빈 리스트 반환."""
    try:
        from pytrends.request import TrendReq  # type: ignore[import-untyped]
        pt = TrendReq(hl="ko-KR", tz=540)
        df = pt.trending_searches(pn="south_korea")
        return df[0].tolist()[:count]
    except Exception:
        return []

SYSTEM_PROMPT = """\
당신은 YouTube Shorts 콘텐츠 기획자입니다.
주어진 채널 주제에 맞는 한국어 YouTube Shorts 영상 주제를 생성하세요.

규칙:
- 각 주제는 30-60초 짜리 Shorts 영상에 적합해야 합니다
- "~의 비밀", "~가 실제로 ~하면", "~에 대한 충격적인 사실" 등 호기심을 자극하는 제목
- 이미 존재하는 주제와 중복되면 안 됩니다
- 성과 데이터가 제공되면, 성공 패턴을 참고하여 유사한 스타일의 주제를 생성하세요
- 주제 다양성: 형식(리스트형/비교형/스토리형/질문형)과 감정톤(호기심/공포/감동/유머)을 골고루 분배하세요
- JSON 형식으로 반환: {"topics": ["주제1", "주제2", ...]}
"""


def generate_topics(
    channel: str,
    existing_topics: list[str],
    count: int = GEN_COUNT,
    api_key: str | None = None,
    top_performers: list[dict] | None = None,
    trending_keywords: list[str] | None = None,
) -> list[str]:
    """LLM으로 채널에 맞는 새 주제 생성. 7개 프로바이더 자동 fallback 지원.

    성과 데이터 + 트렌드 기반 추천 지원.
    """
    # 통합 LLM 클라이언트 (모든 프로바이더 자동 fallback)
    llm = LLMClient(caller_script="topic_auto_generator")
    if not llm.enabled_providers():
        logger.warning("사용 가능한 LLM API 키 없음 - 주제 생성 스킵")
        return []

    existing_str = "\n".join(f"- {t}" for t in existing_topics[-30:])

    performance_context = ""
    if top_performers:
        perf_lines = [f"- {t['topic']} (비용: ${t.get('cost_usd', 0):.3f})" for t in top_performers[:10]]
        performance_context = f"""

최근 성공한 주제 패턴 (참고):
{chr(10).join(perf_lines)}

위 성공 패턴과 유사한 스타일/형식의 주제를 우선 생성하세요."""

    trending_context = ""
    if trending_keywords:
        trending_context = f"""

현재 한국 트렌딩 키워드 (참고하여 연관 주제 생성):
{', '.join(trending_keywords[:8])}"""

    user_prompt = f"""채널: {channel}

기존 주제 목록 (중복 방지):
{existing_str}
{performance_context}
{trending_context}

위 주제들과 겹치지 않는 새로운 주제 {count}개를 생성하세요.
형식(리스트형, 비교형, 스토리형, 질문형)과 감정톤(호기심, 공포, 감동, 유머)을 골고루 섞어주세요.
JSON 형식: {{"topics": [...]}}"""

    try:
        if hasattr(llm, "generate_json_bridged"):
            data = llm.generate_json_bridged(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=0.9,
            )
        else:
            data = llm.generate_json(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=0.9,
            )
    except RuntimeError as err:
        logger.error("LLM 주제 생성 실패 [%s]: %s", channel, err)
        return []

    raw_topics = data.get("topics", [])
    topics: list[str] = []
    for item in raw_topics:
        if isinstance(item, str):
            t = item.strip()
        elif isinstance(item, dict):
            t = str(item.get("topic", "")).strip()
        else:
            continue
        if t:
            topics.append(t)
    return topics


def check_and_replenish(
    threshold: int = THRESHOLD,
    count: int = GEN_COUNT,
    dry_run: bool = False,
) -> dict[str, list[str]]:
    """채널별 pending 체크 후 부족하면 보충. 생성된 주제 dict 반환."""
    channels = get_channels()
    if not channels:
        return {}

    result: dict[str, list[str]] = {}

    for ch in channels:
        items = get_all(channel=ch)
        pending = [i for i in items if i["status"] == "pending"]

        if len(pending) > threshold:
            continue

        logger.info("[%s] pending %d개 <= %d -> 보충 시작", ch, len(pending), threshold)
        existing = [i["topic"] for i in items]
        top_performers = get_top_performing_topics(limit=10, channel=ch)
        trending = get_trending_topics(count=10)
        if _COMMUNITY_TRENDS_OK:
            try:
                community = get_community_trend_titles(limit=5)
                if community:
                    logger.debug("[COMMUNITY] %s", ", ".join(community[:3]))
                    trending = trending + community
            except Exception:
                logger.warning("커뮤니티 트렌드 수집 실패 (무시)")
        if trending:
            logger.debug("[TREND] %s", ", ".join(trending[:5]))
        new_topics = generate_topics(
            ch, existing, count=count,
            top_performers=top_performers,
            trending_keywords=trending,
        )

        if not new_topics:
            logger.warning("[%s] 생성 실패 또는 결과 없음", ch)
            continue

        result[ch] = new_topics
        for topic in new_topics:
            if dry_run:
                logger.info("  [DRY] %s", topic)
            else:
                add_topic(topic, channel=ch, notes="auto-generated")
                logger.info("  [ADD] %s", topic)

    return result


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Shorts 주제 자동 보충")
    parser.add_argument("--threshold", type=int, default=THRESHOLD, help=f"보충 임계값 (기본: {THRESHOLD})")
    parser.add_argument("--count", type=int, default=GEN_COUNT, help=f"채널당 생성 수 (기본: {GEN_COUNT})")
    parser.add_argument("--dry-run", action="store_true", help="실제 추가 없이 미리보기")
    args = parser.parse_args()

    load_dotenv(_ROOT / ".env")
    load_dotenv(_ROOT / "shorts-maker-v2" / ".env", override=False)
    init_db()

    print(f"[주제 보충] threshold={args.threshold}, count={args.count}, dry-run={args.dry_run}")

    result = check_and_replenish(
        threshold=args.threshold,
        count=args.count,
        dry_run=args.dry_run,
    )

    total = sum(len(v) for v in result.values())
    if total > 0:
        print(f"\n[완료] {len(result)}개 채널에 총 {total}개 주제 {'미리보기' if args.dry_run else '추가'}")
    else:
        print("\n[완료] 보충 필요 없음 (모든 채널 pending 충분)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
