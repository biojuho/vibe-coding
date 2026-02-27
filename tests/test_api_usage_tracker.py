from __future__ import annotations


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
