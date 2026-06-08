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

PUBLISH_RESEARCH_CONTEXT = {
    "source_frame": "상사와 직원의 감정 싸움",
    "real_issue": "권한을 가진 사람이 책임 있게 말하고 행동해야 한다는 문제",
    "universal_value": "책임 있는 권한",
    "killer_sentence": "이건 윗사람을 공격하자는 게 아니라 권한에는 책임이 따른다는 말입니다",
    "closure": "open",
    "conflict_risk": 0.2,
    "value_reduction_failed": False,
}

PUBLISH_READY_DRAFT = (
    '"먼저 가도 된다" 해놓고 평가에서 태도를 봤대요.\n'
    "참 이상한 기준이에요. "
    "이건 윗사람을 공격하자는 게 아니라 권한에는 책임이 따른다는 말입니다. "
    "개인 감정으로 끝낼 일이 아니라, 같은 기준을 설명하는 책임의 문제거든요. "
    "정답은 회사마다 달라질 수 있어도 기준은 남습니다."
)


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
    async def test_auto_publish_env_still_blocks_missing_research_context(self, monkeypatch):
        """AUTO_PUBLISH alone cannot bypass the single publish decision gate."""
        monkeypatch.setenv("AUTO_PUBLISH", "1")
        ctx = _make_ctx()
        ctx.screenshot_task = None
        ctx.drafts = {"twitter": PUBLISH_READY_DRAFT, "_provider_used": "gemini"}

        mock_notion = AsyncMock()
        mock_notion.upload = AsyncMock(return_value=("https://notion.so/drop", "page-drop"))
        mock_notion.update_page_properties = AsyncMock()
        mock_notion.last_error_code = None

        mock_config = MagicMock()
        mock_config.get.side_effect = lambda key, default=None: {
            "content_strategy.require_human_approval": False,
            "auto_publish.enabled": True,
            "publish.quality_threshold": 85,
        }.get(key, default)

        with (
            patch("pipeline.process_stages.persist_stage.regulation_checker", None),
            patch("pipeline.process_stages.persist_stage.notebooklm_enricher", None),
            patch("pipeline.process_stages.persist_stage.record_draft_event"),
            patch("pipeline.process_stages.persist_stage.refresh_ml_scorer_if_needed"),
            patch("pipeline.process_stages.persist_stage.post_to_twitter", new=AsyncMock()) as post_mock,
        ):
            result = await run_persist_stage(
                ctx=ctx,
                image_uploader=MagicMock(),
                image_generator=None,
                notion_uploader=mock_notion,
                twitter_poster=MagicMock(enabled=True),
                config=mock_config,
                review_only=False,
            )

        assert result is True
        post_mock.assert_not_awaited()
        assert ctx.result["publish_decision"]["action"] == "DROP"
        assert ctx.post_data["x_publish_status"] == "Blocked"
        assert ctx.post_data["x_publish_error"] == "research_context value reduction failed"

    @pytest.mark.asyncio
    async def test_publish_ready_decision_waits_for_explicit_auto_publish_flag(self, monkeypatch):
        """A ready X draft is marked Ready to Post, but is not posted without AUTO_PUBLISH."""
        monkeypatch.delenv("AUTO_PUBLISH", raising=False)
        ctx = _make_ctx()
        ctx.screenshot_task = None
        ctx.post_data["research_context"] = PUBLISH_RESEARCH_CONTEXT
        ctx.post_data["quality_gate_scores"] = {"twitter": 95}
        ctx.drafts = {"twitter": PUBLISH_READY_DRAFT, "_provider_used": "gemini"}

        mock_notion = AsyncMock()
        mock_notion.upload = AsyncMock(return_value=("https://notion.so/ready", "page-ready"))
        mock_notion.update_page_properties = AsyncMock()
        mock_notion.last_error_code = None

        mock_config = MagicMock()
        mock_config.get.side_effect = lambda key, default=None: {
            "content_strategy.require_human_approval": False,
            "auto_publish.enabled": False,
            "publish.quality_threshold": 85,
        }.get(key, default)

        with (
            patch("pipeline.process_stages.persist_stage.regulation_checker", None),
            patch("pipeline.process_stages.persist_stage.notebooklm_enricher", None),
            patch("pipeline.process_stages.persist_stage.record_draft_event"),
            patch("pipeline.process_stages.persist_stage.refresh_ml_scorer_if_needed"),
            patch("pipeline.process_stages.persist_stage.post_to_twitter", new=AsyncMock()) as post_mock,
        ):
            result = await run_persist_stage(
                ctx=ctx,
                image_uploader=MagicMock(),
                image_generator=None,
                notion_uploader=mock_notion,
                twitter_poster=MagicMock(enabled=True),
                config=mock_config,
                review_only=False,
            )

        assert result is True
        post_mock.assert_not_awaited()
        assert ctx.result["publish_decision"]["action"] == "PUBLISH"
        assert ctx.post_data["x_publish_status"] == "Ready to Post"

    @pytest.mark.asyncio
    async def test_records_comment_trigger_avg_from_drafts_stash(self):
        """T-1107: persist 단계가 drafts._comment_trigger_avg 를 record_draft_event 에 전달."""
        ctx = _make_ctx()
        ctx.screenshot_task = None
        ctx.drafts = {
            "twitter": "[공감형 트윗] Test tweet",
            "_provider_used": "gemini",
            "_hook_score": 7.2,
            "_virality_score": 8.0,
            "_fit_score": 6.5,
            "_comment_trigger_avg": 7.85,
        }

        mock_notion = AsyncMock()
        mock_notion.upload = AsyncMock(return_value=("https://notion.so/page-ct", "page-ct-1"))
        mock_notion.update_page_properties = AsyncMock()
        mock_notion.last_error_code = None

        mock_config = MagicMock()
        mock_config.get = MagicMock(return_value=True)

        with (
            patch("pipeline.process_stages.persist_stage.regulation_checker", None),
            patch("pipeline.process_stages.persist_stage.notebooklm_enricher", None),
            patch("pipeline.process_stages.persist_stage.record_draft_event") as record_mock,
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
        record_mock.assert_called_once()
        kwargs = record_mock.call_args.kwargs
        assert kwargs["comment_trigger_avg"] == 7.85
        assert kwargs["hook_score"] == 7.2
        assert kwargs["virality_score"] == 8.0
        assert kwargs["fit_score"] == 6.5

    @pytest.mark.asyncio
    async def test_records_zero_comment_trigger_avg_when_not_stashed(self):
        """drafts 에 _comment_trigger_avg 가 없으면 0.0 으로 안전하게 폴백."""
        ctx = _make_ctx()
        ctx.screenshot_task = None
        # drafts 에 _comment_trigger_avg 없음

        mock_notion = AsyncMock()
        mock_notion.upload = AsyncMock(return_value=("https://notion.so/page-nz", "page-nz-1"))
        mock_notion.update_page_properties = AsyncMock()
        mock_notion.last_error_code = None

        mock_config = MagicMock()
        mock_config.get = MagicMock(return_value=True)

        with (
            patch("pipeline.process_stages.persist_stage.regulation_checker", None),
            patch("pipeline.process_stages.persist_stage.notebooklm_enricher", None),
            patch("pipeline.process_stages.persist_stage.record_draft_event") as record_mock,
            patch("pipeline.process_stages.persist_stage.refresh_ml_scorer_if_needed"),
        ):
            await run_persist_stage(
                ctx=ctx,
                image_uploader=MagicMock(),
                image_generator=None,
                notion_uploader=mock_notion,
                twitter_poster=None,
                config=mock_config,
                review_only=False,
            )

        record_mock.assert_called_once()
        kwargs = record_mock.call_args.kwargs
        assert kwargs["comment_trigger_avg"] == 0.0

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
