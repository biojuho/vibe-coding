"""Unit tests for `execution/llm_wiki_audit.py`."""

from __future__ import annotations

import ast
import importlib.util
import json
import sys
from datetime import date
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "execution" / "llm_wiki_audit.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("llm_wiki_audit", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["llm_wiki_audit"] = module
    spec.loader.exec_module(module)
    return module


audit = _load_module()


def _write_wiki_file(root: Path, name: str, text: str) -> Path:
    target = root / "docs" / "wiki" / "llm" / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    return target


def _write_repo_file(root: Path, name: str, text: str) -> Path:
    target = root / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    return target


def _write_source_inventory(root: Path, today: date = date(2026, 6, 8)) -> Path:
    inventory = audit.build_source_inventory(root, today=today)
    target = root / "docs" / "wiki" / "llm" / "source-inventory.json"
    target.write_text(json.dumps(inventory, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return target


def _write_code_fact_targets(root: Path) -> None:
    _write_repo_file(
        root,
        "workspace/execution/llm_client.py",
        "\n".join(
            [
                'PROVIDER_ALIASES = {"chatgpt": "openai", "gemini": "google"}',
                'DEFAULT_PROVIDER_ORDER = ["ollama", "openai", "google"]',
                'DEFAULT_MODELS = {"ollama": "qwen-test", "openai": "gpt-test", "google": "gemini-test"}',
                'OPENAI_COMPATIBLE_BASE_URLS = {"xai": "https://api.x.ai/v1"}',
                'API_KEY_ENV_VARS = {"openai": "OPENAI_API_KEY", "google": "GEMINI_API_KEY"}',
                'PRICING = {"gpt-test": {"input": 1.0, "output": 2.0}}',
                "",
                "class LLMClient:",
                "    def __init__(self, providers=None):",
                "        self.providers = list(providers or DEFAULT_PROVIDER_ORDER)",
                "        self.models = DEFAULT_MODELS.copy()",
                "",
                "    def generate_text(self):",
                "        return 'ok'",
                "",
            ]
        ),
    )
    _write_repo_file(
        root,
        "projects/shorts-maker-v2/src/shorts_maker_v2/providers/llm_router.py",
        "\n".join(
            [
                'PROVIDER_ALIASES = {"gemini": "google"}',
                'DEFAULT_MODELS = {"google": "gemini-test", "openai": "gpt-test"}',
                "OPENAI_COMPATIBLE_BASE_URLS = {}",
                "",
                "class LLMRouter:",
                "    def __init__(self, providers=None):",
                "        self.providers = providers or ['openai']",
                "",
            ]
        ),
    )
    _write_repo_file(
        root,
        "projects/blind-to-x/pipeline/draft_providers.py",
        "\n".join(
            [
                'PROVIDER_ALIASES = {"chatgpt": "openai"}',
                'DEFAULT_PROVIDER_ORDER = ["openai", "gemini", "ollama"]',
                "",
                "class DraftProvidersMixin:",
                "    def _generate_with_openai(self):",
                "        return 'ok'",
                "",
                "    def _generate_with_gemini(self):",
                "        return 'ok'",
                "",
                "    def _generate_with_ollama(self):",
                "        return 'ok'",
                "",
            ]
        ),
    )


def _write_code_fact_wiki(root: Path) -> None:
    _write_wiki_file(
        root,
        "README.md",
        "# LLM Wiki\n\n| # | page | note |\n|---|---|---|\n| 01 | [Architecture](01-architecture.md) | code facts |\n",
    )
    _write_wiki_file(
        root,
        "01-architecture.md",
        "# 01\n\n`LLMClient` uses `DEFAULT_PROVIDER_ORDER` and `DEFAULT_MODELS`.\n",
    )


def _write_code_facts(root: Path, today: date = date(2026, 6, 8)) -> Path:
    facts = audit.build_code_facts(root, today=today)
    target = root / "docs" / "wiki" / "llm" / "code-facts.json"
    target.write_text(json.dumps(facts, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target


def _write_config_fact_targets(root: Path) -> None:
    _write_repo_file(
        root,
        "projects/shorts-maker-v2/config.yaml",
        "\n".join(
            [
                "providers:",
                '  llm: "openai"',
                "  llm_providers:",
                "    - google",
                "    - openai",
                "  llm_models:",
                '    google: "gemini-test"',
                '    openai: "gpt-test"',
                '  llm_model: "gpt-test"',
                "",
            ]
        ),
    )
    for name, openai_enabled in (("config.example.yaml", "false"), ("config.ci.yaml", "true")):
        _write_repo_file(
            root,
            f"projects/blind-to-x/{name}",
            "\n".join(
                [
                    "llm:",
                    '  strategy: "fallback"',
                    "  providers:",
                    "    - gemini",
                    "    - deepseek",
                    "    - openai",
                    "  max_retries_per_provider: 2",
                    "  request_timeout_seconds: 45",
                    "  pricing:",
                    "    gemini:",
                    "      input_per_1m: 0.0",
                    "      output_per_1m: 0.0",
                    "    deepseek:",
                    "      input_per_1m: 0.14",
                    "      output_per_1m: 0.28",
                    "    openai:",
                    "      input_per_1m: 0.15",
                    "      output_per_1m: 0.60",
                    "gemini:",
                    "  enabled: true",
                    '  api_key: "SECRET_SHOULD_NOT_LEAK"',
                    '  model: "gemini-test"',
                    "deepseek:",
                    "  enabled: true",
                    '  api_key: "SECRET_SHOULD_NOT_LEAK"',
                    '  model: "deepseek-test"',
                    "openai:",
                    f"  enabled: {openai_enabled}",
                    "  chat_enabled: true",
                    '  api_key: "SECRET_SHOULD_NOT_LEAK"',
                    '  chat_model: "gpt-test"',
                    "",
                ]
            ),
        )


def _write_config_fact_wiki(root: Path) -> None:
    _write_wiki_file(
        root,
        "README.md",
        "# LLM Wiki\n\n| # | page | note |\n|---|---|---|\n| 01 | [Config](01-config.md) | config facts |\n",
    )
    _write_wiki_file(
        root,
        "01-config.md",
        "# 01\n\n`config.yaml` uses `llm_providers` for fallback order.\n",
    )


def _write_config_facts(root: Path, today: date = date(2026, 6, 8)) -> Path:
    facts = audit.build_config_facts(root, today=today)
    target = root / "docs" / "wiki" / "llm" / "config-facts.json"
    target.write_text(json.dumps(facts, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target


def _write_minimal_healthy_wiki(root: Path) -> None:
    _write_wiki_file(
        root,
        "README.md",
        "# LLM Wiki\n\n"
        "| # | page | note |\n"
        "|---|---|---|\n"
        "| 01 | [Architecture](01-architecture.md) | local |\n"
        "| 02 | [Providers](02-providers.md) | external |\n",
    )
    _write_wiki_file(
        root,
        "01-architecture.md",
        "# 01\n\nSee [providers](02-providers.md).\n",
    )
    _write_wiki_file(
        root,
        "02-providers.md",
        "# 02\n\n"
        "공식: [OpenAI models](https://developers.openai.com/api/docs/models)\n\n"
        "*외부 자료 검증일: 2026-06-08*\n",
    )
    _write_source_inventory(root)


def _codes(report: dict) -> set[str]:
    return {issue["code"] for issue in report["issues"]}


def test_derived_provider_metadata_records_aliases_urls_keys_and_pricing() -> None:
    derived = audit._derived_provider_metadata(
        {
            "PROVIDER_ALIASES": {"chatgpt": "openai", "gemini": "google"},
            "OPENAI_COMPATIBLE_BASE_URLS": {"xai": "https://api.x.ai/v1"},
            "API_KEY_ENV_VARS": {"openai": "OPENAI_API_KEY", "google": "GEMINI_API_KEY"},
            "PRICING": {"gpt-test": {"input": 1.0}, "gemini-test": {"input": 0.0}},
        }
    )

    assert derived == {
        "alias_count": 2,
        "alias_canonical_providers": ["google", "openai"],
        "openai_compatible_providers": ["xai"],
        "api_key_providers": ["google", "openai"],
        "pricing_models": ["gemini-test", "gpt-test"],
    }


def test_derived_generation_helper_metadata_compares_helpers_to_default_order() -> None:
    tree = ast.parse(
        "\n".join(
            (
                "class Router:",
                "    def _generate_with_openai(self): pass",
                "    def _generate_with_google(self): pass",
                "def _generate_with_xai(): pass",
            )
        )
    )

    derived = audit._derived_generation_helper_metadata(tree, ["openai", "anthropic"])

    assert derived == {
        "generation_helper_providers": ["google", "openai", "xai"],
        "default_providers_without_generation_helper": ["anthropic"],
        "generation_helpers_outside_default_order": ["google", "xai"],
    }


def test_derived_constructor_assignments_records_target_constructor_defaults() -> None:
    tree = ast.parse(
        "\n".join(
            (
                "DEFAULT_PROVIDER_ORDER = ['openai']",
                "DEFAULT_MODELS = {'openai': 'gpt-test'}",
                "class LLMClient:",
                "    def __init__(self, providers=None):",
                "        self.providers = list(providers or DEFAULT_PROVIDER_ORDER)",
                "        self.models = DEFAULT_MODELS.copy()",
            )
        )
    )

    assert audit._derived_constructor_assignments("workspace_llm_client", tree) == {
        "constructor_providers_expression": "list(providers or DEFAULT_PROVIDER_ORDER)",
        "constructor_models_expression": "DEFAULT_MODELS.copy()",
    }


def test_release_summary_docs_collects_only_triggered_pages(tmp_path: Path) -> None:
    plain_page = _write_wiki_file(tmp_path, "01-plain.md", "# 01\n\nNo release evidence here.\n")
    release_page = _write_wiki_file(
        tmp_path,
        "14-maintenance.md",
        "# 14\n\n`llm_wiki_release_summary.py` writes to `GITHUB_STEP_SUMMARY`.\n",
    )

    docs = audit._release_summary_docs([plain_page, release_page])

    assert docs == [(release_page, release_page.read_text(encoding="utf-8"))]


def test_missing_release_summary_marker_issues_reports_required_markers() -> None:
    issues = audit._missing_release_summary_marker_issues(
        "docs/wiki/llm/14-maintenance.md",
        "`llm_wiki_release_summary.py` writes to `GITHUB_STEP_SUMMARY`.",
    )

    assert [issue.code for issue in issues] == [
        "release_summary_visible_artifact_missing",
        "release_summary_upload_artifact_action_missing",
    ]
    assert {issue.path for issue in issues} == {"docs/wiki/llm/14-maintenance.md"}


def test_release_summary_doc_issues_flags_unsafe_workflow_examples(tmp_path: Path) -> None:
    page = _write_wiki_file(
        tmp_path,
        "14-maintenance.md",
        "\n".join(
            [
                "# 14",
                "",
                "- run: echo 'LLM Wiki ok' >> \"$GITHUB_STEP_SUMMARY\"",
                "- uses: actions/upload-artifact@v4",
                "  with:",
                "    path: .tmp/llm-wiki-strict-audit-current.json",
                "",
            ]
        ),
    )

    issues = audit._release_summary_doc_issues(tmp_path, page, page.read_text(encoding="utf-8"))

    assert [issue.code for issue in issues] == [
        "release_summary_stale_upload_artifact_action",
        "release_summary_hidden_tmp_artifact_upload",
        "release_summary_manual_step_summary_echo",
    ]
    assert issues[0].message.endswith("not v4.")


def test_source_inventory_manifest_sources_reports_entry_shape_and_duplicates() -> None:
    first_entry = {"url": "https://one.test", "pages": ["01.md"]}
    duplicate_entry = {"url": "https://one.test", "pages": ["02.md"]}

    manifest_sources, issues = audit._source_inventory_manifest_sources(
        [
            first_entry,
            duplicate_entry,
            [],
            {"url": "ftp://bad.test"},
        ],
        "docs/wiki/llm/source-inventory.json",
    )

    assert manifest_sources == {"https://one.test": duplicate_entry}
    assert [issue.code for issue in issues] == [
        "duplicate_source_inventory_url",
        "invalid_source_inventory_entry",
        "invalid_source_inventory_entry",
    ]


def test_source_inventory_drift_issues_reports_missing_then_stale_urls() -> None:
    issues = audit._source_inventory_drift_issues(
        {"https://used.test"},
        {"https://stale.test"},
        "docs/wiki/llm/source-inventory.json",
    )

    assert [issue.code for issue in issues] == [
        "source_inventory_missing_url",
        "source_inventory_stale_url",
    ]
    assert "https://used.test" in issues[0].message
    assert "https://stale.test" in issues[1].message


def test_source_inventory_entry_issues_validate_metadata_and_dates() -> None:
    entry = {
        "pages": ["01-wrong.md"],
        "source_type": "forum",
        "volatility": "weekly",
        "last_verified": "not-a-date",
        "review_after": "2026-06-01",
    }

    issues = audit._source_inventory_entry_issues(
        "https://docs.test/source",
        entry,
        ["02-providers.md"],
        "docs/wiki/llm/source-inventory.json",
        today=date(2026, 6, 8),
    )

    assert [issue.code for issue in issues] == [
        "source_inventory_page_mismatch",
        "invalid_source_type",
        "invalid_source_volatility",
        "invalid_source_last_verified",
        "source_review_due",
    ]


def test_source_inventory_entry_issues_flag_review_before_verified() -> None:
    entry = {
        "pages": ["02-providers.md"],
        "source_type": "official-docs",
        "volatility": "high",
        "last_verified": "2026-06-08",
        "review_after": "2026-06-01",
    }

    issues = audit._source_inventory_entry_issues(
        "https://docs.test/source",
        entry,
        ["02-providers.md"],
        "docs/wiki/llm/source-inventory.json",
        today=date(2026, 6, 8),
    )

    assert [issue.code for issue in issues] == [
        "invalid_source_review_after",
        "source_review_due",
    ]


def test_healthy_wiki_passes(tmp_path: Path):
    _write_minimal_healthy_wiki(tmp_path)

    report = audit.build_report(tmp_path, today=date(2026, 6, 8))

    assert report["summary"]["status"] == "pass"
    assert report["summary"]["page_count"] == 3
    assert report["summary"]["numbered_page_count"] == 2
    assert report["summary"]["source_page_count"] == 1
    assert report["summary"]["source_inventory_count"] == 1
    assert report["issues"] == []


def test_missing_readme_index_and_broken_local_links_fail(tmp_path: Path):
    _write_wiki_file(
        tmp_path,
        "README.md",
        "# LLM Wiki\n\n| # | page | note |\n|---|---|---|\n| 01 | [Architecture](01-architecture.md) | local |\n",
    )
    _write_wiki_file(
        tmp_path,
        "01-architecture.md",
        "# 01\n\nSee [missing](missing.md).\n",
    )
    _write_wiki_file(tmp_path, "02-providers.md", "# 02\n")

    report = audit.build_report(tmp_path, today=date(2026, 6, 8))

    assert report["summary"]["status"] == "fail"
    assert {"missing_readme_index", "broken_local_link"} <= _codes(report)


def test_external_urls_require_source_evidence_and_verified_date(tmp_path: Path):
    _write_wiki_file(
        tmp_path,
        "README.md",
        "# LLM Wiki\n\n| # | page | note |\n|---|---|---|\n| 01 | [Providers](01-providers.md) | external |\n",
    )
    _write_wiki_file(
        tmp_path,
        "01-providers.md",
        "# 01\n\nSee https://developers.openai.com/api/docs/models for models.\n",
    )

    report = audit.build_report(tmp_path, today=date(2026, 6, 8))

    assert report["summary"]["status"] == "fail"
    assert {"missing_source_evidence", "missing_verified_date", "missing_source_inventory"} <= _codes(report)


def test_localhost_urls_inside_code_blocks_do_not_require_source_dates(tmp_path: Path):
    _write_wiki_file(
        tmp_path,
        "README.md",
        "# LLM Wiki\n\n| # | page | note |\n|---|---|---|\n| 01 | [Ops](01-ops.md) | local |\n",
    )
    _write_wiki_file(
        tmp_path,
        "01-ops.md",
        "# 01\n\n```bash\ncurl http://127.0.0.1:3030/health\n```\n",
    )

    report = audit.build_report(tmp_path, today=date(2026, 6, 8))

    assert report["summary"]["status"] == "pass"
    assert report["summary"]["source_page_count"] == 0
    assert report["issues"] == []


def test_release_summary_contract_passes_with_helper_and_visible_artifact(tmp_path: Path):
    _write_wiki_file(
        tmp_path,
        "README.md",
        "# LLM Wiki\n\n"
        "| # | page | note |\n"
        "|---|---|---|\n"
        "| 14 | [Maintenance](14-maintenance-verification.md) | release summary |\n",
    )
    _write_wiki_file(
        tmp_path,
        "14-maintenance-verification.md",
        "\n".join(
            [
                "# 14",
                "",
                "`llm_wiki_strict_evidence` must be reviewed through `llm_wiki_release_summary.py`.",
                "The helper appends Markdown to `GITHUB_STEP_SUMMARY` and copies evidence into",
                "`release-evidence/llm-wiki` for upload.",
                "",
                "```yaml",
                "- uses: actions/upload-artifact@v7",
                "  with:",
                "    name: llm-wiki-release-evidence",
                "    path: release-evidence/llm-wiki",
                "```",
                "",
            ]
        ),
    )

    report = audit.build_report(tmp_path, today=date(2026, 6, 8))

    assert report["summary"]["status"] == "pass"
    assert report["summary"]["release_summary_contract_status"] == "pass"
    assert report["summary"]["release_summary_contract_issue_count"] == 0
    assert report["issues"] == []


def test_release_summary_contract_fails_on_manual_echo_stale_action_and_tmp_upload(tmp_path: Path):
    _write_wiki_file(
        tmp_path,
        "README.md",
        "# LLM Wiki\n\n"
        "| # | page | note |\n"
        "|---|---|---|\n"
        "| 14 | [Maintenance](14-maintenance-verification.md) | release summary |\n",
    )
    _write_wiki_file(
        tmp_path,
        "14-maintenance-verification.md",
        "\n".join(
            [
                "# 14",
                "",
                "`llm_wiki_strict_evidence` should be echoed into `GITHUB_STEP_SUMMARY`.",
                "",
                "```yaml",
                "- run: echo 'LLM Wiki ok' >> \"$GITHUB_STEP_SUMMARY\"",
                "- uses: actions/upload-artifact@v4",
                "  with:",
                "    path: .tmp/llm-wiki-strict-audit-current.json",
                "```",
                "",
            ]
        ),
    )

    report = audit.build_report(tmp_path, today=date(2026, 6, 8))

    assert report["summary"]["status"] == "fail"
    assert report["summary"]["release_summary_contract_status"] == "fail"
    assert report["summary"]["release_summary_contract_issue_count"] == 6
    assert {
        "release_summary_helper_missing",
        "release_summary_visible_artifact_missing",
        "release_summary_upload_artifact_action_missing",
        "release_summary_stale_upload_artifact_action",
        "release_summary_hidden_tmp_artifact_upload",
        "release_summary_manual_step_summary_echo",
    } <= _codes(report)


def test_source_inventory_records_pages_and_review_window(tmp_path: Path):
    _write_minimal_healthy_wiki(tmp_path)

    inventory = audit.build_source_inventory(tmp_path, today=date(2026, 6, 8))

    assert inventory["schema_version"] == 1
    assert inventory["sources"] == [
        {
            "url": "https://developers.openai.com/api/docs/models",
            "host": "developers.openai.com",
            "pages": ["02-providers.md"],
            "topic": "provider-models-pricing-limits",
            "source_type": "official-docs",
            "volatility": "high",
            "cadence_days": 45,
            "last_verified": "2026-06-08",
            "review_after": "2026-07-23",
            "notes": "Generated from docs/wiki/llm markdown links; revalidate the source before updating time-sensitive claims.",
        }
    ]


def test_inline_code_urls_are_normalized_without_backticks(tmp_path: Path):
    _write_wiki_file(
        tmp_path,
        "README.md",
        "# LLM Wiki\n\n| # | page | note |\n|---|---|---|\n| 01 | [Providers](01-providers.md) | external |\n",
    )
    _write_wiki_file(
        tmp_path,
        "01-providers.md",
        "# 01\n\n怨듭떇: `https://api.deepseek.com`\n\n*?몃? ?먮즺 寃利앹씪: 2026-06-08*\n",
    )

    inventory = audit.build_source_inventory(tmp_path, today=date(2026, 6, 8))

    assert inventory["sources"][0]["url"] == "https://api.deepseek.com"


def test_source_inventory_drift_fails(tmp_path: Path):
    _write_minimal_healthy_wiki(tmp_path)
    inventory_path = tmp_path / "docs" / "wiki" / "llm" / "source-inventory.json"
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    inventory["sources"][0]["url"] = "https://example.com/stale"
    inventory_path.write_text(json.dumps(inventory, ensure_ascii=False, indent=2), encoding="utf-8")

    report = audit.build_report(tmp_path, today=date(2026, 6, 8))

    assert report["summary"]["status"] == "fail"
    assert {"source_inventory_missing_url", "source_inventory_stale_url"} <= _codes(report)


def test_source_inventory_review_due_fails(tmp_path: Path):
    _write_minimal_healthy_wiki(tmp_path)
    inventory_path = tmp_path / "docs" / "wiki" / "llm" / "source-inventory.json"
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    inventory["sources"][0]["review_after"] = "2026-06-30"
    inventory_path.write_text(json.dumps(inventory, ensure_ascii=False, indent=2), encoding="utf-8")

    report = audit.build_report(tmp_path, today=date(2026, 7, 1))

    assert report["summary"]["status"] == "fail"
    assert "source_review_due" in _codes(report)


def test_stale_verified_date_fails(tmp_path: Path):
    _write_minimal_healthy_wiki(tmp_path)
    (tmp_path / "docs" / "wiki" / "llm" / "02-providers.md").write_text(
        "# 02\n\n## 출처\n\n- https://developers.openai.com/api/docs/models\n\n*외부 자료 검증일: 2026-01-01*\n",
        encoding="utf-8",
    )

    report = audit.build_report(tmp_path, today=date(2026, 6, 8), max_source_age_days=30)

    assert report["summary"]["status"] == "fail"
    assert "stale_verified_date" in _codes(report)


def test_code_facts_manifest_records_python_literals_and_methods(tmp_path: Path):
    _write_code_fact_targets(tmp_path)

    facts = audit.build_code_facts(tmp_path, today=date(2026, 6, 8))
    by_id = {item["id"]: item for item in facts["facts"]}

    llm_client = by_id["workspace_llm_client"]
    assert llm_client["constants"]["DEFAULT_PROVIDER_ORDER"] == ["ollama", "openai", "google"]
    assert llm_client["derived"]["default_model_count"] == 3
    assert llm_client["derived"]["constructor_providers_expression"] == "list(providers or DEFAULT_PROVIDER_ORDER)"
    assert "generate_text" in llm_client["classes"]["LLMClient"]

    blind_to_x = by_id["blind_to_x_draft_providers"]
    assert blind_to_x["derived"]["generation_helper_providers"] == ["gemini", "ollama", "openai"]
    assert blind_to_x["derived"]["default_providers_without_generation_helper"] == []
    assert facts["checks"][0]["status"] == "pass"


def test_code_facts_missing_manifest_fails_when_wiki_mentions_code(tmp_path: Path):
    _write_code_fact_wiki(tmp_path)
    _write_code_fact_targets(tmp_path)

    report = audit.build_report(tmp_path, today=date(2026, 6, 8))

    assert report["summary"]["status"] == "fail"
    assert "missing_code_facts" in _codes(report)


def test_code_facts_drift_fails_when_python_constant_changes(tmp_path: Path):
    _write_code_fact_wiki(tmp_path)
    _write_code_fact_targets(tmp_path)
    _write_code_facts(tmp_path)
    llm_client = tmp_path / "workspace" / "execution" / "llm_client.py"
    llm_client.write_text(
        llm_client.read_text(encoding="utf-8").replace("gpt-test", "gpt-test-next"),
        encoding="utf-8",
    )

    report = audit.build_report(tmp_path, today=date(2026, 6, 8))

    assert report["summary"]["status"] == "fail"
    assert "code_facts_drift" in _codes(report)


def test_code_facts_manifest_passes_when_code_matches(tmp_path: Path):
    _write_code_fact_wiki(tmp_path)
    _write_code_fact_targets(tmp_path)
    _write_code_facts(tmp_path)

    report = audit.build_report(tmp_path, today=date(2026, 6, 8))

    assert report["summary"]["status"] == "pass"
    assert report["summary"]["code_fact_count"] == 3
    assert report["summary"]["code_fact_check_count"] == 1
    assert report["summary"]["code_fact_check_status_counts"]["pass"] == 1
    assert report["summary"]["manifest_check_warning_count"] == 0


def test_config_facts_manifest_records_tracked_yaml_defaults(tmp_path: Path):
    _write_config_fact_targets(tmp_path)

    facts = audit.build_config_facts(tmp_path, today=date(2026, 6, 8))
    by_id = {item["id"]: item for item in facts["facts"]}

    shorts = by_id["shorts_maker_v2_config"]
    assert shorts["facts"]["providers.llm_providers"] == ["google", "openai"]
    assert shorts["derived"]["providers_without_model"] == []

    blind_example = by_id["blind_to_x_config_example"]
    assert blind_example["facts"]["llm.providers"] == ["gemini", "deepseek", "openai"]
    assert blind_example["derived"]["model_by_provider"] == {
        "deepseek": "deepseek-test",
        "gemini": "gemini-test",
        "openai": "gpt-test",
    }
    assert "SECRET_SHOULD_NOT_LEAK" not in json.dumps(facts)
    coverage_checks = [check for check in facts["checks"] if check["id"].endswith("_coverage")]
    assert {check["status"] for check in coverage_checks} == {"pass"}


def test_config_facts_cross_manifest_records_runtime_helper_gaps(tmp_path: Path):
    _write_config_fact_targets(tmp_path)
    _write_code_fact_targets(tmp_path)

    facts = audit.build_config_facts(tmp_path, today=date(2026, 6, 8))
    checks = {check["id"]: check for check in facts["checks"]}

    blind_check = checks["blind_to_x_config_example_runtime_helpers"]
    assert blind_check["status"] == "warning"
    assert blind_check["warning_classification"] == "accepted_known"
    assert "18-runtime-wiring-checks.md" in blind_check["accepted_reason"]
    assert blind_check["missing_runtime_providers"] == ["deepseek"]
    assert blind_check["runtime_providers_outside_config"] == ["ollama"]

    shorts_check = checks["shorts_maker_v2_config_runtime_models"]
    assert shorts_check["status"] == "pass"
    assert shorts_check["missing_runtime_providers"] == []


def test_config_facts_missing_manifest_fails_when_wiki_mentions_config(tmp_path: Path):
    _write_config_fact_wiki(tmp_path)
    _write_config_fact_targets(tmp_path)

    report = audit.build_report(tmp_path, today=date(2026, 6, 8))

    assert report["summary"]["status"] == "fail"
    assert "missing_config_facts" in _codes(report)


def test_config_facts_drift_fails_when_yaml_provider_order_changes(tmp_path: Path):
    _write_config_fact_wiki(tmp_path)
    _write_config_fact_targets(tmp_path)
    _write_config_facts(tmp_path)
    config_path = tmp_path / "projects" / "shorts-maker-v2" / "config.yaml"
    config_path.write_text(
        config_path.read_text(encoding="utf-8").replace("- google\n    - openai", "- openai\n    - google"),
        encoding="utf-8",
    )

    report = audit.build_report(tmp_path, today=date(2026, 6, 8))

    assert report["summary"]["status"] == "fail"
    assert "config_facts_drift" in _codes(report)


def test_config_facts_manifest_passes_when_config_matches(tmp_path: Path):
    _write_config_fact_wiki(tmp_path)
    _write_config_fact_targets(tmp_path)
    _write_code_fact_targets(tmp_path)
    _write_config_facts(tmp_path)

    report = audit.build_report(tmp_path, today=date(2026, 6, 8))

    assert report["summary"]["status"] == "pass"
    assert report["summary"]["config_fact_count"] == 3
    assert report["summary"]["warning_count"] == 0
    assert report["summary"]["config_fact_check_count"] == 6
    assert report["summary"]["config_fact_check_status_counts"]["pass"] == 4
    assert report["summary"]["config_fact_check_status_counts"]["warning"] == 2
    assert report["summary"]["config_fact_check_warning_count"] == 2
    assert report["summary"]["manifest_check_warning_count"] == 2
    assert report["summary"]["manifest_check_accepted_warning_count"] == 2
    assert report["summary"]["manifest_check_unexpected_warning_count"] == 0
    assert report["summary"]["manifest_check_warning_classification_counts"] == {
        "accepted_known": 2,
        "unexpected": 0,
    }
    assert [item["id"] for item in report["summary"]["manifest_check_warnings"]] == [
        "blind_to_x_config_example_runtime_helpers",
        "blind_to_x_config_ci_runtime_helpers",
    ]
    assert report["summary"]["manifest_check_warnings"][0]["manifest"] == "config-facts.json"
    assert report["summary"]["manifest_check_warnings"][0]["classification"] == "accepted_known"
    assert "18-runtime-wiring-checks.md" in report["summary"]["manifest_check_warnings"][0]["accepted_reason"]
    assert report["summary"]["manifest_check_warnings"][0]["missing_runtime_providers"] == ["deepseek"]
    assert report["summary"]["manifest_check_warnings"][0]["runtime_providers_outside_config"] == ["ollama"]


def test_manifest_warning_without_acceptance_metadata_is_unexpected():
    summary = audit._manifest_check_summary(
        {
            "checks": [
                {
                    "id": "new_runtime_gap",
                    "status": "warning",
                    "message": "New manifest warning without acceptance metadata.",
                }
            ]
        },
        manifest_name="config-facts.json",
    )

    assert summary["warning_count"] == 1
    assert summary["warning_classification_counts"] == {
        "accepted_known": 0,
        "unexpected": 1,
    }
    assert summary["warnings"][0]["classification"] == "unexpected"


def _report_with_unexpected_manifest_warning(*args, **kwargs) -> dict:
    return {
        "summary": {
            "status": "pass",
            "page_count": 3,
            "error_count": 0,
            "warning_count": 0,
            "manifest_check_count": 1,
            "manifest_check_warning_count": 1,
            "manifest_check_warning_classification_counts": {
                "accepted_known": 0,
                "unexpected": 1,
            },
            "manifest_check_accepted_warning_count": 0,
            "manifest_check_unexpected_warning_count": 1,
            "manifest_check_warnings": [
                {
                    "manifest": "code-facts.json",
                    "id": "new_manifest_warning",
                    "message": "New manifest warning without accepted metadata.",
                    "classification": "unexpected",
                }
            ],
        },
        "issues": [],
    }


def test_default_cli_keeps_unexpected_manifest_warnings_non_failing(monkeypatch, capsys):
    monkeypatch.setattr(audit, "build_report", _report_with_unexpected_manifest_warning)

    exit_code = audit.main(["--today", "2026-06-08"])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "1 manifest warnings" in output
    assert "0 accepted known, 1 unexpected; non-failing" in output
    assert "[manifest-warning:unexpected]" in output


def test_cli_parser_helper_preserves_flags_and_paths():
    args = audit._parse_llm_wiki_audit_args(
        [
            "--repo-root",
            "repo",
            "--wiki-dir",
            "wiki",
            "--today",
            "2026-06-08",
            "--write-source-inventory",
            "--write-code-facts",
            "--write-config-facts",
            "--strict-manifest-warnings",
            "--write-strict-release-evidence",
            "--strict-release-evidence-path",
            ".tmp/evidence.json",
            "--json",
        ]
    )

    assert args.repo_root == Path("repo")
    assert args.wiki_dir == Path("wiki")
    assert args.today == "2026-06-08"
    assert args.write_source_inventory is True
    assert args.write_code_facts is True
    assert args.write_config_facts is True
    assert args.fail_on_unexpected_manifest_warnings is True
    assert args.write_strict_release_evidence is True
    assert args.strict_release_evidence_path == Path(".tmp/evidence.json")
    assert args.json is True


def test_strict_manifest_summary_helper_sets_mode_and_failure():
    args = audit._parse_llm_wiki_audit_args(["--write-strict-release-evidence"])
    report = {"summary": {"manifest_check_unexpected_warning_count": 2}}

    unexpected_count, strict_mode, strict_failure = audit._apply_strict_manifest_warning_summary(report, args)

    assert unexpected_count == 2
    assert strict_mode is True
    assert strict_failure is True
    assert report["summary"]["strict_manifest_warning_mode"] is True
    assert report["summary"]["strict_manifest_warning_failure"] is True


def test_write_requested_audit_artifacts_uses_resolved_wiki_dir(monkeypatch, tmp_path: Path):
    wiki_dir = tmp_path / "custom" / "wiki"
    wiki_dir.mkdir(parents=True)
    args = audit._parse_llm_wiki_audit_args(
        [
            "--repo-root",
            str(tmp_path),
            "--wiki-dir",
            "custom/wiki",
            "--write-source-inventory",
        ]
    )

    def fake_source_inventory(repo_root: Path, *, wiki_dir: Path, today: date) -> dict:
        return {
            "repo_root": repo_root.name,
            "wiki_dir": wiki_dir.as_posix(),
            "today": today.isoformat(),
        }

    monkeypatch.setattr(audit, "build_source_inventory", fake_source_inventory)

    audit._write_requested_audit_artifacts(args, today=date(2026, 6, 8))

    payload = json.loads((wiki_dir / audit.SOURCE_INVENTORY_NAME).read_text(encoding="utf-8"))
    assert payload == {
        "repo_root": tmp_path.name,
        "wiki_dir": "custom/wiki",
        "today": "2026-06-08",
    }


def test_strict_manifest_warning_cli_fails_on_unexpected_warnings(monkeypatch, capsys):
    monkeypatch.setattr(audit, "build_report", _report_with_unexpected_manifest_warning)

    exit_code = audit.main(
        [
            "--today",
            "2026-06-08",
            "--fail-on-unexpected-manifest-warnings",
        ]
    )

    output = capsys.readouterr().out
    assert exit_code == 1
    assert "Strict manifest warning gate: fail (1 unexpected manifest warnings)" in output


def test_strict_manifest_warning_json_reports_failure(monkeypatch, capsys):
    monkeypatch.setattr(audit, "build_report", _report_with_unexpected_manifest_warning)

    exit_code = audit.main(
        [
            "--today",
            "2026-06-08",
            "--strict-manifest-warnings",
            "--json",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert payload["summary"]["strict_manifest_warning_mode"] is True
    assert payload["summary"]["strict_manifest_warning_failure"] is True
    assert payload["summary"]["manifest_check_unexpected_warning_count"] == 1


def test_write_strict_release_evidence_enables_strict_mode_and_records_artifact(tmp_path: Path, capsys):
    _write_minimal_healthy_wiki(tmp_path)
    head_sha = "abcdef1234567890abcdef1234567890abcdef12"
    (tmp_path / ".git" / "refs" / "heads").mkdir(parents=True)
    (tmp_path / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    (tmp_path / ".git" / "refs" / "heads" / "main").write_text(f"{head_sha}\n", encoding="utf-8")

    exit_code = audit.main(
        [
            "--repo-root",
            str(tmp_path),
            "--today",
            "2026-06-08",
            "--write-strict-release-evidence",
            "--strict-release-evidence-path",
            ".tmp/strict-evidence.json",
            "--json",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    evidence_path = tmp_path / ".tmp" / "strict-evidence.json"
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert payload["summary"]["strict_manifest_warning_mode"] is True
    assert payload["summary"]["strict_manifest_warning_failure"] is False
    assert payload["summary"]["strict_release_evidence_path"] == ".tmp/strict-evidence.json"
    assert payload["summary"]["strict_release_evidence_status"] == "pass"
    assert evidence["schema_version"] == 1
    assert evidence["evidence_type"] == "llm_wiki_strict_release_audit"
    assert evidence["command"].endswith("--strict-release-evidence-path .tmp/strict-evidence.json")
    assert evidence["git"]["head_sha"] == head_sha
    assert evidence["release_gate"]["status"] == "pass"
    assert evidence["release_gate"]["strict_manifest_warning_mode"] is True
    assert evidence["report"]["summary"]["strict_release_evidence_path"] == ".tmp/strict-evidence.json"


def test_write_strict_release_evidence_records_failure_on_unexpected_manifest_warning(
    monkeypatch, tmp_path: Path, capsys
):
    monkeypatch.setattr(audit, "build_report", _report_with_unexpected_manifest_warning)

    exit_code = audit.main(
        [
            "--repo-root",
            str(tmp_path),
            "--today",
            "2026-06-08",
            "--write-strict-release-evidence",
            "--strict-release-evidence-path",
            ".tmp/strict-evidence.json",
            "--json",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    evidence = json.loads((tmp_path / ".tmp" / "strict-evidence.json").read_text(encoding="utf-8"))
    assert exit_code == 1
    assert payload["summary"]["strict_manifest_warning_mode"] is True
    assert payload["summary"]["strict_manifest_warning_failure"] is True
    assert payload["summary"]["strict_release_evidence_status"] == "fail"
    assert evidence["release_gate"]["status"] == "fail"
    assert evidence["release_gate"]["unexpected_manifest_warning_count"] == 1
    assert evidence["report"]["summary"]["manifest_check_warnings"][0]["classification"] == "unexpected"


def test_text_output_exposes_non_failing_manifest_warnings(tmp_path: Path, capsys):
    _write_config_fact_wiki(tmp_path)
    _write_config_fact_targets(tmp_path)
    _write_code_fact_targets(tmp_path)
    _write_config_facts(tmp_path)

    exit_code = audit.main(["--repo-root", str(tmp_path), "--today", "2026-06-08"])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "LLM wiki audit: pass" in output
    assert "0 audit warnings, 2 manifest warnings" in output
    assert "Manifest checks: 6 checks, 2 warnings (2 accepted known, 0 unexpected; non-failing)" in output
    assert "[manifest-warning:accepted_known]" in output
    assert "blind_to_x_config_example_runtime_helpers" in output
    assert "missing runtime: deepseek" in output
    assert "runtime outside config: ollama" in output


def test_config_facts_drift_fails_when_runtime_helper_changes(tmp_path: Path):
    _write_config_fact_wiki(tmp_path)
    _write_config_fact_targets(tmp_path)
    _write_code_fact_targets(tmp_path)
    _write_config_facts(tmp_path)
    draft_providers = tmp_path / "projects" / "blind-to-x" / "pipeline" / "draft_providers.py"
    draft_providers.write_text(
        draft_providers.read_text(encoding="utf-8").replace("def _generate_with_gemini", "def _generate_with_claude"),
        encoding="utf-8",
    )

    report = audit.build_report(tmp_path, today=date(2026, 6, 8))

    assert report["summary"]["status"] == "fail"
    assert "config_facts_drift" in _codes(report)
