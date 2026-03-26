"""test_tech_vs.py — 기술 비교(VS) 쇼츠 단위 테스트

테스트 대상:
- LayoutEngine: vs_title_bar, vs_split_cards, vs_score_bar
- TechVsTemplate: 씬 구조, 승자 판정, SFX 마커
- Pipeline: tech_vs 템플릿 렌더링
- generate_tech_vs_short: 편의 API
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


@pytest.fixture
def ai_tech_config():
    return {
        "name": "AI/기술",
        "palette": {
            "primary": "#00D4FF",
            "secondary": "#7C3AED",
            "accent": "#00FF88",
            "bg": "#0A0E1A",
        },
        "font_title": "Pretendard-ExtraBold",
        "font_body": "Pretendard-Regular",
        "color_preset": "neon_tech",
        "keyword_highlights": {"tech_terms": "#00FF88", "numbers": "#FFD700"},
        "hook_style": "glitch",
    }


@pytest.fixture
def sample_vs_data():
    return {
        "item_a": {
            "name": "GPT-5",
            "scores": {"성능": 95, "가격": 70, "속도": 88},
        },
        "item_b": {
            "name": "Claude 4",
            "scores": {"성능": 90, "가격": 85, "속도": 92},
        },
        "categories": ["성능", "가격", "속도"],
    }


# ════════════════════════════════════════════════════════════════
# 1. LayoutEngine — VS 레이아웃
# ════════════════════════════════════════════════════════════════


class TestVsTitleBar:
    def test_creates_image(self, ai_tech_config, tmp_path):
        from ShortsFactory.engines.layout_engine import LayoutEngine

        engine = LayoutEngine(ai_tech_config)
        out = tmp_path / "vs_bar.png"
        result = engine.vs_title_bar("GPT-5", "Claude 4", output_path=out)
        assert result.exists()
        assert result.stat().st_size > 0

    def test_dimensions(self, ai_tech_config, tmp_path):
        from PIL import Image

        from ShortsFactory.engines.layout_engine import LayoutEngine

        engine = LayoutEngine(ai_tech_config)
        out = tmp_path / "bar_dim.png"
        engine.vs_title_bar("A", "B", output_path=out)
        img = Image.open(out)
        assert img.width == 1080
        assert img.height == int(1920 * 0.15)
        assert img.mode == "RGBA"


class TestVsSplitCards:
    def test_creates_image(self, ai_tech_config, tmp_path):
        from ShortsFactory.engines.layout_engine import LayoutEngine

        engine = LayoutEngine(ai_tech_config)
        out = tmp_path / "split.png"
        result = engine.vs_split_cards("GPT 설명", "Claude 설명", output_path=out)
        assert result.exists()

    def test_dimensions(self, ai_tech_config, tmp_path):
        from PIL import Image

        from ShortsFactory.engines.layout_engine import LayoutEngine

        engine = LayoutEngine(ai_tech_config)
        out = tmp_path / "split_dim.png"
        engine.vs_split_cards("A", "B", output_path=out)
        img = Image.open(out)
        assert img.width == 1080
        assert img.height == int(1920 * 0.55)

    def test_glow_line_disabled(self, ai_tech_config, tmp_path):
        from ShortsFactory.engines.layout_engine import LayoutEngine

        engine = LayoutEngine(ai_tech_config)
        out = tmp_path / "no_glow.png"
        result = engine.vs_split_cards("A", "B", glow_line=False, output_path=out)
        assert result.exists()


class TestVsScoreBar:
    def test_creates_image(self, ai_tech_config, tmp_path):
        from ShortsFactory.engines.layout_engine import LayoutEngine

        engine = LayoutEngine(ai_tech_config)
        out = tmp_path / "score.png"
        result = engine.vs_score_bar("성능", 95, 90, output_path=out)
        assert result.exists()

    def test_zero_scores(self, ai_tech_config, tmp_path):
        from ShortsFactory.engines.layout_engine import LayoutEngine

        engine = LayoutEngine(ai_tech_config)
        out = tmp_path / "zero.png"
        result = engine.vs_score_bar("가격", 0, 0, output_path=out)
        assert result.exists()

    def test_max_score(self, ai_tech_config, tmp_path):
        from ShortsFactory.engines.layout_engine import LayoutEngine

        engine = LayoutEngine(ai_tech_config)
        out = tmp_path / "max.png"
        result = engine.vs_score_bar("속도", 100, 100, max_score=100, output_path=out)
        assert result.exists()


# ════════════════════════════════════════════════════════════════
# 2. TechVsTemplate
# ════════════════════════════════════════════════════════════════


class TestTechVsTemplate:
    def test_scene_count(self, ai_tech_config, sample_vs_data):
        from ShortsFactory.templates.tech_vs import TechVsTemplate

        template = TechVsTemplate(ai_tech_config)
        scenes = template.build_scenes(sample_vs_data)
        # intro(1) + categories(3) + conclusion(1) = 5
        assert len(scenes) == 5

    def test_intro_scene(self, ai_tech_config, sample_vs_data):
        from ShortsFactory.templates.tech_vs import TechVsTemplate

        template = TechVsTemplate(ai_tech_config)
        scenes = template.build_scenes(sample_vs_data)
        intro = scenes[0]
        assert intro.role == "hook"
        assert intro.animation == "vs_clash"
        assert "GPT-5" in intro.text
        assert "Claude 4" in intro.text

    def test_category_scenes(self, ai_tech_config, sample_vs_data):
        from ShortsFactory.templates.tech_vs import TechVsTemplate

        template = TechVsTemplate(ai_tech_config)
        scenes = template.build_scenes(sample_vs_data)
        body_scenes = [s for s in scenes if s.role == "body"]
        assert len(body_scenes) == 3
        for s in body_scenes:
            assert s.animation == "bar_fill"
            assert s.duration == 4.0
            assert "score_a" in s.extra
            assert "score_b" in s.extra

    def test_winner_a(self, ai_tech_config, sample_vs_data):
        """GPT-5의 총점(95+70+88=253)이 Claude 4(90+85+92=267)보다 낮음 → Claude 4 승."""
        from ShortsFactory.templates.tech_vs import TechVsTemplate

        template = TechVsTemplate(ai_tech_config)
        scenes = template.build_scenes(sample_vs_data)
        winner_info = template.get_winner(scenes)
        assert winner_info["winner"] == "Claude 4"
        assert winner_info["winner_color"] == "#7C3AED"

    def test_winner_b_higher(self, ai_tech_config):
        from ShortsFactory.templates.tech_vs import TechVsTemplate

        data = {
            "item_a": {"name": "A", "scores": {"x": 100, "y": 100}},
            "item_b": {"name": "B", "scores": {"x": 50, "y": 50}},
            "categories": ["x", "y"],
        }
        template = TechVsTemplate(ai_tech_config)
        scenes = template.build_scenes(data)
        winner_info = template.get_winner(scenes)
        assert winner_info["winner"] == "A"

    def test_draw(self, ai_tech_config):
        from ShortsFactory.templates.tech_vs import TechVsTemplate

        data = {
            "item_a": {"name": "X", "scores": {"점수": 80}},
            "item_b": {"name": "Y", "scores": {"점수": 80}},
            "categories": ["점수"],
        }
        template = TechVsTemplate(ai_tech_config)
        scenes = template.build_scenes(data)
        winner_info = template.get_winner(scenes)
        assert winner_info["winner"] == "무승부"

    def test_total_duration(self, ai_tech_config, sample_vs_data):
        from ShortsFactory.templates.tech_vs import TechVsTemplate

        template = TechVsTemplate(ai_tech_config)
        scenes = template.build_scenes(sample_vs_data)
        total = template.get_total_duration(scenes)
        # 2(인트로) + 3*4(항목) + 3(결론) = 17초
        assert total == 17.0

    def test_sfx_markers(self, ai_tech_config, sample_vs_data):
        from ShortsFactory.templates.tech_vs import TechVsTemplate

        template = TechVsTemplate(ai_tech_config)
        scenes = template.build_scenes(sample_vs_data)
        markers = template.get_sfx_markers(scenes)
        # 3 bar_fill + 1 fanfare = 4
        assert len(markers) == 4
        types = [m["type"] for m in markers]
        assert types.count("bar_fill") == 3
        assert "fanfare" in types

    def test_conclusion_glow(self, ai_tech_config, sample_vs_data):
        from ShortsFactory.templates.tech_vs import TechVsTemplate

        template = TechVsTemplate(ai_tech_config)
        scenes = template.build_scenes(sample_vs_data)
        conclusion = scenes[-1]
        assert conclusion.role == "cta"
        assert conclusion.animation == "winner_glow"
        assert conclusion.extra["full_screen_glow"] is True

    def test_conclusion_draw_sfx(self, ai_tech_config):
        from ShortsFactory.templates.tech_vs import TechVsTemplate

        data = {
            "item_a": {"name": "X", "scores": {"점수": 50}},
            "item_b": {"name": "Y", "scores": {"점수": 50}},
            "categories": ["점수"],
        }
        template = TechVsTemplate(ai_tech_config)
        scenes = template.build_scenes(data)
        markers = template.get_sfx_markers(scenes)
        assert markers[-1]["type"] == "draw"


# ════════════════════════════════════════════════════════════════
# 3. Pipeline 통합
# ════════════════════════════════════════════════════════════════


class TestVsPipeline:
    def test_create_and_manifest(self, tmp_path, sample_vs_data):
        from ShortsFactory.pipeline import ShortsFactory

        factory = ShortsFactory(channel="ai_tech")
        factory.create("tech_vs", sample_vs_data)
        out = tmp_path / "vs_output.mp4"

        with patch("ShortsFactory.pipeline._ffmpeg_available", return_value=False):
            factory.render(out)

        manifest_path = out.parent / f".assets_{out.stem}" / "manifest.json"
        assert manifest_path.exists()
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert manifest["template"] == "tech_vs"
        assert manifest["total_duration"] == 17.0
        assert len(manifest["scenes"]) == 5


# ════════════════════════════════════════════════════════════════
# 4. generate_tech_vs_short
# ════════════════════════════════════════════════════════════════


class TestGenerateVsShort:
    def test_function_signature(self):
        import inspect

        from ShortsFactory.generate_short import generate_tech_vs_short

        sig = inspect.signature(generate_tech_vs_short)
        params = list(sig.parameters.keys())
        assert "item_a" in params
        assert "item_b" in params
        assert "categories" in params

    def test_generate_with_mock(self, tmp_path, sample_vs_data):
        from ShortsFactory.generate_short import generate_tech_vs_short

        out = tmp_path / "gen_vs.mp4"
        with patch("ShortsFactory.pipeline._ffmpeg_available", return_value=False):
            result = generate_tech_vs_short(
                item_a=sample_vs_data["item_a"],
                item_b=sample_vs_data["item_b"],
                categories=sample_vs_data["categories"],
                output_path=out,
            )
        assert result == out
