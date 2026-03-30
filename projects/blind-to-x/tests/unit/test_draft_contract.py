from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.draft_contract import iter_publishable_drafts, split_draft_bundle  # noqa: E402
from pipeline.draft_generator import TweetDraftGenerator  # noqa: E402
from pipeline.draft_quality_gate import DraftQualityGate  # noqa: E402
from pipeline.editorial_reviewer import EditorialReviewer  # noqa: E402


def test_split_draft_bundle_separates_publishable_and_review_metadata():
    drafts = {
        "twitter": "publishable",
        "reply_text": "reply",
        "creator_take": "memo",
        "_provider_used": "gemini",
    }

    bundle = split_draft_bundle(drafts)

    assert bundle["publishable"] == {"twitter": "publishable"}
    assert bundle["auxiliary"] == {"reply_text": "reply"}
    assert bundle["review_meta"] == {"creator_take": "memo"}
    assert bundle["internal"] == {"_provider_used": "gemini"}


def test_iter_publishable_drafts_skips_reply_and_creator_take():
    drafts = {
        "twitter": "publishable",
        "reply_text": "reply",
        "creator_take": "memo",
        "_provider_used": "gemini",
    }

    assert list(iter_publishable_drafts(drafts)) == [("twitter", "publishable")]


def test_quality_gate_only_validates_publishable_keys():
    gate = DraftQualityGate()
    results = gate.validate_all(
        {
            "twitter": "연봉 280이면 조용할 줄 알았는데 더 흔들립니다. 지금 버티기 vs 이직 준비, 뭐가 현실적이세요?",
            "reply_text": "원문: (링크)",
            "creator_take": "운영자 메모",
        }
    )

    assert "twitter" in results
    assert "reply_text" not in results
    assert "creator_take" not in results


@patch.object(EditorialReviewer, "_call_llm", new_callable=AsyncMock)
def test_editorial_reviewer_only_reviews_publishable_drafts(mock_call_llm):
    reviewer = EditorialReviewer(config=None)
    reviewer._providers = [{"name": "fake"}]
    mock_call_llm.return_value = {
        "scores": {"hook": 8, "specificity": 8, "voice": 8, "engagement": 8, "readability": 8},
        "suggestions": ["ok"],
        "rewritten": "개선된 게시용 초안",
    }

    result = asyncio.run(
        reviewer.review_and_polish(
            {
                "twitter": "초기 게시용 초안",
                "reply_text": "원문: (링크)",
                "creator_take": "운영자 메모",
            },
            {"title": "테스트", "content": "본문"},
        )
    )

    assert result.polished_drafts["twitter"] == "초기 게시용 초안"
    assert result.polished_drafts["reply_text"] == "원문: (링크)"
    assert result.polished_drafts["creator_take"] == "운영자 메모"
    assert list(result.original_drafts) == ["twitter"]
    assert mock_call_llm.await_count == 1


def test_format_examples_is_deterministic_for_same_seed():
    examples = [
        {"text": "예시 A", "hook_type": "숫자", "grade": "A"},
        {"text": "예시 B", "hook_type": "장면", "grade": "A"},
        {"text": "예시 C", "hook_type": "대사", "grade": "A"},
    ]

    first = TweetDraftGenerator._select_examples_deterministically(examples, limit=2, seed_text="salary")
    second = TweetDraftGenerator._select_examples_deterministically(examples, limit=2, seed_text="salary")
    third = TweetDraftGenerator._select_examples_deterministically(examples, limit=2, seed_text="culture")

    assert first == second
    assert len(first) == 2
    assert third != first
