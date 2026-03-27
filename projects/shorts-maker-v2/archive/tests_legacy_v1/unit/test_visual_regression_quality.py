from __future__ import annotations

import hashlib
from pathlib import Path

_EXPECTED_HASHES = {
    "ai_tech_hook_overlay": "5775ede816bee1ebaa803d1ed1f04c45",
    "ai_tech_body_overlay": "7ccf8b1b7fcc282a99853be5c5c07e84",
    "psychology_hook_overlay": "767c760ece96217628a5fe15f640d888",
    "psychology_body_overlay": "d747a22b69b19c644cafea91ebfa6f81",
}


def _assert_matches_expected_hash(name: str, image_path: Path) -> None:
    current_hash = hashlib.md5(image_path.read_bytes()).hexdigest()
    expected_hash = _EXPECTED_HASHES[name]
    assert expected_hash, f"Missing approved hash for {name}"
    assert current_hash == expected_hash


def _render_text_engine(config: dict, text: str, *, role: str, keywords: list[str], output: Path) -> Path:
    from ShortsFactory.engines.text_engine import TextEngine

    engine = TextEngine(config)
    return engine.render_subtitle(text, role=role, keywords=keywords, output_path=output)


def test_ai_tech_hook_visual_baseline(tmp_path) -> None:
    config = {
        "palette": {"primary": "#00D4FF", "secondary": "#7C3AED", "accent": "#00FF88", "bg": "#0A0E1A"},
        "font_title": "Pretendard-ExtraBold",
        "font_body": "Pretendard-Regular",
        "keyword_highlights": ["GPT", "API", "GPU"],
        "highlight_color": "#00F0FF",
    }
    output = _render_text_engine(
        config,
        "GPT API workflow just changed again.",
        role="hook",
        keywords=["GPT", "API"],
        output=tmp_path / "ai_hook.png",
    )
    _assert_matches_expected_hash("ai_tech_hook_overlay", output)


def test_ai_tech_body_visual_baseline(tmp_path) -> None:
    config = {
        "palette": {"primary": "#00D4FF", "secondary": "#7C3AED", "accent": "#00FF88", "bg": "#0A0E1A"},
        "font_title": "Pretendard-ExtraBold",
        "font_body": "Pretendard-Regular",
        "keyword_highlights": ["GPT", "BENCHMARK", "CUDA"],
        "highlight_color": "#00F0FF",
    }
    output = _render_text_engine(
        config,
        "New benchmark numbers are public today.",
        role="body",
        keywords=["BENCHMARK"],
        output=tmp_path / "ai_body.png",
    )
    _assert_matches_expected_hash("ai_tech_body_overlay", output)


def test_psychology_hook_visual_baseline(tmp_path) -> None:
    config = {
        "palette": {"primary": "#E879F9", "secondary": "#F59E0B", "accent": "#FB7185", "bg": "#1A0A1E"},
        "font_title": "Pretendard-ExtraBold",
        "font_body": "Pretendard-Regular",
        "keyword_highlights": ["LOSS", "BIAS"],
        "highlight_color": "#E879F9",
    }
    output = _render_text_engine(
        config,
        "Loss bias hurts more than the same reward helps.",
        role="hook",
        keywords=["LOSS", "BIAS"],
        output=tmp_path / "psych_hook.png",
    )
    _assert_matches_expected_hash("psychology_hook_overlay", output)


def test_psychology_body_visual_baseline(tmp_path) -> None:
    config = {
        "palette": {"primary": "#E879F9", "secondary": "#F59E0B", "accent": "#FB7185", "bg": "#1A0A1E"},
        "font_title": "Pretendard-ExtraBold",
        "font_body": "Pretendard-Regular",
        "keyword_highlights": ["SELF", "DEFENSE"],
        "highlight_color": "#E879F9",
    }
    output = _render_text_engine(
        config,
        "Your self image is protected by a defense pattern.",
        role="body",
        keywords=["SELF", "DEFENSE"],
        output=tmp_path / "psych_body.png",
    )
    _assert_matches_expected_hash("psychology_body_overlay", output)
