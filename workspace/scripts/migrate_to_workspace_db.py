"""
workspace.db 단일 파일 마이그레이션 스크립트
=============================================
기존 분산된 7개 SQLite DB를 workspace.db 하나로 통합합니다.

사용법:
    python workspace/scripts/migrate_to_workspace_db.py

동작:
    1. 기존 DB 파일들을 ATTACH해서 모든 테이블 데이터를 workspace.db로 복사
    2. 성공 후 기존 파일을 .bak으로 이름 변경 (삭제하지 않음)
    3. 이미 workspace.db가 존재하면 기존 데이터 보존 (중복 INSERT는 IGNORE)

안전 원칙:
    - 원본 파일은 삭제하지 않고 .bak 접미사로 보존
    - workspace.db가 없으면 새로 생성, 있으면 추가 병합
    - 각 단계 실패 시 해당 DB 건너뛰고 계속 진행 (롤백 없음)
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

_WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
_TMP = _WORKSPACE_ROOT / ".tmp"
_TARGET = _TMP / "workspace.db"

# 마이그레이션 대상: (별칭, 기존 파일명)
_SOURCES = [
    ("api_usage", "api_usage.db"),
    ("scheduler", "scheduler.db"),
    ("content", "content.db"),
    ("finance", "finance.db"),
    ("debug_history", "debug_history.db"),
    ("result_tracker", "result_tracker.db"),
    ("debt_history", "debt_history.db"),
    ("qaqc_history", "qaqc_history.db"),
]


def _quote_identifier(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def _get_tables(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall()
    return [r[0] for r in rows]


def _get_create_ddl(conn: sqlite3.Connection, table: str) -> str:
    row = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()
    return row[0] if row else ""


def migrate_db(alias: str, src_path: Path, target_conn: sqlite3.Connection) -> bool:
    if not src_path.exists():
        print(f"  [{alias}] 파일 없음: {src_path.name} (건너뜀)")
        return True

    print(f"  [{alias}] {src_path.name} → workspace.db 마이그레이션 중...")
    try:
        src_conn = sqlite3.connect(str(src_path))
        src_conn.row_factory = sqlite3.Row
        tables = _get_tables(src_conn)

        if not tables:
            print(f"  [{alias}] 테이블 없음, 건너뜀")
            src_conn.close()
            return True

        for table in tables:
            # workspace.db에 테이블이 없으면 생성
            ddl = _get_create_ddl(src_conn, table)
            if ddl:
                try:
                    target_conn.execute(ddl)
                except sqlite3.OperationalError:
                    pass  # 이미 존재 (CREATE TABLE IF NOT EXISTS 아닌 경우 대비)

            # 데이터 복사 (중복 키는 IGNORE)
            quoted_table = _quote_identifier(table)
            select_all_sql = "SELECT * FROM " + quoted_table
            select_cols_sql = select_all_sql + " LIMIT 0"
            rows = src_conn.execute(select_all_sql).fetchall()
            if not rows:
                print(f"    {table}: 행 없음")
                continue

            cols = [desc[0] for desc in src_conn.execute(select_cols_sql).description]
            placeholders = ", ".join("?" * len(cols))
            col_list = ", ".join(_quote_identifier(c) for c in cols)
            insert_sql = "INSERT OR IGNORE INTO " + quoted_table + " (" + col_list + ") VALUES (" + placeholders + ")"

            target_conn.executemany(insert_sql, [tuple(r) for r in rows])
            target_conn.commit()
            print(f"    {table}: {len(rows)}행 복사 완료")

        src_conn.close()
        return True

    except Exception as exc:
        print(f"  [{alias}] 오류 (건너뜀): {exc}")
        return False


def backup_source(src_path: Path) -> None:
    bak_path = src_path.with_suffix(".db.bak")
    try:
        src_path.rename(bak_path)
        print(f"  백업: {src_path.name} → {bak_path.name}")
    except Exception as exc:
        print(f"  백업 실패 ({src_path.name}): {exc}")


def main() -> int:
    _TMP.mkdir(parents=True, exist_ok=True)

    print("\n=== workspace.db 마이그레이션 시작 ===")
    print(f"대상: {_TARGET}\n")

    # WAL 모드로 target 열기
    target_conn = sqlite3.connect(str(_TARGET))
    target_conn.execute("PRAGMA journal_mode=WAL")
    target_conn.execute("PRAGMA synchronous=NORMAL")

    failed: list[str] = []
    migrated: list[str] = []

    for alias, filename in _SOURCES:
        src_path = _TMP / filename
        ok = migrate_db(alias, src_path, target_conn)
        if ok and src_path.exists():
            backup_source(src_path)
            migrated.append(alias)
        elif not ok:
            failed.append(alias)

    target_conn.close()

    print("\n=== 완료 ===")
    print(f"성공: {len(migrated)}개 ({', '.join(migrated) or '없음'})")
    if failed:
        print(f"실패: {len(failed)}개 ({', '.join(failed)}) — 원본 파일 유지됨")
        return 1

    workspace_size = _TARGET.stat().st_size / 1024 if _TARGET.exists() else 0
    print(f"workspace.db 크기: {workspace_size:.1f} KB")
    print("\n원본 파일은 .bak으로 보존됩니다. 정상 동작 확인 후 수동으로 삭제하세요.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
