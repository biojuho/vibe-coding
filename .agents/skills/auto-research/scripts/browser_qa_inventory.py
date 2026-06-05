#!/usr/bin/env python3
"""Inventory direct browser-click QA evidence for local browser apps."""

from __future__ import annotations

import argparse
import json
import re
import struct
import sys
import zlib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


BROWSER_DEPENDENCIES = {
    "@playwright/test",
    "@vitejs/plugin-react",
    "@vitest/browser-playwright",
    "next",
    "react",
    "vite",
}
BROWSER_SCRIPT_MARKERS = ("next", "vite")
DIRECT_QA_TERMS = (
    "playwright",
    "browser qa",
    "browser-click",
    "browser click",
    "chrome cdp",
    "app-click",
)
VERIFY_TERMS = (
    "passed",
    "pass",
    "0 errors",
    "console errors/warnings 0",
    "console/network issues 0",
    "console issue 0",
    "returned 200",
    "status 200",
)
NON_EVIDENCE_PREFIXES = (
    "- boundary:",
    "- completed ",
    "- gate note:",
    "| next priorities |",
)
LOG_PATHS = (
    ".ai/TASKS.md",
    ".ai/HANDOFF.md",
    ".ai/SESSION_LOG.md",
)
ARTIFACT_DIRS = ("output/playwright",)
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
ARTIFACT_PATTERN = re.compile(r"(?P<path>(?:output|\.tmp)[/\\][^\s,;|`'\")]+?\.(?:png|jpg|jpeg|webp|json))", re.I)
MAX_LOG_SUMMARY_CHARS = 260
STALE_SCREENSHOT_DAYS = 14
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
PNG_CHANNELS_BY_COLOR_TYPE = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}
GENERIC_PROJECT_TOKENS = {
    "app",
    "chain",
    "dashboard",
    "game",
    "maker",
    "project",
    "tool",
}


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


def _package_sections(package_data: dict[str, Any]) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    for key in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
        value = package_data.get(key)
        if isinstance(value, dict):
            sections.append(value)
    return sections


def _package_dependency_names(package_data: dict[str, Any]) -> set[str]:
    names: set[str] = set()
    for section in _package_sections(package_data):
        names.update(str(key) for key in section)
    return names


def _package_scripts(package_data: dict[str, Any]) -> dict[str, str]:
    scripts = package_data.get("scripts")
    if not isinstance(scripts, dict):
        return {}
    return {str(key): str(value) for key, value in scripts.items() if isinstance(value, str)}


def _is_browser_app(path: Path, package_data: dict[str, Any]) -> bool:
    dependency_names = _package_dependency_names(package_data)
    if dependency_names & BROWSER_DEPENDENCIES:
        return True
    scripts = " ".join(_package_scripts(package_data).values()).lower()
    if any(marker in scripts for marker in BROWSER_SCRIPT_MARKERS):
        return True
    if (path / "src" / "app").exists() or (path / "index.html").exists():
        return True
    return False


def _project_dirs(root: Path) -> list[Path]:
    candidates: list[Path] = []
    projects_dir = root / "projects"
    if projects_dir.exists():
        candidates.extend(path for path in projects_dir.iterdir() if path.is_dir())
    if (root / "package.json").exists():
        candidates.append(root)
    unique = sorted({path.resolve() for path in candidates})
    return [path for path in unique if (path / "package.json").exists()]


def _project_tokens(project_path: str) -> list[str]:
    if project_path == ".":
        return ["workspace"]
    name = Path(project_path).name.lower()
    parts = [part for part in re.split(r"[^a-z0-9]+", name) if part]
    tokens = {name, name.replace("-", " ")}
    first_part = parts[0] if parts else ""
    if len(first_part) >= 5 and first_part not in GENERIC_PROJECT_TOKENS:
        tokens.add(first_part)
    if name.endswith("-dashboard"):
        tokens.add(name.removesuffix("-dashboard"))
    return sorted(tokens, key=lambda value: (-len(value), value))


def _contains_project_token(text: str, tokens: list[str]) -> bool:
    lowered = text.lower()
    return any(token in lowered for token in tokens)


def _line_title(lowered_line: str) -> str:
    match = re.search(r"\*\*(?P<title>t-\d+[^*]+)\*\*", lowered_line)
    return match.group("title") if match else ""


def _explicit_project_names(text: str, project_names: list[str]) -> list[str]:
    return [
        project_name for project_name in project_names if project_name in text or project_name.replace("-", " ") in text
    ]


def _line_targets_project(lowered_line: str, project_name: str, project_names: list[str], tokens: list[str]) -> bool:
    if lowered_line.strip().startswith(NON_EVIDENCE_PREFIXES):
        return False

    bracket_targets = re.findall(r"\[([a-z0-9][a-z0-9-]+)\]", lowered_line)
    if bracket_targets:
        return project_name in bracket_targets

    title = _line_title(lowered_line)
    if title:
        projects_in_title = _explicit_project_names(title, project_names)
        token_in_title = _contains_project_token(title, tokens)
        if projects_in_title or token_in_title:
            return project_name in projects_in_title or token_in_title

    explicit_projects = _explicit_project_names(lowered_line, project_names)
    if explicit_projects and project_name not in explicit_projects:
        return False
    return _contains_project_token(lowered_line, tokens)


def _artifact_mentions(text: str, root: Path) -> list[dict[str, Any]]:
    mentions: list[dict[str, Any]] = []
    seen: set[str] = set()
    for match in ARTIFACT_PATTERN.finditer(text):
        raw_path = match.group("path").replace("\\", "/")
        if raw_path in seen:
            continue
        seen.add(raw_path)
        artifact_path = root / raw_path
        mentions.append(
            {
                "path": raw_path,
                "exists": artifact_path.exists(),
                "kind": "image" if artifact_path.suffix.lower() in IMAGE_SUFFIXES else "json",
            }
        )
    return mentions


def _age_days(modified_at: datetime, now: datetime) -> int:
    seconds = max(0.0, (now - modified_at).total_seconds())
    return int(seconds // 86400)


def _paeth_predictor(left: int, up: int, upper_left: int) -> int:
    estimate = left + up - upper_left
    left_distance = abs(estimate - left)
    up_distance = abs(estimate - up)
    upper_left_distance = abs(estimate - upper_left)
    if left_distance <= up_distance and left_distance <= upper_left_distance:
        return left
    if up_distance <= upper_left_distance:
        return up
    return upper_left


def _decode_png_pixels(
    compressed: bytes,
    width: int,
    height: int,
    bytes_per_pixel: int,
) -> tuple[bytes, list[str]]:
    try:
        raw = zlib.decompress(compressed)
    except zlib.error as exc:
        return b"", [f"png idat decompress failed: {exc}"]

    row_length = width * bytes_per_pixel
    expected_length = height * (row_length + 1)
    if len(raw) < expected_length:
        return b"", [f"png pixel data truncated: expected {expected_length} byte(s), got {len(raw)}"]

    previous = bytearray(row_length)
    pixels = bytearray()
    offset = 0
    for _row_index in range(height):
        filter_type = raw[offset]
        offset += 1
        row = bytearray(raw[offset : offset + row_length])
        offset += row_length
        if filter_type not in {0, 1, 2, 3, 4}:
            return b"", [f"unsupported png filter type: {filter_type}"]

        for index in range(row_length):
            left = row[index - bytes_per_pixel] if index >= bytes_per_pixel else 0
            up = previous[index]
            upper_left = previous[index - bytes_per_pixel] if index >= bytes_per_pixel else 0
            if filter_type == 1:
                row[index] = (row[index] + left) & 0xFF
            elif filter_type == 2:
                row[index] = (row[index] + up) & 0xFF
            elif filter_type == 3:
                row[index] = (row[index] + ((left + up) // 2)) & 0xFF
            elif filter_type == 4:
                row[index] = (row[index] + _paeth_predictor(left, up, upper_left)) & 0xFF

        pixels.extend(row)
        previous = row

    return bytes(pixels), []


def _pixels_are_nonblank(pixels: bytes, bytes_per_pixel: int) -> bool:
    if not pixels:
        return False
    first_pixel = pixels[:bytes_per_pixel]
    for offset in range(bytes_per_pixel, len(pixels), bytes_per_pixel):
        if pixels[offset : offset + bytes_per_pixel] != first_pixel:
            return True
    return False


def _png_metadata(path: Path) -> dict[str, Any]:
    issues: list[str] = []
    try:
        data = path.read_bytes()
    except OSError as exc:
        return {
            "image_check": "unreadable",
            "image_valid": False,
            "nonblank": False,
            "image_issues": [str(exc)],
        }

    if not data.startswith(PNG_SIGNATURE):
        return {
            "image_check": "invalid",
            "image_valid": False,
            "nonblank": False,
            "image_issues": ["png signature missing"],
        }

    offset = len(PNG_SIGNATURE)
    width = 0
    height = 0
    bit_depth = 0
    color_type = -1
    compression_method = 0
    filter_method = 0
    interlace_method = 0
    idat = bytearray()
    saw_iend = False
    while offset + 8 <= len(data):
        chunk_length = struct.unpack(">I", data[offset : offset + 4])[0]
        chunk_type = data[offset + 4 : offset + 8]
        payload_start = offset + 8
        payload_end = payload_start + chunk_length
        chunk_end = payload_end + 4
        if chunk_end > len(data):
            issues.append(f"png chunk {chunk_type.decode('ascii', errors='replace')} is truncated")
            break
        payload = data[payload_start:payload_end]
        if chunk_type == b"IHDR":
            if chunk_length != 13:
                issues.append("png ihdr chunk has invalid length")
            else:
                (
                    width,
                    height,
                    bit_depth,
                    color_type,
                    compression_method,
                    filter_method,
                    interlace_method,
                ) = struct.unpack(">IIBBBBB", payload)
        elif chunk_type == b"IDAT":
            idat.extend(payload)
        elif chunk_type == b"IEND":
            saw_iend = True
            break
        offset = chunk_end

    metadata: dict[str, Any] = {"width": width, "height": height}
    if width <= 0 or height <= 0:
        issues.append("png dimensions are missing or invalid")
    if not saw_iend:
        issues.append("png iend chunk missing")
    if not idat:
        issues.append("png idat chunk missing")
    if issues:
        metadata.update(
            {
                "image_check": "invalid",
                "image_valid": False,
                "nonblank": False,
                "image_issues": issues,
            }
        )
        return metadata

    bytes_per_pixel = PNG_CHANNELS_BY_COLOR_TYPE.get(color_type)
    if (
        bit_depth != 8
        or bytes_per_pixel is None
        or compression_method != 0
        or filter_method != 0
        or interlace_method != 0
    ):
        metadata.update(
            {
                "image_check": "nonblank_check_unsupported",
                "image_valid": True,
                "nonblank": None,
                "image_issues": ["png nonblank check supports only 8-bit non-interlaced color types 0, 2, 3, 4, and 6"],
            }
        )
        return metadata

    pixels, pixel_issues = _decode_png_pixels(bytes(idat), width, height, bytes_per_pixel)
    if pixel_issues:
        metadata.update(
            {
                "image_check": "invalid",
                "image_valid": False,
                "nonblank": False,
                "image_issues": pixel_issues,
            }
        )
        return metadata

    nonblank = _pixels_are_nonblank(pixels, bytes_per_pixel)
    metadata.update(
        {
            "image_check": "ok" if nonblank else "blank",
            "image_valid": True,
            "nonblank": nonblank,
        }
    )
    return metadata


def _image_metadata(path: Path) -> dict[str, Any]:
    if path.suffix.lower() == ".png":
        return _png_metadata(path)
    return {
        "image_check": "nonblank_check_unsupported",
        "image_valid": None,
        "nonblank": None,
        "image_issues": ["non-png image metadata check is not supported"],
    }


def _scan_logs(root: Path, project_path: str, project_names: list[str], tokens: list[str]) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    project_name = Path(project_path).name.lower()
    for rel_log_path in LOG_PATHS:
        log_path = root / rel_log_path
        try:
            lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
        except FileNotFoundError:
            continue
        for line_number, line in enumerate(lines, start=1):
            lowered = line.lower()
            if not _line_targets_project(lowered, project_name, project_names, tokens):
                continue
            matched_terms = [term for term in DIRECT_QA_TERMS if term in lowered]
            if not matched_terms:
                continue
            summary = line.strip()
            if len(summary) > MAX_LOG_SUMMARY_CHARS:
                summary = summary[: MAX_LOG_SUMMARY_CHARS - 3] + "..."
            evidence.append(
                {
                    "kind": "log",
                    "source": rel_log_path,
                    "line": line_number,
                    "project": project_path,
                    "matched_terms": matched_terms,
                    "verified": any(term in lowered for term in VERIFY_TERMS),
                    "artifacts": _artifact_mentions(line, root),
                    "summary": summary,
                }
            )
    return evidence


def _scan_artifacts(root: Path, tokens: list[str], now: datetime) -> list[dict[str, Any]]:
    artifacts: list[dict[str, Any]] = []
    for rel_dir in ARTIFACT_DIRS:
        artifact_dir = root / rel_dir
        try:
            children = list(artifact_dir.iterdir())
        except (FileNotFoundError, NotADirectoryError, PermissionError, OSError):
            continue
        for path in sorted(children):
            if not path.is_file() or path.suffix.lower() not in IMAGE_SUFFIXES:
                continue
            if not _contains_project_token(path.name, tokens):
                continue
            stat = path.stat()
            modified_at = datetime.fromtimestamp(stat.st_mtime, UTC)
            artifact = {
                "kind": "screenshot",
                "path": _relative(path, root),
                "bytes": stat.st_size,
                "modified_at": modified_at.isoformat(),
                "age_days": _age_days(modified_at, now),
            }
            artifact.update(_image_metadata(path))
            artifacts.append(artifact)
    return artifacts


def _freshest_screenshot(artifacts: list[dict[str, Any]]) -> dict[str, Any] | None:
    screenshots = [artifact for artifact in artifacts if artifact.get("kind") == "screenshot"]
    if not screenshots:
        return None
    return max(screenshots, key=lambda artifact: str(artifact.get("modified_at") or ""))


def _project_summary(
    path: Path,
    root: Path,
    project_names: list[str],
    include_non_browser: bool,
    now: datetime,
) -> dict[str, Any] | None:
    package_data = _load_json(path / "package.json")
    project_path = _relative(path, root)
    browser_app = _is_browser_app(path, package_data)
    if not browser_app and not include_non_browser:
        return None
    tokens = _project_tokens(project_path)
    log_evidence = _scan_logs(root, project_path, project_names, tokens)
    artifact_evidence = _scan_artifacts(root, tokens, now)
    freshest = _freshest_screenshot(artifact_evidence)
    verified_log_count = sum(1 for item in log_evidence if item.get("verified"))
    valid_screenshots = [artifact for artifact in artifact_evidence if artifact.get("image_valid") is True]
    usable_screenshots = [
        artifact
        for artifact in artifact_evidence
        if artifact.get("image_valid") is not False and artifact.get("nonblank") is not False
    ]
    fresh_valid_screenshots = [
        artifact for artifact in valid_screenshots if int(artifact.get("age_days") or 0) <= STALE_SCREENSHOT_DAYS
    ]
    fresh_usable_screenshots = [
        artifact for artifact in usable_screenshots if int(artifact.get("age_days") or 0) <= STALE_SCREENSHOT_DAYS
    ]
    nonblank_screenshots = [artifact for artifact in artifact_evidence if artifact.get("nonblank") is True]
    fresh_nonblank_screenshots = [
        artifact for artifact in nonblank_screenshots if int(artifact.get("age_days") or 0) <= STALE_SCREENSHOT_DAYS
    ]
    status = "covered" if browser_app and (verified_log_count or usable_screenshots) else "missing"
    if not browser_app:
        status = "not_browser_app"
    project = {
        "path": project_path,
        "browser_app": browser_app,
        "tokens": tokens,
        "status": status,
        "log_evidence_count": len(log_evidence),
        "verified_log_evidence_count": verified_log_count,
        "current_screenshot_count": len(artifact_evidence),
        "valid_screenshot_count": len(valid_screenshots),
        "usable_screenshot_count": len(usable_screenshots),
        "fresh_valid_screenshot_count": len(fresh_valid_screenshots),
        "fresh_usable_screenshot_count": len(fresh_usable_screenshots),
        "nonblank_screenshot_count": len(nonblank_screenshots),
        "fresh_nonblank_screenshot_count": len(fresh_nonblank_screenshots),
        "evidence": [*artifact_evidence, *log_evidence],
    }
    if freshest:
        project["freshest_screenshot_path"] = freshest["path"]
        project["freshest_screenshot_modified_at"] = freshest["modified_at"]
        project["freshest_screenshot_age_days"] = freshest["age_days"]
        project["freshest_screenshot_fresh"] = freshest["age_days"] <= STALE_SCREENSHOT_DAYS
        project["freshest_screenshot_image_check"] = freshest.get("image_check")
        project["freshest_screenshot_image_valid"] = freshest.get("image_valid")
        project["freshest_screenshot_nonblank"] = freshest.get("nonblank")
        if freshest.get("width") is not None:
            project["freshest_screenshot_width"] = freshest.get("width")
        if freshest.get("height") is not None:
            project["freshest_screenshot_height"] = freshest.get("height")
    return project


def _recommendations(projects: list[dict[str, Any]]) -> list[str]:
    recommendations: list[str] = []
    missing = [project["path"] for project in projects if project["browser_app"] and project["status"] == "missing"]
    if missing:
        recommendations.append("Run direct browser-click QA for project(s): " + ", ".join(missing))
    no_current_screenshot = [
        project["path"]
        for project in projects
        if project["browser_app"] and project["status"] == "covered" and project["current_screenshot_count"] == 0
    ]
    if no_current_screenshot:
        recommendations.append(
            "Capture or retain output/playwright screenshots for covered project(s): "
            + ", ".join(no_current_screenshot)
        )
    stale_screenshot = [
        project["path"]
        for project in projects
        if project["browser_app"]
        and project["status"] == "covered"
        and project.get("freshest_screenshot_fresh") is False
    ]
    if stale_screenshot:
        recommendations.append(
            f"Refresh browser QA screenshots older than {STALE_SCREENSHOT_DAYS} day(s) for project(s): "
            + ", ".join(stale_screenshot)
        )
    invalid_screenshot = [
        project["path"]
        for project in projects
        if project["browser_app"] and project["current_screenshot_count"] and project["valid_screenshot_count"] == 0
    ]
    if invalid_screenshot:
        recommendations.append(
            "Refresh invalid browser QA screenshots for project(s): " + ", ".join(invalid_screenshot)
        )
    blank_screenshot = [
        project["path"]
        for project in projects
        if project["browser_app"] and project["valid_screenshot_count"] and project["usable_screenshot_count"] == 0
    ]
    if blank_screenshot:
        recommendations.append("Refresh blank browser QA screenshots for project(s): " + ", ".join(blank_screenshot))
    return recommendations


def build_inventory(root: Path, include_non_browser: bool = False, now: datetime | None = None) -> dict[str, Any]:
    root = root.resolve()
    now = now or datetime.now(UTC)
    project_dirs = _project_dirs(root)
    project_names = sorted(path.name.lower() for path in project_dirs)
    projects = [
        summary
        for path in project_dirs
        if (summary := _project_summary(path, root, project_names, include_non_browser, now)) is not None
    ]
    browser_projects = [project for project in projects if project["browser_app"]]
    covered = [project for project in browser_projects if project["status"] == "covered"]
    missing = [project for project in browser_projects if project["status"] == "missing"]
    projects_with_current_screenshot = [project for project in browser_projects if project["current_screenshot_count"]]
    projects_with_fresh_screenshot = [
        project for project in projects_with_current_screenshot if project.get("freshest_screenshot_fresh") is True
    ]
    projects_with_stale_screenshot = [
        project for project in projects_with_current_screenshot if project.get("freshest_screenshot_fresh") is False
    ]
    projects_with_valid_screenshot = [project for project in browser_projects if project["valid_screenshot_count"]]
    projects_with_usable_screenshot = [project for project in browser_projects if project["usable_screenshot_count"]]
    projects_with_fresh_valid_screenshot = [
        project for project in browser_projects if project["fresh_valid_screenshot_count"]
    ]
    projects_with_fresh_usable_screenshot = [
        project for project in browser_projects if project["fresh_usable_screenshot_count"]
    ]
    projects_with_nonblank_screenshot = [
        project for project in browser_projects if project["nonblank_screenshot_count"]
    ]
    projects_with_fresh_nonblank_screenshot = [
        project for project in browser_projects if project["fresh_nonblank_screenshot_count"]
    ]
    summary = {
        "root": str(root),
        "browser_project_count": len(browser_projects),
        "covered_count": len(covered),
        "missing_count": len(missing),
        "current_screenshot_project_count": len(projects_with_current_screenshot),
        "fresh_screenshot_project_count": len(projects_with_fresh_screenshot),
        "stale_screenshot_project_count": len(projects_with_stale_screenshot),
        "valid_screenshot_project_count": len(projects_with_valid_screenshot),
        "usable_screenshot_project_count": len(projects_with_usable_screenshot),
        "fresh_valid_screenshot_project_count": len(projects_with_fresh_valid_screenshot),
        "fresh_usable_screenshot_project_count": len(projects_with_fresh_usable_screenshot),
        "nonblank_screenshot_project_count": len(projects_with_nonblank_screenshot),
        "fresh_nonblank_screenshot_project_count": len(projects_with_fresh_nonblank_screenshot),
        "freshest_screenshots": {
            project["path"]: {
                "path": project["freshest_screenshot_path"],
                "modified_at": project["freshest_screenshot_modified_at"],
                "age_days": project["freshest_screenshot_age_days"],
                "fresh": project["freshest_screenshot_fresh"],
                "image_check": project["freshest_screenshot_image_check"],
                "image_valid": project["freshest_screenshot_image_valid"],
                "nonblank": project["freshest_screenshot_nonblank"],
                "width": project.get("freshest_screenshot_width"),
                "height": project.get("freshest_screenshot_height"),
            }
            for project in projects_with_current_screenshot
        },
        "covered_projects": [project["path"] for project in covered],
        "missing_projects": [project["path"] for project in missing],
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
        "browser QA coverage: "
        f"{summary['covered_count']}/{summary['browser_project_count']} covered, "
        f"{summary['missing_count']} missing"
    )
    for project in inventory["projects"]:
        if not project["browser_app"]:
            continue
        print(
            f"- {project['path']}: {project['status']} "
            f"(logs={project['verified_log_evidence_count']}/{project['log_evidence_count']}, "
            f"screenshots={project['current_screenshot_count']}, usable={project['usable_screenshot_count']})"
        )
    for recommendation in inventory["recommendations"]:
        print(f"recommendation: {recommendation}")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Repository root to inspect")
    parser.add_argument("--include-non-browser", action="store_true", help="Include non-browser package projects")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text")
    parser.add_argument("--output", type=Path, help="Optional path to write the inventory JSON")
    args = parser.parse_args(argv)

    inventory = build_inventory(args.root, args.include_non_browser)
    if args.output:
        _write_json(args.output, inventory)
    if args.json:
        json.dump(inventory, sys.stdout, ensure_ascii=True, indent=2)
        print()
    else:
        _print_text(inventory)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
