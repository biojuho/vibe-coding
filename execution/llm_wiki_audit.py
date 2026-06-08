"""Audit the LLM wiki for local link, index, and source-freshness hygiene.

The LLM wiki mixes repo facts with fast-moving provider/security references.
This script intentionally does not fetch external URLs. It checks the
deterministic parts that should be true before a human or agent trusts the
wiki: every local markdown link resolves, every numbered page is indexed from
README, and pages that cite external URLs carry source evidence plus a
verification date.

Usage:
    py -3.13 execution/llm_wiki_audit.py --json
    py -3.13 execution/llm_wiki_audit.py --today 2026-06-08
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from dataclasses import dataclass, asdict
from datetime import date, timedelta
from pathlib import Path
from typing import Iterable
from urllib.parse import unquote, urlparse

import yaml


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


REPO_ROOT_DEFAULT = Path(__file__).resolve().parents[1]
WIKI_DIR_DEFAULT = Path("docs/wiki/llm")
SOURCE_INVENTORY_NAME = "source-inventory.json"
SOURCE_INVENTORY_SCHEMA_VERSION = 1
CODE_FACTS_NAME = "code-facts.json"
CODE_FACTS_SCHEMA_VERSION = 1
CONFIG_FACTS_NAME = "config-facts.json"
CONFIG_FACTS_SCHEMA_VERSION = 1
STRICT_RELEASE_EVIDENCE_SCHEMA_VERSION = 1
STRICT_RELEASE_EVIDENCE_DEFAULT = Path(".tmp/llm-wiki-strict-audit-current.json")
ACCEPTED_MANIFEST_WARNING_IDS = {
    "blind_to_x_config_example_runtime_helpers": {
        "classification": "accepted_known",
        "reason": "Accepted current blind-to-x config/runtime wiring debt; see docs/wiki/llm/18-runtime-wiring-checks.md.",
    },
    "blind_to_x_config_ci_runtime_helpers": {
        "classification": "accepted_known",
        "reason": "Accepted current blind-to-x config/runtime wiring debt; see docs/wiki/llm/18-runtime-wiring-checks.md.",
    },
}

FENCED_CODE_RE = re.compile(r"```.*?```", re.DOTALL)
MARKDOWN_LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
EXTERNAL_URL_RE = re.compile(r"https?://[^\s<>)]+")
VERIFY_DATE_RE = re.compile(r"외부 자료 검증일:\s*(\d{4}-\d{2}-\d{2})")
SOURCE_HEADING_RE = re.compile(r"^##\s+출처\b", re.MULTILINE)
OFFICIAL_SOURCE_RE = re.compile(r"공식\s*:", re.MULTILINE)
NUMBERED_PAGE_RE = re.compile(r"^\d{2}-.+\.md$")
README_INDEX_LINK_RE = re.compile(r"\]\((\d{2}-.+?\.md)(?:#[^)]+)?\)")

IGNORED_URL_PREFIXES = (
    "http://127.0.0.1",
    "http://localhost",
    "https://localhost",
)
SOURCE_TYPES = {
    "code-config",
    "official-blog",
    "official-docs",
    "official-pricing",
    "official-rate-limit",
    "paper",
    "provider-console",
    "standard",
}
VOLATILITY_CADENCE_DAYS = {
    "high": 45,
    "medium": 90,
    "low": 180,
}

CODE_FACT_TARGETS = (
    {
        "id": "workspace_llm_client",
        "path": "workspace/execution/llm_client.py",
        "constants": (
            "PROVIDER_ALIASES",
            "DEFAULT_PROVIDER_ORDER",
            "DEFAULT_MODELS",
            "OPENAI_COMPATIBLE_BASE_URLS",
            "API_KEY_ENV_VARS",
            "PRICING",
        ),
    },
    {
        "id": "shorts_llm_router",
        "path": "projects/shorts-maker-v2/src/shorts_maker_v2/providers/llm_router.py",
        "constants": (
            "PROVIDER_ALIASES",
            "DEFAULT_MODELS",
            "OPENAI_COMPATIBLE_BASE_URLS",
        ),
    },
    {
        "id": "blind_to_x_draft_providers",
        "path": "projects/blind-to-x/pipeline/draft_providers.py",
        "constants": (
            "PROVIDER_ALIASES",
            "DEFAULT_PROVIDER_ORDER",
        ),
    },
)

CODE_FACT_MARKERS = (
    "LLMClient",
    "LLMRouter",
    "DEFAULT_MODELS",
    "DEFAULT_PROVIDER_ORDER",
    "draft_providers.py",
    "llm_client.py",
    "llm_router.py",
)

CONFIG_FACT_TARGETS = (
    {
        "id": "shorts_maker_v2_config",
        "project": "shorts-maker-v2",
        "path": "projects/shorts-maker-v2/config.yaml",
        "kind": "shorts_maker_v2",
    },
    {
        "id": "blind_to_x_config_example",
        "project": "blind-to-x",
        "path": "projects/blind-to-x/config.example.yaml",
        "kind": "blind_to_x",
    },
    {
        "id": "blind_to_x_config_ci",
        "project": "blind-to-x",
        "path": "projects/blind-to-x/config.ci.yaml",
        "kind": "blind_to_x",
    },
)

CONFIG_FACT_MARKERS = (
    "config.yaml",
    "config.example.yaml",
    "config.ci.yaml",
    "llm_providers",
    "config-facts.json",
)
RELEASE_SUMMARY_TRIGGER_MARKERS = (
    "llm_wiki_strict_evidence",
    "llm_wiki_release_summary.py",
    "GITHUB_STEP_SUMMARY",
    "release-evidence/llm-wiki",
    "actions/upload-artifact",
)
RELEASE_SUMMARY_REQUIRED_MARKERS = {
    "llm_wiki_release_summary.py": "release_summary_helper_missing",
    "GITHUB_STEP_SUMMARY": "release_summary_step_summary_missing",
    "release-evidence/llm-wiki": "release_summary_visible_artifact_missing",
    "actions/upload-artifact@v7": "release_summary_upload_artifact_action_missing",
}
STALE_UPLOAD_ARTIFACT_RE = re.compile(r"actions/upload-artifact@v([1-6])(?:\b|[^\d])")
HIDDEN_TMP_ARTIFACT_PATH_RE = re.compile(r"(?im)^\s*path:\s*['\"]?\.tmp(?:[/\\\s'\"#]|$)")
MANUAL_STEP_SUMMARY_ECHO_RE = re.compile(
    r"(?im)^\s*(?:-\s*run:\s*)?(?:echo|printf|Add-Content|Out-File)\b[^\n]*GITHUB_STEP_SUMMARY"
)


@dataclass(frozen=True)
class Issue:
    severity: str
    code: str
    path: str
    message: str


def _strip_fenced_code(text: str) -> str:
    return FENCED_CODE_RE.sub("", text)


def _repo_rel(repo_root: Path, path: Path) -> str:
    try:
        return path.relative_to(repo_root).as_posix()
    except ValueError:
        return path.as_posix()


def _repo_output_path(repo_root: Path, path: Path) -> Path:
    return path if path.is_absolute() else repo_root / path


def _current_git_head(repo_root: Path) -> str | None:
    head_path = repo_root / ".git" / "HEAD"
    try:
        head_value = head_path.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if not head_value:
        return None
    if not head_value.startswith("ref: "):
        return head_value
    ref_path = repo_root / ".git" / head_value.removeprefix("ref: ").strip()
    try:
        ref_value = ref_path.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return ref_value or None


def _summary_int(summary: dict, key: str) -> int:
    try:
        return int(summary.get(key, 0) or 0)
    except (TypeError, ValueError):
        return 0


def _read_text(path: Path) -> tuple[str, str | None]:
    try:
        return path.read_text(encoding="utf-8"), None
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace"), "invalid UTF-8 bytes replaced"
    except OSError as exc:
        return "", str(exc)


def _read_json(path: Path, *, root_label: str = "source inventory root") -> tuple[dict, str | None]:
    text, error = _read_text(path)
    if error:
        return {}, error
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        return {}, f"invalid JSON: {exc}"
    if not isinstance(data, dict):
        return {}, f"{root_label} must be a JSON object"
    return data, None


def _read_yaml(path: Path) -> tuple[dict, str | None]:
    text, error = _read_text(path)
    if error:
        return {}, error
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        return {}, f"invalid YAML: {exc}"
    if data is None:
        return {}, None
    if not isinstance(data, dict):
        return {}, "config root must be a mapping"
    return data, None


def _normalize_markdown_target(raw: str) -> str | None:
    target = raw.strip()
    if not target or target.startswith("#"):
        return None
    if target.startswith(("http://", "https://", "mailto:", "app://", "plugin://")):
        return None

    # Drop optional markdown title: [x](path.md "title")
    if " " in target:
        target = target.split(" ", 1)[0]
    target = target.strip("<>").strip()
    if not target:
        return None
    return unquote(target.split("#", 1)[0])


def _candidate_local_paths(repo_root: Path, source_file: Path, target: str) -> list[Path]:
    clean = target.replace("\\", "/")
    if clean.startswith("/"):
        return [repo_root / clean.lstrip("/")]
    return [source_file.parent / clean]


def _iter_markdown_files(wiki_dir: Path) -> list[Path]:
    return sorted(path for path in wiki_dir.glob("*.md") if path.is_file())


def _external_urls(text: str) -> list[str]:
    stripped = _strip_fenced_code(text)
    urls = [url.rstrip(".,;:!?`'\"") for url in EXTERNAL_URL_RE.findall(stripped)]
    return [url for url in urls if not url.startswith(IGNORED_URL_PREFIXES)]


def _url_host(url: str) -> str:
    return urlparse(url).netloc.lower()


def _verified_date(text: str) -> date | None:
    match = VERIFY_DATE_RE.search(text)
    if not match:
        return None
    try:
        return date.fromisoformat(match.group(1))
    except ValueError:
        return None


def _has_source_evidence(text: str) -> bool:
    return bool(SOURCE_HEADING_RE.search(text) or OFFICIAL_SOURCE_RE.search(text))


def _source_type_for(url: str) -> str:
    host = _url_host(url)
    parsed_path = urlparse(url).path.lower()
    lower_url = url.lower()

    if host == "api.xiaomimimo.com":
        return "code-config"
    if host in {"ceur-ws.org"} or parsed_path.endswith(".pdf"):
        return "paper"
    if "owasp.org" in host:
        return "standard"
    if host == "aistudio.google.com":
        return "provider-console"
    if "/pricing" in parsed_path or "pricing" in lower_url:
        return "official-pricing"
    if "rate-limit" in lower_url or "/limits" in parsed_path:
        return "official-rate-limit"
    if host in {"openai.com", "www.anthropic.com"} or "/news/" in parsed_path:
        return "official-blog"
    return "official-docs"


def _volatility_for(url: str, pages: Iterable[str]) -> str:
    page_names = set(pages)
    lower_url = url.lower()
    if (
        "02-providers.md" in page_names
        or "13-model-selection.md" in page_names
        or "pricing" in lower_url
        or "rate-limit" in lower_url
        or "models" in lower_url
        or "deprecation" in lower_url
        or "/news/" in lower_url
    ):
        return "high"
    if (
        "10-structured-outputs.md" in page_names
        or "11-reasoning-models.md" in page_names
        or "09-agent-harness.md" in page_names
        or "15-source-inventory.md" in page_names
    ):
        return "medium"
    return "low"


def _topic_for(pages: Iterable[str]) -> str:
    page_names = set(pages)
    if "02-providers.md" in page_names:
        return "provider-models-pricing-limits"
    if "13-model-selection.md" in page_names:
        return "model-lifecycle"
    if "10-structured-outputs.md" in page_names:
        return "structured-outputs"
    if "11-reasoning-models.md" in page_names:
        return "reasoning"
    if "09-agent-harness.md" in page_names:
        return "agent-harness"
    if "08-security.md" in page_names:
        return "security"
    if "15-source-inventory.md" in page_names:
        return "wiki-maintenance"
    return "wiki-maintenance"


def _collect_source_refs(repo_root: Path, markdown_files: Iterable[Path]) -> dict[str, dict]:
    refs: dict[str, dict] = {}
    for path in markdown_files:
        text, error = _read_text(path)
        if error:
            continue
        page = path.name
        checked = _verified_date(text)
        for url in _external_urls(text):
            item = refs.setdefault(url, {"url": url, "pages": set(), "verified_dates": []})
            item["pages"].add(page)
            if checked is not None:
                item["verified_dates"].append(checked)
    for item in refs.values():
        item["pages"] = sorted(item["pages"])
    return refs


def _json_safe_literal(value):
    if value is None or isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, tuple | list):
        return [_json_safe_literal(item) for item in value]
    if isinstance(value, set):
        return [_json_safe_literal(item) for item in sorted(value, key=repr)]
    if isinstance(value, dict):
        return {str(key): _json_safe_literal(item) for key, item in value.items()}
    return repr(value)


def _literal_assignments(tree: ast.Module) -> tuple[dict[str, object], dict[str, int]]:
    constants: dict[str, object] = {}
    line_numbers: dict[str, int] = {}
    for statement in tree.body:
        names: list[str] = []
        value_node: ast.AST | None = None
        if isinstance(statement, ast.Assign):
            value_node = statement.value
            names = [target.id for target in statement.targets if isinstance(target, ast.Name)]
        elif isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name):
            value_node = statement.value
            names = [statement.target.id]
        if value_node is None:
            continue
        try:
            value = _json_safe_literal(ast.literal_eval(value_node))
        except (ValueError, SyntaxError):
            continue
        for name in names:
            constants[name] = value
            line_numbers[name] = getattr(statement, "lineno", 0)
    return constants, line_numbers


def _function_names(tree: ast.Module) -> list[str]:
    return sorted(
        statement.name for statement in tree.body if isinstance(statement, ast.FunctionDef | ast.AsyncFunctionDef)
    )


def _class_methods(tree: ast.Module) -> dict[str, list[str]]:
    classes: dict[str, list[str]] = {}
    for statement in tree.body:
        if not isinstance(statement, ast.ClassDef):
            continue
        classes[statement.name] = sorted(
            item.name for item in statement.body if isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef)
        )
    return classes


def _generation_helper_providers(tree: ast.Module) -> list[str]:
    names = set(_function_names(tree))
    for methods in _class_methods(tree).values():
        names.update(methods)
    return sorted(name.removeprefix("_generate_with_") for name in names if name.startswith("_generate_with_"))


def _self_assignment_expression(tree: ast.Module, class_name: str, attribute_name: str) -> str | None:
    for statement in tree.body:
        if not isinstance(statement, ast.ClassDef) or statement.name != class_name:
            continue
        init_method = next(
            (
                item
                for item in statement.body
                if isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef) and item.name == "__init__"
            ),
            None,
        )
        if init_method is None:
            return None
        for child in ast.walk(init_method):
            if not isinstance(child, ast.Assign):
                continue
            for target in child.targets:
                if (
                    isinstance(target, ast.Attribute)
                    and target.attr == attribute_name
                    and isinstance(target.value, ast.Name)
                    and target.value.id == "self"
                ):
                    try:
                        return ast.unparse(child.value)
                    except Exception:  # pragma: no cover - ast.unparse is expected on supported Python.
                        return None
    return None


def _derive_code_facts(target_id: str, tree: ast.Module, constants: dict[str, object]) -> dict:
    derived: dict[str, object] = {}
    default_order = constants.get("DEFAULT_PROVIDER_ORDER")
    if isinstance(default_order, list):
        derived["default_provider_order"] = default_order
        derived["default_provider_count"] = len(default_order)

    default_models = constants.get("DEFAULT_MODELS")
    if isinstance(default_models, dict):
        derived["default_model_providers"] = sorted(default_models)
        derived["default_model_count"] = len(default_models)

    aliases = constants.get("PROVIDER_ALIASES")
    if isinstance(aliases, dict):
        derived["alias_count"] = len(aliases)
        derived["alias_canonical_providers"] = sorted({str(value) for value in aliases.values()})

    compatible_urls = constants.get("OPENAI_COMPATIBLE_BASE_URLS")
    if isinstance(compatible_urls, dict):
        derived["openai_compatible_providers"] = sorted(compatible_urls)

    api_key_env_vars = constants.get("API_KEY_ENV_VARS")
    if isinstance(api_key_env_vars, dict):
        derived["api_key_providers"] = sorted(api_key_env_vars)

    pricing = constants.get("PRICING")
    if isinstance(pricing, dict):
        derived["pricing_models"] = sorted(pricing)

    helper_providers = _generation_helper_providers(tree)
    if helper_providers:
        derived["generation_helper_providers"] = helper_providers
        if isinstance(default_order, list):
            derived["default_providers_without_generation_helper"] = sorted(
                provider for provider in default_order if provider not in helper_providers
            )
            derived["generation_helpers_outside_default_order"] = sorted(
                provider for provider in helper_providers if provider not in default_order
            )

    class_name = {
        "workspace_llm_client": "LLMClient",
        "shorts_llm_router": "LLMRouter",
    }.get(target_id)
    if class_name:
        providers_expr = _self_assignment_expression(tree, class_name, "providers")
        if providers_expr:
            derived["constructor_providers_expression"] = providers_expr
        models_expr = _self_assignment_expression(tree, class_name, "models")
        if models_expr:
            derived["constructor_models_expression"] = models_expr

    return derived


def _code_fact_for_target(repo_root: Path, target: dict) -> dict:
    rel_path = target["path"]
    path = repo_root / rel_path
    fact: dict[str, object] = {
        "id": target["id"],
        "path": rel_path,
        "requested_constants": list(target["constants"]),
    }
    if not path.exists():
        fact["status"] = "missing"
        return fact

    text, error = _read_text(path)
    if error:
        fact["status"] = "read_error"
        fact["error"] = error
        return fact
    try:
        tree = ast.parse(text, filename=rel_path)
    except SyntaxError as exc:
        fact["status"] = "syntax_error"
        fact["error"] = f"{exc.msg} at line {exc.lineno}"
        return fact

    assignments, line_numbers = _literal_assignments(tree)
    requested = set(target["constants"])
    constants = {name: assignments[name] for name in target["constants"] if name in assignments}
    fact.update(
        {
            "status": "ok",
            "constants": constants,
            "constant_lines": {name: line_numbers[name] for name in constants},
            "missing_constants": sorted(requested - set(constants)),
            "functions": _function_names(tree),
            "classes": _class_methods(tree),
            "derived": _derive_code_facts(target["id"], tree, constants),
        }
    )
    return fact


def _code_fact_checks(facts: list[dict]) -> list[dict]:
    checks: list[dict] = []
    for fact in facts:
        if fact.get("id") != "blind_to_x_draft_providers":
            continue
        derived = fact.get("derived")
        if not isinstance(derived, dict):
            continue
        missing_helpers = derived.get("default_providers_without_generation_helper", [])
        extra_helpers = derived.get("generation_helpers_outside_default_order", [])
        status = "pass" if not missing_helpers and not extra_helpers else "warning"
        checks.append(
            {
                "id": "blind_to_x_default_provider_helpers",
                "status": status,
                "message": (
                    "blind-to-x default provider order is covered by generation helpers."
                    if status == "pass"
                    else "blind-to-x default provider order and generation helpers differ."
                ),
                "missing_helpers": missing_helpers,
                "extra_helpers": extra_helpers,
            }
        )
    return checks


def build_code_facts(
    repo_root: Path,
    *,
    today: date | None = None,
) -> dict:
    repo_root = repo_root.resolve()
    today = today or date.today()
    facts = [_code_fact_for_target(repo_root, target) for target in CODE_FACT_TARGETS]
    return {
        "schema_version": CODE_FACTS_SCHEMA_VERSION,
        "generated_at": today.isoformat(),
        "policy": {
            "method": "Python AST parse plus ast.literal_eval for module-level literal constants.",
            "scope": "Provider aliases, fallback order, default models, pricing keys, API-key mappings, class methods, and generation helper names.",
            "non_goal": "This manifest does not prove that prose claims are semantically correct; it makes code drift visible before review.",
        },
        "facts": facts,
        "checks": _code_fact_checks(facts),
    }


def _stable_code_facts_payload(manifest: dict) -> dict:
    return {
        "schema_version": manifest.get("schema_version"),
        "facts": manifest.get("facts"),
        "checks": manifest.get("checks", []),
    }


def _wiki_mentions_code_facts(markdown_files: Iterable[Path]) -> bool:
    for path in markdown_files:
        text, error = _read_text(path)
        if error:
            continue
        if any(marker in text for marker in CODE_FACT_MARKERS):
            return True
    return False


def _string_list(value) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, str)]


def _string_dict(value) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    return {str(key): str(item) for key, item in value.items() if isinstance(item, str)}


def _extract_provider_sections(config: dict, providers: Iterable[str]) -> dict[str, dict]:
    sections: dict[str, dict] = {}
    for provider in providers:
        section = config.get(provider)
        if not isinstance(section, dict):
            continue
        provider_fact: dict[str, object] = {}
        for key in ("enabled", "chat_enabled", "model", "chat_model", "image_model"):
            value = section.get(key)
            if isinstance(value, bool | str | int | float) or value is None:
                provider_fact[key] = value
        sections[provider] = provider_fact
    return sections


def _config_fact_for_target(repo_root: Path, target: dict) -> dict:
    rel_path = target["path"]
    path = repo_root / rel_path
    fact: dict[str, object] = {
        "id": target["id"],
        "project": target["project"],
        "path": rel_path,
        "kind": target["kind"],
        "tracked_only": True,
    }
    if not path.exists():
        fact["status"] = "missing"
        return fact

    config, error = _read_yaml(path)
    if error:
        fact["status"] = "read_error"
        fact["error"] = error
        return fact

    if target["kind"] == "shorts_maker_v2":
        providers_config = config.get("providers", {})
        if not isinstance(providers_config, dict):
            providers_config = {}
        provider_order = _string_list(providers_config.get("llm_providers"))
        model_map = _string_dict(providers_config.get("llm_models"))
        fact.update(
            {
                "status": "ok",
                "facts": {
                    "providers.llm": providers_config.get("llm"),
                    "providers.llm_model": providers_config.get("llm_model"),
                    "providers.llm_providers": provider_order,
                    "providers.llm_models": model_map,
                },
                "derived": {
                    "provider_count": len(provider_order),
                    "model_provider_count": len(model_map),
                    "providers_without_model": sorted(
                        provider for provider in provider_order if provider not in model_map
                    ),
                    "models_without_provider": sorted(
                        provider for provider in model_map if provider not in provider_order
                    ),
                },
            }
        )
        return fact

    llm_config = config.get("llm", {})
    if not isinstance(llm_config, dict):
        llm_config = {}
    provider_order = _string_list(llm_config.get("providers"))
    pricing = llm_config.get("pricing")
    pricing_providers = sorted(str(key) for key in pricing) if isinstance(pricing, dict) else []
    provider_sections = _extract_provider_sections(config, provider_order)
    model_by_provider: dict[str, str] = {}
    for provider, section in provider_sections.items():
        model = section.get("model")
        if isinstance(model, str):
            model_by_provider[provider] = model
            continue
        chat_model = section.get("chat_model")
        if isinstance(chat_model, str):
            model_by_provider[provider] = chat_model
    fact.update(
        {
            "status": "ok",
            "facts": {
                "llm.strategy": llm_config.get("strategy"),
                "llm.providers": provider_order,
                "llm.max_retries_per_provider": llm_config.get("max_retries_per_provider"),
                "llm.request_timeout_seconds": llm_config.get("request_timeout_seconds"),
                "llm.pricing_providers": pricing_providers,
                "provider_sections": provider_sections,
            },
            "derived": {
                "provider_count": len(provider_order),
                "enabled_providers": sorted(
                    provider for provider, section in provider_sections.items() if section.get("enabled") is True
                ),
                "disabled_providers": sorted(
                    provider for provider, section in provider_sections.items() if section.get("enabled") is False
                ),
                "model_by_provider": model_by_provider,
                "providers_without_model": sorted(
                    provider for provider in provider_order if provider not in model_by_provider
                ),
                "pricing_without_provider": sorted(
                    provider for provider in pricing_providers if provider not in provider_order
                ),
                "providers_without_pricing": sorted(
                    provider for provider in provider_order if provider not in pricing_providers
                ),
            },
        }
    )
    return fact


def _config_fact_checks(facts: list[dict]) -> list[dict]:
    checks: list[dict] = []
    for fact in facts:
        if fact.get("status") != "ok":
            continue
        derived = fact.get("derived")
        if not isinstance(derived, dict):
            continue
        providers_without_model = derived.get("providers_without_model", [])
        models_without_provider = derived.get("models_without_provider", [])
        pricing_without_provider = derived.get("pricing_without_provider", [])
        providers_without_pricing = derived.get("providers_without_pricing", [])
        issues = {
            "providers_without_model": providers_without_model,
            "models_without_provider": models_without_provider,
            "pricing_without_provider": pricing_without_provider,
            "providers_without_pricing": providers_without_pricing,
        }
        status = "pass" if not any(issues.values()) else "warning"
        checks.append(
            {
                "id": f"{fact['id']}_coverage",
                "status": status,
                "message": (
                    "Tracked LLM config provider defaults have model/pricing coverage."
                    if status == "pass"
                    else "Tracked LLM config provider defaults have coverage gaps."
                ),
                **issues,
            }
        )
    return checks


def _fact_by_id(manifest: dict) -> dict[str, dict]:
    facts = manifest.get("facts")
    if not isinstance(facts, list):
        return {}
    return {str(fact.get("id")): fact for fact in facts if isinstance(fact, dict)}


def _list_from_path(item: dict, path: tuple[str, ...]) -> list[str]:
    current = item
    for key in path:
        if not isinstance(current, dict):
            return []
        current = current.get(key)
    return _string_list(current)


def _runtime_provider_checks(config_facts: list[dict], code_manifest: dict) -> list[dict]:
    code_by_id = _fact_by_id(code_manifest)
    checks: list[dict] = []

    for fact in config_facts:
        if fact.get("status") != "ok":
            continue

        fact_id = fact.get("id")
        if fact_id == "shorts_maker_v2_config":
            config_providers = _list_from_path(fact, ("facts", "providers.llm_providers"))
            code_fact_id = "shorts_llm_router"
            code_fact = code_by_id.get(code_fact_id, {})
            runtime_providers = _list_from_path(code_fact, ("derived", "default_model_providers"))
            check_id = "shorts_maker_v2_config_runtime_models"
            runtime_label = "LLMRouter default models"
        elif fact_id in {"blind_to_x_config_example", "blind_to_x_config_ci"}:
            config_providers = _list_from_path(fact, ("facts", "llm.providers"))
            code_fact_id = "blind_to_x_draft_providers"
            code_fact = code_by_id.get(code_fact_id, {})
            runtime_providers = _list_from_path(code_fact, ("derived", "generation_helper_providers"))
            suffix = "example" if fact_id == "blind_to_x_config_example" else "ci"
            check_id = f"blind_to_x_config_{suffix}_runtime_helpers"
            runtime_label = "DraftProvidersMixin _generate_with_* helpers"
        else:
            continue

        if not config_providers or not runtime_providers:
            continue

        missing_runtime = sorted(provider for provider in config_providers if provider not in runtime_providers)
        runtime_outside_config = sorted(provider for provider in runtime_providers if provider not in config_providers)
        status = "pass" if not missing_runtime and not runtime_outside_config else "warning"
        check = {
            "id": check_id,
            "status": status,
            "message": (
                f"Tracked config providers match {runtime_label}."
                if status == "pass"
                else f"Tracked config providers and {runtime_label} differ."
            ),
            "config_fact_id": str(fact_id),
            "code_fact_id": code_fact_id,
            "config_providers": config_providers,
            "runtime_providers": runtime_providers,
            "missing_runtime_providers": missing_runtime,
            "runtime_providers_outside_config": runtime_outside_config,
        }
        accepted_warning = ACCEPTED_MANIFEST_WARNING_IDS.get(check_id)
        if status == "warning" and accepted_warning:
            check["warning_classification"] = accepted_warning["classification"]
            check["accepted_reason"] = accepted_warning["reason"]
        checks.append(check)

    return checks


def build_config_facts(
    repo_root: Path,
    *,
    today: date | None = None,
) -> dict:
    repo_root = repo_root.resolve()
    today = today or date.today()
    facts = [_config_fact_for_target(repo_root, target) for target in CONFIG_FACT_TARGETS]
    code_manifest = build_code_facts(repo_root, today=today)
    return {
        "schema_version": CONFIG_FACTS_SCHEMA_VERSION,
        "generated_at": today.isoformat(),
        "policy": {
            "method": "PyYAML yaml.safe_load on tracked YAML config files, then explicit extraction of LLM provider/model defaults.",
            "scope": "Tracked config files only. Secret-bearing local projects/blind-to-x/config.yaml is intentionally excluded.",
            "non_goal": "This manifest records runtime wiring gaps as checks, but it does not prove live provider credentials or API responses work.",
        },
        "facts": facts,
        "checks": [*_config_fact_checks(facts), *_runtime_provider_checks(facts, code_manifest)],
    }


def _stable_config_facts_payload(manifest: dict) -> dict:
    return {
        "schema_version": manifest.get("schema_version"),
        "facts": manifest.get("facts"),
        "checks": manifest.get("checks", []),
    }


def _wiki_mentions_config_facts(markdown_files: Iterable[Path]) -> bool:
    for path in markdown_files:
        text, error = _read_text(path)
        if error:
            continue
        if any(marker in text for marker in CONFIG_FACT_MARKERS):
            return True
    return False


def _manifest_check_summary(manifest: dict, *, manifest_name: str) -> dict:
    checks = manifest.get("checks", [])
    if not isinstance(checks, list):
        checks = []

    status_counts = {
        "pass": 0,
        "warning": 0,
        "fail": 0,
        "error": 0,
        "unknown": 0,
    }
    warnings: list[dict] = []
    warning_classification_counts = {
        "accepted_known": 0,
        "unexpected": 0,
    }
    check_count = 0

    for check in checks:
        if not isinstance(check, dict):
            continue
        check_count += 1
        raw_status = check.get("status")
        status = raw_status if isinstance(raw_status, str) and raw_status else "unknown"
        if status not in status_counts:
            status_counts[status] = 0
        status_counts[status] += 1
        if status != "warning":
            continue

        warning = {
            "manifest": manifest_name,
            "id": str(check.get("id", "")),
            "message": str(check.get("message", "")),
        }
        classification = check.get("warning_classification")
        if classification != "accepted_known":
            classification = "unexpected"
        warning["classification"] = classification
        warning_classification_counts[classification] = warning_classification_counts.get(classification, 0) + 1
        if check.get("accepted_reason"):
            warning["accepted_reason"] = str(check["accepted_reason"])
        if check.get("missing_runtime_providers"):
            warning["missing_runtime_providers"] = check["missing_runtime_providers"]
        if check.get("runtime_providers_outside_config"):
            warning["runtime_providers_outside_config"] = check["runtime_providers_outside_config"]
        warnings.append(warning)

    return {
        "check_count": check_count,
        "status_counts": status_counts,
        "warning_count": len(warnings),
        "warning_classification_counts": warning_classification_counts,
        "warnings": warnings,
    }


def _format_manifest_warning(warning: dict) -> str:
    classification = str(warning.get("classification") or "unexpected")
    line = (
        f"- [manifest-warning:{classification}] "
        f"{warning.get('manifest', '')}: {warning.get('id', '')} - {warning.get('message', '')}"
    )
    details: list[str] = []
    missing_runtime = warning.get("missing_runtime_providers")
    if isinstance(missing_runtime, list) and missing_runtime:
        details.append(f"missing runtime: {', '.join(str(item) for item in missing_runtime)}")
    runtime_outside_config = warning.get("runtime_providers_outside_config")
    if isinstance(runtime_outside_config, list) and runtime_outside_config:
        details.append(f"runtime outside config: {', '.join(str(item) for item in runtime_outside_config)}")
    if details:
        line = f"{line} ({'; '.join(details)})"
    return line


def build_source_inventory(
    repo_root: Path,
    *,
    wiki_dir: Path = WIKI_DIR_DEFAULT,
    today: date | None = None,
) -> dict:
    repo_root = repo_root.resolve()
    if not wiki_dir.is_absolute():
        wiki_dir = repo_root / wiki_dir
    wiki_dir = wiki_dir.resolve()
    today = today or date.today()

    pages = _iter_markdown_files(wiki_dir)
    refs = _collect_source_refs(repo_root, pages)
    sources: list[dict] = []
    for url in sorted(refs):
        ref = refs[url]
        source_pages = ref["pages"]
        checked_dates = ref["verified_dates"]
        last_verified = min(checked_dates) if checked_dates else today
        volatility = _volatility_for(url, source_pages)
        cadence_days = VOLATILITY_CADENCE_DAYS[volatility]
        sources.append(
            {
                "url": url,
                "host": _url_host(url),
                "pages": source_pages,
                "topic": _topic_for(source_pages),
                "source_type": _source_type_for(url),
                "volatility": volatility,
                "cadence_days": cadence_days,
                "last_verified": last_verified.isoformat(),
                "review_after": (last_verified + timedelta(days=cadence_days)).isoformat(),
                "notes": "Generated from docs/wiki/llm markdown links; revalidate the source before updating time-sensitive claims.",
            }
        )

    return {
        "schema_version": SOURCE_INVENTORY_SCHEMA_VERSION,
        "generated_at": today.isoformat(),
        "wiki_dir": _repo_rel(repo_root, wiki_dir),
        "policy": {
            "high_volatility_days": VOLATILITY_CADENCE_DAYS["high"],
            "medium_volatility_days": VOLATILITY_CADENCE_DAYS["medium"],
            "low_volatility_days": VOLATILITY_CADENCE_DAYS["low"],
            "source_priority": "official docs and standards first; papers or blogs only when they are the primary source for the claim.",
        },
        "sources": sources,
    }


def _audit_readme_index(repo_root: Path, wiki_dir: Path, pages: Iterable[Path]) -> list[Issue]:
    readme = wiki_dir / "README.md"
    issues: list[Issue] = []
    if not readme.exists():
        return [
            Issue(
                severity="error",
                code="missing_readme",
                path=_repo_rel(repo_root, readme),
                message="LLM wiki README.md is required.",
            )
        ]

    text, error = _read_text(readme)
    if error:
        issues.append(
            Issue(
                severity="warning",
                code="read_error",
                path=_repo_rel(repo_root, readme),
                message=error,
            )
        )

    indexed = set(README_INDEX_LINK_RE.findall(text))
    numbered_pages = {path.name for path in pages if NUMBERED_PAGE_RE.match(path.name)}
    for page_name in sorted(numbered_pages - indexed):
        issues.append(
            Issue(
                severity="error",
                code="missing_readme_index",
                path=_repo_rel(repo_root, readme),
                message=f"{page_name} exists but is not linked from the README index.",
            )
        )
    return issues


def _audit_local_links(repo_root: Path, markdown_files: Iterable[Path]) -> list[Issue]:
    issues: list[Issue] = []
    for path in markdown_files:
        text, error = _read_text(path)
        rel = _repo_rel(repo_root, path)
        if error:
            issues.append(Issue("warning", "read_error", rel, error))

        body = _strip_fenced_code(text)
        for raw_target in MARKDOWN_LINK_RE.findall(body):
            target = _normalize_markdown_target(raw_target)
            if target is None:
                continue
            if any(candidate.exists() for candidate in _candidate_local_paths(repo_root, path, target)):
                continue
            issues.append(
                Issue(
                    severity="error",
                    code="broken_local_link",
                    path=rel,
                    message=f"Local markdown link does not resolve: {raw_target}",
                )
            )
    return issues


def _audit_release_summary_contract(repo_root: Path, markdown_files: Iterable[Path]) -> list[Issue]:
    docs: list[tuple[Path, str]] = []
    for path in markdown_files:
        text, error = _read_text(path)
        if error:
            continue
        if any(marker in text for marker in RELEASE_SUMMARY_TRIGGER_MARKERS):
            docs.append((path, text))

    if not docs:
        return []

    issues: list[Issue] = []
    combined = "\n".join(text for _, text in docs)
    primary_path = _repo_rel(repo_root, docs[0][0])
    for marker, code in RELEASE_SUMMARY_REQUIRED_MARKERS.items():
        if marker not in combined:
            issues.append(
                Issue(
                    severity="error",
                    code=code,
                    path=primary_path,
                    message=f"Release-summary workflow docs must mention `{marker}`.",
                )
            )

    for path, text in docs:
        rel = _repo_rel(repo_root, path)
        stale_versions = sorted({f"v{match.group(1)}" for match in STALE_UPLOAD_ARTIFACT_RE.finditer(text)})
        if stale_versions:
            issues.append(
                Issue(
                    severity="error",
                    code="release_summary_stale_upload_artifact_action",
                    path=rel,
                    message=(
                        "Release-summary workflow docs must use actions/upload-artifact@v7, "
                        f"not {', '.join(stale_versions)}."
                    ),
                )
            )
        if HIDDEN_TMP_ARTIFACT_PATH_RE.search(text):
            issues.append(
                Issue(
                    severity="error",
                    code="release_summary_hidden_tmp_artifact_upload",
                    path=rel,
                    message="Upload examples must use visible `release-evidence/llm-wiki`, not direct `.tmp` paths.",
                )
            )
        if MANUAL_STEP_SUMMARY_ECHO_RE.search(text):
            issues.append(
                Issue(
                    severity="error",
                    code="release_summary_manual_step_summary_echo",
                    path=rel,
                    message=(
                        "Release-summary docs must use `llm_wiki_release_summary.py` instead of manual "
                        "`GITHUB_STEP_SUMMARY` shell echoing."
                    ),
                )
            )
    return issues


def _release_summary_contract_status(markdown_files: Iterable[Path], issues: list[Issue]) -> str:
    for path in markdown_files:
        text, error = _read_text(path)
        if error:
            continue
        if any(marker in text for marker in RELEASE_SUMMARY_TRIGGER_MARKERS):
            return "fail" if issues else "pass"
    return "not_applicable"


def _audit_source_inventory(
    repo_root: Path,
    wiki_dir: Path,
    markdown_files: Iterable[Path],
    *,
    today: date,
) -> list[Issue]:
    issues: list[Issue] = []
    refs = _collect_source_refs(repo_root, markdown_files)
    actual_urls = set(refs)
    manifest_path = wiki_dir / SOURCE_INVENTORY_NAME
    rel_manifest = _repo_rel(repo_root, manifest_path)

    if actual_urls and not manifest_path.exists():
        return [
            Issue(
                severity="error",
                code="missing_source_inventory",
                path=rel_manifest,
                message=f"{SOURCE_INVENTORY_NAME} is required when the LLM wiki contains external URLs.",
            )
        ]
    if not manifest_path.exists():
        return issues

    manifest, error = _read_json(manifest_path)
    if error:
        return [
            Issue(
                severity="error",
                code="invalid_source_inventory",
                path=rel_manifest,
                message=error,
            )
        ]

    if manifest.get("schema_version") != SOURCE_INVENTORY_SCHEMA_VERSION:
        issues.append(
            Issue(
                severity="error",
                code="source_inventory_schema_mismatch",
                path=rel_manifest,
                message=f"Expected schema_version {SOURCE_INVENTORY_SCHEMA_VERSION}.",
            )
        )

    sources = manifest.get("sources")
    if not isinstance(sources, list):
        return [
            *issues,
            Issue(
                severity="error",
                code="invalid_source_inventory",
                path=rel_manifest,
                message="sources must be a list.",
            ),
        ]

    manifest_sources: dict[str, dict] = {}
    for index, entry in enumerate(sources):
        if not isinstance(entry, dict):
            issues.append(
                Issue("error", "invalid_source_inventory_entry", rel_manifest, f"sources[{index}] must be an object.")
            )
            continue
        url = entry.get("url")
        if not isinstance(url, str) or not url.startswith(("http://", "https://")):
            issues.append(
                Issue("error", "invalid_source_inventory_entry", rel_manifest, f"sources[{index}] has invalid url.")
            )
            continue
        if url in manifest_sources:
            issues.append(Issue("error", "duplicate_source_inventory_url", rel_manifest, f"Duplicate URL: {url}"))
        manifest_sources[url] = entry

    manifest_urls = set(manifest_sources)
    for url in sorted(actual_urls - manifest_urls):
        issues.append(
            Issue(
                severity="error",
                code="source_inventory_missing_url",
                path=rel_manifest,
                message=f"External URL is used in markdown but missing from source inventory: {url}",
            )
        )
    for url in sorted(manifest_urls - actual_urls):
        issues.append(
            Issue(
                severity="error",
                code="source_inventory_stale_url",
                path=rel_manifest,
                message=f"Source inventory URL is no longer used in markdown: {url}",
            )
        )

    for url in sorted(manifest_urls & actual_urls):
        entry = manifest_sources[url]
        pages = entry.get("pages")
        expected_pages = refs[url]["pages"]
        if pages != expected_pages:
            issues.append(
                Issue(
                    severity="error",
                    code="source_inventory_page_mismatch",
                    path=rel_manifest,
                    message=f"{url} pages are {pages!r}; expected {expected_pages!r}.",
                )
            )

        source_type = entry.get("source_type")
        if source_type not in SOURCE_TYPES:
            issues.append(
                Issue(
                    severity="error",
                    code="invalid_source_type",
                    path=rel_manifest,
                    message=f"{url} has invalid source_type {source_type!r}.",
                )
            )

        volatility = entry.get("volatility")
        if volatility not in VOLATILITY_CADENCE_DAYS:
            issues.append(
                Issue(
                    severity="error",
                    code="invalid_source_volatility",
                    path=rel_manifest,
                    message=f"{url} has invalid volatility {volatility!r}.",
                )
            )

        try:
            last_verified = date.fromisoformat(str(entry.get("last_verified")))
        except ValueError:
            issues.append(
                Issue(
                    severity="error",
                    code="invalid_source_last_verified",
                    path=rel_manifest,
                    message=f"{url} has invalid last_verified {entry.get('last_verified')!r}.",
                )
            )
            last_verified = None

        try:
            review_after = date.fromisoformat(str(entry.get("review_after")))
        except ValueError:
            issues.append(
                Issue(
                    severity="error",
                    code="invalid_source_review_after",
                    path=rel_manifest,
                    message=f"{url} has invalid review_after {entry.get('review_after')!r}.",
                )
            )
            review_after = None

        if last_verified is not None and review_after is not None and review_after < last_verified:
            issues.append(
                Issue(
                    severity="error",
                    code="invalid_source_review_after",
                    path=rel_manifest,
                    message=f"{url} review_after is before last_verified.",
                )
            )
        if review_after is not None and today > review_after:
            issues.append(
                Issue(
                    severity="error",
                    code="source_review_due",
                    path=rel_manifest,
                    message=f"{url} review_after {review_after.isoformat()} is past due.",
                )
            )

    return issues


def _audit_code_facts(
    repo_root: Path,
    wiki_dir: Path,
    markdown_files: Iterable[Path],
    *,
    today: date,
) -> list[Issue]:
    issues: list[Issue] = []
    manifest_path = wiki_dir / CODE_FACTS_NAME
    rel_manifest = _repo_rel(repo_root, manifest_path)

    if _wiki_mentions_code_facts(markdown_files) and not manifest_path.exists():
        return [
            Issue(
                severity="error",
                code="missing_code_facts",
                path=rel_manifest,
                message=f"{CODE_FACTS_NAME} is required when the LLM wiki references code facts.",
            )
        ]
    if not manifest_path.exists():
        return issues

    manifest, error = _read_json(manifest_path, root_label="code facts root")
    if error:
        return [
            Issue(
                severity="error",
                code="invalid_code_facts",
                path=rel_manifest,
                message=error,
            )
        ]

    if manifest.get("schema_version") != CODE_FACTS_SCHEMA_VERSION:
        issues.append(
            Issue(
                severity="error",
                code="code_facts_schema_mismatch",
                path=rel_manifest,
                message=f"Expected schema_version {CODE_FACTS_SCHEMA_VERSION}.",
            )
        )

    if not isinstance(manifest.get("facts"), list):
        return [
            *issues,
            Issue(
                severity="error",
                code="invalid_code_facts",
                path=rel_manifest,
                message="facts must be a list.",
            ),
        ]

    current = build_code_facts(repo_root, today=today)
    if _stable_code_facts_payload(manifest) != _stable_code_facts_payload(current):
        issues.append(
            Issue(
                severity="error",
                code="code_facts_drift",
                path=rel_manifest,
                message=(
                    "Current Python code facts differ from code-facts.json; "
                    "run --write-code-facts and review affected wiki claims."
                ),
            )
        )

    return issues


def _audit_config_facts(
    repo_root: Path,
    wiki_dir: Path,
    markdown_files: Iterable[Path],
    *,
    today: date,
) -> list[Issue]:
    issues: list[Issue] = []
    manifest_path = wiki_dir / CONFIG_FACTS_NAME
    rel_manifest = _repo_rel(repo_root, manifest_path)

    if _wiki_mentions_config_facts(markdown_files) and not manifest_path.exists():
        return [
            Issue(
                severity="error",
                code="missing_config_facts",
                path=rel_manifest,
                message=f"{CONFIG_FACTS_NAME} is required when the LLM wiki references config facts.",
            )
        ]
    if not manifest_path.exists():
        return issues

    manifest, error = _read_json(manifest_path, root_label="config facts root")
    if error:
        return [
            Issue(
                severity="error",
                code="invalid_config_facts",
                path=rel_manifest,
                message=error,
            )
        ]

    if manifest.get("schema_version") != CONFIG_FACTS_SCHEMA_VERSION:
        issues.append(
            Issue(
                severity="error",
                code="config_facts_schema_mismatch",
                path=rel_manifest,
                message=f"Expected schema_version {CONFIG_FACTS_SCHEMA_VERSION}.",
            )
        )

    if not isinstance(manifest.get("facts"), list):
        return [
            *issues,
            Issue(
                severity="error",
                code="invalid_config_facts",
                path=rel_manifest,
                message="facts must be a list.",
            ),
        ]

    current = build_config_facts(repo_root, today=today)
    if _stable_config_facts_payload(manifest) != _stable_config_facts_payload(current):
        issues.append(
            Issue(
                severity="error",
                code="config_facts_drift",
                path=rel_manifest,
                message=(
                    "Current tracked YAML config facts differ from config-facts.json; "
                    "run --write-config-facts and review affected wiki claims."
                ),
            )
        )

    return issues


def _audit_external_sources(
    repo_root: Path,
    markdown_files: Iterable[Path],
    *,
    today: date,
    max_source_age_days: int,
) -> list[Issue]:
    issues: list[Issue] = []
    for path in markdown_files:
        text, error = _read_text(path)
        rel = _repo_rel(repo_root, path)
        if error:
            continue
        urls = _external_urls(text)
        if not urls:
            continue
        if not _has_source_evidence(text):
            issues.append(
                Issue(
                    severity="error",
                    code="missing_source_evidence",
                    path=rel,
                    message="External URLs are present, but no source section or official-source marker was found.",
                )
            )
        checked = _verified_date(text)
        if checked is None:
            issues.append(
                Issue(
                    severity="error",
                    code="missing_verified_date",
                    path=rel,
                    message="External URLs are present, but `외부 자료 검증일: YYYY-MM-DD` is missing.",
                )
            )
            continue
        age = (today - checked).days
        if age > max_source_age_days:
            issues.append(
                Issue(
                    severity="error",
                    code="stale_verified_date",
                    path=rel,
                    message=(f"External source verification is {age} days old (limit {max_source_age_days})."),
                )
            )
    return issues


def build_report(
    repo_root: Path,
    *,
    wiki_dir: Path = WIKI_DIR_DEFAULT,
    today: date | None = None,
    max_source_age_days: int = 120,
) -> dict:
    repo_root = repo_root.resolve()
    if not wiki_dir.is_absolute():
        wiki_dir = repo_root / wiki_dir
    wiki_dir = wiki_dir.resolve()
    today = today or date.today()

    if not wiki_dir.exists():
        issue = Issue("error", "missing_wiki_dir", _repo_rel(repo_root, wiki_dir), "LLM wiki directory not found.")
        return {
            "summary": {
                "status": "fail",
                "page_count": 0,
                "error_count": 1,
                "warning_count": 0,
                "today": today.isoformat(),
                "wiki_dir": _repo_rel(repo_root, wiki_dir),
            },
            "issues": [asdict(issue)],
        }

    pages = _iter_markdown_files(wiki_dir)
    issues: list[Issue] = []
    issues.extend(_audit_readme_index(repo_root, wiki_dir, pages))
    issues.extend(_audit_local_links(repo_root, pages))
    release_summary_contract_issues = _audit_release_summary_contract(repo_root, pages)
    issues.extend(release_summary_contract_issues)
    issues.extend(_audit_source_inventory(repo_root, wiki_dir, pages, today=today))
    issues.extend(_audit_code_facts(repo_root, wiki_dir, pages, today=today))
    issues.extend(_audit_config_facts(repo_root, wiki_dir, pages, today=today))
    issues.extend(
        _audit_external_sources(
            repo_root,
            pages,
            today=today,
            max_source_age_days=max_source_age_days,
        )
    )

    error_count = sum(1 for issue in issues if issue.severity == "error")
    warning_count = sum(1 for issue in issues if issue.severity == "warning")
    status = "fail" if error_count else "warn" if warning_count else "pass"
    source_pages = sum(1 for path in pages if _external_urls(_read_text(path)[0]))
    source_inventory_path = wiki_dir / SOURCE_INVENTORY_NAME
    code_facts_path = wiki_dir / CODE_FACTS_NAME
    code_facts, code_facts_error = ({}, "missing")
    if code_facts_path.exists():
        code_facts, code_facts_error = _read_json(code_facts_path, root_label="code facts root")
    code_fact_count = len(code_facts.get("facts", [])) if code_facts_error is None else 0
    code_fact_check_summary = (
        _manifest_check_summary(code_facts, manifest_name=CODE_FACTS_NAME)
        if code_facts_error is None
        else _manifest_check_summary({}, manifest_name=CODE_FACTS_NAME)
    )
    config_facts_path = wiki_dir / CONFIG_FACTS_NAME
    config_facts, config_facts_error = ({}, "missing")
    if config_facts_path.exists():
        config_facts, config_facts_error = _read_json(config_facts_path, root_label="config facts root")
    config_fact_count = len(config_facts.get("facts", [])) if config_facts_error is None else 0
    config_fact_check_summary = (
        _manifest_check_summary(config_facts, manifest_name=CONFIG_FACTS_NAME)
        if config_facts_error is None
        else _manifest_check_summary({}, manifest_name=CONFIG_FACTS_NAME)
    )
    manifest_check_warnings = [
        *code_fact_check_summary["warnings"],
        *config_fact_check_summary["warnings"],
    ]
    manifest_check_warning_classification_counts = {
        "accepted_known": (
            code_fact_check_summary["warning_classification_counts"].get("accepted_known", 0)
            + config_fact_check_summary["warning_classification_counts"].get("accepted_known", 0)
        ),
        "unexpected": (
            code_fact_check_summary["warning_classification_counts"].get("unexpected", 0)
            + config_fact_check_summary["warning_classification_counts"].get("unexpected", 0)
        ),
    }

    return {
        "summary": {
            "status": status,
            "page_count": len(pages),
            "numbered_page_count": sum(1 for path in pages if NUMBERED_PAGE_RE.match(path.name)),
            "source_page_count": source_pages,
            "error_count": error_count,
            "warning_count": warning_count,
            "release_summary_contract_status": _release_summary_contract_status(
                pages,
                release_summary_contract_issues,
            ),
            "release_summary_contract_issue_count": len(release_summary_contract_issues),
            "source_inventory_count": len(_collect_source_refs(repo_root, pages)),
            "source_inventory_path": _repo_rel(repo_root, source_inventory_path),
            "code_fact_count": code_fact_count,
            "code_fact_check_count": code_fact_check_summary["check_count"],
            "code_fact_check_status_counts": code_fact_check_summary["status_counts"],
            "code_fact_check_warning_count": code_fact_check_summary["warning_count"],
            "code_facts_path": _repo_rel(repo_root, code_facts_path),
            "config_fact_count": config_fact_count,
            "config_fact_check_count": config_fact_check_summary["check_count"],
            "config_fact_check_status_counts": config_fact_check_summary["status_counts"],
            "config_fact_check_warning_count": config_fact_check_summary["warning_count"],
            "config_facts_path": _repo_rel(repo_root, config_facts_path),
            "manifest_check_count": code_fact_check_summary["check_count"] + config_fact_check_summary["check_count"],
            "manifest_check_warning_count": len(manifest_check_warnings),
            "manifest_check_warning_classification_counts": manifest_check_warning_classification_counts,
            "manifest_check_accepted_warning_count": manifest_check_warning_classification_counts["accepted_known"],
            "manifest_check_unexpected_warning_count": manifest_check_warning_classification_counts["unexpected"],
            "manifest_check_warnings": manifest_check_warnings,
            "today": today.isoformat(),
            "max_source_age_days": max_source_age_days,
            "wiki_dir": _repo_rel(repo_root, wiki_dir),
        },
        "issues": [asdict(issue) for issue in issues],
    }


def build_strict_release_evidence(
    report: dict,
    *,
    repo_root: Path,
    evidence_path: Path,
    today: date,
) -> dict:
    repo_root = repo_root.resolve()
    evidence_path = _repo_output_path(repo_root, evidence_path).resolve()
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    audit_status = str(summary.get("status") or "unknown")
    strict_manifest_warning_failure = bool(summary.get("strict_manifest_warning_failure"))
    gate_status = "fail" if audit_status == "fail" or strict_manifest_warning_failure else "pass"
    command = "py -3.13 execution/llm_wiki_audit.py --write-strict-release-evidence --json"
    default_evidence_path = _repo_output_path(repo_root, STRICT_RELEASE_EVIDENCE_DEFAULT).resolve()
    if evidence_path != default_evidence_path:
        command += f" --strict-release-evidence-path {_repo_rel(repo_root, evidence_path)}"

    return {
        "schema_version": STRICT_RELEASE_EVIDENCE_SCHEMA_VERSION,
        "evidence_type": "llm_wiki_strict_release_audit",
        "generated_at": today.isoformat(),
        "artifact_path": _repo_rel(repo_root, evidence_path),
        "command": command,
        "git": {
            "head_sha": _current_git_head(repo_root),
        },
        "release_gate": {
            "status": gate_status,
            "audit_status": audit_status,
            "strict_manifest_warning_mode": bool(summary.get("strict_manifest_warning_mode")),
            "strict_manifest_warning_failure": strict_manifest_warning_failure,
            "accepted_manifest_warning_count": _summary_int(summary, "manifest_check_accepted_warning_count"),
            "unexpected_manifest_warning_count": _summary_int(summary, "manifest_check_unexpected_warning_count"),
        },
        "report": report,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit docs/wiki/llm for maintainability regressions.")
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT_DEFAULT)
    parser.add_argument("--wiki-dir", type=Path, default=WIKI_DIR_DEFAULT)
    parser.add_argument("--today", type=str, default=None, help="Override today's date (YYYY-MM-DD).")
    parser.add_argument(
        "--max-source-age-days",
        type=int,
        default=120,
        help="Maximum allowed age for external-source verification dates.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON.")
    parser.add_argument(
        "--write-source-inventory",
        action="store_true",
        help=f"Rewrite docs/wiki/llm/{SOURCE_INVENTORY_NAME} from current markdown URLs before auditing.",
    )
    parser.add_argument(
        "--write-code-facts",
        action="store_true",
        help=f"Rewrite docs/wiki/llm/{CODE_FACTS_NAME} from current Python code facts before auditing.",
    )
    parser.add_argument(
        "--write-config-facts",
        action="store_true",
        help=f"Rewrite docs/wiki/llm/{CONFIG_FACTS_NAME} from current tracked YAML config facts before auditing.",
    )
    parser.add_argument(
        "--fail-on-unexpected-manifest-warnings",
        "--strict-manifest-warnings",
        dest="fail_on_unexpected_manifest_warnings",
        action="store_true",
        help="Exit nonzero when manifest warnings without accepted_known classification are present.",
    )
    parser.add_argument(
        "--write-strict-release-evidence",
        action="store_true",
        help=(
            "Write a reusable strict release/current-head evidence JSON artifact and enable strict manifest warnings."
        ),
    )
    parser.add_argument(
        "--strict-release-evidence-path",
        type=Path,
        default=STRICT_RELEASE_EVIDENCE_DEFAULT,
        help=f"Output path for --write-strict-release-evidence (default: {STRICT_RELEASE_EVIDENCE_DEFAULT}).",
    )
    args = parser.parse_args(argv)

    today = date.fromisoformat(args.today) if args.today else date.today()
    if args.write_source_inventory:
        wiki_dir = args.wiki_dir if args.wiki_dir.is_absolute() else args.repo_root / args.wiki_dir
        inventory = build_source_inventory(args.repo_root, wiki_dir=args.wiki_dir, today=today)
        inventory_path = wiki_dir / SOURCE_INVENTORY_NAME
        inventory_path.write_text(json.dumps(inventory, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.write_code_facts:
        wiki_dir = args.wiki_dir if args.wiki_dir.is_absolute() else args.repo_root / args.wiki_dir
        facts = build_code_facts(args.repo_root, today=today)
        facts_path = wiki_dir / CODE_FACTS_NAME
        facts_path.write_text(json.dumps(facts, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.write_config_facts:
        wiki_dir = args.wiki_dir if args.wiki_dir.is_absolute() else args.repo_root / args.wiki_dir
        facts = build_config_facts(args.repo_root, today=today)
        facts_path = wiki_dir / CONFIG_FACTS_NAME
        facts_path.write_text(json.dumps(facts, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    report = build_report(
        args.repo_root,
        wiki_dir=args.wiki_dir,
        today=today,
        max_source_age_days=args.max_source_age_days,
    )
    unexpected_manifest_warning_count = report["summary"].get("manifest_check_unexpected_warning_count", 0)
    strict_manifest_warning_mode = bool(args.fail_on_unexpected_manifest_warnings or args.write_strict_release_evidence)
    strict_manifest_warning_failure = bool(strict_manifest_warning_mode and unexpected_manifest_warning_count)
    report["summary"]["strict_manifest_warning_mode"] = strict_manifest_warning_mode
    report["summary"]["strict_manifest_warning_failure"] = strict_manifest_warning_failure
    if args.write_strict_release_evidence:
        evidence_path = _repo_output_path(args.repo_root.resolve(), args.strict_release_evidence_path)
        evidence_path.parent.mkdir(parents=True, exist_ok=True)
        evidence_status = "fail" if report["summary"]["status"] == "fail" or strict_manifest_warning_failure else "pass"
        report["summary"]["strict_release_evidence_path"] = _repo_rel(args.repo_root.resolve(), evidence_path.resolve())
        report["summary"]["strict_release_evidence_status"] = evidence_status
        evidence = build_strict_release_evidence(
            report,
            repo_root=args.repo_root,
            evidence_path=evidence_path,
            today=today,
        )
        evidence_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        summary = report["summary"]
        manifest_warning_count = summary.get("manifest_check_warning_count", 0)
        print(
            f"LLM wiki audit: {summary['status']} "
            f"({summary['page_count']} pages, {summary['error_count']} errors, "
            f"{summary['warning_count']} audit warnings, "
            f"{manifest_warning_count} manifest warnings)"
        )
        if manifest_warning_count:
            classification_counts = summary.get("manifest_check_warning_classification_counts", {})
            accepted_count = (
                classification_counts.get("accepted_known", 0) if isinstance(classification_counts, dict) else 0
            )
            unexpected_count = (
                classification_counts.get("unexpected", 0) if isinstance(classification_counts, dict) else 0
            )
            print(
                f"Manifest checks: {summary.get('manifest_check_count', 0)} checks, "
                f"{manifest_warning_count} warnings "
                f"({accepted_count} accepted known, {unexpected_count} unexpected; non-failing)"
            )
            for warning in summary.get("manifest_check_warnings", []):
                print(_format_manifest_warning(warning))
        if strict_manifest_warning_failure:
            print(
                f"Strict manifest warning gate: fail ({unexpected_manifest_warning_count} unexpected manifest warnings)"
            )
        if args.write_strict_release_evidence:
            print(
                "Strict release evidence: "
                f"{summary.get('strict_release_evidence_path')} "
                f"({summary.get('strict_release_evidence_status')})"
            )
        for issue in report["issues"]:
            print(f"- [{issue['severity']}] {issue['path']}: {issue['code']} - {issue['message']}")
    return 1 if report["summary"]["status"] == "fail" or strict_manifest_warning_failure else 0


if __name__ == "__main__":
    raise SystemExit(main())
