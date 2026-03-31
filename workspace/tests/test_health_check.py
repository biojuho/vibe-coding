from __future__ import annotations

from unittest.mock import MagicMock, patch

import execution.health_check as hc


# ---------------------------------------------------------------------------
# check_env_vars
# ---------------------------------------------------------------------------


def test_check_env_vars_detects_set_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test123")
    results = hc.check_env_vars()
    oai = [r for r in results if r["name"] == "OPENAI_API_KEY"]
    assert len(oai) == 1
    assert oai[0]["status"] == hc.STATUS_OK


def test_check_env_vars_detects_missing_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    results = hc.check_env_vars()
    oai = [r for r in results if r["name"] == "OPENAI_API_KEY"]
    assert len(oai) == 1
    assert oai[0]["status"] == hc.STATUS_WARN


# ---------------------------------------------------------------------------
# check_api_connections
# ---------------------------------------------------------------------------


def test_check_api_missing_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    results = hc.check_api_connections()
    oai = [r for r in results if r["name"] == "OpenAI"]
    assert oai[0]["status"] == hc.STATUS_WARN


def test_check_api_key_only_no_url(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    results = hc.check_api_connections()
    ant = [r for r in results if r["name"] == "Anthropic"]
    assert ant[0]["status"] == hc.STATUS_OK
    assert "no ping endpoint" in ant[0]["detail"]


def test_check_api_connection_success(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    with patch.object(hc.requests, "get", return_value=mock_resp):
        results = hc.check_api_connections()
    oai = [r for r in results if r["name"] == "OpenAI"]
    assert oai[0]["status"] == hc.STATUS_OK


def test_check_api_connection_401(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    mock_resp = MagicMock()
    mock_resp.status_code = 401
    with patch.object(hc.requests, "get", return_value=mock_resp):
        results = hc.check_api_connections()
    oai = [r for r in results if r["name"] == "OpenAI"]
    assert oai[0]["status"] == hc.STATUS_FAIL
    assert "401" in oai[0]["detail"]


def test_check_api_connection_timeout(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    import requests as req

    with patch.object(hc.requests, "get", side_effect=req.Timeout("timed out")):
        results = hc.check_api_connections()
    oai = [r for r in results if r["name"] == "OpenAI"]
    assert oai[0]["status"] == hc.STATUS_FAIL


def test_check_api_connection_error(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    import requests as req

    with patch.object(hc.requests, "get", side_effect=req.ConnectionError("conn")):
        results = hc.check_api_connections()
    oai = [r for r in results if r["name"] == "OpenAI"]
    assert oai[0]["status"] == hc.STATUS_FAIL


def test_check_api_429(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    mock_resp = MagicMock()
    mock_resp.status_code = 429
    with patch.object(hc.requests, "get", return_value=mock_resp):
        results = hc.check_api_connections()
    oai = [r for r in results if r["name"] == "OpenAI"]
    assert oai[0]["status"] == hc.STATUS_WARN


def test_check_api_403(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    mock_resp = MagicMock()
    mock_resp.status_code = 403
    with patch.object(hc.requests, "get", return_value=mock_resp):
        results = hc.check_api_connections()
    oai = [r for r in results if r["name"] == "OpenAI"]
    assert oai[0]["status"] == hc.STATUS_FAIL


def test_check_api_unknown_status(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    mock_resp = MagicMock()
    mock_resp.status_code = 503
    with patch.object(hc.requests, "get", return_value=mock_resp):
        results = hc.check_api_connections()
    oai = [r for r in results if r["name"] == "OpenAI"]
    assert oai[0]["status"] == hc.STATUS_WARN


def test_check_api_generic_exception(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    with patch.object(hc.requests, "get", side_effect=RuntimeError("unexpected")):
        results = hc.check_api_connections()
    oai = [r for r in results if r["name"] == "OpenAI"]
    assert oai[0]["status"] == hc.STATUS_FAIL


def test_check_api_multi_keys_all_set(monkeypatch):
    monkeypatch.setenv("CLOUDINARY_CLOUD_NAME", "test")
    monkeypatch.setenv("CLOUDINARY_API_KEY", "test")
    monkeypatch.setenv("CLOUDINARY_API_SECRET", "test")
    results = hc.check_api_connections()
    cloud = [r for r in results if r["name"] == "Cloudinary"]
    assert cloud[0]["status"] == hc.STATUS_OK


def test_check_api_multi_keys_missing(monkeypatch):
    monkeypatch.delenv("CLOUDINARY_CLOUD_NAME", raising=False)
    monkeypatch.setenv("CLOUDINARY_API_KEY", "test")
    monkeypatch.setenv("CLOUDINARY_API_SECRET", "test")
    results = hc.check_api_connections()
    cloud = [r for r in results if r["name"] == "Cloudinary"]
    assert cloud[0]["status"] == hc.STATUS_WARN


# ---------------------------------------------------------------------------
# check_directories / check_files
# ---------------------------------------------------------------------------


def test_check_directories():
    results = hc.check_directories()
    assert len(results) > 0
    exec_check = [r for r in results if r["name"] == "execution/"]
    assert exec_check[0]["status"] == hc.STATUS_OK


def test_check_files():
    results = hc.check_files()
    assert len(results) > 0


# ---------------------------------------------------------------------------
# check_databases
# ---------------------------------------------------------------------------


def test_check_databases_skip_missing(monkeypatch):
    monkeypatch.setattr(hc, "DB_CHECKS", [("nonexistent.db", hc._ROOT / "nonexistent.db")])
    results = hc.check_databases()
    assert results[0]["status"] == hc.STATUS_SKIP


def test_check_databases_valid(tmp_path):
    import sqlite3

    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("CREATE TABLE test_table (id INTEGER)")
    conn.close()

    original = hc.DB_CHECKS
    hc.DB_CHECKS = [("test.db", db_path)]
    try:
        results = hc.check_databases()
        assert results[0]["status"] == hc.STATUS_OK
        assert "test_table" in results[0]["detail"]
    finally:
        hc.DB_CHECKS = original


# ---------------------------------------------------------------------------
# check_venv / check_git
# ---------------------------------------------------------------------------


def test_check_venv():
    results = hc.check_venv()
    assert len(results) == 1
    assert results[0]["category"] == "environment"


def test_check_git():
    results = hc.check_git()
    assert len(results) == 1


# ---------------------------------------------------------------------------
# run_all_checks / get_summary
# ---------------------------------------------------------------------------


def test_run_all_checks_returns_list():
    results = hc.run_all_checks()
    assert isinstance(results, list)
    assert len(results) > 0


def test_run_all_checks_with_filter():
    results = hc.run_all_checks(category="filesystem")
    for r in results:
        assert r["category"] == "filesystem"


def test_run_all_checks_with_governance_filter():
    results = hc.run_all_checks(category="governance")
    assert len(results) > 0
    for r in results:
        assert r["category"] == "governance"


def test_get_summary_ok():
    results = [hc._check_result("test", "test", hc.STATUS_OK)]
    s = hc.get_summary(results)
    assert s["overall"] == hc.STATUS_OK
    assert s["counts"][hc.STATUS_OK] == 1


def test_get_summary_fail_overrides():
    results = [
        hc._check_result("a", "t", hc.STATUS_OK),
        hc._check_result("b", "t", hc.STATUS_FAIL),
    ]
    s = hc.get_summary(results)
    assert s["overall"] == hc.STATUS_FAIL


def test_get_summary_warn():
    results = [
        hc._check_result("a", "t", hc.STATUS_OK),
        hc._check_result("b", "t", hc.STATUS_WARN),
    ]
    s = hc.get_summary(results)
    assert s["overall"] == hc.STATUS_WARN


def test_checker_exception_handled(monkeypatch):
    """checker가 예외를 던져도 run_all_checks가 계속 진행."""

    def _boom():
        raise RuntimeError("boom")

    monkeypatch.setattr(hc, "check_env_vars", _boom)
    results = hc.run_all_checks(category="env")
    assert any(r["status"] == hc.STATUS_FAIL for r in results)


# ---------------------------------------------------------------------------
# check_apis — future.result() exception path (lines 209-210)
# ---------------------------------------------------------------------------


def test_check_apis_future_exception(monkeypatch):
    """check_api_connections의 future.result() 예외 시 STATUS_FAIL."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    def _exploding_check(api):
        raise RuntimeError("executor boom")

    monkeypatch.setattr(hc, "_check_single_api", _exploding_check)
    results = hc.check_api_connections()
    assert any(r["status"] == hc.STATUS_FAIL and "unexpected error" in r["detail"] for r in results)


# ---------------------------------------------------------------------------
# check_directories — missing directory (line 224)
# ---------------------------------------------------------------------------


def test_check_directories_missing(monkeypatch):
    """존재하지 않는 디렉토리가 STATUS_FAIL."""
    from pathlib import Path

    monkeypatch.setattr(
        hc,
        "REQUIRED_DIRS",
        [("nonexistent_dir/", Path("/this/path/does/not/exist/at/all"))],
    )
    results = hc.check_directories()
    assert len(results) == 1
    assert results[0]["status"] == hc.STATUS_FAIL
    assert "missing" in results[0]["detail"]


# ---------------------------------------------------------------------------
# check_files — missing file (line 235)
# ---------------------------------------------------------------------------


def test_check_files_missing(monkeypatch):
    """존재하지 않는 파일이 STATUS_FAIL."""
    from pathlib import Path

    monkeypatch.setattr(
        hc,
        "REQUIRED_FILES",
        [("missing.txt", Path("/this/file/does/not/exist.txt"))],
    )
    results = hc.check_files()
    assert len(results) == 1
    assert results[0]["status"] == hc.STATUS_FAIL
    assert "missing" in results[0]["detail"]


# ---------------------------------------------------------------------------
# check_databases — corrupt DB (lines 252-253)
# ---------------------------------------------------------------------------


def test_check_databases_corrupt(tmp_path):
    """손상된 DB 파일이 STATUS_FAIL."""
    db_path = tmp_path / "corrupt.db"
    db_path.write_bytes(b"this is not a valid sqlite database")

    original = hc.DB_CHECKS
    hc.DB_CHECKS = [("corrupt.db", db_path)]
    try:
        results = hc.check_databases()
        assert results[0]["status"] == hc.STATUS_FAIL
    finally:
        hc.DB_CHECKS = original


# ---------------------------------------------------------------------------
# _print_report (lines 326-345)
# ---------------------------------------------------------------------------


def test_print_report_output(capsys):
    """_print_report가 카테고리별 아이콘/요약을 출력."""
    results = [
        hc._check_result("env_var_1", "env", hc.STATUS_OK, "set"),
        hc._check_result("env_var_2", "env", hc.STATUS_WARN, "missing"),
        hc._check_result("dir_1", "filesystem", hc.STATUS_FAIL, "missing: /x"),
        hc._check_result("skip_1", "database", hc.STATUS_SKIP, "not created yet"),
    ]
    hc._print_report(results)
    captured = capsys.readouterr().out
    assert "[ENV]" in captured
    assert "[FILESYSTEM]" in captured
    assert "[DATABASE]" in captured
    assert "Overall:" in captured
    assert "FAIL" in captured
    assert "OK=1" in captured
    assert "WARN=1" in captured
    assert "FAIL=1" in captured
    assert "SKIP=1" in captured


def test_print_report_all_ok(capsys):
    """모두 OK일 때 overall도 OK."""
    results = [
        hc._check_result("check1", "env", hc.STATUS_OK, "good"),
    ]
    hc._print_report(results)
    captured = capsys.readouterr().out
    assert "OK" in captured


# ---------------------------------------------------------------------------
# check_venv: venv not activated but exists / venv not found (lines 265-268)
# ---------------------------------------------------------------------------


def test_check_venv_exists_not_activated(monkeypatch, tmp_path):
    """venv directory exists but not activated."""
    venv_dir = tmp_path / "venv"
    venv_dir.mkdir()
    monkeypatch.setattr(hc, "_ROOT", tmp_path)
    # Ensure not in venv
    monkeypatch.delattr("sys.real_prefix", raising=False)
    monkeypatch.setattr("sys.base_prefix", "sys.prefix_value")
    monkeypatch.setattr("sys.prefix", "sys.prefix_value")
    result = hc.check_venv()
    assert result[0]["status"] == hc.STATUS_WARN


def test_check_venv_not_found(monkeypatch, tmp_path):
    """venv directory not found."""
    monkeypatch.setattr(hc, "_ROOT", tmp_path)
    monkeypatch.delattr("sys.real_prefix", raising=False)
    monkeypatch.setattr("sys.base_prefix", "sys.prefix_value")
    monkeypatch.setattr("sys.prefix", "sys.prefix_value")
    result = hc.check_venv()
    assert result[0]["status"] == hc.STATUS_FAIL


# ---------------------------------------------------------------------------
# check_git: no .git directory (line 276)
# ---------------------------------------------------------------------------


def test_check_git_not_found(monkeypatch, tmp_path):
    """No .git directory."""
    monkeypatch.setattr(hc, "_ROOT", tmp_path)
    result = hc.check_git()
    assert result[0]["status"] == hc.STATUS_FAIL
