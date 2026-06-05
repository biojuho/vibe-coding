import json
import os
import re
import sys
import zlib
from datetime import datetime
from importlib import util as importlib_util
from pathlib import Path


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


PROJECT_ROOT = Path(__file__).resolve().parents[1]
# parents: [0]=scripts [1]=knowledge-dashboard [2]=projects [3]=<workspace root>.
# REPO_ROOT must be the workspace root that holds .ai/, workspace/execution, and
# infrastructure/ — parents[2] (=projects/) silently misses all of them, which
# drops sessions/readiness/skill_lint from the dashboard (the parents off-by-one
# antipattern). parents[3] is correct.
REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_FILE = DATA_DIR / "dashboard_data.json"
# qaqc_runner.py writes its local artifact to public/ (read source for local tooling).
# It must NOT ship in the deployed bundle: public/ is served without auth, so
# public/qaqc_result.json is gitignored and untracked. The authenticated Next route
# (src/app/api/data/qaqc/route.ts) serves data/qaqc_result.json instead, which this
# sync refreshes from the public source so it never goes stale (ADR-023).
QAQC_FILE = PROJECT_ROOT / "public" / "qaqc_result.json"
QAQC_DATA_FILE = DATA_DIR / "qaqc_result.json"
READINESS_FILE = DATA_DIR / "product_readiness.json"
SKILL_LINT_FILE = DATA_DIR / "skill_lint.json"
SESSION_LOG_PATH = REPO_ROOT / ".ai" / "SESSION_LOG.md"
NOTEBOOKLM_VENV_LIB = REPO_ROOT / "infrastructure" / "notebooklm-mcp" / "venv" / "Lib" / "site-packages"
NOTEBOOKLM_TOKEN_DIR = REPO_ROOT / "infrastructure" / "notebooklm-mcp" / "tokens"
NOTEBOOKLM_AUTH_TOKEN_ENV_VAR = "NOTEBOOKLM_AUTH_TOKEN_PATH"
NOTEBOOKLM_TEMPLATE_MARKERS = ("replace-with", "placeholder", "example", "set-via")
GITHUB_TOKEN = os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN", "")
LOCAL_INVENTORY_SCRIPT = REPO_ROOT / ".agents" / "skills" / "auto-research" / "scripts" / "github_project_inventory.py"

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


def _is_notebooklm_template_string(value: object) -> bool:
    return isinstance(value, str) and any(marker in value.lower() for marker in NOTEBOOKLM_TEMPLATE_MARKERS)


def _notebooklm_cookie_values(cookies: object) -> list[str]:
    if not isinstance(cookies, dict):
        return []
    return [value for value in cookies.values() if isinstance(value, str)]


def _cookie_values_are_empty_or_template(cookie_values: list[str]) -> bool:
    if not cookie_values:
        return True
    return all((not value) or _is_notebooklm_template_string(value) for value in cookie_values)


def _has_template_notebooklm_identity_field(data: dict) -> bool:
    for key in ("csrf_token", "session_id"):
        value = data.get(key, "")
        if value and _is_notebooklm_template_string(value):
            return True
    return False


def is_notebooklm_token_template(data: dict) -> bool:
    cookies = data.get("cookies")
    if not isinstance(cookies, dict) or not cookies:
        return True

    cookie_values = _notebooklm_cookie_values(cookies)
    if _cookie_values_are_empty_or_template(cookie_values):
        return True

    return _has_template_notebooklm_identity_field(data)


def fetch_github_repos():
    print("Fetching GitHub repositories...")
    if httpx is None:
        print(f"  - httpx is not available: {NOTEBOOKLM_IMPORT_ERROR}; using local project inventory")
        return fetch_local_workspace_projects()
    if not GITHUB_TOKEN:
        print("  - GITHUB_PERSONAL_ACCESS_TOKEN is not configured; using local project inventory")
        return fetch_local_workspace_projects()

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
        print(f"  - Error fetching GitHub repos: {exc}; using local project inventory")
        return fetch_local_workspace_projects()


def github_remote_base_url(remote_output: str) -> str | None:
    for line in remote_output.splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        remote_url = parts[1].strip()
        if "github.com" not in remote_url:
            continue
        if remote_url.startswith("git@github.com:"):
            remote_url = "https://github.com/" + remote_url.removeprefix("git@github.com:")
        if remote_url.startswith("https://github.com/"):
            return remote_url.removesuffix(".git")
    return None


def local_project_repo_url(base_url: str | None, branch: str | None, project_path: str) -> str:
    if not base_url:
        return ""
    if project_path == ".":
        return base_url
    safe_branch = branch or "main"
    return f"{base_url}/tree/{safe_branch}/{project_path}"


def stable_local_project_id(project_path: str) -> int:
    return zlib.crc32(project_path.encode("utf-8")) & 0x7FFFFFFF


def infer_local_project_language(project: dict) -> str | None:
    markers = set(project.get("markers") or [])
    if "pyproject.toml" in markers or "requirements.txt" in markers:
        return "Python"
    if "package.json" not in markers:
        return None
    path = str(project.get("path") or "")
    if any(part in path for part in ("dashboard", "word-chain")):
        return "TypeScript"
    return "JavaScript"


def describe_local_project(project: dict) -> str:
    markers = ", ".join(str(marker) for marker in project.get("markers") or []) or "no markers"
    test_count = int(project.get("test_file_count") or 0)
    workflow_count = len(project.get("workflows") or [])
    readme_status = "README present" if project.get("has_readme") else "README missing"
    return (
        f"Local workspace project; {readme_status}; {test_count} test file(s); "
        f"{workflow_count} workflow file(s); markers: {markers}."
    )


def local_project_to_github_repo(project: dict, base_url: str | None, branch: str | None) -> dict:
    project_path = str(project.get("path") or ".")
    name = "vibe-coding" if project_path == "." else Path(project_path).name
    return {
        "id": stable_local_project_id(project_path),
        "name": name,
        "full_name": f"local/{name}",
        "description": describe_local_project(project),
        "html_url": local_project_repo_url(base_url, branch, project_path),
        "language": infer_local_project_language(project),
        "stargazers_count": 0,
        "updated_at": datetime.now().astimezone().isoformat(),
    }


def fetch_local_workspace_projects(repo_root: Path = REPO_ROOT) -> list[dict]:
    if not LOCAL_INVENTORY_SCRIPT.exists():
        print(f"  - Local inventory script not found: {LOCAL_INVENTORY_SCRIPT}")
        return []

    try:
        spec = importlib_util.spec_from_file_location("github_project_inventory", LOCAL_INVENTORY_SCRIPT)
        if spec is None or spec.loader is None:
            raise RuntimeError("failed to create inventory module spec")
        module = importlib_util.module_from_spec(spec)
        spec.loader.exec_module(module)
        inventory = module.build_inventory(repo_root, include_prs=False)
    except Exception as exc:
        print(f"  - Local project inventory failed: {exc}")
        return []

    projects = inventory.get("projects")
    if not isinstance(projects, list):
        print("  - Local project inventory returned no project list")
        return []

    git = inventory.get("git") if isinstance(inventory.get("git"), dict) else {}
    remote = git.get("remote") if isinstance(git.get("remote"), dict) else {}
    base_url = github_remote_base_url(str(remote.get("stdout") or ""))
    branch = str(git.get("branch") or "main")
    repos = [
        local_project_to_github_repo(project, base_url, branch) for project in projects if isinstance(project, dict)
    ]
    print(f"  - Found {len(repos)} local workspace project(s)")
    return repos


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


def aggregate_trend_by_day(trend: list[dict]) -> list[dict]:
    """Collapse multiple same-day runs into one point per calendar day.

    get_trend_data returns one row per saved QC run, so several runs on the same
    day would otherwise render as overlapping points on the "30일" area chart.
    Rows are assumed chronological, so the last row for a given day wins (latest
    run). Output is sorted ascending by day.
    """
    by_day: dict[str, dict] = {}
    for point in trend:
        raw_date = str(point.get("date", ""))
        if not raw_date:
            continue
        day = raw_date[:10]
        by_day[day] = {**point, "date": day}
    return [by_day[day] for day in sorted(by_day)]


def fetch_qaqc_trend() -> list[dict]:
    print("Fetching QA/QC trend data...")
    try:
        from qaqc_history_db import QaQcHistoryDB

        db = QaQcHistoryDB()
        trend = aggregate_trend_by_day(db.get_trend_data(days=30))
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

        report = build_report(REPO_ROOT)
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
        # Timezone-aware so the client renders an unambiguous instant regardless
        # of where the sync host and the viewer are located.
        "last_updated": datetime.now().astimezone().isoformat(),
        "github": fetch_github_repos(),
        "notebooklm": fetch_notebooklm_notebooks(),
        "sessions": parse_session_log(),
    }

    if QAQC_FILE.exists():
        try:
            with QAQC_FILE.open("r", encoding="utf-8") as file_obj:
                qaqc_data = json.load(file_obj)

            qaqc_data["trend"] = fetch_qaqc_trend()
            # NOTE: intentionally NOT embedded into dashboard_data.json. The client
            # always reads QA/QC from /api/data/qaqc (data/qaqc_result.json), so an
            # embedded copy here would be dead, payload-bloating, and a staleness trap.
            # Mirror the fresh QA/QC payload into the authenticated data/ location
            # that the Next route serves, so /api/data/qaqc never returns stale data.
            try:
                with QAQC_DATA_FILE.open("w", encoding="utf-8") as data_obj:
                    json.dump(qaqc_data, data_obj, indent=2, ensure_ascii=False)
                print(f"  - QA/QC result loaded and mirrored to {QAQC_DATA_FILE}")
            except Exception as mirror_exc:
                print(f"  - QA/QC result loaded (mirror to data/ failed: {mirror_exc})")
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
