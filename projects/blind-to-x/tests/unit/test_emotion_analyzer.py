"""Tests for pipeline.emotion_analyzer — coverage uplift."""

from __future__ import annotations

from unittest.mock import patch, MagicMock


from pipeline.emotion_analyzer import (
    EmotionProfile,
    analyze_emotions,
    get_emotion_profile,
    _KOTE_TO_AXIS,
    _EMOTION_GROUPS,
)


# ── EmotionProfile dataclass ─────────────────────────────────────


class TestEmotionProfile:
    def test_default_values(self):
        p = EmotionProfile()
        assert p.top_emotions == []
        assert p.emotion_axis == "공감"
        assert p.dominant_group == ""
        assert p.valence == 0.0
        assert p.arousal == 0.0
        assert p.confidence == 0.0

    def test_custom_values(self):
        p = EmotionProfile(
            top_emotions=[{"label": "화남/분노", "score": 0.9}],
            emotion_axis="분노",
            dominant_group="부정_강",
            valence=-0.5,
            arousal=0.8,
            confidence=0.9,
        )
        assert p.emotion_axis == "분노"
        assert p.arousal == 0.8


# ── analyze_emotions ─────────────────────────────────────────────


class TestAnalyzeEmotions:
    def test_empty_text(self):
        assert analyze_emotions("") == []

    def test_whitespace_only(self):
        assert analyze_emotions("   ") == []

    def test_none_classifier_returns_empty(self):
        # _get_classifier returns None when model isn't available
        with patch("pipeline.emotion_analyzer._get_classifier", return_value=None):
            assert analyze_emotions("연봉이 적어서 화가 나요") == []

    def test_classifier_returns_results(self):
        fake_clf = MagicMock()
        fake_clf.return_value = [
            [
                {"label": "화남/분노", "score": 0.92},
                {"label": "짜증", "score": 0.75},
                {"label": "슬픔", "score": 0.30},
                {"label": "기쁨", "score": 0.10},
                {"label": "놀람", "score": 0.05},
                {"label": "유머", "score": 0.02},
            ]
        ]
        with patch("pipeline.emotion_analyzer._get_classifier", return_value=fake_clf):
            result = analyze_emotions("연봉이 적어서 화가 나요", top_k=3)
            assert len(result) == 3
            assert result[0]["label"] == "화남/분노"
            assert result[0]["score"] == 0.92

    def test_classifier_exception_returns_empty(self):
        fake_clf = MagicMock(side_effect=RuntimeError("모델 오류"))
        with patch("pipeline.emotion_analyzer._get_classifier", return_value=fake_clf):
            assert analyze_emotions("테스트") == []

    def test_text_truncated_to_512(self):
        fake_clf = MagicMock(
            return_value=[
                [
                    {"label": "기쁨", "score": 0.5},
                ]
            ]
        )
        with patch("pipeline.emotion_analyzer._get_classifier", return_value=fake_clf):
            long_text = "가" * 1000
            analyze_emotions(long_text)
            call_args = fake_clf.call_args[0][0]
            assert len(call_args) == 512

    def test_non_nested_result_returns_empty(self):
        """If classifier returns non-list of list format → empty."""
        fake_clf = MagicMock(
            return_value=[
                {"label": "기쁨", "score": 0.5},
            ]
        )
        with patch("pipeline.emotion_analyzer._get_classifier", return_value=fake_clf):
            result = analyze_emotions("테스트")
            # results[0] is a dict, not a list → should return []
            assert result == []


# ── get_emotion_profile ──────────────────────────────────────────


class TestGetEmotionProfile:
    def test_empty_emotions_returns_default(self):
        with patch("pipeline.emotion_analyzer.analyze_emotions", return_value=[]):
            profile = get_emotion_profile("테스트")
            assert profile.emotion_axis == "공감"
            assert profile.confidence == 0.0

    def test_anger_dominant_profile(self):
        emotions = [
            {"label": "화남/분노", "score": 0.9},
            {"label": "짜증", "score": 0.7},
            {"label": "불평/불만", "score": 0.5},
            {"label": "슬픔", "score": 0.2},
            {"label": "기쁨", "score": 0.05},
        ]
        with patch("pipeline.emotion_analyzer.analyze_emotions", return_value=emotions):
            profile = get_emotion_profile("연봉 적다")
            assert profile.emotion_axis == "분노"
            assert profile.dominant_group == "부정_강"
            assert profile.valence < 0  # negative
            assert profile.arousal > 0
            assert profile.confidence == 0.9

    def test_positive_profile(self):
        emotions = [
            {"label": "기쁨", "score": 0.8},
            {"label": "감동", "score": 0.6},
            {"label": "고마움", "score": 0.4},
            {"label": "편안/안심", "score": 0.3},
            {"label": "재미있음", "score": 0.2},
        ]
        with patch("pipeline.emotion_analyzer.analyze_emotions", return_value=emotions):
            profile = get_emotion_profile("승진했다")
            assert profile.emotion_axis == "공감"
            assert profile.valence > 0  # positive
            assert len(profile.top_emotions) == 5

    def test_unmapped_emotion_defaults_to_gong_gam(self):
        """Emotion not in _KOTE_TO_AXIS → axis stays 공감."""
        emotions = [
            {"label": "UNKNOWN_EMOTION", "score": 0.9},
            {"label": "ANOTHER_UNKNOWN", "score": 0.5},
        ]
        with patch("pipeline.emotion_analyzer.analyze_emotions", return_value=emotions):
            profile = get_emotion_profile("무언가")
            assert profile.emotion_axis == "공감"

    def test_mixed_emotions_valence_near_zero(self):
        """Mixed positive and negative → valence ≈ 0."""
        emotions = [
            {"label": "화남/분노", "score": 0.5},
            {"label": "기쁨", "score": 0.5},
            {"label": "슬픔", "score": 0.3},
            {"label": "감동", "score": 0.3},
        ]
        with patch("pipeline.emotion_analyzer.analyze_emotions", return_value=emotions):
            profile = get_emotion_profile("복잡한 감정")
            assert -0.5 < profile.valence < 0.5

    def test_insight_axis(self):
        """Emotion mapped to 통찰."""
        emotions = [
            {"label": "깨달음", "score": 0.85},
            {"label": "존경", "score": 0.6},
        ]
        with patch("pipeline.emotion_analyzer.analyze_emotions", return_value=emotions):
            profile = get_emotion_profile("인생 교훈")
            assert profile.emotion_axis == "통찰"


# ── _KOTE_TO_AXIS mapping sanity ─────────────────────────────────


class TestKoteMapping:
    def test_all_axes_reachable(self):
        """Verify every target axis has at least one mapped emotion."""
        axes = set(_KOTE_TO_AXIS.values())
        expected = {"분노", "허탈", "현타", "공감", "웃김", "경악", "통찰"}
        assert axes == expected

    def test_all_group_labels_exist(self):
        """Every emotion group has at least one label."""
        for group, labels in _EMOTION_GROUPS.items():
            assert len(labels) >= 1, f"Group {group} has no labels"
