from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch


from shorts_maker_v2.pipeline.render_step import RenderStep

from conftest_render import _make_render_step


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
