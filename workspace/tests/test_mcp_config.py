from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_mcp_config_excludes_redundant_filesystem_server() -> None:
    config = json.loads((REPO_ROOT / ".mcp.json").read_text(encoding="utf-8"))
    servers = config["mcpServers"]

    assert "filesystem" not in servers
    assert "notion" in servers
    assert "sqlite-multi" in servers


def test_amazonq_legacy_workspace_config_matches_root_mcp_config() -> None:
    root_config = json.loads((REPO_ROOT / ".mcp.json").read_text(encoding="utf-8"))
    amazonq_config = json.loads((REPO_ROOT / ".amazonq" / "mcp.json").read_text(encoding="utf-8"))

    assert amazonq_config == root_config


def test_mcp_toggle_script_supports_guard_action() -> None:
    script_text = (REPO_ROOT / "workspace" / "scripts" / "mcp_toggle.ps1").read_text(encoding="utf-8")

    assert 'ValidateSet("Enable", "Disable", "Status", "Guard")' in script_text
    assert "function Show-AiToolStatus" in script_text
    assert '"Guard" {' in script_text


def test_code_review_graph_mcp_uses_python_interpreter() -> None:
    """code-review-graph MCP는 python 인터프리터로 기동해야 한다.

    기본값은 portable한 ``python``이지만, 이 워크스페이스에서는 ``code_review_graph``
    패키지가 ``python3.13``에만 설치돼 있고 기본 ``python``(=3.11)에는 없어
    launcher가 ``python3.13``로 핀돼 있다(commit a1aa434a). 두 형태 모두 허용하되
    그 외(셸/임의 명령)는 거부해 인터프리터 계약은 유지한다.
    """
    config = json.loads((REPO_ROOT / ".mcp.json").read_text(encoding="utf-8"))
    server = config["mcpServers"]["code-review-graph"]

    assert server["command"] in ("python", "python3.13")
    assert server["args"] == ["-m", "code_review_graph", "serve"]
    assert server["env"] == {"PYTHONUTF8": "1"}
