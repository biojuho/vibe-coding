"""Tests for content_intelligence — 감성 분석 모듈."""

from __future__ import annotations

from shorts_maker_v2.utils.content_intelligence import (
    SentimentResult,
    analyze_sentiment,
)


class TestAnalyzeSentiment:
    """analyze_sentiment 함수 테스트."""

    def test_empty_narrations(self):
        result = analyze_sentiment([])
        assert result.primary_emotion == "neutral"
        assert result.intensity == 1
        assert result.tags == []

    def test_single_empty_string(self):
        result = analyze_sentiment([""])
        assert result.primary_emotion == "neutral"

    def test_awe_keywords(self):
        narrations = [
            "이것은 정말 놀라운 우주의 비밀입니다.",
            "믿기 어려운 경이로운 발견이 이루어졌습니다.",
        ]
        result = analyze_sentiment(narrations)
        assert result.primary_emotion == "awe"
        assert result.intensity >= 2
        assert any("놀라운" in t or "경이로운" in t for t in result.tags)

    def test_curiosity_keywords(self):
        narrations = [
            "왜 이런 일이 벌어졌을까? 숨겨진 진실을 파헤칩니다.",
            "알려지지 않은 비밀, 그 의문의 해답은?",
        ]
        result = analyze_sentiment(narrations)
        assert result.primary_emotion == "curiosity"

    def test_fear_keywords(self):
        narrations = [
            "이 위험한 물질은 치명적입니다.",
            "공포의 순간, 소름 끼치는 경고가 울립니다.",
        ]
        result = analyze_sentiment(narrations)
        assert result.primary_emotion == "fear"

    def test_hope_keywords(self):
        narrations = [
            "미래의 가능성, 희망을 품은 발전.",
            "기적같은 치료법이 발견되었습니다.",
        ]
        result = analyze_sentiment(narrations)
        assert result.primary_emotion == "hope"

    def test_intensity_boosters(self):
        narrations = [
            "절대로 놀라운!! 역대 최고의 경이로운 발견입니다.",
        ]
        result = analyze_sentiment(narrations)
        # 부스터가 intensity를 올려야 함
        assert result.intensity >= 3

    def test_multiple_emotions_picks_dominant(self):
        narrations = [
            "놀라운 발견! 경이로운 우주!",
            "약간 무서운 상황이지만...",
        ]
        result = analyze_sentiment(narrations)
        # awe 키워드가 더 많으므로 awe가 primary
        assert result.primary_emotion == "awe"

    def test_english_keywords(self):
        narrations = [
            "This is an incredible discovery.",
            "Amazing and mind-blowing facts about the universe.",
        ]
        result = analyze_sentiment(narrations)
        assert result.primary_emotion == "awe"

    def test_tags_limited(self):
        narrations = [
            "놀라운 경이로운 상상을 초월 믿기 어려운 amazing incredible mind-blowing unbelievable 우주 광활 무한"
        ]
        result = analyze_sentiment(narrations)
        assert len(result.tags) <= 6

    def test_to_dict(self):
        result = analyze_sentiment(["놀라운 발견"])
        d = result.to_dict()
        assert "primary_emotion" in d
        assert "intensity" in d
        assert "tags" in d
        assert "emotion_scores" in d
        assert isinstance(d["emotion_scores"], dict)

    def test_intensity_bounds(self):
        """intensity는 항상 1~5 범위여야 함."""
        result = analyze_sentiment(["일반적인 문장입니다."])
        assert 1 <= result.intensity <= 5

        # 극단적 부스터 케이스
        result2 = analyze_sentiment(
            [
                "절대 최고 역대 충격 극한 전무후무 absolutely extreme "
                "ultimate shocking 놀라운 경이로운 amazing incredible"
            ]
        )
        assert result2.intensity <= 5

    def test_humor_detection(self):
        narrations = [
            "정말 재미있는 황당한 이야기, 웃긴 반전이 기다립니다.",
        ]
        result = analyze_sentiment(narrations)
        assert result.primary_emotion == "humor"

    def test_nostalgia_detection(self):
        narrations = [
            "옛날 추억이 그리운 과거의 전설, 역사 속 고대 이야기.",
        ]
        result = analyze_sentiment(narrations)
        assert result.primary_emotion == "nostalgia"


class TestSentimentResult:
    """SentimentResult dataclass 검증."""

    def test_default_fields(self):
        r = SentimentResult(primary_emotion="awe", intensity=3)
        assert r.tags == []
        assert r.emotion_scores == {}

    def test_to_dict_structure(self):
        r = SentimentResult(
            primary_emotion="curiosity",
            intensity=2,
            tags=["왜", "비밀"],
            emotion_scores={"curiosity": 5, "awe": 1},
        )
        d = r.to_dict()
        assert d == {
            "primary_emotion": "curiosity",
            "intensity": 2,
            "tags": ["왜", "비밀"],
            "emotion_scores": {"curiosity": 5, "awe": 1},
        }
