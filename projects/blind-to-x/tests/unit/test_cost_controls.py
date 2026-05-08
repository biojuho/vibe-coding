from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.cost_db import CostDatabase  # noqa: E402
from pipeline.cost_tracker import CostTracker  # noqa: E402
from pipeline.draft_generator import TweetDraftGenerator  # noqa: E402
from pipeline.process import process_single_post  # noqa: E402


class FakeConfig:
    def __init__(self, data: dict):
        self.data = data

    def get(self, key, default=None):
        cur = self.data
        for part in key.split("."):
            if isinstance(cur, dict):
                cur = cur.get(part)
            else:
                return default
        return default if cur is None else cur


class StubScraper:
    min_content_length = 20

    async def scrape_post(self, url):
        return {
            "title": f"title:{url}",
            "url": url,
            "content": "직장인 공감 포인트가 충분히 담긴 테스트 본문입니다. 이직과 회사 문화 이야기가 포함됩니다.",
            "screenshot_path": None,
        }

    def assess_quality(self, _post_data):
        return {"score": 90, "reasons": [], "metrics": {}}


class StubImageUploader:
    async def upload(self, _path):
        return "https://image.example/test.png"


class StubImageGenerator:
    def __init__(self):
        self.called = 0

    async def generate_image(self, *_args, **_kwargs):
        self.called += 1
        return "https://image.example/generated.png"


class StubDraftGenerator:
    async def generate_drafts(self, _post_data, top_tweets=None, output_formats=None, allow_partial=False):  # noqa: ARG002
        return {
            "twitter": "[공감형 트윗]\n초안",
            "newsletter": "뉴스레터 초안",
            "_provider_used": "gemini",
        }, "office illustration"


class StubNotionUploaderOk:
    last_error_code = None
    last_error_message = None

    async def is_duplicate(self, _url):
        return False

    async def upload(self, _post_data, _image_url, _drafts, analysis=None, **kwargs):  # noqa: ARG002
        return "https://notion.so/page", "page-1"

    async def update_page_properties(self, _page_id, _updates):
        return True


def test_cost_tracker_uses_persisted_daily_totals():
    db = CostDatabase()
    db.record_text_cost(provider="openai", usd=1.25)
    db.record_image_cost(provider="gemini", image_count=500, usd=0.0)

    tracker = CostTracker(FakeConfig({"limits": {"daily_api_budget_usd": 1.0}}))

    assert tracker.current_cost >= 1.25
    assert tracker.is_budget_exceeded() is True
    assert tracker.can_use_gemini_image() is False


def test_record_draft_upserts_publish_state():
    db = CostDatabase()
    db.record_draft(
        source="blind",
        topic_cluster="이직",
        hook_type="공감형",
        emotion_axis="공감",
        draft_style="공감형",
        provider_used="gemini",
        final_rank_score=82.0,
        published=False,
        content_url="https://example.com/post-1",
        notion_page_id="page-1",
    )
    db.record_draft(
        source="blind",
        topic_cluster="이직",
        hook_type="공감형",
        emotion_axis="공감",
        draft_style="공감형",
        provider_used="gemini",
        final_rank_score=82.0,
        published=True,
        content_url="https://example.com/post-1",
        notion_page_id="page-1",
    )

    with db._conn() as conn:
        row = conn.execute(
            """
            SELECT COUNT(*) AS cnt, MAX(published) AS published
            FROM draft_analytics
            WHERE content_url = ?
            """,
            ("https://example.com/post-1",),
        ).fetchone()

    assert row["cnt"] == 1
    assert row["published"] == 1


from unittest.mock import patch  # noqa: E402


@patch("pipeline.editorial_reviewer.EditorialReviewer")
def test_review_only_still_generates_image_and_records_draft(mock_reviewer_class):
    mock_reviewer = mock_reviewer_class.return_value

    # AsyncMock is automatically used if the patched method is async in 3.8+, but let's be safe:
    async def mock_eval(*args, **kwargs):
        return {
            "action": "approve",
            "revised_drafts": {"twitter": "revised tweet", "_provider_used": "gemini"},
            "reason": "OK",
        }

    mock_reviewer.evaluate_and_rewrite = mock_eval

    image_generator = StubImageGenerator()

    result = asyncio.run(
        process_single_post(
            "https://example.com/a",
            StubScraper(),
            StubImageUploader(),
            image_generator=image_generator,
            draft_generator=StubDraftGenerator(),
            notion_uploader=StubNotionUploaderOk(),
            config=FakeConfig(
                {
                    "content_strategy": {"require_human_approval": True},
                    "ranking": {
                        "final_rank_min": 60,
                        "weights": {
                            "scrape_quality": 0.35,
                            "publishability": 0.40,
                            "performance": 0.25,
                        },
                    },
                    "review": {
                        "auto_move_to_review_threshold": 65,
                        "reject_on_missing_title": True,
                        "reject_on_missing_content": True,
                    },
                }
            ),
            source_name="blind",
            feed_mode="popular",
            review_only=True,
        )
    )

    assert result["success"] is True
    assert image_generator.called == 1  # review_only여도 이미지 생성은 실행

    with CostDatabase()._conn() as conn:
        row = conn.execute(
            "SELECT provider_used, published FROM draft_analytics WHERE content_url = ?",
            ("https://example.com/a",),
        ).fetchone()

    assert row["provider_used"] == "gemini"
    assert row["published"] == 0


def test_draft_cache_persists_across_generator_instances(tmp_path):

    cache_db = tmp_path / "draft_cache.db"
    config = FakeConfig(
        {
            "llm": {
                "providers": ["gemini"],
                "max_retries_per_provider": 1,
                "request_timeout_seconds": 5,
                "race": {"enabled": False},
                "cache_db_path": str(cache_db),
            },
            "gemini": {"enabled": True, "api_key": "gemini-key", "model": "gemini-2.5-flash"},
            "tweet_style": {"tone": "테스트", "max_length": 280},
        }
    )

    call_count = {"gemini": 0}

    async def _gemini(_prompt):
        call_count["gemini"] += 1
        return (
            "<twitter>저장된 초안</twitter>"
            "<reply>첫 댓글</reply>"
            "<creator_take>운영자 해석</creator_take>"
            "<image_prompt>prompt</image_prompt>",
            10,
            5,
            0,
            0,
        )

    gen1 = TweetDraftGenerator(config)
    gen1._generate_with_gemini = _gemini
    drafts1, image_prompt1 = asyncio.run(
        gen1.generate_drafts({"title": "제목", "content": "본문", "content_profile": {}}, output_formats=["twitter"])
    )

    # Draft cache is now SQLite-backed (DraftCache), NOT clearing it here
    # gen2 should hit the SQLite cache from gen1

    gen2 = TweetDraftGenerator(config)
    gen2._generate_with_gemini = _gemini
    drafts2, image_prompt2 = asyncio.run(
        gen2.generate_drafts({"title": "제목", "content": "본문", "content_profile": {}}, output_formats=["twitter"])
    )

    # gen1: 1 generation call; gen2: SQLite DraftCache hit = 0 new calls
    assert call_count["gemini"] == 1
    assert drafts1 == drafts2
    assert image_prompt1 == image_prompt2 == "prompt"
