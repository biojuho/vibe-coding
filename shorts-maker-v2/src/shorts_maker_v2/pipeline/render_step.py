from __future__ import annotations

import contextlib
import logging
import random
import time
from pathlib import Path
from typing import Any

import numpy as np
from moviepy import (
    CompositeAudioClip,
    CompositeVideoClip,
    ImageClip,
    VideoClip,
    VideoFileClip,
    concatenate_videoclips,
    vfx,
)
from moviepy.audio.fx import MultiplyVolume

from shorts_maker_v2.config import AppConfig
from shorts_maker_v2.models import SceneAsset, ScenePlan
from shorts_maker_v2.providers.llm_router import LLMRouter
from shorts_maker_v2.providers.openai_client import OpenAIClient
from shorts_maker_v2.render.animations import apply_text_animation

# HUD 오버레이 비활성화 (깔끔한 화면 유지)
from shorts_maker_v2.render.audio_postprocess import postprocess_tts_audio
from shorts_maker_v2.render.broll_overlay import create_broll_pip
from shorts_maker_v2.render.caption_pillow import (
    _OUTLINE_THICKNESS_MAP,
    CaptionStyle,
    apply_preset,
    calculate_safe_position,
    register_custom_styles,
    render_caption_image,
    resolve_channel_style,
)
from shorts_maker_v2.render.color_grading import color_grade_clip
from shorts_maker_v2.render.karaoke import (
    apply_ssml_break_correction,
    build_keyword_color_map,
    group_word_segments,
    load_words_json,
    render_karaoke_highlight_image,
    render_karaoke_image,
)
from shorts_maker_v2.render.video_renderer import ClipHandle, create_renderer

# MoviePy 2.x: PIL.Image.ANTIALIAS hotfix no longer needed (Pillow native)

logger = logging.getLogger(__name__)

_QUALITY_PROFILES = {
    "draft": {"crf": 28, "preset": "ultrafast", "maxrate": None},
    "standard": {"crf": 20, "preset": "medium", "maxrate": "8M"},
    "premium": {"crf": 16, "preset": "slow", "maxrate": "12M"},
}


class RenderStep:
    # YPP: 역할별 자막 프리셋 조합 로테이션 (반복적 콘텐츠 방지)
    _CAPTION_COMBOS: list[tuple[str, str, str]] = [
        # (hook_preset, body_preset, cta_preset)
        ("bold", "subtitle", "default"),  # 임팩트 → 영화적 → 깔끔
        ("neon", "default", "subtitle"),  # 네온 → 깔끔 → 영화적
        ("bold", "default", "neon"),  # 임팩트 → 깔끔 → 네온
        ("neon", "subtitle", "bold"),  # 네온 → 영화적 → 임팩트
        ("subtitle", "bold", "cta"),  # 영화적 → 임팩트 → CTA 특화
        ("default", "neon", "bold"),  # 깔끔 → 네온 → 임팩트
    ]
    _CHANNEL_STYLE_TUNING: dict[str, dict[str, int]] = {
        "ai_tech": {
            "margin_x": 72,
            "bottom_offset": 300,
            "line_spacing": 14,
        },
        "psychology": {
            "font_size": 68,
            "margin_x": 76,
            "bottom_offset": 330,
            "line_spacing": 16,
        },
    }
    _CHANNEL_MOTION_CHOICES: dict[str, dict[str, list[str] | str]] = {
        "ai_tech": {
            "hook": "dramatic_ken_burns",
            "body": ["pan_left", "pan_right", "ken_burns", "zoom_out"],
            "cta": ["zoom_out", "ken_burns"],
        },
        "psychology": {
            "hook": "ken_burns",
            "body": ["ken_burns", "zoom_out"],
            "cta": ["zoom_out"],
        },
    }
    _CHANNEL_TRANSITIONS: dict[str, dict[tuple[str, str], list[str]]] = {
        "ai_tech": {
            ("hook", "body"): ["flash", "glitch", "zoom"],
            ("body", "body"): ["slide", "zoom", "crossfade"],
            ("body", "cta"): ["zoom", "crossfade"],
            ("hook", "cta"): ["flash", "zoom"],
        },
        "psychology": {
            ("hook", "body"): ["crossfade", "slide"],
            ("body", "body"): ["crossfade", "slide"],
            ("body", "cta"): ["crossfade"],
            ("hook", "cta"): ["crossfade"],
        },
    }

    def __init__(
        self,
        config: AppConfig,
        openai_client: OpenAIClient | None = None,
        *,
        llm_router: LLMRouter | None = None,
        job_index: int = 0,
        channel_key: str = "",
        video_renderer_backend: str | None = None,
    ):
        self.config = config
        self._openai_client = openai_client
        self._llm_router = llm_router
        # Scene 조립은 아직 MoviePy native clip에 의존하므로,
        # backend 선택은 최종 encode 단계에만 적용합니다.
        self._renderer_backend = video_renderer_backend or "moviepy"
        self._native_renderer = create_renderer("moviepy")
        self._output_renderer = (
            self._native_renderer if self._renderer_backend == "moviepy" else create_renderer(self._renderer_backend)
        )
        self._job_index = job_index
        self._channel_key = channel_key
        self._channel_profile = self._load_channel_profile(channel_key)
        self._keyword_color_map = self._build_keyword_color_map()

        # YPP: bottom_offset에 ±20px 랜덤 변동
        offset_jitter = random.randint(-20, 20)
        style_tuning = self._CHANNEL_STYLE_TUNING.get(channel_key, {})
        tuned_font_size = max(48, style_tuning.get("font_size", config.captions.font_size))
        tuned_margin_x = max(40, style_tuning.get("margin_x", config.captions.margin_x))
        tuned_line_spacing = max(8, style_tuning.get("line_spacing", config.captions.line_spacing))
        tuned_bottom_offset = style_tuning.get("bottom_offset", config.captions.bottom_offset)
        jittered_offset = max(220, tuned_bottom_offset + offset_jitter)

        # Register user-defined custom styles before building base_style
        register_custom_styles(config.captions.custom_styles)

        # Resolve stroke_width from outline_thickness if stroke_width is default (0)
        stroke_w = config.captions.stroke_width
        if stroke_w == 0 and config.captions.outline_thickness != "medium":
            stroke_w = _OUTLINE_THICKNESS_MAP.get(config.captions.outline_thickness, 4)

        base_style = CaptionStyle(
            font_size=tuned_font_size,
            margin_x=tuned_margin_x,
            bottom_offset=jittered_offset,
            text_color=config.captions.text_color,
            stroke_color=config.captions.stroke_color,
            stroke_width=stroke_w,
            line_spacing=tuned_line_spacing,
            font_candidates=config.captions.font_candidates,
            mode=config.captions.mode,
            words_per_chunk=config.captions.words_per_chunk,
            bg_color=config.captions.bg_color,
            bg_opacity=config.captions.bg_opacity,
            bg_radius=config.captions.bg_radius,
            safe_zone_enabled=config.captions.safe_zone_enabled,
            center_hook=config.captions.center_hook,
            line_spacing_factor=config.captions.line_spacing_factor,
        )

        forced_preset = self._resolve_style_override()
        if forced_preset:
            combo = (forced_preset, forced_preset, forced_preset)
            logger.info(
                "[RenderStep] style_preset 강제 적용 — hook/body/cta=%s (channel=%r)",
                forced_preset,
                channel_key or "default",
            )
        else:
            # 채널별 caption_combo 우선 사용, 없으면 job_index 기반 로테이션
            combo = self._resolve_caption_combo(channel_key, job_index)
        # Apply channel_style_map overrides if configured
        channel_map = config.captions.channel_style_map
        hook_preset = resolve_channel_style(channel_key, "hook", channel_map) or combo[0]
        body_preset = resolve_channel_style(channel_key, "body", channel_map) or combo[1]
        cta_preset = resolve_channel_style(channel_key, "cta", channel_map) or combo[2]

        self.hook_style = apply_preset(base_style, hook_preset)
        self.body_style = apply_preset(base_style, body_preset)
        self.cta_style = apply_preset(base_style, cta_preset)

        logger.info(
            "[RenderStep] 자막 combo — hook=%s, body=%s, cta=%s (channel=%r)",
            combo[0],
            combo[1],
            combo[2],
            channel_key or "default",
        )

    @staticmethod
    def _load_channel_profile(channel_key: str) -> dict:
        if not channel_key:
            return {}
        try:
            from shorts_maker_v2.utils.channel_router import ChannelRouter

            return ChannelRouter().get_profile(channel_key)
        except Exception as exc:
            logger.warning("[RenderStep] 채널 프로파일 로드 실패: %s", exc)
            return {}

    def _build_keyword_color_map(self) -> dict[str, tuple[int, int, int, int]] | None:
        keywords = self._channel_profile.get("highlight_keywords")
        if not keywords:
            return None
        color = self._channel_profile.get(
            "highlight_color",
            self.config.captions.highlight_color,
        )
        return build_keyword_color_map(list(keywords), color)

    def _resolve_style_override(self) -> str:
        preset = str(getattr(self.config.captions, "style_preset", "") or "").strip()
        return "" if preset in {"", "default"} else preset

    # ── Renderer helpers (native clip passthrough) ─────────────────────────────

    def _load_video_clip(self, path: str | Path, audio: bool = True):
        """MoviePy renderer 경유 비디오 로드 -> native clip 반환."""
        return self._native_renderer.load_video(path, audio=audio).native

    def _load_image_clip(self, path: str | Path, duration: float = 5.0):
        """MoviePy renderer 경유 이미지 로드 -> native clip 반환."""
        return self._native_renderer.load_image(path, duration=duration).native

    def _load_audio_clip(self, path: str | Path):
        """MoviePy renderer 경유 오디오 로드 -> native clip 반환."""
        return self._native_renderer.load_audio(path).native

    @staticmethod
    def try_render_with_adapter(
        *,
        channel: str,
        scene_plans: list[ScenePlan],
        scene_assets: list[SceneAsset],
        output_path: Path,
        logger: Any,
    ) -> tuple[bool, str | None]:
        """RenderAdapter를 통한 ShortsFactory 렌더링을 시도합니다.

        Render 관련 ScenePlan/SceneAsset → adapter payload 변환은 render_step이
        담당하고, orchestrator는 renderer mode 라우팅만 맡도록 역할을 분리합니다.
        """
        try:
            from ShortsFactory.interfaces import RenderAdapter

            adapter = RenderAdapter()
            scenes_data = [scene_plan.to_dict() for scene_plan in scene_plans]
            assets_map = {asset.scene_id: asset.visual_path for asset in scene_assets}
            audio_map = {asset.scene_id: asset.audio_path for asset in scene_assets if asset.audio_path}

            result = adapter.render_with_plan(
                channel_id=channel,
                scenes=scenes_data,
                assets=assets_map,
                output_path=output_path,
                audio_paths=audio_map or None,
            )

            if result.success:
                logger.info(
                    "shorts_factory_render_ok",
                    channel=channel,
                    template=result.template_used,
                    duration_sec=result.duration_sec,
                )
                return True, None

            logger.warning(
                "shorts_factory_render_failed",
                channel=channel,
                error=result.error,
                fallback="native_render_step",
            )
            return False, result.error or "ShortsFactory render failed"

        except Exception as exc:
            logger.warning(
                "shorts_factory_import_failed",
                error=str(exc),
                fallback="native_render_step",
            )
            return False, str(exc)

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
                        channel_key,
                        combo_list,
                    )
                    return tuple(combo_list)  # type: ignore[return-value]
            except Exception as exc:
                logger.warning("[RenderStep] caption_combo 로드 실패: %s", exc)

        # 폴백: job_index 기반 로테이션
        combo = cls._CAPTION_COMBOS[job_index % len(cls._CAPTION_COMBOS)]
        logger.info("[RenderStep] 로테이션 combo 사용 (job_index=%d): %s", job_index, combo)
        return combo

    def _build_effect_map(self, target_width: int, target_height: int) -> dict:
        """모든 카메라 모션 효과의 단일 매핑."""
        return {
            "ken_burns": lambda c: self._ken_burns(c, target_width, target_height),
            "dramatic_ken_burns": lambda c: self._dramatic_ken_burns(c, target_width, target_height),
            "zoom_out": lambda c: self._zoom_out(c, target_width, target_height),
            "pan_left": lambda c: self._pan_horizontal(c, target_width, target_height, +1),
            "pan_right": lambda c: self._pan_horizontal(c, target_width, target_height, -1),
            "drift": lambda c: self._drift(c, target_width, target_height),
            "push_in": lambda c: self._push_in(c, target_width, target_height),
            "shake": lambda c: self._shake(c, target_width, target_height, fps=self.config.video.fps),
            "ease_ken_burns": lambda c: self._ease_ken_burns(c, target_width, target_height),
        }

    # 랜덤 풀에서 제외할 효과 (명시적 지정에서만 사용)
    _RANDOM_EXCLUDE = {"shake", "dramatic_ken_burns"}

    def _apply_named_effect(self, effect_name: str, clip, target_width: int, target_height: int):
        effect_map = self._build_effect_map(target_width, target_height)
        fn = effect_map.get(effect_name)
        if fn is None:
            return self._apply_random_effect(clip, target_width, target_height)
        return fn(clip), effect_name

    def _apply_channel_image_motion(
        self,
        clip,
        *,
        role: str,
        target_width: int,
        target_height: int,
        exclude: str = "",
    ):
        channel_motion = self._CHANNEL_MOTION_CHOICES.get(self._channel_key, {})
        motion = channel_motion.get(role)
        if isinstance(motion, str):
            return self._apply_named_effect(motion, clip, target_width, target_height)
        if isinstance(motion, list) and motion:
            candidates = [name for name in motion if name != exclude] or motion
            chosen = random.choice(candidates)
            return self._apply_named_effect(chosen, clip, target_width, target_height)
        if role == "hook":
            return self._apply_named_effect("dramatic_ken_burns", clip, target_width, target_height)
        return self._apply_random_effect(clip, target_width, target_height, exclude=exclude)

    @staticmethod
    def _caption_y(clip, target_height: int, style: CaptionStyle, role: str = "body") -> int:
        """Calculate caption Y position with safe zone awareness."""
        if style.safe_zone_enabled:
            return calculate_safe_position(target_height, clip.h, style, role)
        return max(80, int(target_height - clip.h - style.bottom_offset))

    def _render_static_caption(
        self,
        text: str,
        target_width: int,
        style: CaptionStyle,
        output_path: Path,
        role: str,
    ) -> Path:
        """정적 자막 렌더링. hook 씬에서 그라디언트+글로우를 시도합니다."""
        if role == "hook" and self._channel_key:
            try:
                from ShortsFactory.engines.text_engine import TextEngine

                channel_cfg = self._channel_profile or {}
                engine = TextEngine(channel_cfg)
                # 그라디언트 텍스트 우선 시도
                try:
                    return engine.render_gradient_text(
                        text,
                        role="hook",
                        output_path=output_path,
                    )
                except Exception:
                    pass
                # 폴백: 글로우 자막
                return engine.render_subtitle_with_glow(
                    text,
                    role="hook",
                    output_path=output_path,
                )
            except Exception as exc:
                logger.debug("[TextEngine] glow/gradient 폴백: %s", exc)
        return render_caption_image(text, target_width, style, output_path)

    def _build_bookend_clip(self, path_str: str, duration: float, target_width: int, target_height: int):
        """인트로/아웃트로 클립 빌드 (이미지 또는 비디오)."""
        path = Path(path_str)
        if not path.exists():
            return None
        ext = path.suffix.lower()
        if ext in (".mp4", ".mov", ".avi", ".webm"):
            clip = self._load_video_clip(path, audio=False)
            clip = clip.subclipped(0, min(clip.duration, duration))
        elif ext in (".png", ".jpg", ".jpeg", ".webp"):
            clip = self._load_image_clip(path, duration=duration)
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
            return frame[y1 : y1 + target_height, x1 : x1 + target_width]

        return zoomed.transform(make_frame).with_duration(clip.duration)

    @staticmethod
    def _drift(clip, target_width: int, target_height: int, speed: float = 0.04):
        """Body 씬용 느린 수평 드리프트 (미세한 움직임감)."""
        overscan = 0.06
        zoomed = clip.resized(1.0 + overscan)
        max_shift = zoomed.w * overscan / 2
        dur = max(clip.duration, 0.001)
        zw, zh = zoomed.w, zoomed.h

        def make_frame(get_frame, t):
            frame = get_frame(t)
            progress = (t / dur) * 2 - 1  # -1 to +1
            cx = zw / 2 + max_shift * progress * speed / 0.04
            x1 = int(max(0, min(cx - target_width / 2, zw - target_width)))
            y1 = int(max(0, (zh - target_height) / 2))
            return frame[y1 : y1 + target_height, x1 : x1 + target_width]

        return zoomed.transform(make_frame).with_duration(clip.duration)

    @staticmethod
    def _push_in(clip, target_width: int, target_height: int, zoom: float = 0.08):
        """CTA 씬용 점진적 줌인 (긴박감 연출). ease-out 커브 적용."""

        def resize_func(t: float) -> float:
            progress = t / max(clip.duration, 0.001)
            # ease-out: 1 - (1-p)^2
            eased = 1.0 - (1.0 - progress) ** 2
            return 1.0 + zoom * eased

        zoomed = clip.resized(resize_func)
        return zoomed.cropped(
            x_center=zoomed.w / 2,
            y_center=zoomed.h / 2,
            width=target_width,
            height=target_height,
        )

    @staticmethod
    def _shake(clip, target_width: int, target_height: int, amplitude: int = 3, fps: int = 30):
        """Hook 씬용 미세 진동 효과 (충격/긴장감)."""

        overscan = 0.04
        zoomed = clip.resized(1.0 + overscan)
        dur = max(clip.duration, 0.001)
        zw, zh = zoomed.w, zoomed.h
        cx, cy = zw / 2, zh / 2
        # Pre-generate random offsets for deterministic rendering
        n_frames = max(1, int(dur * fps))
        rng = np.random.RandomState(42)
        offsets_x = rng.randint(-amplitude, amplitude + 1, size=n_frames)
        offsets_y = rng.randint(-amplitude, amplitude + 1, size=n_frames)

        def make_frame(get_frame, t):
            frame = get_frame(t)
            # Shake intensity decays over time (strongest at start)
            decay = max(0.0, 1.0 - t / dur * 0.7)
            idx = min(int(t * fps), n_frames - 1)
            ox = int(offsets_x[idx] * decay)
            oy = int(offsets_y[idx] * decay)
            x1 = int(max(0, min(cx - target_width / 2 + ox, zw - target_width)))
            y1 = int(max(0, min(cy - target_height / 2 + oy, zh - target_height)))
            return frame[y1 : y1 + target_height, x1 : x1 + target_width]

        return zoomed.transform(make_frame).with_duration(clip.duration)

    @staticmethod
    def _ease_ken_burns(clip, target_width: int, target_height: int, zoom: float = 0.08):
        """ease-in-out Ken Burns (부드러운 시작/끝). Body 씬에 적합."""

        def resize_func(t: float) -> float:
            progress = t / max(clip.duration, 0.001)
            # ease-in-out: cubic
            eased = 4 * progress**3 if progress < 0.5 else 1 - (-2 * progress + 2) ** 3 / 2
            return 1.0 + zoom * eased

        zoomed = clip.resized(resize_func)
        return zoomed.cropped(
            x_center=zoomed.w / 2,
            y_center=zoomed.h / 2,
            width=target_width,
            height=target_height,
        )

    def _apply_random_effect(self, clip, target_width: int, target_height: int, *, exclude: str = ""):
        """zoom-in / zoom-out / pan / drift / push_in / ease_ken_burns 중 랜덤 선택 (exclude로 연속 동일 효과 방지)."""
        all_effects = self._build_effect_map(target_width, target_height)
        excluded = self._RANDOM_EXCLUDE | {exclude}
        candidates = {k: v for k, v in all_effects.items() if k not in excluded}
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
            base = self._load_video_clip(asset.visual_path, audio=False)
            if base.duration < duration_sec:
                base = base.with_effects([vfx.Loop(duration=duration_sec)])
            elif base.duration > duration_sec:
                base = base.subclipped(0, duration_sec)
        else:
            base = self._load_image_clip(asset.visual_path, duration=duration_sec)
        return self._fit_vertical(base, target_width, target_height)

    # ── BGM 무드 매칭 ─────────────────────────────────────────────────────────

    # 무드별 한국어 키워드 (파일명에도 활용)
    _MOOD_KEYWORDS: dict[str, list[str]] = {
        "dramatic": [
            "블랙홀",
            "우주",
            "죽음",
            "사망",
            "재앙",
            "공포",
            "위험",
            "충격",
            "비밀",
            "경고",
            "무서운",
            "진실",
            "폭발",
            "전쟁",
            "붕괴",
            "최후",
            "멸종",
        ],
        "upbeat": [
            "돈",
            "절약",
            "성공",
            "방법",
            "비결",
            "팁",
            "건강",
            "행복",
            "성장",
            "개선",
            "효과",
            "좋은",
            "최고",
            "쉬운",
            "간단",
            "빠른",
            "부자",
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
            'Choose exactly one: "dramatic", "upbeat", or "calm".\n'
            'Output JSON: {"mood": "..."}'
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
            return random.choice(["crossfade", "flash", "glitch", "zoom", "slide", "wipe", "iris"])
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
            arr = np.ones((target_height, target_width, 3), dtype="uint8") * 255
            return ImageClip(arr, is_mask=False).with_duration(0.12)

        def _structural_style(prev_role: str, cur_role: str) -> str:
            """Phase 4-C: 역할 쌍에 따른 전환 스타일 결정."""
            pair = (prev_role, cur_role)
            channel_mapping = self._CHANNEL_TRANSITIONS.get(self._channel_key, {})
            if pair in channel_mapping:
                return random.choice(channel_mapping[pair])
            mapping: dict[tuple[str, str], list[str]] = {
                ("hook", "body"): ["flash", "glitch", "zoom", "rgb_split", "iris"],  # 강한 전환
                ("hook", "cta"): ["flash", "zoom", "iris"],  # 직접 CTA
                ("body", "body"): ["crossfade", "slide", "wipe", "morph_cut"],  # 부드러운 흐름
                ("body", "cta"): ["crossfade", "slide", "zoom", "wipe"],  # 자연스러운 마무리
                ("cta", "body"): ["flash", "glitch", "rgb_split"],  # 재시작 강조
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
                # Glitch: RGB 채널 분리 + 흰색 플래시 (0.2초)
                glitch_dur = 0.2

                def _glitch_factory(_clip, _glitch_dur, _tw, _th):
                    def _filter(get_frame, t):
                        frame = get_frame(t)
                        remaining = _clip.duration - t
                        if remaining > _glitch_dur:
                            return frame
                        progress = 1.0 - (remaining / max(0.01, _glitch_dur))
                        shift = int(18 * (1.0 - progress))
                        if shift == 0:
                            return frame
                        out = np.copy(frame)
                        # R 채널 오른쪽, B 채널 왼쪽 이동
                        if shift < _tw:
                            out[:, shift:, 0] = frame[:, :-shift, 0]
                            out[:, :-shift, 2] = frame[:, shift:, 2]
                        # 스캔라인 노이즈 (짝수 행)
                        out[::2, :, :] = np.clip(
                            out[::2, :, :].astype(np.int16) + int(30 * (1.0 - progress)), 0, 255
                        ).astype(np.uint8)
                        return out

                    return _filter

                clip = clip.transform(_glitch_factory(clip, glitch_dur, target_width, target_height))
                result.append(clip)
                if not is_last:
                    # 짧은 흰색 플래시
                    flash_arr = np.ones((target_height, target_width, 3), dtype="uint8") * 255
                    result.append(ImageClip(flash_arr, is_mask=False).with_duration(0.06))
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
            elif style == "wipe":
                # Wipe: 왼→오 와이프 전환 (이전 클립 위에 다음 클립이 덮어감)

                if i > 0 and len(result) > 0:
                    wipe_dur = min(fade_sec * 2, 0.5)
                    prev_clip = result[-1]

                    def _wipe_mask_factory(_wipe_dur, _tw, _th):
                        def _make_mask(t):
                            buf = np.zeros((_th, _tw), dtype="float32")
                            progress = min(1.0, t / max(0.01, _wipe_dur))
                            reveal_w = int(_tw * progress)
                            if reveal_w > 0:
                                buf[:, :reveal_w] = 1.0
                            return buf

                        return _make_mask

                    wipe_mask = VideoClip(
                        _wipe_mask_factory(wipe_dur, target_width, target_height),
                        duration=wipe_dur,
                        is_mask=True,
                    )
                    wipe_clip = clip.subclipped(0, wipe_dur)
                    wipe_clip = wipe_clip.with_start(prev_clip.duration - wipe_dur)
                    wipe_clip = wipe_clip.with_mask(wipe_mask)
                    # 이전 클립 유지 + 와이프 오버레이
                    combined = CompositeVideoClip(
                        [prev_clip, wipe_clip],
                        size=(target_width, target_height),
                    ).with_duration(prev_clip.duration)
                    result[-1] = combined
                else:
                    result.append(clip)
            elif style == "iris":
                # Iris: 원형으로 확장되며 등장 (아이리스 전환)

                iris_dur = min(fade_sec * 2, 0.4)

                def _iris_filter_factory(_iris_dur, _tw, _th):
                    cx, cy = _tw / 2, _th / 2
                    max_r = (_tw**2 + _th**2) ** 0.5 / 2
                    # 거리 그리드 한 번만 계산
                    y_grid, x_grid = np.ogrid[:_th, :_tw]
                    _dist = np.sqrt((x_grid - cx) ** 2 + (y_grid - cy) ** 2)

                    def _filter(get_frame, t):
                        frame = get_frame(t)
                        if t >= _iris_dur:
                            return frame
                        progress = t / max(0.01, _iris_dur)
                        radius = max_r * progress
                        mask = (_dist <= radius).astype(np.float32)
                        mask_3d = mask[:, :, np.newaxis]
                        return (frame.astype(np.float32) * mask_3d).astype(np.uint8)

                    return _filter

                clip = clip.transform(_iris_filter_factory(iris_dur, target_width, target_height))
                result.append(clip)
            elif style == "rgb_split":
                # RGB Split: RGB 채널 분리 글리치 전환

                split_dur = min(fade_sec, 0.25)

                def _rgb_split_factory(_split_dur):
                    def _filter(get_frame, t):
                        frame = get_frame(t)
                        if t >= _split_dur:
                            return frame
                        progress = 1.0 - (t / max(0.01, _split_dur))
                        shift = int(12 * progress)
                        if shift == 0:
                            return frame
                        out = np.copy(frame)
                        # R 채널 오른쪽, B 채널 왼쪽 이동
                        out[:, shift:, 0] = frame[:, :-shift, 0]
                        out[:, :-shift, 2] = frame[:, shift:, 2]
                        return out

                    return _filter

                clip = clip.transform(_rgb_split_factory(split_dur))
                result.append(clip)
            elif style == "morph_cut":
                # Morph Cut: 급속 줌인 + 페이드 (점프컷 부드러움)
                if fade_sec > 0:
                    morph_dur = min(fade_sec, 0.3)
                    if not is_last:
                        clip = clip.with_effects([vfx.FadeOut(morph_dur)])
                    if i > 0:
                        clip = clip.with_effects([vfx.FadeIn(morph_dur)])

                        # 약간의 줌인으로 시작 (1.05x → 1.0x)
                        def _morph_resize_factory(_morph_dur):
                            def _resize(t):
                                if t >= _morph_dur:
                                    return 1.0
                                return 1.05 - 0.05 * (t / max(0.01, _morph_dur))

                            return _resize

                        clip = clip.resized(_morph_resize_factory(morph_dur))
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
        matched = [f for f in bgm_files if any(k in f.stem.lower() for k in mood_keys)]
        if matched:
            chosen = random.choice(matched)
            logger.info("[BGM] mood=%s → %s", mood, chosen.name)
            return chosen
        chosen = random.choice(bgm_files)
        logger.info("[BGM] mood=%s (no match, random fallback) → %s", mood, chosen.name)
        return chosen

    @staticmethod
    def _collect_bgm_files(bgm_dir: Path) -> list[Path]:
        files: list[Path] = []
        for pattern in ("*.mp3", "*.wav", "*.m4a", "*.aac"):
            files.extend(bgm_dir.glob(pattern))
        return sorted(files)

    def _generate_lyria_bgm(
        self,
        *,
        run_dir: Path,
        duration_sec: float,
        channel: str = "",
        topic: str = "",
    ) -> Path | None:
        """Google Lyria로 영상 길이에 맞는 맞춤 BGM을 생성합니다.

        Returns:
            생성된 BGM 파일 경로 또는 None (실패 시)
        """
        import asyncio
        import os

        api_key = os.getenv("GEMINI_API_KEY", "")
        if not api_key:
            logger.info("[BGM/Lyria] GEMINI_API_KEY 없음 → local fallback")
            return None

        # 채널별 프롬프트 결정
        prompt_map = self.config.audio.lyria_prompt_map or {}
        prompt = prompt_map.get(channel, prompt_map.get("default", ""))
        if not prompt:
            prompt = "calm lo-fi beats with soft piano, minimal percussion, background music"

        bgm_path = run_dir / "bgm_lyria.mp3"
        if bgm_path.exists() and bgm_path.stat().st_size > 0:
            logger.info("[BGM/Lyria] 캐시 사용: %s", bgm_path.name)
            return bgm_path

        try:
            from shorts_maker_v2.providers.google_music_client import GoogleMusicClient

            client = GoogleMusicClient.from_env()
            # Lyria 생성: 영상 길이 + 2초 여유
            coro = client.generate_music_file(
                prompt=prompt,
                output_path=bgm_path,
                duration_sec=min(duration_sec + 2, 120),
                bpm=90,
                temperature=1.0,
            )
            try:
                asyncio.run(coro)
            except RuntimeError as exc:
                if "event loop" not in str(exc).lower() and "running" not in str(exc).lower():
                    raise
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(asyncio.run, coro)
                    future.result()

            if bgm_path.exists() and bgm_path.stat().st_size > 0:
                logger.info("[BGM/Lyria] 생성 완료: %s (%.1fs)", bgm_path.name, duration_sec)
                return bgm_path
        except Exception as exc:
            logger.warning("[BGM/Lyria] 생성 실패: %s → local fallback", exc)

        return None

    @staticmethod
    def _apply_rms_ducking(
        narration_audio,
        bgm_clip,
        *,
        base_vol: float = 0.12,
        duck_factor: float = 0.25,
        window_sec: float = 0.5,
    ):
        """RMS 기반 Audio Ducking: 나레이션이 있는 구간에서 BGM 볼륨을 자동 감소.

        나레이션 RMS가 높은 구간 → BGM 볼륨을 duck_factor로 감소
        나레이션이 없는 구간 → BGM 볼륨을 base_vol 그대로 유지
        """
        try:
            nar_dur = narration_audio.duration
            if not nar_dur or nar_dur <= 0:
                return bgm_clip.with_effects([MultiplyVolume(base_vol)])

            # 나레이션 RMS 에너지를 window_sec 간격으로 샘플링
            fps = 44100
            nar_array = narration_audio.to_soundarray(fps=fps)
            if nar_array.ndim > 1:
                nar_array = nar_array.mean(axis=1)

            window_samples = int(window_sec * fps)
            n_windows = max(1, len(nar_array) // window_samples)

            rms_values = []
            for i in range(n_windows):
                chunk = nar_array[i * window_samples : (i + 1) * window_samples]
                rms = float(np.sqrt(float(np.mean(chunk**2))))
                rms_values.append(rms)

            # RMS 임계값: 평균의 30%를 기준으로 음성 구간 판별
            if not rms_values:
                return bgm_clip.with_effects([MultiplyVolume(base_vol)])

            rms_threshold = float(np.mean(rms_values)) * 0.3
            speech_count = sum(1 for r in rms_values if r > rms_threshold)

            # 음성 구간 비율로 전체 BGM 볼륨 결정 (chunk 분할 대신 간단한 접근)
            # 음성 비율이 높으면 전체적으로 낮은 볼륨, 낮으면 약간 높은 볼륨
            speech_ratio = speech_count / max(len(rms_values), 1)
            effective_vol = base_vol * (duck_factor + (1 - duck_factor) * (1 - speech_ratio))

            ducked = bgm_clip.with_effects([MultiplyVolume(effective_vol)])
            logger.info(
                "[BGM/Ducking] RMS ducking 적용: speech=%d/%d (%.0f%%), vol=%.2f",
                speech_count,
                len(rms_values),
                speech_ratio * 100,
                effective_vol,
            )
            return ducked
        except Exception as exc:
            logger.warning("[BGM/Ducking] RMS ducking 실패, 고정 볼륨 사용: %s", exc)
            return bgm_clip.with_effects([MultiplyVolume(base_vol)])

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
        for i, (role, dur) in enumerate(zip(scene_roles, scene_durations, strict=False)):
            # Hook 씬 시작에 임팩트 SFX
            if role == "hook" and sfx_files.get("hook"):
                sfx_path = random.choice(sfx_files["hook"])
                clip = self._load_audio_clip(sfx_path)
                clip = clip.with_effects([MultiplyVolume(volume)])
                sfx_clips.append(clip.with_start(cursor))
            # CTA 씬 시작에 팝 SFX
            elif role == "cta" and sfx_files.get("cta"):
                sfx_path = random.choice(sfx_files["cta"])
                clip = self._load_audio_clip(sfx_path)
                clip = clip.with_effects([MultiplyVolume(volume)])
                sfx_clips.append(clip.with_start(cursor))
            # 씬 전환 시점에 스위시 SFX (마지막 씬 제외)
            if i < len(scene_roles) - 1 and sfx_files.get("transition"):
                sfx_path = random.choice(sfx_files["transition"])
                clip = self._load_audio_clip(sfx_path)
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
        _caption_clips_to_close: list = []  # karaoke ImageClip 추적 (close 용)
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

        # ── 제목/HUD 오버레이 비활성화 (깔끔한 화면 유지) ──

        # ── 씬별 클립 빌드 ──
        for plan, asset in zip(scene_plans, scene_assets, strict=False):
            duration_sec = asset.duration_sec
            role = plan.structure_role
            scene_roles.append(role)

            # 1) 베이스 비주얼 클립
            base = self._build_base_clip(asset, duration_sec, target_width, target_height)

            # 2) 카메라 효과 (Ken Burns 등)
            if asset.visual_type == "image":
                base, last_effect = self._apply_channel_image_motion(
                    base,
                    role=role,
                    target_width=target_width,
                    target_height=target_height,
                    exclude=last_effect,
                )

            # 2.5) 색보정 (채널별 컬러 그레이딩 + 비네트)
            try:
                base = color_grade_clip(base, self._channel_key, role)
            except Exception as cg_exc:
                logger.warning("[ColorGrade] 색보정 실패: %s", cg_exc)

            # 2.9) TTS 오디오 후처리 (노멀라이즈 + EQ)
            try:
                postprocess_tts_audio(
                    Path(asset.audio_path),
                    voice_name=self.config.providers.tts_voice,
                )
            except Exception as pp_exc:
                logger.warning("[AudioPost] 후처리 실패, 원본 사용: %s", pp_exc)

            # 3) 오디오 합성
            audio = self._load_audio_clip(asset.audio_path)
            _audio_clips_to_close.append(audio)  # 생성 직후 등록 → 예외 시에도 close 보장
            if audio.duration != duration_sec and audio.duration > duration_sec:
                audio = audio.subclipped(0, duration_sec)
                # audio shorter than visual → visual에 맞춤 (음성 끝 자연 종료)
            base = base.with_audio(audio)

            # 4) 자막 오버레이
            style = self.hook_style if role == "hook" else self.cta_style if role == "cta" else self.body_style

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
                    chunk_groups = group_word_segments(corrected_words, style.words_per_chunk)
                    chunks = [(start, end, text) for start, end, text, _ in chunk_groups]

                    # Word-level highlight 모드
                    if self.config.captions.highlight_mode == "word":
                        caption_clips = []
                        for _chunk_start, _chunk_end, _chunk_text, chunk_words in chunk_groups:
                            chunk_text_words = [word.word for word in chunk_words]
                            for wi, word_segment in enumerate(chunk_words):
                                ws = word_segment.start
                                wd = max(0.05, word_segment.end - word_segment.start)
                                highlight_out = run_dir / f"kh_{plan.scene_id:02d}_{word_segment.start:.2f}_{wi}.png"
                                render_karaoke_highlight_image(
                                    words=chunk_text_words,
                                    active_word_index=wi,
                                    canvas_width=target_width,
                                    style=style,
                                    highlight_color=self.config.captions.highlight_color,
                                    output_path=highlight_out,
                                    keyword_colors=self._keyword_color_map,
                                )
                                highlight_clip = ImageClip(str(highlight_out), transparent=True)
                                _caption_clips_to_close.append(highlight_clip)
                                cap_clip = (
                                    highlight_clip.with_duration(wd)
                                    .with_start(ws)
                                    .with_position(
                                        ("center", self._caption_y(highlight_clip, target_height, style, role))
                                    )
                                )
                                caption_clips.append(cap_clip)
                    else:
                        caption_clips = []
                        for chunk_start, chunk_end, chunk_text in chunks:
                            cd = max(0.1, chunk_end - chunk_start)
                            cap_out = run_dir / f"kc_{plan.scene_id:02d}_{chunk_start:.2f}.png"
                            render_karaoke_image(chunk_text, target_width, style, cap_out)
                            caption_image = ImageClip(str(cap_out), transparent=True)
                            _caption_clips_to_close.append(caption_image)
                            cap_clip = (
                                caption_image.with_duration(cd)
                                .with_start(chunk_start)
                                .with_position(("center", self._caption_y(caption_image, target_height, style, role)))
                            )
                            caption_clips.append(cap_clip)

                    if caption_clips:
                        base = CompositeVideoClip([base] + caption_clips, size=(target_width, target_height))

                except Exception as kex:
                    logger.warning("[Karaoke] 카라오케 실패, 정적 자막 폴백: %s", kex)
                    cap_out = run_dir / f"caption_fallback_{plan.scene_id:02d}.png"
                    cap_img = self._render_static_caption(
                        plan.narration_ko,
                        target_width,
                        style,
                        cap_out,
                        role,
                    )
                    cap_clip_img = ImageClip(str(cap_img), transparent=True)
                    _caption_clips_to_close.append(cap_clip_img)
                    cap_clip = cap_clip_img.with_duration(duration_sec).with_position(
                        ("center", self._caption_y(cap_clip_img, target_height, style, role))
                    )
                    base = CompositeVideoClip([base, cap_clip], size=(target_width, target_height))
            else:
                # 정적 자막 모드 — hook 씬에서 TextEngine glow 시도
                cap_out = run_dir / f"caption_static_{plan.scene_id:02d}.png"
                cap_img = self._render_static_caption(
                    plan.narration_ko,
                    target_width,
                    style,
                    cap_out,
                    role,
                )
                cap_clip_img = ImageClip(str(cap_img), transparent=True)
                _caption_clips_to_close.append(cap_clip_img)
                cap_clip = cap_clip_img.with_duration(duration_sec).with_position(
                    ("center", self._caption_y(cap_clip_img, target_height, style, role))
                )
                base = CompositeVideoClip([base, cap_clip], size=(target_width, target_height))

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
                    pip_clip = create_broll_pip(str(broll_path), duration_sec, target_width, target_height)
                    if pip_clip is not None:
                        base = CompositeVideoClip([base, pip_clip], size=(target_width, target_height))
                except Exception:
                    pass

            # 7) HUD 오버레이 — 비활성화 (깔끔한 화면 유지)
            # 8) 제목 오버레이 — 비활성화

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

        # ── YouTube Shorts 하드 리밋 (59초) ──
        MAX_SHORTS_DURATION = 59.0  # YouTube Shorts 최대 60초, 1초 마진
        if final_video.duration and final_video.duration > MAX_SHORTS_DURATION:
            logger.warning(
                "[DURATION] 영상 %.1fs > %.1fs — Shorts 제한에 맞게 트림",
                final_video.duration,
                MAX_SHORTS_DURATION,
            )
            final_video = final_video.subclipped(0, MAX_SHORTS_DURATION)

        # BGM: Lyria AI 생성 (1순위) → local assets 폴백
        target_dur = final_video.duration
        bgm_clip = None

        # 1순위: Lyria AI BGM (영상 길이에 맞는 맞춤 BGM)
        if self.config.audio.bgm_provider == "lyria" and final_video.audio is not None:
            lyria_bgm = self._generate_lyria_bgm(
                run_dir=run_dir,
                duration_sec=target_dur,
                channel=getattr(self, "_channel_key", ""),
                topic=topic or title,
            )
            if lyria_bgm:
                bgm_clip = self._load_audio_clip(lyria_bgm)
                _bgm_clip = bgm_clip
                if bgm_clip.duration and bgm_clip.duration > target_dur:
                    bgm_clip = bgm_clip.subclipped(0, target_dur)
                logger.info("[BGM] Lyria AI BGM 사용: %s", lyria_bgm.name)

        # 2순위: local assets/bgm 폴백 (크로스페이드 루핑)
        if bgm_clip is None and final_video.audio is not None:
            bgm_dir = (run_dir.parent.parent / self.config.audio.bgm_dir).resolve()
            if bgm_dir.exists():
                bgm_files = self._collect_bgm_files(bgm_dir)
                if bgm_files:
                    bgm_path = self._pick_bgm_by_mood(bgm_files, topic or title)
                    bgm_clip = self._load_audio_clip(bgm_path)
                    _bgm_clip = bgm_clip
                    # 크로스페이드 루핑 (끊김 방지)
                    if bgm_clip.duration and bgm_clip.duration < target_dur:
                        repeats = int(target_dur / bgm_clip.duration) + 1
                        from moviepy import concatenate_audioclips

                        # 단순 반복 루핑 (오디오 클립에 비디오 이펙트 적용 불가)
                        bgm_clip = concatenate_audioclips([bgm_clip] * repeats)
                    bgm_clip = bgm_clip.subclipped(0, target_dur)
                    logger.info("[BGM] local 파일 사용: %s", bgm_path.name)

        # RMS 기반 Ducking 적용
        if bgm_clip is not None and final_video.audio is not None:
            base_vol = self.config.audio.bgm_volume
            duck_factor = self.config.audio.ducking_factor
            bgm_clip = self._apply_rms_ducking(
                final_video.audio,
                bgm_clip,
                base_vol=base_vol,
                duck_factor=duck_factor,
            )
            mixed_audio = CompositeAudioClip([final_video.audio, bgm_clip])
            final_video = final_video.with_audio(mixed_audio)

        # SFX 효과음 레이어
        if self.config.audio.sfx_enabled:
            sfx_files = self._load_sfx_files(run_dir)
            if sfx_files:
                scene_durations = [a.duration_sec for a in scene_assets]
                sfx_clips = self._build_sfx_clips(scene_roles, scene_durations, sfx_files)
                if sfx_clips and final_video.audio is not None:
                    _audio_clips_to_close.extend(sfx_clips)
                    all_audio = [final_video.audio] + sfx_clips
                    final_video = final_video.with_audio(CompositeAudioClip(all_audio))
                    logger.info("[SFX] %d effects applied", len(sfx_clips))

        # HW 가속 인코더 자동 감지
        from shorts_maker_v2.utils.hwaccel import detect_gpu_info, detect_hw_encoder

        hw_codec, hw_params = detect_hw_encoder(self.config.video.hw_accel)

        # Sprint 3: GPU 정보 로깅
        try:
            gpu_info = detect_gpu_info()
            logger.info(
                "[RENDER] GPU: %s | Encoder: %s | HW Decode: %s",
                gpu_info["gpu_name"],
                gpu_info["encoder"],
                gpu_info["decoder_support"],
            )
        except Exception as gpu_exc:
            logger.debug("[RENDER] GPU 정보 조회 실패: %s", gpu_exc)

        # ── Quality Profile 적용 ──
        qp = _QUALITY_PROFILES.get(self.config.video.quality_profile, _QUALITY_PROFILES["standard"])

        if hw_codec == "libx264":
            ffmpeg_extra = [
                "-crf",
                str(qp["crf"]),
                "-pix_fmt",
                "yuv420p",
            ]
            # Bitrate cap for YouTube optimization
            if qp["maxrate"]:
                ffmpeg_extra.extend(["-maxrate", qp["maxrate"], "-bufsize", qp["maxrate"]])
            preset = qp["preset"]
        else:
            ffmpeg_extra = list(hw_params)
            preset = None

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
            handle = ClipHandle(
                backend=self._renderer_backend,
                native=final_video,
                duration=video_duration,
            )
            self._output_renderer.write(
                handle,
                output_path,
                fps=write_kwargs.get("fps", 30),
                codec=write_kwargs.get("codec", "libx264"),
                audio_codec=write_kwargs.get("audio_codec", "aac"),
                preset=write_kwargs.get("preset"),
                ffmpeg_params=write_kwargs.get("ffmpeg_params"),
            )
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
                with contextlib.suppress(Exception):
                    clip.close()
            for clip in _audio_clips_to_close:
                with contextlib.suppress(Exception):
                    clip.close()
            if _bgm_clip is not None:
                with contextlib.suppress(Exception):
                    _bgm_clip.close()
            for clip in _caption_clips_to_close:
                with contextlib.suppress(Exception):
                    clip.close()
        return output_path
