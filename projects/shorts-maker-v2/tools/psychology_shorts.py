#!/usr/bin/env python3
"""심리학 실험 스토리텔링 쇼츠 생성기 (Psychology Experiment Shorts Generator)

입력: experiment_name, year, setup_text, result_text, insight_text, image_path
출력: 1080×1920, 30~45초 MP4

Phase 1 – 미스터리 훅 (0-3 s)  : 타자기 텍스트 + 밝기 램프
Phase 2 – 실험 배경 (3-10 s)   : 제목카드 + 이미지 + 설명카드
Phase 3 – 결과 반전 (10-25 s)  : "그런데..." + 붉은 플래시 + 결과카드
Phase 4 – 교훈     (25-35 s)   : 인사이트 인용 + 마무리 질문
"""

from __future__ import annotations

import argparse
import math
import os
import re
import warnings
from pathlib import Path

# Pillow deprecation warning 억제 (load_default size param)
warnings.filterwarnings("ignore", category=DeprecationWarning, module="PIL")

import numpy as np
from PIL import Image, ImageDraw, ImageFont

try:
    from moviepy import VideoClip
except ImportError:
    from moviepy.editor import VideoClip  # type: ignore[no-redef]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Generator
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class PsychologyShortsGenerator:
    """심리학 실험 기반 YouTube Shorts 생성기."""

    # ── 색상 팔레트 ──────────────────────────────────────────────────────────
    BG_PURPLE = (26, 10, 30)  # #1A0A1E
    BG_BLACK = (5, 2, 8)
    BG_RED = (45, 10, 10)  # #2D0A0A
    CARD_BG = (45, 27, 51, 204)  # #2D1B33  80 %
    WHITE = (255, 255, 255)
    LAVENDER = (232, 121, 249)  # #E879F9
    AMBER = (245, 158, 11)  # #F59E0B
    PINK = (251, 113, 133)  # #FB7185

    # ── 레이아웃 ─────────────────────────────────────────────────────────────
    W, H = 1080, 1920
    FPS = 30
    MARGIN = 60

    # ── 페이즈 타이밍 (초) ───────────────────────────────────────────────────
    P1_END = 3.0
    P2_END = 10.0
    P3_END = 25.0
    P4_END = 35.0

    # ── 감정 단어 사전 (키워드 하이라이트) ─────────────────────────────────────
    EMOTION_WORDS = {
        "두려움",
        "복종",
        "공포",
        "불안",
        "고통",
        "충격",
        "분노",
        "슬픔",
        "죄책감",
        "혼란",
        "절망",
        "압박",
        "위협",
        "무력감",
        "동조",
        "순종",
        "거부",
        "저항",
        "갈등",
        "트라우마",
        "스트레스",
        "우울",
        "공감",
        "연민",
        "권위",
        "순응",
        "양심",
        "전기충격",
        "비명",
        "항의",
    }

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  Init
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def __init__(
        self,
        experiment_name: str,
        year: int | str,
        setup_text: str,
        result_text: str,
        insight_text: str,
        image_path: str | None = None,
        hook_text: str = "이 실험의 결과를 아무도 예상 못했다",
        question_text: str = "당신은 어떻게 했을까요?",
    ):
        self.experiment_name = experiment_name
        self.year = str(year)
        self.setup_text = setup_text
        self.result_text = result_text
        self.insight_text = insight_text
        self.hook_text = hook_text
        self.question_text = question_text

        # 실험명 + 학자명 하이라이트용 추가 키워드
        self._highlight_names = {experiment_name}
        # 실험명에서 공백 분리된 단어 각각도 등록
        for w in experiment_name.split():
            self._highlight_names.add(w)

        # 이미지 로드
        self.experiment_image: Image.Image | None = None
        if image_path and Path(image_path).exists():
            self.experiment_image = Image.open(image_path).convert("RGBA")

        # 폰트
        self._load_fonts()

        # 사전 계산
        self._bg_gradient = self._make_gradient()
        self._bg_array = np.array(self._bg_gradient, dtype=np.float32)
        self._vignette = self._make_vignette()

        # 텍스트 래핑 캐시
        self._setup_lines = self._wrap(self.setup_text, self.font_body, self.W - self.MARGIN * 2 - 40)
        self._result_lines = self._wrap(self.result_text, self.font_body, self.W - self.MARGIN * 2 - 40)
        self._insight_lines = self._wrap(self.insight_text, self.font_quote, self.W - self.MARGIN * 2 - 80)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  Fonts
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _load_fonts(self) -> None:
        dirs = [
            Path("C:/Windows/Fonts"),
            Path(os.path.expanduser("~/AppData/Local/Microsoft/Windows/Fonts")),
        ]

        def _find(names: list[str], fallback: str = "malgun.ttf") -> str:
            for d in dirs:
                for n in names:
                    p = d / n
                    if p.exists():
                        return str(p)
            for d in dirs:
                p = d / fallback
                if p.exists():
                    return str(p)
            return ""

        serif = _find(["NanumMyeongjo.ttf", "batang.ttc"])
        _find(["NanumMyeongjoBold.ttf", "NanumMyeongjoExtraBold.ttf"])
        sans = _find(["NanumGothic.ttf", "malgun.ttf"])
        sans_b = _find(["NanumGothicBold.ttf", "NanumGothicExtraBold.ttf", "malgunbd.ttf"])

        def _load(path: str, size: int) -> ImageFont.FreeTypeFont:
            if path:
                return ImageFont.truetype(path, size)
            return ImageFont.load_default(size)

        self.font_hook = _load(sans_b, 76)  # Phase 1  훅
        self.font_title = _load(serif, 52)  # Phase 2  실험명
        self.font_body = _load(sans, 40)  # Phase 2,3 본문
        self.font_bold = _load(sans_b, 52)  # Phase 3  강조
        self.font_quote = _load(serif, 46)  # Phase 4  인용
        self.font_question = _load(sans_b, 54)  # Phase 4  질문
        self.font_turnaround = _load(sans_b, 80)  # Phase 3  "그런데..."
        self.font_small = _load(sans, 34)  # 부가 텍스트
        self.font_cursor = _load(sans, 76)  # 타자기 커서

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  Background / Vignette
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _make_gradient(self) -> Image.Image:
        """수직 그라데이션 (보라 → 검정)."""
        arr = np.zeros((self.H, self.W, 4), dtype=np.uint8)
        for y in range(self.H):
            r = y / self.H
            arr[y, :, 0] = int(self.BG_PURPLE[0] * (1 - r) + self.BG_BLACK[0] * r)
            arr[y, :, 1] = int(self.BG_PURPLE[1] * (1 - r) + self.BG_BLACK[1] * r)
            arr[y, :, 2] = int(self.BG_PURPLE[2] * (1 - r) + self.BG_BLACK[2] * r)
            arr[y, :, 3] = 255
        return Image.fromarray(arr, "RGBA")

    def _make_vignette(self) -> Image.Image:
        """방사형 비네팅 (모서리 어둡게) — numpy 벡터화."""
        ys = np.arange(self.H, dtype=np.float32)
        xs = np.arange(self.W, dtype=np.float32)
        yy, xx = np.meshgrid(ys, xs, indexing="ij")
        cx, cy = self.W / 2.0, self.H / 2.0
        dist = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / math.hypot(cx, cy)
        alpha = np.where(dist > 0.55, np.clip((dist - 0.55) / 0.45 * 180, 0, 255), 0).astype(np.uint8)
        arr = np.zeros((self.H, self.W, 4), dtype=np.uint8)
        arr[:, :, 3] = alpha
        return Image.fromarray(arr, "RGBA")

    def _get_bg(self, brightness: float = 0.5, red_mix: float = 0.0) -> Image.Image:
        """밝기 + 빨간 톤 혼합 배경 생성."""
        bg = self._bg_array.copy()
        bg[:, :, :3] *= brightness
        if red_mix > 0:
            # BG_RED 값은 0-255 단위이므로 brightness 곱해서 같은 스케일로 맞춤
            red_target = np.array(self.BG_RED, dtype=np.float32) * brightness
            red_arr = np.full_like(bg[:, :, :3], red_target, dtype=np.float32)
            bg[:, :, :3] = bg[:, :, :3] * (1 - red_mix) + red_arr * red_mix
        return Image.fromarray(np.clip(bg, 0, 255).astype(np.uint8), "RGBA")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  Text Utils
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    @staticmethod
    def _wrap(text: str, font: ImageFont.FreeTypeFont, max_w: int) -> list[str]:
        words = text.split()
        lines: list[str] = []
        cur = ""
        for w in words:
            test = f"{cur} {w}".strip()
            bbox = font.getbbox(test)
            if bbox[2] - bbox[0] <= max_w:
                cur = test
            else:
                if cur:
                    lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        return lines

    def _text_w(self, text: str, font: ImageFont.FreeTypeFont) -> int:
        bbox = font.getbbox(text)
        return bbox[2] - bbox[0]

    def _text_h(self, text: str, font: ImageFont.FreeTypeFont) -> int:
        bbox = font.getbbox(text)
        return bbox[3] - bbox[1]

    def _get_word_color(self, word: str) -> tuple[int, int, int]:
        """키워드 하이라이트 색상 결정."""
        clean = re.sub(r"[^가-힣a-zA-Z0-9]", "", word)
        # 감정 단어 → 핑크
        if clean in self.EMOTION_WORDS:
            return self.PINK
        # 숫자/통계 → 앰버
        if re.search(r"\d", word):
            return self.AMBER
        # 실험명/학자명 → 라벤더
        if clean in self._highlight_names:
            return self.LAVENDER
        return self.WHITE

    def _draw_highlighted_line(
        self,
        draw: ImageDraw.ImageDraw,
        line: str,
        y: int,
        font: ImageFont.FreeTypeFont,
        default_color: tuple = (255, 255, 255, 255),
        center: bool = True,
        alpha: int = 255,
    ) -> None:
        """키워드 하이라이트가 적용된 한 줄 렌더링."""
        words = line.split()
        # 전체 너비 계산 (센터링용)
        total_w = self._text_w(line, font)
        x = (self.W - total_w) // 2 if center else self.MARGIN + 20

        for i, word in enumerate(words):
            seg = word + (" " if i < len(words) - 1 else "")
            color = self._get_word_color(word)
            fill = (*color, alpha)
            draw.text((x, y), seg, font=font, fill=fill)
            x += self._text_w(seg, font)

    def _draw_card(
        self,
        draw: ImageDraw.ImageDraw,
        x: int,
        y: int,
        w: int,
        h: int,
        color: tuple = (45, 27, 51, 204),
        radius: int = 20,
    ) -> None:
        """반투명 둥근 사각형 카드."""
        draw.rounded_rectangle([(x, y), (x + w, y + h)], radius=radius, fill=color)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  Easing
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    @staticmethod
    def _ease_out(t: float) -> float:
        return 1 - (1 - min(1, max(0, t))) ** 3

    @staticmethod
    def _ease_in_out(t: float) -> float:
        t = min(1, max(0, t))
        return 3 * t * t - 2 * t * t * t

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  Phase Renderers
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _draw_phase1(self, draw: ImageDraw.ImageDraw, t: float) -> None:
        """Phase 1 – 미스터리 훅 (0‒3 s): 타자기 + 밝기 램프."""
        # 타자기 효과: 0.05초 간격
        chars_vis = min(len(self.hook_text), int(t / 0.05))
        visible = self.hook_text[:chars_vis]

        # 커서 깜빡임 (0.25s 주기)
        cursor = "▌" if (t * 4) % 1 < 0.5 and chars_vis < len(self.hook_text) else ""
        display = visible + cursor

        # 줄 바꿈 처리 (화면 너비 초과 시)
        lines = self._wrap(display, self.font_hook, self.W - self.MARGIN * 2)
        line_h = self._text_h("가", self.font_hook) + 12
        total_h = line_h * len(lines)
        start_y = (self.H - total_h) // 2

        for i, line in enumerate(lines):
            lw = self._text_w(line, self.font_hook)
            x = (self.W - lw) // 2
            draw.text((x, start_y + i * line_h), line, font=self.font_hook, fill=(255, 255, 255, 255))

    def _draw_phase2(self, draw: ImageDraw.ImageDraw, overlay: Image.Image, t: float) -> None:
        """Phase 2 – 실험 배경 (3‒10 s): 제목 + 이미지 + 설명 카드."""
        # ── 상단: 실험명 + 연도 ──
        title_text = f"{self.experiment_name}, {self.year}"
        title_alpha = int(255 * self._ease_out(t / 0.8))
        tw = self._text_w(title_text, self.font_title)
        tx = (self.W - tw) // 2
        draw.text((tx, 160), title_text, font=self.font_title, fill=(*self.LAVENDER, title_alpha))

        # 구분선
        line_alpha = int(180 * self._ease_out(t / 1.0))
        line_y = 230
        draw.line(
            [(self.W // 2 - 120, line_y), (self.W // 2 + 120, line_y)],
            fill=(*self.LAVENDER, line_alpha),
            width=2,
        )

        # ── 중앙: 이미지 ──
        if self.experiment_image is not None:
            img_appear = self._ease_out((t - 0.3) / 1.0)
            if img_appear > 0:
                target_w = int(self.W * 0.70)
                ratio = target_w / self.experiment_image.width
                target_h = int(self.experiment_image.height * ratio)
                target_h = min(target_h, 700)  # 최대 높이 제한

                resized = self.experiment_image.resize((target_w, target_h), Image.LANCZOS)
                # 반투명 적용
                alpha_channel = resized.split()[3]
                alpha_channel = alpha_channel.point(lambda p: int(p * img_appear))
                resized.putalpha(alpha_channel)

                ix = (self.W - target_w) // 2
                iy = 280
                overlay.paste(resized, (ix, iy), resized)

        # ── 하단: 설명 카드 ──
        card_y_start = 1050
        line_h = self._text_h("가", self.font_body) + 16
        card_h = line_h * len(self._setup_lines) + 50
        card_x = self.MARGIN
        card_w = self.W - self.MARGIN * 2

        # 카드 페이드인
        card_alpha = int(204 * self._ease_out((t - 0.5) / 0.6))
        if card_alpha > 0:
            self._draw_card(draw, card_x, card_y_start, card_w, card_h, color=(45, 27, 51, card_alpha), radius=16)

        # 줄 단위 순차 페이드인 (0.3초 간격)
        for i, line in enumerate(self._setup_lines):
            line_delay = 0.8 + i * 0.3
            line_alpha = int(255 * self._ease_out((t - line_delay) / 0.5))
            if line_alpha > 0:
                ly = card_y_start + 25 + i * line_h
                self._draw_highlighted_line(draw, line, ly, self.font_body, alpha=line_alpha)

    def _draw_phase3(self, draw: ImageDraw.ImageDraw, t: float) -> None:
        """Phase 3 – 결과 반전 (10‒25 s): 전환 + 결과 카드."""
        # ── "그런데..." 팝업 (0‒0.5 s) ──
        if t < 1.5:
            popup_scale = self._ease_out(min(1, t / 0.25))
            popup_alpha = 255 if t < 1.0 else int(255 * (1 - (t - 1.0) / 0.5))
            popup_alpha = max(0, popup_alpha)
            text = "그런데..."
            tw = self._text_w(text, self.font_turnaround)
            tx = (self.W - tw) // 2
            ty = self.H // 2 - 50
            # 스케일 효과 시뮬레이션 (텍스트 크기 조절은 비용이 크므로 alpha로 표현)
            draw.text((tx, ty), text, font=self.font_turnaround, fill=(255, 255, 255, int(popup_alpha * popup_scale)))

        # ── 결과 설명 카드 ──
        if t >= 1.2:
            card_t = t - 1.2
            card_x = self.MARGIN
            card_w = self.W - self.MARGIN * 2
            line_h = self._text_h("가", self.font_body) + 16

            # 결과 텍스트를 카드 2~3개로 분할
            cards = self._split_into_cards(self._result_lines, max_lines=3)

            y_cursor = 350
            for ci, card_lines in enumerate(cards):
                card_delay = ci * 1.5
                card_alpha_f = self._ease_out((card_t - card_delay) / 0.6)
                if card_alpha_f <= 0:
                    y_cursor += line_h * len(card_lines) + 90
                    continue

                card_alpha = int(204 * card_alpha_f)
                card_h = line_h * len(card_lines) + 50

                self._draw_card(draw, card_x, y_cursor, card_w, card_h, color=(45, 27, 51, card_alpha), radius=16)

                for li, line in enumerate(card_lines):
                    la = int(255 * self._ease_out((card_t - card_delay - 0.2 - li * 0.15) / 0.4))
                    if la > 0:
                        ly = y_cursor + 25 + li * line_h
                        self._draw_highlighted_line(draw, line, ly, self.font_body, alpha=la)

                y_cursor += card_h + 40

    def _draw_phase4(self, draw: ImageDraw.ImageDraw, t: float) -> None:
        """Phase 4 – 교훈/인사이트 (25‒35 s): 인용 + 질문."""
        line_h = self._text_h("가", self.font_quote) + 18

        # ── 큰 따옴표 ──
        quote_alpha = int(120 * self._ease_out(t / 0.6))
        # 열기 따옴표
        draw.text((self.MARGIN + 10, 450), "\u201c", font=self.font_turnaround, fill=(*self.LAVENDER, quote_alpha))

        # ── 인사이트 텍스트 (줄 단위 페이드인) ──
        for i, line in enumerate(self._insight_lines):
            delay = 0.3 + i * 0.3
            la = int(255 * self._ease_out((t - delay) / 0.5))
            if la > 0:
                ly = 560 + i * line_h
                self._draw_highlighted_line(draw, line, ly, self.font_quote, alpha=la)

        # 닫기 따옴표
        last_y = 560 + len(self._insight_lines) * line_h
        close_alpha = int(120 * self._ease_out((t - 0.3 - len(self._insight_lines) * 0.3) / 0.4))
        if close_alpha > 0:
            cw = self._text_w("\u201d", self.font_turnaround)
            draw.text(
                (self.W - self.MARGIN - cw - 10, last_y - 20),
                "\u201d",
                font=self.font_turnaround,
                fill=(*self.LAVENDER, max(0, close_alpha)),
            )

        # ── 구분선 ──
        sep_y = last_y + 60
        sep_alpha = int(100 * self._ease_out((t - 2.0) / 0.5))
        if sep_alpha > 0:
            draw.line(
                [(self.W // 2 - 80, sep_y), (self.W // 2 + 80, sep_y)],
                fill=(255, 255, 255, sep_alpha),
                width=2,
            )

        # ── 마무리 질문 ──
        q_delay = 2.5
        q_alpha = int(255 * self._ease_out((t - q_delay) / 0.6))
        if q_alpha > 0:
            qw = self._text_w(self.question_text, self.font_question)
            (self.W - qw) // 2
            qy = sep_y + 60

            # 글자별 순차 등장
            chars_vis = min(len(self.question_text), int((t - q_delay) / 0.04))
            visible_q = self.question_text[:chars_vis]
            self._text_w(visible_q, self.font_question)
            vx = (self.W - qw) // 2  # 최종 위치 기준 정렬 유지
            draw.text((vx, qy), visible_q, font=self.font_question, fill=(*self.LAVENDER, q_alpha))

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  Card Splitting Helper
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    @staticmethod
    def _split_into_cards(lines: list[str], max_lines: int = 3) -> list[list[str]]:
        """줄 목록을 max_lines씩 카드로 분할."""
        cards: list[list[str]] = []
        for i in range(0, len(lines), max_lines):
            cards.append(lines[i : i + max_lines])
        return cards if cards else [lines]

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  Frame Composition
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _render_frame(self, t: float) -> np.ndarray:
        """시간 t에 대한 프레임 생성 → numpy (H, W, 3)."""
        # ── 배경 ──
        if t < self.P1_END:
            brightness = min(0.5, 0.1 + 0.4 * min(t, 2.0) / 2.0)
            bg = self._get_bg(brightness)
        elif t < self.P2_END:
            bg = self._get_bg(0.5)
        elif t < self.P3_END:
            local = t - self.P2_END
            if local < 0.5:
                bg = self._get_bg(0.5)
            elif local < 0.8:
                red = (local - 0.5) / 0.3
                bg = self._get_bg(0.5, red_mix=red * 0.7)
            elif local < 2.0:
                bg = self._get_bg(0.5, red_mix=0.7)
            else:
                red = max(0, 0.7 * (1 - (local - 2.0) / 3.0))
                bg = self._get_bg(0.5, red_mix=red)
        else:
            bg = self._get_bg(0.6)

        # ── 오버레이 ──
        overlay = Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        if t < self.P1_END:
            self._draw_phase1(draw, t)
        elif t < self.P2_END:
            self._draw_phase2(draw, overlay, t - self.P1_END)
        elif t < self.P3_END:
            self._draw_phase3(draw, t - self.P2_END)
        else:
            self._draw_phase4(draw, t - self.P3_END)

        # ── 합성 ──
        frame = Image.alpha_composite(bg, overlay)
        # phase 4에서만 비네팅 강조
        if t >= self.P3_END:
            frame = Image.alpha_composite(frame, self._vignette)

        return np.array(frame.convert("RGB"))

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  Generate
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def generate(self, output_path: str = "psychology_shorts.mp4") -> str:
        """MP4 영상 생성."""
        duration = self.P4_END

        def make_frame(t: float) -> np.ndarray:
            return self._render_frame(t)

        clip = VideoClip(make_frame, duration=duration).with_fps(self.FPS)

        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        clip.write_videofile(
            str(out),
            codec="libx264",
            preset="medium",
            bitrate="8000k",
            audio=False,
            logger="bar",
        )
        print(f"\n✅ 생성 완료: {out.resolve()}")
        print(f"   크기: {self.W}×{self.H} | 길이: {duration:.0f}초 | FPS: {self.FPS}")
        return str(out.resolve())


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Built-in Demo: Milgram Experiment
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DEMO_DATA = {
    "experiment_name": "밀그램 복종 실험",
    "year": 1961,
    "hook_text": "이 실험의 결과를 아무도 예상 못했다",
    "setup_text": (
        "예일대의 스탠리 밀그램 교수는 평범한 시민 40명을 모집했다. "
        "참가자들은 '학습 실험'이라는 설명을 듣고, 학습자가 틀릴 때마다 "
        "전기충격 버튼을 누르라는 지시를 받았다. "
        "전압은 15V에서 450V까지 올라갔고, 학습자는 사실 연기자였다."
    ),
    "result_text": (
        "놀랍게도 참가자의 65%가 최대 450V까지 전기충격을 가했다. "
        "학습자가 비명을 지르고 항의해도, 실험자가 '계속하세요'라고 "
        "말하면 대부분이 복종했다. 사전 설문에서 전문가들은 "
        "1% 미만만 끝까지 갈 것이라 예측했지만, 현실은 달랐다."
    ),
    "insight_text": (
        "권위 앞에서 우리의 양심은 생각보다 쉽게 무너진다. "
        "밀그램은 이것이 개인의 성격이 아니라, "
        "상황의 힘이라고 결론지었다. "
        "우리 모두 그 버튼을 누를 수 있다."
    ),
    "question_text": "당신은 그 버튼을 눌렀을까요?",
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  CLI
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def main() -> int:
    parser = argparse.ArgumentParser(description="심리학 실험 스토리텔링 쇼츠 생성기")
    parser.add_argument("--demo", action="store_true", help="밀그램 실험 데모 영상 생성")
    parser.add_argument("--name", type=str, default="", help="실험명")
    parser.add_argument("--year", type=str, default="", help="실험 연도")
    parser.add_argument("--setup", type=str, default="", help="실험 배경 텍스트")
    parser.add_argument("--result", type=str, default="", help="결과 텍스트")
    parser.add_argument("--insight", type=str, default="", help="교훈 텍스트")
    parser.add_argument("--hook", type=str, default="이 실험의 결과를 아무도 예상 못했다", help="훅 텍스트")
    parser.add_argument("--question", type=str, default="당신은 어떻게 했을까요?", help="마무리 질문")
    parser.add_argument("--image", type=str, default="", help="이미지 경로")
    parser.add_argument("--out", type=str, default="psychology_shorts.mp4", help="출력 파일 경로")
    args = parser.parse_args()

    if args.demo:
        print("🧪 밀그램 복종 실험 데모 생성 중...")
        gen = PsychologyShortsGenerator(**DEMO_DATA)
        gen.generate(args.out)
        return 0

    if not all([args.name, args.setup, args.result, args.insight]):
        print("[FAIL] --name, --setup, --result, --insight 는 필수입니다. --demo로 데모를 먼저 시도해보세요.")
        return 1

    gen = PsychologyShortsGenerator(
        experiment_name=args.name,
        year=args.year or "N/A",
        setup_text=args.setup,
        result_text=args.result,
        insight_text=args.insight,
        image_path=args.image or None,
        hook_text=args.hook,
        question_text=args.question,
    )
    gen.generate(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
