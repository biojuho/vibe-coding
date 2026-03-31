from __future__ import annotations

import execution.debug_history_db as dhdb


def _patch_db(monkeypatch, tmp_path):
    monkeypatch.setattr(dhdb, "DB_PATH", tmp_path / "debug_history.db")
    dhdb.init_db()


# ---------------------------------------------------------------------------
# init_db
# ---------------------------------------------------------------------------


def test_init_db_creates_tables(monkeypatch, tmp_path):
    _patch_db(monkeypatch, tmp_path)
    import sqlite3

    conn = sqlite3.connect(str(tmp_path / "debug_history.db"))
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    assert "debug_entries" in tables
    assert "error_patterns" in tables
    conn.close()


def test_init_db_idempotent(monkeypatch, tmp_path):
    _patch_db(monkeypatch, tmp_path)
    dhdb.init_db()  # 두 번 호출해도 오류 없음


# ---------------------------------------------------------------------------
# add_entry / list_entries
# ---------------------------------------------------------------------------


def test_add_entry_returns_id(monkeypatch, tmp_path):
    _patch_db(monkeypatch, tmp_path)
    entry_id = dhdb.add_entry(symptom="테스트 에러", severity="P2", module="test_module")
    assert isinstance(entry_id, int)
    assert entry_id >= 1


def test_list_entries_returns_added(monkeypatch, tmp_path):
    _patch_db(monkeypatch, tmp_path)
    dhdb.add_entry(symptom="에러A", severity="P1", module="mod_a")
    dhdb.add_entry(symptom="에러B", severity="P2", module="mod_b")
    entries = dhdb.list_entries()
    assert len(entries) == 2


def test_list_entries_filter_severity(monkeypatch, tmp_path):
    _patch_db(monkeypatch, tmp_path)
    dhdb.add_entry(symptom="p1 에러", severity="P1")
    dhdb.add_entry(symptom="p2 에러", severity="P2")
    entries = dhdb.list_entries(severity="P1")
    assert len(entries) == 1
    assert entries[0]["severity"] == "P1"


def test_list_entries_filter_layer(monkeypatch, tmp_path):
    _patch_db(monkeypatch, tmp_path)
    dhdb.add_entry(symptom="지침 에러", layer="directive")
    dhdb.add_entry(symptom="실행 에러", layer="execution")
    entries = dhdb.list_entries(layer="directive")
    assert len(entries) == 1
    assert entries[0]["layer"] == "directive"


def test_list_entries_filter_module(monkeypatch, tmp_path):
    _patch_db(monkeypatch, tmp_path)
    dhdb.add_entry(symptom="유튜브 에러", module="youtube_uploader")
    dhdb.add_entry(symptom="노션 에러", module="notion_client")
    entries = dhdb.list_entries(module="youtube")
    assert len(entries) == 1


def test_list_entries_limit(monkeypatch, tmp_path):
    _patch_db(monkeypatch, tmp_path)
    for i in range(10):
        dhdb.add_entry(symptom=f"에러 {i}")
    entries = dhdb.list_entries(limit=3)
    assert len(entries) == 3


def test_add_entry_all_fields(monkeypatch, tmp_path):
    _patch_db(monkeypatch, tmp_path)
    dhdb.add_entry(
        symptom="전체 필드 테스트",
        severity="P0",
        layer="orchestration",
        module="test_mod",
        root_cause="테스트 원인",
        solution="테스트 해결",
        directive_updated=True,
        test_added=True,
        commit_hash="abc1234",
        tags="test,debug",
        notes="메모",
    )
    entries = dhdb.list_entries()
    e = entries[0]
    assert e["severity"] == "P0"
    assert e["layer"] == "orchestration"
    assert e["directive_updated"] == 1
    assert e["test_added"] == 1
    assert e["commit_hash"] == "abc1234"
    assert e["tags"] == "test,debug"


# ---------------------------------------------------------------------------
# search_entries
# ---------------------------------------------------------------------------


def test_search_by_symptom(monkeypatch, tmp_path):
    _patch_db(monkeypatch, tmp_path)
    dhdb.add_entry(symptom="업로드 무한 루프", solution="MAX_RETRIES 추가")
    dhdb.add_entry(symptom="다른 에러")
    results = dhdb.search_entries("무한 루프")
    assert len(results) == 1
    assert "무한 루프" in results[0]["symptom"]


def test_search_by_solution(monkeypatch, tmp_path):
    _patch_db(monkeypatch, tmp_path)
    dhdb.add_entry(symptom="에러", solution="try/except 추가")
    results = dhdb.search_entries("try/except")
    assert len(results) == 1


def test_search_by_tags(monkeypatch, tmp_path):
    _patch_db(monkeypatch, tmp_path)
    dhdb.add_entry(symptom="에러", tags="playwright,timeout")
    results = dhdb.search_entries("playwright")
    assert len(results) == 1


def test_search_no_results(monkeypatch, tmp_path):
    _patch_db(monkeypatch, tmp_path)
    dhdb.add_entry(symptom="에러")
    results = dhdb.search_entries("존재하지않는키워드")
    assert len(results) == 0


# ---------------------------------------------------------------------------
# get_stats
# ---------------------------------------------------------------------------


def test_get_stats_empty(monkeypatch, tmp_path):
    _patch_db(monkeypatch, tmp_path)
    stats = dhdb.get_stats()
    assert stats["total_entries"] == 0
    assert stats["directive_update_rate"] == 0.0
    assert stats["test_addition_rate"] == 0.0


def test_get_stats_with_data(monkeypatch, tmp_path):
    _patch_db(monkeypatch, tmp_path)
    dhdb.add_entry(symptom="P1 에러", severity="P1", module="mod_a", directive_updated=True, test_added=True)
    dhdb.add_entry(symptom="P2 에러", severity="P2", module="mod_a")
    dhdb.add_entry(symptom="P2 에러2", severity="P2", module="mod_b", test_added=True)

    stats = dhdb.get_stats()
    assert stats["total_entries"] == 3
    assert stats["by_severity"]["P1"] == 1
    assert stats["by_severity"]["P2"] == 2
    assert stats["top_modules"]["mod_a"] == 2
    assert stats["directive_update_rate"] == 33.3  # 1/3
    assert stats["test_addition_rate"] == 66.7  # 2/3


# ---------------------------------------------------------------------------
# error_patterns
# ---------------------------------------------------------------------------


def test_register_pattern_new(monkeypatch, tmp_path):
    _patch_db(monkeypatch, tmp_path)
    dhdb.register_pattern("ImportError", "ImportError", "pip list", "terminal")
    patterns = dhdb.list_patterns()
    assert len(patterns) == 1
    assert patterns[0]["pattern"] == "ImportError"
    assert patterns[0]["times_seen"] == 1


def test_register_pattern_duplicate_increments(monkeypatch, tmp_path):
    _patch_db(monkeypatch, tmp_path)
    dhdb.register_pattern("ImportError", "ImportError", "pip list", "terminal")
    dhdb.register_pattern("ImportError", "ImportError", "pip list", "terminal")
    patterns = dhdb.list_patterns()
    assert len(patterns) == 1
    assert patterns[0]["times_seen"] == 2


def test_lookup_pattern_match(monkeypatch, tmp_path):
    _patch_db(monkeypatch, tmp_path)
    dhdb.register_pattern("ImportError", "ImportError", "pip list", "terminal")
    dhdb.register_pattern("KeyError", "KeyError", "데이터 구조", "debugger")
    matches = dhdb.lookup_pattern("ImportError: No module named 'xxx'")
    assert len(matches) == 1
    assert matches[0]["pattern"] == "ImportError"


def test_lookup_pattern_no_match(monkeypatch, tmp_path):
    _patch_db(monkeypatch, tmp_path)
    dhdb.register_pattern("ImportError", "ImportError", "pip list", "terminal")
    matches = dhdb.lookup_pattern("SomeOtherError happened")
    assert len(matches) == 0


def test_seed_known_patterns(monkeypatch, tmp_path):
    _patch_db(monkeypatch, tmp_path)
    count = dhdb.seed_known_patterns()
    assert count >= 15
    patterns = dhdb.list_patterns()
    assert len(patterns) >= 15
    # 주요 패턴 존재 확인
    pattern_names = {p["pattern"] for p in patterns}
    assert "ImportError" in pattern_names
    assert "KeyError" in pattern_names
    assert "TimeoutError" in pattern_names


# ---------------------------------------------------------------------------
# auto_capture_error
# ---------------------------------------------------------------------------


def test_auto_capture_error_new_entry(monkeypatch, tmp_path):
    """auto_capture_error가 새 예외를 기록하고 entry ID를 반환."""
    _patch_db(monkeypatch, tmp_path)
    exc = ValueError("something went wrong")
    entry_id = dhdb.auto_log_error(exc, module="test_mod")
    assert isinstance(entry_id, int)
    assert entry_id >= 1
    entries = dhdb.list_entries(module="test_mod")
    assert len(entries) == 1
    assert "[auto]" in entries[0]["symptom"]
    assert "ValueError" in entries[0]["symptom"]
    assert entries[0]["tags"] == "auto_captured"


def test_auto_capture_error_deduplicates(monkeypatch, tmp_path):
    """같은 module + 에러 타입이 24시간 내 중복이면 None 반환."""
    _patch_db(monkeypatch, tmp_path)
    exc1 = ValueError("first error")
    first_id = dhdb.auto_log_error(exc1, module="dedup_mod")
    assert first_id is not None

    exc2 = ValueError("second error same type")
    second_id = dhdb.auto_log_error(exc2, module="dedup_mod")
    assert second_id is None

    entries = dhdb.list_entries(module="dedup_mod")
    assert len(entries) == 1


def test_auto_capture_error_with_context(monkeypatch, tmp_path):
    """context 파라미터가 symptom 문자열에 반영."""
    _patch_db(monkeypatch, tmp_path)
    exc = RuntimeError("ctx error")
    entry_id = dhdb.auto_log_error(exc, module="ctx_mod", context="pipeline")
    assert entry_id is not None
    entries = dhdb.list_entries(module="ctx_mod")
    assert "[auto][pipeline]" in entries[0]["symptom"]
    assert "RuntimeError" in entries[0]["symptom"]


def test_auto_capture_error_with_severity(monkeypatch, tmp_path):
    """severity 파라미터가 올바르게 전달."""
    _patch_db(monkeypatch, tmp_path)
    exc = TypeError("type issue")
    entry_id = dhdb.auto_log_error(exc, module="sev_mod", severity="P0")
    assert entry_id is not None
    entries = dhdb.list_entries(module="sev_mod")
    assert entries[0]["severity"] == "P0"


def test_auto_capture_error_outer_exception_returns_none(monkeypatch, tmp_path):
    """외부 예외 발생 시 None 반환 (크래시 방지)."""
    _patch_db(monkeypatch, tmp_path)
    # init_db를 예외 발생시키도록 패치
    monkeypatch.setattr(dhdb, "init_db", lambda: (_ for _ in ()).throw(RuntimeError("boom")))
    exc = ValueError("won't be recorded")
    result = dhdb.auto_log_error(exc, module="fail_mod")
    assert result is None


# ---------------------------------------------------------------------------
# log_scrape_quality / get_scrape_quality_stats
# ---------------------------------------------------------------------------


def test_log_scrape_quality_and_stats(monkeypatch, tmp_path):
    """log_scrape_quality로 기록 후 get_scrape_quality_stats로 조회."""
    _patch_db(monkeypatch, tmp_path)
    dhdb.log_scrape_quality("blind", "https://example.com/1", 85.5, ["missing_image"])
    dhdb.log_scrape_quality("blind", "https://example.com/2", 92.0, [])
    dhdb.log_scrape_quality("ppomppu", "https://ppomppu.co.kr/1", 70.0, ["short_content", "no_title"])

    stats = dhdb.get_scrape_quality_stats(days=14)
    assert stats["lookback_days"] == 14
    assert isinstance(stats["by_source"], list)
    assert len(stats["by_source"]) == 2
    sources = {row["source"] for row in stats["by_source"]}
    assert sources == {"blind", "ppomppu"}


def test_log_scrape_quality_exception_swallowed(monkeypatch, tmp_path):
    """log_scrape_quality는 conn.execute 실패 시 예외를 삼킴."""
    _patch_db(monkeypatch, tmp_path)

    original_conn = dhdb._conn

    def _readonly_conn():
        conn = original_conn()
        # Drop the table so INSERT fails
        conn.execute("DROP TABLE IF EXISTS scrape_quality_log")
        conn.commit()
        return conn

    monkeypatch.setattr(dhdb, "_conn", _readonly_conn)
    # INSERT 실패하지만 예외 없이 실행 완료 (except pass)
    dhdb.log_scrape_quality("test", "http://x.com", 50.0, [])


def test_get_scrape_quality_stats_empty(monkeypatch, tmp_path):
    """데이터 없을 때 빈 by_source 반환."""
    _patch_db(monkeypatch, tmp_path)
    stats = dhdb.get_scrape_quality_stats()
    assert stats["by_source"] == []
    assert stats["lookback_days"] == 14


# ---------------------------------------------------------------------------
# _print_entries
# ---------------------------------------------------------------------------


def test_print_entries_empty(monkeypatch, tmp_path, capsys):
    """빈 목록 시 '결과 없음' 출력."""
    _patch_db(monkeypatch, tmp_path)
    dhdb._print_entries([])
    captured = capsys.readouterr().out
    assert "결과 없음" in captured


def test_print_entries_with_data(monkeypatch, tmp_path, capsys):
    """엔트리 데이터의 각 필드가 올바르게 출력."""
    _patch_db(monkeypatch, tmp_path)
    entries = [
        {
            "severity": "P1",
            "created_at": "2026-03-07 12:00:00",
            "module": "youtube_uploader",
            "symptom": "업로드 타임아웃",
            "root_cause": "API 속도 제한",
            "solution": "재시도 로직 추가",
            "directive_updated": 1,
            "test_added": 1,
            "layer": "execution",
        },
    ]
    dhdb._print_entries(entries)
    captured = capsys.readouterr().out
    assert "[P1]" in captured
    assert "youtube_uploader" in captured
    assert "업로드 타임아웃" in captured
    assert "API 속도 제한" in captured
    assert "재시도 로직 추가" in captured


def test_print_entries_no_root_cause_or_solution(monkeypatch, tmp_path, capsys):
    """root_cause/solution이 없는 엔트리도 정상 출력."""
    _patch_db(monkeypatch, tmp_path)
    entries = [
        {
            "severity": "P2",
            "created_at": "2026-03-07 13:00:00",
            "module": None,
            "symptom": "알 수 없는 에러",
            "root_cause": None,
            "solution": None,
            "directive_updated": 0,
            "test_added": 0,
            "layer": "execution",
        },
    ]
    dhdb._print_entries(entries)
    captured = capsys.readouterr().out
    assert "[P2]" in captured
    assert "(no module)" in captured
    assert "원인" not in captured
    assert "해결" not in captured
