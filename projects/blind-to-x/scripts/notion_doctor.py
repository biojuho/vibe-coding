from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import ConfigManager, load_env  # noqa: E402
from pipeline.notion_retry_diagnostics import notion_retry_diagnostics  # noqa: E402
from pipeline.notion_upload import NotionUploader  # noqa: E402

_PROVIDER_KEY_REQUIREMENTS = (
    {
        "provider": "anthropic",
        "env_keys": ("ANTHROPIC_API_KEY",),
        "config_key": "anthropic.api_key",
        "enabled_key": "anthropic.enabled",
    },
    {
        "provider": "gemini",
        "env_keys": ("GEMINI_API_KEY", "GOOGLE_API_KEY"),
        "config_key": "gemini.api_key",
        "enabled_key": "gemini.enabled",
    },
    {
        "provider": "deepseek",
        "env_keys": ("DEEPSEEK_API_KEY",),
        "config_key": "deepseek.api_key",
        "enabled_key": "deepseek.enabled",
    },
    {
        "provider": "moonshot",
        "env_keys": ("MOONSHOT_API_KEY",),
        "config_key": "moonshot.api_key",
        "enabled_key": "moonshot.enabled",
    },
    {
        "provider": "zhipuai",
        "env_keys": ("ZHIPUAI_API_KEY",),
        "config_key": "zhipuai.api_key",
        "enabled_key": "zhipuai.enabled",
    },
    {
        "provider": "xai",
        "env_keys": ("XAI_API_KEY", "GROK_API_KEY"),
        "config_key": "xai.api_key",
        "enabled_key": "xai.enabled",
    },
    {
        "provider": "openai",
        "env_keys": ("OPENAI_API_KEY",),
        "config_key": "openai.api_key",
        "enabled_key": "openai.chat_enabled",
    },
)

_LLM_PROVIDER_ALIASES = {
    "claude": "anthropic",
    "anthropic": "anthropic",
    "gemini": "gemini",
    "deepseek": "deepseek",
    "moonshot": "moonshot",
    "zhipuai": "zhipuai",
    "grok": "xai",
    "xai": "xai",
    "chatgpt": "openai",
    "openai": "openai",
}
_PUBLISH_CREDENTIAL_ENV_KEYS = (
    "TWITTER_CONSUMER_KEY",
    "TWITTER_CONSUMER_SECRET",
    "TWITTER_ACCESS_TOKEN",
    "TWITTER_ACCESS_TOKEN_SECRET",
    "X_BEARER_TOKEN",
    "THREADS_ACCESS_TOKEN",
)
_PUBLISH_SIDE_EFFECT_ENV_KEYS = (
    "AUTO_PUBLISH",
    "OPENAI_IMAGE_ENABLED",
    "TWITTER_ENABLED",
    "X_AUTO_PUBLISH",
    "THREADS_AUTO_PUBLISH",
    "BLOG_AUTO_PUBLISH",
)


def _mask_token(value: str) -> str:
    if not value:
        return "(empty)"
    if len(value) <= 8:
        return value
    return f"{value[:4]}...{value[-4:]}"


def _config_value_state(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return "missing"
    if text.startswith("${") and text.endswith("}"):
        return "placeholder"
    return "set"


def _has_usable_config_value(value: object) -> bool:
    return _config_value_state(value) == "set"


def _env_truthy(name: str) -> bool:
    return str(os.environ.get(name, "") or "").strip().lower() in {"1", "true", "yes", "on"}


def _as_bool(value: Any, *, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "y", "on"}:
            return True
        if normalized in {"0", "false", "no", "n", "off", ""}:
            return False
        return default
    return bool(value)


def _provider_explicitly_enabled(config: ConfigManager, requirement: dict[str, Any]) -> bool:
    provider = str(requirement["provider"])
    enabled_key = str(requirement["enabled_key"])
    explicit = config.get(enabled_key, None)
    if provider == "openai" and explicit is None:
        explicit = config.get("openai.enabled", None)
    if explicit is not None:
        return _as_bool(explicit)

    configured = config.get("llm.providers", []) or []
    normalized = {_LLM_PROVIDER_ALIASES.get(str(item).strip().lower(), "") for item in configured}
    return provider in normalized


def _env_key_states(env_keys: tuple[str, ...]) -> dict[str, str]:
    return {env_key: "set" if os.environ.get(env_key, "").strip() else "missing" for env_key in env_keys}


def _provider_key_diagnostics(config: ConfigManager) -> dict[str, Any]:
    checks = []
    for requirement in _PROVIDER_KEY_REQUIREMENTS:
        provider = str(requirement["provider"])
        env_keys = tuple(str(key) for key in requirement["env_keys"])
        config_key = str(requirement["config_key"])
        enabled_key = str(requirement["enabled_key"])
        enabled = _provider_explicitly_enabled(config, requirement)
        env_key_states = _env_key_states(env_keys)
        env_present = any(state == "set" for state in env_key_states.values())
        config_state = _config_value_state(config.get(config_key, ""))
        ready = bool(not enabled or env_present or config_state == "set")
        operator_action = ""
        if enabled and not ready:
            env_hint = " or ".join(env_keys)
            operator_action = f"Set {env_hint} or {config_key}, or disable {enabled_key} if this provider is not used."

        checks.append(
            {
                "provider": provider,
                "enabled": enabled,
                "ready": ready,
                "severity": "ok" if ready else "warning",
                "env_keys": list(env_keys),
                "env_state": "set" if env_present else "missing",
                "env_key_states": env_key_states,
                "config_key": config_key,
                "config_state": config_state,
                "operator_action": operator_action,
            }
        )

    missing_enabled = [check["provider"] for check in checks if check["enabled"] and not check["ready"]]
    return {
        "operator_action_required": bool(missing_enabled),
        "missing_enabled_providers": missing_enabled,
        "ready_enabled_provider_count": sum(1 for check in checks if check["enabled"] and check["ready"]),
        "enabled_provider_count": sum(1 for check in checks if check["enabled"]),
        "credential_values_redacted": True,
        "checks": checks,
    }


def _publish_safety_diagnostics(config: ConfigManager) -> dict[str, Any]:
    side_effect_keys_enabled = [key for key in _PUBLISH_SIDE_EFFECT_ENV_KEYS if _env_truthy(key)]
    credential_keys_present = [
        key for key in _PUBLISH_CREDENTIAL_ENV_KEYS if str(os.environ.get(key, "") or "").strip()
    ]
    twitter_config_enabled = _as_bool(config.get("twitter.enabled", False))
    unsafe = bool(side_effect_keys_enabled or twitter_config_enabled)
    operator_actions = []
    if side_effect_keys_enabled:
        operator_actions.append(
            "Disable publish/cost side-effect env flags for review-only runs: " + ", ".join(side_effect_keys_enabled)
        )
    if twitter_config_enabled:
        operator_actions.append("Set twitter.enabled=false unless you are explicitly running --reprocess-approved.")
    if credential_keys_present:
        operator_actions.append(
            "Credential env keys are present; keep values local and confirm manual publish before use."
        )

    return {
        "operator_action_required": unsafe,
        "severity": "warning" if unsafe else "ok",
        "auto_publish_env_enabled": _env_truthy("AUTO_PUBLISH"),
        "image_generation_env_enabled": _env_truthy("OPENAI_IMAGE_ENABLED"),
        "twitter_config_enabled": twitter_config_enabled,
        "side_effect_env_keys_enabled": side_effect_keys_enabled,
        "credential_env_keys_present": credential_keys_present,
        "credential_env_key_count": len(credential_keys_present),
        "credential_values_redacted": True,
        "manual_publish_required": True,
        "operator_actions": operator_actions,
    }


def _credential_diagnostic_lines(config: ConfigManager, config_path: str) -> list[str]:
    api_key_config = config.get("notion.api_key", "")
    database_id_config = config.get("notion.database_id", "")
    api_key_env = os.environ.get("NOTION_API_KEY", "").strip()
    database_id_env = os.environ.get("NOTION_DATABASE_ID", "").strip()

    missing = []
    if not api_key_env and not _has_usable_config_value(api_key_config):
        missing.append("NOTION_API_KEY")
    if not database_id_env and not _has_usable_config_value(database_id_config):
        missing.append("NOTION_DATABASE_ID")

    lines = [
        f"config_path: {config_path}",
        f"NOTION_API_KEY env: {'set' if api_key_env else 'missing'}",
        f"notion.api_key config: {_config_value_state(api_key_config)}",
        f"NOTION_DATABASE_ID env: {'set' if database_id_env else 'missing'}",
        f"notion.database_id config: {_config_value_state(database_id_config)}",
    ]
    if missing:
        lines.append(f"missing_credentials: {', '.join(missing)}")
        lines.append(
            "fix: set missing values in project .env, the BLIND_TO_X_ENV_PATH file, "
            "or config.yaml; NOTION_API_KEY must be the integration Bearer token and "
            "NOTION_DATABASE_ID must be the target database/data_source ID."
        )
    else:
        lines.append("credentials_present: true")
        lines.append(
            "fix: if schema fetch still fails, verify the target database/data_source ID, "
            "share it with the integration, and confirm the collection mode before rerun."
        )
    return lines


def _doctor_actions() -> list[str]:
    return [
        "If missing_credentials is present, set NOTION_API_KEY and NOTION_DATABASE_ID before schema work",
        "Verify NOTION_API_KEY is the integration Bearer token",
        "Verify NOTION_DATABASE_ID is the target database/data_source ID for the selected collection mode",
        "For collection_kind=data_source, use a data source ID with Notion-Version 2025-09-03",
        "For 403 restricted_resource or 404 object_not_found, share the target database/data source with the integration",
        "For rate_limited/service_overload/transient_server_error, retry after Retry-After/backoff before schema changes",
        "Ensure URL property exists (url or rich_text type)",
        "If reviewer columns are missing, run: py -3 scripts/sync_notion_review_schema.py --config config.yaml --apply",
    ]


def _build_doctor_payload(
    *,
    config: ConfigManager,
    config_path: str,
    notion: NotionUploader,
    ok: bool,
    accessible_objects: list[str] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "ok": ok,
        "status": "PASS" if ok else "FAIL",
        "token_masked": _mask_token(notion.api_key or ""),
        "raw_id": notion.raw_database_id or "",
        "normalized_id": notion.database_id or "",
        "collection_kind": notion.collection_kind,
        "credential_check": _credential_diagnostic_lines(config, config_path),
        "provider_key_check": _provider_key_diagnostics(config),
        "publish_safety_check": _publish_safety_diagnostics(config),
    }
    if ok:
        payload["resolved_props"] = notion.props
    else:
        payload.update(
            {
                "error_code": notion.last_error_code,
                "error_message": notion.last_error_message,
                "accessible_objects": accessible_objects or [],
                "actions": _doctor_actions(),
            }
        )
        payload.update(notion_retry_diagnostics(notion, retry_label="notion_doctor"))
    return payload


def _print_provider_key_check(payload: dict[str, Any]) -> None:
    provider_key_check = payload.get("provider_key_check")
    if not isinstance(provider_key_check, dict):
        return
    print("  provider_key_check:")
    print(f"    operator_action_required: {provider_key_check.get('operator_action_required')}")
    print(f"    ready_enabled_provider_count: {provider_key_check.get('ready_enabled_provider_count')}")
    print(f"    enabled_provider_count: {provider_key_check.get('enabled_provider_count')}")
    print(f"    credential_values_redacted: {provider_key_check.get('credential_values_redacted')}")
    missing = provider_key_check.get("missing_enabled_providers") or []
    print(f"    missing_enabled_providers: {', '.join(missing) if missing else '(none)'}")
    for check in provider_key_check.get("checks", []):
        if not isinstance(check, dict) or check.get("severity") != "warning":
            continue
        env_key_states = check.get("env_key_states")
        env_key_state_text = ""
        if isinstance(env_key_states, dict) and env_key_states:
            env_key_state_text = " env_keys=" + ",".join(
                f"{env_key}={state}" for env_key, state in env_key_states.items()
            )
        print(
            "    - "
            f"{check.get('provider')}: env={check.get('env_state')} "
            f"config={check.get('config_state')} action={check.get('operator_action')}"
            f"{env_key_state_text}"
        )


def _print_publish_safety_check(payload: dict[str, Any]) -> None:
    publish_safety_check = payload.get("publish_safety_check")
    if not isinstance(publish_safety_check, dict):
        return
    print("  publish_safety_check:")
    print(f"    severity: {publish_safety_check.get('severity')}")
    print(f"    operator_action_required: {publish_safety_check.get('operator_action_required')}")
    print(f"    auto_publish_env_enabled: {publish_safety_check.get('auto_publish_env_enabled')}")
    print(f"    image_generation_env_enabled: {publish_safety_check.get('image_generation_env_enabled')}")
    print(f"    twitter_config_enabled: {publish_safety_check.get('twitter_config_enabled')}")
    print(f"    manual_publish_required: {publish_safety_check.get('manual_publish_required')}")
    side_effect_keys = publish_safety_check.get("side_effect_env_keys_enabled") or []
    print(f"    side_effect_env_keys_enabled: {', '.join(side_effect_keys) if side_effect_keys else '(none)'}")
    keys = publish_safety_check.get("credential_env_keys_present") or []
    print(f"    credential_env_key_count: {publish_safety_check.get('credential_env_key_count')}")
    print(f"    credential_env_keys_present: {', '.join(keys) if keys else '(none)'}")
    print(f"    credential_values_redacted: {publish_safety_check.get('credential_values_redacted')}")
    for action in publish_safety_check.get("operator_actions", []):
        print(f"    action: {action}")


def _print_text_report(payload: dict[str, Any]) -> None:
    print("[NOTION DOCTOR]")
    print(f"  token: {payload['token_masked']}")
    print(f"  raw_id: {payload['raw_id'] or '(empty)'}")
    print(f"  normalized_id: {payload['normalized_id'] or '(empty)'}")

    if payload["ok"]:
        print("  status: PASS")
        print(f"  collection_kind: {payload['collection_kind']}")
        print(f"  resolved_props: {payload['resolved_props']}")
        _print_provider_key_check(payload)
        _print_publish_safety_check(payload)
        return

    print("  status: FAIL")
    print(f"  error_code: {payload['error_code']}")
    print(f"  error_message: {payload['error_message']}")
    print("  credential_check:")
    for line in payload["credential_check"]:
        print(f"    {line}")

    _print_provider_key_check(payload)
    _print_publish_safety_check(payload)

    if payload["accessible_objects"]:
        print("  accessible_objects:")
        for item in payload["accessible_objects"]:
            print(f"    - {item}")

    retry_summary = payload.get("notion_retry_summary")
    if isinstance(retry_summary, dict):
        print("  notion_retry_summary:")
        for key in ("final_state", "attempt_count", "retry_count", "last_status", "retryable"):
            print(f"    {key}: {retry_summary.get(key)}")
        failure_classification = payload.get("notion_failure_classification")
        if isinstance(failure_classification, dict):
            print("  notion_failure_classification:")
            for key in ("category", "retry_recommended", "wait_seconds", "primary_repair"):
                print(f"    {key}: {failure_classification.get(key)}")
        print(f"  notion_operator_action: {payload.get('notion_operator_action')}")

    print("  action:")
    for index, action in enumerate(payload["actions"], start=1):
        print(f"    {index}) {action}")


async def run(config_path: str, *, json_output: bool = False) -> int:
    load_env()
    config = ConfigManager(config_path)
    notion = NotionUploader(config)

    ok = await notion.ensure_schema()
    previews = [] if ok else await notion.list_accessible_sources(limit=10)
    payload = _build_doctor_payload(
        config=config,
        config_path=config_path,
        notion=notion,
        ok=ok,
        accessible_objects=previews,
    )
    if json_output:
        print(json.dumps(payload, ensure_ascii=True, sort_keys=True))
    else:
        _print_text_report(payload)

    if ok:
        return 0

    return 2


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Diagnose Notion connection/schema for blind-to-x.")
    parser.add_argument("--config", default="config.yaml", help="Path to config file")
    parser.add_argument("--json", action="store_true", help="Print a structured JSON doctor report")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    return asyncio.run(run(args.config, json_output=args.json))


if __name__ == "__main__":
    raise SystemExit(main())
