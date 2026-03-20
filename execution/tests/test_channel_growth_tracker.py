"""T4-1: channel_growth_tracker 단위 테스트."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest


# ── DB 격리를 위한 fixture ──────────────────────────────────
@pytest.fixture(autouse=True)
def _isolated_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """각 테스트마다 독립된 DB 경로 사용."""
    monkeypatch.setattr(
        "execution.channel_growth_tracker.DB_PATH",
        tmp_path / "test_channel_growth.db",
    )


# ── import after monkeypatch setup ──────────────────────────
from execution.channel_growth_tracker import (  # noqa: E402
    add_channel,
    calculate_growth_rate,
    get_channel_comparison,
    get_channels,
    get_growth_history,
    get_latest_snapshot,
    init_db,
    _save_snapshot,
)


def test_init_db_creates_tables(tmp_path: Path) -> None:
    init_db()
    from execution.channel_growth_tracker import DB_PATH

    conn = sqlite3.connect(str(DB_PATH))
    tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    conn.close()
    assert "channels" in tables
    assert "growth_snapshots" in tables


def test_add_channel_and_get() -> None:
    init_db()
    row_id = add_channel("UC_test_123", "테스트 채널")
    assert row_id > 0

    channels = get_channels()
    assert len(channels) == 1
    assert channels[0]["channel_id"] == "UC_test_123"
    assert channels[0]["name"] == "테스트 채널"


def test_add_channel_duplicate_returns_existing() -> None:
    init_db()
    id1 = add_channel("UC_dup", "채널A")
    id2 = add_channel("UC_dup", "채널B")
    assert id1 == id2

    channels = get_channels()
    assert len(channels) == 1


def test_snapshot_save_and_retrieve() -> None:
    init_db()
    db_id = add_channel("UC_snap", "스냅샷 테스트")
    _save_snapshot(db_id, subscribers=1000, total_views=50000, video_count=100)

    latest = get_latest_snapshot(db_id)
    assert latest is not None
    assert latest["subscribers"] == 1000
    assert latest["total_views"] == 50000
    assert latest["video_count"] == 100


def test_growth_history_empty() -> None:
    init_db()
    db_id = add_channel("UC_empty", "빈 히스토리")
    history = get_growth_history(db_id, days=30)
    assert history == []


def test_growth_history_returns_data() -> None:
    init_db()
    db_id = add_channel("UC_hist", "히스토리 테스트")
    _save_snapshot(db_id, 100, 5000, 10)
    _save_snapshot(db_id, 120, 6000, 12)

    history = get_growth_history(db_id, days=30)
    assert len(history) == 2
    assert history[0]["subscribers"] == 100
    assert history[1]["subscribers"] == 120


def test_calculate_growth_rate_insufficient_data() -> None:
    init_db()
    db_id = add_channel("UC_rate1", "단일 스냅샷")
    _save_snapshot(db_id, 500, 10000, 20)

    rate = calculate_growth_rate(db_id, days=7)
    assert rate["subscriber_growth_rate"] == 0.0
    assert rate["view_growth_rate"] == 0.0


def test_calculate_growth_rate_with_data() -> None:
    init_db()
    db_id = add_channel("UC_rate2", "성장률 테스트")
    _save_snapshot(db_id, 1000, 50000, 50)
    _save_snapshot(db_id, 1100, 55000, 52)

    rate = calculate_growth_rate(db_id, days=7)
    assert rate["subscriber_growth_rate"] == 10.0  # (1100-1000)/1000 * 100
    assert rate["view_growth_rate"] == 10.0


def test_channel_comparison_empty() -> None:
    init_db()
    comparison = get_channel_comparison()
    assert comparison == []


def test_channel_comparison_with_data() -> None:
    init_db()
    id1 = add_channel("UC_cmp1", "채널1")
    id2 = add_channel("UC_cmp2", "채널2")
    _save_snapshot(id1, 500, 10000, 20)
    _save_snapshot(id2, 1000, 50000, 100)

    comparison = get_channel_comparison()
    assert len(comparison) == 2
    names = {ch["name"] for ch in comparison}
    assert "채널1" in names
    assert "채널2" in names
