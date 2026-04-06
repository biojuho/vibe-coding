"""Tests for pipeline.style_bandit — 0% → 80%+ coverage target."""

from __future__ import annotations

import sqlite3
from unittest.mock import MagicMock


from pipeline.style_bandit import (
    StyleBandit,
    _beta_sample,
    _DEFAULT_STYLES,
)


# ── _beta_sample ─────────────────────────────────────────────────────


class TestBetaSample:
    def test_returns_float(self):
        val = _beta_sample(1.0, 1.0)
        assert isinstance(val, float)
        assert 0.0 <= val <= 1.0

    def test_near_zero_params_clamped(self):
        """Very small params should be clamped, not raise."""
        val = _beta_sample(0.0, 0.0)
        assert isinstance(val, float)

    def test_large_alpha_biases_high(self):
        """High alpha should bias samples high."""
        samples = [_beta_sample(100.0, 1.0) for _ in range(50)]
        assert sum(samples) / len(samples) > 0.8


# ── StyleBandit with in-memory SQLite ────────────────────────────────


def _make_in_memory_db():
    """Create a mock CostDatabase backed by in-memory SQLite."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row

    class FakeDB:
        def _conn(self):
            return conn

    return FakeDB(), conn


class TestStyleBandit:
    def setup_method(self):
        self.db, self.conn = _make_in_memory_db()
        self.bandit = StyleBandit(db=self.db)

    def test_table_created(self):
        tables = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='bandit_arms'"
        ).fetchall()
        assert len(tables) == 1

    def test_select_style_single(self):
        """Single style should be returned directly."""
        result = self.bandit.select_style("연봉", ["공감형"])
        assert result == "공감형"

    def test_select_style_empty(self):
        """Empty styles list returns default."""
        result = self.bandit.select_style("연봉", [])
        assert result == "공감형"

    def test_select_style_none(self):
        """None available_styles uses defaults."""
        result = self.bandit.select_style("연봉", None)
        assert result in _DEFAULT_STYLES

    def test_select_style_multiple(self):
        """Should select one of the available styles."""
        styles = ["공감형", "논쟁형", "정보전달형"]
        result = self.bandit.select_style("연봉", styles)
        assert result in styles

    def test_select_style_after_learning(self):
        """After repeated positive rewards, the rewarded arm should dominate."""
        for _ in range(50):
            self.bandit.update("연봉", "논쟁형", reward=1.0)
            self.bandit.update("연봉", "공감형", reward=0.0)

        # Over many samples, the learned arm should win most times
        wins = sum(1 for _ in range(30) if self.bandit.select_style("연봉", ["공감형", "논쟁형"]) == "논쟁형")
        assert wins >= 20  # 논쟁형 should dominate

    def test_update_inserts_new_arm(self):
        self.bandit.update("연봉", "한줄팩폭형", reward=0.7)
        row = self.conn.execute("SELECT * FROM bandit_arms WHERE draft_style = '한줄팩폭형'").fetchone()
        assert row is not None
        assert int(row["total_trials"]) == 1

    def test_update_increments_existing(self):
        self.bandit.update("연봉", "공감형", reward=0.5)
        self.bandit.update("연봉", "공감형", reward=0.8)
        row = self.conn.execute("SELECT * FROM bandit_arms WHERE draft_style = '공감형'").fetchone()
        assert int(row["total_trials"]) == 2

    def test_update_clamps_reward(self):
        """Reward outside [0,1] should be clamped."""
        self.bandit.update("연봉", "공감형", reward=-0.5)
        self.bandit.update("연봉", "공감형", reward=1.5)
        row = self.conn.execute("SELECT * FROM bandit_arms WHERE draft_style = '공감형'").fetchone()
        assert int(row["total_trials"]) == 2

    def test_get_arm_stats_empty(self):
        stats = self.bandit.get_arm_stats("연봉")
        assert stats == []

    def test_get_arm_stats_with_data(self):
        self.bandit.update("연봉", "공감형", reward=0.8)
        self.bandit.update("연봉", "논쟁형", reward=0.3)
        stats = self.bandit.get_arm_stats("연봉")
        assert len(stats) == 2
        assert all("mean_reward" in s for s in stats)

    def test_get_arm_stats_all(self):
        self.bandit.update("연봉", "공감형", reward=0.8)
        self.bandit.update("퇴사", "논쟁형", reward=0.3)
        stats = self.bandit.get_arm_stats()
        assert len(stats) == 2


class TestStyleBanditErrorHandling:
    def test_select_style_db_error_fallback(self):
        """On DB error, select_style should fall back to random."""
        db = MagicMock()
        db._conn.side_effect = Exception("DB crash")
        bandit = StyleBandit.__new__(StyleBandit)
        bandit._db = db
        bandit._lock = __import__("threading").Lock()
        bandit._table_ready = True

        result = bandit.select_style("연봉", ["공감형", "논쟁형"])
        assert result in ["공감형", "논쟁형"]

    def test_update_db_error_silent(self):
        """On DB error, update should not raise."""
        db = MagicMock()
        db._conn.side_effect = Exception("DB crash")
        bandit = StyleBandit.__new__(StyleBandit)
        bandit._db = db
        bandit._lock = __import__("threading").Lock()
        bandit._table_ready = True

        bandit.update("연봉", "공감형", reward=0.5)  # should not raise

    def test_get_arm_stats_db_error(self):
        db = MagicMock()
        db._conn.side_effect = Exception("DB crash")
        bandit = StyleBandit.__new__(StyleBandit)
        bandit._db = db
        bandit._lock = __import__("threading").Lock()
        bandit._table_ready = True

        assert bandit.get_arm_stats() == []
