"""
시스템 헬스체크 스크립트
========================
n8n에서 주기적으로 호출하여 전체 시스템 상태를 점검합니다.

점검 항목:
  1. Notion API 연결 상태
  2. LLM API 키 유효성 (Gemini)
  3. Python 환경 상태
  4. 디스크 용량
  5. 최근 파이프라인 실행 기록 (로그 확인)
"""

import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

# BTX 프로젝트 경로를 sys.path에 추가
BTX_DIR = Path(os.getenv("BTX_DIR", r"C:\Users\박주호\Desktop\Vibe coding\blind-to-x"))
sys.path.insert(0, str(BTX_DIR))

from dotenv import load_dotenv

# .env 로드 (여러 경로 탐색)
for env_candidate in [
    BTX_DIR / ".env",
    Path(r"C:\Users\박주호\Desktop\Vibe coding\.env"),
]:
    if env_candidate.exists():
        load_dotenv(env_candidate)


def check_notion_api() -> dict:
    """Notion API 연결 확인."""
    try:
        import httpx
        db_id = os.getenv("NOTION_DATABASE_ID", "")
        token = os.getenv("NOTION_API_KEY", "") or os.getenv("NOTION_TOKEN", "")

        if not db_id or not token:
            return {"status": "error", "message": "NOTION_DATABASE_ID 또는 NOTION_TOKEN 미설정"}

        resp = httpx.get(
            f"https://api.notion.com/v1/databases/{db_id}",
            headers={
                "Authorization": f"Bearer {token}",
                "Notion-Version": "2022-06-28",
            },
            timeout=10,
        )

        if resp.status_code == 200:
            title = resp.json().get("title", [{}])[0].get("plain_text", "Unknown")
            return {"status": "ok", "message": f"DB 연결 성공: {title}"}
        else:
            return {"status": "error", "message": f"HTTP {resp.status_code}: {resp.text[:200]}"}

    except Exception as e:
        return {"status": "error", "message": str(e)}


def check_llm_api() -> dict:
    """Gemini API 키 유효성 확인 (가벼운 모델 목록 조회)."""
    try:
        import httpx
        api_key = os.getenv("GEMINI_API_KEY", "") or os.getenv("GOOGLE_API_KEY", "")

        if not api_key:
            return {"status": "warning", "message": "GEMINI_API_KEY 미설정 (fallback 체인 사용 가능)"}

        resp = httpx.get(
            f"https://generativelanguage.googleapis.com/v1/models?key={api_key}",
            timeout=10,
        )

        if resp.status_code == 200:
            models = resp.json().get("models", [])
            return {"status": "ok", "message": f"Gemini 연결 성공 ({len(models)}개 모델 사용 가능)"}
        else:
            return {"status": "error", "message": f"HTTP {resp.status_code}"}

    except Exception as e:
        return {"status": "error", "message": str(e)}


def check_disk_space() -> dict:
    """디스크 용량 확인."""
    try:
        usage = shutil.disk_usage("C:\\")
        free_gb = usage.free / (1024 ** 3)
        total_gb = usage.total / (1024 ** 3)
        used_pct = (usage.used / usage.total) * 100

        status = "ok" if free_gb > 10 else ("warning" if free_gb > 5 else "error")
        return {
            "status": status,
            "message": f"C: {free_gb:.1f}GB 남음 ({used_pct:.0f}% 사용중, 전체 {total_gb:.0f}GB)",
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}


def check_python_env() -> dict:
    """Python 환경 확인."""
    try:
        version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        venv = os.getenv("VIRTUAL_ENV", "")

        # 핵심 패키지 확인
        missing = []
        for pkg in ["playwright", "httpx", "notion_client", "dotenv"]:
            try:
                __import__(pkg.replace("-", "_"))
            except ImportError:
                missing.append(pkg)

        if missing:
            return {
                "status": "warning",
                "message": f"Python {version} | 누락 패키지: {', '.join(missing)}",
            }

        return {
            "status": "ok",
            "message": f"Python {version} | 핵심 패키지 정상",
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}


def check_recent_logs() -> dict:
    """최근 브릿지 로그 확인."""
    try:
        log_dir = Path(__file__).parent / "logs"
        if not log_dir.exists():
            return {"status": "ok", "message": "로그 디렉토리 없음 (첫 실행)"}

        log_files = sorted(log_dir.glob("bridge_*.jsonl"), reverse=True)
        if not log_files:
            return {"status": "ok", "message": "실행 기록 없음"}

        # 최신 로그에서 마지막 줄 읽기
        latest = log_files[0]
        with open(latest, "r", encoding="utf-8") as f:
            lines = f.readlines()

        if not lines:
            return {"status": "ok", "message": "로그 파일 비어있음"}

        last_entry = json.loads(lines[-1])
        last_status = last_entry.get("status", "unknown")
        last_time = last_entry.get("timestamp", "unknown")
        last_cmd = last_entry.get("command", "unknown")

        return {
            "status": "ok" if last_status == "success" else "warning",
            "message": f"마지막 실행: {last_cmd} ({last_status}) @ {last_time}",
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}


def run_healthcheck() -> dict:
    """전체 헬스체크 실행."""
    checks = {
        "notion_api": check_notion_api(),
        "llm_api": check_llm_api(),
        "disk_space": check_disk_space(),
        "python_env": check_python_env(),
        "recent_logs": check_recent_logs(),
    }

    # 전체 상태 판단
    statuses = [c["status"] for c in checks.values()]
    if "error" in statuses:
        overall = "unhealthy"
    elif "warning" in statuses:
        overall = "degraded"
    else:
        overall = "healthy"

    result = {
        "overall_status": overall,
        "checks": checks,
        "timestamp": datetime.now().isoformat(),
    }

    return result


if __name__ == "__main__":
    result = run_healthcheck()
    print(json.dumps(result, ensure_ascii=False, indent=2))

    # 종료 코드: healthy=0, degraded=1, unhealthy=2
    exit_codes = {"healthy": 0, "degraded": 1, "unhealthy": 2}
    sys.exit(exit_codes.get(result["overall_status"], 2))
