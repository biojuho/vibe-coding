"""
test_harness_guard.py — Unit tests for pipeline.harness_guard
=============================================================
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# blind-to-x 프로젝트 루트를 sys.path에 추가
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from pipeline.harness_guard import (
    PreflightError,
    create_sandbox_context,
    is_harness_enabled,
    run_preflight,
)


# ── is_harness_enabled ──────────────────────────────────────────────────────


class TestIsHarnessEnabled:
    def test_disabled_by_default(self, monkeypatch):
        monkeypatch.delenv("HARNESS_ENABLED", raising=False)
        assert is_harness_enabled() is False

    def test_enabled_with_1(self, monkeypatch):
        monkeypatch.setenv("HARNESS_ENABLED", "1")
        assert is_harness_enabled() is True

    def test_disabled_with_0(self, monkeypatch):
        monkeypatch.setenv("HARNESS_ENABLED", "0")
        assert is_harness_enabled() is False

    def test_disabled_with_empty(self, monkeypatch):
        monkeypatch.setenv("HARNESS_ENABLED", "")
        assert is_harness_enabled() is False

    def test_disabled_with_true_string(self, monkeypatch):
        monkeypatch.setenv("HARNESS_ENABLED", "true")
        assert is_harness_enabled() is False

    def test_enabled_with_whitespace(self, monkeypatch):
        monkeypatch.setenv("HARNESS_ENABLED", " 1 ")
        assert is_harness_enabled() is True


# ── run_preflight ────────────────────────────────────────────────────────────


class TestRunPreflight:
    def test_skipped_when_disabled(self, monkeypatch):
        monkeypatch.delenv("HARNESS_ENABLED", raising=False)
        result = run_preflight()
        assert result["passed"] is True
        assert result["skipped"] is True
        assert result["issues"] == []

    def test_passes_when_no_issues(self, monkeypatch):
        monkeypatch.setenv("HARNESS_ENABLED", "1")

        mock_instance = MagicMock()
        mock_instance.run_preflight.return_value = {"passed": True, "issues": []}

        mock_module = MagicMock()
        mock_module.SecurityChecklist.return_value = mock_instance

        with patch.dict(sys.modules, {"harness_security_checklist": mock_module}):
            result = run_preflight()

        assert result["passed"] is True
        assert result["issues"] == []
        assert result["skipped"] is False

    def test_raises_on_critical_issues(self, monkeypatch):
        monkeypatch.setenv("HARNESS_ENABLED", "1")

        mock_checklist_cls = MagicMock()
        mock_instance = MagicMock()
        mock_instance.run_preflight.return_value = {
            "passed": False,
            "issues": [{"severity": "critical", "message": "Missing .env protection"}],
        }
        mock_checklist_cls.return_value = mock_instance

        mock_module = MagicMock()
        mock_module.SecurityChecklist = mock_checklist_cls

        with patch.dict(sys.modules, {"harness_security_checklist": mock_module}):
            with pytest.raises(PreflightError, match="critical"):
                run_preflight()

    def test_warns_on_non_critical_issues(self, monkeypatch):
        monkeypatch.setenv("HARNESS_ENABLED", "1")

        mock_checklist_cls = MagicMock()
        mock_instance = MagicMock()
        mock_instance.run_preflight.return_value = {
            "passed": True,
            "issues": [{"severity": "warning", "message": "Deprecated pattern found"}],
        }
        mock_checklist_cls.return_value = mock_instance

        mock_module = MagicMock()
        mock_module.SecurityChecklist = mock_checklist_cls

        with patch.dict(sys.modules, {"harness_security_checklist": mock_module}):
            result = run_preflight()

        assert result["passed"] is True
        assert len(result["issues"]) == 1
        assert result["skipped"] is False

    def test_handles_import_error_gracefully(self, monkeypatch):
        monkeypatch.setenv("HARNESS_ENABLED", "1")

        # Ensure the module is not importable
        with patch.dict(sys.modules, {"harness_security_checklist": None}):
            result = run_preflight()

        assert result["passed"] is True
        assert result["skipped"] is True


# ── create_sandbox_context ───────────────────────────────────────────────────


class TestCreateSandboxContext:
    def test_returns_none_when_disabled(self, monkeypatch):
        monkeypatch.delenv("HARNESS_ENABLED", raising=False)
        assert create_sandbox_context() is None

    def test_returns_none_on_import_error(self, monkeypatch):
        monkeypatch.setenv("HARNESS_ENABLED", "1")

        with patch.dict(sys.modules, {"harness_sandbox": None}):
            result = create_sandbox_context()

        assert result is None

    def test_creates_sandbox_with_profile(self, monkeypatch):
        monkeypatch.setenv("HARNESS_ENABLED", "1")

        mock_config = MagicMock()
        mock_instance = MagicMock()
        mock_instance.id = "sandbox-123"

        mock_manager_cls = MagicMock()
        mock_manager = MagicMock()
        mock_manager.get_predefined_profiles.return_value = {"blind-to-x": mock_config}
        mock_manager.create.return_value = mock_instance
        mock_manager_cls.return_value = mock_manager

        mock_module = MagicMock()
        mock_module.SandboxManager = mock_manager_cls
        mock_module.SandboxConfig = MagicMock()

        with patch.dict(sys.modules, {"harness_sandbox": mock_module}):
            result = create_sandbox_context("blind-to-x")

        assert result == mock_instance
        mock_manager.create.assert_called_once_with(mock_config)

    def test_uses_default_config_for_unknown_profile(self, monkeypatch):
        monkeypatch.setenv("HARNESS_ENABLED", "1")

        mock_instance = MagicMock()
        mock_instance.id = "sandbox-456"

        mock_manager_cls = MagicMock()
        mock_manager = MagicMock()
        mock_manager.get_predefined_profiles.return_value = {}
        mock_manager.create.return_value = mock_instance
        mock_manager_cls.return_value = mock_manager

        mock_sandbox_config_cls = MagicMock()

        mock_module = MagicMock()
        mock_module.SandboxManager = mock_manager_cls
        mock_module.SandboxConfig = mock_sandbox_config_cls

        with patch.dict(sys.modules, {"harness_sandbox": mock_module}):
            result = create_sandbox_context("unknown-profile")

        assert result == mock_instance
        mock_sandbox_config_cls.assert_called_once()
