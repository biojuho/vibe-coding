"""Unit tests for workspace/execution/llm_usage_summary.py.

Pure stdlib + tmp_path fixtures. No live DB or filesystem dependencies.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest

from execution.llm_usage_summary import (
    Aggregate,
    CallRecord,
    _parse_timestamp,
    aggregate,
    load_jsonl_records,
    load_sqlite_records,
    main,
    merge_dedup,
    render_text,
)


# ── _parse_timestamp ────────────────────────────────────────────────────────


def test_parse_timestamp_iso_with_z():
    dt = _parse_timestamp("2026-05-08T01:40:07.647087Z")
    assert dt is not None
    assert dt.tzinfo is not None
    assert dt.year == 2026
    assert dt.month == 5


def test_parse_timestamp_iso_with_offset():
    dt = _parse_timestamp("2026-05-08T01:40:07+00:00")
    assert dt is not None
    assert dt.tzinfo is not None


def test_parse_timestamp_naive_treated_as_utc():
    dt = _parse_timestamp("2026-05-08 01:40:07")
    assert dt is not None
    assert dt.tzinfo == timezone.utc


def test_parse_timestamp_garbage_returns_none():
    assert _parse_timestamp("") is None
    assert _parse_timestamp("not-a-date") is None
    assert _parse_timestamp(None) is None  # type: ignore[arg-type]


# ── Aggregate ───────────────────────────────────────────────────────────────


def _make_record(**overrides):
    base = {
        "timestamp": datetime(2026, 5, 8, 12, 0, 0, tzinfo=timezone.utc),
        "provider": "anthropic",
        "model": "claude-sonnet-4-20250514",
        "input_tokens": 1000,
        "output_tokens": 500,
        "cache_creation_tokens": 0,
        "cache_read_tokens": 0,
        "cost_usd": 0.012,
        "latency_ms": 250.0,
        "success": True,
        "fallback_used": False,
    }
    base.update(overrides)
    return CallRecord(**base)


def test_aggregate_basic_counts():
    agg = Aggregate(label="anthropic")
    agg.add(_make_record(cost_usd=0.01))
    agg.add(_make_record(cost_usd=0.02))
    d = agg.to_dict()
    assert d["total_calls"] == 2
    assert d["total_input_tokens"] == 2000
    assert d["total_output_tokens"] == 1000
    assert abs(d["total_cost_usd"] - 0.03) < 1e-9


def test_aggregate_cache_hit_ratio():
    agg = Aggregate(label="anthropic")
    # 100 input (no cache), then 100 hit, then 50 hit + 50 miss
    agg.add(_make_record(input_tokens=100, cache_read_tokens=0))
    agg.add(_make_record(input_tokens=0, cache_read_tokens=100))
    agg.add(_make_record(input_tokens=50, cache_read_tokens=50))
    # total input = 150, total cache_read = 150 → ratio 0.5
    assert abs(agg.cache_hit_ratio() - 0.5) < 1e-9


def test_aggregate_cache_hit_ratio_zero_when_no_cache():
    agg = Aggregate(label="openai")
    agg.add(_make_record(input_tokens=1000, cache_read_tokens=0))
    assert agg.cache_hit_ratio() == 0.0


def test_aggregate_error_and_fallback_rate():
    agg = Aggregate(label="test")
    agg.add(_make_record(success=True, fallback_used=False))
    agg.add(_make_record(success=False, fallback_used=True))
    agg.add(_make_record(success=True, fallback_used=True))
    d = agg.to_dict()
    assert d["error_count"] == 1
    # to_dict rounds to 4 decimals
    assert abs(d["error_rate"] - 0.3333) < 1e-4
    assert d["fallback_count"] == 2
    assert abs(d["fallback_rate"] - 0.6667) < 1e-4


def test_aggregate_latency_p95():
    agg = Aggregate(label="test")
    for latency in [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]:
        agg.add(_make_record(latency_ms=float(latency)))
    # avg = 550, p95 of 10 datapoints via nearest-rank → top of distribution
    assert agg.avg_latency_ms() == 550.0
    # round(10 * 0.95) - 1 = round(9.5) - 1 = 10 - 1 = 9 → sorted_l[9] = 1000
    # (Python banker's rounding sends 9.5 → 10 since 10 is even)
    assert agg.p95_latency_ms() == 1000.0


def test_aggregate_latency_p95_larger_sample():
    """p95 with 20 datapoints — middle of distribution behaviour."""
    agg = Aggregate(label="test")
    for latency in range(50, 1050, 50):  # 50, 100, ..., 1000 → 20 items
        agg.add(_make_record(latency_ms=float(latency)))
    # round(20 * 0.95) - 1 = 19 - 1 = 18 → sorted_l[18] = 950
    assert agg.p95_latency_ms() == 950.0


def test_aggregate_latency_zero_excluded():
    agg = Aggregate(label="test")
    agg.add(_make_record(latency_ms=0.0))
    agg.add(_make_record(latency_ms=100.0))
    # latency=0 means "not measured" → excluded
    assert agg.avg_latency_ms() == 100.0


# ── load_jsonl_records ──────────────────────────────────────────────────────


def test_load_jsonl_records_real_shape(tmp_path: Path):
    """Real-world payload from production llm_metrics.py."""
    metrics_dir = tmp_path / "llm_metrics"
    metrics_dir.mkdir()
    log = metrics_dir / "llm_calls_2026-05-08.jsonl"
    log.write_text(
        '{"timestamp": "2026-05-08T01:40:07Z", "provider": "openai", "model": "gpt-4o-mini",'
        ' "input_tokens": 100, "output_tokens": 50, "cache_creation_tokens": 0,'
        ' "cache_read_tokens": 0, "cost_usd": 0.0001, "latency_ms": 250.0, "success": true,'
        ' "error": "", "caller": "test", "metadata": {"fallback_used": true}}\n',
        encoding="utf-8",
    )
    records = list(load_jsonl_records(metrics_dir))
    assert len(records) == 1
    r = records[0]
    assert r.provider == "openai"
    assert r.fallback_used is True
    assert r.input_tokens == 100


def test_load_jsonl_records_filters_by_since(tmp_path: Path):
    metrics_dir = tmp_path / "llm_metrics"
    metrics_dir.mkdir()
    log = metrics_dir / "llm_calls_test.jsonl"
    log.write_text(
        '{"timestamp": "2026-01-01T00:00:00Z", "provider": "old", "model": "x"}\n'
        '{"timestamp": "2026-12-31T00:00:00Z", "provider": "new", "model": "y"}\n',
        encoding="utf-8",
    )
    since = datetime(2026, 6, 1, tzinfo=timezone.utc)
    records = list(load_jsonl_records(metrics_dir, since=since))
    assert len(records) == 1
    assert records[0].provider == "new"


def test_load_jsonl_records_skips_bad_lines(tmp_path: Path):
    metrics_dir = tmp_path / "llm_metrics"
    metrics_dir.mkdir()
    log = metrics_dir / "llm_calls_test.jsonl"
    log.write_text(
        "not-json\n"
        '{"timestamp": "garbage", "provider": "x"}\n'  # bad timestamp -> skip
        '{"timestamp": "2026-05-08T00:00:00Z", "provider": "ok", "model": "m"}\n'
        "\n",  # blank line
        encoding="utf-8",
    )
    records = list(load_jsonl_records(metrics_dir))
    assert len(records) == 1
    assert records[0].provider == "ok"


def test_load_jsonl_records_missing_dir(tmp_path: Path):
    records = list(load_jsonl_records(tmp_path / "nonexistent"))
    assert records == []


# ── load_sqlite_records ─────────────────────────────────────────────────────


def _make_db_with_api_calls(tmp_path: Path, *, with_cache_cols: bool = True) -> Path:
    db = tmp_path / "workspace.db"
    conn = sqlite3.connect(str(db))
    base_cols = """
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        provider TEXT NOT NULL,
        model TEXT DEFAULT '',
        endpoint TEXT DEFAULT '',
        tokens_input INTEGER DEFAULT 0,
        tokens_output INTEGER DEFAULT 0,
        cost_usd REAL DEFAULT 0,
        caller_script TEXT DEFAULT '',
        bridge_mode TEXT DEFAULT '',
        reason_codes TEXT DEFAULT '[]',
        repair_count INTEGER DEFAULT 0,
        fallback_used INTEGER DEFAULT 0,
        language_score REAL DEFAULT NULL,
        provider_used TEXT DEFAULT '',
        timestamp TEXT DEFAULT ''
    """
    if with_cache_cols:
        base_cols += ", cache_creation_tokens INTEGER DEFAULT 0, cache_read_tokens INTEGER DEFAULT 0"
    conn.execute(f"CREATE TABLE api_calls ({base_cols})")
    conn.commit()
    conn.close()
    return db


def test_load_sqlite_records_with_cache_columns(tmp_path: Path):
    db = _make_db_with_api_calls(tmp_path, with_cache_cols=True)
    conn = sqlite3.connect(str(db))
    conn.execute(
        "INSERT INTO api_calls (provider, model, tokens_input, tokens_output, cost_usd, "
        "cache_creation_tokens, cache_read_tokens, timestamp) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        ("anthropic", "claude-sonnet-4", 1000, 500, 0.012, 800, 200, "2026-05-08 12:00:00"),
    )
    conn.commit()
    conn.close()

    records = list(load_sqlite_records(db))
    assert len(records) == 1
    r = records[0]
    assert r.provider == "anthropic"
    assert r.cache_creation_tokens == 800
    assert r.cache_read_tokens == 200


def test_load_sqlite_records_without_cache_columns_returns_zeros(tmp_path: Path):
    """legacy DBs lacking the T-255 cache columns must still parse (with cache=0)."""
    db = _make_db_with_api_calls(tmp_path, with_cache_cols=False)
    conn = sqlite3.connect(str(db))
    conn.execute(
        "INSERT INTO api_calls (provider, model, tokens_input, tokens_output, cost_usd, timestamp) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        ("openai", "gpt-4o-mini", 100, 50, 0.0001, "2026-05-08 12:00:00"),
    )
    conn.commit()
    conn.close()

    records = list(load_sqlite_records(db))
    assert len(records) == 1
    r = records[0]
    assert r.provider == "openai"
    assert r.cache_creation_tokens == 0
    assert r.cache_read_tokens == 0


def test_load_sqlite_records_missing_db(tmp_path: Path):
    assert list(load_sqlite_records(tmp_path / "nonexistent.db")) == []


# ── merge_dedup ─────────────────────────────────────────────────────────────


def test_merge_dedup_prefers_richer_record():
    ts = datetime(2026, 5, 8, 12, 0, 0, tzinfo=timezone.utc)
    poor = _make_record(timestamp=ts, latency_ms=0.0)  # SQLite-style
    rich = _make_record(timestamp=ts, latency_ms=250.0)  # JSONL-style
    merged = merge_dedup([poor], [rich])
    assert len(merged) == 1
    assert merged[0].latency_ms == 250.0


def test_merge_dedup_keeps_distinct_records():
    ts = datetime(2026, 5, 8, 12, 0, 0, tzinfo=timezone.utc)
    a = _make_record(timestamp=ts, input_tokens=100)
    b = _make_record(timestamp=ts, input_tokens=200)  # different tokens → distinct call
    merged = merge_dedup([a, b])
    assert len(merged) == 2


# ── aggregate ───────────────────────────────────────────────────────────────


def test_aggregate_by_provider():
    records = [
        _make_record(provider="openai", cost_usd=0.001),
        _make_record(provider="openai", cost_usd=0.002),
        _make_record(provider="anthropic", cost_usd=0.01),
    ]
    aggs = aggregate(records, group_by="provider")
    assert len(aggs) == 2
    # sorted by cost desc — anthropic first
    assert aggs[0].label == "anthropic"
    assert aggs[1].label == "openai"
    assert aggs[1].total_calls == 2


def test_aggregate_by_model():
    records = [
        _make_record(provider="openai", model="gpt-4o-mini"),
        _make_record(provider="openai", model="gpt-4o"),
    ]
    aggs = aggregate(records, group_by="model")
    labels = {a.label for a in aggs}
    assert labels == {"openai/gpt-4o-mini", "openai/gpt-4o"}


def test_aggregate_by_caller_handles_empty():
    records = [_make_record()]  # caller defaults to ""
    aggs = aggregate(records, group_by="caller")
    assert aggs[0].label == "(unknown)"


def test_aggregate_overall_single_bucket():
    records = [
        _make_record(provider="openai", cost_usd=0.001),
        _make_record(provider="anthropic", cost_usd=0.01),
    ]
    aggs = aggregate(records, group_by="overall")
    assert len(aggs) == 1
    assert aggs[0].label == "overall"
    assert aggs[0].total_calls == 2


# ── render_text ─────────────────────────────────────────────────────────────


def test_render_text_empty():
    out = render_text([], days=7, group_by="overall")
    assert "no records found" in out


def test_render_text_shows_cost_and_cache():
    agg = Aggregate(label="anthropic")
    agg.add(_make_record(provider="anthropic", input_tokens=100, cache_read_tokens=900, cost_usd=0.005))
    out = render_text([agg], days=7, group_by="provider")
    assert "anthropic" in out
    assert "hit_ratio" in out


def test_render_text_skips_latency_block_when_zero():
    agg = Aggregate(label="x")
    agg.add(_make_record(latency_ms=0.0))
    out = render_text([agg], days=7, group_by="overall")
    assert "latency:" not in out


# ── main CLI ────────────────────────────────────────────────────────────────


def test_main_json_output_empty(tmp_path, capsys):
    exit_code = main(
        [
            "--days",
            "7",
            "--metrics-dir",
            str(tmp_path / "no_metrics"),
            "--db",
            str(tmp_path / "no_db.db"),
            "--json",
        ]
    )
    assert exit_code == 0
    captured = capsys.readouterr().out
    payload = json.loads(captured)
    assert payload["days"] == 7
    assert payload["record_count"] == 0
    assert payload["aggregates"] == []


def test_main_filters_by_provider(tmp_path, capsys):
    metrics_dir = tmp_path / "llm_metrics"
    metrics_dir.mkdir()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    log = metrics_dir / "llm_calls_test.jsonl"
    log.write_text(
        f'{{"timestamp": "{today}", "provider": "anthropic", "model": "claude", "cost_usd": 0.01}}\n'
        f'{{"timestamp": "{today}", "provider": "openai", "model": "gpt", "cost_usd": 0.001}}\n',
        encoding="utf-8",
    )
    exit_code = main(
        [
            "--days",
            "1",
            "--metrics-dir",
            str(metrics_dir),
            "--db",
            str(tmp_path / "no_db.db"),
            "--provider",
            "anthropic",
            "--json",
        ]
    )
    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["record_count"] == 1
    assert payload["aggregates"][0]["label"] == "overall"


@pytest.mark.parametrize("by", ["overall", "provider", "model", "caller"])
def test_main_group_by_choices_all_valid(tmp_path, by):
    exit_code = main(
        [
            "--metrics-dir",
            str(tmp_path / "no_metrics"),
            "--db",
            str(tmp_path / "no_db.db"),
            "--by",
            by,
            "--json",
        ]
    )
    assert exit_code == 0
