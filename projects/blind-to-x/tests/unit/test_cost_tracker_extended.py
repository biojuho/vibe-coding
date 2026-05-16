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


def test_cost_tracker_records_anthropic_cache_tokens(monkeypatch, tmp_path) -> None:
    db = CostDatabase(tmp_path / "costs.db")
    monkeypatch.setattr("pipeline.cost_tracker._try_get_cost_db", lambda: db)

    tracker = CostTracker(
        FakeConfig(
            {
                "limits": {"daily_api_budget_usd": 10.0},
                "llm": {"pricing": {"anthropic": {"input_per_1m": 3.0, "output_per_1m": 15.0}}},
            }
        )
    )

    tracker.add_text_generation_cost(
        "anthropic",
        input_tokens=1_000,
        output_tokens=100,
        cache_creation_tokens=1_000,
        cache_read_tokens=1_000,
        cache_creation_multiplier=2.0,
    )

    assert round(tracker.current_cost, 4) == 0.0108
    with db._conn() as conn:
        row = conn.execute(
            "SELECT cache_creation_tokens, cache_read_tokens, usd_estimated FROM daily_text_costs"
        ).fetchone()

    assert row["cache_creation_tokens"] == 1_000
    assert row["cache_read_tokens"] == 1_000
    assert round(row["usd_estimated"], 4) == 0.0108


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


def test_add_text_generation_cost_invokes_forwarder(monkeypatch, tmp_path) -> None:
    """`add_text_generation_cost` must call the workspace forwarder every time;
    the env gate inside the forwarder decides whether a write actually happens."""
    monkeypatch.delenv("BTX_USAGE_FORWARD", raising=False)
    db = CostDatabase(tmp_path / "costs.db")
    monkeypatch.setattr("pipeline.cost_tracker._try_get_cost_db", lambda: db)

    seen: list[dict] = []
    monkeypatch.setattr(
        "pipeline.cost_tracker._maybe_forward_to_workspace_usage",
        lambda **kwargs: seen.append(kwargs),
    )

    tracker = CostTracker(FakeConfig({"limits": {"daily_api_budget_usd": 5.0}}))
    tracker.add_text_generation_cost("anthropic", input_tokens=10, output_tokens=5)

    assert len(seen) == 1
    assert seen[0]["provider"] == "anthropic"
    assert seen[0]["input_tokens"] == 10
    assert seen[0]["output_tokens"] == 5


def test_workspace_usage_forwarder_env_gate(monkeypatch, tmp_path) -> None:
    """Real forwarder writes to workspace.db only when BTX_USAGE_FORWARD=1."""
    import types

    from pipeline import cost_tracker as ct

    # Patch the workspace import surface so we can detect calls deterministically.
    # Use SimpleNamespace so log_api_call stays a plain function (not a bound method
    # that injects `self` as the first positional argument).
    calls: list[dict] = []

    def fake_log_api_call(**kwargs):  # noqa: ANN003
        calls.append(kwargs)

    fake_module = types.SimpleNamespace(log_api_call=fake_log_api_call)
    monkeypatch.setitem(sys.modules, "execution.api_usage_tracker", fake_module)

    # Case 1: disabled
    monkeypatch.delenv("BTX_USAGE_FORWARD", raising=False)
    ct._maybe_forward_to_workspace_usage(provider="anthropic", input_tokens=1, output_tokens=2, cost_usd=0.001)
    assert calls == []

    # Case 2: enabled
    monkeypatch.setenv("BTX_USAGE_FORWARD", "1")
    ct._maybe_forward_to_workspace_usage(
        provider="anthropic",
        input_tokens=3,
        output_tokens=4,
        cost_usd=0.002,
        model="claude-haiku-4-5",
    )
    assert len(calls) == 1
    assert calls[0]["provider"] == "anthropic"
    assert calls[0]["tokens_input"] == 3
    assert calls[0]["tokens_output"] == 4
    assert calls[0]["model"] == "claude-haiku-4-5"
    assert calls[0]["endpoint"] == "blind-to-x.cost_tracker"
    assert calls[0]["caller_script"].endswith("cost_tracker.py")


def test_workspace_usage_forwarder_swallows_import_errors(monkeypatch) -> None:
    """Forwarder must never raise even if workspace import fails."""
    import types

    from pipeline import cost_tracker as ct

    monkeypatch.setenv("BTX_USAGE_FORWARD", "1")

    def boom(**kwargs):  # noqa: ANN003
        raise RuntimeError("simulated workspace import failure")

    broken_module = types.SimpleNamespace(log_api_call=boom)
    monkeypatch.setitem(sys.modules, "execution.api_usage_tracker", broken_module)

    ct._maybe_forward_to_workspace_usage(provider="anthropic", input_tokens=1, output_tokens=2, cost_usd=0.001)
    # No exception raised — that's the contract.
