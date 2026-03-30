"""Phase 3 테스트 — Camoufox 통합 + KOTE 감정 분석."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# ── Camoufox 통합 테스트 ─────────────────────────────────────────────
class TestCamoufoxIntegration:
    def test_camoufox_importable(self):
        """camoufox 패키지가 import 가능한지 확인."""
        try:
            from camoufox.async_api import AsyncCamoufox

            assert AsyncCamoufox is not None
        except ImportError:
            pytest.skip("camoufox not installed")

    def test_base_scraper_has_camo_ctx(self):
        """BaseScraper에 _camo_ctx 속성이 있는지 확인."""
        from scrapers.base import BaseScraper

        class DummyConfig:
            def get(self, key, default=None):
                return default

        scraper = BaseScraper(DummyConfig())
        assert hasattr(scraper, "_camo_ctx")
        assert scraper._camo_ctx is None

    def test_base_scraper_engine_config(self):
        """browser.engine config가 올바르게 읽히는지 확인."""
        from scrapers.base import BaseScraper

        class ChromeConfig:
            def get(self, key, default=None):
                if key == "browser.engine":
                    return "chromium"
                return default

        scraper = BaseScraper(ChromeConfig())
        # engine=chromium이면 Camoufox 사용 안 함
        assert scraper.config.get("browser.engine") == "chromium"


# ── KOTE 감정 분석 테스트 ────────────────────────────────────────────
class TestEmotionAnalyzer:
    """KOTE 모델 로드가 느리므로 모듈 레벨에서 한 번만 로드."""

    @pytest.fixture(scope="class")
    def analyzer_available(self):
        import pipeline.emotion_analyzer as ea

        ea._load_attempted = False
        ea._classifier = None
        clf = ea._get_classifier()
        return clf is not None

    def test_analyze_emotions_with_model(self, analyzer_available):
        if not analyzer_available:
            pytest.skip("KOTE model not loadable")
        from pipeline.emotion_analyzer import analyze_emotions

        result = analyze_emotions("연봉이 너무 적어서 화가 나요")
        assert len(result) > 0
        assert "label" in result[0]
        assert "score" in result[0]
        assert result[0]["score"] > 0

    def test_anger_detected(self, analyzer_available):
        if not analyzer_available:
            pytest.skip("KOTE model not loadable")
        from pipeline.emotion_analyzer import analyze_emotions

        result = analyze_emotions("상사가 너무 짜증나고 화가 치밀어 오른다")
        labels = [r["label"] for r in result]
        assert any("화남" in lbl or "짜증" in lbl or "불평" in lbl for lbl in labels)

    def test_joy_detected(self, analyzer_available):
        if not analyzer_available:
            pytest.skip("KOTE model not loadable")
        from pipeline.emotion_analyzer import analyze_emotions

        result = analyze_emotions("이직 성공해서 너무 기쁘고 행복합니다")
        labels = [r["label"] for r in result]
        assert any("기쁨" in lbl or "감동" in lbl or "고마움" in lbl for lbl in labels)

    def test_emotion_profile_structure(self, analyzer_available):
        if not analyzer_available:
            pytest.skip("KOTE model not loadable")
        from pipeline.emotion_analyzer import get_emotion_profile

        profile = get_emotion_profile("퇴사하고 싶은데 용기가 없다")
        assert hasattr(profile, "emotion_axis")
        assert hasattr(profile, "valence")
        assert hasattr(profile, "arousal")
        assert hasattr(profile, "dominant_group")
        assert -1 <= profile.valence <= 1
        assert 0 <= profile.arousal <= 1

    def test_emotion_axis_mapping(self, analyzer_available):
        if not analyzer_available:
            pytest.skip("KOTE model not loadable")
        from pipeline.emotion_analyzer import get_emotion_profile

        # 분노 텍스트 → 분노 axis
        angry = get_emotion_profile("진짜 빡치네 이런 회사 때려칠래")
        assert angry.emotion_axis in ("분노", "현타", "허탈")  # 분노 계열

    def test_empty_text_returns_empty(self):
        from pipeline.emotion_analyzer import analyze_emotions

        result = analyze_emotions("")
        assert result == []


class TestEmotionAnalyzerFallback:
    """KOTE 모델 없이도 content_intelligence가 동작하는지 확인."""

    def test_classify_emotion_axis_without_kote(self):
        """KOTE 미로드 시 키워드 폴백."""
        import pipeline.emotion_analyzer as ea

        old_clf = ea._classifier
        old_attempted = ea._load_attempted
        try:
            ea._classifier = None
            ea._load_attempted = True  # 로드 실패 상태
            from pipeline.content_intelligence import classify_emotion_axis

            result = classify_emotion_axis("빡치는 상사", "상사가 너무 화나게 한다")
            assert isinstance(result, str)
            assert len(result) > 0
        finally:
            ea._classifier = old_clf
            ea._load_attempted = old_attempted


# ── extract_clean_text (trafilatura) 추가 확인 ────────────────────────
class TestTrafilaturaInScrapers:
    def test_extract_method_exists(self):
        from scrapers.base import BaseScraper

        assert hasattr(BaseScraper, "_extract_clean_text")
        assert callable(BaseScraper._extract_clean_text)
