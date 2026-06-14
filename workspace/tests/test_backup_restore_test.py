from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import execution.backup_restore_test as restore_module


def _backup_root(tmp_path: Path) -> Path:
    onedrive = tmp_path / "OneDrive"
    backup = onedrive / "VibeCodingBackup" / "backup_20260610_0700"
    backup.mkdir(parents=True)
    return backup


def test_backup_database_files_keeps_supported_extensions_sorted(tmp_path: Path) -> None:
    backup = _backup_root(tmp_path)
    (backup / "b.sqlite3").write_text("placeholder", encoding="utf-8")
    (backup / "a.db").write_text("placeholder", encoding="utf-8")
    (backup / "ignored.txt").write_text("placeholder", encoding="utf-8")
    nested = backup / "nested"
    nested.mkdir()
    (nested / "c.sqlite").write_text("placeholder", encoding="utf-8")

    paths = [path.relative_to(backup).as_posix() for path in restore_module._backup_database_files(backup)]

    assert paths == ["a.db", "b.sqlite3", "nested/c.sqlite"]


def test_database_restore_check_dry_run_reports_relative_path(tmp_path: Path) -> None:
    backup = _backup_root(tmp_path)
    db_path = backup / "data.sqlite"
    db_path.write_text("placeholder", encoding="utf-8")

    result = restore_module._database_restore_check(backup, db_path, dry_run=True)

    assert result == {"path": "data.sqlite", "dry_run": True}


def test_run_restore_test_dry_run_passes_with_required_files(tmp_path: Path, monkeypatch) -> None:
    backup = _backup_root(tmp_path)
    monkeypatch.setenv("OneDrive", str(tmp_path / "OneDrive"))
    for rel_path in restore_module.CRITICAL_FILES:
        path = backup / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("ok", encoding="utf-8")
    (backup / "workspace.db").write_text("placeholder", encoding="utf-8")

    result = restore_module.run_restore_test(dry_run=True)

    assert result["overall"] == "PASS"
    assert result["backup_found"] is True
    assert result["db_checks"] == [{"path": "workspace.db", "dry_run": True}]
    assert all(check["exists"] for check in result["file_checks"])


def test_direct_script_json_dry_run_does_not_require_pythonpath(tmp_path: Path) -> None:
    env = os.environ.copy()
    env["OneDrive"] = ""
    env["PYTHONPATH"] = ""
    env["PYTHON_DOTENV_DISABLED"] = "1"

    completed = subprocess.run(
        [
            sys.executable,
            str(Path(restore_module.__file__).resolve()),
            "--json",
            "--dry-run",
            "--no-notify",
        ],
        cwd=tmp_path,
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0
    assert "ModuleNotFoundError" not in completed.stderr
    payload = json.loads(completed.stdout)
    assert set(payload) >= {"overall", "backup_found", "db_checks", "file_checks", "errors"}
