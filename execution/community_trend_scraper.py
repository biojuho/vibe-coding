"""
커뮤니티 트렌드 수집 스크립트.

dopamine-bot 스크래퍼를 라이브러리로 호출하여 한국 커뮤니티 인기 게시글 제목을 수집.
shorts-maker-v2의 토픽 자동 생성(topic_auto_generator.py)에 추가 시그널로 사용.

Usage (library):
    from execution.community_trend_scraper import get_community_trends
    trends = get_community_trends(sources=["fmkorea", "ppomppu"], limit=10)

Usage (CLI):
    python execution/community_trend_scraper.py
    python execution/community_trend_scraper.py --source fmkorea --limit 5 --json
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

_BOT_DIR = Path(__file__).resolve().parent.parent / "dopamine-bot"
_SCRAPERS_DIR = _BOT_DIR / "scrapers"
_CONFIG_PATH = _BOT_DIR / "config.yaml"

# dopamine-bot 스크래퍼 lazy import (경로가 없을 수도 있으므로 가드)
_FMKoreaScraper = None
_PpomppuScraper = None

if _SCRAPERS_DIR.is_dir():
    sys.path.insert(0, str(_BOT_DIR))
    try:
        from scrapers.fmkorea import FMKoreaScraper as _FMKoreaScraper  # noqa: F401
    except ImportError:
        logger.debug("FMKoreaScraper import 실패")
    try:
        from scrapers.ppomppu import PpomppuScraper as _PpomppuScraper  # noqa: F401
    except ImportError:
        logger.debug("PpomppuScraper import 실패")


def _load_config(config_path: str | None = None) -> dict:
    """dopamine-bot/config.yaml 로드. 실패 시 빈 dict 반환."""
    path = Path(config_path) if config_path else _CONFIG_PATH
    if not path.exists():
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        logger.warning("config 로드 실패: %s", path)
        return {}


_SCRAPER_MAP: dict[str, tuple] = {
    "fmkorea": ("_FMKoreaScraper", "fmkorea"),
    "ppomppu": ("_PpomppuScraper", "ppomppu"),
}

ALL_SOURCES = list(_SCRAPER_MAP.keys())


def get_community_trends(
    sources: list[str] | None = None,
    limit: int = 10,
    config_path: str | None = None,
) -> list[dict[str, str]]:
    """한국 커뮤니티 인기 게시글 수집.

    Returns:
        list of dicts: {'title', 'source', 'views', 'recommendations', 'link'}
        소스 실패 시 해당 소스만 건너뛰고 나머지 결과 반환.
    """
    target_sources = sources or ALL_SOURCES
    config = _load_config(config_path)
    scraper_configs = config.get("dopamine_bot", {}).get("scrapers", {})
    all_posts: list[dict[str, str]] = []

    for source_name in target_sources:
        if source_name not in _SCRAPER_MAP:
            logger.warning("알 수 없는 소스: %s", source_name)
            continue

        scraper_var, config_key = _SCRAPER_MAP[source_name]
        scraper_cls = globals().get(scraper_var)
        if scraper_cls is None:
            logger.debug("%s 스크래퍼 미사용 (import 실패)", source_name)
            continue

        src_conf = scraper_configs.get(config_key, {})
        if not src_conf.get("enabled", True):
            logger.debug("%s 비활성화됨", source_name)
            continue

        try:
            post_limit = src_conf.get("post_limit", limit)
            if source_name == "fmkorea":
                target_url = src_conf.get("target_url", "https://www.fmkorea.com/index.php?mid=best&listStyle=list")
                scraper = scraper_cls(target_url=target_url, post_limit=post_limit)
            else:
                scraper = scraper_cls(post_limit=post_limit)
            posts = scraper.scrape()
            all_posts.extend(posts)
        except Exception:
            logger.warning("%s 스크래핑 실패 (무시)", source_name, exc_info=True)

    return all_posts[:limit]


def get_community_trend_titles(
    sources: list[str] | None = None,
    limit: int = 10,
    config_path: str | None = None,
) -> list[str]:
    """커뮤니티 인기 게시글 제목만 추출. GPT 프롬프트 주입용."""
    posts = get_community_trends(sources=sources, limit=limit, config_path=config_path)
    return [p["title"] for p in posts if p.get("title")]


def main() -> int:
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    parser = argparse.ArgumentParser(description="커뮤니티 트렌드 수집")
    parser.add_argument("--source", choices=ALL_SOURCES, help="특정 소스만 수집")
    parser.add_argument("--limit", type=int, default=10, help="최대 수집 수 (기본: 10)")
    parser.add_argument("--json", action="store_true", help="JSON 형식 출력")
    args = parser.parse_args()

    sources = [args.source] if args.source else None
    trends = get_community_trends(sources=sources, limit=args.limit)

    if args.json:
        print(json.dumps(trends, ensure_ascii=False, indent=2))
    else:
        print(f"[커뮤니티 트렌드] {len(trends)}건 수집")
        for i, post in enumerate(trends, 1):
            print(f"  {i}. [{post.get('source', '?')}] {post.get('title', '?')} (조회: {post.get('views', '?')})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
