import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_FILE = DATA_DIR / "dashboard_data.json"
QAQC_FILE = DATA_DIR / "qaqc_result.json"
SESSION_LOG_PATH = REPO_ROOT / ".ai" / "SESSION_LOG.md"
NOTEBOOKLM_VENV_LIB = REPO_ROOT / "infrastructure" / "notebooklm-mcp" / "venv" / "Lib" / "site-packages"
NOTEBOOKLM_TOKEN_PATH = REPO_ROOT / "infrastructure" / "notebooklm-mcp" / "tokens" / "auth.json"
GITHUB_TOKEN = os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN", "")

if NOTEBOOKLM_VENV_LIB.exists():
    sys.path.append(str(NOTEBOOKLM_VENV_LIB))

# Shared QA/QC helpers live in the repo-wide workspace control plane.
sys.path.insert(0, str(REPO_ROOT / "workspace" / "execution"))

try:
    import httpx
    from notebooklm_mcp.api_client import NotebookLMClient
    from notebooklm_mcp.auth import AuthTokens
except ImportError as exc:
    print(f"Error importing modules: {exc}")
    print("Please run this script with the correct python environment")
    sys.exit(1)


def fetch_github_repos():
    print("Fetching GitHub repositories...")
    if not GITHUB_TOKEN:
        print("  - GITHUB_PERSONAL_ACCESS_TOKEN is not configured")
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
    except Exception as exc:
        print(f"  - Error fetching GitHub repos: {exc}")
        return []


def fetch_notebooklm_notebooks():
    print("Fetching NotebookLM notebooks...")
    if not NOTEBOOKLM_TOKEN_PATH.exists():
        print(f"  - Token file not found at {NOTEBOOKLM_TOKEN_PATH}")
        return []

    try:
        with NOTEBOOKLM_TOKEN_PATH.open("r", encoding="utf-8") as file_obj:
            data = json.load(file_obj)

        tokens = AuthTokens.from_dict(data)
        client = NotebookLMClient(cookies=tokens.cookies, csrf_token=tokens.csrf_token, session_id=tokens.session_id)
        notebooks = client.list_notebooks()

        simplified = []
        for notebook in notebooks:
            simplified.append(
                {
                    "id": notebook.id,
                    "title": notebook.title,
                    "source_count": notebook.source_count,
                    "url": notebook.url,
                    "ownership": notebook.ownership,
                    "sources": [
                        {"id": source.get("id"), "title": source.get("title"), "type": source.get("type")}
                        for source in (notebook.sources or [])
                    ],
                }
            )

        print(f"  - Found {len(simplified)} notebooks")
        return simplified
    except Exception as exc:
        print(f"  - Error fetching NotebookLM notebooks: {exc}")
        import traceback

        traceback.print_exc()
        return []


def parse_session_log() -> list[dict]:
    print("Parsing session log...")
    if not SESSION_LOG_PATH.exists():
        print("  - SESSION_LOG.md not found")
        return []

    try:
        content = SESSION_LOG_PATH.read_text(encoding="utf-8")
    except Exception as exc:
        print(f"  - Error reading session log: {exc}")
        return []

    sessions = []
    blocks = re.split(r"\n(?=##\s)", content)

    for block in blocks:
        date_match = re.search(r"(\d{4}-\d{2}-\d{2})", block)
        if not date_match:
            continue

        date = date_match.group(1)
        tool_match = re.search(r"(?:Tool|AI|도구)[:\s]*([^\n|]+)", block, re.IGNORECASE)
        summary_match = re.search(r"(?:Summary|작업|요약)[:\s]*([^\n|]+)", block, re.IGNORECASE)
        files_match = re.findall(r"(?:changed|modified|파일)[:\s]*(\d+)", block, re.IGNORECASE)

        verdict = None
        if "CONDITIONALLY_APPROVED" in block:
            verdict = "CONDITIONALLY_APPROVED"
        elif "REJECTED" in block:
            verdict = "REJECTED"
        elif "APPROVED" in block:
            verdict = "APPROVED"

        sessions.append(
            {
                "date": date,
                "tool": tool_match.group(1).strip() if tool_match else "Unknown",
                "summary": (summary_match.group(1).strip() if summary_match else block[:100].strip())[:200],
                "verdict": verdict,
                "files_changed": int(files_match[0]) if files_match else 0,
            }
        )

    sessions = sessions[-20:]
    print(f"  - Found {len(sessions)} sessions")
    return sessions


def fetch_qaqc_trend() -> list[dict]:
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
    except Exception as exc:
        print(f"  - Error fetching trend: {exc}")
        return []


def main():
    print(f"Starting data sync at {datetime.now().isoformat()}...")
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    data = {
        "last_updated": datetime.now().isoformat(),
        "github": fetch_github_repos(),
        "notebooklm": fetch_notebooklm_notebooks(),
        "sessions": parse_session_log(),
    }

    if QAQC_FILE.exists():
        try:
            with QAQC_FILE.open("r", encoding="utf-8") as file_obj:
                qaqc_data = json.load(file_obj)

            qaqc_data["trend"] = fetch_qaqc_trend()
            data["qaqc"] = qaqc_data
            print("  - QA/QC result loaded")
        except Exception as exc:
            print(f"  - Error loading QA/QC result: {exc}")

    with OUTPUT_FILE.open("w", encoding="utf-8") as file_obj:
        json.dump(data, file_obj, indent=2, ensure_ascii=False)

    print(f"Data saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
