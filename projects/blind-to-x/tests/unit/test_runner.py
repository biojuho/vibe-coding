import sys
import types
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pipeline.runner import _append_cross_source_insights, execute_pipeline, handle_single_commands


@pytest.fixture
def mock_args():
    args = MagicMock()
    args.reprocess_approved = False
    args.review_queue_report = False
    args.review_queue_lookback_days = None
    args.review_queue_stale_days = None
    args.review_queue_action_limit = None
    args.review_queue_ready_attention_limit = None
    args.review_queue_report_output = None
    args.review_queue_report_fail_on_warning = False
    args.digest = False
    args.sentiment_report = False
    args.review_only = False
    args.dry_run = False
    args.parallel = 1
    args.limit = None
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
async def test_string_false_disables_cross_source_insights(monkeypatch):
    insight_module = types.ModuleType("pipeline.cross_source_insight")
    process_mock = AsyncMock(return_value=[{"source": "cross_source_insight"}])
    insight_module.process_cross_source_insights = process_mock
    monkeypatch.setitem(sys.modules, "pipeline.cross_source_insight", insight_module)

    config = MagicMock()
    config.get.side_effect = lambda key, default=None: {"cross_source_insight.enabled": "false"}.get(key, default)
    results = [{"source": "blind"}]

    returned = await _append_cross_source_insights(
        results,
        dry_run=False,
        config_mgr=config,
        draft_generator=MagicMock(),
        notion_uploader=MagicMock(),
        image_uploader=MagicMock(),
        image_generator=MagicMock(),
        output_formats=["twitter"],
        top_examples=[],
        trend_monitor=MagicMock(),
    )

    process_mock.assert_not_awaited()
    assert returned == results


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
@patch("pipeline.runner.run_review_queue_report", new_callable=AsyncMock)
async def test_handle_single_commands_review_queue_report_is_read_only(mock_run, mock_args, mock_config, capsys):
    mock_args.review_queue_report = True
    mock_args.review_queue_lookback_days = 14
    mock_args.review_queue_stale_days = 0
    mock_args.review_queue_action_limit = 4
    mock_args.review_queue_ready_attention_limit = 6
    mock_args.review_queue_report_output = ".tmp/custom_review_queue_report.json"
    mock_args.limit = 20
    mock_run.return_value = {
        "success": True,
        "dry_run": True,
        "total_records": 1,
        "status_counts": {
            "Ready to Post": 1,
            "Published": 0,
            "Blocked": 0,
            "Needs Edit": 0,
            "Missing": 0,
            "Other": 0,
        },
        "blocked_count": 0,
        "ready_to_post_count": 1,
        "published_count": 0,
        "needs_edit_count": 0,
        "missing_status_count": 0,
        "stale_ready_count": 0,
        "operator_action_count": 0,
        "operator_actions": [],
        "severity": "ok",
        "severity_reasons": [],
    }

    notifier = AsyncMock()
    notion = AsyncMock()
    twitter = AsyncMock()
    handled = await handle_single_commands(mock_args, mock_config, notifier, notion, twitter)

    assert handled is True
    mock_run.assert_awaited_once_with(
        notion,
        lookback_days=14,
        limit=20,
        stale_days=0,
        action_limit=4,
        ready_attention_limit=6,
        output_path=".tmp/custom_review_queue_report.json",
    )
    notifier.send_message.assert_not_called()
    twitter.post_tweet.assert_not_called()
    assert "read-only" in capsys.readouterr().out


@pytest.mark.asyncio
@patch("pipeline.runner.run_review_queue_report", new_callable=AsyncMock)
async def test_handle_single_commands_review_queue_report_sets_optional_exit_code(mock_run, mock_args, mock_config):
    mock_args.review_queue_report = True
    mock_args.review_queue_report_fail_on_warning = True
    mock_run.return_value = {
        "success": True,
        "dry_run": True,
        "total_records": 1,
        "status_counts": {
            "Ready to Post": 0,
            "Published": 0,
            "Blocked": 1,
            "Needs Edit": 0,
            "Missing": 0,
            "Other": 0,
        },
        "blocked_count": 1,
        "ready_to_post_count": 0,
        "published_count": 0,
        "needs_edit_count": 0,
        "missing_status_count": 0,
        "stale_ready_count": 0,
        "operator_action_count": 1,
        "operator_actions": [],
        "severity": "critical",
        "severity_reasons": ["blocked_count=1"],
    }

    handled = await handle_single_commands(mock_args, mock_config, AsyncMock(), AsyncMock(), AsyncMock())

    assert handled is True
    assert mock_args._single_command_exit_code == 2


@pytest.mark.asyncio
@patch("pipeline.runner.run_reprocess_approved", new_callable=AsyncMock)
async def test_handle_single_commands_reprocess_warns_on_notion_sync_degraded(mock_run, mock_args, mock_config):
    mock_args.reprocess_approved = True
    mock_run.return_value = [
        {
            "success": True,
            "twitter_url": "https://x.com/post/123",
            "notion_update_success": False,
            "notion_operator_action": "Retry the Notion X publish-state update after at least 6s.",
        }
    ]

    notifier = AsyncMock()
    handled = await handle_single_commands(mock_args, mock_config, notifier, None, None)

    assert handled is True
    notifier.send_message.assert_awaited_once()
    message = notifier.send_message.await_args.args[0]
    assert "notion_sync_warning 1" in message
    assert "operator_action Retry the Notion X publish-state update after at least 6s." in message
    assert notifier.send_message.await_args.kwargs["level"] == "WARNING"


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
