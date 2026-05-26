"""
text_engine.py — 자막/타이포그래피 엔진 v2
==========================================
채널별 palette + keyword_highlights를 기반으로
자막 이미지를 생성합니다.

v2 개선사항:
- render_gradient_text(): 두 색상 그라데이션 텍스트
- render_emoji_badge(): 이모지+라벨 배지 (Hook 씬용)
- render_progress_bar(): 카운트다운 진행률 표시
- 'headline' 역할 스타일 추가
- 개선된 자간/줄간 계산

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

from PIL import Image, ImageDraw, ImageFont

from ShortsFactory.engines.layout_utils import draw_highlighted_text, hex_to_rgb, wrap_lines

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
        candidates = [str(p)] if p.exists() else ["C:/Windows/Fonts/malgunbd.ttf", "C:/Windows/Fonts/malgun.ttf"]
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
        self.highlight_color = channel_config.get(
            "highlight_color",
            self.palette.get("accent", "#FFD700"),
        )
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
        """텍스트와 키워드 하이라이트를 적용한 자막 이미지를 생성합니다."""
        from ShortsFactory.engines.render_strategies.subtitle import render_subtitle

        return render_subtitle(self, text, keywords=keywords, role=role, output_path=output_path)

    def render_title(self, text: str, *, output_path: Path | None = None) -> Path:
        """타이틀 전용 렌더링 (font_title, 큰 폰트 사이즈)."""
        from ShortsFactory.engines.render_strategies.utility import render_title

        return render_title(self, text, output_path=output_path)

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
        """네온 글로우 효과가 적용된 자막 이미지를 생성합니다."""
        from ShortsFactory.engines.render_strategies.subtitle import render_subtitle_with_glow

        return render_subtitle_with_glow(
            self,
            text,
            glow_color=glow_color,
            glow_radius=glow_radius,
            keywords=keywords,
            role=role,
            output_path=output_path,
        )

    def render_badge(
        self,
        number: int,
        *,
        badge_color: str = "#7C3AED",
        text_color: str = "#FFFFFF",
        size: int = 80,
        output_path: Path | None = None,
    ) -> Path:
        """원형 순번 배지 이미지를 생성합니다."""
        from ShortsFactory.engines.render_strategies.badge import render_badge

        return render_badge(
            self, number, badge_color=badge_color, text_color=text_color, size=size, output_path=output_path
        )

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
        """큰 워터마크 순번 이미지를 생성합니다."""
        from ShortsFactory.engines.render_strategies.utility import render_watermark_number

        return render_watermark_number(
            self,
            number,
            font_size=font_size,
            text_color=text_color,
            opacity=opacity,
            canvas_w=canvas_w,
            canvas_h=canvas_h,
            output_path=output_path,
        )

    def render_gradient_text(
        self,
        text: str,
        *,
        color_start: str | None = None,
        color_end: str | None = None,
        role: str = "hook",
        output_path: Path | None = None,
    ) -> Path:
        """두 색상 사이의 세로 그라데이션이 적용된 텍스트 이미지를 생성합니다."""
        from ShortsFactory.engines.render_strategies.gradient import render_gradient_text

        return render_gradient_text(
            self,
            text,
            color_start=color_start,
            color_end=color_end,
            role=role,
            output_path=output_path,
        )

    def render_emoji_badge(
        self,
        emoji: str,
        label: str = "",
        *,
        size: int = 120,
        badge_color: str | None = None,
        output_path: Path | None = None,
    ) -> Path:
        """이모지 + 라벨 배지 이미지를 생성합니다."""
        from ShortsFactory.engines.render_strategies.badge import render_emoji_badge

        return render_emoji_badge(
            self,
            emoji,
            label=label,
            size=size,
            badge_color=badge_color,
            output_path=output_path,
        )

    def render_progress_bar(
        self,
        progress: float,
        *,
        width: int = 800,
        height: int = 24,
        bar_color: str | None = None,
        bg_color: str = "#1A1A2E",
        label: str = "",
        output_path: Path | None = None,
    ) -> Path:
        """진행률 바 이미지를 생성합니다."""
        from ShortsFactory.engines.render_strategies.utility import render_progress_bar

        return render_progress_bar(
            self,
            progress,
            width=width,
            height=height,
            bar_color=bar_color,
            bg_color=bg_color,
            label=label,
            output_path=output_path,
        )

    # ── 내부 메서드 ─────────────────────────────────────────────────────

    def _prepare_text_layout(
        self,
        text: str,
        role: str,
        scale: int = 2,
        extra_pad: int = 0,
    ) -> dict[str, Any]:
        """폰트 분석, 줄바꿈 및 바운딩 박스를 계산하여 공통 레이아웃 파라미터를 생성합니다."""
        style = self._get_style(role)
        font_name = self.font_title if role in ("hook", "headline") else self.font_body

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
            (0, 0),
            line_text,
            font=hi_font,
            spacing=style.line_spacing * scale,
            stroke_width=style.stroke_width * scale,
        )
        text_w = int(bbox[2] - bbox[0])
        text_h = int(bbox[3] - bbox[1])

        img_w = min(canvas_w, text_w + style.padding * 4 * scale + extra_pad * 2)
        img_h = text_h + style.padding * 2 * scale + extra_pad * 2

        tx = (img_w - text_w) / 2
        ty = extra_pad + style.padding * scale - bbox[1]

        return {
            "style": style,
            "hi_font": hi_font,
            "scale": scale,
            "lines": lines,
            "line_text": line_text,
            "text_w": text_w,
            "text_h": text_h,
            "img_w": img_w,
            "img_h": img_h,
            "tx": tx,
            "ty": ty,
        }

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
        elif role == "headline":
            return TextStyle(
                font_size=96,
                text_color=palette.get("primary", "#FFFFFF"),
                stroke_color="#000000",
                stroke_width=6,
                bg_opacity=0,
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
        if isinstance(self.keyword_highlights, (list, tuple, set)):
            return self.highlight_color if keyword else None
        for _category, color in self.keyword_highlights.items():
            # 실제로는 카테고리 기반이므로, 키워드가 어떤 카테고리인지
            # 판단하는 로직 필요 — 여기서는 숫자/특수 패턴으로 구분
            if (
                keyword.replace(",", "").replace(".", "").replace("%", "").strip().isdigit()
                and "numbers" in self.keyword_highlights
            ):
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
        draw_highlighted_text(
            draw=draw,
            lines=lines,
            font=font,
            start_x=start_x,
            start_y=start_y,
            style=style,
            scale=scale,
            keywords=keywords,
            img_w=img_w,
            resolve_keyword_color_fn=self._resolve_keyword_color,
        )

    @staticmethod
    def _wrap_lines(
        draw: ImageDraw.ImageDraw,
        text: str,
        font: ImageFont.FreeTypeFont,
        max_width: int,
        stroke_width: int,
    ) -> list[str]:
        """텍스트를 최대 너비에 맞게 줄바꿈합니다."""
        return wrap_lines(draw, text, font, max_width, stroke_width)

    @staticmethod
    def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
        """#RRGGBB 형식을 (R, G, B) 튜플로 변환."""
        return hex_to_rgb(hex_color)
