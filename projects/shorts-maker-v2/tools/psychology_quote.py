#!/usr/bin/env python3
"""심리학 기반 자기계발 명언 쇼츠 생성기.

배경 이미지(블러) 위에 명언 텍스트를 감성적으로 렌더링.
- 줄 단위 페이드인 + 슬라이드
- 핵심 단어 앰버 강조
- 떠오르는 파티클 효과
- 상/하단 그라데이션 오버레이
"""

from __future__ import annotations

import argparse
import math
import os
import random
import re
import warnings
from pathlib import Path

warnings.filterwarnings("ignore", category=DeprecationWarning, module="PIL")

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

try:
    from moviepy import VideoClip
except ImportError:
    from moviepy.editor import VideoClip  # type: ignore


class QuoteShortsGenerator:
    W, H = 1080, 1920
    FPS = 30
    MARGIN = 80
    WHITE = (255, 255, 255)
    LAVENDER = (232, 121, 249)
    AMBER = (245, 158, 11)

    # 강조할 심리학/자기계발 키워드
    HL_WORDS = {
        "무의식",
        "의식",
        "자아",
        "그림자",
        "페르소나",
        "원형",
        "개성화",
        "성장",
        "변화",
        "용기",
        "두려움",
        "자유",
        "책임",
        "의미",
        "목적",
        "행복",
        "고통",
        "치유",
        "수용",
        "인정",
        "사랑",
        "진실",
        "본능",
        "선택",
        "운명",
        "잠재력",
        "가능성",
        "힘",
        "강점",
        "약점",
        "균형",
    }

    def __init__(
        self,
        quote_text: str,
        author: str,
        category_tags: str = "#자기계발 #심리학",
        insight_line: str = "",
        bg_image: str | None = None,
        highlight_words: list[str] | None = None,
        duration: float = 20.0,
    ):
        self.quote = quote_text
        self.author = author
        self.tags = category_tags
        self.insight = insight_line
        self.duration = max(15, min(25, duration))
        if highlight_words:
            self.HL_WORDS = self.HL_WORDS | set(highlight_words)

        self._load_fonts()

        # 배경 준비 (블러 + 어둡게)
        self._bg = self._prepare_bg(bg_image)
        # 상/하단 그라데이션
        self._grad_top = self._mk_grad(True)
        self._grad_bot = self._mk_grad(False)
        # 파티클 시드
        random.seed(42)
        self._particles = [
            {
                "x": random.randint(0, self.W),
                "y": random.randint(0, self.H),
                "r": random.uniform(1.5, 3.5),
                "speed": random.uniform(15, 40),
                "alpha": random.randint(60, 160),
                "phase": random.uniform(0, 2 * math.pi),
            }
            for _ in range(45)
        ]
        # 텍스트 래핑
        tw = self.W - self.MARGIN * 2
        self._q_lines = self._wrap(quote_text, self.f_quote, tw)

    # ── Fonts ──
    def _load_fonts(self):
        dirs = [Path("C:/Windows/Fonts"), Path(os.path.expanduser("~/AppData/Local/Microsoft/Windows/Fonts"))]

        def _f(names, fb="malgun.ttf"):
            for d in dirs:
                for n in names:
                    if (d / n).exists():
                        return str(d / n)
            for d in dirs:
                if (d / fb).exists():
                    return str(d / fb)
            return ""

        se = _f(["NanumMyeongjo.ttf", "NanumMyeongjoBold.ttf", "batang.ttc"])
        _f(["NanumGothicBold.ttf", "NanumGothicExtraBold.ttf", "malgunbd.ttf"])
        sa = _f(["NanumGothic.ttf", "malgun.ttf"])

        def _l(p, s):
            return ImageFont.truetype(p, s) if p else ImageFont.load_default(s)

        self.f_quote = _l(se, 60)
        self.f_tag = _l(sa, 32)
        self.f_author = _l(se, 42)
        self.f_insight = _l(sa, 34)
        self.f_small = _l(sa, 28)

    # ── Background ──
    def _prepare_bg(self, img_path: str | None) -> np.ndarray:
        if img_path and Path(img_path).exists():
            img = Image.open(img_path).convert("RGB")
            # 리사이즈 (커버)
            scale = max(self.W / img.width, self.H / img.height)
            nw, nh = int(img.width * scale), int(img.height * scale)
            img = img.resize((nw, nh), Image.LANCZOS)
            left = (nw - self.W) // 2
            top = (nh - self.H) // 2
            img = img.crop((left, top, left + self.W, top + self.H))
        else:
            # 이미지 없으면 보라-검정 그라데이션
            arr = np.zeros((self.H, self.W, 3), dtype=np.uint8)
            for y in range(self.H):
                r = y / self.H
                arr[y, :] = [int(30 * (1 - r)), int(10 * (1 - r)), int(40 * (1 - r))]
            img = Image.fromarray(arr, "RGB")
        # 가우시안 블러 + 어둡게
        img = img.filter(ImageFilter.GaussianBlur(radius=30))
        arr = np.array(img, dtype=np.float32) * 0.4
        return np.clip(arr, 0, 255).astype(np.uint8)

    def _mk_grad(self, is_top: bool) -> Image.Image:
        a = np.zeros((self.H, self.W, 4), dtype=np.uint8)
        zone = self.H // 3
        for y in range(zone):
            if is_top:
                alpha = int(153 * (1 - y / zone))  # 60% → 0
                a[y, :, 3] = alpha
            else:
                alpha = int(179 * (y / zone))  # 0 → 70%
                a[self.H - zone + y, :, 3] = alpha
        return Image.fromarray(a, "RGBA")

    # ── Text Helpers ──
    @staticmethod
    def _wrap(text, font, mw):
        lines, cur = [], ""
        for ch in text:
            if ch == "\n":
                if cur:
                    lines.append(cur)
                cur = ""
                continue
            t = cur + ch
            if font.getbbox(t)[2] - font.getbbox(t)[0] <= mw:
                cur = t
            else:
                if cur:
                    lines.append(cur)
                cur = ch
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

    def _is_hl(self, word: str) -> bool:
        c = re.sub(r"[^가-힣a-zA-Z]", "", word)
        return c in self.HL_WORDS

    # ── Particles ──
    def _draw_particles(self, draw, t):
        for p in self._particles:
            y = (p["y"] - p["speed"] * t) % self.H
            x = p["x"] + math.sin(t * 0.8 + p["phase"]) * 20
            x = x % self.W
            flicker = 0.6 + 0.4 * math.sin(t * 2 + p["phase"])
            al = int(p["alpha"] * flicker)
            r = p["r"]
            draw.ellipse([(x - r, y - r), (x + r, y + r)], fill=(255, 255, 240, al))

    # ── Frame ──
    def _render(self, t):
        dur = self.duration
        # Timing
        bg_fade_end = 2.0
        quote_start = 2.0
        quote_interval = 0.5
        quote_done = quote_start + len(self._q_lines) * quote_interval + 0.5
        author_start = max(quote_done, dur - 8)
        fade_out_start = dur - 3.0

        # Background alpha
        bg_alpha = self._eo(t / bg_fade_end) if t < bg_fade_end else 1.0
        # Overall fade-out
        global_alpha = 1.0
        if t > fade_out_start:
            global_alpha = 1 - self._eo((t - fade_out_start) / 3.0)

        # Background
        bg_arr = self._bg.astype(np.float32) * bg_alpha * global_alpha
        bg = Image.fromarray(np.clip(bg_arr, 0, 255).astype(np.uint8), "RGB").convert("RGBA")

        # Gradient overlays
        ov = Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0))
        if bg_alpha > 0.1:
            bg.paste(
                Image.alpha_composite(Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0)), self._grad_top),
                (0, 0),
                self._grad_top,
            )
            bg.paste(
                Image.alpha_composite(Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0)), self._grad_bot),
                (0, 0),
                self._grad_bot,
            )

        draw = ImageDraw.Draw(ov)

        # Particles
        if t > 1.0:
            pa = self._eo((t - 1.0) / 2.0) * global_alpha
            if pa > 0.1:
                self._draw_particles(draw, t)

        # Tags (상단)
        if t > 1.5:
            ta = int(153 * self._eo((t - 1.5) / 1.0) * global_alpha)  # 60% max
            if ta > 0:
                tw_ = self._tw(self.tags, self.f_tag)
                draw.text(((self.W - tw_) // 2, 180), self.tags, font=self.f_tag, fill=(*self.LAVENDER, ta))

        # Quote lines (중앙)
        lh = self._th("가", self.f_quote) + 24
        total_h = lh * len(self._q_lines)
        base_y = (self.H - total_h) // 2 - 60  # 약간 위쪽

        for i, line in enumerate(self._q_lines):
            line_t = t - quote_start - i * quote_interval
            if line_t < 0:
                continue
            prog = self._eo(line_t / 0.6)
            alpha = int(255 * prog * global_alpha)
            slide_x = int(15 * (1 - prog))  # 왼쪽에서 15px 슬라이드

            if alpha <= 0:
                continue

            # 단어별 하이라이트 렌더링
            y = base_y + i * lh
            x = self.MARGIN + slide_x
            words = line.split() if " " in line else list(line)
            if " " in line:
                for j, w in enumerate(words):
                    seg = w + (" " if j < len(words) - 1 else "")
                    col = self.AMBER if self._is_hl(w) else self.WHITE
                    draw.text((x, y), seg, font=self.f_quote, fill=(*col, alpha))
                    x += self._tw(seg, self.f_quote)
            else:
                # 한국어 — 공백 없이 이어진 경우 전체 흰색 렌더
                # 단어 단위 강조는 공백으로 구분된 텍스트에만 적용
                lw = self._tw(line, self.f_quote)
                draw.text(((self.W - lw) // 2 + slide_x, y), line, font=self.f_quote, fill=(255, 255, 255, alpha))

        # Author (하단)
        if t > author_start:
            aa = self._eo((t - author_start) / 1.0) * global_alpha
            ai = int(179 * aa)  # 70% max
            if ai > 0:
                atxt = f"— {self.author}"
                aw = self._tw(atxt, self.f_author)
                author_y = self.H - 420
                draw.text(((self.W - aw) // 2, author_y), atxt, font=self.f_author, fill=(255, 255, 255, ai))
                # 구분선
                line_w = 80
                lx = (self.W - line_w) // 2
                draw.line(
                    [(lx, author_y + 70), (lx + line_w, author_y + 70)], fill=(*self.LAVENDER, int(ai * 0.5)), width=2
                )
                # Insight line
                if self.insight:
                    ia = int(200 * self._eo((t - author_start - 0.8) / 0.8) * global_alpha)
                    if ia > 0:
                        iw = self._tw(self.insight, self.f_insight)
                        draw.text(
                            ((self.W - iw) // 2, author_y + 95),
                            self.insight,
                            font=self.f_insight,
                            fill=(200, 200, 210, ia),
                        )

        comp = Image.alpha_composite(bg, ov)
        return np.array(comp.convert("RGB"))

    def generate(self, out="quote_shorts.mp4"):
        clip = VideoClip(lambda t: self._render(t), duration=self.duration).with_fps(self.FPS)
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        clip.write_videofile(str(out), codec="libx264", preset="medium", bitrate="8000k", audio=False, logger="bar")
        print(f"\n✅ 생성 완료: {Path(out).resolve()}")
        print(f"   크기: {self.W}×{self.H} | 길이: {self.duration:.0f}초 | FPS: {self.FPS}")
        return str(Path(out).resolve())


DEMO_DATA = {
    "quote_text": ("당신이 되고자 하는 것이 아니라,\n당신이 이미 가진 것을 인정하는 순간\n진정한 변화가 시작된다."),
    "author": "칼 융 (Carl Jung)",
    "category_tags": "#자기계발 #심리학 #칼융",
    "insight_line": "그림자를 수용하면 자아는 더 강해집니다",
    "highlight_words": ["인정", "변화", "진정한"],
    "duration": 20.0,
}


def main():
    pa = argparse.ArgumentParser(description="심리학 명언 쇼츠 생성기")
    pa.add_argument("--demo", action="store_true", help="칼 융 명언 데모")
    pa.add_argument("--quote", type=str, default="")
    pa.add_argument("--author", type=str, default="")
    pa.add_argument("--tags", type=str, default="#자기계발 #심리학")
    pa.add_argument("--insight", type=str, default="")
    pa.add_argument("--bg-image", type=str, default=None)
    pa.add_argument("--highlight", nargs="*", default=[])
    pa.add_argument("--duration", type=float, default=20)
    pa.add_argument("--out", type=str, default="quote_shorts.mp4")
    a = pa.parse_args()
    if a.demo:
        print("💡 칼 융 명언 데모 생성 중...")
        QuoteShortsGenerator(**DEMO_DATA).generate(a.out)
        return 0
    if not all([a.quote, a.author]):
        print("[FAIL] --quote, --author 필수. --demo로 먼저 시도하세요.")
        return 1
    QuoteShortsGenerator(a.quote, a.author, a.tags, a.insight, a.bg_image, a.highlight, a.duration).generate(a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
