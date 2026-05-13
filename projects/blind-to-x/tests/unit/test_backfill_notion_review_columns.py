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
    _fetch_page_sections,
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
    assert updates["publish_platforms"] == ["숏폼", "Threads"]
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
