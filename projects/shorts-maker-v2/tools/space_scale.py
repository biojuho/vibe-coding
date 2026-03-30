#!/usr/bin/env python3
"""우주 스케일 비교 줌아웃 쇼츠 생성기.

작은 것에서 큰 것으로 줌아웃하며 스케일감을 연출.
별 파티클 + 글로우 링 + 카운트업 애니메이션 + 와프 전환.
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


class SpaceScaleGenerator:
    W, H = 1080, 1920
    FPS = 30

    # Palette
    BG = (3, 0, 20)  # #030014
    INDIGO = (129, 140, 248)  # #818CF8
    AMBER = (245, 158, 11)  # #F59E0B
    WHITE = (255, 255, 255)
    STAR_BLUE = (180, 200, 255)
    DEEP_PURPLE = (88, 28, 135)  # 글로우 외곽

    def __init__(
        self, scales: list[dict], outro_text: str = "그리고 이 모든 것 속에\n당신이 있습니다", duration: float = 40.0
    ):
        """
        Args:
            scales: [{"name": "인간", "size_text": "1.7m", "image_path": "..."}, ...]
                    작은것→큰것 순서.
            outro_text: 마지막 감성 텍스트.
            duration: 총 영상 길이.
        """
        self.scales = scales
        self.outro_text = outro_text
        n = len(scales)
        self.duration = max(25, min(60, duration))

        # Phase timing: 각 스케일에 균등 배분 + 마지막 아웃트로
        self.outro_dur = 4.0
        self.rewind_dur = 2.5
        self.total_scale_dur = self.duration - self.outro_dur - self.rewind_dur
        self.step_dur = self.total_scale_dur / max(1, n)
        self.trans_dur = min(1.5, self.step_dur * 0.35)  # 전환 시간

        self._load_fonts()
        self._load_images()
        self._init_stars()

        # Preprocess text
        self.W - 140
        self._outro_lines = self.outro_text.split("\n")

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

        sb = _f(["NanumGothicBold.ttf", "malgunbd.ttf"])
        sa = _f(["NanumGothic.ttf", "malgun.ttf"])

        def _l(p, s):
            return ImageFont.truetype(p, s) if p else ImageFont.load_default(s)

        self.f_name = _l(sb, 56)
        self.f_size = _l(sb, 72)
        self.f_unit = _l(sa, 38)
        self.f_big = _l(sb, 52)
        self.f_small = _l(sa, 30)
        self.f_outro = _l(sb, 48)

    def _load_images(self):
        """각 스케일 이미지를 원형 크롭하여 캐싱."""
        self._imgs = []
        target_size = int(self.W * 0.40)  # 화면의 40%
        for sc in self.scales:
            path = sc.get("image_path", "")
            if path and Path(path).exists():
                img = Image.open(path).convert("RGBA")
                # 정사각형 크롭
                s = min(img.width, img.height)
                l_ = (img.width - s) // 2
                t_ = (img.height - s) // 2
                img = img.crop((l_, t_, l_ + s, t_ + s))
                img = img.resize((target_size, target_size), Image.LANCZOS)
            else:
                # Placeholder: gradient circle
                img = self._make_placeholder(target_size, sc.get("name", "?"))
            # Circular mask
            mask = Image.new("L", (target_size, target_size), 0)
            ImageDraw.Draw(mask).ellipse([(0, 0), (target_size, target_size)], fill=255)
            img.putalpha(mask)
            self._imgs.append(img)

    def _make_placeholder(self, size, name):
        """플레이스홀더 원형 그래디언트."""
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        cx, cy = size // 2, size // 2
        for r in range(size // 2, 0, -1):
            frac = r / (size // 2)
            c = (
                int(self.INDIGO[0] * frac * 0.5),
                int(self.INDIGO[1] * frac * 0.5),
                int(130 + 120 * frac),
                int(200 * frac),
            )
            draw.ellipse([(cx - r, cy - r), (cx + r, cy + r)], fill=c)
        # 이름 이니셜
        ch = name[0] if name else "?"
        tw = draw.textlength(ch, font=self.f_big) if hasattr(draw, "textlength") else self.f_big.getlength(ch)
        draw.text(((size - tw) / 2, size // 2 - 30), ch, font=self.f_big, fill=(255, 255, 255, 200))
        return img

    def _init_stars(self):
        """별 파티클 초기화 (300개)."""
        random.seed(42)
        cx, cy = self.W / 2, self.H / 2
        self._stars = []
        for _ in range(350):
            # 중앙에서 랜덤 각도+거리
            angle = random.uniform(0, math.tau)
            dist = random.uniform(10, max(self.W, self.H) * 0.8)
            x = cx + math.cos(angle) * dist
            y = cy + math.sin(angle) * dist
            is_blue = random.random() < 0.3
            color = self.STAR_BLUE if is_blue else self.WHITE
            self._stars.append(
                {
                    "x0": x,
                    "y0": y,
                    "angle": angle,
                    "dist0": dist,
                    "r": random.uniform(0.8, 3.5),
                    "color": color,
                    "twinkle_ph": random.uniform(0, math.tau),
                    "twinkle_spd": random.uniform(1.5, 4.0),
                    "alpha_base": random.randint(80, 220),
                }
            )

    def _draw_stars(self, draw, t, speed_mult=1.0):
        """별 파티클 렌더링 — 중앙에서 바깥으로 이동."""
        cx, cy = self.W / 2, self.H / 2
        for s in self._stars:
            # 줌아웃 효과: 시간에 따라 dist 증가
            d = s["dist0"] + t * 15 * speed_mult
            d = d % (max(self.W, self.H) * 0.9)  # wrap
            x = cx + math.cos(s["angle"]) * d
            y = cy + math.sin(s["angle"]) * d

            # 화면 밖이면 스킵
            if x < -5 or x > self.W + 5 or y < -5 or y > self.H + 5:
                continue

            # 트윙클
            twinkle = 0.4 + 0.6 * ((math.sin(t * s["twinkle_spd"] + s["twinkle_ph"]) + 1) / 2)
            alpha = int(s["alpha_base"] * twinkle)
            r = s["r"] * (0.7 + 0.3 * twinkle)

            # 와프 시 스트레칭
            if speed_mult > 2.0:
                streak = min(8, speed_mult * 1.5)
                dx = math.cos(s["angle"]) * streak
                dy = math.sin(s["angle"]) * streak
                draw.line([(x, y), (x + dx, y + dy)], fill=(*s["color"], alpha), width=max(1, int(r * 0.7)))
            else:
                draw.ellipse([(x - r, y - r), (x + r, y + r)], fill=(*s["color"], alpha))

    def _draw_glow_ring(self, draw, cx, cy, radius, t, alpha_base=50):
        """소프트 글로우 링."""
        for i in range(20):
            r = radius + i * 2
            pulse = 0.7 + 0.3 * math.sin(t * 2.0 + i * 0.2)
            al = int(alpha_base * pulse * (1 - i / 20))
            if al < 1:
                continue
            draw.ellipse([(cx - r, cy - r), (cx + r, cy + r)], outline=(*self.INDIGO, al), width=2)

    def _draw_countup(self, draw, text, t_local, total_t, cy):
        """카운트업 애니메이션 — 숫자 부분만 올라감."""
        # "930,000 km" → 숫자와 단위 분리
        parts = text.split()
        num_str = parts[0] if parts else text
        unit_str = " ".join(parts[1:]) if len(parts) > 1 else ""

        # 숫자에서 콤마/소수점 제거하여 float 파싱
        try:
            target = float(num_str.replace(",", "").replace("억", ""))
            is_numeric = True
        except (ValueError, AttributeError):
            is_numeric = False

        prog = min(1, t_local / min(1.5, total_t * 0.4))
        prog = self._eo(prog)  # ease-out

        if is_numeric and prog < 1.0:
            current = target * prog
            # 원본 포맷 유지 (콤마)
            if "," in num_str:
                display = f"{int(current):,}"
            elif "." in num_str:
                display = f"{current:.1f}"
            else:
                display = str(int(current))
        else:
            display = num_str

        full = f"{display} {unit_str}".strip()
        fa = int(255 * self._eo(t_local / 0.5))

        # 사이즈 텍스트 (앰버)
        tw = self._tw(full, self.f_size)
        draw.text(((self.W - tw) // 2, cy), full, font=self.f_size, fill=(*self.AMBER, fa))

    @staticmethod
    def _eo(t):
        return 1 - (1 - min(1, max(0, t))) ** 3

    @staticmethod
    def _ei(t):
        return min(1, max(0, t)) ** 2

    def _tw(self, t, f):
        b = f.getbbox(t)
        return b[2] - b[0] if b else 0

    def _render(self, t):
        n = len(self.scales)
        scale_end = self.total_scale_dur
        outro_start = scale_end
        rewind_start = outro_start + self.outro_dur

        # BG
        bg = Image.new("RGBA", (self.W, self.H), (*self.BG, 255))
        ov = Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0))
        draw = ImageDraw.Draw(ov)

        # 현재 페이즈 계산
        if t < scale_end:
            idx = min(int(t / self.step_dur), n - 1)
            lt = t - idx * self.step_dur  # 현재 스텝 내 로컬 시간
            lt / self.step_dur

            # 와프 속도 — 전환 중 가속
            if lt < self.trans_dur and idx > 0:
                warp = 1 + 5 * (1 - lt / self.trans_dur)  # 빠르게 감속
            elif lt > self.step_dur - self.trans_dur and idx < n - 1:
                warp = 1 + 5 * ((lt - (self.step_dur - self.trans_dur)) / self.trans_dur)
            else:
                warp = 1.0

            # Stars
            self._draw_stars(draw, t, warp)

            # 전환: 이전 이미지 축소 퇴장
            if lt < self.trans_dur and idx > 0:
                prev_scale = 1.0 - self._eo(lt / self.trans_dur) * 0.9
                prev_alpha = int(255 * (1 - self._eo(lt / self.trans_dur)))
                if prev_scale > 0.05:
                    self._draw_scale_item(draw, bg, idx - 1, prev_scale, prev_alpha, t)

            # 현재 이미지
            if lt < self.trans_dur and idx > 0:
                cur_prog = self._eo(lt / self.trans_dur)
                cur_scale = 0.1 + cur_prog * 0.9
                cur_alpha = int(255 * cur_prog)
            elif lt > self.step_dur - self.trans_dur and idx < n - 1:
                exit_prog = self._eo((lt - (self.step_dur - self.trans_dur)) / self.trans_dur)
                cur_scale = 1.0 - exit_prog * 0.9
                cur_alpha = int(255 * (1 - exit_prog))
            else:
                cur_scale = 1.0
                cur_alpha = 255

            self._draw_scale_item(
                draw,
                bg,
                idx,
                cur_scale,
                cur_alpha,
                t,
                show_text=True,
                text_t=max(0, lt - self.trans_dur * (1 if idx > 0 else 0)),
            )

        elif t < rewind_start:
            # Outro
            lt = t - outro_start
            self._draw_stars(draw, t, 0.3)

            # Flash at start
            if lt < 0.5:
                flash_a = int(120 * (1 - lt / 0.5))
                draw.rectangle([(0, 0), (self.W, self.H)], fill=(255, 255, 255, flash_a))

            # Outro text
            lh = 70
            total_h = len(self._outro_lines) * lh
            start_y = (self.H - total_h) // 2
            for i, line in enumerate(self._outro_lines):
                la = int(255 * self._eo((lt - 0.3 - i * 0.4) / 0.8))
                if la < 0:
                    la = 0
                tw = self._tw(line, self.f_outro)
                # Slide up slightly
                slide = int(15 * (1 - self._eo((lt - 0.3 - i * 0.4) / 0.8)))
                draw.text(
                    ((self.W - tw) // 2, start_y + i * lh + slide), line, font=self.f_outro, fill=(*self.WHITE, la)
                )

        else:
            # Rewind: 빠르게 줌인 역재생
            lt = t - rewind_start
            rewind_prog = self._eo(lt / self.rewind_dur)
            self._draw_stars(draw, t, 4 * (1 - rewind_prog))

            # 역순으로 이미지 빠르게 스캐닝
            rev_idx = n - 1 - int(rewind_prog * n)
            rev_idx = max(0, min(n - 1, rev_idx))
            sc = 0.3 + rewind_prog * 0.5
            al = int(150 * (1 - rewind_prog * 0.5))
            self._draw_scale_item(draw, bg, rev_idx, sc, al, t)

            # 마지막에 지구(첫 번째 또는 "Earth" 관련) 아이템
            if rewind_prog > 0.8:
                ea = int(255 * self._eo((rewind_prog - 0.8) / 0.2))
                self._draw_scale_item(draw, bg, 0, 1.0, ea, t, show_text=True, text_t=2)

        comp = Image.alpha_composite(bg, ov)
        return np.array(comp.convert("RGB"))

    def _draw_scale_item(self, draw, bg, idx, scale, alpha, t, show_text=False, text_t=0):
        """하나의 스케일 단계 렌더링."""
        if idx < 0 or idx >= len(self.scales):
            return

        sc = self.scales[idx]
        img = self._imgs[idx]
        target_size = img.width

        cx, cy = self.W // 2, self.H // 2 - 80

        # 글로우 링
        if alpha > 30:
            ring_r = int(target_size * scale / 2) + 20
            self._draw_glow_ring(draw, cx, cy, ring_r, t, alpha_base=int(50 * alpha / 255))

        # 이미지 (스케일 적용)
        if scale > 0.05 and alpha > 10:
            sz = max(10, int(target_size * scale))
            resized = img.resize((sz, sz), Image.LANCZOS)
            # 알파 조정
            if alpha < 255:
                arr = np.array(resized)
                arr[:, :, 3] = (arr[:, :, 3].astype(np.float32) * alpha / 255).clip(0, 255).astype(np.uint8)
                resized = Image.fromarray(arr)
            paste_x = cx - sz // 2
            paste_y = cy - sz // 2
            bg.paste(resized, (paste_x, paste_y), resized)

        # 텍스트
        if show_text and alpha > 30:
            name = sc.get("name", "")
            size_text = sc.get("size_text", "")

            # 이름 (인디고, 상단)
            name_y = cy - int(target_size * scale / 2) - 80
            if name_y < 50:
                name_y = 50
            na = int(min(255, alpha) * self._eo(text_t / 0.6))
            if na > 0:
                nw = self._tw(name, self.f_name)
                draw.text(((self.W - nw) // 2, name_y), name, font=self.f_name, fill=(*self.INDIGO, na))

            # 크기 (앰버, 하단, 카운트업)
            size_y = cy + int(target_size * scale / 2) + 40
            if size_y > self.H - 200:
                size_y = self.H - 200
            if text_t > 0.3 and size_text:
                self._draw_countup(draw, size_text, text_t - 0.3, self.step_dur, size_y)

            # 스텝 인디케이터
            step_text = f"{idx + 1} / {len(self.scales)}"
            sa = int(100 * self._eo(text_t / 0.8))
            sw = self._tw(step_text, self.f_small)
            draw.text(((self.W - sw) // 2, self.H - 120), step_text, font=self.f_small, fill=(*self.INDIGO, sa))

    def generate(self, out="space_scale.mp4"):
        clip = VideoClip(lambda t: self._render(t), duration=self.duration).with_fps(self.FPS)
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        clip.write_videofile(str(out), codec="libx264", preset="medium", bitrate="8000k", audio=False, logger="bar")
        sz = Path(out).stat().st_size / (1024 * 1024)
        print(f"\n✅ 생성 완료: {Path(out).resolve()}")
        print(f"   크기: {self.W}×{self.H} | 길이: {self.duration:.0f}초 | 파일: {sz:.1f}MB")
        return str(Path(out).resolve())


# ── Demo data ──
DEMO_SCALES = [
    {"name": "인간", "size_text": "1.7 m"},
    {"name": "에베레스트 산", "size_text": "8,849 m"},
    {"name": "지구", "size_text": "12,742 km"},
    {"name": "목성", "size_text": "139,820 km"},
    {"name": "태양", "size_text": "1,392,700 km"},
    {"name": "태양계", "size_text": "287억 km"},
    {"name": "은하수", "size_text": "100,000 광년"},
    {"name": "관측 가능한 우주", "size_text": "930억 광년"},
]


def main():
    pa = argparse.ArgumentParser(description="우주 스케일 비교 줌아웃 쇼츠")
    pa.add_argument("--demo", action="store_true", help="데모 영상 생성")
    pa.add_argument("--out", default="output/demo_space_scale.mp4")
    pa.add_argument("--duration", type=float, default=42.0)
    a = pa.parse_args()

    if a.demo:
        print("🔭 우주 스케일 비교 쇼츠 생성 중...")
        gen = SpaceScaleGenerator(
            scales=DEMO_SCALES,
            duration=a.duration,
            outro_text="그리고 이 모든 것 속에\n당신이 있습니다",
        )
        gen.generate(a.out)
    else:
        print("--demo 플래그로 데모를 생성하세요")


if __name__ == "__main__":
    raise SystemExit(main())
