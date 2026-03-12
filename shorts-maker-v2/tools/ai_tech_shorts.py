#!/usr/bin/env python3
"""AI 뉴스 브레이킹 쇼츠 생성기.

사이버펑크 HUD 스타일의 AI/기술 속보 숏폼 영상.
4-Phase: 충격 통계/헤드라인 → 핵심 포인트 → 임팩트 분석 → CTA.
"""
from __future__ import annotations
import argparse, math, os, random, warnings
from pathlib import Path
from typing import Any
warnings.filterwarnings("ignore", category=DeprecationWarning, module="PIL")

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
try:
    from moviepy import VideoClip
except ImportError:
    from moviepy.editor import VideoClip  # type: ignore


class AINewsShortsGenerator:
    W, H = 1080, 1920
    FPS = 30
    MG = 70  # margin

    # Cyberpunk palette
    BG_DARK = (10, 22, 40)       # #0A1628
    CYAN = (0, 240, 255)         # #00F0FF
    MAGENTA = (255, 0, 170)      # #FF00AA
    MATRIX_GREEN = (57, 255, 20) # #39FF14
    ICE_BLUE = (224, 247, 255)   # #E0F7FF
    AMBER = (245, 158, 11)       # #F59E0B
    WHITE = (255, 255, 255)

    # Phase timings
    PH1_END = 5.0   # Hook
    PH2_END = 18.0  # Key points
    PH3_END = 28.0  # Impact
    PH4_END = 35.0  # CTA

    def __init__(self, headline: str,
                 stat: str = "",
                 key_points: list[str] | None = None,
                 impact: str = "",
                 source: str = "",
                 cta: str = "구독하고 AI 트렌드를 놓치지 마세요!",
                 image_path: str | None = None,
                 duration: float = 35.0):
        self.headline = headline
        self.stat = stat or headline
        self.key_points = (key_points or [])[:5]
        self.impact = impact
        self.source = source
        self.cta = cta
        self.duration = max(30, min(50, duration))

        # Recalc phase boundaries
        r = self.duration / 35.0
        self.PH1_END = 5.0
        self.PH2_END = 5.0 + 13.0 * r
        self.PH3_END = self.PH2_END + 10.0 * r
        self.PH4_END = self.duration

        self._load_fonts()
        self._bg_img = self._load_bg(image_path)

        # Preprocess text
        tw = self.W - self.MG * 2 - 30
        self._headline_lines = self._wrap(headline, self.f_title, tw)
        self._impact_lines = self._wrap(impact, self.f_body, tw - 40) if impact else []
        self._kp_lines = [self._wrap(kp, self.f_body, tw - 80) for kp in self.key_points]

        # Grid / scan line particles
        random.seed(42)
        self._particles = [
            {"x": random.randint(0, self.W), "y": random.randint(0, self.H),
             "vx": random.uniform(-15, 15), "vy": random.uniform(-30, -5),
             "r": random.uniform(1, 2.5), "a": random.randint(30, 80),
             "ph": random.uniform(0, math.tau)}
            for _ in range(18)
        ]

    def _load_fonts(self):
        dirs = [Path("C:/Windows/Fonts"),
                Path(os.path.expanduser("~/AppData/Local/Microsoft/Windows/Fonts"))]
        def _f(ns, fb="malgun.ttf"):
            for d in dirs:
                for n in ns:
                    if (d / n).exists(): return str(d / n)
            for d in dirs:
                if (d / fb).exists(): return str(d / fb)
            return ""
        sb = _f(["NanumGothicBold.ttf", "malgunbd.ttf"])
        sa = _f(["NanumGothic.ttf", "malgun.ttf"])
        def _l(p, s):
            return ImageFont.truetype(p, s) if p else ImageFont.load_default(s)
        self.f_title = _l(sb, 58)
        self.f_stat = _l(sb, 72)
        self.f_body = _l(sa, 34)
        self.f_big = _l(sb, 48)
        self.f_small = _l(sa, 28)
        self.f_badge = _l(sb, 26)

    def _load_bg(self, path):
        if path and Path(path).exists():
            img = Image.open(path).convert("RGB")
            sc = max(self.W / img.width, self.H / img.height)
            nw, nh = int(img.width * sc), int(img.height * sc)
            img = img.resize((nw, nh), Image.LANCZOS)
            l_ = (nw - self.W) // 2; t_ = (nh - self.H) // 2
            img = img.crop((l_, t_, l_ + self.W, t_ + self.H))
            # Cool blue tint
            arr = np.array(img, dtype=np.float32)
            arr[:, :, 0] *= 0.5; arr[:, :, 1] *= 0.6; arr[:, :, 2] *= 0.9
            return arr.astype(np.uint8)
        # Fallback: dark gradient with grid
        arr = np.zeros((self.H, self.W, 3), dtype=np.uint8)
        for y in range(self.H):
            r_ = y / self.H
            arr[y, :] = [int(10 + 5 * r_), int(22 - 8 * r_), int(40 - 10 * r_)]
        return arr

    @staticmethod
    def _wrap(text, font, mw):
        lines, cur = [], ""
        for seg in text.replace("\n", " \n ").split(" "):
            if seg == "\n":
                if cur: lines.append(cur)
                cur = ""; continue
            t = f"{cur} {seg}".strip() if cur else seg
            if font.getbbox(t)[2] - font.getbbox(t)[0] <= mw:
                cur = t
            else:
                if cur: lines.append(cur)
                cur = seg
        if cur: lines.append(cur)
        return lines

    def _tw(self, t, f): b = f.getbbox(t); return b[2] - b[0]
    def _th(self, t, f): b = f.getbbox(t); return b[3] - b[1]

    @staticmethod
    def _eo(t): return 1 - (1 - min(1, max(0, t))) ** 3
    @staticmethod
    def _ei(t): return min(1, max(0, t)) ** 2

    # ── Drawing helpers ──
    def _draw_grid(self, draw, t):
        """HUD 그리드 라인."""
        sp = 120
        a = int(15 + 8 * math.sin(t * 0.5))
        for x in range(0, self.W, sp):
            draw.line([(x, 0), (x, self.H)], fill=(0, 100, 150, a), width=1)
        for y in range(0, self.H, sp):
            draw.line([(0, y), (self.W, y)], fill=(0, 100, 150, a), width=1)

    def _draw_scanline(self, draw, t):
        """움직이는 스캔라인."""
        y_pos = int((t * 200) % (self.H + 60)) - 30
        for dy in range(-15, 16):
            al = max(0, int(40 * (1 - abs(dy) / 15)))
            draw.line([(0, y_pos + dy), (self.W, y_pos + dy)],
                      fill=(0, 200, 255, al), width=1)

    def _draw_particles(self, draw, t):
        for p in self._particles:
            x = (p["x"] + p["vx"] * t) % self.W
            y = (p["y"] + p["vy"] * t) % self.H
            fl = 0.4 + 0.6 * math.sin(t * 1.5 + p["ph"])
            al = int(p["a"] * fl)
            draw.ellipse([(x - p["r"], y - p["r"]), (x + p["r"], y + p["r"])],
                         fill=(0, 200, 255, al))

    def _draw_hud_badge(self, draw, x, y, text, color=None):
        """HUD 스타일 배지."""
        c = color or self.CYAN
        tw_ = self._tw(text, self.f_badge) + 24
        draw.rounded_rectangle([(x, y), (x + tw_, y + 36)],
                               radius=4, fill=(*c, 40), outline=(*c, 120), width=1)
        draw.text((x + 12, y + 5), text, font=self.f_badge, fill=(*c, 220))
        return tw_

    def _draw_card(self, draw, x, y, w, h, alpha=200):
        for i in range(6):
            draw.rounded_rectangle(
                [(x + i, y + i), (x + w - i, y + h - i)],
                radius=10,
                fill=(*self.BG_DARK, alpha - i * 8))
        # Border glow
        draw.rounded_rectangle([(x, y), (x + w, y + h)],
                               radius=10, outline=(*self.CYAN, 60), width=1)

    # ── Phase renderers ──
    def _ph1(self, draw, t):
        """충격 통계 / 헤드라인 (0~5초)."""
        # "BREAKING" badge
        if t > 0.3:
            ba = int(255 * self._eo((t - 0.3) / 0.5))
            # Pulsing effect
            pulse = 0.8 + 0.2 * math.sin(t * 6)
            b_al = int(ba * pulse)
            bw = self._draw_hud_badge(draw, self.MG, 600, "⚡ BREAKING", self.MAGENTA)

        # Stat / headline with typewriter
        if t > 0.8:
            # Large stat text
            stat_shown = self.stat[:int((t - 0.8) / 0.04)]
            if stat_shown:
                sta = int(255 * min(1, (t - 0.8) / 1.0))
                sw = self._tw(stat_shown, self.f_stat)
                # Glow behind
                for dx, dy, ga in [(0, 0, sta), (-1, -1, sta // 3), (1, 1, sta // 3)]:
                    draw.text(((self.W - sw) // 2 + dx, 680 + dy), stat_shown,
                              font=self.f_stat, fill=(*self.CYAN, ga))

        # Headline below
        if t > 2.5:
            lh = self._th("가", self.f_title) + 14
            for i, line in enumerate(self._headline_lines):
                la = int(230 * self._eo((t - 2.5 - i * 0.2) / 0.6))
                tw_ = self._tw(line, self.f_title)
                draw.text(((self.W - tw_) // 2, 820 + i * lh), line,
                          font=self.f_title, fill=(*self.ICE_BLUE, la))

    def _ph2(self, draw, t):
        """핵심 포인트 (PH1→PH2)."""
        lt = t - self.PH1_END
        dur = self.PH2_END - self.PH1_END

        # Section label
        if lt > 0.3:
            la = int(200 * self._eo((lt - 0.3) / 0.5))
            self._draw_hud_badge(draw, self.MG, 380, "📊 핵심 포인트", self.CYAN)

        # Key point cards
        lh = self._th("가", self.f_body) + 12
        card_gap = max(1.5, dur / max(1, len(self.key_points) + 1))
        for i, kp in enumerate(self.key_points):
            pt = lt - 0.8 - i * card_gap * 0.5
            if pt < 0: continue
            prog = self._eo(pt / 0.6)
            alpha = int(240 * prog)
            slide_x = int(30 * (1 - prog))

            lines = self._kp_lines[i]
            ch = 35 + len(lines) * lh + 15
            cy = 440 + i * (ch + 30)
            cx = self.MG + slide_x

            # Card
            if alpha > 10:
                self._draw_card(draw, cx, cy, self.W - self.MG * 2, ch, int(alpha * 0.8))

            # Number badge
            num_text = f"0{i + 1}"
            draw.text((cx + 18, cy + 8), num_text,
                      font=self.f_badge, fill=(*self.CYAN, alpha))

            # Point text
            for j, ln in enumerate(lines):
                draw.text((cx + 70, cy + 10 + j * lh), ln,
                          font=self.f_body, fill=(*self.ICE_BLUE, alpha))

    def _ph3(self, draw, t):
        """임팩트 분석 (PH2→PH3)."""
        lt = t - self.PH2_END
        dur = self.PH3_END - self.PH2_END

        # "왜 중요한가?" header
        if lt < 3.0:
            ta = int(255 * self._eo(lt / 0.8))
            if lt > 2.0:
                ta = int(ta * (1 - self._eo((lt - 2.0) / 1.0)))
            txt = "⚠️ 왜 중요한가?"
            tw_ = self._tw(txt, self.f_big)
            draw.text(((self.W - tw_) // 2, self.H // 2 - 50), txt,
                      font=self.f_big, fill=(*self.AMBER, ta))

        # Impact card
        if lt > 2.0 and self._impact_lines:
            ca = int(220 * self._eo((lt - 2.0) / 1.0))
            lh = self._th("가", self.f_body) + 14
            card_h = 60 + len(self._impact_lines) * lh + 30
            cx, cy = 60, 600
            self._draw_card(draw, cx, cy, self.W - 120, card_h, ca)

            for i, line in enumerate(self._impact_lines):
                la = int(230 * self._eo((lt - 2.5 - i * 0.15) / 0.5))
                if la < 0: la = 0
                draw.text((cx + 30, cy + 35 + i * lh), line,
                          font=self.f_body, fill=(*self.ICE_BLUE, la))

        # Source
        if self.source and lt > 3.5:
            sa = int(120 * self._eo((lt - 3.5) / 0.5))
            stxt = f"출처: {self.source}"
            sw = self._tw(stxt, self.f_small)
            draw.text(((self.W - sw) // 2, 1300), stxt,
                      font=self.f_small, fill=(*self.WHITE, sa))

    def _ph4(self, draw, t):
        """CTA (PH3→End)."""
        lt = t - self.PH3_END
        dur = self.PH4_END - self.PH3_END

        # Channel badge
        if lt > 0.5:
            ba = int(200 * self._eo((lt - 0.5) / 0.8))
            self._draw_hud_badge(draw, (self.W - 200) // 2, 700, "🤖 퓨처 시냅스", self.CYAN)

        # CTA text
        if lt > 1.0:
            ca = int(255 * self._eo((lt - 1.0) / 0.8))
            if lt > dur - 1.5:
                ca = int(ca * (1 - self._ei((lt - (dur - 1.5)) / 1.5)))
            cta_w = self._tw(self.cta, self.f_big)
            # Glow
            for dx, dy, ga in [(0, 0, ca), (-1, 0, ca // 4), (1, 0, ca // 4)]:
                draw.text(((self.W - cta_w) // 2 + dx, 800 + dy), self.cta,
                          font=self.f_big, fill=(*self.CYAN, ga))

        # Subscribe prompt
        if lt > 2.0:
            pa = int(180 * self._eo((lt - 2.0) / 0.6))
            if lt > dur - 1.5:
                pa = int(pa * (1 - self._ei((lt - (dur - 1.5)) / 1.5)))
            ptxt = "🔔 알림 설정하고 가장 빠르게 만나세요"
            pw = self._tw(ptxt, self.f_small)
            draw.text(((self.W - pw) // 2, 880), ptxt,
                      font=self.f_small, fill=(*self.ICE_BLUE, pa))

    # ── Main render ──
    def _render(self, t):
        # Background
        if t < self.PH1_END:
            br = self._eo(t / 2.0) * 0.35
        elif t < self.PH2_END:
            br = 0.3
        elif t < self.PH3_END:
            br = 0.25
        else:
            lt_ = t - self.PH3_END
            dur4 = self.PH4_END - self.PH3_END
            br = 0.25 * (1 - self._ei(lt_ / dur4) * 0.4)

        arr = (self._bg_img.astype(np.float32) * br).clip(0, 255).astype(np.uint8)
        bg = Image.fromarray(arr, "RGB").convert("RGBA")
        ov = Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0))
        draw = ImageDraw.Draw(ov)

        # HUD effects
        self._draw_grid(draw, t)
        self._draw_scanline(draw, t)
        self._draw_particles(draw, t)

        # Phase content
        if t < self.PH1_END:
            self._ph1(draw, t)
        elif t < self.PH2_END:
            self._ph2(draw, t)
        elif t < self.PH3_END:
            self._ph3(draw, t)
        else:
            self._ph4(draw, t)

        # Corner HUD elements
        ts = f"{t:.1f}s"
        draw.text((self.W - 120, 60), ts, font=self.f_small, fill=(*self.CYAN, 60))
        # Top-left corner lines
        draw.line([(20, 30), (70, 30)], fill=(*self.CYAN, 80), width=2)
        draw.line([(20, 30), (20, 80)], fill=(*self.CYAN, 80), width=2)
        # Bottom-right corner lines
        draw.line([(self.W - 70, self.H - 30), (self.W - 20, self.H - 30)],
                  fill=(*self.CYAN, 80), width=2)
        draw.line([(self.W - 20, self.H - 80), (self.W - 20, self.H - 30)],
                  fill=(*self.CYAN, 80), width=2)

        comp = Image.alpha_composite(bg, ov)
        return np.array(comp.convert("RGB"))

    def generate(self, out="ai_news.mp4"):
        clip = VideoClip(lambda t: self._render(t), duration=self.duration).with_fps(self.FPS)
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        clip.write_videofile(str(out), codec="libx264", preset="medium",
                             bitrate="8000k", audio=False, logger="bar")
        print(f"\n✅ 생성 완료: {Path(out).resolve()}")
        print(f"   크기: {self.W}×{self.H} | 길이: {self.duration:.0f}초")
        return str(Path(out).resolve())


class TechVSShortsGenerator:
    """기술 비교 (A vs B) 쇼츠 생성기.

    좌우 분할 화면으로 두 기술을 시각적으로 비교.
    """
    W, H = 1080, 1920
    FPS = 30

    CYAN = (0, 240, 255)
    MAGENTA = (255, 0, 170)
    ICE_BLUE = (224, 247, 255)
    BG_DARK = (10, 22, 40)

    def __init__(self, tech_a: str, tech_b: str,
                 points_a: list[str] | None = None,
                 points_b: list[str] | None = None,
                 verdict: str = "",
                 duration: float = 35.0):
        self.tech_a = tech_a
        self.tech_b = tech_b
        self.points_a = (points_a or [])[:4]
        self.points_b = (points_b or [])[:4]
        self.verdict = verdict
        self.duration = duration

        self._load_fonts()

        tw = self.W // 2 - 60
        self._pa_lines = [self._wrap(p, self.f_body, tw) for p in self.points_a]
        self._pb_lines = [self._wrap(p, self.f_body, tw) for p in self.points_b]
        self._verdict_lines = self._wrap(verdict, self.f_body, self.W - 160) if verdict else []

        random.seed(77)
        self._particles = [
            {"x": random.randint(0, self.W), "y": random.randint(0, self.H),
             "vx": random.uniform(-10, 10), "vy": random.uniform(-20, -5),
             "r": random.uniform(1, 2), "a": random.randint(20, 60),
             "ph": random.uniform(0, math.tau)}
            for _ in range(14)
        ]

    def _load_fonts(self):
        dirs = [Path("C:/Windows/Fonts"),
                Path(os.path.expanduser("~/AppData/Local/Microsoft/Windows/Fonts"))]
        def _f(ns, fb="malgun.ttf"):
            for d in dirs:
                for n in ns:
                    if (d / n).exists(): return str(d / n)
            for d in dirs:
                if (d / fb).exists(): return str(d / fb)
            return ""
        sb = _f(["NanumGothicBold.ttf", "malgunbd.ttf"])
        sa = _f(["NanumGothic.ttf", "malgun.ttf"])
        def _l(p, s):
            return ImageFont.truetype(p, s) if p else ImageFont.load_default(s)
        self.f_title = _l(sb, 52)
        self.f_body = _l(sa, 32)
        self.f_big = _l(sb, 44)
        self.f_small = _l(sa, 26)
        self.f_badge = _l(sb, 28)
        self.f_vs = _l(sb, 80)

    @staticmethod
    def _wrap(text, font, mw):
        lines, cur = [], ""
        for seg in text.split(" "):
            t = f"{cur} {seg}".strip() if cur else seg
            if font.getbbox(t)[2] - font.getbbox(t)[0] <= mw:
                cur = t
            else:
                if cur: lines.append(cur)
                cur = seg
        if cur: lines.append(cur)
        return lines

    def _tw(self, t, f): b = f.getbbox(t); return b[2] - b[0]
    def _th(self, t, f): b = f.getbbox(t); return b[3] - b[1]
    @staticmethod
    def _eo(t): return 1 - (1 - min(1, max(0, t))) ** 3

    def _render(self, t):
        # Dark bg
        arr = np.zeros((self.H, self.W, 3), dtype=np.uint8)
        for y in range(self.H):
            arr[y, :] = [10, 22, 40]
        bg = Image.fromarray(arr, "RGB").convert("RGBA")
        ov = Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0))
        draw = ImageDraw.Draw(ov)

        # Grid
        sp = 120
        ga = int(12 + 5 * math.sin(t * 0.5))
        for x in range(0, self.W, sp):
            draw.line([(x, 0), (x, self.H)], fill=(0, 80, 120, ga), width=1)
        for y_ in range(0, self.H, sp):
            draw.line([(0, y_), (self.W, y_)], fill=(0, 80, 120, ga), width=1)

        # Particles
        for p in self._particles:
            x = (p["x"] + p["vx"] * t) % self.W
            y = (p["y"] + p["vy"] * t) % self.H
            fl = 0.4 + 0.6 * math.sin(t * 1.5 + p["ph"])
            al = int(p["a"] * fl)
            draw.ellipse([(x - p["r"], y - p["r"]), (x + p["r"], y + p["r"])],
                         fill=(0, 180, 240, al))

        mid = self.W // 2

        # Phase 1: VS intro (0~4s)
        if t < 4:
            a_a = int(255 * self._eo(t / 1.0))
            b_a = int(255 * self._eo((t - 0.5) / 1.0))
            # Left: Tech A
            aw = self._tw(self.tech_a, self.f_title)
            draw.text(((mid - aw) // 2, 750), self.tech_a,
                      font=self.f_title, fill=(*self.CYAN, a_a))
            # Right: Tech B
            bw = self._tw(self.tech_b, self.f_title)
            draw.text((mid + (mid - bw) // 2, 750), self.tech_b,
                      font=self.f_title, fill=(*self.MAGENTA, b_a))
            # VS
            if t > 1.0:
                va = int(255 * self._eo((t - 1.0) / 0.5))
                vw = self._tw("VS", self.f_vs)
                draw.text(((self.W - vw) // 2, 720), "VS",
                          font=self.f_vs, fill=(255, 255, 255, va))
            # Divider
            draw.line([(mid, 700), (mid, 850)], fill=(*self.CYAN, 100), width=2)

        # Phase 2: Points (4~25s)
        elif t < self.duration - 8:
            lt = t - 4
            # Divider line
            draw.line([(mid, 300), (mid, 1500)], fill=(255, 255, 255, 40), width=2)
            # Headers
            aw = self._tw(self.tech_a, self.f_title)
            draw.text(((mid - aw) // 2, 320), self.tech_a,
                      font=self.f_title, fill=(*self.CYAN, 220))
            bw = self._tw(self.tech_b, self.f_title)
            draw.text((mid + (mid - bw) // 2, 320), self.tech_b,
                      font=self.f_title, fill=(*self.MAGENTA, 220))

            lh = self._th("가", self.f_body) + 10
            # A points
            for i, lines in enumerate(self._pa_lines):
                pt = lt - i * 2.0
                if pt < 0: continue
                al = int(220 * self._eo(pt / 0.5))
                for j, ln in enumerate(lines):
                    draw.text((40, 430 + i * 140 + j * lh), ln,
                              font=self.f_body, fill=(*self.ICE_BLUE, al))
            # B points
            for i, lines in enumerate(self._pb_lines):
                pt = lt - 1.0 - i * 2.0
                if pt < 0: continue
                al = int(220 * self._eo(pt / 0.5))
                for j, ln in enumerate(lines):
                    draw.text((mid + 30, 430 + i * 140 + j * lh), ln,
                              font=self.f_body, fill=(*self.ICE_BLUE, al))

        # Phase 3: Verdict (last 8s)
        else:
            lt = t - (self.duration - 8)
            if lt < 3:
                ta = int(255 * self._eo(lt / 0.8))
                txt = "🏆 결론"
                tw_ = self._tw(txt, self.f_big)
                draw.text(((self.W - tw_) // 2, 650), txt,
                          font=self.f_big, fill=(*self.CYAN, ta))
            if lt > 1.5 and self._verdict_lines:
                lh = self._th("가", self.f_body) + 14
                for i, ln in enumerate(self._verdict_lines):
                    la = int(230 * self._eo((lt - 1.5 - i * 0.2) / 0.5))
                    if la < 0: la = 0
                    tw_ = self._tw(ln, self.f_body)
                    draw.text(((self.W - tw_) // 2, 750 + i * lh), ln,
                              font=self.f_body, fill=(*self.ICE_BLUE, la))

        comp = Image.alpha_composite(bg, ov)
        return np.array(comp.convert("RGB"))

    def generate(self, out="tech_vs.mp4"):
        clip = VideoClip(lambda t: self._render(t), duration=self.duration).with_fps(self.FPS)
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        clip.write_videofile(str(out), codec="libx264", preset="medium",
                             bitrate="8000k", audio=False, logger="bar")
        print(f"\n✅ 생성 완료: {Path(out).resolve()}")
        return str(Path(out).resolve())


# ── Demo data ──
DEMO_NEWS = {
    "headline": "GPT-5 출시가 확정됐습니다",
    "stat": "2026년 1분기 출시 확정",
    "key_points": [
        "멀티모달 통합: 텍스트·이미지·비디오·코드를 하나의 모델로 처리",
        "1M 토큰 컨텍스트 윈도우로 책 전체를 한 번에 분석 가능",
        "에이전트 모드: 웹 브라우징부터 코딩까지 자율 수행",
        "할루시네이션 90% 감소 — 팩트체크 내재화",
    ],
    "impact": (
        "GPT-5는 단순한 챗봇을 넘어 '디지털 동료'로 진화합니다. "
        "SWE 벤치마크 75% → 92% 달성으로 주니어 개발자 수준의 코딩이 가능하며, "
        "기업용 API 가격은 오히려 40% 인하될 예정입니다."
    ),
    "source": "OpenAI 공식 블로그 (2026.03)",
    "duration": 35.0,
}

DEMO_VS = {
    "tech_a": "Claude 4",
    "tech_b": "GPT-5",
    "points_a": [
        "긴 컨텍스트에 강함 (200K 토큰)",
        "안전성·윤리 최우선 설계",
        "코드 리뷰에 특화된 추론",
        "가격 대비 성능 우위",
    ],
    "points_b": [
        "멀티모달 통합 (영상·음성)",
        "에이전트 자율 실행 가능",
        "더 넓은 플러그인 생태계",
        "실시간 웹 검색 내장",
    ],
    "verdict": "코드 품질이 중요하면 Claude 4, 범용 AI 비서가 필요하면 GPT-5가 유리합니다.",
    "duration": 35.0,
}


def main():
    pa = argparse.ArgumentParser(description="AI/기술 쇼츠 생성기")
    pa.add_argument("--demo", choices=["news", "vs", "all"], default="news")
    pa.add_argument("--out", type=str, default="output/ai_tech_demo.mp4")
    a = pa.parse_args()
    if a.demo in ("news", "all"):
        print("🤖 AI 뉴스 브레이킹 쇼츠 생성 중...")
        AINewsShortsGenerator(**DEMO_NEWS).generate(
            a.out if a.demo == "news" else "output/demo_ai_news.mp4"
        )
    if a.demo in ("vs", "all"):
        print("⚔️ 기술 비교 쇼츠 생성 중...")
        TechVSShortsGenerator(**DEMO_VS).generate(
            a.out if a.demo == "vs" else "output/demo_tech_vs.mp4"
        )

if __name__ == "__main__":
    raise SystemExit(main())
