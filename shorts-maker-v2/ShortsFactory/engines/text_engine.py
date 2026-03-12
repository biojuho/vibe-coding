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

import numpy as np  # [QA 수정] gradient vectorization에 필요

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

    # ── v2 신규 메서드 ────────────────────────────────────────────────────

    def render_gradient_text(
        self,
        text: str,
        *,
        color_start: str | None = None,
        color_end: str | None = None,
        role: str = "hook",
        output_path: Path | None = None,
    ) -> Path:
        """두 색상 사이의 세로 그라데이션이 적용된 텍스트 이미지를 생성합니다.

        Hook 씬이나 CTA에서 시각적 임팩트를 위해 사용합니다.

        Args:
            text: 렌더링할 텍스트.
            color_start: 그라데이션 시작 색상 (상단, None → palette accent).
            color_end: 그라데이션 종료 색상 (하단, None → palette primary).
            role: 씬 역할.
            output_path: 출력 경로.

        Returns:
            생성된 이미지 경로.
        """
        if output_path is None:
            import tempfile
            output_path = Path(tempfile.mktemp(suffix=".png"))
        output_path.parent.mkdir(parents=True, exist_ok=True)

        cs = self._hex_to_rgb(color_start or self.palette.get("accent", "#00FF88"))
        ce = self._hex_to_rgb(color_end or self.palette.get("primary", "#00D4FF"))

        style = self._get_style(role)
        font_name = self.font_title if role in ("hook", "headline") else self.font_body
        scale = 2
        hi_font = _resolve_font(font_name, style.font_size * scale)
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
        img_w = min(canvas_w, text_w + style.padding * 4 * scale)
        img_h = text_h + style.padding * 2 * scale

        # 1) 텍스트를 흰색으로 먼저 렌더
        text_layer = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
        text_draw = ImageDraw.Draw(text_layer)
        tx = (img_w - text_w) / 2
        ty = style.padding * scale - bbox[1]

        # 드롭 섀도우
        text_draw.multiline_text(
            (tx + scale, ty + scale), line_text, font=hi_font,
            fill=(0, 0, 0, 160), spacing=style.line_spacing * scale,
            align="center",
        )
        text_draw.multiline_text(
            (tx, ty), line_text, font=hi_font,
            fill=(255, 255, 255, 255),
            stroke_width=style.stroke_width * scale,
            stroke_fill=style.stroke_color,
            spacing=style.line_spacing * scale,
            align="center",
        )

        # 2) 세로 그라데이션 레이어 생성 (numpy 벡터화) # [QA 수정] putpixel→numpy
        ratios = np.linspace(0, 1, img_h).reshape(-1, 1)  # (H, 1)
        cs_arr = np.array(cs, dtype=np.float32)  # (3,)
        ce_arr = np.array(ce, dtype=np.float32)  # (3,)
        grad_row = (cs_arr * (1 - ratios) + ce_arr * ratios).astype(np.uint8)  # (H, 3)
        grad_arr = np.tile(grad_row[:, np.newaxis, :], (1, img_w, 1))  # (H, W, 3)
        alpha_ch = np.full((img_h, img_w, 1), 255, dtype=np.uint8)
        grad_rgba = np.concatenate([grad_arr, alpha_ch], axis=-1)  # (H, W, 4)
        gradient = Image.fromarray(grad_rgba, "RGBA")

        # 3) 텍스트 알파로 그라데이션 마스킹
        # 텍스트의 알파 채널을 그라데이션에 적용
        _, _, _, text_alpha = text_layer.split()
        gradient.putalpha(text_alpha)

        # 4) 스트로크 레이어 (검정 아웃라인)
        stroke_layer = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
        stroke_draw = ImageDraw.Draw(stroke_layer)
        stroke_draw.multiline_text(
            (tx, ty), line_text, font=hi_font,
            fill=(0, 0, 0, 0),
            stroke_width=style.stroke_width * scale,
            stroke_fill=(0, 0, 0, 220),
            spacing=style.line_spacing * scale,
            align="center",
        )

        # 합성: 스트로크 위에 그라데이션 텍스트
        result = Image.alpha_composite(stroke_layer, gradient)

        # 다운샘플
        final_w = max(1, img_w // scale)
        final_h = max(1, img_h // scale)
        result = result.resize((final_w, final_h), Image.LANCZOS)
        result.save(output_path, format="PNG")
        logger.debug("[TextEngine] 그라데이션 텍스트: %s", output_path.name)
        return output_path

    def render_emoji_badge(
        self,
        emoji: str,
        label: str = "",
        *,
        size: int = 120,
        badge_color: str | None = None,
        output_path: Path | None = None,
    ) -> Path:
        """이모지 + 라벨 배지 이미지를 생성합니다.

        Hook 씬 상단에 표시되는 시각적 아이콘 배지입니다.

        Args:
            emoji: 이모지 문자열 (e.g. "🔥").
            label: 배지 하단 라벨 (e.g. "HOT").
            size: 배지 크기 (px).
            badge_color: 배지 배경색 (None → palette accent).
            output_path: 출력 경로.

        Returns:
            생성된 배지 이미지 경로.
        """
        if output_path is None:
            import tempfile
            output_path = Path(tempfile.mktemp(suffix=".png"))
        output_path.parent.mkdir(parents=True, exist_ok=True)

        bc = self._hex_to_rgb(badge_color or self.palette.get("accent", "#FF4444"))
        scale = 2
        hi_size = size * scale
        pad = 20 * scale if label else 0

        total_h = hi_size + pad
        image = Image.new("RGBA", (hi_size, total_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)

        # 원형 배경
        draw.ellipse(
            [0, 0, hi_size - 1, hi_size - 1],
            fill=(*bc, 220),
        )

        # 이모지 텍스트 (Segoe UI Emoji 또는 fallback)
        emoji_font = _resolve_font("Segoe UI Emoji", int(hi_size * 0.45))
        e_bbox = draw.textbbox((0, 0), emoji, font=emoji_font)
        e_x = (hi_size - (e_bbox[2] - e_bbox[0])) / 2 - e_bbox[0]
        e_y = (hi_size - (e_bbox[3] - e_bbox[1])) / 2 - e_bbox[1]
        draw.text((e_x, e_y), emoji, font=emoji_font, fill=(255, 255, 255, 255))

        # 라벨
        if label and pad > 0:
            label_font = _resolve_font(self.font_title, int(14 * scale))
            l_bbox = draw.textbbox((0, 0), label, font=label_font)
            l_x = (hi_size - (l_bbox[2] - l_bbox[0])) / 2 - l_bbox[0]
            draw.text((l_x, hi_size + 2), label, font=label_font, fill=(255, 255, 255, 200))

        # 다운샘플
        final_w = max(1, hi_size // scale)
        final_h = max(1, total_h // scale)
        image = image.resize((final_w, final_h), Image.LANCZOS)
        image.save(output_path, format="PNG")
        logger.debug("[TextEngine] 이모지 배지: %s %s", emoji, label)
        return output_path

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
        """진행률 바 이미지를 생성합니다.

        카운트다운이나 퀴즈 타이머에서 사용.

        Args:
            progress: 진행률 (0.0~1.0).
            width: 바 너비 (px).
            height: 바 높이 (px).
            bar_color: 진행률 바 색상 (None → palette accent).
            bg_color: 배경 바 색상.
            label: 바 우측 라벨 (e.g. "3/5").
            output_path: 출력 경로.

        Returns:
            생성된 프로그레스 바 이미지 경로.
        """
        if output_path is None:
            import tempfile
            output_path = Path(tempfile.mktemp(suffix=".png"))
        output_path.parent.mkdir(parents=True, exist_ok=True)

        bc = self._hex_to_rgb(bar_color or self.palette.get("accent", "#00FF88"))
        bgc = self._hex_to_rgb(bg_color)

        scale = 2
        total_w = width * scale
        total_h = (height + 30 if label else height) * scale
        bar_h = height * scale
        radius = bar_h // 2

        image = Image.new("RGBA", (total_w, total_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)

        # 배경 바
        draw.rounded_rectangle(
            [(0, 0), (total_w, bar_h)],
            radius=radius,
            fill=(*bgc, 180),
        )

        # 진행 바
        fill_w = max(bar_h, int(total_w * min(1.0, max(0.0, progress))))
        draw.rounded_rectangle(
            [(0, 0), (fill_w, bar_h)],
            radius=radius,
            fill=(*bc, 220),
        )

        # 라벨
        if label:
            label_font = _resolve_font(self.font_body, int(12 * scale))
            draw.text(
                (total_w - 10 * scale, bar_h + 5 * scale),
                label, font=label_font,
                fill=(200, 200, 200, 200),
                anchor="rt",
            )

        # 다운샘플
        final_w = max(1, total_w // scale)
        final_h = max(1, total_h // scale)
        image = image.resize((final_w, final_h), Image.LANCZOS)
        image.save(output_path, format="PNG")
        logger.debug("[TextEngine] 프로그레스 바: %.0f%%", progress * 100)
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
