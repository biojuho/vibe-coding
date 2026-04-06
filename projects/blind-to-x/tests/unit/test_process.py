"""Tests for pipeline.process."""

import asyncio
import pytest
from unittest.mock import AsyncMock, patch

from pipeline.process import process_single_post, calculate_run_metrics
from config import ERROR_DUPLICATE_URL, ERROR_NOTION_SCHEMA_MISMATCH, ERROR_SCRAPE_FAILED


@pytest.mark.asyncio
async def test_process_early_returns():
    # Test dedup skip
    with patch("pipeline.process.run_dedup_stage", new_callable=AsyncMock) as m_dedup:
        m_dedup.return_value = False
        res = await process_single_post("http://test", None, None)
        assert res["url"] == "http://test"

    # Test fetch skip
    with (
        patch("pipeline.process.run_dedup_stage", new_callable=AsyncMock) as m_dedup,
        patch("pipeline.process.run_fetch_stage", new_callable=AsyncMock) as m_fetch,
    ):
        m_dedup.return_value = True
        m_fetch.return_value = False
        res = await process_single_post("http://test", None, None)
        assert res["url"] == "http://test"

    # Test filter skip
    with (
        patch("pipeline.process.run_dedup_stage", new_callable=AsyncMock) as m_dedup,
        patch("pipeline.process.run_fetch_stage", new_callable=AsyncMock) as m_fetch,
        patch("pipeline.process.run_filter_stage", new_callable=AsyncMock) as m_filter,
    ):
        m_dedup.return_value = True
        m_fetch.return_value = True
        m_filter.return_value = False
        res = await process_single_post("http://test", None, None)
        assert res["url"] == "http://test"

    # Test generate skip
    with (
        patch("pipeline.process.run_dedup_stage", new_callable=AsyncMock) as m_dedup,
        patch("pipeline.process.run_fetch_stage", new_callable=AsyncMock) as m_fetch,
        patch("pipeline.process.run_filter_stage", new_callable=AsyncMock) as m_filter,
        patch("pipeline.process.run_generate_stage", new_callable=AsyncMock) as m_gen,
    ):
        m_dedup.return_value = True
        m_fetch.return_value = True
        m_filter.return_value = True
        m_gen.return_value = False
        res = await process_single_post("http://test", None, None)
        assert res["url"] == "http://test"

    # Test persist skip
    with (
        patch("pipeline.process.run_dedup_stage", new_callable=AsyncMock) as m_dedup,
        patch("pipeline.process.run_fetch_stage", new_callable=AsyncMock) as m_fetch,
        patch("pipeline.process.run_filter_stage", new_callable=AsyncMock) as m_filter,
        patch("pipeline.process.run_generate_stage", new_callable=AsyncMock) as m_gen,
        patch("pipeline.process.run_persist_stage", new_callable=AsyncMock) as m_persist,
    ):
        m_dedup.return_value = True
        m_fetch.return_value = True
        m_filter.return_value = True
        m_gen.return_value = True
        m_persist.return_value = False
        res = await process_single_post("http://test", None, None)
        assert res["url"] == "http://test"

    # Test full success
    with (
        patch("pipeline.process.run_dedup_stage", new_callable=AsyncMock) as m_dedup,
        patch("pipeline.process.run_fetch_stage", new_callable=AsyncMock) as m_fetch,
        patch("pipeline.process.run_filter_stage", new_callable=AsyncMock) as m_filter,
        patch("pipeline.process.run_generate_stage", new_callable=AsyncMock) as m_gen,
        patch("pipeline.process.run_persist_stage", new_callable=AsyncMock) as m_persist,
    ):
        m_dedup.return_value = True
        m_fetch.return_value = True
        m_filter.return_value = True
        m_gen.return_value = True
        m_persist.return_value = True
        res = await process_single_post("http://test", None, None)
        assert res["url"] == "http://test"


def test_sync_runtime_overrides_removed():
    """Verify _sync_runtime_overrides was removed as part of global-state cleanup."""
    import pipeline.process as proc_mod

    assert not hasattr(proc_mod, "_sync_runtime_overrides"), (
        "_sync_runtime_overrides should have been removed — it was a global monkeypatch."
    )


def test_calculate_run_metrics():
    results = [
        {"success": True, "notion_url": "link", "quality_score": 80},
        {"success": False, "error_code": ERROR_DUPLICATE_URL},
        {"success": False, "error_code": ERROR_NOTION_SCHEMA_MISMATCH},
        {"success": True, "notion_url": "(skipped-duplicate)"},
    ]

    metrics = calculate_run_metrics(results)
    assert len(metrics["successful"]) == 2
    assert len(metrics["failed"]) == 2
    assert len(metrics["duplicate_skips"]) == 1
    assert len(metrics["schema_mismatches"]) == 1
    assert metrics["avg_quality_score"] == 80.0
    assert metrics["live_upload_attempts"] == 3  # 4 total - 1 dedup
    assert len(metrics["live_upload_success"]) == 1

    # dry_run = True tests
    metrics_dry = calculate_run_metrics(results, dry_run=True)
    assert metrics_dry["live_upload_attempts"] == 0


class _TimeoutConfig:
    def __init__(self, values):
        self._values = values

    def get(self, key, default=None):
        return self._values.get(key, default)


@pytest.mark.asyncio
async def test_process_fetch_timeout_sets_failure_reason():
    async def _slow_fetch(*args, **kwargs):
        await asyncio.sleep(1.1)
        return True

    config = _TimeoutConfig(
        {
            "pipeline.fetch_timeout_seconds": 1,
            "pipeline.process_timeout_seconds": 5,
        }
    )

    with (
        patch("pipeline.process.run_dedup_stage", new_callable=AsyncMock) as m_dedup,
        patch("pipeline.process.run_fetch_stage", side_effect=_slow_fetch),
    ):
        m_dedup.return_value = True
        res = await process_single_post("http://test", None, None, config=config)

    assert res["error_code"] == ERROR_SCRAPE_FAILED
    assert res["failure_stage"] == "post_fetch"
    assert res["failure_reason"] == "fetch_timeout"
    assert res["stage_status"]["fetch"]["status"] == "failed"


@pytest.mark.asyncio
async def test_process_timeout_marks_running_stage_failed():
    async def _slow_generate(*args, **kwargs):
        await asyncio.sleep(1.1)
        return True

    config = _TimeoutConfig(
        {
            "pipeline.fetch_timeout_seconds": 5,
            "pipeline.process_timeout_seconds": 1,
        }
    )

    with (
        patch("pipeline.process.run_dedup_stage", new_callable=AsyncMock) as m_dedup,
        patch("pipeline.process.run_fetch_stage", new_callable=AsyncMock) as m_fetch,
        patch("pipeline.process.run_filter_stage", new_callable=AsyncMock) as m_filter,
        patch("pipeline.process.run_generate_stage", side_effect=_slow_generate),
    ):
        m_dedup.return_value = True
        m_fetch.return_value = True
        m_filter.return_value = True
        res = await process_single_post("http://test", None, None, config=config)

    assert res["error_code"] == "PROCESS_TIMEOUT"
    assert res["failure_reason"] == "process_timeout"
    assert res["failure_stage"] == "pipeline"
