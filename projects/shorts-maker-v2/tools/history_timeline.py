#!/usr/bin/env python3
"""역사 사건 타임라인 쇼츠 생성기.

좌측 타임라인 바 + 우측 이벤트 카드, 세피아 톤.
이벤트 타입별 특수 효과 (war→빨강, discovery→금색, culture→기본).
"""

from __future__ import annotations

import argparse
import math
import os
import random
import warnings
from pathlib import Path
from typing import Any

warnings.filterwarnings("ignore", category=DeprecationWarning, module="PIL")

import numpy as np
from PIL import Image, ImageDraw, ImageFont

try:
    from moviepy import VideoClip
except ImportError:
    from moviepy.editor import VideoClip  # type: ignore


class HistoryTimelineGenerator:
    W, H = 1080, 1920
    FPS = 30
    MARGIN = 60
    # Colors
    BG = (26, 20, 8)
    GOLD = (212, 165, 116)
    TEXT = (189, 181, 164)
    WHITE = (255, 255, 255)
    WAR_RED = (196, 30, 58)
    DISC_GOLD = (255, 215, 0)
    TIMELINE_X = 100  # 타임라인 바 중심 X

    EVENT_DUR = 6.0
    INTRO = 3.0
    OUTRO = 4.0

    def __init__(self, title: str, events: list[dict[str, Any]]):
        self.title = title
        self.events = events
        self.n = len(events)
        self.duration = self.INTRO + self.n * self.EVENT_DUR + self.OUTRO
        self._load_fonts()
        self._bg = self._mk_bg()
        self._vignette = self._mk_vignette()
        # 먼지 파티클
        random.seed(7)
        self._dust = [
            {
                "x": random.randint(0, self.W),
                "y": random.randint(0, self.H),
                "r": random.uniform(1, 3),
                "vx": random.uniform(-8, 8),
                "vy": random.uniform(-15, -5),
                "a": random.randint(30, 90),
                "ph": random.uniform(0, math.tau),
            }
            for _ in range(8)
        ]
        # 이벤트 텍스트 래핑
        tw = self.W - 200
        for e in self.events:
            e["_desc"] = self._wrap(e.get("description", ""), self.f_body, tw)
            e["_title"] = self._wrap(e.get("title", ""), self.f_title, tw)

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

        self.f_year = _l(sb, 90)
        self.f_title = _l(se, 56)
        self.f_body = _l(sa, 36)
        self.f_intro = _l(sb, 64)
        self.f_small = _l(sa, 32)

    # ── Background ──
    def _mk_bg(self):
        a = np.zeros((self.H, self.W, 4), dtype=np.uint8)
        for y in range(self.H):
            r = y / self.H
            a[y, :, 0] = int(self.BG[0] * (1 - r * 0.3))
            a[y, :, 1] = int(self.BG[1] * (1 - r * 0.3))
            a[y, :, 2] = int(self.BG[2] * (1 - r * 0.3))
            a[y, :, 3] = 255
        # 양피지 텍스처 (노이즈)
        noise = np.random.RandomState(42).randint(0, 30, (self.H, self.W), dtype=np.uint8)
        a[:, :, 0] = np.clip(a[:, :, 0].astype(int) + noise * 0.1, 0, 255).astype(np.uint8)
        a[:, :, 1] = np.clip(a[:, :, 1].astype(int) + noise * 0.08, 0, 255).astype(np.uint8)
        return a.astype(np.float32)

    def _mk_vignette(self):
        ys = np.arange(self.H, dtype=np.float32)
        xs = np.arange(self.W, dtype=np.float32)
        yy, xx = np.meshgrid(ys, xs, indexing="ij")
        cx, cy = self.W / 2, self.H / 2
        d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / math.hypot(cx, cy)
        al = np.where(d > 0.5, np.clip((d - 0.5) / 0.5 * 200, 0, 200), 0).astype(np.uint8)
        a = np.zeros((self.H, self.W, 4), dtype=np.uint8)
        a[:, :, 3] = al
        return Image.fromarray(a, "RGBA")

    def _get_bg(self, tint=None, tint_a=0.0):
        bg = self._bg.copy()
        bg[:, :, :3] *= 0.8  # base darken
        if tint and tint_a > 0:
            ta = np.array(tint, dtype=np.float32)
            bg[:, :, 0] = bg[:, :, 0] * (1 - tint_a) + ta[0] * tint_a
            bg[:, :, 1] = bg[:, :, 1] * (1 - tint_a) + ta[1] * tint_a
            bg[:, :, 2] = bg[:, :, 2] * (1 - tint_a) + ta[2] * tint_a
        return Image.fromarray(np.clip(bg, 0, 255).astype(np.uint8), "RGBA")

    # ── Helpers ──
    @staticmethod
    def _wrap(text, font, mw):
        lines, cur = [], ""
        for w in text.split():
            t = f"{cur} {w}".strip()
            if font.getbbox(t)[2] - font.getbbox(t)[0] <= mw:
                cur = t
            else:
                if cur:
                    lines.append(cur)
                cur = w
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

    def _sepia_color(self, etype):
        if etype == "war":
            return self.WAR_RED
        if etype == "discovery":
            return self.DISC_GOLD
        return self.WHITE

    # ── Drawing ──
    def _draw_dust(self, draw, t):
        for p in self._dust:
            x = (p["x"] + p["vx"] * t + math.sin(t + p["ph"]) * 15) % self.W
            y = (p["y"] + p["vy"] * t) % self.H
            fl = 0.5 + 0.5 * math.sin(t * 1.5 + p["ph"])
            al = int(p["a"] * fl)
            r = p["r"]
            draw.ellipse([(x - r, y - r), (x + r, y + r)], fill=(200, 180, 150, al))

    def _draw_timeline_bar(self, draw, active_idx, t):
        """좌측 세로 타임라인 바 + 마커."""
        x = self.TIMELINE_X
        y_start, y_end = 200, self.H - 200
        # 메인 라인
        draw.line([(x, y_start), (x, y_end)], fill=(*self.GOLD, 80), width=2)
        if self.n == 0:
            return
        # 마커
        for i in range(self.n):
            r_ratio = i / max(1, self.n - 1) if self.n > 1 else 0.5
            my = int(y_start + (y_end - y_start) * r_ratio)
            mr = 8
            is_active = i == active_idx
            if is_active:
                pulse = 0.5 + 0.5 * math.sin(t * 4)
                glow_r = int(mr + 6 * pulse)
                draw.ellipse([(x - glow_r, my - glow_r), (x + glow_r, my + glow_r)], fill=(*self.GOLD, int(60 * pulse)))
            fill_a = 255 if is_active else 100
            draw.ellipse([(x - mr, my - mr), (x + mr, my + mr)], fill=(*self.GOLD, fill_a))

    def _draw_event_card(self, draw, ev, y_base, alpha, etype):
        """우측 이벤트 카드."""
        x = 160
        col = self._sepia_color(etype)
        # 연도 (배경처럼 큰 글자)
        year = str(ev.get("year", ""))
        ya = int(alpha * 0.3)
        if ya > 0:
            draw.text((x, y_base), year, font=self.f_year, fill=(*self.GOLD, ya))
        # 이벤트명
        title_y = y_base + 100
        lh_t = self._th("가", self.f_title) + 12
        for i, l in enumerate(ev["_title"]):
            la = int(alpha * min(1, 1))
            draw.text((x, title_y + i * lh_t), l, font=self.f_title, fill=(*col, la))
        # 설명
        desc_y = title_y + len(ev["_title"]) * lh_t + 20
        lh_d = self._th("가", self.f_body) + 10
        for i, l in enumerate(ev["_desc"]):
            draw.text((x, desc_y + i * lh_d), l, font=self.f_body, fill=(*self.TEXT, int(alpha * 0.85)))

    # ── Intro / Outro ──
    def _draw_intro(self, draw, t):
        a = int(255 * self._eo(t / 1.5))
        tw_ = self._tw(self.title, self.f_intro)
        draw.text(((self.W - tw_) // 2, self.H // 2 - 60), self.title, font=self.f_intro, fill=(255, 255, 255, a))
        # 구분선
        la = int(180 * self._eo((t - 0.5) / 1.0))
        if la > 0:
            lw = 120
            lx = (self.W - lw) // 2
            draw.line([(lx, self.H // 2 + 30), (lx + lw, self.H // 2 + 30)], fill=(*self.GOLD, la), width=2)

    def _draw_outro(self, draw, t):
        fade = 1 - self._eo(t / 3.0)
        a = int(200 * fade)
        txt = "역사는 반복된다"
        tw_ = self._tw(txt, self.f_intro)
        draw.text(((self.W - tw_) // 2, self.H // 2 - 40), txt, font=self.f_intro, fill=(255, 255, 255, a))

    # ── Render ──
    def _render(self, t):
        # Phase detection
        if t < self.INTRO:
            return self._render_intro(t)
        event_t = t - self.INTRO
        if event_t >= self.n * self.EVENT_DUR:
            return self._render_outro(t - self.INTRO - self.n * self.EVENT_DUR)
        idx = min(int(event_t / self.EVENT_DUR), self.n - 1)
        local_t = event_t - idx * self.EVENT_DUR
        return self._render_event(idx, local_t, t)

    def _render_intro(self, t):
        0.3 + 0.2 * self._eo(t / 2)
        bg = self._get_bg()
        ov = Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        self._draw_intro(d, t)
        self._draw_dust(d, t)
        f = Image.alpha_composite(bg, ov)
        f = Image.alpha_composite(f, self._vignette)
        return np.array(f.convert("RGB"))

    def _render_event(self, idx, lt, gt):
        ev = self.events[idx]
        etype = ev.get("type", "culture")
        # Background tint
        tint, tint_a = None, 0
        if etype == "war" and lt < 0.5:
            tint, tint_a = (80, 10, 15), 0.15 * (1 - lt / 0.5)
        elif etype == "discovery" and lt < 0.3:
            tint, tint_a = (60, 50, 10), 0.1 * (1 - lt / 0.3)
        bg = self._get_bg(tint, tint_a)
        ov = Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        # Timeline bar
        self._draw_timeline_bar(d, idx, gt)
        # Event card: fade in (0-1s), hold, fade out (last 1s)
        if lt < 1.0:
            prog = self._eo(lt / 1.0)
        elif lt > self.EVENT_DUR - 1.0:
            prog = 1 - self._eo((lt - (self.EVENT_DUR - 1.0)) / 1.0)
        else:
            prog = 1.0
        alpha = int(255 * prog)
        slide_y = int(20 * (1 - self._eo(lt / 0.8)))
        # Y position (center-ish)
        y_base = 400 + slide_y
        # Last event zoom hint
        is_last = (idx == self.n - 1) and lt > self.EVENT_DUR - 3
        if is_last:
            # subtle zoom via larger alpha hold
            alpha = 255
        self._draw_event_card(d, ev, y_base, alpha, etype)
        self._draw_dust(d, gt)
        f = Image.alpha_composite(bg, ov)
        f = Image.alpha_composite(f, self._vignette)
        return np.array(f.convert("RGB"))

    def _render_outro(self, t):
        bg = self._get_bg()
        ov = Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        self._draw_timeline_bar(d, -1, t)
        self._draw_outro(d, t)
        self._draw_dust(d, t + 100)
        f = Image.alpha_composite(bg, ov)
        f = Image.alpha_composite(f, self._vignette)
        return np.array(f.convert("RGB"))

    def generate(self, out="history_timeline.mp4"):
        clip = VideoClip(lambda t: self._render(t), duration=self.duration).with_fps(self.FPS)
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        clip.write_videofile(str(out), codec="libx264", preset="medium", bitrate="8000k", audio=False, logger="bar")
        print(f"\n✅ 생성 완료: {Path(out).resolve()}")
        print(f"   크기: {self.W}×{self.H} | 길이: {self.duration:.0f}초 | 이벤트: {self.n}개 | FPS: {self.FPS}")
        return str(Path(out).resolve())


DEMO_DATA = {
    "title": "한국 근현대사 주요 사건",
    "events": [
        {
            "year": 1919,
            "title": "3·1 운동",
            "description": "일제 강점기 최대 규모의 독립운동. 전국적으로 200만 명 이상이 참여한 비폭력 만세 시위.",
            "type": "culture",
        },
        {
            "year": 1945,
            "title": "광복",
            "description": "35년간의 일본 식민 지배가 종결. 8월 15일 조선이 해방되었다.",
            "type": "discovery",
        },
        {
            "year": 1950,
            "title": "한국전쟁 발발",
            "description": "6월 25일 북한의 남침으로 시작된 전쟁. 3년간 약 300만 명의 민간인 사상자 발생.",
            "type": "war",
        },
        {
            "year": 1988,
            "title": "서울 올림픽",
            "description": "대한민국의 경제 성장과 민주화를 전 세계에 알린 역사적 순간.",
            "type": "culture",
        },
    ],
}


def main():
    pa = argparse.ArgumentParser(description="역사 타임라인 쇼츠 생성기")
    pa.add_argument("--demo", action="store_true", help="한국 근현대사 데모")
    pa.add_argument("--out", type=str, default="history_timeline.mp4")
    a = pa.parse_args()
    if a.demo:
        print("📜 한국 근현대사 타임라인 데모 생성 중...")
        HistoryTimelineGenerator(**DEMO_DATA).generate(a.out)
        return 0
    print("[INFO] --demo로 먼저 시도하세요. 프로그래밍 방식 사용은 Python import 권장.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
