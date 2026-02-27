from __future__ import annotations

from unittest.mock import MagicMock, patch


import execution.github_stats as gs


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_response(status_code: int = 200, json_data=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data if json_data is not None else {}
    return resp


# ---------------------------------------------------------------------------
# is_configured
# ---------------------------------------------------------------------------

def test_is_configured_true(monkeypatch):
    monkeypatch.setattr(gs, "GITHUB_TOKEN", "ghp_test_token")
    assert gs.is_configured() is True


def test_is_configured_false(monkeypatch):
    monkeypatch.setattr(gs, "GITHUB_TOKEN", "")
    assert gs.is_configured() is False


# ---------------------------------------------------------------------------
# _headers
# ---------------------------------------------------------------------------

def test_headers_include_auth_when_token_set(monkeypatch):
    monkeypatch.setattr(gs, "GITHUB_TOKEN", "ghp_abc")
    headers = gs._headers()
    assert "Authorization" in headers
    assert headers["Authorization"] == "token ghp_abc"


def test_headers_no_auth_when_no_token(monkeypatch):
    monkeypatch.setattr(gs, "GITHUB_TOKEN", "")
    headers = gs._headers()
    assert "Authorization" not in headers


# ---------------------------------------------------------------------------
# get_user
# ---------------------------------------------------------------------------

def test_get_user_returns_none_when_not_configured(monkeypatch):
    monkeypatch.setattr(gs, "GITHUB_TOKEN", "")
    result = gs.get_user()
    assert result is None


def test_get_user_returns_none_on_http_error(monkeypatch):
    monkeypatch.setattr(gs, "GITHUB_TOKEN", "tok")
    monkeypatch.setattr(gs, "_request", lambda *a, **kw: _make_response(401))
    result = gs.get_user()
    assert result is None


def test_get_user_parses_response(monkeypatch):
    monkeypatch.setattr(gs, "GITHUB_TOKEN", "tok")
    payload = {
        "login": "jooho",
        "name": "Joo Ho",
        "bio": "dev",
        "avatar_url": "https://avatars.example.com/1",
        "public_repos": 10,
        "followers": 5,
        "following": 3,
    }
    monkeypatch.setattr(gs, "_request", lambda *a, **kw: _make_response(200, payload))
    user = gs.get_user()
    assert user is not None
    assert user["login"] == "jooho"
    assert user["public_repos"] == 10


# ---------------------------------------------------------------------------
# get_repos
# ---------------------------------------------------------------------------

def test_get_repos_empty_when_not_configured(monkeypatch):
    monkeypatch.setattr(gs, "GITHUB_TOKEN", "")
    assert gs.get_repos() == []


def test_get_repos_returns_empty_on_http_error(monkeypatch):
    monkeypatch.setattr(gs, "GITHUB_TOKEN", "tok")
    monkeypatch.setattr(gs, "_request", lambda *a, **kw: _make_response(403))
    assert gs.get_repos() == []


def test_get_repos_single_page(monkeypatch):
    monkeypatch.setattr(gs, "GITHUB_TOKEN", "tok")
    raw = [
        {
            "name": "repo-a",
            "full_name": "jooho/repo-a",
            "private": False,
            "language": "Python",
            "stargazers_count": 3,
            "updated_at": "2026-02-01T00:00:00Z",
            "description": "A repo",
        }
    ]
    # 첫 페이지 응답 → 두 번째 페이지 빈 목록
    responses = iter([_make_response(200, raw), _make_response(200, [])])
    monkeypatch.setattr(gs, "_request", lambda *a, **kw: next(responses))
    repos = gs.get_repos()
    assert len(repos) == 1
    assert repos[0]["name"] == "repo-a"
    assert repos[0]["stars"] == 3


# ---------------------------------------------------------------------------
# get_commit_heatmap_data
# ---------------------------------------------------------------------------

def test_commit_heatmap_aggregates_by_day(monkeypatch):
    fake_commits = [
        {"repo": "r1", "sha": "aabbcc", "message": "feat: x", "date": "2026-02-01T10:00:00Z"},
        {"repo": "r1", "sha": "ddeeff", "message": "fix: y", "date": "2026-02-01T15:00:00Z"},
        {"repo": "r2", "sha": "001122", "message": "chore: z", "date": "2026-02-02T09:00:00Z"},
    ]
    monkeypatch.setattr(gs, "get_commits", lambda days=365: fake_commits)
    heatmap = gs.get_commit_heatmap_data(days=7)
    assert heatmap.get("2026-02-01") == 2
    assert heatmap.get("2026-02-02") == 1


def test_commit_heatmap_ignores_empty_date(monkeypatch):
    fake_commits = [
        {"repo": "r1", "sha": "abc", "message": "msg", "date": ""},
    ]
    monkeypatch.setattr(gs, "get_commits", lambda days=365: fake_commits)
    heatmap = gs.get_commit_heatmap_data()
    assert heatmap == {}


# ---------------------------------------------------------------------------
# get_pr_stats
# ---------------------------------------------------------------------------

def test_pr_stats_not_configured(monkeypatch):
    monkeypatch.setattr(gs, "GITHUB_TOKEN", "")
    stats = gs.get_pr_stats()
    assert stats == {"open": 0, "closed": 0, "merged": 0, "total": 0}


def test_pr_stats_no_user(monkeypatch):
    monkeypatch.setattr(gs, "GITHUB_TOKEN", "tok")
    monkeypatch.setattr(gs, "get_user", lambda: None)
    stats = gs.get_pr_stats()
    assert stats["total"] == 0


def test_pr_stats_aggregates_open_closed(monkeypatch):
    monkeypatch.setattr(gs, "GITHUB_TOKEN", "tok")
    monkeypatch.setattr(gs, "get_user", lambda: {"login": "jooho"})

    counts = {"open": 3, "closed": 5, "merged": 2}

    def fake_search(query: str) -> int:
        if "state:open" in query:
            return counts["open"]
        if "state:closed" in query:
            return counts["closed"]
        if "is:merged" in query:
            return counts["merged"]
        return 0

    monkeypatch.setattr(gs, "_search_issue_count", fake_search)
    stats = gs.get_pr_stats(state="all")
    assert stats["open"] == 3
    assert stats["closed"] == 5
    assert stats["merged"] == 2
    assert stats["total"] == 8  # open + closed


def test_pr_stats_open_only(monkeypatch):
    monkeypatch.setattr(gs, "GITHUB_TOKEN", "tok")
    monkeypatch.setattr(gs, "get_user", lambda: {"login": "jooho"})

    def fake_search(query: str) -> int:
        if "state:open" in query:
            return 7
        return 0

    monkeypatch.setattr(gs, "_search_issue_count", fake_search)
    stats = gs.get_pr_stats(state="open")
    assert stats["total"] == 7


def test_pr_stats_invalid_state_defaults_to_all(monkeypatch):
    monkeypatch.setattr(gs, "GITHUB_TOKEN", "tok")
    monkeypatch.setattr(gs, "get_user", lambda: {"login": "jooho"})
    monkeypatch.setattr(gs, "_search_issue_count", lambda q: 1)
    # invalid state → defaults to "all" → total = open + closed
    stats = gs.get_pr_stats(state="invalid_value")
    assert stats["total"] == 2  # 1 open + 1 closed


# ---------------------------------------------------------------------------
# get_language_stats
# ---------------------------------------------------------------------------

def test_language_stats_counts(monkeypatch):
    fake_repos = [
        {"language": "Python"},
        {"language": "Python"},
        {"language": "JavaScript"},
        {"language": None},  # 언어 미설정 repo
    ]
    monkeypatch.setattr(gs, "get_repos", lambda: fake_repos)
    stats = gs.get_language_stats()
    assert stats.get("Python") == 2
    assert stats.get("JavaScript") == 1
    assert None not in stats


def test_language_stats_sorted_descending(monkeypatch):
    fake_repos = [
        {"language": "Go"},
        {"language": "Python"},
        {"language": "Python"},
        {"language": "Python"},
        {"language": "Go"},
    ]
    monkeypatch.setattr(gs, "get_repos", lambda: fake_repos)
    stats = gs.get_language_stats()
    langs = list(stats.keys())
    assert langs[0] == "Python"  # 가장 많은 언어가 첫 번째


# ---------------------------------------------------------------------------
# _request (direct HTTP layer)
# ---------------------------------------------------------------------------

def test_request_calls_requests_get_and_logs(monkeypatch):
    monkeypatch.setattr(gs, "GITHUB_TOKEN", "tok")
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    with patch("execution.github_stats.requests.get", return_value=mock_resp) as mock_get, \
         patch("execution.github_stats.log_api_call") as mock_log:
        resp = gs._request("user")
        assert resp is mock_resp
        mock_get.assert_called_once()
        mock_log.assert_called_once()


# ---------------------------------------------------------------------------
# get_repos edge case: empty first page
# ---------------------------------------------------------------------------

def test_get_repos_empty_first_page(monkeypatch):
    monkeypatch.setattr(gs, "GITHUB_TOKEN", "tok")
    monkeypatch.setattr(gs, "_request", lambda *a, **kw: _make_response(200, []))
    assert gs.get_repos() == []


# ---------------------------------------------------------------------------
# get_commits
# ---------------------------------------------------------------------------

def test_get_commits_not_configured(monkeypatch):
    monkeypatch.setattr(gs, "GITHUB_TOKEN", "")
    assert gs.get_commits() == []


def test_get_commits_no_user(monkeypatch):
    monkeypatch.setattr(gs, "GITHUB_TOKEN", "tok")
    monkeypatch.setattr(gs, "get_user", lambda: None)
    assert gs.get_commits() == []


def test_get_commits_returns_commits(monkeypatch):
    monkeypatch.setattr(gs, "GITHUB_TOKEN", "tok")
    monkeypatch.setattr(gs, "get_user", lambda: {"login": "jooho"})
    monkeypatch.setattr(gs, "get_repos", lambda: [{"name": "repo-a", "full_name": "jooho/repo-a"}])
    commit_data = [
        {
            "sha": "abc123def456",
            "commit": {
                "message": "feat: add feature\n\nLong description",
                "author": {"date": "2026-02-01T10:00:00Z"},
            },
        }
    ]
    monkeypatch.setattr(gs, "_request", lambda *a, **kw: _make_response(200, commit_data))
    commits = gs.get_commits(days=7)
    assert len(commits) == 1
    assert commits[0]["repo"] == "repo-a"
    assert commits[0]["sha"] == "abc123de"
    assert commits[0]["message"] == "feat: add feature"
    assert commits[0]["date"] == "2026-02-01T10:00:00Z"


def test_get_commits_skips_failed_repos(monkeypatch):
    monkeypatch.setattr(gs, "GITHUB_TOKEN", "tok")
    monkeypatch.setattr(gs, "get_user", lambda: {"login": "jooho"})
    monkeypatch.setattr(gs, "get_repos", lambda: [
        {"name": "repo-a", "full_name": "jooho/repo-a"},
        {"name": "repo-b", "full_name": "jooho/repo-b"},
    ])
    good_commit = [{"sha": "aabb1122", "commit": {"message": "fix", "author": {"date": "2026-02-01T09:00:00Z"}}}]
    responses = iter([_make_response(403), _make_response(200, good_commit)])
    monkeypatch.setattr(gs, "_request", lambda *a, **kw: next(responses))
    commits = gs.get_commits()
    assert len(commits) == 1
    assert commits[0]["repo"] == "repo-b"


def test_get_commits_sorted_descending(monkeypatch):
    monkeypatch.setattr(gs, "GITHUB_TOKEN", "tok")
    monkeypatch.setattr(gs, "get_user", lambda: {"login": "jooho"})
    monkeypatch.setattr(gs, "get_repos", lambda: [{"name": "r", "full_name": "jooho/r"}])
    commit_data = [
        {"sha": "aa", "commit": {"message": "first", "author": {"date": "2026-01-01T00:00:00Z"}}},
        {"sha": "bb", "commit": {"message": "second", "author": {"date": "2026-02-01T00:00:00Z"}}},
    ]
    monkeypatch.setattr(gs, "_request", lambda *a, **kw: _make_response(200, commit_data))
    commits = gs.get_commits()
    assert commits[0]["date"] > commits[1]["date"]


# ---------------------------------------------------------------------------
# _search_issue_count (direct)
# ---------------------------------------------------------------------------

def test_search_issue_count_returns_total(monkeypatch):
    monkeypatch.setattr(gs, "_request", lambda *a, **kw: _make_response(200, {"total_count": 42}))
    assert gs._search_issue_count("author:jooho type:pr state:open") == 42


def test_search_issue_count_returns_zero_on_error(monkeypatch):
    monkeypatch.setattr(gs, "_request", lambda *a, **kw: _make_response(422))
    assert gs._search_issue_count("author:jooho type:pr") == 0


# ---------------------------------------------------------------------------
# get_pr_stats: state="closed" branch
# ---------------------------------------------------------------------------

def test_pr_stats_closed_only(monkeypatch):
    monkeypatch.setattr(gs, "GITHUB_TOKEN", "tok")
    monkeypatch.setattr(gs, "get_user", lambda: {"login": "jooho"})

    def fake_search(query: str) -> int:
        if "state:closed" in query:
            return 4
        return 0

    monkeypatch.setattr(gs, "_search_issue_count", fake_search)
    stats = gs.get_pr_stats(state="closed")
    assert stats["total"] == 4
