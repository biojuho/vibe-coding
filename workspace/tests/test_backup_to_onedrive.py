from __future__ import annotations

import json
from pathlib import Path

import execution.backup_to_onedrive as backup_module


def _configure_paths(tmp_path, monkeypatch):
    root = tmp_path / "workspace"
    onedrive = tmp_path / "OneDrive"
    root.mkdir()
    onedrive.mkdir()

    monkeypatch.setattr(backup_module, "_ROOT", root)
    monkeypatch.setattr(backup_module, "_ONEDRIVE", onedrive)
    monkeypatch.setattr(backup_module, "_BACKUP_ROOT", onedrive / "VibeCodingBackup")
    monkeypatch.setattr(backup_module, "_STATUS_FILE", root / ".tmp" / "backup_status.json")
    return root, onedrive


def test_backup_dry_run_counts_only_allowed_files(tmp_path, monkeypatch) -> None:
    root, _ = _configure_paths(tmp_path, monkeypatch)
    monkeypatch.setattr(backup_module, "MAX_FILE_SIZE", 12)

    (root / "keep.py").write_text("print('ok')", encoding="utf-8")
    (root / "build").mkdir()
    (root / "build" / "skip.js").write_text("ignored", encoding="utf-8")
    (root / "huge.txt").write_text("x" * 20, encoding="utf-8")

    result = backup_module.backup(dry_run=True)

    assert result["file_count"] == 1
    assert result["skipped_count"] >= 2
    assert result["dry_run"] is True


def test_copy_project_files_dry_run_reports_counts_without_copy(tmp_path, monkeypatch) -> None:
    root, onedrive = _configure_paths(tmp_path, monkeypatch)
    monkeypatch.setattr(backup_module, "MAX_FILE_SIZE", 12)

    (root / "keep.py").write_text("print('ok')", encoding="utf-8")
    (root / "build").mkdir()
    (root / "build" / "skip.js").write_text("ignored", encoding="utf-8")
    (root / "huge.txt").write_text("x" * 20, encoding="utf-8")

    dest = onedrive / "VibeCodingBackup" / "backup_test"
    stats = backup_module._copy_project_files(dest, dry_run=True)

    assert stats["file_count"] == 1
    assert stats["skipped_count"] == 2
    assert stats["total_bytes"] == len("print('ok')")
    assert stats["errors"] == []
    assert not (dest / "keep.py").exists()


def test_copy_backup_source_reports_copy_error(tmp_path, monkeypatch) -> None:
    root, onedrive = _configure_paths(tmp_path, monkeypatch)
    src = root / "keep.py"
    src.write_text("print('ok')", encoding="utf-8")

    def fail_copy(*_args, **_kwargs):
        raise OSError("copy blocked")

    monkeypatch.setattr(backup_module.shutil, "copy2", fail_copy)

    copied_bytes, error = backup_module._copy_backup_source(
        src,
        onedrive / "VibeCodingBackup" / "backup_test" / "keep.py",
        Path("keep.py"),
        dry_run=False,
    )

    assert copied_bytes == 0
    assert error == "keep.py: copy blocked"


def test_backup_copies_files_and_saves_status(tmp_path, monkeypatch) -> None:
    root, onedrive = _configure_paths(tmp_path, monkeypatch)
    (root / "src").mkdir()
    (root / "src" / "main.py").write_text("print('hello')", encoding="utf-8")

    result = backup_module.backup(dry_run=False)
    status = backup_module.get_status()

    copied_file = Path(result["dest"]) / "src" / "main.py"
    assert copied_file.exists()
    assert status["configured"] is True
    assert status["total_backups"] == 1
    assert status["latest_backup"].startswith("backup_")
    assert Path(onedrive / "VibeCodingBackup").exists()


def test_cleanup_old_backups_keeps_recent_only(tmp_path, monkeypatch) -> None:
    _, onedrive = _configure_paths(tmp_path, monkeypatch)
    monkeypatch.setattr(backup_module, "MAX_BACKUPS", 2)

    for name in ["backup_20260321_1200", "backup_20260320_1200", "backup_20260319_1200"]:
        (onedrive / "VibeCodingBackup" / name).mkdir(parents=True)

    removed = backup_module._cleanup_old_backups()
    remaining = sorted(path.name for path in (onedrive / "VibeCodingBackup").glob("backup_*"))

    assert removed == 1
    assert remaining == ["backup_20260320_1200", "backup_20260321_1200"]


def test_get_status_reads_saved_json(tmp_path, monkeypatch) -> None:
    root, _ = _configure_paths(tmp_path, monkeypatch)
    backup_module._STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    backup_module._STATUS_FILE.write_text(
        json.dumps({"last_backup_at": "2026-03-21T12:00:00", "last_file_count": 3}),
        encoding="utf-8",
    )

    status = backup_module.get_status()

    assert status["configured"] is True
    assert status["last_file_count"] == 3
    assert status["total_backups"] == 0
