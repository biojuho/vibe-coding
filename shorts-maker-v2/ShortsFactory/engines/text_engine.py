"""
text_engine.py — 자막/타이포그래피 엔진
=======================================
채널별 palette + keyword_highlights를 기반으로
자막 이미지를 생성합니다.

독립 사용:
    from ShortsFactory.engines.text_engine import TextEngine
    engine = TextEngine(channel_config)
    path = engine.render_subtitle("성능 3배 향상", keywords=["3배"], role="body")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFilter, ImageFont

logger = logging.getLogger(__name__)

# ── 폰트 후보 (Windows 기준, fallback 포함) ────────────────────────────────
_FONT_CANDIDATES: dict[str, list[str]] = {
    "Pretendard-ExtraBold": [
        "C:/Windows/Fonts/Pretendard-ExtraBold.otf",
        "C:/Windows/Fonts/malgunbd.ttf",
    ],
    "Pretendard-Bold": [
        "C:/Windows/Fonts/Pretendard-Bold.otf",
        "C:/Windows/Fonts/malgunbd.ttf",
    ],
    "Pretendard-Regular": [
        "C:/Windows/Fonts/Pretendard-Regular.otf",
        "C:/Windows/Fonts/malgun.ttf",
    ],
    "NanumMyeongjo-Bold": [
        "C:/Windows/Fonts/NanumMyeongjoBold.ttf",
        "C:/Windows/Fonts/malgunbd.ttf",
    ],
}


def _resolve_font(font_name: str, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """폰트 이름으로 실제 폰트 파일을 찾아 로드합니다."""
    candidates = _FONT_CANDIDATES.get(font_name, [])
    # 직접 경로가 주어진 경우
    if not candidates:
        p = Path(font_name)
        if p.exists():
            candidates = [str(p)]
        else:
            candidates = [
                "C:/Windows/Fonts/malgunbd.ttf",
                "C:/Windows/Fonts/malgun.ttf",
            ]
    for path in candidates:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


@dataclass
class TextStyle:
    """렌더링에 사용할 텍스트 스타일 파라미터."""
    font_size: int = 72
    text_color: str = "#FFFFFF"
    stroke_color: str = "#000000"
    stroke_width: int = 4
    bg_color: str = "#000000"
    bg_opacity: int = 185
    padding: int = 20
    line_spacing: int = 12


class TextEngine:
    """채널별 자막/타이포그래피 엔진.

    Args:
        channel_config: channels.yaml에서 읽은 채널 설정 dict.
    """

    def __init__(self, channel_config: dict[str, Any]) -> None:
        self.config = channel_config
        self.palette = channel_config.get("palette", {})
        self.font_title = channel_config.get("font_title", "Pretendard-ExtraBold")
        self.font_body = channel_config.get("font_body", "Pretendard-Regular")
        self.keyword_highlights = channel_config.get("keyword_highlights", {})
        self._canvas_width = 1080
        self._canvas_height = 1920

    # ── 공개 메서드 ─────────────────────────────────────────────────────

    def render_subtitle(
        self,
        text: str,
        *,
        keywords: list[str] | None = None,
        role: str = "body",
        output_path: Path | None = None,
    ) -> Path:
        """텍스트와 키워드 하이라이트를 적용한 자막 이미지를 생성합니다.

        Args:
            text: 자막 텍스트.
            keywords: 하이라이트할 키워드 리스트.
            role: 씬 역할 ("hook", "body", "cta").
            output_path: 출력 경로 (None이면 임시 파일).

        Returns:
            생성된 자막 이미지 경로.
        """
        if output_path is None:
            import tempfile
            output_path = Path(tempfile.mktemp(suffix=".png"))

        output_path.parent.mkdir(parents=True, exist_ok=True)

        style = self._get_style(role)
        font_name = self.font_title if role == "hook" else self.font_body
        font = _resolve_font(font_name, style.font_size)

        # 이미지 생성 (2x 슈퍼샘플링)
        scale = 2
        hi_size = style.font_size * scale
        hi_font = _resolve_font(font_name, hi_size)
        canvas_w = self._canvas_width * scale

        # 텍스트 줄바꿈
        probe_img = Image.new("RGBA", (canvas_w, 200), (0, 0, 0, 0))
        draw = ImageDraw.Draw(probe_img)
        max_text_w = canvas_w - (style.padding * 2 * scale)
        lines = self._wrap_lines(draw, text, hi_font, max_text_w, style.stroke_width * scale)
        line_text = "\n".join(lines)

        # 텍스트 바운딩 박스 계산
        bbox = draw.multiline_textbbox(
            (0, 0), line_text, font=hi_font,
            spacing=style.line_spacing * scale,
            stroke_width=style.stroke_width * scale,
        )
        text_w = int(bbox[2] - bbox[0])
        text_h = int(bbox[3] - bbox[1])
        img_w = min(canvas_w, text_w + style.padding * 4 * scale)
        img_h = text_h + style.padding * 2 * scale

        image = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)

        # 배경 박스 (반투명)
        if style.bg_opacity > 0:
            bg_layer = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
            bg_draw = ImageDraw.Draw(bg_layer)
            bg_r, bg_g, bg_b = self._hex_to_rgb(style.bg_color)
            bg_draw.rounded_rectangle(
                [(0, 0), (img_w, img_h)],
                radius=18 * scale,
                fill=(bg_r, bg_g, bg_b, style.bg_opacity),
            )
            image = Image.alpha_composite(image, bg_layer)
            draw = ImageDraw.Draw(image)

        tx = (img_w - text_w) / 2
        ty = style.padding * scale - bbox[1]

        # 키워드가 없으면 단색 텍스트
        if not keywords:
            # 드롭 섀도우
            draw.multiline_text(
                (tx + scale, ty + scale), line_text, font=hi_font,
                fill=(0, 0, 0, 160), spacing=style.line_spacing * scale,
                align="center",
            )
            draw.multiline_text(
                (tx, ty), line_text, font=hi_font,
                fill=style.text_color,
                stroke_width=style.stroke_width * scale,
                stroke_fill=style.stroke_color,
                spacing=style.line_spacing * scale,
                align="center",
            )
        else:
            # 키워드 하이라이트 적용 — 줄별로 처리
            self._draw_highlighted_text(
                draw, lines, hi_font, tx, ty,
                style, scale, keywords, img_w,
            )

        # 다운샘플
        final_w = max(1, img_w // scale)
        final_h = max(1, img_h // scale)
        image = image.resize((final_w, final_h), Image.LANCZOS)
        image.save(output_path, format="PNG")
        logger.debug("[TextEngine] 자막 렌더: %s (%d×%d)", output_path.name, final_w, final_h)
        return output_path

    def render_title(self, text: str, *, output_path: Path | None = None) -> Path:
        """타이틀 전용 렌더링 (font_title, 큰 폰트 사이즈)."""
        return self.render_subtitle(
            text, role="hook", output_path=output_path,
        )

    def render_subtitle_with_glow(
        self,
        text: str,
        *,
        glow_color: str | None = None,
        glow_radius: int = 20,
        keywords: list[str] | None = None,
        role: str = "body",
        output_path: Path | None = None,
    ) -> Path:
        """네온 글로우 효과가 적용된 자막 이미지를 생성합니다.

        텍스트 주변에 발광 효과(blur glow)를 추가합니다.
        사양서의 cyan glow (shadowcolor=#00D4FF) 용도입니다.

        Args:
            text: 자막 텍스트.
            glow_color: 글로우 색상 (None이면 palette primary 사용).
            glow_radius: 글로우 블러 반경 (px).
            keywords: 하이라이트할 키워드 리스트.
            role: 씬 역할.
            output_path: 출력 경로.

        Returns:
            생성된 자막 이미지 경로.
        """
        if output_path is None:
            import tempfile
            output_path = Path(tempfile.mktemp(suffix=".png"))
        output_path.parent.mkdir(parents=True, exist_ok=True)

        gc = glow_color or self.palette.get("primary", "#00D4FF")
        gc_rgb = self._hex_to_rgb(gc)

        style = self._get_style(role)
        font_name = self.font_title if role in ("hook", "headline") else self.font_body
        scale = 2
        hi_size = style.font_size * scale
        hi_font = _resolve_font(font_name, hi_size)
        canvas_w = self._canvas_width * scale

        # 텍스트 줄바꿈
        probe_img = Image.new("RGBA", (canvas_w, 200), (0, 0, 0, 0))
        draw = ImageDraw.Draw(probe_img)
        max_text_w = canvas_w - (style.padding * 2 * scale)
        lines = self._wrap_lines(draw, text, hi_font, max_text_w, style.stroke_width * scale)
        line_text = "\n".join(lines)

        bbox = draw.multiline_textbbox(
            (0, 0), line_text, font=hi_font,
            spacing=style.line_spacing * scale,
            stroke_width=style.stroke_width * scale,
        )
        text_w = int(bbox[2] - bbox[0])
        text_h = int(bbox[3] - bbox[1])
        pad = glow_radius * scale
        img_w = min(canvas_w, text_w + style.padding * 4 * scale + pad * 2)
        img_h = text_h + style.padding * 2 * scale + pad * 2

        # 1) 글로우 레이어 — 동일 텍스트를 글로우 색상으로, 블러 적용
        glow_layer = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
        glow_draw = ImageDraw.Draw(glow_layer)
        tx = (img_w - text_w) / 2
        ty = pad + style.padding * scale - bbox[1]

        glow_draw.multiline_text(
            (tx, ty), line_text, font=hi_font,
            fill=(*gc_rgb, 200),
            spacing=style.line_spacing * scale,
            align="center",
        )
        glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(radius=glow_radius * scale))

        # 2) 메인 텍스트 레이어
        text_layer = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
        text_draw = ImageDraw.Draw(text_layer)
        text_draw.multiline_text(
            (tx, ty), line_text, font=hi_font,
            fill=style.text_color,
            stroke_width=style.stroke_width * scale,
            stroke_fill=style.stroke_color,
            spacing=style.line_spacing * scale,
            align="center",
        )

        # 3) 합성: 글로우 → 텍스트
        result = Image.alpha_composite(glow_layer, text_layer)

        # 다운샘플
        final_w = max(1, img_w // scale)
        final_h = max(1, img_h // scale)
        result = result.resize((final_w, final_h), Image.LANCZOS)
        result.save(output_path, format="PNG")
        logger.debug("[TextEngine] 글로우 자막 렌더: %s", output_path.name)
        return output_path

    def render_badge(
        self,
        number: int,
        *,
        badge_color: str = "#7C3AED",
        text_color: str = "#FFFFFF",
        size: int = 80,
        output_path: Path | None = None,
    ) -> Path:
        """원형 순번 배지 이미지를 생성합니다.

        카드 상단에 표시할 번호 배지 (사양서: 원형, #7C3AED 배경, 흰색 숫자).

        Args:
            number: 표시할 숫자.
            badge_color: 배지 배경색.
            text_color: 숫자 색상.
            size: 배지 직경 (px).
            output_path: 출력 경로.

        Returns:
            생성된 배지 이미지 경로.
        """
        if output_path is None:
            import tempfile
            output_path = Path(tempfile.mktemp(suffix=".png"))
        output_path.parent.mkdir(parents=True, exist_ok=True)

        scale = 2
        hi_size = size * scale
        image = Image.new("RGBA", (hi_size, hi_size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)

        bg_rgb = self._hex_to_rgb(badge_color)
        draw.ellipse(
            [0, 0, hi_size - 1, hi_size - 1],
            fill=(*bg_rgb, 255),
        )

        font = _resolve_font(self.font_title, int(hi_size * 0.5))
        num_str = str(number)
        bbox = draw.textbbox((0, 0), num_str, font=font)
        tx = (hi_size - (bbox[2] - bbox[0])) / 2 - bbox[0]
        ty = (hi_size - (bbox[3] - bbox[1])) / 2 - bbox[1]
        draw.text((tx, ty), num_str, font=font, fill=text_color)

        image = image.resize((size, size), Image.LANCZOS)
        image.save(output_path, format="PNG")
        logger.debug("[TextEngine] 배지 렌더: #%d (%dpx)", number, size)
        return output_path

    def render_watermark_number(
        self,
        number: int,
        *,
        font_size: int = 200,
        text_color: str = "#7C3AED",
        opacity: float = 0.5,
        canvas_w: int = 400,
        canvas_h: int = 300,
        output_path: Path | None = None,
    ) -> Path:
        """큰 워터마크 순번 이미지를 생성합니다.

        카운트다운 항목의 좌측 상단에 반투명으로 표시되는 큰 숫자입니다.

        Args:
            number: 표시할 숫자.
            font_size: 폰트 크기 (px).
            text_color: 텍스트 색상.
            opacity: 투명도 (0.0~1.0).
            canvas_w: 캔버스 너비.
            canvas_h: 캔버스 높이.
            output_path: 출력 경로.

        Returns:
            생성된 워터마크 이미지 경로.
        """
        if output_path is None:
            import tempfile
            output_path = Path(tempfile.mktemp(suffix=".png"))
        output_path.parent.mkdir(parents=True, exist_ok=True)

        scale = 2
        hi_w, hi_h = canvas_w * scale, canvas_h * scale
        hi_font_size = font_size * scale

        image = Image.new("RGBA", (hi_w, hi_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        font = _resolve_font(self.font_title, hi_font_size)

        num_str = str(number)
        rgb = self._hex_to_rgb(text_color)
        alpha = int(255 * opacity)

        bbox = draw.textbbox((0, 0), num_str, font=font)
        tx = hi_w * 0.1  # 좌측 여백
        ty = (hi_h - (bbox[3] - bbox[1])) / 2 - bbox[1]

        draw.text(
            (tx, ty), num_str, font=font,
            fill=(*rgb, alpha),
        )

        image = image.resize((canvas_w, canvas_h), Image.LANCZOS)
        image.save(output_path, format="PNG")
        logger.debug("[TextEngine] 워터마크 순번: #%d (%dpx, %.0f%% opacity)", number, font_size, opacity * 100)
        return output_path

    # ── 내부 메서드 ─────────────────────────────────────────────────────

    def _get_style(self, role: str) -> TextStyle:
        """역할에 따른 자막 스타일 반환."""
        palette = self.palette
        if role == "hook":
            return TextStyle(
                font_size=84,
                text_color=palette.get("accent", "#00FF88"),
                stroke_color="#000000",
                stroke_width=5,
                bg_opacity=200,
                bg_color=palette.get("bg", "#000000"),
            )
        elif role == "cta":
            return TextStyle(
                font_size=76,
                text_color="#FFD700",
                stroke_color="#000000",
                stroke_width=4,
                bg_opacity=180,
            )
        else:  # body
            return TextStyle(
                font_size=68,
                text_color=palette.get("primary", "#FFFFFF"),
                stroke_color="#000000",
                stroke_width=3,
                bg_opacity=185,
            )

    def _resolve_keyword_color(self, keyword: str) -> str | None:
        """keyword_highlights에서 해당 키워드의 색상을 찾습니다."""
        for _category, color in self.keyword_highlights.items():
            # 실제로는 카테고리 기반이므로, 키워드가 어떤 카테고리인지
            # 판단하는 로직 필요 — 여기서는 숫자/특수 패턴으로 구분
            if keyword.replace(",", "").replace(".", "").replace("%", "").strip().isdigit():
                if "numbers" in self.keyword_highlights:
                    return self.keyword_highlights["numbers"]
            # 기본: 첫 번째 하이라이트 색상 사용
            return color
        return None

    def _draw_highlighted_text(
        self,
        draw: ImageDraw.ImageDraw,
        lines: list[str],
        font: ImageFont.FreeTypeFont,
        start_x: float,
        start_y: float,
        style: TextStyle,
        scale: int,
        keywords: list[str],
        img_w: int,
    ) -> None:
        """키워드가 포함된 텍스트를 색상 하이라이트하여 그립니다."""
        y = start_y
        for line in lines:
            # 줄 전체 너비 계산
            line_bbox = draw.textbbox((0, 0), line, font=font, stroke_width=style.stroke_width * scale)
            line_w = line_bbox[2] - line_bbox[0]
            x = (img_w - line_w) / 2  # 중앙 정렬

            # 단어별로 나눠서 키워드 매칭
            remaining = line
            cursor_x = x
            while remaining:
                matched = False
                for kw in keywords:
                    if remaining.startswith(kw):
                        # 키워드 색상으로 그리기
                        kw_color = self._resolve_keyword_color(kw) or style.text_color
                        draw.text(
                            (cursor_x + scale, y + scale), kw, font=font,
                            fill=(0, 0, 0, 160),
                        )
                        draw.text(
                            (cursor_x, y), kw, font=font,
                            fill=kw_color,
                            stroke_width=style.stroke_width * scale,
                            stroke_fill=style.stroke_color,
                        )
                        kw_bbox = draw.textbbox((0, 0), kw, font=font, stroke_width=style.stroke_width * scale)
                        cursor_x += kw_bbox[2] - kw_bbox[0]
                        remaining = remaining[len(kw):]
                        matched = True
                        break

                if not matched:
                    # 일반 문자 그리기 (한 글자씩)
                    char = remaining[0]
                    draw.text(
                        (cursor_x + scale, y + scale), char, font=font,
                        fill=(0, 0, 0, 160),
                    )
                    draw.text(
                        (cursor_x, y), char, font=font,
                        fill=style.text_color,
                        stroke_width=style.stroke_width * scale,
                        stroke_fill=style.stroke_color,
                    )
                    char_bbox = draw.textbbox((0, 0), char, font=font, stroke_width=style.stroke_width * scale)
                    cursor_x += char_bbox[2] - char_bbox[0]
                    remaining = remaining[1:]

            # 다음 줄
            line_h = line_bbox[3] - line_bbox[1]
            y += line_h + style.line_spacing * scale

    @staticmethod
    def _wrap_lines(
        draw: ImageDraw.ImageDraw,
        text: str,
        font: ImageFont.FreeTypeFont,
        max_width: int,
        stroke_width: int,
    ) -> list[str]:
        """텍스트를 최대 너비에 맞게 줄바꿈합니다."""
        words = text.split()
        if not words:
            return [""]
        lines: list[str] = []
        current: list[str] = []
        for word in words:
            candidate = " ".join(current + [word])
            bbox = draw.textbbox((0, 0), candidate, font=font, stroke_width=stroke_width)
            w = bbox[2] - bbox[0]
            if w <= max_width or not current:
                current.append(word)
            else:
                lines.append(" ".join(current))
                current = [word]
        if current:
            lines.append(" ".join(current))
        return lines

    @staticmethod
    def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
        """#RRGGBB 형식을 (R, G, B) 튜플로 변환."""
        h = hex_color.lstrip("#")
        if len(h) != 6:
            return (0, 0, 0)
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
