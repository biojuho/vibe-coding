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
