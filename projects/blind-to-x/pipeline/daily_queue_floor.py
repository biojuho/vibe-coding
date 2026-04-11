"""Daily Notion queue floor helpers for review-only runs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import logging
from typing import Any
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

DEFAULT_DAILY_QUEUE_TARGET = 5
DEFAULT_RELAXED_PRE_EDITORIAL_SCORE = 20.0


@dataclass(frozen=True)
class DailyQueueFloorState:
    target: int = 0
    current: int = 0
    remaining: int = 0
    active: bool = False


def is_daily_queue_floor_active(state: DailyQueueFloorState | None) -> bool:
    return bool(state and state.active and state.remaining > 0)


def relaxed_pre_editorial_threshold(config: Any, default_threshold: float) -> float:
    if config is None or not hasattr(config, "get"):
        return min(default_threshold, DEFAULT_RELAXED_PRE_EDITORIAL_SCORE)

    try:
        relaxed = float(
            config.get(
                "review.minimum_daily_queue_pre_editorial_score",
                DEFAULT_RELAXED_PRE_EDITORIAL_SCORE,
            )
        )
    except Exception:
        relaxed = DEFAULT_RELAXED_PRE_EDITORIAL_SCORE
    return min(default_threshold, relaxed)


def relax_per_source_limits(config: Any) -> bool:
    if config is None or not hasattr(config, "get"):
        return True
    return bool(config.get("review.minimum_daily_queue_relax_per_source_limits", True))


def _resolve_timezone(config: Any) -> ZoneInfo:
    tz_name = "Asia/Seoul"
    if config is not None and hasattr(config, "get"):
        tz_name = str(config.get("schedule.timezone", tz_name) or tz_name)
    try:
        return ZoneInfo(tz_name)
    except Exception:
        logger.warning("Unknown timezone '%s'; falling back to Asia/Seoul", tz_name)
        return ZoneInfo("Asia/Seoul")


def _parse_created_time(value: Any, tz: ZoneInfo) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(tz)
    except (TypeError, ValueError):
        return None


async def resolve_daily_queue_floor(
    config: Any,
    notion_uploader: Any,
    review_only: bool,
) -> DailyQueueFloorState:
    """Compute how many review cards are still needed for today's floor."""
    if config is not None and hasattr(config, "get"):
        try:
            target = int(config.get("review.minimum_daily_queue", DEFAULT_DAILY_QUEUE_TARGET))
        except Exception:
            target = DEFAULT_DAILY_QUEUE_TARGET
    else:
        target = DEFAULT_DAILY_QUEUE_TARGET

    if target <= 0 or not review_only or notion_uploader is None:
        return DailyQueueFloorState(target=max(target, 0))

    tz = _resolve_timezone(config)
    day_start = datetime.now(tz).replace(hour=0, minute=0, second=0, microsecond=0)
    lookback_days = 2
    page_limit = max(target * 20, 100)

    try:
        pages = await notion_uploader.get_recent_pages(days=lookback_days, limit=page_limit)
        current = 0
        for page in pages:
            created_at = _parse_created_time(page.get("created_time"), tz)
            if created_at and created_at >= day_start:
                current += 1
    except Exception as exc:
        logger.warning("Daily queue floor count failed; assuming 0 current cards: %s", exc)
        current = 0

    remaining = max(0, target - current)
    return DailyQueueFloorState(
        target=target,
        current=current,
        remaining=remaining,
        active=remaining > 0,
    )
