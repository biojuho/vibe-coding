from __future__ import annotations

from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from shorts_maker_v2.models import SceneAsset, ScenePlan
from shorts_maker_v2.pipeline.render_step import RenderStep


def _make_render_step(
    transition_style: str = "random",
    *,
    channel_key: str = "",
    video_renderer_backend: str | None = None,
) -> RenderStep:
    """RenderStep의 __init__이 사용하는 모든 config 필드를 MagicMock으로 구성."""
    config = MagicMock()

    # video
    config.video.resolution = (1080, 1920)
    config.video.fps = 30
    config.video.transition_style = transition_style
    config.video.encoding_preset = "fast"
    config.video.encoding_crf = 23

    # captions (CaptionStyle 생성에 필요)
    config.captions.mode = "karaoke"
    config.captions.font_size = 72
    config.captions.margin_x = 60
    config.captions.bottom_offset = 280
    config.captions.text_color = "#FFFFFF"
    config.captions.stroke_color = "#000000"
    config.captions.stroke_width = 0
    config.captions.line_spacing = 12
    config.captions.bg_color = "#000000"
    config.captions.bg_opacity = 185
    config.captions.bg_radius = 18
    config.captions.style_preset = "default"
    config.captions.words_per_chunk = 3
    config.captions.font_candidates = ("C:/Windows/Fonts/malgunbd.ttf",)
    config.captions.outline_thickness = "medium"
    config.captions.custom_styles = {}
    config.captions.safe_zone_enabled = True
    config.captions.center_hook = False
    config.captions.line_spacing_factor = 1.0
    config.captions.channel_style_map = {}
    config.captions.highlight_color = "#FFD700"
    config.captions.highlight_mode = "word"
    config.captions.hook_animation = "pop"

    # audio
    config.audio.bgm_dir = "assets/bgm"
    config.audio.bgm_volume = 0.12
    config.audio.fade_duration = 0.5
    config.audio.sfx_enabled = False
    config.audio.sfx_dir = "assets/sfx"
    config.audio.sfx_volume = 0.35
    config.audio.bgm_provider = "local"
    config.audio.ducking_factor = 0.25
    config.audio.lyria_prompt_map = {}

    # intro/outro
    config.intro_outro.intro_path = ""
    config.intro_outro.outro_path = ""
    config.intro_outro.intro_duration = 2.0
    config.intro_outro.outro_duration = 2.0

    # providers
    config.providers.visual_styles = ()
    config.providers.tts_voice = "ko-KR-SunHiNeural"

    openai_client = MagicMock()
    return RenderStep(
        config=config,
        openai_client=openai_client,
        job_index=0,
        channel_key=channel_key,
        video_renderer_backend=video_renderer_backend,
    )


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


# ─── 무드 분류 테스트 ────────────────────────────────────────────────────────


def test_classify_mood_dramatic() -> None:
    """블랙홀, 우주 등 키워드 → dramatic."""
    assert RenderStep._classify_mood_keywords("블랙홀의 비밀") == "dramatic"
    assert RenderStep._classify_mood_keywords("전쟁의 역사") == "dramatic"


def test_classify_mood_upbeat() -> None:
    """돈, 성공 등 키워드 → upbeat."""
    assert RenderStep._classify_mood_keywords("돈 벌기 팁") == "upbeat"
    assert RenderStep._classify_mood_keywords("성공하는 방법") == "upbeat"


def test_classify_mood_calm_default() -> None:
    """매칭 키워드 없으면 → calm (기본값)."""
    assert RenderStep._classify_mood_keywords("오늘의 날씨") == "calm"


# ─── BGM 선택 테스트 ────────────────────────────────────────────────────────


def test_pick_bgm_by_mood_matches_filename(tmp_path: Path) -> None:
    """파일명에 무드 키워드가 있으면 우선 선택."""
    step = _make_render_step()
    step._llm_router = None  # GPT 분류 비활성화
    step._openai_client = None  # OpenAI 분류 비활성화

    bgm_dramatic = tmp_path / "bgm_dramatic_01.mp3"
    bgm_upbeat = tmp_path / "bgm_upbeat_01.mp3"
    bgm_calm = tmp_path / "bgm_calm_01.mp3"
    for f in [bgm_dramatic, bgm_upbeat, bgm_calm]:
        f.write_bytes(b"\x00" * 100)

    # "블랙홀" → dramatic → bgm_dramatic_01.mp3
    result = step._pick_bgm_by_mood([bgm_dramatic, bgm_upbeat, bgm_calm], "블랙홀의 비밀")
    assert "dramatic" in result.name


def test_pick_bgm_fallback_random(tmp_path: Path) -> None:
    """무드 매칭 실패 시 랜덤 폴백."""
    step = _make_render_step()
    step._llm_router = None
    step._openai_client = None

    bgm_files = [
        tmp_path / "bgm_01.mp3",
        tmp_path / "bgm_02.mp3",
    ]
    for f in bgm_files:
        f.write_bytes(b"\x00" * 100)

    # 매칭되는 파일명 없음 → 랜덤 선택
    result = step._pick_bgm_by_mood(bgm_files, "오늘의 날씨")
    assert result in bgm_files


# ─── 랜덤 효과 테스트 ────────────────────────────────────────────────────────


def test_apply_random_effect_has_method() -> None:
    """_apply_random_effect 메서드 존재 확인."""
    step = _make_render_step()
    assert hasattr(step, "_apply_random_effect")
    assert callable(step._apply_random_effect)


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


# ─── 자막 콤보 로테이션 테스트 ──────────────────────────────────────────────


def test_caption_combo_count() -> None:
    """최소 3개 이상의 자막 콤보 존재."""
    combos = RenderStep._CAPTION_COMBOS
    assert len(combos) >= 3


def test_caption_combo_rotation_varies() -> None:
    """다른 job_index는 다른 콤보 선택."""
    combos = RenderStep._CAPTION_COMBOS
    if len(combos) > 1:
        assert combos[0] != combos[1]


# ─── 제목 이미지 렌더링 테스트 ──────────────────────────────────────────────


def test_render_title_image_creates_file(tmp_path: Path) -> None:
    """_render_title_image가 PNG 파일을 정상 생성."""
    step = _make_render_step()
    output = tmp_path / "title.png"
    result = step._render_title_image("테스트 제목입니다", 1080, output)
    assert result.exists()
    assert result.stat().st_size > 0
    # PNG 매직 바이트 확인
    with open(result, "rb") as f:
        assert f.read(4) == b"\x89PNG"


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


# ─── BGM 수집 테스트 ──────────────────────────────────────────────────────


def test_collect_bgm_files_supports_wav(tmp_path: Path) -> None:
    """BGM 수집 시 wav 확장자도 포함한다."""
    mp3_file = tmp_path / "bgm_calm_01.mp3"
    wav_file = tmp_path / "bgm_calm_02.wav"
    txt_file = tmp_path / "notes.txt"
    mp3_file.write_bytes(b"\x00" * 10)
    wav_file.write_bytes(b"\x00" * 10)
    txt_file.write_text("ignore", encoding="utf-8")

    files = RenderStep._collect_bgm_files(tmp_path)

    assert mp3_file in files
    assert wav_file in files
    assert txt_file not in files


def test_collect_bgm_files_supports_m4a_and_aac(tmp_path: Path) -> None:
    """BGM 수집 시 m4a/aac 확장자도 포함한다."""
    m4a_file = tmp_path / "bgm_01.m4a"
    aac_file = tmp_path / "bgm_02.aac"
    m4a_file.write_bytes(b"\x00" * 10)
    aac_file.write_bytes(b"\x00" * 10)

    files = RenderStep._collect_bgm_files(tmp_path)
    assert m4a_file in files
    assert aac_file in files


def test_collect_bgm_files_empty_dir(tmp_path: Path) -> None:
    """빈 디렉토리 → 빈 리스트."""
    assert RenderStep._collect_bgm_files(tmp_path) == []


# ─── 카메라 효과 테스트 ────────────────────────────────────────────────────────


def _make_fake_clip(w: int = 1200, h: int = 2200, duration: float = 3.0):
    """MoviePy clip을 시뮬레이트하는 MagicMock 생성."""
    clip = MagicMock()
    clip.w = w
    clip.h = h
    clip.duration = duration

    def _resized(scale_or_func):
        new_clip = MagicMock()
        s = scale_or_func(0.0) if callable(scale_or_func) else scale_or_func
        new_clip.w = int(w * s)
        new_clip.h = int(h * s)
        new_clip.duration = duration
        new_clip.cropped = MagicMock(return_value=new_clip)
        new_clip.transform = MagicMock(return_value=new_clip)
        new_clip.with_duration = MagicMock(return_value=new_clip)
        return new_clip

    clip.resized = MagicMock(side_effect=_resized)
    clip.cropped = MagicMock(return_value=clip)
    clip.transform = MagicMock(return_value=clip)
    clip.with_duration = MagicMock(return_value=clip)
    return clip


def test_ken_burns_calls_resized_and_cropped() -> None:
    """_ken_burns가 resized와 cropped를 호출한다."""
    clip = _make_fake_clip()
    RenderStep._ken_burns(clip, 1080, 1920)
    clip.resized.assert_called_once()


def test_dramatic_ken_burns_stronger_zoom() -> None:
    """_dramatic_ken_burns는 기본 zoom=0.12로 더 강한 효과."""
    clip = _make_fake_clip()
    RenderStep._dramatic_ken_burns(clip, 1080, 1920)
    clip.resized.assert_called_once()
    resize_func = clip.resized.call_args[0][0]
    assert callable(resize_func)
    end_scale = resize_func(clip.duration)
    assert abs(end_scale - 1.12) < 0.001


def test_zoom_out_decreasing_scale() -> None:
    """_zoom_out는 시간이 지남에 따라 scale이 감소한다."""
    clip = _make_fake_clip()
    RenderStep._zoom_out(clip, 1080, 1920)
    resize_func = clip.resized.call_args[0][0]
    start_scale = resize_func(0.0)
    end_scale = resize_func(clip.duration)
    assert start_scale > end_scale


def test_push_in_ease_out_curve() -> None:
    """_push_in은 ease-out 커브를 적용한다."""
    clip = _make_fake_clip()
    RenderStep._push_in(clip, 1080, 1920)
    resize_func = clip.resized.call_args[0][0]
    start = resize_func(0.0)
    end = resize_func(clip.duration)
    assert start < end
    assert abs(end - 1.08) < 0.001


def test_ease_ken_burns_cubic() -> None:
    """_ease_ken_burns는 ease-in-out cubic 함수 적용."""
    clip = _make_fake_clip()
    RenderStep._ease_ken_burns(clip, 1080, 1920)
    resize_func = clip.resized.call_args[0][0]
    assert abs(resize_func(0.0) - 1.0) < 0.001
    assert abs(resize_func(clip.duration) - 1.08) < 0.001


def test_pan_horizontal_calls_resized() -> None:
    """_pan_horizontal은 overscan만큼 resized를 호출한다."""
    clip = _make_fake_clip()
    RenderStep._pan_horizontal(clip, 1080, 1920, direction=1)
    clip.resized.assert_called_once_with(1.12)


def test_drift_calls_resized() -> None:
    """_drift는 overscan=0.06으로 resized를 호출한다."""
    clip = _make_fake_clip()
    RenderStep._drift(clip, 1080, 1920)
    clip.resized.assert_called_once_with(1.06)


def test_shake_calls_resized() -> None:
    """_shake는 overscan=0.04로 resized를 호출한다."""
    clip = _make_fake_clip(duration=1.0)
    RenderStep._shake(clip, 1080, 1920, amplitude=3, fps=30)
    clip.resized.assert_called_once_with(1.04)


# ─── 효과 라우터 테스트 ────────────────────────────────────────────────────────


def test_apply_named_effect_known_name() -> None:
    """알려진 이름 → 해당 효과 반환."""
    step = _make_render_step()
    clip = _make_fake_clip()
    _, name = step._apply_named_effect("ken_burns", clip, 1080, 1920)
    assert name == "ken_burns"


def test_apply_named_effect_unknown_falls_back() -> None:
    """미지 이름 → _apply_random_effect 폴백."""
    step = _make_render_step()
    clip = _make_fake_clip()
    _, name = step._apply_named_effect("nonexistent_effect", clip, 1080, 1920)
    all_effects = step._build_effect_map(1080, 1920)
    assert name in all_effects


def test_apply_random_effect_respects_exclude() -> None:
    """_apply_random_effect는 _RANDOM_EXCLUDE 세트를 존중."""
    step = _make_render_step()
    clip = _make_fake_clip()
    for _ in range(20):
        _, chosen = step._apply_random_effect(clip, 1080, 1920)
        assert chosen not in RenderStep._RANDOM_EXCLUDE


def test_apply_channel_image_motion_string_motion() -> None:
    """채널 모션이 문자열이면 해당 효과를 직접 적용."""
    step = _make_render_step()
    step._channel_key = "ai_tech"
    clip = _make_fake_clip()
    _, name = step._apply_channel_image_motion(
        clip,
        role="hook",
        target_width=1080,
        target_height=1920,
    )
    assert name == "dramatic_ken_burns"


def test_apply_channel_image_motion_list_motion() -> None:
    """채널 모션이 리스트면 그 중에서 선택."""
    step = _make_render_step()
    step._channel_key = "ai_tech"
    clip = _make_fake_clip()
    _, name = step._apply_channel_image_motion(
        clip,
        role="body",
        target_width=1080,
        target_height=1920,
    )
    expected = RenderStep._CHANNEL_MOTION_CHOICES["ai_tech"]["body"]
    assert name in expected


def test_apply_channel_image_motion_hook_default() -> None:
    """채널 미지정 + hook → dramatic_ken_burns 폴백."""
    step = _make_render_step()
    step._channel_key = "unknown_channel"
    clip = _make_fake_clip()
    _, name = step._apply_channel_image_motion(
        clip,
        role="hook",
        target_width=1080,
        target_height=1920,
    )
    assert name == "dramatic_ken_burns"


# ─── 전환 효과 테스트 ──────────────────────────────────────────────────────────


def test_apply_transitions_cut_returns_clips_as_is() -> None:
    """cut 스타일 → 클립을 그대로 반환."""
    step = _make_render_step(transition_style="cut")
    clips = [MagicMock(), MagicMock()]
    result = step._apply_transitions(clips, 1080, 1920)
    assert result == clips


def test_apply_transitions_crossfade_applies_effects() -> None:
    """crossfade 스타일 → FadeIn/FadeOut 적용."""
    step = _make_render_step(transition_style="crossfade")
    clip1 = MagicMock()
    clip2 = MagicMock()
    clip1.with_effects = MagicMock(return_value=clip1)
    clip2.with_effects = MagicMock(return_value=clip2)
    result = step._apply_transitions([clip1, clip2], 1080, 1920)
    assert len(result) == 2


def test_apply_transitions_flash_inserts_white_frame() -> None:
    """flash 스타일 → 클립 사이에 흰색 프레임 삽입."""
    step = _make_render_step(transition_style="flash")
    clip1 = MagicMock()
    clip2 = MagicMock()
    result = step._apply_transitions([clip1, clip2], 1080, 1920)
    # clip1 + white_frame + clip2 = 3개
    assert len(result) == 3


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


def test_caption_y_with_safe_zone_enabled() -> None:
    """safe_zone_enabled=True → calculate_safe_position 호출."""
    clip = MagicMock()
    clip.h = 100
    style = MagicMock()
    style.safe_zone_enabled = True
    with patch(
        "shorts_maker_v2.pipeline.render_captions.calculate_safe_position",
        return_value=500,
    ) as mock_csp:
        result = RenderStep._caption_y(clip, 1920, style, "body")
    assert result == 500
    mock_csp.assert_called_once_with(1920, 100, style, "body")


def test_caption_y_non_centered_hook_uses_lower_third_but_body_stays_centered() -> None:
    step = _make_render_step()
    clip = MagicMock()
    clip.h = 240

    hook_y = RenderStep._caption_y(clip, 1920, step.hook_style, "hook")
    body_y = RenderStep._caption_y(clip, 1920, step.body_style, "body")

    assert hook_y == 1296
    assert body_y == 792
    assert hook_y > body_y


def test_caption_y_without_safe_zone() -> None:
    """safe_zone_enabled=False → bottom_offset 기반 계산."""
    clip = MagicMock()
    clip.h = 100
    style = MagicMock()
    style.safe_zone_enabled = False
    style.bottom_offset = 300
    result = RenderStep._caption_y(clip, 1920, style, "body")
    expected = max(80, int(1920 - 100 - 300))
    assert result == expected


def test_resolve_style_override_empty() -> None:
    """style_preset이 빈 문자열이면 빈 문자열 반환."""
    step = _make_render_step()
    step.config.captions.style_preset = ""
    assert step._resolve_style_override() == ""


def test_resolve_style_override_default() -> None:
    """style_preset이 'default'면 빈 문자열 반환."""
    step = _make_render_step()
    step.config.captions.style_preset = "default"
    assert step._resolve_style_override() == ""


def test_resolve_style_override_neon() -> None:
    """style_preset이 'neon'이면 'neon' 반환."""
    step = _make_render_step()
    step.config.captions.style_preset = "neon"
    assert step._resolve_style_override() == "neon"


def test_resolve_caption_combo_fallback_rotation() -> None:
    """채널 프로파일이 없으면 job_index 기반 로테이션."""
    combo0 = RenderStep._resolve_caption_combo("", 0)
    combo1 = RenderStep._resolve_caption_combo("", 1)
    assert len(combo0) == 4
    assert len(combo1) == 4
    if len(RenderStep._CAPTION_COMBOS) > 1:
        assert combo0 != combo1


def test_resolve_caption_combo_uses_channel_profile() -> None:
    """채널 프로파일에 caption_combo가 있으면 우선 사용."""
    mock_router = MagicMock()
    mock_router.return_value.get_profile.return_value = {"caption_combo": ["neon", "bold", "subtitle", "closing"]}
    with patch(
        "shorts_maker_v2.utils.channel_router.ChannelRouter",
        mock_router,
    ):
        combo = RenderStep._resolve_caption_combo("ai_tech", 0)
    assert combo == ("neon", "bold", "subtitle", "closing")


# ─── BGM 무드 GPT 분류 테스트 ─────────────────────────────────────────────────


def test_classify_mood_gpt_via_llm_router() -> None:
    """LLMRouter 성공 시 GPT 결과 반환."""
    step = _make_render_step()
    step._llm_router = MagicMock()
    step._llm_router.generate_json.return_value = {"mood": "dramatic"}
    result = step._classify_mood_gpt("우주의 비밀")
    assert result == "dramatic"


def test_classify_mood_gpt_via_openai_fallback() -> None:
    """LLMRouter 없고 OpenAI 성공 시 결과 반환."""
    step = _make_render_step()
    step._llm_router = None
    step._openai_client = MagicMock()
    step._openai_client.generate_json.return_value = {"mood": "upbeat"}
    result = step._classify_mood_gpt("성공하는 법")
    assert result == "upbeat"


def test_classify_mood_gpt_all_fail_returns_none() -> None:
    """LLM/OpenAI 모두 실패 시 None."""
    step = _make_render_step()
    step._llm_router = MagicMock()
    step._llm_router.generate_json.side_effect = Exception("fail")
    step._openai_client = MagicMock()
    step._openai_client.generate_json.side_effect = Exception("fail")
    result = step._classify_mood_gpt("anything")
    assert result is None


def test_classify_mood_gpt_then_keyword_fallback() -> None:
    """_classify_mood: GPT 실패 → 키워드 폴백."""
    step = _make_render_step()
    step._llm_router = None
    step._openai_client = None
    result = step._classify_mood("블랙홀에 빠져들다")
    assert result == "dramatic"


# ─── SFX 테스트 ──────────────────────────────────────────────────────────────


def test_load_sfx_files_categorizes(tmp_path: Path) -> None:
    """SFX 파일을 역할별로 분류한다."""
    step = _make_render_step()
    step.config.audio.sfx_dir = "sfx"
    sfx_dir = tmp_path / "project" / "sfx"
    sfx_dir.mkdir(parents=True)
    (sfx_dir / "whoosh_01.mp3").write_bytes(b"\x00")
    (sfx_dir / "pop_bell.wav").write_bytes(b"\x00")
    (sfx_dir / "ambient_loop.mp3").write_bytes(b"\x00")

    run_dir = tmp_path / "project" / "runs" / "run1"
    run_dir.mkdir(parents=True)

    result = step._load_sfx_files(run_dir)
    assert len(result.get("hook", [])) >= 1
    assert len(result.get("cta", [])) >= 1
    assert len(result.get("transition", [])) >= 1


def test_load_sfx_files_empty(tmp_path: Path) -> None:
    """SFX 디렉토리 없으면 빈 dict."""
    step = _make_render_step()
    step.config.audio.sfx_dir = "nonexistent_sfx"
    run_dir = tmp_path / "project" / "runs" / "run1"
    run_dir.mkdir(parents=True)
    result = step._load_sfx_files(run_dir)
    assert result == {}


# ─── RMS Ducking 테스트 ──────────────────────────────────────────────────────


def test_apply_rms_ducking_returns_ducked_clip() -> None:
    """RMS ducking이 effective_vol을 적용한다."""
    import numpy as np

    narration = MagicMock()
    narration.duration = 2.0
    narration.to_soundarray.return_value = np.random.randn(88200)

    bgm = MagicMock()
    ducked = MagicMock()
    bgm.with_effects = MagicMock(return_value=ducked)

    result = RenderStep._apply_rms_ducking(narration, bgm, base_vol=0.12)
    bgm.with_effects.assert_called_once()
    assert result is ducked


def test_apply_rms_ducking_no_duration() -> None:
    """나레이션 duration이 0이면 고정 볼륨."""
    narration = MagicMock()
    narration.duration = 0

    bgm = MagicMock()
    ducked = MagicMock()
    bgm.with_effects = MagicMock(return_value=ducked)

    result = RenderStep._apply_rms_ducking(narration, bgm, base_vol=0.15)
    assert result is ducked


def test_apply_rms_ducking_exception_fallback() -> None:
    """RMS 계산 실패 시 고정 볼륨 폴백."""
    narration = MagicMock()
    narration.duration = 2.0
    narration.to_soundarray.side_effect = Exception("numpy error")

    bgm = MagicMock()
    ducked = MagicMock()
    bgm.with_effects = MagicMock(return_value=ducked)

    result = RenderStep._apply_rms_ducking(narration, bgm, base_vol=0.12)
    assert result is ducked


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


# ─── _build_keyword_color_map ───────────────────────────────────────────────


def test_build_keyword_color_map_no_keywords_returns_none() -> None:
    """highlight_keywords 없으면 None 반환."""
    step = _make_render_step()
    step._channel_profile = {}
    assert step._build_keyword_color_map() is None


def test_build_keyword_color_map_with_keywords_returns_dict() -> None:
    """highlight_keywords 있으면 dict 반환."""
    step = _make_render_step()
    step._channel_profile = {
        "highlight_keywords": ["AI", "GPT"],
        "highlight_color": "#FF0000",
    }
    step.config.captions.highlight_color = "#E879F9"
    result = step._build_keyword_color_map()
    assert isinstance(result, dict)
    assert len(result) >= 1


# ─── _build_effect_map ──────────────────────────────────────────────────────


def test_build_effect_map_all_expected_effects() -> None:
    """효과 맵에 9개 기본 효과가 모두 존재한다."""
    step = _make_render_step()
    effect_map = step._build_effect_map(1080, 1920)
    expected = {
        "ken_burns",
        "dramatic_ken_burns",
        "zoom_out",
        "pan_left",
        "pan_right",
        "drift",
        "push_in",
        "shake",
        "ease_ken_burns",
    }
    assert set(effect_map.keys()) == expected


def test_build_effect_map_values_are_callable() -> None:
    """효과 맵의 모든 값이 callable이다."""
    step = _make_render_step()
    effect_map = step._build_effect_map(1080, 1920)
    for name, fn in effect_map.items():
        assert callable(fn), f"{name} is not callable"


# ─── _classify_mood (combined) ──────────────────────────────────────────────


def test_classify_mood_gpt_value_used() -> None:
    """_classify_mood: GPT가 값을 반환하면 그것을 사용."""
    step = _make_render_step()
    step._llm_router = MagicMock()
    step._llm_router.generate_json.return_value = {"mood": "upbeat"}
    assert step._classify_mood("아무 텍스트") == "upbeat"


def test_classify_mood_no_gpt_keyword_calm() -> None:
    """_classify_mood: GPT 없고 키워드 매칭 없으면 calm."""
    step = _make_render_step()
    step._llm_router = None
    step._openai_client = None
    assert step._classify_mood("오늘의 날씨") == "calm"


# ─── _classify_mood_gpt 추가 분기 ──────────────────────────────────────────


def test_classify_mood_gpt_invalid_mood_falls_to_openai() -> None:
    """LLMRouter가 유효하지 않은 무드를 반환하면 OpenAI fallback."""
    step = _make_render_step()
    step._llm_router = MagicMock()
    step._llm_router.generate_json.return_value = {"mood": "invalid_mood"}
    step._openai_client = MagicMock()
    step._openai_client.generate_json.return_value = {"mood": "calm"}
    assert step._classify_mood_gpt("테스트") == "calm"


def test_classify_mood_gpt_llm_fails_openai_fallback() -> None:
    """LLMRouter 예외 → OpenAI fallback 사용."""
    step = _make_render_step()
    step._llm_router = MagicMock()
    step._llm_router.generate_json.side_effect = RuntimeError("LLM down")
    step._openai_client = MagicMock()
    step._openai_client.generate_json.return_value = {"mood": "upbeat"}
    assert step._classify_mood_gpt("돈 벌기 팁") == "upbeat"


# ─── _resolve_style_override 추가 ──────────────────────────────────────────


def test_resolve_style_override_whitespace_only() -> None:
    """공백만 있는 style_preset → 빈 문자열."""
    step = _make_render_step()
    step.config.captions.style_preset = "   "
    assert step._resolve_style_override() == ""


# ─── _resolve_caption_combo 추가 ────────────────────────────────────────────


def test_resolve_caption_combo_short_combo_falls_back() -> None:
    """caption_combo가 3개 미만이면 로테이션 폴백."""
    mock_router = MagicMock()
    mock_router.return_value.get_profile.return_value = {
        "caption_combo": ["bold", "neon"],  # only 2
    }
    with patch(
        "shorts_maker_v2.utils.channel_router.ChannelRouter",
        mock_router,
    ):
        result = RenderStep._resolve_caption_combo("ai_tech", 0)
    assert result == RenderStep._CAPTION_COMBOS[0]


def test_resolve_caption_combo_router_exception_falls_back() -> None:
    """ChannelRouter 예외 시 로테이션 폴백."""
    with patch(
        "shorts_maker_v2.utils.channel_router.ChannelRouter",
        side_effect=RuntimeError("router broken"),
    ):
        result = RenderStep._resolve_caption_combo("ai_tech", 2)
    expected = RenderStep._CAPTION_COMBOS[2 % len(RenderStep._CAPTION_COMBOS)]
    assert result == expected


# ─── _render_static_caption ─────────────────────────────────────────────────


def test_render_static_caption_non_hook_direct(tmp_path: Path) -> None:
    """non-hook role → render_caption_image 직접 호출."""
    step = _make_render_step()
    output = tmp_path / "caption.png"
    mock_style = MagicMock()
    with patch(
        "shorts_maker_v2.pipeline.render_captions.render_caption_image",
        return_value=output,
    ) as mock_fn:
        result = step._render_static_caption("테스트 자막", 1080, mock_style, output, "body")
    mock_fn.assert_called_once_with("테스트 자막", 1080, mock_style, output)
    assert result == output


def test_render_static_caption_hook_without_channel(tmp_path: Path) -> None:
    """hook role이지만 channel_key 없으면 render_caption_image 직접 호출."""
    step = _make_render_step()
    step._channel_key = ""
    output = tmp_path / "caption.png"
    mock_style = MagicMock()
    with patch(
        "shorts_maker_v2.pipeline.render_captions.render_caption_image",
        return_value=output,
    ) as mock_fn:
        result = step._render_static_caption("훅 자막", 1080, mock_style, output, "hook")
    mock_fn.assert_called_once()
    assert result == output


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


# ─── _generate_lyria_bgm ───────────────────────────────────────────────────


def test_generate_lyria_bgm_no_api_key(tmp_path: Path) -> None:
    """GEMINI_API_KEY 없으면 None 반환."""
    step = _make_render_step()
    step.config.audio.lyria_prompt_map = {}
    with patch.dict("os.environ", {}, clear=True):
        result = step._generate_lyria_bgm(run_dir=tmp_path, duration_sec=30.0)
    assert result is None


def test_generate_lyria_bgm_cached_file(tmp_path: Path) -> None:
    """캐시 파일이 존재하면 그대로 반환."""
    step = _make_render_step()
    step.config.audio.lyria_prompt_map = {}
    cached = tmp_path / "bgm_lyria.mp3"
    cached.write_bytes(b"\xff\xfb\x90" + b"\x00" * 100)

    with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}):
        result = step._generate_lyria_bgm(run_dir=tmp_path, duration_sec=30.0)
    assert result == cached


# ─── _build_sfx_clips ──────────────────────────────────────────────────────


def test_build_sfx_clips_with_all_roles(tmp_path: Path) -> None:
    """hook/cta/transition SFX가 올바른 위치에 배치."""
    step = _make_render_step()

    def _make_sfx_clip(*args, **kwargs):
        clip = MagicMock()
        clip.with_effects.return_value = clip
        clip.with_start.return_value = clip
        return clip

    step._load_audio_clip = MagicMock(side_effect=_make_sfx_clip)

    hook_file = tmp_path / "whoosh.mp3"
    cta_file = tmp_path / "pop.mp3"
    trans_file = tmp_path / "swoosh.mp3"
    for f in (hook_file, cta_file, trans_file):
        f.write_bytes(b"\x00" * 10)

    sfx_files = {
        "hook": [hook_file],
        "cta": [cta_file],
        "transition": [trans_file],
    }
    clips = step._build_sfx_clips(
        ["hook", "body", "cta"],
        [3.0, 5.0, 4.0],
        sfx_files,
    )
    # hook SFX + 2 transitions + cta SFX = at least 4
    assert len(clips) >= 3
    assert step._load_audio_clip.call_count >= 3


def test_build_sfx_clips_empty_files() -> None:
    """SFX 파일이 비어 있으면 빈 리스트."""
    step = _make_render_step()
    sfx_files = {"hook": [], "cta": [], "transition": []}
    clips = step._build_sfx_clips(["hook", "body"], [3.0, 5.0], sfx_files)
    assert clips == []


def test_build_sfx_clips_only_transition(tmp_path: Path) -> None:
    """transition SFX만 있을 때 씬 전환 시점에만 배치."""
    step = _make_render_step()

    def _make_sfx_clip(*args, **kwargs):
        clip = MagicMock()
        clip.with_effects.return_value = clip
        clip.with_start.return_value = clip
        return clip

    step._load_audio_clip = MagicMock(side_effect=_make_sfx_clip)

    trans_file = tmp_path / "swoosh.mp3"
    trans_file.write_bytes(b"\x00" * 10)

    sfx_files = {"hook": [], "cta": [], "transition": [trans_file]}
    clips = step._build_sfx_clips(
        ["hook", "body", "cta"],
        [3.0, 5.0, 4.0],
        sfx_files,
    )
    # 3 scenes → 2 transition points
    assert len(clips) == 2


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


# ─── _apply_transitions 추가 스타일 ─────────────────────────────────────────


def test_apply_transitions_zoom_applies_fade_out() -> None:
    """zoom 스타일 → FadeOut 적용."""
    step = _make_render_step(transition_style="zoom")
    clip1 = MagicMock()
    clip2 = MagicMock()
    clip1.with_effects = MagicMock(return_value=clip1)
    clip2.with_effects = MagicMock(return_value=clip2)
    result = step._apply_transitions([clip1, clip2], 1080, 1920)
    assert len(result) == 2


def test_apply_transitions_slide() -> None:
    """slide 스타일 → FadeIn/FadeOut 적용."""
    step = _make_render_step(transition_style="slide")
    clip1 = MagicMock()
    clip2 = MagicMock()
    clip1.with_effects = MagicMock(return_value=clip1)
    clip2.with_effects = MagicMock(return_value=clip2)
    result = step._apply_transitions([clip1, clip2], 1080, 1920)
    assert len(result) == 2


def test_apply_transitions_glitch_inserts_flash() -> None:
    """glitch 스타일 → 글리치 효과 + 플래시 삽입."""
    step = _make_render_step(transition_style="glitch")
    clip1 = MagicMock()
    clip1.duration = 3.0
    clip1.transform = MagicMock(return_value=clip1)
    clip2 = MagicMock()
    clip2.duration = 3.0
    clip2.transform = MagicMock(return_value=clip2)
    result = step._apply_transitions([clip1, clip2], 1080, 1920)
    # clip1 (glitch applied) + flash + clip2
    assert len(result) == 3


def test_apply_transitions_iris() -> None:
    """iris 스타일 → iris 필터 적용."""
    step = _make_render_step(transition_style="iris")
    clip1 = MagicMock()
    clip1.duration = 3.0
    clip1.transform = MagicMock(return_value=clip1)
    clip2 = MagicMock()
    clip2.duration = 3.0
    clip2.transform = MagicMock(return_value=clip2)
    result = step._apply_transitions([clip1, clip2], 1080, 1920)
    assert len(result) == 2


def test_apply_transitions_rgb_split() -> None:
    """rgb_split 스타일 → RGB split 필터 적용."""
    step = _make_render_step(transition_style="rgb_split")
    clip1 = MagicMock()
    clip1.duration = 3.0
    clip1.transform = MagicMock(return_value=clip1)
    clip2 = MagicMock()
    clip2.duration = 3.0
    clip2.transform = MagicMock(return_value=clip2)
    result = step._apply_transitions([clip1, clip2], 1080, 1920)
    assert len(result) == 2


def test_apply_transitions_morph_cut() -> None:
    """morph_cut 스타일 → 페이드 + 줌인 적용."""
    step = _make_render_step(transition_style="morph_cut")
    clip1 = MagicMock()
    clip1.duration = 3.0
    clip1.with_effects = MagicMock(return_value=clip1)
    clip1.resized = MagicMock(return_value=clip1)
    clip2 = MagicMock()
    clip2.duration = 3.0
    clip2.with_effects = MagicMock(return_value=clip2)
    clip2.resized = MagicMock(return_value=clip2)
    result = step._apply_transitions([clip1, clip2], 1080, 1920)
    assert len(result) == 2


def test_apply_transitions_with_roles_structural() -> None:
    """roles 제공 + random → 구조적 전환 스타일 사용."""
    step = _make_render_step(transition_style="random")
    clip1 = MagicMock()
    clip1.duration = 3.0
    clip1.with_effects = MagicMock(return_value=clip1)
    clip1.transform = MagicMock(return_value=clip1)
    clip2 = MagicMock()
    clip2.duration = 3.0
    clip2.with_effects = MagicMock(return_value=clip2)
    clip2.transform = MagicMock(return_value=clip2)
    clip2.subclipped = MagicMock(return_value=clip2)
    clip2.with_start = MagicMock(return_value=clip2)
    clip2.with_mask = MagicMock(return_value=clip2)
    clip2.resized = MagicMock(return_value=clip2)
    result = step._apply_transitions(
        [clip1, clip2],
        1080,
        1920,
        roles=["hook", "body"],
    )
    assert len(result) >= 2


# ─── _apply_random_effect exclude 로직 ──────────────────────────────────────


def test_apply_random_effect_with_exclude_param() -> None:
    """exclude 파라미터가 해당 효과를 제외."""
    step = _make_render_step()
    clip = _make_fake_clip()
    for _ in range(20):
        _, chosen = step._apply_random_effect(
            clip,
            1080,
            1920,
            exclude="ken_burns",
        )
        assert chosen != "ken_burns"


# ─── _pick_bgm_by_mood (GPT 경유) ──────────────────────────────────────────


def test_pick_bgm_by_mood_uses_gpt_mood(tmp_path: Path) -> None:
    """GPT 무드 분류 결과가 BGM 선택에 반영."""
    step = _make_render_step()
    step._llm_router = MagicMock()
    step._llm_router.generate_json.return_value = {"mood": "upbeat"}
    step._openai_client = None

    bgm_upbeat = tmp_path / "bgm_upbeat_01.mp3"
    bgm_calm = tmp_path / "bgm_calm_01.mp3"
    for f in [bgm_upbeat, bgm_calm]:
        f.write_bytes(b"\x00" * 100)

    result = step._pick_bgm_by_mood([bgm_upbeat, bgm_calm], "아무 텍스트")
    assert "upbeat" in result.name


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


# ─── _render_static_caption hook + channel (TextEngine 경로) ────────────────


def test_render_static_caption_hook_with_channel_text_engine_fails(
    tmp_path: Path,
) -> None:
    """hook + channel_key이지만 TextEngine 실패 → render_caption_image 폴백."""
    import builtins

    step = _make_render_step()
    step._channel_key = "ai_tech"
    step._channel_profile = {"some": "profile"}
    output = tmp_path / "caption.png"
    mock_style = MagicMock()

    original_import = builtins.__import__

    def _blocking_import(name, *args, **kwargs):
        if "ShortsFactory" in name:
            raise ImportError("blocked for test")
        return original_import(name, *args, **kwargs)

    with (
        patch("builtins.__import__", side_effect=_blocking_import),
        patch(
            "shorts_maker_v2.pipeline.render_captions.render_caption_image",
            return_value=output,
        ) as mock_fn,
    ):
        result = step._render_static_caption(
            "훅 자막",
            1080,
            mock_style,
            output,
            "hook",
        )
    mock_fn.assert_called_once()
    assert result == output


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


# ─── _collect_bgm_files 정렬 확인 ──────────────────────────────────────────


def test_collect_bgm_files_sorted_order(tmp_path: Path) -> None:
    """파일들이 정렬된 순서로 반환."""
    c = tmp_path / "bgm_c.mp3"
    a = tmp_path / "bgm_a.mp3"
    b = tmp_path / "bgm_b.mp3"
    for f in (c, a, b):
        f.write_bytes(b"\x00" * 10)
    files = RenderStep._collect_bgm_files(tmp_path)
    names = [f.name for f in files]
    assert names == sorted(names)


# ─── _apply_rms_ducking 정상 동작 (numpy 경유) ─────────────────────────────


def test_apply_rms_ducking_normal_with_speech() -> None:
    """나레이션 음성이 있는 경우 ducking 적용."""
    import numpy as np

    # Generate fake audio with some loud sections
    narration = MagicMock()
    narration.duration = 3.0
    # 3 seconds at 44100Hz = 132300 samples, loud signal
    audio_data = np.ones(132300) * 0.5
    narration.to_soundarray.return_value = audio_data

    bgm = MagicMock()
    ducked = MagicMock()
    bgm.with_effects = MagicMock(return_value=ducked)

    result = RenderStep._apply_rms_ducking(narration, bgm, base_vol=0.12)
    assert result is ducked
    bgm.with_effects.assert_called_once()


def test_apply_rms_ducking_stereo_audio() -> None:
    """스테레오 나레이션 오디오 → 모노 변환 후 처리."""
    import numpy as np

    narration = MagicMock()
    narration.duration = 2.0
    # Stereo: (88200, 2)
    narration.to_soundarray.return_value = np.random.randn(88200, 2)

    bgm = MagicMock()
    ducked = MagicMock()
    bgm.with_effects = MagicMock(return_value=ducked)

    result = RenderStep._apply_rms_ducking(narration, bgm, base_vol=0.12)
    assert result is ducked


class _DummyClip:
    def __init__(
        self,
        name: str,
        *,
        duration: float = 3.0,
        w: int = 1080,
        h: int = 1920,
        audio=None,
    ) -> None:
        self.name = name
        self.duration = duration
        self.w = w
        self.h = h
        self.audio = audio
        self.closed = False
        self.effects: list = []
        self.start = 0.0
        self.position = None
        self.mask = None

    def with_effects(self, effects):
        self.effects.extend(effects)
        return self

    def with_audio(self, audio):
        self.audio = audio
        return self

    def with_duration(self, duration: float):
        self.duration = duration
        return self

    def with_start(self, start: float):
        self.start = start
        return self

    def with_position(self, position):
        self.position = position
        return self

    def with_mask(self, mask):
        self.mask = mask
        return self

    def subclipped(self, start: float, end: float):
        return _DummyClip(
            f"{self.name}:sub",
            duration=max(0.0, end - start),
            w=self.w,
            h=self.h,
            audio=self.audio,
        )

    def resized(self, scale_or_func):
        scale = scale_or_func(0.0) if callable(scale_or_func) else scale_or_func
        return _DummyClip(
            f"{self.name}:resized",
            duration=self.duration,
            w=max(1, int(self.w * scale)),
            h=max(1, int(self.h * scale)),
            audio=self.audio,
        )

    def cropped(self, *, x1, y1, x2, y2):
        return _DummyClip(
            f"{self.name}:cropped",
            duration=self.duration,
            w=max(1, int(x2 - x1)),
            h=max(1, int(y2 - y1)),
            audio=self.audio,
        )

    def transform(self, _func):
        return self

    def close(self):
        self.closed = True


class _DummyAudioClip(_DummyClip):
    def __init__(self, name: str, *, duration: float = 3.0) -> None:
        super().__init__(name, duration=duration, w=1, h=1, audio=None)


def _configure_render_step_for_run(
    step: RenderStep,
    *,
    captions_mode: str = "karaoke",
    highlight_mode: str = "word",
    bgm_provider: str = "lyria",
    sfx_enabled: bool = False,
) -> None:
    step.config.captions.mode = captions_mode
    step.config.captions.highlight_mode = highlight_mode
    step.config.captions.hook_animation = "pop"
    step.config.providers.tts_voice = "ko-KR-SunHiNeural"
    step.config.audio.bgm_provider = bgm_provider
    step.config.audio.ducking_factor = 0.25
    step.config.audio.lyria_prompt_map = {"default": "calm piano", "ai_tech": "tech pulse"}
    step.config.audio.sfx_enabled = sfx_enabled
    step.config.video.hw_accel = "auto"
    step.config.video.quality_profile = "draft"
    step.config.intro_outro.intro_path = ""
    step.config.intro_outro.outro_path = ""


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


def test_generate_lyria_bgm_creates_file_from_client(tmp_path: Path) -> None:
    """Lyria generation should return the generated file when the client succeeds."""
    step = _make_render_step()
    step.config.audio.lyria_prompt_map = {"default": "calm piano", "ai_tech": "tech pulse"}

    async def _write_music_file(*, output_path, **kwargs):  # noqa: ARG001
        output_path.write_bytes(b"bgm-data")

    client = SimpleNamespace(generate_music_file=_write_music_file)

    with (
        patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}),
        patch(
            "shorts_maker_v2.providers.google_music_client.GoogleMusicClient.from_env",
            return_value=client,
        ),
    ):
        result = step._generate_lyria_bgm(
            run_dir=tmp_path,
            duration_sec=30.0,
            channel="ai_tech",
            topic="future chips",
        )

    assert result == tmp_path / "bgm_lyria.mp3"
    assert result.exists()


def test_generate_lyria_bgm_returns_none_on_client_failure(tmp_path: Path) -> None:
    """Lyria generation should fail closed and fall back to local assets."""
    step = _make_render_step()
    step.config.audio.lyria_prompt_map = {}

    with (
        patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}),
        patch(
            "shorts_maker_v2.providers.google_music_client.GoogleMusicClient.from_env",
            side_effect=RuntimeError("music client down"),
        ),
    ):
        result = step._generate_lyria_bgm(run_dir=tmp_path, duration_sec=20.0)

    assert result is None


def test_run_handles_full_karaoke_lyria_and_sfx_flow(tmp_path: Path) -> None:
    """run() should cover the main render flow with lyric BGM and SFX mixing."""
    step = _make_render_step(channel_key="ai_tech")
    _configure_render_step_for_run(step, bgm_provider="lyria", sfx_enabled=True)
    step.config.intro_outro.intro_path = "intro.mp4"
    step.config.intro_outro.outro_path = "outro.png"

    workspace = tmp_path / "workspace"
    run_dir = workspace / "runs" / "job-001"
    output_dir = workspace / "output"
    run_dir.mkdir(parents=True)
    output_dir.mkdir(parents=True)

    audio_path1 = run_dir / "scene01.mp3"
    audio_path2 = run_dir / "scene02.mp3"
    ssml_path = run_dir / "scene01_words_ssml.txt"
    ssml_path.write_text("break", encoding="utf-8")
    (run_dir / "broll_01.mp4").write_bytes(b"broll")

    scene_plans = [
        ScenePlan(1, "Hook narration", "hook visual", 3.0, "hook"),
        ScenePlan(2, "Closing narration", "closing visual", 4.0, "closing"),
    ]
    scene_assets = [
        SceneAsset(1, str(audio_path1), "image", "visual-1.png", 3.0),
        SceneAsset(2, str(audio_path2), "image", "visual-2.png", 4.0),
    ]

    word_segments = [
        SimpleNamespace(word="AI", start=0.0, end=0.5),
        SimpleNamespace(word="future", start=0.5, end=1.0),
    ]
    highlight_chunks = [
        (0.0, 1.0, "AI future", word_segments),
    ]

    base_lookup = {
        1: _DummyClip("base-1", duration=3.0),
        2: _DummyClip("base-2", duration=4.0),
    }
    audio_lookup = {
        str(audio_path1): _DummyAudioClip("scene-audio-1", duration=4.0),
        str(audio_path2): _DummyAudioClip("scene-audio-2", duration=4.0),
        str(run_dir / "bgm_lyria.mp3"): _DummyAudioClip("bgm", duration=80.0),
    }

    def _image_clip_factory(*args, **kwargs):  # noqa: ARG001
        return _DummyClip("image", duration=0.1, w=400, h=120)

    def _composite_video_factory(clips, size=None):  # noqa: ARG001
        duration = max((getattr(clip, "duration", 0.0) for clip in clips), default=0.0)
        audio = next((clip.audio for clip in clips if getattr(clip, "audio", None) is not None), None)
        return _DummyClip("composite-video", duration=duration, audio=audio)

    def _composite_audio_factory(clips):
        duration = max((getattr(clip, "duration", 0.0) for clip in clips), default=0.0)
        return _DummyAudioClip("mixed-audio", duration=duration)

    final_video = _DummyClip("final-video", duration=62.0, audio=_DummyAudioClip("narration", duration=62.0))
    final_video.subclipped = lambda start, end: final_video.with_duration(max(0.0, end - start))

    with ExitStack() as stack:
        stack.enter_context(
            patch.object(
                step,
                "_build_bookend_clip",
                side_effect=lambda path, duration, *_: _DummyClip(
                    path,
                    duration=duration,
                ),
            )
        )
        stack.enter_context(
            patch.object(
                step,
                "_build_base_clip",
                side_effect=lambda asset, *_: base_lookup[asset.scene_id],
            )
        )
        stack.enter_context(
            patch.object(
                step,
                "_apply_channel_image_motion",
                side_effect=lambda base, **kwargs: (
                    base,
                    f"{kwargs['role']}-motion",
                ),
            )
        )
        stack.enter_context(
            patch.object(
                step,
                "_load_audio_clip",
                side_effect=lambda path: audio_lookup[str(path)],
            )
        )
        stack.enter_context(
            patch.object(
                step,
                "_apply_transitions",
                side_effect=lambda clips, *args, **kwargs: clips,
            )
        )
        lyria_bgm = stack.enter_context(
            patch.object(step, "_generate_lyria_bgm", return_value=run_dir / "bgm_lyria.mp3")
        )
        ducking = stack.enter_context(
            patch.object(step, "_apply_rms_ducking", return_value=_DummyAudioClip("ducked", duration=62.0))
        )
        load_sfx = stack.enter_context(
            patch.object(
                step,
                "_load_sfx_files",
                return_value={
                    "hook": [Path("hook.mp3")],
                    "transition": [Path("swish.mp3")],
                    "cta": [],
                },
            )
        )
        build_sfx = stack.enter_context(
            patch.object(
                step,
                "_build_sfx_clips",
                return_value=[_DummyAudioClip("sfx-1", duration=0.2), _DummyAudioClip("sfx-2", duration=0.2)],
            )
        )
        stack.enter_context(
            patch(
                "shorts_maker_v2.pipeline.render_step.color_grade_clip",
                side_effect=lambda clip, *args, **kwargs: clip,
            )
        )
        stack.enter_context(
            patch(
                "shorts_maker_v2.pipeline.render_step.postprocess_tts_audio",
                return_value=None,
            )
        )
        stack.enter_context(
            patch(
                "shorts_maker_v2.pipeline.render_step.load_words_json",
                return_value=word_segments,
            )
        )
        ssml_fix = stack.enter_context(
            patch("shorts_maker_v2.pipeline.render_step.apply_ssml_break_correction", return_value=word_segments)
        )
        stack.enter_context(
            patch(
                "shorts_maker_v2.pipeline.render_step.group_word_segments",
                return_value=highlight_chunks,
            )
        )
        render_highlight = stack.enter_context(
            patch("shorts_maker_v2.pipeline.render_step.render_karaoke_highlight_image", return_value=None)
        )
        stack.enter_context(
            patch(
                "shorts_maker_v2.pipeline.render_step.ImageClip",
                side_effect=_image_clip_factory,
            )
        )
        stack.enter_context(
            patch(
                "shorts_maker_v2.pipeline.render_step.CompositeVideoClip",
                side_effect=_composite_video_factory,
            )
        )
        stack.enter_context(
            patch(
                "shorts_maker_v2.pipeline.render_step.CompositeAudioClip",
                side_effect=_composite_audio_factory,
            )
        )
        broll_pip = stack.enter_context(
            patch("shorts_maker_v2.pipeline.render_step.create_broll_pip", return_value=_DummyClip("pip", duration=1.0))
        )
        animate = stack.enter_context(
            patch("shorts_maker_v2.pipeline.render_step.apply_text_animation", side_effect=lambda clip, **kwargs: clip)
        )
        concat_videos = stack.enter_context(
            patch("shorts_maker_v2.pipeline.render_step.concatenate_videoclips", return_value=final_video)
        )
        stack.enter_context(
            patch(
                "shorts_maker_v2.utils.hwaccel.detect_hw_encoder",
                return_value=("libx264", ["-ignored"]),
            )
        )
        stack.enter_context(
            patch(
                "shorts_maker_v2.utils.hwaccel.detect_gpu_info",
                return_value={"gpu_name": "Fake GPU", "encoder": "libx264", "decoder_support": True},
            )
        )
        write_video = stack.enter_context(patch.object(step._output_renderer, "write", return_value=None))
        stack.enter_context(patch("builtins.print"))

        result = step.run(
            scene_plans=scene_plans,
            scene_assets=scene_assets,
            output_dir=output_dir,
            output_filename="final.mp4",
            run_dir=run_dir,
            title="AI future",
            topic="AI future",
        )

    assert result == output_dir / "final.mp4"
    assert final_video.closed is True
    assert concat_videos.called
    assert lyria_bgm.called
    assert ducking.called
    assert load_sfx.called
    assert build_sfx.called
    assert render_highlight.called
    assert ssml_fix.called
    assert broll_pip.called
    assert animate.called
    write_video.assert_called_once()


def test_run_uses_static_caption_fallback_and_local_bgm_when_karaoke_fails(tmp_path: Path) -> None:
    """run() should recover from karaoke/render warnings and fall back to local BGM."""
    step = _make_render_step(channel_key="ai_tech")
    _configure_render_step_for_run(step, bgm_provider="local", sfx_enabled=False)

    workspace = tmp_path / "workspace"
    run_dir = workspace / "runs" / "job-002"
    output_dir = workspace / "output"
    bgm_dir = workspace / "assets" / "bgm"
    run_dir.mkdir(parents=True)
    output_dir.mkdir(parents=True)
    bgm_dir.mkdir(parents=True)
    bgm_path = bgm_dir / "bgm_loop.mp3"
    bgm_path.write_bytes(b"loop")
    (run_dir / "broll_01.mp4").write_bytes(b"broll")

    audio_path = run_dir / "scene01.mp3"
    scene_plans = [ScenePlan(1, "Fallback narration", "visual", 5.0, "hook")]
    scene_assets = [SceneAsset(1, str(audio_path), "image", "visual-1.png", 5.0)]

    base_clip = _DummyClip("base", duration=5.0)
    final_video = _DummyClip("final", duration=10.0, audio=_DummyAudioClip("narration", duration=10.0))
    local_bgm_clip = _DummyAudioClip("local-bgm", duration=2.0)
    looped_bgm_clip = _DummyAudioClip("looped-bgm", duration=12.0)

    def _image_clip_factory(*args, **kwargs):  # noqa: ARG001
        return _DummyClip("caption", duration=0.1, w=500, h=120)

    def _composite_video_factory(clips, size=None):  # noqa: ARG001
        audio = next((clip.audio for clip in clips if getattr(clip, "audio", None) is not None), None)
        duration = max((getattr(clip, "duration", 0.0) for clip in clips), default=0.0)
        return _DummyClip("composite-video", duration=duration, audio=audio)

    def _composite_audio_factory(clips):
        duration = max((getattr(clip, "duration", 0.0) for clip in clips), default=0.0)
        return _DummyAudioClip("mixed-audio", duration=duration)

    with ExitStack() as stack:
        stack.enter_context(patch.object(step, "_build_base_clip", return_value=base_clip))
        stack.enter_context(patch.object(step, "_apply_channel_image_motion", return_value=(base_clip, "ken_burns")))
        stack.enter_context(
            patch.object(
                step,
                "_load_audio_clip",
                side_effect=lambda path: (
                    local_bgm_clip if str(path) == str(bgm_path) else _DummyAudioClip("scene", duration=5.5)
                ),
            )
        )
        static_caption = stack.enter_context(
            patch.object(step, "_render_static_caption", return_value=run_dir / "caption.png")
        )
        stack.enter_context(
            patch.object(
                step,
                "_apply_transitions",
                side_effect=lambda clips, *args, **kwargs: clips,
            )
        )
        pick_bgm = stack.enter_context(patch.object(step, "_pick_bgm_by_mood", return_value=bgm_path))
        ducking = stack.enter_context(
            patch.object(step, "_apply_rms_ducking", return_value=_DummyAudioClip("ducked", duration=10.0))
        )
        stack.enter_context(
            patch(
                "shorts_maker_v2.pipeline.render_step.color_grade_clip",
                side_effect=RuntimeError("grade failed"),
            )
        )
        stack.enter_context(
            patch(
                "shorts_maker_v2.pipeline.render_step.postprocess_tts_audio",
                side_effect=RuntimeError("post failed"),
            )
        )
        stack.enter_context(
            patch(
                "shorts_maker_v2.pipeline.render_step.load_words_json",
                side_effect=RuntimeError("words missing"),
            )
        )
        stack.enter_context(
            patch(
                "shorts_maker_v2.pipeline.render_step.ImageClip",
                side_effect=_image_clip_factory,
            )
        )
        stack.enter_context(
            patch(
                "shorts_maker_v2.pipeline.render_step.CompositeVideoClip",
                side_effect=_composite_video_factory,
            )
        )
        stack.enter_context(
            patch(
                "shorts_maker_v2.pipeline.render_step.CompositeAudioClip",
                side_effect=_composite_audio_factory,
            )
        )
        stack.enter_context(
            patch(
                "shorts_maker_v2.pipeline.render_step.create_broll_pip",
                side_effect=RuntimeError("pip failed"),
            )
        )
        stack.enter_context(
            patch(
                "shorts_maker_v2.pipeline.render_step.apply_text_animation",
                side_effect=RuntimeError("anim failed"),
            )
        )
        stack.enter_context(
            patch(
                "shorts_maker_v2.pipeline.render_step.concatenate_videoclips",
                return_value=final_video,
            )
        )
        concat_audio = stack.enter_context(patch("moviepy.concatenate_audioclips", return_value=looped_bgm_clip))
        stack.enter_context(
            patch(
                "shorts_maker_v2.utils.hwaccel.detect_hw_encoder",
                return_value=("h264_nvenc", ["-preset", "p4"]),
            )
        )
        stack.enter_context(
            patch(
                "shorts_maker_v2.utils.hwaccel.detect_gpu_info",
                side_effect=RuntimeError("gpu lookup failed"),
            )
        )
        write_video = stack.enter_context(patch.object(step._output_renderer, "write", return_value=None))
        stack.enter_context(patch("builtins.print"))

        result = step.run(
            scene_plans=scene_plans,
            scene_assets=scene_assets,
            output_dir=output_dir,
            output_filename="fallback.mp4",
            run_dir=run_dir,
            title="Fallback topic",
            topic="Fallback topic",
        )

    assert result == output_dir / "fallback.mp4"
    assert static_caption.called
    assert pick_bgm.called
    assert concat_audio.called
    assert ducking.called
    write_video.assert_called_once()
