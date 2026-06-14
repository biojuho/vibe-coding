#!/usr/bin/env python3
"""Regenerate approval pathspec coverage from the current dirty handoff."""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DEFAULT_HANDOFF_PATH = Path(".tmp/scoped-dirty-worktree-handoff-plan-current.json")
DEFAULT_OUTPUT_JSON = Path(".tmp/approval-pathspec-consistency-current.json")
DEFAULT_OUTPUT_MD = Path(".tmp/approval-pathspec-consistency-current.md")
DEFAULT_COVERAGE_JSON = Path(".tmp/authorization-coverage-current.json")
DEFAULT_COVERAGE_MD = Path(".tmp/authorization-coverage-current.md")
DEFAULT_COMBINED_PATHSPEC = Path(".tmp/approval-pathspec-combined-current.pathspec")
DEFAULT_PATHSPEC_GLOB = "approve-*.pathspec"


class _WriteFailure(Exception):
    def __init__(self, path: Path, cause: OSError) -> None:
        super().__init__(f"{type(cause).__name__}: {cause}")
        self.path = path
        self.cause = cause


def _resolve(root: Path, path: Path) -> Path:
    return path if path.is_absolute() else root / path


def _read_json(path: Path) -> dict[str, Any]:
    try:
        parsed = json.loads(path.read_text(encoding="utf-8-sig"))
    except (FileNotFoundError, OSError, UnicodeError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _normalize_path(path: str) -> str:
    return path.replace("\\", "/").strip()


def _parse_porcelain_path(line: str) -> str:
    path = line[2:].lstrip() if len(line) > 2 else ""
    if " -> " in path:
        path = path.rsplit(" -> ", 1)[-1]
    return _normalize_path(path)


def _git_lines(root: Path, args: list[str]) -> list[str]:
    completed = subprocess.run(
        ["git", *args],
        cwd=root,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        return []
    return [line for line in completed.stdout.splitlines() if line.strip()]


def _live_dirty_paths(root: Path) -> list[str]:
    lines = _git_lines(root, ["-c", "core.quotepath=false", "status", "--porcelain=v1", "--untracked-files=all"])
    return sorted({path for line in lines if (path := _parse_porcelain_path(line))})


def _live_staged_paths(root: Path) -> list[str]:
    return sorted({_normalize_path(line) for line in _git_lines(root, ["diff", "--cached", "--name-only"])})


def _handoff_signature_input(handoff: dict[str, Any]) -> dict[str, Any]:
    signature = _as_dict(handoff.get("dirty_signature"))
    return _as_dict(signature.get("input"))


def _dirty_paths_from_handoff(handoff: dict[str, Any]) -> list[str]:
    signature_input = _handoff_signature_input(handoff)
    return sorted(
        {_normalize_path(str(path)) for path in _as_list(signature_input.get("dirty_paths")) if str(path).strip()},
    )


def _staged_count_from_handoff(handoff: dict[str, Any]) -> int | None:
    signature_input = _handoff_signature_input(handoff)
    if "staged" not in signature_input:
        return None
    try:
        return int(signature_input.get("staged") or 0)
    except (TypeError, ValueError):
        return None


def _read_pathspec(path: Path) -> list[str]:
    try:
        raw = path.read_text(encoding="utf-8-sig")
    except UnicodeError:
        try:
            raw = path.read_text(encoding="utf-16")
        except (OSError, UnicodeError):
            return []
    except OSError:
        return []
    entries: list[str] = []
    for line in raw.splitlines():
        normalized = _normalize_path(line)
        if normalized and not normalized.startswith("#"):
            entries.append(normalized)
    return entries


def _is_evidence_path(path: str) -> bool:
    return (
        path.startswith(".ai/") or path.startswith(".tmp/") or path.startswith("output/") or path.startswith(".cache/")
    )


def build_report(
    *,
    root: Path,
    handoff_json: Path,
    pathspec_dir: Path,
    pathspec_glob: str = DEFAULT_PATHSPEC_GLOB,
    generated_at: str | None = None,
) -> dict[str, Any]:
    handoff = _read_json(handoff_json)
    handoff_dirty_paths = _dirty_paths_from_handoff(handoff)
    live_dirty_paths = _live_dirty_paths(root)
    dirty_paths = live_dirty_paths or handoff_dirty_paths
    handoff_matches_live = None
    handoff_only_dirty_paths: list[str] = []
    live_only_dirty_paths: list[str] = []
    if handoff_dirty_paths and live_dirty_paths:
        handoff_set = set(handoff_dirty_paths)
        live_set = set(live_dirty_paths)
        handoff_matches_live = handoff_set == live_set
        handoff_only_dirty_paths = sorted(handoff_set - live_set)
        live_only_dirty_paths = sorted(live_set - handoff_set)
    staged_paths = _live_staged_paths(root)
    staged_count = len(staged_paths)
    if not staged_paths and (handoff_staged := _staged_count_from_handoff(handoff)) is not None:
        staged_count = handoff_staged

    dirty_set = set(dirty_paths)
    pathspec_files = sorted(pathspec_dir.glob(pathspec_glob))
    pathspec_results: list[dict[str, Any]] = []
    covered_dirty: set[str] = set()
    all_entries: set[str] = set()
    empty_pathspecs: list[str] = []

    for pathspec in pathspec_files:
        entries = _read_pathspec(pathspec)
        unique_entries = sorted(set(entries))
        if not unique_entries:
            empty_pathspecs.append(pathspec.name)
        entry_set = set(unique_entries)
        covered = sorted(entry_set & dirty_set)
        all_entries.update(entry_set)
        covered_dirty.update(covered)
        pathspec_results.append(
            {
                "pathspec": pathspec.name,
                "path_count": len(entries),
                "unique_path_count": len(unique_entries),
                "duplicate_count": len(entries) - len(unique_entries),
                "covered_dirty_count": len(covered),
                "covered_dirty_paths": covered,
                "extra_non_dirty_count": len(entry_set - dirty_set),
                "extra_non_dirty_paths": sorted(entry_set - dirty_set),
                "mode": "coverage_intersection",
            },
        )

    uncovered_dirty = sorted(dirty_set - covered_dirty)
    uncovered_non_evidence = [path for path in uncovered_dirty if not _is_evidence_path(path)]
    extra_non_dirty = sorted(all_entries - dirty_set)
    status = "ok"
    if not pathspec_files:
        status = "pathspecs_unavailable"
    elif staged_count:
        status = "staged_changes_present"
    elif uncovered_dirty:
        status = "needs_refresh"
    elif handoff_matches_live is False:
        status = "stale_handoff"

    return {
        "generated_at": generated_at or datetime.now(UTC).isoformat(),
        "status": status,
        "basis": "live git dirty pathspec coverage intersection when available, no real staging",
        "input_source": "live_git_dirty_paths" if live_dirty_paths else "dirty_handoff_signature",
        "dirty_count": len(dirty_paths),
        "dirty_paths": dirty_paths,
        "handoff_dirty_count": len(handoff_dirty_paths),
        "handoff_dirty_paths": handoff_dirty_paths,
        "live_dirty_count": len(live_dirty_paths),
        "live_dirty_paths": live_dirty_paths,
        "handoff_matches_live": handoff_matches_live,
        "handoff_only_dirty_count": len(handoff_only_dirty_paths),
        "handoff_only_dirty_paths": handoff_only_dirty_paths,
        "live_only_dirty_count": len(live_only_dirty_paths),
        "live_only_dirty_paths": live_only_dirty_paths,
        "covered_dirty_count": len(covered_dirty),
        "covered_dirty_paths": sorted(covered_dirty),
        "uncovered_dirty_count": len(uncovered_dirty),
        "uncovered_dirty_paths": uncovered_dirty,
        "uncovered_non_evidence_source_count": len(uncovered_non_evidence),
        "uncovered_non_evidence_source_paths": uncovered_non_evidence,
        "pathspec_count": len(pathspec_files),
        "pathspec_entry_count": sum(result["path_count"] for result in pathspec_results),
        "unique_pathspec_entry_count": len(all_entries),
        "empty_pathspec_count": len(empty_pathspecs),
        "empty_pathspecs": empty_pathspecs,
        "extra_non_dirty_count": len(extra_non_dirty),
        "extra_non_dirty_paths": extra_non_dirty,
        "staged_count": staged_count,
        "staged_paths": staged_paths,
        "pathspec_results": pathspec_results,
        "side_effects_performed": {
            "real_staging": False,
            "commit_created": False,
            "push_performed": False,
            "reverted_changes": False,
        },
    }


def coverage_summary(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "generated_at": report.get("generated_at"),
        "status": report.get("status"),
        "dirty_count": report.get("dirty_count"),
        "covered_dirty_count": report.get("covered_dirty_count"),
        "uncovered_dirty_count": report.get("uncovered_dirty_count"),
        "uncovered_dirty_paths": report.get("uncovered_dirty_paths", []),
        "uncovered_non_evidence_source_count": report.get("uncovered_non_evidence_source_count"),
        "uncovered_non_evidence_source_paths": report.get("uncovered_non_evidence_source_paths", []),
        "pathspec_count": report.get("pathspec_count"),
        "empty_pathspec_count": report.get("empty_pathspec_count"),
        "empty_pathspecs": report.get("empty_pathspecs", []),
        "input_source": report.get("input_source"),
        "handoff_dirty_count": report.get("handoff_dirty_count"),
        "live_dirty_count": report.get("live_dirty_count"),
        "handoff_matches_live": report.get("handoff_matches_live"),
        "handoff_only_dirty_count": report.get("handoff_only_dirty_count"),
        "handoff_only_dirty_paths": report.get("handoff_only_dirty_paths", []),
        "live_only_dirty_count": report.get("live_only_dirty_count"),
        "live_only_dirty_paths": report.get("live_only_dirty_paths", []),
        "staged_count": report.get("staged_count"),
        "staged_paths": report.get("staged_paths", []),
        "basis": report.get("basis"),
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Approval Pathspec Consistency",
        "",
        f"- Status: `{report.get('status')}`",
        f"- Input source: `{report.get('input_source')}`",
        f"- Dirty / covered / uncovered: `{report.get('dirty_count')}` / `{report.get('covered_dirty_count')}` / `{report.get('uncovered_dirty_count')}`",
        f"- Handoff / live dirty: `{report.get('handoff_dirty_count')}` / `{report.get('live_dirty_count')}`",
        f"- Handoff matches live: `{report.get('handoff_matches_live')}`",
        f"- Pathspec files: `{report.get('pathspec_count')}`",
        f"- Staged paths: `{report.get('staged_count')}`",
        f"- Extra non-dirty paths: `{report.get('extra_non_dirty_count')}`",
        "",
    ]
    uncovered = _as_list(report.get("uncovered_dirty_paths"))
    if uncovered:
        lines.extend(["## Uncovered Dirty Paths", ""])
        lines.extend(f"- `{path}`" for path in uncovered)
        lines.append("")
    lines.extend(
        [
            "## Boundary",
            "",
            "This validates approval pathspec coverage only. It does not stage, commit, push, revert, retry T-251, or mark the goal complete.",
            "",
        ],
    )
    return "\n".join(lines)


def _write_text(path: Path, text: str) -> None:
    tmp = path.with_name(f"{path.name}.refresh-tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(text, encoding="utf-8", newline="\n")
        tmp.replace(path)
    except OSError as exc:
        try:
            if tmp.is_file() or tmp.is_symlink():
                tmp.unlink()
        except OSError:
            pass
        raise _WriteFailure(path, exc) from exc


def _prepare_text(path: Path, text: str) -> Path:
    tmp = path.with_name(f"{path.name}.refresh-tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(text, encoding="utf-8", newline="\n")
    except OSError as exc:
        try:
            if tmp.is_file() or tmp.is_symlink():
                tmp.unlink()
        except OSError:
            pass
        raise _WriteFailure(path, exc) from exc
    return tmp


def _cleanup_prepared(paths: list[Path]) -> None:
    for path in paths:
        try:
            if path.is_file() or path.is_symlink():
                path.unlink()
        except OSError:
            pass


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    _write_text(path, json.dumps(payload, ensure_ascii=True, indent=2) + "\n")


def write_outputs(
    *,
    report: dict[str, Any],
    output_json: Path,
    output_md: Path,
    coverage_json: Path,
    coverage_md: Path,
    combined_pathspec: Path,
) -> None:
    markdown = render_markdown(report)
    outputs = [
        (output_json, json.dumps(report, ensure_ascii=True, indent=2) + "\n"),
        (coverage_json, json.dumps(coverage_summary(report), ensure_ascii=True, indent=2) + "\n"),
        (output_md, markdown),
        (coverage_md, markdown),
        (combined_pathspec, "\n".join(_as_list(report.get("covered_dirty_paths"))) + "\n"),
    ]
    prepared: list[tuple[Path, Path]] = []
    try:
        for path, text in outputs:
            prepared.append((path, _prepare_text(path, text)))
        for path, tmp in prepared:
            tmp.replace(path)
    except OSError as exc:
        _cleanup_prepared([tmp for _, tmp in prepared])
        path = next((target for target, tmp in prepared if tmp.exists()), output_json)
        raise _WriteFailure(path, exc) from exc
    except _WriteFailure:
        _cleanup_prepared([tmp for _, tmp in prepared])
        raise


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--handoff-json", type=Path, default=DEFAULT_HANDOFF_PATH)
    parser.add_argument("--pathspec-dir", type=Path, default=Path(".tmp"))
    parser.add_argument("--pathspec-glob", default=DEFAULT_PATHSPEC_GLOB)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    parser.add_argument("--coverage-json", type=Path, default=DEFAULT_COVERAGE_JSON)
    parser.add_argument("--coverage-md", type=Path, default=DEFAULT_COVERAGE_MD)
    parser.add_argument("--combined-pathspec", type=Path, default=DEFAULT_COMBINED_PATHSPEC)
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = args.root.resolve()
    report = build_report(
        root=root,
        handoff_json=_resolve(root, args.handoff_json),
        pathspec_dir=_resolve(root, args.pathspec_dir),
        pathspec_glob=args.pathspec_glob,
    )
    try:
        write_outputs(
            report=report,
            output_json=_resolve(root, args.output_json),
            output_md=_resolve(root, args.output_md),
            coverage_json=_resolve(root, args.coverage_json),
            coverage_md=_resolve(root, args.coverage_md),
            combined_pathspec=_resolve(root, args.combined_pathspec),
        )
    except _WriteFailure as exc:
        report["status"] = "write_failed"
        report["write_error"] = str(exc)
        report["write_error_path"] = exc.path.as_posix()
        if args.json:
            print(json.dumps(report, ensure_ascii=True, indent=2))
        else:
            print(f"status=write_failed path={exc.path.as_posix()} error={exc}", flush=True)
        return 4
    if args.json:
        print(json.dumps(report, ensure_ascii=True, indent=2))
    else:
        print(
            "status={status} dirty={dirty_count} covered={covered_dirty_count} uncovered={uncovered_dirty_count}".format(
                **report,
            ),
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
