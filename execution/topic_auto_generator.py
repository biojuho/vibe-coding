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

import io
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

# Windows cp949 인코딩 문제 방지
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from execution.content_db import add_topic, get_all, get_channels, get_top_performing_topics, init_db  # noqa: E402

THRESHOLD = 3   # pending이 이 이하면 보충
GEN_COUNT = 5   # 한 번에 생성할 주제 수
MODEL = "gpt-4o-mini"

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
) -> list[str]:
    """GPT로 채널에 맞는 새 주제 생성. 성과 데이터 기반 추천 지원."""
    key = api_key or os.getenv("OPENAI_API_KEY", "")
    if not key:
        print("[WARN] OPENAI_API_KEY 없음 - 주제 생성 스킵")
        return []

    client = OpenAI(api_key=key, timeout=60)

    existing_str = "\n".join(f"- {t}" for t in existing_topics[-30:])

    performance_context = ""
    if top_performers:
        perf_lines = [f"- {t['topic']} (비용: ${t.get('cost_usd', 0):.3f})" for t in top_performers[:10]]
        performance_context = f"""

최근 성공한 주제 패턴 (참고):
{chr(10).join(perf_lines)}

위 성공 패턴과 유사한 스타일/형식의 주제를 우선 생성하세요."""

    user_prompt = f"""채널: {channel}

기존 주제 목록 (중복 방지):
{existing_str}
{performance_context}

위 주제들과 겹치지 않는 새로운 주제 {count}개를 생성하세요.
형식(리스트형, 비교형, 스토리형, 질문형)과 감정톤(호기심, 공포, 감동, 유머)을 골고루 섞어주세요.
JSON 형식: {{"topics": [...]}}"""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.9,
    )
    content = (response.choices[0].message.content or "").strip()
    if not content:
        return []

    data = json.loads(content)
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

        print(f"  [{ch}] pending {len(pending)}개 <= {threshold} -> 보충 시작")
        existing = [i["topic"] for i in items]
        top_performers = get_top_performing_topics(limit=10, channel=ch)
        new_topics = generate_topics(ch, existing, count=count, top_performers=top_performers)

        if not new_topics:
            print(f"  [{ch}] 생성 실패 또는 결과 없음")
            continue

        result[ch] = new_topics
        for topic in new_topics:
            if dry_run:
                print(f"    [DRY] {topic}")
            else:
                add_topic(topic, channel=ch, notes="auto-generated")
                print(f"    [ADD] {topic}")

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
