"""Unit tests for pipeline.draft_quality_gate — 미커버 헬퍼 & 엣지 케이스 집중.

타겟: pipeline/draft_quality_gate.py
기존 테스트(test_quality_gate_and_scenes.py)가 다루지 않는 핵심 로직:
  - _looks_like_error_text: LLM 에러 응답 감지
  - _has_scene_anchor: 구체 장면/대사/숫자 탐지
  - _has_cliche_opening: 해설형 상투 오프닝 감지
  - _has_generic_cta: generic CTA 감지
  - strict_mode: 경고도 실패로 처리
  - validate_all + format_summary: 멀티 플랫폼 일괄 검증 & 리포트 생성
  - 경계값 테스트: 정확히 min_len/max_len 경계
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from pipeline.draft_quality_gate import (
    DraftQualityGate,
    QualityResult,
    _has_cliche_opening,
    _has_generic_cta,
    _has_scene_anchor,
    _looks_like_error_text,
)


# ── _looks_like_error_text 테스트 ────────────────────────────────────────


class TestLooksLikeErrorText:
    """LLM 에러/SDK 에러 응답 감지."""

    @pytest.mark.parametrize(
        "text",
        [
            "Error generating drafts: rate limit exceeded",
            "Too Many Requests (429)",
            "Traceback (most recent call last):",
            "AttributeError: 'NoneType' object has no attribute 'text'",
            "asyncopenai.APIError: server error",
            "SDK error: invalid API key",
            "Gemini API Error: RESOURCE_EXHAUSTED",
            "Service Unavailable",
        ],
    )
    def test_detects_error_responses(self, text):
        assert _looks_like_error_text(text) is True

    @pytest.mark.parametrize(
        "text",
        [
            "블라인드에서 화제가 된 연봉 이야기를 공유합니다",
            "🔥 실화? 5년차에 연봉 1억 달성했다는 후기",
            "요즘 회사 분위기가 좋아요",
            "",
        ],
    )
    def test_normal_text_not_flagged(self, text):
        assert _looks_like_error_text(text) is False

    def test_none_input_safe(self):
        """None이 들어와도 크래시 없이 False."""
        assert _looks_like_error_text(None) is False


# ── _has_scene_anchor 테스트 ─────────────────────────────────────────────


class TestHasSceneAnchor:
    """첫 문장에 구체 장면(숫자, 인용, 직장 키워드)이 있는지 검사."""

    def test_number_anchor(self):
        assert _has_scene_anchor("연봉 8000만원 받는 5년차 개발자가 말하길") is True

    def test_quote_anchor(self):
        assert _has_scene_anchor('"이거 실화냐"라고 동료가 먼저 물었다') is True

    def test_workplace_keyword_anchor(self):
        assert _has_scene_anchor("회의실에서 부장님이 갑자기 말했다") is True

    def test_dialogue_marker_anchor(self):
        assert _has_scene_anchor("내가 그렇게 했더니 팀장이 화를 냈다") is True

    def test_vague_opening_no_anchor(self):
        assert _has_scene_anchor("직장 생활에서 중요한 것은 소통입니다") is False

    def test_empty_string(self):
        assert _has_scene_anchor("") is False


# ── _has_cliche_opening 테스트 ───────────────────────────────────────────


class TestHasClicheOpening:
    """해설형 상투적 오프닝 감지."""

    @pytest.mark.parametrize(
        "text",
        [
            "오늘은 연봉에 대해 이야기해보겠습니다. 많은 분들이 궁금하시죠.",
            "많은 직장인들이 고민하고 있는 주제입니다",
            "현실적으로 봤을 때 이 문제는 심각합니다",
            "결론적으로 말씀드리겠습니다",
            "요즘 사람들이 가장 관심 있는 연봉 이야기",
            "한번 생각해봅시다. 연봉이란 무엇인가",
        ],
    )
    def test_detects_cliche_openings(self, text):
        assert _has_cliche_opening(text) is True

    @pytest.mark.parametrize(
        "text",
        [
            '"야 이거 실화냐?" 옆자리 동료가 화면을 가리켰다',
            "연봉 8000만원 받는 5년차 개발자의 퇴사 이유",
            "회의실 문을 열자마자 전원 침묵이었다",
        ],
    )
    def test_specific_openings_not_flagged(self, text):
        assert _has_cliche_opening(text) is False


# ── _has_generic_cta 테스트 ──────────────────────────────────────────────


class TestHasGenericCTA:
    """상투적 CTA(여러분 생각은?) 감지."""

    @pytest.mark.parametrize(
        "text",
        [
            "여러분 생각은 어떠신가요?",
            "여러분도 그렇게 생각하시나요",
            "공감하시나요?",
            "어떻게 생각하시나요?",
            "여러분은 어떻게 생각하세요?",
        ],
    )
    def test_detects_generic_cta(self, text):
        assert _has_generic_cta(text) is True

    @pytest.mark.parametrize(
        "text",
        [
            "돈 아끼는 방법 공유하려고 합니다",
            "이직하고 싶은 마음이 들 때 어떡하시나요",
            "다음 글에서 후기 공유할게요",
        ],
    )
    def test_specific_cta_not_flagged(self, text):
        assert _has_generic_cta(text) is False


# ── DraftQualityGate 통합 테스트 (미커버 분기) ───────────────────────────


class TestDraftQualityGateEdgeCases:
    """기존 테스트에서 누락된 경계값 & 분기 테스트."""

    @pytest.fixture
    def gate(self):
        return DraftQualityGate()

    @pytest.fixture
    def strict_gate(self):
        return DraftQualityGate(strict_mode=True)

    # ── 빈 초안 / 에러 응답 ──────────────────────────────────────────

    def test_empty_draft_fails(self, gate):
        result = gate.validate("twitter", "")
        assert result.passed is False
        assert result.should_retry is True
        assert any(i.rule == "초안 존재" for i in result.items)

    def test_whitespace_only_draft_fails(self, gate):
        result = gate.validate("twitter", "   \n\t  ")
        assert result.passed is False

    def test_error_text_detected(self, gate):
        result = gate.validate("twitter", "Error generating drafts: rate limit exceeded. Try again later.")
        assert result.passed is False
        assert any(i.rule == "에러 응답" for i in result.items)

    # ── 글자 수 경계값 ───────────────────────────────────────────────

    @patch("pipeline.draft_quality_gate._load_cliche_watchlist", return_value=[])
    def test_twitter_exact_min_len(self, mock_cliche):
        """정확히 60자 → 통과."""
        gate = DraftQualityGate()
        # 60자 한글 텍스트 (CTA + 훅 포함)
        text = '"8000만원" 받았다는 5년차 개발자 실화? 옆에서 보니까 진짜 헐 소름돋음'
        actual_len = len(text.strip())
        if actual_len < 60:
            text += "가" * (60 - actual_len)
        result = gate.validate("twitter", text[:280])
        # 최소 글자 수 위반은 없어야 함
        assert not any(i.rule == "최소 글자 수" and not i.passed for i in result.items)

    @patch("pipeline.draft_quality_gate._load_cliche_watchlist", return_value=[])
    def test_twitter_exceeds_max_len_280(self, mock_cliche):
        """281자 → 최대 글자 수 위반."""
        gate = DraftQualityGate()
        text = "가" * 281
        result = gate.validate("twitter", text)
        assert any(i.rule == "최대 글자 수" and not i.passed for i in result.items)

    # ── 한글 비율 경계 ───────────────────────────────────────────────

    @patch("pipeline.draft_quality_gate._load_cliche_watchlist", return_value=[])
    def test_mostly_english_low_korean_ratio(self, mock_cliche):
        """영어 위주 텍스트 → 한글 비율 경고."""  # [QA 수정] Q3 vacuous truth 제거
        gate = DraftQualityGate()
        text = "The quick brown fox jumps over the lazy dog. " * 3 + "실화?"
        result = gate.validate("twitter", text)
        kr_items = [i for i in result.items if "한글 비율" in i.rule]
        assert len(kr_items) > 0, "한글 비율 검사 항목이 존재해야 합니다"
        assert kr_items[0].passed is False

    # ── strict_mode 테스트 ───────────────────────────────────────────

    @patch("pipeline.draft_quality_gate._load_cliche_watchlist", return_value=[])
    def test_strict_mode_warning_becomes_failure(self, mock_cliche):
        """strict_mode에서는 경고도 실패 처리."""  # [QA 수정] Q2 vacuous truth 제거
        strict_gate = DraftQualityGate(strict_mode=True)
        # CTA 없는 twitter 초안 (warning 발생) — 하지만 장면 훅은 포함
        # NOTE: "생각"은 CTA 패턴에 매치되므로 CTA 미포함 텍스트를 사용
        text = '"실수령 600만원" 받는 3년차 개발자가 말하길. 이것저것 뒤죽박죽이었다고 한다. 참 세상 어렵다.'
        if len(text) < 60:
            text += "가" * (60 - len(text))
        result = strict_gate.validate("twitter", text)
        # 경고 항목이 반드시 존재해야 함 (vacuous truth 방지)
        has_warning_fail = any(not i.passed and i.severity == "warning" for i in result.items)
        assert has_warning_fail, "strict_mode 검증을 위해 warning 실패 항목이 반드시 있어야 합니다"
        assert result.passed is False
        assert result.should_retry is True

    # ── 금지 패턴 (twitter에서 URL) ──────────────────────────────────

    @patch("pipeline.draft_quality_gate._load_cliche_watchlist", return_value=[])
    def test_twitter_url_forbidden(self, mock_cliche):
        """twitter 초안에 URL이 포함되면 경고."""
        gate = DraftQualityGate()
        text = '"실화?" 3년차 연봉 8000만원 후기 https://blind.com/post/123 여기서 봄'
        result = gate.validate("twitter", text)
        forbidden_items = [i for i in result.items if i.rule == "금지 패턴"]
        assert len(forbidden_items) > 0
        assert forbidden_items[0].passed is False

    # ── 알 수 없는 플랫폼 ────────────────────────────────────────────

    def test_unknown_platform_passes(self, gate):
        """등록되지 않은 플랫폼은 규칙이 없으므로 통과."""
        result = gate.validate("tiktok", "짧은 텍스트")
        assert result.passed is True
        assert any(i.rule == "규칙 존재" for i in result.items)

    # ── custom_rules 오버라이드 ──────────────────────────────────────

    @patch("pipeline.draft_quality_gate._load_cliche_watchlist", return_value=[])
    def test_custom_rules_override(self, mock_cliche):
        """custom_rules로 기존 규칙 오버라이드."""
        gate = DraftQualityGate(custom_rules={"twitter": {"max_len": 100}})
        text = "가" * 101  # 기본 280자 → 100자로 낮아졌으니 위반
        result = gate.validate("twitter", text)
        assert any(i.rule == "최대 글자 수" and not i.passed for i in result.items)

    @patch("pipeline.draft_quality_gate._load_cliche_watchlist", return_value=[])
    def test_custom_new_platform(self, mock_cliche):
        """새 플랫폼을 custom_rules로 추가."""
        gate = DraftQualityGate(custom_rules={"tiktok": {"min_len": 10, "max_len": 50}})
        result = gate.validate("tiktok", "짧은 글 실화냐 5초 전 작성")
        assert not any(i.rule == "규칙 존재" for i in result.items)


# ── validate_all + format_summary 테스트 ─────────────────────────────────


class TestValidateAllAndFormatSummary:
    """멀티 플랫폼 일괄 검증 & 리포트 생성."""

    @patch("pipeline.draft_quality_gate._load_cliche_watchlist", return_value=[])
    def test_validate_all_filters_internal_keys(self, mock_cliche):
        """내부 메타 키(_로 시작)는 검증 대상에서 제외."""
        gate = DraftQualityGate()
        drafts = {
            "_provider": "deepseek",
            "_cost": "0.002",
            "twitter": '"실화? 연봉 8000" 관련 5년차 개발자 후기가 블라인드에서 대박이다! 소름돋는다 진짜 ㅋㅋ 어떤 사람들은 믿기 힘들다고',
        }
        results = gate.validate_all(drafts)
        assert "_provider" not in results
        assert "_cost" not in results
        assert "twitter" in results

    @patch("pipeline.draft_quality_gate._load_cliche_watchlist", return_value=[])
    def test_format_summary_contains_all_platforms(self, mock_cliche):
        """format_summary에 모든 플랫폼 결과가 포함."""
        gate = DraftQualityGate()
        results = {
            "twitter": QualityResult(platform="twitter", passed=True, score=90),
            "threads": QualityResult(platform="threads", passed=False, score=60, should_retry=True),
        }
        summary = gate.format_summary(results)
        assert "twitter" in summary
        assert "threads" in summary
        assert "재생성 권장" in summary

    @patch("pipeline.draft_quality_gate._load_cliche_watchlist", return_value=[])
    def test_format_summary_all_pass(self, mock_cliche):
        """전체 통과 시 '전체 플랫폼 품질 게이트 통과' 메시지."""
        gate = DraftQualityGate()
        results = {
            "twitter": QualityResult(platform="twitter", passed=True, score=100),
        }
        summary = gate.format_summary(results)
        assert "전체 플랫폼 품질 게이트 통과" in summary


# ── QualityResult.add 점수 계산 테스트 ───────────────────────────────────


class TestQualityResultScoring:
    """점수 감점 및 should_retry 플래그 로직."""

    def test_error_deducts_25_and_sets_retry(self):
        r = QualityResult(platform="test")
        r.add("테스트", False, "에러 발생", "error")
        assert r.score == 75
        assert r.should_retry is True
        assert r.passed is False

    def test_warning_deducts_10_no_retry(self):
        r = QualityResult(platform="test")
        r.add("테스트", False, "경고 발생", "warning")
        assert r.score == 90
        assert r.should_retry is False
        assert r.passed is True  # 경고는 통과

    def test_multiple_errors_clamp_at_zero(self):
        r = QualityResult(platform="test")
        for i in range(10):
            r.add(f"에러{i}", False, "", "error")
        assert r.score == 0  # max(0, ...) 클램핑
        assert r.should_retry is True

    def test_info_no_penalty(self):
        r = QualityResult(platform="test")
        r.add("정보", True, "참고", "info")
        assert r.score == 100
        assert r.passed is True

    def test_to_dict_serialization(self):
        """to_dict 직렬화 검증."""
        r = QualityResult(platform="twitter", passed=True, score=85)
        r.add("글자 수", True, "150자", "info")
        r.add("CTA 포함", False, "CTA 없음", "warning")

        d = r.to_dict()
        assert d["platform"] == "twitter"
        assert d["score"] == 75  # 초기 85 - warning 감점 10 = 75
        assert len(d["items"]) == 2
        assert d["items"][1]["rule"] == "CTA 포함"

    def test_summary_format(self):
        """summary() 한 줄 요약 형식."""
        r = QualityResult(platform="twitter", passed=True, score=90)
        s = r.summary()
        assert "✅" in s
        assert "twitter" in s
        assert "90" in s

        r2 = QualityResult(platform="threads", passed=False, score=50)
        r2.add("에러", False, "", "error")
        s2 = r2.summary()
        assert "❌" in s2
        assert "1 issues" in s2
