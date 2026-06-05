import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from pipeline.runner import handle_single_commands, execute_pipeline


@pytest.fixture
def mock_args():
    args = MagicMock()
    args.reprocess_approved = False
    args.digest = False
    args.sentiment_report = False
    args.review_only = False
    args.dry_run = False
    args.parallel = 1
    return args


@pytest.fixture
def mock_config():
    config = MagicMock()
    config.get.return_value = False
    return config


def _feed_stats():
    return {"low_engagement_skips": 0, "blacklist_skips": 0, "cross_source_dedup_count": 0}


def _metrics(successful=None, failed=None):
    successful = [1] if successful is None else successful
    failed = [] if failed is None else failed
    return {
        "successful": successful,
        "failed": failed,
        "duplicate_skips": [],
        "filtered_skips": [],
        "avg_quality_score": 90.0,
        "upload_success_rate": 100.0,
        "live_upload_success": successful,
        "live_upload_attempts": len(successful) + len(failed),
        "content_duplicate_skips": [],
    }


@pytest.mark.asyncio
@patch("pipeline.runner.run_reprocess_approved", new_callable=AsyncMock)
async def test_handle_single_commands_reprocess(mock_run, mock_args, mock_config):
    mock_args.reprocess_approved = True
    mock_run.return_value = [{"success": True}]

    notifier = AsyncMock()
    handled = await handle_single_commands(mock_args, mock_config, notifier, None, None)

    assert handled is True
    mock_run.assert_called_once()
    notifier.send_message.assert_not_called()  # all succcess, fail count is 0


@pytest.mark.asyncio
async def test_handle_single_commands_none(mock_args, mock_config):
    handled = await handle_single_commands(mock_args, mock_config, None, None, None)
    assert handled is False


@pytest.mark.asyncio
@patch("pipeline.runner.collect_feed_items", new_callable=AsyncMock)
@patch("pipeline.runner.process_single_post", new_callable=AsyncMock)
@patch("pipeline.runner.calculate_run_metrics")
async def test_execute_pipeline_basic(mock_calc, mock_process, mock_collect, mock_args, mock_config):
    mock_collect.return_value = (
        [{"url": "http://1", "source": "blind", "scraper": None, "feed_mode": "popular"}],
        _feed_stats(),
    )

    mock_process.return_value = {"success": True}

    mock_calc.return_value = _metrics()

    notifier = AsyncMock()

    await execute_pipeline(mock_args, mock_config, {}, notifier, None, None, None, None, None, None, None)

    # process_single_post should be called once since we have 1 post
    mock_process.assert_called_once()
    notifier.send_message.assert_called_once()


@pytest.mark.asyncio
@patch("pipeline.runner.collect_feed_items", new_callable=AsyncMock)
@patch("pipeline.runner.process_single_post", new_callable=AsyncMock)
@patch("pipeline.runner.run_dry_run_single", new_callable=AsyncMock)
@patch("pipeline.runner.calculate_run_metrics")
async def test_execute_pipeline_dry_run_uses_preview_path(
    mock_calc,
    mock_dry_run_single,
    mock_process,
    mock_collect,
    mock_args,
    mock_config,
):
    mock_args.dry_run = True
    mock_collect.return_value = (
        [{"url": "http://dry", "source": "blind", "scraper": None, "feed_mode": "popular"}],
        _feed_stats(),
    )
    mock_dry_run_single.return_value = {"success": True, "dry_run": True}
    mock_calc.return_value = _metrics()
    notifier = AsyncMock()

    await execute_pipeline(mock_args, mock_config, {}, notifier, None, None, None, None, None, None, None)

    mock_dry_run_single.assert_awaited_once()
    mock_process.assert_not_called()
    notifier.send_message.assert_not_called()


@pytest.mark.asyncio
@patch("pipeline.runner.collect_feed_items", new_callable=AsyncMock)
@patch("pipeline.runner.process_single_post", new_callable=AsyncMock)
@patch("pipeline.runner.calculate_run_metrics")
async def test_execute_pipeline_parallel_processes_each_item(
    mock_calc, mock_process, mock_collect, mock_args, mock_config
):
    mock_args.parallel = 2
    mock_collect.return_value = (
        [
            {"url": "http://1", "source": "blind", "scraper": None, "feed_mode": "popular"},
            {"url": "http://2", "source": "blind", "scraper": None, "feed_mode": "popular"},
        ],
        _feed_stats(),
    )
    mock_process.side_effect = [{"success": True}, {"success": True}]
    mock_calc.return_value = _metrics(successful=[1, 2])
    notifier = AsyncMock()

    await execute_pipeline(mock_args, mock_config, {}, notifier, None, None, None, None, None, None, None)

    assert mock_process.await_count == 2
    notifier.send_message.assert_called_once()
