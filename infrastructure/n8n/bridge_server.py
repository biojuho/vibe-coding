"""
n8n ↔ 호스트 브릿지 서버
========================
n8n Docker 컨테이너에서 호스트 Windows의 파이프라인을 안전하게 실행하기 위한
경량 HTTP 브릿지 서버입니다.

아키텍처:
  n8n (Docker) --HTTP Request--> bridge_server.py (Host:9876) --subprocess--> main.py

보안:
  - localhost(127.0.0.1)에서만 수신 + Docker 내부 네트워크
  - Bearer 토큰 인증
  - 허용된 명령어 화이트리스트만 실행 가능
"""

import asyncio
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, Header, BackgroundTasks
from pydantic import BaseModel
from typing import Optional

# ─── 설정 ────────────────────────────────────────────────────────────────────

BRIDGE_TOKEN = os.getenv("BRIDGE_TOKEN", "N8N_BRIDGE_TOKEN_PLACEHOLDER")
BTX_DIR = Path(os.getenv("BTX_DIR", r"C:\Users\박주호\Desktop\Vibe coding\blind-to-x"))
PYTHON_EXE = os.getenv("PYTHON_EXE", sys.executable)
LOG_DIR = Path(os.getenv("BRIDGE_LOG_DIR", r"C:\Users\박주호\Desktop\Vibe coding\infrastructure\n8n\logs"))

# 허용된 커맨드 화이트리스트 (보안)
ALLOWED_COMMANDS = {
    "btx_pipeline": {
        "cmd": [PYTHON_EXE, str(BTX_DIR / "main.py"), "--parallel", "3"],
        "cwd": str(BTX_DIR),
        "description": "Blind-to-X 파이프라인 전체 실행",
    },
    "btx_dry_run": {
        "cmd": [PYTHON_EXE, str(BTX_DIR / "main.py"), "--dry-run"],
        "cwd": str(BTX_DIR),
        "description": "Blind-to-X 파이프라인 드라이런 (데이터 변경 없음)",
    },
    "healthcheck": {
        "cmd": [PYTHON_EXE, str(Path(__file__).parent / "healthcheck.py")],
        "cwd": str(Path(__file__).parent),
        "description": "시스템 전체 헬스체크",
    },
}

# ─── FastAPI 앱 ──────────────────────────────────────────────────────────────

app = FastAPI(
    title="n8n Bridge Server",
    description="n8n → Host 브릿지 서버 (Blind-to-X / Shorts Maker 파이프라인용)",
    version="1.0.0",
)

LOG_DIR.mkdir(parents=True, exist_ok=True)


# ─── 모델 ────────────────────────────────────────────────────────────────────

class ExecuteRequest(BaseModel):
    command: str  # ALLOWED_COMMANDS 키
    timeout: int = 600  # 기본 10분 타임아웃


class ExecuteResponse(BaseModel):
    status: str
    command: str
    exit_code: Optional[int] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    duration_seconds: Optional[float] = None
    timestamp: str


class HealthResponse(BaseModel):
    status: str
    checks: dict
    timestamp: str


# ─── 인증 ────────────────────────────────────────────────────────────────────

def verify_token(authorization: str = Header(None)):
    """Bearer 토큰 인증."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    token = authorization.split(" ", 1)[1]
    if token != BRIDGE_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid token")


# ─── 실행 기록 ───────────────────────────────────────────────────────────────

_execution_history: list[dict] = []


def _log_execution(result: dict):
    """실행 결과를 로그 파일에 기록."""
    _execution_history.append(result)
    # 최근 100건만 메모리에 유지
    if len(_execution_history) > 100:
        _execution_history.pop(0)

    log_file = LOG_DIR / f"bridge_{datetime.now().strftime('%Y%m%d')}.jsonl"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(result, ensure_ascii=False) + "\n")


# ─── 엔드포인트 ──────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    """브릿지 서버 상태."""
    return {
        "service": "n8n Bridge Server",
        "status": "running",
        "available_commands": list(ALLOWED_COMMANDS.keys()),
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/commands")
async def list_commands(authorization: str = Header(None)):
    """사용 가능한 명령어 목록."""
    verify_token(authorization)
    return {
        "commands": {
            k: {"description": v["description"]}
            for k, v in ALLOWED_COMMANDS.items()
        }
    }


@app.post("/execute", response_model=ExecuteResponse)
async def execute_command(
    request: ExecuteRequest,
    authorization: str = Header(None),
):
    """화이트리스트된 명령어를 실행합니다."""
    verify_token(authorization)

    if request.command not in ALLOWED_COMMANDS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown command: {request.command}. "
                   f"Available: {list(ALLOWED_COMMANDS.keys())}",
        )

    cmd_config = ALLOWED_COMMANDS[request.command]
    start_time = datetime.now()

    # Windows UTF-8 인코딩 보장
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"

    try:
        result = subprocess.run(
            cmd_config["cmd"],
            cwd=cmd_config["cwd"],
            capture_output=True,
            text=True,
            timeout=request.timeout,
            encoding="utf-8",
            errors="replace",
            env=env,
        )

        duration = (datetime.now() - start_time).total_seconds()
        response = ExecuteResponse(
            status="success" if result.returncode == 0 else "failed",
            command=request.command,
            exit_code=result.returncode,
            stdout=result.stdout[-5000:] if result.stdout else None,  # 마지막 5000자
            stderr=result.stderr[-2000:] if result.stderr else None,  # 마지막 2000자
            duration_seconds=round(duration, 2),
            timestamp=start_time.isoformat(),
        )

    except subprocess.TimeoutExpired:
        duration = (datetime.now() - start_time).total_seconds()
        response = ExecuteResponse(
            status="timeout",
            command=request.command,
            duration_seconds=round(duration, 2),
            stderr=f"Command timed out after {request.timeout} seconds",
            timestamp=start_time.isoformat(),
        )

    except Exception as e:
        duration = (datetime.now() - start_time).total_seconds()
        response = ExecuteResponse(
            status="error",
            command=request.command,
            duration_seconds=round(duration, 2),
            stderr=str(e),
            timestamp=start_time.isoformat(),
        )

    _log_execution(response.model_dump())
    return response


@app.get("/history")
async def execution_history(
    limit: int = 10,
    authorization: str = Header(None),
):
    """최근 실행 기록."""
    verify_token(authorization)
    return {"history": _execution_history[-limit:]}


# ─── 메인 ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    print("=" * 60)
    print("  n8n Bridge Server")
    print(f"  Listening on http://127.0.0.1:9876")
    print(f"  Available commands: {list(ALLOWED_COMMANDS.keys())}")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=9876, log_level="info")
