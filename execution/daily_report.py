"""
Daily report generator for workspace activity.

Usage:
    python execution/daily_report.py [--date YYYY-MM-DD] [--format json|markdown]
"""

import argparse
import json
import os
import subprocess
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

WORKSPACE = Path(__file__).resolve().parent.parent
REPORT_DIR = WORKSPACE / ".tmp" / "reports"

REPO_SCAN_EXCLUDED_DIRS = {"node_modules", "venv", ".tmp", "__pycache__"}
FILE_SCAN_EXCLUDED_DIRS = REPO_SCAN_EXCLUDED_DIRS | {".git"}


def _target_time_window(target_date: date) -> Tuple[datetime, datetime]:
    window_start = datetime.combine(target_date, datetime.min.time())
    window_end = window_start + timedelta(days=1)
    return window_start, window_end


def _git_time_window(target_date: date) -> Tuple[str, str]:
    date_text = target_date.strftime("%Y-%m-%d")
    return f"{date_text}T00:00:00", f"{date_text}T23:59:59"


def _find_git_repos() -> List[Path]:
    repositories: List[Path] = []
    for root, directory_names, _file_names in os.walk(str(WORKSPACE)):
        directory_names[:] = [
            directory_name
            for directory_name in directory_names
            if directory_name not in REPO_SCAN_EXCLUDED_DIRS
        ]
        if ".git" in directory_names:
            repositories.append(Path(root))
            directory_names.remove(".git")
    return repositories


def _run_git_log(repo_path: Path, since_time: str, until_time: str) -> List[str]:
    try:
        result = subprocess.run(
            [
                "git",
                "log",
                f"--since={since_time}",
                f"--until={until_time}",
                "--pretty=format:%H|%s|%an|%ai",
                "--all",
            ],
            cwd=str(repo_path),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []

    if result.returncode != 0:
        return []

    stdout = (result.stdout or "").strip()
    if not stdout:
        return []

    return stdout.splitlines()


def _parse_commit_line(repo_name: str, raw_line: str) -> Optional[Dict]:
    parts = raw_line.split("|", 3)
    if len(parts) != 4:
        return None

    commit_hash, message, author_name, committed_at = parts
    return {
        "repo": repo_name,
        "hash": commit_hash[:8],
        "message": message,
        "author": author_name,
        "date": committed_at,
    }


def collect_git_activity(target_date: date) -> List[Dict]:
    since_time, until_time = _git_time_window(target_date)
    commit_entries: List[Dict] = []

    for repo_path in _find_git_repos():
        raw_log_lines = _run_git_log(repo_path, since_time, until_time)
        for raw_line in raw_log_lines:
            commit_entry = _parse_commit_line(repo_path.name, raw_line)
            if commit_entry is not None:
                commit_entries.append(commit_entry)

    return commit_entries


def collect_file_changes(target_date: date) -> Dict:
    modified_file_count = 0
    window_start, window_end = _target_time_window(target_date)

    for root, directory_names, file_names in os.walk(str(WORKSPACE)):
        directory_names[:] = [
            directory_name
            for directory_name in directory_names
            if directory_name not in FILE_SCAN_EXCLUDED_DIRS
        ]
        for file_name in file_names:
            file_path = Path(root) / file_name
            try:
                modified_at = datetime.fromtimestamp(file_path.stat().st_mtime)
            except OSError:
                continue

            if window_start <= modified_at < window_end:
                modified_file_count += 1

    return {"files_modified": modified_file_count, "date": target_date.isoformat()}


def collect_scheduler_logs(target_date: date) -> List[Dict]:
    try:
        from execution.scheduler_engine import get_logs
    except Exception:
        return []

    log_entries = get_logs(limit=200)
    target_date_prefix = target_date.isoformat()
    scheduler_events: List[Dict] = []

    for log_entry in log_entries:
        started_at = log_entry.started_at
        if not started_at or not started_at.startswith(target_date_prefix):
            continue
        scheduler_events.append(
            {
                "task_name": log_entry.task_name,
                "started_at": started_at,
                "exit_code": log_entry.exit_code,
            }
        )
    return scheduler_events


def _summarize_commits_by_repo(commit_entries: List[Dict]) -> Dict[str, int]:
    commits_by_repo: Dict[str, int] = {}
    for commit_entry in commit_entries:
        repo_name = commit_entry["repo"]
        commits_by_repo[repo_name] = commits_by_repo.get(repo_name, 0) + 1
    return commits_by_repo


def _build_summary(
    commit_entries: List[Dict],
    commits_by_repo: Dict[str, int],
    file_changes: Dict,
    scheduler_logs: List[Dict],
) -> Dict:
    return {
        "total_commits": len(commit_entries),
        "active_repos": len(commits_by_repo),
        "files_modified": file_changes["files_modified"],
        "scheduler_tasks_run": len(scheduler_logs),
    }


def _build_report_payload(
    report_date: date,
    commit_entries: List[Dict],
    file_changes: Dict,
    scheduler_logs: List[Dict],
) -> Dict:
    commits_by_repo = _summarize_commits_by_repo(commit_entries)
    summary = _build_summary(commit_entries, commits_by_repo, file_changes, scheduler_logs)
    return {
        "date": report_date.isoformat(),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "summary": summary,
        "git_activity": {
            "commits": commit_entries,
            "by_repo": commits_by_repo,
        },
        "file_changes": file_changes,
        "scheduler_logs": scheduler_logs,
    }


def _save_report(report_date: date, report_payload: Dict) -> Path:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_DIR / f"daily_{report_date.isoformat()}.json"
    report_path.write_text(
        json.dumps(report_payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return report_path


def generate_report(target_date: Optional[date] = None) -> Dict:
    report_date = target_date or date.today()
    commit_entries = collect_git_activity(report_date)
    file_changes = collect_file_changes(report_date)
    scheduler_logs = collect_scheduler_logs(report_date)

    report_payload = _build_report_payload(
        report_date,
        commit_entries,
        file_changes,
        scheduler_logs,
    )
    _save_report(report_date, report_payload)
    return report_payload


def send_report_to_telegram(report: Dict) -> Dict:
    try:
        from execution.telegram_notifier import send_daily_report
    except ModuleNotFoundError:
        from telegram_notifier import send_daily_report
    return send_daily_report(report)


def _print_markdown_report(report: Dict) -> None:
    summary = report["summary"]
    print(f"# Daily Report: {report['date']}")
    print("\n## Summary")
    print(f"- Commits: {summary['total_commits']}")
    print(f"- Active repos: {summary['active_repos']}")
    print(f"- Files modified: {summary['files_modified']}")
    print(f"- Scheduler tasks: {summary['scheduler_tasks_run']}")
    commits = report["git_activity"]["commits"]
    if commits:
        print("\n## Git Commits")
        for commit in commits:
            print(f"- [{commit['repo']}] {commit['hash']} {commit['message']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Joolife Daily Report Generator")
    parser.add_argument("--date", help="Target date (YYYY-MM-DD)")
    parser.add_argument("--format", choices=["json", "markdown"], default="json")
    parser.add_argument(
        "--telegram",
        action="store_true",
        help="Send the generated report summary to Telegram.",
    )
    args = parser.parse_args()

    selected_date = date.fromisoformat(args.date) if args.date else date.today()
    report = generate_report(selected_date)
    telegram_meta = None

    if args.telegram:
        response = send_report_to_telegram(report)
        telegram_meta = {
            "sent": True,
            "message_id": response.get("result", {}).get("message_id"),
        }

    if args.format == "json":
        output = dict(report)
        if telegram_meta is not None:
            output["telegram"] = telegram_meta
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        _print_markdown_report(report)
        if telegram_meta is not None:
            print("\n## Telegram")
            print(f"- Sent: {telegram_meta['sent']}")
            print(f"- Message ID: {telegram_meta['message_id']}")
