from __future__ import annotations

from execution.lyria_bgm_generator import _build_output_path, _slugify


def test_slugify_preserves_korean_prompt_signal() -> None:
    assert _slugify("미니멀 테크노") == "미니멀-테크노"


def test_slugify_uses_fallback_for_empty_prompt() -> None:
    assert _slugify("!!!") == "lyria-bgm"


def test_build_output_path_uses_prompt_slug(tmp_path) -> None:
    output_path = _build_output_path("감성 피아노", tmp_path, "wav")

    assert output_path == tmp_path / "감성-피아노.wav"
