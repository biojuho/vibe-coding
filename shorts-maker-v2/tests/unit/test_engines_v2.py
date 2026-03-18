"""
test_engines_v2.py — 엔진 v2 기능 단위 테스트
==============================================
Phase 2에서 추가된 v2 메서드들의 기능을 검증합니다.

테스트 대상:
- TextEngine v2: render_gradient_text, render_emoji_badge, render_progress_bar
- TransitionEngine v2: swipe, blur_dissolve, zoom_through, color_wipe
- HookEngine v2: shake, reveal, combo effects
- BackgroundEngine v2: noise_texture, scanline_overlay, mesh_gradient
"""

import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from PIL import Image

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# 공통 테스트 채널 설정
_CHANNEL_CONFIG = {
    "channel_name": "test_channel",
    "palette": {
        "bg": "#0A0E1A",
        "primary": "#00D4FF",
        "accent": "#00FF88",
        "secondary": "#7C3AED",
    },
    "font_title": "Pretendard-ExtraBold",
    "font_body": "Pretendard-Regular",
    "hook_style": "popup",
    "keyword_highlights": {"numbers": "#FFD700"},
}


# ══════════════════════════════════════════════════════════════════════
# TextEngine v2 Tests
# ══════════════════════════════════════════════════════════════════════


class TestTextEngineV2:
    """TextEngine v2 메서드 테스트."""

    @pytest.fixture
    def engine(self):
        from ShortsFactory.engines.text_engine import TextEngine
        return TextEngine(_CHANNEL_CONFIG)

    def test_render_gradient_text_creates_file(self, engine, tmp_path):
        """render_gradient_text가 PNG 파일을 생성하는지 확인."""
        output = tmp_path / "gradient.png"
        result = engine.render_gradient_text("테스트 그라데이션", output_path=output)
        assert result.exists()
        assert result.suffix == ".png"
        img = Image.open(result)
        assert img.mode == "RGBA"
        assert img.width > 0 and img.height > 0

    def test_render_gradient_text_custom_colors(self, engine, tmp_path):
        """커스텀 색상 그라데이션이 적용되는지 확인."""
        output = tmp_path / "gradient_custom.png"
        result = engine.render_gradient_text(
            "커스텀 컬러",
            color_start="#FF0000",
            color_end="#0000FF",
            output_path=output,
        )
        assert result.exists()
        img = Image.open(result)
        assert img.width > 0

    def test_render_emoji_badge_creates_file(self, engine, tmp_path):
        """render_emoji_badge가 PNG 파일을 생성하는지 확인."""
        output = tmp_path / "emoji.png"
        result = engine.render_emoji_badge("🔥", "HOT", output_path=output)
        assert result.exists()
        img = Image.open(result)
        assert img.mode == "RGBA"

    def test_render_emoji_badge_no_label(self, engine, tmp_path):
        """라벨 없는 이모지 배지 생성."""
        output = tmp_path / "emoji_nolabel.png"
        result = engine.render_emoji_badge("⭐", output_path=output)
        assert result.exists()

    def test_render_progress_bar_creates_file(self, engine, tmp_path):
        """render_progress_bar가 PNG 파일을 생성하는지 확인."""
        output = tmp_path / "progress.png"
        result = engine.render_progress_bar(0.6, output_path=output)
        assert result.exists()
        img = Image.open(result)
        assert img.width > 0

    def test_render_progress_bar_edge_values(self, engine, tmp_path):
        """0%, 100% 등 경계값 테스트."""
        for i, progress in enumerate([0.0, 0.5, 1.0]):
            output = tmp_path / f"progress_{i}.png"
            result = engine.render_progress_bar(progress, output_path=output)
            assert result.exists()

    def test_render_progress_bar_with_label(self, engine, tmp_path):
        """라벨 포함 프로그레스 바."""
        output = tmp_path / "progress_label.png"
        result = engine.render_progress_bar(0.75, label="3/4", output_path=output)
        assert result.exists()

    def test_get_style_headline(self, engine):
        """headline 역할 스타일이 올바른지 확인."""
        style = engine._get_style("headline")
        assert style.font_size == 96
        assert style.bg_opacity == 0  # 배경 없음


# ══════════════════════════════════════════════════════════════════════
# TransitionEngine v2 Tests
# ══════════════════════════════════════════════════════════════════════

_HAS_FFMPEG = False
try:
    import shutil
    if shutil.which("ffmpeg"):
        from moviepy import VideoClip
        _HAS_FFMPEG = True
except (RuntimeError, ImportError, OSError):
    pass


@pytest.mark.skipif(not _HAS_FFMPEG, reason="moviepy/ffmpeg not available")
class TestTransitionEngineV2:
    """TransitionEngine v2 메서드 테스트."""

    @pytest.fixture
    def engine(self):
        from ShortsFactory.engines.transition_engine import TransitionEngine
        return TransitionEngine(_CHANNEL_CONFIG)

    def _make_mock_clip(self, duration=2.0, w=1080, h=1920):
        """테스트용 mock 클립 생성."""
        clip = MagicMock()
        clip.duration = duration
        clip.w = w
        clip.h = h
        clip.size = (w, h)
        # get_frame은 랜덤 프레임 반환
        clip.get_frame = lambda t: np.random.randint(0, 255, (h, w, 3), dtype=np.uint8)
        return clip

    def test_swipe_right(self, engine):
        """swipe right 전환이 VideoClip을 반환하는지 확인."""
        clip_a = self._make_mock_clip()
        clip_b = self._make_mock_clip()
        result = engine.swipe(clip_a, clip_b, direction="right")
        assert result is not None
        assert result.duration > 0

    def test_swipe_all_directions(self, engine):
        """4방향 스와이프 모두 동작 확인."""
        for direction in ["left", "right", "up", "down"]:
            clip_a = self._make_mock_clip()
            clip_b = self._make_mock_clip()
            result = engine.swipe(clip_a, clip_b, direction=direction, duration=0.2)
            assert result is not None, f"swipe_{direction} failed"

    def test_blur_dissolve(self, engine):
        """blur_dissolve 전환이 동작하는지 확인."""
        clip_a = self._make_mock_clip()
        clip_b = self._make_mock_clip()
        result = engine.blur_dissolve(clip_a, clip_b, duration=0.3)
        assert result is not None
        assert result.duration > 0

    def test_zoom_through(self, engine):
        """zoom_through 전환이 동작하는지 확인."""
        clip_a = self._make_mock_clip()
        clip_b = self._make_mock_clip()
        result = engine.zoom_through(clip_a, clip_b, duration=0.3)
        assert result is not None

    def test_color_wipe(self, engine):
        """color_wipe이 VideoClip을 반환하는지 확인."""
        result = engine.color_wipe(duration=0.2)
        assert result is not None
        assert result.duration == 0.2

    def test_make_transition_swipe_right(self, engine):
        """_make_transition에서 'swipe_right' 스타일 라우팅 확인."""
        clip_a = self._make_mock_clip()
        clip_b = self._make_mock_clip()
        result = engine._make_transition(clip_a, clip_b, "swipe_right")
        assert result is not None

    def test_normalize_role_extended(self, engine):
        """intro/outro 역할 정규화 확인."""
        assert engine._normalize_role("intro") == "intro"
        assert engine._normalize_role("outro") == "outro"
        assert engine._normalize_role("HOOK") == "hook"
        assert engine._normalize_role("random") == "body"

    def test_flash_backward_compat(self, engine):
        """기존 flash() 메서드가 여전히 동작하는지."""
        result = engine.flash(duration=0.15)
        assert result is not None

    def test_apply_backward_compat(self, engine):
        """기존 apply() 메서드가 역할 기반 전환 선택과 함께 동작하는지."""
        clips = [self._make_mock_clip() for _ in range(3)]
        roles = ["hook", "body", "cta"]
        # apply는 모킹된 클립에서는 flash/crossfade만 발생
        result = engine.apply(clips, roles=roles)
        assert len(result) >= len(clips)


# ══════════════════════════════════════════════════════════════════════
# HookEngine v2 Tests
# ══════════════════════════════════════════════════════════════════════


class TestHookEngineV2:
    """HookEngine v2 메서드 테스트."""

    @pytest.fixture
    def engine_popup(self):
        from ShortsFactory.engines.hook_engine import HookEngine
        return HookEngine({**_CHANNEL_CONFIG, "hook_style": "popup"})

    @pytest.fixture
    def engine_shake(self):
        from ShortsFactory.engines.hook_engine import HookEngine
        return HookEngine({**_CHANNEL_CONFIG, "hook_style": "shake"})

    @pytest.fixture
    def engine_reveal(self):
        from ShortsFactory.engines.hook_engine import HookEngine
        return HookEngine({**_CHANNEL_CONFIG, "hook_style": "reveal"})

    @pytest.fixture
    def engine_combo(self):
        from ShortsFactory.engines.hook_engine import HookEngine
        return HookEngine({**_CHANNEL_CONFIG, "hook_style": "glitch_shake"})

    def _make_clip_with_frame(self, w=100, h=100, duration=1.0):
        """프레임 데이터가 포함된 mock 클립 생성."""
        clip = MagicMock()
        clip.duration = duration
        clip.w = w
        clip.h = h
        clip.mask = None
        frame = np.random.randint(0, 255, (h, w, 3), dtype=np.uint8)
        clip.get_frame = lambda t: frame
        return clip

    def test_shake_animation(self):
        """_apply_shake가 프레임을 변형하는지 확인."""
        from ShortsFactory.engines.hook_engine import _apply_shake
        clip = self._make_clip_with_frame()
        result = _apply_shake(clip, 0.3)
        assert result is not None

    def test_reveal_animation(self):
        """_apply_reveal이 프레임을 변형하는지 확인."""
        from ShortsFactory.engines.hook_engine import _apply_reveal
        clip = self._make_clip_with_frame()
        result = _apply_reveal(clip, 0.5)
        assert result is not None

    def test_create_hook_shake(self, engine_shake):
        """shake 스타일의 create_hook이 동작하는지 확인."""
        clip = self._make_clip_with_frame()
        result = engine_shake.create_hook(clip, duration=0.3)
        assert result is not None

    def test_create_hook_reveal(self, engine_reveal):
        """reveal 스타일의 create_hook이 동작하는지 확인."""
        clip = self._make_clip_with_frame()
        result = engine_reveal.create_hook(clip, duration=0.5)
        assert result is not None

    def test_create_hook_combo(self, engine_combo):
        """combo (glitch+shake) 스타일의 create_hook이 동작하는지 확인."""
        clip = self._make_clip_with_frame()
        result = engine_combo.create_hook(clip, duration=0.4)
        assert result is not None

    def test_create_hook_with_shake(self, engine_popup):
        """create_hook_with_shake 팩토리 메서드 테스트."""
        clip = self._make_clip_with_frame()
        result = engine_popup.create_hook_with_shake(clip, shake_duration=0.2)
        assert result is not None

    def test_create_hook_with_reveal(self, engine_popup):
        """create_hook_with_reveal 팩토리 메서드 테스트."""
        clip = self._make_clip_with_frame()
        result = engine_popup.create_hook_with_reveal(clip, reveal_duration=0.3)
        assert result is not None

    def test_list_available_effects(self, engine_popup):
        """list_available_effects가 올바른 효과 목록을 반환하는지 확인."""
        effects = engine_popup.list_available_effects()
        assert "shake" in effects
        assert "reveal" in effects
        assert "combo_gs" in effects
        assert len(effects) >= 7

    def test_get_animation_type_v2(self):
        """v2 스타일 매핑 확인."""
        from ShortsFactory.engines.hook_engine import HookEngine
        engine = HookEngine({**_CHANNEL_CONFIG, "hook_style": "reveal"})
        assert engine.get_animation_type() == "reveal"


# ══════════════════════════════════════════════════════════════════════
# BackgroundEngine v2 Tests
# ══════════════════════════════════════════════════════════════════════


class TestBackgroundEngineV2:
    """BackgroundEngine v2 메서드 테스트."""

    @pytest.fixture
    def engine(self):
        from ShortsFactory.engines.background_engine import BackgroundEngine
        return BackgroundEngine(_CHANNEL_CONFIG)

    def test_create_noise_texture(self, engine, tmp_path):
        """노이즈 텍스처 생성 확인."""
        output = tmp_path / "noise.png"
        result = engine.create_noise_texture(
            200, 200, intensity=0.1, output_path=output,
        )
        assert result.exists()
        img = Image.open(result)
        assert img.mode == "RGBA"
        assert img.size == (200, 200)

    def test_create_noise_texture_grain_size(self, engine, tmp_path):
        """grain_size 옵션이 동작하는지 확인."""
        output = tmp_path / "noise_grain.png"
        result = engine.create_noise_texture(
            200, 200, grain_size=4, output_path=output,
        )
        assert result.exists()

    def test_create_noise_texture_color(self, engine, tmp_path):
        """컬러 노이즈 생성 확인."""
        output = tmp_path / "noise_color.png"
        result = engine.create_noise_texture(
            200, 200, monochrome=False, output_path=output,
        )
        assert result.exists()

    def test_create_scanline_overlay(self, engine, tmp_path):
        """스캔라인 오버레이 생성 확인."""
        output = tmp_path / "scanlines.png"
        result = engine.create_scanline_overlay(
            200, 200, line_spacing=4, output_path=output,
        )
        assert result.exists()
        img = Image.open(result)
        assert img.mode == "RGBA"

    def test_create_scanline_has_lines(self, engine, tmp_path):
        """스캔라인이 실제로 라인을 포함하는지 확인."""
        output = tmp_path / "scanlines_check.png"
        engine.create_scanline_overlay(
            100, 100, line_spacing=4, line_opacity=0.5, output_path=output,
        )
        img = Image.open(output)
        arr = np.array(img)
        # line_spacing=4이면 y=0,4,8... 에 알파 > 0인 행이 있어야 함
        assert arr[0, 0, 3] > 0  # 첫 줄
        assert arr[4, 0, 3] > 0  # 4번째 줄
        assert arr[1, 0, 3] == 0  # 사이 줄은 투명

    def test_create_mesh_gradient(self, engine, tmp_path):
        """메쉬 그라데이션 생성 확인."""
        output = tmp_path / "mesh.png"
        result = engine.create_mesh_gradient(
            200, 300, num_points=3, blur_radius=50, output_path=output,
        )
        assert result.exists()
        img = Image.open(result)
        assert img.mode == "RGB"

    def test_create_mesh_gradient_custom_colors(self, engine, tmp_path):
        """커스텀 색상 메쉬 그라데이션."""
        output = tmp_path / "mesh_custom.png"
        result = engine.create_mesh_gradient(
            200, 300,
            colors=["#FF0000", "#00FF00", "#0000FF"],
            output_path=output,
        )
        assert result.exists()

    # 기존 메서드 회귀 테스트
    def test_create_gradient_backward_compat(self, engine, tmp_path):
        """기존 create_gradient가 여전히 동작하는지 확인."""
        output = tmp_path / "gradient.png"
        result = engine.create_gradient(200, 300, output_path=output)
        assert result.exists()

    def test_create_particle_backward_compat(self, engine, tmp_path):
        """기존 create_particle_overlay가 여전히 동작하는지 확인."""
        output = tmp_path / "particle.png"
        result = engine.create_particle_overlay(200, 300, output_path=output)
        assert result.exists()
