#!/usr/bin/env python3
"""우주 팩트 폭탄 쇼츠 생성기.

빠른 템포로 충격적인 우주 사실을 연속 공개.
글리치 플래시 + 카운트업 + 딥 스페이스 컬러 그레이딩.
"""
from __future__ import annotations
import argparse, math, os, random, warnings
from pathlib import Path
warnings.filterwarnings("ignore", category=DeprecationWarning, module="PIL")

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
try:
    from moviepy import VideoClip
except ImportError:
    from moviepy.editor import VideoClip  # type: ignore


class SpaceFactBombGenerator:
    W, H = 1080, 1920
    FPS = 30

    # Deep space palette
    BG = (3, 0, 20)               # #030014
    CYAN = (6, 182, 212)          # #06B6D4
    AMBER = (245, 158, 11)        # #F59E0B
    LAVENDER = (129, 140, 248)    # #818CF8
    WHITE = (240, 240, 255)
    DEEP_NAVY = (8, 12, 40)       # 그림자
    CARD_BG = (10, 15, 45)        # 카드 배경

    def __init__(self, topic_title: str,
                 facts: list[dict],
                 outro_text: str = "우주는 아직 99%가\n미지의 영역",
                 duration: float = 35.0):
        """
        Args:
            topic_title: "우주에서 가장 ○○한 것"
            facts: [{"title": "...", "detail": "...", "number": "100,000", "unit": "광년", "image_path": ""}]
            outro_text: 마무리 감성 텍스트
            duration: 총 길이
        """
        self.topic_title = topic_title
        self.facts = facts[:6]  # max 6개
        self.outro_text = outro_text
        n = len(self.facts)
        self.duration = max(20, min(50, duration))

        # Phase timing
        self.hook_dur = 2.5
        self.outro_dur = 3.5
        self.cards_dur = self.duration - self.hook_dur - self.outro_dur
        self.card_dur = self.cards_dur / max(1, n)
        self.trans_dur = 0.3  # 카드 간 전환

        self._load_fonts()
        self._init_stars()
        self._init_glitch()
        self._preprocess_text()

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
        self.f_hook = _l(sb, 80)       # 훅 타이틀
        self.f_title = _l(sb, 52)      # 팩트 제목
        self.f_number = _l(sb, 88)     # 숫자 (크게)
        self.f_unit = _l(sb, 44)       # 단위
        self.f_detail = _l(sa, 32)     # 부가 설명
        self.f_badge = _l(sb, 28)      # FACT 01 배지
        self.f_outro = _l(sb, 48)      # 아웃트로
        self.f_small = _l(sa, 26)      # 작은 텍스트

    def _init_stars(self):
        random.seed(77)
        cx, cy = self.W / 2, self.H / 2
        self._stars = []
        for _ in range(400):
            angle = random.uniform(0, math.tau)
            dist = random.uniform(5, max(self.W, self.H) * 0.85)
            is_blue = random.random() < 0.35
            color = (180, 200, 255) if is_blue else (255, 255, 255)
            self._stars.append({
                "x0": cx + math.cos(angle) * dist,
                "y0": cy + math.sin(angle) * dist,
                "angle": angle,
                "dist0": dist,
                "r": random.uniform(0.5, 3.0),
                "color": color,
                "twk_ph": random.uniform(0, math.tau),
                "twk_spd": random.uniform(2, 5),
                "alpha": random.randint(60, 220),
            })

    def _init_glitch(self):
        """글리치 타이밍 시드."""
        random.seed(33)
        self._glitch_slices = [
            {"y": random.randint(0, self.H), "h": random.randint(3, 20),
             "dx": random.choice([-1, 1]) * random.randint(5, 30),
             "color_shift": random.choice(["r", "g", "b"])}
            for _ in range(15)
        ]

    def _preprocess_text(self):
        tw = self.W - 120
        self._hook_lines = self._wrap(self.topic_title, self.f_hook, tw)
        self._fact_data = []
        for f in self.facts:
            self._fact_data.append({
                "title_lines": self._wrap(f.get("title", ""), self.f_title, tw - 40),
                "detail_lines": self._wrap(f.get("detail", ""), self.f_detail, tw - 40),
                "number": f.get("number", ""),
                "unit": f.get("unit", ""),
                "image_path": f.get("image_path", ""),
            })
        self._outro_lines = self.outro_text.split("\n")

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
    def _ei(t): return min(1, max(0, t)) ** 2.5

    # ── Drawing helpers ──

    def _draw_stars(self, draw, t, density_mult=1.0, speed=1.0):
        cx, cy = self.W / 2, self.H / 2
        count = int(len(self._stars) * min(2.0, density_mult))
        for i, s in enumerate(self._stars):
            if i >= count:
                break
            d = s["dist0"] + t * 12 * speed
            d = d % (max(self.W, self.H) * 0.9)
            x = cx + math.cos(s["angle"]) * d
            y = cy + math.sin(s["angle"]) * d
            if x < -3 or x > self.W + 3 or y < -3 or y > self.H + 3:
                continue
            tw_ = 0.4 + 0.6 * ((math.sin(t * s["twk_spd"] + s["twk_ph"]) + 1) / 2)
            al = int(s["alpha"] * tw_ * min(1.0, density_mult))
            r = s["r"] * (0.7 + 0.3 * tw_)
            draw.ellipse([(x - r, y - r), (x + r, y + r)],
                         fill=(*s["color"], min(255, al)))

    def _draw_glitch(self, arr, intensity=1.0):
        """글리치 효과 — 수평 슬라이스 이동 + RGB 쉬프트."""
        if intensity < 0.05:
            return arr
        result = arr.copy()
        n_slices = max(1, int(len(self._glitch_slices) * intensity))
        for gl in self._glitch_slices[:n_slices]:
            y = gl["y"]
            h = max(1, int(gl["h"] * intensity))
            dx = int(gl["dx"] * intensity)
            y1 = max(0, y)
            y2 = min(self.H, y + h)
            if y1 >= y2:
                continue
            sl = arr[y1:y2].copy()
            if dx > 0:
                result[y1:y2, dx:] = sl[:, :self.W - dx]
            elif dx < 0:
                result[y1:y2, :self.W + dx] = sl[:, -dx:]
            # Color channel shift
            if gl["color_shift"] == "r" and y2 < self.H:
                shift = max(1, int(3 * intensity))
                safe_y2 = min(self.H, y2 + shift)
                if safe_y2 > y1 + shift:
                    result[y1 + shift:safe_y2, :, 0] = arr[y1:safe_y2 - shift, :, 0]
        return result

    def _draw_vignette(self, arr, strength=0.7):
        """비네팅 — 모서리 어둡게."""
        h, w = arr.shape[:2]
        Y, X = np.ogrid[:h, :w]
        cx, cy = w / 2, h / 2
        dist = np.sqrt((X - cx) ** 2 + (Y - cy) ** 2)
        max_dist = math.sqrt(cx ** 2 + cy ** 2)
        vignette = 1 - (dist / max_dist) ** 2 * strength
        vignette = np.clip(vignette, 0, 1)
        return (arr.astype(np.float32) * vignette[:, :, np.newaxis]).clip(0, 255).astype(np.uint8)

    def _deep_space_grade(self, arr):
        """딥 스페이스 컬러 그레이딩 — 블루 쉬프트 + 대비 증가."""
        f = arr.astype(np.float32)
        # Blue shift
        f[:, :, 2] = np.clip(f[:, :, 2] * 1.15 + 8, 0, 255)
        # Slight desaturate red
        f[:, :, 0] = np.clip(f[:, :, 0] * 0.92, 0, 255)
        # Contrast +10%
        mean = f.mean()
        f = np.clip((f - mean) * 1.1 + mean, 0, 255)
        return f.astype(np.uint8)

    def _draw_badge(self, draw, x, y, text, color=None):
        c = color or self.CYAN
        tw_ = self._tw(text, self.f_badge) + 24
        draw.rounded_rectangle([(x, y), (x + tw_, y + 36)],
                               radius=6, fill=(*c, 40), outline=(*c, 140), width=2)
        draw.text((x + 12, y + 4), text, font=self.f_badge, fill=(*c, 230))
        return tw_

    def _draw_countup(self, draw, number_str, unit, cx, cy, t_local, alpha=255):
        """카운트업 숫자 + 단위."""
        # Parse number
        try:
            target = float(number_str.replace(",", "").replace("억", ""))
            is_num = True
        except (ValueError, AttributeError):
            is_num = False

        prog = min(1, t_local / 1.2)
        prog = self._eo(prog)

        if is_num and prog < 1.0:
            current = target * prog
            if "," in number_str:
                display = f"{int(current):,}"
            elif "." in number_str:
                display = f"{current:.1f}"
            elif "억" in number_str:
                display = f"{int(current)}억"
            else:
                display = str(int(current))
        else:
            display = number_str

        # Number (amber, large)
        na = min(255, alpha)
        nw = self._tw(display, self.f_number)
        draw.text((cx - nw // 2, cy), display,
                  font=self.f_number, fill=(*self.AMBER, na))

        # Unit (smaller, below)
        if unit:
            uw = self._tw(unit, self.f_unit)
            draw.text((cx - uw // 2, cy + 95), unit,
                      font=self.f_unit, fill=(*self.AMBER, int(na * 0.8)))

    # ── Phase renderers ──

    def _render_hook(self, draw, t):
        """훅: 타이틀 + 줌인 + 글리치."""
        # Title
        lh = self._th("가", self.f_hook) + 16
        total_h = len(self._hook_lines) * lh
        start_y = (self.H - total_h) // 2 - 50

        for i, line in enumerate(self._hook_lines):
            # Pop bounce
            prog = self._eo((t - 0.2 - i * 0.15) / 0.5)
            if prog <= 0:
                continue
            scale = 0.5 + prog * 0.5
            al = int(255 * prog)
            tw_ = self._tw(line, self.f_hook)
            x = (self.W - tw_) // 2
            y = start_y + i * lh + int(20 * (1 - prog))
            draw.text((x, y), line, font=self.f_hook, fill=(*self.WHITE, al))

        # "알고 계셨나요?" subtitle
        if t > 1.5:
            sub = "알고 계셨나요?"
            sa = int(180 * self._eo((t - 1.5) / 0.5))
            sw = self._tw(sub, self.f_detail)
            draw.text(((self.W - sw) // 2, start_y + total_h + 30), sub,
                      font=self.f_detail, fill=(*self.CYAN, sa))

    def _render_fact_card(self, draw, idx, t_local):
        """팩트 카드 한 장."""
        if idx >= len(self._fact_data):
            return
        fact = self._fact_data[idx]

        # Zoom effect via alpha
        if t_local < self.trans_dur:
            prog = self._eo(t_local / self.trans_dur)
        elif t_local > self.card_dur - self.trans_dur:
            prog = 1 - self._eo((t_local - (self.card_dur - self.trans_dur)) / self.trans_dur)
        else:
            prog = 1.0
        alpha = int(255 * prog)

        # FACT badge
        badge_text = f"FACT {idx + 1:02d}"
        self._draw_badge(draw, 60, 420, badge_text, self.CYAN)

        # Title (lavender)
        lh = self._th("가", self.f_title) + 14
        for i, line in enumerate(self._hook_lines if not fact["title_lines"] else fact["title_lines"]):
            la = int(alpha * self._eo((t_local - 0.2 - i * 0.1) / 0.4))
            if la < 0: la = 0
            tw_ = self._tw(line, self.f_title)
            draw.text(((self.W - tw_) // 2, 490 + i * lh), line,
                      font=self.f_title, fill=(*self.LAVENDER, la))

        # Number + unit (center, countup)
        if fact["number"]:
            num_t = max(0, t_local - 0.5)
            self._draw_countup(draw, fact["number"], fact["unit"],
                               self.W // 2, 680, num_t, alpha)

        # Detail (bottom, small, opacity 70%)
        if fact["detail_lines"]:
            dlh = self._th("가", self.f_detail) + 10
            dy = 900
            for i, line in enumerate(fact["detail_lines"]):
                da = int(alpha * 0.7 * self._eo((t_local - 0.8 - i * 0.1) / 0.4))
                if da < 0: da = 0
                dw = self._tw(line, self.f_detail)
                draw.text(((self.W - dw) // 2, dy + i * dlh), line,
                          font=self.f_detail, fill=(*self.WHITE, da))

        # Progress bar (bottom)
        n = len(self.facts)
        bar_y = self.H - 80
        bar_w = self.W - 120
        bar_x = 60
        # Background
        draw.rounded_rectangle([(bar_x, bar_y), (bar_x + bar_w, bar_y + 4)],
                               radius=2, fill=(*self.DEEP_NAVY, 100))
        # Fill
        fill_w = int(bar_w * (idx + t_local / self.card_dur) / n)
        draw.rounded_rectangle([(bar_x, bar_y), (bar_x + fill_w, bar_y + 4)],
                               radius=2, fill=(*self.CYAN, int(alpha * 0.6)))

    def _render_outro(self, draw, t_local):
        """마무리 감성 텍스트."""
        lh = 65
        total_h = len(self._outro_lines) * lh
        start_y = (self.H - total_h) // 2

        for i, line in enumerate(self._outro_lines):
            la = int(230 * self._eo((t_local - 0.3 - i * 0.3) / 0.7))
            if la < 0: la = 0
            tw_ = self._tw(line, self.f_outro)
            slide = int(15 * (1 - self._eo((t_local - 0.3 - i * 0.3) / 0.7)))
            draw.text(((self.W - tw_) // 2, start_y + i * lh + slide), line,
                      font=self.f_outro, fill=(*self.WHITE, la))

        # Fade out at end
        if t_local > self.outro_dur - 1.5:
            fo = self._ei((t_local - (self.outro_dur - 1.5)) / 1.5)
            draw.rectangle([(0, 0), (self.W, self.H)],
                           fill=(*self.BG, int(200 * fo)))

    # ── Main render ──
    def _render(self, t):
        n = len(self.facts)
        cards_start = self.hook_dur
        outro_start = cards_start + self.cards_dur
        apply_glitch = False
        glitch_intensity = 0

        # BG
        arr = np.full((self.H, self.W, 3), self.BG, dtype=np.uint8)
        bg = Image.fromarray(arr, "RGB").convert("RGBA")
        ov = Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0))
        draw = ImageDraw.Draw(ov)

        # Determine phase
        if t < cards_start:
            # Hook
            star_density = 1.0
            star_speed = 1.0 + t * 0.5  # 줌인 가속
            self._draw_stars(draw, t, star_density, star_speed)
            self._render_hook(draw, t)
            # Glitch flash at ~1.8s
            if 1.7 < t < 1.9:
                apply_glitch = True
                glitch_intensity = 1.0 - abs(t - 1.8) / 0.1

        elif t < outro_start:
            # Fact cards
            lt = t - cards_start
            idx = min(int(lt / self.card_dur), n - 1)
            card_lt = lt - idx * self.card_dur

            self._draw_stars(draw, t, 0.6, 0.5)
            self._render_fact_card(draw, idx, card_lt)

            # Glitch at card transitions
            if card_lt < self.trans_dur:
                apply_glitch = True
                glitch_intensity = 0.5 * (1 - card_lt / self.trans_dur)
            elif card_lt > self.card_dur - self.trans_dur:
                apply_glitch = True
                glitch_intensity = 0.5 * ((card_lt - (self.card_dur - self.trans_dur)) / self.trans_dur)

        else:
            # Outro
            lt = t - outro_start
            star_density = 1.0 + lt * 0.5  # 밀도 증가
            self._draw_stars(draw, t, min(2.0, star_density), 0.3)
            self._render_outro(draw, lt)

        # Composite
        comp = Image.alpha_composite(bg, ov)
        result = np.array(comp.convert("RGB"))

        # Post-processing
        result = self._deep_space_grade(result)
        result = self._draw_vignette(result, strength=0.65)

        if apply_glitch and glitch_intensity > 0.05:
            result = self._draw_glitch(result, glitch_intensity)

        return result

    def generate(self, out="space_fact_bomb.mp4"):
        clip = VideoClip(lambda t: self._render(t), duration=self.duration).with_fps(self.FPS)
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        clip.write_videofile(str(out), codec="libx264", preset="medium",
                             bitrate="8000k", audio=False, logger="bar")
        sz = Path(out).stat().st_size / (1024 * 1024)
        print(f"\n✅ 생성 완료: {Path(out).resolve()}")
        print(f"   크기: {self.W}×{self.H} | 길이: {self.duration:.0f}초 | 파일: {sz:.1f}MB")
        return str(Path(out).resolve())


# ── Demo data ──
DEMO_FACTS = {
    "topic_title": "우주에서 가장\n거대한 것들",
    "facts": [
        {
            "title": "다이아몬드로 이루어진 행성",
            "number": "55",
            "unit": "캔크리 e",
            "detail": "탄소가 극도의 압력을 받아 행성 전체가 다이아몬드로 구성. 지구에서 40광년 거리.",
        },
        {
            "title": "우주 최대 구조물",
            "number": "100억",
            "unit": "광년",
            "detail": "헤라클레스-코로나 보레알리스 장성. 관측 가능한 우주의 10%를 차지하는 초거대 구조.",
        },
        {
            "title": "1초에 빛의 속도로 회전하는 별",
            "number": "716",
            "unit": "회전/초",
            "detail": "펄서 PSR J1748-2446ad. 적도 표면 속도가 빛의 24%에 달함.",
        },
        {
            "title": "우주에서 가장 차가운 곳",
            "number": "-272",
            "unit": "°C",
            "detail": "부메랑 성운. 절대영도보다 겨우 1도 높은 우주에서 가장 추운 자연 환경.",
        },
        {
            "title": "물이 가장 많은 곳",
            "number": "140조",
            "unit": "배 (지구 해양 대비)",
            "detail": "퀘이사 APM 08279+5255 주변. 120억 광년 거리에 거대한 수증기 구름 존재.",
        },
    ],
    "duration": 35.0,
}

def main():
    pa = argparse.ArgumentParser(description="우주 팩트 폭탄 쇼츠 생성기")
    pa.add_argument("--demo", action="store_true", help="데모 영상 생성")
    pa.add_argument("--out", default="output/demo_space_fact.mp4")
    pa.add_argument("--duration", type=float, default=35.0)
    a = pa.parse_args()

    if a.demo:
        print("💣 우주 팩트 폭탄 쇼츠 생성 중...")
        gen = SpaceFactBombGenerator(**DEMO_FACTS)
        gen.generate(a.out)
    else:
        print("--demo 플래그로 데모를 생성하세요")

if __name__ == "__main__":
    raise SystemExit(main())
