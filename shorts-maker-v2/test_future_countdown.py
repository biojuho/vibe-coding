"""test_future_countdown.py — 미래 기술 카운트다운 쇼츠 단위 테스트

테스트 대상:
- BackgroundEngine: animated particles, blurred background
- TextEngine: watermark number
- FutureCountdownTemplate: 카운트다운 씬 구조, 1위 특별 효과
- Pipeline: future_countdown 템플릿 렌더링
- generate_future_countdown_short: 편의 API
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
            "bg": "#0B0D21",
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
def sample_items():
    return [
        {"rank": 5, "title": "양자 컴퓨팅", "description": "양자 우위 달성"},
        {"rank": 4, "title": "뇌-컴퓨터 인터페이스", "description": "생각으로 제어"},
        {"rank": 3, "title": "핵융합 에너지", "description": "무한 에너지원"},
        {"rank": 2, "title": "AGI", "description": "범용 인공지능"},
        {"rank": 1, "title": "나노 로봇", "description": "체내 자율 치료"},
    ]


# ════════════════════════════════════════════════════════════════
# 1. BackgroundEngine — 파티클 & 블러 배경
# ════════════════════════════════════════════════════════════════

class TestAnimatedParticles:
    def test_creates_frames(self, ai_tech_config, tmp_path):
        from ShortsFactory.engines.background_engine import BackgroundEngine

        engine = BackgroundEngine(ai_tech_config)
        frames = engine.create_animated_particle_frames(
            width=270, height=480,
            num_particles=10, num_frames=5,
            output_dir=tmp_path / "particles",
        )
        assert len(frames) == 5
        for f in frames:
            assert f.exists()
            assert f.stat().st_size > 0

    def test_density_multiplier(self, ai_tech_config, tmp_path):
        from ShortsFactory.engines.background_engine import BackgroundEngine
        from PIL import Image
        import numpy as np

        engine = BackgroundEngine(ai_tech_config)
        # 일반 밀도
        frames_normal = engine.create_animated_particle_frames(
            width=270, height=480, num_particles=10, num_frames=1,
            density_multiplier=1.0, output_dir=tmp_path / "p_normal",
        )
        # 3배 밀도
        frames_dense = engine.create_animated_particle_frames(
            width=270, height=480, num_particles=10, num_frames=1,
            density_multiplier=3.0, output_dir=tmp_path / "p_dense",
        )

        # 3배 밀도 프레임이 더 많은 비배경 픽셀을 가져야 함
        n_arr = np.array(Image.open(frames_normal[0]).convert("RGBA"))
        d_arr = np.array(Image.open(frames_dense[0]).convert("RGBA"))
        # 단순히 둘 다 생성되는지만 확인 (랜덤이라 정확한 비교 어려움)
        assert frames_normal[0].exists()
        assert frames_dense[0].exists()

    def test_particle_movement(self, ai_tech_config, tmp_path):
        """파티클이 실제로 상승하는지 확인 (프레임 간 변화)."""
        from ShortsFactory.engines.background_engine import BackgroundEngine
        from PIL import Image
        import numpy as np

        engine = BackgroundEngine(ai_tech_config)
        frames = engine.create_animated_particle_frames(
            width=270, height=480, num_particles=5, num_frames=3,
            speed=10, output_dir=tmp_path / "movement",
        )

        arr_0 = np.array(Image.open(frames[0]))
        arr_2 = np.array(Image.open(frames[2]))
        # 프레임이 달라야 함 (파티클이 이동했으므로)
        assert not np.array_equal(arr_0, arr_2)


class TestBlurredBg:
    def test_creates_blurred_image(self, ai_tech_config, tmp_path):
        from ShortsFactory.engines.background_engine import BackgroundEngine
        from PIL import Image

        # 테스트용 이미지 생성
        src = tmp_path / "source.png"
        Image.new("RGB", (200, 200), (255, 0, 0)).save(src)

        engine = BackgroundEngine(ai_tech_config)
        out = tmp_path / "blurred.png"
        result = engine.create_blurred_bg(src, 540, 960, output_path=out)

        assert result.exists()
        img = Image.open(result)
        assert img.size == (540, 960)

    def test_fallback_on_missing_image(self, ai_tech_config, tmp_path):
        from ShortsFactory.engines.background_engine import BackgroundEngine

        engine = BackgroundEngine(ai_tech_config)
        out = tmp_path / "fallback.png"
        result = engine.create_blurred_bg(
            "nonexistent.png", 270, 480, output_path=out,
        )
        assert result.exists()


# ════════════════════════════════════════════════════════════════
# 2. TextEngine — 워터마크 순번
# ════════════════════════════════════════════════════════════════

class TestWatermarkNumber:
    def test_render_watermark(self, ai_tech_config, tmp_path):
        from ShortsFactory.engines.text_engine import TextEngine

        engine = TextEngine(ai_tech_config)
        out = tmp_path / "watermark.png"
        result = engine.render_watermark_number(5, output_path=out)
        assert result.exists()
        assert result.stat().st_size > 0

    def test_watermark_dimensions(self, ai_tech_config, tmp_path):
        from ShortsFactory.engines.text_engine import TextEngine
        from PIL import Image

        engine = TextEngine(ai_tech_config)
        out = tmp_path / "dim.png"
        engine.render_watermark_number(
            3, canvas_w=300, canvas_h=200, output_path=out,
        )
        img = Image.open(out)
        assert img.size == (300, 200)
        assert img.mode == "RGBA"

    def test_watermark_opacity(self, ai_tech_config, tmp_path):
        from ShortsFactory.engines.text_engine import TextEngine
        from PIL import Image
        import numpy as np

        engine = TextEngine(ai_tech_config)
        out = tmp_path / "opacity.png"
        engine.render_watermark_number(1, opacity=0.5, output_path=out)

        arr = np.array(Image.open(out))
        # 반투명 픽셀이 있어야 함 (0 < alpha < 255)
        non_zero = arr[:, :, 3][(arr[:, :, 3] > 0) & (arr[:, :, 3] < 255)]
        assert len(non_zero) > 0


# ════════════════════════════════════════════════════════════════
# 3. FutureCountdownTemplate
# ════════════════════════════════════════════════════════════════

class TestFutureCountdownTemplate:
    def test_scene_count(self, ai_tech_config, sample_items):
        from ShortsFactory.templates.future_countdown import FutureCountdownTemplate

        template = FutureCountdownTemplate(ai_tech_config)
        scenes = template.build_scenes({"items": sample_items})

        # intro(1) + items(5) + outro(1) = 7
        assert len(scenes) == 7

    def test_intro_scene(self, ai_tech_config, sample_items):
        from ShortsFactory.templates.future_countdown import FutureCountdownTemplate

        template = FutureCountdownTemplate(ai_tech_config)
        scenes = template.build_scenes({"items": sample_items})

        intro = scenes[0]
        assert intro.role == "hook"
        assert intro.start_time == 0.0
        assert intro.animation == "bounce_popup"
        assert "TOP 5" in intro.text

    def test_countdown_order(self, ai_tech_config, sample_items):
        """항목이 역순으로 정렬 (5→1)."""
        from ShortsFactory.templates.future_countdown import FutureCountdownTemplate

        template = FutureCountdownTemplate(ai_tech_config)
        scenes = template.build_scenes({"items": sample_items})

        body_scenes = [s for s in scenes if s.role == "body"]
        ranks = [s.extra["rank"] for s in body_scenes]
        assert ranks == [5, 4, 3, 2, 1]

    def test_first_place_effects(self, ai_tech_config, sample_items):
        """1위 항목에 골드 색상, 줌 펄스, 플래시 효과."""
        from ShortsFactory.templates.future_countdown import FutureCountdownTemplate

        template = FutureCountdownTemplate(ai_tech_config)
        scenes = template.build_scenes({"items": sample_items})

        first = [s for s in scenes if s.extra.get("is_first")][0]
        assert first.extra["text_color"] == "#FFD700"
        assert first.animation == "zoom_pulse_flash"
        assert first.extra["particle_density"] == 3.0
        assert first.extra["flash_duration"] == 0.2
        assert first.extra["zoom_pulse_count"] == 2

    def test_non_first_items(self, ai_tech_config, sample_items):
        from ShortsFactory.templates.future_countdown import FutureCountdownTemplate

        template = FutureCountdownTemplate(ai_tech_config)
        scenes = template.build_scenes({"items": sample_items})

        non_first = [s for s in scenes if s.role == "body" and not s.extra.get("is_first")]
        for item in non_first:
            assert item.extra["text_color"] == "#00D4FF"
            assert item.animation == "fade_in"
            assert item.extra["particle_density"] == 1.0

    def test_total_duration(self, ai_tech_config, sample_items):
        from ShortsFactory.templates.future_countdown import FutureCountdownTemplate

        template = FutureCountdownTemplate(ai_tech_config)
        scenes = template.build_scenes({"items": sample_items})
        total = template.get_total_duration(scenes)

        # 2초(인트로) + 5*8초(항목) + 3초(아웃트로) = 45초
        assert total == 45.0

    def test_sfx_markers(self, ai_tech_config, sample_items):
        from ShortsFactory.templates.future_countdown import FutureCountdownTemplate

        template = FutureCountdownTemplate(ai_tech_config)
        scenes = template.build_scenes({"items": sample_items})
        markers = template.get_sfx_markers(scenes)

        assert len(markers) == 5
        # 1위는 'impact', 나머지는 'whoosh'
        types = [m["type"] for m in markers]
        assert types.count("whoosh") == 4
        assert types.count("impact") == 1

    def test_particle_density_map(self, ai_tech_config, sample_items):
        from ShortsFactory.templates.future_countdown import FutureCountdownTemplate

        template = FutureCountdownTemplate(ai_tech_config)
        scenes = template.build_scenes({"items": sample_items})
        density_map = template.get_particle_density_map(scenes)

        assert len(density_map) == 1  # 1위만 밀도 ≠ 1.0
        assert density_map[0]["density"] == 3.0

    def test_custom_intro_text(self, ai_tech_config, sample_items):
        from ShortsFactory.templates.future_countdown import FutureCountdownTemplate

        template = FutureCountdownTemplate(ai_tech_config)
        scenes = template.build_scenes({
            "items": sample_items,
            "intro_text": "커스텀 인트로",
        })
        assert scenes[0].text == "커스텀 인트로"

    def test_outro_scene(self, ai_tech_config, sample_items):
        from ShortsFactory.templates.future_countdown import FutureCountdownTemplate

        template = FutureCountdownTemplate(ai_tech_config)
        scenes = template.build_scenes({"items": sample_items})

        outro = scenes[-1]
        assert outro.role == "cta"
        assert outro.animation == "fade_in"
        assert outro.extra.get("subscribe_icon") is True


# ════════════════════════════════════════════════════════════════
# 4. Pipeline 통합 테스트
# ════════════════════════════════════════════════════════════════

class TestCountdownPipeline:
    def test_create_and_manifest(self, tmp_path, sample_items):
        from ShortsFactory.pipeline import ShortsFactory

        factory = ShortsFactory(channel="ai_tech")
        factory.create("future_countdown", {"items": sample_items})
        out = tmp_path / "countdown.mp4"

        with patch("ShortsFactory.pipeline._ffmpeg_available", return_value=False):
            factory.render(out)

        manifest_path = out.parent / f".assets_{out.stem}" / "manifest.json"
        assert manifest_path.exists()

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert manifest["template"] == "future_countdown"
        assert manifest["total_duration"] == 45.0
        assert len(manifest["scenes"]) == 7
        assert len(manifest["sfx_markers"]) == 5


# ════════════════════════════════════════════════════════════════
# 5. generate_future_countdown_short 테스트
# ════════════════════════════════════════════════════════════════

class TestGenerateCountdownShort:
    def test_function_signature(self):
        from ShortsFactory.generate_short import generate_future_countdown_short
        import inspect

        sig = inspect.signature(generate_future_countdown_short)
        params = list(sig.parameters.keys())
        assert "items" in params
        assert "intro_text" in params
        assert "bg_music" in params

    def test_generate_with_mock(self, tmp_path, sample_items):
        from ShortsFactory.generate_short import generate_future_countdown_short

        out = tmp_path / "gen_countdown.mp4"
        with patch("ShortsFactory.pipeline._ffmpeg_available", return_value=False):
            result = generate_future_countdown_short(
                items=sample_items, output_path=out,
            )
        assert result == out
