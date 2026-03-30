"""YAML 규칙 자동 갱신 스크립트 (Phase 3-1).

커뮤니티 트렌드(에펨코리아, 뽐뿌) 또는 Google Trends에서 인기 키워드를 수집해
`classification_rules.yaml`의 topic_rules에 새 키워드를 병합합니다.

사용법:
    python scripts/update_classification_rules.py [--dry-run] [--min-freq N]

동작:
1. 커뮤니티 트렌드 스크래퍼로 인기 게시글 제목 수집
2. 명사 추출 (간단한 정규식 기반, 2글자 이상 한글)
3. 기존 규칙에 없는 고빈도 단어를 후보로 선정
4. --dry-run 시 후보만 출력, 아니면 YAML 파일에 병합
5. 병합 시 기존 규칙 순서·내용 유지 (새 항목은 파일 끝에 추가)

주의: 자동 병합은 topic_rules에만 적용. emotion/hook/audience는 수동 관리.
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
from collections import Counter
from pathlib import Path

import yaml

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# 프로젝트 루트 기준 상대 경로
_BTX_ROOT = Path(__file__).resolve().parent.parent
_RULES_PATH = _BTX_ROOT / "rules" / "classification.yaml"
_ROOT_PROJ = _BTX_ROOT.parent

# 공통 조사/어미 (불용어) — 한글 2글자 이상이어도 토픽 의미 없는 것들
_STOPWORDS = {
    "이거",
    "저거",
    "그거",
    "이건",
    "저건",
    "그건",
    "그냥",
    "진짜",
    "정말",
    "너무",
    "매우",
    "아주",
    "그리고",
    "하지만",
    "그래서",
    "그러나",
    "그런데",
    "이미",
    "이제",
    "또한",
    "갑자기",
    "드디어",
    "어떻게",
    "왜지",
    "무슨",
    "이런",
    "저런",
    "나도",
    "나는",
    "저는",
    "우리",
    "자기",
    "저한테",
    "회사",
    "직장",
    "직원",
    "사람",
    "대리",
    "부장",  # 너무 일반적
}

# 최소 단어 길이
_MIN_WORD_LEN = 2
# 최대 단어 길이 (긴 복합어 제외)
_MAX_WORD_LEN = 7


def _extract_nouns_simple(text: str) -> list[str]:
    """간단한 정규식 기반 한글 명사 추출."""
    tokens = re.findall(r"[가-힣]{%d,%d}" % (_MIN_WORD_LEN, _MAX_WORD_LEN), text)
    return [t for t in tokens if t not in _STOPWORDS]


def _collect_community_titles(limit: int = 100) -> list[str]:
    """커뮤니티 트렌드 스크래퍼로 인기 게시글 제목 수집."""
    titles: list[str] = []
    try:
        # 루트 프로젝트 execution/ 경로 추가
        if str(_ROOT_PROJ) not in sys.path:
            sys.path.insert(0, str(_ROOT_PROJ))

        from execution.community_trend_scraper import scrape_trending_posts

        posts = scrape_trending_posts(limit=limit)
        titles = [p.get("title", "") for p in posts if p.get("title")]
        logger.info("커뮤니티 트렌드 수집: %d개 게시글 제목", len(titles))
    except Exception as exc:
        logger.warning("커뮤니티 트렌드 수집 실패 (fallback: 빈 리스트): %s", exc)
    return titles


def _collect_google_trends_titles() -> list[str]:
    """pytrends Google 트렌드 키워드 수집 (선택적 폴백)."""
    try:
        from pytrends.request import TrendReq

        pt = TrendReq(hl="ko-KR", tz=540, timeout=(10, 25))
        df = pt.trending_searches(pn="south_korea")
        keywords = df[0].tolist()
        logger.info("Google Trends 수집: %d개 키워드", len(keywords))
        return keywords
    except Exception as exc:
        logger.debug("Google Trends 수집 실패 (무시): %s", exc)
        return []


def _load_existing_keywords(rules_path: Path) -> set[str]:
    """현재 YAML의 모든 topic_rules 키워드를 set으로 반환."""
    with rules_path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    keywords: set[str] = set()
    for rule in data.get("topic_rules", []):
        for kw in rule.get("keywords", []):
            keywords.add(kw)
    return keywords


def _build_candidate_keywords(
    titles: list[str],
    existing: set[str],
    min_freq: int = 3,
) -> list[tuple[str, int]]:
    """고빈도 신규 키워드 후보 반환 (word, frequency) 리스트."""
    counter: Counter = Counter()
    for title in titles:
        nouns = _extract_nouns_simple(title)
        counter.update(nouns)

    candidates = [(word, freq) for word, freq in counter.most_common(50) if freq >= min_freq and word not in existing]
    return candidates


def _merge_into_yaml(
    rules_path: Path,
    candidates: list[tuple[str, int]],
    label: str = "트렌드_자동",
) -> int:
    """후보 키워드를 topic_rules에 병합. 반환: 실제로 추가된 키워드 수."""
    with rules_path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    topic_rules: list[dict] = data.get("topic_rules", [])

    # 이미 "트렌드_자동" 라벨 존재 시 해당 항목에 병합
    auto_rule = next((r for r in topic_rules if r.get("label") == label), None)
    existing_in_auto: set[str] = set(auto_rule.get("keywords", [])) if auto_rule else set()

    new_keywords = [w for w, _ in candidates if w not in existing_in_auto]
    if not new_keywords:
        logger.info("병합할 신규 키워드 없음.")
        return 0

    if auto_rule is None:
        topic_rules.append({"label": label, "keywords": new_keywords})
    else:
        auto_rule["keywords"] = sorted(set(auto_rule["keywords"]) | set(new_keywords))

    data["topic_rules"] = topic_rules

    # 원본 주석 보존을 위해 파일 헤더(#으로 시작하는 줄)를 유지
    original_lines = rules_path.read_text(encoding="utf-8").splitlines(keepends=True)
    header_lines = []
    for line in original_lines:
        if line.startswith("#"):
            header_lines.append(line)
        else:
            break

    body = yaml.dump(data, allow_unicode=True, sort_keys=False, default_flow_style=False)
    rules_path.write_text("".join(header_lines) + body, encoding="utf-8")

    logger.info("분류 규칙 업데이트 완료: +%d 키워드 → '%s' 라벨", len(new_keywords), label)
    try:
        if str(_BTX_ROOT) not in sys.path:
            sys.path.insert(0, str(_BTX_ROOT))
        from pipeline.rules_loader import write_legacy_rules_snapshot

        write_legacy_rules_snapshot()
    except Exception as exc:
        logger.warning("Legacy rules snapshot sync failed: %s", exc)
    return len(new_keywords)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="classification_rules.yaml 자동 갱신")
    parser.add_argument("--dry-run", action="store_true", help="파일 수정 없이 후보만 출력")
    parser.add_argument("--min-freq", type=int, default=3, help="최소 출현 빈도 (기본 3)")
    parser.add_argument("--limit", type=int, default=100, help="커뮤니티 게시글 수집 한도")
    args = parser.parse_args(argv)

    if not _RULES_PATH.exists():
        logger.error("YAML 파일 없음: %s", _RULES_PATH)
        return 1

    # 1. 제목 수집
    titles = _collect_community_titles(limit=args.limit)
    titles += _collect_google_trends_titles()

    if not titles:
        logger.warning("수집된 제목이 없습니다. 작업 중단.")
        return 0

    # 2. 기존 키워드 로드
    existing = _load_existing_keywords(_RULES_PATH)
    logger.info("기존 키워드 수: %d", len(existing))

    # 3. 후보 선정
    candidates = _build_candidate_keywords(titles, existing, min_freq=args.min_freq)
    if not candidates:
        logger.info("신규 후보 키워드 없음 (min_freq=%d).", args.min_freq)
        return 0

    logger.info("신규 후보 키워드 %d개:", len(candidates))
    for word, freq in candidates:
        logger.info("  '%s' (출현 %d회)", word, freq)

    if args.dry_run:
        logger.info("[dry-run] 파일 미수정.")
        return 0

    # 4. 병합
    added = _merge_into_yaml(_RULES_PATH, candidates)
    logger.info("완료: %d개 추가됨", added)
    return 0


if __name__ == "__main__":
    sys.exit(main())
