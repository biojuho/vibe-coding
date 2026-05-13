"""Bootstrap pipeline components."""

import logging
import sys

from scrapers import get_scraper
from pipeline import ImageUploader, ImageGenerator, TweetDraftGenerator
from pipeline.analytics_tracker import AnalyticsTracker
from pipeline.feedback_loop import FeedbackLoop
from pipeline.cost_tracker import CostTracker

logger = logging.getLogger(__name__)


def resolve_input_sources(config_mgr, args):
    configured_sources = config_mgr.get("input_sources", ["blind"])
    primary_source = config_mgr.get("content_strategy.primary_source", "blind")
    requested_source = getattr(args, "source", "auto") or "auto"

    if requested_source == "multi":
        return configured_sources or ["blind"]

    if requested_source != "auto":
        return [requested_source]

    if primary_source in configured_sources and primary_source != "multi":
        return [primary_source]

    return configured_sources or ["blind"]


def init_scrapers(config_mgr, args):
    """Initialize scrapers from configured input sources."""
    input_sources = resolve_input_sources(config_mgr, args)
    scrapers = {}
    for source in input_sources:
        try:
            scrapers[source] = get_scraper(source)(config_mgr)
        except Exception as exc:
            logger.warning("Could not init scraper %s: %s", source, exc)
    return scrapers


async def check_budget(config_mgr, notifier):
    """Check if daily API budget is exceeded. Exits if over budget."""
    cost_tracker = CostTracker(config_mgr)
    if cost_tracker.is_budget_exceeded():
        logger.error(
            "Daily API budget exceeded: $%.3f >= $%.3f",
            cost_tracker.current_cost,
            cost_tracker.daily_budget,
        )
        await notifier.send_message(
            f"Blind-to-X budget exceeded\nCurrent Cost: ${cost_tracker.current_cost:.3f} / Limit: ${cost_tracker.daily_budget:.3f}",
            level="CRITICAL",
        )
        sys.exit(1)
    return cost_tracker


async def load_feedback_examples(config_mgr, notion_uploader):
    feedback_loop = FeedbackLoop(notion_uploader, config_mgr)
    try:
        return await feedback_loop.get_few_shot_examples()
    except Exception as exc:  # pragma: no cover - defensive fallback
        logger.warning("Failed to load feedback examples: %s", exc)
        return []


async def init_components(args, config_mgr, scrapers, notion_uploader, cost_tracker):
    """Initialize pipeline components (generators, trackers, monitors)."""
    image_uploader = ImageUploader(config_mgr)
    image_generator = None if getattr(args, "dry_run", False) else ImageGenerator(config_mgr, cost_tracker=cost_tracker)
    draft_generator = TweetDraftGenerator(config_mgr, cost_tracker=cost_tracker)
    analytics_tracker = AnalyticsTracker(config_mgr)

    for scraper in scrapers.values():
        scraper.cleanup_old_screenshots()

    if config_mgr.get("twitter.enabled", False):
        try:
            await analytics_tracker.sync_metrics()
        except Exception as exc:
            logger.warning("Analytics sync failed before run: %s", exc)

    top_examples = await load_feedback_examples(config_mgr, notion_uploader)
    await notion_uploader.warm_cache()

    trend_monitor = None
    if config_mgr.get("trends.enabled", False):
        try:
            from pipeline.trend_monitor import TrendMonitor

            trend_monitor = TrendMonitor(config_mgr)
            await trend_monitor.get_trending_keywords()
            logger.info("TrendMonitor 초기화 완료")
        except Exception as exc:
            logger.warning("TrendMonitor 초기화 실패 (무시): %s", exc)

    feedback_loop = FeedbackLoop(notion_uploader, config_mgr)
    adaptive_weights = await feedback_loop.compute_adaptive_weights()
    if adaptive_weights:
        config_mgr.config.setdefault("ranking", {})["weights"] = adaptive_weights
        logger.info("랭킹 가중치 적응형으로 교체: %s", adaptive_weights)
    else:
        logger.info("기본 랭킹 가중치 유지 (성과 데이터 부족 또는 상관관계 없음)")

    return image_uploader, image_generator, draft_generator, top_examples, trend_monitor
