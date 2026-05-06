from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from conftest_render import _make_fake_clip, _make_render_step

from shorts_maker_v2.models import SceneAsset, ScenePlan
from shorts_maker_v2.pipeline.render_step import RenderStep

# ─── 전환 스타일 테스트 ────────────────────────────────────────────────────────


def test_pick_transition_style_random() -> None:
    """'random' 설정 시 유효한 스타일 반환."""
    step = _make_render_step(transition_style="random")
    valid_styles = {"crossfade", "flash", "glitch", "zoom", "slide", "wipe", "iris"}
    for _ in range(20):
        style = step._pick_transition_style()
        assert style in valid_styles


def test_pick_transition_style_fixed() -> None:
    """고정 스타일 설정 시 해당 스타일만 반환."""
    step = _make_render_step(transition_style="crossfade")
    assert step._pick_transition_style() == "crossfade"


def test_load_audio_clip_uses_moviepy_native_renderer_when_ffmpeg_backend_enabled() -> None:
    """최종 출력 backend가 ffmpeg여도 내부 조립용 로드는 MoviePy를 유지한다."""
    step = _make_render_step(video_renderer_backend="ffmpeg")
    native_audio = object()
    step._native_renderer.load_audio = MagicMock(return_value=MagicMock(native=native_audio))
    step._output_renderer.load_audio = MagicMock(return_value=MagicMock(native="should-not-be-used"))

    result = step._load_audio_clip("sample.mp3")

    assert result is native_audio
    step._native_renderer.load_audio.assert_called_once_with("sample.mp3")
    step._output_renderer.load_audio.assert_not_called()


def _ensure_fake_shorts_factory():
    """ShortsFactory가 sys.path에 없을 때 가짜 모듈을 sys.modules에 주입."""
    import sys

    if "ShortsFactory" not in sys.modules:
        fake_sf = MagicMock()
        sys.modules["ShortsFactory"] = fake_sf
        sys.modules["ShortsFactory.interfaces"] = fake_sf.interfaces


def test_try_render_with_adapter_success(tmp_path: Path) -> None:
    """RenderAdapter 성공 시 (True, None)과 올바른 payload를 반환한다."""
    _ensure_fake_shorts_factory()
    scene_plans = [
        ScenePlan(
            scene_id=1,
            narration_ko="테스트 내레이션",
            visual_prompt_en="test visual",
            target_sec=3.0,
            structure_role="hook",
        )
    ]
    scene_assets = [
        SceneAsset(
            scene_id=1,
            audio_path=str(tmp_path / "audio.mp3"),
            visual_type="image",
            visual_path=str(tmp_path / "image.png"),
            duration_sec=3.0,
        )
    ]
    mock_logger = MagicMock()
    mock_result = MagicMock(success=True, template_used="ai_news_breaking", duration_sec=3.2)

    with patch("ShortsFactory.interfaces.RenderAdapter") as adapter_cls:
        adapter_cls.return_value.render_with_plan.return_value = mock_result

        success, error = RenderStep.try_render_with_adapter(
            channel="ai_tech",
            scene_plans=scene_plans,
            scene_assets=scene_assets,
            output_path=tmp_path / "output.mp4",
            logger=mock_logger,
        )

    assert success is True
    assert error is None
    adapter_cls.return_value.render_with_plan.assert_called_once_with(
        channel_id="ai_tech",
        scenes=[scene_plans[0].to_dict()],
        assets={1: str(tmp_path / "image.png")},
        output_path=tmp_path / "output.mp4",
        audio_paths={1: str(tmp_path / "audio.mp3")},
    )


def test_try_render_with_adapter_failure_returns_error(tmp_path: Path) -> None:
    """RenderAdapter 실패 시 native render_step 폴백용 에러를 반환한다."""
    _ensure_fake_shorts_factory()
    mock_logger = MagicMock()
    mock_result = MagicMock(success=False, error="sf failed")

    with patch("ShortsFactory.interfaces.RenderAdapter") as adapter_cls:
        adapter_cls.return_value.render_with_plan.return_value = mock_result

        success, error = RenderStep.try_render_with_adapter(
            channel="ai_tech",
            scene_plans=[],
            scene_assets=[],
            output_path=tmp_path / "output.mp4",
            logger=mock_logger,
        )

    assert success is False
    assert error == "sf failed"


# ─── 썸네일 추출 테스트 ──────────────────────────────────────────────────


def test_extract_thumbnail_returns_none_for_missing_file(tmp_path: Path) -> None:
    """존재하지 않는 비디오 → None 반환 (에러 없이)."""
    result = RenderStep.extract_thumbnail(
        tmp_path / "nonexistent.mp4",
        tmp_path / "thumb.png",
    )
    assert result is None


def test_extract_thumbnail_returns_none_for_invalid_file(tmp_path: Path) -> None:
    """잘못된 비디오 파일 → None 반환."""
    bad_video = tmp_path / "bad.mp4"
    bad_video.write_bytes(b"\x00" * 100)
    result = RenderStep.extract_thumbnail(bad_video, tmp_path / "thumb.png")
    assert result is None


# ─── 유틸리티 메서드 테스트 ────────────────────────────────────────────────────


def test_fit_vertical_scales_and_crops() -> None:
    """_fit_vertical은 scale/crop 로직을 수행한다."""
    clip = _make_fake_clip(w=800, h=600)
    clip.resized = MagicMock(return_value=clip)
    clip.cropped = MagicMock(return_value=clip)
    RenderStep._fit_vertical(clip, 1080, 1920)
    clip.resized.assert_called_once()
    clip.cropped.assert_called_once()


def test_build_bookend_clip_missing_file() -> None:
    """존재하지 않는 파일 → None 반환."""
    step = _make_render_step()
    result = step._build_bookend_clip("/nonexistent/file.mp4", 2.0, 1080, 1920)
    assert result is None


def test_build_bookend_clip_unsupported_ext(tmp_path: Path) -> None:
    """지원하지 않는 확장자 → None 반환."""
    step = _make_render_step()
    txt = tmp_path / "intro.txt"
    txt.write_text("hello")
    result = step._build_bookend_clip(str(txt), 2.0, 1080, 1920)
    assert result is None


# ─── Quality Profile 테스트 ──────────────────────────────────────────────────


def test_quality_profiles_exist() -> None:
    """3개 프로파일(draft/standard/premium)이 존재한다."""
    from shorts_maker_v2.pipeline.render_step import _QUALITY_PROFILES

    assert "draft" in _QUALITY_PROFILES
    assert "standard" in _QUALITY_PROFILES
    assert "premium" in _QUALITY_PROFILES
    assert _QUALITY_PROFILES["premium"]["crf"] < _QUALITY_PROFILES["standard"]["crf"]


# ═══════════════════════════════════════════════════════════════════════════════
# 추가 커버리지 테스트 (누락 분기 보완)
# ═══════════════════════════════════════════════════════════════════════════════


# ─── _QUALITY_PROFILES 상세 ──────────────────────────────────────────────────


def test_quality_profiles_have_expected_keys() -> None:
    """모든 프로파일에 crf/preset/maxrate 키가 존재한다."""
    from shorts_maker_v2.pipeline.render_step import _QUALITY_PROFILES

    for name in ("draft", "standard", "premium"):
        profile = _QUALITY_PROFILES[name]
        assert "crf" in profile
        assert "preset" in profile
        assert "maxrate" in profile


def test_quality_profiles_crf_ordering() -> None:
    """draft > standard > premium CRF 순서."""
    from shorts_maker_v2.pipeline.render_step import _QUALITY_PROFILES

    assert _QUALITY_PROFILES["draft"]["crf"] > _QUALITY_PROFILES["standard"]["crf"]
    assert _QUALITY_PROFILES["standard"]["crf"] > _QUALITY_PROFILES["premium"]["crf"]


# ─── _load_channel_profile ──────────────────────────────────────────────────


def test_load_channel_profile_empty_key_returns_empty_dict() -> None:
    """빈 channel_key → {} 반환."""
    assert RenderStep._load_channel_profile("") == {}


def test_load_channel_profile_import_fails_returns_empty_dict() -> None:
    """ChannelRouter import 실패 → {} 반환."""
    with patch(
        "shorts_maker_v2.utils.channel_router.ChannelRouter",
        side_effect=ImportError("no module"),
    ):
        result = RenderStep._load_channel_profile("ai_tech")
    assert result == {}


def test_load_channel_profile_exception_returns_empty_dict() -> None:
    """ChannelRouter.get_profile() 예외 → {} 반환."""
    mock_router = MagicMock()
    mock_router.return_value.get_profile.side_effect = ValueError("bad key")
    with patch(
        "shorts_maker_v2.utils.channel_router.ChannelRouter",
        mock_router,
    ):
        result = RenderStep._load_channel_profile("ai_tech")
    assert result == {}


# ─── _fit_vertical ──────────────────────────────────────────────────────────


def test_fit_vertical_narrower_clip_scales_up() -> None:
    """클립이 타겟보다 좁으면 스케일업 후 크롭."""
    mock_clip = MagicMock()
    mock_clip.w = 540
    mock_clip.h = 960
    mock_resized = MagicMock()
    mock_resized.w = 1080
    mock_resized.h = 1920
    mock_clip.resized.return_value = mock_resized
    mock_cropped = MagicMock()
    mock_resized.cropped.return_value = mock_cropped

    result = RenderStep._fit_vertical(mock_clip, 1080, 1920)
    mock_clip.resized.assert_called_once_with(2.0)
    assert result is mock_cropped


def test_fit_vertical_wider_clip_scales_and_crops() -> None:
    """클립이 타겟보다 넓으면 스케일 후 가로 크롭."""
    mock_clip = MagicMock()
    mock_clip.w = 1920
    mock_clip.h = 1080
    scale = max(1080 / 1920, 1920 / 1080)
    mock_resized = MagicMock()
    mock_resized.w = int(1920 * scale)
    mock_resized.h = int(1080 * scale)
    mock_clip.resized.return_value = mock_resized
    mock_cropped = MagicMock()
    mock_resized.cropped.return_value = mock_cropped

    result = RenderStep._fit_vertical(mock_clip, 1080, 1920)
    actual_scale = mock_clip.resized.call_args[0][0]
    assert actual_scale == pytest.approx(scale, abs=0.01)
    assert result is mock_cropped


# ─── _build_bookend_clip 이미지 경로 ────────────────────────────────────────


def test_build_bookend_clip_image_calls_load_image(tmp_path: Path) -> None:
    """이미지 확장자 → _load_image_clip 호출."""
    img_file = tmp_path / "intro.png"
    img_file.write_bytes(b"\x89PNG" + b"\x00" * 100)
    step = _make_render_step()
    mock_clip = MagicMock()
    mock_clip.w = 1080
    mock_clip.h = 1920
    mock_clip.duration = 2.0
    mock_resized = MagicMock()
    mock_resized.w = 1080
    mock_resized.h = 1920
    mock_clip.resized.return_value = mock_resized
    mock_resized.cropped.return_value = mock_resized
    step._native_renderer.load_image = MagicMock(
        return_value=MagicMock(native=mock_clip),
    )
    result = step._build_bookend_clip(str(img_file), 2.0, 1080, 1920)
    assert result is not None


# ─── _build_base_clip ──────────────────────────────────────────────────────


def test_build_base_clip_image_type() -> None:
    """이미지 타입 에셋 → _load_image_clip 호출."""
    step = _make_render_step()
    mock_clip = MagicMock()
    mock_clip.w = 1080
    mock_clip.h = 1920
    mock_clip.duration = 3.0
    mock_clip.resized.return_value = mock_clip
    mock_clip.cropped.return_value = mock_clip
    step._native_renderer.load_image = MagicMock(
        return_value=MagicMock(native=mock_clip),
    )
    asset = MagicMock()
    asset.visual_type = "image"
    asset.visual_path = "/tmp/test.png"
    result = step._build_base_clip(asset, 3.0, 1080, 1920)
    assert result is not None


def test_build_base_clip_video_type_shorter() -> None:
    """비디오 타입이 목표보다 짧으면 Loop 효과."""
    step = _make_render_step()
    mock_clip = MagicMock()
    mock_clip.w = 1080
    mock_clip.h = 1920
    mock_clip.duration = 2.0  # shorter than target
    mock_clip.resized.return_value = mock_clip
    mock_clip.cropped.return_value = mock_clip
    looped = MagicMock()
    looped.w = 1080
    looped.h = 1920
    looped.resized.return_value = looped
    looped.cropped.return_value = looped
    mock_clip.with_effects.return_value = looped
    step._native_renderer.load_video = MagicMock(
        return_value=MagicMock(native=mock_clip),
    )
    asset = MagicMock()
    asset.visual_type = "video"
    asset.visual_path = "/tmp/test.mp4"
    result = step._build_base_clip(asset, 5.0, 1080, 1920)
    mock_clip.with_effects.assert_called_once()
    assert result is not None


def test_build_base_clip_video_type_longer() -> None:
    """비디오 타입이 목표보다 길면 subclip."""
    step = _make_render_step()
    mock_clip = MagicMock()
    mock_clip.w = 1080
    mock_clip.h = 1920
    mock_clip.duration = 10.0  # longer than target
    subclipped = MagicMock()
    subclipped.w = 1080
    subclipped.h = 1920
    subclipped.resized.return_value = subclipped
    subclipped.cropped.return_value = subclipped
    mock_clip.subclipped.return_value = subclipped
    mock_clip.resized.return_value = mock_clip
    mock_clip.cropped.return_value = mock_clip
    step._native_renderer.load_video = MagicMock(
        return_value=MagicMock(native=mock_clip),
    )
    asset = MagicMock()
    asset.visual_type = "video"
    asset.visual_path = "/tmp/test.mp4"
    result = step._build_base_clip(asset, 5.0, 1080, 1920)
    mock_clip.subclipped.assert_called_once_with(0, 5.0)
    assert result is not None


# ─── _load_video_clip / _load_image_clip ────────────────────────────────────


def test_load_video_clip_returns_native() -> None:
    """_load_video_clip → native clip 반환."""
    step = _make_render_step()
    native_clip = object()
    step._native_renderer.load_video = MagicMock(
        return_value=MagicMock(native=native_clip),
    )
    result = step._load_video_clip("/tmp/test.mp4")
    assert result is native_clip


def test_load_image_clip_returns_native() -> None:
    """_load_image_clip → native clip 반환."""
    step = _make_render_step()
    native_clip = object()
    step._native_renderer.load_image = MagicMock(
        return_value=MagicMock(native=native_clip),
    )
    result = step._load_image_clip("/tmp/test.png", duration=3.0)
    assert result is native_clip
    step._native_renderer.load_image.assert_called_once_with(
        "/tmp/test.png",
        duration=3.0,
    )


def test_try_render_with_adapter_import_failure_returns_error(tmp_path: Path) -> None:
    """Import failure should return a native fallback error."""
    import builtins

    original_import = builtins.__import__

    def _blocking_import(name, *args, **kwargs):
        if name == "ShortsFactory.interfaces":
            raise ImportError("adapter unavailable")
        return original_import(name, *args, **kwargs)

    with patch("builtins.__import__", side_effect=_blocking_import):
        success, error = RenderStep.try_render_with_adapter(
            channel="ai_tech",
            scene_plans=[],
            scene_assets=[],
            output_path=tmp_path / "output.mp4",
            logger=MagicMock(),
        )

    assert success is False
    assert error == "adapter unavailable"


def test_extract_thumbnail_success_writes_png(tmp_path: Path) -> None:
    """Thumbnail extraction should save a PNG when frame capture succeeds."""
    import numpy as np

    frame = np.zeros((4, 4, 3), dtype=np.uint8)
    clip = MagicMock(duration=1.2)
    clip.get_frame.return_value = frame
    output_path = tmp_path / "thumb.png"

    with patch("shorts_maker_v2.pipeline.render_captions.VideoFileClip", return_value=clip):
        result = RenderStep.extract_thumbnail(
            tmp_path / "video.mp4",
            output_path,
            timestamp_sec=0.5,
        )

    assert result == output_path
    assert output_path.exists()
    clip.close.assert_called_once()
