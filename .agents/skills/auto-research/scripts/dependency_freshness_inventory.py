#!/usr/bin/env python3
"""Inventory npm dependency freshness for local package projects."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any


PACKAGE_SECTIONS = ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies")
PROJECT_SCAN_EXCLUDES = {".git", ".next", ".tmp", "dist", "node_modules", "output"}
VERSION_PATTERN = re.compile(r"(?P<major>\d+)(?:\.(?P<minor>\d+))?(?:\.(?P<patch>\d+))?")
PRERELEASE_PATTERN = re.compile(r"[-.](alpha|beta|canary|dev|next|pre|rc)(?:[.-]|\d|$)", re.I)
PRERELEASE_CHANNEL_PATTERN = re.compile(r"[-.](?P<channel>alpha|beta|canary|dev|next|pre|rc)(?:[.-]|\d|$)", re.I)
PEER_VERSION_TOKEN_PATTERN = re.compile(
    r"(?P<op>>=|<=|>|<|\^|~|=)?\s*v?(?P<major>\d+)(?:\.(?:\d+|x|X|\*))?(?:\.(?:\d+|x|X|\*))?"
)
PEER_BLOCKER_SAMPLE_LIMIT = 10


def _relative(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _package_dependency_names(package_data: dict[str, Any]) -> set[str]:
    names: set[str] = set()
    for section_name in PACKAGE_SECTIONS:
        section = package_data.get(section_name)
        if isinstance(section, dict):
            names.update(str(key) for key in section)
    return names


def _project_dirs(root: Path) -> list[Path]:
    candidates: list[Path] = []
    projects_dir = root / "projects"
    if projects_dir.exists():
        candidates.extend(path for path in projects_dir.iterdir() if path.is_dir())
    if (root / "package.json").exists():
        candidates.append(root)
    unique = sorted({path.resolve() for path in candidates})
    return [path for path in unique if (path / "package.json").exists() and path.name not in PROJECT_SCAN_EXCLUDES]


def _npm_command() -> str | None:
    for command in ("npm.cmd", "npm"):
        resolved = shutil.which(command)
        if resolved:
            return resolved
    return None


def _run_npm_outdated(project_path: Path, timeout: int) -> dict[str, Any]:
    command = _npm_command()
    if command is None:
        return {
            "available": False,
            "returncode": None,
            "stdout": "",
            "stderr": "npm command not found",
        }
    try:
        completed = subprocess.run(
            [command, "outdated", "--json"],
            cwd=str(project_path),
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "available": False,
            "returncode": None,
            "stdout": exc.stdout or "",
            "stderr": f"npm outdated timed out after {timeout}s",
        }
    except (FileNotFoundError, OSError) as exc:
        return {
            "available": False,
            "returncode": None,
            "stdout": "",
            "stderr": str(exc),
        }
    return {
        "available": True,
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def _run_npm_dist_tags(project_path: Path, package_name: str, timeout: int) -> dict[str, Any]:
    command = _npm_command()
    if command is None:
        return {
            "available": False,
            "returncode": None,
            "stdout": "",
            "stderr": "npm command not found",
        }
    try:
        completed = subprocess.run(
            [command, "view", package_name, "dist-tags", "--json"],
            cwd=str(project_path),
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "available": False,
            "returncode": None,
            "stdout": exc.stdout or "",
            "stderr": f"npm view {package_name} dist-tags timed out after {timeout}s",
        }
    except (FileNotFoundError, OSError) as exc:
        return {
            "available": False,
            "returncode": None,
            "stdout": "",
            "stderr": str(exc),
        }
    return {
        "available": True,
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def _parse_version(version: Any) -> tuple[int, int, int] | None:
    if not isinstance(version, str):
        return None
    match = VERSION_PATTERN.search(version)
    if not match:
        return None
    return (
        int(match.group("major")),
        int(match.group("minor") or 0),
        int(match.group("patch") or 0),
    )


def _package_name_from_lock_path(lock_path: str) -> str:
    parts = [part for part in lock_path.replace("\\", "/").split("node_modules/") if part]
    if not parts:
        return lock_path or "unknown"
    tail = parts[-1].strip("/")
    if tail.startswith("@"):
        scoped_parts = tail.split("/")
        return "/".join(scoped_parts[:2]) if len(scoped_parts) >= 2 else tail
    return tail.split("/", 1)[0] or "unknown"


def _peer_range_allows_major(range_value: Any, target_major: int) -> bool:
    if not isinstance(range_value, str):
        return False

    range_text = range_value.strip()
    if not range_text:
        return False
    if range_text in {"*", "x", "X"}:
        return True

    for alternative in range_text.split("||"):
        alternative = alternative.strip()
        if not alternative:
            continue
        if alternative in {"*", "x", "X"}:
            return True

        tokens = [
            (match.group("op") or "", int(match.group("major")))
            for match in PEER_VERSION_TOKEN_PATTERN.finditer(alternative)
        ]
        if not tokens:
            continue

        if any(op in {"", "^", "~", "="} and major == target_major for op, major in tokens):
            return True

        lower_allows_target = False
        upper_allows_target = False
        upper_blocks_target = False
        for op, major in tokens:
            if op in {">=", ">"} and major <= target_major:
                lower_allows_target = True
            elif op == "<" and major <= target_major:
                upper_blocks_target = True
            elif op == "<=" and major < target_major:
                upper_blocks_target = True
            elif op in {"<", "<="} and major > target_major:
                upper_allows_target = True

        if not upper_blocks_target and (lower_allows_target or upper_allows_target):
            return True

    return False


def _find_peer_blockers(
    project_path: Path, dependency_name: str, target_major: int
) -> tuple[list[dict[str, Any]], str]:
    lock_data = _load_json(project_path / "package-lock.json")
    packages = lock_data.get("packages")
    if not isinstance(packages, dict):
        return [], "missing_lockfile"

    blockers = []
    for lock_path, package_entry in sorted(packages.items(), key=lambda item: str(item[0]).lower()):
        if not lock_path or not isinstance(package_entry, dict):
            continue
        peer_dependencies = package_entry.get("peerDependencies")
        if not isinstance(peer_dependencies, dict) or dependency_name not in peer_dependencies:
            continue
        peer_range = peer_dependencies[dependency_name]
        if _peer_range_allows_major(peer_range, target_major):
            continue
        blockers.append(
            {
                "package": str(package_entry.get("name") or _package_name_from_lock_path(str(lock_path))),
                "version": str(package_entry.get("version") or "unknown"),
                "peer_range": str(peer_range),
                "path": str(lock_path).replace("\\", "/"),
            }
        )

    return blockers, "blocked" if blockers else "none"


def _is_prerelease(version: Any) -> bool:
    return isinstance(version, str) and bool(PRERELEASE_PATTERN.search(version))


def _prerelease_channel(version: Any) -> str | None:
    if not isinstance(version, str):
        return None
    match = PRERELEASE_CHANNEL_PATTERN.search(version)
    if not match:
        return None
    return match.group("channel").lower()


def _version_delta(current: tuple[int, int, int] | None, target: tuple[int, int, int] | None) -> str:
    if current is None or target is None:
        return "unknown"
    if target[0] != current[0]:
        return "major"
    if target[1] != current[1]:
        return "minor"
    if target[2] != current[2]:
        return "patch"
    return "same"


def classify_dependency(name: str, raw: dict[str, Any]) -> dict[str, Any]:
    current = str(raw.get("current", "")).strip()
    wanted = str(raw.get("wanted", "")).strip()
    latest = str(raw.get("latest", "")).strip()
    current_version = _parse_version(current)
    wanted_version = _parse_version(wanted)
    latest_version = _parse_version(latest)
    wanted_delta = _version_delta(current_version, wanted_version)
    latest_delta = _version_delta(current_version, latest_version)
    current_is_prerelease = _is_prerelease(current)
    latest_is_prerelease = _is_prerelease(latest)

    classification = "unknown"
    action = "inspect_manually"
    candidate = False
    deferred = False
    reason = "version metadata is incomplete or not comparable"

    if wanted and current and wanted != current and wanted_delta in {"patch", "minor"}:
        classification = "adopt_patch_minor"
        action = "candidate"
        candidate = True
        reason = f"{name} can move from {current} to wanted {wanted} within the same major"
    elif wanted and current and wanted != current and wanted_delta == "major":
        classification = "defer_major_range_update"
        action = "defer"
        deferred = True
        reason = f"{name} wanted version {wanted} crosses a major boundary from {current}"
    elif (
        current_version
        and latest_version
        and current_is_prerelease
        and not latest_is_prerelease
        and latest_version[0] < current_version[0]
    ):
        classification = "defer_channel_mismatch"
        action = "defer"
        deferred = True
        reason = f"{name} is on prerelease major {current}; npm latest {latest} is a lower stable major"
    elif latest and current and latest != current and latest_delta == "major":
        classification = "defer_major_migration"
        action = "defer"
        deferred = True
        reason = f"{name} latest {latest} crosses a major boundary from {current}"
    elif latest and current and latest != current and latest_delta in {"patch", "minor"}:
        classification = "range_blocked_patch_minor"
        action = "inspect_range"
        deferred = True
        reason = f"{name} latest {latest} is {latest_delta}-level, but package range only wants {wanted or 'unknown'}"
    elif latest == current or wanted_delta == "same":
        classification = "range_current"
        action = "none"
        reason = f"{name} has no npm-wanted update"

    return {
        "name": name,
        "current": current,
        "wanted": wanted,
        "latest": latest,
        "wanted_delta": wanted_delta,
        "latest_delta": latest_delta,
        "classification": classification,
        "action": action,
        "candidate": candidate,
        "deferred": deferred,
        "reason": reason,
    }


def _parse_outdated_result(result: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    stdout = str(result.get("stdout") or "").strip()
    if not stdout:
        return {}, []
    try:
        parsed = json.loads(stdout)
    except json.JSONDecodeError as exc:
        return {}, [f"failed to parse npm outdated JSON: {exc}"]
    if not isinstance(parsed, dict):
        return {}, ["npm outdated JSON root was not an object"]
    return parsed, []


def _parse_dist_tags_result(result: dict[str, Any]) -> tuple[dict[str, str], list[str]]:
    if not result.get("available", False):
        return {}, [str(result.get("stderr") or "npm dist-tags unavailable")]
    stdout = str(result.get("stdout") or "").strip()
    if not stdout:
        return {}, ["npm dist-tags JSON was empty"]
    try:
        parsed = json.loads(stdout)
    except json.JSONDecodeError as exc:
        return {}, [f"failed to parse npm dist-tags JSON: {exc}"]
    if not isinstance(parsed, dict):
        return {}, ["npm dist-tags JSON root was not an object"]
    tags = {str(key): str(value) for key, value in parsed.items() if isinstance(value, str)}
    return tags, []


def _apply_prerelease_dist_tag_context(
    dependency: dict[str, Any],
    project_path: Path,
    timeout: int,
    tag_runner: "DistTagRunner",
) -> dict[str, Any]:
    if dependency["classification"] != "defer_channel_mismatch":
        return dependency

    channel = _prerelease_channel(dependency["current"])
    if not channel:
        return dependency

    tags, issues = _parse_dist_tags_result(tag_runner(project_path, dependency["name"], timeout))
    dependency["dist_tag_channel"] = channel
    dependency["dist_tag_check"] = "failed" if issues else "ok"
    if issues:
        dependency["dist_tag_issues"] = issues
        return dependency

    channel_version = tags.get(channel)
    dependency["dist_tag_version"] = channel_version or ""
    if channel_version == dependency["current"]:
        dependency["classification"] = "current_prerelease_channel"
        dependency["action"] = "none"
        dependency["candidate"] = False
        dependency["deferred"] = False
        dependency["reason"] = (
            f"{dependency['name']} is already current on npm {channel} dist-tag ({dependency['current']}); "
            f"npm latest {dependency['latest']} is the lower stable channel"
        )
    return dependency


def _apply_deferred_major_peer_context(dependency: dict[str, Any], project_path: Path) -> dict[str, Any]:
    if not dependency.get("deferred") or dependency.get("latest_delta") != "major":
        return dependency

    latest_version = _parse_version(dependency.get("latest"))
    if latest_version is None:
        return dependency

    target_major = latest_version[0]
    blockers, status = _find_peer_blockers(project_path, str(dependency["name"]), target_major)
    dependency["peer_blocker_check"] = status
    dependency["peer_target_major"] = target_major
    if not blockers:
        return dependency

    dependency["peer_blocker_count"] = len(blockers)
    dependency["peer_blockers"] = blockers[:PEER_BLOCKER_SAMPLE_LIMIT]
    if len(blockers) > PEER_BLOCKER_SAMPLE_LIMIT:
        dependency["peer_blockers_truncated"] = True
    dependency["reason"] += (
        f"; {len(blockers)} installed peer dependency range(s) do not allow {dependency['name']} major {target_major}"
    )
    return dependency


def summarize_project(
    project_path: Path,
    root: Path,
    npm_result: dict[str, Any],
    timeout: int = 60,
    tag_runner: "DistTagRunner" = _run_npm_dist_tags,
) -> dict[str, Any]:
    package_data = _load_json(project_path / "package.json")
    declared_names = _package_dependency_names(package_data)
    project = {
        "path": _relative(project_path, root),
        "package_name": str(package_data.get("name") or project_path.name),
        "status": "unknown",
        "dependency_count": len(declared_names),
        "outdated_count": 0,
        "candidate_count": 0,
        "deferred_count": 0,
        "issues": [],
        "dependencies": [],
    }

    if not npm_result.get("available", False):
        project["status"] = "unavailable"
        project["issues"].append(str(npm_result.get("stderr") or "npm outdated unavailable"))
        return project

    parsed, issues = _parse_outdated_result(npm_result)
    project["issues"].extend(issues)
    if issues:
        project["status"] = "unavailable"
        return project

    dependencies = []
    for name, raw in sorted(parsed.items(), key=lambda item: str(item[0]).lower()):
        dependency = classify_dependency(str(name), raw if isinstance(raw, dict) else {})
        dependency = _apply_prerelease_dist_tag_context(dependency, project_path, timeout, tag_runner)
        dependency = _apply_deferred_major_peer_context(dependency, project_path)
        dependencies.append(dependency)
    project["dependencies"] = dependencies
    project["outdated_count"] = len(dependencies)
    project["candidate_count"] = sum(1 for dependency in dependencies if dependency["candidate"])
    project["deferred_count"] = sum(1 for dependency in dependencies if dependency["deferred"])

    if project["candidate_count"]:
        project["status"] = "candidate"
    elif project["deferred_count"]:
        project["status"] = "deferred_only"
    elif dependencies and all(dependency["action"] == "none" for dependency in dependencies):
        project["status"] = "clean"
    elif dependencies:
        project["status"] = "inspect"
    else:
        project["status"] = "clean"
    return project


def _recommendations(projects: list[dict[str, Any]]) -> list[str]:
    recommendations: list[str] = []
    candidate_projects = [project for project in projects if project["candidate_count"]]
    if candidate_projects:
        names = []
        for project in candidate_projects:
            candidate_names = [
                dependency["name"] for dependency in project["dependencies"] if dependency.get("candidate")
            ]
            names.append(f"{project['path']} ({', '.join(candidate_names)})")
        recommendations.append("Run a focused patch/minor dependency update experiment for: " + "; ".join(names))

    unavailable = [project["path"] for project in projects if project["status"] == "unavailable"]
    if unavailable:
        recommendations.append("Fix npm outdated availability or JSON output for: " + ", ".join(unavailable))

    deferred_projects = [
        project
        for project in projects
        if project["deferred_count"] and not project["candidate_count"] and project["status"] != "unavailable"
    ]
    if deferred_projects and not candidate_projects:
        peer_blocked_projects = []
        other_deferred_projects = []
        for project in deferred_projects:
            peer_blocked_dependencies = []
            other_deferred_dependencies = []
            for dependency in project["dependencies"]:
                if not dependency.get("deferred"):
                    continue
                if dependency.get("latest_delta") == "major" and dependency.get("peer_blocker_check") == "blocked":
                    blocker_count = int(dependency.get("peer_blocker_count") or 0)
                    peer_blocked_dependencies.append(f"{dependency['name']}: {blocker_count} peer blocker(s)")
                else:
                    other_deferred_dependencies.append(str(dependency.get("name") or "unknown"))

            if peer_blocked_dependencies and not other_deferred_dependencies:
                peer_blocked_projects.append(f"{project['path']} ({', '.join(peer_blocked_dependencies)})")
            else:
                other_deferred_projects.append(project["path"])

        if peer_blocked_projects and not other_deferred_projects:
            recommendations.append(
                "No direct npm patch/minor adoption candidates; wait for upstream peer support before "
                "major migrations for: " + "; ".join(peer_blocked_projects)
            )
            return recommendations

        deferred_classifications = {
            str(dependency.get("classification") or "")
            for project in projects
            for dependency in project["dependencies"]
            if dependency.get("deferred")
        }
        has_major = any("major" in classification for classification in deferred_classifications)
        has_channel = any("channel" in classification for classification in deferred_classifications)
        if has_major and has_channel:
            deferred_label = "major or channel migrations"
        elif has_channel:
            deferred_label = "channel migrations"
        elif has_major:
            deferred_label = "major migrations"
        else:
            deferred_label = "manual dependency inspections"
        recommendations.append(
            f"No direct npm patch/minor adoption candidates; defer {deferred_label} for: "
            + ", ".join(project["path"] for project in deferred_projects)
        )
    return recommendations


OutdatedRunner = Callable[[Path, int], dict[str, Any]]
DistTagRunner = Callable[[Path, str, int], dict[str, Any]]


def build_inventory(
    root: Path,
    timeout: int = 60,
    runner: OutdatedRunner = _run_npm_outdated,
    tag_runner: DistTagRunner = _run_npm_dist_tags,
) -> dict[str, Any]:
    root = root.resolve()
    projects = [
        summarize_project(path, root, runner(path, timeout), timeout=timeout, tag_runner=tag_runner)
        for path in _project_dirs(root)
    ]
    summary = {
        "root": str(root),
        "package_project_count": len(projects),
        "clean_project_count": sum(1 for project in projects if project["status"] == "clean"),
        "candidate_project_count": sum(1 for project in projects if project["status"] == "candidate"),
        "deferred_project_count": sum(1 for project in projects if project["status"] == "deferred_only"),
        "unavailable_project_count": sum(1 for project in projects if project["status"] == "unavailable"),
        "candidate_dependency_count": sum(project["candidate_count"] for project in projects),
        "deferred_dependency_count": sum(project["deferred_count"] for project in projects),
        "outdated_dependency_count": sum(project["outdated_count"] for project in projects),
    }
    return {
        "root": str(root),
        "summary": summary,
        "projects": projects,
        "recommendations": _recommendations(projects),
    }


def _print_text(inventory: dict[str, Any]) -> None:
    summary = inventory["summary"]
    print(
        "npm dependency freshness: "
        f"{summary['candidate_dependency_count']} candidate(s), "
        f"{summary['deferred_dependency_count']} deferred, "
        f"{summary['clean_project_count']}/{summary['package_project_count']} clean project(s)"
    )
    for project in inventory["projects"]:
        print(
            f"- {project['path']}: {project['status']} "
            f"(outdated={project['outdated_count']}, candidates={project['candidate_count']}, "
            f"deferred={project['deferred_count']})"
        )
    for recommendation in inventory["recommendations"]:
        print(f"recommendation: {recommendation}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Repository root to inspect")
    parser.add_argument("--timeout", type=int, default=60, help="Per-project npm outdated timeout in seconds")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text")
    parser.add_argument("--output", type=Path, help="Optional path to write the inventory JSON")
    args = parser.parse_args(argv)

    inventory = build_inventory(args.root, args.timeout)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(inventory, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.json:
        json.dump(inventory, sys.stdout, ensure_ascii=False, indent=2)
        print()
    else:
        _print_text(inventory)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
