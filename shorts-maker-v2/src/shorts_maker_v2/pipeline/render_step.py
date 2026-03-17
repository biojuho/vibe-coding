from __future__ import annotations

import logging
import random
import time
from pathlib import Path

logger = logging.getLogger(__name__)

from moviepy import (
    AudioFileClip,
    CompositeAudioClip,
    CompositeVideoClip,
    ImageClip,
    VideoFileClip,
    concatenate_videoclips,
    vfx,
)
from moviepy.audio.fx import MultiplyVolume

from shorts_maker_v2.config import AppConfig
from shorts_maker_v2.models import SceneAsset, ScenePlan
from shorts_maker_v2.providers.llm_router import LLMRouter
from shorts_maker_v2.providers.openai_client import OpenAIClient
from shorts_maker_v2.render.caption_pillow import CaptionStyle, apply_preset, render_caption_image
from shorts_maker_v2.render.karaoke import (
    apply_ssml_break_correction,
    group_into_chunks,
    load_words_json,
    render_karaoke_image,
    render_karaoke_highlight_image,
)
from shorts_maker_v2.render.animations import apply_text_animation
from shorts_maker_v2.render.broll_overlay import create_broll_pip
from shorts_maker_v2.render.hud_overlay import render_hud_overlay

# MoviePy 2.x: PIL.Image.ANTIALIAS hotfix no longer needed (Pillow native)


class RenderStep:
    # YPP: 역할별 자막 프리셋 조합 로테이션 (반복적 콘텐츠 방지)
    _CAPTION_COMBOS: list[tuple[str, str, str]] = [
        # (hook_preset, body_preset, cta_preset)
        ("bold", "subtitle", "default"),    # 임팩트 → 영화적 → 깔끔
        ("neon", "default", "subtitle"),     # 네온 → 깔끔 → 영화적
        ("bold", "default", "neon"),         # 임팩트 → 깔끔 → 네온
        ("neon", "subtitle", "bold"),        # 네온 → 영화적 → 임팩트
        ("subtitle", "bold", "cta"),         # 영화적 → 임팩트 → CTA 특화
        ("default", "neon", "bold"),         # 깔끔 → 네온 → 임팩트
    ]

    def __init__(
        self,
        config: AppConfig,
        openai_client: OpenAIClient | None = None,
        *,
        llm_router: LLMRouter | None = None,
        job_index: int = 0,
        channel_key: str = "",
    ):
        self.config = config
        self._openai_client = openai_client
        self._llm_router = llm_router
        self._job_index = job_index
        self._channel_key = channel_key

        # YPP: bottom_offset에 ±20px 랜덤 변동
        offset_jitter = random.randint(-20, 20)
        jittered_offset = max(200, config.captions.bottom_offset + offset_jitter)

        base_style = CaptionStyle(
            font_size=config.captions.font_size,
            margin_x=config.captions.margin_x,
            bottom_offset=jittered_offset,
            text_color=config.captions.text_color,
            stroke_color=config.captions.stroke_color,
            stroke_width=config.captions.stroke_width,
            line_spacing=config.captions.line_spacing,
            font_candidates=config.captions.font_candidates,
            mode=config.captions.mode,
            words_per_chunk=config.captions.words_per_chunk,
            bg_color=config.captions.bg_color,
            bg_opacity=config.captions.bg_opacity,
            bg_radius=config.captions.bg_radius,
        )

        # 채널별 caption_combo 우선 사용, 없으면 job_index 기반 로테이션
        combo = self._resolve_caption_combo(channel_key, job_index)
        self.hook_style = apply_preset(base_style, combo[0])
        self.body_style = apply_preset(base_style, combo[1])
        self.cta_style = apply_preset(base_style, combo[2])

        logger.info(
            "[RenderStep] 자막 combo — hook=%s, body=%s, cta=%s (channel=%r)",
            combo[0], combo[1], combo[2], channel_key or "default",
        )

    @classmethod
    def _resolve_caption_combo(cls, channel_key: str, job_index: int) -> tuple[str, str, str]:
        """채널 프로파일의 caption_combo를 우선 사용, 없으면 로테이션 폴백."""
        if channel_key:
            try:
                from shorts_maker_v2.utils.channel_router import ChannelRouter
                router = ChannelRouter()
                profile = router.get_profile(channel_key)
                combo_list = profile.get("caption_combo")
                if combo_list and len(combo_list) == 3:
                    logger.info(
                        "[RenderStep] 채널 '%s' 전용 caption_combo 적용: %s",
                        channel_key, combo_list,
                    )
                    return tuple(combo_list)  # type: ignore[return-value]
            except Exception as exc:
                logger.warning("[RenderStep] caption_combo 로드 실패: %s", exc)

        # 폴백: job_index 기반 로테이션
        combo = cls._CAPTION_COMBOS[job_index % len(cls._CAPTION_COMBOS)]
        logger.info("[RenderStep] 로테이션 combo 사용 (job_index=%d): %s", job_index, combo)
        return combo


    def _build_bookend_clip(self, path_str: str, duration: float, target_width: int, target_height: int):
        """인트로/아웃트로 클립 빌드 (이미지 또는 비디오)."""
        path = Path(path_str)
        if not path.exists():
            return None
        ext = path.suffix.lower()
        if ext in (".mp4", ".mov", ".avi", ".webm"):
            clip = VideoFileClip(str(path)).without_audio()
            clip = clip.subclipped(0, min(clip.duration, duration))
        elif ext in (".png", ".jpg", ".jpeg", ".webp"):
            clip = ImageClip(str(path)).with_duration(duration)
        else:
            return None
        return self._fit_vertical(clip, target_width, target_height)

    @staticmethod
    def _ken_burns(clip, target_width: int, target_height: int, zoom: float = 0.06):
        """이미지 클립에 서서히 줌인하는 켄번스 효과 적용."""
        def resize_func(t: float) -> float:
            return 1.0 + zoom * (t / max(clip.duration, 0.001))

        zoomed = clip.resized(resize_func)
        return zoomed.cropped(
            x_center=zoomed.w / 2,
            y_center=zoomed.h / 2,
            width=target_width,
            height=target_height,
        )

    @staticmethod
    def _dramatic_ken_burns(clip, target_width: int, target_height: int, zoom: float = 0.12):
        """Hook 씬용 빠르고 강렬한 줌인 효과 (기본 zoom 2배)."""
        def resize_func(t: float) -> float:
            return 1.0 + zoom * (t / max(clip.duration, 0.001))

        zoomed = clip.resized(resize_func)
        return zoomed.cropped(
            x_center=zoomed.w / 2,
            y_center=zoomed.h / 2,
            width=target_width,
            height=target_height,
        )

    @staticmethod
    def _zoom_out(clip, target_width: int, target_height: int, zoom: float = 0.06):
        """이미지 클립에 서서히 줌아웃하는 효과 적용."""
        def resize_func(t: float) -> float:
            return 1.0 + zoom * (1.0 - t / max(clip.duration, 0.001))

        zoomed = clip.resized(resize_func)
        return zoomed.cropped(
            x_center=zoomed.w / 2,
            y_center=zoomed.h / 2,
            width=target_width,
            height=target_height,
        )

    @staticmethod
    def _pan_horizontal(clip, target_width: int, target_height: int, direction: int = 1):
        """이미지 클립에 수평 패닝 효과 적용 (direction: +1=좌→우, -1=우→좌)."""
        overscan = 0.12
        zoomed = clip.resized(1.0 + overscan)
        max_shift = zoomed.w * overscan / 2
        dur = max(clip.duration, 0.001)
        zw, zh = zoomed.w, zoomed.h
        y_center = zh / 2

        def make_frame(get_frame, t):
            frame = get_frame(t)
            progress = t / dur - 0.5
            cx = zw / 2 + direction * max_shift * progress
            x1 = int(max(0, cx - target_width / 2))
            y1 = int(max(0, y_center - target_height / 2))
            return frame[y1:y1 + target_height, x1:x1 + target_width]

        return zoomed.transform(make_frame).with_duration(clip.duration)

    def _apply_random_effect(self, clip, target_width: int, target_height: int, *, exclude: str = ""):
        """zoom-in / zoom-out / pan-left / pan-right 중 랜덤 선택 (exclude로 연속 동일 효과 방지)."""
        all_effects = {
            "ken_burns": lambda c: self._ken_burns(c, target_width, target_height),
            "zoom_out": lambda c: self._zoom_out(c, target_width, target_height),
            "pan_left": lambda c: self._pan_horizontal(c, target_width, target_height, +1),
            "pan_right": lambda c: self._pan_horizontal(c, target_width, target_height, -1),
        }
        candidates = {k: v for k, v in all_effects.items() if k != exclude}
        if not candidates:
            candidates = all_effects
        chosen_name = random.choice(list(candidates.keys()))
        return candidates[chosen_name](clip), chosen_name

    @staticmethod
    def _fit_vertical(clip, target_width: int, target_height: int):
        scale = max(target_width / clip.w, target_height / clip.h)
        resized = clip.resized(scale)
        x1 = max(0, (resized.w - target_width) / 2)
        y1 = max(0, (resized.h - target_height) / 2)
        return resized.cropped(x1=x1, y1=y1, x2=x1 + target_width, y2=y1 + target_height)

    def _render_title_image(self, title: str, canvas_width: int, output_path: Path) -> Path:
        """영상 상단에 표시할 제목 오버레이 이미지 렌더링."""
        import PIL.Image as _Image
        import PIL.ImageDraw as _ImageDraw
        import PIL.ImageFont as _ImageFont

        font_size = 38
        font = None
        for fp in self.config.captions.font_candidates:
            p = Path(fp)
            if p.exists():
                try:
                    font = _ImageFont.truetype(str(p), font_size)
                    break
                except Exception:
                    continue
        if font is None:
            font = _ImageFont.load_default()

        pad_y = 14
        probe = _Image.new("RGBA", (canvas_width, 200), (0, 0, 0, 0))
        draw = _ImageDraw.Draw(probe)
        bbox = draw.textbbox((0, 0), title, font=font)
        text_w = max(1, int(bbox[2] - bbox[0]))
        text_h = max(1, int(bbox[3] - bbox[1]))

        image_w = canvas_width
        image_h = text_h + pad_y * 2
        image = _Image.new("RGBA", (image_w, image_h), (0, 0, 0, 0))
        draw = _ImageDraw.Draw(image)
        draw.rectangle([(0, 0), (image_w, image_h)], fill=(0, 0, 0, 160))
        x = (image_w - text_w) / 2 - bbox[0]
        y = pad_y - bbox[1]
        draw.text((x, y), title, font=font, fill="#FFFFFF", stroke_width=1, stroke_fill="#000000")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        image.save(str(output_path), format="PNG")
        return output_path

    def _build_base_clip(self, asset: SceneAsset, duration_sec: float, target_width: int, target_height: int):
        if asset.visual_type == "video":
            base = VideoFileClip(asset.visual_path).without_audio()
            if base.duration < duration_sec:
                base = base.with_effects([vfx.Loop(duration=duration_sec)])
            elif base.duration > duration_sec:
                base = base.subclipped(0, duration_sec)
        else:
            base = ImageClip(asset.visual_path).with_duration(duration_sec)
        return self._fit_vertical(base, target_width, target_height)

    # ── BGM 무드 매칭 ─────────────────────────────────────────────────────────

    # 무드별 한국어 키워드 (파일명에도 활용)
    _MOOD_KEYWORDS: dict[str, list[str]] = {
        "dramatic": [
            "블랙홀", "우주", "죽음", "사망", "재앙", "공포", "위험", "충격", "비밀",
            "경고", "무서운", "진실", "폭발", "전쟁", "붕괴", "최후", "멸종",
        ],
        "upbeat": [
            "돈", "절약", "성공", "방법", "비결", "팁", "건강", "행복", "성장",
            "개선", "효과", "좋은", "최고", "쉬운", "간단", "빠른", "부자",
        ],
    }
    # 파일명 기반 무드 감지 키워드
    _BGM_MOOD_NAMES: dict[str, list[str]] = {
        "dramatic": ["dramatic", "cinematic", "epic", "intense", "dark", "suspense"],
        "upbeat": ["upbeat", "happy", "positive", "energetic", "fun", "bright", "pop"],
        "calm": ["calm", "ambient", "chill", "relax", "soft", "peaceful", "gentle"],
    }

    @classmethod
    def _classify_mood_keywords(cls, text: str) -> str:
        """키워드 기반 BGM 무드 분류 (폴백용)."""
        for mood, keywords in cls._MOOD_KEYWORDS.items():
            if any(kw in text for kw in keywords):
                return mood
        return "calm"

    def _classify_mood_gpt(self, text: str) -> str | None:
        """LLMRouter(7-provider fallback)로 BGM 무드 분류. 실패 시 None 반환."""
        _system = (
            "You classify YouTube Shorts topics into a BGM mood. "
            "Choose exactly one: \"dramatic\", \"upbeat\", or \"calm\".\n"
            "Output JSON: {\"mood\": \"...\"}"
        )
        _user = f"Topic: {text}"

        # 1차: LLMRouter (7-provider fallback)
        if self._llm_router:
            try:
                result = self._llm_router.generate_json(
                    system_prompt=_system,
                    user_prompt=_user,
                    temperature=0.0,
                )
                mood = str(result.get("mood", "")).strip().lower()
                if mood in ("dramatic", "upbeat", "calm"):
                    return mood
            except Exception:
                pass

        # 2차 폴백: OpenAI 직접 (llm_router 없을 때)
        if self._openai_client:
            try:
                result = self._openai_client.generate_json(
                    model="gpt-4o-mini",
                    system_prompt=_system,
                    user_prompt=_user,
                    temperature=0.0,
                )
                mood = str(result.get("mood", "")).strip().lower()
                if mood in ("dramatic", "upbeat", "calm"):
                    return mood
            except Exception:
                pass

        return None

    def _classify_mood(self, text: str) -> str:
        """GPT 우선, 실패 시 키워드 폴백."""
        gpt_mood = self._classify_mood_gpt(text)
        if gpt_mood:
            return gpt_mood
        return self._classify_mood_keywords(text)

    def _pick_transition_style(self) -> str:
        """'random'이면 실제 스타일 중 하나를 무작위 선택."""
        style = self.config.video.transition_style
        if style == "random":
            return random.choice(["crossfade", "flash", "glitch", "zoom", "slide"])
        return style

    def _apply_transitions(
        self,
        clips: list,
        target_width: int,
        target_height: int,
        roles: list[str] | None = None,
    ) -> list:
        """
        씬 클립 목록에 전환 효과 적용.
        roles가 주어지면 구조적 패턴 사용:
          Hook→Body : flash (강한 전환)
          Body→Body : crossfade (부드러운 흐름)
          Body→CTA  : crossfade (자연스러운 마무리)
        roles가 없거나 config가 "random"이 아니면 기존 동작 유지.
        """
        fade_sec = self.config.audio.fade_duration
        global_style = self.config.video.transition_style

        def _white_frame() -> ImageClip:
            import numpy as _np
            arr = _np.ones((target_height, target_width, 3), dtype="uint8") * 255
            return ImageClip(arr, is_mask=False).with_duration(0.12)

        def _structural_style(prev_role: str, cur_role: str) -> str:
            """Phase 4-C: 역할 쌍에 따른 전환 스타일 결정."""
            pair = (prev_role, cur_role)
            mapping: dict[tuple[str, str], list[str]] = {
                ("hook", "body"):  ["flash", "glitch", "zoom"],   # 강한 전환
                ("hook", "cta"):   ["flash", "zoom"],             # 직접 CTA
                ("body", "body"):  ["crossfade", "slide"],        # 부드러운 흐름
                ("body", "cta"):   ["crossfade", "slide", "zoom"],# 자연스러운 마무리
                ("cta", "body"):   ["flash", "glitch"],           # 재시작 강조
            }
            choices = mapping.get(pair, ["crossfade", "slide"])
            return random.choice(choices)

        if global_style == "cut":
            return clips

        result: list = []
        for i, clip in enumerate(clips):
            is_last = i == len(clips) - 1

            # 역할 기반 구조적 전환 (roles 제공 시)
            if roles and i > 0 and global_style == "random" and i < len(roles):
                prev_idx = min(i - 1, len(roles) - 1)
                style = _structural_style(roles[prev_idx], roles[i])
            elif global_style == "random":
                style = self._pick_transition_style()
            else:
                style = global_style

            if style == "crossfade":
                effects = []
                if fade_sec > 0:
                    if i > 0:
                        effects.append(vfx.FadeIn(fade_sec))
                    if not is_last:
                        effects.append(vfx.FadeOut(fade_sec))
                if effects:
                    clip = clip.with_effects(effects)
                result.append(clip)
            elif style == "flash":
                result.append(clip)
                if not is_last:
                    result.append(_white_frame())
            elif style == "glitch":
                # Glitch: 짧은 RGB 글리치 효과 (3프레임 흰+검 교대)
                import numpy as _np
                glitch_frames = []
                for _gi in range(3):
                    color = 255 if _gi % 2 == 0 else 0
                    arr = _np.ones((target_height, target_width, 3), dtype="uint8") * color
                    glitch_frames.append(ImageClip(arr, is_mask=False).with_duration(0.04))
                result.append(clip)
                if not is_last:
                    result.extend(glitch_frames)
            elif style == "zoom":
                # Zoom: 현재 클립 끝을 줌-아웃하며 전환
                if fade_sec > 0 and not is_last:
                    clip = clip.with_effects([vfx.FadeOut(fade_sec * 0.5)])
                result.append(clip)
            elif style == "slide":
                # Slide: 페이드인/아웃으로 자연스러운 슬라이드 느낌
                effects = []
                if i > 0:
                    effects.append(vfx.FadeIn(fade_sec * 1.5))
                if not is_last:
                    effects.append(vfx.FadeOut(fade_sec * 0.5))
                if effects:
                    clip = clip.with_effects(effects)
                result.append(clip)
            else:  # cut
                result.append(clip)

        return result

    def _pick_bgm_by_mood(self, bgm_files: list[Path], text: str) -> Path:
        """
        텍스트 무드에 맞는 BGM 파일 선택.
        파일명에 무드 키워드가 있으면 우선 선택, 없으면 랜덤 폴백.
        """
        mood = self._classify_mood(text)
        mood_keys = self._BGM_MOOD_NAMES.get(mood, [])
        matched = [
            f for f in bgm_files
            if any(k in f.stem.lower() for k in mood_keys)
        ]
        if matched:
            chosen = random.choice(matched)
            logger.info("[BGM] mood=%s → %s", mood, chosen.name)
            return chosen
        chosen = random.choice(bgm_files)
        logger.info("[BGM] mood=%s (no match, random fallback) → %s", mood, chosen.name)
        return chosen

    # ── SFX 효과음 ──────────────────────────────────────────────────────────────

    # SFX 파일명 기반 역할 매칭 (파일명에 키워드 포함)
    _SFX_ROLE_KEYWORDS: dict[str, list[str]] = {
        "hook": ["whoosh", "impact", "hit", "boom", "hook"],
        "transition": ["swish", "swoosh", "transition", "sweep", "slide"],
        "cta": ["pop", "ding", "bell", "chime", "cta", "notification"],
    }

    def _load_sfx_files(self, run_dir: Path) -> dict[str, list[Path]]:
        """SFX 디렉토리에서 역할별 효과음 파일 로드."""
        sfx_dir = (run_dir.parent.parent / self.config.audio.sfx_dir).resolve()
        if not sfx_dir.exists():
            return {}
        all_files = list(sfx_dir.glob("*.mp3")) + list(sfx_dir.glob("*.wav"))
        if not all_files:
            return {}
        categorized: dict[str, list[Path]] = {"hook": [], "transition": [], "cta": []}
        for f in all_files:
            stem = f.stem.lower()
            matched = False
            for role, keywords in self._SFX_ROLE_KEYWORDS.items():
                if any(kw in stem for kw in keywords):
                    categorized[role].append(f)
                    matched = True
                    break
            if not matched:
                categorized["transition"].append(f)
        return categorized

    def _build_sfx_clips(
        self,
        scene_roles: list[str],
        scene_durations: list[float],
        sfx_files: dict[str, list[Path]],
    ) -> list:
        """씬 역할/전환 시점에 SFX 오디오 클립 배치."""
        sfx_clips: list = []
        volume = self.config.audio.sfx_volume
        cursor = 0.0
        for i, (role, dur) in enumerate(zip(scene_roles, scene_durations)):
            # Hook 씬 시작에 임팩트 SFX
            if role == "hook" and sfx_files.get("hook"):
                sfx_path = random.choice(sfx_files["hook"])
                clip = AudioFileClip(str(sfx_path))
                clip = clip.with_effects([MultiplyVolume(volume)])
                sfx_clips.append(clip.with_start(cursor))
            # CTA 씬 시작에 팝 SFX
            elif role == "cta" and sfx_files.get("cta"):
                sfx_path = random.choice(sfx_files["cta"])
                clip = AudioFileClip(str(sfx_path))
                clip = clip.with_effects([MultiplyVolume(volume)])
                sfx_clips.append(clip.with_start(cursor))
            # 씬 전환 시점에 스위시 SFX (마지막 씬 제외)
            if i < len(scene_roles) - 1 and sfx_files.get("transition"):
                sfx_path = random.choice(sfx_files["transition"])
                clip = AudioFileClip(str(sfx_path))
                clip = clip.with_effects([MultiplyVolume(volume)])
                transition_t = max(0, cursor + dur - 0.15)
                sfx_clips.append(clip.with_start(transition_t))
            cursor += dur
        return sfx_clips

    # ── 썸네일 추출 ──────────────────────────────────────────────────────────

    @staticmethod
    def extract_thumbnail(video_path: Path, output_path: Path, timestamp_sec: float = 0.5) -> Path | None:
        """Extract a single frame from rendered video as thumbnail PNG."""
        try:
            clip = VideoFileClip(str(video_path))
            try:
                t = min(timestamp_sec, clip.duration - 0.1) if clip.duration > 0.1 else 0.0
                frame = clip.get_frame(t)
            finally:
                clip.close()
            from PIL import Image
            img = Image.fromarray(frame)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            img.save(str(output_path), format="PNG")
            logger.info("Thumbnail extracted: %s (t=%.1fs)", output_path.name, t)
            return output_path
        except Exception as exc:
            logger.warning("Thumbnail extraction failed: %s", exc)
            return None

    # ── 메인 렌더링 ──────────────────────────────────────────────────────────

    def run(
        self,
        *,
        scene_plans: list[ScenePlan],
        scene_assets: list[SceneAsset],
        output_dir: Path,
        output_filename: str,
        run_dir: Path,
        title: str = "",
        topic: str = "",
    ) -> Path:
        """씬 에셋을 최종 영상으로 합성합니다.

        Args:
            scene_plans: 대본 생성 단계의 ScenePlan 목록
            scene_assets: 미디어 생성 단계의 SceneAsset 목록 (TTS + 비주얼)
            output_dir: 최종 영상 출력 디렉토리
            output_filename: 출력 파일 이름 (e.g. "job-id.mp4")
            run_dir: 현재 작업 디렉토리 (중간 파일 저장용)
            title: 영상 제목
            topic: 원본 주제

        Returns:
            렌더링된 MP4 파일 경로
        """
        target_width, target_height = self.config.video.resolution
        io_cfg = self.config.intro_outro

        all_clips: list = []
        _audio_clips_to_close: list = []
        _bgm_clip = None  # BGM 원본 참조 (close 용)
        scene_roles: list[str] = []
        last_effect = ""

        # ── 인트로 삽입 ──
        intro_path = io_cfg.intro_path
        if intro_path:
            intro = self._build_bookend_clip(intro_path, io_cfg.intro_duration, target_width, target_height)
            if intro is not None:
                intro = intro.with_effects([vfx.FadeIn(0.3)])
                all_clips.append(intro)
                scene_roles.append("intro")
                logger.info("[Intro] 인트로 삽입 (%.1fs): %s", io_cfg.intro_duration, intro_path)

        # ── 제목 오버레이 이미지 준비 ──
        title_overlay_clip = None
        if title:
            try:
                title_img_path = run_dir / "title_overlay.png"
                self._render_title_image(title, target_width, title_img_path)
                title_overlay_clip = ImageClip(str(title_img_path)).with_duration(1.0)
            except Exception as exc:
                logger.warning("[Title] 제목 오버레이 생성 실패: %s", exc)

        # ── 씬별 클립 빌드 ──
        for plan, asset in zip(scene_plans, scene_assets):
            duration_sec = asset.duration_sec
            role = plan.structure_role
            scene_roles.append(role)

            # 1) 베이스 비주얼 클립
            base = self._build_base_clip(asset, duration_sec, target_width, target_height)

            # 2) 카메라 효과 (Ken Burns 등)
            if asset.visual_type == "image":
                if role == "hook":
                    base = self._dramatic_ken_burns(base, target_width, target_height)
                    last_effect = "dramatic_ken_burns"
                else:
                    base, last_effect = self._apply_random_effect(
                        base, target_width, target_height, exclude=last_effect
                    )

            # 3) 오디오 합성
            audio = AudioFileClip(asset.audio_path)
            if audio.duration != duration_sec:
                if audio.duration > duration_sec:
                    audio = audio.subclipped(0, duration_sec)
                # audio shorter than visual → visual에 맞춤 (음성 끝 자연 종료)
            _audio_clips_to_close.append(audio)
            base = base.with_audio(audio)

            # 4) 자막 오버레이
            style = (
                self.hook_style if role == "hook"
                else self.cta_style if role == "cta"
                else self.body_style
            )

            # 카라오케 모드
            if style.mode == "karaoke":
                words_json_path = Path(asset.audio_path).parent / f"{Path(asset.audio_path).stem}_words.json"
                ssml_txt_path = words_json_path.parent / f"{words_json_path.stem}_ssml.txt"
                try:
                    raw_words = load_words_json(words_json_path)
                    # SSML break 보정 (ssml 텍스트 파일이 있을 때만)
                    if ssml_txt_path.exists():
                        ssml_text = ssml_txt_path.read_text(encoding="utf-8")
                        corrected_words = apply_ssml_break_correction(raw_words, ssml_text)
                    else:
                        corrected_words = raw_words
                    # group_into_chunks → list[tuple[start, end, text]]
                    chunks = group_into_chunks(corrected_words, style.words_per_chunk)

                    # Word-level highlight 모드
                    if self.config.captions.highlight_mode == "word":
                        caption_clips = []
                        for chunk_start, chunk_end, chunk_text in chunks:
                            # 청크 내 단어별 하이라이트
                            chunk_words = chunk_text.split()
                            chunk_dur = max(0.1, chunk_end - chunk_start)
                            word_dur = chunk_dur / max(len(chunk_words), 1)
                            for wi, cw in enumerate(chunk_words):
                                ws = chunk_start + wi * word_dur
                                wd = max(0.05, word_dur)
                                highlight_out = run_dir / f"kh_{plan.scene_id:02d}_{chunk_start:.2f}_{wi}.png"
                                render_karaoke_highlight_image(
                                    words=chunk_words,
                                    active_word_index=wi,
                                    canvas_width=target_width,
                                    style=style,
                                    highlight_color=self.config.captions.highlight_color,
                                    output_path=highlight_out,
                                )
                                cap_clip = ImageClip(str(highlight_out), transparent=True).with_duration(wd).with_start(ws)
                                caption_clips.append(cap_clip)
                    else:
                        caption_clips = []
                        for chunk_start, chunk_end, chunk_text in chunks:
                            cd = max(0.1, chunk_end - chunk_start)
                            cap_out = run_dir / f"kc_{plan.scene_id:02d}_{chunk_start:.2f}.png"
                            render_karaoke_image(chunk_text, target_width, style, cap_out)
                            cap_clip = ImageClip(str(cap_out), transparent=True).with_duration(cd).with_start(chunk_start)
                            caption_clips.append(cap_clip)

                    if caption_clips:
                        base = CompositeVideoClip([base] + caption_clips)

                except Exception as kex:
                    logger.warning("[Karaoke] 카라오케 실패, 정적 자막 폴백: %s", kex)
                    cap_out = run_dir / f"caption_fallback_{plan.scene_id:02d}.png"
                    cap_img = render_caption_image(plan.narration_ko, target_width, style, cap_out)
                    cap_clip = ImageClip(str(cap_img), transparent=True).with_duration(duration_sec)
                    base = CompositeVideoClip([base, cap_clip])
            else:
                # 정적 자막 모드
                cap_out = run_dir / f"caption_static_{plan.scene_id:02d}.png"
                cap_img = render_caption_image(plan.narration_ko, target_width, style, cap_out)
                cap_clip = ImageClip(str(cap_img), transparent=True).with_duration(duration_sec)
                base = CompositeVideoClip([base, cap_clip])

            # 5) 텍스트 애니메이션 (Hook 씬)
            if role == "hook":
                try:
                    base = apply_text_animation(
                        base,
                        animation_type=self.config.captions.hook_animation,
                        duration=duration_sec,
                    )
                except Exception as aex:
                    logger.warning("[Animation] Hook 애니메이션 실패: %s", aex)

            # 6) B-Roll 오버레이 (PiP)
            broll_path = run_dir / f"broll_{plan.scene_id:02d}.mp4"
            if broll_path.exists():
                try:
                    pip_clip = create_broll_pip(
                        str(broll_path), duration_sec, target_width, target_height
                    )
                    if pip_clip is not None:
                        base = CompositeVideoClip([base, pip_clip])
                except Exception:
                    pass

            # 7) HUD 오버레이
            try:
                hud_clip = render_hud_overlay(
                    width=target_width,
                    height=target_height,
                    duration=duration_sec,
                    scene_index=plan.scene_id,
                    total_scenes=len(scene_plans),
                    role=role,
                )
                if hud_clip is not None:
                    base = CompositeVideoClip([base, hud_clip])
            except Exception:
                pass

            # 8) 제목 오버레이 (첫 번째 씬에만)
            if title_overlay_clip is not None and plan.scene_id == 1:
                try:
                    title_clip = title_overlay_clip.with_position(("center", 80))
                    base = CompositeVideoClip([base, title_clip])
                except Exception:
                    pass

            all_clips.append(base)

        # ── 전환 효과 적용 ──
        all_clips = self._apply_transitions(all_clips, target_width, target_height, roles=scene_roles)

        # ── 아웃트로 삽입 ──
        outro_path = io_cfg.outro_path
        if outro_path:
            outro = self._build_bookend_clip(outro_path, io_cfg.outro_duration, target_width, target_height)
            if outro is not None:
                # Sprint 3: 아웃트로 애니메이션 (FadeIn)
                outro = outro.with_effects([vfx.FadeIn(0.4)])
                all_clips.append(outro)
                logger.info("[Outro] 아웃트로 삽입 (%.1fs): %s", io_cfg.outro_duration, outro_path)

        output_path = output_dir / output_filename
        final_video = concatenate_videoclips(all_clips, method="compose")

        # BGM 무드 매칭 + 오디오 Ducking (Sprint 4)
        bgm_dir = (run_dir.parent.parent / self.config.audio.bgm_dir).resolve()
        if bgm_dir.exists():
            bgm_files = list(bgm_dir.glob("*.mp3"))
            if bgm_files and final_video.audio is not None:
                bgm_path = self._pick_bgm_by_mood(bgm_files, topic or title)
                bgm_clip = AudioFileClip(str(bgm_path))
                _bgm_clip = bgm_clip
                bgm_clip = bgm_clip.with_effects([afx.AudioLoop(duration=final_video.duration)])

                # ── Sprint 4: RMS 기반 오디오 Ducking ──────────────────────
                # TTS 나레이션의 RMS 에너지를 분석하여 BGM 볼륨을 동적 조절.
                # 말소리 있을 때: BGM ↓ (duck_ratio), 침묵 시: BGM ↑ (base_vol)
                base_vol = self.config.audio.bgm_volume      # 0.12
                duck_ratio = 0.30                              # 발화 시 BGM = base_vol * 0.30
                silence_boost = 1.8                            # 침묵 시 BGM = base_vol * 1.8
                attack_sec = 0.20                              # duck 시작 속도 (빠르게 줄임)
                release_sec = 0.40                             # duck 해제 속도 (천천히 올림)
                rms_threshold = 0.01                           # 이 이상이면 "발화 중"

                # TTS 오디오에서 RMS 에너지 프로파일 만들기
                try:
                    import numpy as _np
                    tts_audio = final_video.audio
                    # 100ms 단위로 RMS 샘플링
                    sample_rate = 44100
                    hop_sec = 0.05  # 50ms 단위
                    total_dur = final_video.duration
                    n_samples = max(1, int(total_dur / hop_sec))

                    rms_profile: list[float] = []
                    for i in range(n_samples):
                        t_start = i * hop_sec
                        t_end = min(t_start + hop_sec, total_dur)
                        try:
                            chunk = tts_audio.subclipped(t_start, t_end)
                            frames = chunk.to_soundarray(fps=sample_rate)
                            rms_val = float(_np.sqrt(_np.mean(frames ** 2)))
                        except Exception:
                            rms_val = 0.0
                        rms_profile.append(rms_val)

                    # 스무딩된 duck envelope 생성
                    duck_envelope: list[float] = []
                    current_duck = silence_boost  # 초기: 침묵 상태
                    for rms_val in rms_profile:
                        is_speech = rms_val > rms_threshold
                        target = duck_ratio if is_speech else silence_boost
                        # 지수적 접근 (attack/release 비대칭)
                        if target < current_duck:
                            # Ducking (빠르게)
                            alpha = min(1.0, hop_sec / max(attack_sec, 0.01))
                        else:
                            # Release (천천히)
                            alpha = min(1.0, hop_sec / max(release_sec, 0.01))
                        current_duck += alpha * (target - current_duck)
                        duck_envelope.append(current_duck)

                    logger.info(
                        "[DUCKING] RMS 프로파일 생성 완료: %d 샘플, "
                        "평균 RMS=%.4f, duck 구간=%.0f%%",
                        len(rms_profile),
                        sum(rms_profile) / max(len(rms_profile), 1),
                        sum(1 for r in rms_profile if r > rms_threshold) / max(len(rms_profile), 1) * 100,
                    )

                    # closure에서 참조할 값을 로컬 바인딩
                    _envelope = list(duck_envelope)
                    _hop = hop_sec
                    _base = base_vol

                    def _ducked_bgm_volume(t: float, _e=_envelope, _h=_hop, _b=_base) -> float:
                        """RMS 기반 ducking 볼륨 계수."""
                        if not _e:
                            return _b
                        idx = min(int(t / _h), len(_e) - 1)
                        return _b * _e[max(0, idx)]

                    bgm_clip = bgm_clip.transform(
                        lambda get_frame, t: get_frame(t) * _ducked_bgm_volume(t),
                        apply_to=["audio"],
                    )
                    logger.info("[DUCKING] 오디오 ducking 적용 완료")

                except Exception as duck_exc:
                    # Ducking 실패 시 기존 고정 볼륨 폴백
                    logger.warning("[DUCKING] RMS 분석 실패, 고정 볼륨 폴백: %s", duck_exc)
                    bgm_clip = bgm_clip.with_effects([
                        MultiplyVolume(base_vol),
                    ])

                mixed_audio = CompositeAudioClip([final_video.audio, bgm_clip])
                final_video = final_video.with_audio(mixed_audio)

        # SFX 효과음 레이어
        if self.config.audio.sfx_enabled:
            sfx_files = self._load_sfx_files(run_dir)
            if sfx_files:
                scene_durations = [a.duration_sec for a in scene_assets]
                sfx_clips = self._build_sfx_clips(scene_roles, scene_durations, sfx_files)
                if sfx_clips and final_video.audio is not None:
                    all_audio = [final_video.audio] + sfx_clips
                    final_video = final_video.with_audio(CompositeAudioClip(all_audio))
                    logger.info("[SFX] %d effects applied", len(sfx_clips))

        # HW 가속 인코더 자동 감지
        from shorts_maker_v2.utils.hwaccel import detect_hw_encoder, detect_gpu_info
        hw_codec, hw_params = detect_hw_encoder(self.config.video.hw_accel)

        # Sprint 3: GPU 정보 로깅
        try:
            gpu_info = detect_gpu_info()
            logger.info(
                "[RENDER] GPU: %s | Encoder: %s | HW Decode: %s",
                gpu_info["gpu_name"], gpu_info["encoder"], gpu_info["decoder_support"],
            )
        except Exception:
            pass

        # HW 인코더별 ffmpeg 파라미터 구성
        if hw_codec == "libx264":
            # CPU 인코딩: CRF 기반
            ffmpeg_extra = [
                "-crf", str(self.config.video.encoding_crf),
                "-pix_fmt", "yuv420p",
            ]
            preset = self.config.video.encoding_preset
        else:
            # HW 인코딩: 인코더별 최적 파라미터 사용
            ffmpeg_extra = list(hw_params)
            preset = None  # HW 인코더는 자체 preset 사용

        write_kwargs: dict = {
            "fps": self.config.video.fps,
            "codec": hw_codec,
            "audio_codec": "aac",
            "ffmpeg_params": ffmpeg_extra,
        }
        if preset:
            write_kwargs["preset"] = preset

        # Sprint 3: 렌더링 벤치마크
        video_duration = final_video.duration
        render_start_time = time.perf_counter()

        try:
            final_video.write_videofile(str(output_path), **write_kwargs)
        finally:
            render_elapsed = time.perf_counter() - render_start_time

            # 벤치마크 결과 로깅
            speed_ratio = video_duration / max(render_elapsed, 0.001)
            logger.info(
                "[BENCHMARK] 인코딩 완료 — codec=%s | 영상=%.1fs | 렌더링=%.1fs | 속도=%.2fx (%s)",
                hw_codec,
                video_duration,
                render_elapsed,
                speed_ratio,
                "실시간보다 빠름" if speed_ratio > 1.0 else "실시간보다 느림",
            )
            print(
                f"\n[BENCHMARK] {hw_codec} | "
                f"영상 {video_duration:.1f}s → 렌더링 {render_elapsed:.1f}s "
                f"({speed_ratio:.2f}x {'⚡' if speed_ratio > 1.0 else '🐌'})\n"
            )

            # Phase 1-A: close ALL clips to prevent OOM in batch mode
            final_video.close()
            for clip in all_clips:
                try:
                    clip.close()
                except Exception:
                    pass
            for clip in _audio_clips_to_close:
                try:
                    clip.close()
                except Exception:
                    pass
            if _bgm_clip is not None:
                try:
                    _bgm_clip.close()
                except Exception:
                    pass
        return output_path
