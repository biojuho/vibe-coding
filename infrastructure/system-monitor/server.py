"""
System Monitor MCP Server (v2 — 완성판)
========================================
로컬 시스템의 CPU, 메모리, 디스크, 프로세스, 네트워크 상태를
실시간으로 모니터링하는 MCP 서버.

Tools:
  - get_system_stats: CPU/메모리/디스크/OS 종합 통계
  - get_process_list: 실행 중인 프로세스 목록 (필터링 가능)
  - check_service_health: 핵심 서비스(n8n, Streamlit, bridge 등) 상태 확인
  - get_network_status: 네트워크 연결 및 API 엔드포인트 핑 테스트
  - get_disk_breakdown: 프로젝트별 디스크 사용량 분석

Usage:
    python server.py
"""

from __future__ import annotations

import datetime
import platform
import socket
import subprocess
from pathlib import Path
from typing import Any

import psutil
from dotenv import load_dotenv

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    FastMCP = None

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(_PROJECT_ROOT / ".env")


# ─── 도구 함수 ────────────────────────────────────────────────────────────────


def _build_system_stats() -> dict[str, Any]:
    """CPU, 메모리, 디스크, OS 종합 통계를 반환합니다."""
    cpu_percent = psutil.cpu_percent(interval=1)
    cpu_count = psutil.cpu_count()
    cpu_freq = psutil.cpu_freq()

    vm = psutil.virtual_memory()
    memory = {
        "total_gb": round(vm.total / (1024**3), 2),
        "available_gb": round(vm.available / (1024**3), 2),
        "used_gb": round(vm.used / (1024**3), 2),
        "percent": vm.percent,
    }

    # Windows에서 C:\ 사용
    disk_path = "C:\\" if platform.system() == "Windows" else "/"
    disk = psutil.disk_usage(disk_path)
    disk_info = {
        "total_gb": round(disk.total / (1024**3), 2),
        "free_gb": round(disk.free / (1024**3), 2),
        "used_gb": round(disk.used / (1024**3), 2),
        "percent": disk.percent,
    }

    # 부팅 시간
    boot_time = datetime.datetime.fromtimestamp(psutil.boot_time())
    uptime = datetime.datetime.now() - boot_time

    sys_info = {
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python_version": platform.python_version(),
        "boot_time": boot_time.isoformat(),
        "uptime_hours": round(uptime.total_seconds() / 3600, 1),
    }

    return {
        "cpu": {
            "percent": cpu_percent,
            "cores": cpu_count,
            "freq_mhz": round(cpu_freq.current, 0) if cpu_freq else None,
        },
        "memory": memory,
        "disk": disk_info,
        "os": sys_info,
        "timestamp": datetime.datetime.now().isoformat(),
    }


def _get_process_list(filter_name: str = "", top_n: int = 20) -> dict[str, Any]:
    """실행 중인 프로세스 목록을 반환합니다.

    Args:
        filter_name: 프로세스 이름 필터 (부분 일치)
        top_n: 반환할 최대 프로세스 수 (메모리 사용량 기준 정렬)
    """
    processes = []
    for proc in psutil.process_iter(["pid", "name", "memory_percent", "cpu_percent", "status"]):
        try:
            info = proc.info
            name = info.get("name", "")
            if filter_name and filter_name.lower() not in name.lower():
                continue
            processes.append(
                {
                    "pid": info["pid"],
                    "name": name,
                    "memory_pct": round(info.get("memory_percent", 0) or 0, 2),
                    "cpu_pct": round(info.get("cpu_percent", 0) or 0, 1),
                    "status": info.get("status", "unknown"),
                }
            )
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    # 메모리 사용량 기준 정렬
    processes.sort(key=lambda p: p["memory_pct"], reverse=True)

    return {
        "total_processes": len(processes),
        "processes": processes[:top_n],
        "filter": filter_name or "(none)",
        "timestamp": datetime.datetime.now().isoformat(),
    }


def _check_service_health() -> dict[str, Any]:
    """핵심 서비스(n8n, Streamlit, bridge 서버 등)의 생존 여부를 확인합니다."""
    services = {
        "n8n_docker": {"port": 5678, "description": "n8n 자동화 엔진"},
        "bridge_server": {"port": 9876, "description": "n8n HTTP 브릿지"},
        "streamlit": {"port": 8501, "description": "메인 대시보드"},
        "streamlit_result": {"port": 8503, "description": "결과 대시보드"},
    }

    results = {}
    for name, info in services.items():
        port = info["port"]
        is_alive = False
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=2):
                is_alive = True
        except (ConnectionRefusedError, socket.timeout, OSError):
            pass

        results[name] = {
            "port": port,
            "description": info["description"],
            "status": "running" if is_alive else "stopped",
            "alive": is_alive,
        }

    # Docker Desktop 확인 # [QA 수정] 타임아웃 3초, OSError 추가
    docker_running = False
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            text=True,
            timeout=3,
            creationflags=0x08000000 if platform.system() == "Windows" else 0,  # CREATE_NO_WINDOW
        )
        docker_running = result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass

    results["docker_desktop"] = {
        "description": "Docker Desktop",
        "status": "running" if docker_running else "stopped",
        "alive": docker_running,
    }

    alive_count = sum(1 for s in results.values() if s["alive"])
    total = len(results)

    return {
        "services": results,
        "summary": f"{alive_count}/{total} 서비스 정상",
        "all_healthy": alive_count == total,
        "timestamp": datetime.datetime.now().isoformat(),
    }


def _get_network_status() -> dict[str, Any]:
    """네트워크 연결 상태 및 API 엔드포인트 핑 테스트를 수행합니다."""
    endpoints = {
        "notion_api": "api.notion.com",
        "openai_api": "api.openai.com",
        "google_api": "generativelanguage.googleapis.com",
        "telegram_api": "api.telegram.org",
        "pexels_api": "api.pexels.com",
        "cloudinary": "api.cloudinary.com",
        "github": "api.github.com",
    }

    results = {}
    for name, host in endpoints.items():
        reachable = False
        latency_ms = None
        try:
            start = datetime.datetime.now()
            socket.create_connection((host, 443), timeout=3).close()
            latency_ms = round((datetime.datetime.now() - start).total_seconds() * 1000, 1)
            reachable = True
        except (socket.timeout, OSError):
            pass

        results[name] = {
            "host": host,
            "reachable": reachable,
            "latency_ms": latency_ms,
        }

    reachable_count = sum(1 for r in results.values() if r["reachable"])

    return {
        "endpoints": results,
        "summary": f"{reachable_count}/{len(results)} 엔드포인트 연결 가능",
        "internet_available": reachable_count > 0,
        "timestamp": datetime.datetime.now().isoformat(),
    }


def _get_disk_breakdown() -> dict[str, Any]:
    """프로젝트 폴더별 디스크 사용량을 분석합니다."""
    dirs_to_check = {
        "blind-to-x": _PROJECT_ROOT / "blind-to-x",
        "shorts-maker-v2": _PROJECT_ROOT / "shorts-maker-v2",
        "hanwoo-dashboard": _PROJECT_ROOT / "hanwoo-dashboard",
        "knowledge-dashboard": _PROJECT_ROOT / "knowledge-dashboard",
        "suika-game-v2": _PROJECT_ROOT / "suika-game-v2",
        "word-chain": _PROJECT_ROOT / "word-chain",
        ".tmp": _PROJECT_ROOT / ".tmp",
        "venv": _PROJECT_ROOT / "venv",
        "infrastructure": _PROJECT_ROOT / "infrastructure",
        "execution": _PROJECT_ROOT / "execution",
    }

    breakdown = {}
    total_size = 0

    for name, path in sorted(dirs_to_check.items()):
        if not path.exists():
            breakdown[name] = {"exists": False, "size_mb": 0}
            continue
        try:
            size = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
            size_mb = round(size / (1024 * 1024), 1)
            breakdown[name] = {"exists": True, "size_mb": size_mb}
            total_size += size
        except PermissionError:
            breakdown[name] = {"exists": True, "size_mb": "permission_denied"}

    return {
        "breakdown": breakdown,
        "total_mb": round(total_size / (1024 * 1024), 1),
        "total_gb": round(total_size / (1024**3), 2),
        "timestamp": datetime.datetime.now().isoformat(),
    }


# ─── MCP 서버 등록 ────────────────────────────────────────────────────────────

if FastMCP is not None:
    mcp = FastMCP(
        "system-monitor",
        instructions=(
            "로컬 시스템 모니터링 MCP 서버. "
            "CPU/메모리/디스크, 프로세스, 서비스 헬스, 네트워크 상태, 프로젝트별 디스크 분석을 제공합니다."
        ),
    )

    @mcp.tool()
    def get_system_stats() -> dict[str, Any]:
        """CPU, 메모리, 디스크, OS 종합 통계를 반환합니다."""
        return _build_system_stats()

    @mcp.tool()
    def get_process_list(filter_name: str = "", top_n: int = 20) -> dict[str, Any]:
        """실행 중인 프로세스 목록을 반환합니다. 이름으로 필터링하고 메모리 사용량 기준 정렬합니다.

        Args:
            filter_name: 프로세스 이름 필터 (부분 일치, 예: 'python', 'docker')
            top_n: 반환할 최대 프로세스 수 (기본 20)
        """
        return _get_process_list(filter_name, top_n)

    @mcp.tool()
    def check_service_health() -> dict[str, Any]:
        """핵심 서비스(n8n, Streamlit, bridge, Docker)의 실행 상태를 확인합니다."""
        return _check_service_health()

    @mcp.tool()
    def get_network_status() -> dict[str, Any]:
        """외부 API 엔드포인트의 연결 가능 여부와 지연 시간을 측정합니다."""
        return _get_network_status()

    @mcp.tool()
    def get_disk_breakdown() -> dict[str, Any]:
        """프로젝트 폴더별 디스크 사용량을 분석합니다."""
        return _get_disk_breakdown()

else:
    mcp = None
    get_system_stats = _build_system_stats
    get_process_list = _get_process_list
    check_service_health = _check_service_health
    get_network_status = _get_network_status
    get_disk_breakdown = _get_disk_breakdown


if __name__ == "__main__":
    if mcp is None:
        import json

        print("mcp 패키지 미설치. 직접 테스트 모드:")
        print("\n=== System Stats ===")
        print(json.dumps(_build_system_stats(), indent=2, ensure_ascii=False))
        print("\n=== Service Health ===")
        print(json.dumps(_check_service_health(), indent=2, ensure_ascii=False))
    else:
        mcp.run()
