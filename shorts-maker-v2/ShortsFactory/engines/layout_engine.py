"""
layout_engine.py — 분할/카드 레이아웃 엔진
"""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)


def _load_font(name: str, size: int):
    _C = {
        "Pretendard-ExtraBold": "C:/Windows/Fonts/malgunbd.ttf",
        "Pretendard-Bold": "C:/Windows/Fonts/malgunbd.ttf",
        "Pretendard-Regular": "C:/Windows/Fonts/malgun.ttf",
        "NanumMyeongjo-Bold": "C:/Windows/Fonts/malgunbd.ttf",
    }
    path = _C.get(name, "C:/Windows/Fonts/malgun.ttf")
    try:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    except Exception as exc:
        logging.getLogger(__name__).warning("폰트 로드 실패 (%s): %s", name, exc)
    return ImageFont.load_default()


class LayoutEngine:
    def __init__(self, channel_config: dict[str, Any]) -> None:
        self.config = channel_config
        self.palette = channel_config.get("palette", {})
        self.font_title = channel_config.get("font_title", "Pretendard-Bold")
        self.font_body = channel_config.get("font_body", "Pretendard-Regular")
        self._width, self._height = 1080, 1920

    def split_screen(
        self,
        left_text: str,
        right_text: str,
        *,
        left_label: str = "DO ✅",
        right_label: str = "DON'T ❌",
        left_color: str | None = None,
        right_color: str | None = None,
        output_path: Path | None = None,
    ) -> Path:
        if output_path is None:
            _fd, _tmp = tempfile.mkstemp(suffix=".png")
            os.close(_fd)
            output_path = Path(_tmp)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        bg = self._hex(self.palette.get("bg", "#0A0E1A"))
        pos = self._hex(left_color or self.palette.get("accent", "#34D399"))
        neg = self._hex(right_color or "#EF4444")
        img = Image.new("RGB", (self._width, self._height), bg)
        d = ImageDraw.Draw(img)
        hw = self._width // 2
        d.line([(hw, 100), (hw, self._height - 100)], fill=(100, 100, 100), width=3)
        lf = _load_font(self.font_title, 48)
        bf = _load_font(self.font_body, 36)
        d.text((hw // 2, 200), left_label, font=lf, fill=pos, anchor="mm")
        d.text((hw + hw // 2, 200), right_label, font=lf, fill=neg, anchor="mm")
        self._wrap(d, left_text, bf, 40, 320, hw - 80, (255, 255, 255))
        self._wrap(d, right_text, bf, hw + 40, 320, hw - 80, (255, 255, 255))
        img.save(output_path, format="PNG")
        return output_path

    def card_layout(self, items: list[dict[str, str]], *, output_path: Path | None = None) -> Path:
        if output_path is None:
            _fd, _tmp = tempfile.mkstemp(suffix=".png")
            os.close(_fd)
            output_path = Path(_tmp)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        bg = self._hex(self.palette.get("bg", "#0A0E1A"))
        pri = self._hex(self.palette.get("primary", "#00D4FF"))
        acc = self._hex(self.palette.get("accent", "#00FF88"))
        img = Image.new("RGB", (self._width, self._height), bg)
        d = ImageDraw.Draw(img)
        tf = _load_font(self.font_title, 42)
        bf = _load_font(self.font_body, 32)
        ch, m, ys = 220, 40, 200
        for i, item in enumerate(items):
            y = ys + i * (ch + m)
            if y + ch > self._height - 100:
                break
            d.rectangle([(40, y), (48, y + ch)], fill=acc)
            d.text((70, y + 20), item.get("title", ""), font=tf, fill=pri)
            self._wrap(d, item.get("body", ""), bf, 70, y + 80, self._width - 160, (220, 220, 220))
        img.save(output_path, format="PNG")
        return output_path

    def timeline_layout(self, events: list[dict[str, str]], *, output_path: Path | None = None) -> Path:
        if output_path is None:
            _fd, _tmp = tempfile.mkstemp(suffix=".png")
            os.close(_fd)
            output_path = Path(_tmp)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        bg = self._hex(self.palette.get("bg", "#1A1408"))
        pri = self._hex(self.palette.get("primary", "#D4A574"))
        acc = self._hex(self.palette.get("accent", "#C41E3A"))
        img = Image.new("RGB", (self._width, self._height), bg)
        d = ImageDraw.Draw(img)
        df = _load_font(self.font_title, 40)
        tf = _load_font(self.font_title, 36)
        sf = _load_font(self.font_body, 28)
        lx = 160
        d.line([(lx, 100), (lx, self._height - 100)], fill=pri, width=3)
        ys = 180
        sp = max(250, (self._height - 300) // max(len(events), 1))
        for i, ev in enumerate(events):
            y = ys + i * sp
            if y > self._height - 200:
                break
            d.ellipse([lx - 12, y - 12, lx + 12, y + 12], fill=acc)
            d.text((lx - 130, y - 15), ev.get("date", ""), font=df, fill=pri)
            d.text((lx + 30, y - 20), ev.get("title", ""), font=tf, fill=(255, 255, 255))
            if ev.get("desc"):
                self._wrap(d, ev["desc"], sf, lx + 30, y + 25, self._width - lx - 70, (180, 180, 180))
        img.save(output_path, format="PNG")
        return output_path

    # ── VS 비교 레이아웃 메서드들 ────────────────────────────────

    def vs_title_bar(
        self,
        name_a: str,
        name_b: str,
        *,
        color_a: str = "#00D4FF",
        color_b: str = "#7C3AED",
        vs_color: str = "#FF4444",
        height_ratio: float = 0.15,
        output_path: Path | None = None,
    ) -> Path:
        """VS 타이틀 바 이미지를 생성합니다 (상단 15%).

        좌측 A 이름(시안), 중앙 VS 배지(빨강), 우측 B 이름(퍼플).

        Args:
            name_a: A 항목 이름.
            name_b: B 항목 이름.
            color_a: A 색상.
            color_b: B 색상.
            vs_color: VS 배지 색상.
            height_ratio: 화면 대비 높이 비율.
            output_path: 출력 경로.
        """
        if output_path is None:
            _fd, _tmp = tempfile.mkstemp(suffix=".png")
            os.close(_fd)
            output_path = Path(_tmp)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        bar_h = int(self._height * height_ratio)
        img = Image.new("RGBA", (self._width, bar_h), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)

        # 반투명 배경 바
        d.rectangle([0, 0, self._width, bar_h], fill=(10, 14, 26, 220))

        hw = self._width // 2
        name_font = _load_font(self.font_title, 52)
        vs_font = _load_font(self.font_title, 44)

        # A 이름 (좌측)
        a_rgb = self._hex(color_a)
        d.text((hw // 2, bar_h // 2), name_a, font=name_font, fill=(*a_rgb, 255), anchor="mm")

        # B 이름 (우측)
        b_rgb = self._hex(color_b)
        d.text((hw + hw // 2, bar_h // 2), name_b, font=name_font, fill=(*b_rgb, 255), anchor="mm")

        # VS 배지 (중앙 원형)
        vs_rgb = self._hex(vs_color)
        badge_r = 45
        cx, cy = hw, bar_h // 2
        d.ellipse(
            [cx - badge_r, cy - badge_r, cx + badge_r, cy + badge_r],
            fill=(*vs_rgb, 255),
        )
        d.text((cx, cy), "VS", font=vs_font, fill=(255, 255, 255, 255), anchor="mm")

        img.save(output_path, format="PNG")
        logger.debug("[LayoutEngine] VS 타이틀 바: %s vs %s", name_a, name_b)
        return output_path

    def vs_split_cards(
        self,
        text_a: str,
        text_b: str,
        *,
        color_a: str = "#00D4FF",
        color_b: str = "#7C3AED",
        glow_line: bool = True,
        height_ratio: float = 0.55,
        output_path: Path | None = None,
    ) -> Path:
        """좌우 분할 비교 카드 이미지를 생성합니다 (중앙 55%).

        중앙에 네온 글로우 구분선 포함.

        Args:
            text_a: A 설명 텍스트.
            text_b: B 설명 텍스트.
            color_a: A 테마 색상.
            color_b: B 테마 색상.
            glow_line: 네온 글로우 구분선 여부.
            height_ratio: 화면 대비 높이 비율.
            output_path: 출력 경로.
        """
        if output_path is None:
            _fd, _tmp = tempfile.mkstemp(suffix=".png")
            os.close(_fd)
            output_path = Path(_tmp)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        card_h = int(self._height * height_ratio)
        img = Image.new("RGBA", (self._width, card_h), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)

        hw = self._width // 2
        pad = 40
        card_radius = 16

        a_rgb = self._hex(color_a)
        b_rgb = self._hex(color_b)

        # A 카드 (좌측)
        d.rounded_rectangle(
            [pad, pad, hw - 10, card_h - pad],
            radius=card_radius,
            fill=(17, 24, 39, 217),  # #111827 85%
            outline=(*a_rgb, 100),
            width=2,
        )
        # B 카드 (우측)
        d.rounded_rectangle(
            [hw + 10, pad, self._width - pad, card_h - pad],
            radius=card_radius,
            fill=(17, 24, 39, 217),
            outline=(*b_rgb, 100),
            width=2,
        )

        # 텍스트
        bf = _load_font(self.font_body, 34)
        self._wrap(d, text_a, bf, pad + 30, pad + 30, hw - pad - 70, (*a_rgb, 255))
        self._wrap(d, text_b, bf, hw + 40, pad + 30, hw - pad - 70, (*b_rgb, 255))

        # 네온 글로우 구분선
        if glow_line:
            for offset in range(-3, 4):
                alpha = max(0, 120 - abs(offset) * 40)
                d.line(
                    [(hw + offset, 0), (hw + offset, card_h)],
                    fill=(*a_rgb, alpha),
                    width=1,
                )

        img.save(output_path, format="PNG")
        logger.debug("[LayoutEngine] VS 분할 카드 생성")
        return output_path

    def vs_score_bar(
        self,
        category: str,
        score_a: float,
        score_b: float,
        *,
        max_score: float = 100.0,
        color_a: str = "#00D4FF",
        color_b: str = "#7C3AED",
        bar_height: int = 50,
        width: int | None = None,
        output_path: Path | None = None,
    ) -> Path:
        """비교 스코어 바 차트 이미지를 생성합니다.

        중앙에서 좌우로 바가 확장되는 형태.

        Args:
            category: 비교 항목명.
            score_a: A 점수.
            score_b: B 점수.
            max_score: 최대 점수.
            color_a: A 바 색상.
            color_b: B 바 색상.
            bar_height: 바 높이.
            width: 이미지 너비.
            output_path: 출력 경로.
        """
        if output_path is None:
            _fd, _tmp = tempfile.mkstemp(suffix=".png")
            os.close(_fd)
            output_path = Path(_tmp)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        w = width or self._width
        total_h = bar_height + 60  # 항목명 + 바
        img = Image.new("RGBA", (w, total_h), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)

        # 항목명 (중앙)
        cat_font = _load_font(self.font_title, 30)
        d.text((w // 2, 15), category, font=cat_font, fill=(255, 255, 255, 230), anchor="mt")

        # 바 영역
        bar_y = 45
        hw = w // 2
        max_bar_w = hw - 60  # 각 방향 최대 너비

        a_rgb = self._hex(color_a)
        b_rgb = self._hex(color_b)

        a_w = int(max_bar_w * min(score_a / max_score, 1.0))
        b_w = int(max_bar_w * min(score_b / max_score, 1.0))

        # 배경 바
        d.rounded_rectangle(
            [50, bar_y, w - 50, bar_y + bar_height],
            radius=8,
            fill=(30, 30, 40, 180),
        )

        # A 바 (좌측으로)
        if a_w > 0:
            d.rounded_rectangle(
                [hw - a_w, bar_y + 2, hw - 2, bar_y + bar_height - 2],
                radius=6,
                fill=(*a_rgb, 220),
            )

        # B 바 (우측으로)
        if b_w > 0:
            d.rounded_rectangle(
                [hw + 2, bar_y + 2, hw + b_w, bar_y + bar_height - 2],
                radius=6,
                fill=(*b_rgb, 220),
            )

        # 점수 텍스트
        score_font = _load_font(self.font_body, 24)
        d.text(
            (hw - a_w - 10, bar_y + bar_height // 2),
            str(int(score_a)),
            font=score_font,
            fill=(*a_rgb, 255),
            anchor="rm",
        )
        d.text(
            (hw + b_w + 10, bar_y + bar_height // 2),
            str(int(score_b)),
            font=score_font,
            fill=(*b_rgb, 255),
            anchor="lm",
        )

        img.save(output_path, format="PNG")
        logger.debug("[LayoutEngine] VS 스코어 바: %s (A:%.0f vs B:%.0f)", category, score_a, score_b)
        return output_path

    # ── v2: 넘버드 리스트 레이아웃 ──────────────────────────────────

    def numbered_list_layout(
        self,
        items: list[str],
        *,
        title: str = "",
        badge_color: str | None = None,
        output_path: Path | None = None,
    ) -> Path:
        """넘버 배지가 있는 리스트 레이아웃을 생성합니다.

        각 항목 앞에 원형 넘버 배지가 표시됩니다.

        Args:
            items: 리스트 항목 텍스트 목록.
            title: 상단 제목 (선택).
            badge_color: 배지 색상 (기본: accent).
            output_path: 출력 경로.
        """
        if output_path is None:
            _fd, _tmp = tempfile.mkstemp(suffix=".png")
            os.close(_fd)
            output_path = Path(_tmp)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        bg = self._hex(self.palette.get("bg", "#0A0E1A"))
        acc = self._hex(badge_color or self.palette.get("accent", "#00FF88"))
        pri = self._hex(self.palette.get("primary", "#00D4FF"))

        img = Image.new("RGB", (self._width, self._height), bg)
        d = ImageDraw.Draw(img)

        tf = _load_font(self.font_title, 48)
        bf = _load_font(self.font_body, 34)
        nf = _load_font(self.font_title, 30)

        y_start = 160
        if title:
            d.text((self._width // 2, 100), title, font=tf, fill=pri, anchor="mm")
            y_start = 200

        item_h = 140
        for i, item_text in enumerate(items):
            y = y_start + i * item_h
            if y + item_h > self._height - 100:
                break
            # 넘버 배지 (원형)
            cx, cy = 90, y + 40
            r = 28
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=acc)
            d.text((cx, cy), str(i + 1), font=nf, fill=(10, 14, 26), anchor="mm")
            # 텍스트
            self._wrap(d, item_text, bf, 140, y + 15, self._width - 200, (230, 230, 230))

        img.save(output_path, format="PNG")
        logger.debug("[LayoutEngine v2] numbered_list: %d items", len(items))
        return output_path

    # ── v2: 이미지+텍스트 오버레이 ───────────────────────────────

    def image_text_overlay(
        self,
        text: str,
        *,
        position: str = "bottom",
        opacity: int = 200,
        output_path: Path | None = None,
    ) -> Path:
        """반투명 텍스트 버블 오버레이를 생성합니다 (이미지 위에 합성용).

        Args:
            text: 표시할 텍스트.
            position: "top" | "center" | "bottom".
            opacity: 배경 투명도 (0-255).
            output_path: 출력 경로.
        """
        if output_path is None:
            _fd, _tmp = tempfile.mkstemp(suffix=".png")
            os.close(_fd)
            output_path = Path(_tmp)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        pri = self._hex(self.palette.get("primary", "#00D4FF"))
        img = Image.new("RGBA", (self._width, self._height), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        bf = _load_font(self.font_body, 38)

        # 텍스트 높이 측정
        lines = self._wrap_lines(text, bf, self._width - 120)
        line_h = 48
        block_h = len(lines) * line_h + 40

        # 위치 계산
        if position == "top":
            box_y = 60
        elif position == "center":
            box_y = (self._height - block_h) // 2
        else:  # bottom
            box_y = self._height - block_h - 120

        # 반투명 배경
        d.rounded_rectangle(
            [30, box_y, self._width - 30, box_y + block_h],
            radius=20,
            fill=(10, 14, 26, opacity),
        )

        # 텍스트
        for i, ln in enumerate(lines):
            d.text(
                (60, box_y + 20 + i * line_h),
                ln,
                font=bf,
                fill=(*pri, 250),
            )

        img.save(output_path, format="PNG")
        logger.debug("[LayoutEngine v2] image_text_overlay: %s", position)
        return output_path

    # ── v2: KPI 메트릭 대시보드 ──────────────────────────────────

    def metric_dashboard(
        self,
        metrics: list[dict[str, str]],
        *,
        title: str = "",
        cols: int = 2,
        output_path: Path | None = None,
    ) -> Path:
        """KPI 메트릭 대시보드 카드를 생성합니다.

        Args:
            metrics: [{"label": "구독자", "value": "10만", "change": "+12%"}, ...]
            title: 대시보드 제목 (선택).
            cols: 열 개수 (1~3).
            output_path: 출력 경로.
        """
        if output_path is None:
            _fd, _tmp = tempfile.mkstemp(suffix=".png")
            os.close(_fd)
            output_path = Path(_tmp)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        bg = self._hex(self.palette.get("bg", "#0A0E1A"))
        pri = self._hex(self.palette.get("primary", "#00D4FF"))
        acc = self._hex(self.palette.get("accent", "#00FF88"))

        img = Image.new("RGB", (self._width, self._height), bg)
        d = ImageDraw.Draw(img)

        tf = _load_font(self.font_title, 46)
        vf = _load_font(self.font_title, 56)  # 큰 값
        lf = _load_font(self.font_body, 28)
        cf = _load_font(self.font_body, 24)

        y_start = 160
        if title:
            d.text((self._width // 2, 90), title, font=tf, fill=pri, anchor="mm")
            y_start = 200

        cols = max(1, min(cols, 3))
        card_w = (self._width - 40 * (cols + 1)) // cols
        card_h = 200
        gap = 40

        for idx, m in enumerate(metrics):
            row, col = divmod(idx, cols)
            x = gap + col * (card_w + gap)
            y = y_start + row * (card_h + gap)
            if y + card_h > self._height - 60:
                break

            # 카드 배경
            d.rounded_rectangle(
                [x, y, x + card_w, y + card_h],
                radius=16,
                fill=(20, 25, 45),
                outline=(*pri, 60),
                width=1,
            )

            # 라벨
            d.text((x + card_w // 2, y + 30), m.get("label", ""), font=lf, fill=(180, 180, 180), anchor="mm")
            # 값
            d.text((x + card_w // 2, y + 90), m.get("value", ""), font=vf, fill=pri, anchor="mm")
            # 변화량
            change = m.get("change", "")
            if change:
                is_positive = change.startswith("+")
                color = acc if is_positive else (239, 68, 68)  # green or red
                d.text((x + card_w // 2, y + 150), change, font=cf, fill=color, anchor="mm")

        img.save(output_path, format="PNG")
        logger.debug("[LayoutEngine v2] metric_dashboard: %d metrics", len(metrics))
        return output_path

    # ── v2: 단계별 가이드 레이아웃 ─────────────────────────────────

    def step_by_step_layout(
        self,
        steps: list[dict[str, str]],
        *,
        title: str = "",
        output_path: Path | None = None,
    ) -> Path:
        """단계별 가이드 레이아웃을 생성합니다 (커넥터 라인 포함).

        Args:
            steps: [{"label": "STEP 1", "title": "준비", "desc": "재료를 준비합니다"}, ...]
            title: 상단 제목 (선택).
            output_path: 출력 경로.
        """
        if output_path is None:
            _fd, _tmp = tempfile.mkstemp(suffix=".png")
            os.close(_fd)
            output_path = Path(_tmp)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        bg = self._hex(self.palette.get("bg", "#0A0E1A"))
        pri = self._hex(self.palette.get("primary", "#00D4FF"))
        acc = self._hex(self.palette.get("accent", "#00FF88"))

        img = Image.new("RGB", (self._width, self._height), bg)
        d = ImageDraw.Draw(img)

        tf = _load_font(self.font_title, 44)
        sf = _load_font(self.font_title, 32)
        bf = _load_font(self.font_body, 28)
        label_f = _load_font(self.font_body, 22)

        y_start = 160
        if title:
            d.text((self._width // 2, 90), title, font=tf, fill=pri, anchor="mm")
            y_start = 200

        step_h = max(200, (self._height - y_start - 100) // max(len(steps), 1))
        dot_x = 100

        for i, step in enumerate(steps):
            y = y_start + i * step_h
            if y + step_h > self._height - 60:
                break

            # 커넥터 라인 (마지막 제외)
            if i < len(steps) - 1:
                d.line([(dot_x, y + 30), (dot_x, y + step_h)], fill=(*pri, 80), width=2)

            # 도트
            d.ellipse([dot_x - 16, y + 14, dot_x + 16, y + 46], fill=acc)

            # 라벨 (STEP 1 등)
            label = step.get("label", f"STEP {i + 1}")
            d.text((dot_x + 40, y + 10), label, font=label_f, fill=acc)

            # 제목
            d.text((dot_x + 40, y + 40), step.get("title", ""), font=sf, fill=(255, 255, 255))

            # 설명
            desc = step.get("desc", "")
            if desc:
                self._wrap(d, desc, bf, dot_x + 40, y + 80, self._width - dot_x - 100, (180, 180, 180))

        img.save(output_path, format="PNG")
        logger.debug("[LayoutEngine v2] step_by_step: %d steps", len(steps))
        return output_path

    # ── v2: 인용문 카드 ──────────────────────────────────────────

    def quote_card(
        self,
        quote: str,
        *,
        author: str = "",
        accent_color: str | None = None,
        output_path: Path | None = None,
    ) -> Path:
        """인용문 카드를 생성합니다 (좌측 악센트 바 + 큰따옴표).

        Args:
            quote: 인용 텍스트.
            author: 저자/출처 (선택).
            accent_color: 악센트 색상 (기본: primary).
            output_path: 출력 경로.
        """
        if output_path is None:
            _fd, _tmp = tempfile.mkstemp(suffix=".png")
            os.close(_fd)
            output_path = Path(_tmp)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        bg = self._hex(self.palette.get("bg", "#0A0E1A"))
        pri = self._hex(accent_color or self.palette.get("primary", "#00D4FF"))

        card_h = 500
        img = Image.new("RGB", (self._width, card_h), bg)
        d = ImageDraw.Draw(img)

        # 카드 배경
        d.rounded_rectangle(
            [40, 30, self._width - 40, card_h - 30],
            radius=20,
            fill=(17, 24, 39),
            outline=(*pri, 60),
            width=1,
        )

        # 좌측 악센트 바
        d.rectangle([40, 30, 50, card_h - 30], fill=pri)

        # 큰따옴표
        qf = _load_font(self.font_title, 80)
        d.text((90, 50), "\u201c", font=qf, fill=(*pri, 150))

        # 인용 텍스트
        qbf = _load_font(self.font_body, 36)
        self._wrap(d, quote, qbf, 100, 150, self._width - 200, (230, 230, 230))

        # 저자
        if author:
            af = _load_font(self.font_body, 28)
            d.text((self._width - 80, card_h - 80), f"— {author}", font=af, fill=(*pri, 200), anchor="rm")

        img.save(output_path, format="PNG")
        logger.debug("[LayoutEngine v2] quote_card: %.30s...", quote)
        return output_path

    # ── v2: 비교표 ───────────────────────────────────────────────

    def comparison_table(
        self,
        headers: list[str],
        rows: list[list[str]],
        *,
        header_color: str | None = None,
        output_path: Path | None = None,
    ) -> Path:
        """비교표 레이아웃을 생성합니다.

        Args:
            headers: 헤더 텍스트 목록 (3개 권장).
            rows: 행 데이터 목록 (각 행은 headers와 동일 길이).
            header_color: 헤더 배경 색상 (기본: primary).
            output_path: 출력 경로.
        """
        if output_path is None:
            _fd, _tmp = tempfile.mkstemp(suffix=".png")
            os.close(_fd)
            output_path = Path(_tmp)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        bg = self._hex(self.palette.get("bg", "#0A0E1A"))
        pri = self._hex(header_color or self.palette.get("primary", "#00D4FF"))

        row_h = 70
        header_h = 80
        total_h = header_h + row_h * len(rows) + 80
        total_h = min(total_h, self._height)

        img = Image.new("RGB", (self._width, total_h), bg)
        d = ImageDraw.Draw(img)

        col_w = (self._width - 80) // max(len(headers), 1)
        hf = _load_font(self.font_title, 30)
        rf = _load_font(self.font_body, 28)

        # 헤더
        d.rectangle([30, 30, self._width - 30, 30 + header_h], fill=(*pri, 40))
        for j, h in enumerate(headers):
            cx = 40 + j * col_w + col_w // 2
            d.text((cx, 30 + header_h // 2), h, font=hf, fill=pri, anchor="mm")

        # 행
        for i, row in enumerate(rows):
            y = 30 + header_h + i * row_h
            if y + row_h > total_h - 10:
                break
            if i % 2 == 1:
                d.rectangle([30, y, self._width - 30, y + row_h], fill=(20, 25, 40))
            for j, cell in enumerate(row):
                cx = 40 + j * col_w + col_w // 2
                d.text((cx, y + row_h // 2), cell, font=rf, fill=(210, 210, 210), anchor="mm")

        # 테두리
        d.rectangle([30, 30, self._width - 30, 30 + header_h + len(rows) * row_h], outline=(*pri, 40), width=1)

        img.save(output_path, format="PNG")
        logger.debug("[LayoutEngine v2] comparison_table: %dx%d", len(headers), len(rows))
        return output_path

    # ── 유틸리티 ─────────────────────────────────────────────────

    @staticmethod
    def _wrap(d, text, font, x, y, mw, fill):
        words, lines, cur = text.split(), [], []
        for w in words:
            c = " ".join(cur + [w])
            try:
                bw = d.textbbox((0, 0), c, font=font)[2]
            except Exception:
                bw = len(c) * 20
            if bw <= mw or not cur:
                cur.append(w)
            else:
                lines.append(" ".join(cur))
                cur = [w]
        if cur:
            lines.append(" ".join(cur))
        for i, ln in enumerate(lines):
            d.text((x, y + i * 40), ln, font=font, fill=fill)

    @staticmethod
    def _wrap_lines(text: str, font, max_width: int) -> list[str]:
        """텍스트를 max_width 내에서 줄바꿈하여 리스트 반환."""
        words = text.split()
        lines: list[str] = []
        cur: list[str] = []
        for w in words:
            c = " ".join(cur + [w])
            try:
                from PIL import Image as _Img
                from PIL import ImageDraw as _Draw

                probe = _Img.new("RGB", (1, 1))
                d = _Draw.Draw(probe)
                bw = d.textbbox((0, 0), c, font=font)[2]
            except Exception:
                bw = len(c) * 20
            if bw <= max_width or not cur:
                cur.append(w)
            else:
                lines.append(" ".join(cur))
                cur = [w]
        if cur:
            lines.append(" ".join(cur))
        return lines

    @staticmethod
    def _hex(c: str) -> tuple[int, int, int]:
        h = c.lstrip("#")
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)) if len(h) == 6 else (0, 0, 0)
