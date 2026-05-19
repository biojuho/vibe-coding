from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.notion_upload import NotionUploader  # noqa: E402
from scripts.backfill_notion_review_columns import (  # noqa: E402
    _append_x_upload_card,
    _fetch_page_sections,
    _needs_x_upload_card,
    build_review_backfill_updates,
)


def _mock_config() -> dict:
    return {
        "notion.api_key": "test_api_key",
        "notion.database_id": "test_db_id",
        "notion.status_default": "검토필요",
        "dedup.cache_ttl_minutes": "30",
        "dedup.lookback_days": "14",
    }


def test_build_review_backfill_updates_derives_reviewer_columns():
    notion = NotionUploader(_mock_config())
    record = {
        "status": "검토필요",
        "memo": "원본 링크: https://example.com/post\n왜 고름: 월급 얘기가 바로 직장인 현실로 연결되는 글",
        "source": "blind",
        "creator_take": "",
        "review_focus": "",
        "feedback_request": "",
        "evidence_anchor": "",
        "risk_flags": [],
        "rejection_reasons": [],
        "publish_platforms": [],
        "x_publish_status": "",
        "tweet_body": "",
        "threads_body": "",
        "blog_body": "",
    }
    sections = {
        "콘텐츠 인텔리전스": [
            "왜 고름: 월급 얘기가 바로 직장인 현실로 연결되는 글",
            "공감 앵커: 연봉 1800 깎고 이직",
        ],
        "X(Twitter) 초안": ["숏폼 초안"],
        "Threads 초안": ["Threads 초안"],
    }

    updates = build_review_backfill_updates(notion, record, sections)

    assert updates["creator_take"] == "월급 얘기가 바로 직장인 현실로 연결되는 글"
    assert updates["evidence_anchor"] == "연봉 1800 깎고 이직"
    assert updates["publish_platforms"] == ["X", "Threads"]
    assert updates["x_publish_status"] == "Ready to Post"
    assert "근거 앵커" in updates["review_focus"]
    assert "반려 사유" in updates["feedback_request"]


def test_build_review_backfill_updates_infers_rejection_reasons_for_rejected_pages():
    notion = NotionUploader(_mock_config())
    record = {
        "status": "반려됨",
        "memo": "원본 링크: https://example.com/post\n왜 고름: 감은 있지만 근거가 약한 글",
        "source": "blind",
        "creator_take": "",
        "review_focus": "",
        "feedback_request": "",
        "evidence_anchor": "",
        "risk_flags": ["근거 약함"],
        "rejection_reasons": [],
        "publish_platforms": [],
        "tweet_body": "",
        "threads_body": "",
        "blog_body": "",
    }
    sections = {"콘텐츠 인텔리전스": ["왜 고름: 감은 있지만 근거가 약한 글"]}

    updates = build_review_backfill_updates(notion, record, sections)

    assert updates["rejection_reasons"] == ["근거 약함"]


def test_needs_x_upload_card_detects_missing_card_with_tweet_body():
    record = {"tweet_body": "바로 올릴 X 본문"}

    assert _needs_x_upload_card(record, {"검토 요약": []}) is True
    assert _needs_x_upload_card(record, {"X 업로드 카드": []}) is False
    assert _needs_x_upload_card({"tweet_body": ""}, {"검토 요약": []}) is False


@pytest.mark.asyncio
async def test_append_x_upload_card_appends_copy_ready_blocks():
    notion = NotionUploader(_mock_config())
    notion._safe_notion_call = AsyncMock(return_value={})
    notion.client = MagicMock()
    notion.client.blocks.children.append = AsyncMock()

    record = {
        "page_id": "page-1",
        "tweet_body": "팀장보다 먼저 퇴근했다가 혼났다.",
        "reply_text": "원문: https://example.com/post\n#직장문화",
    }

    result = await _append_x_upload_card(notion, record)

    assert result is True
    notion._safe_notion_call.assert_awaited_once()
    kwargs = notion._safe_notion_call.await_args.kwargs
    assert kwargs["block_id"] == "page-1"
    headings = [
        block[block["type"]]["rich_text"][0]["text"]["content"]
        for block in kwargs["children"]
        if block.get("type") in {"heading_2", "heading_3"}
    ]
    assert "X 업로드 카드" in headings
    assert "X 본문" in headings
    assert "첫 답글 / 출처 메모" in headings


@pytest.mark.asyncio
async def test_fetch_page_sections_recurses_toggle_children():
    notion = MagicMock()
    notion.client = MagicMock()
    notion.client.blocks.children.list = AsyncMock(
        side_effect=[
            {
                "results": [
                    {
                        "id": "toggle-1",
                        "type": "toggle",
                        "has_children": True,
                        "toggle": {"rich_text": [{"plain_text": "진단 펼치기"}]},
                    }
                ],
                "has_more": False,
                "next_cursor": None,
            },
            {
                "results": [
                    {
                        "id": "heading-1",
                        "type": "heading_3",
                        "has_children": False,
                        "heading_3": {"rich_text": [{"plain_text": "콘텐츠 인텔리전스"}]},
                    },
                    {
                        "id": "paragraph-1",
                        "type": "paragraph",
                        "has_children": False,
                        "paragraph": {"rich_text": [{"plain_text": "공감 앵커: 연봉 1800 깎고 이직"}]},
                    },
                ],
                "has_more": False,
                "next_cursor": None,
            },
        ]
    )

    sections = await _fetch_page_sections(notion, "page-1")

    assert sections["콘텐츠 인텔리전스"] == ["공감 앵커: 연봉 1800 깎고 이직"]
    assert "진단 펼치기" not in sections
