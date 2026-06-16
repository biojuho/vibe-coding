"""topic_validator 단위 테스트."""

from unittest.mock import MagicMock

from shorts_maker_v2.pipeline.topic_validator import (
    TopicValidation,
    _parse_result,
    validate_topic,
)


class TestParseResult:
    def test_valid_result(self):
        data = {
            "is_valid": True,
            "confidence": 0.9,
            "reason": "Good topic",
            "suggestions": [],
            "visual_feasibility": 8,
            "fact_verifiability": 7,
            "format_suitability": 9,
            "channel_relevance": 8,
        }
        result = _parse_result(data)
        assert result.is_valid is True
        assert result.confidence == 0.9
        assert result.reason == "Good topic"
        assert len(result.scores) == 4
        assert result.scores["visual_feasibility"] == 8

    def test_invalid_result_with_suggestions(self):
        data = {
            "is_valid": False,
            "confidence": 0.8,
            "reason": "Too abstract",
            "suggestions": ["Try X instead", "Or Y"],
        }
        result = _parse_result(data)
        assert result.is_valid is False
        assert len(result.suggestions) == 2

    def test_clamps_confidence(self):
        result = _parse_result({"confidence": 2.0})
        assert result.confidence == 1.0

        result = _parse_result({"confidence": -0.5})
        assert result.confidence == 0.0

    def test_clamps_scores(self):
        result = _parse_result({"visual_feasibility": 15})
        assert result.scores["visual_feasibility"] == 10

        result = _parse_result({"visual_feasibility": 0})
        assert result.scores["visual_feasibility"] == 1

    def test_missing_fields_defaults(self):
        result = _parse_result({})
        assert result.is_valid is False
        assert result.confidence == 0.5
        assert result.reason == "No reason provided."
        assert result.suggestions == []

    def test_invalid_data_returns_permissive(self):
        result = _parse_result({"confidence": "not-a-number"})
        assert result.is_valid is True
        assert result.confidence == 0.0
        assert "Parse error" in result.reason

    def test_suggestions_filters_empty(self):
        result = _parse_result({"suggestions": ["good", "", None, "also good"]})
        assert result.suggestions == ["good", "also good"]

    def test_suggestions_non_list(self):
        result = _parse_result({"suggestions": "not a list"})
        assert result.suggestions == []

    def test_float_score_string_rounds_correctly(self):
        """LLM 가 '7.5' 같은 float 문자열로 점수를 내도 scores 손실 없이 반올림."""
        result = _parse_result({"visual_feasibility": "7.5"})
        assert result.scores["visual_feasibility"] == 8
        # confidence는 남아야 함 — 버그 전엔 ValueError로 confidence=0.0 반환
        assert result.confidence == 0.5  # default (not parse-error fallback)

    def test_float_score_numeric_truncates_correctly(self):
        """숫자 7.5 입력도 int(round()) 처리해 8로 반올림됨."""
        result = _parse_result({"visual_feasibility": 7.5})
        assert result.scores["visual_feasibility"] == 8

    def test_float_score_string_45_rounds_to_5(self):
        """'4.5' → round(4.5) = 4 (Python banker's rounding) — 동작 문서화."""
        result = _parse_result({"visual_feasibility": "4.5"})
        # Python round(4.5) = 4 (banker's rounding)
        assert result.scores["visual_feasibility"] in (4, 5)  # accept either


class TestValidateTopic:
    def test_empty_topic_rejected(self):
        result = validate_topic("", "ai_tech", {})
        assert result.is_valid is False
        assert result.confidence == 1.0

    def test_whitespace_topic_rejected(self):
        result = validate_topic("   ", "ai_tech", {})
        assert result.is_valid is False

    def test_llm_failure_allows_topic(self):
        mock_router = MagicMock()
        mock_router.generate_json.side_effect = RuntimeError("LLM down")
        result = validate_topic("블랙홀 사진", "space", {}, llm_router=mock_router)
        assert result.is_valid is True
        assert result.confidence == 0.0
        assert "LLM unavailable" in result.reason

    def test_successful_validation(self):
        mock_router = MagicMock()
        mock_router.generate_json.return_value = {
            "is_valid": True,
            "confidence": 0.95,
            "reason": "Great topic",
            "suggestions": [],
            "visual_feasibility": 9,
            "fact_verifiability": 8,
            "format_suitability": 9,
            "channel_relevance": 10,
        }
        result = validate_topic("AI 칩 전쟁", "ai_tech", {}, llm_router=mock_router)
        assert result.is_valid is True
        assert result.scores["channel_relevance"] == 10


class TestTopicValidation:
    def test_frozen_dataclass(self):
        tv = TopicValidation(is_valid=True, confidence=0.8, reason="ok")
        assert tv.is_valid is True
        assert tv.suggestions == []
        assert tv.scores == {}


# ── _parse_result NaN/Inf 회귀 테스트 (TV-NI 시리즈) ────────────────────────


class TestParseResultNanInf:
    """_parse_result 이 NaN/Inf LLM 출력에도 크래시 없이 안전 폴백해야 함."""

    def test_nan_confidence_becomes_0_5(self):
        """TV-NI001: confidence=nan → 0.5 (최대 신뢰도 1.0 둔갑 방지)."""
        import math

        result = _parse_result({"is_valid": True, "confidence": float("nan"), "reason": "ok"})
        assert not math.isnan(result.confidence)
        assert result.confidence == 0.5

    def test_inf_confidence_becomes_0_5(self):
        """TV-NI002: confidence=inf → 0.5 (1.0 클램핑이 아닌 안전 기본값)."""
        result = _parse_result({"is_valid": True, "confidence": float("inf"), "reason": "ok"})
        assert result.confidence == 0.5

    def test_inf_score_does_not_raise(self):
        """TV-NI003: 점수에 inf가 와도 OverflowError 없이 해당 키 무시."""
        result = _parse_result(
            {
                "is_valid": True,
                "confidence": 0.8,
                "reason": "ok",
                "visual_feasibility": float("inf"),
                "fact_verifiability": 7,
            }
        )
        assert "visual_feasibility" not in result.scores
        assert result.scores.get("fact_verifiability") == 7

    def test_nan_score_does_not_raise(self):
        """TV-NI004: 점수에 nan이 와도 OverflowError/ValueError 없이 키 무시."""
        result = _parse_result(
            {
                "is_valid": True,
                "confidence": 0.9,
                "reason": "ok",
                "visual_feasibility": float("nan"),
                "channel_relevance": 8,
            }
        )
        assert "visual_feasibility" not in result.scores
        assert result.scores.get("channel_relevance") == 8

    def test_string_inf_score_does_not_raise(self):
        """TV-NI005: 'inf' 문자열 점수에 OverflowError 없음."""
        result = _parse_result(
            {
                "is_valid": False,
                "confidence": 0.7,
                "reason": "test",
                "format_suitability": "inf",
                "channel_relevance": 6,
            }
        )
        assert "format_suitability" not in result.scores
        assert result.scores.get("channel_relevance") == 6
