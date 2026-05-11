from __future__ import annotations

import builtins
from datetime import date

import execution.daily_report as dr


def test_generate_report_includes_llm_bridge(monkeypatch):
    target_date = date(2026, 3, 4)
    monkeypatch.setattr(dr, "collect_git_activity", lambda _date: [{"repo": "repo", "hash": "abc", "message": "feat"}])
    monkeypatch.setattr(dr, "collect_file_changes", lambda _date: {"files_modified": 5, "date": _date.isoformat()})
    monkeypatch.setattr(
        dr,
        "collect_scheduler_logs",
        lambda _date: [{"task_name": "job", "started_at": _date.isoformat(), "exit_code": 0}],
    )
    monkeypatch.setattr(
        dr,
        "collect_llm_bridge_activity",
        lambda _date: {
            "total_calls": 3,
            "shadow_calls": 2,
            "enforce_calls": 1,
            "repair_calls": 1,
            "fallback_calls": 1,
            "average_language_score": 0.91,
            "reason_codes": {"mixed_language": 2},
            "top_reason_codes": [{"reason_code": "mixed_language", "count": 2}],
            "by_provider": {"deepseek": 2, "google": 1},
        },
    )
    monkeypatch.setattr(
        dr,
        "collect_api_alerts",
        lambda: {
            "alert_count": 1,
            "alerts": [{"type": "fallback_rate", "detail": "openai fallback rate high"}],
            "expected_providers": ["openai"],
            "window_days": 7,
        },
    )
    monkeypatch.setattr(
        dr, "_save_report", lambda report_date, report_payload: dr.REPORT_DIR / f"daily_{report_date.isoformat()}.json"
    )

    report = dr.generate_report(target_date)

    assert report["summary"]["llm_bridge_calls"] == 3
    assert report["summary"]["llm_bridge_repairs"] == 1
    assert report["summary"]["llm_bridge_fallbacks"] == 1
    assert report["summary"]["api_alerts"] == 1
    assert report["llm_bridge"]["top_reason_codes"][0]["reason_code"] == "mixed_language"
    assert report["api_alerts"]["alerts"][0]["type"] == "fallback_rate"


def test_collect_llm_bridge_activity_returns_empty_shape_when_import_fails(monkeypatch):
    original_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "execution.api_usage_tracker":
            raise ModuleNotFoundError("boom")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    result = dr.collect_llm_bridge_activity(date(2026, 3, 4))

    assert result["total_calls"] == 0
    assert result["top_reason_codes"] == []


def test_collect_api_alerts_uses_configured_expected_providers(monkeypatch):
    seen = {}

    def fake_detect_alerts(**kwargs):
        seen.update(kwargs)
        return [{"type": "dead_provider", "provider": "anthropic", "detail": "anthropic missing"}]

    original_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "execution.api_usage_tracker":
            module = type("FakeApiUsageTracker", (), {"detect_alerts": fake_detect_alerts})
            return module
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    monkeypatch.setenv("DAILY_REPORT_API_ALERT_EXPECTED_PROVIDERS", "openai, anthropic")
    monkeypatch.setenv("DAILY_REPORT_API_ALERT_DAYS", "3")

    result = dr.collect_api_alerts()

    assert seen == {"days_window": 3, "expected_providers": ["openai", "anthropic"]}
    assert result["alert_count"] == 1
    assert result["expected_providers"] == ["openai", "anthropic"]
    assert result["window_days"] == 3


def test_collect_api_alerts_returns_empty_shape_when_import_fails(monkeypatch):
    original_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "execution.api_usage_tracker":
            raise ModuleNotFoundError("boom")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    result = dr.collect_api_alerts()

    assert result["alert_count"] == 0
    assert result["alerts"] == []
    assert "error" in result
