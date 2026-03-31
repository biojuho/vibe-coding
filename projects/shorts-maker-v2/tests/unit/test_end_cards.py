from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from shorts_maker_v2.render import ending_card, outro_card

WINDOWS_FONT_CANDIDATES = [
    str(path)
    for path in (
        Path(r"C:\Windows\Fonts\malgun.ttf"),
        Path(r"C:\Windows\Fonts\arial.ttf"),
        Path(r"C:\Windows\Fonts\seguiemj.ttf"),
    )
    if path.exists()
]


def _font_candidates() -> list[str]:
    if not WINDOWS_FONT_CANDIDATES:
        pytest.skip("Windows font files not available for card rendering tests")
    return WINDOWS_FONT_CANDIDATES


def test_render_outro_card_creates_expected_png(tmp_path: Path) -> None:
    output = tmp_path / "outro.png"

    result = outro_card.render_outro_card(
        target_width=540,
        target_height=960,
        output_path=output,
        channel_key="ai_tech",
        font_candidates=_font_candidates(),
    )

    assert result == output
    assert output.exists()
    with Image.open(output) as image:
        assert image.size == (540, 960)
        assert image.mode == "RGBA"


def test_render_outro_card_accepts_unknown_channel_key(tmp_path: Path) -> None:
    output = tmp_path / "fallback_outro.png"

    result = outro_card.render_outro_card(
        target_width=320,
        target_height=568,
        output_path=output,
        channel_key="unknown_channel",
        font_candidates=_font_candidates(),
    )

    assert result.exists()
    assert result.stat().st_size > 0


def test_ensure_outro_assets_reuses_existing_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    existing = tmp_path / "outro" / "ai_tech_outro.png"
    existing.parent.mkdir(parents=True, exist_ok=True)
    existing.write_bytes(b"existing")

    def fail_render(*args, **kwargs):
        raise AssertionError("render_outro_card should not be called when asset already exists")

    monkeypatch.setattr(outro_card, "render_outro_card", fail_render)

    result = outro_card.ensure_outro_assets("ai_tech", tmp_path)

    assert result == existing
    assert result.read_bytes() == b"existing"


def test_ensure_outro_assets_returns_none_when_render_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        outro_card, "render_outro_card", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom"))
    )

    result = outro_card.ensure_outro_assets("ai_tech", tmp_path)

    assert result is None


def test_render_branded_ending_card_creates_expected_png(tmp_path: Path) -> None:
    output = tmp_path / "ending.png"

    result = ending_card.render_branded_ending_card(
        target_width=540,
        target_height=960,
        output_path=output,
        channel_key="psychology",
        font_candidates=_font_candidates(),
    )

    assert result == output
    assert output.exists()
    with Image.open(output) as image:
        assert image.size == (540, 960)
        assert image.mode == "RGBA"


def test_render_ending_card_wrapper_delegates_to_branded_renderer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    expected = tmp_path / "delegated.png"

    def fake_render_branded_ending_card(**kwargs):
        captured.update(kwargs)
        return expected

    monkeypatch.setattr(ending_card, "render_branded_ending_card", fake_render_branded_ending_card)

    result = ending_card.render_ending_card(
        target_width=1080,
        target_height=1920,
        output_path=expected,
        channel_name="ignored",
        font_candidates=["font-a.ttf"],
        channel_key="space",
    )

    assert result == expected
    assert captured == {
        "target_width": 1080,
        "target_height": 1920,
        "output_path": expected,
        "channel_key": "space",
        "font_candidates": ["font-a.ttf"],
    }


def test_hex_to_rgb_helpers_match_expected_values() -> None:
    assert outro_card._hex_to_rgb("#A855F7") == (168, 85, 247)
    assert ending_card._hex_to_rgb("#4CAF50") == (76, 175, 80)
