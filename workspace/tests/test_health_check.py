from __future__ import annotations

import re
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


def test_parse_env_key_file_ignores_comments_and_invalid_lines(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n# comment\nOPENAI_API_KEY=sk-test\nNO_EQUALS\n EMPTY_KEY = ignored\nOPENAI_API_KEY=duplicate\n",
        encoding="utf-8",
    )

    assert hc._parse_env_key_file(env_file) == {"OPENAI_API_KEY", "EMPTY_KEY"}


def test_env_completeness_delta_results_preserves_status_and_text():
    results = hc._env_completeness_delta_results(["A", "B"], ["C"])

    assert [result["name"] for result in results] == [
        "env_completeness:missing",
        "env_completeness:extra",
    ]
    assert results[0]["status"] == hc.STATUS_WARN
    assert results[0]["detail"] == "keys in .env.example but not in .env: A, B"
    assert results[1]["status"] == hc.STATUS_OK
    assert results[1]["detail"] == "extra keys in .env (not in example): C"


def test_check_env_completeness_reports_matching_key_count(monkeypatch, tmp_path):
    (tmp_path / ".env").write_text("A=1\nB=2\n", encoding="utf-8")
    (tmp_path / ".env.example").write_text("A=\nB=\n", encoding="utf-8")
    monkeypatch.setattr(hc, "_ROOT", tmp_path)

    results = hc.check_env_completeness()

    assert len(results) == 1
    assert results[0]["name"] == "env_completeness"
    assert results[0]["status"] == hc.STATUS_OK
    assert results[0]["detail"] == ".env matches .env.example (2 keys)"


# ---------------------------------------------------------------------------
# check_api_connections
# ---------------------------------------------------------------------------


def test_check_api_missing_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    results = hc.check_api_connections()
    oai = [r for r in results if r["name"] == "OpenAI"]
    assert oai[0]["status"] == hc.STATUS_WARN


def test_multi_key_api_result_reports_missing_and_all_set(monkeypatch):
    api = {"env_keys": ["A_KEY", "B_KEY"]}
    monkeypatch.delenv("A_KEY", raising=False)
    monkeypatch.setenv("B_KEY", "set")

    missing = hc._multi_key_api_result(api, "Multi")
    assert missing["status"] == hc.STATUS_WARN
    assert missing["detail"] == "missing keys: A_KEY"

    monkeypatch.setenv("A_KEY", "set")
    complete = hc._multi_key_api_result(api, "Multi")
    assert complete["status"] == hc.STATUS_OK
    assert complete["detail"] == "all keys set"


def test_api_auth_headers_preserves_scheme_and_extra_headers():
    headers = hc._api_auth_headers(
        {
            "auth_header": "Token",
            "extra_headers": {"Notion-Version": "2022-06-28"},
        },
        "secret",
    )

    assert headers == {
        "Authorization": "Token secret",
        "Notion-Version": "2022-06-28",
    }


def test_api_status_result_uses_provider_overrides():
    api = {
        "auth_failure_status": hc.STATUS_WARN,
        "auth_failure_detail": "optional auth failed",
        "permission_failure_status": hc.STATUS_WARN,
        "permission_failure_detail": "optional permission failed",
    }

    assert hc._api_status_result("Provider", api, 200)["detail"] == "connected"
    assert hc._api_status_result("Provider", api, 401)["status"] == hc.STATUS_WARN
    assert hc._api_status_result("Provider", api, 401)["detail"] == "optional auth failed"
    assert hc._api_status_result("Provider", api, 403)["detail"] == "optional permission failed"
    assert hc._api_status_result("Provider", api, 429)["status"] == hc.STATUS_WARN
    assert hc._api_status_result("Provider", api, 503)["detail"] == "HTTP 503"


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


def test_check_api_connection_401_optional_provider_warn(monkeypatch):
    monkeypatch.setenv("MOONSHOT_API_KEY", "sk-test-moonshot-valid-format-1234567890")
    mock_resp = MagicMock()
    mock_resp.status_code = 401
    with patch.object(hc.requests, "get", return_value=mock_resp):
        results = hc.check_api_connections()
    moonshot = [r for r in results if r["name"] == "Moonshot"]
    assert moonshot[0]["status"] == hc.STATUS_WARN
    assert "optional fallback provider" in moonshot[0]["detail"]


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


def test_check_api_key_health_401_optional_provider_warn(monkeypatch):
    monkeypatch.setenv("MOONSHOT_API_KEY", "sk-test-moonshot-valid-format-1234567890")
    mock_resp = MagicMock()
    mock_resp.status_code = 401
    with patch.object(hc.requests, "get", return_value=mock_resp):
        results = hc.check_api_key_health()
    moonshot = [r for r in results if r["name"] == "key:MOONSHOT_API_KEY"]
    assert moonshot[0]["status"] == hc.STATUS_WARN
    assert "optional fallback provider" in moonshot[0]["detail"]


def test_api_key_names_preserve_order_and_dedupe(monkeypatch):
    monkeypatch.setattr(
        hc,
        "API_CHECKS",
        [
            {"name": "A", "env_key": "A_KEY"},
            {"name": "Multi", "env_keys": ["B_KEY", "A_KEY"]},
        ],
    )
    monkeypatch.setattr(
        hc,
        "_KEY_FORMAT_PATTERNS",
        {
            "C_KEY": ("c_", re.compile(r"^c_")),
            "A_KEY": ("a_", re.compile(r"^a_")),
        },
    )

    assert hc._api_key_names() == ["A_KEY", "B_KEY", "C_KEY"]


def test_api_key_format_result_reports_unexpected_format(monkeypatch):
    monkeypatch.setattr(hc, "_KEY_FORMAT_PATTERNS", {"A_KEY": ("a_", re.compile(r"^a_"))})

    assert hc._api_key_format_result("A_KEY", "a_valid") is None
    bad = hc._api_key_format_result("A_KEY", "bad")
    assert bad["name"] == "key:A_KEY"
    assert bad["status"] == hc.STATUS_WARN
    assert bad["detail"] == "unexpected format (expected a_)"
    assert hc._api_key_format_result("B_KEY", "anything") is None


def test_api_key_validation_headers_preserve_extra_headers():
    headers = hc._api_key_validation_headers(
        {
            "auth_header": "Token",
            "extra_headers": {"Notion-Version": "2022-06-28"},
        },
        "secret",
    )

    assert headers == {
        "Authorization": "Token secret",
        "Notion-Version": "2022-06-28",
    }


def test_api_key_validation_status_result_uses_provider_overrides():
    endpoint = {
        "auth_failure_status": hc.STATUS_WARN,
        "auth_failure_detail": "optional auth failed",
        "permission_failure_status": hc.STATUS_WARN,
        "permission_failure_detail": "optional permission failed",
    }

    assert hc._api_key_validation_status_result("key:A", endpoint, 200)["detail"] == "valid (auth ok)"
    assert hc._api_key_validation_status_result("key:A", endpoint, 401)["status"] == hc.STATUS_WARN
    assert hc._api_key_validation_status_result("key:A", endpoint, 401)["detail"] == "optional auth failed"
    assert hc._api_key_validation_status_result("key:A", endpoint, 403)["detail"] == "optional permission failed"
    assert hc._api_key_validation_status_result("key:A", endpoint, 429)["status"] == hc.STATUS_WARN
    assert hc._api_key_validation_status_result("key:A", endpoint, 503)["detail"] == "HTTP 503"


def test_api_key_health_result_keeps_no_endpoint_success(monkeypatch):
    monkeypatch.setenv("CUSTOM_KEY", "custom-valid")
    monkeypatch.setattr(hc, "_KEY_FORMAT_PATTERNS", {"CUSTOM_KEY": ("custom-", re.compile(r"^custom-"))})
    monkeypatch.setattr(hc, "_KEY_VALIDATION_ENDPOINTS", {})

    result = hc._api_key_health_result("CUSTOM_KEY")

    assert result["name"] == "key:CUSTOM_KEY"
    assert result["status"] == hc.STATUS_OK
    assert result["detail"] == "key set, format ok (no ping endpoint)"
