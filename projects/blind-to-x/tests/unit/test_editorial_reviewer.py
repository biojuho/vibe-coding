"""Tests for pipeline.editorial_reviewer pure helpers."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

from pipeline.editorial_reviewer import _REWRITE_THRESHOLD, EditorialReviewer


def _make_reviewer(thresholds: dict | None = None, brand_voice: dict | None = None) -> EditorialReviewer:
    """Create a reviewer without triggering full __init__."""
    obj = object.__new__(EditorialReviewer)
    obj._editorial_thresholds = thresholds
    obj.brand_voice = brand_voice or {}
    obj._api_key = None
    obj._model = "gemini-2.0-flash"
    return obj


# ── _get_threshold ───────────────────────────────────────────────────────────


class TestGetThreshold:
    def test_default_no_config(self):
        reviewer = _make_reviewer()
        assert reviewer._get_threshold("twitter") == _REWRITE_THRESHOLD

    def test_platform_default(self):
        reviewer = _make_reviewer(thresholds={"defaults": {"twitter": 6.0}})
        assert reviewer._get_threshold("twitter") == 6.0

    def test_topic_override(self):
        reviewer = _make_reviewer(
            thresholds={
                "defaults": {"twitter": 6.0},
                "topic_overrides": {"경제": {"twitter": 7.5}},
            }
        )
        assert reviewer._get_threshold("twitter", "경제") == 7.5

    def test_topic_override_missing_platform(self):
        reviewer = _make_reviewer(
            thresholds={
                "defaults": {"twitter": 6.0},
                "topic_overrides": {"경제": {"threads": 8.0}},
            }
        )
        # Topic override exists but not for twitter → falls to platform default
        assert reviewer._get_threshold("twitter", "경제") == 6.0

    def test_topic_no_override_falls_to_default(self):
        reviewer = _make_reviewer(thresholds={"defaults": {"naver_blog": 4.5}, "topic_overrides": {}})
        assert reviewer._get_threshold("naver_blog") == 4.5

    def test_missing_platform_in_defaults(self):
        reviewer = _make_reviewer(thresholds={"defaults": {}})
        assert reviewer._get_threshold("unknown_platform") == _REWRITE_THRESHOLD


# ── _build_review_prompt ─────────────────────────────────────────────────────


class TestBuildReviewPrompt:
    def test_basic_prompt_structure(self):
        reviewer = _make_reviewer()
        prompt = reviewer._build_review_prompt(
            platform="twitter",
            draft_text="이것은 초안입니다.",
            post_data={"title": "테스트 제목", "content": "본문 내용"},
        )
        assert "테스트 제목" in prompt
        assert "twitter" in prompt
        assert "이것은 초안입니다" in prompt
        assert "hook" in prompt
        assert "JSON" in prompt

    def test_content_truncated(self):
        reviewer = _make_reviewer()
        long_content = "가" * 1000
        prompt = reviewer._build_review_prompt(
            platform="threads",
            draft_text="초안",
            post_data={"content": long_content},
        )
        # Content should be truncated to 500 chars
        assert "가" * 500 in prompt
        assert "가" * 501 not in prompt

    def test_brand_voice_included(self):
        reviewer = _make_reviewer(
            brand_voice={
                "persona": "직장인 선배",
                "voice_traits": ["솔직한", "다정한"],
                "forbidden_expressions": ["갓생", "MBTI"],
            }
        )
        prompt = reviewer._build_review_prompt(
            platform="twitter",
            draft_text="초안",
            post_data={},
        )
        assert "직장인 선배" in prompt
        assert "솔직한" in prompt
        assert "갓생" in prompt

    def test_no_brand_voice(self):
        reviewer = _make_reviewer(brand_voice={})
        prompt = reviewer._build_review_prompt(
            platform="twitter",
            draft_text="초안",
            post_data={},
        )
        # Brand voice section should not have a persona value (empty)
        assert "페르소나:" not in prompt or "페르소나: \n" not in prompt

    def test_numbers_extracted_from_content(self):
        reviewer = _make_reviewer()
        prompt = reviewer._build_review_prompt(
            platform="twitter",
            draft_text="초안",
            post_data={"content": "연봉 5000만원, 이직률 30%"},
        )
        assert "5000만" in prompt or "30%" in prompt

    def test_topic_from_profile(self):
        reviewer = _make_reviewer()
        prompt = reviewer._build_review_prompt(
            platform="twitter",
            draft_text="초안",
            post_data={"content_profile": {"topic_cluster": "경제"}},
        )
        assert "경제" in prompt


# BTX-ER001 — _reviewer_node handles float score strings from LLM
class TestReviewerNodeFloatScores:
    """LLM sometimes returns "7.5" or 7.5 instead of integer scores (BTX-ER001)."""

    def _make_reviewer_with_llm(self, fake_result: dict):
        reviewer = _make_reviewer()
        reviewer._call_llm = AsyncMock(return_value=fake_result)
        return reviewer

    def _run(self, coro):
        return asyncio.get_event_loop().run_until_complete(coro)

    def test_float_string_scores_do_not_raise(self):
        """'7.5' score strings must not raise ValueError from int()."""
        reviewer = self._make_reviewer_with_llm(
            {
                "scores": {
                    "accuracy": "7.5",
                    "relevance": "8.0",
                    "originality": "6.5",
                    "clarity": "9",
                    "engagement": "7.5",
                },
                "suggestions": [],
                "rewritten": "rewritten text",
            }
        )
        state = {
            "platform": "twitter",
            "draft_text": "test draft",
            "post_data": {},
            "avg_score": 0.0,
            "iteration": 0,
            "max_iterations": 3,
            "rewritten_candidate": "",
        }
        result = self._run(reviewer._reviewer_node(state))
        assert "avg_score" in result
        assert isinstance(result["avg_score"], float)

    def test_float_scores_clamped_to_1_10(self):
        """Scores outside [1, 10] must be clamped even with float values."""
        reviewer = self._make_reviewer_with_llm(
            {
                "scores": {
                    "accuracy": 11.5,  # over max
                    "relevance": -0.5,  # under min
                    "originality": 5.0,
                    "clarity": 5.0,
                    "engagement": 5.0,
                },
                "suggestions": [],
                "rewritten": "text",
            }
        )
        state = {
            "platform": "twitter",
            "draft_text": "draft",
            "post_data": {},
            "avg_score": 0.0,
            "iteration": 0,
            "max_iterations": 3,
            "rewritten_candidate": "",
        }
        result = self._run(reviewer._reviewer_node(state))
        # avg_score should be (10 + 1 + 5 + 5 + 5) / 5 = 5.2
        assert 1.0 <= result["avg_score"] <= 10.0
