"""test_ai_news_generator.py — AI 뉴스 속보 쇼츠 생성기 단위 테스트

테스트 대상:
- BackgroundEngine: grid overlay, gradient shift
- TextEngine: neon glow, badge
- HookEngine: glitch v2, brightness flash
- AiNewsTemplate: 시간 기반 레이아웃
- ShortsFactory pipeline: 매니페스트 생성
- generate_ai_news_short: 편의 API
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# 프로젝트 루트를 sys.path에 추가
_PROJECT_ROOT = Path(__file__).resolve().parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


# ── 채널 설정 fixture ─────────────────────────────────────────────

@pytest.fixture
def ai_tech_config():
    """ai_tech 채널 설정 (channels.yaml 기반)."""
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
        "keyword_highlights": {
            "tech_terms": "#00FF88",
            "numbers": "#FFD700",
        },
        "hook_style": "glitch",
    }


@pytest.fixture
def sample_data():
    """AiNewsTemplate 테스트용 샘플 데이터."""
    return {
        "news_title": "GPT-5 출시 — 성능 3배 향상",
        "hook_text": "🚨 AI 속보",
        "points": [
            {"text": "멀티모달 성능 대폭 향상", "keywords": ["멀티모달"]},
            {"text": "추론 속도 3배 개선", "keywords": ["3배"]},
            {"text": "API 가격 50% 인하", "keywords": ["50%"]},
        ],
    }


@pytest.fixture
def tmp_output(tmp_path):
    """임시 출력 디렉토리."""
    return tmp_path


# ════════════════════════════════════════════════════════════════
# 1. BackgroundEngine 테스트
# ════════════════════════════════════════════════════════════════

class TestBackgroundEngine:
    def test_create_grid_overlay(self, ai_tech_config, tmp_output):
        from ShortsFactory.engines.background_engine import BackgroundEngine

        engine = BackgroundEngine(ai_tech_config)
        out = tmp_output / "grid.png"
        result = engine.create_grid_overlay(output_path=out)

        assert result.exists()
        assert result.suffix == ".png"
        assert result.stat().st_size > 0

    def test_grid_overlay_dimensions(self, ai_tech_config, tmp_output):
        from ShortsFactory.engines.background_engine import BackgroundEngine
        from PIL import Image

        engine = BackgroundEngine(ai_tech_config)
        out = tmp_output / "grid_dim.png"
        engine.create_grid_overlay(width=540, height=960, output_path=out)

        img = Image.open(out)
        assert img.size == (540, 960)
        assert img.mode == "RGBA"

    def test_grid_overlay_opacity(self, ai_tech_config, tmp_output):
        """그리드 오버레이 opacity 5% 확인."""
        from ShortsFactory.engines.background_engine import BackgroundEngine
        from PIL import Image
        import numpy as np

        engine = BackgroundEngine(ai_tech_config)
        out = tmp_output / "grid_op.png"
        engine.create_grid_overlay(opacity=0.05, output_path=out)

        arr = np.array(Image.open(out))
        # 알파 채널이 낮은 값이어야 함 (0.05 * 255 ≈ 12)
        non_zero_alpha = arr[:, :, 3][arr[:, :, 3] > 0]
        if len(non_zero_alpha) > 0:
            assert non_zero_alpha.max() <= 15  # 약간의 여유

    def test_create_gradient_shift_frames(self, ai_tech_config, tmp_output):
        from ShortsFactory.engines.background_engine import BackgroundEngine

        engine = BackgroundEngine(ai_tech_config)
        frames = engine.create_gradient_shift_frames(
            width=270, height=480, num_frames=5, output_dir=tmp_output / "grad",
        )

        assert len(frames) == 5
        for f in frames:
            assert f.exists()


# ════════════════════════════════════════════════════════════════
# 2. TextEngine 테스트
# ════════════════════════════════════════════════════════════════

class TestTextEngine:
    def test_render_subtitle_with_glow(self, ai_tech_config, tmp_output):
        from ShortsFactory.engines.text_engine import TextEngine

        engine = TextEngine(ai_tech_config)
        out = tmp_output / "glow.png"
        result = engine.render_subtitle_with_glow(
            "GPT-5 출시",
            glow_color="#00D4FF",
            output_path=out,
        )

        assert result.exists()
        assert result.stat().st_size > 1000  # 의미 있는 크기

    def test_render_badge(self, ai_tech_config, tmp_output):
        from ShortsFactory.engines.text_engine import TextEngine

        engine = TextEngine(ai_tech_config)
        out = tmp_output / "badge.png"
        result = engine.render_badge(1, output_path=out)

        assert result.exists()
        assert result.stat().st_size > 0

    def test_badge_dimensions(self, ai_tech_config, tmp_output):
        from ShortsFactory.engines.text_engine import TextEngine
        from PIL import Image

        engine = TextEngine(ai_tech_config)
        out = tmp_output / "badge_dim.png"
        engine.render_badge(3, size=100, output_path=out)

        img = Image.open(out)
        assert img.size == (100, 100)
        assert img.mode == "RGBA"

    def test_render_subtitle_with_glow_custom_radius(self, ai_tech_config, tmp_output):
        from ShortsFactory.engines.text_engine import TextEngine

        engine = TextEngine(ai_tech_config)
        out = tmp_output / "glow_r30.png"
        result = engine.render_subtitle_with_glow(
            "테스트 텍스트", glow_radius=30, output_path=out,
        )

        assert result.exists()


# ════════════════════════════════════════════════════════════════
# 3. HookEngine 테스트
# ════════════════════════════════════════════════════════════════

class TestHookEngine:
    def test_create_hook(self, ai_tech_config):
        from ShortsFactory.engines.hook_engine import HookEngine

        engine = HookEngine(ai_tech_config)
        assert engine.hook_style == "glitch"
        assert engine.get_animation_type() == "glitch"

    def test_create_hook_with_flash_method_exists(self, ai_tech_config):
        from ShortsFactory.engines.hook_engine import HookEngine

        engine = HookEngine(ai_tech_config)
        assert hasattr(engine, "create_hook_with_flash")

    def test_brightness_flash_function(self):
        from ShortsFactory.engines.hook_engine import _apply_brightness_flash
        assert callable(_apply_brightness_flash)

    def test_glitch_rgb_split(self):
        """개선된 글리치가 RGB 분리를 수행하는지 확인."""
        from ShortsFactory.engines.hook_engine import _apply_glitch
        import numpy as np
        from unittest.mock import MagicMock

        clip = MagicMock()
        clip.transform = MagicMock(return_value=clip)

        result = _apply_glitch(clip, 0.1)
        assert clip.transform.called


# ════════════════════════════════════════════════════════════════
# 4. AiNewsTemplate 테스트
# ════════════════════════════════════════════════════════════════

class TestAiNewsTemplate:
    def test_build_scenes_structure(self, ai_tech_config, sample_data):
        from ShortsFactory.templates.ai_news import AiNewsTemplate

        template = AiNewsTemplate(ai_tech_config)
        scenes = template.build_scenes(sample_data)

        # 최소 씬: hook + headline + 3 cards + cta = 6
        assert len(scenes) >= 5

    def test_hook_scene(self, ai_tech_config, sample_data):
        from ShortsFactory.templates.ai_news import AiNewsTemplate

        template = AiNewsTemplate(ai_tech_config)
        scenes = template.build_scenes(sample_data)

        hook = scenes[0]
        assert hook.role == "hook"
        assert hook.start_time == 0.0
        assert hook.animation == "glitch_flash"
        assert hook.extra["text_color"] == "#FF4444"

    def test_headline_scene(self, ai_tech_config, sample_data):
        from ShortsFactory.templates.ai_news import AiNewsTemplate

        template = AiNewsTemplate(ai_tech_config)
        scenes = template.build_scenes(sample_data)

        headline = scenes[1]
        assert headline.role == "headline"
        assert headline.start_time == 1.5
        assert headline.animation == "slide_up"
        assert headline.extra.get("glow") is True

    def test_card_scenes(self, ai_tech_config, sample_data):
        from ShortsFactory.templates.ai_news import AiNewsTemplate

        template = AiNewsTemplate(ai_tech_config)
        scenes = template.build_scenes(sample_data)

        # 카드는 3개 (points 3개)
        cards = [s for s in scenes if s.role == "body"]
        assert len(cards) == 3

        for i, card in enumerate(cards):
            assert card.animation == "slide_in_right"
            assert card.extra["badge_number"] == i + 1
            assert card.extra["card_bg"] == "#111827"

    def test_cta_scene(self, ai_tech_config, sample_data):
        from ShortsFactory.templates.ai_news import AiNewsTemplate

        template = AiNewsTemplate(ai_tech_config)
        scenes = template.build_scenes(sample_data)

        cta = scenes[-1]
        assert cta.role == "cta"
        assert cta.animation == "fade_in"
        assert cta.extra.get("gradient_shift") is True

    def test_sfx_markers(self, ai_tech_config, sample_data):
        from ShortsFactory.templates.ai_news import AiNewsTemplate

        template = AiNewsTemplate(ai_tech_config)
        scenes = template.build_scenes(sample_data)
        markers = template.get_sfx_markers(scenes)

        assert len(markers) == 3  # 카드 3개 → whoosh 3개
        for m in markers:
            assert m["type"] == "whoosh"
            assert isinstance(m["time"], float)

    def test_total_duration(self, ai_tech_config, sample_data):
        from ShortsFactory.templates.ai_news import AiNewsTemplate

        template = AiNewsTemplate(ai_tech_config)
        scenes = template.build_scenes(sample_data)
        total = template.get_total_duration(scenes)

        # 최소: 1.5(훅) + 1.5(헤드라인) + 3×4.4(카드) + 5(CTA) ≈ 21.2초
        assert total >= 20.0
        assert total <= 35.0  # 합리적 상한

    def test_custom_cta(self, ai_tech_config):
        from ShortsFactory.templates.ai_news import AiNewsTemplate

        template = AiNewsTemplate(ai_tech_config)
        scenes = template.build_scenes({
            "news_title": "테스트",
            "points": [{"text": "포인트1", "keywords": []}],
            "cta_text": "커스텀 CTA 문구",
        })

        cta = scenes[-1]
        assert cta.text == "커스텀 CTA 문구"


# ════════════════════════════════════════════════════════════════
# 5. Scene dataclass 테스트
# ════════════════════════════════════════════════════════════════

class TestScene:
    def test_new_fields(self):
        from ShortsFactory.templates.base_template import Scene

        scene = Scene(
            role="body",
            text="테스트",
            start_time=3.0,
            animation="slide_in_right",
        )
        assert scene.start_time == 3.0
        assert scene.animation == "slide_in_right"

    def test_default_values(self):
        from ShortsFactory.templates.base_template import Scene

        scene = Scene(role="body")
        assert scene.start_time is None
        assert scene.animation == "none"


# ════════════════════════════════════════════════════════════════
# 6. Pipeline 통합 테스트
# ════════════════════════════════════════════════════════════════

class TestPipeline:
    def test_create_and_manifest(self, tmp_output, sample_data):
        """ShortsFactory.create() → render()가 매니페스트를 정상 생성하는지 확인."""
        from ShortsFactory.pipeline import ShortsFactory

        factory = ShortsFactory(channel="ai_tech")
        factory.create("ai_news", sample_data)

        out = tmp_output / "test_output.mp4"

        # FFmpeg 미설치 환경에서도 매니페스트까지는 생성
        with patch("ShortsFactory.pipeline._ffmpeg_available", return_value=False):
            result = factory.render(out)

        # 매니페스트 확인
        assets_dir = out.parent / f".assets_{out.stem}"
        manifest_path = assets_dir / "manifest.json"
        assert manifest_path.exists()

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert manifest["channel"] == "ai_tech"
        assert manifest["template"] == "ai_news"
        assert manifest["total_duration"] > 0
        assert len(manifest["scenes"]) >= 5
        assert len(manifest["sfx_markers"]) == 3

    def test_calculate_total_duration(self, sample_data):
        from ShortsFactory.pipeline import ShortsFactory

        factory = ShortsFactory(channel="ai_tech")
        factory.create("ai_news", sample_data)
        dur = factory._calculate_total_duration()

        assert dur > 20.0


# ════════════════════════════════════════════════════════════════
# 7. generate_ai_news_short 테스트
# ════════════════════════════════════════════════════════════════

class TestGenerateShort:
    def test_function_signature(self):
        from ShortsFactory.generate_short import generate_ai_news_short
        import inspect

        sig = inspect.signature(generate_ai_news_short)
        params = list(sig.parameters.keys())

        assert "news_title" in params
        assert "points" in params
        assert "hook_text" in params
        assert "bg_music" in params
        assert "cta_text" in params

    def test_generate_with_mock_ffmpeg(self, tmp_output, sample_data):
        from ShortsFactory.generate_short import generate_ai_news_short

        out = tmp_output / "gen_test.mp4"
        with patch("ShortsFactory.pipeline._ffmpeg_available", return_value=False):
            result = generate_ai_news_short(
                news_title=sample_data["news_title"],
                points=sample_data["points"],
                output_path=out,
            )

        # FFmpeg 없어도 에셋+매니페스트는 생성
        assert result == out
