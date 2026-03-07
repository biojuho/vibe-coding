from __future__ import annotations

from datetime import date

import execution.api_usage_tracker as aut


def _patch_db(monkeypatch, tmp_path):
    monkeypatch.setattr(aut, "DB_PATH", tmp_path / "api_usage.db")
    aut.init_db()


# ---------------------------------------------------------------------------
# init_db
# ---------------------------------------------------------------------------

def test_init_db_creates_table(monkeypatch, tmp_path):
    monkeypatch.setattr(aut, "DB_PATH", tmp_path / "api_usage.db")
    aut.init_db()

    import sqlite3
    conn = sqlite3.connect(str(tmp_path / "api_usage.db"))
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    assert "api_calls" in tables
    conn.close()


def test_init_db_idempotent(monkeypatch, tmp_path):
    monkeypatch.setattr(aut, "DB_PATH", tmp_path / "api_usage.db")
    aut.init_db()
    aut.init_db()  # 두 번 호출해도 오류 없어야 함


# ---------------------------------------------------------------------------
# log_api_call
# ---------------------------------------------------------------------------

def test_log_api_call_basic(monkeypatch, tmp_path):
    _patch_db(monkeypatch, tmp_path)
    aut.log_api_call(provider="anthropic", model="claude-sonnet-4", tokens_input=100, tokens_output=50)

    summary = aut.get_usage_summary(days=1)
    assert summary["total_calls"] == 1
    assert summary["total_tokens"] == 150


def test_log_api_call_auto_cost_calculation(monkeypatch, tmp_path):
    _patch_db(monkeypatch, tmp_path)
    # claude-sonnet-4: input=0.003/1K, output=0.015/1K
    aut.log_api_call(
        provider="anthropic",
        model="claude-sonnet-4",
        tokens_input=1000,
        tokens_output=1000,
    )
    summary = aut.get_usage_summary(days=1)
    # 1000/1000 * 0.003 + 1000/1000 * 0.015 = 0.018
    assert abs(summary["total_cost_usd"] - 0.018) < 1e-6


def test_log_api_call_explicit_cost_overrides_pricing(monkeypatch, tmp_path):
    _patch_db(monkeypatch, tmp_path)
    aut.log_api_call(
        provider="openai",
        model="gpt-4o",
        tokens_input=1000,
        tokens_output=1000,
        cost_usd=0.999,  # 명시적 비용
    )
    summary = aut.get_usage_summary(days=1)
    assert abs(summary["total_cost_usd"] - 0.999) < 1e-4


def test_log_api_call_unknown_model_no_auto_cost(monkeypatch, tmp_path):
    _patch_db(monkeypatch, tmp_path)
    aut.log_api_call(
        provider="mystery",
        model="unknown-model-xyz",
        tokens_input=500,
        tokens_output=500,
    )
    summary = aut.get_usage_summary(days=1)
    assert summary["total_cost_usd"] == 0.0


def test_log_multiple_calls(monkeypatch, tmp_path):
    _patch_db(monkeypatch, tmp_path)
    for i in range(5):
        aut.log_api_call(provider="github", endpoint=f"/repos/{i}")

    summary = aut.get_usage_summary(days=1)
    assert summary["total_calls"] == 5


# ---------------------------------------------------------------------------
# get_usage_summary
# ---------------------------------------------------------------------------

def test_usage_summary_empty_db(monkeypatch, tmp_path):
    _patch_db(monkeypatch, tmp_path)
    summary = aut.get_usage_summary(days=30)
    assert summary["total_calls"] == 0
    assert summary["total_tokens"] == 0
    assert summary["total_cost_usd"] == 0.0


def test_usage_summary_days_field(monkeypatch, tmp_path):
    _patch_db(monkeypatch, tmp_path)
    summary = aut.get_usage_summary(days=7)
    assert summary["days"] == 7


# ---------------------------------------------------------------------------
# get_daily_breakdown
# ---------------------------------------------------------------------------

def test_daily_breakdown_groups_by_day(monkeypatch, tmp_path):
    _patch_db(monkeypatch, tmp_path)
    aut.log_api_call(provider="openai", tokens_input=100, tokens_output=50)
    aut.log_api_call(provider="anthropic", tokens_input=200, tokens_output=100)

    breakdown = aut.get_daily_breakdown(days=1)
    # 같은 날 2건 → 합계
    total_calls = sum(r["calls"] for r in breakdown)
    assert total_calls == 2


def test_daily_breakdown_empty(monkeypatch, tmp_path):
    _patch_db(monkeypatch, tmp_path)
    result = aut.get_daily_breakdown(days=1)
    assert result == []


# ---------------------------------------------------------------------------
# get_provider_breakdown
# ---------------------------------------------------------------------------

def test_provider_breakdown(monkeypatch, tmp_path):
    _patch_db(monkeypatch, tmp_path)
    aut.log_api_call(provider="anthropic")
    aut.log_api_call(provider="anthropic")
    aut.log_api_call(provider="openai")

    breakdown = aut.get_provider_breakdown(days=1)
    providers = {r["provider"]: r["calls"] for r in breakdown}
    assert providers.get("anthropic") == 2
    assert providers.get("openai") == 1


def test_provider_breakdown_empty(monkeypatch, tmp_path):
    _patch_db(monkeypatch, tmp_path)
    result = aut.get_provider_breakdown(days=1)
    assert result == []


def test_get_bridge_activity_for_date(monkeypatch, tmp_path):
    _patch_db(monkeypatch, tmp_path)
    aut.log_api_call(
        provider="deepseek",
        model="deepseek-chat",
        bridge_mode="shadow",
        reason_codes=["mixed_language", "mojibake"],
        repair_count=1,
        fallback_used=True,
        language_score=0.72,
        provider_used="google",
    )
    aut.log_api_call(
        provider="google",
        model="gemini-2.5-flash",
        bridge_mode="shadow",
        reason_codes=["mixed_language"],
        repair_count=0,
        fallback_used=False,
        language_score=0.95,
        provider_used="google",
    )

    summary = aut.get_bridge_activity_for_date(date.today())

    assert summary["total_calls"] == 2
    assert summary["shadow_calls"] == 2
    assert summary["repair_calls"] == 1
    assert summary["fallback_calls"] == 1
    assert summary["reason_codes"]["mixed_language"] == 2
    assert summary["reason_codes"]["mojibake"] == 1
    assert summary["by_provider"]["google"] == 2


def test_get_bridge_daily_and_reason_breakdown(monkeypatch, tmp_path):
    _patch_db(monkeypatch, tmp_path)
    aut.log_api_call(
        provider="deepseek",
        bridge_mode="shadow",
        reason_codes=["mixed_language"],
        repair_count=1,
        fallback_used=False,
        language_score=0.7,
    )
    aut.log_api_call(
        provider="google",
        bridge_mode="enforce",
        reason_codes=["mixed_language", "mojibake"],
        repair_count=0,
        fallback_used=True,
        language_score=0.95,
    )

    daily = aut.get_bridge_daily_breakdown(days=1)
    reasons = aut.get_bridge_reason_breakdown(days=1)

    assert len(daily) == 1
    assert daily[0]["calls"] == 2
    assert daily[0]["shadow_calls"] == 1
    assert daily[0]["enforce_calls"] == 1
    assert daily[0]["repair_calls"] == 1
    assert daily[0]["fallback_calls"] == 1
    assert reasons[0]["reason_code"] == "mixed_language"
    assert reasons[0]["count"] == 2


def test_get_bridge_provider_breakdown(monkeypatch, tmp_path):
    _patch_db(monkeypatch, tmp_path)
    aut.log_api_call(
        provider="deepseek",
        bridge_mode="shadow",
        reason_codes=["mixed_language"],
        repair_count=0,
        fallback_used=False,
        language_score=0.7,
        provider_used="deepseek",
    )
    aut.log_api_call(
        provider="deepseek",
        bridge_mode="enforce",
        reason_codes=[],
        repair_count=1,
        fallback_used=True,
        language_score=0.93,
        provider_used="deepseek",
    )
    aut.log_api_call(
        provider="google",
        bridge_mode="shadow",
        reason_codes=["mojibake"],
        repair_count=1,
        fallback_used=False,
        language_score=0.88,
        provider_used="google",
    )

    breakdown = aut.get_bridge_provider_breakdown(days=1)
    by_provider = {item["provider"]: item for item in breakdown}

    assert by_provider["deepseek"]["bridge_calls"] == 2
    assert by_provider["deepseek"]["bridge_failure_rate"] == 50.0
    assert by_provider["deepseek"]["repair_success_rate"] == 100.0
    assert by_provider["deepseek"]["fallback_calls"] == 1
    assert by_provider["google"]["repair_success_rate"] == 0.0


# ---------------------------------------------------------------------------
# check_api_keys
# ---------------------------------------------------------------------------

def test_check_api_keys_all_missing(monkeypatch):
    # 모든 환경변수 제거
    for env_name in aut.API_KEYS.values():
        monkeypatch.delenv(env_name, raising=False)

    result = aut.check_api_keys()
    assert all(v is False for v in result.values())


def test_check_api_keys_detects_set_key(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key-12345")
    result = aut.check_api_keys()
    assert result["anthropic"] is True


def test_check_api_keys_short_value_is_false(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "abc")  # 5자 이하
    result = aut.check_api_keys()
    assert result["openai"] is False


def test_check_api_keys_returns_all_providers(monkeypatch):
    for env_name in aut.API_KEYS.values():
        monkeypatch.delenv(env_name, raising=False)
    result = aut.check_api_keys()
    assert set(result.keys()) == set(aut.API_KEYS.keys())


# ---------------------------------------------------------------------------
# _ensure_columns ALTER TABLE path (line 106)
# ---------------------------------------------------------------------------


def test_ensure_columns_alter_table(monkeypatch, tmp_path):
    """When a column doesn't exist, ALTER TABLE is executed."""
    import sqlite3

    db_path = tmp_path / "alter_test.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE test_table (id INTEGER PRIMARY KEY, name TEXT)")
    conn.commit()

    # Call _ensure_columns to add a new column
    aut._ensure_columns(conn, "test_table", {"new_col": "TEXT DEFAULT 'hello'"})
    conn.commit()

    # Verify column was added
    cols = {row["name"] for row in conn.execute("PRAGMA table_info(test_table)").fetchall()}
    assert "new_col" in cols
    conn.close()


# ---------------------------------------------------------------------------
# Bridge analytics: shadow/enforce, repair, fallback, reason_codes, language_score
# (lines 248-249, 268-269, 322-323, 369-370)
# ---------------------------------------------------------------------------


def test_bridge_analytics_shadow_and_enforce_modes(monkeypatch, tmp_path):
    """Log calls with shadow and enforce modes, then verify daily breakdown."""
    _patch_db(monkeypatch, tmp_path)

    aut.log_api_call(
        provider="deepseek",
        model="deepseek-chat",
        bridge_mode="shadow",
        reason_codes=["mixed_language"],
        repair_count=1,
        fallback_used=False,
        language_score=0.8,
        provider_used="deepseek",
    )
    aut.log_api_call(
        provider="google",
        model="gemini-2.5-flash",
        bridge_mode="enforce",
        reason_codes=["mojibake"],
        repair_count=0,
        fallback_used=True,
        language_score=0.9,
        provider_used="google",
    )

    daily = aut.get_bridge_daily_breakdown(days=1)
    assert len(daily) == 1
    assert daily[0]["shadow_calls"] == 1
    assert daily[0]["enforce_calls"] == 1
    assert daily[0]["repair_calls"] == 1
    assert daily[0]["fallback_calls"] == 1

    reasons = aut.get_bridge_reason_breakdown(days=1)
    reason_map = {r["reason_code"]: r["count"] for r in reasons}
    assert reason_map["mixed_language"] == 1
    assert reason_map["mojibake"] == 1

    providers = aut.get_bridge_provider_breakdown(days=1)
    by_prov = {p["provider"]: p for p in providers}
    assert by_prov["deepseek"]["bridge_calls"] == 1
    assert by_prov["google"]["fallback_calls"] == 1


def test_bridge_analytics_reason_codes_parsing(monkeypatch, tmp_path):
    """Multiple reason_codes in a single call are each counted."""
    _patch_db(monkeypatch, tmp_path)

    aut.log_api_call(
        provider="deepseek",
        bridge_mode="shadow",
        reason_codes=["mixed_language", "mojibake", "grammar"],
        repair_count=0,
        fallback_used=False,
        language_score=0.7,
    )

    reasons = aut.get_bridge_reason_breakdown(days=1)
    reason_map = {r["reason_code"]: r["count"] for r in reasons}
    assert reason_map["mixed_language"] == 1
    assert reason_map["mojibake"] == 1
    assert reason_map["grammar"] == 1


def test_bridge_analytics_language_score_averaging(monkeypatch, tmp_path):
    """Language scores are averaged across calls."""
    _patch_db(monkeypatch, tmp_path)

    aut.log_api_call(
        provider="deepseek",
        bridge_mode="shadow",
        reason_codes=[],
        repair_count=0,
        fallback_used=False,
        language_score=0.6,
        provider_used="deepseek",
    )
    aut.log_api_call(
        provider="deepseek",
        bridge_mode="shadow",
        reason_codes=[],
        repair_count=0,
        fallback_used=False,
        language_score=0.8,
        provider_used="deepseek",
    )

    providers = aut.get_bridge_provider_breakdown(days=1)
    ds = next(p for p in providers if p["provider"] == "deepseek")
    assert ds["average_language_score"] is not None
    assert abs(ds["average_language_score"] - 0.7) < 0.01


# ---------------------------------------------------------------------------
# get_blind_to_x_summary (lines 406-424)
# ---------------------------------------------------------------------------


def test_get_blind_to_x_summary_empty(monkeypatch, tmp_path):
    """No blind-to-x calls -> empty summary."""
    _patch_db(monkeypatch, tmp_path)

    result = aut.get_blind_to_x_summary(days=30)
    assert result["total_calls"] == 0
    assert result["total_cost_usd"] == 0.0
    assert result["providers"] == []


def test_get_blind_to_x_summary_with_data(monkeypatch, tmp_path):
    """blind-to-x calls are filtered by caller_script."""
    _patch_db(monkeypatch, tmp_path)

    # blind-to-x call
    aut.log_api_call(
        provider="google",
        model="gemini-2.5-flash",
        tokens_input=500,
        tokens_output=200,
        cost_usd=0.001,
        caller_script="blind-to-x/pipeline",
    )
    # Non blind-to-x call (should be excluded)
    aut.log_api_call(
        provider="openai",
        model="gpt-4o-mini",
        tokens_input=100,
        tokens_output=50,
        cost_usd=0.01,
        caller_script="shorts_daily_runner",
    )

    result = aut.get_blind_to_x_summary(days=30)
    assert result["total_calls"] == 1
    assert abs(result["total_cost_usd"] - 0.001) < 1e-6
    assert len(result["providers"]) == 1
    assert result["providers"][0]["provider"] == "google"


# ---------------------------------------------------------------------------
# get_bridge_activity_for_date — enforce mode, reason codes, repair, fallback
# ---------------------------------------------------------------------------


def test_bridge_activity_enforce_and_repair(monkeypatch, tmp_path):
    """Enforce mode, repair count, fallback, reason codes and language scores."""
    _patch_db(monkeypatch, tmp_path)

    aut.log_api_call(
        provider="deepseek",
        bridge_mode="enforce",
        reason_codes=["low_hangul_ratio", "mixed_language"],
        repair_count=2,
        fallback_used=True,
        language_score=0.4,
        provider_used="google",
    )
    aut.log_api_call(
        provider="openai",
        bridge_mode="enforce",
        reason_codes=[],
        repair_count=0,
        fallback_used=False,
        language_score=0.9,
        provider_used="openai",
    )

    result = aut.get_bridge_activity_for_date(date.today())
    assert result["total_calls"] == 2
    assert result["enforce_calls"] == 2
    assert result["shadow_calls"] == 0
    assert result["repair_calls"] == 1
    assert result["fallback_calls"] == 1
    assert result["by_provider"]["google"] == 1
    assert result["by_provider"]["openai"] == 1
    assert result["reason_codes"]["low_hangul_ratio"] == 1
    assert result["reason_codes"]["mixed_language"] == 1
    assert result["average_language_score"] is not None
    assert abs(result["average_language_score"] - 0.65) < 0.01


# ---------------------------------------------------------------------------
# JSONDecodeError handling in reason_codes parsing (lines 268-269, 322-323, 369-370)
# ---------------------------------------------------------------------------

def test_bridge_activity_malformed_reason_codes(monkeypatch, tmp_path):
    """Malformed reason_codes JSON is handled gracefully."""
    _patch_db(monkeypatch, tmp_path)
    import sqlite3
    conn = sqlite3.connect(str(tmp_path / "api_usage.db"))
    conn.execute(
        """INSERT INTO api_calls
           (provider, model, caller_script, tokens_input, tokens_output,
            bridge_mode, repair_count, fallback_used, language_score, provider_used, reason_codes)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        ("google", "gemini", "test.py", 10, 10,
         "enforce", 0, 0, 0.8, "google", "NOT_VALID_JSON"),
    )
    conn.commit()
    conn.close()

    result = aut.get_bridge_activity_for_date(date.today())
    assert result["total_calls"] == 1
    # Malformed JSON → empty reason_codes, no crash
    assert result["reason_codes"] == {}


def test_bridge_reason_code_breakdown_malformed(monkeypatch, tmp_path):
    """get_bridge_reason_code_breakdown handles malformed reason_codes."""
    _patch_db(monkeypatch, tmp_path)
    import sqlite3
    conn = sqlite3.connect(str(tmp_path / "api_usage.db"))
    conn.execute(
        """INSERT INTO api_calls
           (provider, model, caller_script, tokens_input, tokens_output,
            bridge_mode, repair_count, fallback_used, language_score, provider_used, reason_codes)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        ("google", "gemini", "test.py", 10, 10,
         "enforce", 0, 0, 0.8, "google", "{broken"),
    )
    conn.commit()
    conn.close()

    result = aut.get_bridge_reason_breakdown(days=30)
    assert result == []


def test_bridge_provider_breakdown_malformed_reason_codes(monkeypatch, tmp_path):
    """get_bridge_provider_breakdown handles malformed reason_codes."""
    _patch_db(monkeypatch, tmp_path)
    import sqlite3
    conn = sqlite3.connect(str(tmp_path / "api_usage.db"))
    conn.execute(
        """INSERT INTO api_calls
           (provider, model, caller_script, tokens_input, tokens_output,
            bridge_mode, repair_count, fallback_used, language_score, provider_used, reason_codes)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        ("openai", "gpt-4o", "test.py", 10, 10,
         "enforce", 0, 0, 0.7, "openai", "<<<invalid>>>"),
    )
    conn.commit()
    conn.close()

    result = aut.get_bridge_provider_breakdown(days=30)
    assert len(result) == 1
    assert result[0]["provider"] == "openai"
    assert result[0]["issue_calls"] == 0  # malformed → empty reason_codes → no issue
