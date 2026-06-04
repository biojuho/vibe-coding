"""Block accidental reuse of T-#### task IDs in normal commit messages.

The `task-id` workflow already suggests the next safe ID, but a user or agent
can still type a stale ID into a commit message. This script is designed for
Git's `commit-msg` hook: it compares the current commit message against recent
commit subjects/bodies and blocks non-context commits that reuse an exact task
ID.

`[ai-context]` commits are intentionally allowed to mention an existing task ID
because they record follow-up evidence for the same cycle. When two tools truly
collide at the same instant, the documented fallback is a suffixed ID such as
`T-1254b`; this gate allows that as long as the exact suffixed ID is new.
"""

from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
AI_CONTEXT_PREFIX = "[ai-context]"
_TASK_ID_PATTERN = re.compile(r"\bT-(\d{4,})([a-z])?\b")


def _message_text(path: Path) -> str:
    raw = path.read_text(encoding="utf-8-sig", errors="replace")
    lines = []
    for line in raw.splitlines():
        if line.lstrip().startswith("#"):
            continue
        lines.append(line)
    return "\n".join(lines).strip()


def commit_subject(message_text: str) -> str:
    for line in message_text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return ""


def is_ai_context_subject(subject: str) -> bool:
    return subject.startswith(AI_CONTEXT_PREFIX)


def extract_task_ids(text: str) -> set[str]:
    return {f"T-{number}{suffix or ''}" for number, suffix in _TASK_ID_PATTERN.findall(text)}


def git_log_text(window: int) -> str:
    try:
        result = subprocess.run(
            ["git", "log", f"-{window}", "--format=%s%n%b"],
            cwd=str(ROOT),
            capture_output=True,
            check=False,
        )
    except FileNotFoundError:
        return ""
    if result.returncode != 0:
        return ""
    return result.stdout.decode("utf-8", errors="replace")


def find_duplicate_task_ids(
    message_text: str,
    *,
    history_text: str,
    allow_ai_context: bool = True,
) -> list[str]:
    subject = commit_subject(message_text)
    if allow_ai_context and is_ai_context_subject(subject):
        return []

    current_ids = extract_task_ids(message_text)
    if not current_ids:
        return []

    history_ids = extract_task_ids(history_text)
    return sorted(current_ids & history_ids)


def suggested_next_id(git_window: int) -> str | None:
    try:
        from next_task_id import suggest_next_id

        return str(suggest_next_id(git_window=git_window)["suggested_id"])
    except Exception:
        return None


def build_error(duplicates: list[str], *, git_window: int) -> str:
    lines = [
        "Task ID gate blocked this commit.",
        "The commit message reuses task ID(s) already present in recent git history:",
    ]
    for task_id in duplicates:
        lines.append(f"  - {task_id}")
    lines.extend(
        [
            "",
            "`[ai-context]` follow-up commits may reference an existing task ID.",
            "For a new normal commit, run `python execution/next_task_id.py --json` right before committing.",
        ]
    )
    suggestion = suggested_next_id(git_window)
    if suggestion:
        lines.append(f"Suggested next ID from the current state: {suggestion}")
    lines.append("For a same-second collision fallback, use a new suffixed ID such as `T-1254b`.")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Block duplicate task IDs in normal commit messages.")
    parser.add_argument("commit_message_file", type=Path, help="Path to the Git commit message file.")
    parser.add_argument(
        "--git-window",
        type=int,
        default=100,
        help="Number of recent git commits to scan for task IDs (default: 100).",
    )
    parser.add_argument(
        "--history-text",
        default=None,
        help="Override git history text for tests.",
    )
    args = parser.parse_args(argv)

    text = _message_text(args.commit_message_file)
    history = args.history_text if args.history_text is not None else git_log_text(args.git_window)
    duplicates = find_duplicate_task_ids(text, history_text=history)
    if not duplicates:
        return 0

    print(build_error(duplicates, git_window=args.git_window))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
