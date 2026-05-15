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
# qaqc_runner.py writes the canonical artifact to public/; data/qaqc_result.json is a gitignored orphan.
QAQC_FILE = PROJECT_ROOT / "public" / "qaqc_result.json"
READINESS_FILE = DATA_DIR / "product_readiness.json"
SKILL_LINT_FILE = DATA_DIR / "skill_lint.json"
SESSION_LOG_PATH = REPO_ROOT / ".ai" / "SESSION_LOG.md"
NOTEBOOKLM_VENV_LIB = REPO_ROOT / "infrastructure" / "notebooklm-mcp" / "venv" / "Lib" / "site-packages"
NOTEBOOKLM_TOKEN_DIR = REPO_ROOT / "infrastructure" / "notebooklm-mcp" / "tokens"
NOTEBOOKLM_AUTH_TOKEN_ENV_VAR = "NOTEBOOKLM_AUTH_TOKEN_PATH"
GITHUB_TOKEN = os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN", "")

if NOTEBOOKLM_VENV_LIB.exists():
    sys.path.append(str(NOTEBOOKLM_VENV_LIB))

# Shared QA/QC helpers live in the repo-wide workspace control plane.
sys.path.insert(0, str(REPO_ROOT / "workspace" / "execution"))
sys.path.insert(0, str(REPO_ROOT / "execution"))

try:
    import httpx
    from notebooklm_mcp.api_client import NotebookLMClient
    from notebooklm_mcp.auth import AuthTokens
except ImportError as exc:
    httpx = None
    NotebookLMClient = None
    AuthTokens = None
    NOTEBOOKLM_IMPORT_ERROR = exc
else:
    NOTEBOOKLM_IMPORT_ERROR = None


def _candidate_notebooklm_token_paths(repo_root: Path = REPO_ROOT) -> list[Path]:
    token_dir = repo_root / "infrastructure" / "notebooklm-mcp" / "tokens"
    configured = os.environ.get(NOTEBOOKLM_AUTH_TOKEN_ENV_VAR, "").strip()
    candidates: list[Path] = []

    if configured:
        configured_path = Path(configured)
        if not configured_path.is_absolute():
            configured_path = repo_root / configured_path
        candidates.append(configured_path)

    candidates.append(token_dir / "auth.local.json")
    candidates.append(token_dir / "auth.json")

    unique_candidates: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate)
        if key in seen:
            continue
        seen.add(key)
        unique_candidates.append(candidate)
    return unique_candidates


def resolve_notebooklm_token_path(repo_root: Path = REPO_ROOT) -> Path | None:
    for candidate in _candidate_notebooklm_token_paths(repo_root):
        if candidate.exists():
            return candidate
    return None


def is_notebooklm_token_template(data: dict) -> bool:
    markers = ("replace-with", "placeholder", "example", "set-via")

    def is_template_string(value: object) -> bool:
        return isinstance(value, str) and any(marker in value.lower() for marker in markers)

    cookies = data.get("cookies")
    if not isinstance(cookies, dict) or not cookies:
        return True

    cookie_values = [value for value in cookies.values() if isinstance(value, str)]
    if not cookie_values:
        return True

    if all((not value) or is_template_string(value) for value in cookie_values):
        return True

    for key in ("csrf_token", "session_id"):
        value = data.get(key, "")
        if value and is_template_string(value):
            return True

    return False


def fetch_github_repos():
    print("Fetching GitHub repositories...")
    if httpx is None:
        print(f"  - httpx is not available: {NOTEBOOKLM_IMPORT_ERROR}")
        return []
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
    if NOTEBOOKLM_IMPORT_ERROR is not None or NotebookLMClient is None or AuthTokens is None:
        print(f"  - NotebookLM dependencies are not available: {NOTEBOOKLM_IMPORT_ERROR}")
        return []

    token_path = resolve_notebooklm_token_path()
    if token_path is None:
        checked = ", ".join(str(path) for path in _candidate_notebooklm_token_paths())
        print(f"  - Token file not found. Checked: {checked}")
        return []

    try:
        with token_path.open("r", encoding="utf-8") as file_obj:
            data = json.load(file_obj)

        if is_notebooklm_token_template(data):
            print(
                "  - NotebookLM token file is still a checked-in template. "
                "Create tokens/auth.local.json or set NOTEBOOKLM_AUTH_TOKEN_PATH."
            )
            return []

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


def build_product_readiness() -> dict:
    print("Building product readiness score...")
    try:
        from product_readiness_score import build_report

        report = build_report(REPO_ROOT, qaqc_path=QAQC_FILE)
        with READINESS_FILE.open("w", encoding="utf-8") as file_obj:
            json.dump(report, file_obj, indent=2, ensure_ascii=False)
        print(f"  - Readiness score: {report['overall']['score']} ({report['overall']['state']})")
        return report
    except Exception as exc:
        print(f"  - Error building readiness score: {exc}")
        return {}


def build_skill_lint() -> dict:
    print("Building skill lint report...")
    try:
        from skill_lint import build_report

        report = build_report(REPO_ROOT)
        with SKILL_LINT_FILE.open("w", encoding="utf-8") as file_obj:
            json.dump(report, file_obj, indent=2, ensure_ascii=False)
        print(f"  - Skill lint: {report['summary']['status']} ({report['summary']['issue_count']} issue(s))")
        return report
    except Exception as exc:
        print(f"  - Error building skill lint report: {exc}")
        return {}


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

    readiness = build_product_readiness()
    if readiness:
        data["readiness"] = readiness

    skill_lint = build_skill_lint()
    if skill_lint:
        data["skill_lint"] = skill_lint

    with OUTPUT_FILE.open("w", encoding="utf-8") as file_obj:
        json.dump(data, file_obj, indent=2, ensure_ascii=False)

    print(f"Data saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
