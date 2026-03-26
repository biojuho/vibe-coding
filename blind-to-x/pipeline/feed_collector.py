"""Feed collection, filtering, dedup, and per-source limit logic.

Extracted from main.py to keep the orchestration layer thin.
"""

from __future__ import annotations

import logging

from pipeline.dedup import check_cross_source_duplicates

logger = logging.getLogger(__name__)


async def collect_feed_items(config_mgr, args, scrapers) -> list[dict]:
    """Collect, filter, dedup and limit candidate posts across all sources.

    Args:
        config_mgr: ConfigManager instance.
        args: Parsed argparse Namespace (url, popular, trending, limit …).
        scrapers: Dict of {source_name: scraper_instance}.

    Returns:
        List of item dicts, each with keys:
            url, source, scraper, feed_mode, feed_title, feed_engagement.
        Also returns a stats dict as the second element when called as a tuple.
    """
    input_sources = list(scrapers.keys())
    effective_limit = args.limit or config_mgr.get("scrape_limit", 5)
    fetch_multiplier = int(config_mgr.get("feed_filter.fetch_multiplier", 2))
    min_engagement = float(config_mgr.get("feed_filter.min_engagement_score", 0))
    title_blacklist = [kw.lower() for kw in (config_mgr.get("feed_filter.title_blacklist") or [])]

    low_engagement_skips = 0
    blacklist_skips = 0
    urls_to_process: list[dict] = []

    for source_name, scraper in scrapers.items():
        feed_mode = "trending"
        if args.urls and source_name == input_sources[0]:
            # Manual URLs: wrap in items directly
            for u in args.urls:
                urls_to_process.append(
                    {
                        "url": u,
                        "source": source_name,
                        "scraper": scraper,
                        "feed_mode": "manual",
                        "feed_title": "",
                        "feed_engagement": 0,
                    }
                )
            continue

        if args.popular:
            feed_mode = "popular"
        elif args.trending or config_mgr.get("schedule.enabled", True):
            feed_mode = "trending"

        candidates = await scraper.get_feed_candidates(
            mode=feed_mode,
            limit=effective_limit * fetch_multiplier,
        )
        for candidate in candidates:
            # 제목 블랙리스트 필터
            if title_blacklist and candidate.title:
                _title_lower = candidate.title.lower()
                if any(kw in _title_lower for kw in title_blacklist):
                    logger.info(
                        "SKIP [blacklist] %s '%s' %s",
                        source_name,
                        candidate.title[:40],
                        candidate.url,
                    )
                    blacklist_skips += 1
                    continue
            if min_engagement > 0 and candidate.engagement_score < min_engagement:
                logger.info(
                    "SKIP [low engagement] %s (score=%.1f, likes=%d, comments=%d) %s",
                    source_name,
                    candidate.engagement_score,
                    candidate.likes,
                    candidate.comments,
                    candidate.url,
                )
                low_engagement_skips += 1
                continue
            urls_to_process.append(
                {
                    "url": candidate.url,
                    "source": source_name,
                    "scraper": scraper,
                    "feed_mode": feed_mode,
                    "feed_title": candidate.title,
                    "feed_engagement": candidate.engagement_score,
                }
            )

    # Sort all candidates by engagement (cross-source)
    urls_to_process.sort(key=lambda c: c.get("feed_engagement", 0), reverse=True)

    # Cross-source dedup (before individual scraping)
    cross_source_dedup_count = 0
    if config_mgr.get("dedup.cross_source_enabled", True):
        before_count = len(urls_to_process)
        sim_threshold = float(config_mgr.get("dedup.title_similarity_threshold", 0.6))
        urls_to_process = check_cross_source_duplicates(urls_to_process, threshold=sim_threshold)
        cross_source_dedup_count = before_count - len(urls_to_process)

    # Per-source limit (독식 방지: 소스별 최대 선택 수 적용)
    per_source_limits = config_mgr.get("scrape_limits_per_source", {})
    if per_source_limits:
        source_counts: dict[str, int] = {}
        limited_items: list[dict] = []
        for item in urls_to_process:
            src = item["source"]
            src_limit = int(per_source_limits.get(src, effective_limit))
            source_counts[src] = source_counts.get(src, 0) + 1
            if source_counts[src] <= src_limit:
                limited_items.append(item)
            else:
                logger.debug(
                    "Per-source limit reached for %s (%d/%d), skipping: %s",
                    src,
                    source_counts[src],
                    src_limit,
                    item.get("url", ""),
                )
        per_source_skips = len(urls_to_process) - len(limited_items)
        if per_source_skips:
            logger.info("Per-source limit applied: %d items skipped", per_source_skips)
        urls_to_process = limited_items

    # Apply global limit after sorting + dedup
    urls_to_process = urls_to_process[:effective_limit]

    # URL dedup (중복 URL 제거)
    seen: set[str] = set()
    deduped_items: list[dict] = []
    for item in urls_to_process:
        if item["url"] not in seen and item["url"].startswith(("http://", "https://")):
            seen.add(item["url"])
            deduped_items.append(item)
    urls_to_process = deduped_items

    stats = {
        "low_engagement_skips": low_engagement_skips,
        "blacklist_skips": blacklist_skips,
        "cross_source_dedup_count": cross_source_dedup_count,
    }
    return urls_to_process, stats
