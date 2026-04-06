"""Thompson Sampling multi-armed bandit for draft style selection (Phase 4-A).

Maintains Beta(α, β) distributions per (topic_cluster, draft_style) arm.
State is persisted to .tmp/btx_costs.db → bandit_arms table, so learning
survives process restarts.

Usage:
    bandit = get_style_bandit()
    style = bandit.select_style("연봉", ["공감형", "논쟁형", "정보전달형"])
    # ... generate draft, measure engagement ...
    bandit.update("연봉", style, reward=0.8)  # reward: 0.0–1.0

Reward conventions:
    1.0  = published + high engagement (RT/likes > threshold)
    0.7  = published, average engagement
    0.3  = generated but not published (filtered out)
    0.0  = rejected by quality gate / provider error
"""

from __future__ import annotations

import logging
import random
import threading
from typing import Sequence

logger = logging.getLogger(__name__)

# Jeffreys-like prior: β(1, 1) = uniform. Raises to β(1.5, 1.5) for slight
# optimism bias — prevents permanently cold styles from being ignored.
_PRIOR_ALPHA = 1.0
_PRIOR_BETA = 1.0

_DEFAULT_STYLES = ["공감형", "논쟁형", "정보전달형", "한줄팩폭형"]


def _beta_sample(alpha: float, beta: float) -> float:
    """Sample from Beta(alpha, beta). Clamps params to avoid degenerate dist."""
    return random.betavariate(max(alpha, 1e-6), max(beta, 1e-6))


class StyleBandit:
    """Thread-safe Thompson Sampling bandit backed by SQLite.

    Each arm is identified by (topic_cluster, draft_style).
    Unknown arms are initialized with the flat prior Beta(α₀, β₀).
    """

    def __init__(self, db=None):
        self._db = db  # CostDatabase instance — injected or lazy-loaded
        self._lock = threading.Lock()
        self._table_ready = False
        self._ensure_table()

    # ── Private helpers ──────────────────────────────────────────────

    def _get_db(self):
        if self._db is None:
            from pipeline.cost_db import get_cost_db

            self._db = get_cost_db()
        return self._db

    def _ensure_table(self) -> None:
        if self._table_ready:
            return
        try:
            db = self._get_db()
            with db._conn() as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS bandit_arms (
                        topic_cluster TEXT NOT NULL,
                        draft_style   TEXT NOT NULL,
                        alpha         REAL NOT NULL DEFAULT 1.0,
                        beta          REAL NOT NULL DEFAULT 1.0,
                        total_trials  INTEGER NOT NULL DEFAULT 0,
                        last_updated  TEXT NOT NULL DEFAULT (datetime('now')),
                        PRIMARY KEY (topic_cluster, draft_style)
                    )
                    """
                )
            self._table_ready = True
        except Exception as exc:
            logger.warning("StyleBandit: failed to create bandit_arms table: %s", exc)

    def _get_arms(self, topic_cluster: str, styles: Sequence[str]) -> dict[str, tuple[float, float]]:
        """Return {style: (alpha, beta)} for given styles from DB."""
        if not styles:
            return {}
        try:
            db = self._get_db()
            placeholders = ",".join("?" * len(styles))
            with db._conn() as conn:
                rows = conn.execute(
                    f"""SELECT draft_style, alpha, beta
                          FROM bandit_arms
                         WHERE topic_cluster = ? AND draft_style IN ({placeholders})""",
                    (topic_cluster, *styles),
                ).fetchall()
            return {row["draft_style"]: (float(row["alpha"]), float(row["beta"])) for row in rows}
        except Exception as exc:
            logger.warning("StyleBandit._get_arms failed: %s", exc)
            return {}

    # ── Public API ───────────────────────────────────────────────────

    def select_style(
        self,
        topic_cluster: str,
        available_styles: Sequence[str] | None = None,
    ) -> str:
        """Thompson Sampling: sample Beta(α,β) per arm, return argmax style.

        Falls back to uniform random when only one style or on error.
        """
        styles = list(available_styles if available_styles is not None else _DEFAULT_STYLES)
        if not styles:
            return "공감형"
        if len(styles) == 1:
            return styles[0]

        try:
            arms = self._get_arms(topic_cluster, styles)
            samples = {
                style: _beta_sample(
                    arms.get(style, (_PRIOR_ALPHA, _PRIOR_BETA))[0],
                    arms.get(style, (_PRIOR_ALPHA, _PRIOR_BETA))[1],
                )
                for style in styles
            }
            selected = max(samples, key=lambda s: samples[s])
            logger.debug(
                "StyleBandit[%s]: selected=%s, samples=%s",
                topic_cluster,
                selected,
                {k: round(_v, 3) for k, _v in samples.items()},
            )
            return selected
        except Exception as exc:
            logger.warning("StyleBandit.select_style failed: %s. Falling back to random.", exc)
            return random.choice(styles)

    def update(self, topic_cluster: str, style: str, reward: float) -> None:
        """Update Beta(α, β) for arm after observing a reward in [0, 1].

        α tracks positive outcomes (reward proportional update).
        β tracks negative outcomes ((1-reward) proportional update).
        """
        reward = max(0.0, min(1.0, float(reward)))
        alpha_inc = reward
        beta_inc = 1.0 - reward

        try:
            db = self._get_db()
            with db._conn() as conn:
                conn.execute(
                    """
                    INSERT INTO bandit_arms
                        (topic_cluster, draft_style, alpha, beta, total_trials, last_updated)
                    VALUES (?, ?, ?, ?, 1, datetime('now'))
                    ON CONFLICT(topic_cluster, draft_style) DO UPDATE SET
                        alpha        = alpha + ?,
                        beta         = beta + ?,
                        total_trials = total_trials + 1,
                        last_updated = datetime('now')
                    """,
                    (
                        topic_cluster,
                        style,
                        _PRIOR_ALPHA + alpha_inc,
                        _PRIOR_BETA + beta_inc,
                        alpha_inc,
                        beta_inc,
                    ),
                )
            logger.debug(
                "StyleBandit.update[%s/%s]: reward=%.2f α+=%.2f β+=%.2f",
                topic_cluster,
                style,
                reward,
                alpha_inc,
                beta_inc,
            )
        except Exception as exc:
            logger.warning("StyleBandit.update failed: %s", exc)

    def get_arm_stats(self, topic_cluster: str | None = None) -> list[dict]:
        """Return arm statistics for inspection and dashboard display."""
        try:
            db = self._get_db()
            with db._conn() as conn:
                if topic_cluster:
                    rows = conn.execute(
                        """SELECT topic_cluster, draft_style, alpha, beta,
                                  total_trials, last_updated
                             FROM bandit_arms
                            WHERE topic_cluster = ?
                            ORDER BY alpha / (alpha + beta) DESC""",
                        (topic_cluster,),
                    ).fetchall()
                else:
                    rows = conn.execute(
                        """SELECT topic_cluster, draft_style, alpha, beta,
                                  total_trials, last_updated
                             FROM bandit_arms
                            ORDER BY topic_cluster, alpha / (alpha + beta) DESC"""
                    ).fetchall()
            return [
                {
                    "topic_cluster": row["topic_cluster"],
                    "draft_style": row["draft_style"],
                    "alpha": round(float(row["alpha"]), 3),
                    "beta": round(float(row["beta"]), 3),
                    "mean_reward": round(float(row["alpha"]) / (float(row["alpha"]) + float(row["beta"])), 3),
                    "total_trials": int(row["total_trials"]),
                    "last_updated": row["last_updated"],
                }
                for row in rows
            ]
        except Exception as exc:
            logger.warning("StyleBandit.get_arm_stats failed: %s", exc)
            return []


# ── Module-level singleton ───────────────────────────────────────────

_bandit: StyleBandit | None = None
_bandit_lock = threading.Lock()


def get_style_bandit() -> StyleBandit:
    """Thread-safe lazy singleton for StyleBandit."""
    global _bandit
    if _bandit is None:
        with _bandit_lock:
            if _bandit is None:
                _bandit = StyleBandit()
    return _bandit
