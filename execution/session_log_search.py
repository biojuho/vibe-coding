#!/usr/bin/env python3
"""session_log_search.py — .ai/SESSION_LOG + archive 통합 FTS5 검색

3계층 아키텍처의 Execution 계층. 현재 SESSION_LOG.md와 archive/ 전체를
SQLite FTS5 인덱스로 만들고 BM25로 랭킹해서 과거 AI 세션 기록을 검색한다.

지원 포맷:
    1) 현재 로그 — 마크다운 테이블:  | Date | Tool | Summary | Files |
    2) 아카이브   — 헤딩 + 본문:     ## YYYY-MM-DD | Tool | Title

Usage:
    python execution/session_log_search.py "notion timeout"
    python execution/session_log_search.py --tool Codex --since 2026-04-01 "feedback loop"
    python execution/session_log_search.py --reindex
    python execution/session_log_search.py --stats

인덱스 위치: .tmp/session_log_search.db (재생성 가능, 커밋 금지)
"""

from __future__ import annotations

import argparse
import re
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AI_DIR = ROOT / ".ai"
ARCHIVE_DIR = AI_DIR / "archive"
DB_PATH = ROOT / ".tmp" / "session_log_search.db"

ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# Archive headings use '|', '—' (em dash), or '??' as separators between
# date, tool, and title. The '??' variant exists because one archive file's
# em-dashes were lossily re-encoded at some point; keep it searchable anyway.
_SEP = r"(?:\||\u2014|\?\?)"
HEADING_RE = re.compile(
    r"^##\s+(?P<date>\d{4}-\d{2}-\d{2})\s*" + _SEP + r"\s*"
    r"(?P<tool>.+?)\s*" + _SEP + r"\s*"
    r"(?P<title>.+?)\s*$"
)


@dataclass
class Entry:
    date: str
    tool: str
    title: str
    body: str
    files: str
    source: str


def parse_table_file(path: Path) -> list[Entry]:
    """Parse current SESSION_LOG.md (markdown table)."""
    entries: list[Entry] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            continue
        parts = [p.strip() for p in line.strip().strip("|").split("|")]
        if len(parts) < 4:
            continue
        date, tool = parts[0], parts[1]
        if not ISO_DATE.match(date):
            continue
        # Summary may contain inner '|'; join middle cells back together.
        summary = " | ".join(parts[2:-1])
        files = parts[-1]
        entries.append(Entry(date=date, tool=tool, title="", body=summary, files=files, source=path.name))
    return entries


def parse_heading_file(path: Path) -> list[Entry]:
    """Parse archive files (## heading + multi-line body)."""
    lines = path.read_text(encoding="utf-8").splitlines()
    entries: list[Entry] = []
    current: Entry | None = None
    body_buf: list[str] = []

    def flush() -> None:
        nonlocal current
        if current is not None:
            current.body = "\n".join(body_buf).strip()
            entries.append(current)

    for line in lines:
        m = HEADING_RE.match(line)
        if m:
            flush()
            current = Entry(
                date=m["date"],
                tool=m["tool"],
                title=m["title"],
                body="",
                files="",
                source=path.name,
            )
            body_buf = []
            continue
        if current is not None:
            body_buf.append(line)
    flush()
    return entries


def discover_files() -> list[tuple[Path, str]]:
    files: list[tuple[Path, str]] = []
    current = AI_DIR / "SESSION_LOG.md"
    if current.exists():
        files.append((current, "table"))
    if ARCHIVE_DIR.exists():
        for p in sorted(ARCHIVE_DIR.glob("SESSION_LOG_*.md")):
            files.append((p, "heading"))
    return files


def build_index() -> int:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            """
            CREATE VIRTUAL TABLE entries USING fts5(
                date, tool, title, body, files, source,
                tokenize = 'unicode61 remove_diacritics 2'
            )
            """
        )
    except sqlite3.OperationalError as exc:
        conn.close()
        raise SystemExit(f"SQLite FTS5 unavailable ({exc}). Rebuild Python with FTS5 or install pysqlite3.") from exc

    count = 0
    for path, fmt in discover_files():
        parser = parse_table_file if fmt == "table" else parse_heading_file
        for e in parser(path):
            conn.execute(
                "INSERT INTO entries (date, tool, title, body, files, source) VALUES (?, ?, ?, ?, ?, ?)",
                (e.date, e.tool, e.title, e.body, e.files, e.source),
            )
            count += 1
    conn.commit()
    conn.close()
    return count


def should_rebuild() -> bool:
    if not DB_PATH.exists():
        return True
    db_mtime = DB_PATH.stat().st_mtime
    for path, _ in discover_files():
        if path.stat().st_mtime > db_mtime:
            return True
    return False


def ensure_index() -> None:
    if should_rebuild():
        build_index()


_FTS_SAFE_TOKEN = re.compile(r"^\w+\*?$", re.UNICODE)


def normalize_query(q: str) -> str:
    """Auto-quote tokens with punctuation so `hanwoo-dashboard` etc. work.

    Leaves explicit FTS5 syntax untouched if the user already used quotes,
    parentheses, or a column filter (`col:term`).
    """
    if '"' in q or "(" in q or ":" in q:
        return q
    out: list[str] = []
    for token in q.split():
        if token in ("AND", "OR", "NOT") or token.upper().startswith("NEAR"):
            out.append(token)
            continue
        if _FTS_SAFE_TOKEN.match(token):
            out.append(token)
            continue
        # Wrap as a quoted phrase to escape FTS5 punctuation semantics.
        out.append('"' + token.replace('"', "") + '"')
    return " ".join(out)


def search(query: str, *, tool: str | None, since: str | None, limit: int) -> list[sqlite3.Row]:
    ensure_index()
    query = normalize_query(query)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    sql = [
        "SELECT date, tool, title,",
        " snippet(entries, 3, '[', ']', ' … ', 14) AS snip,",
        " files, source, bm25(entries) AS score",
        "FROM entries WHERE entries MATCH ?",
    ]
    params: list = [query]
    if tool:
        sql.append("AND tool LIKE ?")
        params.append(f"%{tool}%")
    if since:
        sql.append("AND date >= ?")
        params.append(since)
    sql.append("ORDER BY score LIMIT ?")
    params.append(limit)
    rows = conn.execute(" ".join(sql), params).fetchall()
    conn.close()
    return rows


def format_results(rows: list[sqlite3.Row]) -> str:
    if not rows:
        return "(no matches)"
    out: list[str] = []
    for r in rows:
        header = f"{r['date']} | {r['tool']} | {r['source']}"
        if r["title"]:
            header += f" | {r['title']}"
        out.append(header)
        snip = (r["snip"] or "").replace("\n", " ")
        out.append(f"  {snip}")
        if r["files"]:
            files_compact = r["files"]
            if len(files_compact) > 160:
                files_compact = files_compact[:157] + "..."
            out.append(f"  files: {files_compact}")
        out.append("")
    return "\n".join(out).rstrip()


def stats() -> str:
    ensure_index()
    conn = sqlite3.connect(DB_PATH)
    total = conn.execute("SELECT COUNT(*) FROM entries").fetchone()[0]
    date_range = conn.execute("SELECT MIN(date), MAX(date) FROM entries").fetchone()
    by_tool = conn.execute("SELECT tool, COUNT(*) FROM entries GROUP BY tool ORDER BY 2 DESC").fetchall()
    by_source = conn.execute("SELECT source, COUNT(*) FROM entries GROUP BY source ORDER BY 1").fetchall()
    conn.close()
    lines = [
        f"Total entries: {total}",
        f"Date range: {date_range[0]} → {date_range[1]}",
        f"Index: {DB_PATH}",
        "",
        "By tool:",
    ]
    lines += [f"  {t}: {n}" for t, n in by_tool]
    lines += ["", "By source:"]
    lines += [f"  {s}: {n}" for s, n in by_source]
    return "\n".join(lines)


def main() -> int:
    p = argparse.ArgumentParser(
        description=".ai/SESSION_LOG + archive 통합 FTS5 검색",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "FTS5 쿼리 예:\n"
            "  notion timeout         (AND 기본)\n"
            "  notion OR timeout\n"
            '  "exact phrase"\n'
            "  blind*                 (prefix)\n"
        ),
    )
    p.add_argument("query", nargs="*", help="검색어 (여러 단어 허용, FTS5 MATCH 문법)")
    p.add_argument("--tool", help="도구명 필터 (예: Codex, Claude, Gemini)")
    p.add_argument("--since", help="YYYY-MM-DD 이후만")
    p.add_argument("--limit", type=int, default=10, help="결과 개수 (default 10)")
    p.add_argument("--reindex", action="store_true", help="인덱스 강제 재생성")
    p.add_argument("--stats", action="store_true", help="인덱스 통계 출력")
    args = p.parse_args()

    query_str = " ".join(args.query).strip() if args.query else ""

    if args.reindex:
        n = build_index()
        print(f"Rebuilt index: {n} entries -> {DB_PATH}")
        if not query_str and not args.stats:
            return 0

    if args.stats:
        print(stats())
        return 0

    if not query_str:
        p.error("query is required (or use --stats / --reindex)")

    rows = search(query_str, tool=args.tool, since=args.since, limit=args.limit)
    print(format_results(rows))
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
