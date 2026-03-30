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
    def __init__(self, performance=None, approved=None):
        self.performance = performance or []
        self.approved = approved or []

    async def get_top_performing_posts(self, **kwargs):  # noqa: ARG002
        return self.performance

    async def get_recent_approved_posts(self, **kwargs):  # noqa: ARG002
        return self.approved


def test_few_shot_prefers_performance_examples():
    notion = FakeNotionUploader(
        performance=[{"text": "성과형 예시", "views": 1000, "topic_cluster": "연봉"}],
        approved=[{"text": "승인 예시"}],
    )
    loop = FeedbackLoop(notion, FakeConfig())

    result = asyncio.run(loop.get_few_shot_examples())

    assert result == [{"text": "성과형 예시", "views": 1000, "topic_cluster": "연봉"}]


def test_few_shot_falls_back_to_approved_examples():
    notion = FakeNotionUploader(
        performance=[],
        approved=[{"text": "승인 예시", "review_status": "승인됨"}],
    )
    loop = FeedbackLoop(notion, FakeConfig())

    result = asyncio.run(loop.get_few_shot_examples())

    assert result == [{"text": "승인 예시", "review_status": "승인됨"}]


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
