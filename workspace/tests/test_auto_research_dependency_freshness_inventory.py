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


def _peer_metadata(version: str, peer_dependencies: dict[str, str]) -> dict[str, object]:
    return {
        "available": True,
        "returncode": 0,
        "stdout": json.dumps({"version": version, "peerDependencies": peer_dependencies}),
        "stderr": "",
    }


def test_peer_range_alternative_allows_major_contract() -> None:
    allows_major = dependency_freshness_inventory._peer_range_alternative_allows_major

    assert allows_major("", 10) is False
    assert allows_major("*", 10) is True
    assert allows_major("^10.0.0", 10) is True
    assert allows_major("<10", 10) is False
    assert allows_major(">=9 <11", 10) is True


def test_patch_minor_wanted_update_is_candidate() -> None:
    result = dependency_freshness_inventory.classify_dependency(
        "react",
        {"current": "19.2.3", "wanted": "19.2.7", "latest": "19.2.7"},
    )

    assert result["classification"] == "adopt_patch_minor"
    assert result["wanted_delta"] == "patch"
    assert result["candidate"] is True
    assert result["deferred"] is False


def test_missing_local_current_with_wanted_equal_latest_is_not_manual_inspect() -> None:
    result = dependency_freshness_inventory.classify_dependency(
        "matter-js",
        {"wanted": "0.20.0", "latest": "0.20.0"},
    )

    assert result["classification"] == "range_current_missing_install"
    assert result["action"] == "none"
    assert result["candidate"] is False
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


def test_unreadable_package_json_is_treated_as_empty_metadata(tmp_path: Path, monkeypatch) -> None:
    project_path = tmp_path / "projects" / "locked-dependencies"
    _write_package(project_path, {"react": "^19.0.0"})
    original_read_text = dependency_freshness_inventory.Path.read_text

    def fake_read_text(path: Path, *args, **kwargs):
        if path == project_path / "package.json":
            raise OSError("locked")
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(dependency_freshness_inventory.Path, "read_text", fake_read_text)

    result = dependency_freshness_inventory.build_inventory(
        tmp_path,
        runner=lambda _path, _timeout: _npm_result({}),
    )

    assert result["summary"]["package_project_count"] == 1
    assert result["summary"]["clean_project_count"] == 1
    assert result["projects"][0]["path"] == "projects/locked-dependencies"
    assert result["projects"][0]["status"] == "clean"
    assert result["projects"][0]["dependencies"] == []
    assert result["recommendations"] == []


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
        peer_metadata_runner=lambda _path, _package_name, _timeout: _peer_metadata(
            "7.37.5", {"eslint": "^3 || ^4 || ^5 || ^6 || ^7 || ^8 || ^9.7"}
        ),
    )

    assert result["summary"]["candidate_dependency_count"] == 0
    assert result["summary"]["deferred_dependency_count"] == 2
    assert result["summary"]["peer_blocker_latest_supported_count"] == 0
    assert result["summary"]["peer_blocker_latest_blocked_count"] == 2
    assert result["recommendations"] == [
        "No direct npm patch/minor adoption candidates; wait for upstream peer support before "
        "major migrations for: projects/hanwoo-dashboard "
        "(eslint: 1 peer blocker(s), 0/1 latest-supported, 1 still blocked); "
        "projects/knowledge-dashboard (eslint: 1 peer blocker(s), 0/1 latest-supported, 1 still blocked)"
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
        peer_metadata_runner=lambda _path, package_name, _timeout: (
            _peer_metadata("7.37.5", {"eslint": "^3 || ^4 || ^5 || ^6 || ^7 || ^8 || ^9.7"})
            if package_name == "eslint-plugin-react"
            else _peer_metadata("7.1.1", {"eslint": "^3 || ^4 || ^5 || ^6 || ^7 || ^8 || ^9 || ^10.0.0"})
        ),
    )

    dependency = result["projects"][0]["dependencies"][0]
    assert dependency["classification"] == "defer_major_migration"
    assert dependency["peer_blocker_check"] == "blocked"
    assert dependency["peer_target_major"] == 10
    assert dependency["peer_blocker_count"] == 1
    assert dependency["peer_blocker_latest_check"] == "still_blocked"
    assert dependency["peer_blocker_latest_supported_count"] == 0
    assert dependency["peer_blocker_latest_blocked_count"] == 1
    assert dependency["peer_blocker_latest_unavailable_count"] == 0
    assert dependency["peer_blockers"] == [
        {
            "package": "eslint-plugin-react",
            "version": "7.37.5",
            "peer_range": "^3 || ^4 || ^5 || ^6 || ^7 || ^8 || ^9.7",
            "path": "node_modules/eslint-config-next/node_modules/eslint-plugin-react",
            "latest_version": "7.37.5",
            "latest_peer_range": "^3 || ^4 || ^5 || ^6 || ^7 || ^8 || ^9.7",
            "latest_peer_allows_target": False,
            "latest_peer_check": "blocks_target_major",
        }
    ]
    assert "do not allow eslint major 10" in dependency["reason"]


def test_deferred_eslint_major_reports_partial_latest_peer_support(tmp_path: Path) -> None:
    project_path = tmp_path / "projects" / "hanwoo-dashboard"
    _write_package(project_path, {"eslint": "^9.39.4"})
    _write_package_lock(
        project_path,
        {
            "": {
                "name": "hanwoo-dashboard",
                "dependencies": {"eslint": "^9.39.4"},
            },
            "node_modules/eslint-plugin-react": {
                "version": "7.37.5",
                "peerDependencies": {"eslint": "^3 || ^4 || ^5 || ^6 || ^7 || ^8 || ^9.7"},
            },
            "node_modules/eslint-plugin-react-hooks": {
                "version": "7.0.1",
                "peerDependencies": {"eslint": "^3 || ^4 || ^5 || ^6 || ^7 || ^8 || ^9"},
            },
        },
    )

    latest_metadata = {
        "eslint-plugin-react": _peer_metadata("7.37.5", {"eslint": "^3 || ^4 || ^5 || ^6 || ^7 || ^8 || ^9.7"}),
        "eslint-plugin-react-hooks": _peer_metadata(
            "7.1.1", {"eslint": "^3 || ^4 || ^5 || ^6 || ^7 || ^8 || ^9 || ^10.0.0"}
        ),
    }

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
        peer_metadata_runner=lambda _path, package_name, _timeout: latest_metadata[package_name],
    )

    dependency = result["projects"][0]["dependencies"][0]
    checks_by_package = {blocker["package"]: blocker for blocker in dependency["peer_blockers"]}
    assert dependency["peer_blocker_latest_check"] == "partial_upstream_support"
    assert dependency["peer_blocker_latest_supported_count"] == 1
    assert dependency["peer_blocker_latest_blocked_count"] == 1
    assert dependency["peer_blocker_latest_unavailable_count"] == 0
    assert result["summary"]["peer_blocker_latest_supported_count"] == 1
    assert result["summary"]["peer_blocker_latest_blocked_count"] == 1
    assert checks_by_package["eslint-plugin-react-hooks"]["latest_version"] == "7.1.1"
    assert checks_by_package["eslint-plugin-react-hooks"]["latest_peer_check"] == "allows_target_major"
    assert checks_by_package["eslint-plugin-react-hooks"]["latest_peer_allows_target"] is True
    assert "latest metadata shows 1 peer blocker(s) now allow the target major" in dependency["reason"]
    assert result["recommendations"] == [
        "No direct npm patch/minor adoption candidates; wait for upstream peer support before "
        "major migrations for: projects/hanwoo-dashboard "
        "(eslint: 2 peer blocker(s), 1/2 latest-supported, 1 still blocked)"
    ]


def test_peer_blocker_dependency_label_includes_latest_status_counts() -> None:
    dependency = {
        "name": "eslint",
        "peer_blocker_count": 3,
        "peer_blocker_latest_check": "partial_upstream_support",
        "peer_blocker_latest_supported_count": 1,
        "peer_blocker_latest_blocked_count": 1,
        "peer_blocker_latest_unavailable_count": 1,
    }

    assert (
        dependency_freshness_inventory._peer_blocker_dependency_label(dependency)
        == "eslint: 3 peer blocker(s), 1/3 latest-supported, 1 still blocked, 1 unavailable"
    )


def test_runtime_blocking_recommendations_preserve_message_order_and_count() -> None:
    deferred_projects = [
        {
            "path": "projects/root",
            "dependencies": [
                {
                    "name": "turbo",
                    "classification": "runtime_version_mismatch",
                    "declared_version": "2.9.17",
                    "runtime_version": "2.9.16",
                }
            ],
        },
        {
            "path": "projects/app",
            "dependencies": [
                {
                    "name": "turbo",
                    "classification": "defer_latest_runtime_mismatch",
                    "latest": "2.9.17",
                    "runtime_version": "2.9.16",
                }
            ],
        },
    ]

    recommendations, runtime_blocking_count = dependency_freshness_inventory._runtime_blocking_recommendations(
        deferred_projects
    )

    assert runtime_blocking_count == 2
    assert recommendations == [
        "Resolve local dependency runtime mismatches before adoption for: "
        "projects/root (turbo: expected 2.9.17, runtime 2.9.16)",
        "Defer latest binary dependency candidates with known runtime mismatch for: "
        "projects/app (turbo: latest 2.9.17, runtime 2.9.16)",
    ]


def test_deferred_recommendation_project_groups_skip_runtime_blockers() -> None:
    projects = [
        {
            "path": "projects/peer-only",
            "dependencies": [
                {
                    "name": "eslint",
                    "deferred": True,
                    "classification": "defer_major_migration",
                    "latest_delta": "major",
                    "peer_blocker_check": "blocked",
                    "peer_blocker_count": 1,
                },
                {
                    "name": "turbo",
                    "deferred": True,
                    "classification": "runtime_version_mismatch",
                },
            ],
        },
        {
            "path": "projects/mixed",
            "dependencies": [
                {
                    "name": "next-auth",
                    "deferred": True,
                    "classification": "defer_channel_mismatch",
                    "latest_delta": "major",
                }
            ],
        },
    ]

    peer_blocked_projects, other_deferred_projects = (
        dependency_freshness_inventory._deferred_recommendation_project_groups(projects)
    )

    assert peer_blocked_projects == ["projects/peer-only (eslint: 1 peer blocker(s))"]
    assert other_deferred_projects == ["projects/mixed"]


def test_deferred_recommendation_label_names_classification_mix() -> None:
    label = dependency_freshness_inventory._deferred_recommendation_label

    assert label({"defer_major_migration", "defer_channel_mismatch"}) == "major or channel migrations"
    assert label({"defer_channel_mismatch"}) == "channel migrations"
    assert label({"defer_major_migration"}) == "major migrations"
    assert label({"inspect_manually"}) == "manual dependency inspections"


def test_empty_outdated_payload_marks_project_clean(tmp_path: Path) -> None:
    _write_package(tmp_path / "projects" / "suika-game-v2")

    result = dependency_freshness_inventory.build_inventory(tmp_path, runner=lambda _path, _timeout: _npm_result({}))

    assert result["summary"]["clean_project_count"] == 1
    assert result["projects"][0]["status"] == "clean"
    assert result["recommendations"] == []


def test_runtime_version_mismatch_blocks_clean_dependency_adoption(tmp_path: Path) -> None:
    _write_package(tmp_path, {"turbo": "^2.9.17"})

    result = dependency_freshness_inventory.build_inventory(
        tmp_path,
        runner=lambda _path, _timeout: _npm_result({}),
        runtime_runner=lambda _path, _package_name, _timeout: {
            "available": True,
            "returncode": 0,
            "stdout": "2.9.16",
            "stderr": "",
        },
    )

    project = result["projects"][0]
    dependency = project["dependencies"][0]
    assert project["status"] == "deferred_only"
    assert result["summary"]["runtime_mismatch_dependency_count"] == 1
    assert dependency["classification"] == "runtime_version_mismatch"
    assert dependency["runtime_version"] == "2.9.16"
    assert dependency["declared_version"] == "2.9.17"
    assert dependency["candidate"] is False
    assert dependency["deferred"] is True
    assert result["recommendations"] == [
        "Resolve local dependency runtime mismatches before adoption for: . (turbo: expected 2.9.17, runtime 2.9.16)"
    ]


def test_matching_runtime_version_keeps_clean_dependency_project_clean(tmp_path: Path) -> None:
    _write_package(tmp_path, {"turbo": "^2.9.17"})

    result = dependency_freshness_inventory.build_inventory(
        tmp_path,
        runner=lambda _path, _timeout: _npm_result({}),
        runtime_runner=lambda _path, _package_name, _timeout: {
            "available": True,
            "returncode": 0,
            "stdout": "2.9.17",
            "stderr": "",
        },
    )

    assert result["summary"]["runtime_mismatch_dependency_count"] == 0
    assert result["projects"][0]["status"] == "clean"
    assert result["projects"][0]["dependencies"] == []
    assert result["recommendations"] == []


def test_runtime_mismatch_is_not_listed_as_major_migration(tmp_path: Path) -> None:
    _write_package(tmp_path, {"turbo": "^2.9.17"})
    _write_package(tmp_path / "projects" / "knowledge-dashboard")
    root = tmp_path.resolve()

    def runner(path: Path, _timeout: int) -> dict[str, object]:
        if path.resolve() == root:
            return _npm_result({})
        return _npm_result(
            {
                "typescript": {
                    "current": "5.9.3",
                    "wanted": "5.9.3",
                    "latest": "6.0.3",
                }
            }
        )

    result = dependency_freshness_inventory.build_inventory(
        tmp_path,
        runner=runner,
        runtime_runner=lambda _path, _package_name, _timeout: {
            "available": True,
            "returncode": 0,
            "stdout": "2.9.16",
            "stderr": "",
        },
    )

    assert result["recommendations"] == [
        "Resolve local dependency runtime mismatches before adoption for: . (turbo: expected 2.9.17, runtime 2.9.16)",
        "No direct npm patch/minor adoption candidates; defer major migrations for: projects/knowledge-dashboard",
    ]


def test_known_windows_latest_runtime_mismatch_defers_candidate(tmp_path: Path, monkeypatch) -> None:
    _write_package(tmp_path, {"turbo": "^2.9.16"})
    monkeypatch.setattr(dependency_freshness_inventory.sys, "platform", "win32")
    monkeypatch.setattr(dependency_freshness_inventory.platform, "machine", lambda: "AMD64")

    result = dependency_freshness_inventory.build_inventory(
        tmp_path,
        runner=lambda _path, _timeout: _npm_result(
            {
                "turbo": {
                    "current": "2.9.16",
                    "wanted": "2.9.17",
                    "latest": "2.9.17",
                }
            }
        ),
    )

    project = result["projects"][0]
    dependency = project["dependencies"][0]
    assert project["status"] == "deferred_only"
    assert project["candidate_count"] == 0
    assert project["deferred_count"] == 1
    assert dependency["classification"] == "defer_latest_runtime_mismatch"
    assert dependency["latest_runtime_check"] == "known_mismatch"
    assert dependency["platform_package"] == "@turbo/windows-64"
    assert dependency["runtime_version"] == "2.9.16"
    assert dependency["expected_latest_version"] == "2.9.17"
    assert dependency["candidate"] is False
    assert dependency["deferred"] is True
    assert result["summary"]["candidate_dependency_count"] == 0
    assert result["summary"]["latest_runtime_mismatch_dependency_count"] == 1
    assert result["recommendations"] == [
        "Defer latest binary dependency candidates with known runtime mismatch for: . "
        "(turbo: latest 2.9.17, runtime 2.9.16)"
    ]


def test_known_windows_latest_runtime_mismatch_does_not_block_other_platforms(tmp_path: Path, monkeypatch) -> None:
    _write_package(tmp_path, {"turbo": "^2.9.16"})
    monkeypatch.setattr(dependency_freshness_inventory.sys, "platform", "linux")
    monkeypatch.setattr(dependency_freshness_inventory.platform, "machine", lambda: "x86_64")

    result = dependency_freshness_inventory.build_inventory(
        tmp_path,
        runner=lambda _path, _timeout: _npm_result(
            {
                "turbo": {
                    "current": "2.9.16",
                    "wanted": "2.9.17",
                    "latest": "2.9.17",
                }
            }
        ),
    )

    dependency = result["projects"][0]["dependencies"][0]
    assert result["projects"][0]["status"] == "candidate"
    assert result["summary"]["candidate_dependency_count"] == 1
    assert result["summary"]["latest_runtime_mismatch_dependency_count"] == 0
    assert dependency["classification"] == "adopt_patch_minor"
    assert dependency["candidate"] is True


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


def test_main_reports_output_write_failure_without_overwriting(tmp_path: Path, capsys) -> None:
    _write_package(tmp_path)
    output = tmp_path / "dependency.json"
    output.write_text('{"status":"existing"}\n', encoding="utf-8")
    output.with_name(f"{output.name}.refresh-tmp").mkdir()

    code = dependency_freshness_inventory.main(
        [
            "--root",
            str(tmp_path),
            "--output",
            str(output),
            "--json",
        ]
    )

    assert code == 4
    assert output.read_text(encoding="utf-8") == '{"status":"existing"}\n'
    stdout = json.loads(capsys.readouterr().out)
    assert stdout["status"] == "write_failed"
    assert stdout["write_error_path"] == output.as_posix()
    assert stdout["write_error"]


def test_main_reports_output_parent_write_failure_without_traceback(tmp_path: Path, capsys) -> None:
    _write_package(tmp_path)
    blocked_parent = tmp_path / ".blocked-parent"
    blocked_parent.write_text("not a directory\n", encoding="utf-8")
    output = blocked_parent / "dependency.json"

    code = dependency_freshness_inventory.main(
        [
            "--root",
            str(tmp_path),
            "--output",
            str(output),
            "--json",
        ]
    )

    assert code == 4
    assert blocked_parent.read_text(encoding="utf-8") == "not a directory\n"
    stdout = json.loads(capsys.readouterr().out)
    assert stdout["status"] == "write_failed"
    assert stdout["write_error_path"] == output.as_posix()
    assert stdout["write_error"]
