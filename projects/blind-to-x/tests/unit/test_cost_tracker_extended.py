from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.cost_db import CostDatabase  # noqa: E402
from pipeline.cost_tracker import CostTracker  # noqa: E402


class FakeConfig:
    def __init__(self, data: dict):
        self.data = data

    def get(self, key, default=None):
        current = self.data
        for part in key.split("."):
            if not isinstance(current, dict):
                return default
            current = current.get(part)
        return default if current is None else current


def test_cost_tracker_uses_configured_pricing_and_summary(monkeypatch, tmp_path) -> None:
    db = CostDatabase(tmp_path / "costs.db")
    db.record_draft(content_url="https://example.com/post-1", notion_page_id="page-1")

    monkeypatch.setattr("pipeline.cost_tracker._try_get_cost_db", lambda: db)

    tracker = CostTracker(
        FakeConfig(
            {
                "limits": {"daily_api_budget_usd": 10.0},
                "llm": {"pricing": {"openai": {"input_per_1m": 1.5, "output_per_1m": 2.0}}},
            }
        )
    )

    tracker.add_text_generation_cost("openai", input_tokens=100_000, output_tokens=50_000)
    tracker.add_dalle_cost(2)

    assert tracker.current_cost == 0.33
    assert tracker.provider_calls["openai"] == 1
    assert tracker.provider_tokens["openai"] == {"input": 100_000, "output": 50_000}

    summary = tracker.get_summary()
    assert "openai: 1 calls" in summary
    assert "DALL-E Calls: 2" in summary
    assert "Avg Cost/Post (30d): $0.33000 (1 posts)" in summary


def test_cost_tracker_sends_gemini_threshold_alerts_once(monkeypatch) -> None:
    alerts: list[tuple[str, str]] = []

    monkeypatch.setattr("pipeline.cost_tracker._try_get_cost_db", lambda: None)
    monkeypatch.setattr(
        "pipeline.cost_tracker._try_send_telegram",
        lambda message, level="INFO": alerts.append((level, message)),
    )

    tracker = CostTracker(FakeConfig({"limits": {"daily_api_budget_usd": 10.0}}))

    tracker.add_gemini_image_count(400)
    tracker.add_gemini_image_count(100)
    tracker.add_gemini_image_count(50)

    assert [level for level, _message in alerts] == ["WARNING", "CRITICAL"]
    assert tracker.gemini_image_count == 550


def test_cost_tracker_budget_exceeded_uses_persisted_totals_and_alerts(monkeypatch, tmp_path) -> None:
    db = CostDatabase(tmp_path / "costs.db")
    db.record_text_cost(provider="openai", usd=1.25)
    alerts: list[tuple[str, str]] = []

    monkeypatch.setattr("pipeline.cost_tracker._try_get_cost_db", lambda: db)
    monkeypatch.setattr(
        "pipeline.cost_tracker._try_send_telegram",
        lambda message, level="INFO": alerts.append((level, message)),
    )

    tracker = CostTracker(FakeConfig({"limits": {"daily_api_budget_usd": 1.0}}))

    assert tracker.is_budget_exceeded() is True
    assert alerts and alerts[0][0] == "CRITICAL"


def test_cost_tracker_can_use_gemini_image_prefers_persisted_daily_total(monkeypatch, tmp_path) -> None:
    db = CostDatabase(tmp_path / "costs.db")
    db.record_image_cost(provider="gemini", image_count=499, usd=0.0)

    monkeypatch.setattr("pipeline.cost_tracker._try_get_cost_db", lambda: db)

    tracker = CostTracker(FakeConfig({"limits": {"daily_api_budget_usd": 5.0}}))
    tracker.gemini_image_count = 10

    assert tracker.can_use_gemini_image() is True

    db.record_image_cost(provider="gemini", image_count=1, usd=0.0)
    assert tracker.can_use_gemini_image() is False
