from pathlib import Path

import execution.mcp_diagnostic as mcp_diagnostic


def test_initial_status_tracks_untested_checks():
    assert mcp_diagnostic._initial_status() == {
        "path_exists": False,
        "env_check": "passed",
        "syntax_check": "untested",
        "import_check": "untested",
        "handshake": "untested",
        "error_details": None,
    }


def test_missing_required_keys_reads_environment(monkeypatch):
    monkeypatch.setenv("MCP_PRESENT_KEY", " configured ")
    monkeypatch.delenv("MCP_MISSING_KEY", raising=False)

    assert mcp_diagnostic._missing_required_keys({"required_keys": ["MCP_PRESENT_KEY", "MCP_MISSING_KEY"]}) == [
        "MCP_MISSING_KEY"
    ]


def test_initialize_request_matches_mcp_json_rpc_shape():
    request = mcp_diagnostic._initialize_request()

    assert request["jsonrpc"] == "2.0"
    assert request["id"] == 1
    assert request["method"] == "initialize"
    assert request["params"]["protocolVersion"] == "2024-11-05"
    assert request["params"]["clientInfo"] == {
        "name": "mcp-diagnostic",
        "version": "1.0.0",
    }


def test_apply_handshake_response_sets_passed_for_json_rpc_result():
    status = mcp_diagnostic._initial_status()

    mcp_diagnostic._apply_handshake_response('{"jsonrpc":"2.0","id":1,"result":{}}', status)

    assert status["handshake"] == "passed"
    assert status["error_details"] is None


def test_apply_handshake_response_records_not_json():
    status = mcp_diagnostic._initial_status()

    mcp_diagnostic._apply_handshake_response("not-json", status)

    assert status["handshake"] == "failed (not json)"
    assert status["error_details"] == "Not JSON output: not-json"


def test_diagnose_server_returns_missing_path_status(monkeypatch, tmp_path):
    monkeypatch.setattr(mcp_diagnostic, "_PROJECT_ROOT", tmp_path)

    status = mcp_diagnostic._diagnose_server(
        "missing",
        {"path": "missing/server.py", "required_keys": [], "optional_keys": []},
        "python",
    )

    assert status == {
        "path_exists": False,
        "env_check": "passed",
        "syntax_check": "untested",
        "import_check": "untested",
        "handshake": "untested",
        "error_details": "Script file missing",
    }


def test_server_overall_status_requires_core_checks_to_pass():
    passed_status = mcp_diagnostic._initial_status()
    passed_status.update(
        {
            "syntax_check": "passed",
            "import_check": "passed",
            "handshake": "passed",
        }
    )
    failed_status = passed_status | {"handshake": "failed (timeout)"}

    assert mcp_diagnostic._server_overall_status(passed_status) == "OK"
    assert mcp_diagnostic._server_overall_status(failed_status) == "FAILED"


def test_import_probe_code_points_at_server_parent():
    server_path = Path("infrastructure/example/server.py")

    probe_code = mcp_diagnostic._import_probe_code(server_path)

    assert "sys.path.append" in probe_code
    assert "infrastructure\\example" in probe_code or "infrastructure/example" in probe_code
    assert probe_code.endswith("import server")
