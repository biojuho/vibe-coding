"""
콘텐츠 DB - Shorts Manager용.
SQLite 기반 콘텐츠 큐 및 생성 이력 관리.

Usage:
    python workspace/execution/content_db.py init
    python workspace/execution/content_db.py add --topic "블랙홀의 미스터리 5가지" --channel "우주/천문학"
    python workspace/execution/content_db.py list
    python workspace/execution/content_db.py channels
"""

import argparse
import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from path_contract import TMP_ROOT, resolve_project_dir

OPS_STATUS_HEALTHY = "healthy"
OPS_STATUS_WARNING = "warning"
OPS_STATUS_CRITICAL = "critical"
OPS_STATUS_SETUP_REQUIRED = "setup_required"

_SHORTS_V2_DIR = resolve_project_dir("shorts-maker-v2", required_paths=("config.yaml",))
_SHORTS_BGM_DIR = _SHORTS_V2_DIR / "assets" / "bgm"
_SHORTS_BRAND_DIR = _SHORTS_V2_DIR / "assets" / "channels"
_SHORTS_OUTPUT_DIR = _SHORTS_V2_DIR / "output"
DB_PATH = TMP_ROOT / "content.db"
UPDATABLE_COLUMNS = {
    "status",
    "job_id",
    "title",
    "video_path",
    "thumbnail_path",
    "cost_usd",
    "duration_sec",
    "notes",
    "channel",
    "youtube_video_id",
    "youtube_status",
    "youtube_url",
    "youtube_uploaded_at",
    "youtube_error",
    "notion_page_id",
    "yt_views",
    "yt_likes",
    "yt_comments",
    "yt_ctr",
    "yt_avg_watch_sec",
    "yt_stats_updated_at",
    "hook_pattern",
}


def _conn() -> sqlite3.Connection:
    """SQLite 연결 반환. `with _conn() as conn:` 패턴으로 사용하면 자동 close."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")  # 동시 읽기 허용
    return conn


def init_db() -> None:
    conn = _conn()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS content_queue (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                topic          TEXT NOT NULL,
                channel        TEXT NOT NULL DEFAULT '',
                status         TEXT NOT NULL DEFAULT 'pending',
                job_id         TEXT DEFAULT '',
                title          TEXT DEFAULT '',
                video_path     TEXT DEFAULT '',
                thumbnail_path TEXT DEFAULT '',
                cost_usd       REAL DEFAULT 0.0,
                duration_sec   REAL DEFAULT 0.0,
                notes          TEXT DEFAULT '',
                youtube_video_id    TEXT DEFAULT '',
                youtube_status      TEXT DEFAULT '',
                youtube_url         TEXT DEFAULT '',
                youtube_uploaded_at TEXT DEFAULT '',
                youtube_error       TEXT DEFAULT '',
                created_at     TEXT DEFAULT (datetime('now','localtime')),
                updated_at     TEXT DEFAULT (datetime('now','localtime'))
            );

            CREATE TABLE IF NOT EXISTS channel_settings (
                channel            TEXT PRIMARY KEY,
                voice              TEXT DEFAULT 'alloy',
                style_preset       TEXT DEFAULT 'default',
                font_color         TEXT DEFAULT '#FFD700',
                image_style_prefix TEXT DEFAULT '',
                created_at         TEXT DEFAULT (datetime('now','localtime')),
                updated_at         TEXT DEFAULT (datetime('now','localtime'))
            );
        """)
        # 기존 DB migration: 컬럼 없으면 추가
        _migrations = [
            "ALTER TABLE content_queue ADD COLUMN channel TEXT NOT NULL DEFAULT ''",
            "ALTER TABLE content_queue ADD COLUMN youtube_video_id TEXT DEFAULT ''",
            "ALTER TABLE content_queue ADD COLUMN youtube_status TEXT DEFAULT ''",
            "ALTER TABLE content_queue ADD COLUMN youtube_url TEXT DEFAULT ''",
            "ALTER TABLE content_queue ADD COLUMN youtube_uploaded_at TEXT DEFAULT ''",
            "ALTER TABLE content_queue ADD COLUMN youtube_error TEXT DEFAULT ''",
            "ALTER TABLE content_queue ADD COLUMN notion_page_id TEXT DEFAULT ''",
            "ALTER TABLE content_queue ADD COLUMN yt_views INTEGER DEFAULT 0",
            "ALTER TABLE content_queue ADD COLUMN yt_likes INTEGER DEFAULT 0",
            "ALTER TABLE content_queue ADD COLUMN yt_comments INTEGER DEFAULT 0",
            "ALTER TABLE content_queue ADD COLUMN yt_ctr REAL DEFAULT 0.0",
            "ALTER TABLE content_queue ADD COLUMN yt_avg_watch_sec REAL DEFAULT 0.0",
            "ALTER TABLE content_queue ADD COLUMN yt_stats_updated_at TEXT DEFAULT ''",
            "ALTER TABLE content_queue ADD COLUMN hook_pattern TEXT DEFAULT ''",
        ]
        for stmt in _migrations:
            try:
                conn.execute(stmt)
            except sqlite3.OperationalError:
                pass  # 이미 존재
        conn.commit()
    finally:
        conn.close()


def add_topic(topic: str, notes: str = "", channel: str = "") -> int:
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO content_queue (topic, notes, channel) VALUES (?, ?, ?)",
            (topic.strip(), notes.strip(), channel.strip()),
        )
        conn.commit()
        return cur.lastrowid or 0


def get_all(channel: str | None = None) -> list[dict[str, Any]]:
    with _conn() as conn:
        if channel:
            rows = conn.execute(
                "SELECT * FROM content_queue WHERE channel = ? ORDER BY created_at DESC",
                (channel,),
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM content_queue ORDER BY created_at DESC").fetchall()
    return [dict(r) for r in rows]


def get_by_id(item_id: int) -> dict[str, Any] | None:
    """단일 항목 조회. 없으면 None."""
    with _conn() as conn:
        row = conn.execute("SELECT * FROM content_queue WHERE id = ?", (item_id,)).fetchone()
    return dict(row) if row else None


def get_channels() -> list[str]:
    """채널 목록 반환 (중복 제거, 알파벳 순)."""
    with _conn() as conn:
        rows = conn.execute(
            "SELECT DISTINCT channel FROM content_queue WHERE channel != '' ORDER BY channel"
        ).fetchall()
    return [r["channel"] for r in rows]


def get_channel_settings(channel: str) -> dict[str, Any] | None:
    """채널 설정 반환. 없으면 None."""
    with _conn() as conn:
        row = conn.execute("SELECT * FROM channel_settings WHERE channel = ?", (channel,)).fetchone()
    return dict(row) if row else None


_CHANNEL_SETTING_COLUMNS = {"voice", "style_preset", "font_color", "image_style_prefix"}


def upsert_channel_settings(channel: str, **kwargs: Any) -> None:
    """채널 설정 생성 또는 업데이트."""
    invalid = set(kwargs) - _CHANNEL_SETTING_COLUMNS
    if invalid:
        raise ValueError(f"Unsupported channel_settings fields: {', '.join(sorted(invalid))}")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _conn() as conn:
        existing = conn.execute("SELECT channel FROM channel_settings WHERE channel = ?", (channel,)).fetchone()
        if existing:
            if kwargs:
                conn.execute(
                    """
                    UPDATE channel_settings
                    SET
                        voice = COALESCE(?, voice),
                        style_preset = COALESCE(?, style_preset),
                        font_color = COALESCE(?, font_color),
                        image_style_prefix = COALESCE(?, image_style_prefix),
                        updated_at = ?
                    WHERE channel = ?
                    """,
                    (
                        kwargs.get("voice"),
                        kwargs.get("style_preset"),
                        kwargs.get("font_color"),
                        kwargs.get("image_style_prefix"),
                        now,
                        channel,
                    ),
                )
        else:
            conn.execute(
                """
                INSERT INTO channel_settings (
                    channel,
                    voice,
                    style_preset,
                    font_color,
                    image_style_prefix,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    channel,
                    kwargs.get("voice", "alloy"),
                    kwargs.get("style_preset", "default"),
                    kwargs.get("font_color", "#FFD700"),
                    kwargs.get("image_style_prefix", ""),
                    now,
                    now,
                ),
            )
        conn.commit()


def update_job(item_id: int, **kwargs: Any) -> None:
    if not kwargs:
        return
    invalid_keys = set(kwargs) - UPDATABLE_COLUMNS
    if invalid_keys:
        invalid_list = ", ".join(sorted(invalid_keys))
        raise ValueError(f"Unsupported update fields: {invalid_list}")
    kwargs["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    set_clause = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [item_id]
    query = f"UPDATE content_queue SET {set_clause} WHERE id = ?"  # noqa: S608 — keys whitelisted via UPDATABLE_COLUMNS
    with _conn() as conn:
        conn.execute(query, values)
        conn.commit()


def delete_item(item_id: int) -> None:
    with _conn() as conn:
        conn.execute("DELETE FROM content_queue WHERE id = ?", (item_id,))
        conn.commit()


def get_kpis(channel: str | None = None) -> dict[str, Any]:
    params = (channel,) if channel else ()
    base_query = """
        SELECT
            COUNT(*)                                               AS total,
            SUM(CASE WHEN status='success' THEN 1 ELSE 0 END)    AS success_count,
            SUM(CASE WHEN status='failed'  THEN 1 ELSE 0 END)    AS failed_count,
            SUM(CASE WHEN status='pending' THEN 1 ELSE 0 END)    AS pending_count,
            SUM(CASE WHEN status='running' THEN 1 ELSE 0 END)    AS running_count,
            COALESCE(SUM(cost_usd), 0.0)                          AS total_cost_usd,
            COALESCE(AVG(CASE WHEN status='success' THEN cost_usd END), 0.0) AS avg_cost_usd
        FROM content_queue
    """
    if channel:
        base_query += " WHERE channel = ?"
    with _conn() as conn:
        row = conn.execute(base_query, params).fetchone()
    return dict(row) if row else {}


def get_daily_stats(days: int = 30) -> list[dict[str, Any]]:
    """일별 생성 건수 + 비용 집계 (최근 N일)."""
    with _conn() as conn:
        rows = conn.execute(
            """
            SELECT
                date(updated_at) AS day,
                COUNT(*)                                            AS total,
                SUM(CASE WHEN status='success' THEN 1 ELSE 0 END) AS success,
                SUM(CASE WHEN status='failed'  THEN 1 ELSE 0 END) AS failed,
                COALESCE(SUM(cost_usd), 0.0)                       AS cost_usd
            FROM content_queue
            WHERE updated_at >= date('now', 'localtime', ?)
              AND status IN ('success', 'failed')
            GROUP BY date(updated_at)
            ORDER BY day
        """,
            (f"-{days} days",),
        ).fetchall()
    return [dict(r) for r in rows]


def get_channel_stats() -> list[dict[str, Any]]:
    """채널별 성공/실패/비용/길이 집계."""
    with _conn() as conn:
        rows = conn.execute("""
            SELECT
                channel,
                COUNT(*)                                            AS total,
                SUM(CASE WHEN status='success' THEN 1 ELSE 0 END) AS success,
                SUM(CASE WHEN status='failed'  THEN 1 ELSE 0 END) AS failed,
                SUM(CASE WHEN status='pending' THEN 1 ELSE 0 END) AS pending,
                COALESCE(SUM(cost_usd), 0.0)                       AS total_cost,
                COALESCE(AVG(CASE WHEN status='success' THEN cost_usd END), 0.0)         AS avg_cost,
                COALESCE(AVG(CASE WHEN status='success' THEN duration_sec END), 0.0)     AS avg_duration
            FROM content_queue
            WHERE channel != ''
            GROUP BY channel
            ORDER BY channel
        """).fetchall()
    return [dict(r) for r in rows]


def get_top_performing_topics(
    limit: int = 10,
    channel: str | None = None,
) -> list[dict[str, Any]]:
    """성공한 주제 중 비용 효율이 좋은 상위 N개 반환."""
    base_query = """
        SELECT topic, channel, cost_usd, duration_sec, title, notes, updated_at
        FROM content_queue
        WHERE status = 'success'
    """
    params: list[Any] = []
    if channel:
        base_query += " AND channel = ?"
        params.append(channel)
    base_query += " ORDER BY cost_usd ASC, updated_at DESC LIMIT ?"
    params.append(limit)
    with _conn() as conn:
        rows = conn.execute(base_query, params).fetchall()  # noqa: S608
    return [dict(r) for r in rows]


def get_hourly_stats(days: int = 30) -> list[dict[str, Any]]:
    """시간대별 생성 성공률 집계."""
    with _conn() as conn:
        rows = conn.execute(
            """
            SELECT
                CAST(strftime('%H', updated_at) AS INTEGER) AS hour,
                COUNT(*)                                            AS total,
                SUM(CASE WHEN status='success' THEN 1 ELSE 0 END) AS success,
                SUM(CASE WHEN status='failed'  THEN 1 ELSE 0 END) AS failed,
                ROUND(
                    CAST(SUM(CASE WHEN status='success' THEN 1 ELSE 0 END) AS REAL)
                    / MAX(COUNT(*), 1) * 100, 1
                ) AS success_rate
            FROM content_queue
            WHERE updated_at >= date('now', 'localtime', ?)
              AND status IN ('success', 'failed')
            GROUP BY hour
            ORDER BY hour
        """,
            (f"-{days} days",),
        ).fetchall()
    return [dict(r) for r in rows]


def get_youtube_stats() -> dict[str, int]:
    """YouTube 업로드 현황 집계."""
    with _conn() as conn:
        row = conn.execute("""
            SELECT
                SUM(CASE WHEN youtube_status = 'uploaded' THEN 1 ELSE 0 END) AS uploaded,
                SUM(CASE WHEN youtube_status = 'failed'   THEN 1 ELSE 0 END) AS yt_failed,
                SUM(CASE WHEN status = 'success' AND (youtube_status = '' OR youtube_status IS NULL) THEN 1 ELSE 0 END) AS awaiting
            FROM content_queue
        """).fetchone()
    if row:
        return {"uploaded": row["uploaded"] or 0, "failed": row["yt_failed"] or 0, "awaiting": row["awaiting"] or 0}
    return {"uploaded": 0, "failed": 0, "awaiting": 0}  # pragma: no cover — aggregate query always returns a row


def _collect_channel_usage_stats() -> dict[str, dict[str, int]]:
    with _conn() as conn:
        rows = conn.execute(
            """
            SELECT
                channel,
                COUNT(*) AS total_count,
                SUM(CASE WHEN status='pending' THEN 1 ELSE 0 END) AS pending_count,
                SUM(CASE WHEN status='running' THEN 1 ELSE 0 END) AS running_count,
                SUM(CASE WHEN status='failed' THEN 1 ELSE 0 END) AS failed_count,
                SUM(CASE WHEN status='success' THEN 1 ELSE 0 END) AS success_count
            FROM content_queue
            WHERE channel != ''
            GROUP BY channel
            """
        ).fetchall()
    return {
        row["channel"]: {
            "total_count": int(row["total_count"] or 0),
            "pending_count": int(row["pending_count"] or 0),
            "running_count": int(row["running_count"] or 0),
            "failed_count": int(row["failed_count"] or 0),
            "success_count": int(row["success_count"] or 0),
        }
        for row in rows
    }


def _resolve_bgm_readiness() -> bool:
    if not _SHORTS_BGM_DIR.exists():
        return False
    return any(path.is_file() and path.suffix.lower() == ".mp3" for path in _SHORTS_BGM_DIR.iterdir())


def _resolve_brand_asset_readiness(channel: str) -> bool:
    brand_dir = _SHORTS_BRAND_DIR / channel
    return (brand_dir / "intro.png").exists() and (brand_dir / "outro.png").exists()


def _derive_ops_status(issues: list[str]) -> str:
    if any(issue.startswith("setup:") for issue in issues):
        return OPS_STATUS_SETUP_REQUIRED
    if any(issue.startswith("critical:") for issue in issues):
        return OPS_STATUS_CRITICAL
    if issues:
        return OPS_STATUS_WARNING
    return OPS_STATUS_HEALTHY


def _derive_next_action(issues: list[str]) -> str:
    if not issues:
        return "렌더 실행 가능"
    if any(issue.startswith("setup:") for issue in issues):
        return "채널 설정 저장"
    if any("brand_asset_missing" in issue for issue in issues):
        return "브랜드 에셋 생성"
    if any("bgm_missing" in issue for issue in issues):
        return "BGM 추가 또는 스킵 확인"
    if any("failed_jobs" in issue for issue in issues):
        return "실패 건 확인"
    return "운영 상태 점검"


def get_channel_readiness_summary(channels: list[str] | None = None) -> list[dict[str, Any]]:
    settings_by_channel: dict[str, dict[str, Any]] = {}
    conn = _conn()
    rows = conn.execute("SELECT * FROM channel_settings ORDER BY channel").fetchall()
    conn.close()
    for row in rows:
        settings_by_channel[row["channel"]] = dict(row)

    usage_by_channel = _collect_channel_usage_stats()
    channel_names = set(settings_by_channel) | set(usage_by_channel)
    if channels:
        channel_names |= {channel for channel in channels if channel}

    bgm_ready = _resolve_bgm_readiness()
    summary: list[dict[str, Any]] = []
    for channel in sorted(channel_names):
        settings = settings_by_channel.get(channel)
        stats = usage_by_channel.get(
            channel,
            {
                "total_count": 0,
                "pending_count": 0,
                "running_count": 0,
                "failed_count": 0,
                "success_count": 0,
            },
        )
        brand_assets_ready = _resolve_brand_asset_readiness(channel)
        issues: list[str] = []
        if settings is None:
            issues.append("setup:channel_settings_missing")
        if not bgm_ready:
            issues.append("warning:bgm_missing")
        if not brand_assets_ready:
            issues.append("warning:brand_asset_missing")
        if stats["failed_count"] > 0:
            issues.append("warning:failed_jobs_present")

        summary.append(
            {
                "channel": channel,
                "status": _derive_ops_status(issues),
                "voice": (settings or {}).get("voice", ""),
                "style_preset": (settings or {}).get("style_preset", ""),
                "font_color": (settings or {}).get("font_color", ""),
                "image_style_prefix": (settings or {}).get("image_style_prefix", ""),
                "has_settings": settings is not None,
                "bgm_ready": bgm_ready,
                "brand_assets_ready": brand_assets_ready,
                "total_count": stats["total_count"],
                "pending_count": stats["pending_count"],
                "running_count": stats["running_count"],
                "failed_count": stats["failed_count"],
                "success_count": stats["success_count"],
                "issues": issues,
                "next_action": _derive_next_action(issues),
            }
        )
    return summary


def get_recent_failure_items(
    channel: str | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    conn = _conn()
    query = """
        SELECT *
        FROM content_queue
        WHERE status = 'failed'
    """
    params: list[Any] = []
    if channel:
        query += " AND channel = ?"
        params.append(channel)
    query += " ORDER BY updated_at DESC, id DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(query, params).fetchall()  # noqa: S608
    conn.close()

    bgm_ready = _resolve_bgm_readiness()
    failures: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        channel_name = item.get("channel", "")
        settings = get_channel_settings(channel_name) if channel_name else None
        brand_assets_ready = _resolve_brand_asset_readiness(channel_name) if channel_name else False
        issues: list[str] = []
        if channel_name and settings is None:
            issues.append("setup:channel_settings_missing")
        if not bgm_ready:
            issues.append("warning:bgm_missing")
        if channel_name and not brand_assets_ready:
            issues.append("warning:brand_asset_missing")

        if any(issue.startswith("setup:") for issue in issues):
            next_action = "채널 설정 저장 후 재실행"
        elif any("brand_asset_missing" in issue for issue in issues):
            next_action = "브랜드 에셋 확인 후 재실행"
        elif any("bgm_missing" in issue for issue in issues):
            next_action = "BGM 스킵 가능 여부 확인"
        elif item.get("notes"):
            next_action = "실패 메모 확인 후 재실행"
        else:
            next_action = "최근 로그 확인 후 재실행"

        failures.append(
            {
                **item,
                "has_settings": settings is not None,
                "bgm_ready": bgm_ready,
                "brand_assets_ready": brand_assets_ready,
                "issues": issues,
                "failure_reason": item.get("notes") or "실패 사유 메모 없음",
                "next_action": next_action,
                "retry_recommended": settings is not None,
            }
        )
    return failures


def _load_manifest_payloads(output_dir: Path | None = None) -> list[dict[str, Any]]:
    manifests_dir = output_dir or _SHORTS_OUTPUT_DIR
    if not manifests_dir.exists():
        return []

    payloads: list[dict[str, Any]] = []
    manifest_paths = sorted(
        manifests_dir.glob("*_manifest.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    for path in manifest_paths:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(payload, dict):
            continue
        payloads.append(
            {
                **payload,
                "_manifest_path": str(path),
            }
        )
    return payloads


def _check_manifest_vs_db(
    manifests: list[dict[str, Any]],
    job_lookup: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """매니페스트 → DB 방향 차이를 계산한다.

    Returns (missing_in_db, pending_sync).
    """
    missing_in_db: list[dict[str, Any]] = []
    pending_sync: list[dict[str, Any]] = []
    for manifest in manifests:
        job_id = manifest.get("job_id", "")
        if not job_id:
            continue
        item = job_lookup.get(job_id)
        if item is None:
            missing_in_db.append(
                {
                    "job_id": job_id,
                    "title": manifest.get("title", ""),
                    "status": manifest.get("status", ""),
                    "manifest_path": manifest["_manifest_path"],
                }
            )
            continue

        mismatches: list[str] = []
        if manifest.get("status") and item.get("status") != manifest.get("status"):
            mismatches.append("status")
        if manifest.get("output_path") and item.get("video_path") != manifest.get("output_path"):
            mismatches.append("video_path")
        if manifest.get("thumbnail_path") and item.get("thumbnail_path") != manifest.get("thumbnail_path"):
            mismatches.append("thumbnail_path")
        if manifest.get("title") and item.get("title") != manifest.get("title"):
            mismatches.append("title")
        if mismatches:
            pending_sync.append(
                {
                    "id": item["id"],
                    "job_id": job_id,
                    "topic": item.get("topic", ""),
                    "channel": item.get("channel", ""),
                    "mismatches": mismatches,
                    "manifest_path": manifest["_manifest_path"],
                }
            )
    return missing_in_db, pending_sync


def _check_db_vs_manifests(
    items: list[dict[str, Any]],
    manifest_job_ids: set[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """DB → 매니페스트 방향 차이를 계산한다.

    Returns (missing_output_file, missing_manifest).
    """
    missing_output_file: list[dict[str, Any]] = []
    missing_manifest: list[dict[str, Any]] = []
    for item in items:
        job_id = item.get("job_id", "")
        video_path = item.get("video_path", "")
        if item.get("status") == "success" and video_path and not Path(video_path).exists():
            missing_output_file.append(
                {
                    "id": item["id"],
                    "job_id": job_id,
                    "topic": item.get("topic", ""),
                    "channel": item.get("channel", ""),
                    "video_path": video_path,
                }
            )
        if job_id and job_id not in manifest_job_ids:
            missing_manifest.append(
                {
                    "id": item["id"],
                    "job_id": job_id,
                    "topic": item.get("topic", ""),
                    "channel": item.get("channel", ""),
                    "status": item.get("status", ""),
                }
            )
    return missing_output_file, missing_manifest


def get_manifest_sync_diffs(
    output_dir: Path | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    manifests = _load_manifest_payloads(output_dir=output_dir)
    items = get_all()
    job_lookup = {item.get("job_id"): item for item in items if item.get("job_id")}
    manifest_job_ids = {manifest.get("job_id") for manifest in manifests if manifest.get("job_id")}

    missing_in_db, pending_sync = _check_manifest_vs_db(manifests, job_lookup)
    missing_output_file, missing_manifest = _check_db_vs_manifests(items, manifest_job_ids)

    summary = {
        "missing_in_db_count": len(missing_in_db),
        "pending_sync_count": len(pending_sync),
        "missing_output_file_count": len(missing_output_file),
        "missing_manifest_count": len(missing_manifest),
    }

    return {
        "summary": summary,
        "missing_in_db": missing_in_db[:limit],
        "pending_sync": pending_sync[:limit],
        "missing_output_file": missing_output_file[:limit],
        "missing_manifest": missing_manifest[:limit],
    }


def get_review_queue_items(
    channel: str | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    query = """
        SELECT *
        FROM content_queue
        WHERE status = 'success'
          AND video_path != ''
    """
    params: list[Any] = []
    if channel:
        query += " AND channel = ?"
        params.append(channel)
    query += " ORDER BY updated_at DESC, id DESC LIMIT ?"
    params.append(limit)
    with _conn() as conn:
        rows = conn.execute(query, params).fetchall()  # noqa: S608

    queue: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        video_path = str(item.get("video_path") or "")
        thumbnail_path = str(item.get("thumbnail_path") or "")
        video_exists = bool(video_path) and Path(video_path).exists()
        thumbnail_exists = bool(thumbnail_path) and Path(thumbnail_path).exists()

        if not video_exists:
            review_status = OPS_STATUS_CRITICAL
            next_action = "영상 재생성 또는 경로 확인"
        elif thumbnail_path and not thumbnail_exists:
            review_status = OPS_STATUS_WARNING
            next_action = "썸네일 재생성 확인"
        else:
            review_status = OPS_STATUS_HEALTHY
            next_action = "수동 검수 진행"

        queue.append(
            {
                **item,
                "video_exists": video_exists,
                "thumbnail_exists": thumbnail_exists,
                "review_status": review_status,
                "next_action": next_action,
            }
        )
    return queue


def get_uploadable_items(
    channel: str | None = None,
    limit: int = 10,
    include_failed: bool = False,
) -> list[dict[str, Any]]:
    """업로드 가능한 항목 조회 (성공 + 영상 있음 + 미업로드, 필요 시 실패 재시도 포함)."""
    query = """
        SELECT * FROM content_queue
        WHERE status = 'success'
          AND video_path != ''
          AND (
                youtube_status = ''
             OR youtube_status IS NULL
    """
    if include_failed:
        query += """
             OR youtube_status = 'failed'
        """
    query += """
          )
    """
    params: list[Any] = []
    if channel:
        query += " AND channel = ?"
        params.append(channel)
    query += " ORDER BY updated_at DESC LIMIT ?"
    params.append(limit)
    with _conn() as conn:
        rows = conn.execute(query, params).fetchall()  # noqa: S608
    return [dict(r) for r in rows]


def get_performance_stats(
    channel: str | None = None,
    min_views: int = 0,
) -> list[dict[str, Any]]:
    """YouTube 성과 데이터가 있는 항목 반환 (분석용)."""
    query = """
        SELECT id, topic, channel, title, hook_pattern,
               yt_views, yt_likes, yt_comments, yt_ctr, yt_avg_watch_sec,
               duration_sec, cost_usd, yt_stats_updated_at, youtube_url
        FROM content_queue
        WHERE youtube_status = 'uploaded'
          AND yt_views >= ?
    """
    params: list[Any] = [min_views]
    if channel:
        query += " AND channel = ?"
        params.append(channel)
    query += " ORDER BY yt_views DESC"
    with _conn() as conn:
        rows = conn.execute(query, params).fetchall()  # noqa: S608
    return [dict(r) for r in rows]


def get_hook_pattern_performance() -> list[dict[str, Any]]:
    """훅 패턴별 평균 성과 집계."""
    with _conn() as conn:
        rows = conn.execute("""
            SELECT
                hook_pattern,
                COUNT(*) AS count,
                COALESCE(AVG(yt_views), 0) AS avg_views,
                COALESCE(AVG(yt_likes), 0) AS avg_likes,
                COALESCE(AVG(yt_ctr), 0) AS avg_ctr,
                COALESCE(AVG(yt_avg_watch_sec), 0) AS avg_watch_sec
            FROM content_queue
            WHERE youtube_status = 'uploaded'
              AND hook_pattern != ''
              AND yt_views > 0
            GROUP BY hook_pattern
            ORDER BY avg_views DESC
        """).fetchall()
    return [dict(r) for r in rows]


def get_channel_performance_summary() -> list[dict[str, Any]]:
    """채널별 YouTube 성과 요약."""
    with _conn() as conn:
        rows = conn.execute("""
            SELECT
                channel,
                COUNT(*) AS video_count,
                COALESCE(SUM(yt_views), 0) AS total_views,
                COALESCE(AVG(yt_views), 0) AS avg_views,
                COALESCE(AVG(yt_ctr), 0) AS avg_ctr,
                COALESCE(AVG(yt_avg_watch_sec), 0) AS avg_watch_sec,
                COALESCE(SUM(cost_usd), 0) AS total_cost
            FROM content_queue
            WHERE youtube_status = 'uploaded'
              AND channel != ''
            GROUP BY channel
            ORDER BY total_views DESC
        """).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _cli() -> None:
    parser = argparse.ArgumentParser(description="Shorts Content DB CLI")
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("init", help="DB 초기화")

    add_p = sub.add_parser("add", help="주제 추가")
    add_p.add_argument("--topic", required=True)
    add_p.add_argument("--notes", default="")
    add_p.add_argument("--channel", default="")

    list_p = sub.add_parser("list", help="목록 출력")
    list_p.add_argument("--channel", default="")

    sub.add_parser("channels", help="채널 목록 출력")
    sub.add_parser("kpis", help="KPI 출력")

    ch_set_p = sub.add_parser("channel-set", help="채널 설정 저장")
    ch_set_p.add_argument("--channel", required=True)
    ch_set_p.add_argument("--voice", default="")
    ch_set_p.add_argument("--style-preset", dest="style_preset", default="")
    ch_set_p.add_argument("--font-color", dest="font_color", default="")
    ch_set_p.add_argument("--image-prefix", dest="image_style_prefix", default="")

    ch_get_p = sub.add_parser("channel-get", help="채널 설정 조회")
    ch_get_p.add_argument("--channel", required=True)

    args = parser.parse_args()
    if args.cmd == "init":
        init_db()
        print("DB 초기화 완료:", DB_PATH)
    elif args.cmd == "add":
        init_db()
        row_id = add_topic(args.topic, args.notes, args.channel)
        print(f"추가 완료 (id={row_id}): [{args.channel}] {args.topic}")
    elif args.cmd == "list":
        init_db()
        ch = getattr(args, "channel", "")
        for item in get_all(channel=ch or None):
            print(f"[{item['id']}] {item['status']:10s} [{item.get('channel', ''):12s}] {item['topic']}")
    elif args.cmd == "channels":
        init_db()
        for ch in get_channels():
            print(ch)
    elif args.cmd == "kpis":
        init_db()
        import json

        print(json.dumps(get_kpis(), indent=2))
    elif args.cmd == "channel-set":
        init_db()
        kwargs = {
            k: v
            for k, v in {
                "voice": args.voice,
                "style_preset": args.style_preset,
                "font_color": args.font_color,
                "image_style_prefix": args.image_style_prefix,
            }.items()
            if v
        }
        upsert_channel_settings(args.channel, **kwargs)
        print(f"채널 설정 저장: [{args.channel}] {kwargs}")
    elif args.cmd == "channel-get":
        init_db()
        import json

        settings = get_channel_settings(args.channel)
        if settings:
            print(json.dumps(settings, indent=2, ensure_ascii=False))
        else:
            print(f"[{args.channel}] 설정 없음")
    else:
        parser.print_help()


if __name__ == "__main__":
    _cli()
