"""파이프라인 상태 감시 + 자동 Telegram 알림.

스케줄러에 등록하여 파이프라인 직후(매일 20:30) 실행하거나,
수동으로 시스템 상태를 점검할 때 사용합니다.

Usage (CLI):
    python execution/pipeline_watchdog.py              # 전체 점검 + 알림
    python execution/pipeline_watchdog.py --json       # JSON 출력만
    python execution/pipeline_watchdog.py --no-notify  # 알림 없이 점검만
    python execution/pipeline_watchdog.py --daily      # 매일 요약 리포트 (성공해도 전송)

Usage (library):
    from execution.pipeline_watchdog import PipelineWatchdog
    wd = PipelineWatchdog()
    report = wd.run_all()
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import sqlite3
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

_ROOT = Path(__file__).resolve().parent.parent
_BTX_ROOT = _ROOT / "blind-to-x"
_BTX_TMP = _BTX_ROOT / ".tmp"
_BTX_LOG_DIR = _BTX_TMP / "logs"

# ── 상태 상수 ────────────────────────────────────────────
STATUS_OK = "ok"
STATUS_WARN = "warn"
STATUS_FAIL = "fail"
STATUS_SKIP = "skip"
STATUS_RUNNING = "running"

# ── Watchdog 결과 저장 ───────────────────────────────────
_WATCHDOG_HISTORY = _ROOT / ".tmp" / "watchdog_history.json"
_HEARTBEAT_FILE = _ROOT / ".tmp" / "watchdog_heartbeat.json"
_MAX_HISTORY = 30  # 최근 30회분만 보관
_HEARTBEAT_STALE_MINUTES = 30  # heartbeat가 이보다 오래되면 워치독 사망 판정


def _check(name: str, status: str, detail: str = "") -> Dict[str, Any]:
    """점검 결과 딕셔너리 생성."""
    return {
        "name": name,
        "status": status,
        "detail": detail,
        "checked_at": datetime.now().isoformat(timespec="seconds"),
    }


class PipelineWatchdog:
    """파이프라인 상태 감시자."""

    def __init__(self) -> None:
        self.checks: List[Dict[str, Any]] = []
        self.alerts: List[str] = []

    # ── blind-to-x 파이프라인 마지막 실행 확인 ──────────

    def check_btx_last_run(self, max_hours: int = 26) -> Dict[str, Any]:
        """blind-to-x가 최근 N시간 내에 실행됐는지 확인.

        로그 파일 경로: blind-to-x/.tmp/logs/scheduled_*.log
        Lock 파일: blind-to-x/.tmp/.running.lock
        """
        result = _check("btx_pipeline", STATUS_SKIP, "")

        # 1) lock 파일 → 현재 실행 중?
        lock_file = _BTX_TMP / ".running.lock"
        if lock_file.exists():
            try:
                lock_age_sec = (
                    datetime.now() - datetime.fromtimestamp(lock_file.stat().st_mtime)
                ).total_seconds()
                if lock_age_sec > 3600:
                    result["status"] = STATUS_WARN
                    result["detail"] = (
                        f"Stale lock ({lock_age_sec / 3600:.1f}h old) — 프로세스가 멈췄을 수 있음"
                    )
                    self.alerts.append(
                        f"⚠️ blind-to-x lock 파일이 {lock_age_sec / 3600:.1f}시간째 남아있습니다 (좀비?)"
                    )
                    self.checks.append(result)
                    return result
                else:
                    result["status"] = STATUS_RUNNING
                    result["detail"] = f"Currently running ({lock_age_sec / 60:.0f}min)"
                    self.checks.append(result)
                    return result
            except Exception:
                pass

        # 2) 로그 파일로 마지막 실행 시각 확인
        if not _BTX_LOG_DIR.exists():
            result["status"] = STATUS_WARN
            result["detail"] = "Log directory not found"
            self.checks.append(result)
            return result

        log_files = sorted(
            _BTX_LOG_DIR.glob("scheduled_*.log"),
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )

        if not log_files:
            result["status"] = STATUS_WARN
            result["detail"] = "No scheduled log files found"
            self.alerts.append("⚠️ blind-to-x 스케줄 실행 로그가 없습니다")
            self.checks.append(result)
            return result

        latest_log = log_files[0]
        last_mod = datetime.fromtimestamp(latest_log.stat().st_mtime)
        age_hours = (datetime.now() - last_mod).total_seconds() / 3600

        # 마지막 로그 내용에서 성공/실패 판별
        try:
            content = latest_log.read_text(encoding="utf-8", errors="replace")
            last_lines = content.strip().splitlines()[-5:]
            has_failure = any("Failures: " in line and "Failures: 0" not in line for line in last_lines)
        except Exception:
            has_failure = False

        if age_hours <= max_hours:
            if has_failure:
                result["status"] = STATUS_WARN
                result["detail"] = (
                    f"Last run: {last_mod:%m/%d %H:%M} ({age_hours:.1f}h ago) — 일부 실패 있음"
                )
                self.alerts.append(
                    f"⚠️ blind-to-x 마지막 실행에 실패된 태스크가 있습니다 ({latest_log.name})"
                )
            else:
                result["status"] = STATUS_OK
                result["detail"] = f"Last run: {last_mod:%m/%d %H:%M} ({age_hours:.1f}h ago) ✓"
        else:
            result["status"] = STATUS_FAIL
            result["detail"] = (
                f"Stale! Last run: {last_mod:%m/%d %H:%M} ({age_hours:.1f}h ago)"
            )
            self.alerts.append(
                f"🚨 blind-to-x가 {age_hours:.0f}시간 동안 실행되지 않았습니다!"
            )

        self.checks.append(result)
        return result

    # ── 스케줄러 태스크 상태 ────────────────────────────

    def check_scheduler_health(self) -> Dict[str, Any]:
        """내부 스케줄러(scheduler.db) 태스크 상태 점검."""
        db_path = _ROOT / ".tmp" / "scheduler.db"
        result = _check("scheduler_tasks", STATUS_SKIP, "")

        if not db_path.exists():
            result["detail"] = "scheduler.db not found (may not be in use)"
            self.checks.append(result)
            return result

        try:
            conn = sqlite3.connect(str(db_path))
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT name, enabled, failure_count, last_run, next_run FROM tasks"
            ).fetchall()
            conn.close()

            disabled_tasks: List[str] = []
            high_fail_tasks: List[str] = []

            for row in rows:
                task = dict(row)
                if not task.get("enabled"):
                    disabled_tasks.append(task["name"])
                fail_count = task.get("failure_count") or 0
                if fail_count >= 3:
                    high_fail_tasks.append(f"{task['name']}(fails={fail_count})")

            issues: List[str] = []
            if disabled_tasks:
                issues.append(f"Disabled: {', '.join(disabled_tasks)}")
            if high_fail_tasks:
                issues.append(f"High-fail: {', '.join(high_fail_tasks)}")
                self.alerts.append(f"⚠️ 스케줄러 태스크 누적 실패: {', '.join(high_fail_tasks)}")

            if high_fail_tasks:
                result["status"] = STATUS_FAIL
            elif disabled_tasks:
                result["status"] = STATUS_WARN
            else:
                result["status"] = STATUS_OK

            result["detail"] = (
                "; ".join(issues) if issues else f"{len(rows)} tasks, all healthy"
            )
        except Exception as exc:
            result["status"] = STATUS_FAIL
            result["detail"] = f"DB error: {exc}"

        self.checks.append(result)
        return result

    # ── Notion API 연결 ───────────────────────────────

    def check_notion_api(self) -> Dict[str, Any]:
        """Notion API 응답 확인."""
        result = _check("notion_api", STATUS_SKIP, "")
        api_key = os.getenv("NOTION_API_KEY", "")

        if not api_key:
            result["status"] = STATUS_FAIL
            result["detail"] = "NOTION_API_KEY not set"
            self.alerts.append("🚨 Notion API 키가 설정되지 않았습니다!")
            self.checks.append(result)
            return result

        try:
            resp = requests.get(
                "https://api.notion.com/v1/users/me",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Notion-Version": "2022-06-28",
                },
                timeout=10,
            )
            if resp.status_code == 200:
                result["status"] = STATUS_OK
                result["detail"] = "connected"
            elif resp.status_code == 401:
                result["status"] = STATUS_FAIL
                result["detail"] = "401 Unauthorized — 토큰 만료?"
                self.alerts.append("🚨 Notion API 인증 실패 (토큰 만료 가능)")
            else:
                result["status"] = STATUS_WARN
                result["detail"] = f"HTTP {resp.status_code}"
        except requests.Timeout:
            result["status"] = STATUS_FAIL
            result["detail"] = "timeout (10s)"
            self.alerts.append("🚨 Notion API 타임아웃")
        except requests.ConnectionError:
            result["status"] = STATUS_FAIL
            result["detail"] = "connection failed"
            self.alerts.append("🚨 Notion API 연결 실패 (네트워크 확인)")
        except Exception as exc:
            result["status"] = STATUS_FAIL
            result["detail"] = str(exc)[:200]

        self.checks.append(result)
        return result

    # ── Windows Task Scheduler ────────────────────────

    def check_windows_task(self, task_name: str = "BlindToX_Pipeline") -> Dict[str, Any]:
        """Windows Task Scheduler에 태스크가 등록/활성화되어 있는지 확인."""
        result = _check("win_task_scheduler", STATUS_SKIP, "")

        try:
            proc = subprocess.run(
                ["schtasks", "/Query", "/TN", task_name, "/FO", "LIST"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=10,
            )
            if proc.returncode != 0:
                result["status"] = STATUS_WARN
                result["detail"] = f"Task '{task_name}' not found in scheduler"
                self.alerts.append(f"⚠️ Windows 스케줄러에 {task_name} 태스크가 없습니다")
            else:
                lines = proc.stdout.splitlines()
                status_line = ""
                next_run_line = ""
                for line in lines:
                    low = line.lower()
                    if "status:" in low or "상태:" in line:
                        status_line = line.split(":", 1)[-1].strip()
                    if "next run time:" in low or "다음 실행 시간:" in line:
                        next_run_line = line.split(":", 1)[-1].strip()

                disabled_keywords = {"disabled", "사용 안 함", "사용 안함"}
                if any(kw in status_line.lower() for kw in disabled_keywords):
                    result["status"] = STATUS_WARN
                    result["detail"] = f"Task DISABLED (status={status_line})"
                    self.alerts.append(f"⚠️ {task_name} 스케줄러 태스크가 비활성화됨")
                else:
                    result["status"] = STATUS_OK
                    detail_parts = [f"status={status_line}"]
                    if next_run_line:
                        detail_parts.append(f"next={next_run_line}")
                    result["detail"] = ", ".join(detail_parts)

        except FileNotFoundError:
            result["status"] = STATUS_SKIP
            result["detail"] = "schtasks not available"
        except subprocess.TimeoutExpired:
            result["status"] = STATUS_WARN
            result["detail"] = "schtasks query timed out"
        except Exception as exc:
            result["status"] = STATUS_SKIP
            result["detail"] = str(exc)[:200]

        self.checks.append(result)
        return result

    # ── 디스크 공간 ──────────────────────────────────

    def check_disk_space(self, min_free_gb: float = 10.0) -> Dict[str, Any]:
        """C: 드라이브 잔여 공간 점검."""
        result = _check("disk_space", STATUS_OK, "")

        try:
            usage = shutil.disk_usage(Path(__file__).resolve().drive + "\\")
            free_gb = usage.free / (1024**3)
            total_gb = usage.total / (1024**3)

            result["detail"] = f"{free_gb:.1f}GB free / {total_gb:.0f}GB total"

            if free_gb < min_free_gb:
                result["status"] = STATUS_FAIL
                self.alerts.append(f"🚨 디스크 공간 부족! {free_gb:.1f}GB 남음")
            elif free_gb < min_free_gb * 2:
                result["status"] = STATUS_WARN
        except Exception as exc:
            result["status"] = STATUS_SKIP
            result["detail"] = str(exc)[:200]

        self.checks.append(result)
        return result

    # ── Telegram 알림 상태 ──────────────────────────

    def check_telegram(self) -> Dict[str, Any]:
        """Telegram 알림 시스템이 설정되어 있는지 확인."""
        result = _check("telegram", STATUS_SKIP, "")

        bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        chat_id = os.getenv("TELEGRAM_CHAT_ID", "")

        if not bot_token or not chat_id:
            result["status"] = STATUS_WARN
            missing = []
            if not bot_token:
                missing.append("TELEGRAM_BOT_TOKEN")
            if not chat_id:
                missing.append("TELEGRAM_CHAT_ID")
            result["detail"] = f"Missing: {', '.join(missing)}"
        else:
            result["status"] = STATUS_OK
            result["detail"] = "configured"

        self.checks.append(result)
        return result

    # ── 백업 상태 확인 ───────────────────────────────

    def check_backup_status(self) -> Dict[str, Any]:
        """OneDrive 백업이 최근에 실행되었는지 확인."""
        result = _check("backup", STATUS_SKIP, "")

        onedrive = os.getenv("OneDrive", "")
        if not onedrive:
            result["detail"] = "OneDrive path not found"
            self.checks.append(result)
            return result

        backup_dir = Path(onedrive) / "VibeCodingBackup"
        if not backup_dir.exists():
            result["status"] = STATUS_WARN
            result["detail"] = "Backup directory not created yet"
            self.checks.append(result)
            return result

        # 최신 백업 폴더 확인
        backups = sorted(backup_dir.glob("backup_*"), reverse=True)
        if not backups:
            result["status"] = STATUS_WARN
            result["detail"] = "No backups found"
            self.alerts.append("⚠️ OneDrive 백업이 한 번도 실행되지 않았습니다")
        else:
            latest = backups[0]
            latest_mod = datetime.fromtimestamp(latest.stat().st_mtime)
            age_days = (datetime.now() - latest_mod).days

            if age_days <= 2:
                result["status"] = STATUS_OK
                result["detail"] = f"Latest: {latest.name} ({age_days}d ago), {len(backups)} total"
            elif age_days <= 7:
                result["status"] = STATUS_WARN
                result["detail"] = f"Latest: {latest.name} ({age_days}d ago) — 갱신 필요"
            else:
                result["status"] = STATUS_FAIL
                result["detail"] = f"Latest: {latest.name} ({age_days}d ago) — 오래됨!"
                self.alerts.append(f"⚠️ 마지막 백업이 {age_days}일 전입니다")

        self.checks.append(result)
        return result

    # ── 전체 실행 ────────────────────────────────────

    def run_all(self) -> Dict[str, Any]:
        """모든 점검 실행."""
        self.checks.clear()
        self.alerts.clear()

        self.check_btx_last_run()
        self.check_scheduler_health()
        self.check_notion_api()
        self.check_windows_task()
        self.check_disk_space()
        self.check_telegram()
        self.check_backup_status()

        # 종합 판정
        statuses = [c["status"] for c in self.checks]
        if STATUS_FAIL in statuses:
            overall = "FAIL"
        elif STATUS_WARN in statuses:
            overall = "WARN"
        else:
            overall = "OK"

        report = {
            "overall": overall,
            "checked_at": datetime.now().isoformat(timespec="seconds"),
            "checks": self.checks,
            "alerts": self.alerts,
            "alert_count": len(self.alerts),
        }

        # 이력 저장 + heartbeat 갱신
        self._save_history(report)
        self._write_heartbeat(report["overall"])

        return report

    @staticmethod
    def _write_heartbeat(overall: str) -> None:
        """워치독 생존 신호를 기록합니다."""
        try:
            _HEARTBEAT_FILE.parent.mkdir(parents=True, exist_ok=True)
            heartbeat = {
                "pid": os.getpid(),
                "last_scan": datetime.now().isoformat(timespec="seconds"),
                "overall": overall,
            }
            _HEARTBEAT_FILE.write_text(
                json.dumps(heartbeat, ensure_ascii=False), encoding="utf-8"
            )
        except Exception as exc:
            logger.warning("Failed to write heartbeat: %s", exc)

    @staticmethod
    def check_heartbeat_fresh() -> dict:
        """워치독 heartbeat가 신선한지 확인합니다 (외부 체크용).

        Returns:
            {"alive": bool, "age_minutes": float, "detail": str}
        """
        if not _HEARTBEAT_FILE.exists():
            return {"alive": False, "age_minutes": -1, "detail": "heartbeat 파일 없음"}

        try:
            data = json.loads(_HEARTBEAT_FILE.read_text(encoding="utf-8"))
            last_scan = datetime.fromisoformat(data["last_scan"])
            age_minutes = (datetime.now() - last_scan).total_seconds() / 60

            alive = age_minutes < _HEARTBEAT_STALE_MINUTES
            return {
                "alive": alive,
                "age_minutes": round(age_minutes, 1),
                "detail": f"last={data['last_scan']}, overall={data.get('overall', '?')}, pid={data.get('pid', '?')}",
            }
        except Exception as exc:
            return {"alive": False, "age_minutes": -1, "detail": str(exc)[:200]}

    def _save_history(self, report: Dict[str, Any]) -> None:
        """점검 이력 저장 (최근 N회분)."""
        try:
            history: List[Dict[str, Any]] = []
            if _WATCHDOG_HISTORY.exists():
                history = json.loads(
                    _WATCHDOG_HISTORY.read_text(encoding="utf-8")
                )

            # 슬림 버전만 저장 (용량 절약)
            slim = {
                "overall": report["overall"],
                "checked_at": report["checked_at"],
                "alert_count": report["alert_count"],
                "alerts": report["alerts"][:5],  # 최대 5개만
            }
            history.append(slim)

            # 최근 N회분만 유지
            history = history[-_MAX_HISTORY:]

            _WATCHDOG_HISTORY.parent.mkdir(parents=True, exist_ok=True)
            _WATCHDOG_HISTORY.write_text(
                json.dumps(history, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception as exc:
            logger.warning("Failed to save watchdog history: %s", exc)

    # ── Telegram 모듈 로딩 (중복 제거) ──────────────────  # [QA 수정]

    @staticmethod
    def _load_telegram_module():
        """telegram_notifier 모듈을 동적 로딩. 실패 시 None 반환."""
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "telegram_notifier",
            _ROOT / "execution" / "telegram_notifier.py",
        )
        if spec is None or spec.loader is None:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    # ── Telegram 알림 ──────────────────────────────────────

    def send_alerts_if_needed(self) -> bool:
        """이상이 감지된 경우에만 Telegram 알림 전송."""
        if not self.alerts:
            return False

        try:
            mod = self._load_telegram_module()  # [QA 수정] DRY 적용
            if mod is None or not mod.is_configured():
                logger.info("Telegram not configured, skipping alerts")
                return False

            level = "CRITICAL" if len(self.alerts) >= 3 else "WARNING"
            msg_lines = [
                f"📊 Watchdog Report ({datetime.now():%m/%d %H:%M})",
                "",
                *self.alerts,
            ]
            mod.send_alert("\n".join(msg_lines), level=level)
            return True
        except Exception as exc:
            logger.warning("Failed to send Telegram alert: %s", exc)
            return False

    def send_daily_summary(self, report: Dict[str, Any]) -> bool:
        """매일 전체 상태 요약을 Telegram으로 전송 (성공/실패 무관)."""
        try:
            mod = self._load_telegram_module()  # [QA 수정] DRY 적용
            if mod is None or not mod.is_configured():
                return False

            icons = {STATUS_OK: "✅", STATUS_WARN: "⚠️", STATUS_FAIL: "❌",
                     STATUS_SKIP: "⏭️", STATUS_RUNNING: "🔄"}
            overall_icons = {"OK": "✅", "WARN": "⚠️", "FAIL": "❌"}

            lines = [
                f"📊 Daily Watchdog ({datetime.now():%Y-%m-%d %H:%M})",
                f"{overall_icons.get(report['overall'], '?')} Overall: {report['overall']}",
                "",
            ]
            for check in report["checks"]:
                icon = icons.get(check["status"], "?")
                lines.append(f"{icon} {check['name']}: {check['detail'][:60]}")

            if report["alerts"]:
                lines.append("")
                lines.append(f"📢 Alerts ({report['alert_count']}):")
                for alert in report["alerts"]:
                    lines.append(f"  {alert}")

            mod.send_message("\n".join(lines))
            return True
        except Exception as exc:
            logger.warning("Failed to send daily summary: %s", exc)
            return False


# ── CLI ──────────────────────────────────────────────────

def _print_report(report: Dict[str, Any]) -> None:
    """터미널 출력."""
    icons = {STATUS_OK: "✅", STATUS_WARN: "⚠️", STATUS_FAIL: "❌",
             STATUS_SKIP: "⏭️", STATUS_RUNNING: "🔄", "unknown": "❓"}
    overall_icons = {"OK": "✅", "WARN": "⚠️", "FAIL": "❌"}

    print(f"\n{'═' * 55}")
    print("  🐕 Pipeline Watchdog Report")
    print(f"  {report['checked_at']}")
    print(f"{'═' * 55}")

    for check in report["checks"]:
        icon = icons.get(check["status"], "?")
        print(f"  {icon} {check['name']}: {check['detail']}")

    print(f"\n{'─' * 55}")
    overall_icon = overall_icons.get(report["overall"], "?")
    print(f"  {overall_icon} Overall: {report['overall']}")

    if report["alerts"]:
        print(f"\n  📢 Alerts ({report['alert_count']}):")
        for alert in report["alerts"]:
            print(f"    {alert}")

    print(f"{'═' * 55}\n")


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="Pipeline Watchdog — 시스템 상태 감시")
    parser.add_argument("--json", action="store_true", help="JSON 출력")
    parser.add_argument("--no-notify", action="store_true", help="Telegram 알림 비활성화")
    parser.add_argument("--daily", action="store_true", help="매일 요약 리포트 전송 (성공해도)")
    parser.add_argument("--check-alive", action="store_true",
                        help="워치독 heartbeat 상태만 확인 (자동 재시작 체크용)")
    args = parser.parse_args()

    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        level=logging.INFO,
    )

    # --check-alive: heartbeat만 확인 후 종료
    if args.check_alive:
        hb = PipelineWatchdog.check_heartbeat_fresh()
        if args.json:
            print(json.dumps(hb, ensure_ascii=False))
        else:
            status = "ALIVE" if hb["alive"] else "DEAD"
            print(f"Watchdog: {status} ({hb['detail']})")

        if not hb["alive"]:
            # 워치독 사망 → Telegram 알림 + exit code 1
            try:
                mod = PipelineWatchdog._load_telegram_module()
                if mod and mod.is_configured():
                    age = hb["age_minutes"]
                    mod.send_alert(
                        f"🚨 Watchdog DEAD — heartbeat {age}분 전 마지막 갱신\n"
                        f"Detail: {hb['detail']}",
                        level="CRITICAL",
                    )
            except Exception:
                pass
            sys.exit(1)
        sys.exit(0)

    watchdog = PipelineWatchdog()
    report = watchdog.run_all()

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False, default=str))
    else:
        _print_report(report)

    if not args.no_notify:
        if args.daily:
            watchdog.send_daily_summary(report)
        else:
            watchdog.send_alerts_if_needed()
