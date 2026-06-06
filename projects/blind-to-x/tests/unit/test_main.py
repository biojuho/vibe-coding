"""Tests for main.py entry point — extracted helper functions."""

from __future__ import annotations

import os
import time
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

# Ensure the project root is importable and 'main' resolves to blind-to-x/main.py
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.cli import (
    _apply_recommended_source_fallback,
    _resolve_source_preflight_sources,
    acquire_lock as _acquire_lock,
    _is_process_alive,
    _source_preflight_requested,
    _source_preflight_should_continue,
    build_parser as _build_parser,
    run_main as _run_main,
    run_source_preflight_command as _run_source_preflight_command,
)
from pipeline.runner import handle_single_commands as _handle_single_commands
from pipeline.bootstrap import init_scrapers as _init_scrapers, resolve_input_sources as _resolve_input_sources


# ---------------------------------------------------------------------------
# _build_parser
# ---------------------------------------------------------------------------


class TestBuildParser:
    def test_default_args(self):
        parser = _build_parser()
        args = parser.parse_args([])
        assert args.config == "config.yaml"
        assert args.dry_run is False
        assert args.parallel == 3
        assert args.source == "auto"
        assert args.require_source_ready is False

    def test_urls_arg(self):
        parser = _build_parser()
        args = parser.parse_args(["--urls", "http://a.com", "http://b.com"])
        assert args.urls == ["http://a.com", "http://b.com"]

    def test_dry_run(self):
        parser = _build_parser()
        args = parser.parse_args(["--dry-run"])
        assert args.dry_run is True

    def test_parallel_arg(self):
        parser = _build_parser()
        args = parser.parse_args(["--parallel", "5"])
        assert args.parallel == 5

    def test_reprocess_approved(self):
        parser = _build_parser()
        args = parser.parse_args(["--reprocess-approved"])
        assert args.reprocess_approved is True

    def test_digest_with_date(self):
        parser = _build_parser()
        args = parser.parse_args(["--digest", "--digest-date", "2026-03-31"])
        assert args.digest is True
        assert args.digest_date == "2026-03-31"

    def test_source_preflight_args(self):
        parser = _build_parser()
        args = parser.parse_args(
            [
                "--source-preflight",
                "--source",
                "ppomppu",
                "--source-preflight-fail-on-problem",
                "--source-preflight-timeout-ms",
                "5000",
                "--source-preflight-output",
                ".tmp/preflight.json",
                "--source-preflight-screenshot-dir",
                "screenshots/preflight",
                "--source-preflight-click-through",
                "--source-preflight-use-recommended",
                "--source-preflight-viewport",
                "mobile",
            ]
        )

        assert args.source_preflight is True
        assert args.source == "ppomppu"
        assert args.source_preflight_fail_on_problem is True
        assert args.source_preflight_timeout_ms == 5000
        assert args.source_preflight_output == Path(".tmp/preflight.json")
        assert args.source_preflight_screenshot_dir == Path("screenshots/preflight")
        assert args.source_preflight_click_through is True
        assert args.source_preflight_use_recommended is True
        assert args.source_preflight_viewport == "mobile"

    def test_require_source_ready_args(self):
        parser = _build_parser()
        args = parser.parse_args(["--require-source-ready", "--source", "ppomppu"])

        assert args.require_source_ready is True
        assert args.source_preflight is False
        assert args.source == "ppomppu"


# ---------------------------------------------------------------------------
# _is_process_alive
# ---------------------------------------------------------------------------


class TestIsProcessAlive:
    def test_current_process(self, monkeypatch):
        # Windows + Python 3.14에서 os.kill(pid, 0)이 asyncio signal handler와
        # 간섭하여 이후 Future.result() 호출 시 SIGINT가 propagate됨.
        # os.kill을 모킹하여 _is_process_alive 로직만 격리 테스트.
        monkeypatch.setattr("pipeline.cli.os.kill", lambda pid, sig: None)
        assert _is_process_alive(os.getpid()) is True

    def test_nonexistent_pid(self, monkeypatch):
        # 999999999는 Windows max PID(65535) 범위 초과로 OS-level 동작이 예측 불가.
        # os.kill을 모킹하여 안전하게 "프로세스 없음" 동작을 시뮬레이션.
        import errno

        def fake_kill(pid, sig):
            raise ProcessLookupError(errno.ESRCH, "No such process")

        monkeypatch.setattr("pipeline.cli.os.kill", fake_kill)
        assert _is_process_alive(999999) is False


# ---------------------------------------------------------------------------
# _resolve_input_sources
# ---------------------------------------------------------------------------


class TestResolveInputSources:
    def test_explicit_source_overrides(self):
        config = MagicMock()
        args = MagicMock(source="fmkorea")
        assert _resolve_input_sources(config, args) == ["fmkorea"]

    def test_explicit_blind_overrides_multi_config(self):
        config = MagicMock()
        config.get.side_effect = lambda key, default=None: {
            "input_sources": ["blind", "fmkorea", "ppomppu"],
            "content_strategy.primary_source": "multi",
        }.get(key, default)
        args = MagicMock(source="blind")
        assert _resolve_input_sources(config, args) == ["blind"]

    def test_multi_source_uses_configured_sources(self):
        config = MagicMock()
        config.get.side_effect = lambda key, default=None: {
            "input_sources": ["blind", "fmkorea", "ppomppu"],
            "content_strategy.primary_source": "blind",
        }.get(key, default)
        args = MagicMock(source="multi")
        assert _resolve_input_sources(config, args) == ["blind", "fmkorea", "ppomppu"]

    def test_default_blind(self):
        config = MagicMock()
        config.get.side_effect = lambda key, default=None: {
            "input_sources": ["blind"],
            "content_strategy.primary_source": "blind",
        }.get(key, default)
        args = MagicMock(source="auto")
        result = _resolve_input_sources(config, args)
        assert "blind" in result

    def test_configured_sources(self):
        config = MagicMock()
        config.get.side_effect = lambda key, default=None: {
            "input_sources": ["fmkorea", "ppomppu"],
            "content_strategy.primary_source": "multi",
        }.get(key, default)
        args = MagicMock(source="auto")
        result = _resolve_input_sources(config, args)
        assert result == ["fmkorea", "ppomppu"]


# ---------------------------------------------------------------------------
# source preflight
# ---------------------------------------------------------------------------


class TestSourcePreflight:
    def test_source_preflight_request_helpers(self):
        assert _source_preflight_requested(SimpleNamespace(source_preflight=False, require_source_ready=False)) is False
        assert _source_preflight_requested(SimpleNamespace(source_preflight=True, require_source_ready=False)) is True
        assert _source_preflight_requested(SimpleNamespace(source_preflight=False, require_source_ready=True)) is True

        assert _source_preflight_should_continue(SimpleNamespace(require_source_ready=False), 0) is False
        assert _source_preflight_should_continue(SimpleNamespace(require_source_ready=True), 0) is True
        assert _source_preflight_should_continue(SimpleNamespace(require_source_ready=True), 1) is False

    def test_recommended_source_fallback_rewrites_source_only_when_enabled(self):
        report = {
            "summary": {
                "ok": False,
                "ready_sources": ["jobplanet", "ppomppu"],
                "recommended_source": "ppomppu",
            }
        }
        args = SimpleNamespace(
            require_source_ready=True,
            source_preflight_use_recommended=True,
            source="multi",
        )

        selected = _apply_recommended_source_fallback(args, report)

        assert selected == "ppomppu"
        assert args.source == "ppomppu"

    def test_recommended_source_fallback_ignores_report_only_preflight(self):
        report = {"summary": {"recommended_source": "ppomppu"}}
        args = SimpleNamespace(
            require_source_ready=False,
            source_preflight_use_recommended=True,
            source="multi",
        )

        selected = _apply_recommended_source_fallback(args, report)

        assert selected is None
        assert args.source == "multi"

    def test_recommended_source_fallback_requires_recommendation(self):
        args = SimpleNamespace(
            require_source_ready=True,
            source_preflight_use_recommended=True,
            source="multi",
        )

        selected = _apply_recommended_source_fallback(args, {"summary": {"recommended_source": None}})

        assert selected is None
        assert args.source == "multi"

    def test_recommended_source_fallback_requires_ready_source_membership(self):
        args = SimpleNamespace(
            require_source_ready=True,
            source_preflight_use_recommended=True,
            source="multi",
        )
        report = {
            "summary": {
                "ready_sources": ["jobplanet"],
                "recommended_source": "ppomppu",
            }
        }

        selected = _apply_recommended_source_fallback(args, report)

        assert selected is None
        assert args.source == "multi"

    def test_resolve_source_preflight_sources_filters_unsupported(self):
        config = MagicMock()
        config.get.side_effect = lambda key, default=None: {
            "input_sources": ["blind", "internal", "ppomppu"],
            "content_strategy.primary_source": "multi",
        }.get(key, default)
        args = SimpleNamespace(source="multi")

        assert _resolve_source_preflight_sources(config, args) == ["blind", "ppomppu"]

    @pytest.mark.asyncio
    async def test_source_preflight_command_skips_when_flag_absent(self):
        args = SimpleNamespace(source_preflight=False)

        result = await _run_source_preflight_command(MagicMock(), args)

        assert result is None

    @pytest.mark.asyncio
    async def test_source_preflight_command_runs_probe_and_returns_exit_code(self, monkeypatch, tmp_path):
        calls = {}

        async def fake_run_source_preflight(**kwargs):
            calls.update(kwargs)
            return {"summary": {"ok": False}}

        monkeypatch.setattr("pipeline.cli.run_source_preflight", fake_run_source_preflight)
        config = MagicMock()
        config.get.side_effect = lambda key, default=None: {
            "input_sources": ["blind", "ppomppu"],
            "content_strategy.primary_source": "multi",
        }.get(key, default)
        args = SimpleNamespace(
            source_preflight=True,
            source="multi",
            source_preflight_fail_on_problem=True,
            source_preflight_timeout_ms=500,
            source_preflight_output=tmp_path / "preflight.json",
            source_preflight_screenshot_dir=tmp_path / "screens",
            source_preflight_headed=True,
            source_preflight_click_through=True,
            source_preflight_use_recommended=False,
            source_preflight_viewport="mobile",
        )

        result = await _run_source_preflight_command(config, args)

        assert result == 1
        assert calls == {
            "sources": ["blind", "ppomppu"],
            "custom_urls": None,
            "timeout_ms": 1000,
            "output_path": tmp_path / "preflight.json",
            "screenshot_dir": tmp_path / "screens",
            "headed": True,
            "viewport": "mobile",
            "click_through": True,
        }

    @pytest.mark.asyncio
    async def test_source_preflight_command_rejects_unsupported_source(self, monkeypatch):
        fake_run_source_preflight = AsyncMock()
        monkeypatch.setattr("pipeline.cli.run_source_preflight", fake_run_source_preflight)
        args = SimpleNamespace(source_preflight=True, source="internal")

        result = await _run_source_preflight_command(MagicMock(), args)

        assert result == 1
        fake_run_source_preflight.assert_not_called()

    @pytest.mark.asyncio
    async def test_require_source_ready_implies_fail_on_problem(self, monkeypatch, tmp_path):
        calls = {}

        async def fake_run_source_preflight(**kwargs):
            calls.update(kwargs)
            return {"summary": {"ok": False}}

        monkeypatch.setattr("pipeline.cli.run_source_preflight", fake_run_source_preflight)
        config = MagicMock()
        config.get.side_effect = lambda key, default=None: {
            "input_sources": ["ppomppu"],
            "content_strategy.primary_source": "ppomppu",
        }.get(key, default)
        args = SimpleNamespace(
            source_preflight=False,
            require_source_ready=True,
            source="ppomppu",
            source_preflight_fail_on_problem=False,
            source_preflight_timeout_ms=500,
            source_preflight_output=tmp_path / "preflight.json",
            source_preflight_screenshot_dir=tmp_path / "screens",
            source_preflight_headed=False,
            source_preflight_click_through=False,
            source_preflight_use_recommended=False,
            source_preflight_viewport="desktop",
        )

        result = await _run_source_preflight_command(config, args)

        assert result == 1
        assert calls["sources"] == ["ppomppu"]

    @pytest.mark.asyncio
    async def test_require_source_ready_can_continue_with_recommended_source(self, monkeypatch, tmp_path):
        calls = {}

        async def fake_run_source_preflight(**kwargs):
            calls.update(kwargs)
            return {
                "summary": {
                    "ok": False,
                    "ready_sources": ["jobplanet", "ppomppu"],
                    "problem_sources": [{"source": "blind", "status": "blocked"}],
                    "recommended_source": "ppomppu",
                }
            }

        monkeypatch.setattr("pipeline.cli.run_source_preflight", fake_run_source_preflight)
        config = MagicMock()
        config.get.side_effect = lambda key, default=None: {
            "input_sources": ["blind", "jobplanet", "ppomppu"],
            "content_strategy.primary_source": "multi",
        }.get(key, default)
        args = SimpleNamespace(
            source_preflight=False,
            require_source_ready=True,
            source="multi",
            source_preflight_fail_on_problem=False,
            source_preflight_timeout_ms=500,
            source_preflight_output=tmp_path / "preflight.json",
            source_preflight_screenshot_dir=tmp_path / "screens",
            source_preflight_headed=False,
            source_preflight_click_through=True,
            source_preflight_use_recommended=True,
            source_preflight_viewport="desktop",
        )

        result = await _run_source_preflight_command(config, args)

        assert result == 0
        assert calls["sources"] == ["blind", "jobplanet", "ppomppu"]
        assert args.source == "ppomppu"


class TestRunMainSourcePreflight:
    def _patch_run_main_dependencies(self, monkeypatch, tmp_path, preflight_exit: int):
        lock_file = tmp_path / "run.lock"
        fake_config = MagicMock()
        execute_pipeline = AsyncMock()

        async def fake_run_source_preflight_command(config_mgr, args):
            assert config_mgr is fake_config
            assert args.require_source_ready is True
            return preflight_exit

        fake_harness_guard = ModuleType("pipeline.harness_guard")
        fake_harness_guard.is_harness_enabled = lambda: False
        fake_harness_guard.run_preflight = lambda: {"passed": True, "skipped": False, "issues": []}

        monkeypatch.setattr("pipeline.cli._LOCK_FILE", lock_file)
        monkeypatch.setattr("pipeline.cli.ConfigManager", lambda path: fake_config)
        monkeypatch.setattr("pipeline.cli.run_source_preflight_command", fake_run_source_preflight_command)
        monkeypatch.setattr("pipeline.cli.NotificationManager", lambda config_mgr: MagicMock())
        monkeypatch.setattr("pipeline.cli.NotionUploader", lambda config_mgr: MagicMock())
        monkeypatch.setattr("pipeline.cli.TwitterPoster", lambda config_mgr: MagicMock())
        monkeypatch.setattr("pipeline.cli.handle_single_commands", AsyncMock(return_value=False))
        monkeypatch.setattr("pipeline.cli.init_scrapers", MagicMock(return_value={"ppomppu": MagicMock()}))
        monkeypatch.setattr("pipeline.cli.check_budget", AsyncMock(return_value=MagicMock()))
        monkeypatch.setattr(
            "pipeline.cli.init_components",
            AsyncMock(return_value=tuple(MagicMock() for _ in range(5))),
        )
        monkeypatch.setattr("pipeline.cli.execute_pipeline", execute_pipeline)
        monkeypatch.setitem(sys.modules, "pipeline.harness_guard", fake_harness_guard)

        return lock_file, execute_pipeline

    @pytest.mark.asyncio
    async def test_require_source_ready_continues_to_pipeline_on_success(self, monkeypatch, tmp_path):
        lock_file, execute_pipeline = self._patch_run_main_dependencies(monkeypatch, tmp_path, preflight_exit=0)
        monkeypatch.setattr(sys, "argv", ["main.py", "--require-source-ready", "--source", "ppomppu"])

        await _run_main()

        execute_pipeline.assert_awaited_once()
        assert not lock_file.exists()

    @pytest.mark.asyncio
    async def test_require_source_ready_exits_before_pipeline_on_failure(self, monkeypatch, tmp_path):
        lock_file, execute_pipeline = self._patch_run_main_dependencies(monkeypatch, tmp_path, preflight_exit=1)
        monkeypatch.setattr(sys, "argv", ["main.py", "--require-source-ready", "--source", "ppomppu"])

        with pytest.raises(SystemExit) as exc_info:
            await _run_main()

        assert exc_info.value.code == 1
        execute_pipeline.assert_not_awaited()
        assert not lock_file.exists()

    @pytest.mark.asyncio
    async def test_recommended_source_single_command_releases_lock(self, monkeypatch, tmp_path):
        lock_file, execute_pipeline = self._patch_run_main_dependencies(monkeypatch, tmp_path, preflight_exit=0)

        async def fake_run_source_preflight_command(config_mgr, args):
            assert args.require_source_ready is True
            assert args.source_preflight_use_recommended is True
            args.source = "ppomppu"
            return 0

        handle_single_commands = AsyncMock(return_value=True)
        monkeypatch.setattr("pipeline.cli.run_source_preflight_command", fake_run_source_preflight_command)
        monkeypatch.setattr("pipeline.cli.handle_single_commands", handle_single_commands)
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "main.py",
                "--require-source-ready",
                "--source",
                "multi",
                "--source-preflight-use-recommended",
                "--sentiment-report",
            ],
        )

        await _run_main()

        handle_single_commands.assert_awaited_once()
        handled_args = handle_single_commands.await_args.args[0]
        assert handled_args.source == "ppomppu"
        execute_pipeline.assert_not_awaited()
        assert not lock_file.exists()


# ---------------------------------------------------------------------------
# _acquire_lock
# ---------------------------------------------------------------------------


class TestAcquireLock:
    def test_acquire_fresh(self, tmp_path, monkeypatch):
        lock_file = tmp_path / "test.lock"
        monkeypatch.setattr("pipeline.cli._LOCK_FILE", lock_file)
        assert _acquire_lock() is True
        assert lock_file.exists()

    def test_stale_lock_overwritten(self, tmp_path, monkeypatch):
        lock_file = tmp_path / "test.lock"
        lock_file.parent.mkdir(parents=True, exist_ok=True)
        # Write a stale lock (1 hour + 1 second ago)
        lock_file.write_text(f"99999:{time.time() - 3601}")
        monkeypatch.setattr("pipeline.cli._LOCK_FILE", lock_file)
        monkeypatch.setattr("pipeline.cli._is_process_alive", lambda pid: False)
        assert _acquire_lock() is True

    def test_active_lock_blocks(self, tmp_path, monkeypatch):
        lock_file = tmp_path / "test.lock"
        lock_file.parent.mkdir(parents=True, exist_ok=True)
        lock_file.write_text(f"{os.getpid()}:{time.time()}")
        monkeypatch.setattr("pipeline.cli._LOCK_FILE", lock_file)
        monkeypatch.setattr("pipeline.cli._is_process_alive", lambda pid: True)
        assert _acquire_lock() is False


# ---------------------------------------------------------------------------
# _init_scrapers
# ---------------------------------------------------------------------------


class TestInitScrapers:
    def test_init_with_valid_scraper(self, monkeypatch):
        mock_scraper_cls = MagicMock()
        mock_scraper_cls.return_value = MagicMock()
        monkeypatch.setattr("pipeline.bootstrap.get_scraper", lambda name: mock_scraper_cls)
        monkeypatch.setattr(
            "pipeline.bootstrap.resolve_input_sources",
            lambda config, args: ["blind"],
        )
        config = MagicMock()
        args = MagicMock()
        result = _init_scrapers(config, args)
        assert "blind" in result

    def test_init_with_failing_scraper(self, monkeypatch):
        def fail_scraper(name):
            raise RuntimeError("no scraper")

        monkeypatch.setattr("pipeline.bootstrap.get_scraper", fail_scraper)
        monkeypatch.setattr(
            "pipeline.bootstrap.resolve_input_sources",
            lambda config, args: ["broken"],
        )
        config = MagicMock()
        args = MagicMock()
        result = _init_scrapers(config, args)
        assert result == {}


# ---------------------------------------------------------------------------
# _handle_single_commands
# ---------------------------------------------------------------------------


class TestHandleSingleCommands:
    @pytest.mark.asyncio
    async def test_reprocess_approved(self, monkeypatch):
        args = MagicMock(reprocess_approved=True, limit=5)
        config = MagicMock()
        config.get.return_value = 10
        notifier = AsyncMock()
        notion = AsyncMock()
        twitter = AsyncMock()
        mock_reprocess = AsyncMock(return_value=[{"success": True}])
        monkeypatch.setattr("pipeline.runner.run_reprocess_approved", mock_reprocess)

        result = await _handle_single_commands(args, config, notifier, notion, twitter)
        assert result is True
        mock_reprocess.assert_called_once()

    @pytest.mark.asyncio
    async def test_digest(self, monkeypatch):
        args = MagicMock(reprocess_approved=False, digest=True, digest_date=None)
        config = MagicMock()
        notifier = AsyncMock()
        notion = AsyncMock()
        twitter = AsyncMock()
        mock_digest = AsyncMock()
        monkeypatch.setattr("pipeline.runner.run_digest", mock_digest)

        result = await _handle_single_commands(args, config, notifier, notion, twitter)
        assert result is True

    @pytest.mark.asyncio
    async def test_sentiment_report(self, monkeypatch):
        args = MagicMock(reprocess_approved=False, digest=False, sentiment_report=True)
        config = MagicMock()
        notifier = AsyncMock()
        notion = AsyncMock()
        twitter = AsyncMock()
        mock_report = MagicMock()
        monkeypatch.setattr("pipeline.runner.run_sentiment_report", mock_report)

        result = await _handle_single_commands(args, config, notifier, notion, twitter)
        assert result is True

    @pytest.mark.asyncio
    async def test_no_command(self):
        args = MagicMock(reprocess_approved=False, digest=False, sentiment_report=False)
        config = MagicMock()
        notifier = AsyncMock()
        notion = AsyncMock()
        twitter = AsyncMock()

        result = await _handle_single_commands(args, config, notifier, notion, twitter)
        assert result is False
