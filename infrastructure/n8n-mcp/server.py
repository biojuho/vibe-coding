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

import os
from pathlib import Path

import requests
from dotenv import load_dotenv

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    FastMCP = None

# ─── 환경 설정 ────────────────────────────────────────────────────────────────

# .env 파일 탐색: 프로젝트 루트 → 현재 디렉토리 순
_project_root = Path(__file__).resolve().parent.parent.parent
_env_path = _project_root / ".env"
if _env_path.exists():
    load_dotenv(_env_path)
else:
    load_dotenv()

BRIDGE_URL: str = os.getenv("BRIDGE_URL", "http://localhost:9876")
BRIDGE_TOKEN: str = os.getenv("BRIDGE_TOKEN", "")

# ─── MCP 서버 ─────────────────────────────────────────────────────────────────

if FastMCP is not None:
    mcp = FastMCP(
        "n8n-workflow",
        description="n8n 브릿지 서버를 통해 워크플로우를 트리거하고 관리하는 MCP 서버",
    )
else:
    mcp = None


def _headers() -> dict[str, str]:
    """인증 헤더를 생성합니다."""
    return {"Authorization": f"Bearer {BRIDGE_TOKEN}"}


# ─── 도구 ─────────────────────────────────────────────────────────────────────


@mcp.tool()
def trigger_workflow(command: str, timeout: int = 600) -> dict:
    """브릿지 서버를 통해 워크플로우를 실행합니다.

    Args:
        command: 실행할 명령어 (btx_pipeline, btx_dry_run, healthcheck,
                 onedrive_backup, yt_analytics, cache_cleanup)
        timeout: 실행 타임아웃 (초). 기본값 600초 (10분).

    Returns:
        실행 결과 (status, exit_code, stdout, stderr, duration_seconds)
    """
    try:
        resp = requests.post(
            f"{BRIDGE_URL}/execute",
            json={"command": command, "timeout": timeout},
            headers=_headers(),
            timeout=timeout + 30,  # HTTP 타임아웃은 명령 타임아웃보다 여유있게
        )
        resp.raise_for_status()
        return resp.json()
    except requests.ConnectionError:
        return {
            "status": "error",
            "message": f"브릿지 서버({BRIDGE_URL})에 연결할 수 없습니다. 서버가 실행 중인지 확인하세요.",
        }
    except requests.Timeout:
        return {
            "status": "error",
            "message": f"요청이 타임아웃되었습니다 ({timeout + 30}초 초과).",
        }
    except requests.HTTPError as e:
        return {
            "status": "error",
            "message": f"HTTP 오류: {e.response.status_code} - {e.response.text}",
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"예상치 못한 오류: {e}",
        }


@mcp.tool()
def get_available_commands() -> dict:
    """브릿지 서버에서 사용 가능한 명령어 목록을 조회합니다.

    Returns:
        명령어 이름과 설명이 포함된 딕셔너리
    """
    try:
        resp = requests.get(
            f"{BRIDGE_URL}/commands",
            headers=_headers(),
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.ConnectionError:
        return {
            "status": "error",
            "message": f"브릿지 서버({BRIDGE_URL})에 연결할 수 없습니다. 서버가 실행 중인지 확인하세요.",
        }
    except requests.HTTPError as e:
        return {
            "status": "error",
            "message": f"HTTP 오류: {e.response.status_code} - {e.response.text}",
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"예상치 못한 오류: {e}",
        }


@mcp.tool()
def get_execution_history(limit: int = 10) -> dict:
    """최근 워크플로우 실행 이력을 조회합니다.

    Args:
        limit: 반환할 최대 이력 수. 기본값 10.

    Returns:
        최근 실행 이력 리스트
    """
    try:
        resp = requests.get(
            f"{BRIDGE_URL}/history",
            params={"limit": limit},
            headers=_headers(),
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.ConnectionError:
        return {
            "status": "error",
            "message": f"브릿지 서버({BRIDGE_URL})에 연결할 수 없습니다. 서버가 실행 중인지 확인하세요.",
        }
    except requests.HTTPError as e:
        return {
            "status": "error",
            "message": f"HTTP 오류: {e.response.status_code} - {e.response.text}",
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"예상치 못한 오류: {e}",
        }


@mcp.tool()
def check_bridge_health() -> dict:
    """브릿지 서버의 상태를 확인합니다.

    Returns:
        서버 상태 정보 (uptime, memory, status, 최근 실행 정보)
    """
    try:
        resp = requests.get(
            f"{BRIDGE_URL}/health",
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.ConnectionError:
        return {
            "status": "unreachable",
            "message": f"브릿지 서버({BRIDGE_URL})에 연결할 수 없습니다. 서버가 실행 중인지 확인하세요.",
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"헬스체크 실패: {e}",
        }


# ─── 메인 ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run()
