from __future__ import annotations

import asyncio
import json
import subprocess
import sys
from pathlib import Path

import pytest

_BTX_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_BTX_ROOT))

from scripts import recompute_scores  # noqa: E402


class _FakeConfig:
    def __init__(self, path: str):
        self.path = path

    def get(self, key: str, default=None):
        if key == "ranking.weights":
            return {"scrape_quality": 0.3, "publishability": 0.4, "performance": 0.3}
        return default


class _FakeProfile:
    def __init__(self, title: str, score: float):
        self.title = title
        self.score = score

    def to_dict(self):
        return {
            "topic_cluster": "career",
            "hook_type": "question",
            "emotion_axis": "empathy",
            "audience_fit": "office_workers",
            "scrape_quality_score": 72.0,
            "publishability_score": 81.0,
            "performance_score": 63.0,
            "final_rank_score": self.score,
            "recommended_draft_type": "insight",
        }


class _FakeFeedbackLoop:
    def __init__(self, notion_uploader, config_mgr):
        self.notion_uploader = notion_uploader
        self.config_mgr = config_mgr

    async def get_few_shot_examples(self):
        return [{"title": "winner"}]


class _FakeNotionUploader:
    instances: list["_FakeNotionUploader"] = []

    def __init__(self, config_mgr):
        self.config_mgr = config_mgr
        self.updated: list[tuple[str, dict]] = []
        self.pages = [
            {
                "page_id": "page-1",
                "title": "First",
                "memo": "memo text",
                "likes": 10,
                "scrape_quality_score": 72,
            },
            {
                "page_id": "page-2",
                "title": "Second",
                "text": "body text",
                "likes": 2,
                "scrape_quality_score": 65,
            },
        ]
        self.instances.append(self)

    async def get_recent_pages(self, *, days: int, limit: int):
        return self.pages[:limit]

    def extract_page_record(self, page):
        return page

    async def update_page_properties(self, page_id: str, properties: dict):
        self.updated.append((page_id, properties))
        return True


def _patch_recompute(monkeypatch):
    _FakeNotionUploader.instances.clear()
    build_calls = []

    def fake_build_content_profile(post_data, *, scrape_quality_score, historical_examples, ranking_weights):
        base_score = 88.0 if post_data["title"] == "First" else 77.0
        score = base_score + (5.0 if ranking_weights.get("performance") == 0.9 else 0.0)
        build_calls.append(
            {
                "post_data": post_data,
                "scrape_quality_score": scrape_quality_score,
                "historical_examples": historical_examples,
                "ranking_weights": ranking_weights,
            }
        )
        return _FakeProfile(post_data["title"], score)

    monkeypatch.setattr(recompute_scores, "ConfigManager", _FakeConfig)
    monkeypatch.setattr(recompute_scores, "NotionUploader", _FakeNotionUploader)
    monkeypatch.setattr(recompute_scores, "FeedbackLoop", _FakeFeedbackLoop)
    monkeypatch.setattr(recompute_scores, "build_content_profile", fake_build_content_profile)
    return build_calls


def test_run_dry_run_json_suppresses_notion_writes(monkeypatch, capsys):
    build_calls = _patch_recompute(monkeypatch)

    exit_code = asyncio.run(
        recompute_scores.run(
            days=30,
            limit=2,
            config_path="config.yaml",
            dry_run=True,
            json_output=True,
            sample_limit=1,
        )
    )

    assert exit_code == 0
    uploader = _FakeNotionUploader.instances[-1]
    assert uploader.updated == []
    assert len(build_calls) == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["mode"] == "dry-run"
    assert payload["runtime_notes"] == {
        "input_fixture": False,
        "scoring_dependencies_may_initialize": True,
        "dependency_scope": "notion_recent_pages_and_content_intelligence_scoring",
    }
    assert payload["safety"] == {
        "notion_reads": True,
        "notion_writes": False,
        "x_posts": False,
        "auto_publish_default": False,
        "manual_publish_required": True,
    }
    assert payload["planned"] == 2
    assert payload["updated"] == 0
    assert payload["score_update_samples"] == [
        {
            "page_id": "page-1",
            "title": "First",
            "topic_cluster": "career",
            "hook_type": "question",
            "final_rank_score": 88.0,
            "chosen_draft_type": "insight",
        }
    ]
    assert payload["operator_action"].startswith("Review planned score_update_samples")


def test_score_update_preserves_zero_scrape_quality_score(monkeypatch):
    build_calls = []

    def fake_build_content_profile(post_data, *, scrape_quality_score, historical_examples, ranking_weights):
        build_calls.append(scrape_quality_score)
        return _FakeProfile(post_data["title"], 42.0)

    monkeypatch.setattr(recompute_scores, "build_content_profile", fake_build_content_profile)

    recompute_scores._score_update_from_record(
        {
            "page_id": "page-zero",
            "title": "Zero",
            "memo": "body",
            "scrape_quality_score": 0,
        },
        top_examples=[],
        ranking_weights={},
    )

    assert build_calls == [0.0]


def test_run_input_dry_run_uses_local_records_without_notion(monkeypatch, tmp_path, capsys):
    build_calls = _patch_recompute(monkeypatch)
    input_path = tmp_path / "score_fixture.json"
    input_path.write_text(
        json.dumps(
            {
                "historical_examples": [{"title": "local winner"}],
                "records": [
                    {
                        "page_id": "fixture-1",
                        "title": "First",
                        "memo": "fixture memo",
                        "likes": 4,
                        "scrape_quality_score": 71,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    exit_code = asyncio.run(
        recompute_scores.run(
            days=30,
            limit=10,
            config_path="config.example.yaml",
            dry_run=True,
            json_output=True,
            input_path=str(input_path),
        )
    )

    assert exit_code == 0
    assert _FakeNotionUploader.instances == []
    assert build_calls[0]["historical_examples"] == [{"title": "local winner"}]
    payload = json.loads(capsys.readouterr().out)
    assert payload["input_source"] == str(input_path)
    assert payload["runtime_notes"] == {
        "input_fixture": True,
        "scoring_dependencies_may_initialize": True,
        "dependency_scope": "content_intelligence_scoring_and_optional_ml_model_cache",
        "notion_reads": False,
        "notion_writes": False,
        "zero_dependency_validation_command": "scripts/recompute_scores.py --validate-input --input <path> --json",
        "runtime_contract_gate_command": "scripts/recompute_scores.py --assert-runtime-contract --input <path> --json",
        "offline_hint": "Prepare ML model caches first before using HF_HUB_OFFLINE=1 for scoring dry-runs.",
    }
    assert payload["safety"] == {
        "notion_reads": False,
        "notion_writes": False,
        "x_posts": False,
        "auto_publish_default": False,
        "manual_publish_required": True,
    }
    assert payload["planned"] == 1
    assert payload["score_update_samples"][0]["page_id"] == "fixture-1"
    assert payload["score_update_samples"][0]["final_rank_score"] == 88.0
    assert payload["operator_action"] == "Review local fixture score_update_samples; no Notion read or write occurred."


def test_run_input_dry_run_compares_candidate_ranking_weights(monkeypatch, tmp_path, capsys):
    _patch_recompute(monkeypatch)
    input_path = tmp_path / "score_fixture.json"
    input_path.write_text(
        json.dumps(
            {
                "candidate_ranking_weights": {
                    "scrape_quality": 0.1,
                    "publishability": 0.0,
                    "performance": 0.9,
                },
                "records": [
                    {"page_id": "fixture-1", "title": "First", "memo": "fixture memo"},
                    {"page_id": "fixture-2", "title": "Second", "memo": "fixture memo"},
                ],
            }
        ),
        encoding="utf-8",
    )

    exit_code = asyncio.run(
        recompute_scores.run(
            days=30,
            limit=10,
            config_path="config.example.yaml",
            dry_run=True,
            json_output=True,
            input_path=str(input_path),
        )
    )

    assert exit_code == 0
    assert _FakeNotionUploader.instances == []
    payload = json.loads(capsys.readouterr().out)
    assert payload["runtime_notes"]["scoring_dependencies_may_initialize"] is True
    assert payload["runtime_notes"]["dependency_scope"] == "content_intelligence_scoring_and_optional_ml_model_cache"
    comparison = payload["score_comparison"]
    assert comparison["enabled"] is True
    assert comparison["candidate_ranking_weights"] == {
        "scrape_quality": 0.1,
        "publishability": 0.0,
        "performance": 0.9,
    }
    assert comparison["current_average_final_rank_score"] == 82.5
    assert comparison["candidate_average_final_rank_score"] == 87.5
    assert comparison["average_score_delta"] == 5.0
    assert comparison["improved_count"] == 2
    assert comparison["regressed_count"] == 0
    assert comparison["samples"][0] == {
        "page_id": "fixture-1",
        "title": "First",
        "current_final_rank_score": 88.0,
        "candidate_final_rank_score": 93.0,
        "score_delta": 5.0,
    }
    assert comparison["variants"]["candidate"]["signals"] == {
        "success": True,
        "provider": "local_scoring",
        "model": "ranking_weights.candidate",
        "token_cost_estimate": 0.0,
        "latency_ms": None,
        "final_rank_score": 87.5,
        "draft_quality_score": None,
        "safety_risk_flags": [],
        "duplicate_or_near_duplicate": False,
        "operator_action_required": False,
    }
    assert payload["operator_action"].startswith("Candidate ranking.weights improved")


def test_validate_input_json_reports_fixture_shape(tmp_path, capsys):
    input_path = tmp_path / "score_fixture.json"
    input_path.write_text(
        json.dumps(
            {
                "candidate_ranking_weights": {"scrape_quality": 0.3, "publishability": 0.4},
                "historical_examples": [{"title": "winner"}],
                "records": [
                    {
                        "page_id": "fixture-1",
                        "title": "First",
                        "memo": "fixture memo",
                        "scrape_quality_score": 72,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    exit_code = recompute_scores.validate_input(str(input_path), json_output=True)

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "ok"
    assert payload["ok"] is True
    assert payload["record_count"] == 1
    assert payload["historical_example_count"] == 1
    assert payload["candidate_ranking_weights_present"] is True
    assert payload["candidate_ranking_weight_keys"] == ["publishability", "scrape_quality"]
    assert payload["errors"] == []
    assert payload["safety"] == {
        "notion_reads": False,
        "notion_writes": False,
        "x_posts": False,
        "auto_publish_default": False,
        "manual_publish_required": True,
    }
    assert payload["runtime_contract"] == {
        "validation": {
            "loads_runtime_dependencies": False,
            "scoring_runs": False,
            "notion_reads": False,
            "notion_writes": False,
            "x_posts": False,
        },
        "scoring_dry_run": {
            "input_fixture": True,
            "scoring_dependencies_may_initialize": True,
            "dependency_scope": "content_intelligence_scoring_and_optional_ml_model_cache",
            "notion_reads": False,
            "notion_writes": False,
            "zero_dependency_validation_command": "scripts/recompute_scores.py --validate-input --input <path> --json",
            "runtime_contract_gate_command": "scripts/recompute_scores.py --assert-runtime-contract --input <path> --json",
            "offline_hint": "Prepare ML model caches first before using HF_HUB_OFFLINE=1 for scoring dry-runs.",
        },
    }


def test_validate_input_json_accepts_explicit_empty_records(tmp_path, capsys):
    input_path = tmp_path / "empty_records_fixture.json"
    input_path.write_text(
        json.dumps(
            {
                "candidate_ranking_weights": {"hook": 1.0},
                "historical_examples": [],
                "records": [],
            }
        ),
        encoding="utf-8",
    )

    exit_code = recompute_scores.validate_input(str(input_path), json_output=True)

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "ok"
    assert payload["ok"] is True
    assert payload["record_count"] == 0
    assert payload["historical_example_count"] == 0
    assert payload["candidate_ranking_weights_present"] is True
    assert payload["candidate_ranking_weight_keys"] == ["hook"]
    assert payload["errors"] == []
    assert payload["warnings"] == ["records_empty"]


def test_validate_input_json_rejects_falsey_non_array_examples(tmp_path, capsys):
    input_path = tmp_path / "invalid_examples_fixture.json"
    input_path.write_text(
        json.dumps(
            {
                "candidate_ranking_weights": {"hook": 1.0},
                "historical_examples": "",
                "records": [{"page_id": "fixture-1", "title": "First", "memo": "fixture memo"}],
            }
        ),
        encoding="utf-8",
    )

    exit_code = recompute_scores.validate_input(str(input_path), json_output=True)

    assert exit_code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "fail"
    assert payload["ok"] is False
    assert payload["errors"] == ["recompute_scores historical_examples must be an array"]
    assert payload["warnings"] == []
    assert payload["operator_action"] == "Fix recompute_scores fixture errors before scoring dry-run."


def test_assert_runtime_contract_reports_zero_runtime_gate(tmp_path, capsys):
    input_path = tmp_path / "score_fixture.json"
    input_path.write_text(
        json.dumps(
            {
                "candidate_ranking_weights": {"performance": 0.9},
                "records": [{"page_id": "fixture-1", "title": "First", "memo": "fixture memo"}],
            }
        ),
        encoding="utf-8",
    )

    assert recompute_scores.assert_runtime_contract(str(input_path), json_output=True) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "ok"
    assert payload["ok"] is True
    assert payload["gate_errors"] == []
    assert payload["runtime_contract"]["validation"]["loads_runtime_dependencies"] is False
    assert payload["runtime_contract"]["validation"]["scoring_runs"] is False
    assert payload["runtime_contract"]["scoring_dry_run"]["scoring_dependencies_may_initialize"] is True
    assert payload["safety"]["notion_reads"] is False
    assert payload["safety"]["notion_writes"] is False


def test_assert_runtime_contract_fails_when_fixture_invalid(tmp_path, capsys):
    input_path = tmp_path / "score_fixture.json"
    input_path.write_text(json.dumps({"records": [{"title": ""}]}), encoding="utf-8")

    assert recompute_scores.assert_runtime_contract(str(input_path), json_output=True) == 1

    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "fail"
    assert payload["ok"] is False
    assert "validation_not_ok" in payload["gate_errors"]
    assert "validation_errors_present" in payload["gate_errors"]
    assert payload["operator_action"] == "Fix runtime contract gate errors before scoring dry-run."


def test_write_sample_input_creates_valid_fixture(tmp_path, capsys):
    output_path = tmp_path / "recompute_scores_fixture.json"

    exit_code = recompute_scores.write_sample_input(str(output_path), json_output=True)

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "ok"
    assert payload["ok"] is True
    assert payload["output_path"] == str(output_path)
    assert payload["overwritten"] is False
    assert payload["validation"]["record_count"] == 2
    assert payload["validation"]["candidate_ranking_weights_present"] is True
    assert payload["safety"]["notion_reads"] is False
    assert payload["safety"]["notion_writes"] is False
    assert payload["runtime_contract"]["validation"]["loads_runtime_dependencies"] is False
    assert payload["runtime_contract"]["scoring_dry_run"]["scoring_dependencies_may_initialize"] is True
    assert payload["runtime_contract"]["scoring_dry_run"]["runtime_contract_gate_command"] == (
        "scripts/recompute_scores.py --assert-runtime-contract --input <path> --json"
    )
    assert payload["operator_action"] == (
        "Run recompute_scores --validate-input, then --assert-runtime-contract, then --input with --dry-run --json."
    )

    generated = json.loads(output_path.read_text(encoding="utf-8"))
    assert generated["schema_version"] == 1
    assert len(generated["records"]) == 2
    assert recompute_scores.validate_input(str(output_path), json_output=True) == 0


def test_generated_sample_input_validates_and_scores_without_notion(monkeypatch, tmp_path, capsys):
    build_calls = _patch_recompute(monkeypatch)
    output_path = tmp_path / "recompute_scores_fixture.json"

    assert recompute_scores.write_sample_input(str(output_path), json_output=True) == 0
    writer_payload = json.loads(capsys.readouterr().out)
    assert writer_payload["ok"] is True
    assert writer_payload["validation"]["record_count"] == 2

    assert recompute_scores.validate_input(str(output_path), json_output=True) == 0
    validation_payload = json.loads(capsys.readouterr().out)
    assert validation_payload["ok"] is True
    assert validation_payload["candidate_ranking_weights_present"] is True
    assert validation_payload["safety"]["notion_reads"] is False
    assert validation_payload["runtime_contract"]["validation"]["scoring_runs"] is False
    assert validation_payload["runtime_contract"]["scoring_dry_run"]["dependency_scope"] == (
        "content_intelligence_scoring_and_optional_ml_model_cache"
    )
    assert validation_payload["runtime_contract"]["scoring_dry_run"]["runtime_contract_gate_command"] == (
        "scripts/recompute_scores.py --assert-runtime-contract --input <path> --json"
    )
    assert validation_payload["operator_action"] == (
        "Run recompute_scores --assert-runtime-contract, then --input with --dry-run --json when ready."
    )

    exit_code = asyncio.run(
        recompute_scores.run(
            days=30,
            limit=10,
            config_path="config.example.yaml",
            dry_run=True,
            json_output=True,
            input_path=str(output_path),
        )
    )

    assert exit_code == 0
    assert _FakeNotionUploader.instances == []
    assert len(build_calls) == 4
    payload = json.loads(capsys.readouterr().out)
    assert payload["mode"] == "dry-run"
    assert payload["input_source"] == str(output_path)
    assert payload["planned"] == 2
    assert payload["updated"] == 0
    assert payload["runtime_notes"]["input_fixture"] is True
    assert payload["runtime_notes"]["notion_reads"] is False
    assert "HF_HUB_OFFLINE=1" in payload["runtime_notes"]["offline_hint"]
    assert payload["safety"] == {
        "notion_reads": False,
        "notion_writes": False,
        "x_posts": False,
        "auto_publish_default": False,
        "manual_publish_required": True,
    }
    comparison = payload["score_comparison"]
    assert comparison["enabled"] is True
    assert comparison["candidate_ranking_weights"] == {
        "scrape_quality": 0.25,
        "publishability": 0.45,
        "performance": 0.3,
    }
    assert comparison["samples"][0]["page_id"] == "fixture-1"
    assert comparison["variants"]["candidate"]["signals"]["provider"] == "local_scoring"
    assert comparison["variants"]["candidate"]["signals"]["token_cost_estimate"] == 0.0


def test_validate_input_json_reports_fixable_record_errors(tmp_path, capsys):
    input_path = tmp_path / "score_fixture.json"
    input_path.write_text(
        json.dumps(
            {
                "records": [
                    {
                        "title": "",
                        "memo": "",
                        "scrape_quality_score": "bad",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    exit_code = recompute_scores.validate_input(str(input_path), json_output=True)

    assert exit_code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "fail"
    assert payload["ok"] is False
    assert payload["errors"] == ["records[0].page_id_missing", "records[0].scrape_quality_score_not_numeric"]
    assert payload["warnings"] == [
        "records[0].title_missing",
        "records[0].content_missing",
        "candidate_ranking_weights_missing",
    ]
    assert payload["operator_action"] == "Fix recompute_scores fixture errors before scoring dry-run."


def test_run_input_requires_dry_run(monkeypatch, tmp_path):
    _patch_recompute(monkeypatch)
    input_path = tmp_path / "score_fixture.json"
    input_path.write_text(json.dumps([{"page_id": "fixture-1", "title": "First"}]), encoding="utf-8")

    with pytest.raises(ValueError, match="--input requires --dry-run"):
        asyncio.run(
            recompute_scores.run(
                days=30,
                limit=1,
                config_path="config.example.yaml",
                input_path=str(input_path),
            )
        )

    assert _FakeNotionUploader.instances == []


def test_run_default_write_path_keeps_existing_summary_prefix(monkeypatch, capsys):
    _patch_recompute(monkeypatch)

    exit_code = asyncio.run(
        recompute_scores.run(
            days=7,
            limit=1,
            config_path="config.yaml",
        )
    )

    assert exit_code == 0
    uploader = _FakeNotionUploader.instances[-1]
    assert uploader.updated == [
        (
            "page-1",
            {
                "topic_cluster": "career",
                "hook_type": "question",
                "emotion_axis": "empathy",
                "audience_fit": "office_workers",
                "scrape_quality_score": 72.0,
                "publishability_score": 81.0,
                "performance_score": 63.0,
                "final_rank_score": 88.0,
                "chosen_draft_type": "insight",
            },
        )
    ]
    output = capsys.readouterr().out.strip()
    assert output.startswith("recompute_scores complete: updated=1 total=1 days=7")
    assert "mode=write" in output
    assert "notion_writes=true" in output
    assert "scoring_dependencies=may_initialize" in output
    assert "operator_action=No operator action required." in output


def test_direct_script_help_works_without_project_pythonpath():
    result = subprocess.run(
        [sys.executable, str(_BTX_ROOT / "scripts" / "recompute_scores.py"), "--help"],
        cwd=_BTX_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "--dry-run" in result.stdout
    assert "--json" in result.stdout
    assert "--input" in result.stdout
    assert "--validate-input" in result.stdout
    assert "--assert-runtime-contract" in result.stdout
    assert "--write-sample-input" in result.stdout


def test_direct_script_validate_input_outputs_json_without_loading_env(tmp_path):
    input_path = tmp_path / "score_fixture.json"
    input_path.write_text(
        json.dumps(
            {
                "candidate_ranking_weights": {"performance": 0.9},
                "records": [{"page_id": "fixture-1", "title": "First", "memo": "fixture memo"}],
            }
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(_BTX_ROOT / "scripts" / "recompute_scores.py"),
            "--validate-input",
            "--input",
            str(input_path),
            "--json",
        ],
        cwd=_BTX_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["safety"]["notion_reads"] is False
    assert payload["safety"]["notion_writes"] is False
    assert payload["runtime_contract"]["validation"]["loads_runtime_dependencies"] is False
    assert payload["runtime_contract"]["scoring_dry_run"]["scoring_dependencies_may_initialize"] is True
    assert "loguru is not installed" not in result.stdout
    assert "loguru is not installed" not in result.stderr


def test_direct_script_assert_runtime_contract_outputs_json_without_loading_env(tmp_path):
    input_path = tmp_path / "score_fixture.json"
    input_path.write_text(
        json.dumps(
            {
                "candidate_ranking_weights": {"performance": 0.9},
                "records": [{"page_id": "fixture-1", "title": "First", "memo": "fixture memo"}],
            }
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(_BTX_ROOT / "scripts" / "recompute_scores.py"),
            "--assert-runtime-contract",
            "--input",
            str(input_path),
            "--json",
        ],
        cwd=_BTX_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["gate_errors"] == []
    assert payload["runtime_contract"]["validation"]["loads_runtime_dependencies"] is False
    assert payload["runtime_contract"]["validation"]["scoring_runs"] is False
    assert payload["runtime_contract"]["scoring_dry_run"]["scoring_dependencies_may_initialize"] is True
    assert "loguru is not installed" not in result.stdout
    assert "loguru is not installed" not in result.stderr


def test_direct_script_write_sample_input_outputs_clean_json(tmp_path):
    output_path = tmp_path / "recompute_scores_fixture.json"

    result = subprocess.run(
        [
            sys.executable,
            str(_BTX_ROOT / "scripts" / "recompute_scores.py"),
            "--write-sample-input",
            str(output_path),
            "--json",
        ],
        cwd=_BTX_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["output_path"] == str(output_path)
    assert output_path.exists()
    assert "loguru is not installed" not in result.stdout
    assert "loguru is not installed" not in result.stderr


def test_direct_script_validate_input_requires_input():
    result = subprocess.run(
        [sys.executable, str(_BTX_ROOT / "scripts" / "recompute_scores.py"), "--validate-input"],
        cwd=_BTX_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 2
    assert "--validate-input requires --input" in result.stderr


def test_direct_script_assert_runtime_contract_requires_input():
    result = subprocess.run(
        [sys.executable, str(_BTX_ROOT / "scripts" / "recompute_scores.py"), "--assert-runtime-contract"],
        cwd=_BTX_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 2
    assert "--assert-runtime-contract requires --input" in result.stderr


def test_direct_script_rejects_input_without_dry_run(tmp_path):
    input_path = tmp_path / "score_fixture.json"
    input_path.write_text(json.dumps([{"page_id": "fixture-1", "title": "First"}]), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(_BTX_ROOT / "scripts" / "recompute_scores.py"),
            "--config",
            "config.example.yaml",
            "--input",
            str(input_path),
        ],
        cwd=_BTX_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 2
    assert "--input requires --dry-run" in result.stderr
