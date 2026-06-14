"""tune_best_of_n_weight.py 단위 테스트.

DB 로딩(load_recent_rows)은 환경 의존적이라 모킹하고, 순수 분석/리포트 헬퍼만 검증한다.
"""

from __future__ import annotations

import math
import sqlite3
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

_BTX_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_BTX_ROOT))

from scripts.tune_best_of_n_weight import (  # noqa: E402  (sys.path 조작 후 import)
    build_report,
    correlate_axis,
    load_recent_rows,
    pearson,
    sweep_comment_weights,
)


def test_pearson_returns_none_for_insufficient_data():
    assert pearson([], []) is None
    assert pearson([1.0], [1.0]) is None
    assert pearson([1, 2, 3], [1, 2]) is None


def test_pearson_returns_one_for_perfectly_linear_data():
    xs = [1.0, 2.0, 3.0, 4.0]
    ys = [2.0, 4.0, 6.0, 8.0]
    r = pearson(xs, ys)
    assert r is not None
    assert math.isclose(r, 1.0, abs_tol=1e-9)


def test_pearson_returns_negative_for_anti_correlated():
    xs = [1.0, 2.0, 3.0, 4.0]
    ys = [4.0, 3.0, 2.0, 1.0]
    r = pearson(xs, ys)
    assert r is not None
    assert math.isclose(r, -1.0, abs_tol=1e-9)


def test_pearson_returns_none_when_variance_is_zero():
    assert pearson([5.0, 5.0, 5.0], [1.0, 2.0, 3.0]) is None


def test_correlate_axis_skips_double_zero_rows_and_garbage():
    rows = [
        {"hook_score": 0.0, "engagement_rate": 0.0},  # skipped (둘 다 0)
        {"hook_score": "garbage", "engagement_rate": 0.5},  # skipped
        {"hook_score": 0.4, "engagement_rate": 0.1},
        {"hook_score": 0.5, "engagement_rate": 0.2},
        {"hook_score": 0.7, "engagement_rate": 0.3},
    ]
    r, n = correlate_axis(rows, "hook_score", "engagement_rate")
    assert n == 3
    assert r is not None
    assert r > 0.9  # 거의 완벽한 양의 상관


def test_sweep_comment_weights_returns_best_pure_4axis_when_4axis_is_engagement():
    # avg 는 engagement_rate 와 anti-correlate(노이즈)지만 ct 는 정합.
    # w 가 1.0 에 가까울수록 combined ↑ engagement_rate 상관 ↑.
    rows = [
        {"final_rank_score": 60.0 - i, "comment_trigger_avg": 0.1 * (i + 1), "engagement_rate": 0.1 * (i + 1)}
        for i in range(6)
    ]
    best_w, best_r, n = sweep_comment_weights(rows)
    assert n == 6
    assert best_w is not None
    assert best_r is not None
    assert best_w >= 0.5  # 4축 weight 가 우세해야
    assert best_r > 0.9


def test_sweep_comment_weights_returns_none_for_insufficient_data():
    best_w, best_r, n = sweep_comment_weights([])
    assert best_w is None
    assert best_r is None
    assert n == 0

    rows_with_zero_ct = [
        {"final_rank_score": 50.0, "comment_trigger_avg": 0.0, "engagement_rate": 0.2},
        {"final_rank_score": 50.0, "comment_trigger_avg": 0.0, "engagement_rate": 0.3},
    ]
    best_w, best_r, n = sweep_comment_weights(rows_with_zero_ct)
    assert best_w is None
    assert n == 0


def test_load_recent_rows_reads_sqlite_without_cost_database(monkeypatch, tmp_path):
    db_path = tmp_path / "btx_costs.db"
    monkeypatch.setattr("scripts.tune_best_of_n_weight._DEFAULT_DB_PATH", db_path)
    monkeypatch.setitem(sys.modules, "pipeline.cost_db", None)
    today = date.today().isoformat()
    old_day = (date.today() - timedelta(days=60)).isoformat()

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE draft_analytics (
                date TEXT NOT NULL,
                published INTEGER DEFAULT 0,
                hook_score REAL,
                virality_score REAL,
                fit_score REAL,
                final_rank_score REAL,
                engagement_rate REAL,
                yt_views INTEGER,
                impression_count INTEGER
            )
            """
        )
        conn.executemany(
            """
            INSERT INTO draft_analytics (
                date, published, hook_score, virality_score, fit_score,
                final_rank_score, engagement_rate, yt_views, impression_count
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (today, 1, 0.8, 0.7, 0.6, 80.0, 0.12, 1000, 2000),
                (today, 0, 0.9, 0.8, 0.7, 90.0, 0.2, 2000, 3000),
                (old_day, 1, 0.5, 0.4, 0.3, 50.0, 0.05, 500, 900),
            ],
        )

    rows = load_recent_rows(days=30)

    assert len(rows) == 1
    assert rows[0]["date"] == today
    assert rows[0]["final_rank_score"] == 80.0
    assert rows[0]["comment_trigger_avg"] is None


def test_build_report_handles_insufficient_samples():
    text, summary = build_report([], days=30, min_samples=10)
    assert "샘플이 부족" in text
    assert summary["sample_count"] == 0
    assert summary["recommendation"]["reason"] == "insufficient_samples"
    assert summary["recommendation"]["weight"] == 0.5


def test_build_report_uses_final_rank_signal_when_ct_missing():
    rows = [
        {
            "hook_score": 0.5,
            "virality_score": 0.4,
            "fit_score": 0.6,
            "final_rank_score": 60.0 + i,
            "comment_trigger_avg": None,
            "engagement_rate": 0.05 + i * 0.01,
        }
        for i in range(15)
    ]
    text, summary = build_report(rows, days=30, min_samples=10)
    assert summary["sample_count"] == 15
    assert summary["comment_trigger_sweep"]["best_w"] is None
    rec = summary["recommendation"]
    assert rec is not None
    # final_rank_score 가 강한 양의 상관 → weight 0.4 추천 (final_rank_already_predictive)
    assert rec["reason"] == "final_rank_already_predictive"
    assert rec["weight"] == 0.4
    assert "권장" in text


def test_build_report_recommends_higher_weight_when_final_rank_anti_correlates():
    # final_rank 가 engagement 와 음의 상관 → 4축 비중을 늘려야
    rows = [
        {
            "hook_score": 0.5,
            "virality_score": 0.4,
            "fit_score": 0.6,
            "final_rank_score": 90.0 - i,  # 감소
            "comment_trigger_avg": None,
            "engagement_rate": 0.05 + i * 0.01,  # 증가 → 음의 상관
        }
        for i in range(15)
    ]
    _, summary = build_report(rows, days=30, min_samples=10)
    rec = summary["recommendation"]
    assert rec["reason"] == "final_rank_weak_predictor"
    assert rec["weight"] == 0.6


def test_build_report_uses_sweep_when_comment_trigger_data_present():
    rows = []
    for i in range(15):
        rows.append(
            {
                "hook_score": 0.5,
                "virality_score": 0.4,
                "fit_score": 0.6,
                "final_rank_score": 50.0,
                "comment_trigger_avg": 0.1 * (i + 1),
                "engagement_rate": 0.1 * (i + 1),
            }
        )
    _, summary = build_report(rows, days=30, min_samples=10)
    sweep = summary["comment_trigger_sweep"]
    assert sweep["best_w"] is not None
    assert sweep["samples"] == 15
    rec = summary["recommendation"]
    assert rec["reason"] == "sweep_best"
    assert 0.0 <= rec["weight"] <= 1.0


@pytest.mark.parametrize(
    "missing_field",
    ["hook_score", "virality_score", "fit_score", "final_rank_score"],
)
def test_correlate_axis_skips_rows_missing_field(missing_field):
    rows = []
    for i in range(5):
        row = {
            "hook_score": 0.5 + i * 0.1,
            "virality_score": 0.4 + i * 0.1,
            "fit_score": 0.6 + i * 0.1,
            "final_rank_score": 50.0 + i,
            "engagement_rate": 0.1 + i * 0.05,
        }
        if i == 0:
            row[missing_field] = None
        rows.append(row)
    r, n = correlate_axis(rows, missing_field, "engagement_rate")
    assert n == 4  # 한 행 누락
    assert r is not None
