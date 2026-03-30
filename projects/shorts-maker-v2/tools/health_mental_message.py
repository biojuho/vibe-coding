#!/usr/bin/env python3
"""정신건강 감성 메시지 쇼츠 생성기.

따뜻하고 안전한 느낌 — 호흡 리듬 밝기 변화 + 줄 단위 페이드인 + 민트 하이라이트.
배경: 자연/풍경 이미지 블러 or 그래디언트.
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
from PIL import Image, ImageDraw, ImageFilter, ImageFont

try:
    from moviepy import VideoClip
except ImportError:
    from moviepy.editor import VideoClip  # type: ignore


class MentalHealthMessageGenerator:
    W, H = 1080, 1920
    FPS = 30

    # Warm palette
    BG = (12, 22, 18)
    MINT = (52, 211, 153)  # #34D399
    WHITE = (245, 248, 245)
    WARM_WHITE = (255, 250, 240)

    def __init__(
        self,
        message_lines: list[str],
        highlight_words: list[str] | None = None,
        closing_text: str = "오늘 하루도 잘 버텼어요",
        disclaimer: str = "어려움이 있다면 전문가 상담을 받아주세요",
        bg_image: str = "",
        duration: float = 22.0,
    ):
        self.message_lines = message_lines
        self.highlight_words = set(highlight_words or [])
        self.closing_text = closing_text
        self.disclaimer = disclaimer
        self.bg_image = bg_image
        self.duration = max(15, min(30, duration))

        # Phase timing
        self.breath_intro = 3.0
        self.text_start = 3.0
        self.line_interval = 0.7
        self.text_dur = self.text_start + len(message_lines) * self.line_interval + 2.0
        self.hold_start = self.text_dur
        self.hold_dur = max(3.0, self.duration - self.text_dur - 4.0)
        self.fade_start = self.hold_start + self.hold_dur
        self.fade_dur = self.duration - self.fade_start

        self._load_fonts()
        self._bg_frame = self._prepare_bg()

        # Soft particles (firefly-like)
        random.seed(42)
        self._particles = [
            {
                "x": random.randint(0, self.W),
                "y": random.randint(0, self.H),
                "vy": random.uniform(-6, -1.5),
                "vx": random.uniform(-1, 1),
                "r": random.uniform(1, 3),
                "a": random.randint(15, 55),
                "ph": random.uniform(0, math.tau),
                "spd": random.uniform(0.8, 2.0),
            }
            for _ in range(25)
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

        # Serif for emotional feel
        serif = _f(["NanumMyeongjo.ttf", "NanumMyeongjoBold.ttf", "batang.ttc"])
        sans = _f(["NanumGothic.ttf", "malgun.ttf"])
        sb = _f(["NanumGothicBold.ttf", "malgunbd.ttf"])

        def _l(p, s):
            return ImageFont.truetype(p, s) if p else ImageFont.load_default(s)

        self.f_msg = _l(serif, 50)  # 메시지 (세리프)
        self.f_highlight = _l(serif, 50)  # 하이라이트 (same font, colored)
        self.f_closing = _l(sb, 30)  # 마무리 작은 텍스트
        self.f_disc = _l(sans, 22)  # 면책

    def _prepare_bg(self):
        """배경 이미지 준비 (블러 + 어둡게) or 그래디언트."""
        if self.bg_image and Path(self.bg_image).exists():
            img = Image.open(self.bg_image).convert("RGB")
            img = img.resize((self.W, self.H), Image.Resampling.LANCZOS)
            img = img.filter(ImageFilter.GaussianBlur(radius=25))
            arr = np.array(img, dtype=np.float32) * 0.35
            return arr.clip(0, 255).astype(np.uint8)
        else:
            # Warm dark green gradient
            arr = np.zeros((self.H, self.W, 3), dtype=np.uint8)
            for y in range(self.H):
                r = y / self.H
                arr[y, :, 0] = int(8 + 10 * r)  # R
                arr[y, :, 1] = int(18 + 15 * r)  # G
                arr[y, :, 2] = int(14 + 8 * r)  # B
            return arr

    def _tw(self, t, f):
        b = f.getbbox(t)
        return b[2] - b[0] if b else 0

    def _th(self, t, f):
        b = f.getbbox(t)
        return b[3] - b[1] if b else 0

    @staticmethod
    def _eo(t):
        return 1 - (1 - min(1, max(0, t))) ** 3

    def _breathing_brightness(self, t):
        """호흡 리듬 밝기 0.35→0.45→0.35, 주기 3초."""
        return 0.40 + 0.05 * math.sin(t * math.tau / 3.0)

    def _ken_burns_scale(self, t):
        """느린 줌인 (1.0→1.03, 매우 미묘)."""
        return 1.0 + 0.015 * (t / max(1, self.duration))

    def _draw_particles(self, draw, t, alpha_mult=1.0):
        for p in self._particles:
            x = (p["x"] + p["vx"] * t * 10) % self.W
            y = (p["y"] + p["vy"] * t * 8) % self.H
            fl = 0.3 + 0.7 * ((math.sin(t * p["spd"] + p["ph"]) + 1) / 2)
            al = int(p["a"] * fl * alpha_mult)
            r = p["r"] * (0.7 + 0.3 * fl)
            # Soft glow
            for gi in range(3):
                gr = r + gi * 2
                ga = max(1, al // (gi + 1))
                draw.ellipse([(x - gr, y - gr), (x + gr, y + gr)], fill=(*self.MINT, ga))

    def _draw_message_line(self, draw, line, cx, cy, alpha):
        """줄 렌더링 — 핵심 단어 민트 하이라이트 포함."""
        if not self.highlight_words:
            tw_ = self._tw(line, self.f_msg)
            draw.text((cx - tw_ // 2, cy), line, font=self.f_msg, fill=(*self.WARM_WHITE, alpha))
            return

        # Split into words, highlight matching
        words = line.split(" ") if " " in line else [line]
        # Measure total width
        segments = []
        for w in words:
            is_hl = any(kw in w for kw in self.highlight_words)
            segments.append({"text": w, "hl": is_hl})

        total_w = sum(self._tw(s["text"], self.f_msg) for s in segments)
        total_w += (len(segments) - 1) * self._tw(" ", self.f_msg)

        x = cx - total_w // 2
        space_w = self._tw(" ", self.f_msg)
        for i, seg in enumerate(segments):
            color = self.MINT if seg["hl"] else self.WARM_WHITE
            draw.text((x, cy), seg["text"], font=self.f_msg, fill=(*color, alpha))
            x += self._tw(seg["text"], self.f_msg)
            if i < len(segments) - 1:
                x += space_w

    def _apply_warm_grade(self, arr):
        """따뜻한 그린 톤 그레이딩."""
        f = arr.astype(np.float32)
        # Green shift
        f[:, :, 1] = np.clip(f[:, :, 1] * 1.05 + 3, 0, 255)
        # Warm tint
        f[:, :, 0] = np.clip(f[:, :, 0] * 1.02, 0, 255)
        # Slight contrast
        mean = f.mean()
        f = np.clip((f - mean) * 1.03 + mean, 0, 255)
        return f.astype(np.uint8)

    def _apply_vignette(self, arr, strength=0.4):
        h, w = arr.shape[:2]
        Y, X = np.ogrid[:h, :w]
        cx, cy = w / 2, h / 2
        dist = np.sqrt((X - cx) ** 2 + (Y - cy) ** 2)
        max_d = math.sqrt(cx**2 + cy**2)
        vig = 1 - (dist / max_d) ** 2 * strength
        vig = np.clip(vig, 0, 1)
        return (arr.astype(np.float32) * vig[:, :, np.newaxis]).clip(0, 255).astype(np.uint8)

    def _render(self, t):
        # Breathing brightness
        br = self._breathing_brightness(t)

        # Background with brightness
        bg_f = self._bg_frame.astype(np.float32) * (br / 0.35)
        bg_f = bg_f.clip(0, 255).astype(np.uint8)

        # Ken Burns (simple crop-scale simulation)
        scale = self._ken_burns_scale(t)
        if scale > 1.001:
            img = Image.fromarray(bg_f)
            new_w = int(self.W * scale)
            new_h = int(self.H * scale)
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            dx = (new_w - self.W) // 2
            dy = (new_h - self.H) // 2
            img = img.crop((dx, dy, dx + self.W, dy + self.H))
            bg_f = np.array(img)

        bg = Image.fromarray(bg_f).convert("RGBA")
        ov = Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0))
        draw = ImageDraw.Draw(ov)

        # Overall fade
        if t < 1.5:
            master_alpha = self._eo(t / 1.5)
        elif t > self.duration - 2.0:
            master_alpha = 1 - self._eo((t - (self.duration - 2.0)) / 2.0)
        else:
            master_alpha = 1.0

        # Particles
        self._draw_particles(draw, t, master_alpha * 0.6)

        # Message lines
        if t >= self.text_start:
            lh = 72
            total_h = len(self.message_lines) * lh
            start_y = (self.H - total_h) // 2 - 40

            for i, line in enumerate(self.message_lines):
                line_t = t - self.text_start - i * self.line_interval
                if line_t < 0:
                    continue
                prog = self._eo(line_t / 0.8)  # slow fade in
                al = int(240 * prog * master_alpha)
                slide = int(10 * (1 - prog))
                cy = start_y + i * lh + slide
                self._draw_message_line(draw, line, self.W // 2, cy, al)

        # Closing text
        all_lines_done = self.text_start + len(self.message_lines) * self.line_interval + 1.5
        if t > all_lines_done:
            cl_prog = self._eo((t - all_lines_done) / 1.0)
            cl_al = int(160 * cl_prog * master_alpha)
            cw = self._tw(self.closing_text, self.f_closing)
            cy = (self.H + (len(self.message_lines) * 72)) // 2 + 60
            draw.text(((self.W - cw) // 2, cy), self.closing_text, font=self.f_closing, fill=(*self.MINT, cl_al))

        # Disclaimer (last 3 seconds)
        if t > self.duration - 3.5:
            disc_prog = self._eo((t - (self.duration - 3.5)) / 0.8)
            da = int(100 * disc_prog * master_alpha)
            dw = self._tw(self.disclaimer, self.f_disc)
            draw.text(((self.W - dw) // 2, self.H - 130), self.disclaimer, font=self.f_disc, fill=(*self.WHITE, da))

        # Top gradient (subtle)
        for y in range(150):
            ga = int(80 * (1 - y / 150) * master_alpha)
            draw.line([(0, y), (self.W, y)], fill=(0, 0, 0, ga))
        # Bottom gradient
        for y in range(self.H - 200, self.H):
            ga = int(100 * ((y - (self.H - 200)) / 200) * master_alpha)
            draw.line([(0, y), (self.W, y)], fill=(0, 0, 0, ga))

        comp = Image.alpha_composite(bg, ov)
        result = np.array(comp.convert("RGB"))
        result = self._apply_warm_grade(result)
        result = self._apply_vignette(result, 0.35)
        return result

    def generate(self, out="mental_health_message.mp4"):
        clip = VideoClip(lambda t: self._render(t), duration=self.duration).with_fps(self.FPS)
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        clip.write_videofile(str(out), codec="libx264", preset="medium", bitrate="8000k", audio=False, logger="bar")
        sz = Path(out).stat().st_size / (1024 * 1024)
        print(f"\n✅ 생성 완료: {Path(out).resolve()}")
        print(f"   크기: {self.W}×{self.H} | 길이: {self.duration:.0f}초 | 파일: {sz:.1f}MB")
        return str(Path(out).resolve())


# ── Demo data ──
DEMO_DATA = {
    "message_lines": [
        "당신이 느끼는 감정은",
        "모두 괜찮은 감정이에요.",
        "",
        "슬퍼도 괜찮고,",
        "지쳐도 괜찮고,",
        "아무것도 하고 싶지 않아도",
        "괜찮아요.",
        "",
        "지금 이 순간,",
        "당신은 충분합니다.",
    ],
    "highlight_words": ["괜찮은", "괜찮고", "괜찮아요", "충분합니다"],
    "closing_text": "오늘 하루도 잘 버텼어요 💚",
    "disclaimer": "어려움이 있다면 전문가 상담을 받아주세요 (1393)",
    "duration": 22.0,
}


def main():
    pa = argparse.ArgumentParser(description="정신건강 감성 메시지 쇼츠")
    pa.add_argument("--demo", action="store_true")
    pa.add_argument("--out", default="output/demo_mental_health.mp4")
    pa.add_argument("--bg", default="", help="배경 이미지 경로")
    a = pa.parse_args()

    if a.demo:
        print("💚 정신건강 감성 메시지 쇼츠 생성 중...")
        data = {**DEMO_DATA}
        if a.bg:
            data["bg_image"] = a.bg
        gen = MentalHealthMessageGenerator(**data)
        gen.generate(a.out)
    else:
        print("--demo 플래그로 데모를 생성하세요")


if __name__ == "__main__":
    raise SystemExit(main())
