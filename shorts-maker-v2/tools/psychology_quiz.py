#!/usr/bin/env python3
"""심리학 퀴즈 인터랙티브 쇼츠 생성기.

Phase 1 (0-5s)  : 질문 + 원형 카운트다운
Phase 2 (5-10s) : 선택지 A/B 슬라이드인
Phase 3 (10-25s): 정답 + 통계 바 + 해설
Phase 4 (25-30s): 반전 + CTA
"""
from __future__ import annotations
import argparse, math, os, re, warnings
from pathlib import Path
warnings.filterwarnings("ignore", category=DeprecationWarning, module="PIL")

import numpy as np
from PIL import Image, ImageDraw, ImageFont
try:
    from moviepy import VideoClip
except ImportError:
    from moviepy.editor import VideoClip  # type: ignore


class PsychologyQuizGenerator:
    BG_PURPLE = (26, 10, 30)
    BG_BLACK = (5, 2, 8)
    WHITE = (255, 255, 255)
    LAVENDER = (232, 121, 249)
    AMBER = (245, 158, 11)
    PINK = (251, 113, 133)
    CARD_BG = (45, 27, 51, 204)
    GRAY = (80, 70, 90)
    W, H = 1080, 1920
    FPS = 30
    MARGIN = 60
    P1, P2, P3, P4 = 5.0, 10.0, 25.0, 30.0

    PSYCH_TERMS = {
        "인지","편향","효과","이론","심리","뇌","행동","판단","선택",
        "손실","회피","위험","프레이밍","앵커링","확증","동조","권위",
        "휴리스틱","전망","카너먼","트버스키","넛지","프라이밍",
        "확실성","기대값","본능","경향",
    }

    def __init__(self, question:str, option_a:str, option_b:str,
                 answer:str, stat_percent:int, explanation:str,
                 twist_text:str="", cta_text:str="다음 퀴즈도 도전해보세요!"):
        self.question=question; self.option_a=option_a; self.option_b=option_b
        self.answer=answer.upper(); self.stat_pct=stat_percent
        self.explanation=explanation; self.twist_text=twist_text; self.cta_text=cta_text
        self._load_fonts()
        self._bg_grad=self._mk_gradient()
        self._bg_arr=np.array(self._bg_grad,dtype=np.float32)
        self._vignette=self._mk_vignette()
        tw=self.W-self.MARGIN*2-40
        self._q_lines=self._wrap(question,self.f_question,tw)
        self._exp_lines=self._wrap(explanation,self.f_body,tw)
        self._twist_lines=self._wrap(twist_text,self.f_body,tw) if twist_text else []

    # ── Fonts ──
    def _load_fonts(self):
        dirs=[Path("C:/Windows/Fonts"),Path(os.path.expanduser("~/AppData/Local/Microsoft/Windows/Fonts"))]
        def _f(ns,fb="malgun.ttf"):
            for d in dirs:
                for n in ns:
                    if(d/n).exists(): return str(d/n)
            for d in dirs:
                if(d/fb).exists(): return str(d/fb)
            return ""
        se=_f(["NanumMyeongjo.ttf","batang.ttc"])
        sb=_f(["NanumGothicBold.ttf","NanumGothicExtraBold.ttf","malgunbd.ttf"])
        sa=_f(["NanumGothic.ttf","malgun.ttf"])
        def _l(p,s):
            return ImageFont.truetype(p,s) if p else ImageFont.load_default(s)
        self.f_question=_l(sb,64); self.f_option=_l(sa,44); self.f_body=_l(sa,40)
        self.f_bold=_l(sb,52); self.f_stat=_l(sb,56); self.f_countdown=_l(sb,60)
        self.f_small=_l(sa,34); self.f_badge=_l(sb,36); self.f_turn=_l(sb,72)
        self.f_cta=_l(sb,48); self.f_quote=_l(se,46)

    # ── Background / Vignette ──
    def _mk_gradient(self):
        a=np.zeros((self.H,self.W,4),dtype=np.uint8)
        for y in range(self.H):
            r=y/self.H
            a[y,:,0]=int(self.BG_PURPLE[0]*(1-r)+self.BG_BLACK[0]*r)
            a[y,:,1]=int(self.BG_PURPLE[1]*(1-r)+self.BG_BLACK[1]*r)
            a[y,:,2]=int(self.BG_PURPLE[2]*(1-r)+self.BG_BLACK[2]*r)
            a[y,:,3]=255
        return Image.fromarray(a,"RGBA")

    def _mk_vignette(self):
        ys=np.arange(self.H,dtype=np.float32); xs=np.arange(self.W,dtype=np.float32)
        yy,xx=np.meshgrid(ys,xs,indexing="ij")
        cx,cy=self.W/2,self.H/2
        d=np.sqrt((xx-cx)**2+(yy-cy)**2)/math.hypot(cx,cy)
        al=np.where(d>0.55,np.clip((d-0.55)/0.45*180,0,255),0).astype(np.uint8)
        a=np.zeros((self.H,self.W,4),dtype=np.uint8); a[:,:,3]=al
        return Image.fromarray(a,"RGBA")

    def _get_bg(self,br=0.5):
        bg=self._bg_arr.copy(); bg[:,:,:3]*=br
        return Image.fromarray(np.clip(bg,0,255).astype(np.uint8),"RGBA")

    # ── Text Helpers ──
    @staticmethod
    def _wrap(text,font,mw):
        lines,cur=[],""
        for w in text.split():
            t=f"{cur} {w}".strip()
            if font.getbbox(t)[2]-font.getbbox(t)[0]<=mw: cur=t
            else:
                if cur: lines.append(cur)
                cur=w
        if cur: lines.append(cur)
        return lines

    def _tw(self,t,f): b=f.getbbox(t); return b[2]-b[0]
    def _th(self,t,f): b=f.getbbox(t); return b[3]-b[1]

    @staticmethod
    def _eo(t): return 1-(1-min(1,max(0,t)))**3

    def _word_color(self,w):
        c=re.sub(r"[^가-힣a-zA-Z0-9]","",w)
        if c in self.PSYCH_TERMS: return self.LAVENDER
        if re.search(r"\d",w): return self.AMBER
        return self.WHITE

    def _hl_line(self,draw,line,y,font,alpha=255,center=True):
        words=line.split(); tw=self._tw(line,font)
        x=(self.W-tw)//2 if center else self.MARGIN+20
        for i,w in enumerate(words):
            seg=w+(" " if i<len(words)-1 else "")
            draw.text((x,y),seg,font=font,fill=(*self._word_color(w),alpha))
            x+=self._tw(seg,font)

    def _card(self,draw,x,y,w,h,col=(45,27,51,204),r=16):
        draw.rounded_rectangle([(x,y),(x+w,y+h)],radius=r,fill=col)

    # ── Phase 1: Question + Countdown ──
    def _ph1(self,draw,t):
        # Question text (bounce in)
        bounce=max(0,40*(1-self._eo(t/0.5)))
        lh=self._th("가",self.f_question)+14
        total_h=lh*len(self._q_lines)
        sy=int((self.H//2-100)-total_h//2+bounce)
        qa=int(255*self._eo(t/0.5))
        for i,l in enumerate(self._q_lines):
            lw=self._tw(l,self.f_question)
            draw.text(((self.W-lw)//2, sy+i*lh),l,font=self.f_question,fill=(255,255,255,qa))
        # "잠시 생각해보세요..."
        hint_a=int(255*self._eo((t-0.8)/0.5))
        if hint_a>0:
            ht="잠시 생각해보세요..."
            hw=self._tw(ht,self.f_small)
            draw.text(((self.W-hw)//2, sy+total_h+40),ht,font=self.f_small,fill=(200,200,200,hint_a))
        # Countdown ring (1.5s~4.5s)
        if 1.5<=t<4.5:
            el=t-1.5; prog=1-el/3; num=max(1,3-int(el))
            cx,cy,r=self.W//2, sy+total_h+160, 50
            bb=[(cx-r,cy-r),(cx+r,cy+r)]
            draw.arc(bb,0,360,fill=(*self.GRAY,120),width=6)
            ea=-90+360*prog
            if ea>-90: draw.arc(bb,-90,ea,fill=(*self.LAVENDER,255),width=6)
            nt=str(num); nw=self._tw(nt,self.f_countdown)
            draw.text((cx-nw//2,cy-self._th(nt,self.f_countdown)//2-4),nt,
                       font=self.f_countdown,fill=(255,255,255,255))

    # ── Phase 2: Options Slide-in ──
    def _ph2(self,draw,t):
        cw=self.W-self.MARGIN*2; ch=180
        # Option A: slide from left
        ap=self._eo(t/0.8)
        ax=int(-cw+(self.MARGIN+cw)*ap); ay=520
        self._opt_card(draw,ax,ay,cw,ch,"A",self.option_a,self.LAVENDER,int(255*ap))
        # Option B: slide from right
        bp=self._eo((t-0.3)/0.8)
        bx=int(self.W-(self.W-self.MARGIN)*bp); by=780
        self._opt_card(draw,bx,by,cw,ch,"B",self.option_b,self.AMBER,int(255*max(0,bp)))

    def _opt_card(self,draw,x,y,w,h,letter,text,bcol,alpha):
        if alpha<=0: return
        draw.rounded_rectangle([(x,y),(x+w,y+h)],radius=20,
                                fill=(45,27,51,int(alpha*0.8)),
                                outline=(*bcol,alpha),width=4)
        br=28; bcx=x+50; bcy=y+h//2
        draw.ellipse([(bcx-br,bcy-br),(bcx+br,bcy+br)],fill=(*bcol,alpha))
        lw=self._tw(letter,self.f_badge)
        draw.text((bcx-lw//2,bcy-self._th(letter,self.f_badge)//2-3),
                   letter,font=self.f_badge,fill=(255,255,255,alpha))
        lines=self._wrap(text,self.f_option,w-130)
        lh2=self._th("가",self.f_option)+8
        ty=y+(h-lh2*len(lines))//2
        for i,l in enumerate(lines):
            draw.text((x+100,ty+i*lh2),l,font=self.f_option,fill=(255,255,255,alpha))

    # ── Phase 3: Answer + Stats + Explanation ──
    def _ph3(self,draw,overlay,t):
        cw=self.W-self.MARGIN*2; ch=180
        ans_col=self.LAVENDER if self.answer=="A" else self.AMBER
        wrong_col=self.AMBER if self.answer=="A" else self.LAVENDER
        ans_txt=self.option_a if self.answer=="A" else self.option_b
        # Flash
        if t<0.25:
            fa=int(200*(1-t/0.25))
            draw.rectangle([(0,0),(self.W,self.H)],fill=(255,255,255,fa))
        # Correct card stays, wrong dims
        dim=int(255*max(0,1-t/0.5))
        wrong_y=780 if self.answer=="A" else 520
        wrong_let="B" if self.answer=="A" else "A"
        wrong_txt=self.option_b if self.answer=="A" else self.option_a
        self._opt_card(draw,self.MARGIN,wrong_y,cw,ch,wrong_let,wrong_txt,wrong_col,dim)
        # Correct card
        cor_y=520 if self.answer=="A" else 780
        final_y=250; cur_y=int(cor_y+(final_y-cor_y)*self._eo(t/0.8))
        self._opt_card(draw,self.MARGIN,cur_y,cw,ch,self.answer,ans_txt,ans_col,255)
        # Stat text
        sa=int(255*self._eo((t-1.0)/0.6))
        if sa>0:
            st=f"{self.stat_pct}%의 사람이 {self.answer}를 선택합니다"
            sw=self._tw(st,self.f_bold)
            draw.text(((self.W-sw)//2,500),st,font=self.f_bold,fill=(*ans_col,sa))
        # Stat bar
        if t>1.5:
            bp=self._eo((t-1.5)/1.5)
            bx=self.MARGIN+40; by_=580; bw=self.W-self.MARGIN*2-80; bh=44
            draw.rounded_rectangle([(bx,by_),(bx+bw,by_+bh)],radius=bh//2,fill=(60,50,70,200))
            fw=int(bw*(self.stat_pct/100)*bp)
            if fw>bh:
                draw.rounded_rectangle([(bx,by_),(bx+fw,by_+bh)],radius=bh//2,fill=(*ans_col,220))
            pt=f"{int(self.stat_pct*bp)}%"
            draw.text((bx+fw+12,by_+4),pt,font=self.f_bold,fill=(*ans_col,255))
        # Explanation card
        if t>3.0:
            et=t-3.0; lh=self._th("가",self.f_body)+16
            card_h=lh*len(self._exp_lines)+50
            cy_=700
            ca=int(204*self._eo(et/0.6))
            if ca>0:
                self._card(draw,self.MARGIN,cy_,cw,card_h,col=(45,27,51,ca))
            for i,l in enumerate(self._exp_lines):
                la=int(255*self._eo((et-0.3-i*0.2)/0.4))
                if la>0:
                    self._hl_line(draw,l,cy_+25+i*lh,self.f_body,alpha=la)

    # ── Phase 4: Twist + CTA ──
    def _ph4(self,draw,t):
        # "하지만 실제로는..."
        ta=int(255*self._eo(t/0.5))
        tt="하지만 실제로는..."
        tw_=self._tw(tt,self.f_turn)
        draw.text(((self.W-tw_)//2,350),tt,font=self.f_turn,fill=(255,255,255,ta))
        # Twist card
        if self._twist_lines:
            lh=self._th("가",self.f_body)+16
            cw=self.W-self.MARGIN*2; ch_=lh*len(self._twist_lines)+50
            cy_=500; ca=int(204*self._eo((t-0.5)/0.6))
            if ca>0: self._card(draw,self.MARGIN,cy_,cw,ch_,col=(45,27,51,ca))
            for i,l in enumerate(self._twist_lines):
                la=int(255*self._eo((t-0.8-i*0.2)/0.4))
                if la>0: self._hl_line(draw,l,cy_+25+i*lh,self.f_body,alpha=la)
        # CTA
        cta_a=int(255*self._eo((t-3.0)/0.6))
        if cta_a>0:
            cw2=self._tw(self.cta_text,self.f_cta)
            draw.text(((self.W-cw2)//2,1300),self.cta_text,font=self.f_cta,fill=(*self.LAVENDER,cta_a))

    # ── Frame Composition ──
    def _render(self,t):
        br=0.3 if t<self.P1 else 0.5
        bg=self._get_bg(br if t<self.P1 else 0.5)
        ov=Image.new("RGBA",(self.W,self.H),(0,0,0,0))
        d=ImageDraw.Draw(ov)
        if t<self.P1: self._ph1(d,t)
        elif t<self.P2: self._ph2(d,t-self.P1)
        elif t<self.P3: self._ph3(d,ov,t-self.P2)
        else: self._ph4(d,t-self.P3)
        f=Image.alpha_composite(bg,ov)
        if t>=self.P3: f=Image.alpha_composite(f,self._vignette)
        return np.array(f.convert("RGB"))

    def generate(self,out="psychology_quiz.mp4"):
        clip=VideoClip(lambda t:self._render(t),duration=self.P4).with_fps(self.FPS)
        Path(out).parent.mkdir(parents=True,exist_ok=True)
        clip.write_videofile(str(out),codec="libx264",preset="medium",bitrate="8000k",audio=False,logger="bar")
        print(f"\n✅ 생성 완료: {Path(out).resolve()}")
        print(f"   크기: {self.W}×{self.H} | 길이: {self.P4:.0f}초 | FPS: {self.FPS}")
        return str(Path(out).resolve())


DEMO_DATA = {
    "question": "확실한 100만원 vs 50% 확률의 250만원, 당신의 선택은?",
    "option_a": "확실하게 100만원을 받겠다",
    "option_b": "50% 확률로 250만원에 도전!",
    "answer": "A",
    "stat_percent": 72,
    "explanation": (
        "전망 이론에 따르면 인간은 이익 상황에서 "
        "위험을 회피하는 경향이 있습니다. "
        "기대값은 B가 125만원으로 더 높지만, "
        "확실한 이득을 선호하는 것이 인간의 본능입니다. "
        "이것을 확실성 효과라고 부릅니다."
    ),
    "twist_text": (
        "같은 사람에게 '100만원 손실 vs 50% 확률로 "
        "250만원 손실'을 물으면? 대부분 위험한 선택을 합니다. "
        "이것이 카너먼이 발견한 손실 회피 편향의 핵심입니다."
    ),
}


def main():
    pa=argparse.ArgumentParser(description="심리학 퀴즈 인터랙티브 쇼츠 생성기")
    pa.add_argument("--demo",action="store_true",help="전망 이론 퀴즈 데모")
    pa.add_argument("--question",type=str,default="")
    pa.add_argument("--option-a",type=str,default="")
    pa.add_argument("--option-b",type=str,default="")
    pa.add_argument("--answer",type=str,default="A")
    pa.add_argument("--stat",type=int,default=50)
    pa.add_argument("--explanation",type=str,default="")
    pa.add_argument("--twist",type=str,default="")
    pa.add_argument("--out",type=str,default="psychology_quiz.mp4")
    a=pa.parse_args()
    if a.demo:
        print("🧠 전망 이론 퀴즈 데모 생성 중...")
        PsychologyQuizGenerator(**DEMO_DATA).generate(a.out)
        return 0
    if not all([a.question,a.option_a,a.option_b,a.explanation]):
        print("[FAIL] --question, --option-a, --option-b, --explanation 필수. --demo로 먼저 시도하세요.")
        return 1
    PsychologyQuizGenerator(a.question,a.option_a,a.option_b,a.answer,a.stat,a.explanation,a.twist).generate(a.out)
    return 0

if __name__=="__main__": raise SystemExit(main())
