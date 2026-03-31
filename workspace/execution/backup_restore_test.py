"""OneDrive 백업 복원 테스트 — 월 1회 자동 실행.

백업된 SQLite DB의 무결성을 검증하고, 핵심 파일 존재를 확인합니다.
Task Scheduler에 등록하여 월 1회 실행하세요.

Usage:
    python workspace/execution/backup_restore_test.py           # 전체 검증 + Telegram 알림
    python workspace/execution/backup_restore_test.py --json    # JSON 출력만
    python workspace/execution/backup_restore_test.py --dry-run # 실제 복사 없이 경로만 확인
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

load_dotenv()

from execution._logging import logger  # noqa: E402

_ROOT = Path(__file__).resolve().parent.parent


def _find_latest_backup() -> Path | None:
    """최신 OneDrive 백업 폴더를 찾습니다."""
    onedrive = os.getenv("OneDrive", "")
    if not onedrive:
        return None

    backup_dir = Path(onedrive) / "VibeCodingBackup"
    if not backup_dir.exists():
        return None

    backups = sorted(backup_dir.glob("backup_*"), reverse=True)
    return backups[0] if backups else None


def _check_sqlite_integrity(db_path: Path) -> dict:
    """SQLite DB의 integrity_check를 실행합니다."""
    result = {"path": str(db_path), "exists": db_path.exists(), "ok": False, "detail": ""}

    if not db_path.exists():
        result["detail"] = "파일 없음"
        return result

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.execute("PRAGMA integrity_check")
        check_result = cursor.fetchone()[0]
        conn.close()

        result["ok"] = check_result == "ok"
        result["detail"] = check_result
        result["size_mb"] = round(db_path.stat().st_size / (1024 * 1024), 2)
    except Exception as exc:
        result["detail"] = str(exc)[:200]

    return result


def _check_file_exists(backup_dir: Path, relative_path: str) -> dict:
    """백업 내 특정 파일의 존재를 확인합니다."""
    full_path = backup_dir / relative_path
    exists = full_path.exists()
    size = full_path.stat().st_size if exists else 0

    return {
        "path": relative_path,
        "exists": exists,
        "size_bytes": size,
    }


def run_restore_test(*, dry_run: bool = False) -> dict:
    """복원 테스트를 실행합니다."""
    report = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "overall": "UNKNOWN",
        "backup_found": False,
        "backup_path": None,
        "db_checks": [],
        "file_checks": [],
        "errors": [],
    }

    # 1. 최신 백업 찾기
    backup = _find_latest_backup()
    if not backup:
        report["overall"] = "FAIL"
        report["errors"].append("OneDrive 백업 폴더를 찾을 수 없습니다")
        return report

    report["backup_found"] = True
    report["backup_path"] = str(backup)
    backup_age_days = (datetime.now() - datetime.fromtimestamp(backup.stat().st_mtime)).days
    report["backup_age_days"] = backup_age_days

    if backup_age_days > 7:
        report["errors"].append(f"백업이 {backup_age_days}일 전 — 갱신 필요")

    # 2. SQLite DB 무결성 검증
    db_patterns = [
        "**/*.db",
        "**/*.sqlite",
        "**/*.sqlite3",
    ]
    db_files = []
    for pattern in db_patterns:
        db_files.extend(backup.glob(pattern))

    # 최대 5개 DB만 검증 (시간 절약)
    for db_path in sorted(db_files)[:5]:
        if dry_run:
            report["db_checks"].append({"path": str(db_path.relative_to(backup)), "dry_run": True})
        else:
            # 임시 폴더에 복사 후 검증 (원본 보호)
            restore_dir = _ROOT / ".tmp" / "restore_test"
            restore_dir.mkdir(parents=True, exist_ok=True)
            temp_db = restore_dir / db_path.name
            try:
                shutil.copy2(db_path, temp_db)
                check = _check_sqlite_integrity(temp_db)
                check["path"] = str(db_path.relative_to(backup))
                report["db_checks"].append(check)
            finally:
                if temp_db.exists():
                    temp_db.unlink()

    # 3. 핵심 파일 존재 확인
    critical_files = [
        ".ai/CONTEXT.md",
        ".ai/DECISIONS.md",
        "CLAUDE.md",
        "pytest.ini",
    ]
    for rel_path in critical_files:
        report["file_checks"].append(_check_file_exists(backup, rel_path))

    # 4. 종합 판정
    db_ok = all(c.get("ok", False) or c.get("dry_run", False) for c in report["db_checks"])
    files_ok = all(c["exists"] for c in report["file_checks"])

    if db_ok and files_ok and not report["errors"]:
        report["overall"] = "PASS"
    elif report["errors"]:
        report["overall"] = "FAIL"
    else:
        report["overall"] = "WARN"

    # 임시 폴더 정리
    restore_dir = _ROOT / ".tmp" / "restore_test"
    if restore_dir.exists():
        shutil.rmtree(restore_dir, ignore_errors=True)

    return report


def _send_telegram(report: dict) -> None:
    """결과를 Telegram으로 전송합니다."""
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

        icons = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌"}
        icon = icons.get(report["overall"], "❓")
        db_summary = f"{sum(1 for c in report['db_checks'] if c.get('ok'))}/{len(report['db_checks'])} DB OK"
        file_summary = f"{sum(1 for c in report['file_checks'] if c['exists'])}/{len(report['file_checks'])} files"

        msg = (
            f"🗄️ Backup Restore Test ({report['timestamp'][:10]})\n"
            f"{icon} {report['overall']} — {db_summary}, {file_summary}\n"
            f"Backup: {report.get('backup_age_days', '?')}d old"
        )
        if report["errors"]:
            msg += "\n⚠️ " + "; ".join(report["errors"])

        level = "INFO" if report["overall"] == "PASS" else "WARNING"
        mod.send_alert(msg, level=level)
    except Exception as exc:
        logger.warning("Telegram 전송 실패: %s", exc)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="OneDrive 백업 복원 테스트")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-notify", action="store_true")
    args = parser.parse_args()

    report = run_restore_test(dry_run=args.dry_run)

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"\n{'=' * 50}")
        print(f"  Backup Restore Test — {report['overall']}")
        print(f"  {report['timestamp']}")
        print(f"{'=' * 50}")
        if report["backup_path"]:
            print(f"  Backup: {report['backup_path']} ({report.get('backup_age_days', '?')}d old)")
        for check in report["db_checks"]:
            ok = "✅" if check.get("ok") else "❌"
            print(f"  {ok} DB: {check['path']} — {check.get('detail', 'N/A')}")
        for check in report["file_checks"]:
            ok = "✅" if check["exists"] else "❌"
            print(f"  {ok} File: {check['path']}")
        if report["errors"]:
            for err in report["errors"]:
                print(f"  ⚠️ {err}")
        print(f"{'=' * 50}\n")

    if not args.no_notify:
        _send_telegram(report)
