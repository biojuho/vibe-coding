"""Regression tests for pipeline.process_stages.generate_review_stage."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import ERROR_DRAFT_GENERATION_FAILED  # noqa: E402
from pipeline.process_stages.context import ProcessRunContext, build_process_result  # noqa: E402
from pipeline.process_stages.generate_review_stage import run_generate_review_stage  # noqa: E402


def _make_ctx(url: str = "http://test/1") -> ProcessRunContext:
    return ProcessRunContext(
        url=url,
        trace_id="test-trace",
        result=build_process_result(url, "test-trace"),
        post_data={"title": "테스트 제목", "content": "본문 내용"},
    )


# ── GRS-RFD: retry 후 failure dict가 Notion persist로 흐르면 안 됨 ─────────────


@pytest.mark.asyncio
async def test_retry_failure_dict_does_not_flow_to_notion_persist():
    """GRS-RFD001: quality gate retry 실패 dict 가 _complete_generate_review_stage 로 흘러 Notion 에 정상 업로드되면 안 된다."""
    ctx = _make_ctx()

    failure_dict = {
        "_generation_failed": True,
        "_generation_error": "All retries exhausted",
        "_provider_used": "none",
    }

    # Initial generation succeeds (passes the first _handle_generation_failure check)
    initial_success = {"twitter": "초기 생성된 트윗 내용", "_provider_used": "anthropic"}

    mock_generator = MagicMock()
    mock_generator.generate_drafts = AsyncMock(return_value=(initial_success, None))

    async def _fake_quality_gate_retries(
        ctx, drafts, image_prompt, draft_generator, top_tweets, output_formats, config, review_only
    ):
        # Simulates retry exhaustion: returns failure dict instead of valid drafts
        return failure_dict, None, None, None, False

    with (
        patch(
            "pipeline.process_stages.generate_review_stage._run_quality_gate_retries",
            side_effect=_fake_quality_gate_retries,
        ),
        patch(
            "pipeline.process_stages.generate_review_stage._complete_generate_review_stage",
        ) as mock_complete,
        patch(
            "pipeline.process_stages.generate_review_stage.ensure_research_context",
            return_value={},
        ),
        patch(
            "pipeline.process_stages.generate_review_stage._start_screenshot_upload",
        ),
    ):
        await run_generate_review_stage(
            ctx,
            draft_generator=mock_generator,
            image_uploader=None,
            top_tweets=None,
            output_formats=["twitter"],
            config=MagicMock(),
        )

    # _complete_generate_review_stage must NOT be called — failure must exit early
    mock_complete.assert_not_called(), "Failure dict must not reach _complete_generate_review_stage (Notion persist)"

    # Stage result must indicate generation failure
    assert ctx.result.get("error_code") == ERROR_DRAFT_GENERATION_FAILED, (
        f"Expected {ERROR_DRAFT_GENERATION_FAILED}, got: {ctx.result.get('error_code')}"
    )
    assert ctx.post_data.get("draft_generation_failed") is True
