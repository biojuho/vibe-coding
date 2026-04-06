"""Tests for main.py entry point — extracted helper functions."""

from __future__ import annotations

import os
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

# Ensure the project root is importable and 'main' resolves to blind-to-x/main.py
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# When collected alongside other projects, sys.modules['main'] may point to
# a different main module.  Force-reload from the correct path.
_main_path = PROJECT_ROOT / "main.py"
if "main" in sys.modules:
    _existing = getattr(sys.modules["main"], "__file__", "") or ""
    if str(_main_path) not in _existing:
        del sys.modules["main"]

import main as _btx_main  # noqa: E402

_acquire_lock = _btx_main._acquire_lock
_build_parser = _btx_main._build_parser
_handle_single_commands = _btx_main._handle_single_commands
_init_scrapers = _btx_main._init_scrapers
_is_process_alive = _btx_main._is_process_alive
_resolve_input_sources = _btx_main._resolve_input_sources


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
        assert args.source == "blind"

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


# ---------------------------------------------------------------------------
# _is_process_alive
# ---------------------------------------------------------------------------


class TestIsProcessAlive:
    def test_current_process(self, monkeypatch):
        # Windows + Python 3.14에서 os.kill(pid, 0)이 asyncio signal handler와
        # 간섭하여 이후 Future.result() 호출 시 SIGINT가 propagate됨.
        # os.kill을 모킹하여 _is_process_alive 로직만 격리 테스트.
        monkeypatch.setattr("main.os.kill", lambda pid, sig: None)
        assert _is_process_alive(os.getpid()) is True

    def test_nonexistent_pid(self, monkeypatch):
        # 999999999는 Windows max PID(65535) 범위 초과로 OS-level 동작이 예측 불가.
        # os.kill을 모킹하여 안전하게 "프로세스 없음" 동작을 시뮬레이션.
        import errno

        def fake_kill(pid, sig):
            raise ProcessLookupError(errno.ESRCH, "No such process")

        monkeypatch.setattr("main.os.kill", fake_kill)
        assert _is_process_alive(999999) is False


# ---------------------------------------------------------------------------
# _resolve_input_sources
# ---------------------------------------------------------------------------


class TestResolveInputSources:
    def test_explicit_source_overrides(self):
        config = MagicMock()
        args = MagicMock(source="fmkorea")
        assert _resolve_input_sources(config, args) == ["fmkorea"]

    def test_default_blind(self):
        config = MagicMock()
        config.get.side_effect = lambda key, default=None: {
            "input_sources": ["blind"],
            "content_strategy.primary_source": "blind",
        }.get(key, default)
        args = MagicMock(source="blind")
        result = _resolve_input_sources(config, args)
        assert "blind" in result

    def test_configured_sources(self):
        config = MagicMock()
        config.get.side_effect = lambda key, default=None: {
            "input_sources": ["fmkorea", "ppomppu"],
            "content_strategy.primary_source": "multi",
        }.get(key, default)
        args = MagicMock(source="blind")
        result = _resolve_input_sources(config, args)
        assert result == ["fmkorea", "ppomppu"]


# ---------------------------------------------------------------------------
# _acquire_lock
# ---------------------------------------------------------------------------


class TestAcquireLock:
    def test_acquire_fresh(self, tmp_path, monkeypatch):
        lock_file = tmp_path / "test.lock"
        monkeypatch.setattr("main._LOCK_FILE", lock_file)
        assert _acquire_lock() is True
        assert lock_file.exists()

    def test_stale_lock_overwritten(self, tmp_path, monkeypatch):
        lock_file = tmp_path / "test.lock"
        lock_file.parent.mkdir(parents=True, exist_ok=True)
        # Write a stale lock (1 hour + 1 second ago)
        lock_file.write_text(f"99999:{time.time() - 3601}")
        monkeypatch.setattr("main._LOCK_FILE", lock_file)
        monkeypatch.setattr("main._is_process_alive", lambda pid: False)
        assert _acquire_lock() is True

    def test_active_lock_blocks(self, tmp_path, monkeypatch):
        lock_file = tmp_path / "test.lock"
        lock_file.parent.mkdir(parents=True, exist_ok=True)
        lock_file.write_text(f"{os.getpid()}:{time.time()}")
        monkeypatch.setattr("main._LOCK_FILE", lock_file)
        monkeypatch.setattr("main._is_process_alive", lambda pid: True)
        assert _acquire_lock() is False


# ---------------------------------------------------------------------------
# _init_scrapers
# ---------------------------------------------------------------------------


class TestInitScrapers:
    def test_init_with_valid_scraper(self, monkeypatch):
        mock_scraper_cls = MagicMock()
        mock_scraper_cls.return_value = MagicMock()
        monkeypatch.setattr("main.get_scraper", lambda name: mock_scraper_cls)
        monkeypatch.setattr(
            "main._resolve_input_sources",
            lambda config, args: ["blind"],
        )
        config = MagicMock()
        args = MagicMock()
        result = _init_scrapers(config, args)
        assert "blind" in result

    def test_init_with_failing_scraper(self, monkeypatch):
        def fail_scraper(name):
            raise RuntimeError("no scraper")

        monkeypatch.setattr("main.get_scraper", fail_scraper)
        monkeypatch.setattr(
            "main._resolve_input_sources",
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
        monkeypatch.setattr("main.run_reprocess_approved", mock_reprocess)

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
        monkeypatch.setattr("main.run_digest", mock_digest)

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
        monkeypatch.setattr("main.run_sentiment_report", mock_report)

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
