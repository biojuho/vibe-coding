"""Harness Security Checklist — pre-flight & runtime security validation for agent execution.

Part of Harness Engineering AI Phase 0 (ADR-025).

Provides layered security checks that run before and during agent execution:
  1. Pre-flight checks: environment, credentials, config validity.
  2. Runtime guards: path traversal, secret scanning, command injection detection.
  3. Audit trail: structured logging of every security-relevant event.

Usage::

    checklist = SecurityChecklist(workspace_root="/path/to/vibe-coding")
    report = checklist.run_preflight()
    if not report.passed:
        for issue in report.issues:
            print(issue)

    # Runtime — validate before executing
    result = checklist.validate_path("/some/path")
    result = checklist.scan_for_secrets("some code content")
"""

from __future__ import annotations

import logging
import os
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Sequence

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Severity & Issue models
# ---------------------------------------------------------------------------


class Severity(Enum):
    """Issue severity level."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass(frozen=True)
class SecurityIssue:
    """A single security finding."""

    check_name: str
    severity: Severity
    message: str
    remediation: str = ""

    def __str__(self) -> str:
        icon = {"info": "ℹ️", "warning": "⚠️", "critical": "🚨"}.get(self.severity.value, "❓")
        return f"{icon} [{self.check_name}] {self.message}"


@dataclass
class SecurityReport:
    """Aggregated result of security checks."""

    issues: list[SecurityIssue] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    @property
    def passed(self) -> bool:
        """True if no critical issues were found."""
        return not any(i.severity == Severity.CRITICAL for i in self.issues)

    @property
    def has_warnings(self) -> bool:
        return any(i.severity == Severity.WARNING for i in self.issues)

    @property
    def critical_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.CRITICAL)

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.WARNING)

    def add(self, issue: SecurityIssue) -> None:
        self.issues.append(issue)
        if issue.severity == Severity.CRITICAL:
            logger.warning("CRITICAL security issue: %s", issue.message)

    def summary(self) -> str:
        """One-line summary string."""
        icon = "✅" if self.passed else "🚨"
        parts = [f"{icon} Security Report"]
        if self.critical_count:
            parts.append(f"{self.critical_count} critical")
        if self.warning_count:
            parts.append(f"{self.warning_count} warnings")
        if not self.issues:
            parts.append("all clear")
        return " — ".join(parts)


# ---------------------------------------------------------------------------
# Secret patterns
# ---------------------------------------------------------------------------

# Compiled patterns for detecting secrets in code/output
_SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("AWS Access Key", re.compile(r"AKIA[0-9A-Z]{16}", re.ASCII)),
    ("AWS Secret Key", re.compile(r"(?i)aws_secret_access_key\s*[=:]\s*\S{20,}", re.ASCII)),
    ("GitHub Token", re.compile(r"gh[ps]_[A-Za-z0-9_]{36,}", re.ASCII)),
    ("GitHub Fine-Grained Token", re.compile(r"github_pat_[A-Za-z0-9_]{22,}", re.ASCII)),
    ("OpenAI API Key", re.compile(r"sk-[A-Za-z0-9]{20,}", re.ASCII)),
    ("Anthropic Key", re.compile(r"sk-ant-[A-Za-z0-9\-]{20,}", re.ASCII)),
    ("Supabase Key", re.compile(r"sbp_[A-Za-z0-9]{20,}", re.ASCII)),
    ("Slack Token", re.compile(r"xox[baprs]-[A-Za-z0-9\-]{10,}", re.ASCII)),
    (
        "Generic API Key",
        re.compile(r"(?i)(api[_-]?key|secret[_-]?key|access[_-]?token)\s*[=:]\s*['\"]?[A-Za-z0-9\-_]{20,}", re.ASCII),
    ),
    ("Private Key Block", re.compile(r"-----BEGIN\s+(RSA\s+)?PRIVATE KEY-----", re.ASCII)),
    ("Telegram Bot Token", re.compile(r"\d{8,10}:[A-Za-z0-9_-]{35}", re.ASCII)),
    ("Google Cloud Key", re.compile(r"AIza[A-Za-z0-9_\\-]{35}", re.ASCII)),
]


# ---------------------------------------------------------------------------
# Dangerous command patterns
# ---------------------------------------------------------------------------

_DANGEROUS_COMMANDS: list[tuple[str, re.Pattern[str]]] = [
    ("rm -rf /", re.compile(r"\brm\s+(-[a-zA-Z]*f[a-zA-Z]*\s+)?/\s", re.ASCII)),
    ("chmod 777", re.compile(r"\bchmod\s+777\b", re.ASCII)),
    ("curl | bash", re.compile(r"\bcurl\s+.*\|\s*(ba)?sh\b", re.ASCII)),
    ("wget | bash", re.compile(r"\bwget\s+.*\|\s*(ba)?sh\b", re.ASCII)),
    ("eval()", re.compile(r"\beval\s*\(", re.ASCII)),
    ("exec()", re.compile(r"\bexec\s*\(", re.ASCII)),
    ("os.system()", re.compile(r"\bos\.system\s*\(", re.ASCII)),
    ("subprocess.call without list", re.compile(r"subprocess\.\w+\(['\"]", re.ASCII)),
    ("SQL injection risk", re.compile(r"f['\"].*SELECT.*\{", re.ASCII)),
    ("Format string SQL", re.compile(r"\.format\(.*\).*(?:SELECT|INSERT|UPDATE|DELETE)", re.ASCII | re.IGNORECASE)),
]


# ---------------------------------------------------------------------------
# Path traversal patterns
# ---------------------------------------------------------------------------

_TRAVERSAL_PATTERN = re.compile(r"(^|[\\/])\.\.($|[\\/])")
_NULL_BYTE = re.compile(r"\x00")


# ---------------------------------------------------------------------------
# Checklist
# ---------------------------------------------------------------------------


class SecurityChecklist:
    """Pre-flight and runtime security validation.

    Args:
        workspace_root: The root directory of the workspace. Used for
            path containment checks.
        allowed_roots: Additional roots that are considered safe (e.g.
            temp directories). If empty, only workspace_root is allowed.
    """

    def __init__(
        self,
        workspace_root: str | Path | None = None,
        allowed_roots: Sequence[str | Path] = (),
    ) -> None:
        if workspace_root is None:
            workspace_root = Path(__file__).resolve().parents[1]
        self._workspace_root = Path(workspace_root).resolve()
        self._allowed_roots = [Path(r).resolve() for r in allowed_roots] + [self._workspace_root]
        self._audit_log: list[dict] = []

    # -- Pre-flight checks --------------------------------------------------

    def run_preflight(self) -> SecurityReport:
        """Run all pre-flight security checks.

        Returns a SecurityReport with any issues found.
        """
        report = SecurityReport()

        self._check_workspace_exists(report)
        self._check_env_file_permissions(report)
        self._check_gitignore_secrets(report)
        self._check_credentials_not_committed(report)
        self._check_dotenv_not_exposed(report)

        self._log_audit("preflight", passed=report.passed, issues=len(report.issues))
        return report

    def _check_workspace_exists(self, report: SecurityReport) -> None:
        """Verify workspace root exists and is a directory."""
        if not self._workspace_root.is_dir():
            report.add(
                SecurityIssue(
                    check_name="workspace_exists",
                    severity=Severity.CRITICAL,
                    message=f"Workspace root does not exist: {self._workspace_root}",
                    remediation="Set a valid workspace_root path.",
                )
            )

    def _check_env_file_permissions(self, report: SecurityReport) -> None:
        """Check that .env files are not world-readable."""
        env_file = self._workspace_root / ".env"
        if not env_file.exists():
            report.add(
                SecurityIssue(
                    check_name="env_file_permissions",
                    severity=Severity.INFO,
                    message="No .env file found (OK if env vars are managed externally).",
                )
            )
            return

        # On Windows, os.stat mode checks are limited, so just check existence
        if os.name != "nt":
            mode = oct(env_file.stat().st_mode)[-3:]
            if mode[-1] != "0":
                report.add(
                    SecurityIssue(
                        check_name="env_file_permissions",
                        severity=Severity.WARNING,
                        message=f".env is world-readable (mode {mode})",
                        remediation="Run: chmod 600 .env",
                    )
                )

    def _check_gitignore_secrets(self, report: SecurityReport) -> None:
        """Verify .gitignore includes common secret patterns."""
        gitignore = self._workspace_root / ".gitignore"
        if not gitignore.exists():
            report.add(
                SecurityIssue(
                    check_name="gitignore_secrets",
                    severity=Severity.WARNING,
                    message="No .gitignore found — secrets may be committed.",
                    remediation="Create a .gitignore including .env, token.json, credentials.json",
                )
            )
            return

        content = gitignore.read_text(encoding="utf-8", errors="ignore")
        required_patterns = [".env", "token.json", "credentials.json"]
        missing = [p for p in required_patterns if p not in content]
        if missing:
            report.add(
                SecurityIssue(
                    check_name="gitignore_secrets",
                    severity=Severity.WARNING,
                    message=f".gitignore missing entries: {', '.join(missing)}",
                    remediation=f"Add to .gitignore: {', '.join(missing)}",
                )
            )

    def _check_credentials_not_committed(self, report: SecurityReport) -> None:
        """Check that credential files aren't in an obvious bad state."""
        sensitive_files = ["credentials.json", "token.json", "service_account.json"]
        for filename in sensitive_files:
            path = self._workspace_root / filename
            if path.exists():
                # File exists — check if gitignored
                gitignore = self._workspace_root / ".gitignore"
                if gitignore.exists():
                    content = gitignore.read_text(encoding="utf-8", errors="ignore")
                    if filename not in content:
                        report.add(
                            SecurityIssue(
                                check_name="credentials_committed",
                                severity=Severity.CRITICAL,
                                message=f"{filename} exists but not in .gitignore!",
                                remediation=f"Add {filename} to .gitignore immediately.",
                            )
                        )

    def _check_dotenv_not_exposed(self, report: SecurityReport) -> None:
        """Check that .env is not publicly accessible via a static server."""
        public_dirs = ["public", "dist", "build", "out", "static"]
        for d in public_dirs:
            exposed = self._workspace_root / d / ".env"
            if exposed.exists():
                report.add(
                    SecurityIssue(
                        check_name="dotenv_exposed",
                        severity=Severity.CRITICAL,
                        message=f".env found in public directory: {exposed}",
                        remediation=f"Remove {exposed} immediately.",
                    )
                )

    # -- Runtime guards -----------------------------------------------------

    def validate_path(self, path: str) -> SecurityReport:
        """Validate a file path for safety.

        Checks for:
        - Path traversal (``..``)
        - Null bytes
        - Containment within allowed roots
        """
        report = SecurityReport()

        # Null byte injection
        if _NULL_BYTE.search(path):
            report.add(
                SecurityIssue(
                    check_name="null_byte",
                    severity=Severity.CRITICAL,
                    message=f"Null byte detected in path: {repr(path)}",
                )
            )
            self._log_audit("path_validation", path=path, blocked=True, reason="null_byte")
            return report

        # Path traversal
        if _TRAVERSAL_PATTERN.search(path):
            report.add(
                SecurityIssue(
                    check_name="path_traversal",
                    severity=Severity.CRITICAL,
                    message=f"Path traversal detected: {path}",
                )
            )
            self._log_audit("path_validation", path=path, blocked=True, reason="traversal")
            return report

        # Containment check
        try:
            resolved = Path(path).resolve()
            contained = any(_is_subpath(resolved, root) for root in self._allowed_roots)
            if not contained:
                report.add(
                    SecurityIssue(
                        check_name="path_containment",
                        severity=Severity.CRITICAL,
                        message=f"Path escapes workspace: {path}",
                        remediation=f"All paths must be within: {self._allowed_roots}",
                    )
                )
                self._log_audit("path_validation", path=path, blocked=True, reason="escape")
        except (OSError, ValueError) as e:
            report.add(
                SecurityIssue(
                    check_name="path_resolution",
                    severity=Severity.CRITICAL,
                    message=f"Cannot resolve path: {path} ({e})",
                )
            )

        return report

    def scan_for_secrets(self, content: str) -> SecurityReport:
        """Scan text content for embedded secrets or credentials.

        Returns a report listing any secret patterns found.
        """
        report = SecurityReport()

        for secret_name, pattern in _SECRET_PATTERNS:
            if pattern.search(content):
                # Truncate the match for logging
                match = pattern.search(content)
                preview = match.group()[:8] + "..." if match else "???"
                report.add(
                    SecurityIssue(
                        check_name="secret_scan",
                        severity=Severity.CRITICAL,
                        message=f"{secret_name} detected (starts with: {preview})",
                        remediation="Remove secret from content and use environment variables.",
                    )
                )

        self._log_audit(
            "secret_scan",
            findings=len(report.issues),
            passed=report.passed,
        )
        return report

    def validate_command(self, command: str) -> SecurityReport:
        """Check a shell command for dangerous patterns.

        Returns a report with any dangerous patterns found.
        """
        report = SecurityReport()

        for pattern_name, pattern in _DANGEROUS_COMMANDS:
            if pattern.search(command):
                report.add(
                    SecurityIssue(
                        check_name="dangerous_command",
                        severity=Severity.CRITICAL,
                        message=f"Dangerous pattern detected: {pattern_name}",
                        remediation="Review command carefully before execution.",
                    )
                )

        self._log_audit(
            "command_validation",
            command=command[:100],
            findings=len(report.issues),
            passed=report.passed,
        )
        return report

    # -- Audit trail --------------------------------------------------------

    @property
    def audit_log(self) -> list[dict]:
        return list(self._audit_log)

    def _log_audit(self, event: str, **kwargs) -> None:
        """Append a structured audit entry."""
        entry = {
            "timestamp": time.time(),
            "event": event,
            **kwargs,
        }
        self._audit_log.append(entry)
        logger.debug("AUDIT: %s %s", event, kwargs)

    def clear_audit_log(self) -> None:
        """Clear the audit log."""
        self._audit_log.clear()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _is_subpath(path: Path, parent: Path) -> bool:
    """Check if *path* is equal to or a child of *parent*."""
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False
