"""Pipeline Watchdog tests — mocked external dependencies."""

import json
import os
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch


from execution.pipeline_watchdog import (
    STATUS_FAIL,
    STATUS_OK,
    STATUS_RUNNING,
    STATUS_SKIP,
    STATUS_WARN,
    PipelineWatchdog,
    _check,
)


class TestCheckHelper:
    def test_creates_dict(self):
        r = _check("test_name", STATUS_OK, "all good")
        assert r["name"] == "test_name"
        assert r["status"] == STATUS_OK
        assert r["detail"] == "all good"
        assert "checked_at" in r


class TestCheckDiskSpace:
    def test_ok_plenty_of_space(self):
        wd = PipelineWatchdog()
        # Real disk check (should pass on any dev machine with >10GB free)
        result = wd.check_disk_space(min_free_gb=0.001)
        assert result["status"] == STATUS_OK

    @patch("execution.pipeline_watchdog.shutil.disk_usage")
    def test_fail_low_space(self, mock_usage):
        mock_usage.return_value = MagicMock(free=5 * 1024**3, total=500 * 1024**3)
        wd = PipelineWatchdog()
        result = wd.check_disk_space(min_free_gb=10.0)
        assert result["status"] == STATUS_FAIL
        assert len(wd.alerts) > 0

    @patch("execution.pipeline_watchdog.shutil.disk_usage")
    def test_warn_moderate_space(self, mock_usage):
        mock_usage.return_value = MagicMock(free=15 * 1024**3, total=500 * 1024**3)
        wd = PipelineWatchdog()
        result = wd.check_disk_space(min_free_gb=10.0)
        assert result["status"] == STATUS_WARN

    @patch("execution.pipeline_watchdog.shutil.disk_usage", side_effect=OSError("no"))
    def test_skip_on_error(self, _):
        wd = PipelineWatchdog()
        result = wd.check_disk_space()
        assert result["status"] == STATUS_SKIP


class TestCheckTelegram:
    @patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "tok", "TELEGRAM_CHAT_ID": "123"})
    def test_configured(self):
        wd = PipelineWatchdog()
        result = wd.check_telegram()
        assert result["status"] == STATUS_OK

    @patch.dict(os.environ, {}, clear=True)
    def test_missing_vars(self):
        wd = PipelineWatchdog()
        result = wd.check_telegram()
        assert result["status"] == STATUS_WARN
        assert "TELEGRAM_BOT_TOKEN" in result["detail"]


class TestCheckNotionApi:
    @patch.dict(os.environ, {"NOTION_API_KEY": ""}, clear=False)
    def test_no_key(self):
        wd = PipelineWatchdog()
        result = wd.check_notion_api()
        assert result["status"] == STATUS_FAIL

    @patch("execution.pipeline_watchdog.requests.get")
    @patch.dict(os.environ, {"NOTION_API_KEY": "secret_test"})
    def test_success(self, mock_get):
        mock_get.return_value = MagicMock(status_code=200)
        wd = PipelineWatchdog()
        result = wd.check_notion_api()
        assert result["status"] == STATUS_OK

    @patch("execution.pipeline_watchdog.requests.get")
    @patch.dict(os.environ, {"NOTION_API_KEY": "secret_test"})
    def test_unauthorized(self, mock_get):
        mock_get.return_value = MagicMock(status_code=401)
        wd = PipelineWatchdog()
        result = wd.check_notion_api()
        assert result["status"] == STATUS_FAIL

    @patch("execution.pipeline_watchdog.requests.get", side_effect=Exception("timeout"))
    @patch.dict(os.environ, {"NOTION_API_KEY": "secret_test"})
    def test_exception(self, _):
        wd = PipelineWatchdog()
        result = wd.check_notion_api()
        assert result["status"] == STATUS_FAIL


class TestCheckSchedulerHealth:
    def test_no_db(self):
        wd = PipelineWatchdog()
        with patch.object(Path, "exists", return_value=False):
            result = wd.check_scheduler_health()
        assert result["status"] == STATUS_SKIP

    def test_healthy_db(self, tmp_path):
        db_path = tmp_path / "scheduler.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            "CREATE TABLE tasks (name TEXT, enabled INTEGER, failure_count INTEGER, last_run TEXT, next_run TEXT)"
        )
        conn.execute("INSERT INTO tasks VALUES ('btx', 1, 0, '2026-03-22', '2026-03-23')")
        conn.commit()
        conn.close()

        wd = PipelineWatchdog()
        with patch("execution.pipeline_watchdog._ROOT", tmp_path):
            (tmp_path / ".tmp").mkdir(exist_ok=True)
            import shutil

            shutil.copy(str(db_path), str(tmp_path / ".tmp" / "scheduler.db"))
            result = wd.check_scheduler_health()
        assert result["status"] == STATUS_OK

    def test_high_fail_tasks(self, tmp_path):
        db_path = tmp_path / ".tmp" / "scheduler.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            "CREATE TABLE tasks (name TEXT, enabled INTEGER, failure_count INTEGER, last_run TEXT, next_run TEXT)"
        )
        conn.execute("INSERT INTO tasks VALUES ('btx', 1, 5, '2026-03-22', '2026-03-23')")
        conn.commit()
        conn.close()

        wd = PipelineWatchdog()
        with patch("execution.pipeline_watchdog._ROOT", tmp_path):
            result = wd.check_scheduler_health()
        assert result["status"] == STATUS_FAIL


class TestCheckBackup:
    @patch.dict(os.environ, {}, clear=True)
    def test_no_onedrive(self):
        wd = PipelineWatchdog()
        # Clear OneDrive env
        os.environ.pop("OneDrive", None)
        result = wd.check_backup_status()
        assert result["status"] == STATUS_SKIP

    @patch.dict(os.environ, {"OneDrive": "/nonexistent"})
    def test_no_backup_dir(self):
        wd = PipelineWatchdog()
        result = wd.check_backup_status()
        # Either WARN (dir missing) or SKIP (path not found)
        assert result["status"] in (STATUS_WARN, STATUS_SKIP)


class TestCheckWindowsTask:
    @patch("execution.pipeline_watchdog.subprocess.run")
    def test_task_not_found(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="")
        wd = PipelineWatchdog()
        result = wd.check_windows_task()
        assert result["status"] == STATUS_WARN

    @patch("execution.pipeline_watchdog.subprocess.run")
    def test_task_found_enabled(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="TaskName: BlindToX\nStatus: Ready\nNext Run Time: 2026-03-23 20:30",
            stderr="",
        )
        wd = PipelineWatchdog()
        result = wd.check_windows_task()
        assert result["status"] == STATUS_OK

    @patch("execution.pipeline_watchdog.subprocess.run", side_effect=FileNotFoundError)
    def test_schtasks_not_available(self, _):
        wd = PipelineWatchdog()
        result = wd.check_windows_task()
        assert result["status"] == STATUS_SKIP


class TestCheckBtxLastRun:
    def test_no_log_dir(self):
        wd = PipelineWatchdog()
        with (
            patch("execution.pipeline_watchdog._BTX_LOG_DIR", Path("/nonexistent")),
            patch("execution.pipeline_watchdog._BTX_TMP", Path("/nonexistent")),
        ):
            result = wd.check_btx_last_run()
        assert result["status"] == STATUS_WARN

    def test_running_lock(self, tmp_path):
        lock = tmp_path / ".running.lock"
        lock.write_text("running")

        wd = PipelineWatchdog()
        with (
            patch("execution.pipeline_watchdog._BTX_TMP", tmp_path),
            patch("execution.pipeline_watchdog._BTX_LOG_DIR", tmp_path / "logs"),
        ):
            result = wd.check_btx_last_run()
        assert result["status"] == STATUS_RUNNING


class TestRunAll:
    @patch.object(PipelineWatchdog, "check_btx_last_run", return_value=_check("btx", STATUS_OK))
    @patch.object(PipelineWatchdog, "check_scheduler_health", return_value=_check("sched", STATUS_OK))
    @patch.object(PipelineWatchdog, "check_notion_api", return_value=_check("notion", STATUS_OK))
    @patch.object(PipelineWatchdog, "check_windows_task", return_value=_check("wintask", STATUS_OK))
    @patch.object(PipelineWatchdog, "check_disk_space", return_value=_check("disk", STATUS_OK))
    @patch.object(PipelineWatchdog, "check_telegram", return_value=_check("tg", STATUS_OK))
    @patch.object(PipelineWatchdog, "check_backup_status", return_value=_check("backup", STATUS_OK))
    @patch.object(PipelineWatchdog, "_save_history")
    def test_all_ok(self, *_mocks):
        wd = PipelineWatchdog()
        report = wd.run_all()
        assert report["overall"] == "OK"

    @patch.object(PipelineWatchdog, "check_btx_last_run")
    @patch.object(PipelineWatchdog, "check_scheduler_health")
    @patch.object(PipelineWatchdog, "check_notion_api")
    @patch.object(PipelineWatchdog, "check_windows_task")
    @patch.object(PipelineWatchdog, "check_disk_space")
    @patch.object(PipelineWatchdog, "check_telegram")
    @patch.object(PipelineWatchdog, "check_backup_status")
    @patch.object(PipelineWatchdog, "_save_history")
    def test_fail_overall(self, _save, _backup, _tg, _disk, _wt, _notion, _sched, _btx):
        wd = PipelineWatchdog()
        # Simulate one FAIL check
        _btx.side_effect = lambda: wd.checks.append(_check("btx", STATUS_FAIL, "stale"))
        _sched.side_effect = lambda: wd.checks.append(_check("sched", STATUS_OK))
        _notion.side_effect = lambda: wd.checks.append(_check("notion", STATUS_OK))
        _wt.side_effect = lambda: wd.checks.append(_check("wt", STATUS_OK))
        _disk.side_effect = lambda: wd.checks.append(_check("disk", STATUS_OK))
        _tg.side_effect = lambda: wd.checks.append(_check("tg", STATUS_OK))
        _backup.side_effect = lambda: wd.checks.append(_check("backup", STATUS_OK))
        report = wd.run_all()
        assert report["overall"] == "FAIL"


class TestSendAlerts:
    def test_no_alerts_no_send(self):
        wd = PipelineWatchdog()
        assert wd.send_alerts_if_needed() is False

    @patch.object(PipelineWatchdog, "_load_telegram_module", return_value=None)
    def test_no_telegram_module(self, _):
        wd = PipelineWatchdog()
        wd.alerts.append("test alert")
        assert wd.send_alerts_if_needed() is False

    @patch.object(PipelineWatchdog, "_load_telegram_module")
    def test_sends_alert(self, mock_load):
        mock_mod = MagicMock()
        mock_mod.is_configured.return_value = True
        mock_load.return_value = mock_mod
        wd = PipelineWatchdog()
        wd.alerts.append("test alert")
        assert wd.send_alerts_if_needed() is True
        mock_mod.send_alert.assert_called_once()


class TestSaveHistory:
    def test_saves_to_file(self, tmp_path):
        history_path = tmp_path / "watchdog_history.json"
        with patch("execution.pipeline_watchdog._WATCHDOG_HISTORY", history_path):
            wd = PipelineWatchdog()
            report = {"overall": "OK", "checked_at": "2026-03-22", "alert_count": 0, "alerts": []}
            wd._save_history(report)
        assert history_path.exists()
        data = json.loads(history_path.read_text())
        assert len(data) == 1
        assert data[0]["overall"] == "OK"
