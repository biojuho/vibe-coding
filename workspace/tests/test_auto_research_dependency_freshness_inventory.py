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


def _write_package_lock(path: Path, packages: dict[str, object]) -> None:
    payload = {
        "name": path.name,
        "lockfileVersion": 3,
        "packages": packages,
    }
    (path / "package-lock.json").write_text(json.dumps(payload), encoding="utf-8")


def _npm_result(payload: dict[str, object]) -> dict[str, object]:
    return {
        "available": True,
        "returncode": 1 if payload else 0,
        "stdout": json.dumps(payload),
        "stderr": "",
    }


def _dist_tags(payload: dict[str, str]) -> dict[str, object]:
    return {
        "available": True,
        "returncode": 0,
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


def test_current_prerelease_dist_tag_is_not_deferred(tmp_path: Path) -> None:
    _write_package(tmp_path / "projects" / "hanwoo-dashboard", {"next-auth": "5.0.0-beta.31"})

    result = dependency_freshness_inventory.build_inventory(
        tmp_path,
        runner=lambda _path, _timeout: _npm_result(
            {
                "next-auth": {
                    "current": "5.0.0-beta.31",
                    "wanted": "5.0.0-beta.31",
                    "latest": "4.24.14",
                }
            }
        ),
        tag_runner=lambda _path, package_name, _timeout: _dist_tags(
            {"latest": "4.24.14", "beta": "5.0.0-beta.31"} if package_name == "next-auth" else {}
        ),
    )

    project = result["projects"][0]
    dependency = project["dependencies"][0]
    assert project["status"] == "clean"
    assert result["summary"]["deferred_dependency_count"] == 0
    assert dependency["classification"] == "current_prerelease_channel"
    assert dependency["dist_tag_channel"] == "beta"
    assert dependency["dist_tag_version"] == "5.0.0-beta.31"
    assert dependency["candidate"] is False
    assert dependency["deferred"] is False
    assert result["recommendations"] == []


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


def test_major_only_deferred_recommendation_names_major_migrations(tmp_path: Path) -> None:
    _write_package(tmp_path / "projects" / "hanwoo-dashboard")
    _write_package(tmp_path / "projects" / "knowledge-dashboard")

    payloads = {
        "hanwoo-dashboard": _npm_result(
            {
                "eslint": {
                    "current": "9.39.4",
                    "wanted": "9.39.4",
                    "latest": "10.4.1",
                },
                "next-auth": {
                    "current": "5.0.0-beta.31",
                    "wanted": "5.0.0-beta.31",
                    "latest": "4.24.14",
                },
            }
        ),
        "knowledge-dashboard": _npm_result(
            {
                "eslint": {
                    "current": "9.39.4",
                    "wanted": "9.39.4",
                    "latest": "10.4.1",
                }
            }
        ),
    }

    result = dependency_freshness_inventory.build_inventory(
        tmp_path,
        runner=lambda path, _timeout: payloads[path.name],
        tag_runner=lambda _path, package_name, _timeout: _dist_tags(
            {"latest": "4.24.14", "beta": "5.0.0-beta.31"} if package_name == "next-auth" else {}
        ),
    )

    assert result["summary"]["deferred_dependency_count"] == 2
    assert result["recommendations"] == [
        "No direct npm patch/minor adoption candidates; defer major migrations for: "
        "projects/hanwoo-dashboard, projects/knowledge-dashboard"
    ]


def test_peer_blocked_major_recommendation_waits_for_upstream_support(tmp_path: Path) -> None:
    hanwoo_path = tmp_path / "projects" / "hanwoo-dashboard"
    knowledge_path = tmp_path / "projects" / "knowledge-dashboard"
    _write_package(hanwoo_path, {"eslint": "^9.39.4"})
    _write_package(knowledge_path, {"eslint": "^9.39.4"})
    for project_path in (hanwoo_path, knowledge_path):
        _write_package_lock(
            project_path,
            {
                "": {
                    "name": project_path.name,
                    "dependencies": {"eslint": "^9.39.4"},
                },
                "node_modules/eslint-plugin-react": {
                    "version": "7.37.5",
                    "peerDependencies": {"eslint": "^3 || ^4 || ^5 || ^6 || ^7 || ^8 || ^9.7"},
                },
            },
        )

    result = dependency_freshness_inventory.build_inventory(
        tmp_path,
        runner=lambda _path, _timeout: _npm_result(
            {
                "eslint": {
                    "current": "9.39.4",
                    "wanted": "9.39.4",
                    "latest": "10.4.1",
                }
            }
        ),
    )

    assert result["summary"]["candidate_dependency_count"] == 0
    assert result["summary"]["deferred_dependency_count"] == 2
    assert result["recommendations"] == [
        "No direct npm patch/minor adoption candidates; wait for upstream peer support before "
        "major migrations for: projects/hanwoo-dashboard (eslint: 1 peer blocker(s)); "
        "projects/knowledge-dashboard (eslint: 1 peer blocker(s))"
    ]


def test_deferred_eslint_major_reports_lockfile_peer_blockers(tmp_path: Path) -> None:
    project_path = tmp_path / "projects" / "knowledge-dashboard"
    _write_package(project_path, {"eslint": "^9.39.4"})
    _write_package_lock(
        project_path,
        {
            "": {
                "name": "knowledge-dashboard",
                "dependencies": {"eslint": "^9.39.4"},
            },
            "node_modules/eslint-config-next": {
                "version": "16.2.7",
                "peerDependencies": {"eslint": ">=9.0.0"},
            },
            "node_modules/eslint-config-next/node_modules/eslint-plugin-react": {
                "version": "7.37.5",
                "peerDependencies": {"eslint": "^3 || ^4 || ^5 || ^6 || ^7 || ^8 || ^9.7"},
            },
            "node_modules/eslint-plugin-react-hooks": {
                "version": "7.1.1",
                "peerDependencies": {"eslint": "^3 || ^4 || ^5 || ^6 || ^7 || ^8 || ^9 || ^9.7 || ^10.0.0"},
            },
        },
    )

    result = dependency_freshness_inventory.build_inventory(
        tmp_path,
        runner=lambda _path, _timeout: _npm_result(
            {
                "eslint": {
                    "current": "9.39.4",
                    "wanted": "9.39.4",
                    "latest": "10.4.1",
                }
            }
        ),
    )

    dependency = result["projects"][0]["dependencies"][0]
    assert dependency["classification"] == "defer_major_migration"
    assert dependency["peer_blocker_check"] == "blocked"
    assert dependency["peer_target_major"] == 10
    assert dependency["peer_blocker_count"] == 1
    assert dependency["peer_blockers"] == [
        {
            "package": "eslint-plugin-react",
            "version": "7.37.5",
            "peer_range": "^3 || ^4 || ^5 || ^6 || ^7 || ^8 || ^9.7",
            "path": "node_modules/eslint-config-next/node_modules/eslint-plugin-react",
        }
    ]
    assert "do not allow eslint major 10" in dependency["reason"]


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
