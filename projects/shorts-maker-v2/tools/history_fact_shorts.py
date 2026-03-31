#!/usr/bin/env python3
"""역사 팩트 반전 스토리텔링 쇼츠 생성기.

양피지 텍스처 + 세피아 톤 다큐멘터리 스타일.
4-Phase: "알고 보면" 훅 → 통념 소개 → 반전 사실 → 교훈/CTA.
역사팝콘 채널 메인 포맷.
"""

from __future__ import annotations

import argparse
import math
import os
import random
import warnings
from pathlib import Path

warnings.filterwarnings("ignore", category=DeprecationWarning, module="PIL")

import numpy as np
from PIL import Image, ImageDraw, ImageFont

try:
    from moviepy import VideoClip
except ImportError:
    from moviepy.editor import VideoClip  # type: ignore


class HistoryFactGenerator:
    """역사 반전 팩트 스토리텔링 쇼츠."""

    W, H = 1080, 1920
    FPS = 30
    MG = 70

    # Vintage palette
    BG_DARK = (26, 20, 8)  # #1A1408
    PARCHMENT = (44, 34, 16)  # #2C2210
    IVORY = (245, 230, 200)  # #F5E6C8
    GOLD = (212, 165, 116)  # #D4A574
    CRIMSON = (196, 30, 58)  # #C41E3A
    AMBER = (245, 158, 11)  # #F59E0B
    WHITE_DIM = (200, 190, 170)  # 배경 텍스트용

    def __init__(
        self,
        title: str,
        myth: str,
        fact: str,
        details: list[str] | None = None,
        lesson: str = "",
        era: str = "",
        region: str = "",
        cta: str = "구독하고 역사의 반전을 놓치지 마세요!",
        image_path: str | None = None,
        duration: float = 38.0,
    ):
        self.title = title
        self.myth = myth
        self.fact = fact
        self.details = (details or [])[:4]
        self.lesson = lesson
        self.era = era
        self.region = region
        self.cta = cta
        self.duration = max(30, min(50, duration))

        # Phase timings
        r = self.duration / 38.0
        self.PH1_END = 5.0
        self.PH2_END = 5.0 + 10.0 * r
        self.PH3_END = self.PH2_END + 15.0 * r
        self.PH4_END = self.duration

        self._load_fonts()
        self._bg_img = self._load_bg(image_path)
        self._vignette = self._make_vignette()

        # Preprocess text
        tw = self.W - self.MG * 2 - 40
        self._title_lines = self._wrap(title, self.f_title, tw)
        self._myth_lines = self._wrap(myth, self.f_body, tw - 40)
        self._fact_lines = self._wrap(fact, self.f_body, tw - 40)
        self._detail_lines = [self._wrap(d, self.f_body, tw - 60) for d in self.details]
        self._lesson_lines = self._wrap(lesson, self.f_body, tw - 40) if lesson else []

        # Ember particles
        random.seed(88)
        self._embers = [
            {
                "x": random.randint(0, self.W),
                "y": random.randint(self.H // 2, self.H),
                "vx": random.uniform(-8, 8),
                "vy": random.uniform(-25, -8),
                "r": random.uniform(1, 3),
                "a": random.randint(30, 90),
                "ph": random.uniform(0, math.tau),
            }
            for _ in range(16)
        ]

    def _load_fonts(self):
        dirs = [Path("C:/Windows/Fonts"), Path(os.path.expanduser("~/AppData/Local/Microsoft/Windows/Fonts"))]

        def _f(ns, fb="malgun.ttf"):
            for d in dirs:
                for n in ns:
                    if (d / n).exists():
                        return str(d / n)
            for d in dirs:
                if (d / fb).exists():
                    return str(d / fb)
            return ""

        sb = _f(["NanumMyeongjoBold.ttf", "NanumGothicBold.ttf", "malgunbd.ttf"])
        sr = _f(["NanumMyeongjo.ttf", "NanumGothic.ttf", "malgun.ttf"])
        sa = _f(["NanumGothic.ttf", "malgun.ttf"])

        def _l(p, s):
            return ImageFont.truetype(p, s) if p else ImageFont.load_default(s)

        self.f_title = _l(sb, 56)  # 제목: 세리프 Bold
        self.f_body = _l(sa, 34)  # 본문
        self.f_big = _l(sb, 48)  # 반전 텍스트
        self.f_era = _l(sr, 42)  # 연대/지역 (세리프)
        self.f_small = _l(sa, 28)  # 캡션
        self.f_badge = _l(sb, 24)  # 배지

    def _load_bg(self, path):
        if path and Path(path).exists():
            img = Image.open(path).convert("RGB")
            sc = max(self.W / img.width, self.H / img.height)
            nw, nh = int(img.width * sc), int(img.height * sc)
            img = img.resize((nw, nh), Image.LANCZOS)
            l_ = (nw - self.W) // 2
            t_ = (nh - self.H) // 2
            img = img.crop((l_, t_, l_ + self.W, t_ + self.H))
            # Sepia tint
            arr = np.array(img, dtype=np.float32)
            gray = 0.299 * arr[:, :, 0] + 0.587 * arr[:, :, 1] + 0.114 * arr[:, :, 2]
            arr[:, :, 0] = np.clip(gray * 1.1, 0, 255)
            arr[:, :, 1] = np.clip(gray * 0.85, 0, 255)
            arr[:, :, 2] = np.clip(gray * 0.65, 0, 255)
            return arr.astype(np.uint8)
        # Fallback: dark parchment gradient
        arr = np.zeros((self.H, self.W, 3), dtype=np.uint8)
        for y in range(self.H):
            r_ = y / self.H
            arr[y, :] = [int(26 + 10 * r_), int(20 + 6 * r_), int(8 + 4 * r_)]
        return arr

    def _make_vignette(self):
        v = Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0))
        d = ImageDraw.Draw(v)
        for i in range(80):
            al = int(180 * (1 - i / 80) ** 2)
            d.rectangle([(i, i), (self.W - i, self.H - i)], outline=(0, 0, 0, al))
        return np.array(v)

    @staticmethod
    def _wrap(text, font, mw):
        lines, cur = [], ""
        for seg in text.replace("\n", " \n ").split(" "):
            if seg == "\n":
                if cur:
                    lines.append(cur)
                cur = ""
                continue
            t = f"{cur} {seg}".strip() if cur else seg
            if font.getbbox(t)[2] - font.getbbox(t)[0] <= mw:
                cur = t
            else:
                if cur:
                    lines.append(cur)
                cur = seg
        if cur:
            lines.append(cur)
        return lines

    def _tw(self, t, f):
        b = f.getbbox(t)
        return b[2] - b[0]

    def _th(self, t, f):
        b = f.getbbox(t)
        return b[3] - b[1]

    @staticmethod
    def _eo(t):
        return 1 - (1 - min(1, max(0, t))) ** 3

    @staticmethod
    def _ei(t):
        return min(1, max(0, t)) ** 2

    # ── Drawing helpers ──
    def _draw_card(self, draw, x, y, w, h, alpha=180, color=None):
        c = color or self.PARCHMENT
        for i in range(4):
            draw.rounded_rectangle([(x + i, y + i), (x + w - i, y + h - i)], radius=8, fill=(*c, alpha - i * 6))
        draw.rounded_rectangle([(x, y), (x + w, y + h)], radius=8, outline=(*self.GOLD, 50), width=1)

    def _draw_badge(self, draw, x, y, text, color=None):
        c = color or self.GOLD
        tw_ = self._tw(text, self.f_badge) + 20
        draw.rounded_rectangle([(x, y), (x + tw_, y + 32)], radius=4, fill=(*c, 50), outline=(*c, 100), width=1)
        draw.text((x + 10, y + 4), text, font=self.f_badge, fill=(*c, 200))
        return tw_

    def _draw_embers(self, draw, t):
        for p in self._embers:
            x = (p["x"] + p["vx"] * t) % self.W
            y = (p["y"] + p["vy"] * t) % self.H
            fl = 0.3 + 0.7 * math.sin(t * 1.2 + p["ph"])
            al = int(p["a"] * fl)
            r = p["r"] * (0.8 + 0.2 * fl)
            draw.ellipse([(x - r, y - r), (x + r, y + r)], fill=(212, 165, 116, al))

    def _draw_separator(self, draw, y, width=400):
        """장식 구분선."""
        cx = self.W // 2
        draw.line([(cx - width // 2, y), (cx + width // 2, y)], fill=(*self.GOLD, 60), width=1)
        draw.ellipse([(cx - 3, y - 3), (cx + 3, y + 3)], fill=(*self.GOLD, 80))

    # ── Phase renderers ──
    def _ph1(self, draw, t):
        """훅: "알고 보면..." + 제목 (0~5초)."""
        # 화면 서서히 밝아짐
        if t > 0.5:
            # Era badge
            if self.era:
                int(180 * self._eo((t - 0.5) / 0.6))
                self._draw_badge(draw, self.MG, 560, f"📜 {self.era}", self.GOLD)
            if self.region:
                int(180 * self._eo((t - 0.8) / 0.6))
                self._draw_badge(draw, self.MG + 200, 560, f"📍 {self.region}", self.GOLD)

        # Hook text: typewriter
        if t > 1.0:
            hook = "알고 보면 충격적인 사실..."
            shown = hook[: int((t - 1.0) / 0.06)]
            if shown:
                ha = int(250 * min(1, (t - 1.0) / 1.5))
                hw = self._tw(shown, self.f_big)
                draw.text(((self.W - hw) // 2, 650), shown, font=self.f_big, fill=(*self.CRIMSON, ha))

        # Title
        if t > 2.8:
            lh = self._th("가", self.f_title) + 14
            for i, line in enumerate(self._title_lines):
                la = int(240 * self._eo((t - 2.8 - i * 0.25) / 0.7))
                tw_ = self._tw(line, self.f_title)
                draw.text(((self.W - tw_) // 2, 780 + i * lh), line, font=self.f_title, fill=(*self.IVORY, la))

    def _ph2(self, draw, t):
        """통념 소개 (PH1→PH2)."""
        lt = t - self.PH1_END

        # "우리가 알고 있는 이야기" badge
        if lt > 0.3:
            self._draw_badge(draw, self.MG, 400, "📖 우리가 알고 있는 이야기", self.GOLD)

        # Myth card
        if lt > 0.8 and self._myth_lines:
            ca = int(210 * self._eo((lt - 0.8) / 0.8))
            lh = self._th("가", self.f_body) + 12
            card_h = 50 + len(self._myth_lines) * lh + 30
            cx = self.MG
            cy = 460
            self._draw_card(draw, cx, cy, self.W - self.MG * 2, card_h, ca)

            for i, line in enumerate(self._myth_lines):
                la = int(220 * self._eo((lt - 1.0 - i * 0.15) / 0.5))
                if la < 0:
                    la = 0
                draw.text((cx + 30, cy + 30 + i * lh), line, font=self.f_body, fill=(*self.IVORY, la))

        # Era & region (subtle background)
        if self.era and lt > 1.5:
            ea = int(50 * self._eo((lt - 1.5) / 0.5))
            draw.text((self.MG, self.H - 200), self.era, font=self.f_era, fill=(*self.GOLD, ea))

    def _ph3(self, draw, t):
        """반전 사실 (PH2→PH3)."""
        lt = t - self.PH2_END

        # "하지만 사실은..." flash
        if lt < 3.0:
            ta = int(255 * self._eo(lt / 0.6))
            if lt > 2.0:
                ta = int(ta * (1 - self._eo((lt - 2.0) / 1.0)))
            txt = "하지만 사실은..."
            tw_ = self._tw(txt, self.f_big)
            # Crimson glow
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                draw.text(
                    ((self.W - tw_) // 2 + dx, self.H // 2 - 60 + dy),
                    txt,
                    font=self.f_big,
                    fill=(*self.CRIMSON, ta // 3),
                )
            draw.text(((self.W - tw_) // 2, self.H // 2 - 60), txt, font=self.f_big, fill=(*self.CRIMSON, ta))

        # Fact card
        if lt > 2.0 and self._fact_lines:
            ca = int(220 * self._eo((lt - 2.0) / 0.8))
            lh = self._th("가", self.f_body) + 12
            card_h = 50 + len(self._fact_lines) * lh + 30
            cx, cy = self.MG, 500
            self._draw_card(draw, cx, cy, self.W - self.MG * 2, card_h, ca)

            # ❗ badge
            self._draw_badge(draw, cx + 15, cy + 10, "❗ 반전 팩트", self.CRIMSON)

            for i, line in enumerate(self._fact_lines):
                la = int(230 * self._eo((lt - 2.5 - i * 0.15) / 0.5))
                if la < 0:
                    la = 0
                draw.text((cx + 30, cy + 50 + i * lh), line, font=self.f_body, fill=(*self.IVORY, la))

        # Detail points
        if lt > 5.0 and self.details:
            lh = self._th("가", self.f_body) + 10
            base_y = 800 if len(self._fact_lines) <= 3 else 900
            for i, det_lines in enumerate(self._detail_lines):
                pt = lt - 5.0 - i * 1.5
                if pt < 0:
                    continue
                al = int(200 * self._eo(pt / 0.5))
                # Bullet
                draw.text((self.MG + 20, base_y + i * 90), "▸", font=self.f_body, fill=(*self.GOLD, al))
                for j, ln in enumerate(det_lines):
                    draw.text((self.MG + 50, base_y + i * 90 + j * lh), ln, font=self.f_body, fill=(*self.IVORY, al))

    def _ph4(self, draw, t):
        """교훈 + CTA."""
        lt = t - self.PH3_END
        dur = self.PH4_END - self.PH3_END

        # Separator
        self._draw_separator(draw, 650)

        # Lesson
        if self._lesson_lines and lt > 0.5:
            self._draw_badge(draw, self.MG, 680, "💡 알아두면 좋은 것", self.AMBER)
            lh = self._th("가", self.f_body) + 14
            for i, line in enumerate(self._lesson_lines):
                la = int(220 * self._eo((lt - 0.8 - i * 0.2) / 0.6))
                if la < 0:
                    la = 0
                draw.text((self.MG + 20, 730 + i * lh), line, font=self.f_body, fill=(*self.IVORY, la))

        # Channel badge + CTA
        if lt > 2.0:
            ca = int(220 * self._eo((lt - 2.0) / 0.8))
            if lt > dur - 1.5:
                ca = int(ca * (1 - self._ei((lt - (dur - 1.5)) / 1.5)))
            self._draw_badge(draw, (self.W - 180) // 2, 950, "🏺 역사팝콘", self.GOLD)
            cta_w = self._tw(self.cta, self.f_body)
            draw.text(((self.W - cta_w) // 2, 1010), self.cta, font=self.f_body, fill=(*self.GOLD, ca))

    # ── Main render ──
    def _render(self, t):
        # Background brightness by phase
        if t < self.PH1_END:
            br = self._eo(t / 2.5) * 0.35
        elif t < self.PH2_END:
            br = 0.35
        elif t < self.PH3_END:
            lt3 = t - self.PH2_END
            br = 0.35 * (1 - self._eo(lt3 / 0.5) * 0.3) if lt3 < 1.5 else 0.25 + self._eo((lt3 - 1.5) / 1.0) * 0.1
        else:
            br = 0.30

        arr = (self._bg_img.astype(np.float32) * br).clip(0, 255).astype(np.uint8)
        bg = Image.fromarray(arr, "RGB").convert("RGBA")

        # Vignette
        vig = Image.fromarray(self._vignette, "RGBA")
        bg = Image.alpha_composite(bg, vig)

        ov = Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0))
        draw = ImageDraw.Draw(ov)

        # Ember particles
        self._draw_embers(draw, t)

        # Phase content
        if t < self.PH1_END:
            self._ph1(draw, t)
        elif t < self.PH2_END:
            self._ph2(draw, t)
        elif t < self.PH3_END:
            self._ph3(draw, t)
        else:
            self._ph4(draw, t)

        comp = Image.alpha_composite(bg, ov)
        return np.array(comp.convert("RGB"))

    def generate(self, out="history_fact.mp4"):
        clip = VideoClip(lambda t: self._render(t), duration=self.duration).with_fps(self.FPS)
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        clip.write_videofile(str(out), codec="libx264", preset="medium", bitrate="8000k", audio=False, logger="bar")
        print(f"\n✅ 생성 완료: {Path(out).resolve()}")
        print(f"   크기: {self.W}×{self.H} | 길이: {self.duration:.0f}초")
        return str(Path(out).resolve())


class HistoryCountdownGenerator:
    """역사 카운트다운 쇼츠 (TOP N 랭킹).

    5위→1위 카운트다운 with 양피지 카드 + 세피아 톤.
    """

    W, H = 1080, 1920
    FPS = 30

    IVORY = (245, 230, 200)
    GOLD = (212, 165, 116)
    CRIMSON = (196, 30, 58)
    PARCHMENT = (44, 34, 16)

    def __init__(
        self,
        title: str,
        items: list[dict] | None = None,
        cta: str = "더 많은 역사 랭킹이 궁금하다면 구독!",
        duration: float = 40.0,
    ):
        """
        Args:
            items: [{"rank": 5, "name": "피라미드", "desc": "설명"}]
        """
        self.title = title
        self.items = sorted(items or [], key=lambda x: x.get("rank", 99), reverse=True)[:5]
        self.cta = cta
        self.duration = max(30, min(55, duration))
        self._load_fonts()

        tw = self.W - 200
        self._title_lines = self._wrap(title, self.f_title, tw)
        self._item_lines = [
            {
                "rank": it["rank"],
                "name": it.get("name", ""),
                "desc_lines": self._wrap(it.get("desc", ""), self.f_body, tw - 100),
            }
            for it in self.items
        ]

        random.seed(99)
        self._embers = [
            {
                "x": random.randint(0, self.W),
                "y": random.randint(self.H // 2, self.H),
                "vx": random.uniform(-6, 6),
                "vy": random.uniform(-20, -5),
                "r": random.uniform(1, 2.5),
                "a": random.randint(20, 70),
                "ph": random.uniform(0, math.tau),
            }
            for _ in range(12)
        ]

    def _load_fonts(self):
        dirs = [Path("C:/Windows/Fonts"), Path(os.path.expanduser("~/AppData/Local/Microsoft/Windows/Fonts"))]

        def _f(ns, fb="malgun.ttf"):
            for d in dirs:
                for n in ns:
                    if (d / n).exists():
                        return str(d / n)
            for d in dirs:
                if (d / fb).exists():
                    return str(d / fb)
            return ""

        sb = _f(["NanumMyeongjoBold.ttf", "NanumGothicBold.ttf", "malgunbd.ttf"])
        sa = _f(["NanumGothic.ttf", "malgun.ttf"])

        def _l(p, s):
            return ImageFont.truetype(p, s) if p else ImageFont.load_default(s)

        self.f_title = _l(sb, 52)
        self.f_rank = _l(sb, 90)
        self.f_name = _l(sb, 46)
        self.f_body = _l(sa, 32)
        self.f_small = _l(sa, 28)

    @staticmethod
    def _wrap(text, font, mw):
        lines, cur = [], ""
        for seg in text.split(" "):
            t = f"{cur} {seg}".strip() if cur else seg
            if font.getbbox(t)[2] - font.getbbox(t)[0] <= mw:
                cur = t
            else:
                if cur:
                    lines.append(cur)
                cur = seg
        if cur:
            lines.append(cur)
        return lines

    def _tw(self, t, f):
        b = f.getbbox(t)
        return b[2] - b[0]

    def _th(self, t, f):
        b = f.getbbox(t)
        return b[3] - b[1]

    @staticmethod
    def _eo(t):
        return 1 - (1 - min(1, max(0, t))) ** 3

    def _render(self, t):
        # BG
        arr = np.zeros((self.H, self.W, 3), dtype=np.uint8)
        for y in range(self.H):
            r_ = y / self.H
            arr[y, :] = [int(26 + 8 * r_), int(20 + 5 * r_), int(8 + 3 * r_)]
        bg = Image.fromarray(arr, "RGB").convert("RGBA")
        ov = Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0))
        draw = ImageDraw.Draw(ov)

        # Embers
        for p in self._embers:
            x = (p["x"] + p["vx"] * t) % self.W
            y_ = (p["y"] + p["vy"] * t) % self.H
            fl = 0.3 + 0.7 * math.sin(t * 1.2 + p["ph"])
            al = int(p["a"] * fl)
            draw.ellipse([(x - p["r"], y_ - p["r"]), (x + p["r"], y_ + p["r"])], fill=(212, 165, 116, al))

        n = len(self._item_lines)
        # Phase timing
        hook_end = 4.0
        item_dur = (self.duration - hook_end - 5.0) / max(1, n)
        cta_start = self.duration - 5.0

        if t < hook_end:
            # Title
            lh = self._th("가", self.f_title) + 12
            for i, line in enumerate(self._title_lines):
                la = int(240 * self._eo((t - 0.5 - i * 0.2) / 0.8))
                if la < 0:
                    la = 0
                tw_ = self._tw(line, self.f_title)
                draw.text(((self.W - tw_) // 2, 700 + i * lh), line, font=self.f_title, fill=(*self.IVORY, la))
        elif t < cta_start:
            # Item cards
            lt = t - hook_end
            idx = min(int(lt / item_dur), n - 1)
            item_lt = lt - idx * item_dur
            item = self._item_lines[idx]

            # Rank number (large, gold, translucent bg)
            rn = f"#{item['rank']}"
            al = int(255 * self._eo(item_lt / 0.5))
            rw = self._tw(rn, self.f_rank)
            draw.text(((self.W - rw) // 2, 450), rn, font=self.f_rank, fill=(*self.GOLD, al))

            # Name
            if item_lt > 0.3:
                na = int(240 * self._eo((item_lt - 0.3) / 0.5))
                nw = self._tw(item["name"], self.f_name)
                draw.text(((self.W - nw) // 2, 580), item["name"], font=self.f_name, fill=(*self.IVORY, na))

            # Card with description
            if item_lt > 0.8 and item["desc_lines"]:
                lh = self._th("가", self.f_body) + 10
                ch = 30 + len(item["desc_lines"]) * lh + 20
                cx, cy = 80, 670
                ca = int(200 * self._eo((item_lt - 0.8) / 0.5))
                for i in range(3):
                    draw.rounded_rectangle(
                        [(cx + i, cy + i), (cx + self.W - 160 - i, cy + ch - i)],
                        radius=8,
                        fill=(*self.PARCHMENT, ca - i * 5),
                    )
                draw.rounded_rectangle(
                    [(cx, cy), (cx + self.W - 160, cy + ch)], radius=8, outline=(*self.GOLD, ca // 3), width=1
                )
                for j, ln in enumerate(item["desc_lines"]):
                    la = int(220 * self._eo((item_lt - 1.0 - j * 0.1) / 0.4))
                    if la < 0:
                        la = 0
                    draw.text((cx + 25, cy + 20 + j * lh), ln, font=self.f_body, fill=(*self.IVORY, la))
        else:
            # CTA
            clt = t - cta_start
            ca = int(220 * self._eo(clt / 0.8))
            cw = self._tw(self.cta, self.f_body)
            draw.text(((self.W - cw) // 2, 800), self.cta, font=self.f_body, fill=(*self.GOLD, ca))

        comp = Image.alpha_composite(bg, ov)
        return np.array(comp.convert("RGB"))

    def generate(self, out="history_countdown.mp4"):
        clip = VideoClip(lambda t: self._render(t), duration=self.duration).with_fps(self.FPS)
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        clip.write_videofile(str(out), codec="libx264", preset="medium", bitrate="8000k", audio=False, logger="bar")
        print(f"\n✅ 생성 완료: {Path(out).resolve()}")
        return str(Path(out).resolve())


# ── Demo data ──
DEMO_FACT = {
    "title": "클레오파트라는 정말 절세미인이었을까?",
    "era": "기원전 69~30년",
    "region": "이집트 프톨레마이오스 왕조",
    "myth": (
        "할리우드 영화와 대중문화 속 클레오파트라는 "
        "압도적인 미모로 로마 장군들을 사로잡은 절세미인으로 묘사됩니다. "
        "엘리자베스 테일러의 이미지가 워낙 강렬했죠."
    ),
    "fact": (
        "동시대 주화의 초상을 보면, 클레오파트라의 외모는 "
        "매부리코에 돌출된 턱을 가진 평범한 용모였습니다. "
        "그녀의 진짜 무기는 외모가 아니라 7개 국어를 구사하는 "
        "지성과 뛰어난 정치적 화술이었습니다."
    ),
    "details": [
        "그리스어, 이집트어, 히브리어 등 최소 7개 언어 구사",
        "이집트어를 배운 최초의 프톨레마이오스 왕족",
        "카이사르와 안토니우스를 매료시킨 건 대화 능력",
    ],
    "lesson": "역사 속 인물의 이미지는 후대가 만들어낸 경우가 많습니다.",
    "duration": 38.0,
}

DEMO_COUNTDOWN = {
    "title": "인류 역사를 바꾼 발견 TOP 5",
    "items": [
        {"rank": 5, "name": "로제타 스톤", "desc": "이집트 상형문자 해독의 열쇠. 1799년 나폴레옹 원정대가 발견."},
        {"rank": 4, "name": "사해 문서", "desc": "2000년 전 성경 사본. 1947년 베두인 목동이 동굴에서 우연히 발견."},
        {"rank": 3, "name": "투탕카멘 무덤", "desc": "도굴되지 않은 유일한 파라오 무덤. 1922년 하워드 카터 발굴."},
        {"rank": 2, "name": "폼페이 유적", "desc": "화산재에 보존된 고대 로마 도시. 1748년 발굴 시작."},
        {"rank": 1, "name": "테라코타 병마용", "desc": "진시황의 8000개 병마용. 1974년 농민이 우물 파다 발견."},
    ],
    "duration": 40.0,
}


def main():
    pa = argparse.ArgumentParser(description="역사/고고학 쇼츠 생성기")
    pa.add_argument("--demo", choices=["fact", "countdown", "all"], default="fact")
    pa.add_argument("--out", type=str, default="output/history_fact_demo.mp4")
    a = pa.parse_args()
    if a.demo in ("fact", "all"):
        print("🏺 역사 반전 팩트 쇼츠 생성 중...")
        HistoryFactGenerator(**DEMO_FACT).generate(a.out if a.demo == "fact" else "output/demo_history_fact.mp4")
    if a.demo in ("countdown", "all"):
        print("🏆 역사 카운트다운 쇼츠 생성 중...")
        HistoryCountdownGenerator(**DEMO_COUNTDOWN).generate(
            a.out if a.demo == "countdown" else "output/demo_history_countdown.mp4"
        )


if __name__ == "__main__":
    raise SystemExit(main())
