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
