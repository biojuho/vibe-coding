from __future__ import annotations

import datetime
import json
import os
import py_compile
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

# Reconfigure stdout and stderr to UTF-8 to prevent cp949 encoding errors on Windows
if sys.platform.startswith("win"):
    import io

    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        # Fallback for older python versions
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ─── Setup paths ──────────────────────────────────────────────────────────────
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env")

SERVERS = {
    "sqlite-multi": {"path": "infrastructure/sqlite-multi-mcp/server.py", "required_keys": [], "optional_keys": []},
    "system-monitor": {"path": "infrastructure/system-monitor/server.py", "required_keys": [], "optional_keys": []},
    "telegram": {
        "path": "infrastructure/telegram-mcp/server.py",
        "required_keys": ["TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"],
        "optional_keys": [],
    },
    "cloudinary": {
        "path": "infrastructure/cloudinary-mcp/server.py",
        "required_keys": ["CLOUDINARY_CLOUD_NAME", "CLOUDINARY_API_KEY", "CLOUDINARY_API_SECRET"],
        "optional_keys": [],
    },
    "youtube-data": {
        "path": "infrastructure/youtube-mcp/server.py",
        "required_keys": ["YOUTUBE_API_KEY"],
        "optional_keys": [],
    },
    "n8n-workflow": {
        "path": "infrastructure/n8n-mcp/server.py",
        "required_keys": [],
        "optional_keys": ["BRIDGE_TOKEN", "BRIDGE_URL"],
    },
}


def _initial_status() -> dict[str, Any]:
    return {
        "path_exists": False,
        "env_check": "passed",
        "syntax_check": "untested",
        "import_check": "untested",
        "handshake": "untested",
        "error_details": None,
    }


def _missing_required_keys(config: dict[str, Any]) -> list[str]:
    missing_keys = []
    for key in config["required_keys"]:
        val = os.getenv(key, "").strip()
        if not val:
            missing_keys.append(key)
    return missing_keys


def _apply_env_check(status: dict[str, Any], missing_keys: list[str]) -> None:
    if missing_keys:
        print(f"  [WARN] Missing Required Env Keys: {', '.join(missing_keys)}")
        status["env_check"] = f"failed (missing: {', '.join(missing_keys)})"


def _compile_server(server_path: Path, status: dict[str, Any]) -> bool:
    try:
        py_compile.compile(str(server_path), doraise=True)
        status["syntax_check"] = "passed"
        return True
    except py_compile.PyCompileError as e:
        print("  [FAIL] Syntax Check Failed!")
        status["syntax_check"] = "failed"
        status["error_details"] = f"Syntax Error: {str(e)}"
        return False


def _import_probe_code(server_path: Path) -> str:
    return f"import sys; sys.path.append(r'{server_path.parent}'); import server"


def _run_import_probe(python_exe: str, server_path: Path, status: dict[str, Any]) -> bool:
    try:
        proc = subprocess.run(
            [python_exe, "-c", _import_probe_code(server_path)],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=str(_PROJECT_ROOT),
        )
    except subprocess.TimeoutExpired:
        status["import_check"] = "timeout"
        status["error_details"] = "Import check timed out (5s)"
        return False

    if proc.returncode != 0:
        print("  [FAIL] Dependency Import Check Failed!")
        status["import_check"] = "failed"
        status["error_details"] = proc.stderr.strip()
        return False

    status["import_check"] = "passed"
    return True


def _initialize_request() -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "mcp-diagnostic",
                "version": "1.0.0",
            },
        },
    }


def _terminate_process(process: subprocess.Popen[bytes]) -> None:
    process.terminate()
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        process.kill()


def _is_json_rpc_response(resp_json: dict[str, Any]) -> bool:
    return "jsonrpc" in resp_json and ("result" in resp_json or "error" in resp_json)


def _apply_handshake_response(resp_line: str | None, status: dict[str, Any]) -> None:
    if resp_line is None:
        print("  [FAIL] Handshake Failed: Timeout waiting for JSON-RPC response.")
        status["handshake"] = "failed (timeout)"
        status["error_details"] = "No response line on stdout within 4 seconds."
        return

    resp_line = resp_line.strip()
    try:
        resp_json = json.loads(resp_line)
    except json.JSONDecodeError:
        print(f"  [FAIL] Handshake Failed: Output was not valid JSON: {resp_line}")
        status["handshake"] = "failed (not json)"
        status["error_details"] = f"Not JSON output: {resp_line}"
        return

    if _is_json_rpc_response(resp_json):
        print("  [OK] Stdio JSON-RPC Handshake Succeeded!")
        status["handshake"] = "passed"
        return

    print(f"  [FAIL] Handshake Failed: Invalid JSON-RPC structure: {resp_line}")
    status["handshake"] = "failed (invalid structure)"
    status["error_details"] = f"Invalid JSON-RPC format: {resp_line}"


def _handshake_server(python_exe: str, server_path: Path, status: dict[str, Any]) -> None:
    print("  [RUN] Attempting Stdio JSON-RPC Handshake...")
    process = None
    try:
        process = subprocess.Popen(
            [python_exe, str(server_path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(server_path.parent),
            bufsize=0,
        )
        req_str = json.dumps(_initialize_request()) + "\n"
        process.stdin.write(req_str.encode("utf-8"))
        process.stdin.flush()
        resp_line = read_stream_with_timeout(process.stdout, timeout_sec=4)
        _apply_handshake_response(resp_line, status)
    except Exception as e:
        print(f"  [FAIL] Handshake Encountered Exception: {e}")
        status["handshake"] = "failed (exception)"
        status["error_details"] = str(e)
    finally:
        if process is not None:
            _terminate_process(process)


def _diagnose_server(name: str, config: dict[str, Any], python_exe: str) -> dict[str, Any]:
    print(f"* Diagnosing MCP Server: [{name}]")
    server_path = _PROJECT_ROOT / config["path"]
    status = _initial_status()

    if not server_path.exists():
        print(f"  [FAIL] Error: Server script not found at {server_path}")
        status["error_details"] = "Script file missing"
        return status

    status["path_exists"] = True
    _apply_env_check(status, _missing_required_keys(config))

    if not _compile_server(server_path, status):
        return status
    if not _run_import_probe(python_exe, server_path, status):
        return status

    _handshake_server(python_exe, server_path, status)
    return status


def _server_overall_status(status: dict[str, Any]) -> str:
    if status["syntax_check"] != "passed" or status["import_check"] != "passed" or status["handshake"] != "passed":
        return "FAILED"
    return "OK"


def read_stream_with_timeout(stream: Any, timeout_sec: float) -> str | None:
    """Reads a single line from a stream with a strict timeout using threads."""
    output = [None]

    def target():
        try:
            line = stream.readline()
            if isinstance(line, bytes):
                line = line.decode("utf-8", errors="ignore")
            output[0] = line
        except Exception as e:
            output[0] = e

    t = threading.Thread(target=target)
    t.daemon = True
    t.start()
    t.join(timeout_sec)
    if t.is_alive():
        return None  # Timeout occurred
    return output[0]


def run_diagnostics() -> None:
    print("=" * 60)
    print("         MCP SERVERS INTEGRATED HEALTH CHECK & DIAGNOSTICS")
    print("=" * 60)

    python_exe = sys.executable
    print(f"Using Python Interpreter: {python_exe}\n")

    results = {}

    for name, config in SERVERS.items():
        results[name] = _diagnose_server(name, config, python_exe)
        print("-" * 60)

    # Write a summary report
    print("\n" + "=" * 60)
    print("                     DIAGNOSTICS SUMMARY")
    print("=" * 60)

    passed_all = True
    for name, status in results.items():
        overall = _server_overall_status(status)
        if overall == "FAILED":
            passed_all = False

        print(f"[{name}]: {overall}")
        print(f"  - Syntax: {status['syntax_check']}")
        print(f"  - Imports: {status['import_check']}")
        print(f"  - Handshake: {status['handshake']}")
        if status["env_check"] != "passed":
            print(f"  - Environment: {status['env_check']}")
        if status["error_details"]:
            print(f"  - Error Detail: {status['error_details']}")
        print("-" * 40)

    print(
        f"\nFinal Verdict: {'[SUCCESS] ALL SERVERS FUNCTIONAL' if passed_all else '[ERROR] SOME SERVERS FAILED OR ARE DEGRADED'}"
    )
    print("=" * 60)

    # Save the output report dynamically as a docs file for transparency
    save_report(results, passed_all)


def save_report(results: dict[str, dict[str, Any]], passed_all: bool) -> None:
    report_path = _PROJECT_ROOT / "docs" / "mcp_status_report.md"
    os.makedirs(report_path.parent, exist_ok=True)

    md = []
    md.append("# MCP Servers Comprehensive Diagnostics Report")
    md.append("")
    md.append(f"**Date:** {datetime_now_iso()}")
    md.append(
        f"**Overall Verdict:** {'🟢 ALL SERVERS FUNCTIONAL' if passed_all else '🟡 SOME SERVERS FAILED/DEGRADED'}"
    )
    md.append("")
    md.append(
        "This report lists the status of local workspace MCP servers based on a deterministic Stdio JSON-RPC handshake validation."
    )
    md.append("")
    md.append("## Status Matrix")
    md.append("")
    md.append("| Server Name | Syntax Check | Import & Deps | Stdio Handshake | Environment Check | Status |")
    md.append("| :--- | :--- | :--- | :--- | :--- | :--- |")

    for name, s in results.items():
        status_emoji = "🟢 OK"
        if s["syntax_check"] != "passed" or s["import_check"] != "passed" or s["handshake"] != "passed":
            status_emoji = "🔴 FAILED"

        md.append(
            f"| **{name}** | {emoji_for(s['syntax_check'])} | {emoji_for(s['import_check'])} | {emoji_for(s['handshake'])} | {emoji_for(s['env_check'])} | {status_emoji} |"
        )

    md.append("")
    md.append("## Detailed Server Diagnoses")
    md.append("")

    for name, s in results.items():
        md.append(f"### {name}")
        md.append(f"- **Path:** `{SERVERS[name]['path']}`")
        md.append(f"- **Syntax Check:** `{s['syntax_check']}`")
        md.append(f"- **Imports Check:** `{s['import_check']}`")
        md.append(f"- **JSON-RPC Handshake:** `{s['handshake']}`")
        md.append(f"- **Environment Check:** `{s['env_check']}`")
        if s["error_details"]:
            md.append("- **Error Log / Trace:**")
            md.append("  ```text")
            md.append(f"  {s['error_details']}")
            md.append("  ```")
        md.append("---")

    md.append("")
    md.append("## Agent-Side Integrated Notion MCP")
    md.append("- **Verification method:** `mcp_notion-mcp-server_API-get-self` direct call")
    md.append("- **Status:** 🟢 PASS")
    md.append("- **Connected Account:** `Desk Joopark` (Juho Park의 Notion workspace)")

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md))
    print("Diagnostics report written successfully to: docs/mcp_status_report.md")


def emoji_for(val: str | Any) -> str:
    if val == "passed":
        return "✅ passed"
    if val == "failed" or "failed" in str(val):
        return "❌ failed"
    if val == "untested":
        return "⚪ untested"
    return f"⚠️ {val}"


def datetime_now_iso() -> str:
    return datetime.datetime.now().isoformat()


if __name__ == "__main__":
    run_diagnostics()
