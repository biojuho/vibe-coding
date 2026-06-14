import asyncio
import logging
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from pipeline.bootstrap import _log_cost_persistence_status, check_budget, init_components


class _FakeCostTracker:
    current_cost = 0.0
    daily_budget = 10.0

    def __init__(self, _config=None, *, status=None, budget_exceeded=False):
        self._status = status or {
            "status": "sqlite_enabled",
            "fail_open": False,
            "event_count": 0,
            "operation_count": 0,
            "operations": [],
            "operator_action": "",
        }
        self._budget_exceeded = budget_exceeded
        self.budget_checked = False

    def is_budget_exceeded(self):
        self.budget_checked = True
        return self._budget_exceeded

    def get_cost_persistence_status(self):
        if isinstance(self._status, Exception):
            raise self._status
        return self._status


class _FakeConfig:
    def __init__(self, values):
        self.values = values
        self.config = {}

    def get(self, key, default=None):
        return self.values.get(key, default)


def test_init_components_treats_string_false_optional_flags_as_disabled(monkeypatch):
    analytics = MagicMock()
    analytics.sync_metrics = AsyncMock()
    feedback = MagicMock()
    feedback.get_few_shot_examples = AsyncMock(return_value=[])
    feedback.compute_adaptive_weights = AsyncMock(return_value={})
    notion = MagicMock()
    notion.warm_cache = AsyncMock()
    scraper = MagicMock()
    trend_cls = MagicMock()

    monkeypatch.setattr("pipeline.bootstrap.ImageUploader", lambda _config: MagicMock())
    monkeypatch.setattr("pipeline.bootstrap.ImageGenerator", lambda _config, cost_tracker=None: MagicMock())
    monkeypatch.setattr("pipeline.bootstrap.TweetDraftGenerator", lambda _config, cost_tracker=None: MagicMock())
    monkeypatch.setattr("pipeline.bootstrap.AnalyticsTracker", lambda _config: analytics)
    monkeypatch.setattr("pipeline.bootstrap.FeedbackLoop", lambda _notion, _config: feedback)
    monkeypatch.setitem(sys.modules, "pipeline.trend_monitor", SimpleNamespace(TrendMonitor=trend_cls))

    asyncio.run(
        init_components(
            SimpleNamespace(dry_run=True),
            _FakeConfig({"twitter.enabled": "false", "trends.enabled": "false"}),
            {"blind": scraper},
            notion,
            MagicMock(),
        )
    )

    scraper.cleanup_old_screenshots.assert_called_once_with()
    analytics.sync_metrics.assert_not_awaited()
    trend_cls.assert_not_called()
    notion.warm_cache.assert_awaited_once_with()


def test_log_cost_persistence_status_warns_with_operator_action(caplog):
    tracker = _FakeCostTracker(
        status={
            "status": "degraded",
            "fail_open": True,
            "event_count": 2,
            "retained_event_count": 2,
            "total_event_count": 7,
            "operation_count": 2,
            "operations": ["cost_tracker.record_text_cost", "cost_tracker.get_today_summary"],
            "operator_action": "Check .tmp/btx_costs.db permissions/locks.",
        }
    )

    with caplog.at_level(logging.WARNING, logger="pipeline.bootstrap"):
        _log_cost_persistence_status(tracker)

    assert "Cost persistence status: status=degraded fail_open=True event_count=2 operation_count=2" in caplog.text
    assert "operations=cost_tracker.record_text_cost,cost_tracker.get_today_summary" in caplog.text
    assert "retained_event_count=2 total_event_count=7" in caplog.text
    assert "Cost persistence operator action: Check .tmp/btx_costs.db permissions/locks." in caplog.text


def test_log_cost_persistence_status_uses_info_for_healthy_sqlite(caplog):
    tracker = _FakeCostTracker(
        status={
            "status": "sqlite_enabled",
            "fail_open": False,
            "event_count": 0,
            "operation_count": 0,
            "operations": [],
            "operator_action": "",
        }
    )

    with caplog.at_level(logging.INFO, logger="pipeline.bootstrap"):
        _log_cost_persistence_status(tracker)

    assert (
        "Cost persistence status: status=sqlite_enabled fail_open=False event_count=0 operation_count=0" in caplog.text
    )
    assert "operations=-" in caplog.text
    assert "Cost persistence operator action" not in caplog.text
    assert [record.levelno for record in caplog.records] == [logging.INFO]


def test_log_cost_persistence_status_keeps_partial_healthy_sqlite_at_info(caplog):
    tracker = _FakeCostTracker(
        status={
            "status": "sqlite_enabled",
            "event_count": 0,
            "operation_count": 0,
            "operations": [],
            "operator_action": "",
        }
    )

    with caplog.at_level(logging.INFO, logger="pipeline.bootstrap"):
        _log_cost_persistence_status(tracker)

    assert (
        "Cost persistence status: status=sqlite_enabled fail_open=None event_count=0 operation_count=0" in caplog.text
    )
    assert "operations=-" in caplog.text
    assert "Cost persistence operator action" not in caplog.text
    assert [record.levelno for record in caplog.records] == [logging.INFO]


def test_log_cost_persistence_status_handles_corrupt_operations_metadata(caplog):
    tracker = _FakeCostTracker(
        status={
            "status": "degraded",
            "fail_open": True,
            "event_count": 3,
            "operation_count": 1,
            "operations": "cost_tracker.record_text_cost",
            "operator_action": "Check .tmp/btx_costs.db permissions/locks.",
        }
    )

    with caplog.at_level(logging.WARNING, logger="pipeline.bootstrap"):
        _log_cost_persistence_status(tracker)

    assert "Cost persistence status: status=degraded fail_open=True event_count=3 operation_count=1" in caplog.text
    assert "operations=-" in caplog.text
    assert "c,o,s,t,_" not in caplog.text
    assert "Cost persistence operator action: Check .tmp/btx_costs.db permissions/locks." in caplog.text


def test_log_cost_persistence_status_defaults_missing_count_fields(caplog):
    tracker = _FakeCostTracker(
        status={
            "status": "degraded",
            "fail_open": True,
            "operations": [],
            "operator_action": "Check .tmp/btx_costs.db permissions/locks.",
        }
    )

    with caplog.at_level(logging.WARNING, logger="pipeline.bootstrap"):
        _log_cost_persistence_status(tracker)

    assert "Cost persistence status: status=degraded fail_open=True event_count=0 operation_count=0" in caplog.text
    assert "operations=-" in caplog.text
    assert "Cost persistence operator action: Check .tmp/btx_costs.db permissions/locks." in caplog.text


def test_log_cost_persistence_status_defaults_missing_status_field(caplog):
    tracker = _FakeCostTracker(
        status={
            "fail_open": True,
            "event_count": 4,
            "operation_count": 2,
            "operations": ["cost_tracker.record_image_cost"],
            "operator_action": "Check .tmp/btx_costs.db permissions/locks.",
        }
    )

    with caplog.at_level(logging.WARNING, logger="pipeline.bootstrap"):
        _log_cost_persistence_status(tracker)

    assert "Cost persistence status: status=unknown fail_open=True event_count=4 operation_count=2" in caplog.text
    assert "operations=cost_tracker.record_image_cost" in caplog.text
    assert "Cost persistence operator action: Check .tmp/btx_costs.db permissions/locks." in caplog.text


def test_log_cost_persistence_status_warns_for_degraded_status_without_fail_open(caplog):
    tracker = _FakeCostTracker(
        status={
            "status": "degraded",
            "event_count": 5,
            "operation_count": 1,
            "operations": ["cost_tracker.record_text_cost"],
            "operator_action": "",
        }
    )

    with caplog.at_level(logging.WARNING, logger="pipeline.bootstrap"):
        _log_cost_persistence_status(tracker)

    assert "Cost persistence status: status=degraded fail_open=None event_count=5 operation_count=1" in caplog.text
    assert "operations=cost_tracker.record_text_cost" in caplog.text
    assert "Cost persistence operator action" not in caplog.text
    assert [record.levelno for record in caplog.records] == [logging.WARNING]


def test_log_cost_persistence_status_warns_for_unknown_status_without_fail_open(caplog):
    tracker = _FakeCostTracker(
        status={
            "event_count": 6,
            "operation_count": 1,
            "operations": ["cost_tracker.get_today_summary"],
            "operator_action": "",
        }
    )

    with caplog.at_level(logging.WARNING, logger="pipeline.bootstrap"):
        _log_cost_persistence_status(tracker)

    assert "Cost persistence status: status=unknown fail_open=None event_count=6 operation_count=1" in caplog.text
    assert "operations=cost_tracker.get_today_summary" in caplog.text
    assert "Cost persistence operator action" not in caplog.text
    assert [record.levelno for record in caplog.records] == [logging.WARNING]


def test_log_cost_persistence_status_warns_for_invalid_payload(caplog):
    tracker = _FakeCostTracker(status="not-a-status-dict")

    with caplog.at_level(logging.WARNING, logger="pipeline.bootstrap"):
        _log_cost_persistence_status(tracker)

    assert "Cost persistence status unavailable: invalid payload" in caplog.text
    assert "Cost persistence status: status=" not in caplog.text
    assert "Cost persistence operator action" not in caplog.text


@pytest.mark.asyncio
async def test_check_budget_continues_when_cost_status_probe_fails(monkeypatch, caplog):
    tracker = _FakeCostTracker(status=RuntimeError("status backend offline"))
    monkeypatch.setattr("pipeline.bootstrap.CostTracker", lambda config: tracker)
    notifier = AsyncMock()

    with caplog.at_level(logging.WARNING, logger="pipeline.bootstrap"):
        result = await check_budget(object(), notifier)

    assert result is tracker
    assert tracker.budget_checked is True
    notifier.send_message.assert_not_awaited()
    assert "Cost persistence status unavailable: status backend offline" in caplog.text
    assert "Daily API budget exceeded" not in caplog.text


@pytest.mark.asyncio
async def test_check_budget_logs_cost_persistence_from_existing_tracker(monkeypatch, caplog):
    status = {
        "status": "in_memory_only",
        "fail_open": True,
        "event_count": 0,
        "operation_count": 0,
        "operations": [],
        "operator_action": "Check .tmp/btx_costs.db permissions/locks.",
    }
    tracker = _FakeCostTracker(status=status)
    monkeypatch.setattr("pipeline.bootstrap.CostTracker", lambda config: tracker)
    notifier = AsyncMock()

    with caplog.at_level(logging.WARNING, logger="pipeline.bootstrap"):
        result = await check_budget(object(), notifier)

    assert result is tracker
    assert tracker.budget_checked is True
    notifier.send_message.assert_not_awaited()
    assert "Cost persistence status: status=in_memory_only fail_open=True" in caplog.text
    assert "Cost persistence operator action: Check .tmp/btx_costs.db permissions/locks." in caplog.text


@pytest.mark.asyncio
async def test_check_budget_logs_cost_persistence_before_budget_exit(monkeypatch, caplog):
    status = {
        "status": "degraded",
        "fail_open": True,
        "event_count": 1,
        "operation_count": 1,
        "operations": ["cost_tracker.get_today_summary"],
        "operator_action": "Check .tmp/btx_costs.db permissions/locks.",
    }
    tracker = _FakeCostTracker(status=status, budget_exceeded=True)
    tracker.current_cost = 11.0
    tracker.daily_budget = 10.0
    monkeypatch.setattr("pipeline.bootstrap.CostTracker", lambda config: tracker)
    notifier = AsyncMock()

    with caplog.at_level(logging.WARNING, logger="pipeline.bootstrap"):
        with pytest.raises(SystemExit) as exc_info:
            await check_budget(object(), notifier)

    assert exc_info.value.code == 1
    assert tracker.budget_checked is True
    notifier.send_message.assert_awaited_once()
    assert "Current Cost: $11.000 / Limit: $10.000" in notifier.send_message.await_args.args[0]
    assert notifier.send_message.await_args.kwargs["level"] == "CRITICAL"

    messages = [record.getMessage() for record in caplog.records]
    status_index = next(
        index for index, message in enumerate(messages) if message.startswith("Cost persistence status:")
    )
    budget_index = next(
        index for index, message in enumerate(messages) if message.startswith("Daily API budget exceeded:")
    )
    assert status_index < budget_index
    assert "Cost persistence status: status=degraded fail_open=True event_count=1 operation_count=1" in caplog.text
    assert "operations=cost_tracker.get_today_summary" in caplog.text
    assert "Cost persistence operator action: Check .tmp/btx_costs.db permissions/locks." in caplog.text
