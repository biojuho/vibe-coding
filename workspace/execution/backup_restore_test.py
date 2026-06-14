"""Run a lightweight OneDrive backup restore smoke test.

The check finds the latest ``VibeCodingBackup/backup_*`` directory under
OneDrive, validates up to five SQLite databases, and verifies critical files.
It is safe to run from Task Scheduler or directly from the command line.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

load_dotenv()

from execution._logging import logger  # noqa: E402

DB_PATTERNS = ("**/*.db", "**/*.sqlite", "**/*.sqlite3")
MAX_DB_CHECKS = 5
CRITICAL_FILES = (
    ".ai/CONTEXT.md",
    ".ai/DECISIONS.md",
    "CLAUDE.md",
    "pytest.ini",
)


def _find_latest_backup() -> Path | None:
    """Return the latest OneDrive backup directory, if configured."""
    onedrive = os.getenv("OneDrive", "")
    if not onedrive:
        return None

    backup_dir = Path(onedrive) / "VibeCodingBackup"
    if not backup_dir.exists():
        return None

    backups = sorted(backup_dir.glob("backup_*"), reverse=True)
    return backups[0] if backups else None


def _check_sqlite_integrity(db_path: Path) -> dict:
    """Run SQLite ``PRAGMA integrity_check`` for one database file."""
    result = {"path": str(db_path), "exists": db_path.exists(), "ok": False, "detail": ""}

    if not db_path.exists():
        result["detail"] = "file missing"
        return result

    try:
        with sqlite3.connect(str(db_path)) as conn:
            check_result = conn.execute("PRAGMA integrity_check").fetchone()[0]

        result["ok"] = check_result == "ok"
        result["detail"] = check_result
        result["size_mb"] = round(db_path.stat().st_size / (1024 * 1024), 2)
    except Exception as exc:
        result["detail"] = str(exc)[:200]

    return result


def _check_file_exists(backup_dir: Path, relative_path: str) -> dict:
    """Return existence and size metadata for one backed-up file path."""
    full_path = backup_dir / relative_path
    exists = full_path.exists()
    size = full_path.stat().st_size if exists else 0

    return {
        "path": relative_path,
        "exists": exists,
        "size_bytes": size,
    }


def _initial_restore_report() -> dict:
    return {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "overall": "UNKNOWN",
        "backup_found": False,
        "backup_path": None,
        "db_checks": [],
        "file_checks": [],
        "errors": [],
    }


def _backup_database_files(backup: Path) -> list[Path]:
    db_files: list[Path] = []
    for pattern in DB_PATTERNS:
        db_files.extend(backup.glob(pattern))
    return sorted(db_files)


def _database_restore_check(backup: Path, db_path: Path, *, dry_run: bool) -> dict:
    if dry_run:
        return {"path": str(db_path.relative_to(backup)), "dry_run": True}

    restore_dir = _ROOT / ".tmp" / "restore_test"
    restore_dir.mkdir(parents=True, exist_ok=True)
    temp_db = restore_dir / db_path.name
    try:
        shutil.copy2(db_path, temp_db)
        check = _check_sqlite_integrity(temp_db)
        check["path"] = str(db_path.relative_to(backup))
        return check
    finally:
        if temp_db.exists():
            temp_db.unlink()


def _database_restore_checks(backup: Path, *, dry_run: bool) -> list[dict]:
    return [
        _database_restore_check(backup, db_path, dry_run=dry_run)
        for db_path in _backup_database_files(backup)[:MAX_DB_CHECKS]
    ]


def _critical_file_checks(backup: Path) -> list[dict]:
    return [_check_file_exists(backup, rel_path) for rel_path in CRITICAL_FILES]


def _restore_overall(report: dict) -> str:
    db_ok = all(c.get("ok", False) or c.get("dry_run", False) for c in report["db_checks"])
    files_ok = all(c["exists"] for c in report["file_checks"])

    if db_ok and files_ok and not report["errors"]:
        return "PASS"
    if report["errors"]:
        return "FAIL"
    return "WARN"


def _cleanup_restore_dir() -> None:
    restore_dir = _ROOT / ".tmp" / "restore_test"
    if restore_dir.exists():
        shutil.rmtree(restore_dir, ignore_errors=True)


def run_restore_test(*, dry_run: bool = False) -> dict:
    """Run the backup restore smoke test."""
    report = _initial_restore_report()

    backup = _find_latest_backup()
    if not backup:
        report["overall"] = "FAIL"
        report["errors"].append("OneDrive backup directory was not found")
        return report

    report["backup_found"] = True
    report["backup_path"] = str(backup)
    backup_age_days = (datetime.now() - datetime.fromtimestamp(backup.stat().st_mtime)).days
    report["backup_age_days"] = backup_age_days

    if backup_age_days > 7:
        report["errors"].append(f"Backup is {backup_age_days} days old; refresh required")

    report["db_checks"] = _database_restore_checks(backup, dry_run=dry_run)
    report["file_checks"] = _critical_file_checks(backup)
    report["overall"] = _restore_overall(report)
    _cleanup_restore_dir()

    return report


def _send_telegram(report: dict) -> None:
    """Send the restore-test result through the configured Telegram notifier."""
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "telegram_notifier",
            _ROOT / "execution" / "telegram_notifier.py",
        )
        if spec is None or spec.loader is None:
            return
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        if not mod.is_configured():
            return

        icons = {"PASS": "[PASS]", "WARN": "[WARN]", "FAIL": "[FAIL]"}
        icon = icons.get(report["overall"], "[UNKNOWN]")
        db_summary = f"{sum(1 for c in report['db_checks'] if c.get('ok'))}/{len(report['db_checks'])} DB OK"
        file_summary = f"{sum(1 for c in report['file_checks'] if c['exists'])}/{len(report['file_checks'])} files"

        msg = (
            f"Backup Restore Test ({report['timestamp'][:10]})\n"
            f"{icon} {report['overall']} - {db_summary}, {file_summary}\n"
            f"Backup: {report.get('backup_age_days', '?')}d old"
        )
        if report["errors"]:
            msg += "\nWARN " + "; ".join(report["errors"])

        level = "INFO" if report["overall"] == "PASS" else "WARNING"
        mod.send_alert(msg, level=level)
    except Exception as exc:
        logger.warning("Telegram send failed: %s", exc)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="OneDrive backup restore smoke test")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-notify", action="store_true")
    return parser.parse_args()


def _print_text_report(report: dict) -> None:
    print(f"\n{'=' * 50}")
    print(f"  Backup Restore Test - {report['overall']}")
    print(f"  {report['timestamp']}")
    print(f"{'=' * 50}")
    if report["backup_path"]:
        print(f"  Backup: {report['backup_path']} ({report.get('backup_age_days', '?')}d old)")
    for check in report["db_checks"]:
        ok = "OK" if check.get("ok") else "FAIL"
        print(f"  {ok} DB: {check['path']} - {check.get('detail', 'N/A')}")
    for check in report["file_checks"]:
        ok = "OK" if check["exists"] else "MISSING"
        print(f"  {ok} File: {check['path']}")
    if report["errors"]:
        for err in report["errors"]:
            print(f"  WARN {err}")
    print(f"{'=' * 50}\n")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    args = _parse_args()
    report = run_restore_test(dry_run=args.dry_run)

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        _print_text_report(report)

    if not args.no_notify:
        _send_telegram(report)
