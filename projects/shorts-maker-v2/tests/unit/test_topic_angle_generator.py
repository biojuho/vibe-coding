"""Unit tests for TopicAngleGenerator."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from shorts_maker_v2.pipeline.topic_angle_generator import (
    ScoredAngle,
    TopicAngleGenerator,
    _CHANNEL_FORBIDDEN,
    _CHANNEL_HOOK_EXAMPLES,
)
from shorts_maker_v2.pipeline.trend_discovery_step import TrendCandidate


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def mock_config():
    return MagicMock()


@pytest.fixture()
def mock_llm_router():
    router = MagicMock()
    router.generate_json.return_value = {
        "angles": [
            {
                "topic": "AI 야근 역설",
                "angle": "AI 도입이 오히려 업무량을 늘리는 역설",
                "title": "AI 도입했더니 오히려 야근이 늘어난 이유",
                "title_variants": [
                    "AI 도입했더니 오히려 야근이 늘어난 이유",
                    "AI가 오히려 시간을 잡아먹는 진짜 이유",
                    "AI 쓸수록 더 바빠지는 이유",
                ],
                "hook_pattern": "cognitive_dissonance",
                "viral_score": 9.2,
                "source_keyword": "AI 도입 야근",
            },
            {
                "topic": "Claude 승인창 제거",
                "angle": "UX 결정의 숨겨진 비즈니스 이유",
                "title": "클로드가 승인창을 없앤 진짜 이유",
                "title_variants": [
                    "클로드가 승인창을 없앤 진짜 이유",
                    "Anthropic이 확인창을 제거한 충격적인 이유",
                ],
                "hook_pattern": "myth_busting",
                "viral_score": 8.7,
                "source_keyword": "Claude UX",
            },
        ]
    }
    return router


@pytest.fixture()
def sample_candidates():
    return [
        TrendCandidate(keyword="AI 도입 야근", source="youtube_rss", score=0.9, channel="ai_tech"),
        TrendCandidate(keyword="Claude UX", source="llm_brainstorm", score=0.8, channel="ai_tech"),
        TrendCandidate(keyword="바이브코딩 격차", source="google_trends", score=0.7, channel="ai_tech"),
    ]


@pytest.fixture()
def gen(mock_config, mock_llm_router):
    return TopicAngleGenerator(mock_config, llm_router=mock_llm_router)


# ---------------------------------------------------------------------------
# ScoredAngle Tests
# ---------------------------------------------------------------------------

class TestScoredAngle:
    def test_creation(self):
        angle = ScoredAngle(
            topic="AI 야근 역설",
            angle="역설적 결과",
            title="AI 도입했더니 야근이 늘어난 이유",
            hook_pattern="cognitive_dissonance",
            viral_score=9.2,
            source_keyword="AI 도입",
            channel="ai_tech",
        )
        assert angle.viral_score == 9.2
        assert angle.hook_pattern == "cognitive_dissonance"
        assert angle.title_variants == []  # default


# ---------------------------------------------------------------------------
# Channel Config Tests
# ---------------------------------------------------------------------------

class TestChannelConfigs:
    @pytest.mark.parametrize("ch", ["ai_tech", "psychology", "history", "space", "health"])
    def test_all_channels_have_hook_examples(self, ch):
        assert ch in _CHANNEL_HOOK_EXAMPLES
        assert len(_CHANNEL_HOOK_EXAMPLES[ch]) >= 3

    @pytest.mark.parametrize("ch", ["ai_tech", "psychology", "history", "space", "health"])
    def test_all_channels_have_forbidden_terms(self, ch):
        assert ch in _CHANNEL_FORBIDDEN
        assert len(_CHANNEL_FORBIDDEN[ch]) > 5

    def test_ai_tech_examples_use_cognitive_dissonance_pattern(self):
        examples = _CHANNEL_HOOK_EXAMPLES["ai_tech"]
        # 인지 부조화 패턴: "이유" 또는 반전 결과 포함
        assert any("이유" in ex for ex in examples)


# ---------------------------------------------------------------------------
# Prompt Building Tests
# ---------------------------------------------------------------------------

class TestPromptBuilding:
    def test_build_system_prompt_includes_examples(self, gen):
        prompt = gen._build_system_prompt("ai_tech")
        for ex in _CHANNEL_HOOK_EXAMPLES["ai_tech"][:2]:
            assert ex in prompt

    def test_build_system_prompt_includes_forbidden(self, gen):
        prompt = gen._build_system_prompt("ai_tech")
        assert _CHANNEL_FORBIDDEN["ai_tech"] in prompt

    def test_build_user_prompt_lists_candidates(self, sample_candidates):
        prompt = TopicAngleGenerator._build_user_prompt(sample_candidates, "ai_tech", n=3)
        assert "AI 도입 야근" in prompt
        assert "Claude UX" in prompt
        assert "바이브코딩 격차" in prompt

    def test_build_user_prompt_includes_channel_name(self, sample_candidates):
        prompt = TopicAngleGenerator._build_user_prompt(sample_candidates, "ai_tech", n=3)
        assert "퓨처 시냅스" in prompt


# ---------------------------------------------------------------------------
# Parsing Tests
# ---------------------------------------------------------------------------

class TestParseAngles:
    def test_parse_valid_response(self, gen):
        raw = {
            "angles": [
                {
                    "topic": "AI 야근",
                    "angle": "역설",
                    "title": "AI 도입했더니 오히려 야근이 늘어난 이유",
                    "title_variants": ["후보1", "후보2"],
                    "hook_pattern": "cognitive_dissonance",
                    "viral_score": 9.0,
                    "source_keyword": "AI",
                }
            ]
        }
        angles = gen._parse_angles(raw, "ai_tech")
        assert len(angles) == 1
        assert angles[0].viral_score == 9.0

    def test_parse_score_clamped_to_0_10(self, gen):
        raw = {
            "angles": [
                {
                    "topic": "테스트",
                    "title": "제목",
                    "viral_score": 99.9,  # 범위 초과
                    "hook_pattern": "cognitive_dissonance",
                    "source_keyword": "테스트",
                }
            ]
        }
        angles = gen._parse_angles(raw, "ai_tech")
        assert angles[0].viral_score == 10.0

    def test_parse_negative_score_clamped(self, gen):
        raw = {
            "angles": [
                {
                    "topic": "테스트",
                    "title": "제목",
                    "viral_score": -5.0,
                    "hook_pattern": "cognitive_dissonance",
                    "source_keyword": "테스트",
                }
            ]
        }
        angles = gen._parse_angles(raw, "ai_tech")
        assert angles[0].viral_score == 0.0

    def test_parse_missing_topic_skipped(self, gen):
        raw = {
            "angles": [
                {"title": "제목만 있음", "viral_score": 5.0, "hook_pattern": "cognitive_dissonance", "source_keyword": "x"},
            ]
        }
        angles = gen._parse_angles(raw, "ai_tech")
        assert angles == []

    def test_parse_non_dict_response(self, gen):
        angles = gen._parse_angles("not a dict", "ai_tech")  # type: ignore
        assert angles == []

    def test_parse_empty_angles_list(self, gen):
        angles = gen._parse_angles({"angles": []}, "ai_tech")
        assert angles == []


# ---------------------------------------------------------------------------
# Fallback Tests
# ---------------------------------------------------------------------------

class TestFallbackAngles:
    def test_fallback_creates_angle_per_candidate(self, sample_candidates):
        angles = TopicAngleGenerator._fallback_angles(sample_candidates, "ai_tech")
        assert len(angles) == len(sample_candidates)

    def test_fallback_all_cognitive_dissonance(self, sample_candidates):
        angles = TopicAngleGenerator._fallback_angles(sample_candidates, "ai_tech")
        assert all(a.hook_pattern == "cognitive_dissonance" for a in angles)

    def test_fallback_title_uses_keyword(self, sample_candidates):
        angles = TopicAngleGenerator._fallback_angles(sample_candidates, "ai_tech")
        assert "AI 도입 야근" in angles[0].title or "AI 도입 야근" in angles[0].topic

    def test_fallback_score_derived_from_trend_score(self, sample_candidates):
        angles = TopicAngleGenerator._fallback_angles(sample_candidates, "ai_tech")
        for angle, candidate in zip(angles, sample_candidates):
            expected = candidate.score * 6.0
            assert angle.viral_score == pytest.approx(expected)


# ---------------------------------------------------------------------------
# run() Integration Tests
# ---------------------------------------------------------------------------

class TestRun:
    def test_run_returns_angles(self, gen, sample_candidates):
        angles = gen.run(sample_candidates, "ai_tech", n=5)
        assert len(angles) >= 1
        assert all(isinstance(a, ScoredAngle) for a in angles)

    def test_run_sorted_by_viral_score(self, gen, sample_candidates):
        angles = gen.run(sample_candidates, "ai_tech", n=5)
        scores = [a.viral_score for a in angles]
        assert scores == sorted(scores, reverse=True)

    def test_run_limits_to_n(self, gen, sample_candidates):
        angles = gen.run(sample_candidates, "ai_tech", n=1)
        assert len(angles) <= 1

    def test_run_empty_candidates_returns_empty(self, gen):
        result = gen.run([], "ai_tech", n=5)
        assert result == []

    def test_run_llm_error_uses_fallback(self, mock_config, mock_llm_router, sample_candidates):
        mock_llm_router.generate_json.side_effect = RuntimeError("LLM down")
        gen = TopicAngleGenerator(mock_config, llm_router=mock_llm_router)
        angles = gen.run(sample_candidates, "ai_tech", n=3)
        # fallback이 실행되어 결과가 있어야 함
        assert len(angles) > 0
        assert all(a.hook_pattern == "cognitive_dissonance" for a in angles)

    def test_run_single(self, gen):
        angle = gen.run_single("바이브코딩 격차", "ai_tech")
        assert angle is not None
        assert isinstance(angle, ScoredAngle)

    def test_run_single_empty_returns_none(self, mock_config, mock_llm_router):
        mock_llm_router.generate_json.return_value = {"angles": []}
        gen = TopicAngleGenerator(mock_config, llm_router=mock_llm_router)
        result = gen.run_single("테스트", "ai_tech")
        assert result is None

    def test_run_batches_max_10_candidates(self, mock_config, mock_llm_router):
        """후보가 10개를 초과해도 LLM은 1번만 호출되어야 한다."""
        many = [
            TrendCandidate(keyword=f"주제{i}", source="llm_brainstorm", score=0.5, channel="ai_tech")
            for i in range(15)
        ]
        gen = TopicAngleGenerator(mock_config, llm_router=mock_llm_router)
        gen.run(many, "ai_tech", n=5)
        # LLM은 정확히 1번만 호출되어야 함
        assert mock_llm_router.generate_json.call_count == 1
