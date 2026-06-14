"""Clean ACL-locked pytest temp directories from known workspace scratch paths.

This script is intentionally narrow. It targets only regenerated pytest/project
QC temp directories that prior cleanup could not delete from a normal shell.
Run with ``--check`` first. On Windows, ``--apply`` requires an elevated shell.
"""

from __future__ import annotations

import argparse
import ctypes
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]


Rule = tuple[Path, Callable[[Path], bool], str]


def _root_tmp_candidate(path: Path) -> bool:
    return path.is_dir() and (path.name == "project-qc-temp" or path.name.startswith("pytest-"))


def _project_tmp_candidate(path: Path) -> bool:
    return path.is_dir() and (path.name.startswith("pytest") or path.name.startswith("tmp"))


def candidate_rules(root: Path) -> list[Rule]:
    return [
        (root / ".tmp", _root_tmp_candidate, "root pytest/project QC temp directory"),
        (
            root / "projects" / "blind-to-x" / ".tmp",
            _project_tmp_candidate,
            "Blind-to-X pytest/tmp directory",
        ),
        (
            root / "projects" / "shorts-maker-v2" / ".tmp",
            _project_tmp_candidate,
            "Shorts Maker pytest/tmp directory",
        ),
    ]


def is_admin() -> bool:
    if os.name != "nt":
        try:
            return os.geteuid() == 0  # type: ignore[attr-defined]
        except AttributeError:
            return False
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())  # type: ignore[attr-defined]
    except Exception:
        return False


def normalize_under_root(path: Path, root: Path) -> Path:
    root_abs = root.resolve()
    path_abs = path.resolve(strict=False)
    if path_abs == root_abs:
        raise ValueError(f"refusing workspace root: {path_abs}")
    try:
        path_abs.relative_to(root_abs)
    except ValueError as exc:
        raise ValueError(f"refusing path outside workspace: {path_abs}") from exc
    return path_abs


def find_candidates(root: Path = WORKSPACE_ROOT) -> list[dict[str, str]]:
    candidates: list[dict[str, str]] = []
    for base, matcher, reason in candidate_rules(root):
        if not base.exists():
            continue
        for child in sorted(base.iterdir(), key=lambda item: item.name.lower()):
            if matcher(child):
                safe_child = normalize_under_root(child, root)
                candidates.append(
                    {
                        "path": safe_child.relative_to(root.resolve()).as_posix(),
                        "reason": reason,
                    }
                )
    return candidates


def _run(args: list[str]) -> dict[str, Any]:
    completed = subprocess.run(args, capture_output=True, text=True, check=False)
    return {
        "cmd": args[0],
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def repair_acl(path: Path) -> list[dict[str, Any]]:
    if os.name != "nt":
        return []
    account = f"{os.environ.get('USERDOMAIN', '')}\\{os.environ.get('USERNAME', '')}".strip("\\")
    commands = [
        ["takeown", "/F", str(path), "/R", "/D", "Y"],
        ["icacls", str(path), "/reset", "/T", "/C", "/Q"],
        ["icacls", str(path), "/grant", f"{account}:(OI)(CI)F", "/T", "/C", "/Q"],
        ["attrib", "-R", "-S", "-H", str(path), "/S", "/D"],
    ]
    return [_run(command) for command in commands]


def apply_cleanup(root: Path = WORKSPACE_ROOT) -> dict[str, Any]:
    root = root.resolve()
    result: dict[str, Any] = {
        "workspace_root": str(root),
        "admin": is_admin(),
        "deleted": [],
        "failed": [],
    }
    if os.name == "nt" and not result["admin"]:
        result["error"] = "Windows --apply requires an elevated/admin shell."
        return result

    for candidate in find_candidates(root):
        path = normalize_under_root(root / candidate["path"], root)
        repair = repair_acl(path)
        try:
            shutil.rmtree(path)
            result["deleted"].append({**candidate, "repair": repair})
        except Exception as exc:  # pragma: no cover - depends on filesystem ACLs
            result["failed"].append({**candidate, "error": str(exc), "repair": repair})
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="List cleanup candidates without deleting.")
    mode.add_argument("--apply", action="store_true", help="Repair ACLs and delete candidates.")
    parser.add_argument("--json", action="store_true", help="Emit JSON output.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.check:
        payload: dict[str, Any] = {
            "workspace_root": str(WORKSPACE_ROOT),
            "admin": is_admin(),
            "candidates": find_candidates(),
        }
        exit_code = 0
    else:
        payload = apply_cleanup()
        exit_code = 2 if payload.get("error") else (1 if payload["failed"] else 0)

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
