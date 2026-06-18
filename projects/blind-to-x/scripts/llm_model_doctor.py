"""Diagnose whether each configured LLM provider's model is still available.

Providers retire models (~quarterly). When a configured model name is retired,
calls 404 and the pipeline silently falls back to another provider — losing the
intended (often higher-quality or free-tier) provider with no alert. This doctor
checks each enabled provider's configured model against its live API so a dead
model is caught as an explicit failure instead of silent degradation.

Checks (the same endpoints the app calls — see workspace/execution/llm_client.py
OPENAI_COMPATIBLE_BASE_URLS and pipeline/draft_providers.py):
  - anthropic : GET https://api.anthropic.com/v1/models/{model}
  - gemini    : GET https://generativelanguage.googleapis.com/v1beta/models/{model}
  - openai    : GET https://api.openai.com/v1/models/{model}
  - xai/deepseek/moonshot/zhipuai (OpenAI-compatible): GET {base}/models, check membership

Classification is deliberately conservative: only a definitive 404 from a
single-model retrieve (anthropic/gemini/openai) counts as ``dead``. For the
OpenAI-compatible *list* providers, a model absent from a successful list is
``unknown`` — provider model lists vary in completeness and id format, so absence
is not proof of retirement (e.g. DeepSeek serves ``deepseek-chat`` even when its
``/models`` list shape doesn't surface that exact id). Network/auth/parse problems
are ``unreachable``/``auth_error``/``unknown`` (warnings). The bias is toward never
false-alarming a working model as dead.

Usage:
    py -3 scripts/llm_model_doctor.py            # text report
    py -3 scripts/llm_model_doctor.py --json      # structured JSON
Exit codes: 0 = no dead models, 2 = at least one enabled provider's model is dead,
3 = config/setup error.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import ConfigManager, load_env  # noqa: E402

# provider name -> OpenAI-compatible base URL (mirrors
# workspace/execution/llm_client.py OPENAI_COMPATIBLE_BASE_URLS).
OPENAI_COMPATIBLE_BASE_URLS: dict[str, str] = {
    "xai": "https://api.x.ai/v1",
    "deepseek": "https://api.deepseek.com",
    "moonshot": "https://api.moonshot.cn/v1",
    "zhipuai": "https://open.bigmodel.cn/api/paas/v4",
}

# Each spec: provider, the config key holding its model, the enabled flag key,
# the env keys that may hold its API key, and the check method.
PROVIDER_SPECS: tuple[dict[str, Any], ...] = (
    {
        "provider": "anthropic",
        "model_key": "anthropic.model",
        "enabled_key": "anthropic.enabled",
        "env_keys": ("ANTHROPIC_API_KEY",),
        "method": "retrieve",
    },
    {
        "provider": "gemini",
        "model_key": "gemini.model",
        "enabled_key": "gemini.enabled",
        "env_keys": ("GEMINI_API_KEY", "GOOGLE_API_KEY"),
        "method": "retrieve",
    },
    {
        "provider": "openai",
        "model_key": "openai.chat_model",
        "enabled_key": "openai.chat_enabled",
        "env_keys": ("OPENAI_API_KEY",),
        "method": "retrieve",
    },
    {
        "provider": "xai",
        "model_key": "xai.model",
        "enabled_key": "xai.enabled",
        "env_keys": ("XAI_API_KEY", "GROK_API_KEY"),
        "method": "list",
    },
    {
        "provider": "deepseek",
        "model_key": "deepseek.model",
        "enabled_key": "deepseek.enabled",
        "env_keys": ("DEEPSEEK_API_KEY",),
        "method": "list",
    },
    {
        "provider": "moonshot",
        "model_key": "moonshot.model",
        "enabled_key": "moonshot.enabled",
        "env_keys": ("MOONSHOT_API_KEY",),
        "method": "list",
    },
    {
        "provider": "zhipuai",
        "model_key": "zhipuai.model",
        "enabled_key": "zhipuai.enabled",
        "env_keys": ("ZHIPUAI_API_KEY",),
        "method": "list",
    },
)

# (status, json) tuple returned by an injected HTTP getter.
HttpGet = Callable[..., tuple[int, Any]]

OK = "ok"
DEAD = "dead"
AUTH_ERROR = "auth_error"
UNREACHABLE = "unreachable"
UNKNOWN = "unknown"
SKIPPED_NO_KEY = "skipped_no_key"
SKIPPED_DISABLED = "skipped_disabled"
SKIPPED_NO_MODEL = "skipped_no_model"

_FAILING = {DEAD}


def classify_retrieve(status: int) -> str:
    """Classify a single-model GET by HTTP status (pure)."""
    if status == 200:
        return OK
    if status == 404:
        return DEAD
    if status in (401, 403):
        return AUTH_ERROR
    return UNKNOWN


def classify_list(model: str, model_ids: list[str]) -> str:
    """Classify membership of ``model`` in a successfully fetched model list (pure).

    Presence confirms ``ok``. Absence is ``unknown`` (NOT ``dead``): OpenAI-compatible
    providers vary in list completeness/id format, so a missing id is not proof of
    retirement — only a clean single-model 404 (see ``classify_retrieve``) is.
    """
    if not model_ids:
        return UNKNOWN  # empty/unparseable list — don't claim dead
    return OK if model in model_ids else UNKNOWN


def _as_bool(value: Any, *, default: bool = True) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() not in {"0", "false", "no", "off", ""}
    if value is None:
        return default
    return bool(value)


def _resolve_api_key(config: ConfigManager, spec: dict[str, Any]) -> str:
    for env_key in spec["env_keys"]:
        value = str(os.environ.get(env_key, "") or "").strip()
        if value:
            return value
    cfg = config.get(spec["model_key"].rsplit(".", 1)[0] + ".api_key", "")
    return str(cfg or "").strip()


def _extract_model_ids(body: Any) -> list[str]:
    if not isinstance(body, dict):
        return []
    data = body.get("data")
    if not isinstance(data, list):
        return []
    ids: list[str] = []
    for item in data:
        if isinstance(item, dict) and item.get("id"):
            ids.append(str(item["id"]))
    return ids


def check_provider(spec: dict[str, Any], model: str, api_key: str, *, http_get: HttpGet) -> str:
    """Return an availability status for one provider's model using ``http_get``."""
    if not api_key:
        return SKIPPED_NO_KEY
    if not model:
        return SKIPPED_NO_MODEL

    provider = spec["provider"]
    try:
        if spec["method"] == "retrieve":
            if provider == "anthropic":
                url = f"https://api.anthropic.com/v1/models/{model}"
                headers = {"x-api-key": api_key, "anthropic-version": "2023-06-01"}
                params = None
            elif provider == "gemini":
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}"
                headers = {}
                params = {"key": api_key}
            else:  # openai
                url = f"https://api.openai.com/v1/models/{model}"
                headers = {"Authorization": f"Bearer {api_key}"}
                params = None
            status, _ = http_get(url, headers=headers, params=params)
            return classify_retrieve(status)

        # OpenAI-compatible model list
        base = OPENAI_COMPATIBLE_BASE_URLS[provider].rstrip("/")
        status, body = http_get(f"{base}/models", headers={"Authorization": f"Bearer {api_key}"}, params=None)
        if status in (401, 403):
            return AUTH_ERROR
        if status != 200:
            return UNKNOWN
        return classify_list(model, _extract_model_ids(body))
    except Exception:
        return UNREACHABLE


def build_report(config: ConfigManager, *, http_get: HttpGet) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    for spec in PROVIDER_SPECS:
        provider = spec["provider"]
        enabled = _as_bool(config.get(spec["enabled_key"], None))
        if provider == "openai" and config.get(spec["enabled_key"], None) is None:
            enabled = _as_bool(config.get("openai.enabled", None))
        model = str(config.get(spec["model_key"], "") or "").strip()
        if not enabled:
            status = SKIPPED_DISABLED
        else:
            status = check_provider(spec, model, _resolve_api_key(config, spec), http_get=http_get)
        checks.append(
            {
                "provider": provider,
                "enabled": enabled,
                "model": model,
                "status": status,
                "severity": "fail" if status in _FAILING else ("ok" if status == OK else "warning"),
            }
        )

    dead = [c for c in checks if c["status"] == DEAD]
    return {
        "ok": not dead,
        "status": "FAIL" if dead else "PASS",
        "dead_models": [{"provider": c["provider"], "model": c["model"]} for c in dead],
        "operator_action_required": bool(dead),
        "checks": checks,
    }


def _httpx_get(url: str, *, headers: dict | None = None, params: dict | None = None) -> tuple[int, Any]:
    import httpx

    resp = httpx.get(url, headers=headers or {}, params=params or {}, timeout=15)
    try:
        body = resp.json()
    except Exception:
        body = None
    return resp.status_code, body


def _print_text(payload: dict[str, Any]) -> None:
    print("[LLM MODEL DOCTOR]")
    print(f"  status: {payload['status']}")
    for c in payload["checks"]:
        print(f"  - {c['provider']:9s} {c['status']:16s} model={c['model'] or '(none)'} ({c['severity']})")
    if payload["dead_models"]:
        print("  DEAD models (retired/unavailable — update to a current model):")
        for d in payload["dead_models"]:
            print(f"    * {d['provider']}: {d['model']}")


def run(config_path: str, *, json_output: bool = False) -> int:
    load_env()
    config = ConfigManager(config_path)
    payload = build_report(config, http_get=_httpx_get)
    if json_output:
        print(json.dumps(payload, ensure_ascii=True, sort_keys=True))
    else:
        _print_text(payload)
    return 0 if payload["ok"] else 2


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Diagnose LLM provider model availability for blind-to-x.")
    parser.add_argument("--config", default="config.yaml", help="Path to config file")
    parser.add_argument("--json", action="store_true", help="Print a structured JSON report")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        return run(args.config, json_output=args.json)
    except Exception as exc:  # pragma: no cover - defensive top-level guard
        print(f"[LLM MODEL DOCTOR] error: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
