#!/usr/bin/env python3
"""건강 DO vs DON'T 비교 쇼츠 생성기.

상하 분할 레이아웃 — 잘못된 습관(레드) vs 올바른 습관(그린).
헥사곤 패턴 배경 + 슬라이드 전환 + 감성 아웃트로.
"""
from __future__ import annotations
import argparse, math, os, random, warnings
from pathlib import Path
warnings.filterwarnings("ignore", category=DeprecationWarning, module="PIL")

import numpy as np
from PIL import Image, ImageDraw, ImageFont
try:
    from moviepy import VideoClip
except ImportError:
    from moviepy.editor import VideoClip  # type: ignore


class HealthDoVsDontGenerator:
    W, H = 1080, 1920
    FPS = 30
    MG = 60  # margin

    # Palette
    BG = (10, 26, 20)             # #0A1A14
    RED = (239, 68, 68)           # #EF4444
    GREEN = (52, 211, 153)        # #34D399
    WHITE = (240, 245, 240)
    DARK_RED = (50, 15, 15)
    DARK_GREEN = (12, 40, 30)
    CARD_BG_DONT = (239, 68, 68)  # with 10% opacity
    CARD_BG_DO = (52, 211, 153)
    DIVIDER = (30, 60, 45)

    def __init__(self, title: str,
                 pairs: list[dict],
                 category: str = "건강습관",
                 outro_text: str = "건강한 습관이\n인생을 바꿉니다",
                 disclaimer: str = "※ 의학적 조언이 아닌 정보 제공 목적입니다",
                 duration: float = 30.0):
        """
        Args:
            title: "아침 공복에 하면 안 되는 3가지"
            pairs: [{"dont_text": "...", "do_text": "..."}, ...]
            category: 카테고리 태그
        """
        self.title = title
        self.pairs = pairs[:5]
        self.category = category
        self.outro_text = outro_text
        self.disclaimer = disclaimer
        n = len(self.pairs)
        self.duration = max(20, min(45, duration))

        # Phase timing
        self.intro_dur = 2.5
        self.outro_dur = 3.5
        self.cards_dur = self.duration - self.intro_dur - self.outro_dur
        self.card_dur = self.cards_dur / max(1, n)
        self.trans_dur = 0.35

        self._load_fonts()
        self._preprocess_text()
        self._hex_pattern = self._make_hex_pattern()

        # Subtle particles
        random.seed(55)
        self._particles = [
            {"x": random.randint(0, self.W), "y": random.randint(0, self.H),
             "vy": random.uniform(-8, -2), "r": random.uniform(1, 2.5),
             "a": random.randint(15, 50), "ph": random.uniform(0, math.tau)}
            for _ in range(20)
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
        self.f_title = _l(sb, 56)
        self.f_label = _l(sb, 38)     # DO/DON'T label
        self.f_body = _l(sa, 36)      # card text
        self.f_vs = _l(sb, 32)        # VS badge
        self.f_tag = _l(sb, 28)       # category tag
        self.f_outro = _l(sb, 46)     # outro
        self.f_small = _l(sa, 22)     # disclaimer
        self.f_counter = _l(sb, 24)   # pair counter

    def _preprocess_text(self):
        tw = self.W - self.MG * 2 - 80
        self._title_lines = self._wrap(self.title, self.f_title, tw)
        self._pair_data = []
        for p in self.pairs:
            self._pair_data.append({
                "dont_lines": self._wrap(p.get("dont_text", ""), self.f_body, tw - 20),
                "do_lines": self._wrap(p.get("do_text", ""), self.f_body, tw - 20),
            })
        self._outro_lines = self.outro_text.split("\n")

    def _make_hex_pattern(self):
        """헥사곤 패턴 배경 (opacity 5%)."""
        pat = Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0))
        draw = ImageDraw.Draw(pat)
        hex_r = 40
        hex_h = hex_r * math.sqrt(3)
        cols = int(self.W / (hex_r * 1.5)) + 2
        rows = int(self.H / hex_h) + 2
        for row in range(rows):
            for col in range(cols):
                cx = col * hex_r * 1.5
                cy = row * hex_h + (hex_h / 2 if col % 2 else 0)
                pts = []
                for i in range(6):
                    angle = math.pi / 6 + i * math.pi / 3
                    px = cx + hex_r * math.cos(angle)
                    py = cy + hex_r * math.sin(angle)
                    pts.append((px, py))
                draw.polygon(pts, outline=(52, 211, 153, 12))  # 5% opacity
        return np.array(pat)

    @staticmethod
    def _wrap(text, font, mw):
        lines, cur = [], ""
        for seg in text.replace("\n", " ").split(" "):
            t = f"{cur} {seg}".strip() if cur else seg
            bb = font.getbbox(t)
            if bb[2] - bb[0] <= mw:
                cur = t
            else:
                if cur: lines.append(cur)
                cur = seg
        if cur: lines.append(cur)
        return lines

    def _tw(self, t, f):
        b = f.getbbox(t)
        return b[2] - b[0] if b else 0

    def _th(self, t, f):
        b = f.getbbox(t)
        return b[3] - b[1] if b else 0

    @staticmethod
    def _eo(t): return 1 - (1 - min(1, max(0, t))) ** 3
    @staticmethod
    def _ei(t): return min(1, max(0, t)) ** 2

    def _draw_particles(self, draw, t):
        for p in self._particles:
            x = p["x"]
            y = (p["y"] + p["vy"] * t) % self.H
            fl = 0.4 + 0.6 * math.sin(t * 1.5 + p["ph"])
            al = int(p["a"] * fl)
            r = p["r"]
            draw.ellipse([(x - r, y - r), (x + r, y + r)],
                         fill=(*self.GREEN, al))

    def _draw_card(self, draw, x, y, w, h, color, alpha=25):
        """반투명 색상 카드."""
        # BG fill
        draw.rounded_rectangle([(x, y), (x + w, y + h)],
                               radius=12, fill=(*color, alpha))
        # Left accent line
        draw.rounded_rectangle([(x, y + 8), (x + 4, y + h - 8)],
                               radius=2, fill=(*color, 180))
        # Border
        draw.rounded_rectangle([(x, y), (x + w, y + h)],
                               radius=12, outline=(*color, 40), width=1)

    # ── Phase renderers ──

    def _render_intro(self, draw, t):
        """인트로: 타이틀 + 카테고리 태그."""
        lh = self._th("가", self.f_title) + 14
        total_h = len(self._title_lines) * lh
        start_y = (self.H - total_h) // 2 - 40

        for i, line in enumerate(self._title_lines):
            prog = self._eo((t - 0.2 - i * 0.15) / 0.5)
            if prog <= 0: continue
            al = int(250 * prog)
            bounce = int(15 * (1 - prog))
            tw_ = self._tw(line, self.f_title)
            draw.text(((self.W - tw_) // 2, start_y + i * lh + bounce), line,
                      font=self.f_title, fill=(*self.WHITE, al))

        # Category tag
        if t > 1.0:
            ta = int(200 * self._eo((t - 1.0) / 0.5))
            tag = f"#{self.category}"
            tag_w = self._tw(tag, self.f_tag) + 24
            tx = (self.W - tag_w) // 2
            ty = start_y + total_h + 30
            draw.rounded_rectangle([(tx, ty), (tx + tag_w, ty + 38)],
                                   radius=6, fill=(*self.GREEN, 30), outline=(*self.GREEN, ta))
            draw.text((tx + 12, ty + 5), tag, font=self.f_tag, fill=(*self.GREEN, ta))

    def _render_pair(self, draw, idx, t_local):
        """DO/DON'T 카드 쌍."""
        if idx >= len(self._pair_data):
            return
        pair = self._pair_data[idx]

        # Exit animation
        if t_local > self.card_dur - self.trans_dur:
            exit_prog = self._eo((t_local - (self.card_dur - self.trans_dur)) / self.trans_dur)
            slide_x = int(-self.W * 0.3 * exit_prog)
            alpha_mult = 1 - exit_prog
        else:
            slide_x = 0
            alpha_mult = 1.0

        card_w = self.W - self.MG * 2
        card_h = 320
        card_x = self.MG + slide_x

        # ── DON'T card (상단 45%) ──
        dont_y = 400
        dont_prog = self._eo(t_local / 0.4)
        dont_slide = int(self.W * 0.15 * (1 - dont_prog))
        dont_alpha = int(255 * dont_prog * alpha_mult)

        if dont_prog > 0:
            dx = card_x + dont_slide
            self._draw_card(draw, dx, dont_y, card_w, card_h, self.RED, alpha=25)

            # ❌ DON'T label
            la = int(dont_alpha * 0.9)
            draw.text((dx + 20, dont_y + 15), "❌", font=self.f_label, fill=(*self.RED, la))
            draw.text((dx + 65, dont_y + 18), "DON'T", font=self.f_label, fill=(*self.RED, la))

            # Text
            lh = self._th("가", self.f_body) + 12
            for i, line in enumerate(pair["dont_lines"]):
                tla = int(dont_alpha * self._eo((t_local - 0.15 - i * 0.08) / 0.3))
                if tla < 0: tla = 0
                draw.text((dx + 25, dont_y + 70 + i * lh), line,
                          font=self.f_body, fill=(*self.WHITE, tla))

        # ── VS divider (중간) ──
        vs_y = dont_y + card_h + 15
        vs_zone_h = 60
        if t_local > 0.2:
            va = int(180 * self._eo((t_local - 0.2) / 0.3) * alpha_mult)
            # line
            draw.line([(self.MG + 30 + slide_x, vs_y + vs_zone_h // 2),
                       (self.W - self.MG - 30 + slide_x, vs_y + vs_zone_h // 2)],
                      fill=(*self.DIVIDER, va), width=1)
            # VS badge
            vs_w = 60
            vx = (self.W - vs_w) // 2 + slide_x
            draw.rounded_rectangle([(vx, vs_y + 10), (vx + vs_w, vs_y + vs_zone_h - 10)],
                                   radius=8, fill=(*self.BG, 255))
            draw.rounded_rectangle([(vx, vs_y + 10), (vx + vs_w, vs_y + vs_zone_h - 10)],
                                   radius=8, outline=(*self.GREEN, va // 2), width=1)
            vtw = self._tw("VS", self.f_vs)
            draw.text(((self.W - vtw) // 2 + slide_x, vs_y + 14), "VS",
                      font=self.f_vs, fill=(*self.WHITE, va))

        # ── DO card (하단 45%) ──
        do_y = vs_y + vs_zone_h + 15
        do_prog = self._eo((t_local - 0.5) / 0.4)  # 0.5초 지연
        do_slide = int(self.W * 0.15 * (1 - do_prog))

        if do_prog > 0:
            do_alpha = int(255 * do_prog * alpha_mult)
            dx = card_x + do_slide
            self._draw_card(draw, dx, do_y, card_w, card_h, self.GREEN, alpha=25)

            # ✅ DO label
            la = int(do_alpha * 0.9)
            draw.text((dx + 20, do_y + 15), "✅", font=self.f_label, fill=(*self.GREEN, la))
            draw.text((dx + 65, do_y + 18), "DO", font=self.f_label, fill=(*self.GREEN, la))

            # Text
            lh = self._th("가", self.f_body) + 12
            for i, line in enumerate(pair["do_lines"]):
                tla = int(do_alpha * self._eo((t_local - 0.7 - i * 0.08) / 0.3))
                if tla < 0: tla = 0
                draw.text((dx + 25, do_y + 70 + i * lh), line,
                          font=self.f_body, fill=(*self.WHITE, tla))

        # Pair counter
        ct = f"{idx + 1} / {len(self.pairs)}"
        cta = int(100 * alpha_mult)
        cw = self._tw(ct, self.f_counter)
        draw.text(((self.W - cw) // 2, self.H - 100), ct,
                  font=self.f_counter, fill=(*self.GREEN, cta))

    def _render_outro(self, draw, t_local):
        """아웃트로: 감성 텍스트 + 면책."""
        lh = 62
        total_h = len(self._outro_lines) * lh
        start_y = (self.H - total_h) // 2 - 40

        for i, line in enumerate(self._outro_lines):
            la = int(240 * self._eo((t_local - 0.3 - i * 0.3) / 0.6))
            if la < 0: la = 0
            tw_ = self._tw(line, self.f_outro)
            slide = int(12 * (1 - self._eo((t_local - 0.3 - i * 0.3) / 0.6)))
            draw.text(((self.W - tw_) // 2, start_y + i * lh + slide), line,
                      font=self.f_outro, fill=(*self.WHITE, la))

        # Disclaimer
        if t_local > 1.5:
            da = int(120 * self._eo((t_local - 1.5) / 0.5))
            dw = self._tw(self.disclaimer, self.f_small)
            draw.text(((self.W - dw) // 2, self.H - 150), self.disclaimer,
                      font=self.f_small, fill=(*self.WHITE, da))

        # Fade out
        if t_local > self.outro_dur - 1.0:
            fo = self._ei((t_local - (self.outro_dur - 1.0)) / 1.0)
            draw.rectangle([(0, 0), (self.W, self.H)], fill=(*self.BG, int(200 * fo)))

    # ── Main render ──
    def _render(self, t):
        cards_start = self.intro_dur
        outro_start = cards_start + self.cards_dur

        # BG
        bg = Image.new("RGBA", (self.W, self.H), (*self.BG, 255))

        # Hex pattern overlay
        hex_ov = Image.fromarray(self._hex_pattern, "RGBA")
        bg = Image.alpha_composite(bg, hex_ov)

        ov = Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0))
        draw = ImageDraw.Draw(ov)

        # Particles
        self._draw_particles(draw, t)

        if t < cards_start:
            self._render_intro(draw, t)
        elif t < outro_start:
            lt = t - cards_start
            idx = min(int(lt / self.card_dur), len(self.pairs) - 1)
            card_lt = lt - idx * self.card_dur
            self._render_pair(draw, idx, card_lt)
        else:
            lt = t - outro_start
            self._render_outro(draw, lt)

        comp = Image.alpha_composite(bg, ov)
        return np.array(comp.convert("RGB"))

    def generate(self, out="health_do_vs_dont.mp4"):
        clip = VideoClip(lambda t: self._render(t), duration=self.duration).with_fps(self.FPS)
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        clip.write_videofile(str(out), codec="libx264", preset="medium",
                             bitrate="8000k", audio=False, logger="bar")
        sz = Path(out).stat().st_size / (1024 * 1024)
        print(f"\n✅ 생성 완료: {Path(out).resolve()}")
        print(f"   크기: {self.W}×{self.H} | 길이: {self.duration:.0f}초 | 파일: {sz:.1f}MB")
        return str(Path(out).resolve())


# ── Demo data ──
DEMO_DATA = {
    "title": "아침 공복에\n하면 안 되는 3가지",
    "category": "아침습관",
    "pairs": [
        {
            "dont_text": "일어나자마자 커피를 마신다. 빈속에 카페인은 위산 분비를 과도하게 자극합니다.",
            "do_text": "먼저 물 한 잔을 마신다. 밤새 탈수된 몸에 수분 보충이 최우선입니다.",
        },
        {
            "dont_text": "단 음료나 주스로 하루를 시작한다. 빈속의 당분은 혈당 스파이크를 유발합니다.",
            "do_text": "단백질 위주 아침식사를 한다. 계란, 그릭요거트 등으로 혈당을 안정시킵니다.",
        },
        {
            "dont_text": "격한 운동을 바로 시작한다. 근육이 경직된 상태에서 부상 위험이 높습니다.",
            "do_text": "가벼운 스트레칭으로 몸을 깨운다. 5~10분 워밍업이 하루 컨디션을 좌우합니다.",
        },
    ],
    "duration": 30.0,
}


def main():
    pa = argparse.ArgumentParser(description="건강 DO vs DON'T 비교 쇼츠")
    pa.add_argument("--demo", action="store_true")
    pa.add_argument("--out", default="output/demo_health_dodont.mp4")
    a = pa.parse_args()

    if a.demo:
        print("💊 건강 DO vs DON'T 쇼츠 생성 중...")
        gen = HealthDoVsDontGenerator(**DEMO_DATA)
        gen.generate(a.out)
    else:
        print("--demo 플래그로 데모를 생성하세요")

if __name__ == "__main__":
    raise SystemExit(main())
