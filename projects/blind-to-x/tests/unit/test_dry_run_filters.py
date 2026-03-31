"""Verify that filter logic is applied before draft generation."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import blind_scraper as bs  # noqa: E402
from pipeline.process_stages.runtime import SPAM_KEYWORDS  # noqa: E402


class FakeConfig:
    def __init__(self):
        self.data = {
            "content_strategy": {"require_human_approval": True},
            "ranking": {
                "final_rank_min": 60,
                "weights": {"scrape_quality": 0.35, "publishability": 0.40, "performance": 0.25},
            },
            "review": {
                "auto_move_to_review_threshold": 65,
                "reject_on_missing_title": True,
                "reject_on_missing_content": True,
            },
        }

    def get(self, key, default=None):
        cur = self.data
        for part in key.split("."):
            if isinstance(cur, dict):
                cur = cur.get(part)
            else:
                return default
        return default if cur is None else cur


class StubImageUploader:
    async def upload(self, _path):
        return "https://image.example/test.png"


class StubDraftGenerator:
    called = False

    async def generate_drafts(self, _post_data, top_tweets=None, output_formats=None):  # noqa: ARG002
        StubDraftGenerator.called = True
        return {"twitter": "draft text"}, None


class StubNotionUploaderNoCall:
    last_error_code = None
    last_error_message = None

    async def is_duplicate(self, _url):
        return False

    async def upload(self, *_args, **_kwargs):
        raise AssertionError("upload should not be called for filtered cases")


def test_spam_keywords_exported_and_non_empty():
    assert isinstance(SPAM_KEYWORDS, list)
    assert len(SPAM_KEYWORDS) > 0


def test_spam_keywords_contains_expected_values():
    assert "스팸대출" in SPAM_KEYWORDS
    assert "추천인" in SPAM_KEYWORDS


def test_short_content_does_not_call_draft_generator():
    StubDraftGenerator.called = False

    class ShortScraper:
        min_content_length = 20

        async def scrape_post(self, url):
            return {"url": url, "title": "짧은 글", "content": "짧다", "screenshot_path": None}

        def assess_quality(self, _):
            return {"score": 90, "reasons": [], "metrics": {}}

    result = asyncio.run(
        bs.process_single_post(
            "https://example.com/short",
            ShortScraper(),
            StubImageUploader(),
            draft_generator=StubDraftGenerator(),
            notion_uploader=StubNotionUploaderNoCall(),
            config=FakeConfig(),
        )
    )
    assert result["error_code"] == bs.ERROR_FILTERED_SHORT
    assert result["notion_url"] == "(skipped-filtered)"
    assert not StubDraftGenerator.called


def test_spam_content_does_not_call_draft_generator():
    StubDraftGenerator.called = False

    class SpamScraper:
        min_content_length = 20

        async def scrape_post(self, url):
            return {
                "url": url,
                "title": "정상 제목",
                "content": "스팸대출 링크로 유도하는 스팸 게시글입니다. 추천인을 넣어 달라는 내용입니다.",
                "screenshot_path": None,
            }

        def assess_quality(self, _):
            return {"score": 90, "reasons": [], "metrics": {}}

    result = asyncio.run(
        bs.process_single_post(
            "https://example.com/spam",
            SpamScraper(),
            StubImageUploader(),
            draft_generator=StubDraftGenerator(),
            notion_uploader=StubNotionUploaderNoCall(),
            config=FakeConfig(),
        )
    )
    assert result["error_code"] == bs.ERROR_FILTERED_SPAM
    assert result["notion_url"] == "(skipped-filtered)"
    assert not StubDraftGenerator.called


def test_low_quality_content_does_not_call_draft_generator():
    StubDraftGenerator.called = False

    class LowQualityScraper:
        min_content_length = 20

        async def scrape_post(self, url):
            return {
                "url": url,
                "title": "low quality english title",
                "content": "this post is all english with no korean whatsoever just filler words here",
                "screenshot_path": None,
            }

        def assess_quality(self, _):
            return {"score": 30, "reasons": ["low_korean_ratio"], "metrics": {}}

    result = asyncio.run(
        bs.process_single_post(
            "https://example.com/lowq",
            LowQualityScraper(),
            StubImageUploader(),
            draft_generator=StubDraftGenerator(),
            notion_uploader=StubNotionUploaderNoCall(),
            config=FakeConfig(),
        )
    )
    assert result["error_code"] == bs.ERROR_FILTERED_LOW_QUALITY
    assert result["failure_reason"] == "low_korean_ratio"
    assert not StubDraftGenerator.called
