"""Tests for content_intelligence.py defensive fixes — YAML 타입 검증 + None 입력 방어.

커버하는 취약점:
  1. _yaml_rules_to_tuples(): YAML 엔트리가 dict 가 아닌 경우(str/int/None) AttributeError 크래시
  2. evaluate_candidate_editorial_fit(): title/content 가 None 일 때 "None\\nNone" 텍스트 오염
  3. _extract_empathy_anchor(): 빈 문자열 / None 입력 시 방어
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.content_intelligence import (
    _yaml_rules_to_tuples,
    _extract_empathy_anchor,
    evaluate_candidate_editorial_fit,
    classify_topic_cluster,
    classify_emotion_axis,
    classify_audience_fit,
)


# ═══════════════════════════════════════════════════════════════════════════
# 1. _yaml_rules_to_tuples: non-dict YAML 엔트리 방어
# ═══════════════════════════════════════════════════════════════════════════


class TestYamlRulesToTuplesDefensive:
    """YAML 규칙 파일이 오염되었을 때 안전하게 fallback 하는지 검증."""

    FALLBACK = [("테스트", ("키워드",))]

    def test_non_dict_entries_are_skipped(self):
        """YAML에 str/int/None 엔트리가 섞여있으면 건너뛰고 유효 엔트리만 반환."""
        malformed_rules = {
            "test_rules": [
                "just_a_string",  # str → 건너뜀
                42,  # int → 건너뜀
                None,  # None → 건너뜀
                {"label": "연봉", "keywords": ["연봉", "월급"]},  # 유효
            ]
        }
        with patch("pipeline.content_intelligence.rules._load_rules", return_value=malformed_rules):
            result = _yaml_rules_to_tuples("test_rules", self.FALLBACK)

        assert len(result) == 1
        assert result[0][0] == "연봉"
        assert "연봉" in result[0][1]

    def test_all_non_dict_entries_returns_fallback(self):
        """모든 엔트리가 non-dict 이면 fallback 반환."""
        malformed_rules = {"test_rules": ["string1", "string2", 123]}
        with patch("pipeline.content_intelligence.rules._load_rules", return_value=malformed_rules):
            result = _yaml_rules_to_tuples("test_rules", self.FALLBACK)

        assert result == self.FALLBACK

    def test_rules_not_a_list_returns_fallback(self):
        """규칙 값이 list 가 아닌 dict 이면 fallback 반환."""
        malformed_rules = {"test_rules": {"not": "a list"}}
        with patch("pipeline.content_intelligence.rules._load_rules", return_value=malformed_rules):
            result = _yaml_rules_to_tuples("test_rules", self.FALLBACK)

        assert result == self.FALLBACK

    def test_missing_key_returns_fallback(self):
        """키가 없으면 fallback 반환."""
        with patch("pipeline.content_intelligence.rules._load_rules", return_value={}):
            result = _yaml_rules_to_tuples("nonexistent_key", self.FALLBACK)

        assert result == self.FALLBACK

    def test_entry_missing_label_is_skipped(self):
        """label 이 빈 문자열인 엔트리는 건너뜀."""
        rules = {"test_rules": [{"label": "", "keywords": ["kw"]}, {"label": "유효", "keywords": ["ok"]}]}
        with patch("pipeline.content_intelligence.rules._load_rules", return_value=rules):
            result = _yaml_rules_to_tuples("test_rules", self.FALLBACK)

        assert len(result) == 1
        assert result[0][0] == "유효"

    def test_entry_missing_keywords_is_skipped(self):
        """keywords 가 빈 리스트인 엔트리는 건너뜀."""
        rules = {"test_rules": [{"label": "라벨", "keywords": []}, {"label": "유효", "keywords": ["ok"]}]}
        with patch("pipeline.content_intelligence.rules._load_rules", return_value=rules):
            result = _yaml_rules_to_tuples("test_rules", self.FALLBACK)

        assert len(result) == 1
        assert result[0][0] == "유효"


# ═══════════════════════════════════════════════════════════════════════════
# 2. evaluate_candidate_editorial_fit: None 입력 방어
# ═══════════════════════════════════════════════════════════════════════════


class TestEvaluateCandidateNoneInputs:
    """title/content/source 가 None 일 때 크래시 없이 결과를 반환하는지 검증."""

    def test_none_title_does_not_crash(self):
        """title=None 이어도 정상 dict 반환."""
        result = evaluate_candidate_editorial_fit(title=None, content="직장인 공감 글")
        assert isinstance(result, dict)
        assert "topic_cluster" in result
        assert "score" in result
        # "None" 문자열이 텍스트에 포함되면 안 됨
        assert result.get("empathy_anchor", "") != "None"

    def test_none_content_does_not_crash(self):
        """content=None 이어도 정상 dict 반환."""
        result = evaluate_candidate_editorial_fit(title="테스트 제목", content=None)
        assert isinstance(result, dict)
        assert "score" in result

    def test_none_title_and_content_does_not_crash(self):
        """title=None, content=None 이어도 크래시 없음."""
        result = evaluate_candidate_editorial_fit(title=None, content=None)
        assert isinstance(result, dict)
        assert result["score"] >= 0
        # 빈 텍스트이므로 "기타" 토픽으로 분류되어야 함
        assert result["topic_cluster"] == "기타"

    def test_none_source_does_not_crash(self):
        """source=None 이어도 정상 동작."""
        result = evaluate_candidate_editorial_fit(title="연봉 인상", source=None, content="테스트")
        assert isinstance(result, dict)

    def test_integer_inputs_coerced_to_string(self):
        """정수가 title 에 들어와도 str 변환 후 동작."""
        result = evaluate_candidate_editorial_fit(title=12345, content=67890)
        assert isinstance(result, dict)
        assert "score" in result


# ═══════════════════════════════════════════════════════════════════════════
# 3. _extract_empathy_anchor: 엣지 케이스 방어
# ═══════════════════════════════════════════════════════════════════════════


class TestExtractEmpathyAnchorEdgeCases:
    """빈 문자열 및 특수 입력에 대한 방어."""

    def test_empty_strings(self):
        """빈 제목+본문이어도 빈 문자열 반환 (크래시 아님)."""
        result = _extract_empathy_anchor("", "")
        assert isinstance(result, str)

    def test_quote_extraction(self):
        """인용문이 있으면 추출."""
        result = _extract_empathy_anchor("제목", '"연봉 500은 받아야 사람 대접 받는다" 라는 댓글')
        assert "연봉 500" in result

    def test_number_extraction(self):
        """숫자가 있으면 주변 컨텍스트 추출."""
        result = _extract_empathy_anchor("연봉 5000만원 현실", "")
        assert "5000" in result

    def test_long_content_truncation(self):
        """매우 긴 입력도 80자 이내로 잘림."""
        long_text = "직장인 " * 100
        result = _extract_empathy_anchor("", long_text)
        assert len(result) <= 80


# ═══════════════════════════════════════════════════════════════════════════
# 4. classify 함수들: None 입력 방어
# ═══════════════════════════════════════════════════════════════════════════


class TestClassifyFunctionsNoneInputs:
    """분류 함수들이 None 입력에 안전한지 검증."""

    def test_classify_topic_cluster_none(self):
        result = classify_topic_cluster(None, None)
        assert isinstance(result, str)
        assert result == "기타"

    def test_classify_emotion_axis_none(self):
        result = classify_emotion_axis(None, None)
        assert isinstance(result, str)

    def test_classify_audience_fit_none(self):
        result = classify_audience_fit(None, None)
        assert isinstance(result, str)
        assert result == "범용"
