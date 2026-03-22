"""
Telegram notification helpers for Joolife Hub.

Usage:
    python execution/telegram_notifier.py check
    python execution/telegram_notifier.py updates --limit 10
    python execution/telegram_notifier.py send --message "hello"
    python execution/telegram_notifier.py daily-report --date 2026-02-28
"""

from __future__ import annotations

import execution._logging  # noqa: F401 — loguru 중앙 설정 활성화

import argparse
import json
import os
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_API_BASE = "https://api.telegram.org"
DEFAULT_MESSAGE_LIMIT = 4000
STATUS_PATH = Path(__file__).resolve().parent.parent / ".tmp" / "telegram_status.json"


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


def _load_status_payload() -> Dict[str, Any]:
    if not STATUS_PATH.exists():
        return {}
    try:
        return json.loads(STATUS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _record_delivery_status(
    *,
    ok: bool,
    message_text: str,
    error: str = "",
    response_payload: Optional[Dict[str, Any]] = None,
) -> None:
    payload = _load_status_payload()
    now_iso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    payload.update(
        {
            "last_attempt_at": now_iso,
            "last_delivery_ok": ok,
            "last_error": error[:300],
            "last_message_preview": message_text[:120],
        }
    )
    if ok:
        payload["last_success_at"] = now_iso
        payload["last_error"] = ""
        payload["last_message_id"] = (
            (response_payload or {}).get("result", {}).get("message_id")
            if isinstance(response_payload, dict)
            else None
        )
    else:
        payload["last_failure_at"] = now_iso

    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def get_delivery_status_summary() -> Dict[str, Any]:
    config = load_config()
    payload = _load_status_payload()
    summary: Dict[str, Any] = {
        "enabled": config.enabled,
        "configured": is_configured(config),
        "has_bot_token": bool(config.bot_token),
        "has_chat_id": bool(config.chat_id),
        "scheduler_mode": config.scheduler_mode,
        "last_attempt_at": payload.get("last_attempt_at", ""),
        "last_success_at": payload.get("last_success_at", ""),
        "last_failure_at": payload.get("last_failure_at", ""),
        "last_delivery_ok": payload.get("last_delivery_ok"),
        "last_error": payload.get("last_error", ""),
        "last_message_preview": payload.get("last_message_preview", ""),
        "last_message_id": payload.get("last_message_id"),
        "status": "healthy",
        "next_action": "정상 동작 중입니다.",
    }
    if not config.enabled:
        summary["status"] = "setup_required"
        summary["next_action"] = "TELEGRAM_ENABLED 설정을 확인하세요."
    elif not summary["configured"]:
        summary["status"] = "setup_required"
        summary["next_action"] = "봇 토큰과 채팅 ID를 설정하세요."
    elif payload.get("last_delivery_ok") is False:
        summary["status"] = "warning"
        summary["next_action"] = "최근 Telegram 전송 실패 원인을 확인하세요."
    elif not payload.get("last_attempt_at"):
        summary["status"] = "warning"
        summary["next_action"] = "테스트 메시지 또는 리포트 전송을 한 번 실행하세요."
    return summary


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

    validated_text = _validate_message(text)
    try:
        response = requests.post(
            _api_url(config.bot_token, "sendMessage"),
            json={
                "chat_id": target_chat_id,
                "text": validated_text,
                "disable_notification": disable_notification,
            },
            timeout=timeout,
        )
        _raise_for_telegram_error(response)
        payload = response.json()
        _record_delivery_status(ok=True, message_text=validated_text, response_payload=payload)
        return payload
    except Exception as exc:
        _record_delivery_status(ok=False, message_text=validated_text, error=str(exc))
        raise


def send_alert(
    text: str,
    level: str = "INFO",
    *,
    chat_id: Optional[str] = None,
    disable_notification: bool = False,
    timeout: int = 15,
) -> Dict[str, Any]:
    """Sends a tiered alert message to Telegram.

    Args:
        text: The message content.
        level: "CRITICAL" 🚨, "WARNING" ⚠️, or "INFO" ℹ️.
    """
    prefixes = {
        "CRITICAL": "🚨 [CRITICAL]",
        "WARNING": "⚠️ [WARNING]",
        "INFO": "ℹ️ [INFO]",
    }
    prefix = prefixes.get(level.upper(), "ℹ️ [INFO]")
    formatted_text = f"{prefix}\n{text}"
    return send_message(
        formatted_text,
        chat_id=chat_id,
        disable_notification=disable_notification,
        timeout=timeout,
    )


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
    bridge = report.get("llm_bridge", {})
    lines = [
        f"[Joolife][Daily Report] {report.get('date', '')}",
        f"Commits: {summary.get('total_commits', 0)}",
        f"Active repos: {summary.get('active_repos', 0)}",
        f"Files modified: {summary.get('files_modified', 0)}",
        f"Scheduler tasks: {summary.get('scheduler_tasks_run', 0)}",
    ]
    if summary.get("llm_bridge_calls", 0):
        lines.extend(
            [
                f"LLM bridge calls: {summary.get('llm_bridge_calls', 0)}",
                f"LLM bridge repairs: {summary.get('llm_bridge_repairs', 0)}",
                f"LLM bridge fallbacks: {summary.get('llm_bridge_fallbacks', 0)}",
            ]
        )
        top_reason_codes = bridge.get("top_reason_codes", [])
        if top_reason_codes:
            top = ", ".join(
                f"{item.get('reason_code', '?')}={item.get('count', 0)}"
                for item in top_reason_codes[:3]
            )
            lines.append(f"LLM bridge reasons: {top}")
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


# ── 알림 티어링 (P2 digest / P3 일일 요약) ───────────────


_DIGEST_FILE = Path(__file__).resolve().parent.parent / ".tmp" / "telegram_digest.json"


def queue_digest(text: str, level: str = "INFO") -> None:
    """P2/P3 알림을 digest 큐에 저장합니다 (즉시 전송하지 않음).

    30분 또는 일일 주기로 flush_digest()를 호출하면 한꺼번에 전송됩니다.
    """
    import json as _json

    _DIGEST_FILE.parent.mkdir(parents=True, exist_ok=True)
    queue: list = []
    if _DIGEST_FILE.exists():
        try:
            queue = _json.loads(_DIGEST_FILE.read_text(encoding="utf-8"))
        except Exception:
            queue = []

    queue.append({
        "text": text,
        "level": level,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    })
    _DIGEST_FILE.write_text(_json.dumps(queue, ensure_ascii=False), encoding="utf-8")


def flush_digest(*, title: str = "Digest") -> Optional[Dict[str, Any]]:
    """큐에 쌓인 알림을 하나의 메시지로 합쳐 전송합니다.

    빈 큐면 None 반환. 전송 후 큐 파일 삭제.
    """
    import json as _json

    if not _DIGEST_FILE.exists():
        return None

    try:
        queue = _json.loads(_DIGEST_FILE.read_text(encoding="utf-8"))
    except Exception:
        return None

    if not queue:
        _DIGEST_FILE.unlink(missing_ok=True)
        return None

    # 레벨별 카운트
    counts = {"CRITICAL": 0, "WARNING": 0, "INFO": 0}
    for item in queue:
        lvl = item.get("level", "INFO").upper()
        counts[lvl] = counts.get(lvl, 0) + 1

    # 가장 높은 레벨 결정
    if counts["CRITICAL"]:
        overall_level = "CRITICAL"
    elif counts["WARNING"]:
        overall_level = "WARNING"
    else:
        overall_level = "INFO"

    lines = [f"📋 {title} ({len(queue)}건)", ""]
    for item in queue[-20:]:  # 최대 20건
        prefix = {"CRITICAL": "🚨", "WARNING": "⚠️", "INFO": "ℹ️"}.get(
            item.get("level", "INFO").upper(), "ℹ️"
        )
        lines.append(f"{prefix} {item['text'][:100]}")

    if len(queue) > 20:
        lines.append(f"... +{len(queue) - 20}건 생략")

    _DIGEST_FILE.unlink(missing_ok=True)
    return send_alert("\n".join(lines), level=overall_level)


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
    p_send.add_argument("--level", default="INFO", choices=["INFO", "WARNING", "CRITICAL"])
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
        if hasattr(args, "level"):
            response = send_alert(
                args.message,
                level=args.level,
                disable_notification=bool(args.disable_notification),
            )
        else:
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
