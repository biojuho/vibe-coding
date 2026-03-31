"""Tests for main.py entry point — extracted helper functions."""

from __future__ import annotations

import os
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Ensure the project root is importable
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from main import (
    _acquire_lock,
    _build_parser,
    _handle_single_commands,
    _init_scrapers,
    _is_process_alive,
    _resolve_input_sources,
)


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
    def test_current_process(self):
        assert _is_process_alive(os.getpid()) is True

    def test_nonexistent_pid(self):
        assert _is_process_alive(999999999) is False


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
    async def test_reprocess_approved(self):
        args = MagicMock(reprocess_approved=True, limit=5)
        config = MagicMock()
        config.get.return_value = 10
        notifier = AsyncMock()
        notion = AsyncMock()
        twitter = AsyncMock()

        with patch("main.run_reprocess_approved", new_callable=AsyncMock) as mock_reprocess:
            mock_reprocess.return_value = [{"success": True}]
            result = await _handle_single_commands(args, config, notifier, notion, twitter)
            assert result is True
            mock_reprocess.assert_called_once()

    @pytest.mark.asyncio
    async def test_digest(self):
        args = MagicMock(reprocess_approved=False, digest=True, digest_date=None)
        config = MagicMock()
        notifier = AsyncMock()
        notion = AsyncMock()
        twitter = AsyncMock()

        with patch("main.run_digest", new_callable=AsyncMock) as mock_digest:
            result = await _handle_single_commands(args, config, notifier, notion, twitter)
            assert result is True

    @pytest.mark.asyncio
    async def test_sentiment_report(self):
        args = MagicMock(reprocess_approved=False, digest=False, sentiment_report=True)
        config = MagicMock()
        notifier = AsyncMock()
        notion = AsyncMock()
        twitter = AsyncMock()

        with patch("main.run_sentiment_report") as mock_report:
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
