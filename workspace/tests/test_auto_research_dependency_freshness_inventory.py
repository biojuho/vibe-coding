"""Unit tests for the auto-research dependency freshness inventory helper."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / ".agents" / "skills" / "auto-research" / "scripts" / "dependency_freshness_inventory.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("dependency_freshness_inventory", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["dependency_freshness_inventory"] = module
    spec.loader.exec_module(module)
    return module


dependency_freshness_inventory = _load_module()


def _write_package(path: Path, dependencies: dict[str, str] | None = None) -> None:
    path.mkdir(parents=True, exist_ok=True)
    package = {
        "name": path.name,
        "dependencies": dependencies or {"example": "^1.0.0"},
    }
    (path / "package.json").write_text(json.dumps(package), encoding="utf-8")


def _npm_result(payload: dict[str, object]) -> dict[str, object]:
    return {
        "available": True,
        "returncode": 1 if payload else 0,
        "stdout": json.dumps(payload),
        "stderr": "",
    }


def test_patch_minor_wanted_update_is_candidate() -> None:
    result = dependency_freshness_inventory.classify_dependency(
        "react",
        {"current": "19.2.3", "wanted": "19.2.7", "latest": "19.2.7"},
    )

    assert result["classification"] == "adopt_patch_minor"
    assert result["wanted_delta"] == "patch"
    assert result["candidate"] is True
    assert result["deferred"] is False


def test_latest_major_only_is_deferred_migration() -> None:
    result = dependency_freshness_inventory.classify_dependency(
        "eslint",
        {"current": "9.39.4", "wanted": "9.39.4", "latest": "10.4.1"},
    )

    assert result["classification"] == "defer_major_migration"
    assert result["latest_delta"] == "major"
    assert result["candidate"] is False
    assert result["deferred"] is True


def test_prerelease_channel_mismatch_is_deferred() -> None:
    result = dependency_freshness_inventory.classify_dependency(
        "next-auth",
        {"current": "5.0.0-beta.31", "wanted": "5.0.0-beta.31", "latest": "4.24.14"},
    )

    assert result["classification"] == "defer_channel_mismatch"
    assert result["candidate"] is False
    assert result["deferred"] is True


def test_build_inventory_summarizes_candidates_and_deferred(tmp_path: Path) -> None:
    _write_package(tmp_path / "projects" / "word-chain")
    _write_package(tmp_path / "projects" / "hanwoo-dashboard")

    payloads = {
        "word-chain": _npm_result(
            {
                "react": {
                    "current": "19.2.3",
                    "wanted": "19.2.7",
                    "latest": "19.2.7",
                }
            }
        ),
        "hanwoo-dashboard": _npm_result(
            {
                "typescript": {
                    "current": "5.9.3",
                    "wanted": "5.9.3",
                    "latest": "6.0.3",
                }
            }
        ),
    }

    def runner(path: Path, timeout: int) -> dict[str, object]:
        assert timeout == 60
        return payloads[path.name]

    result = dependency_freshness_inventory.build_inventory(tmp_path, runner=runner)

    assert result["summary"]["package_project_count"] == 2
    assert result["summary"]["candidate_dependency_count"] == 1
    assert result["summary"]["deferred_dependency_count"] == 1
    by_path = {project["path"]: project for project in result["projects"]}
    assert by_path["projects/word-chain"]["status"] == "candidate"
    assert by_path["projects/hanwoo-dashboard"]["status"] == "deferred_only"
    assert result["recommendations"] == [
        "Run a focused patch/minor dependency update experiment for: projects/word-chain (react)"
    ]


def test_empty_outdated_payload_marks_project_clean(tmp_path: Path) -> None:
    _write_package(tmp_path / "projects" / "suika-game-v2")

    result = dependency_freshness_inventory.build_inventory(tmp_path, runner=lambda _path, _timeout: _npm_result({}))

    assert result["summary"]["clean_project_count"] == 1
    assert result["projects"][0]["status"] == "clean"
    assert result["recommendations"] == []


def test_invalid_npm_json_marks_project_unavailable(tmp_path: Path) -> None:
    _write_package(tmp_path / "projects" / "knowledge-dashboard")

    result = dependency_freshness_inventory.build_inventory(
        tmp_path,
        runner=lambda _path, _timeout: {
            "available": True,
            "returncode": 1,
            "stdout": "not json",
            "stderr": "",
        },
    )

    assert result["projects"][0]["status"] == "unavailable"
    assert result["summary"]["unavailable_project_count"] == 1
    assert result["recommendations"] == [
        "Fix npm outdated availability or JSON output for: projects/knowledge-dashboard"
    ]
