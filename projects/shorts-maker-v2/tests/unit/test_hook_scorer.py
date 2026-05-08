"""Tests for hook_scorer module."""

from __future__ import annotations

from shorts_maker_v2.pipeline.hook_scorer import HookScore, score_hook


class TestScoreHook:
    """Hook Strength Scorer 단위 테스트."""

    def test_short_question_hook_high_brevity(self):
        """짧은 질문형 Hook은 brevity+punch 점수가 높지만 단독으론 통과 미달."""
        result = score_hook("이거 진짜일까?")
        assert result.brevity_score >= 0.9
        assert result.punch_score > 0.0
        # 질문만으로는 curiosity/specificity 부족 → 0.6 미만 가능
        assert result.hook_strength > 0.3

    def test_long_hook_low_brevity(self):
        """50자 이상 긴 Hook은 brevity 낮음."""
        long_text = (
            "이것은 매우 매우 긴 Hook 나레이션으로 스크롤을 멈추기에는 너무 길고 집중력을 잃게 만드는 텍스트입니다"
        )
        result = score_hook(long_text)
        assert result.brevity_score <= 0.4
        assert len(result.feedback) > 0

    def test_shock_words_boost_punch(self):
        """충격 단어가 punch_score를 높임."""
        result = score_hook("충격 반전!")
        assert result.punch_score >= 0.3

    def test_number_pattern_specificity(self):
        """숫자 패턴이 specificity_score를 높임."""
        result = score_hook("단 3초만에")
        assert result.specificity_score > 0.0

    def test_curiosity_gap_pattern(self):
        """호기심 갭 패턴 감지."""
        result = score_hook("알고 보니 이유가")
        assert result.curiosity_score > 0.0

    def test_empty_hook_low_score(self):
        """빈 Hook은 낮은 점수."""
        result = score_hook("")
        assert result.hook_strength < 0.6
        assert result.passed is False

    def test_ideal_hook_high_score(self):
        """이상적인 Hook: 짧고, 질문형, 숫자, 호기심 갭 모두 포함."""
        # 모든 차원을 활성화하는 Hook: 질문+숫자+호기심갭+충격
        result = score_hook("사실은 90%가 충격 받은 이유")
        assert result.passed is True
        assert result.hook_strength >= 0.6

    def test_to_dict_structure(self):
        """to_dict() 출력 구조 확인."""
        result = score_hook("테스트")
        d = result.to_dict()
        assert "hook_strength" in d
        assert "passed" in d
        assert "feedback" in d
        assert isinstance(d["feedback"], list)

    def test_custom_threshold(self):
        """커스텀 threshold 적용 확인."""
        result = score_hook("안녕", threshold=0.99)
        assert result.passed is False
        result2 = score_hook("안녕", threshold=0.01)
        assert result2.passed is True

    def test_returns_hook_score_type(self):
        """반환 타입이 HookScore인지 확인."""
        result = score_hook("테스트 Hook")
        assert isinstance(result, HookScore)
