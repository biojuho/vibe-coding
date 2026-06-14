from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.notion_retry_diagnostics import notion_failure_classification, notion_retry_operator_action  # noqa: E402
from scripts.notion_doctor import (  # noqa: E402
    _build_doctor_payload,
    _credential_diagnostic_lines,
    _print_text_report,
    _provider_key_diagnostics,
    _publish_safety_diagnostics,
    run,
)

DOCTOR_COMMON_SCHEMA_KEYS = {
    "ok",
    "status",
    "token_masked",
    "raw_id",
    "normalized_id",
    "collection_kind",
    "credential_check",
    "provider_key_check",
    "publish_safety_check",
}
DOCTOR_FAILURE_TRIAGE_KEYS = (
    "credential_check",
    "publish_safety_check",
    "error_code",
    "error_message",
    "notion_retry_summary",
    "notion_failure_classification",
    "notion_operator_action",
    "accessible_objects",
    "actions",
)
DOCTOR_FAILURE_SCHEMA_KEYS = set(DOCTOR_FAILURE_TRIAGE_KEYS) | {
    "notion_retry_report",
}
PUBLISH_SAFETY_SCHEMA_KEYS = {
    "operator_action_required",
    "severity",
    "auto_publish_env_enabled",
    "image_generation_env_enabled",
    "twitter_config_enabled",
    "side_effect_env_keys_enabled",
    "credential_env_keys_present",
    "credential_env_key_count",
    "credential_values_redacted",
    "manual_publish_required",
    "operator_actions",
}
PROVIDER_KEY_CHECK_SCHEMA_KEYS = {
    "operator_action_required",
    "missing_enabled_providers",
    "ready_enabled_provider_count",
    "enabled_provider_count",
    "credential_values_redacted",
    "checks",
}
PROVIDER_KEY_CHECK_ENTRY_SCHEMA_KEYS = {
    "provider",
    "enabled",
    "ready",
    "severity",
    "env_keys",
    "env_state",
    "env_key_states",
    "config_key",
    "config_state",
    "operator_action",
}
NOTION_RETRY_SUMMARY_SCHEMA_KEYS = {
    "final_state",
    "attempt_count",
    "retry_count",
    "last_status",
    "retryable",
}
NOTION_FAILURE_CLASSIFICATION_SCHEMA_KEYS = {
    "category",
    "status",
    "retryable",
    "retry_recommended",
    "wait_seconds",
    "primary_repair",
}


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


class _FakeNotionUploader:
    def __init__(self, config):
        self.config = config
        self.api_key = "ntn_test_secret_value"
        self.raw_database_id = "1234567890abcdef1234567890abcdef"
        self.database_id = "12345678-90ab-cdef-1234-567890abcdef"
        self.collection_kind = "database"
        self.props = {"title": "Title", "url": "Source URL"}
        self.last_error_code = ""
        self.last_error_message = ""

    async def ensure_schema(self):
        return True

    async def list_accessible_sources(self, limit: int = 10):
        raise AssertionError(f"list_accessible_sources should not run on success: {limit}")


class _FakeFailingNotionUploader(_FakeNotionUploader):
    def __init__(self, config):
        super().__init__(config)
        self.props = {}
        self.last_error_code = "ERROR_NOTION_SCHEMA_FETCH_FAILED"
        self.last_error_message = "not shared with integration"
        self.last_notion_retry_report = _retry_report()

    async def ensure_schema(self):
        return False

    async def list_accessible_sources(self, limit: int = 10):
        return [
            "database:Review Queue (abc123)",
            "page:Workspace Home (def456)",
        ][:limit]


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


def _terminal_notion_status_report(status: int) -> dict:
    return {
        "attempt_count": 1,
        "retry_count": 0,
        "max_retries": 1,
        "final_state": "failed",
        "final_error": f"HTTP {status}",
        "last_status": status,
        "retryable": False,
        "attempts": [
            {
                "attempt": 1,
                "status": status,
                "retry_after_seconds": None,
                "retryable": False,
                "will_retry": False,
                "delay_seconds": None,
                "error_type": "HTTPStatusError",
                "error": f"HTTP {status}",
            },
        ],
    }


def _clear_publish_env(monkeypatch) -> None:
    for env_name in (
        "AUTO_PUBLISH",
        "OPENAI_IMAGE_ENABLED",
        "TWITTER_ENABLED",
        "X_AUTO_PUBLISH",
        "THREADS_AUTO_PUBLISH",
        "BLOG_AUTO_PUBLISH",
        "TWITTER_CONSUMER_KEY",
        "TWITTER_CONSUMER_SECRET",
        "TWITTER_ACCESS_TOKEN",
        "TWITTER_ACCESS_TOKEN_SECRET",
        "X_BEARER_TOKEN",
        "THREADS_ACCESS_TOKEN",
    ):
        monkeypatch.delenv(env_name, raising=False)


def _assert_publish_safety_schema(payload: dict) -> None:
    publish_safety = payload["publish_safety_check"]

    missing = sorted(PUBLISH_SAFETY_SCHEMA_KEYS - publish_safety.keys())
    assert not missing, f"publish_safety_check missing fields: {missing}"


def _assert_provider_key_check_schema(provider_key_check: dict) -> None:
    missing = sorted(PROVIDER_KEY_CHECK_SCHEMA_KEYS - provider_key_check.keys())
    assert not missing, f"provider_key_check missing fields: {missing}"

    assert isinstance(provider_key_check["checks"], list)
    assert provider_key_check["checks"], "provider_key_check.checks should include provider rows"
    for check in provider_key_check["checks"]:
        missing_check = sorted(PROVIDER_KEY_CHECK_ENTRY_SCHEMA_KEYS - check.keys())
        assert not missing_check, f"provider_key_check.checks[] missing fields: {missing_check}"


def _assert_failure_payload_schema(payload: dict) -> None:
    missing_common = sorted(DOCTOR_COMMON_SCHEMA_KEYS - payload.keys())
    missing_failure = sorted(DOCTOR_FAILURE_SCHEMA_KEYS - payload.keys())
    assert not missing_common, f"doctor payload missing common fields: {missing_common}"
    assert not missing_failure, f"doctor payload missing failure fields: {missing_failure}"

    retry_summary = payload["notion_retry_summary"]
    missing_retry = sorted(NOTION_RETRY_SUMMARY_SCHEMA_KEYS - retry_summary.keys())
    assert not missing_retry, f"notion_retry_summary missing fields: {missing_retry}"

    failure_classification = payload["notion_failure_classification"]
    missing_classification = sorted(NOTION_FAILURE_CLASSIFICATION_SCHEMA_KEYS - failure_classification.keys())
    assert not missing_classification, f"notion_failure_classification missing fields: {missing_classification}"

    _assert_publish_safety_schema(payload)
    _assert_provider_key_check_schema(payload["provider_key_check"])


@pytest.mark.parametrize(
    ("status", "expected_action"),
    [
        (401, "Update NOTION_API_KEY with a valid Notion integration Bearer token before rerun."),
        (403, "Share the target database/data source with the Notion integration before rerun."),
        (
            404,
            "Verify NOTION_DATABASE_ID is the target database/data_source ID and shared before rerun.",
        ),
    ],
)
def test_notion_retry_operator_action_separates_credential_permission_and_not_found(status, expected_action):
    action = notion_retry_operator_action(
        {
            "last_status": status,
            "retryable": False,
            "attempts": [{"status": status, "will_retry": False}],
        }
    )

    assert action == expected_action


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


def test_notion_failure_classification_separates_rate_limit_and_schema_repair():
    rate_limited = notion_failure_classification(
        {
            "last_status": 429,
            "retryable": True,
            "attempts": [{"retry_after_seconds": 8, "delay_seconds": 8}],
        }
    )
    schema_error = notion_failure_classification(
        {
            "last_status": 400,
            "retryable": False,
            "attempts": [{"status": 400, "will_retry": False}],
        }
    )

    assert rate_limited == {
        "category": "rate_limited",
        "status": 429,
        "retryable": True,
        "retry_recommended": True,
        "wait_seconds": 8,
        "primary_repair": "respect_retry_after_or_backoff",
    }
    assert schema_error == {
        "category": "schema_or_payload",
        "status": 400,
        "retryable": False,
        "retry_recommended": False,
        "wait_seconds": None,
        "primary_repair": "fix_schema_or_payload",
    }


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
            "or config.yaml; NOTION_API_KEY must be the integration Bearer token and "
            "NOTION_DATABASE_ID must be the target database/data_source ID."
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
        (
            "fix: if schema fetch still fails, verify the target database/data_source ID, "
            "share it with the integration, and confirm the collection mode before rerun."
        ),
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
    assert diagnostics["credential_values_redacted"] is True
    assert checks["anthropic"]["severity"] == "warning"
    assert checks["anthropic"]["config_state"] == "placeholder"
    assert checks["anthropic"]["env_key_states"] == {"ANTHROPIC_API_KEY": "missing"}
    assert "Set ANTHROPIC_API_KEY" in checks["anthropic"]["operator_action"]
    assert checks["gemini"]["env_keys"] == ["GEMINI_API_KEY", "GOOGLE_API_KEY"]
    assert checks["gemini"]["env_key_states"] == {
        "GEMINI_API_KEY": "missing",
        "GOOGLE_API_KEY": "missing",
    }
    assert "GEMINI_API_KEY or GOOGLE_API_KEY" in checks["gemini"]["operator_action"]
    assert checks["openai"]["ready"] is True
    assert checks["xai"]["enabled"] is False


def test_provider_key_diagnostics_reports_per_env_key_state_without_values(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("GOOGLE_API_KEY", "google-secret-value")
    config = _FakeConfig(
        {
            "gemini.enabled": True,
            "gemini.api_key": "",
        }
    )

    diagnostics = _provider_key_diagnostics(config)
    gemini = {item["provider"]: item for item in diagnostics["checks"]}["gemini"]

    assert diagnostics["operator_action_required"] is False
    assert diagnostics["credential_values_redacted"] is True
    assert gemini["ready"] is True
    assert gemini["env_state"] == "set"
    assert gemini["env_key_states"] == {
        "GEMINI_API_KEY": "missing",
        "GOOGLE_API_KEY": "set",
    }
    assert "google-secret-value" not in str(diagnostics)


def test_provider_key_diagnostics_treats_enabled_string_false_as_disabled(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    config = _FakeConfig(
        {
            "anthropic.enabled": "false",
            "anthropic.api_key": "",
        }
    )

    diagnostics = _provider_key_diagnostics(config)
    anthropic = {item["provider"]: item for item in diagnostics["checks"]}["anthropic"]

    assert diagnostics["operator_action_required"] is False
    assert diagnostics["missing_enabled_providers"] == []
    assert anthropic["enabled"] is False
    assert anthropic["ready"] is True


def test_provider_key_diagnostics_respects_llm_provider_aliases(monkeypatch):
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
            "llm.providers": ["Claude", "grok", "chatgpt", "moonshot", "zhipuai"],
        }
    )

    diagnostics = _provider_key_diagnostics(config)
    checks = {item["provider"]: item for item in diagnostics["checks"]}

    assert diagnostics["operator_action_required"] is True
    assert diagnostics["missing_enabled_providers"] == ["anthropic", "moonshot", "zhipuai", "xai", "openai"]
    assert checks["anthropic"]["enabled"] is True
    assert checks["xai"]["enabled"] is True
    assert checks["openai"]["enabled"] is True
    assert checks["deepseek"]["enabled"] is False


def test_provider_key_diagnostics_schema_matches_ops_runbook(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    config = _FakeConfig(
        {
            "llm.providers": ["claude", "gemini"],
            "anthropic.api_key": "${ANTHROPIC_API_KEY}",
            "gemini.api_key": "",
        }
    )

    diagnostics = _provider_key_diagnostics(config)

    _assert_provider_key_check_schema(diagnostics)
    runbook = (ROOT / "docs" / "ops-runbook.md").read_text(encoding="utf-8")
    for key in PROVIDER_KEY_CHECK_SCHEMA_KEYS - {"checks"}:
        assert f"`provider_key_check.{key}`" in runbook
    assert "`provider_key_check.checks[].provider`" in runbook
    for key in PROVIDER_KEY_CHECK_ENTRY_SCHEMA_KEYS - {"provider"}:
        assert f"`{key}`" in runbook
    assert diagnostics["operator_action_required"] is True
    assert diagnostics["missing_enabled_providers"] == ["anthropic", "gemini"]
    assert "ANTHROPIC_API_KEY" in str(diagnostics)
    assert "GEMINI_API_KEY" in str(diagnostics)


def test_publish_safety_diagnostics_reports_states_without_secret_values(monkeypatch):
    _clear_publish_env(monkeypatch)
    monkeypatch.setenv("AUTO_PUBLISH", "true")
    monkeypatch.setenv("OPENAI_IMAGE_ENABLED", "1")
    monkeypatch.setenv("TWITTER_CONSUMER_KEY", "consumer-key-secret-value")
    monkeypatch.setenv("TWITTER_ACCESS_TOKEN", "access-token-secret-value")
    config = _FakeConfig({"twitter.enabled": True})

    diagnostics = _publish_safety_diagnostics(config)

    assert diagnostics["operator_action_required"] is True
    assert diagnostics["severity"] == "warning"
    assert diagnostics["auto_publish_env_enabled"] is True
    assert diagnostics["image_generation_env_enabled"] is True
    assert diagnostics["twitter_config_enabled"] is True
    assert diagnostics["side_effect_env_keys_enabled"] == ["AUTO_PUBLISH", "OPENAI_IMAGE_ENABLED"]
    assert diagnostics["credential_env_keys_present"] == ["TWITTER_CONSUMER_KEY", "TWITTER_ACCESS_TOKEN"]
    assert diagnostics["credential_env_key_count"] == 2
    assert diagnostics["credential_values_redacted"] is True
    assert diagnostics["manual_publish_required"] is True
    assert "consumer-key-secret-value" not in str(diagnostics)
    assert "access-token-secret-value" not in str(diagnostics)
    assert any("AUTO_PUBLISH" in action for action in diagnostics["operator_actions"])
    assert any("twitter.enabled=false" in action for action in diagnostics["operator_actions"])


def test_publish_safety_diagnostics_treats_twitter_string_false_as_disabled(monkeypatch):
    _clear_publish_env(monkeypatch)
    config = _FakeConfig({"twitter.enabled": "false"})

    diagnostics = _publish_safety_diagnostics(config)

    assert diagnostics["operator_action_required"] is False
    assert diagnostics["severity"] == "ok"
    assert diagnostics["twitter_config_enabled"] is False
    assert diagnostics["operator_actions"] == []


def test_build_doctor_payload_success_masks_token_and_keeps_schema_summary(monkeypatch):
    _clear_publish_env(monkeypatch)
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
            (
                "fix: if schema fetch still fails, verify the target database/data_source ID, "
                "share it with the integration, and confirm the collection mode before rerun."
            ),
        ],
        "provider_key_check": payload["provider_key_check"],
        "publish_safety_check": payload["publish_safety_check"],
        "resolved_props": {"title": "콘텐츠", "url": "원본 URL"},
    }
    assert payload["provider_key_check"]["operator_action_required"] is False
    assert payload["publish_safety_check"]["operator_action_required"] is False
    assert payload["publish_safety_check"]["credential_values_redacted"] is True
    assert "ntn_test_secret_value" not in str(payload)


def test_build_doctor_payload_failure_includes_machine_readable_actions(monkeypatch):
    _clear_publish_env(monkeypatch)
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
    assert payload["publish_safety_check"]["operator_action_required"] is False
    assert payload["actions"] == [
        "If missing_credentials is present, set NOTION_API_KEY and NOTION_DATABASE_ID before schema work",
        "Verify NOTION_API_KEY is the integration Bearer token",
        "Verify NOTION_DATABASE_ID is the target database/data_source ID for the selected collection mode",
        "For collection_kind=data_source, use a data source ID with Notion-Version 2025-09-03",
        "For 403 restricted_resource or 404 object_not_found, share the target database/data source with the integration",
        "For rate_limited/service_overload/transient_server_error, retry after Retry-After/backoff before schema changes",
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
    assert payload["notion_failure_classification"] == {
        "category": "service_overload",
        "status": 529,
        "retryable": True,
        "retry_recommended": True,
        "wait_seconds": None,
        "primary_repair": "respect_retry_after_or_backoff",
    }
    assert payload["notion_retry_report"] == notion.last_notion_retry_report
    assert payload["notion_operator_action"] == ("Retry notion_doctor later, then reduce request rate if it repeats.")


def test_doctor_failure_payload_schema_matches_ops_runbook_triage(monkeypatch):
    _clear_publish_env(monkeypatch)
    notion = _FakeNotion()
    notion.last_notion_retry_report = _retry_report()

    payload = _build_doctor_payload(
        config=_FakeConfig({}),
        config_path="config.yaml",
        notion=notion,
        ok=False,
        accessible_objects=["database:Review Queue (abc123)"],
    )

    _assert_failure_payload_schema(payload)
    runbook = (ROOT / "docs" / "ops-runbook.md").read_text(encoding="utf-8")
    for key in DOCTOR_FAILURE_TRIAGE_KEYS:
        assert f"`{key}`" in runbook, f"runbook must document doctor failure field: {key}"
    for key in (
        "operator_action_required",
        "auto_publish_env_enabled",
        "image_generation_env_enabled",
        "twitter_config_enabled",
        "credential_values_redacted",
    ):
        assert key in payload["publish_safety_check"]
        assert f"`{key}=false`" in runbook or f"`{key}=true`" in runbook


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
    assert "notion_failure_classification:" in output
    assert "category: service_overload" in output
    assert "primary_repair: respect_retry_after_or_backoff" in output
    assert "notion_operator_action: Retry notion_doctor later" in output


def test_print_text_report_includes_provider_readiness_counts(capsys, monkeypatch):
    for env_name in (
        "ANTHROPIC_API_KEY",
        "GEMINI_API_KEY",
        "GOOGLE_API_KEY",
    ):
        monkeypatch.delenv(env_name, raising=False)
    payload = _build_doctor_payload(
        config=_FakeConfig(
            {
                "anthropic.enabled": True,
                "anthropic.api_key": "anthropic-config-secret-value",
                "gemini.enabled": True,
                "gemini.api_key": "",
            }
        ),
        config_path="config.yaml",
        notion=_FakeNotion(),
        ok=True,
    )

    _print_text_report(payload)

    output = capsys.readouterr().out
    assert "provider_key_check:" in output
    assert "operator_action_required: True" in output
    assert "ready_enabled_provider_count: 1" in output
    assert "enabled_provider_count: 2" in output
    assert "credential_values_redacted: True" in output
    assert "missing_enabled_providers: gemini" in output
    assert "gemini: env=missing config=missing action=Set GEMINI_API_KEY or GOOGLE_API_KEY" in output
    assert "env_keys=GEMINI_API_KEY=missing,GOOGLE_API_KEY=missing" in output
    assert "anthropic-config-secret-value" not in output


def test_print_text_report_includes_publish_safety_without_secret_values(capsys, monkeypatch):
    _clear_publish_env(monkeypatch)
    monkeypatch.setenv("AUTO_PUBLISH", "true")
    monkeypatch.setenv("OPENAI_IMAGE_ENABLED", "true")
    monkeypatch.setenv("TWITTER_CONSUMER_SECRET", "consumer-secret-value")
    payload = _build_doctor_payload(
        config=_FakeConfig({}),
        config_path="config.yaml",
        notion=_FakeNotion(),
        ok=True,
    )

    _print_text_report(payload)

    output = capsys.readouterr().out
    assert "publish_safety_check:" in output
    assert "manual_publish_required: True" in output
    assert "side_effect_env_keys_enabled: AUTO_PUBLISH, OPENAI_IMAGE_ENABLED" in output
    assert "credential_env_key_count: 1" in output
    assert "credential_env_keys_present: TWITTER_CONSUMER_SECRET" in output
    assert "credential_values_redacted: True" in output
    assert "consumer-secret-value" not in output


@pytest.mark.asyncio
async def test_run_json_output_includes_redacted_publish_safety_contract(capsys, monkeypatch):
    _clear_publish_env(monkeypatch)
    monkeypatch.setenv("TWITTER_CONSUMER_SECRET", "json-secret-value")
    monkeypatch.setattr("scripts.notion_doctor.load_env", lambda: None)
    monkeypatch.setattr("scripts.notion_doctor.ConfigManager", lambda config_path: _FakeConfig({}))
    monkeypatch.setattr("scripts.notion_doctor.NotionUploader", _FakeNotionUploader)

    result = await run("config.yaml", json_output=True)

    assert result == 0
    output = capsys.readouterr().out
    payload = json.loads(output)
    publish_safety = payload["publish_safety_check"]
    assert publish_safety["operator_action_required"] is False
    assert publish_safety["severity"] == "ok"
    assert publish_safety["auto_publish_env_enabled"] is False
    assert publish_safety["image_generation_env_enabled"] is False
    assert publish_safety["twitter_config_enabled"] is False
    assert publish_safety["credential_env_keys_present"] == ["TWITTER_CONSUMER_SECRET"]
    assert publish_safety["credential_env_key_count"] == 1
    assert publish_safety["credential_values_redacted"] is True
    assert "TWITTER_CONSUMER_SECRET" in output
    assert "json-secret-value" not in output
    assert "ntn_test_secret_value" not in output


@pytest.mark.asyncio
async def test_run_json_failure_output_keeps_retry_preview_and_publish_safety(capsys, monkeypatch):
    _clear_publish_env(monkeypatch)
    monkeypatch.setenv("AUTO_PUBLISH", "true")
    monkeypatch.setenv("TWITTER_ACCESS_TOKEN", "json-failure-secret-value")
    monkeypatch.setattr("scripts.notion_doctor.load_env", lambda: None)
    monkeypatch.setattr("scripts.notion_doctor.ConfigManager", lambda config_path: _FakeConfig({}))
    monkeypatch.setattr("scripts.notion_doctor.NotionUploader", _FakeFailingNotionUploader)

    result = await run("config.yaml", json_output=True)

    assert result == 2
    output = capsys.readouterr().out
    payload = json.loads(output)
    assert payload["ok"] is False
    assert payload["status"] == "FAIL"
    assert payload["error_code"] == "ERROR_NOTION_SCHEMA_FETCH_FAILED"
    assert payload["accessible_objects"] == [
        "database:Review Queue (abc123)",
        "page:Workspace Home (def456)",
    ]
    assert payload["notion_retry_summary"] == {
        "final_state": "failed",
        "attempt_count": 3,
        "retry_count": 2,
        "last_status": 529,
        "retryable": True,
    }
    assert payload["notion_failure_classification"]["category"] == "service_overload"
    assert payload["notion_failure_classification"]["primary_repair"] == "respect_retry_after_or_backoff"
    assert payload["notion_operator_action"] == "Retry notion_doctor later, then reduce request rate if it repeats."
    _assert_failure_payload_schema(payload)
    publish_safety = payload["publish_safety_check"]
    assert publish_safety["operator_action_required"] is True
    assert publish_safety["severity"] == "warning"
    assert publish_safety["auto_publish_env_enabled"] is True
    assert publish_safety["credential_env_keys_present"] == ["TWITTER_ACCESS_TOKEN"]
    assert publish_safety["credential_values_redacted"] is True
    assert "TWITTER_ACCESS_TOKEN" in output
    assert "json-failure-secret-value" not in output
    assert "ntn_test_secret_value" not in output


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "expected_category", "expected_repair", "expected_action"),
    [
        (
            401,
            "credential_invalid",
            "fix_notion_token",
            "Update NOTION_API_KEY with a valid Notion integration Bearer token before rerun.",
        ),
        (
            403,
            "permission_or_sharing",
            "share_database_with_integration",
            "Share the target database/data source with the Notion integration before rerun.",
        ),
        (
            404,
            "object_not_found_or_not_shared",
            "verify_database_id_and_sharing",
            "Verify NOTION_DATABASE_ID is the target database/data_source ID and shared before rerun.",
        ),
    ],
)
async def test_run_json_failure_output_keeps_status_specific_operator_action(
    capsys,
    monkeypatch,
    status,
    expected_category,
    expected_repair,
    expected_action,
):
    class _FakeStatusFailingNotionUploader(_FakeFailingNotionUploader):
        def __init__(self, config):
            super().__init__(config)
            self.last_notion_retry_report = _terminal_notion_status_report(status)

    _clear_publish_env(monkeypatch)
    monkeypatch.setattr("scripts.notion_doctor.load_env", lambda: None)
    monkeypatch.setattr("scripts.notion_doctor.ConfigManager", lambda config_path: _FakeConfig({}))
    monkeypatch.setattr("scripts.notion_doctor.NotionUploader", _FakeStatusFailingNotionUploader)

    result = await run("config.yaml", json_output=True)

    assert result == 2
    output = capsys.readouterr().out
    payload = json.loads(output)
    assert payload["notion_retry_summary"]["last_status"] == status
    assert payload["notion_retry_summary"]["retryable"] is False
    assert payload["notion_failure_classification"]["category"] == expected_category
    assert payload["notion_failure_classification"]["retry_recommended"] is False
    assert payload["notion_failure_classification"]["primary_repair"] == expected_repair
    assert payload["notion_operator_action"] == expected_action
    _assert_failure_payload_schema(payload)
    assert "ntn_test_secret_value" not in output
