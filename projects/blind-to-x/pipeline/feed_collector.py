"""Feed collection, filtering, dedup, and per-source limit logic.

Extracted from main.py to keep the orchestration layer thin.
"""

from __future__ import annotations

import logging

from pipeline.content_intelligence import evaluate_candidate_editorial_fit
from pipeline.daily_queue_floor import (
    DailyQueueFloorState,
    is_daily_queue_floor_active,
    relax_per_source_limits,
    relaxed_pre_editorial_threshold,
)
from pipeline.dedup import check_cross_source_duplicates

logger = logging.getLogger(__name__)


async def collect_feed_items(config_mgr, args, scrapers, daily_queue_floor: DailyQueueFloorState | None = None) -> tuple[list[dict], dict]:
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
    floor_active = is_daily_queue_floor_active(daily_queue_floor)
    if floor_active:
        effective_limit = max(effective_limit, daily_queue_floor.remaining)

    fetch_multiplier = int(config_mgr.get("feed_filter.fetch_multiplier", 3))
    min_engagement = float(config_mgr.get("feed_filter.min_engagement_score", 0))
    title_blacklist = [kw.lower() for kw in (config_mgr.get("feed_filter.title_blacklist") or [])]
    # Pre-screening (title-only) uses a lower bar than the full editorial
    # threshold; full scoring with content happens after scraping in process.py.
    min_pre_editorial_score = float(config_mgr.get("feed_filter.min_pre_editorial_score", 35))
    if floor_active:
        min_pre_editorial_score = relaxed_pre_editorial_threshold(config_mgr, min_pre_editorial_score)
        logger.info(
            "[daily_queue_floor] active: current=%d target=%d remaining=%d pre_editorial>=%.1f limit=%d",
            daily_queue_floor.current,
            daily_queue_floor.target,
            daily_queue_floor.remaining,
            min_pre_editorial_score,
            effective_limit,
        )

    low_engagement_skips = 0
    blacklist_skips = 0
    editorial_skips = 0
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
                        "pre_editorial_score": 100,
                        "pre_editorial_reasons": ["수동 지정 URL"],
                        "pre_editorial_dimensions": {},
                        "pre_editorial_topic_cluster": "기타",
                        "pre_editorial_empathy_anchor": "",
                        "pre_editorial_spinoff_angle": "",
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

            editorial_fit = evaluate_candidate_editorial_fit(
                title=candidate.title,
                source=source_name,
                content="",
            )
            pre_editorial_score = float(editorial_fit.get("score", 0.0) or 0.0)
            # Title-only pre-screening: ignore hard_reject (designed for
            # title+content) and use a lower threshold.  Full editorial
            # scoring runs again after scraping with the actual content.
            if pre_editorial_score < min_pre_editorial_score:
                logger.info(
                    "SKIP [pre-editorial] %s '%s' score=%.1f reasons=%s",
                    source_name,
                    (candidate.title or "")[:60],
                    pre_editorial_score,
                    ", ".join(editorial_fit.get("hard_reject_reasons") or editorial_fit.get("reason_labels") or []),
                )
                editorial_skips += 1
                continue
            urls_to_process.append(
                {
                    "url": candidate.url,
                    "source": source_name,
                    "scraper": scraper,
                    "feed_mode": feed_mode,
                    "feed_title": candidate.title,
                    "feed_engagement": candidate.engagement_score,
                    "pre_editorial_score": pre_editorial_score,
                    "pre_editorial_reasons": editorial_fit.get("reason_labels", []),
                    "pre_editorial_dimensions": editorial_fit.get("dimensions", {}),
                    "pre_editorial_topic_cluster": editorial_fit.get("topic_cluster", "기타"),
                    "pre_editorial_empathy_anchor": editorial_fit.get("empathy_anchor", ""),
                    "pre_editorial_spinoff_angle": editorial_fit.get("spinoff_angle", ""),
                }
            )

    # Sort by editorial fit first, engagement second.
    urls_to_process.sort(
        key=lambda c: (
            c.get("pre_editorial_score", 0),
            c.get("feed_engagement", 0),
        ),
        reverse=True,
    )

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
        relax_source_limits = floor_active and relax_per_source_limits(config_mgr)
        for item in urls_to_process:
            src = item["source"]
            src_limit = int(per_source_limits.get(src, effective_limit))
            if relax_source_limits:
                src_limit = max(src_limit, effective_limit)
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
        "editorial_skips": editorial_skips,
        "cross_source_dedup_count": cross_source_dedup_count,
    }
    return urls_to_process, stats
