"""
layout_engine.py — 분할/카드 레이아웃 엔진
"""
from __future__ import annotations
import logging, tempfile
from pathlib import Path
from typing import Any
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

def _load_font(name: str, size: int):
    _C = {"Pretendard-ExtraBold": "C:/Windows/Fonts/malgunbd.ttf",
          "Pretendard-Bold": "C:/Windows/Fonts/malgunbd.ttf",
          "Pretendard-Regular": "C:/Windows/Fonts/malgun.ttf",
          "NanumMyeongjo-Bold": "C:/Windows/Fonts/malgunbd.ttf"}
    path = _C.get(name, "C:/Windows/Fonts/malgun.ttf")
    try:
        if Path(path).exists(): return ImageFont.truetype(path, size)
    except Exception: pass
    return ImageFont.load_default()

class LayoutEngine:
    def __init__(self, channel_config: dict[str, Any]) -> None:
        self.config = channel_config
        self.palette = channel_config.get("palette", {})
        self.font_title = channel_config.get("font_title", "Pretendard-Bold")
        self.font_body = channel_config.get("font_body", "Pretendard-Regular")
        self._width, self._height = 1080, 1920

    def split_screen(self, left_text: str, right_text: str, *,
                     left_label: str="DO ✅", right_label: str="DON'T ❌",
                     left_color: str|None=None, right_color: str|None=None,
                     output_path: Path|None=None) -> Path:
        if output_path is None: output_path = Path(tempfile.mktemp(suffix=".png"))
        output_path.parent.mkdir(parents=True, exist_ok=True)
        bg = self._hex(self.palette.get("bg","#0A0E1A"))
        pos = self._hex(left_color or self.palette.get("accent","#34D399"))
        neg = self._hex(right_color or "#EF4444")
        img = Image.new("RGB", (self._width, self._height), bg)
        d = ImageDraw.Draw(img)
        hw = self._width // 2
        d.line([(hw,100),(hw,self._height-100)], fill=(100,100,100), width=3)
        lf = _load_font(self.font_title, 48)
        bf = _load_font(self.font_body, 36)
        d.text((hw//2,200), left_label, font=lf, fill=pos, anchor="mm")
        d.text((hw+hw//2,200), right_label, font=lf, fill=neg, anchor="mm")
        self._wrap(d, left_text, bf, 40, 320, hw-80, (255,255,255))
        self._wrap(d, right_text, bf, hw+40, 320, hw-80, (255,255,255))
        img.save(output_path, format="PNG")
        return output_path

    def card_layout(self, items: list[dict[str,str]], *, output_path: Path|None=None) -> Path:
        if output_path is None: output_path = Path(tempfile.mktemp(suffix=".png"))
        output_path.parent.mkdir(parents=True, exist_ok=True)
        bg = self._hex(self.palette.get("bg","#0A0E1A"))
        pri = self._hex(self.palette.get("primary","#00D4FF"))
        acc = self._hex(self.palette.get("accent","#00FF88"))
        img = Image.new("RGB", (self._width, self._height), bg)
        d = ImageDraw.Draw(img)
        tf = _load_font(self.font_title, 42)
        bf = _load_font(self.font_body, 32)
        ch, m, ys = 220, 40, 200
        for i, item in enumerate(items):
            y = ys + i*(ch+m)
            if y+ch > self._height-100: break
            d.rectangle([(40,y),(48,y+ch)], fill=acc)
            d.text((70,y+20), item.get("title",""), font=tf, fill=pri)
            self._wrap(d, item.get("body",""), bf, 70, y+80, self._width-160, (220,220,220))
        img.save(output_path, format="PNG")
        return output_path

    def timeline_layout(self, events: list[dict[str,str]], *, output_path: Path|None=None) -> Path:
        if output_path is None: output_path = Path(tempfile.mktemp(suffix=".png"))
        output_path.parent.mkdir(parents=True, exist_ok=True)
        bg = self._hex(self.palette.get("bg","#1A1408"))
        pri = self._hex(self.palette.get("primary","#D4A574"))
        acc = self._hex(self.palette.get("accent","#C41E3A"))
        img = Image.new("RGB", (self._width, self._height), bg)
        d = ImageDraw.Draw(img)
        df = _load_font(self.font_title, 40)
        tf = _load_font(self.font_title, 36)
        sf = _load_font(self.font_body, 28)
        lx = 160
        d.line([(lx,100),(lx,self._height-100)], fill=pri, width=3)
        ys = 180
        sp = max(250, (self._height-300)//max(len(events),1))
        for i, ev in enumerate(events):
            y = ys + i*sp
            if y > self._height-200: break
            d.ellipse([lx-12,y-12,lx+12,y+12], fill=acc)
            d.text((lx-130,y-15), ev.get("date",""), font=df, fill=pri)
            d.text((lx+30,y-20), ev.get("title",""), font=tf, fill=(255,255,255))
            if ev.get("desc"):
                self._wrap(d, ev["desc"], sf, lx+30, y+25, self._width-lx-70, (180,180,180))
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
            output_path = Path(tempfile.mktemp(suffix=".png"))
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
        d.text((hw // 2, bar_h // 2), name_a, font=name_font,
               fill=(*a_rgb, 255), anchor="mm")

        # B 이름 (우측)
        b_rgb = self._hex(color_b)
        d.text((hw + hw // 2, bar_h // 2), name_b, font=name_font,
               fill=(*b_rgb, 255), anchor="mm")

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
            output_path = Path(tempfile.mktemp(suffix=".png"))
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
                    fill=(*a_rgb, alpha), width=1,
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
            output_path = Path(tempfile.mktemp(suffix=".png"))
        output_path.parent.mkdir(parents=True, exist_ok=True)

        w = width or self._width
        total_h = bar_height + 60  # 항목명 + 바
        img = Image.new("RGBA", (w, total_h), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)

        # 항목명 (중앙)
        cat_font = _load_font(self.font_title, 30)
        d.text((w // 2, 15), category, font=cat_font,
               fill=(255, 255, 255, 230), anchor="mt")

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
            radius=8, fill=(30, 30, 40, 180),
        )

        # A 바 (좌측으로)
        if a_w > 0:
            d.rounded_rectangle(
                [hw - a_w, bar_y + 2, hw - 2, bar_y + bar_height - 2],
                radius=6, fill=(*a_rgb, 220),
            )

        # B 바 (우측으로)
        if b_w > 0:
            d.rounded_rectangle(
                [hw + 2, bar_y + 2, hw + b_w, bar_y + bar_height - 2],
                radius=6, fill=(*b_rgb, 220),
            )

        # 점수 텍스트
        score_font = _load_font(self.font_body, 24)
        d.text((hw - a_w - 10, bar_y + bar_height // 2),
               str(int(score_a)), font=score_font,
               fill=(*a_rgb, 255), anchor="rm")
        d.text((hw + b_w + 10, bar_y + bar_height // 2),
               str(int(score_b)), font=score_font,
               fill=(*b_rgb, 255), anchor="lm")

        img.save(output_path, format="PNG")
        logger.debug("[LayoutEngine] VS 스코어 바: %s (A:%.0f vs B:%.0f)", category, score_a, score_b)
        return output_path

    @staticmethod
    def _wrap(d, text, font, x, y, mw, fill):
        words, lines, cur = text.split(), [], []
        for w in words:
            c = " ".join(cur+[w])
            try: bw = d.textbbox((0,0),c,font=font)[2]
            except: bw = len(c)*20
            if bw <= mw or not cur: cur.append(w)
            else: lines.append(" ".join(cur)); cur = [w]
        if cur: lines.append(" ".join(cur))
        for i, ln in enumerate(lines): d.text((x,y+i*40), ln, font=font, fill=fill)

    @staticmethod
    def _hex(c: str) -> tuple[int,int,int]:
        h = c.lstrip("#")
        return (int(h[0:2],16),int(h[2:4],16),int(h[4:6],16)) if len(h)==6 else (0,0,0)
