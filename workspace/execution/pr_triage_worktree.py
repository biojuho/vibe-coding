"""
Prepare and clean up isolated git worktrees for PR-style validation.

This helper adapts the useful part of ACPX's PR triage flow to the local-first
Vibe Coding workspace:

- keep the user's active worktree untouched
- create a deterministic isolated worktree under `.tmp/`
- optionally run a merge-conflict preflight against a base ref
- persist the session metadata as JSON for downstream orchestration

The helper is intentionally local-only. It does not fetch, push, comment on
pull requests, or approve workflow runs.

Usage:
    python workspace/execution/pr_triage_worktree.py prepare \
        --repo-path projects/hanwoo-dashboard \
        --head-ref feature/my-branch \
        --base-ref main \
        --label pr-123

    python workspace/execution/pr_triage_worktree.py cleanup \
        --session-dir .tmp/pr_triage_worktrees/hanwoo-dashboard/pr-123-20260331T120000Z
"""

from __future__ import annotations

import argparse
import json
import locale
import re
import shutil
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = WORKSPACE_ROOT.parent
TMP_ROOT = REPO_ROOT / ".tmp" / "pr_triage_worktrees"


@dataclass(frozen=True)
class GitResult:
    returncode: int
    stdout: str
    stderr: str


def _decode_output(payload: bytes) -> str:
    encodings = [
        "utf-8",
        getattr(locale, "getencoding", lambda: None)(),
        locale.getpreferredencoding(False),
        "cp949",
    ]
    for encoding in encodings:
        if not encoding:
            continue
        try:
            return payload.decode(encoding)
        except UnicodeDecodeError:
            continue
    return payload.decode("utf-8", errors="replace")


def _run_git(repo_path: Path, args: list[str], *, check: bool = True) -> GitResult:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo_path,
        capture_output=True,
        check=False,
    )
    result = GitResult(
        returncode=completed.returncode,
        stdout=_decode_output(completed.stdout).strip(),
        stderr=_decode_output(completed.stderr).strip(),
    )
    if check and result.returncode != 0:
        raise RuntimeError(
            "\n".join(
                [
                    f"git {' '.join(args)} failed with exit code {result.returncode}",
                    f"cwd: {repo_path}",
                    f"stdout: {result.stdout or '(empty)'}",
                    f"stderr: {result.stderr or '(empty)'}",
                ]
            )
        )
    return result


def _utc_timestamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def _slugify(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip())
    slug = slug.strip("-._")
    return slug or "session"


def _resolve_repo_root(repo_path: Path) -> Path:
    root_text = _run_git(repo_path, ["rev-parse", "--show-toplevel"]).stdout
    return Path(root_text)


def _resolve_commit(repo_root: Path, ref: str) -> str:
    return _run_git(repo_root, ["rev-parse", f"{ref}^{{commit}}"]).stdout


def _relative_to_root(path: Path, root: Path) -> str | None:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return None


def _session_root_for_repo(repo_root: Path) -> Path:
    return TMP_ROOT / _slugify(repo_root.name or "repo")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _ensure_inside_tmp(path: Path) -> None:
    resolved = path.resolve()
    tmp_root = TMP_ROOT.resolve()
    if not resolved.is_relative_to(tmp_root):
        raise ValueError(f"Refusing to operate outside {tmp_root}: {resolved}")


def _cleanup_merge_state(worktree_path: Path) -> None:
    _run_git(worktree_path, ["merge", "--abort"], check=False)
    _run_git(worktree_path, ["reset", "--hard", "HEAD"], check=False)


def _remove_worktree(repo_path: Path, worktree_path: Path) -> None:
    if worktree_path.exists():
        _run_git(repo_path, ["worktree", "remove", "--force", str(worktree_path)], check=False)
    _run_git(repo_path, ["worktree", "prune"], check=False)


def collect_conflict_state(worktree_path: Path, base_ref: str) -> dict[str, Any]:
    _cleanup_merge_state(worktree_path)
    merge_base = _run_git(worktree_path, ["merge-base", "HEAD", base_ref], check=False).stdout
    merge_attempt = _run_git(
        worktree_path,
        ["merge", "--no-commit", "--no-ff", base_ref],
        check=False,
    )
    conflicted_files = _run_git(
        worktree_path,
        ["diff", "--name-only", "--diff-filter=U"],
        check=False,
    ).stdout.splitlines()
    status = "conflicted" if conflicted_files else "clean"
    state = {
        "status": status,
        "base_ref": base_ref,
        "merge_base": merge_base,
        "conflicted_files": conflicted_files,
        "merge_stdout": merge_attempt.stdout,
        "merge_stderr": merge_attempt.stderr,
        "merge_exit_code": merge_attempt.returncode,
    }
    _cleanup_merge_state(worktree_path)
    return state


def prepare_session(
    repo_path: Path,
    head_ref: str,
    *,
    base_ref: str | None = None,
    label: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    repo_root = _resolve_repo_root(repo_path)
    repo_rel_path = _relative_to_root(repo_root, REPO_ROOT)
    head_sha = _resolve_commit(repo_root, head_ref)
    base_sha = _resolve_commit(repo_root, base_ref) if base_ref else None
    session_label = _slugify(label or head_ref)
    session_dir = _session_root_for_repo(repo_root) / f"{session_label}-{_utc_timestamp()}"
    worktree_path = session_dir / "repo"
    conflict_state_path = session_dir / "conflict-state.json"
    manifest_path = session_dir / "manifest.json"

    session_dir.mkdir(parents=True, exist_ok=False)
    try:
        _run_git(repo_root, ["worktree", "add", "--detach", str(worktree_path), head_sha])
    except Exception:
        shutil.rmtree(session_dir, ignore_errors=True)
        raise

    try:
        branch_text = _run_git(worktree_path, ["branch", "--show-current"], check=False).stdout
        conflict_state = (
            collect_conflict_state(worktree_path, base_ref)
            if base_ref
            else {
                "status": "skipped",
                "base_ref": None,
                "merge_base": "",
                "conflicted_files": [],
                "merge_stdout": "",
                "merge_stderr": "",
                "merge_exit_code": 0,
            }
        )
        manifest = {
            "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "repo_path": str(repo_root),
            "repo_rel_path": repo_rel_path,
            "session_dir": str(session_dir),
            "worktree_path": str(worktree_path),
            "label": session_label,
            "head_ref": head_ref,
            "head_sha": head_sha,
            "base_ref": base_ref,
            "base_sha": base_sha,
            "worktree_branch": branch_text or None,
            "conflict_check": conflict_state,
            "metadata": metadata or {},
            "artifacts": {
                "manifest_path": str(manifest_path),
                "conflict_state_path": str(conflict_state_path),
            },
        }
        _write_json(conflict_state_path, conflict_state)
        _write_json(manifest_path, manifest)
        return manifest
    except Exception:
        _remove_worktree(repo_root, worktree_path)
        shutil.rmtree(session_dir, ignore_errors=True)
        raise


def cleanup_session(session_dir: Path, *, keep_session_dir: bool = False) -> dict[str, Any]:
    _ensure_inside_tmp(session_dir)
    manifest_path = session_dir / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Missing manifest: {manifest_path}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    repo_path = Path(manifest["repo_path"])
    worktree_path = Path(manifest["worktree_path"])

    _remove_worktree(repo_path, worktree_path)

    if not keep_session_dir and session_dir.exists():
        shutil.rmtree(session_dir, ignore_errors=True)

    return {
        "session_dir": str(session_dir),
        "worktree_path": str(worktree_path),
        "removed": not worktree_path.exists(),
        "session_dir_exists": session_dir.exists(),
    }


def _load_metadata(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise ValueError("--metadata-json must decode to a JSON object")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare isolated git worktrees for PR triage")
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare_parser = subparsers.add_parser("prepare")
    prepare_parser.add_argument("--repo-path", required=True, help="Local path to a git repo or a child directory")
    prepare_parser.add_argument("--head-ref", required=True, help="Branch, tag, or commit to check out")
    prepare_parser.add_argument("--base-ref", help="Optional base branch/ref for conflict preflight")
    prepare_parser.add_argument("--label", help="Optional session label (for example: pr-123)")
    prepare_parser.add_argument(
        "--metadata-json",
        help="Optional JSON object with extra PR metadata to persist into the manifest",
    )

    cleanup_parser = subparsers.add_parser("cleanup")
    cleanup_parser.add_argument("--session-dir", required=True, help="Session directory created by prepare")
    cleanup_parser.add_argument(
        "--keep-session-dir",
        action="store_true",
        help="Remove the git worktree registration but keep the session folder and JSON artifacts",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "prepare":
            payload = prepare_session(
                Path(args.repo_path),
                args.head_ref,
                base_ref=args.base_ref,
                label=args.label,
                metadata=_load_metadata(args.metadata_json),
            )
        else:
            payload = cleanup_session(Path(args.session_dir), keep_session_dir=args.keep_session_dir)
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2, ensure_ascii=False))
        return 1

    print(json.dumps({"ok": True, "result": payload}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
