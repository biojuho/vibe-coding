"""
n8n host bridge server.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import psutil
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).resolve().parents[2]
WORKSPACE_DIR = ROOT_DIR / "workspace"
N8N_DIR = ROOT_DIR / "infrastructure" / "n8n"


def default_btx_dir(repo_root: Path = ROOT_DIR) -> Path:
    return repo_root / "projects" / "blind-to-x"


def default_log_dir(repo_root: Path = ROOT_DIR) -> Path:
    return repo_root / "infrastructure" / "n8n" / "logs"


def workspace_module_command(module: str, *args: str, python_exe: str, workspace_dir: Path) -> dict[str, object]:
    return {
        "cmd": [python_exe, "-m", module, *args],
        "cwd": str(workspace_dir),
    }


BRIDGE_TOKEN = os.getenv("BRIDGE_TOKEN")
if not BRIDGE_TOKEN:
    raise RuntimeError("BRIDGE_TOKEN environment variable is required.")

BTX_DIR = Path(os.getenv("BTX_DIR") or default_btx_dir())
PYTHON_EXE = os.getenv("PYTHON_EXE", sys.executable)
LOG_DIR = Path(os.getenv("BRIDGE_LOG_DIR") or default_log_dir())


def build_allowed_commands(
    *,
    repo_root: Path = ROOT_DIR,
    btx_dir: Path | None = None,
    python_exe: str | None = None,
) -> dict[str, dict[str, object]]:
    workspace_dir = repo_root / "workspace"
    n8n_dir = repo_root / "infrastructure" / "n8n"
    resolved_btx_dir = Path(btx_dir or default_btx_dir(repo_root))
    resolved_python = python_exe or PYTHON_EXE

    return {
        "btx_pipeline": {
            "cmd": [resolved_python, str(resolved_btx_dir / "main.py"), "--parallel", "3"],
            "cwd": str(resolved_btx_dir),
            "description": "Blind-to-X pipeline full run",
        },
        "btx_dry_run": {
            "cmd": [resolved_python, str(resolved_btx_dir / "main.py"), "--dry-run"],
            "cwd": str(resolved_btx_dir),
            "description": "Blind-to-X pipeline dry run",
        },
        "healthcheck": {
            "cmd": [resolved_python, str(n8n_dir / "healthcheck.py")],
            "cwd": str(n8n_dir),
            "description": "System health check",
        },
        "onedrive_backup": {
            **workspace_module_command(
                "execution.backup_to_onedrive",
                python_exe=resolved_python,
                workspace_dir=workspace_dir,
            ),
            "description": "OneDrive backup",
        },
        "yt_analytics": {
            **workspace_module_command(
                "execution.result_tracker_db",
                "collect",
                python_exe=resolved_python,
                workspace_dir=workspace_dir,
            ),
            "description": "YouTube analytics sync",
        },
        "cache_cleanup": {
            "cmd": [resolved_python, "-c", "from execution.llm_client import cache_cleanup; print(f'Cleaned {cache_cleanup()} entries')"],
            "cwd": str(workspace_dir),
            "description": "LLM cache cleanup",
        },
        "notebooklm_pipeline": {
            **workspace_module_command(
                "execution.gdrive_pdf_extractor",
                "list-folder",
                python_exe=resolved_python,
                workspace_dir=workspace_dir,
            ),
            "description": "NotebookLM Drive listing",
        },
        # ── Shorts Maker v2 ──
        "shorts_generate": {
            "cmd": [
                resolved_python, "-m", "shorts_maker_v2",
                "generate", "--jobs", "1",
            ],
            "cwd": str(repo_root / "projects" / "shorts-maker-v2"),
            "description": "Generate 1 YouTube Short (full pipeline)",
        },
        "shorts_batch": {
            "cmd": [
                resolved_python, "-m", "shorts_maker_v2",
                "generate", "--jobs", "3",
            ],
            "cwd": str(repo_root / "projects" / "shorts-maker-v2"),
            "description": "Generate 3 YouTube Shorts (batch mode)",
        },
        "shorts_dry_run": {
            "cmd": [
                resolved_python, "-m", "shorts_maker_v2",
                "generate", "--jobs", "1", "--dry-run",
            ],
            "cwd": str(repo_root / "projects" / "shorts-maker-v2"),
            "description": "Shorts dry run (script only, no render)",
        },
    }


ALLOWED_COMMANDS = build_allowed_commands(btx_dir=BTX_DIR, python_exe=PYTHON_EXE)

app = FastAPI(
    title="n8n Bridge Server",
    description="HTTP bridge between n8n and local pipelines",
    version="1.2.0",
)

_server_start_time = datetime.now()
_execution_history: list[dict] = []

LOG_DIR.mkdir(parents=True, exist_ok=True)


class ExecuteRequest(BaseModel):
    command: str
    timeout: int = 600


class ExecuteResponse(BaseModel):
    status: str
    command: str
    exit_code: Optional[int] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    duration_seconds: Optional[float] = None
    timestamp: str


def verify_token(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    token = authorization.split(" ", 1)[1]
    if token != BRIDGE_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid token")


def _log_execution(result: dict):
    _execution_history.append(result)
    if len(_execution_history) > 100:
        _execution_history.pop(0)

    log_file = LOG_DIR / f"bridge_{datetime.now().strftime('%Y%m%d')}.jsonl"
    with open(log_file, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(result, ensure_ascii=False) + "\n")


@app.get("/")
async def root():
    return {
        "service": "n8n Bridge Server",
        "status": "running",
        "available_commands": list(ALLOWED_COMMANDS.keys()),
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/health")
async def health():
    now = datetime.now()
    uptime_seconds = round((now - _server_start_time).total_seconds(), 2)
    process = psutil.Process(os.getpid())
    memory_mb = round(process.memory_info().rss / (1024 * 1024), 2)
    total_executions = len(_execution_history)
    last_execution_at = _execution_history[-1].get("timestamp") if _execution_history else None

    if memory_mb > 512:
        status = "unhealthy"
    elif memory_mb > 256:
        status = "degraded"
    elif total_executions >= 3 and all(item.get("status") != "success" for item in _execution_history[-3:]):
        status = "degraded"
    else:
        status = "healthy"

    return {
        "uptime_seconds": uptime_seconds,
        "memory_mb": memory_mb,
        "total_executions": total_executions,
        "last_execution_at": last_execution_at,
        "status": status,
        "timestamp": now.isoformat(),
    }


@app.get("/commands")
async def list_commands(authorization: str = Header(None)):
    verify_token(authorization)
    return {
        "commands": {
            key: {"description": value["description"]}
            for key, value in ALLOWED_COMMANDS.items()
        }
    }


@app.post("/execute", response_model=ExecuteResponse)
async def execute_command(request: ExecuteRequest, authorization: str = Header(None)):
    verify_token(authorization)

    if request.command not in ALLOWED_COMMANDS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown command: {request.command}. Available: {list(ALLOWED_COMMANDS.keys())}",
        )

    cmd_config = ALLOWED_COMMANDS[request.command]
    start_time = datetime.now()
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
            stdout=result.stdout[-5000:] if result.stdout else None,
            stderr=result.stderr[-2000:] if result.stderr else None,
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
    except Exception as exc:
        duration = (datetime.now() - start_time).total_seconds()
        response = ExecuteResponse(
            status="error",
            command=request.command,
            duration_seconds=round(duration, 2),
            stderr=str(exc),
            timestamp=start_time.isoformat(),
        )

    _log_execution(response.model_dump())
    return response


@app.get("/history")
async def execution_history(limit: int = 10, authorization: str = Header(None)):
    verify_token(authorization)
    return {"history": _execution_history[-limit:]}


class GDriveExtractRequest(BaseModel):
    file_id: str
    dest_dir: Optional[str] = None


class ContentWriteRequest(BaseModel):
    text: str
    project: str = "default"
    provider: Optional[str] = None


class NotionArticleRequest(BaseModel):
    title: str
    article: str
    project: str = ""
    ai_provider: str = "gemini"
    drive_url: str = ""
    tags: Optional[list[str]] = None
    db_id: Optional[str] = None


@app.post("/notebooklm/extract-pdf")
async def notebooklm_extract_pdf(request: GDriveExtractRequest, authorization: str = Header(None)):
    verify_token(authorization)
    try:
        sys.path.insert(0, str(WORKSPACE_DIR))
        from execution.gdrive_pdf_extractor import download_and_extract

        result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: download_and_extract(request.file_id, dest_dir=request.dest_dir),
        )
        _log_execution(
            {
                "endpoint": "notebooklm/extract-pdf",
                "file_id": request.file_id,
                "status": "success",
                "timestamp": datetime.now().isoformat(),
            }
        )
        return result
    except Exception as exc:  # pragma: no cover - API path
        logger.error("[Bridge] extract-pdf failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/notebooklm/write-article")
async def notebooklm_write_article(request: ContentWriteRequest, authorization: str = Header(None)):
    verify_token(authorization)
    try:
        sys.path.insert(0, str(WORKSPACE_DIR))
        from execution.content_writer import write_article

        result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: write_article(
                request.text,
                project=request.project,
                provider=request.provider,
            ),
        )
        _log_execution(
            {
                "endpoint": "notebooklm/write-article",
                "project": request.project,
                "status": "success",
                "timestamp": datetime.now().isoformat(),
            }
        )
        return result
    except Exception as exc:  # pragma: no cover - API path
        logger.error("[Bridge] write-article failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/notebooklm/create-notion-page")
async def notebooklm_create_notion_page(request: NotionArticleRequest, authorization: str = Header(None)):
    verify_token(authorization)
    try:
        sys.path.insert(0, str(WORKSPACE_DIR))
        from execution.notion_article_uploader import create_article_page

        result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: create_article_page(
                title=request.title,
                article=request.article,
                project=request.project,
                ai_provider=request.ai_provider,
                drive_url=request.drive_url,
                tags=request.tags,
                db_id=request.db_id,
            ),
        )
        _log_execution(
            {
                "endpoint": "notebooklm/create-notion-page",
                "title": request.title,
                "status": "success",
                "timestamp": datetime.now().isoformat(),
            }
        )
        return result
    except Exception as exc:  # pragma: no cover - API path
        logger.error("[Bridge] create-notion-page failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


if __name__ == "__main__":
    import uvicorn

    print("=" * 60)
    print("  n8n Bridge Server")
    print("  Listening on http://127.0.0.1:9876")
    print(f"  Available commands: {list(ALLOWED_COMMANDS.keys())}")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=9876, log_level="info")
