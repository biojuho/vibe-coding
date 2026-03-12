"""Phase 4-E: A/B style performance tracker.

Scans past job manifests to compute success rates per hook_pattern
and caption_combo. Provides weighted random selection for ScriptStep
and RenderStep to favor historically successful styles.

Includes a YouTube performance feedback loop via Thompson Sampling
(Beta distribution) backed by a SQLite database.

Usage:
    tracker = StyleTracker(output_dir)
    best_pattern = tracker.weighted_pick("hook_pattern", ["질문형", "충격형", "공감형"])

    # Record YouTube performance for a caption combo
    tracker.record_performance("my_channel", "bold_white", views=12000, likes=450)

    # Get best combo via Thompson Sampling
    best_combo = tracker.get_weighted_combo("my_channel")
"""
from __future__ import annotations

import json
import logging
import random
import sqlite3
import threading
from collections import Counter
from pathlib import Path
from typing import Sequence

logger = logging.getLogger(__name__)

_DB_INIT_SQL = """
CREATE TABLE IF NOT EXISTS combo_performance (
    channel     TEXT    NOT NULL,
    combo_name  TEXT    NOT NULL,
    views       INTEGER NOT NULL DEFAULT 0,
    likes       INTEGER NOT NULL DEFAULT 0,
    trials      INTEGER NOT NULL DEFAULT 0,
    successes   INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (channel, combo_name)
);
"""

# A video is considered "successful" if its like-rate >= this threshold.
_DEFAULT_SUCCESS_THRESHOLD = 0.03  # 3% like/view ratio


class StyleTracker:
    """Reads past manifests and computes style success rates.

    Also maintains a SQLite-backed Thompson Sampling model for
    YouTube performance feedback per caption combo.
    """

    def __init__(
        self,
        output_dir: Path,
        max_manifests: int = 200,
        db_path: Path | None = None,
        success_threshold: float = _DEFAULT_SUCCESS_THRESHOLD,
    ):
        self._output_dir = Path(output_dir)
        self._max_manifests = max_manifests
        self._stats: dict[str, Counter] = {}
        self._loaded = False

        # SQLite performance DB
        if db_path is None:
            db_path = Path(".tmp") / "style_performance.db"
        self._db_path = Path(db_path)
        self._success_threshold = success_threshold
        self._db_lock = threading.Lock()
        self._db_initialized = False

    # ------------------------------------------------------------------
    # SQLite helpers
    # ------------------------------------------------------------------

    def _ensure_db(self) -> None:
        """Create DB directory and table if needed (idempotent)."""
        if self._db_initialized:
            return
        with self._db_lock:
            if self._db_initialized:
                return
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            with self._get_conn() as conn:
                conn.executescript(_DB_INIT_SQL)
            self._db_initialized = True

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path), timeout=10)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.row_factory = sqlite3.Row
        return conn

    # ------------------------------------------------------------------
    # Manifest-based methods (unchanged API)
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        if not self._output_dir.exists():
            return
        manifests = sorted(
            self._output_dir.glob("*_manifest.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )[: self._max_manifests]

        for mf in manifests:
            try:
                data = json.loads(mf.read_text(encoding="utf-8"))
                status = data.get("status", "")
                ab_variant = data.get("ab_variant", {})
                if not ab_variant:
                    continue
                for key, value in ab_variant.items():
                    if key not in self._stats:
                        self._stats[key] = Counter()
                    if status == "success":
                        self._stats[key][str(value)] += 1
                    else:
                        # Track failures with negative weight
                        self._stats[key][str(value)] += 0
            except Exception:
                continue

        if self._stats:
            logger.debug(
                "StyleTracker loaded %d manifests, keys=%s",
                len(manifests),
                list(self._stats.keys()),
            )

    def get_success_counts(self, key: str) -> dict[str, int]:
        """Return {variant_name: success_count} for given A/B key."""
        self._load()
        return dict(self._stats.get(key, {}))

    def weighted_pick(self, key: str, candidates: Sequence[str], min_data: int = 5) -> str:
        """Select from candidates weighted by past success rate.

        Falls back to uniform random if insufficient data (<min_data total runs).
        """
        self._load()
        counts = self._stats.get(key, Counter())
        total = sum(counts.values())

        if total < min_data or not candidates:
            return random.choice(candidates) if candidates else ""

        # Build weights: success_count + 1 (Laplace smoothing)
        weights = [counts.get(str(c), 0) + 1 for c in candidates]
        return random.choices(candidates, weights=weights, k=1)[0]

    # ------------------------------------------------------------------
    # YouTube performance feedback loop
    # ------------------------------------------------------------------

    def record_performance(
        self,
        channel: str,
        combo_name: str,
        views: int,
        likes: int,
    ) -> None:
        """Record YouTube performance data for a caption combo.

        Each call counts as one trial. A trial is marked as a success
        if the like/view ratio meets the success_threshold.

        Args:
            channel: YouTube channel identifier.
            combo_name: Caption combo name (e.g. "bold_white").
            views: Number of views for the video.
            likes: Number of likes for the video.
        """
        self._ensure_db()

        is_success = (likes / views) >= self._success_threshold if views > 0 else False
        success_inc = 1 if is_success else 0

        with self._db_lock:
            with self._get_conn() as conn:
                conn.execute(
                    """
                    INSERT INTO combo_performance (channel, combo_name, views, likes, trials, successes)
                    VALUES (?, ?, ?, ?, 1, ?)
                    ON CONFLICT (channel, combo_name) DO UPDATE SET
                        views      = views + excluded.views,
                        likes      = likes + excluded.likes,
                        trials     = trials + 1,
                        successes  = successes + excluded.successes,
                        updated_at = datetime('now')
                    """,
                    (channel, combo_name, views, likes, success_inc),
                )

        logger.debug(
            "Recorded performance: channel=%s combo=%s views=%d likes=%d success=%s",
            channel,
            combo_name,
            views,
            likes,
            is_success,
        )

    def get_weighted_combo(self, channel: str) -> str:
        """Return the best-performing combo via Thompson Sampling.

        Draws a sample from Beta(successes + 1, failures + 1) for each
        combo and returns the one with the highest sample. Falls back
        to the manifest-based weighted_pick for "caption_combo" if no
        performance data exists for the channel.

        Args:
            channel: YouTube channel identifier.

        Returns:
            The combo name selected by Thompson Sampling, or an empty
            string if no combos are available at all.
        """
        self._ensure_db()

        rows: list[sqlite3.Row] = []
        with self._db_lock:
            with self._get_conn() as conn:
                rows = conn.execute(
                    """
                    SELECT combo_name, trials, successes
                    FROM combo_performance
                    WHERE channel = ?
                    """,
                    (channel,),
                ).fetchall()

        if not rows:
            # Fall back to manifest-based rotation
            self._load()
            combos = list(self._stats.get("caption_combo", {}).keys())
            if combos:
                return self.weighted_pick("caption_combo", combos)
            return ""

        # Thompson Sampling: sample from Beta(alpha, beta) for each arm
        best_combo = ""
        best_sample = -1.0
        for row in rows:
            alpha = row["successes"] + 1  # Laplace prior
            beta = (row["trials"] - row["successes"]) + 1
            sample = random.betavariate(alpha, beta)
            if sample > best_sample:
                best_sample = sample
                best_combo = row["combo_name"]

        logger.debug(
            "Thompson Sampling selected combo=%s for channel=%s (from %d arms)",
            best_combo,
            channel,
            len(rows),
        )
        return best_combo

    def get_performance_stats(self, channel: str) -> list[dict[str, int | str]]:
        """Return raw performance stats for a channel (for debugging/dashboards).

        Returns:
            List of dicts with keys: combo_name, views, likes, trials, successes.
        """
        self._ensure_db()

        with self._db_lock:
            with self._get_conn() as conn:
                rows = conn.execute(
                    """
                    SELECT combo_name, views, likes, trials, successes
                    FROM combo_performance
                    WHERE channel = ?
                    ORDER BY successes DESC, trials DESC
                    """,
                    (channel,),
                ).fetchall()

        return [dict(row) for row in rows]
