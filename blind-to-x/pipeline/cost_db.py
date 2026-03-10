"""Persistent cost tracking for blind-to-x pipeline (SQLite backend).

Run costs are ephemeral in CostTracker (in-memory); this module persists them
to .tmp/btx_costs.db so the Streamlit dashboard can show historical trends.

Tables:
  daily_text_costs  — LLM text generation per provider
  daily_image_costs — image generation per provider
  draft_analytics   — draft style used per post (for A/B tracking)
"""

from __future__ import annotations

import logging
import sqlite3
import threading
from contextlib import contextmanager
from datetime import date, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# .tmp/ 는 blind-to-x 프로젝트 루트 기준
_DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / ".tmp" / "btx_costs.db"
GEMINI_IMAGE_DAILY_LIMIT = 500


class CostDatabase:
    """blind-to-x 파이프라인 비용 SQLite 영속화.

    Thread-safe (threading.Lock 사용).
    스키마 마이그레이션은 _init_db()에서 CREATE IF NOT EXISTS 방식으로 처리.
    """

    def __init__(self, db_path: str | Path | None = None):
        self.db_path = Path(db_path) if db_path else _DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_db()

    @contextmanager
    def _conn(self):
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS daily_text_costs (
                    id             INTEGER PRIMARY KEY AUTOINCREMENT,
                    recorded_at    TEXT    NOT NULL DEFAULT (datetime('now')),
                    date           TEXT    NOT NULL,
                    provider       TEXT    NOT NULL,
                    tokens_input   INTEGER DEFAULT 0,
                    tokens_output  INTEGER DEFAULT 0,
                    usd_estimated  REAL    DEFAULT 0.0
                );

                CREATE TABLE IF NOT EXISTS daily_image_costs (
                    id             INTEGER PRIMARY KEY AUTOINCREMENT,
                    recorded_at    TEXT    NOT NULL DEFAULT (datetime('now')),
                    date           TEXT    NOT NULL,
                    provider       TEXT    NOT NULL,
                    image_count    INTEGER DEFAULT 0,
                    usd_estimated  REAL    DEFAULT 0.0
                );

                CREATE TABLE IF NOT EXISTS draft_analytics (
                    id             INTEGER PRIMARY KEY AUTOINCREMENT,
                    recorded_at    TEXT    NOT NULL DEFAULT (datetime('now')),
                    date           TEXT    NOT NULL,
                    content_url    TEXT    DEFAULT '',
                    notion_page_id TEXT    DEFAULT '',
                    source         TEXT    DEFAULT '',
                    topic_cluster  TEXT    DEFAULT '',
                    hook_type      TEXT    DEFAULT '',
                    emotion_axis   TEXT    DEFAULT '',
                    draft_style    TEXT    DEFAULT '',
                    provider_used  TEXT    DEFAULT '',
                    final_rank_score REAL  DEFAULT 0.0,
                    published      INTEGER DEFAULT 0,
                    published_at   TEXT    DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS provider_failures (
                    provider       TEXT    PRIMARY KEY,
                    fail_count     INTEGER DEFAULT 0,
                    last_fail_at   TEXT    NOT NULL DEFAULT (datetime('now')),
                    skip_until     TEXT    DEFAULT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_text_date  ON daily_text_costs(date);
                CREATE INDEX IF NOT EXISTS idx_image_date ON daily_image_costs(date);
                CREATE INDEX IF NOT EXISTS idx_draft_date ON draft_analytics(date);
                CREATE INDEX IF NOT EXISTS idx_draft_content_url ON draft_analytics(content_url);
                CREATE INDEX IF NOT EXISTS idx_draft_page_id ON draft_analytics(notion_page_id);
            """)
            self._ensure_column(conn, "draft_analytics", "content_url", "TEXT DEFAULT ''")
            self._ensure_column(conn, "draft_analytics", "notion_page_id", "TEXT DEFAULT ''")
            self._ensure_column(conn, "draft_analytics", "published_at", "TEXT DEFAULT ''")
            self._ensure_column(conn, "draft_analytics", "hook_score", "REAL DEFAULT 0.0")
            self._ensure_column(conn, "draft_analytics", "virality_score", "REAL DEFAULT 0.0")
            self._ensure_column(conn, "draft_analytics", "fit_score", "REAL DEFAULT 0.0")
            # Phase 5: YouTube 성과 지표 (연속 ML 타겟)
            self._ensure_column(conn, "draft_analytics", "yt_views", "INTEGER DEFAULT 0")
            self._ensure_column(conn, "draft_analytics", "engagement_rate", "REAL DEFAULT 0.0")
            self._ensure_column(conn, "draft_analytics", "impression_count", "INTEGER DEFAULT 0")

    @staticmethod
    def _ensure_column(conn: sqlite3.Connection, table_name: str, column_name: str, ddl: str) -> None:
        columns = {
            row["name"]
            for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        }
        if column_name not in columns:
            conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {ddl}")

    # ── Write helpers ────────────────────────────────────────────────

    def record_text_cost(
        self,
        provider: str,
        tokens_input: int = 0,
        tokens_output: int = 0,
        usd: float = 0.0,
    ) -> None:
        today = date.today().isoformat()
        try:
            with self._conn() as conn:
                conn.execute(
                    """INSERT INTO daily_text_costs
                       (date, provider, tokens_input, tokens_output, usd_estimated)
                       VALUES (?, ?, ?, ?, ?)""",
                    (today, provider, int(tokens_input), int(tokens_output), float(usd)),
                )
        except Exception as exc:
            logger.warning("CostDB: failed to record text cost: %s", exc)

    def record_image_cost(
        self,
        provider: str,
        image_count: int = 1,
        usd: float = 0.0,
    ) -> None:
        today = date.today().isoformat()
        try:
            with self._conn() as conn:
                conn.execute(
                    """INSERT INTO daily_image_costs
                       (date, provider, image_count, usd_estimated)
                       VALUES (?, ?, ?, ?)""",
                    (today, provider, int(image_count), float(usd)),
                )
        except Exception as exc:
            logger.warning("CostDB: failed to record image cost: %s", exc)

    def record_draft(
        self,
        *,
        source: str = "",
        topic_cluster: str = "",
        hook_type: str = "",
        emotion_axis: str = "",
        draft_style: str = "",
        provider_used: str = "",
        final_rank_score: float = 0.0,
        published: bool = False,
        content_url: str = "",
        notion_page_id: str = "",
    ) -> None:
        today = date.today().isoformat()
        try:
            with self._conn() as conn:
                updated = False
                published_flag = int(published)
                published_at = today if published else ""

                if content_url:
                    cursor = conn.execute(
                        """
                        UPDATE draft_analytics
                           SET date = ?,
                               notion_page_id = CASE WHEN ? != '' THEN ? ELSE notion_page_id END,
                               source = ?,
                               topic_cluster = ?,
                               hook_type = ?,
                               emotion_axis = ?,
                               draft_style = ?,
                               provider_used = CASE WHEN ? != '' THEN ? ELSE provider_used END,
                               final_rank_score = ?,
                               published = CASE WHEN ? = 1 THEN 1 ELSE published END,
                               published_at = CASE
                                   WHEN ? = 1 THEN ?
                                   ELSE published_at
                               END
                         WHERE content_url = ?
                        """,
                        (
                            today,
                            notion_page_id,
                            notion_page_id,
                            source,
                            topic_cluster,
                            hook_type,
                            emotion_axis,
                            draft_style,
                            provider_used,
                            provider_used,
                            float(final_rank_score),
                            published_flag,
                            published_flag,
                            published_at,
                            content_url,
                        ),
                    )
                    updated = cursor.rowcount > 0

                if not updated and notion_page_id:
                    cursor = conn.execute(
                        """
                        UPDATE draft_analytics
                           SET date = ?,
                               content_url = CASE WHEN ? != '' THEN ? ELSE content_url END,
                               source = ?,
                               topic_cluster = ?,
                               hook_type = ?,
                               emotion_axis = ?,
                               draft_style = ?,
                               provider_used = CASE WHEN ? != '' THEN ? ELSE provider_used END,
                               final_rank_score = ?,
                               published = CASE WHEN ? = 1 THEN 1 ELSE published END,
                               published_at = CASE
                                   WHEN ? = 1 THEN ?
                                   ELSE published_at
                               END
                         WHERE notion_page_id = ?
                        """,
                        (
                            today,
                            content_url,
                            content_url,
                            source,
                            topic_cluster,
                            hook_type,
                            emotion_axis,
                            draft_style,
                            provider_used,
                            provider_used,
                            float(final_rank_score),
                            published_flag,
                            published_flag,
                            published_at,
                            notion_page_id,
                        ),
                    )
                    updated = cursor.rowcount > 0

                if not updated:
                    conn.execute(
                        """INSERT INTO draft_analytics
                           (date, content_url, notion_page_id, source, topic_cluster, hook_type,
                            emotion_axis, draft_style, provider_used, final_rank_score,
                            published, published_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            today,
                            content_url,
                            notion_page_id,
                            source,
                            topic_cluster,
                            hook_type,
                            emotion_axis,
                            draft_style,
                            provider_used,
                            float(final_rank_score),
                            published_flag,
                            published_at,
                        ),
                    )
        except Exception as exc:
            logger.warning("CostDB: failed to record draft: %s", exc)

    # ── Read helpers ─────────────────────────────────────────────────

    def get_today_summary(self) -> dict[str, Any]:
        """오늘 비용 요약. Streamlit 대시보드에서 사용."""
        today = date.today().isoformat()
        try:
            with self._conn() as conn:
                text = conn.execute(
                    """SELECT SUM(usd_estimated) as total_usd,
                              SUM(tokens_input) as total_in,
                              SUM(tokens_output) as total_out,
                              COUNT(*) as calls
                       FROM daily_text_costs WHERE date = ?""",
                    (today,),
                ).fetchone()

                image = conn.execute(
                    """SELECT SUM(usd_estimated) as total_usd,
                              SUM(image_count) as total_images
                       FROM daily_image_costs WHERE date = ?""",
                    (today,),
                ).fetchone()

                providers = conn.execute(
                    """SELECT provider,
                              SUM(tokens_input) as ti,
                              SUM(tokens_output) as to_,
                              SUM(usd_estimated) as usd,
                              COUNT(*) as calls
                       FROM daily_text_costs WHERE date = ?
                       GROUP BY provider ORDER BY usd DESC""",
                    (today,),
                ).fetchall()

                gemini_images = conn.execute(
                    """SELECT SUM(image_count) as cnt FROM daily_image_costs
                       WHERE date = ? AND provider = 'gemini'""",
                    (today,),
                ).fetchone()

            text_usd = float(text["total_usd"] or 0)
            image_usd = float(image["total_usd"] or 0) if image else 0.0
            gemini_count = int(gemini_images["cnt"] or 0) if gemini_images else 0
            return {
                "date": today,
                "text_usd": text_usd,
                "image_usd": image_usd,
                "total_usd": text_usd + image_usd,
                "total_text_calls": int(text["calls"] or 0),
                "total_images": int(image["total_images"] or 0) if image else 0,
                "gemini_image_count": gemini_count,
                "gemini_image_limit": GEMINI_IMAGE_DAILY_LIMIT,
                "gemini_rpd_pct": round(gemini_count / GEMINI_IMAGE_DAILY_LIMIT * 100, 1),
                "providers": [
                    {
                        "provider": row["provider"],
                        "calls": row["calls"],
                        "tokens_input": int(row["ti"] or 0),
                        "tokens_output": int(row["to_"] or 0),
                        "usd": float(row["usd"] or 0),
                    }
                    for row in providers
                ],
            }
        except Exception as exc:
            logger.warning("CostDB: failed to read today summary: %s", exc)
            return {
                "date": today, "text_usd": 0.0, "image_usd": 0.0, "total_usd": 0.0,
                "total_text_calls": 0, "total_images": 0, "gemini_image_count": 0,
                "gemini_image_limit": GEMINI_IMAGE_DAILY_LIMIT, "gemini_rpd_pct": 0.0,
                "providers": [],
            }

    def get_daily_trend(self, days: int = 30) -> list[dict[str, Any]]:
        """최근 N일 일별 비용 추세 (텍스트 + 이미지 합산)."""
        cutoff = (date.today() - timedelta(days=days)).isoformat()
        try:
            with self._conn() as conn:
                text_rows = conn.execute(
                    """SELECT date,
                              SUM(usd_estimated) as usd,
                              SUM(tokens_input + tokens_output) as tokens,
                              COUNT(*) as calls
                       FROM daily_text_costs WHERE date >= ?
                       GROUP BY date ORDER BY date""",
                    (cutoff,),
                ).fetchall()

                image_rows = conn.execute(
                    """SELECT date, SUM(usd_estimated) as usd, SUM(image_count) as cnt
                       FROM daily_image_costs WHERE date >= ?
                       GROUP BY date""",
                    (cutoff,),
                ).fetchall()

            img_by_date = {
                r["date"]: (float(r["usd"] or 0), int(r["cnt"] or 0))
                for r in image_rows
            }
            result = []
            for row in text_rows:
                d = row["date"]
                img_usd, img_cnt = img_by_date.get(d, (0.0, 0))
                result.append({
                    "date": d,
                    "text_usd": float(row["usd"] or 0),
                    "image_usd": img_usd,
                    "total_usd": float(row["usd"] or 0) + img_usd,
                    "tokens": int(row["tokens"] or 0),
                    "calls": int(row["calls"] or 0),
                    "images": img_cnt,
                })
            return result
        except Exception as exc:
            logger.warning("CostDB: failed to read daily trend: %s", exc)
            return []

    def get_draft_style_performance(self, days: int = 30) -> list[dict[str, Any]]:
        """드래프트 스타일별 사용 빈도 (A/B 분석 기반)."""
        cutoff = (date.today() - timedelta(days=days)).isoformat()
        try:
            with self._conn() as conn:
                rows = conn.execute(
                    """SELECT draft_style,
                              COUNT(*) as total,
                              AVG(final_rank_score) as avg_score,
                              SUM(published) as published_cnt
                       FROM draft_analytics WHERE date >= ?
                       GROUP BY draft_style ORDER BY total DESC""",
                    (cutoff,),
                ).fetchall()
            return [
                {
                    "draft_style": row["draft_style"],
                    "total": row["total"],
                    "avg_score": round(float(row["avg_score"] or 0), 2),
                    "published_cnt": int(row["published_cnt"] or 0),
                }
                for row in rows
            ]
        except Exception as exc:
            logger.warning("CostDB: failed to read draft performance: %s", exc)
            return []

    def is_daily_budget_exceeded(self, limit_usd: float = 3.0) -> bool:
        return self.get_today_summary()["total_usd"] >= limit_usd

    def get_gemini_image_count_today(self) -> int:
        return self.get_today_summary()["gemini_image_count"]

    # ── Provider failure persistence ──────────────────────────────────

    def record_provider_failure(self, provider: str, skip_hours: float = 24.0) -> None:
        """비복구 불가 에러 발생 시 provider 실패 이력 기록 + skip_until 설정."""
        from datetime import datetime as _dt
        now_iso = _dt.now(date.__class__.__mro__[-1]).isoformat()  # fallback
        try:
            from datetime import datetime as _dt2, timezone as _tz
            now_iso = _dt2.now(_tz.utc).isoformat()
            skip_iso = (_dt2.now(_tz.utc) + timedelta(hours=skip_hours)).isoformat()
            with self._conn() as conn:
                conn.execute(
                    """INSERT INTO provider_failures (provider, fail_count, last_fail_at, skip_until)
                       VALUES (?, 1, ?, ?)
                       ON CONFLICT(provider) DO UPDATE SET
                           fail_count = fail_count + 1,
                           last_fail_at = excluded.last_fail_at,
                           skip_until = excluded.skip_until""",
                    (provider, now_iso, skip_iso),
                )
        except Exception as exc:
            logger.warning("CostDB: failed to record provider failure: %s", exc)

    def get_skipped_providers(self) -> set[str]:
        """현재 skip_until이 아직 유효한 provider 집합 반환."""
        try:
            from datetime import datetime as _dt, timezone as _tz
            now_iso = _dt.now(_tz.utc).isoformat()
            with self._conn() as conn:
                rows = conn.execute(
                    "SELECT provider FROM provider_failures WHERE skip_until > ?",
                    (now_iso,),
                ).fetchall()
            return {row["provider"] for row in rows}
        except Exception as exc:
            logger.warning("CostDB: failed to read skipped providers: %s", exc)
            return set()

    def clear_provider_failure(self, provider: str) -> None:
        """provider 실패 이력 초기화 (성공 후 호출)."""
        try:
            with self._conn() as conn:
                conn.execute(
                    "UPDATE provider_failures SET fail_count = 0, skip_until = NULL WHERE provider = ?",
                    (provider,),
                )
        except Exception as exc:
            logger.warning("CostDB: failed to clear provider failure: %s", exc)

    def record_provider_success(self, provider: str) -> None:
        """프로바이더 성공 기록 — 실패 이력 초기화, circuit 닫힘."""
        self.clear_provider_failure(provider)
        logger.debug("CostDB: provider '%s' circuit CLOSED (success)", provider)

    def get_circuit_skip_hours(self, provider: str) -> float:
        """Circuit Breaker: fail_count 기반 지수적 skip 시간(시간) 계산.

        fail_count 1 → 1h, 2 → 4h, 3 → 12h, 4 → 24h, 5+ → 72h
        """
        try:
            with self._conn() as conn:
                row = conn.execute(
                    "SELECT fail_count FROM provider_failures WHERE provider = ?",
                    (provider,),
                ).fetchone()
            fail_count = int(row["fail_count"] if row else 0)
        except Exception:
            fail_count = 0

        # 지수적 백오프: 1h, 4h, 12h, 24h, 72h (최대 72h)
        thresholds = [1.0, 4.0, 12.0, 24.0, 72.0]
        idx = min(fail_count, len(thresholds) - 1)
        return thresholds[idx]

    # ── Draft self-scoring ────────────────────────────────────────────

    def update_draft_scores(
        self,
        *,
        content_url: str = "",
        notion_page_id: str = "",
        hook_score: float = 0.0,
        virality_score: float = 0.0,
        fit_score: float = 0.0,
    ) -> None:
        """LLM 자가 채점 결과를 draft_analytics에 업데이트."""
        try:
            with self._conn() as conn:
                updated = False
                if content_url:
                    cursor = conn.execute(
                        """UPDATE draft_analytics
                              SET hook_score = ?, virality_score = ?, fit_score = ?
                            WHERE content_url = ?""",
                        (hook_score, virality_score, fit_score, content_url),
                    )
                    updated = cursor.rowcount > 0
                if not updated and notion_page_id:
                    conn.execute(
                        """UPDATE draft_analytics
                              SET hook_score = ?, virality_score = ?, fit_score = ?
                            WHERE notion_page_id = ?""",
                        (hook_score, virality_score, fit_score, notion_page_id),
                    )
        except Exception as exc:
            logger.warning("CostDB: failed to update draft scores: %s", exc)

    def update_draft_view_stats(
        self,
        *,
        content_url: str = "",
        notion_page_id: str = "",
        yt_views: int = 0,
        engagement_rate: float = 0.0,
        impression_count: int = 0,
    ) -> None:
        """YouTube 성과 지표를 draft_analytics에 업데이트 (Phase 5 ML 연속 타겟용)."""
        try:
            with self._conn() as conn:
                updated = False
                if content_url:
                    cursor = conn.execute(
                        """UPDATE draft_analytics
                              SET yt_views = ?, engagement_rate = ?, impression_count = ?
                            WHERE content_url = ?""",
                        (int(yt_views), float(engagement_rate), int(impression_count), content_url),
                    )
                    updated = cursor.rowcount > 0
                if not updated and notion_page_id:
                    conn.execute(
                        """UPDATE draft_analytics
                              SET yt_views = ?, engagement_rate = ?, impression_count = ?
                            WHERE notion_page_id = ?""",
                        (int(yt_views), float(engagement_rate), int(impression_count), notion_page_id),
                    )
        except Exception as exc:
            logger.warning("CostDB: failed to update draft view stats: %s", exc)

    def get_best_draft_style_for_cluster(
        self,
        topic_cluster: str,
        min_samples: int = 5,
        days: int = 30,
    ) -> str | None:
        """토픽 클러스터별 최고 성과 draft_style 반환.

        final_rank_score 평균이 가장 높은 스타일을 반환.
        min_samples 미만 데이터가 있으면 None 반환.
        """
        cutoff = (date.today() - timedelta(days=days)).isoformat()
        try:
            with self._conn() as conn:
                rows = conn.execute(
                    """SELECT draft_style,
                              COUNT(*) as total,
                              AVG(final_rank_score) as avg_score
                       FROM draft_analytics
                       WHERE date >= ? AND topic_cluster = ? AND draft_style != ''
                       GROUP BY draft_style
                       HAVING COUNT(*) >= ?
                       ORDER BY avg_score DESC
                       LIMIT 1""",
                    (cutoff, topic_cluster, min_samples),
                ).fetchall()
            if rows:
                return rows[0]["draft_style"]
            return None
        except Exception as exc:
            logger.warning("CostDB: failed to get best draft style: %s", exc)
            return None

    # ── 포스트별 비용 추적 ─────────────────────────────────────────────

    def get_cost_per_post(self, days: int = 30) -> dict[str, float]:
        """최근 N일간 포스트 1건당 평균 비용 계산.

        Returns:
            {"avg_cost_per_post": float, "total_cost": float, "total_posts": int}
        """
        cutoff = (date.today() - timedelta(days=days)).isoformat()
        try:
            with self._conn() as conn:
                cost_row = conn.execute(
                    """SELECT COALESCE(SUM(usd_estimated), 0) as total_usd
                       FROM daily_text_costs WHERE date >= ?""",
                    (cutoff,),
                ).fetchone()
                img_row = conn.execute(
                    """SELECT COALESCE(SUM(usd_estimated), 0) as total_usd
                       FROM daily_image_costs WHERE date >= ?""",
                    (cutoff,),
                ).fetchone()
                post_row = conn.execute(
                    """SELECT COUNT(*) as cnt FROM draft_analytics WHERE date >= ?""",
                    (cutoff,),
                ).fetchone()

            total_cost = float(cost_row["total_usd"]) + float(img_row["total_usd"])
            total_posts = int(post_row["cnt"]) if post_row else 0
            avg = total_cost / total_posts if total_posts > 0 else 0.0
            return {
                "avg_cost_per_post": round(avg, 5),
                "total_cost": round(total_cost, 5),
                "total_posts": total_posts,
            }
        except Exception as exc:
            logger.warning("CostDB: failed to calc cost per post: %s", exc)
            return {"avg_cost_per_post": 0.0, "total_cost": 0.0, "total_posts": 0}

    # ── Phase 3-C: DB 아카이빙 ─────────────────────────────────────────

    def archive_old_data(self, days: int = 90) -> dict[str, int]:
        """N일 이전 데이터를 아카이브 DB로 이동. 반환: {table: 이동한 행 수}

        아카이브 파일: .tmp/btx_costs_archive_YYYY-Qn.db
        """
        from datetime import datetime as _dt

        cutoff = (date.today() - timedelta(days=days)).isoformat()
        # 분기별 아카이브 파일 이름
        now = _dt.now()
        quarter = (now.month - 1) // 3 + 1
        archive_path = self.db_path.parent / f"btx_costs_archive_{now.year}-Q{quarter}.db"

        tables = ["daily_text_costs", "daily_image_costs", "draft_analytics"]
        result: dict[str, int] = {}

        try:
            with self._conn() as src_conn:
                arch_conn = sqlite3.connect(str(archive_path))
                arch_conn.execute("PRAGMA journal_mode=WAL")
                try:
                    for table in tables:
                        # 아카이브 DB에 테이블 생성 (없으면)
                        schema_row = src_conn.execute(
                            "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
                            (table,),
                        ).fetchone()
                        if schema_row and schema_row[0]:
                            arch_conn.execute(schema_row[0])

                        # 이전 데이터 복사
                        old_rows = src_conn.execute(
                            f"SELECT * FROM {table} WHERE date < ?", (cutoff,)
                        ).fetchall()
                        if not old_rows:
                            result[table] = 0
                            continue

                        col_count = len(old_rows[0])
                        placeholders = ",".join(["?"] * col_count)
                        arch_conn.executemany(
                            f"INSERT OR IGNORE INTO {table} VALUES ({placeholders})",
                            [tuple(r) for r in old_rows],
                        )
                        arch_conn.commit()

                        # 원본에서 삭제
                        deleted = src_conn.execute(
                            f"DELETE FROM {table} WHERE date < ?", (cutoff,)
                        ).rowcount
                        result[table] = deleted
                        logger.info(
                            "CostDB: archived %d rows from %s (cutoff=%s) → %s",
                            deleted, table, cutoff, archive_path.name,
                        )
                finally:
                    arch_conn.close()
        except Exception as exc:
            logger.warning("CostDB: archive_old_data failed: %s", exc)
            result = {t: 0 for t in tables}

        return result


# ── 모듈 레벨 싱글톤 (Phase 2-E) ──────────────────────────────────────

_db_singleton: "CostDatabase | None" = None
_db_singleton_lock = threading.Lock()


def get_cost_db(db_path: "str | Path | None" = None) -> "CostDatabase":
    """모듈 레벨 CostDatabase 싱글톤 반환 (thread-safe 지연 초기화).

    동일 프로세스에서 매번 CostDatabase()를 생성하는 대신 이 함수를 사용하세요.
    """
    global _db_singleton
    if _db_singleton is None:
        with _db_singleton_lock:
            if _db_singleton is None:
                _db_singleton = CostDatabase(db_path)
    return _db_singleton
