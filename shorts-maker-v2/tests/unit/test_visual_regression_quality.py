from __future__ import annotations

import hashlib
from pathlib import Path

from PIL import Image


_BASELINE_DIR = Path(__file__).resolve().parents[2] / ".tmp" / "visual_baselines_quality"


def _assert_matches_baseline(name: str, image_path: Path) -> None:
    baseline_path = _BASELINE_DIR / f"{name}.png"
    baseline_path.parent.mkdir(parents=True, exist_ok=True)

    current_bytes = image_path.read_bytes()
    if not baseline_path.exists():
        baseline_path.write_bytes(current_bytes)
        return

    baseline_bytes = baseline_path.read_bytes()
    assert hashlib.md5(current_bytes).hexdigest() == hashlib.md5(baseline_bytes).hexdigest()


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
        "GPT API 경쟁이 다시 뜨거워졌습니다",
        role="hook",
        keywords=["GPT", "API"],
        output=tmp_path / "ai_hook.png",
    )
    _assert_matches_baseline("ai_tech_hook_overlay", output)


def test_ai_tech_body_visual_baseline(tmp_path) -> None:
    config = {
        "palette": {"primary": "#00D4FF", "secondary": "#7C3AED", "accent": "#00FF88", "bg": "#0A0E1A"},
        "font_title": "Pretendard-ExtraBold",
        "font_body": "Pretendard-Regular",
        "keyword_highlights": ["GPT", "벤치마크", "CUDA"],
        "highlight_color": "#00F0FF",
    }
    output = _render_text_engine(
        config,
        "벤치마크 수치가 다시 공개됐습니다",
        role="body",
        keywords=["벤치마크"],
        output=tmp_path / "ai_body.png",
    )
    _assert_matches_baseline("ai_tech_body_overlay", output)


def test_psychology_hook_visual_baseline(tmp_path) -> None:
    config = {
        "palette": {"primary": "#E879F9", "secondary": "#F59E0B", "accent": "#FB7185", "bg": "#1A0A1E"},
        "font_title": "Pretendard-ExtraBold",
        "font_body": "Pretendard-Regular",
        "keyword_highlights": ["인지 부조화", "자존감"],
        "highlight_color": "#E879F9",
    }
    output = _render_text_engine(
        config,
        "인지 부조화가 커질수록 더 불편해집니다",
        role="hook",
        keywords=["인지 부조화"],
        output=tmp_path / "psych_hook.png",
    )
    _assert_matches_baseline("psychology_hook_overlay", output)


def test_psychology_body_visual_baseline(tmp_path) -> None:
    config = {
        "palette": {"primary": "#E879F9", "secondary": "#F59E0B", "accent": "#FB7185", "bg": "#1A0A1E"},
        "font_title": "Pretendard-ExtraBold",
        "font_body": "Pretendard-Regular",
        "keyword_highlights": ["자존감", "방어기제"],
        "highlight_color": "#E879F9",
    }
    output = _render_text_engine(
        config,
        "자존감이 낮을 때는 방어기제가 먼저 올라옵니다",
        role="body",
        keywords=["자존감", "방어기제"],
        output=tmp_path / "psych_body.png",
    )
    _assert_matches_baseline("psychology_body_overlay", output)
