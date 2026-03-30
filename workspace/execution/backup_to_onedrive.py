"""프로젝트 핵심 파일을 OneDrive로 증분 백업.

venv, node_modules, __pycache__, .next, dist 등 재생성 가능한
파일은 제외하고, 코드 + 설정 + 스킬 + 지침만 백업합니다.

Usage:
    python workspace/execution/backup_to_onedrive.py             # 백업 실행
    python workspace/execution/backup_to_onedrive.py --dry-run   # 미리보기 (복사 안 함)
    python workspace/execution/backup_to_onedrive.py --status     # 백업 현황 확인
"""

from __future__ import annotations

import execution._logging  # noqa: F401 — loguru 중앙 설정 활성화

import argparse
import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Set

from dotenv import load_dotenv

load_dotenv()

from execution._logging import logger  # noqa: E402

# ── 설정 ──────────────────────────────────────────────
_ROOT = Path(__file__).resolve().parent.parent
_ONEDRIVE = Path(os.getenv("OneDrive", ""))
_BACKUP_ROOT = _ONEDRIVE / "VibeCodingBackup"
_STATUS_FILE = _ROOT / ".tmp" / "backup_status.json"

# 최대 보관 백업 수
MAX_BACKUPS = 7

# 건너뛸 디렉토리
SKIP_DIRS: Set[str] = {
    "venv",
    "node_modules",
    "__pycache__",
    ".next",
    ".tmp",
    "_archive",
    ".git",
    "dist",
    "build",
    ".turbo",
    ".vscode",
    ".idea",
    "out",
    ".cache",
    ".nuxt",
}

# 건너뛸 확장자
SKIP_EXTS: Set[str] = {
    ".pyc",
    ".pyo",
    ".db",
    ".sqlite3",
    ".lock",  # package-lock 등은 재생성 가능
    ".whl",
    ".egg-info",
}

# 파일 크기 제한 (10MB)
MAX_FILE_SIZE = 10 * 1024 * 1024


def _should_skip_dir(path: Path) -> bool:
    """지정된 디렉토리이면 건너뛰기."""
    return any(part in SKIP_DIRS for part in path.parts)


def _should_skip_file(path: Path) -> bool:
    """건너뛸 파일인지 확인."""
    if path.suffix.lower() in SKIP_EXTS:
        return True
    try:
        if path.stat().st_size > MAX_FILE_SIZE:
            return True
    except OSError:
        return True
    return False


def _snapshot_sqlite_dbs(dest: Path, *, dry_run: bool = False) -> list[dict]:
    """프로젝트 내 SQLite DB를 VACUUM INTO로 안전하게 스냅샷합니다.

    live DB 파일을 직접 복사하는 대신, VACUUM INTO로 일관된 스냅샷을 생성합니다.
    이는 WAL 모드 DB에서 -wal/-shm 파일과의 시점 불일치를 방지합니다.
    """
    import sqlite3

    results = []
    db_patterns = ["**/*.db", "**/*.sqlite3"]
    skip_dirs = SKIP_DIRS | {"venv", "node_modules"}

    for pattern in db_patterns:
        for db_path in _ROOT.glob(pattern):
            try:
                rel = db_path.relative_to(_ROOT)
            except ValueError:
                continue
            if any(part in skip_dirs for part in rel.parts):
                continue

            entry = {"source": str(rel), "ok": False, "detail": ""}
            if dry_run:
                entry["detail"] = "dry-run"
                entry["ok"] = True
                results.append(entry)
                continue

            snapshot_path = dest / rel
            try:
                snapshot_path.parent.mkdir(parents=True, exist_ok=True)
                conn = sqlite3.connect(str(db_path))
                conn.execute(f"VACUUM INTO '{snapshot_path}'")
                conn.close()
                entry["ok"] = True
                entry["size_mb"] = round(snapshot_path.stat().st_size / (1024 * 1024), 2)
                entry["detail"] = "VACUUM INTO success"
            except Exception as exc:
                entry["detail"] = str(exc)[:200]
                # VACUUM INTO 실패 시 일반 복사로 fallback
                try:
                    shutil.copy2(db_path, snapshot_path)
                    entry["ok"] = True
                    entry["detail"] = f"fallback copy (VACUUM failed: {str(exc)[:60]})"
                except Exception as copy_exc:
                    entry["detail"] = f"both failed: {exc}, {copy_exc}"

            results.append(entry)

    return results


def backup(dry_run: bool = False) -> dict:
    """핵심 파일을 OneDrive로 백업.

    Returns:
        dict with keys: timestamp, dest, file_count, skipped_count, total_bytes, errors
    """
    if not _ONEDRIVE.exists():
        raise RuntimeError(f"OneDrive 경로를 찾을 수 없습니다: {_ONEDRIVE}\n환경변수 OneDrive를 확인하세요.")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    dest = _BACKUP_ROOT / f"backup_{timestamp}"

    file_count = 0
    skipped_count = 0
    total_bytes = 0
    errors: list[str] = []

    for src_file in _ROOT.rglob("*"):
        # 디렉토리는 건너뛰기
        if src_file.is_dir():
            continue

        # 제외 대상 확인
        try:
            rel = src_file.relative_to(_ROOT)
        except ValueError:
            continue

        if _should_skip_dir(rel):
            skipped_count += 1
            continue

        if _should_skip_file(src_file):
            skipped_count += 1
            continue

        dst = dest / rel

        if dry_run:
            logger.info("[DRY-RUN] %s → %s", rel, dst)
            file_count += 1
            total_bytes += src_file.stat().st_size
            continue

        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_file, dst)
            file_count += 1
            total_bytes += src_file.stat().st_size
        except Exception as exc:
            errors.append(f"{rel}: {exc}")
            logger.warning("Failed to copy %s: %s", rel, exc)

    # SQLite DB 안전 스냅샷 (VACUUM INTO)
    db_snapshots = _snapshot_sqlite_dbs(dest, dry_run=dry_run)

    # 오래된 백업 삭제 (최근 N개만 유지)
    if not dry_run:
        _cleanup_old_backups()

    result = {
        "timestamp": timestamp,
        "dest": str(dest),
        "file_count": file_count,
        "skipped_count": skipped_count,
        "total_bytes": total_bytes,
        "total_mb": round(total_bytes / (1024 * 1024), 1),
        "db_snapshots": db_snapshots,
        "errors": errors,
        "dry_run": dry_run,
    }

    # 상태 파일 저장
    if not dry_run:
        _save_status(result)

    return result


def _cleanup_old_backups() -> int:
    """오래된 백업 삭제 (최근 MAX_BACKUPS 개만 유지)."""
    if not _BACKUP_ROOT.exists():
        return 0

    backups = sorted(_BACKUP_ROOT.glob("backup_*"), reverse=True)
    removed = 0

    for old_backup in backups[MAX_BACKUPS:]:
        try:
            shutil.rmtree(old_backup, ignore_errors=True)
            removed += 1
            logger.info("Removed old backup: %s", old_backup.name)
        except Exception as exc:
            logger.warning("Failed to remove %s: %s", old_backup.name, exc)

    return removed


def _save_status(result: dict) -> None:
    """마지막 백업 상태 저장."""
    try:
        _STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
        status = {
            "last_backup_at": datetime.now().isoformat(timespec="seconds"),
            "last_backup_dir": result["dest"],
            "last_file_count": result["file_count"],
            "last_total_mb": result["total_mb"],
            "last_errors": result["errors"][:5],
        }
        _STATUS_FILE.write_text(
            json.dumps(status, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception as exc:
        logger.warning("Failed to save backup status: %s", exc)


def get_status() -> dict:
    """백업 현황 조회."""
    status = {"configured": _ONEDRIVE.exists(), "onedrive_path": str(_ONEDRIVE)}

    if _STATUS_FILE.exists():
        try:
            status.update(json.loads(_STATUS_FILE.read_text(encoding="utf-8")))
        except Exception:
            pass

    if _BACKUP_ROOT.exists():
        backups = sorted(_BACKUP_ROOT.glob("backup_*"), reverse=True)
        status["total_backups"] = len(backups)
        if backups:
            status["latest_backup"] = backups[0].name
            # 전체 백업 크기 계산
            total_size = sum(f.stat().st_size for b in backups for f in b.rglob("*") if f.is_file())
            status["total_backup_size_mb"] = round(total_size / (1024 * 1024), 1)
    else:
        status["total_backups"] = 0

    return status


# ── CLI ──────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="OneDrive Backup — 프로젝트 핵심 파일 백업")
    parser.add_argument("--dry-run", action="store_true", help="실제 복사 없이 미리보기")
    parser.add_argument("--status", action="store_true", help="백업 현황 조회")
    args = parser.parse_args()

    if args.status:
        status = get_status()
        print(json.dumps(status, indent=2, ensure_ascii=False))
    else:
        print(f"\n{'═' * 50}")
        print("  💾 OneDrive Backup")
        print(f"  Source: {_ROOT}")
        print(f"  Dest:   {_BACKUP_ROOT}")
        if args.dry_run:
            print("  Mode:   🔍 DRY RUN (no files will be copied)")
        print(f"{'═' * 50}\n")

        result = backup(dry_run=args.dry_run)

        print(f"\n{'─' * 50}")
        print(f"  Files copied:  {result['file_count']}")
        print(f"  Files skipped: {result['skipped_count']}")
        print(f"  Total size:    {result['total_mb']} MB")
        if result["errors"]:
            print(f"  Errors:        {len(result['errors'])}")
            for err in result["errors"][:5]:
                print(f"    ⚠️ {err}")
        action = "previewed" if args.dry_run else "backed up"
        print(f"\n  ✅ Successfully {action} to:")
        print(f"     {result['dest']}")
        print(f"{'═' * 50}\n")
