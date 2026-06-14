"""Unit tests for pipeline.daily_queue_floor — queue floor helpers."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

from pipeline.daily_queue_floor import (
    DEFAULT_DAILY_QUEUE_TARGET,
    DEFAULT_RELAXED_PRE_EDITORIAL_SCORE,
    DailyQueueFloorState,
    is_daily_queue_floor_active,
    relax_per_source_limits,
    relaxed_pre_editorial_threshold,
    resolve_daily_queue_floor,
)


def _cfg(**kwargs):
    """Minimal config-like object with get()."""
    store = dict(kwargs)

    class _Cfg:
        def get(self, key, default=None):
            return store.get(key, default)

    return _Cfg()


class TestIsActiveFlag:
    def test_none_state_is_inactive(self):
        assert is_daily_queue_floor_active(None) is False

    def test_active_false_is_inactive(self):
        assert is_daily_queue_floor_active(DailyQueueFloorState(active=False, remaining=5)) is False

    def test_remaining_zero_is_inactive(self):
        assert is_daily_queue_floor_active(DailyQueueFloorState(active=True, remaining=0)) is False

    def test_active_with_remaining_is_active(self):
        assert is_daily_queue_floor_active(DailyQueueFloorState(active=True, remaining=3)) is True


class TestRelaxedPreEditorialThreshold:
    def test_none_config_returns_min_of_defaults(self):
        result = relaxed_pre_editorial_threshold(None, 30.0)
        assert result == min(30.0, DEFAULT_RELAXED_PRE_EDITORIAL_SCORE)

    def test_config_with_lower_value_uses_config(self):
        cfg = _cfg(**{"review.minimum_daily_queue_pre_editorial_score": 10.0})
        result = relaxed_pre_editorial_threshold(cfg, 30.0)
        assert result == 10.0

    def test_default_threshold_caps_relaxed(self):
        cfg = _cfg(**{"review.minimum_daily_queue_pre_editorial_score": 5.0})
        result = relaxed_pre_editorial_threshold(cfg, 3.0)
        assert result == 3.0  # default_threshold is the cap

    def test_bad_config_value_falls_back_to_default(self):
        class _BadCfg:
            def get(self, key, default=None):
                return "not-a-float"

        result = relaxed_pre_editorial_threshold(_BadCfg(), 30.0)
        assert result == min(30.0, DEFAULT_RELAXED_PRE_EDITORIAL_SCORE)


class TestRelaxPerSourceLimits:
    def test_none_config_returns_true(self):
        assert relax_per_source_limits(None) is True

    def test_config_false_returns_false(self):
        cfg = _cfg(**{"review.minimum_daily_queue_relax_per_source_limits": False})
        assert relax_per_source_limits(cfg) is False

    def test_config_true_returns_true(self):
        cfg = _cfg(**{"review.minimum_daily_queue_relax_per_source_limits": True})
        assert relax_per_source_limits(cfg) is True


class TestResolveDailyQueueFloor:
    def _run(self, coro):
        return asyncio.run(coro)

    def test_review_only_false_returns_inactive(self):
        state = self._run(resolve_daily_queue_floor(None, MagicMock(), review_only=False))
        assert state.active is False

    def test_notion_uploader_none_returns_inactive(self):
        state = self._run(resolve_daily_queue_floor(None, None, review_only=True))
        assert state.active is False

    def test_target_zero_returns_inactive(self):
        cfg = _cfg(**{"review.minimum_daily_queue": 0})
        state = self._run(resolve_daily_queue_floor(cfg, MagicMock(), review_only=True))
        assert state.active is False

    def test_bad_target_config_falls_back_to_default(self):
        class _BadCfg:
            def get(self, key, default=None):
                return "oops"

        uploader = AsyncMock()
        uploader.get_recent_pages = AsyncMock(return_value=[])
        state = self._run(resolve_daily_queue_floor(_BadCfg(), uploader, review_only=True))
        assert state.target == DEFAULT_DAILY_QUEUE_TARGET

    def test_notion_failure_returns_zero_current(self):
        cfg = _cfg(**{"review.minimum_daily_queue": 5})
        uploader = AsyncMock()
        uploader.get_recent_pages = AsyncMock(side_effect=RuntimeError("network error"))
        state = self._run(resolve_daily_queue_floor(cfg, uploader, review_only=True))
        assert state.current == 0
        assert state.active is True  # remaining = 5 - 0 > 0

    def test_all_pages_today_fills_floor(self):
        from datetime import datetime, timezone

        cfg = _cfg(**{"review.minimum_daily_queue": 2})
        today_iso = datetime.now(timezone.utc).isoformat()
        uploader = AsyncMock()
        uploader.get_recent_pages = AsyncMock(
            return_value=[
                {"created_time": today_iso},
                {"created_time": today_iso},
            ]
        )
        state = self._run(resolve_daily_queue_floor(cfg, uploader, review_only=True))
        assert state.current == 2
        assert state.remaining == 0
        assert state.active is False
