"""
디버깅 히스토리 DB - 에러 패턴 → 해결책 매핑.
디버깅 프로세스 Step 5(피드백 루프) 자동화.

Usage (CLI):
    python workspace/execution/debug_history_db.py add --severity P1 --module youtube_uploader \\
        --symptom "업로드 무한 루프" --cause "재시도 제한 없음" --solution "MAX_RETRIES 추가"
    python workspace/execution/debug_history_db.py list [--severity P1] [--module xxx]
    python workspace/execution/debug_history_db.py search "무한 루프"
    python workspace/execution/debug_history_db.py stats

Usage (library):
    from execution.debug_history_db import add_entry, search_entries, get_stats
"""

import argparse
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

DB_PATH = Path(__file__).resolve().parent.parent / ".tmp" / "workspace.db"

VALID_SEVERITIES = {"P0", "P1", "P2", "P3"}
VALID_LAYERS = {"directive", "orchestration", "execution"}


def _conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """디버깅 히스토리 테이블 생성."""
    conn = _conn()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS debug_entries (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at        TEXT NOT NULL,
                severity          TEXT NOT NULL DEFAULT 'P2',
                layer             TEXT NOT NULL DEFAULT 'execution',
                module            TEXT NOT NULL DEFAULT '',
                symptom           TEXT NOT NULL,
                root_cause        TEXT NOT NULL DEFAULT '',
                solution          TEXT NOT NULL DEFAULT '',
                directive_updated INTEGER NOT NULL DEFAULT 0,
                test_added        INTEGER NOT NULL DEFAULT 0,
                commit_hash       TEXT DEFAULT '',
                tags              TEXT DEFAULT '',
                notes             TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS scrape_quality_log (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                logged_at   TEXT NOT NULL,
                source      TEXT NOT NULL DEFAULT '',
                url         TEXT NOT NULL DEFAULT '',
                quality_score REAL NOT NULL DEFAULT 0.0,
                issues      TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS error_patterns (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern           TEXT NOT NULL UNIQUE,
                error_type        TEXT NOT NULL DEFAULT '',
                first_check       TEXT NOT NULL DEFAULT '',
                tool              TEXT NOT NULL DEFAULT '',
                module_hint       TEXT DEFAULT '',
                times_seen        INTEGER NOT NULL DEFAULT 1,
                last_seen_at      TEXT DEFAULT ''
            );
        """)
        conn.commit()
    finally:
        conn.close()


# ── CRUD 함수 ──────────────────────────────────────────────


def add_entry(
    symptom: str,
    severity: str = "P2",
    layer: str = "execution",
    module: str = "",
    root_cause: str = "",
    solution: str = "",
    directive_updated: bool = False,
    test_added: bool = False,
    commit_hash: str = "",
    tags: str = "",
    notes: str = "",
) -> int:
    """디버깅 이력 추가. 생성된 ID 반환."""
    init_db()
    conn = _conn()
    try:
        cursor = conn.execute(
            """INSERT INTO debug_entries
               (created_at, severity, layer, module, symptom, root_cause,
                solution, directive_updated, test_added, commit_hash, tags, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                datetime.now().isoformat(timespec="seconds"),
                severity.upper(),
                layer.lower(),
                module,
                symptom,
                root_cause,
                solution,
                int(directive_updated),
                int(test_added),
                commit_hash,
                tags,
                notes,
            ),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def auto_log_error(
    exc: Exception,
    module: str,
    context: str = "",
    severity: str = "P2",
) -> Optional[int]:
    """파이프라인 예외를 debug_history_db에 자동 기록.

    같은 module + 에러 타입이 최근 24시간 이내에 이미 기록된 경우 중복 저장 안 함.
    반환: 생성된 entry ID 또는 None (중복/실패)
    """
    try:
        init_db()
        exc_type = type(exc).__name__
        symptom = f"[auto] {exc_type}: {str(exc)[:200]}"
        if context:
            symptom = f"[auto][{context}] {exc_type}: {str(exc)[:180]}"

        # 24시간 내 동일 모듈+에러 타입 중복 확인
        conn = _conn()
        try:
            from datetime import timedelta

            since = (datetime.now() - timedelta(hours=24)).isoformat(timespec="seconds")
            row = conn.execute(
                "SELECT id FROM debug_entries WHERE module=? AND symptom LIKE ? AND created_at>?",
                (module, f"%{exc_type}%", since),
            ).fetchone()
            if row:
                return None  # 중복 억제
        finally:
            conn.close()

        return add_entry(
            symptom=symptom,
            severity=severity,
            layer="execution",
            module=module,
            tags="auto_captured",
        )
    except Exception:
        return None


def list_entries(
    severity: Optional[str] = None,
    layer: Optional[str] = None,
    module: Optional[str] = None,
    limit: int = 50,
) -> List[Dict]:
    """디버깅 이력 목록 조회."""
    init_db()
    conn = _conn()
    try:
        query = "SELECT * FROM debug_entries WHERE 1=1"
        params: list = []
        if severity:
            query += " AND severity = ?"
            params.append(severity.upper())
        if layer:
            query += " AND layer = ?"
            params.append(layer.lower())
        if module:
            query += " AND module LIKE ?"
            params.append(f"%{module}%")
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def search_entries(keyword: str, limit: int = 20) -> List[Dict]:
    """증상/원인/해결책에서 키워드 검색."""
    init_db()
    conn = _conn()
    try:
        rows = conn.execute(
            """SELECT * FROM debug_entries
               WHERE symptom LIKE ? OR root_cause LIKE ? OR solution LIKE ? OR tags LIKE ?
               ORDER BY created_at DESC LIMIT ?""",
            (f"%{keyword}%",) * 4 + (limit,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_stats() -> Dict:
    """디버깅 이력 통계."""
    init_db()
    conn = _conn()
    try:
        total = conn.execute("SELECT COUNT(*) FROM debug_entries").fetchone()[0]
        by_severity = {}
        for row in conn.execute(
            "SELECT severity, COUNT(*) as cnt FROM debug_entries GROUP BY severity ORDER BY severity"
        ).fetchall():
            by_severity[row["severity"]] = row["cnt"]

        by_layer = {}
        for row in conn.execute(
            "SELECT layer, COUNT(*) as cnt FROM debug_entries GROUP BY layer ORDER BY layer"
        ).fetchall():
            by_layer[row["layer"]] = row["cnt"]

        by_module = {}
        for row in conn.execute(
            "SELECT module, COUNT(*) as cnt FROM debug_entries WHERE module != '' GROUP BY module ORDER BY cnt DESC LIMIT 10"  # noqa: E501
        ).fetchall():
            by_module[row["module"]] = row["cnt"]

        directive_rate = 0.0
        test_rate = 0.0
        if total > 0:
            d_count = conn.execute("SELECT COUNT(*) FROM debug_entries WHERE directive_updated = 1").fetchone()[0]
            t_count = conn.execute("SELECT COUNT(*) FROM debug_entries WHERE test_added = 1").fetchone()[0]
            directive_rate = round(d_count / total * 100, 1)
            test_rate = round(t_count / total * 100, 1)

        return {
            "total_entries": total,
            "by_severity": by_severity,
            "by_layer": by_layer,
            "top_modules": by_module,
            "directive_update_rate": directive_rate,
            "test_addition_rate": test_rate,
        }
    finally:
        conn.close()


# ── TTL / 자동 아카이브 ────────────────────────────────────


def archive_old_entries(retention_days: int = 90) -> int:
    """지정 기간 이전의 debug_entries를 삭제하고 VACUUM. 삭제 건수 반환."""
    init_db()
    conn = _conn()
    try:
        from datetime import timedelta

        cutoff = (datetime.now() - timedelta(days=retention_days)).isoformat(timespec="seconds")
        cursor = conn.execute("DELETE FROM debug_entries WHERE created_at < ?", (cutoff,))
        deleted = cursor.rowcount

        # scrape_quality_log도 같은 기간 정리
        conn.execute("DELETE FROM scrape_quality_log WHERE logged_at < ?", (cutoff,))

        conn.commit()
        if deleted > 0:
            conn.execute("VACUUM")
        return deleted
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ── 에러 패턴 등록/조회 ───────────────────────────────────


def register_pattern(
    pattern: str,
    error_type: str = "",
    first_check: str = "",
    tool: str = "",
    module_hint: str = "",
) -> None:
    """에러 패턴 등록 (중복 시 times_seen 증가)."""
    init_db()
    conn = _conn()
    try:
        existing = conn.execute("SELECT id, times_seen FROM error_patterns WHERE pattern = ?", (pattern,)).fetchone()
        if existing:
            conn.execute(
                "UPDATE error_patterns SET times_seen = ?, last_seen_at = ? WHERE id = ?",
                (existing["times_seen"] + 1, datetime.now().isoformat(timespec="seconds"), existing["id"]),
            )
        else:
            conn.execute(
                """INSERT INTO error_patterns (pattern, error_type, first_check, tool, module_hint, last_seen_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (pattern, error_type, first_check, tool, module_hint, datetime.now().isoformat(timespec="seconds")),
            )
        conn.commit()
    finally:
        conn.close()


def lookup_pattern(error_message: str) -> List[Dict]:
    """에러 메시지로 알려진 패턴 검색."""
    init_db()
    conn = _conn()
    try:
        rows = conn.execute(
            "SELECT * FROM error_patterns WHERE ? LIKE '%' || pattern || '%' ORDER BY times_seen DESC",
            (error_message,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def list_patterns() -> List[Dict]:
    """등록된 모든 에러 패턴 조회."""
    init_db()
    conn = _conn()
    try:
        rows = conn.execute("SELECT * FROM error_patterns ORDER BY times_seen DESC").fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


# ── 초기 에러 패턴 시드 데이터 ─────────────────────────────


def seed_known_patterns() -> int:
    """디버깅 SOP 에러 분류 체계(4.2)의 패턴을 시드 등록."""
    patterns = [
        ("ImportError", "ImportError", "pip list, venv 활성화", "terminal", ""),
        ("ModuleNotFoundError", "ImportError", "pip list, venv 활성화", "terminal", ""),
        ("KeyError", "KeyError", "입력 데이터 구조 확인", "print/debugger", ""),
        ("AttributeError", "AttributeError", "입력 데이터 구조 확인", "print/debugger", ""),
        ("ConnectionError", "ConnectionError", "네트워크, API 엔드포인트", "curl/.env", ""),
        ("FileNotFoundError", "FileNotFoundError", "경로, .tmp/ 존재 여부", "ls/os.path.exists", ""),
        ("TimeoutError", "TimeoutError", "API 레이트리밋, 네트워크 지연", "로그/재시도", ""),
        ("asyncio.TimeoutError", "TimeoutError", "async 작업 타임아웃", "asyncio.wait_for", ""),
        ("PermissionError", "PermissionError", "파일 권한, OAuth 토큰", "credentials.json", ""),
        ("sqlite3.OperationalError", "DatabaseError", "DB 락, 테이블 누락", "sqlite3/_migrate()", "content_db"),
        ("notion_client", "NotionError", "속성명 불일치, 401", "config.yaml 매핑", "notion_client"),
        ("is not a property", "NotionError", "Notion 속성명 불일치", "config.yaml 매핑", "notion_client"),
        ("401", "AuthError", "인증 토큰 만료/무효", ".env 키 확인", ""),
        ("429", "RateLimitError", "API 레이트리밋", "재시도/배치 엔드포인트", ""),
        ("500", "ServerError", "외부 서버 에러", "재시도/상태 페이지 확인", ""),
        ("DuplicateWidget", "StreamlitError", "위젯 key 중복", "st.session_state", "workspace/execution/pages/"),
        ("playwright", "PlaywrightError", "브라우저 설치/타임아웃", "playwright install", "blind-to-x"),
        ("content_filter", "SafetyFilter", "DALL-E 안전 필터", "프롬프트 정화/폴백", "media_step"),
        ("JSONDecodeError", "ParseError", "API 응답 파싱 실패", "try/except + raw 로그", ""),
    ]
    count = 0
    for pattern, etype, first_check, tool, module_hint in patterns:
        register_pattern(pattern, etype, first_check, tool, module_hint)
        count += 1
    return count


# ── 스크랩 품질 히스토리 (P2-C) ───────────────────────────


def log_scrape_quality(source: str, url: str, quality_score: float, issues: list) -> None:
    """스크랩 품질 결과를 scrape_quality_log 테이블에 기록.

    Args:
        source: 수집 소스 ("blind", "ppomppu" 등)
        url: 게시글 URL
        quality_score: scrape quality score (0~100)
        issues: 품질 저하 이유 목록
    """
    init_db()
    conn = _conn()
    try:
        conn.execute(
            "INSERT INTO scrape_quality_log (logged_at, source, url, quality_score, issues) VALUES (?, ?, ?, ?, ?)",
            (
                datetime.now(timezone.utc).isoformat(),
                source[:100],
                url[:500],
                round(float(quality_score), 2),
                json.dumps(issues, ensure_ascii=False),
            ),
        )
        conn.commit()
    except Exception:
        pass  # 품질 로깅 실패가 메인 파이프라인을 막으면 안 됨
    finally:
        conn.close()


def get_scrape_quality_stats(days: int = 14) -> Dict:
    """소스별 평균 품질 점수 및 이슈 분포 조회."""
    init_db()
    conn = _conn()
    try:
        cutoff = datetime.now(timezone.utc).replace(microsecond=0).isoformat()[:10]
        rows = conn.execute(
            "SELECT source, AVG(quality_score) as avg_score, COUNT(*) as total "
            "FROM scrape_quality_log "
            "WHERE logged_at >= date(?, ?) "
            "GROUP BY source ORDER BY avg_score DESC",
            (cutoff, f"-{days} days"),
        ).fetchall()
        return {"by_source": [dict(r) for r in rows], "lookback_days": days}
    finally:
        conn.close()


# ── CLI ────────────────────────────────────────────────────


def _print_entries(entries: List[Dict]) -> None:
    if not entries:
        print("(결과 없음)")
        return
    for e in entries:
        d_flag = "📝" if e.get("directive_updated") else "  "
        t_flag = "🧪" if e.get("test_added") else "  "
        print(f"  [{e['severity']}] {e['created_at']}  {e['module'] or '(no module)'}")
        print(f"        증상: {e['symptom']}")
        if e.get("root_cause"):
            print(f"        원인: {e['root_cause']}")
        if e.get("solution"):
            print(f"        해결: {e['solution']}")
        print(f"        {d_flag} directive  {t_flag} test  layer={e['layer']}")
        print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Joolife Debugging History DB")
    sub = parser.add_subparsers(dest="command")

    # add
    add_p = sub.add_parser("add", help="디버깅 이력 추가")
    add_p.add_argument("--severity", default="P2", choices=["P0", "P1", "P2", "P3"])
    add_p.add_argument("--layer", default="execution", choices=["directive", "orchestration", "execution"])
    add_p.add_argument("--module", default="")
    add_p.add_argument("--symptom", required=True)
    add_p.add_argument("--cause", default="")
    add_p.add_argument("--solution", default="")
    add_p.add_argument("--directive-updated", action="store_true")
    add_p.add_argument("--test-added", action="store_true")
    add_p.add_argument("--commit", default="")
    add_p.add_argument("--tags", default="")
    add_p.add_argument("--notes", default="")

    # list
    list_p = sub.add_parser("list", help="이력 조회")
    list_p.add_argument("--severity", default=None)
    list_p.add_argument("--layer", default=None)
    list_p.add_argument("--module", default=None)
    list_p.add_argument("--limit", type=int, default=20)

    # search
    search_p = sub.add_parser("search", help="키워드 검색")
    search_p.add_argument("keyword")

    # stats
    sub.add_parser("stats", help="통계")

    # archive
    archive_p = sub.add_parser("archive", help="오래된 이력 삭제 (기본 90일)")
    archive_p.add_argument("--days", type=int, default=90, help="보관 기간 (일)")

    # seed
    sub.add_parser("seed", help="알려진 에러 패턴 시드 등록")

    # patterns
    sub.add_parser("patterns", help="등록된 에러 패턴 목록")

    # lookup
    lookup_p = sub.add_parser("lookup", help="에러 메시지로 패턴 검색")
    lookup_p.add_argument("error_message")

    args = parser.parse_args()

    if args.command == "add":
        entry_id = add_entry(
            symptom=args.symptom,
            severity=args.severity,
            layer=args.layer,
            module=args.module,
            root_cause=args.cause,
            solution=args.solution,
            directive_updated=args.directive_updated,
            test_added=args.test_added,
            commit_hash=args.commit,
            tags=args.tags,
            notes=args.notes,
        )
        print(f"Added entry #{entry_id}")

    elif args.command == "list":
        entries = list_entries(severity=args.severity, layer=args.layer, module=args.module, limit=args.limit)
        _print_entries(entries)

    elif args.command == "search":
        entries = search_entries(args.keyword)
        _print_entries(entries)

    elif args.command == "stats":
        stats = get_stats()
        print(json.dumps(stats, indent=2, ensure_ascii=False))

    elif args.command == "archive":
        deleted = archive_old_entries(retention_days=args.days)
        print(f"Archived {deleted} entries older than {args.days} days")

    elif args.command == "seed":
        count = seed_known_patterns()
        print(f"Seeded {count} known error patterns")

    elif args.command == "patterns":
        patterns = list_patterns()
        if not patterns:
            print("(등록된 패턴 없음 — 'seed' 명령으로 초기화하세요)")
        else:
            for p in patterns:
                print(f'  [{p["error_type"]}] "{p["pattern"]}" (seen {p["times_seen"]}x)')
                print(f"        첫 확인: {p['first_check']}  도구: {p['tool']}")
                if p["module_hint"]:
                    print(f"        모듈 힌트: {p['module_hint']}")
                print()

    elif args.command == "lookup":
        matches = lookup_pattern(args.error_message)
        if not matches:
            print("알려진 패턴 없음")
        else:
            for m in matches:
                print(f'  [{m["error_type"]}] "{m["pattern"]}"')
                print(f"        첫 확인: {m['first_check']}")
                print(f"        도구: {m['tool']}")
                print()

    else:
        parser.print_help()
