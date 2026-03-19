"""P3 소스 확장 단위 테스트."""
import pytest


class TestSourceHintsConfig:
    """classification_rules.yaml source_hints 정합성."""

    def test_all_sources_in_hints(self):
        """config.yaml input_sources에 등록된 모든 소스가 source_hints에 존재."""
        import yaml, os
        base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        with open(os.path.join(base, "config.yaml"), encoding="utf-8") as f:
            config = yaml.safe_load(f)
        with open(os.path.join(base, "classification_rules.yaml"), encoding="utf-8") as f:
            rules = yaml.safe_load(f)
        hints = rules.get("source_hints", {})
        for src in config.get("input_sources", []):
            assert src in hints, f"source_hints에 '{src}' 누락"

    def test_source_hint_structure(self):
        """각 소스 힌트에 필수 필드가 존재."""
        import yaml, os
        base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        with open(os.path.join(base, "classification_rules.yaml"), encoding="utf-8") as f:
            rules = yaml.safe_load(f)
        for name, hint in rules.get("source_hints", {}).items():
            assert "display_name" in hint, f"{name}: display_name 누락"
            assert "topic_bias" in hint, f"{name}: topic_bias 누락"
            assert "quality_boost" in hint, f"{name}: quality_boost 누락"
            assert isinstance(hint["quality_boost"], (int, float)), f"{name}: quality_boost 숫자 아님"


class TestGetSourceHint:
    """content_intelligence.get_source_hint() 테스트."""

    def test_known_source(self):
        from pipeline.content_intelligence import get_source_hint
        hint = get_source_hint("blind")
        assert hint["display_name"] == "블라인드"
        assert "연봉" in hint["topic_bias"]
        assert hint["quality_boost"] == 1.0

    def test_fmkorea_source(self):
        from pipeline.content_intelligence import get_source_hint
        hint = get_source_hint("fmkorea")
        assert hint["display_name"] == "에펨코리아"
        assert hint["quality_boost"] == 0.85

    def test_jobplanet_source(self):
        from pipeline.content_intelligence import get_source_hint
        hint = get_source_hint("jobplanet")
        assert hint["display_name"] == "잡플래닛"
        assert hint["quality_boost"] == 1.1
        assert "회사문화" in hint["topic_bias"]

    def test_unknown_source_returns_default(self):
        from pipeline.content_intelligence import get_source_hint
        hint = get_source_hint("unknown_source_xyz")
        assert hint["quality_boost"] == 1.0
        assert hint["display_name"] == "unknown_source_xyz"


class TestScraperRegistry:
    """SCRAPER_REGISTRY 등록 확인."""

    def test_all_sources_registered(self):
        from scrapers import SCRAPER_REGISTRY
        for src in ["blind", "ppomppu", "fmkorea", "jobplanet"]:
            assert src in SCRAPER_REGISTRY, f"SCRAPER_REGISTRY에 '{src}' 누락"

    def test_get_scraper(self):
        from scrapers import get_scraper
        cls = get_scraper("fmkorea")
        assert cls.SOURCE_NAME == "fmkorea"
        cls = get_scraper("jobplanet")
        assert cls.SOURCE_NAME == "jobplanet"


class TestConfigInputSources:
    """config.yaml input_sources에 4개 소스 등록 확인."""

    def test_four_sources_enabled(self):
        import yaml, os
        base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        with open(os.path.join(base, "config.yaml"), encoding="utf-8") as f:
            config = yaml.safe_load(f)
        sources = config.get("input_sources", [])
        for s in ["blind", "ppomppu", "fmkorea", "jobplanet"]:
            assert s in sources, f"config.yaml input_sources에 '{s}' 누락"
