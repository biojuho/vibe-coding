"""
SQLite Multi-DB MCP Server
===========================
워크스페이스 SQLite 데이터베이스를 통합 접근하는 MCP 서버.

지원 DB:
  - workspace: 통합 워크스페이스 DB (api_usage, scheduler, content, finance,
               debug_history, result_tracker, debt_history, qaqc_history 테이블 포함)
  - btx_cost:  blind-to-x 전용 비용 추적 DB (별도 프로젝트)

마이그레이션 (2026-04-04):
  workspace.db 단일 파일로 통합 (기존 7개 → 1개).
  기존 별칭(api_usage, scheduler, content, finance, debug_history, result_tracker)은
  모두 workspace.db를 가리키며 하위 호환성을 유지합니다.

Usage:
    python server.py
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    FastMCP = None

# ─── 환경 설정 ────────────────────────────────────────────────────────────────

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(_PROJECT_ROOT / ".env")

# DB 레지스트리: 별칭 → 실제 경로
# 2026-04-04: 기존 7개 DB를 workspace.db 하나로 통합.
# 기존 별칭(api_usage~result_tracker)은 하위 호환성을 위해 유지하며 모두 workspace.db를 가리킴.
_WORKSPACE_DB = _PROJECT_ROOT / ".tmp" / "workspace.db"
_DB_REGISTRY: dict[str, Path] = {
    # 통합 워크스페이스 DB (단일 파일, 테이블로 도메인 분리)
    "workspace": _WORKSPACE_DB,
    # 하위 호환 별칭 — 기존 코드가 도메인별 이름을 사용해도 동일 파일로 라우팅
    "api_usage": _WORKSPACE_DB,
    "scheduler": _WORKSPACE_DB,
    "content": _WORKSPACE_DB,
    "finance": _WORKSPACE_DB,
    "debug_history": _WORKSPACE_DB,
    "result_tracker": _WORKSPACE_DB,
    # blind-to-x 전용 DB (별도 프로젝트 경계 유지)
    "btx_cost": _PROJECT_ROOT / "projects" / "blind-to-x" / ".tmp" / "btx_costs.db",
}


def _resolve_db(db_name: str) -> Path:
    """DB 별칭을 실제 경로로 변환합니다."""
    name = db_name.strip().lower()
    if name not in _DB_REGISTRY:
        available = ", ".join(sorted(_DB_REGISTRY.keys()))
        raise ValueError(f"알 수 없는 DB: '{db_name}'. 사용 가능: {available}")
    path = _DB_REGISTRY[name]
    if not path.exists():
        raise FileNotFoundError(f"DB 파일 없음: {path}")
    return path


def _validate_table_name(table_name: str) -> str:
    """테이블 이름을 검증하여 SQL Injection을 방지합니다. # [QA 수정]"""
    import re

    cleaned = table_name.strip()
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", cleaned):
        raise ValueError(f"유효하지 않은 테이블 이름: '{table_name}'")
    return cleaned


def _safe_query(db_name: str, query: str, params: tuple = ()) -> dict[str, Any]:
    """읽기 전용 SQL 쿼리를 실행합니다.

    보안을 위해 DDL/DML 문(CREATE, DROP, INSERT, UPDATE, DELETE, ALTER)을 차단합니다.
    """
    # 위험한 SQL 문 차단
    normalized = query.strip().upper()
    blocked_keywords = ["CREATE", "DROP", "INSERT", "UPDATE", "DELETE", "ALTER", "ATTACH", "DETACH"]
    first_word = normalized.split()[0] if normalized.split() else ""
    if first_word in blocked_keywords:
        return {
            "error": f"읽기 전용 모드입니다. '{first_word}' 문은 허용되지 않습니다.",
            "hint": "SELECT 문만 사용해 주세요.",
        }

    db_path = _resolve_db(db_name)
    conn = None
    try:
        conn = sqlite3.connect(str(db_path), timeout=5)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(query, params)
        rows = cursor.fetchall()

        # Row를 dict로 변환
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        results = [dict(zip(columns, row)) for row in rows]

        return {
            "db": db_name,
            "query": query,
            "row_count": len(results),
            "columns": columns,
            "results": results[:500],  # 최대 500행 반환
            "truncated": len(results) > 500,
            "retrieved_at": datetime.now().isoformat(),
        }
    except sqlite3.Error as e:
        return {"error": f"SQL 실행 오류: {e}", "db": db_name, "query": query}
    finally:
        if conn:
            conn.close()


# ─── 도구 함수 ────────────────────────────────────────────────────────────────


def _list_databases() -> dict[str, Any]:
    """사용 가능한 모든 DB와 그 상태를 나열합니다."""
    dbs = []
    for name, path in sorted(_DB_REGISTRY.items()):
        info: dict[str, Any] = {
            "name": name,
            "path": str(path),
            "exists": path.exists(),
        }
        if path.exists():
            info["size_kb"] = round(path.stat().st_size / 1024, 1)
            # 테이블 목록 조회
            try:
                conn = sqlite3.connect(str(path), timeout=3)
                cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
                info["tables"] = [row[0] for row in cursor.fetchall()]
                info["table_count"] = len(info["tables"])
                conn.close()
            except Exception as e:
                info["tables"] = []
                info["table_count"] = 0
                info["error"] = str(e)
        dbs.append(info)

    return {
        "databases": dbs,
        "total": len(dbs),
        "available": sum(1 for d in dbs if d["exists"]),
        "retrieved_at": datetime.now().isoformat(),
    }


def _get_table_schema(db_name: str, table_name: str) -> dict[str, Any]:
    """특정 테이블의 스키마(컬럼 정보)를 조회합니다."""
    db_path = _resolve_db(db_name)
    conn = None
    try:
        conn = sqlite3.connect(str(db_path), timeout=3)
        safe_name = _validate_table_name(table_name)  # [QA 수정] SQL Injection 방지
        cursor = conn.execute(f"PRAGMA table_info({safe_name})")  # noqa: S608 — validated by _validate_table_name
        columns = []
        for row in cursor.fetchall():
            columns.append(
                {
                    "cid": row[0],
                    "name": row[1],
                    "type": row[2],
                    "notnull": bool(row[3]),
                    "default_value": row[4],
                    "pk": bool(row[5]),
                }
            )

        if not columns:
            return {"error": f"테이블 '{table_name}'을 찾을 수 없습니다.", "db": db_name}

        # 행 수 조회
        count_cursor = conn.execute(f"SELECT COUNT(*) FROM {safe_name}")  # noqa: S608 — validated by _validate_table_name
        row_count = count_cursor.fetchone()[0]

        return {
            "db": db_name,
            "table": table_name,
            "columns": columns,
            "column_count": len(columns),
            "row_count": row_count,
        }
    except sqlite3.Error as e:
        return {"error": f"스키마 조회 오류: {e}", "db": db_name, "table": table_name}
    finally:
        if conn:
            conn.close()


def _quick_stats(db_name: str) -> dict[str, Any]:
    """DB의 빠른 통계 요약을 반환합니다."""
    db_path = _resolve_db(db_name)
    conn = None
    try:
        conn = sqlite3.connect(str(db_path), timeout=3)
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row[0] for row in cursor.fetchall()]

        stats = {
            "db": db_name,
            "size_kb": round(db_path.stat().st_size / 1024, 1),
            "tables": {},
        }

        for table in tables:
            try:
                safe_t = _validate_table_name(table)  # [QA 수정]
                count = conn.execute(f"SELECT COUNT(*) FROM {safe_t}").fetchone()[0]  # noqa: S608 — validated by _validate_table_name
                stats["tables"][table] = {"row_count": count}
            except sqlite3.Error:
                stats["tables"][table] = {"row_count": "error"}

        stats["table_count"] = len(tables)
        stats["retrieved_at"] = datetime.now().isoformat()
        return stats
    except sqlite3.Error as e:
        return {"error": f"통계 조회 오류: {e}", "db": db_name}
    finally:
        if conn:
            conn.close()


# ─── MCP 서버 등록 ────────────────────────────────────────────────────────────

if FastMCP is not None:
    mcp = FastMCP(
        "sqlite-multi",
        instructions=(
            "워크스페이스 SQLite 데이터베이스 통합 MCP 서버. "
            "workspace DB(api_usage·scheduler·content·finance·debug_history·result_tracker·debt_history·qaqc_history 테이블 통합)와 "
            "btx_cost DB(blind-to-x 전용)를 지원합니다. "
            "모든 쿼리는 읽기 전용(SELECT)입니다."
        ),
    )

    @mcp.tool()
    def list_databases() -> dict[str, Any]:
        """사용 가능한 모든 SQLite 데이터베이스 목록과 상태를 조회합니다."""
        return _list_databases()

    @mcp.tool()
    def query_database(db_name: str, sql: str) -> dict[str, Any]:
        """특정 DB에 읽기 전용 SQL 쿼리를 실행합니다.

        Args:
            db_name: DB 별칭 (api_usage, scheduler, content, finance,
                     debug_history, result_tracker, btx_cost)
            sql: 실행할 SELECT 쿼리
        """
        return _safe_query(db_name, sql)

    @mcp.tool()
    def get_table_schema(db_name: str, table_name: str) -> dict[str, Any]:
        """특정 테이블의 컬럼 정보와 행 수를 조회합니다.

        Args:
            db_name: DB 별칭
            table_name: 테이블 이름
        """
        return _get_table_schema(db_name, table_name)

    @mcp.tool()
    def quick_stats(db_name: str) -> dict[str, Any]:
        """DB의 빠른 통계 요약(테이블별 행 수, 파일 크기 등)을 반환합니다.

        Args:
            db_name: DB 별칭
        """
        return _quick_stats(db_name)
else:
    mcp = None
    list_databases = _list_databases
    query_database = _safe_query
    get_table_schema = _get_table_schema
    quick_stats = _quick_stats


if __name__ == "__main__":
    if mcp is None:
        print("mcp 패키지 미설치. pip install 'mcp[cli]' 후 다시 실행하세요.")
        import json

        print("\n=== DB 목록 ===")
        print(json.dumps(_list_databases(), indent=2, ensure_ascii=False))
    else:
        mcp.run()
