"""Extended tests for pipeline.process_stages.persist_stage — early exits and upload paths."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.process_stages.context import ProcessRunContext, build_process_result
from pipeline.process_stages.persist_stage import run_persist_stage


def _make_ctx(url="https://example.com/post/1") -> ProcessRunContext:
    return ProcessRunContext(
        url=url,
        trace_id="test-trace-001",
        result=build_process_result(url, "test-trace-001"),
        post_data={"title": "Test Post", "source": "blind"},
        profile={"topic_cluster": "경제", "emotion_axis": "분노"},
        drafts={"twitter": "[공감형 트윗] Test tweet", "_provider_used": "gemini"},
        image_prompt="anime style office worker",
    )


class TestRunPersistStage:
    @pytest.mark.asyncio
    async def test_no_notion_uploader(self):
        """Missing notion uploader -> immediate failure."""
        ctx = _make_ctx()
        result = await run_persist_stage(
            ctx=ctx,
            image_uploader=None,
            image_generator=None,
            notion_uploader=None,  # no notion uploader
            twitter_poster=None,
            config=None,
            review_only=False,
        )
        assert result is False
        assert ctx.result["error"] == "Notion uploader not configured"
        assert ctx.result["failure_stage"] == "upload"

    @pytest.mark.asyncio
    async def test_notion_upload_success(self):
        """Successful Notion upload with basic configuration."""
        ctx = _make_ctx()
        ctx.screenshot_task = None

        mock_notion = AsyncMock()
        mock_notion.upload = AsyncMock(return_value=("https://notion.so/page1", "page-id-1"))
        mock_notion.update_page_properties = AsyncMock()
        mock_notion.last_error_code = None

        mock_config = MagicMock()
        mock_config.get = MagicMock(return_value=True)  # require_human_approval = True

        with (
            patch("pipeline.process_stages.persist_stage.regulation_checker", None),
            patch("pipeline.process_stages.persist_stage.notebooklm_enricher", None),
            patch("pipeline.process_stages.persist_stage.record_draft_event"),
            patch("pipeline.process_stages.persist_stage.refresh_ml_scorer_if_needed"),
        ):
            result = await run_persist_stage(
                ctx=ctx,
                image_uploader=MagicMock(),
                image_generator=None,
                notion_uploader=mock_notion,
                twitter_poster=None,
                config=mock_config,
                review_only=False,
            )

        assert result is True
        assert ctx.result["success"] is True
        assert ctx.notion_url == "https://notion.so/page1"
        assert ctx.notion_page_id == "page-id-1"

    @pytest.mark.asyncio
    async def test_notion_upload_failure(self):
        """Failed Notion upload returns False."""
        ctx = _make_ctx()
        ctx.screenshot_task = None

        mock_notion = AsyncMock()
        mock_notion.upload = AsyncMock(return_value=None)
        mock_notion.last_error_code = "RATE_LIMITED"

        with (
            patch("pipeline.process_stages.persist_stage.regulation_checker", None),
            patch("pipeline.process_stages.persist_stage.notebooklm_enricher", None),
        ):
            result = await run_persist_stage(
                ctx=ctx,
                image_uploader=MagicMock(),
                image_generator=None,
                notion_uploader=mock_notion,
                twitter_poster=None,
                config=None,
                review_only=False,
            )

        assert result is False
        assert ctx.result["failure_stage"] == "upload"
        assert ctx.result["failure_reason"] == "notion_upload_failed"

    @pytest.mark.asyncio
    async def test_community_source_uses_original_image(self):
        """Community sources (ppomppu, fmkorea) use original images from post."""
        ctx = _make_ctx()
        ctx.post_data["source"] = "ppomppu"
        ctx.post_data["image_urls"] = ["https://example.com/image.jpg"]
        ctx.screenshot_task = None

        mock_notion = AsyncMock()
        mock_notion.upload = AsyncMock(return_value=("https://notion.so/page1", "page-id-1"))
        mock_notion.update_page_properties = AsyncMock()
        mock_notion.last_error_code = None

        mock_config = MagicMock()
        mock_config.get = MagicMock(return_value=True)

        with (
            patch("pipeline.process_stages.persist_stage.regulation_checker", None),
            patch("pipeline.process_stages.persist_stage.notebooklm_enricher", None),
            patch("pipeline.process_stages.persist_stage.record_draft_event"),
            patch("pipeline.process_stages.persist_stage.refresh_ml_scorer_if_needed"),
        ):
            result = await run_persist_stage(
                ctx=ctx,
                image_uploader=MagicMock(),
                image_generator=None,
                notion_uploader=mock_notion,
                twitter_poster=None,
                config=mock_config,
                review_only=False,
            )

        assert result is True
        # The original image URL should have been passed to notion upload
        call_args = mock_notion.upload.call_args
        # image_url is the second positional argument
        assert call_args[0][1] == "https://example.com/image.jpg"

    @pytest.mark.asyncio
    async def test_screenshot_task_failure(self):
        """Screenshot task failure adds error but doesn't block upload."""
        ctx = _make_ctx()
        ctx.post_data["source"] = "fmkorea"

        # Create a future that raises
        import asyncio

        screenshot_future = asyncio.get_event_loop().create_future()
        screenshot_future.set_exception(RuntimeError("screenshot failed"))
        ctx.screenshot_task = screenshot_future

        mock_notion = AsyncMock()
        mock_notion.upload = AsyncMock(return_value=("https://notion.so/page1", "page-id-1"))
        mock_notion.update_page_properties = AsyncMock()
        mock_notion.last_error_code = None

        mock_config = MagicMock()
        mock_config.get = MagicMock(return_value=True)

        with (
            patch("pipeline.process_stages.persist_stage.regulation_checker", None),
            patch("pipeline.process_stages.persist_stage.notebooklm_enricher", None),
            patch("pipeline.process_stages.persist_stage.record_draft_event"),
            patch("pipeline.process_stages.persist_stage.refresh_ml_scorer_if_needed"),
        ):
            result = await run_persist_stage(
                ctx=ctx,
                image_uploader=MagicMock(),
                image_generator=None,
                notion_uploader=mock_notion,
                twitter_poster=None,
                config=mock_config,
                review_only=False,
            )

        assert result is True
        # Error should be recorded but not blocking
        assert "Screenshot upload error" in ctx.result.get("error", "")

    @pytest.mark.asyncio
    async def test_review_only_sets_status(self):
        """review_only=True sets status to '검토필요' instead of publishing."""
        ctx = _make_ctx()
        ctx.screenshot_task = None
        ctx.decision = {"status": "검토필요"}

        mock_notion = AsyncMock()
        mock_notion.upload = AsyncMock(return_value=("https://notion.so/page1", "page-id-1"))
        mock_notion.update_page_properties = AsyncMock()
        mock_notion.last_error_code = None

        mock_config = MagicMock()
        mock_config.get = MagicMock(return_value=True)

        with (
            patch("pipeline.process_stages.persist_stage.regulation_checker", None),
            patch("pipeline.process_stages.persist_stage.notebooklm_enricher", None),
            patch("pipeline.process_stages.persist_stage.record_draft_event"),
            patch("pipeline.process_stages.persist_stage.refresh_ml_scorer_if_needed"),
        ):
            result = await run_persist_stage(
                ctx=ctx,
                image_uploader=MagicMock(),
                image_generator=None,
                notion_uploader=mock_notion,
                twitter_poster=None,
                config=mock_config,
                review_only=True,
            )

        assert result is True
        # Should update status to review-required
        mock_notion.update_page_properties.assert_called_once()
        call_args = mock_notion.update_page_properties.call_args
        assert call_args[0][1]["status"] == "검토필요"
