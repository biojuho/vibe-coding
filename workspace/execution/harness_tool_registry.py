"""Harness Tool Permission Registry — deny-by-default tool authorization for agent execution.

Part of Harness Engineering AI Phase 0 (ADR-025).

The registry enforces *what* actions agents are allowed to take by maintaining an
explicit allowlist of tools and their constraints.  Every tool invocation must be
checked against the registry before execution:

    registry = ToolRegistry.default()
    decision = registry.check("file_read", path="/projects/blind-to-x/main.py")
    if decision.allowed:
        ...  # proceed

Design principles:
  - Deny-by-default: unregistered tools are never allowed.
  - Path-scoped: write/execute permissions are scoped to allowlisted glob patterns.
  - Budget-limited: per-session invocation caps prevent runaway agents.
  - HITL-flagged: dangerous or irreversible actions require human-in-the-loop approval.
"""

from __future__ import annotations

import fnmatch
import logging
import os
import re
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable, Optional, Sequence

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Risk classification
# ---------------------------------------------------------------------------


class RiskLevel(Enum):
    """Tool risk classification, from safest to most dangerous."""

    SAFE = "safe"
    MODERATE = "moderate"
    DANGEROUS = "dangerous"


# ---------------------------------------------------------------------------
# Permission model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ToolPermission:
    """Declarative permission for a single tool.

    Attributes:
        name: Canonical tool identifier (e.g. ``"file_read"``).
        risk_level: Safety classification.
        allowed_path_globs: If non-empty, the tool may only operate on paths
            matching at least one of these globs.  Empty means "no path
            constraint" (useful for tools like ``grep``).
        requires_hitl: When *True*, the tool invocation is paused and presented
            to a human for explicit approval before execution.
        max_invocations_per_session: Hard cap on how many times this tool may
            be called in a single agent session.  ``0`` means unlimited.
        description: Optional human-readable explanation.
    """

    name: str
    risk_level: RiskLevel = RiskLevel.SAFE
    allowed_path_globs: tuple[str, ...] = ()
    requires_hitl: bool = False
    max_invocations_per_session: int = 0
    description: str = ""


@dataclass
class CheckResult:
    """Outcome of a permission check."""

    allowed: bool
    reason: str = ""
    requires_hitl: bool = False


@dataclass
class InvocationRecord:
    """Immutable audit entry for one tool call."""

    tool_name: str
    agent_id: str
    timestamp: float
    path: str | None
    risk_level: RiskLevel
    result: str  # "allowed", "denied", "hitl_pending"
    reason: str = ""


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class ToolRegistry:
    """Central tool permission registry with deny-by-default policy.

    Usage::

        registry = ToolRegistry()
        registry.register(ToolPermission(name="file_read", risk_level=RiskLevel.SAFE))
        decision = registry.check("file_read", path="/some/path")
    """

    def __init__(self) -> None:
        self._permissions: dict[str, ToolPermission] = {}
        self._session_counts: dict[str, int] = {}
        self._invocation_log: list[InvocationRecord] = []
        self._hitl_handler: Optional[Callable[[str, str | None], bool]] = None

    # -- Registration -------------------------------------------------------

    def register(self, perm: ToolPermission) -> None:
        """Register a tool permission.  Overwrites any existing entry."""
        self._permissions[perm.name] = perm

    def register_many(self, perms: Sequence[ToolPermission]) -> None:
        for p in perms:
            self.register(p)

    def set_hitl_handler(self, handler: Callable[[str, str | None], bool]) -> None:
        """Set the human-in-the-loop callback.

        The handler receives ``(tool_name, path)`` and must return
        *True* to approve or *False* to deny.
        """
        self._hitl_handler = handler

    # -- Querying -----------------------------------------------------------

    def is_registered(self, tool_name: str) -> bool:
        return tool_name in self._permissions

    def get_permission(self, tool_name: str) -> ToolPermission | None:
        return self._permissions.get(tool_name)

    @property
    def registered_tools(self) -> list[str]:
        return sorted(self._permissions)

    @property
    def invocation_log(self) -> list[InvocationRecord]:
        return list(self._invocation_log)

    # -- Checking -----------------------------------------------------------

    def check(
        self,
        tool_name: str,
        *,
        path: str | None = None,
        agent_id: str = "default",
    ) -> CheckResult:
        """Evaluate whether *tool_name* is allowed on *path*.

        Returns a :class:`CheckResult` describing the decision.  This method
        is pure — it does **not** increment the session counter or log the
        invocation.  Use :meth:`authorize` for the side-effecting version.
        """
        perm = self._permissions.get(tool_name)
        if perm is None:
            return CheckResult(allowed=False, reason=f"Tool '{tool_name}' is not registered (deny-by-default)")

        # Budget check
        cap = perm.max_invocations_per_session
        used = self._session_counts.get(tool_name, 0)
        if cap > 0 and used >= cap:
            return CheckResult(
                allowed=False,
                reason=f"Session budget exhausted for '{tool_name}' ({used}/{cap})",
            )

        # Path check
        if perm.allowed_path_globs and path:
            normalized = _normalize_path(path)
            if not any(fnmatch.fnmatch(normalized, g) for g in perm.allowed_path_globs):
                return CheckResult(
                    allowed=False,
                    reason=f"Path '{path}' not covered by allowed globs for '{tool_name}'",
                )

        # Path traversal check
        if path and _has_path_traversal(path):
            return CheckResult(allowed=False, reason=f"Path traversal detected in '{path}'")

        # HITL flag
        if perm.requires_hitl:
            return CheckResult(allowed=True, requires_hitl=True, reason="Requires human approval")

        return CheckResult(allowed=True, reason="Allowed")

    def authorize(
        self,
        tool_name: str,
        *,
        path: str | None = None,
        agent_id: str = "default",
    ) -> CheckResult:
        """Check + record.  Increments session counter and writes audit log.

        For dangerous tools with ``requires_hitl=True``, calls the HITL
        handler if one is registered.  If no handler is set, the call is
        denied with a clear reason.
        """
        result = self.check(tool_name, path=path, agent_id=agent_id)

        perm = self._permissions.get(tool_name)
        risk = perm.risk_level if perm else RiskLevel.DANGEROUS

        if result.allowed and result.requires_hitl:
            if self._hitl_handler is None:
                result = CheckResult(
                    allowed=False,
                    reason="HITL required but no handler registered",
                    requires_hitl=True,
                )
                status = "denied"
            else:
                approved = self._hitl_handler(tool_name, path)
                if not approved:
                    result = CheckResult(allowed=False, reason="HITL denied by human", requires_hitl=True)
                    status = "denied"
                else:
                    status = "allowed"
        elif result.allowed:
            status = "allowed"
        else:
            status = "denied"

        # Record
        self._invocation_log.append(
            InvocationRecord(
                tool_name=tool_name,
                agent_id=agent_id,
                timestamp=time.time(),
                path=path,
                risk_level=risk,
                result=status,
                reason=result.reason,
            )
        )

        if result.allowed:
            self._session_counts[tool_name] = self._session_counts.get(tool_name, 0) + 1

        return result

    def reset_session(self) -> None:
        """Reset per-session counters (e.g. at the start of a new agent run)."""
        self._session_counts.clear()

    def clear_log(self) -> None:
        """Clear the invocation audit log."""
        self._invocation_log.clear()

    # -- Factory ------------------------------------------------------------

    @classmethod
    def default(cls, workspace_root: str | Path | None = None) -> "ToolRegistry":
        """Create a registry pre-loaded with the standard tool categories.

        Uses the workspace root to scope write/execute paths.
        """
        if workspace_root is None:
            workspace_root = Path(__file__).resolve().parents[1]
        root = str(Path(workspace_root).resolve())

        registry = cls()
        registry.register_many(_build_default_permissions(root))
        return registry


# ---------------------------------------------------------------------------
# Default permission sets
# ---------------------------------------------------------------------------


def _build_default_permissions(workspace_root: str) -> list[ToolPermission]:
    """Pre-built permission categories aligned with ADR-025."""

    # Normalize for glob matching
    root = workspace_root.replace("\\", "/")

    projects_glob = f"{root}/projects/*"
    workspace_glob = f"{root}/workspace/*"
    tmp_glob = f"{root}/.tmp/*"
    ai_glob = f"{root}/.ai/*"

    return [
        # ── READ_SAFE ──────────────────────────────────────────────
        ToolPermission(
            name="file_read",
            risk_level=RiskLevel.SAFE,
            description="Read any file within the workspace",
            allowed_path_globs=(f"{root}/*",),
        ),
        ToolPermission(
            name="list_dir",
            risk_level=RiskLevel.SAFE,
            description="List directory contents",
            allowed_path_globs=(f"{root}/*",),
        ),
        ToolPermission(
            name="grep_search",
            risk_level=RiskLevel.SAFE,
            description="Search file contents",
            allowed_path_globs=(f"{root}/*",),
        ),
        # ── WRITE_MODERATE ─────────────────────────────────────────
        ToolPermission(
            name="file_write",
            risk_level=RiskLevel.MODERATE,
            allowed_path_globs=(projects_glob, workspace_glob, tmp_glob, ai_glob),
            max_invocations_per_session=50,
            description="Write files within project/workspace/tmp/.ai directories",
        ),
        ToolPermission(
            name="file_create",
            risk_level=RiskLevel.MODERATE,
            allowed_path_globs=(projects_glob, workspace_glob, tmp_glob, ai_glob),
            max_invocations_per_session=30,
            description="Create new files within project/workspace/tmp/.ai directories",
        ),
        ToolPermission(
            name="file_delete",
            risk_level=RiskLevel.MODERATE,
            requires_hitl=True,
            allowed_path_globs=(tmp_glob,),
            max_invocations_per_session=10,
            description="Delete files — only in .tmp, requires human approval",
        ),
        # ── EXECUTE_DANGEROUS ──────────────────────────────────────
        ToolPermission(
            name="shell_command",
            risk_level=RiskLevel.DANGEROUS,
            requires_hitl=True,
            max_invocations_per_session=20,
            description="Execute shell commands — requires human approval",
        ),
        ToolPermission(
            name="python_exec",
            risk_level=RiskLevel.DANGEROUS,
            requires_hitl=True,
            max_invocations_per_session=10,
            description="Execute Python scripts — requires human approval",
        ),
        # ── NETWORK_DANGEROUS ─────────────────────────────────────
        ToolPermission(
            name="http_request",
            risk_level=RiskLevel.DANGEROUS,
            requires_hitl=True,
            max_invocations_per_session=5,
            description="Make external HTTP requests — requires human approval",
        ),
        ToolPermission(
            name="mcp_call",
            risk_level=RiskLevel.DANGEROUS,
            requires_hitl=True,
            max_invocations_per_session=10,
            description="Invoke MCP server tools — requires human approval",
        ),
    ]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TRAVERSAL_PATTERN = re.compile(r"(^|[\\/])\.\.($|[\\/])")


def _normalize_path(path: str) -> str:
    """Normalize a path for consistent glob matching."""
    return os.path.normpath(path).replace("\\", "/")


def _has_path_traversal(path: str) -> bool:
    """Detect ``..`` segments that could escape the workspace."""
    return bool(_TRAVERSAL_PATTERN.search(path))
