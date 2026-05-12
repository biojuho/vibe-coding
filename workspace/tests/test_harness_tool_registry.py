from __future__ import annotations

from execution.harness_tool_registry import (
    RiskLevel,
    ToolPermission,
    ToolRegistry,
    _build_default_permissions,
    _execute_dangerous_permissions,
    _network_dangerous_permissions,
    _read_safe_permissions,
    _write_moderate_permissions,
)


def test_default_permission_helpers_preserve_registry_shape() -> None:
    permissions = _build_default_permissions(r"C:\repo")
    by_name = {perm.name: perm for perm in permissions}

    assert sorted(by_name) == [
        "file_create",
        "file_delete",
        "file_read",
        "file_write",
        "grep_search",
        "http_request",
        "list_dir",
        "mcp_call",
        "python_exec",
        "shell_command",
    ]
    assert by_name["file_read"].risk_level is RiskLevel.SAFE
    assert by_name["file_write"].allowed_path_globs == (
        "C:/repo/projects/*",
        "C:/repo/workspace/*",
        "C:/repo/.tmp/*",
        "C:/repo/.ai/*",
    )
    assert by_name["file_delete"].requires_hitl is True
    assert by_name["http_request"].max_invocations_per_session == 5


def test_permission_group_helpers_keep_expected_counts() -> None:
    assert len(_read_safe_permissions("C:/repo")) == 3
    assert len(_write_moderate_permissions("a", "b", "c", "d")) == 3
    assert len(_execute_dangerous_permissions()) == 2
    assert len(_network_dangerous_permissions()) == 2


def test_authorize_records_hitl_denial_and_approval() -> None:
    registry = ToolRegistry.default("C:/repo")

    denied = registry.authorize("file_delete", path="C:/repo/.tmp/out.txt", agent_id="agent-a")

    assert denied.allowed is False
    assert denied.requires_hitl is True
    assert registry.invocation_log[-1].result == "denied"
    assert registry.invocation_log[-1].agent_id == "agent-a"

    registry.set_hitl_handler(lambda tool, path: tool == "file_delete" and path == "C:/repo/.tmp/out.txt")
    approved = registry.authorize("file_delete", path="C:/repo/.tmp/out.txt")

    assert approved.allowed is True
    assert approved.requires_hitl is True
    assert registry.invocation_log[-1].result == "allowed"


def test_authorize_preserves_budget_and_path_guards() -> None:
    registry = ToolRegistry()
    registry.register(
        ToolPermission(
            name="limited_read",
            allowed_path_globs=("C:/repo/*",),
            max_invocations_per_session=1,
        )
    )

    traversal = registry.check("limited_read", path="C:/repo/projects/../secret.txt")
    first = registry.authorize("limited_read", path="C:/repo/file.txt")
    second = registry.authorize("limited_read", path="C:/repo/other.txt")

    assert traversal.allowed is False
    assert "Path traversal" in traversal.reason
    assert first.allowed is True
    assert second.allowed is False
    assert "Session budget exhausted" in second.reason
