from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.notion_upload import NotionUploader  # noqa: E402
from scripts.backfill_notion_review_columns import build_review_backfill_updates  # noqa: E402


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
