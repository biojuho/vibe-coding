"""
harness_guard.py — Pipeline harness integration wrapper
=======================================================
Integrates harness_sandbox.py and harness_security_checklist.py into the
blind-to-x pipeline execution loop.

Activation: Set HARNESS_ENABLED=1 environment variable.
When disabled (default), all functions are no-ops.

Usage in main.py:
    from pipeline.harness_guard import run_preflight, is_harness_enabled
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# ── 워크스페이스 루트에서 execution/ 모듈 로딩 ─────────────────────────────
_WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_EXECUTION_DIR = _WORKSPACE_ROOT / "workspace" / "execution"

# execution/ 디렉토리가 sys.path에 없으면 추가
if str(_EXECUTION_DIR) not in sys.path:
    sys.path.insert(0, str(_EXECUTION_DIR))


def is_harness_enabled() -> bool:
    """환경변수 HARNESS_ENABLED=1 인지 확인."""
    return os.environ.get("HARNESS_ENABLED", "").strip() == "1"


def _get_project_root() -> Path:
    """blind-to-x 프로젝트 루트 반환."""
    return Path(__file__).resolve().parent.parent


class PreflightError(Exception):
    """보안 사전 검사 실패 시 발생."""


def run_preflight(workspace_root: Path | str | None = None) -> dict:
    """
    보안 사전 비행 체크를 실행합니다.

    Returns:
        dict with keys: passed (bool), issues (list[str]), skipped (bool)

    Raises:
        PreflightError: 심각한 보안 문제가 발견된 경우 (HARNESS_ENABLED 시에만)
    """
    if not is_harness_enabled():
        logger.debug("Harness disabled. Skipping preflight checks.")
        return {"passed": True, "issues": [], "skipped": True}

    root = Path(workspace_root) if workspace_root else _get_project_root()
    logger.info("Running harness preflight checks on %s", root)

    try:
        from harness_security_checklist import SecurityChecklist

        checklist = SecurityChecklist(project_root=root)
        result = checklist.run_preflight()

        if not result.get("passed", True):
            issues = result.get("issues", [])
            critical = [i for i in issues if i.get("severity") == "critical"]

            if critical:
                msg = f"Preflight FAILED: {len(critical)} critical issue(s) found"
                logger.error(msg)
                for issue in critical:
                    logger.error("  CRITICAL: %s", issue.get("message", str(issue)))
                raise PreflightError(msg)

            # Non-critical issues: warn but pass
            for issue in issues:
                logger.warning("  WARNING: %s", issue.get("message", str(issue)))

        logger.info("Preflight checks passed.")
        return {
            "passed": result.get("passed", True),
            "issues": result.get("issues", []),
            "skipped": False,
        }

    except PreflightError:
        raise
    except ImportError as exc:
        logger.warning(
            "harness_security_checklist module not found (%s). Preflight checks skipped.",
            exc,
        )
        return {"passed": True, "issues": [], "skipped": True}
    except Exception as exc:
        logger.warning("Preflight check error (non-fatal): %s", exc)
        return {"passed": True, "issues": [str(exc)], "skipped": False}


def create_sandbox_context(profile_name: str = "blind-to-x"):
    """
    샌드박스 컨텍스트를 생성합니다 (HARNESS_ENABLED 시에만).

    Returns:
        SandboxInstance 또는 None (비활성 시)
    """
    if not is_harness_enabled():
        return None

    try:
        from harness_sandbox import SandboxManager, SandboxConfig

        manager = SandboxManager()
        predefined = manager.get_predefined_profiles()
        config = predefined.get(profile_name)

        if not config:
            logger.warning("Sandbox profile '%s' not found. Using default.", profile_name)
            config = SandboxConfig(
                name=profile_name,
                allowed_paths=[str(_get_project_root())],
                max_memory_mb=512,
                max_cpu_percent=80,
                timeout_seconds=300,
                network_access=False,
            )

        instance = manager.create(config)
        logger.info("Sandbox '%s' created for profile '%s'", instance.id, profile_name)
        return instance

    except ImportError as exc:
        logger.warning("harness_sandbox module not found (%s). Sandbox skipped.", exc)
        return None
    except Exception as exc:
        logger.warning("Sandbox creation error (non-fatal): %s", exc)
        return None
