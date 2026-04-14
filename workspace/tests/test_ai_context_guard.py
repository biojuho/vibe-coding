from __future__ import annotations

import contextlib
import importlib.util
import io
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "execution" / "ai_context_guard.py"
HOOK = REPO_ROOT / ".githooks" / "commit-msg"
SPEC = importlib.util.spec_from_file_location("ai_context_guard", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def run_guard(tmp_path: Path, subject: str, *staged_files: str) -> tuple[int, str]:
    message_file = tmp_path / "COMMIT_EDITMSG"
    message_file.write_text(subject + "\n", encoding="utf-8")

    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout):
        code = MODULE.main(
            [
                str(message_file),
                *[item for staged in staged_files for item in ("--staged-file", staged)],
            ]
        )
    return code, stdout.getvalue()


def test_non_ai_context_commit_is_ignored(tmp_path: Path) -> None:
    code, output = run_guard(tmp_path, "feat: add dashboard guard", "projects/hanwoo-dashboard/package.json")

    assert code == 0
    assert output == ""


def test_ai_context_commit_allows_known_context_files(tmp_path: Path) -> None:
    code, output = run_guard(
        tmp_path,
        "[ai-context] 세션 로그 업데이트",
        ".ai/HANDOFF.md",
        ".ai/TASKS.md",
        ".ai/archive/SESSION_LOG_before_2026-03-23.md",
    )

    assert code == 0
    assert output == ""


def test_ai_context_commit_blocks_disallowed_files(tmp_path: Path) -> None:
    code, output = run_guard(
        tmp_path,
        "[ai-context] 세션 로그 업데이트",
        ".ai/HANDOFF.md",
        "projects/hanwoo-dashboard/package.json",
    )

    assert code == 1
    assert "projects/hanwoo-dashboard/package.json" in output
    assert "AI context commit guard blocked this commit." in output


def test_ai_context_commit_handles_utf8_bom_subject(tmp_path: Path) -> None:
    message_file = tmp_path / "COMMIT_EDITMSG"
    message_file.write_text("[ai-context] 세션 로그 업데이트\n", encoding="utf-8-sig")

    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout):
        code = MODULE.main(
            [
                str(message_file),
                "--staged-file",
                ".ai/HANDOFF.md",
                "--staged-file",
                "projects/hanwoo-dashboard/package.json",
            ]
        )

    assert code == 1
    assert "projects/hanwoo-dashboard/package.json" in stdout.getvalue()


def test_commit_msg_hook_invokes_ai_context_guard() -> None:
    hook_text = HOOK.read_text(encoding="utf-8")

    assert 'python execution/ai_context_guard.py "$1"' in hook_text
