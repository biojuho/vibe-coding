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
