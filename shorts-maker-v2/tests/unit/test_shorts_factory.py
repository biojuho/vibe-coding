"""test_shorts_factory.py — ShortsFactory 유닛 테스트"""
from __future__ import annotations

import csv
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

# ── Config 로드 테스트 ──────────────────────────────────────────────────────

class TestChannelConfig:
    """channels.yaml 로드 및 5개 채널 설정 검증."""

    @pytest.fixture
    def channels(self):
        cfg_path = Path(__file__).parents[2] / "ShortsFactory" / "config" / "channels.yaml"
        with cfg_path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data["channels"]

    def test_all_five_channels_present(self, channels):
        expected = {"ai_tech", "psychology", "history", "space", "health"}
        assert set(channels.keys()) == expected

    def test_palette_has_required_keys(self, channels):
        for key, ch in channels.items():
            palette = ch["palette"]
            for k in ("primary", "secondary", "accent", "bg"):
                assert k in palette, f"{key} palette missing '{k}'"

    def test_hook_style_defined(self, channels):
        for key, ch in channels.items():
            assert "hook_style" in ch, f"{key} missing hook_style"

    def test_health_has_disclaimer(self, channels):
        assert channels["health"].get("disclaimer") is True

    def test_other_channels_no_disclaimer(self, channels):
        for key in ("ai_tech", "psychology", "history", "space"):
            assert not channels[key].get("disclaimer", False)


class TestColorPresets:
    """color_presets.yaml 프리셋 검증."""

    @pytest.fixture
    def presets(self):
        cfg_path = Path(__file__).parents[2] / "ShortsFactory" / "config" / "color_presets.yaml"
        with cfg_path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data["presets"]

    def test_five_presets_present(self, presets):
        expected = {"neon_tech", "dreamy_purple", "vintage_sepia", "deep_space", "clean_medical"}
        assert set(presets.keys()) == expected

    def test_preset_has_core_params(self, presets):
        for name, p in presets.items():
            for k in ("brightness", "contrast", "saturation", "gamma"):
                assert k in p, f"{name} missing '{k}'"


# ── 엔진 독립 사용 테스트 ───────────────────────────────────────────────────

class TestTextEngine:
    """TextEngine 독립 사용 검증."""

    @pytest.fixture
    def engine(self):
        from ShortsFactory.engines.text_engine import TextEngine
        config = {
            "palette": {"primary": "#00D4FF", "accent": "#00FF88", "bg": "#0A0E1A"},
            "font_title": "Pretendard-ExtraBold",
            "font_body": "Pretendard-Regular",
            "keyword_highlights": {"numbers": "#FFD700"},
        }
        return TextEngine(config)

    def test_render_subtitle_creates_file(self, engine, tmp_path):
        out = tmp_path / "sub.png"
        result = engine.render_subtitle("테스트 자막", output_path=out)
        assert result.exists()
        assert result.suffix == ".png"

    def test_render_title_uses_hook_role(self, engine, tmp_path):
        out = tmp_path / "title.png"
        result = engine.render_title("제목 테스트", output_path=out)
        assert result.exists()


class TestBackgroundEngine:
    """BackgroundEngine 검증."""

    @pytest.fixture
    def engine(self):
        from ShortsFactory.engines.background_engine import BackgroundEngine
        config = {"palette": {"primary": "#818CF8", "accent": "#F59E0B", "bg": "#030014"}}
        return BackgroundEngine(config)

    def test_gradient_creates_file(self, engine, tmp_path):
        out = tmp_path / "bg.png"
        result = engine.create_gradient(540, 960, output_path=out)
        assert result.exists()

    def test_particle_overlay_creates_file(self, engine, tmp_path):
        out = tmp_path / "particles.png"
        result = engine.create_particle_overlay(540, 960, output_path=out)
        assert result.exists()


class TestColorEngine:
    """ColorEngine 검증."""

    def test_load_preset(self):
        from ShortsFactory.engines.color_engine import ColorEngine
        engine = ColorEngine("neon_tech")
        assert engine.preset.contrast == 1.25

    def test_ffmpeg_filter_string(self):
        from ShortsFactory.engines.color_engine import ColorEngine
        engine = ColorEngine("vintage_sepia")
        filt = engine.get_ffmpeg_filter()
        assert "eq=" in filt
        assert "hue=" in filt

    def test_unknown_preset_defaults(self):
        from ShortsFactory.engines.color_engine import ColorEngine
        engine = ColorEngine("nonexistent_preset")
        assert engine.preset.contrast == 1.0  # 기본값


class TestHookEngine:
    """HookEngine 검증."""

    def test_animation_type_mapping(self):
        from ShortsFactory.engines.hook_engine import HookEngine
        e1 = HookEngine({"hook_style": "glitch"})
        assert e1.get_animation_type() == "glitch"
        e2 = HookEngine({"hook_style": "typewriter"})
        assert e2.get_animation_type() == "typing"
        e3 = HookEngine({"hook_style": "zoom_flash"})
        assert e3.get_animation_type() == "popup"


class TestTransitionEngine:
    """TransitionEngine 검증."""

    def test_normalize_role(self):
        from ShortsFactory.engines.transition_engine import TransitionEngine
        engine = TransitionEngine()
        assert engine._normalize_role("hook") == "hook"
        assert engine._normalize_role("rank1") == "body"
        assert engine._normalize_role("cta") == "cta"


class TestLayoutEngine:
    """LayoutEngine 검증."""

    @pytest.fixture
    def engine(self):
        from ShortsFactory.engines.layout_engine import LayoutEngine
        config = {
            "palette": {"primary": "#34D399", "accent": "#EF4444", "bg": "#0A1A14"},
            "font_title": "Pretendard-Bold",
            "font_body": "Pretendard-Regular",
        }
        return LayoutEngine(config)

    def test_split_screen(self, engine, tmp_path):
        out = tmp_path / "split.png"
        result = engine.split_screen("운동하기", "야식먹기", output_path=out)
        assert result.exists()

    def test_card_layout(self, engine, tmp_path):
        out = tmp_path / "cards.png"
        items = [{"title": "항목1", "body": "설명1"}, {"title": "항목2", "body": "설명2"}]
        result = engine.card_layout(items, output_path=out)
        assert result.exists()

    def test_timeline_layout(self, engine, tmp_path):
        out = tmp_path / "timeline.png"
        events = [{"date": "1945", "title": "해방", "desc": "독립"}]
        result = engine.timeline_layout(events, output_path=out)
        assert result.exists()


# ── 템플릿 테스트 ────────────────────────────────────────────────────────────

class TestTemplates:
    """5개 템플릿 씬 빌드 검증."""

    @pytest.fixture
    def ai_config(self):
        return {
            "palette": {"primary": "#00D4FF", "secondary": "#7C3AED", "accent": "#00FF88", "bg": "#0A0E1A"},
            "font_title": "Pretendard-ExtraBold", "font_body": "Pretendard-Regular",
            "keyword_highlights": {"numbers": "#FFD700"},
            "hook_style": "glitch", "color_preset": "neon_tech",
        }

    @pytest.fixture
    def health_config(self):
        return {
            "palette": {"primary": "#34D399", "secondary": "#3B82F6", "accent": "#EF4444", "bg": "#0A1A14"},
            "font_title": "Pretendard-Bold", "font_body": "Pretendard-Regular",
            "keyword_highlights": {"positive": "#34D399", "warning": "#EF4444"},
            "hook_style": "clean_popup", "color_preset": "clean_medical",
            "disclaimer": True,
        }

    def test_ai_news_scene_count(self, ai_config):
        from ShortsFactory.templates.ai_news import AiNewsTemplate
        tmpl = AiNewsTemplate(ai_config)
        scenes = tmpl.build_scenes({
            "hook_text": "🚨 속보",
            "news_title": "GPT-5 출시",
            "points": [{"text": "성능 3배", "keywords": ["3배"]}],
        })
        assert len(scenes) >= 4  # hook + title + point + cta
        assert scenes[0].role == "hook"
        assert scenes[-1].role == "cta"

    def test_health_dodont_has_disclaimer(self, health_config):
        from ShortsFactory.templates.health_dodont import HealthDoDontTemplate
        tmpl = HealthDoDontTemplate(health_config)
        scenes = tmpl.build_scenes({
            "hook_text": "이것만은 꼭!",
            "do_items": ["운동하기"],
            "dont_items": ["야식먹기"],
        })
        roles = [s.role for s in scenes]
        assert "disclaimer" in roles, "health 채널은 면책조항이 있어야 함"

    def test_ai_news_no_disclaimer(self, ai_config):
        from ShortsFactory.templates.ai_news import AiNewsTemplate
        tmpl = AiNewsTemplate(ai_config)
        scenes = tmpl.build_scenes({"hook_text": "테스트"})
        roles = [s.role for s in scenes]
        assert "disclaimer" not in roles


# ── Pipeline 테스트 ──────────────────────────────────────────────────────────

class TestShortsFactory:
    """ShortsFactory 메인 클래스 검증."""

    def test_channel_auto_switch(self):
        from ShortsFactory.pipeline import ShortsFactory
        f1 = ShortsFactory("ai_tech")
        f2 = ShortsFactory("psychology")
        assert f1.channel_config["hook_style"] != f2.channel_config["hook_style"]
        assert f1.channel_config["palette"]["primary"] != f2.channel_config["palette"]["primary"]

    def test_invalid_channel_raises(self):
        from ShortsFactory.pipeline import ShortsFactory
        with pytest.raises(ValueError, match="알 수 없는 채널"):
            ShortsFactory("nonexistent")

    def test_invalid_template_raises(self):
        from ShortsFactory.pipeline import ShortsFactory
        f = ShortsFactory("ai_tech")
        with pytest.raises(ValueError, match="알 수 없는 템플릿"):
            f.create("nonexistent_template", {})

    def test_create_builds_scenes(self):
        from ShortsFactory.pipeline import ShortsFactory
        f = ShortsFactory("ai_tech")
        f.create("ai_news", {"hook_text": "테스트"})
        assert len(f._scenes) >= 2

    def test_list_channels(self):
        from ShortsFactory.pipeline import ShortsFactory
        channels = ShortsFactory.list_channels()
        assert len(channels) == 5
        keys = {c["key"] for c in channels}
        assert keys == {"ai_tech", "psychology", "history", "space", "health"}


# ── 배치 테스트 ──────────────────────────────────────────────────────────────

class TestBatch:
    """BatchProcessor CSV 파싱 검증."""

    def test_csv_parsing(self, tmp_path):
        csv_file = tmp_path / "test.csv"
        with csv_file.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["template", "channel", "hook_text"])
            writer.writeheader()
            writer.writerow({"template": "ai_news", "channel": "ai_tech", "hook_text": "테스트"})
            writer.writerow({"template": "ai_news", "channel": "space", "hook_text": "우주"})

        from ShortsFactory.batch import BatchProcessor
        bp = BatchProcessor()
        rows = bp._parse_csv(csv_file)
        assert len(rows) == 2
        assert rows[0]["channel"] == "ai_tech"

    def test_row_to_data_pipe_split(self):
        from ShortsFactory.batch import BatchProcessor
        row = {"template": "ai_news", "channel": "ai_tech", "keywords": "AI|GPT|NLP"}
        data = BatchProcessor._row_to_data(row)
        assert data["keywords"] == ["AI", "GPT", "NLP"]
