import json
import os
import re
import sys
from pathlib import Path
from datetime import datetime

# Force UTF-8 output for Windows console
sys.stdout.reconfigure(encoding="utf-8")

# Add site-packages from parent directory's venv if needed
NOTEBOOKLM_VENV_LIB = r"c:\Users\박주호\Desktop\Vibe coding\infrastructure\notebooklm-mcp\venv\Lib\site-packages"
if os.path.exists(NOTEBOOKLM_VENV_LIB):
    sys.path.append(NOTEBOOKLM_VENV_LIB)

# execution 경로 추가 (qaqc_history_db용)
ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "execution"))

try:
    from notebooklm_mcp.api_client import NotebookLMClient
    from notebooklm_mcp.auth import AuthTokens
    import httpx
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Please run this script with the correct python environment")
    sys.exit(1)

# Configuration
OUTPUT_FILE = Path("public/dashboard_data.json")
NOTEBOOKLM_TOKEN_PATH = r"c:\Users\박주호\Desktop\Vibe coding\infrastructure\notebooklm-mcp\tokens\auth.json"
SESSION_LOG_PATH = ROOT_DIR / ".ai" / "SESSION_LOG.md"

# [QA 수정] GitHub 토큰은 환경변수에서만 로드 — 하드코딩 제거
GITHUB_TOKEN = os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN", "")


def fetch_github_repos():
    print("Fetching GitHub repositories...")
    if not GITHUB_TOKEN:
        print("  - GITHUB_PERSONAL_ACCESS_TOKEN 환경변수가 설정되지 않았습니다.")
        return []

    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    url = "https://api.github.com/user/repos?sort=updated&per_page=10"

    try:
        response = httpx.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        repos = response.json()

        simplified = []
        for repo in repos:
            simplified.append(
                {
                    "id": repo["id"],
                    "name": repo["name"],
                    "full_name": repo["full_name"],
                    "description": repo["description"],
                    "html_url": repo["html_url"],
                    "language": repo["language"],
                    "stargazers_count": repo["stargazers_count"],
                    "updated_at": repo["updated_at"],
                }
            )
        print(f"  - Found {len(simplified)} repositories")
        return simplified
    except Exception as e:
        print(f"  - Error fetching GitHub repos: {e}")
        return []


def fetch_notebooklm_notebooks():
    print("Fetching NotebookLM notebooks...")
    if not os.path.exists(NOTEBOOKLM_TOKEN_PATH):
        print(f"  - Token file not found at {NOTEBOOKLM_TOKEN_PATH}")
        return []

    try:
        with open(NOTEBOOKLM_TOKEN_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        tokens = AuthTokens.from_dict(data)
        client = NotebookLMClient(cookies=tokens.cookies, csrf_token=tokens.csrf_token, session_id=tokens.session_id)

        notebooks = client.list_notebooks()

        simplified = []
        for nb in notebooks:
            simplified.append(
                {
                    "id": nb.id,
                    "title": nb.title,
                    "source_count": nb.source_count,
                    "url": nb.url,
                    "ownership": nb.ownership,
                    "sources": [{"id": s.get("id"), "title": s.get("title"), "type": s.get("type")} for s in nb.sources]
                    if nb.sources
                    else [],
                }
            )

        print(f"  - Found {len(simplified)} notebooks")
        return simplified
    except Exception as e:
        print(f"  - Error fetching NotebookLM notebooks: {e}")
        import traceback

        traceback.print_exc()
        return []


def parse_session_log() -> list[dict]:
    """SESSION_LOG.md를 파싱하여 세션 엔트리 목록을 반환합니다."""
    print("Parsing session log...")
    if not SESSION_LOG_PATH.exists():
        print("  - SESSION_LOG.md not found")
        return []

    try:
        content = SESSION_LOG_PATH.read_text(encoding="utf-8")
    except Exception as e:
        print(f"  - Error reading session log: {e}")
        return []

    sessions = []
    # 패턴: ## YYYY-MM-DD or ### 날짜 형태의 헤더를 찾아 세션 블록 파싱
    # 세션 로그 형식: | 날짜 | 도구 | 요약 | ... | 형태의 테이블 또는
    # ## 날짜\n- 도구: ...\n- 요약: ... 형태
    blocks = re.split(r"\n(?=##\s)", content)

    for block in blocks:
        # 날짜 추출 시도
        date_match = re.search(r"(\d{4}-\d{2}-\d{2})", block)
        if not date_match:
            continue

        date = date_match.group(1)

        # 도구 이름 추출
        tool_match = re.search(r"(?:도구|Tool|AI)[:\s]*([^\n|]+)", block, re.IGNORECASE)
        tool = tool_match.group(1).strip() if tool_match else "Unknown"

        # 요약 추출
        summary_match = re.search(r"(?:요약|Summary|작업)[:\s]*([^\n|]+)", block, re.IGNORECASE)
        summary = summary_match.group(1).strip() if summary_match else block[:100].strip()

        # QC 판정 추출
        verdict = None
        if "APPROVED" in block or "승인" in block:
            if "CONDITIONALLY" in block or "조건부" in block:
                verdict = "⚠️ 조건부 승인"
            elif "REJECTED" in block or "반려" in block:
                verdict = "❌ 반려"
            else:
                verdict = "✅ APPROVED"

        # 변경 파일 수 추출
        files_match = re.findall(r"(?:변경|changed|modified|파일)[:\s]*(\d+)", block, re.IGNORECASE)
        files_changed = int(files_match[0]) if files_match else 0

        sessions.append(
            {
                "date": date,
                "tool": tool,
                "summary": summary[:200],
                "verdict": verdict,
                "files_changed": files_changed,
            }
        )

    # 최근 20개만
    sessions = sessions[-20:]
    print(f"  - Found {len(sessions)} sessions")
    return sessions


def fetch_qaqc_trend() -> list[dict]:
    """QA/QC 히스토리 DB에서 30일 트렌드 데이터를 가져옵니다."""
    print("Fetching QA/QC trend data...")
    try:
        from qaqc_history_db import QaQcHistoryDB

        db = QaQcHistoryDB()
        trend = db.get_trend_data(days=30)
        print(f"  - Found {len(trend)} trend points")
        return trend
    except ImportError:
        print("  - qaqc_history_db not available")
        return []
    except Exception as e:
        print(f"  - Error fetching trend: {e}")
        return []


def main():
    print(f"Starting data sync at {datetime.now().isoformat()}...")

    # Create public dir if not exists
    OUTPUT_FILE.parent.mkdir(exist_ok=True)

    data = {
        "last_updated": datetime.now().isoformat(),
        "github": fetch_github_repos(),
        "notebooklm": fetch_notebooklm_notebooks(),
        "sessions": parse_session_log(),
    }

    # QA/QC 최신 결과 읽기 (별도 JSON에서)
    qaqc_path = Path("public/qaqc_result.json")
    if qaqc_path.exists():
        try:
            with open(qaqc_path, encoding="utf-8") as f:
                qaqc_data = json.load(f)
            # 트렌드 데이터 추가
            qaqc_data["trend"] = fetch_qaqc_trend()
            data["qaqc"] = qaqc_data
            print("  - QA/QC result loaded")
        except Exception as e:
            print(f"  - Error loading QA/QC result: {e}")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"✅ Data saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
