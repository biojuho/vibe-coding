from __future__ import annotations

import contextlib
import importlib.util
import io
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "execution" / "task_id_gate.py"
HOOK = REPO_ROOT / ".githooks" / "commit-msg"
SPEC = importlib.util.spec_from_file_location("task_id_gate", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def run_gate(tmp_path: Path, subject: str, history: str, head_subject: str = "") -> tuple[int, str]:
    message_file = tmp_path / "COMMIT_EDITMSG"
    message_file.write_text(subject + "\n", encoding="utf-8")

    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout):
        code = MODULE.main([str(message_file), "--history-text", history, "--head-subject", head_subject])
    return code, stdout.getvalue()


def test_non_task_commit_is_ignored(tmp_path: Path) -> None:
    code, output = run_gate(tmp_path, "feat: improve dashboard copy", "feat: T-1254 older work")

    assert code == 0
    assert output == ""


def test_ai_context_followup_can_reference_existing_task(tmp_path: Path) -> None:
    code, output = run_gate(tmp_path, "[ai-context] record T-1254 CI success", "feat: T-1254 older work")

    assert code == 0
    assert output == ""


def test_normal_commit_blocks_unsuffixed_duplicate_task_id(tmp_path: Path) -> None:
    code, output = run_gate(tmp_path, "feat(blind-to-x): T-1254 migrate SDK", "feat: T-1254 older work")

    assert code == 1
    assert "Task ID gate blocked this commit." in output
    assert "T-1254" in output
    assert "python execution/next_task_id.py --json" in output


def test_no_edit_amend_can_reuse_head_task_id(tmp_path: Path) -> None:
    subject = "feat(readiness): T-1257 add workspace release gates"

    code, output = run_gate(tmp_path, subject, subject, head_subject=subject)

    assert code == 0
    assert output == ""


def test_duplicate_task_id_with_different_subject_still_blocks(tmp_path: Path) -> None:
    head_subject = "feat(readiness): T-1257 add workspace release gates"

    code, output = run_gate(
        tmp_path,
        "fix(readiness): T-1257 tweak release gates",
        head_subject,
        head_subject=head_subject,
    )

    assert code == 1
    assert "T-1257" in output


def test_suffix_fallback_is_allowed_when_exact_suffix_is_new(tmp_path: Path) -> None:
    code, output = run_gate(tmp_path, "feat(blind-to-x): T-1254b migrate SDK", "feat: T-1254 older work")

    assert code == 0
    assert output == ""


def test_suffix_fallback_blocks_when_exact_suffix_already_exists(tmp_path: Path) -> None:
    code, output = run_gate(tmp_path, "feat(blind-to-x): T-1254b migrate SDK", "feat: T-1254b older work")

    assert code == 1
    assert "T-1254b" in output


def test_commit_msg_hook_invokes_task_id_gate() -> None:
    hook_text = HOOK.read_text(encoding="utf-8")

    assert 'python execution/task_id_gate.py "$1"' in hook_text
