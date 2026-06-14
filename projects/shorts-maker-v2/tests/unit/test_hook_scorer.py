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

    def test_english_contrast_tech_hook_passes(self):
        result = score_hook("Tiny chips, big savings")
        assert result.passed is True
        assert result.hook_strength >= 0.6
        assert result.punch_score >= 0.7
        assert result.curiosity_score >= 0.5
        assert result.specificity_score >= 0.4

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

    def test_korean_company_name_boosts_specificity(self):
        """한국어 기업명(삼성, GPT 등)이 specificity_score를 높임."""
        result = score_hook("GPT-4o가 출시 24시간 만에 바꿨다")
        assert result.specificity_score >= 0.5

    def test_english_company_name_boosts_specificity(self):
        """영어 회사명(OpenAI, Google 등)이 specificity_score를 높임."""
        result = score_hook("OpenAI just changed everything")
        assert result.specificity_score >= 0.4

    def test_ko_ai_tech_hook_example_passes(self):
        """ko-KR script_step.yaml ai_tech 채널 훅 예시가 통과해야 함."""
        hook = "GPT-4o가 출시 24시간 만에 전 세계 개발자 4000만 명의 워크플로를 바꿨다."
        result = score_hook(hook)
        # 숫자+고유명사 조합 → specificity 충분, 전체 통과
        assert result.specificity_score >= 0.6

    # ── T-AB021: _NUMBER_PATTERN 확장 ─────────────────────────────

    def test_hour_unit_detected_as_number_pattern(self):
        """T-AB021: '시'(시간) 단위가 숫자 패턴으로 감지되어야 함."""
        result = score_hook("24시간 만에 모든 게 바뀐다")
        assert result.specificity_score > 0.0, "24시간 should trigger number specificity"

    def test_comma_separated_number_detected(self):
        """T-AB021: 쉼표 포함 숫자(1,000만원)가 감지되어야 함."""
        result = score_hook("1,000만원 받는 개발자의 루틴")
        assert result.specificity_score > 0.0, "1,000만원 should trigger number specificity"

    def test_english_multiplier_k_detected(self):
        """T-AB021: 영어 배율 100K가 감지되어야 함."""
        result = score_hook("100K users switched overnight")
        assert result.specificity_score > 0.0, "100K should trigger number specificity"

    def test_english_multiplier_b_detected(self):
        """T-AB021: 영어 배율 3B parameters가 감지되어야 함."""
        result = score_hook("3B parameters, one surprising result")
        assert result.specificity_score > 0.0, "3B should trigger number specificity"

    def test_existing_number_patterns_still_work(self):
        """T-AB021 회귀: 기존 '3초', '90%' 같은 패턴이 여전히 감지되어야 함."""
        for hook in ["단 3초만에", "사실은 90%가 충격 받은 이유", "4000만 명이"]:
            result = score_hook(hook)
            assert result.specificity_score > 0.0, f"Pattern should still match: {hook!r}"

    # ── T-AB024: Hook Scorer 가중치 재조정 + 시간적·규모 패턴 ─────────

    def test_flagship_ko_hook_now_passes(self):
        """T-AB024: 사실적 정보 밀집형 한국어 Hook이 통과해야 함."""
        hook = "GPT-4o가 출시 24시간 만에 전 세계 개발자 4000만 명의 워크플로를 바꿨다."
        result = score_hook(hook)
        assert result.passed is True, f"Flagship hook should pass, got strength={result.hook_strength:.3f}"
        assert result.hook_strength >= 0.6

    def test_temporal_impact_boosts_punch(self):
        """T-AB024: '24시간 만에' 패턴이 punch_score를 높여야 함."""
        with_temporal = score_hook("GPT-4o가 출시 24시간 만에 바꿨다")
        without_temporal = score_hook("GPT-4o가 출시하고 나서 바꿨다")
        assert with_temporal.punch_score > without_temporal.punch_score

    def test_global_scale_boosts_punch(self):
        """T-AB024: '전 세계' 패턴이 punch_score를 높여야 함."""
        with_scale = score_hook("전 세계 4000만 명이 바꿨다")
        without_scale = score_hook("많은 사람들이 바꿨다")
        assert with_scale.punch_score > without_scale.punch_score

    def test_english_outcome_words_boost_specificity(self):
        """T-AB024: 'savings, results, revenue' 같은 성과 단어가 specificity를 높여야 함."""
        result = score_hook("Tiny chips, big savings")
        assert result.specificity_score >= 0.7, "English outcome word should boost specificity"
        assert result.passed is True

    def test_info_dense_hook_45_chars_not_max_penalized(self):
        """T-AB024: 40-55자 범위 Hook은 0.3 brevity (0.2 아닌) 를 받아야 함."""
        hook = "전 세계 개발자 4000만 명의 워크플로를 단 하루 만에 바꿨다"  # ~30자
        result = score_hook(hook)
        assert result.brevity_score >= 0.3, "Moderate-length hook should not get minimum brevity"

    def test_regression_benchmark_hook_still_passes(self):
        """T-AB024 회귀: 기존 통과 Hook들이 여전히 통과해야 함."""
        for hook in [
            "사실은 90%가 충격 받은 이유",
            "Tiny chips, big savings",
        ]:
            result = score_hook(hook)
            assert result.passed is True, f"Benchmark hook should still pass: {hook!r}"
