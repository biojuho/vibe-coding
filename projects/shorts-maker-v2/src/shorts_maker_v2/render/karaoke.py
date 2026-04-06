"""
카라오케 스타일 자막 렌더링 (YouTube Shorts 트렌드).
단어를 N개씩 묶어 순서대로 표시 + 다크 배경 박스.

Phase 2 개선:
- sentence_boundary_chunks: 구두점 경계 기반 자연 묶음 분할
- apply_ssml_break_correction: SSML <break> offset 누적 보정
- group_into_chunks: boundary_aware 옵션 추가
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from shorts_maker_v2.render.caption_pillow import CaptionStyle, _load_font


@dataclass
class WordSegment:
    word: str
    start: float  # 오디오 내 시작 시각 (초)
    end: float  # 오디오 내 종료 시각 (초)


def load_words_json(json_path: Path) -> list[WordSegment]:
    """Whisper / EdgeTTS WordBoundary 타임스탬프 JSON 로드."""
    data = json.loads(json_path.read_text(encoding="utf-8"))
    return [
        WordSegment(word=w["word"].strip(), start=float(w["start"]), end=float(w["end"]))
        for w in data
        if w.get("word", "").strip()
    ]


# ── Phase 2: SSML break offset 보정 ─────────────────────────────────────────

# SSML break 태그 파싱 정규식
_SSML_BREAK_RE = re.compile(r'<break\s+time="(\d+(?:\.\d+)?)(ms|s)"\s*/?>', re.IGNORECASE)


def apply_ssml_break_correction(
    words: list[WordSegment],
    ssml_text: str,
) -> list[WordSegment]:
    """SSML <break> 태그의 누적 대기시간을 WordSegment offset에 보정.

    EdgeTTS WordBoundary 이벤트는 SSML break 직후 단어의 start가
    break 시간만큼 지연되지만, 일부 버전에서는 이를 반영하지 않을 수 있습니다.
    이 함수는 SSML 텍스트에서 break 태그를 파싱해 offset 누적값을 계산하고,
    이미 반영된 경우에는 변동이 없도록 conservative하게 적용합니다.

    Args:
        words: WordBoundary 이벤트로 생성된 단어 타이밍 목록.
        ssml_text: 원본 SSML 텍스트 (break 태그 포함).

    Returns:
        SSML break 보정이 적용된 WordSegment 목록 (새 객체).
    """
    if not _SSML_BREAK_RE.search(ssml_text):
        return words  # break 태그 없으면 그대로 반환

    # break 태그 총 대기시간 계산 (초)
    total_break_sec = 0.0
    for match in _SSML_BREAK_RE.finditer(ssml_text):
        value = float(match.group(1))
        unit = match.group(2).lower()
        total_break_sec += value / 1000.0 if unit == "ms" else value

    if total_break_sec <= 0 or not words:
        return words

    # EdgeTTS가 이미 break를 반영했는지 추론:
    # 첫 단어 start가 total_break_sec의 80% 이상이면 이미 반영된 것으로 판단
    first_start = words[0].start if words else 0.0
    already_reflected = first_start >= total_break_sec * 0.8

    if already_reflected:
        return words  # 이미 반영됨 → 보정 불필요

    # 보정 적용: 모든 단어의 start/end에 break 시간 추가
    return [
        WordSegment(
            word=w.word,
            start=round(w.start + total_break_sec, 4),
            end=round(w.end + total_break_sec, 4),
        )
        for w in words
    ]


# ── Phase 2: 자연어 경계 기반 청크 분할 ──────────────────────────────────────

# 한국어 구두점 + 영어 구두점 경계 패턴
_BOUNDARY_CHARS = frozenset(".!?,。！？，")


def sentence_boundary_chunks(
    words: list[WordSegment],
    max_words: int = 4,
    min_words: int = 1,
) -> list[tuple[float, float, str]]:
    """자연어 경계(구두점) 기반 청크 분割.

    구두점이 있는 단어에서 강제로 청크를 분리하여
    발화의 자연스러운 쉬는 지점과 자막을 일치시킵니다.

    Args:
        words: 단어 타이밍 목록.
        max_words: 청크당 최대 단어 수 (구두점 없어도 강제 분리).
        min_words: 청크 병합 임계값 (이보다 짧은 청크는 다음과 병합).

    Returns:
        (start_sec, end_sec, text) 튜플 목록.
    """
    if not words:
        return []

    chunks: list[tuple[float, float, str]] = []
    current: list[WordSegment] = []

    def _flush(buf: list[WordSegment], next_start: float | None = None) -> None:
        if not buf:
            return
        start = buf[0].start
        end = next_start if next_start is not None else buf[-1].end
        text = " ".join(w.word for w in buf)
        chunks.append((start, end, text))

    for i, w in enumerate(words):
        current.append(w)
        word_clean = w.word.rstrip()
        has_boundary = bool(word_clean) and word_clean[-1] in _BOUNDARY_CHARS
        is_max = len(current) >= max_words
        is_last = i == len(words) - 1

        if is_last:
            _flush(current)
            current = []
        elif has_boundary or is_max:
            next_start = words[i + 1].start if i + 1 < len(words) else None
            _flush(current, next_start)
            current = []

    return chunks


def group_word_segments(
    words: list[WordSegment],
    chunk_size: int,
    *,
    boundary_aware: bool = True,
) -> list[tuple[float, float, str, list[WordSegment]]]:
    """단어 세그먼트를 청크 단위로 묶어 원본 타이밍까지 유지합니다."""
    if not words:
        return []

    grouped: list[tuple[float, float, str, list[WordSegment]]] = []

    if boundary_aware:
        current: list[WordSegment] = []
        for i, word in enumerate(words):
            current.append(word)
            word_clean = word.word.rstrip()
            has_boundary = bool(word_clean) and word_clean[-1] in _BOUNDARY_CHARS
            is_max = len(current) >= chunk_size
            is_last = i == len(words) - 1

            if not (is_last or has_boundary or is_max):
                continue

            end = words[i + 1].start if not is_last else current[-1].end
            chunk_words = list(current)
            grouped.append(
                (
                    chunk_words[0].start,
                    end,
                    " ".join(w.word for w in chunk_words),
                    chunk_words,
                )
            )
            current = []
        return grouped

    for i in range(0, len(words), chunk_size):
        chunk_words = words[i : i + chunk_size]
        end = words[i + chunk_size].start if i + chunk_size < len(words) else chunk_words[-1].end
        grouped.append(
            (
                chunk_words[0].start,
                end,
                " ".join(w.word for w in chunk_words),
                list(chunk_words),
            )
        )
    return grouped


def group_into_chunks(
    words: list[WordSegment],
    chunk_size: int,
    *,
    boundary_aware: bool = True,
) -> list[tuple[float, float, str]]:
    """단어를 chunk_size 개씩 묶어 (start, end, text) 반환.

    Phase 2: boundary_aware=True이면 sentence_boundary_chunks를 사용해
    구두점 경계에서 자연스럽게 분리합니다 (max_words는 chunk_size 사용).

    Args:
        words: 단어 타이밍 목록.
        chunk_size: 청크당 최대 단어 수.
        boundary_aware: True이면 구두점 경계 기반 분할 사용 (기본값).

    Returns:
        (start_sec, end_sec, text) 튜플 목록.
    """
    return [
        (start, end, text)
        for start, end, text, _ in group_word_segments(
            words,
            chunk_size,
            boundary_aware=boundary_aware,
        )
    ]


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _scale_style(style: CaptionStyle, *, font_size: int | None = None, scale: int = 1) -> CaptionStyle:
    """Create a new CaptionStyle with scaled dimensions."""
    return CaptionStyle(
        font_size=(font_size or style.font_size) * scale,
        margin_x=style.margin_x * scale,
        bottom_offset=style.bottom_offset * scale,
        text_color=style.text_color,
        stroke_color=style.stroke_color,
        stroke_width=style.stroke_width * scale,
        line_spacing=style.line_spacing * scale,
        font_candidates=style.font_candidates,
        mode=style.mode,
        words_per_chunk=style.words_per_chunk,
        bg_color=style.bg_color,
        bg_opacity=style.bg_opacity,
        bg_radius=style.bg_radius * scale,
    )


def _auto_scale_font(style: CaptionStyle, text: str, max_width: int) -> CaptionStyle:
    """텍스트가 max_width에 맞도록 폰트를 자동 축소.

    최소 폰트 크기는 원래의 50%로 제한.
    """
    from PIL import Image, ImageDraw

    min_font_size = max(24, style.font_size // 2)
    current_size = style.font_size

    while current_size > min_font_size:
        test_style = _scale_style(style, font_size=current_size)
        font = _load_font(test_style)
        probe = Image.new("RGBA", (max_width * 2, 400), (0, 0, 0, 0))
        probe_draw = ImageDraw.Draw(probe)
        bbox = probe_draw.textbbox((0, 0), text, font=font, stroke_width=0)
        text_w = bbox[2] - bbox[0]
        pad_x = 44
        if text_w + pad_x * 2 <= max_width:
            break
        current_size -= 4

    if current_size != style.font_size:
        return _scale_style(style, font_size=current_size)
    return style


def render_karaoke_image(
    text: str,
    canvas_width: int,
    style: CaptionStyle,
    output_path: Path,
) -> Path:
    """
    단어 청크 하나를 자막 이미지로 렌더링.
    2x 슈퍼샘플링 + 다크 반투명 rounded-rect 배경 + 드롭 섀도우 + 텍스트.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    scale = 2  # 2x 슈퍼샘플링

    # 자동 폰트 축소: 텍스트가 캔버스를 초과하면 축소
    style = _auto_scale_font(style, text, canvas_width)

    # 2x 스케일 스타일
    hi_style = CaptionStyle(
        font_size=style.font_size * scale,
        margin_x=style.margin_x * scale,
        bottom_offset=style.bottom_offset * scale,
        text_color=style.text_color,
        stroke_color=style.stroke_color,
        stroke_width=style.stroke_width * scale,
        line_spacing=style.line_spacing * scale,
        font_candidates=style.font_candidates,
        mode=style.mode,
        words_per_chunk=style.words_per_chunk,
        bg_color=style.bg_color,
        bg_opacity=style.bg_opacity,
        bg_radius=style.bg_radius * scale,
    )
    hi_width = canvas_width * scale
    font = _load_font(hi_style)
    pad_x, pad_y = 44 * scale, 20 * scale

    # 텍스트 크기 측정
    probe = Image.new("RGBA", (hi_width, 400 * scale), (0, 0, 0, 0))
    probe_draw = ImageDraw.Draw(probe)
    bbox = probe_draw.textbbox((0, 0), text, font=font, stroke_width=0)
    text_w = max(1, int(bbox[2] - bbox[0]))
    text_h = max(1, int(bbox[3] - bbox[1]))

    image_w = hi_width - hi_style.margin_x * 2 if hi_style.bg_radius == 0 else min(hi_width, text_w + pad_x * 2)
    image_h = text_h + pad_y * 2

    image = Image.new("RGBA", (image_w, image_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    # 배경 rounded rectangle
    r, g, b = _hex_to_rgb(style.bg_color)
    bg_rgba = (r, g, b, style.bg_opacity)
    draw.rounded_rectangle(
        [(0, 0), (image_w - 1, image_h - 1)],
        radius=hi_style.bg_radius,
        fill=bg_rgba,
    )

    # 텍스트 (가운데 정렬)
    x = (image_w - text_w) / 2 - bbox[0]
    y = pad_y - bbox[1]

    # 드롭 섀도우
    shadow_offset = max(2, scale)
    draw.text(
        (x + shadow_offset, y + shadow_offset),
        text,
        font=font,
        fill=(0, 0, 0, 140),
        stroke_width=0,
    )

    # 본문 텍스트
    draw.text(
        (x, y),
        text,
        font=font,
        fill=style.text_color,
        stroke_width=hi_style.stroke_width,
        stroke_fill=style.stroke_color if hi_style.stroke_width > 0 else None,
    )

    # 다운샘플 (LANCZOS)
    final_w = max(1, image_w // scale)
    final_h = max(1, image_h // scale)
    image = image.resize((final_w, final_h), Image.LANCZOS)
    image.save(output_path, format="PNG")
    return output_path


def _render_word_glow(
    image: Image.Image,
    position: tuple[float, float],
    word: str,
    font: ImageFont,
    glow_color: str,
    glow_radius: int = 6,
) -> Image.Image:
    """활성 단어 뒤에 글로우(발광) 레이어를 합성.

    1. image 크기의 임시 RGBA 이미지 생성
    2. glow_color + alpha 180으로 단어 렌더링
    3. GaussianBlur 적용
    4. 원본 image 아래에 합성하여 반환

    Args:
        image: 글로우를 합성할 대상 이미지 (RGBA).
        position: 단어 렌더링 위치 (x, y).
        word: 글로우 대상 단어 텍스트.
        font: PIL ImageFont 인스턴스.
        glow_color: 글로우 색상 (hex).
        glow_radius: GaussianBlur 반경.

    Returns:
        글로우가 합성된 새 RGBA 이미지.
    """
    gr, gg, gb = _hex_to_rgb(glow_color)
    glow_layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow_layer)
    glow_draw.text(position, word, font=font, fill=(gr, gg, gb, 180))
    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(radius=glow_radius))
    # 글로우를 원본 아래에 합성: glow 위에 원본을 붙인다
    result = Image.alpha_composite(glow_layer, image)
    return result


def render_karaoke_highlight_image(
    words: list[str],
    active_word_index: int,
    canvas_width: int,
    style: CaptionStyle,
    highlight_color: str,
    output_path: Path,
    keyword_colors: dict[str, tuple[int, int, int, int]] | None = None,
) -> Path:
    """
    청크 내 단어를 모두 표시하되, active 단어만 highlight 색상으로 강조.
    2x 슈퍼샘플링 + rounded-rect 배경 + 드롭 섀도우.

    시각 효과:
    - 활성 단어: 1.15x 확대 폰트 + 글로우 효과 + highlight_color
    - 비활성 단어: 반투명 흰색 (alpha 120)

    Args:
        words: 청크 내 단어 리스트 (예: ["오늘", "알려드릴", "내용은"])
        active_word_index: 하이라이트할 단어 인덱스 (0-based)
        canvas_width: 영상 가로 해상도
        style: CaptionStyle 설정
        highlight_color: 하이라이트 색상 (hex)
        output_path: 출력 PNG 경로
        keyword_colors: 키워드별 강조 색상 매핑 (선택).
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    scale = 2

    # 자동 폰트 축소
    full_text = " ".join(words)
    style = _auto_scale_font(style, full_text, canvas_width)

    hi_style = _scale_style(style, scale=scale)
    hi_width = canvas_width * scale
    font = _load_font(hi_style)
    active_font = _load_font(_scale_style(hi_style, font_size=int(hi_style.font_size * 1.15)))
    pad_x, pad_y = 44 * scale, 20 * scale

    # 단어 측정
    word_widths, max_text_h, space_w, normal_ascent, active_ascent = _measure_words(
        words,
        active_word_index,
        font,
        active_font,
        hi_width,
        scale,
    )
    text_w = max(1, int(sum(word_widths) + space_w * max(0, len(words) - 1)))
    text_h = max(1, max_text_h)

    image_w = hi_width - hi_style.margin_x * 2 if hi_style.bg_radius == 0 else min(hi_width, text_w + pad_x * 2)
    image_h = text_h + pad_y * 2

    # 배경 렌더링
    image = Image.new("RGBA", (image_w, image_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    r, g, b = _hex_to_rgb(style.bg_color)
    draw.rounded_rectangle(
        [(0, 0), (image_w - 1, image_h - 1)],
        radius=hi_style.bg_radius,
        fill=(r, g, b, style.bg_opacity),
    )

    # 단어별 렌더링
    glow_position, glow_word = _render_words_on_image(
        draw,
        words,
        active_word_index,
        word_widths,
        space_w,
        font,
        active_font,
        hi_style,
        style,
        highlight_color,
        keyword_colors,
        image_w,
        text_w,
        pad_y,
        normal_ascent,
        active_ascent,
        scale,
    )

    # 글로우 효과
    if glow_position is not None and glow_word:
        image = _render_word_glow(
            image,
            glow_position,
            glow_word,
            active_font,
            highlight_color,
            glow_radius=max(4, 6 * scale),
        )

    # 다운샘플
    final_w = max(1, image_w // scale)
    final_h = max(1, image_h // scale)
    image = image.resize((final_w, final_h), Image.LANCZOS)
    image.save(output_path, format="PNG")
    return output_path


def _measure_words(
    words: list[str],
    active_word_index: int,
    font: ImageFont.FreeTypeFont,
    active_font: ImageFont.FreeTypeFont,
    hi_width: int,
    scale: int,
) -> tuple[list[float], int, float, int, int]:
    """Measure word widths, heights, space width, and baseline ascents."""
    probe = Image.new("RGBA", (hi_width, 400 * scale), (0, 0, 0, 0))
    probe_draw = ImageDraw.Draw(probe)
    space_w = probe_draw.textlength(" ", font=font) if hasattr(probe_draw, "textlength") else font.getlength(" ")

    word_widths: list[float] = []
    max_text_h = 0
    for i, word in enumerate(words):
        use_font = active_font if i == active_word_index else font
        w_bbox = probe_draw.textbbox((0, 0), word, font=use_font, stroke_width=0)
        word_widths.append(w_bbox[2] - w_bbox[0])
        h = w_bbox[3] - w_bbox[1]
        if h > max_text_h:
            max_text_h = h

    normal_bbox = probe_draw.textbbox((0, 0), "Ag가", font=font, stroke_width=0)
    active_bbox = probe_draw.textbbox((0, 0), "Ag가", font=active_font, stroke_width=0)
    return word_widths, max_text_h, space_w, -normal_bbox[1], -active_bbox[1]


def _render_words_on_image(
    draw: ImageDraw.ImageDraw,
    words: list[str],
    active_word_index: int,
    word_widths: list[float],
    space_w: float,
    font: ImageFont.FreeTypeFont,
    active_font: ImageFont.FreeTypeFont,
    hi_style: CaptionStyle,
    style: CaptionStyle,
    highlight_color: str,
    keyword_colors: dict[str, tuple[int, int, int, int]] | None,
    image_w: int,
    text_w: int,
    pad_y: int,
    normal_ascent: int,
    active_ascent: int,
    scale: int,
) -> tuple[tuple[float, float] | None, str]:
    """Render each word with shadow, returns glow position and word."""
    base_x = (image_w - text_w) / 2
    hr, hg, hb = _hex_to_rgb(highlight_color)
    dim_color = (255, 255, 255, 255)
    active_color = (hr, hg, hb, 255)
    shadow_offset = max(2, scale)

    glow_position: tuple[float, float] | None = None
    glow_word: str = ""
    x_cursor = base_x

    for i, word in enumerate(words):
        is_active = i == active_word_index
        use_font = active_font if is_active else font
        base_y = pad_y + (normal_ascent - active_ascent) if is_active else pad_y

        # Determine word color
        color = active_color if is_active else dim_color
        if not is_active and keyword_colors and len(word) >= 2:
            clean_word = word.rstrip(".,?!;:~").lower()
            if clean_word in keyword_colors:
                color = keyword_colors[clean_word]

        # Drop shadow
        draw.text(
            (x_cursor + shadow_offset, base_y + shadow_offset),
            word,
            font=use_font,
            fill=(0, 0, 0, 140),
            stroke_width=0,
        )
        # Main text
        draw.text(
            (x_cursor, base_y),
            word,
            font=use_font,
            fill=color,
            stroke_width=hi_style.stroke_width,
            stroke_fill=style.stroke_color if hi_style.stroke_width > 0 else None,
        )

        if is_active:
            glow_position = (x_cursor, base_y)
            glow_word = word

        x_cursor += word_widths[i] + space_w

    return glow_position, glow_word


def build_keyword_color_map(
    keywords: list[str],
    color_hex: str = "#E879F9",
) -> dict[str, tuple[int, int, int, int]]:
    """키워드 리스트 → 하이라이트 색상 매핑 dict 생성.

    단일 단어와 복합어 모두 지원.
    복합어(예: '인지 부조화')는 각 구성 단어로도 매핑.

    Args:
        keywords: 하이라이트할 키워드/전문 용어 리스트.
        color_hex: 강조 색상 (hex).

    Returns:
        {단어: (r, g, b, 255)} 딕셔너리.
    """
    r, g, b = _hex_to_rgb(color_hex)
    color = (r, g, b, 255)
    result: dict[str, tuple[int, int, int, int]] = {}
    for kw in keywords:
        parts = kw.split()
        for part in parts:
            clean = part.strip(".,?!;:~").lower()
            if len(clean) >= 2:
                result[clean] = color
        # 전체 키워드 자체도 등록
        whole = kw.strip().lower()
        if whole:
            result[whole] = color
    return result
