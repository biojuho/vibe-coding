"""Tests for MediaStep pure/static helper methods."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from shorts_maker_v2.models import ScenePlan
from shorts_maker_v2.pipeline.media_step import MediaStep


def _make_step(
    job_index: int = 0,
    tts_voice_pool: list[str] | None = None,
    tts_voice_strategy: str = "fixed",
    tts_voice: str = "alloy",
    visual_styles: list[str] | None = None,
    image_style_prefix: str = "",
    max_retries: int = 2,
) -> MediaStep:
    """Create a MediaStep with dummy dependencies."""
    config = MagicMock()
    config.providers.tts_voice_pool = tts_voice_pool or []
    config.providers.tts_voice_strategy = tts_voice_strategy
    config.providers.tts_voice = tts_voice
    config.providers.visual_styles = visual_styles or []
    config.providers.image_style_prefix = image_style_prefix
    config.limits.max_retries = max_retries
    config.cache.dir = "/tmp/test_cache"
    config.cache.enabled = False
    config.cache.max_size_mb = 100
    config._channel_key = ""
    return MediaStep(
        config=config,
        openai_client=MagicMock(),
        google_client=None,
        pexels_client=None,
        job_index=job_index,
    )


def _make_scene(
    scene_id: int = 1,
    visual_prompt_en: str = "mountain landscape",
    structure_role: str = "body",
    target_sec: float = 5.0,
) -> ScenePlan:
    return ScenePlan(
        scene_id=scene_id,
        narration_ko="나레이션",
        visual_prompt_en=visual_prompt_en,
        target_sec=target_sec,
        structure_role=structure_role,
    )


class TestSceneIdFromPath:
    def test_extracts_scene_id_from_scene_05(self) -> None:
        path = Path("/some/dir/scene_05.mp3")
        assert MediaStep._scene_id_from_path(path) == 5

    def test_extracts_scene_id_from_scene_12(self) -> None:
        path = Path("/some/dir/scene_12.png")
        assert MediaStep._scene_id_from_path(path) == 12

    def test_returns_none_when_no_scene_pattern(self) -> None:
        path = Path("/some/dir/background_music.mp3")
        assert MediaStep._scene_id_from_path(path) is None

    def test_returns_none_for_empty_stem(self) -> None:
        path = Path("/some/dir/.hidden")
        assert MediaStep._scene_id_from_path(path) is None

    def test_extracts_first_match_when_multiple(self) -> None:
        # Only the first `scene_(\d+)` is captured
        path = Path("/some/dir/scene_03_backup_scene_07.mp3")
        assert MediaStep._scene_id_from_path(path) == 3

    def test_single_digit_scene_id(self) -> None:
        path = Path("/runs/abc/scene_1.mp3")
        assert MediaStep._scene_id_from_path(path) == 1


class TestLogDispatch:
    def test_info_calls_info_on_logger(self) -> None:
        mock_logger = MagicMock()
        MediaStep._log(mock_logger, "info", "test_event", key="value")
        mock_logger.info.assert_called_once_with("test_event", key="value")

    def test_warning_calls_warning_on_logger(self) -> None:
        mock_logger = MagicMock()
        MediaStep._log(mock_logger, "warning", "warn_event")
        mock_logger.warning.assert_called_once_with("warn_event")

    def test_none_logger_is_noop(self) -> None:
        # Should not raise
        MediaStep._log(None, "info", "test_event")

    def test_unknown_level_is_noop(self) -> None:
        mock_logger = MagicMock(spec=[])  # no methods
        # getattr returns None for missing attrs, callable(None) is False → noop
        MediaStep._log(mock_logger, "debug", "test_event")


class TestPrepareDirs:
    def test_creates_audio_image_video_dirs(self, tmp_path: Path) -> None:
        audio_dir, image_dir, video_dir = MediaStep._prepare_dirs(tmp_path)
        assert audio_dir.exists() and audio_dir.is_dir()
        assert image_dir.exists() and image_dir.is_dir()
        assert video_dir.exists() and video_dir.is_dir()

    def test_returns_correct_paths(self, tmp_path: Path) -> None:
        audio_dir, image_dir, video_dir = MediaStep._prepare_dirs(tmp_path)
        assert audio_dir == tmp_path / "media" / "audio"
        assert image_dir == tmp_path / "media" / "images"
        assert video_dir == tmp_path / "media" / "videos"

    def test_idempotent_on_existing_dirs(self, tmp_path: Path) -> None:
        MediaStep._prepare_dirs(tmp_path)
        # Second call must not raise
        audio_dir, image_dir, video_dir = MediaStep._prepare_dirs(tmp_path)
        assert audio_dir.exists()


class TestResolveRetryAttempts:
    def test_no_override_returns_config_max_retries(self) -> None:
        step = _make_step(max_retries=3)
        assert step._resolve_retry_attempts(None) == 3

    def test_override_clamps_below_one_to_one(self) -> None:
        step = _make_step(max_retries=3)
        assert step._resolve_retry_attempts(0) == 1

    def test_override_negative_clamps_to_one(self) -> None:
        step = _make_step(max_retries=3)
        assert step._resolve_retry_attempts(-5) == 1

    def test_override_positive_returned_as_is(self) -> None:
        step = _make_step(max_retries=3)
        assert step._resolve_retry_attempts(7) == 7


class TestBuildVisualPrompt:
    def test_hook_role_includes_eye_catching_guide(self) -> None:
        step = _make_step(image_style_prefix="cinematic")
        scene = _make_scene(visual_prompt_en="mountain at night", structure_role="hook")
        result = step._build_visual_prompt(scene, color_hint="")
        assert "HOOK" in result
        assert "mountain at night" in result

    def test_body_role_has_no_special_guide(self) -> None:
        step = _make_step(image_style_prefix="")
        scene = _make_scene(visual_prompt_en="office desk", structure_role="body")
        result = step._build_visual_prompt(scene, color_hint="")
        # 'body' is not in _ROLE_VISUAL_GUIDE → no role prefix
        assert "office desk" in result
        assert "BODY" not in result

    def test_color_hint_included_for_non_hook_roles(self) -> None:
        step = _make_step(image_style_prefix="")
        scene = _make_scene(visual_prompt_en="sunset", structure_role="closing")
        result = step._build_visual_prompt(scene, color_hint="blue-purple")
        assert "blue-purple" in result

    def test_color_hint_excluded_for_hook_role(self) -> None:
        step = _make_step(image_style_prefix="")
        scene = _make_scene(visual_prompt_en="dramatic landscape", structure_role="hook")
        result = step._build_visual_prompt(scene, color_hint="warm orange")
        # hook should NOT include color hint
        assert "warm orange" not in result

    def test_style_prefix_prepended(self) -> None:
        step = _make_step(image_style_prefix="hyperrealistic 8K")
        scene = _make_scene(visual_prompt_en="forest", structure_role="body")
        result = step._build_visual_prompt(scene, color_hint="")
        assert "hyperrealistic 8K" in result

    def test_empty_prompt_with_no_guide_returns_visual_prompt(self) -> None:
        step = _make_step(image_style_prefix="")
        scene = _make_scene(visual_prompt_en="just a prompt", structure_role="body")
        result = step._build_visual_prompt(scene, color_hint="")
        assert result == "just a prompt"


class TestTtsVoiceSelection:
    def test_rotate_strategy_uses_job_index_modulo(self) -> None:
        pool = ["alloy", "nova", "shimmer"]
        step0 = _make_step(tts_voice_pool=pool, tts_voice_strategy="rotate", job_index=0)
        step1 = _make_step(tts_voice_pool=pool, tts_voice_strategy="rotate", job_index=1)
        step3 = _make_step(tts_voice_pool=pool, tts_voice_strategy="rotate", job_index=3)
        assert step0._tts_voice == "alloy"
        assert step1._tts_voice == "nova"
        assert step3._tts_voice == "alloy"  # 3 % 3 == 0

    def test_fixed_strategy_uses_config_voice(self) -> None:
        step = _make_step(tts_voice="echo", tts_voice_strategy="fixed")
        assert step._tts_voice == "echo"

    def test_empty_pool_uses_config_voice(self) -> None:
        step = _make_step(tts_voice="fable", tts_voice_pool=[], tts_voice_strategy="rotate")
        assert step._tts_voice == "fable"


class TestVisualStyleSelection:
    def test_styles_list_rotates_by_job_index(self) -> None:
        styles = ["photorealistic", "oil painting", "watercolor"]
        step0 = _make_step(visual_styles=styles, job_index=0)
        step1 = _make_step(visual_styles=styles, job_index=1)
        step3 = _make_step(visual_styles=styles, job_index=3)
        assert step0._visual_style == "photorealistic"
        assert step1._visual_style == "oil painting"
        assert step3._visual_style == "photorealistic"  # 3 % 3 == 0

    def test_empty_styles_uses_prefix_fallback(self) -> None:
        step = _make_step(visual_styles=[], image_style_prefix="neon cyberpunk")
        assert step._visual_style == "neon cyberpunk"


# ── _read_audio_duration NaN/Inf 가드 (MS-NI 시리즈) ─────────────────────────


class TestReadAudioDurationNanInf:
    """MS-NI: mutagen이 Inf/NaN duration 반환 시 fallback_sec으로 안전 복귀."""

    def test_inf_duration_falls_back(self, tmp_path) -> None:
        """MS-NI001: mutagen.length=inf → fallback_sec 반환."""
        import math
        from unittest.mock import MagicMock, patch

        fake_info = MagicMock()
        fake_info.length = float("inf")
        fake_mp3 = MagicMock()
        fake_mp3.info = fake_info

        with patch("shorts_maker_v2.pipeline.media_step.MP3", return_value=fake_mp3):
            result = MediaStep._read_audio_duration(tmp_path / "x.mp3", fallback_sec=5.0)

        assert math.isfinite(result)
        assert result == 5.0

    def test_nan_duration_falls_back(self, tmp_path) -> None:
        """MS-NI002: mutagen.length=NaN → fallback_sec 반환."""
        import math
        from unittest.mock import MagicMock, patch

        fake_info = MagicMock()
        fake_info.length = float("nan")
        fake_mp3 = MagicMock()
        fake_mp3.info = fake_info

        with patch("shorts_maker_v2.pipeline.media_step.MP3", return_value=fake_mp3):
            result = MediaStep._read_audio_duration(tmp_path / "x.mp3", fallback_sec=3.5)

        assert math.isfinite(result)
        assert result == 3.5

    def test_valid_duration_passes_through(self, tmp_path) -> None:
        """MS-NI003: 정상 duration=42.0 → 그대로 반환."""
        import math
        from unittest.mock import MagicMock, patch

        fake_info = MagicMock()
        fake_info.length = 42.0
        fake_mp3 = MagicMock()
        fake_mp3.info = fake_info

        with patch("shorts_maker_v2.pipeline.media_step.MP3", return_value=fake_mp3):
            result = MediaStep._read_audio_duration(tmp_path / "x.mp3", fallback_sec=5.0)

        assert math.isfinite(result)
        assert result == 42.0
