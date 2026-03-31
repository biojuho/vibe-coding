#!/usr/bin/env python3
"""역사 미스터리 서스펜스 쇼츠 생성기.

어둡고 긴장감 있는 다큐 스타일.
4-Phase: 미스터리 제시 → 배경 설명 → 미스터리 포인트 → 가설/결론.
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


class HistoryMysteryGenerator:
    W, H = 1080, 1920
    FPS = 30
    MG = 80  # margin

    # Color palette
    CREAM = (232, 220, 200)
    GOLD = (212, 165, 116)
    CRIMSON = (196, 30, 58)
    AMBER = (245, 158, 11)
    CARD_BG = (44, 34, 16)
    BG_DARK = (12, 10, 6)

    # Phase timings (seconds) — adjusted at init based on content
    PH1_END = 5.0
    PH2_END = 15.0
    PH3_END = 30.0
    PH4_END = 45.0

    def __init__(
        self,
        title: str,
        background_story: str,
        mystery_points: list[str],
        hypothesis: str,
        cta: str = "당신은 어떻게 생각하나요?",
        image_path: str | None = None,
        duration: float = 45.0,
    ):
        self.title = title
        self.bg_story = background_story
        self.mysteries = mystery_points[:4]  # max 4
        self.hypothesis = hypothesis
        self.cta = cta
        self.duration = max(35, min(55, duration))

        # Recalc phase boundaries based on duration
        r = self.duration / 45.0
        self.PH1_END = 5.0
        self.PH2_END = 5.0 + 10.0 * r
        self.PH3_END = self.PH2_END + 15.0 * r
        self.PH4_END = self.duration

        self._load_fonts()
        self._bg_img = self._load_bg(image_path)
        self._vignette = self._mk_vignette()

        # Preprocess text
        tw = self.W - self.MG * 2 - 40
        self._story_lines = self._wrap(background_story, self.f_body, tw)
        self._hypo_lines = self._wrap(hypothesis, self.f_body, tw)
        self._myst_lines = [self._wrap(m, self.f_body, tw - 50) for m in self.mysteries]
        self._title_lines = self._wrap(title, self.f_title, self.W - self.MG * 2)

        # Particles (dark dust/embers)
        random.seed(13)
        self._embers = [
            {
                "x": random.randint(0, self.W),
                "y": random.randint(0, self.H),
                "r": random.uniform(1, 3),
                "vy": random.uniform(-20, -8),
                "vx": random.uniform(-5, 5),
                "a": random.randint(40, 120),
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

        se = _f(["NanumMyeongjo.ttf", "NanumMyeongjoBold.ttf", "batang.ttc"])
        sb = _f(["NanumGothicBold.ttf", "malgunbd.ttf"])
        sa = _f(["NanumGothic.ttf", "malgun.ttf"])

        def _l(p, s):
            return ImageFont.truetype(p, s) if p else ImageFont.load_default(s)

        self.f_title = _l(se, 62)
        self.f_hook = _l(sa, 40)
        self.f_body = _l(sa, 36)
        self.f_big = _l(sb, 54)
        self.f_small = _l(sa, 30)
        self.f_qmark = _l(sb, 72)

    def _load_bg(self, path):
        if path and Path(path).exists():
            img = Image.open(path).convert("RGB")
            sc = max(self.W / img.width, self.H / img.height)
            nw, nh = int(img.width * sc), int(img.height * sc)
            img = img.resize((nw, nh), Image.LANCZOS)
            l = (nw - self.W) // 2
            t = (nh - self.H) // 2
            img = img.crop((l, t, l + self.W, t + self.H))
            # Apply sepia tint
            arr = np.array(img, dtype=np.float32)
            gray = 0.299 * arr[:, :, 0] + 0.587 * arr[:, :, 1] + 0.114 * arr[:, :, 2]
            arr[:, :, 0] = np.clip(gray * 1.1, 0, 255)
            arr[:, :, 1] = np.clip(gray * 0.9, 0, 255)
            arr[:, :, 2] = np.clip(gray * 0.7, 0, 255)
            return arr.astype(np.uint8)
        # Fallback: dark gradient
        arr = np.zeros((self.H, self.W, 3), dtype=np.uint8)
        for y in range(self.H):
            r = y / self.H
            arr[y, :] = [int(20 * (1 - r * 0.5)), int(15 * (1 - r * 0.5)), int(8 * (1 - r * 0.5))]
        return arr

    def _mk_vignette(self):
        ys = np.arange(self.H, dtype=np.float32)
        xs = np.arange(self.W, dtype=np.float32)
        yy, xx = np.meshgrid(ys, xs, indexing="ij")
        d = np.sqrt((xx - self.W / 2) ** 2 + (yy - self.H / 2) ** 2)
        d = d / math.hypot(self.W / 2, self.H / 2)
        al = np.where(d > 0.4, np.clip((d - 0.4) / 0.6 * 220, 0, 220), 0).astype(np.uint8)
        a = np.zeros((self.H, self.W, 4), dtype=np.uint8)
        a[:, :, 3] = al
        return Image.fromarray(a, "RGBA")

    # ── Helpers ──
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
        return 1 - (1 - min(1, max(0, t))) ** 3  # ease-out

    @staticmethod
    def _ei(t):
        return min(1, max(0, t)) ** 2  # ease-in

    # ── Drawing helpers ──
    def _draw_embers(self, draw, t):
        for p in self._embers:
            x = (p["x"] + p["vx"] * t + math.sin(t * 0.7 + p["ph"]) * 12) % self.W
            y = (p["y"] + p["vy"] * t) % self.H
            fl = 0.4 + 0.6 * math.sin(t * 2 + p["ph"])
            al = int(p["a"] * fl)
            r = p["r"]
            # warm ember color
            draw.ellipse([(x - r, y - r), (x + r, y + r)], fill=(200, 140, 60, al))

    def _draw_card(self, draw, x, y, w, h, alpha=217):
        """양피지 느낌 카드."""
        for i in range(8):
            draw.rounded_rectangle(
                [(x + i, y + i), (x + w - i, y + h - i)], radius=12, fill=(*self.CARD_BG, alpha - i * 5)
            )

    def _typewriter(self, text, t, speed=0.04):
        """타자기 효과: t초 기준 보여줄 글자 수."""
        n = int(t / speed)
        return text[:n]

    def _get_bg_frame(self, brightness, zoom=1.0, pan_y=0):
        """배경 프레임: brightness(0~1), Ken Burns zoom, pan."""
        arr = self._bg_img.astype(np.float32)
        if zoom != 1.0:
            h, w = arr.shape[:2]
            zh, zw = int(h / zoom), int(w / zoom)
            cy = h // 2 + pan_y
            cx = w // 2
            t, l = max(0, cy - zh // 2), max(0, cx - zw // 2)
            crop = arr[t : t + zh, l : l + zw]
            if crop.shape[0] > 0 and crop.shape[1] > 0:
                img = Image.fromarray(crop.astype(np.uint8)).resize((w, h), Image.LANCZOS)
                arr = np.array(img, dtype=np.float32)
        arr *= brightness
        return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB").convert("RGBA")

    # ── Phase renderers ──
    def _ph1(self, draw, t):
        """미스터리 제시 (0~5초)."""
        # Hook text — typewriter
        hook = "아직도 풀리지 않은 수수께끼"
        shown = self._typewriter(hook, t - 0.5, 0.06)
        if shown:
            hw = self._tw(shown, self.f_hook)
            draw.text(((self.W - hw) // 2, 700), shown, font=self.f_hook, fill=(*self.CREAM, 200))

        # Title with glow
        if t > 2.0:
            ta = int(255 * self._eo((t - 2.0) / 1.5))
            for tl_i, tl in enumerate(self._title_lines):
                tw_ = self._tw(tl, self.f_title)
                tx = (self.W - tw_) // 2
                ty = 850 + tl_i * (self._th("가", self.f_title) + 16)
                # Glow (draw text multiple times with lower alpha, offset)
                for gx, gy, ga in [(0, 0, ta), (-1, -1, ta // 4), (1, 1, ta // 4), (-2, 0, ta // 6), (2, 0, ta // 6)]:
                    draw.text((tx + gx, ty + gy), tl, font=self.f_title, fill=(*self.CRIMSON, ga))

    def _ph2(self, draw, t):
        """배경 설명 (PH1_END ~ PH2_END)."""
        lt = t - self.PH1_END
        self.PH2_END - self.PH1_END

        # Card
        card_x, card_y = 50, 550
        card_w, card_h = self.W - 100, 900
        ca = int(217 * self._eo(lt / 1.0))
        if ca > 0:
            self._draw_card(draw, card_x, card_y, card_w, card_h, ca)

        # "배경" label
        if lt > 0.3:
            la = int(180 * self._eo((lt - 0.3) / 0.6))
            label = "▎배경"
            draw.text((card_x + 30, card_y + 25), label, font=self.f_small, fill=(*self.GOLD, la))

        # Story lines — sequential fade-in
        lh = self._th("가", self.f_body) + 14
        base_y = card_y + 80
        for i, line in enumerate(self._story_lines[:16]):
            line_t = lt - 0.8 - i * 0.3
            if line_t < 0:
                break
            la = int(230 * self._eo(line_t / 0.5))
            # Highlight dates/places (digits or specific patterns)
            col = self.CREAM
            draw.text((card_x + 35, base_y + i * lh), line, font=self.f_body, fill=(*col, la))

    def _ph3(self, draw, t):
        """미스터리 포인트 (PH2_END ~ PH3_END)."""
        lt = t - self.PH2_END
        dur = self.PH3_END - self.PH2_END

        # "하지만..." transition
        if lt < 2.0:
            ta = int(255 * self._eo(lt / 0.8))
            if lt > 1.5:
                ta = int(255 * (1 - self._eo((lt - 1.5) / 0.5)))
            txt = "하지만..."
            tw_ = self._tw(txt, self.f_big)
            draw.text(((self.W - tw_) // 2, self.H // 2 - 40), txt, font=self.f_big, fill=(*self.CRIMSON, ta))
            return

        # Mystery point cards
        pt = lt - 2.0
        card_gap = (dur - 2.0) / max(1, len(self.mysteries))
        lh = self._th("가", self.f_body) + 12

        for i, _myst in enumerate(self.mysteries):
            mt = pt - i * card_gap * 0.6  # stagger
            if mt < 0:
                continue

            prog = self._eo(mt / 0.8)
            alpha = int(240 * prog)
            slide_y = int(25 * (1 - prog))

            # Card position
            lines = self._myst_lines[i]
            ch = 30 + len(lines) * lh + 20
            cy = 350 + i * (ch + 50) + slide_y
            cx = 70

            # Card bg
            if alpha > 10:
                self._draw_card(draw, cx, cy, self.W - 140, ch, int(alpha * 0.85))

            # Question mark badge
            qx, qy = cx + 15, cy + 10
            draw.text((qx, qy), "?", font=self.f_qmark, fill=(*self.CRIMSON, alpha))

            # Mystery text
            for j, line in enumerate(lines):
                draw.text((cx + 85, cy + 25 + j * lh), line, font=self.f_body, fill=(*self.CREAM, alpha))

    def _ph4(self, draw, t):
        """가설/결론 (PH3_END ~ PH4_END)."""
        lt = t - self.PH3_END
        dur = self.PH4_END - self.PH3_END

        # "가장 유력한 가설은..." intro
        if lt < 2.5:
            ta = int(255 * self._eo(lt / 1.0))
            txt = "가장 유력한 가설은..."
            tw_ = self._tw(txt, self.f_hook)
            draw.text(((self.W - tw_) // 2, 600), txt, font=self.f_hook, fill=(*self.GOLD, ta))

        # Hypothesis card
        if lt > 1.5:
            ca = int(217 * self._eo((lt - 1.5) / 1.0))
            card_x, card_y = 60, 730
            card_w = self.W - 120
            lh = self._th("가", self.f_body) + 14
            card_h = 60 + len(self._hypo_lines) * lh + 30
            self._draw_card(draw, card_x, card_y, card_w, card_h, ca)

            for i, line in enumerate(self._hypo_lines):
                la = int(230 * self._eo((lt - 2.0 - i * 0.2) / 0.5))
                if la < 0:
                    la = 0
                draw.text((card_x + 30, card_y + 35 + i * lh), line, font=self.f_body, fill=(*self.CREAM, la))

        # CTA
        cta_start = dur - 5
        if lt > cta_start:
            ca = int(220 * self._eo((lt - cta_start) / 1.0))
            # Fade out at very end
            if lt > dur - 2:
                ca = int(ca * (1 - self._eo((lt - (dur - 2)) / 2.0)))
            tw_ = self._tw(self.cta, self.f_hook)
            draw.text(((self.W - tw_) // 2, self.H - 400), self.cta, font=self.f_hook, fill=(*self.AMBER, ca))

            # Comment prompt
            p2 = "💬 댓글로 알려주세요"
            if lt > cta_start + 0.8:
                pa = int(160 * self._eo((lt - cta_start - 0.8) / 0.6))
                if lt > dur - 2:
                    pa = int(pa * (1 - self._eo((lt - (dur - 2)) / 2.0)))
                pw = self._tw(p2, self.f_small)
                draw.text(((self.W - pw) // 2, self.H - 340), p2, font=self.f_small, fill=(*self.CREAM, pa))

    # ── Main render ──
    def _render(self, t):
        # Background: Ken Burns + brightness changes per phase
        if t < self.PH1_END:
            br = self._eo(t / 3.0) * 0.4
            zoom = 1.0
        elif t < self.PH2_END:
            br = 0.35
            prog = (t - self.PH1_END) / (self.PH2_END - self.PH1_END)
            zoom = 1.0 + prog * 0.08  # slow zoom
        elif t < self.PH3_END:
            lt = t - self.PH2_END
            # Brief darken at start of ph3
            br = 0.35 * (1 - 0.6 * (1 - lt)) if lt < 1.0 else 0.3
            zoom = 1.08
        else:
            lt = t - self.PH3_END
            dur4 = self.PH4_END - self.PH3_END
            br = 0.3 * (1 - self._ei(lt / dur4) * 0.5)  # darken at end
            zoom = 1.08 + (lt / dur4) * 0.04

        bg = self._get_bg_frame(br, zoom)
        ov = Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0))
        draw = ImageDraw.Draw(ov)

        # Embers
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
        comp = Image.alpha_composite(comp, self._vignette)
        return np.array(comp.convert("RGB"))

    def generate(self, out="history_mystery.mp4"):
        clip = VideoClip(lambda t: self._render(t), duration=self.duration).with_fps(self.FPS)
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        clip.write_videofile(str(out), codec="libx264", preset="medium", bitrate="8000k", audio=False, logger="bar")
        ph = f"Ph1: 0-{self.PH1_END:.0f}s | Ph2: -{self.PH2_END:.0f}s | Ph3: -{self.PH3_END:.0f}s | Ph4: -{self.PH4_END:.0f}s"
        print(f"\n✅ 생성 완료: {Path(out).resolve()}")
        print(f"   크기: {self.W}×{self.H} | 길이: {self.duration:.0f}초 | {ph}")
        return str(Path(out).resolve())


DEMO_DATA = {
    "title": "디아틀로프 고개 사건",
    "background_story": (
        "1959년 2월, 소련 우랄 산맥. 이고르 디아틀로프가 이끄는 "
        "9명의 대학생 등산팀이 오토르텐 산을 향해 출발했다. "
        "그들은 경험 많은 등산가들이었고, 루트도 충분히 계획되어 있었다. "
        "하지만 2월 26일, 수색대가 발견한 것은 상상을 초월하는 광경이었다."
    ),
    "mystery_points": [
        "텐트가 안쪽에서 칼로 찢겨 있었다. 왜 입구 대신 텐트를 찢고 나갔을까?",
        "영하 30도 속에서 일부는 속옷 차림으로 발견되었다. 모순적 탈의 현상?",
        "2명의 두개골이 골절되었으나 외부 상해 흔적은 없었다. 어떤 힘이 작용했나?",
    ],
    "hypothesis": (
        "2020년 스위스 연구팀은 작은 규모의 눈사태(슬래브 눈사태)가 "
        "텐트를 덮쳤고, 패닉 상태에서 탈출한 뒤 저체온증으로 사망했다는 "
        "모델을 제시했다. 하지만 방사능 검출과 일부 시신의 이상한 변색은 "
        "여전히 설명되지 않는다."
    ),
    "cta": "당신은 어떻게 생각하나요?",
    "duration": 45.0,
}


def main():
    pa = argparse.ArgumentParser(description="역사 미스터리 서스펜스 쇼츠 생성기")
    pa.add_argument("--demo", action="store_true", help="디아틀로프 고개 사건 데모")
    pa.add_argument("--out", type=str, default="history_mystery.mp4")
    a = pa.parse_args()
    if a.demo:
        print("🔍 디아틀로프 고개 사건 미스터리 쇼츠 생성 중...")
        HistoryMysteryGenerator(**DEMO_DATA).generate(a.out)
        return 0
    print("[INFO] --demo로 먼저 시도하세요. Python import로 커스텀 가능.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
