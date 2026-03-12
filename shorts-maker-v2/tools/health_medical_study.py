#!/usr/bin/env python3
"""의학 연구 결과 인포그래픽 쇼츠 생성기.

클린 메디컬 톤 — 연구 소개 → 핵심 발견 카드 + 바 차트 → 결론/권고.
신뢰감 있는 다큐멘터리 스타일.
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


class MedicalStudyGenerator:
    W, H = 1080, 1920
    FPS = 30
    MG = 60

    # Clean medical palette
    BG = (8, 20, 16)              # 다크 그린-블랙
    MINT = (52, 211, 153)         # #34D399
    BLUE = (59, 130, 246)         # #3B82F6
    WHITE = (240, 248, 245)
    GRAY = (100, 116, 110)
    CARD_BG = (14, 30, 24)
    CARD_BORDER = (52, 211, 153)
    BAR_GRAY = (60, 70, 65)
    AMBER = (245, 158, 11)

    def __init__(self, hook: str = "최신 연구가 밝혀낸\n충격적 사실",
                 study_source: str = "",
                 topic: str = "",
                 sample_size: str = "",
                 study_period: str = "",
                 findings: list[dict] | None = None,
                 conclusion: str = "",
                 recommendation: str = "",
                 disclaimer: str = "※ 이 영상은 연구 결과를 소개하는 목적이며,\n전문 의료인과의 상담을 권장합니다.",
                 duration: float = 35.0):
        """
        Args:
            findings: [{"title": "...", "stat": "72%", "comparison": {"label_a": "섭취군", "val_a": 72, "label_b": "비섭취군", "val_b": 31}}]
        """
        self.hook = hook
        self.study_source = study_source
        self.topic = topic
        self.sample_size = sample_size
        self.study_period = study_period
        self.findings = (findings or [])[:4]
        self.conclusion = conclusion
        self.recommendation = recommendation
        self.disclaimer = disclaimer
        n = len(self.findings)
        self.duration = max(25, min(50, duration))

        # Phase timing
        self.hook_dur = 2.5
        self.study_dur = 6.0
        self.concl_dur = 6.0
        self.findings_dur = self.duration - self.hook_dur - self.study_dur - self.concl_dur
        self.finding_dur = self.findings_dur / max(1, n)

        self._load_fonts()
        self._preprocess()
        self._grid = self._make_grid()

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
        self.f_hook = _l(sb, 62)
        self.f_title = _l(sb, 48)
        self.f_stat = _l(sb, 80)
        self.f_body = _l(sa, 34)
        self.f_source = _l(sa, 30)
        self.f_badge = _l(sb, 26)
        self.f_bar = _l(sb, 28)
        self.f_outro = _l(sb, 44)
        self.f_small = _l(sa, 22)
        self.f_num = _l(sb, 36)

    def _preprocess(self):
        tw = self.W - self.MG * 2 - 40
        self._hook_lines = self.hook.split("\n")
        self._topic_lines = self._wrap(self.topic, self.f_title, tw)
        self._concl_lines = self._wrap(self.conclusion, self.f_body, tw)
        self._rec_lines = self._wrap(self.recommendation, self.f_body, tw) if self.recommendation else []
        self._disc_lines = self.disclaimer.split("\n")
        self._finding_data = []
        for f in self.findings:
            self._finding_data.append({
                "title": f.get("title", ""),
                "stat": f.get("stat", ""),
                "title_lines": self._wrap(f.get("title", ""), self.f_body, tw - 40),
                "comparison": f.get("comparison"),
            })

    def _make_grid(self):
        """Subtle grid pattern (medical/scientific feel)."""
        pat = Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0))
        draw = ImageDraw.Draw(pat)
        step = 60
        for x in range(0, self.W, step):
            draw.line([(x, 0), (x, self.H)], fill=(52, 211, 153, 6), width=1)
        for y in range(0, self.H, step):
            draw.line([(0, y), (self.W, y)], fill=(52, 211, 153, 6), width=1)
        return np.array(pat)

    @staticmethod
    def _wrap(text, font, mw):
        lines, cur = [], ""
        for seg in text.replace("\n", " ").split(" "):
            if not seg: continue
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
        b = f.getbbox(t); return b[2] - b[0] if b else 0
    def _th(self, t, f):
        b = f.getbbox(t); return b[3] - b[1] if b else 0
    @staticmethod
    def _eo(t): return 1 - (1 - min(1, max(0, t))) ** 3

    def _draw_badge(self, draw, x, y, text, color=None):
        c = color or self.MINT
        tw_ = self._tw(text, self.f_badge) + 24
        draw.rounded_rectangle([(x, y), (x + tw_, y + 34)],
                               radius=6, fill=(*c, 30), outline=(*c, 120), width=1)
        draw.text((x + 12, y + 4), text, font=self.f_badge, fill=(*c, 220))
        return tw_

    def _draw_bar_chart(self, draw, x, y, w, comparison, progress):
        """비교 바 차트 — 2개 수평 바."""
        if not comparison:
            return 0
        la = comparison.get("label_a", "A")
        va = comparison.get("val_a", 50)
        lb = comparison.get("label_b", "B")
        vb = comparison.get("val_b", 30)
        max_val = max(va, vb, 1)

        bar_h = 36
        gap = 16
        label_w = 120
        bar_area = w - label_w - 80

        # Bar A (mint)
        ay = y
        draw.text((x, ay + 4), la, font=self.f_bar, fill=(*self.WHITE, 200))
        bar_x = x + label_w
        bar_w_a = int(bar_area * (va / max_val) * min(1, progress))
        draw.rounded_rectangle([(bar_x, ay), (bar_x + bar_area, ay + bar_h)],
                               radius=6, fill=(*self.BAR_GRAY, 80))
        if bar_w_a > 5:
            draw.rounded_rectangle([(bar_x, ay), (bar_x + bar_w_a, ay + bar_h)],
                                   radius=6, fill=(*self.MINT, 200))
        # Value
        val_text = f"{int(va * min(1, progress))}%"
        draw.text((bar_x + bar_w_a + 10, ay + 3), val_text,
                  font=self.f_bar, fill=(*self.MINT, int(220 * min(1, progress))))

        # Bar B (gray)
        by = ay + bar_h + gap
        draw.text((x, by + 4), lb, font=self.f_bar, fill=(*self.WHITE, 200))
        bar_w_b = int(bar_area * (vb / max_val) * min(1, progress))
        draw.rounded_rectangle([(bar_x, by), (bar_x + bar_area, by + bar_h)],
                               radius=6, fill=(*self.BAR_GRAY, 80))
        if bar_w_b > 5:
            draw.rounded_rectangle([(bar_x, by), (bar_x + bar_w_b, by + bar_h)],
                                   radius=6, fill=(*self.GRAY, 180))
        val_text_b = f"{int(vb * min(1, progress))}%"
        draw.text((bar_x + bar_w_b + 10, by + 3), val_text_b,
                  font=self.f_bar, fill=(*self.GRAY, int(200 * min(1, progress))))

        return bar_h * 2 + gap + 20

    def _countup_text(self, draw, stat_str, cx, cy, t_local, alpha=255):
        """카운트업 숫자 텍스트."""
        try:
            num_part = ""
            unit_part = ""
            for i, c in enumerate(stat_str):
                if c.isdigit() or c in ".,":
                    num_part += c
                else:
                    unit_part = stat_str[i:]
                    break
            target = float(num_part.replace(",", "")) if num_part else 0
            prog = min(1, t_local / 1.0)
            prog = self._eo(prog)
            current = target * prog
            if "," in num_part:
                display = f"{int(current):,}"
            elif "." in num_part:
                display = f"{current:.1f}"
            else:
                display = str(int(current))
            full = display + unit_part
        except (ValueError, AttributeError):
            full = stat_str

        tw_ = self._tw(full, self.f_stat)
        draw.text((cx - tw_ // 2, cy), full,
                  font=self.f_stat, fill=(*self.MINT, min(255, alpha)))

    # ── Phase renderers ──

    def _render_hook(self, draw, t):
        lh = 75
        total_h = len(self._hook_lines) * lh
        sy = (self.H - total_h) // 2 - 30

        for i, line in enumerate(self._hook_lines):
            prog = self._eo((t - 0.15 - i * 0.12) / 0.5)
            if prog <= 0: continue
            al = int(250 * prog)
            bounce = int(12 * (1 - prog))
            tw_ = self._tw(line, self.f_hook)
            draw.text(((self.W - tw_) // 2, sy + i * lh + bounce), line,
                      font=self.f_hook, fill=(*self.WHITE, al))

    def _render_study_intro(self, draw, t_local):
        """연구 소개 화면."""
        # Source badge
        if self.study_source and t_local > 0.2:
            sa = int(200 * self._eo((t_local - 0.2) / 0.4))
            self._draw_badge(draw, self.MG, 400, f"📋 {self.study_source}", self.BLUE)

        # Topic
        if t_local > 0.5:
            lh = self._th("가", self.f_title) + 14
            for i, line in enumerate(self._topic_lines):
                la = int(240 * self._eo((t_local - 0.5 - i * 0.12) / 0.5))
                if la < 0: la = 0
                tw_ = self._tw(line, self.f_title)
                draw.text(((self.W - tw_) // 2, 480 + i * lh), line,
                          font=self.f_title, fill=(*self.WHITE, la))

        # Sample size & period (countup)
        info_y = 700
        if self.sample_size and t_local > 1.5:
            self._draw_badge(draw, self.MG, info_y, "👥 참여자", self.MINT)
            sa = int(220 * self._eo((t_local - 1.5) / 0.5))
            draw.text((self.MG + 130, info_y + 2), self.sample_size,
                      font=self.f_num, fill=(*self.MINT, sa))

        if self.study_period and t_local > 2.0:
            self._draw_badge(draw, self.MG, info_y + 50, "📅 기간", self.MINT)
            pa = int(220 * self._eo((t_local - 2.0) / 0.5))
            draw.text((self.MG + 130, info_y + 52), self.study_period,
                      font=self.f_num, fill=(*self.MINT, pa))

    def _render_finding(self, draw, idx, t_local):
        """핵심 발견 카드."""
        if idx >= len(self._finding_data):
            return
        fd = self._finding_data[idx]

        # Exit
        if t_local > self.finding_dur - 0.3:
            ep = self._eo((t_local - (self.finding_dur - 0.3)) / 0.3)
            alpha_mult = 1 - ep
        else:
            alpha_mult = 1.0

        # Card background
        card_x, card_y = self.MG - 10, 380
        card_w = self.W - self.MG * 2 + 20
        card_h = 650
        ca = int(255 * self._eo(t_local / 0.4) * alpha_mult)

        # Card bg
        draw.rounded_rectangle([(card_x, card_y), (card_x + card_w, card_y + card_h)],
                               radius=14, fill=(*self.CARD_BG, ca))
        draw.rounded_rectangle([(card_x, card_y), (card_x + card_w, card_y + card_h)],
                               radius=14, outline=(*self.CARD_BORDER, int(ca * 0.3)), width=1)

        # Badge
        badge_text = f"핵심 발견 {idx + 1:02d}"
        self._draw_badge(draw, card_x + 20, card_y + 20, badge_text, self.MINT)

        # Title
        lh = self._th("가", self.f_body) + 12
        for i, line in enumerate(fd["title_lines"]):
            la = int(ca * self._eo((t_local - 0.3 - i * 0.1) / 0.4))
            if la < 0: la = 0
            draw.text((card_x + 30, card_y + 75 + i * lh), line,
                      font=self.f_body, fill=(*self.WHITE, la))

        # Stat number (big, countup)
        if fd["stat"] and t_local > 0.6:
            st = max(0, t_local - 0.6)
            stat_y = card_y + 75 + len(fd["title_lines"]) * lh + 20
            self._countup_text(draw, fd["stat"], self.W // 2, stat_y, st,
                               int(ca * alpha_mult))

        # Bar chart
        if fd["comparison"] and t_local > 1.0:
            bar_prog = self._eo((t_local - 1.0) / 1.5)
            bar_y = card_y + 75 + len(fd["title_lines"]) * lh + 130
            self._draw_bar_chart(draw, card_x + 30, bar_y,
                                 card_w - 60, fd["comparison"],
                                 bar_prog * alpha_mult)

        # Progress dots
        n = len(self.findings)
        dot_y = card_y + card_h + 20
        dot_spacing = 20
        dots_w = n * dot_spacing
        dot_sx = (self.W - dots_w) // 2
        for i in range(n):
            r = 4 if i == idx else 3
            c = self.MINT if i == idx else self.GRAY
            al = int((200 if i == idx else 80) * alpha_mult)
            cx_ = dot_sx + i * dot_spacing + 5
            draw.ellipse([(cx_ - r, dot_y - r), (cx_ + r, dot_y + r)],
                         fill=(*c, al))

    def _render_conclusion(self, draw, t_local):
        """결론 + 권고."""
        # "연구진 결론" badge
        if t_local > 0.2:
            self._draw_badge(draw, self.MG, 450, "🔬 연구 결론", self.MINT)

        # Conclusion text
        lh = self._th("가", self.f_body) + 14
        for i, line in enumerate(self._concl_lines):
            la = int(230 * self._eo((t_local - 0.5 - i * 0.12) / 0.5))
            if la < 0: la = 0
            draw.text((self.MG + 10, 510 + i * lh), line,
                      font=self.f_body, fill=(*self.WHITE, la))

        # Recommendation
        if self._rec_lines and t_local > 2.0:
            rec_y = 510 + len(self._concl_lines) * lh + 30
            self._draw_badge(draw, self.MG, rec_y, "💡 권고 사항", self.AMBER)
            for i, line in enumerate(self._rec_lines):
                la = int(200 * self._eo((t_local - 2.3 - i * 0.1) / 0.4))
                if la < 0: la = 0
                draw.text((self.MG + 10, rec_y + 50 + i * lh), line,
                          font=self.f_body, fill=(*self.WHITE, la))

        # Disclaimer
        if t_local > 3.0:
            da = int(100 * self._eo((t_local - 3.0) / 0.5))
            for i, dl in enumerate(self._disc_lines):
                dw = self._tw(dl, self.f_small)
                draw.text(((self.W - dw) // 2, self.H - 160 + i * 28), dl,
                          font=self.f_small, fill=(*self.WHITE, da))

        # Fade out
        if t_local > self.concl_dur - 1.0:
            fo = (t_local - (self.concl_dur - 1.0)) / 1.0
            draw.rectangle([(0, 0), (self.W, self.H)],
                           fill=(*self.BG, int(200 * fo)))

    def _medical_grade(self, arr):
        """Clean medical color grading."""
        f = arr.astype(np.float32)
        # Green shift
        f[:, :, 1] = np.clip(f[:, :, 1] * 1.03 + 2, 0, 255)
        # Slight desaturate
        gray = 0.299 * f[:, :, 0] + 0.587 * f[:, :, 1] + 0.114 * f[:, :, 2]
        for c in range(3):
            f[:, :, c] = f[:, :, c] * 0.92 + gray * 0.08
        # Contrast +5%
        mean = f.mean()
        f = np.clip((f - mean) * 1.05 + mean, 0, 255)
        return f.astype(np.uint8)

    # ── Main render ──
    def _render(self, t):
        study_start = self.hook_dur
        findings_start = study_start + self.study_dur
        concl_start = findings_start + self.findings_dur

        bg = Image.new("RGBA", (self.W, self.H), (*self.BG, 255))
        grid = Image.fromarray(self._grid, "RGBA")
        bg = Image.alpha_composite(bg, grid)
        ov = Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0))
        draw = ImageDraw.Draw(ov)

        if t < study_start:
            self._render_hook(draw, t)
        elif t < findings_start:
            self._render_study_intro(draw, t - study_start)
        elif t < concl_start:
            lt = t - findings_start
            idx = min(int(lt / self.finding_dur), len(self.findings) - 1)
            f_lt = lt - idx * self.finding_dur
            self._render_finding(draw, idx, f_lt)
        else:
            self._render_conclusion(draw, t - concl_start)

        comp = Image.alpha_composite(bg, ov)
        result = np.array(comp.convert("RGB"))
        result = self._medical_grade(result)
        return result

    def generate(self, out="medical_study.mp4"):
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
    "hook": "최신 연구가 밝혀낸\n충격적 사실",
    "study_source": "하버드 의대 · JAMA Internal Medicine 2024",
    "topic": "하루 30분 걷기가 심혈관 질환 사망률을 획기적으로 낮춘다",
    "sample_size": "41,370명",
    "study_period": "11.1년 추적 관찰",
    "findings": [
        {
            "title": "하루 30분 이상 걷는 그룹의 심혈관 질환 사망 위험이 현저히 감소",
            "stat": "35%",
            "comparison": {
                "label_a": "걷기 그룹",  "val_a": 35,
                "label_b": "비활동 그룹", "val_b": 100,
            },
        },
        {
            "title": "전체 사망률도 유의미하게 낮아지는 결과를 보임",
            "stat": "21%",
            "comparison": {
                "label_a": "걷기 그룹",  "val_a": 21,
                "label_b": "비활동 그룹", "val_b": 100,
            },
        },
        {
            "title": "강도보다 '규칙성'이 더 중요한 것으로 밝혀짐",
            "stat": "92%",
            "comparison": {
                "label_a": "매일 걷기", "val_a": 92,
                "label_b": "주 1회 운동", "val_b": 58,
            },
        },
    ],
    "conclusion": "연구진은 하루 30분의 가벼운 걷기만으로도 심혈관 건강에 극적인 개선 효과가 있다고 결론지었습니다.",
    "recommendation": "특별한 장비 없이, 오늘부터 점심시간에 30분만 걸어보세요.",
    "duration": 35.0,
}


def main():
    pa = argparse.ArgumentParser(description="의학 연구 인포그래픽 쇼츠")
    pa.add_argument("--demo", action="store_true")
    pa.add_argument("--out", default="output/demo_medical_study.mp4")
    a = pa.parse_args()

    if a.demo:
        print("🔬 의학 연구 인포그래픽 쇼츠 생성 중...")
        gen = MedicalStudyGenerator(**DEMO_DATA)
        gen.generate(a.out)
    else:
        print("--demo 플래그로 데모를 생성하세요")

if __name__ == "__main__":
    raise SystemExit(main())
