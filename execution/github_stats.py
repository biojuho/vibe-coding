"""
GitHub 활동 데이터 수집기 - Joolife Hub용.

Usage:
    python execution/github_stats.py repos
    python execution/github_stats.py commits --days 30
    python execution/github_stats.py prs [--state open|closed|all]
"""

import argparse
import json
import os
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import requests
from dotenv import load_dotenv

try:
    from execution.api_usage_tracker import log_api_call
except Exception:  # pragma: no cover - optional integration
    def log_api_call(**_kwargs):
        return None

# 두 .env 파일 모두 로드
load_dotenv()
load_dotenv(
    str(Path(__file__).resolve().parent.parent / "infrastructure" / ".env"),
    override=False,
)

GITHUB_TOKEN = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN", "")
GITHUB_API = "https://api.github.com"


def _headers() -> Dict:
    h = {"Accept": "application/vnd.github.v3+json"}
    if GITHUB_TOKEN:
        h["Authorization"] = f"token {GITHUB_TOKEN}"
    return h


def _request(path: str, params: Optional[Dict] = None, timeout: int = 15) -> requests.Response:
    resp = requests.get(
        f"{GITHUB_API}/{path.lstrip('/')}",
        headers=_headers(),
        params=params,
        timeout=timeout,
    )
    log_api_call(
        provider="github",
        endpoint=f"GET /{path.lstrip('/')}",
        caller_script="execution/github_stats.py",
    )
    return resp


def is_configured() -> bool:
    return bool(GITHUB_TOKEN)


def get_user() -> Optional[Dict]:
    if not is_configured():
        return None
    resp = _request("user", timeout=15)
    if resp.status_code != 200:
        return None
    u = resp.json()
    return {
        "login": u.get("login"),
        "name": u.get("name"),
        "bio": u.get("bio"),
        "avatar_url": u.get("avatar_url"),
        "public_repos": u.get("public_repos"),
        "followers": u.get("followers"),
        "following": u.get("following"),
    }


def get_repos() -> List[Dict]:
    if not is_configured():
        return []
    repos = []
    page = 1
    while True:
        resp = _request(
            "user/repos",
            params={"per_page": 100, "page": page, "sort": "updated"},
            timeout=15,
        )
        if resp.status_code != 200:
            break
        data = resp.json()
        if not data:
            break
        for r in data:
            repos.append(
                {
                    "name": r["name"],
                    "full_name": r["full_name"],
                    "private": r["private"],
                    "language": r.get("language"),
                    "stars": r.get("stargazers_count", 0),
                    "updated_at": r.get("updated_at"),
                    "description": r.get("description", ""),
                }
            )
        page += 1
        if len(data) < 100:
            break
    return repos


def get_commits(days: int = 30) -> List[Dict]:
    """인증 사용자의 최근 커밋 수집 (모든 레포)."""
    if not is_configured():
        return []

    user = get_user()
    if not user:
        return []

    since = (datetime.utcnow() - timedelta(days=days)).isoformat() + "Z"
    repos = get_repos()
    commits = []

    for repo in repos[:30]:  # API 레이트 리밋 고려하여 30개 제한
        resp = _request(
            f"repos/{repo['full_name']}/commits",
            params={"since": since, "author": user["login"], "per_page": 100},
            timeout=15,
        )
        if resp.status_code != 200:
            continue
        for c in resp.json():
            commit = c.get("commit", {})
            commits.append(
                {
                    "repo": repo["name"],
                    "sha": c.get("sha", "")[:8],
                    "message": commit.get("message", "").split("\n")[0],
                    "date": commit.get("author", {}).get("date", ""),
                }
            )
    commits.sort(key=lambda x: x["date"], reverse=True)
    return commits


def get_commit_heatmap_data(days: int = 365) -> Dict[str, int]:
    """날짜별 커밋 수 반환 (히트맵용)."""
    all_commits = get_commits(days)
    heatmap = defaultdict(int)
    for c in all_commits:
        if c["date"]:
            day = c["date"][:10]
            heatmap[day] += 1
    return dict(heatmap)


def _search_issue_count(query: str) -> int:
    resp = _request(
        "search/issues",
        params={"q": query, "per_page": 1},
        timeout=15,
    )
    if resp.status_code != 200:
        return 0
    return int(resp.json().get("total_count", 0))


def get_pr_stats(state: str = "all", days: int = 30, repo_limit: int = 30) -> Dict:
    """PR 통계: open/closed/merged 수."""
    if not is_configured():
        return {"open": 0, "closed": 0, "merged": 0, "total": 0}

    user = get_user()
    if not user:
        return {"open": 0, "closed": 0, "merged": 0, "total": 0}

    state = (state or "all").lower()
    if state not in {"all", "open", "closed"}:
        state = "all"

    since = (datetime.utcnow() - timedelta(days=max(days, 1))).strftime("%Y-%m-%d")
    base_query = f"author:{user['login']} type:pr created:>={since}"

    # repo_limit is accepted for interface stability. Search endpoint already spans all repos.
    _ = repo_limit

    stats = {"open": 0, "closed": 0, "merged": 0, "total": 0}

    stats["open"] = _search_issue_count(f"{base_query} state:open")
    stats["closed"] = _search_issue_count(f"{base_query} state:closed")
    stats["merged"] = _search_issue_count(f"{base_query} is:merged")
    if state == "open":
        stats["total"] = stats["open"]
    elif state == "closed":
        stats["total"] = stats["closed"]
    else:
        stats["total"] = stats["open"] + stats["closed"]
    return stats


def get_language_stats() -> Dict[str, int]:
    """레포별 언어 사용 통계 집계."""
    repos = get_repos()
    langs = defaultdict(int)
    for r in repos:
        if r["language"]:
            langs[r["language"]] += 1
    return dict(sorted(langs.items(), key=lambda x: x[1], reverse=True))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Joolife GitHub Stats")
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("repos")

    p_commits = sub.add_parser("commits")
    p_commits.add_argument("--days", type=int, default=30)

    p_prs = sub.add_parser("prs")
    p_prs.add_argument("--state", default="all")
    p_prs.add_argument("--days", type=int, default=30)
    p_prs.add_argument("--repo-limit", type=int, default=30)

    sub.add_parser("languages")
    sub.add_parser("user")

    args = parser.parse_args()

    if args.cmd == "repos":
        print(json.dumps(get_repos(), indent=2, ensure_ascii=False))
    elif args.cmd == "commits":
        print(json.dumps(get_commits(args.days), indent=2, ensure_ascii=False))
    elif args.cmd == "prs":
        print(
            json.dumps(
                get_pr_stats(args.state, args.days, args.repo_limit),
                indent=2,
                ensure_ascii=False,
            )
        )
    elif args.cmd == "languages":
        print(json.dumps(get_language_stats(), indent=2, ensure_ascii=False))
    elif args.cmd == "user":
        print(json.dumps(get_user(), indent=2, ensure_ascii=False))
    else:
        parser.print_help()
