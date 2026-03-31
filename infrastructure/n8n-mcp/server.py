"""
n8n 워크플로우 MCP 서버
======================
n8n 브릿지 서버(localhost:9876)를 MCP 프로토콜로 노출하여
Claude Desktop 등 MCP 클라이언트에서 워크플로우를 트리거할 수 있게 합니다.

브릿지 서버 API:
  POST /execute  - 워크플로우 실행
  GET  /commands - 사용 가능한 명령어 목록
  GET  /history  - 실행 이력
  GET  /health   - 헬스체크
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    FastMCP = None

# ─── 환경 설정 ────────────────────────────────────────────────────────────────

_project_root = Path(__file__).resolve().parent.parent.parent
load_dotenv(_project_root / ".env")

logger = logging.getLogger(__name__)

BRIDGE_URL: str = os.getenv("BRIDGE_URL", "http://localhost:9876")
BRIDGE_TOKEN: str = os.getenv("BRIDGE_TOKEN", "")

_CONN_ERROR_MSG = f"브릿지 서버({BRIDGE_URL})에 연결할 수 없습니다."

# HTTP 세션 재사용
_session = requests.Session()
_session.headers.update({"Authorization": f"Bearer {BRIDGE_TOKEN}"})


# ─── 도구 함수 ────────────────────────────────────────────────────────────────


def _trigger_workflow(command: str, timeout: int = 600) -> dict[str, Any]:
    """브릿지 서버를 통해 워크플로우를 실행합니다."""
    try:
        resp = _session.post(
            f"{BRIDGE_URL}/execute",
            json={"command": command, "timeout": timeout},
            timeout=timeout + 30,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.ConnectionError:
        return {"status": "error", "message": _CONN_ERROR_MSG}
    except requests.Timeout:
        return {"status": "error", "message": f"요청이 타임아웃되었습니다 ({timeout + 30}초 초과)."}
    except requests.HTTPError as e:
        return {"status": "error", "message": f"HTTP 오류: {e.response.status_code}"}
    except Exception as e:
        logger.error("워크플로우 실행 실패: %s", e)
        return {"status": "error", "message": f"예상치 못한 오류: {e}"}


def _get_available_commands() -> dict[str, Any]:
    """브릿지 서버에서 사용 가능한 명령어 목록을 조회합니다."""
    try:
        resp = _session.get(f"{BRIDGE_URL}/commands", timeout=10)
        resp.raise_for_status()
        return resp.json()
    except requests.ConnectionError:
        return {"status": "error", "message": _CONN_ERROR_MSG}
    except Exception as e:
        logger.error("명령어 목록 조회 실패: %s", e)
        return {"status": "error", "message": f"예상치 못한 오류: {e}"}


def _get_execution_history(limit: int = 10) -> dict[str, Any]:
    """최근 워크플로우 실행 이력을 조회합니다."""
    try:
        resp = _session.get(
            f"{BRIDGE_URL}/history",
            params={"limit": limit},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.ConnectionError:
        return {"status": "error", "message": _CONN_ERROR_MSG}
    except Exception as e:
        logger.error("실행 이력 조회 실패: %s", e)
        return {"status": "error", "message": f"예상치 못한 오류: {e}"}


def _check_bridge_health() -> dict[str, Any]:
    """브릿지 서버의 상태를 확인합니다."""
    try:
        resp = _session.get(f"{BRIDGE_URL}/health", timeout=10)
        resp.raise_for_status()
        return resp.json()
    except requests.ConnectionError:
        return {"status": "unreachable", "message": _CONN_ERROR_MSG}
    except Exception as e:
        logger.error("헬스체크 실패: %s", e)
        return {"status": "error", "message": f"헬스체크 실패: {e}"}


# ─── MCP 서버 등록 ────────────────────────────────────────────────────────────

if FastMCP is not None:
    mcp = FastMCP(
        "n8n-workflow",
        instructions="n8n 브릿지 서버를 통해 워크플로우를 트리거하고 관리하는 MCP 서버",
    )

    @mcp.tool()
    def trigger_workflow(command: str, timeout: int = 600) -> dict[str, Any]:
        """브릿지 서버를 통해 워크플로우를 실행합니다.

        Args:
            command: 실행할 명령어 (btx_pipeline, btx_dry_run, healthcheck,
                     onedrive_backup, yt_analytics, cache_cleanup)
            timeout: 실행 타임아웃 (초). 기본값 600초 (10분).
        """
        return _trigger_workflow(command, timeout)

    @mcp.tool()
    def get_available_commands() -> dict[str, Any]:
        """브릿지 서버에서 사용 가능한 명령어 목록을 조회합니다."""
        return _get_available_commands()

    @mcp.tool()
    def get_execution_history(limit: int = 10) -> dict[str, Any]:
        """최근 워크플로우 실행 이력을 조회합니다.

        Args:
            limit: 반환할 최대 이력 수. 기본값 10.
        """
        return _get_execution_history(limit)

    @mcp.tool()
    def check_bridge_health() -> dict[str, Any]:
        """브릿지 서버의 상태를 확인합니다."""
        return _check_bridge_health()

else:
    mcp = None
    trigger_workflow = _trigger_workflow
    get_available_commands = _get_available_commands
    get_execution_history = _get_execution_history
    check_bridge_health = _check_bridge_health


# ─── 메인 ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if mcp is None:
        print("mcp 패키지 미설치. pip install 'mcp[cli]' 후 다시 실행하세요.")
    else:
        mcp.run()
