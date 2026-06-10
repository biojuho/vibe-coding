from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.notion_retry_diagnostics import notion_retry_operator_action  # noqa: E402
from scripts.notion_doctor import (  # noqa: E402
    _build_doctor_payload,
    _credential_diagnostic_lines,
    _provider_key_diagnostics,
    _print_text_report,
)


class _FakeConfig:
    def __init__(self, values: dict[str, str]):
        self._values = values

    def get(self, key: str, default=None):
        return self._values.get(key, default)


class _FakeNotion:
    api_key = "ntn_test_secret_value"
    raw_database_id = "1234567890abcdef1234567890abcdef"
    database_id = "12345678-90ab-cdef-1234-567890abcdef"
    collection_kind = "database"
    props = {"title": "콘텐츠", "url": "원본 URL"}
    last_error_code = "ERROR_NOTION_SCHEMA_FETCH_FAILED"
    last_error_message = "not shared with integration"


def _retry_report() -> dict:
    return {
        "attempt_count": 3,
        "retry_count": 2,
        "max_retries": 3,
        "final_state": "failed",
        "final_error": "Service Overload",
        "last_status": 529,
        "retryable": True,
        "attempts": [
            {
                "attempt": 1,
                "status": 529,
                "retry_after_seconds": 3,
                "retryable": True,
                "will_retry": True,
                "delay_seconds": 3,
                "error_type": "HTTPStatusError",
                "error": "Service Overload",
            },
            {
                "attempt": 2,
                "status": 529,
                "retry_after_seconds": None,
                "retryable": True,
                "will_retry": True,
                "delay_seconds": 2,
                "error_type": "HTTPStatusError",
                "error": "Service Overload",
            },
            {
                "attempt": 3,
                "status": 529,
                "retry_after_seconds": None,
                "retryable": True,
                "will_retry": False,
                "delay_seconds": None,
                "error_type": "HTTPStatusError",
                "error": "Service Overload",
            },
        ],
    }


def test_notion_retry_operator_action_for_permission_failure():
    action = notion_retry_operator_action(
        {
            "last_status": 403,
            "retryable": False,
            "attempts": [{"status": 403, "will_retry": False}],
        }
    )

    assert action == "Check the Notion token, database ID, and DB/data-source sharing before rerun."


def test_notion_retry_operator_action_preserves_zero_retry_after():
    action = notion_retry_operator_action(
        {
            "last_status": 529,
            "retryable": True,
            "attempts": [{"retry_after_seconds": 0, "delay_seconds": None}],
        },
        retry_label="the Notion duplicate check",
    )

    assert action == "Retry the Notion duplicate check after at least 0s, then reduce request rate if it repeats."


def test_credential_diagnostics_explain_missing_notion_env_and_placeholders(monkeypatch):
    monkeypatch.delenv("NOTION_API_KEY", raising=False)
    monkeypatch.delenv("NOTION_DATABASE_ID", raising=False)
    config = _FakeConfig(
        {
            "notion.api_key": "${NOTION_API_KEY}",
            "notion.database_id": "${NOTION_DATABASE_ID}",
        }
    )

    lines = _credential_diagnostic_lines(config, "config.yaml")

    assert lines == [
        "config_path: config.yaml",
        "NOTION_API_KEY env: missing",
        "notion.api_key config: placeholder",
        "NOTION_DATABASE_ID env: missing",
        "notion.database_id config: placeholder",
        "missing_credentials: NOTION_API_KEY, NOTION_DATABASE_ID",
        (
            "fix: set missing values in project .env, the BLIND_TO_X_ENV_PATH file, "
            "or config.yaml; then rerun notion_doctor."
        ),
    ]


def test_credential_diagnostics_distinguish_present_env_from_share_problem(monkeypatch):
    monkeypatch.setenv("NOTION_API_KEY", "ntn_test_token")
    monkeypatch.setenv("NOTION_DATABASE_ID", "1234567890abcdef1234567890abcdef")
    config = _FakeConfig(
        {
            "notion.api_key": "${NOTION_API_KEY}",
            "notion.database_id": "${NOTION_DATABASE_ID}",
        }
    )

    lines = _credential_diagnostic_lines(config, "config.yaml")

    assert "missing_credentials:" not in "\n".join(lines)
    assert lines[-2:] == [
        "credentials_present: true",
        "fix: if schema fetch still fails, share the target DB/data source with the integration.",
    ]


def test_provider_key_diagnostics_warn_for_enabled_missing_provider_keys(monkeypatch):
    for env_name in (
        "ANTHROPIC_API_KEY",
        "GEMINI_API_KEY",
        "GOOGLE_API_KEY",
        "DEEPSEEK_API_KEY",
        "MOONSHOT_API_KEY",
        "ZHIPUAI_API_KEY",
        "XAI_API_KEY",
        "GROK_API_KEY",
        "OPENAI_API_KEY",
    ):
        monkeypatch.delenv(env_name, raising=False)
    config = _FakeConfig(
        {
            "anthropic.enabled": True,
            "anthropic.api_key": "${ANTHROPIC_API_KEY}",
            "gemini.enabled": True,
            "gemini.api_key": "",
            "xai.enabled": False,
            "openai.chat_enabled": True,
            "openai.api_key": "openai-config-key",
        }
    )

    diagnostics = _provider_key_diagnostics(config)
    checks = {item["provider"]: item for item in diagnostics["checks"]}

    assert diagnostics["operator_action_required"] is True
    assert diagnostics["missing_enabled_providers"] == ["anthropic", "gemini"]
    assert diagnostics["ready_enabled_provider_count"] == 1
    assert checks["anthropic"]["severity"] == "warning"
    assert checks["anthropic"]["config_state"] == "placeholder"
    assert "Set ANTHROPIC_API_KEY" in checks["anthropic"]["operator_action"]
    assert checks["gemini"]["env_keys"] == ["GEMINI_API_KEY", "GOOGLE_API_KEY"]
    assert "GEMINI_API_KEY or GOOGLE_API_KEY" in checks["gemini"]["operator_action"]
    assert checks["openai"]["ready"] is True
    assert checks["xai"]["enabled"] is False


def test_build_doctor_payload_success_masks_token_and_keeps_schema_summary(monkeypatch):
    monkeypatch.setenv("NOTION_API_KEY", "ntn_test_secret_value")
    monkeypatch.setenv("NOTION_DATABASE_ID", "1234567890abcdef1234567890abcdef")

    payload = _build_doctor_payload(
        config=_FakeConfig({}),
        config_path="config.yaml",
        notion=_FakeNotion(),
        ok=True,
    )

    assert payload == {
        "ok": True,
        "status": "PASS",
        "token_masked": "ntn_...alue",
        "raw_id": "1234567890abcdef1234567890abcdef",
        "normalized_id": "12345678-90ab-cdef-1234-567890abcdef",
        "collection_kind": "database",
        "credential_check": [
            "config_path: config.yaml",
            "NOTION_API_KEY env: set",
            "notion.api_key config: missing",
            "NOTION_DATABASE_ID env: set",
            "notion.database_id config: missing",
            "credentials_present: true",
            "fix: if schema fetch still fails, share the target DB/data source with the integration.",
        ],
        "provider_key_check": payload["provider_key_check"],
        "resolved_props": {"title": "콘텐츠", "url": "원본 URL"},
    }
    assert payload["provider_key_check"]["operator_action_required"] is False
    assert "ntn_test_secret_value" not in str(payload)


def test_build_doctor_payload_failure_includes_machine_readable_actions(monkeypatch):
    monkeypatch.delenv("NOTION_API_KEY", raising=False)
    monkeypatch.delenv("NOTION_DATABASE_ID", raising=False)

    payload = _build_doctor_payload(
        config=_FakeConfig(
            {
                "notion.api_key": "${NOTION_API_KEY}",
                "notion.database_id": "${NOTION_DATABASE_ID}",
            }
        ),
        config_path="config.yaml",
        notion=_FakeNotion(),
        ok=False,
        accessible_objects=["database:Review Queue (abc123)"],
    )

    assert payload["ok"] is False
    assert payload["status"] == "FAIL"
    assert payload["error_code"] == "ERROR_NOTION_SCHEMA_FETCH_FAILED"
    assert payload["error_message"] == "not shared with integration"
    assert payload["accessible_objects"] == ["database:Review Queue (abc123)"]
    assert payload["provider_key_check"]["operator_action_required"] is False
    assert payload["actions"] == [
        "Verify NOTION_DATABASE_ID is a real database/data_source ID",
        "Share the target Notion DB/Data Source with the integration",
        "Ensure URL property exists (url or rich_text type)",
        "If reviewer columns are missing, run: py -3 scripts/sync_notion_review_schema.py --config config.yaml --apply",
    ]
    assert "missing_credentials: NOTION_API_KEY, NOTION_DATABASE_ID" in payload["credential_check"]


def test_build_doctor_payload_failure_includes_notion_retry_report(monkeypatch):
    monkeypatch.setenv("NOTION_API_KEY", "ntn_test_token")
    monkeypatch.setenv("NOTION_DATABASE_ID", "1234567890abcdef1234567890abcdef")
    notion = _FakeNotion()
    notion.last_notion_retry_report = _retry_report()

    payload = _build_doctor_payload(
        config=_FakeConfig({}),
        config_path="config.yaml",
        notion=notion,
        ok=False,
        accessible_objects=[],
    )

    assert payload["notion_retry_summary"] == {
        "final_state": "failed",
        "attempt_count": 3,
        "retry_count": 2,
        "last_status": 529,
        "retryable": True,
    }
    assert payload["notion_retry_report"] == notion.last_notion_retry_report
    assert payload["notion_operator_action"] == ("Retry notion_doctor later, then reduce request rate if it repeats.")


def test_print_text_report_includes_retry_summary(capsys, monkeypatch):
    monkeypatch.setenv("NOTION_API_KEY", "ntn_test_token")
    monkeypatch.setenv("NOTION_DATABASE_ID", "1234567890abcdef1234567890abcdef")
    notion = _FakeNotion()
    notion.last_notion_retry_report = _retry_report()
    payload = _build_doctor_payload(
        config=_FakeConfig({}),
        config_path="config.yaml",
        notion=notion,
        ok=False,
        accessible_objects=[],
    )

    _print_text_report(payload)

    output = capsys.readouterr().out
    assert "notion_retry_summary:" in output
    assert "last_status: 529" in output
    assert "notion_operator_action: Retry notion_doctor later" in output
