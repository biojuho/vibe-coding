"""Unit tests for the knowledge-dashboard data sync.

Run with: py -3.13 -m pytest projects/knowledge-dashboard/scripts/test_sync_data.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import sync_data  # noqa: E402


def test_repo_root_reaches_the_workspace_root():
    """Regression guard for the parents[] off-by-one that silently dropped
    sessions / readiness / skill_lint from the dashboard."""
    assert (sync_data.REPO_ROOT / ".ai").is_dir()
    assert (sync_data.REPO_ROOT / "workspace" / "execution").is_dir()
    # PROJECT_ROOT is the dashboard project; REPO_ROOT is two levels above it.
    assert sync_data.PROJECT_ROOT.name == "knowledge-dashboard"
    assert sync_data.REPO_ROOT == sync_data.PROJECT_ROOT.parents[1]


def test_is_notebooklm_token_template_detects_placeholders():
    assert sync_data.is_notebooklm_token_template({}) is True
    assert sync_data.is_notebooklm_token_template({"cookies": {}}) is True
    assert sync_data.is_notebooklm_token_template({"cookies": {"a": ""}}) is True
    assert sync_data.is_notebooklm_token_template({"cookies": {"a": "replace-with-real"}}) is True
    assert sync_data.is_notebooklm_token_template({"cookies": {"sid": "PLACEHOLDER-value"}}) is True
    # A realistic, non-template token is accepted.
    assert sync_data.is_notebooklm_token_template({"cookies": {"sid": "abc123realsessionvalue"}}) is False


SESSION_LOG_FIXTURE = """## 2026-06-01
Tool: Claude
Summary: first work
files changed: 5
CONDITIONALLY_APPROVED

## 2026-06-02
도구: Codex
요약: 두번째 작업
APPROVED
"""


def test_parse_session_log_extracts_bilingual_fields(tmp_path, monkeypatch):
    log = tmp_path / "SESSION_LOG.md"
    log.write_text(SESSION_LOG_FIXTURE, encoding="utf-8")
    monkeypatch.setattr(sync_data, "SESSION_LOG_PATH", log)

    sessions = sync_data.parse_session_log()
    assert len(sessions) == 2

    first, second = sessions
    assert first["date"] == "2026-06-01"
    assert first["tool"] == "Claude"
    assert first["summary"] == "first work"
    assert first["verdict"] == "CONDITIONALLY_APPROVED"
    assert first["files_changed"] == 5

    assert second["date"] == "2026-06-02"
    assert second["tool"] == "Codex"
    assert second["summary"] == "두번째 작업"
    assert second["verdict"] == "APPROVED"
    assert second["files_changed"] == 0


def test_parse_session_log_caps_at_20(tmp_path, monkeypatch):
    blocks = [f"## 2026-05-{day:02d}\nTool: Claude\nSummary: s{day}\n" for day in range(1, 26)]
    log = tmp_path / "SESSION_LOG.md"
    log.write_text("\n".join(blocks), encoding="utf-8")
    monkeypatch.setattr(sync_data, "SESSION_LOG_PATH", log)

    sessions = sync_data.parse_session_log()
    assert len(sessions) == 20  # last 20 only
    # The most recent 20 are kept (days 6..25), in document order.
    assert sessions[0]["date"] == "2026-05-06"
    assert sessions[-1]["date"] == "2026-05-25"


def test_aggregate_trend_by_day_keeps_latest_per_day():
    trend = [
        {"date": "2026-06-01T10:00", "passed": 5, "failed": 1},
        {"date": "2026-06-01T20:00", "passed": 7, "failed": 0},
        {"date": "2026-06-02T09:00", "passed": 3, "failed": 2},
    ]
    out = sync_data.aggregate_trend_by_day(trend)
    assert [p["date"] for p in out] == ["2026-06-01", "2026-06-02"]
    assert out[0]["passed"] == 7  # later same-day run wins
    assert out[1]["failed"] == 2
    assert sync_data.aggregate_trend_by_day([]) == []


def test_candidate_token_paths_honors_env_and_dedupes(tmp_path, monkeypatch):
    monkeypatch.setenv("NOTEBOOKLM_AUTH_TOKEN_PATH", "custom/auth.json")
    paths = sync_data._candidate_notebooklm_token_paths(tmp_path)
    assert paths[0] == tmp_path / "custom" / "auth.json"
    names = [p.name for p in paths]
    assert "auth.local.json" in names
    assert "auth.json" in names
    # No duplicates.
    assert len(paths) == len(set(str(p) for p in paths))
