"""Phase 1 #6 — 이미지 프롬프트 텍스트 억제 helper 회귀.

2026-05-11 thumbnail/배경 케이스: DALL-E/Pollinations/Gemini 가 영어 단어
("MIND UNLEASH" 등) 를 이미지에 그려넣어 YouTube 업로드 품질 차단.
"""

from __future__ import annotations

from shorts_maker_v2.pipeline.media._prompt_filters import with_text_suppression


def test_appends_suppression_to_clean_prompt() -> None:
    """텍스트 억제 negative 가 들어 있지 않은 프롬프트엔 보강된다."""
    prompt = "Cinematic photography of a glowing brain neural network"
    out = with_text_suppression(prompt)
    assert out.startswith(prompt)
    assert "no text" in out.lower()
    assert "no typography" in out.lower()


def test_skips_when_already_suppressed_no_text() -> None:
    """기존 'No text' 가 있으면 중복 부착하지 않는다."""
    prompt = "Bright neon scene. No text, no letters, no words."
    out = with_text_suppression(prompt)
    assert out == prompt
    # 단 1회만 등장하도록 (case-insensitive count)
    assert out.lower().count("no text") == 1


def test_skips_when_already_suppressed_text_free() -> None:
    """`text-free` 같은 대안 표기도 인식한다."""
    prompt = "Watercolor illustration, text-free composition"
    out = with_text_suppression(prompt)
    assert out == prompt


def test_skips_when_already_suppressed_without_text() -> None:
    """`without text` 패턴도 인식."""
    prompt = "Studio photography without text overlays"
    out = with_text_suppression(prompt)
    assert out == prompt


def test_empty_string_passthrough() -> None:
    assert with_text_suppression("") == ""


def test_case_insensitive_marker_match() -> None:
    """대문자 표기 마커도 중복 부착 방지."""
    prompt = "Hero shot. NO TEXT, no labels."
    out = with_text_suppression(prompt)
    assert out == prompt


def test_does_not_modify_already_suppressed_thumbnail_prompts() -> None:
    """thumbnail_step.py 의 채널별 프롬프트는 이미 'No text, no letters, no words.' 가
    포함되어 있어 변경되지 않아야 한다(이중 부착 방지)."""
    # thumbnail_step.py 의 채널 base 프롬프트 한 줄(요약형)
    prompt = (
        "Soft watercolor illustration style, warm pastel colors, "
        "dreamy soft focus, therapeutic calm mood. No text, no letters, no words."
    )
    out = with_text_suppression(prompt)
    assert out == prompt
