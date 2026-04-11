from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.feedback_loop import FeedbackLoop  # noqa: E402


class FakeConfig:
    def __init__(self, data=None):
        self.data = data or {
            "analytics": {
                "lookback_days": 30,
                "top_examples_limit": 3,
                "minimum_posts_for_feedback": 20,
            }
        }

    def get(self, key, default=None):
        cur = self.data
        for part in key.split("."):
            if isinstance(cur, dict):
                cur = cur.get(part)
            else:
                return default
        return default if cur is None else cur


class FakeNotionUploader:
    def __init__(self, performance=None, approved=None, recent_pages=None):
        self.performance = performance or []
        self.approved = approved or []
        self.recent_pages = recent_pages or []

    async def get_top_performing_posts(self, **kwargs):  # noqa: ARG002
        return self.performance

    async def get_recent_approved_posts(self, **kwargs):  # noqa: ARG002
        return self.approved

    async def get_recent_pages(self, **kwargs):  # noqa: ARG002
        return self.recent_pages

    def extract_page_record(self, page):
        return page


def test_few_shot_prefers_performance_examples():
    notion = FakeNotionUploader(
        performance=[{"text": "성과형 예시", "views": 1000, "topic_cluster": "연봉"}],
        approved=[{"text": "승인 예시"}],
    )
    loop = FeedbackLoop(notion, FakeConfig())

    result = asyncio.run(loop.get_few_shot_examples())

    assert result[0] == {"text": "성과형 예시", "views": 1000, "topic_cluster": "연봉"}


def test_few_shot_falls_back_to_approved_examples():
    notion = FakeNotionUploader(
        performance=[],
        approved=[{"text": "승인 예시", "status": "승인됨"}],
    )
    loop = FeedbackLoop(notion, FakeConfig())

    result = asyncio.run(loop.get_few_shot_examples())

    assert result[0] == {"text": "승인 예시", "status": "승인됨"}


def test_few_shot_falls_back_to_yaml_golden_examples():
    notion = FakeNotionUploader(performance=[], approved=[])
    loop = FeedbackLoop(
        notion,
        FakeConfig({"analytics": {"top_examples_limit": 2, "lookback_days": 30, "minimum_posts_for_feedback": 20}}),
    )

    result = asyncio.run(loop.get_few_shot_examples())

    assert len(result) == 2
    assert all(item["example_source"] == "yaml_golden" for item in result)
    assert all(item["text"] for item in result)


def test_get_reviewer_memory_builds_review_guardrails():
    notion = FakeNotionUploader(
        recent_pages=[
            {
                "status": "반려됨",
                "topic_cluster": "연봉",
                "hook_type": "공감형",
                "rejection_reasons": ["팩트 경계", "클리셰"],
                "risk_flags": ["팩트 경계"],
            },
            {
                "status": "보류",
                "topic_cluster": "연봉",
                "hook_type": "공감형",
                "rejection_reasons": ["클리셰"],
                "risk_flags": ["근거 약함"],
            },
        ]
    )
    loop = FeedbackLoop(notion, FakeConfig())

    result = asyncio.run(loop.get_reviewer_memory(limit=3, lookback_days=30))

    assert len(result) >= 2
    assert all(item["example_source"] == "reviewer_memory" for item in result)
    assert any("클리셰" in item["text"] for item in result)


def test_few_shot_examples_append_reviewer_memory():
    notion = FakeNotionUploader(
        performance=[{"text": "성과형 예시", "views": 1000, "topic_cluster": "연봉"}],
        recent_pages=[
            {
                "status": "반려됨",
                "topic_cluster": "연봉",
                "hook_type": "공감형",
                "rejection_reasons": ["팩트 경계"],
                "risk_flags": ["근거 약함"],
            }
        ],
    )
    loop = FeedbackLoop(notion, FakeConfig())

    result = asyncio.run(loop.get_few_shot_examples())

    assert result[0]["text"] == "성과형 예시"
    assert any(item.get("example_source") == "reviewer_memory" for item in result[1:])
