"""Unit tests for ConfigManager.validate() — critical config gate."""

from __future__ import annotations

import pytest


def _make_config(overrides: dict | None = None):  # returns ConfigManager
    from config import ConfigManager

    cfg = ConfigManager.__new__(ConfigManager)
    cfg.config_path = "config.yaml"
    # Minimal valid config that passes all _REQUIRED_KEYS and _NOTION_ENV_KEYS checks
    cfg.config = {
        "request": {"timeout_seconds": 30},
        "scrape_quality": {"min_content_length": 100, "min_korean_ratio": 0.3},
        "ranking": {
            "weights": {
                "scrape_quality": 0.4,
                "publishability": 0.4,
                "performance": 0.2,
            }
        },
        "limits": {"daily_api_budget_usd": 5.0},
        "notion": {"api_key": "test-api-key", "database_id": "test-db-id"},
    }
    if overrides:
        # Deep-merge overrides into cfg.config
        for dot_key, val in overrides.items():
            keys = dot_key.split(".")
            node = cfg.config
            for k in keys[:-1]:
                node = node.setdefault(k, {})
            node[keys[-1]] = val
    return cfg


class TestConfigValidateRequiredKeys:
    def test_valid_config_returns_empty_warnings(self):
        cfg = _make_config()
        warnings = cfg.validate()
        assert warnings == []

    def test_missing_required_key_raises(self):
        from config import ConfigValidationError

        cfg = _make_config()
        # Remove a required nested key by clearing request
        cfg.config["request"] = {}
        with pytest.raises(ConfigValidationError, match="Missing required config key"):
            cfg.validate()

    def test_all_required_keys_missing_raises_once(self):
        from config import ConfigValidationError

        cfg = _make_config()
        cfg.config = {}  # nuke all keys
        with pytest.raises(ConfigValidationError):
            cfg.validate()


class TestConfigValidateNotionKeys:
    def test_unresolved_env_placeholder_warns(self, monkeypatch):
        monkeypatch.delenv("NOTION_API_KEY", raising=False)
        cfg = _make_config({"notion.api_key": "${NOTION_API_KEY}"})
        warnings = cfg.validate()
        assert any("NOTION_API_KEY" in w for w in warnings)

    def test_empty_notion_key_with_no_env_warns(self, monkeypatch):
        monkeypatch.delenv("NOTION_API_KEY", raising=False)
        monkeypatch.delenv("NOTION_DATABASE_ID", raising=False)
        cfg = _make_config({"notion.api_key": "", "notion.database_id": ""})
        warnings = cfg.validate()
        # Both keys are empty → expect 2 warnings
        assert sum("Notion 업로드 불가" in w for w in warnings) == 2

    def test_env_var_set_suppresses_notion_warning(self, monkeypatch):
        monkeypatch.setenv("NOTION_API_KEY", "real-key")
        monkeypatch.setenv("NOTION_DATABASE_ID", "real-db-id")
        cfg = _make_config({"notion.api_key": "", "notion.database_id": ""})
        warnings = cfg.validate()
        assert not any("NOTION_API_KEY" in w for w in warnings)
        assert not any("NOTION_DATABASE_ID" in w for w in warnings)


class TestConfigValidateBudget:
    def test_zero_budget_warns(self):
        cfg = _make_config({"limits.daily_api_budget_usd": 0})
        warnings = cfg.validate()
        assert any("≤ 0" in w for w in warnings)

    def test_negative_budget_warns(self):
        cfg = _make_config({"limits.daily_api_budget_usd": -1.0})
        warnings = cfg.validate()
        assert any("≤ 0" in w for w in warnings)

    def test_positive_budget_no_warning(self):
        cfg = _make_config({"limits.daily_api_budget_usd": 10.0})
        warnings = cfg.validate()
        assert not any("budget" in w.lower() for w in warnings)


class TestConfigValidateWeights:
    def test_weights_not_summing_to_1_warns(self):
        cfg = _make_config(
            {
                "ranking.weights.scrape_quality": 0.5,
                "ranking.weights.publishability": 0.5,
                "ranking.weights.performance": 0.5,
            }
        )
        warnings = cfg.validate()
        assert any("1.0" in w or "합계" in w for w in warnings)

    def test_weights_summing_to_1_no_warning(self):
        cfg = _make_config(
            {
                "ranking.weights.scrape_quality": 0.34,
                "ranking.weights.publishability": 0.33,
                "ranking.weights.performance": 0.33,
            }
        )
        warnings = cfg.validate()
        assert not any("합계" in w for w in warnings)
