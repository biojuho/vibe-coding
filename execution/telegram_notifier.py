"""
Telegram notification helpers for Joolife Hub.

Usage:
    python execution/telegram_notifier.py check
    python execution/telegram_notifier.py updates --limit 10
    python execution/telegram_notifier.py send --message "hello"
    python execution/telegram_notifier.py daily-report --date 2026-02-28
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_API_BASE = "https://api.telegram.org"
DEFAULT_MESSAGE_LIMIT = 4000


@dataclass(frozen=True)
class TelegramConfig:
    bot_token: str
    chat_id: str
    enabled: bool
    scheduler_mode: str


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def load_config() -> TelegramConfig:
    scheduler_mode = os.getenv("TELEGRAM_NOTIFY_SCHEDULER", "failures").strip().lower()
    if scheduler_mode not in {"none", "failures", "all"}:
        scheduler_mode = "failures"
    return TelegramConfig(
        bot_token=os.getenv("TELEGRAM_BOT_TOKEN", "").strip(),
        chat_id=os.getenv("TELEGRAM_CHAT_ID", "").strip(),
        enabled=_env_flag("TELEGRAM_ENABLED", default=True),
        scheduler_mode=scheduler_mode,
    )


def is_configured(config: Optional[TelegramConfig] = None) -> bool:
    active_config = config or load_config()
    return bool(active_config.enabled and active_config.bot_token and active_config.chat_id)


def _api_url(bot_token: str, method_name: str) -> str:
    return f"{TELEGRAM_API_BASE}/bot{bot_token}/{method_name}"


def _validate_message(text: str) -> str:
    clean_text = (text or "").strip()
    if not clean_text:
        raise ValueError("Telegram message is empty.")
    if len(clean_text) <= DEFAULT_MESSAGE_LIMIT:
        return clean_text
    return clean_text[: DEFAULT_MESSAGE_LIMIT - 3].rstrip() + "..."


def _raise_for_telegram_error(response: requests.Response) -> None:
    response.raise_for_status()
    payload = response.json()
    if not payload.get("ok"):
        description = payload.get("description", "Telegram API request failed.")
        raise RuntimeError(description)


def get_me(timeout: int = 15) -> Dict[str, Any]:
    config = load_config()
    if not config.bot_token:
        raise ValueError("TELEGRAM_BOT_TOKEN is not configured.")
    response = requests.get(_api_url(config.bot_token, "getMe"), timeout=timeout)
    _raise_for_telegram_error(response)
    return response.json()


def get_updates(limit: int = 10, timeout: int = 0) -> List[Dict[str, Any]]:
    config = load_config()
    if not config.bot_token:
        raise ValueError("TELEGRAM_BOT_TOKEN is not configured.")
    response = requests.get(
        _api_url(config.bot_token, "getUpdates"),
        params={"limit": max(1, min(int(limit), 100)), "timeout": max(0, int(timeout))},
        timeout=max(15, int(timeout) + 5),
    )
    _raise_for_telegram_error(response)
    payload = response.json()
    return payload.get("result", [])


def send_message(
    text: str,
    *,
    chat_id: Optional[str] = None,
    disable_notification: bool = False,
    timeout: int = 15,
) -> Dict[str, Any]:
    config = load_config()
    if not config.enabled:
        raise RuntimeError("Telegram notifications are disabled by TELEGRAM_ENABLED.")
    target_chat_id = (chat_id or config.chat_id).strip()
    if not config.bot_token:
        raise ValueError("TELEGRAM_BOT_TOKEN is not configured.")
    if not target_chat_id:
        raise ValueError("TELEGRAM_CHAT_ID is not configured.")

    response = requests.post(
        _api_url(config.bot_token, "sendMessage"),
        json={
            "chat_id": target_chat_id,
            "text": _validate_message(text),
            "disable_notification": disable_notification,
        },
        timeout=timeout,
    )
    _raise_for_telegram_error(response)
    return response.json()


def format_scheduler_message(
    *,
    task_name: str,
    exit_code: int,
    trigger_type: str,
    duration_ms: int,
    error_type: str = "",
    stderr: str = "",
    auto_disabled: bool = False,
) -> str:
    status_text = "SUCCESS" if exit_code == 0 else "FAILED"
    lines = [
        f"[Joolife][Scheduler] {status_text}",
        f"Task: {task_name}",
        f"Trigger: {trigger_type}",
        f"Exit code: {exit_code}",
        f"Duration: {duration_ms} ms",
    ]
    if error_type:
        lines.append(f"Error type: {error_type}")
    if auto_disabled:
        lines.append("Auto-disabled: yes")
    cleaned_stderr = (stderr or "").strip()
    if cleaned_stderr:
        lines.append(f"Error: {cleaned_stderr[:300]}")
    return "\n".join(lines)


def maybe_send_scheduler_notification(
    *,
    task_name: str,
    exit_code: int,
    trigger_type: str,
    duration_ms: int,
    error_type: str = "",
    stderr: str = "",
    auto_disabled: bool = False,
) -> Optional[Dict[str, Any]]:
    config = load_config()
    if not is_configured(config):
        return None
    if config.scheduler_mode == "none":
        return None
    if config.scheduler_mode == "failures" and exit_code == 0:
        return None
    return send_message(
        format_scheduler_message(
            task_name=task_name,
            exit_code=exit_code,
            trigger_type=trigger_type,
            duration_ms=duration_ms,
            error_type=error_type,
            stderr=stderr,
            auto_disabled=auto_disabled,
        )
    )


def format_daily_report_message(report: Dict[str, Any], max_commits: int = 5) -> str:
    summary = report.get("summary", {})
    commits = report.get("git_activity", {}).get("commits", [])
    lines = [
        f"[Joolife][Daily Report] {report.get('date', '')}",
        f"Commits: {summary.get('total_commits', 0)}",
        f"Active repos: {summary.get('active_repos', 0)}",
        f"Files modified: {summary.get('files_modified', 0)}",
        f"Scheduler tasks: {summary.get('scheduler_tasks_run', 0)}",
    ]
    if commits:
        lines.append("Recent commits:")
        for commit in commits[:max_commits]:
            repo_name = commit.get("repo", "?")
            commit_hash = commit.get("hash", "")
            message = commit.get("message", "")
            lines.append(f"- [{repo_name}] {commit_hash} {message}".strip())
    return "\n".join(lines)


def send_daily_report(report: Dict[str, Any]) -> Dict[str, Any]:
    return send_message(format_daily_report_message(report))


def _build_check_payload() -> Dict[str, Any]:
    config = load_config()
    payload: Dict[str, Any] = {
        "enabled": config.enabled,
        "configured": is_configured(config),
        "has_bot_token": bool(config.bot_token),
        "has_chat_id": bool(config.chat_id),
        "scheduler_mode": config.scheduler_mode,
    }
    if config.bot_token:
        try:
            me = get_me()
            payload["bot"] = me.get("result", {})
        except Exception as exc:
            payload["bot_error"] = str(exc)
    return payload


def _parse_date(date_text: Optional[str]) -> date:
    return date.fromisoformat(date_text) if date_text else date.today()


def main() -> int:
    parser = argparse.ArgumentParser(description="Joolife Telegram Notifier")
    subparsers = parser.add_subparsers(dest="cmd")

    subparsers.add_parser("check")

    p_updates = subparsers.add_parser("updates")
    p_updates.add_argument("--limit", type=int, default=10)
    p_updates.add_argument("--timeout", type=int, default=0)

    p_send = subparsers.add_parser("send")
    p_send.add_argument("--message", required=True)
    p_send.add_argument("--disable-notification", action="store_true")

    p_report = subparsers.add_parser("daily-report")
    p_report.add_argument("--date")

    args = parser.parse_args()

    if args.cmd == "check":
        print(json.dumps(_build_check_payload(), indent=2, ensure_ascii=False))
        return 0

    if args.cmd == "updates":
        updates = get_updates(limit=args.limit, timeout=args.timeout)
        print(json.dumps(updates, indent=2, ensure_ascii=False))
        return 0

    if args.cmd == "send":
        response = send_message(
            args.message,
            disable_notification=bool(args.disable_notification),
        )
        print(json.dumps(response, indent=2, ensure_ascii=False))
        return 0

    if args.cmd == "daily-report":
        try:
            from execution.daily_report import generate_report
        except ModuleNotFoundError:
            from daily_report import generate_report

        report = generate_report(_parse_date(args.date))
        response = send_daily_report(report)
        print(
            json.dumps(
                {
                    "date": report["date"],
                    "message_id": response.get("result", {}).get("message_id"),
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
