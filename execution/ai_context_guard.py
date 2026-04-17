"""
Guard `[ai-context]` commits from accidental staged-file spillover.

This script is designed for deterministic use from Git's `commit-msg` hook.
It inspects the commit message and, only for `[ai-context]` commits, blocks the
commit when staged files fall outside the approved context-document scope.

Usage:
    python execution/ai_context_guard.py .git/COMMIT_EDITMSG
    python execution/ai_context_guard.py .git/COMMIT_EDITMSG --staged-file .ai/HANDOFF.md
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path, PurePosixPath


AI_CONTEXT_PREFIX = "[ai-context]"
ALLOWED_EXACT = {
    ".ai/HANDOFF.md",
    ".ai/TASKS.md",
    ".ai/SESSION_LOG.md",
    ".ai/CONTEXT.md",
    ".ai/DECISIONS.md",
}
ALLOWED_ARCHIVE_ROOT = PurePosixPath(".ai/archive")


def normalize_repo_path(path: str) -> str:
    return PurePosixPath(path.replace("\\", "/")).as_posix()


def read_commit_subject(message_file: Path) -> str:
    text = message_file.read_text(encoding="utf-8-sig")
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return ""


def is_ai_context_commit(subject: str) -> bool:
    return subject.startswith(AI_CONTEXT_PREFIX)


def get_staged_files() -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if result.returncode != 0:
        return []
    return [normalize_repo_path(line) for line in result.stdout.splitlines() if line.strip()]


def is_allowed_context_path(path: str) -> bool:
    normalized = normalize_repo_path(path)
    if normalized in ALLOWED_EXACT:
        return True

    pure = PurePosixPath(normalized)
    if pure.parent == ALLOWED_ARCHIVE_ROOT and pure.suffix == ".md":
        return True

    return False


def find_disallowed_paths(paths: list[str]) -> list[str]:
    return [path for path in paths if not is_allowed_context_path(path)]


def build_error(subject: str, disallowed_paths: list[str]) -> str:
    lines = []
    lines.append("AI context commit guard blocked this commit.")
    lines.append(f"Commit subject: {subject}")
    lines.append("")
    lines.append("`[ai-context]` commits may stage only context-maintenance files:")
    for path in sorted(ALLOWED_EXACT):
        lines.append(f"  - {path}")
    lines.append("  - .ai/archive/*.md")
    lines.append("")
    lines.append("Disallowed staged files:")
    for path in disallowed_paths:
        lines.append(f"  - {path}")
    lines.append("")
    lines.append("Next step: unstage unrelated files or commit context files with explicit pathspecs.")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Block accidental staged-file spillover in [ai-context] commits.")
    parser.add_argument("commit_message_file", help="Path to the Git commit message file.")
    parser.add_argument(
        "--staged-file",
        action="append",
        default=[],
        help="Override staged-file detection for tests.",
    )
    args = parser.parse_args(argv)

    subject = read_commit_subject(Path(args.commit_message_file))
    if not is_ai_context_commit(subject):
        return 0

    staged_files = [normalize_repo_path(path) for path in args.staged_file] or get_staged_files()
    if not staged_files:
        return 0

    disallowed = find_disallowed_paths(staged_files)
    if not disallowed:
        return 0

    print(build_error(subject, disallowed))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
