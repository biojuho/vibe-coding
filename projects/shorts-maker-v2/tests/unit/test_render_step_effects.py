from __future__ import annotations

from unittest.mock import MagicMock

from conftest_render import _make_fake_clip, _make_render_step

from shorts_maker_v2.pipeline.render_step import RenderStep

# ─── 랜덤 효과 테스트 ────────────────────────────────────────────────────────


def test_apply_random_effect_has_method() -> None:
    """_apply_random_effect 메서드 존재 확인."""
    step = _make_render_step()
    assert hasattr(step, "_apply_random_effect")
    assert callable(step._apply_random_effect)


def _capture_scale_fn(monkeypatch, effect, *args):
    """줌 효과를 `_zoom_crop` 스텁으로 실행해 효과가 넘긴 scale_fn 을 회수.

    줌 효과들은 시간 가변 줌을 `_zoom_crop(clip, tw, th, scale_fn)` 로 위임한다
    (T-346). scale_fn 은 정규화 진행도 p∈[0,1] → 배율 함수다.
    """
    captured = {}

    def spy(clip, target_width, target_height, scale_fn):
        captured["scale_fn"] = scale_fn
        return clip

    monkeypatch.setattr("shorts_maker_v2.pipeline.render_effects._zoom_crop", spy)
    effect(*args)
    return captured["scale_fn"]


def test_ken_burns_scale_curve(monkeypatch) -> None:
    """_ken_burns는 진행도에 따라 1.0 → 1.06 선형 줌인."""
    clip = _make_fake_clip()
    scale_fn = _capture_scale_fn(monkeypatch, RenderStep._ken_burns, clip, 1080, 1920)
    assert abs(scale_fn(0.0) - 1.0) < 0.001
    assert abs(scale_fn(1.0) - 1.06) < 0.001


def test_dramatic_ken_burns_stronger_zoom(monkeypatch) -> None:
    """_dramatic_ken_burns는 기본 zoom=0.12로 더 강한 효과 (end scale 1.12)."""
    clip = _make_fake_clip()
    scale_fn = _capture_scale_fn(monkeypatch, RenderStep._dramatic_ken_burns, clip, 1080, 1920)
    assert abs(scale_fn(1.0) - 1.12) < 0.001


def test_zoom_out_decreasing_scale(monkeypatch) -> None:
    """_zoom_out는 진행도가 늘수록 scale이 감소한다."""
    clip = _make_fake_clip()
    scale_fn = _capture_scale_fn(monkeypatch, RenderStep._zoom_out, clip, 1080, 1920)
    assert scale_fn(0.0) > scale_fn(1.0)


def test_push_in_ease_out_curve(monkeypatch) -> None:
    """_push_in은 ease-out 커브로 줌인한다 (end scale 1.08)."""
    clip = _make_fake_clip()
    scale_fn = _capture_scale_fn(monkeypatch, RenderStep._push_in, clip, 1080, 1920)
    start = scale_fn(0.0)
    end = scale_fn(1.0)
    assert start < end
    assert abs(end - 1.08) < 0.001


def test_ease_ken_burns_cubic(monkeypatch) -> None:
    """_ease_ken_burns는 ease-in-out cubic으로 1.0 → 1.08."""
    clip = _make_fake_clip()
    scale_fn = _capture_scale_fn(monkeypatch, RenderStep._ease_ken_burns, clip, 1080, 1920)
    assert abs(scale_fn(0.0) - 1.0) < 0.001
    assert abs(scale_fn(1.0) - 1.08) < 0.001


def test_zoom_crop_outputs_target_size() -> None:
    """_zoom_crop은 소스 크기와 무관하게 target 크기 프레임을 내고, 줌인한다."""
    import numpy as np
    from moviepy import ImageClip

    from shorts_maker_v2.pipeline.render_effects import _zoom_crop

    src = ImageClip((np.random.rand(1920, 1080, 3) * 255).astype(np.uint8)).with_duration(2.0)
    zoomed = _zoom_crop(src, 1080, 1920, lambda p: 1.0 + 0.06 * p)
    frame_start = zoomed.get_frame(0.0)
    frame_end = zoomed.get_frame(1.99)
    assert frame_start.shape == (1920, 1080, 3)
    assert frame_end.shape == (1920, 1080, 3)
    # 줌인 → 끝 프레임은 시작 프레임과 다르다
    assert not np.array_equal(frame_start, frame_end)


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
