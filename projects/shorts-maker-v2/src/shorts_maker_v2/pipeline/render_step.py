from __future__ import annotations

import contextlib
import logging
import random
import time
from pathlib import Path
from typing import Any

from moviepy import (
    CompositeAudioClip,
    CompositeVideoClip,
    ImageClip,
    concatenate_videoclips,
    vfx,
)

from shorts_maker_v2.config import AppConfig
from shorts_maker_v2.models import SceneAsset, ScenePlan
from shorts_maker_v2.pipeline.render_audio import RenderAudioMixin
from shorts_maker_v2.pipeline.render_captions import RenderCaptionsMixin
from shorts_maker_v2.pipeline.render_effects import RenderEffectsMixin
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
    register_custom_styles,
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


class RenderStep(RenderEffectsMixin, RenderAudioMixin, RenderCaptionsMixin):
    # YPP: 역할별 자막 프리셋 조합 로테이션 (반복적 콘텐츠 방지)
    _CAPTION_COMBOS: list[tuple[str, str, str, str]] = [
        # (hook_preset, body_preset, cta_preset, closing_preset)
        ("bold", "subtitle", "default", "closing"),  # 임팩트 → 영화적 → 깔끔 → 여운
        ("neon", "default", "subtitle", "closing"),  # 네온 → 깔끔 → 영화적 → 여운
        ("bold", "default", "neon", "closing"),  # 임팩트 → 깔끔 → 네온 → 여운
        ("neon", "subtitle", "bold", "closing"),  # 네온 → 영화적 → 임팩트 → 여운
        ("subtitle", "bold", "cta", "closing"),  # 영화적 → 임팩트 → CTA 특화 → 여운
        ("default", "neon", "bold", "closing"),  # 깔끔 → 네온 → 임팩트 → 여운
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
            "closing": ["drift", "ease_ken_burns"],
        },
        "psychology": {
            "hook": "ken_burns",
            "body": ["ken_burns", "zoom_out"],
            "cta": ["zoom_out"],
            "closing": ["drift", "zoom_out"],
        },
    }
    _CHANNEL_TRANSITIONS: dict[str, dict[tuple[str, str], list[str]]] = {
        "ai_tech": {
            ("hook", "body"): ["flash", "glitch", "zoom"],
            ("body", "body"): ["slide", "zoom", "crossfade"],
            ("body", "cta"): ["zoom", "crossfade"],
            ("hook", "cta"): ["flash", "zoom"],
            ("body", "closing"): ["crossfade"],
            ("cta", "closing"): ["crossfade"],
        },
        "psychology": {
            ("hook", "body"): ["crossfade", "slide"],
            ("body", "body"): ["crossfade", "slide"],
            ("body", "cta"): ["crossfade"],
            ("hook", "cta"): ["crossfade"],
            ("body", "closing"): ["crossfade"],
            ("cta", "closing"): ["crossfade"],
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
            combo = (forced_preset, forced_preset, forced_preset, forced_preset)
            logger.info(
                "[RenderStep] style_preset 강제 적용 — hook/body/cta/closing=%s (channel=%r)",
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
        closing_preset = resolve_channel_style(channel_key, "closing", channel_map) or (
            combo[3] if len(combo) > 3 else "closing"
        )

        self.hook_style = apply_preset(base_style, hook_preset)
        self.body_style = apply_preset(base_style, body_preset)
        self.cta_style = apply_preset(base_style, cta_preset)
        self.closing_style = apply_preset(base_style, closing_preset)

        # Silent-fail propagation 버퍼. 카라오케 fallback → static caption,
        # color grade 실패, audio postprocess 실패 같은 "rendered 됐지만 약속한
        # 품질이 안 나온" 케이스를 orchestrator 가 manifest.degraded_steps 로
        # 노출시킬 수 있게 모은다. run() 끝나면 orchestrator 가 drain.
        self._pending_render_warnings: list[dict[str, Any]] = []

        logger.info(
            "[RenderStep] 자막 combo — hook=%s, body=%s, cta=%s, closing=%s (channel=%r)",
            combo[0],
            combo[1],
            combo[2],
            combo[3] if len(combo) > 3 else "closing",
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
    def _resolve_caption_combo(cls, channel_key: str, job_index: int) -> tuple[str, str, str, str]:
        """채널 프로파일의 caption_combo를 우선 사용, 없으면 로테이션 폴백."""
        if channel_key:
            try:
                from shorts_maker_v2.utils.channel_router import ChannelRouter

                router = ChannelRouter()
                profile = router.get_profile(channel_key)
                combo_list = profile.get("caption_combo")
                if combo_list and len(combo_list) >= 3:
                    # Pad with "closing" if channel profile only has 3 elements
                    if len(combo_list) == 3:
                        combo_list = list(combo_list) + ["closing"]
                    logger.info(
                        "[RenderStep] 채널 '%s' 전용 caption_combo 적용: %s",
                        channel_key,
                        combo_list,
                    )
                    return tuple(combo_list[:4])  # type: ignore[return-value]
            except Exception as exc:
                logger.warning("[RenderStep] caption_combo 로드 실패: %s", exc)

        # 폴백: job_index 기반 로테이션
        combo = cls._CAPTION_COMBOS[job_index % len(cls._CAPTION_COMBOS)]
        logger.info("[RenderStep] 로테이션 combo 사용 (job_index=%d): %s", job_index, combo)
        return combo

    def _build_base_clip(self, asset: SceneAsset, duration_sec: float, target_width: int, target_height: int):
        if asset.visual_type == "video":
            base = self._load_video_clip(asset.visual_path, audio=False)
            if base.duration and base.duration < duration_sec:
                base = base.with_effects([vfx.Loop(duration=duration_sec)])
            elif base.duration and base.duration > duration_sec:
                base = base.subclipped(0, duration_sec)
        else:
            base = self._load_image_clip(asset.visual_path, duration=duration_sec)
        return self._fit_vertical(base, target_width, target_height)

    def _record_render_warning(
        self,
        *,
        step: str,
        exc: Exception,
        scene_id: int,
        error_type: str,
        is_retryable: bool = False,
    ) -> None:
        self._pending_render_warnings.append(
            {
                "step": step,
                "code": type(exc).__name__,
                "message": f"scene {scene_id}: {str(exc)[:140]}",
                "scene_id": scene_id,
                "error_type": error_type,
                "is_retryable": is_retryable,
            }
        )

    def _style_for_role(self, role: str):
        return {
            "hook": self.hook_style,
            "cta": self.cta_style,
            "closing": self.closing_style,
        }.get(role, self.body_style)

    def _apply_scene_color_grade(self, base, *, plan: ScenePlan, role: str):
        try:
            return color_grade_clip(base, self._channel_key, role)
        except Exception as cg_exc:
            logger.warning("[ColorGrade] failed, using ungraded clip: %s", cg_exc)
            self._record_render_warning(
                step="color_grade",
                exc=cg_exc,
                scene_id=plan.scene_id,
                error_type="ungraded_clip",
            )
            return base

    def _postprocess_scene_audio(self, *, asset: SceneAsset, plan: ScenePlan) -> None:
        try:
            postprocess_tts_audio(
                Path(asset.audio_path),
                voice_name=self.config.providers.tts_voice,
            )
        except Exception as pp_exc:
            logger.warning("[AudioPost] postprocess failed, using original audio: %s", pp_exc)
            self._record_render_warning(
                step="audio_postprocess",
                exc=pp_exc,
                scene_id=plan.scene_id,
                error_type="unprocessed_audio",
            )

    def _attach_scene_audio(
        self,
        base,
        *,
        asset: SceneAsset,
        duration_sec: float,
        audio_clips_to_close: list[Any] | None,
    ):
        audio = self._load_audio_clip(asset.audio_path)
        if audio_clips_to_close is not None:
            audio_clips_to_close.append(audio)
        if audio.duration and audio.duration > duration_sec:
            audio = audio.subclipped(0, duration_sec)
        return base.with_audio(audio)

    def _attach_audio(
        self,
        base,
        asset: SceneAsset,
        *,
        duration_sec: float,
        audio_clips_to_close: list[Any] | None,
    ):
        return self._attach_scene_audio(
            base,
            asset=asset,
            duration_sec=duration_sec,
            audio_clips_to_close=audio_clips_to_close,
        )

    def _compose_static_caption(
        self,
        base,
        *,
        plan: ScenePlan,
        run_dir: Path,
        target_width: int,
        target_height: int,
        duration_sec: float,
        style,
        role: str,
        caption_clips_to_close: list[Any] | None,
        filename_prefix: str = "caption_static",
    ):
        cap_out = run_dir / f"{filename_prefix}_{plan.scene_id:02d}.png"
        cap_img = self._render_static_caption(
            plan.narration_ko,
            target_width,
            style,
            cap_out,
            role,
        )
        cap_clip_img = ImageClip(str(cap_img), transparent=True)
        if caption_clips_to_close is not None:
            caption_clips_to_close.append(cap_clip_img)
        cap_clip = cap_clip_img.with_duration(duration_sec).with_position(
            ("center", self._caption_y(cap_clip_img, target_height, style, role))
        )
        return CompositeVideoClip([base, cap_clip], size=(target_width, target_height), use_bgclip=True)

    def _load_karaoke_chunk_groups(self, *, asset: SceneAsset, style) -> list:
        words_json_path = Path(asset.audio_path).parent / f"{Path(asset.audio_path).stem}_words.json"
        ssml_txt_path = words_json_path.parent / f"{words_json_path.stem}_ssml.txt"
        raw_words = load_words_json(words_json_path)
        if ssml_txt_path.exists():
            ssml_text = ssml_txt_path.read_text(encoding="utf-8")
            corrected_words = apply_ssml_break_correction(raw_words, ssml_text)
        else:
            corrected_words = raw_words
        return group_word_segments(corrected_words, style.words_per_chunk)

    def _build_word_highlight_caption_clips(
        self,
        *,
        plan: ScenePlan,
        run_dir: Path,
        target_width: int,
        target_height: int,
        style,
        role: str,
        chunk_groups: list,
        caption_clips_to_close: list[Any] | None,
    ) -> list:
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
                if caption_clips_to_close is not None:
                    caption_clips_to_close.append(highlight_clip)
                cap_clip = (
                    highlight_clip.with_duration(wd)
                    .with_start(ws)
                    .with_position(("center", self._caption_y(highlight_clip, target_height, style, role)))
                )
                caption_clips.append(cap_clip)
        return caption_clips

    def _build_karaoke_chunk_caption_clips(
        self,
        *,
        plan: ScenePlan,
        run_dir: Path,
        target_width: int,
        target_height: int,
        style,
        role: str,
        chunk_groups: list,
        caption_clips_to_close: list[Any] | None,
    ) -> list:
        caption_clips = []
        chunks = [(start, end, text) for start, end, text, _ in chunk_groups]
        for chunk_start, chunk_end, chunk_text in chunks:
            cd = max(0.1, chunk_end - chunk_start)
            cap_out = run_dir / f"kc_{plan.scene_id:02d}_{chunk_start:.2f}.png"
            render_karaoke_image(chunk_text, target_width, style, cap_out)
            caption_image = ImageClip(str(cap_out), transparent=True)
            if caption_clips_to_close is not None:
                caption_clips_to_close.append(caption_image)
            cap_clip = (
                caption_image.with_duration(cd)
                .with_start(chunk_start)
                .with_position(("center", self._caption_y(caption_image, target_height, style, role)))
            )
            caption_clips.append(cap_clip)
        return caption_clips

    def _compose_karaoke_caption(
        self,
        base,
        *,
        plan: ScenePlan,
        asset: SceneAsset,
        run_dir: Path,
        target_width: int,
        target_height: int,
        style,
        role: str,
        caption_clips_to_close: list[Any] | None,
    ):
        chunk_groups = self._load_karaoke_chunk_groups(asset=asset, style=style)
        if self.config.captions.highlight_mode == "word":
            caption_clips = self._build_word_highlight_caption_clips(
                plan=plan,
                run_dir=run_dir,
                target_width=target_width,
                target_height=target_height,
                style=style,
                role=role,
                chunk_groups=chunk_groups,
                caption_clips_to_close=caption_clips_to_close,
            )
        else:
            caption_clips = self._build_karaoke_chunk_caption_clips(
                plan=plan,
                run_dir=run_dir,
                target_width=target_width,
                target_height=target_height,
                style=style,
                role=role,
                chunk_groups=chunk_groups,
                caption_clips_to_close=caption_clips_to_close,
            )

        if not caption_clips:
            return base

        return CompositeVideoClip([base] + caption_clips, size=(target_width, target_height), use_bgclip=True)

    def _apply_hook_animation(self, base, *, role: str, duration_sec: float):
        if role != "hook":
            return base
        try:
            return apply_text_animation(
                base,
                animation_type=self.config.captions.hook_animation,
                duration=duration_sec,
            )
        except Exception as aex:
            logger.warning("[Animation] hook animation failed: %s", aex)
            return base

    def _apply_broll_pip(
        self,
        base,
        *,
        plan: ScenePlan,
        run_dir: Path,
        duration_sec: float,
        target_width: int,
        target_height: int,
    ):
        broll_path = run_dir / f"broll_{plan.scene_id:02d}.mp4"
        if not broll_path.exists():
            return base
        try:
            pip_clip = create_broll_pip(str(broll_path), duration_sec, target_width, target_height)
            if pip_clip is None:
                return base
            return CompositeVideoClip([base, pip_clip], size=(target_width, target_height), use_bgclip=True)
        except Exception as exc:
            logger.warning("[RenderStep] B-Roll PiP failed (scene %s, skipped): %s", plan.scene_id, exc)
            return base

    @staticmethod
    def _apply_closing_fade(base, *, role: str, duration_sec: float):
        if role != "closing":
            return base
        fade_dur = min(1.5, duration_sec * 0.4)
        return base.with_effects([vfx.FadeOut(fade_dur)])

    def _render_single_scene(
        self,
        *,
        plan: ScenePlan,
        asset: SceneAsset,
        run_dir: Path,
        target_width: int,
        target_height: int,
        previous_effect: str = "",
        audio_clips_to_close: list[Any] | None = None,
        caption_clips_to_close: list[Any] | None = None,
    ) -> tuple[Any, str]:
        duration_sec = asset.duration_sec
        role = plan.structure_role

        base = self._build_base_clip(asset, duration_sec, target_width, target_height)

        if asset.visual_type == "image":
            base, previous_effect = self._apply_channel_image_motion(
                base,
                role=role,
                target_width=target_width,
                target_height=target_height,
                exclude=previous_effect,
            )

        base = self._apply_scene_color_grade(base, plan=plan, role=role)
        self._postprocess_scene_audio(asset=asset, plan=plan)
        base = self._attach_scene_audio(
            base,
            asset=asset,
            duration_sec=duration_sec,
            audio_clips_to_close=audio_clips_to_close,
        )
        style = self._style_for_role(role)

        if style.mode == "karaoke":
            try:
                base = self._compose_karaoke_caption(
                    base,
                    plan=plan,
                    asset=asset,
                    run_dir=run_dir,
                    target_width=target_width,
                    target_height=target_height,
                    style=style,
                    role=role,
                    caption_clips_to_close=caption_clips_to_close,
                )

            except Exception as kex:
                logger.warning("[Karaoke] failed, falling back to static caption: %s", kex)
                # silent-fail 노출: orchestrator 가 degraded_steps 로 ship.
                self._record_render_warning(
                    step="karaoke_caption",
                    exc=kex,
                    scene_id=plan.scene_id,
                    error_type="caption_fallback",
                )
                base = self._compose_static_caption(
                    base,
                    plan=plan,
                    run_dir=run_dir,
                    target_width=target_width,
                    target_height=target_height,
                    duration_sec=duration_sec,
                    style=style,
                    role=role,
                    caption_clips_to_close=caption_clips_to_close,
                    filename_prefix="caption_fallback",
                )
        else:
            base = self._compose_static_caption(
                base,
                plan=plan,
                run_dir=run_dir,
                target_width=target_width,
                target_height=target_height,
                duration_sec=duration_sec,
                style=style,
                role=role,
                caption_clips_to_close=caption_clips_to_close,
            )

        base = self._apply_hook_animation(base, role=role, duration_sec=duration_sec)
        base = self._apply_broll_pip(
            base,
            plan=plan,
            run_dir=run_dir,
            duration_sec=duration_sec,
            target_width=target_width,
            target_height=target_height,
        )
        base = self._apply_closing_fade(base, role=role, duration_sec=duration_sec)

        return base, previous_effect

    def _concatenate_scene_clips(self, clips: list, *, fps: int):
        if self._renderer_backend != "ffmpeg" or not hasattr(self._output_renderer, "materialize_clip"):
            return concatenate_videoclips(clips, method="compose")

        try:
            segment_handles = [
                self._output_renderer.materialize_clip(
                    ClipHandle(
                        backend="moviepy",
                        native=clip,
                        duration=getattr(clip, "duration", 0.0) or 0.0,
                        width=getattr(clip, "w", 0) or 0,
                        height=getattr(clip, "h", 0) or 0,
                        has_audio=getattr(clip, "audio", None) is not None,
                    ),
                    fps=fps,
                    audio_codec="aac",
                )
                for clip in clips
            ]
            joined = self._output_renderer.concatenate(segment_handles)
            logger.info("[RenderStep] FFmpeg scene concat used (%d segments)", len(segment_handles))
            return self._load_video_clip(joined.native)
        except Exception as exc:
            logger.warning("[RenderStep] FFmpeg scene concat failed; falling back to MoviePy concat: %s", exc)
            return concatenate_videoclips(clips, method="compose")

    # ── 메인 렌더링 ──────────────────────────────────────────────────────────

    def _append_bookend_clip(
        self,
        *,
        path: str | None,
        duration: float,
        target_width: int,
        target_height: int,
        all_clips: list,
        scene_roles: list[str] | None,
        role: str | None,
        fade_in: float,
        label: str,
    ) -> None:
        if not path:
            return

        clip = self._build_bookend_clip(path, duration, target_width, target_height)
        if clip is None:
            return

        clip = clip.with_effects([vfx.FadeIn(fade_in)])
        all_clips.append(clip)
        if scene_roles is not None and role is not None:
            scene_roles.append(role)
        logger.info("[%s] bookend inserted (%.1fs): %s", label, duration, path)

    def _render_scene_sequence(
        self,
        *,
        scene_plans: list[ScenePlan],
        scene_assets: list[SceneAsset],
        run_dir: Path,
        target_width: int,
        target_height: int,
        all_clips: list,
        scene_roles: list[str],
        audio_clips_to_close: list[Any],
        caption_clips_to_close: list[Any],
    ) -> None:
        last_effect = ""
        for plan, asset in zip(scene_plans, scene_assets, strict=False):
            role = plan.structure_role
            scene_roles.append(role)
            base, last_effect = self._render_single_scene(
                plan=plan,
                asset=asset,
                run_dir=run_dir,
                target_width=target_width,
                target_height=target_height,
                previous_effect=last_effect,
                audio_clips_to_close=audio_clips_to_close,
                caption_clips_to_close=caption_clips_to_close,
            )
            all_clips.append(base)

    @staticmethod
    def _trim_to_shorts_limit(final_video, *, max_duration: float = 59.0):
        if final_video.duration and final_video.duration > max_duration:
            logger.warning(
                "[DURATION] video %.1fs > %.1fs, trimming for Shorts",
                final_video.duration,
                max_duration,
            )
            return final_video.subclipped(0, max_duration)
        return final_video

    def _generate_bgm_clip(self, *, final_video, run_dir: Path, title: str, topic: str):
        target_dur = final_video.duration
        if not target_dur:
            return None, None
        bgm_clip = None
        original_bgm_clip = None

        if self.config.audio.bgm_provider == "lyria" and final_video.audio is not None:
            lyria_bgm = self._generate_lyria_bgm(
                run_dir=run_dir,
                duration_sec=target_dur,
                channel=getattr(self, "_channel_key", ""),
                topic=topic or title,
            )
            if lyria_bgm:
                try:
                    bgm_clip = self._load_audio_clip(lyria_bgm)
                    original_bgm_clip = bgm_clip
                    if bgm_clip.duration and bgm_clip.duration > target_dur:
                        bgm_clip = bgm_clip.subclipped(0, target_dur)
                    logger.info("[BGM] Lyria AI BGM used: %s", lyria_bgm.name)
                except Exception as exc:
                    logger.warning("[BGM] Lyria BGM 로드 실패, 건너뜀: %s", exc)
                    bgm_clip = None

        if bgm_clip is None and final_video.audio is not None:
            bgm_dir = (run_dir.parent.parent / self.config.audio.bgm_dir).resolve()
            if bgm_dir.exists():
                bgm_files = self._collect_bgm_files(bgm_dir)
                if bgm_files:
                    bgm_path = self._pick_bgm_by_mood(bgm_files, topic or title)
                    try:
                        bgm_clip = self._load_audio_clip(bgm_path)
                        original_bgm_clip = bgm_clip
                        if bgm_clip.duration and bgm_clip.duration < target_dur:
                            repeats = int(target_dur / bgm_clip.duration) + 1
                            from moviepy import concatenate_audioclips

                            bgm_clip = concatenate_audioclips([bgm_clip] * repeats)
                        bgm_clip = bgm_clip.subclipped(0, target_dur)
                        logger.info("[BGM] local file used: %s", bgm_path.name)
                    except Exception as exc:
                        logger.warning("[BGM] 로컬 BGM 로드 실패 (%s), 건너뜀: %s", bgm_path.name, exc)
                        bgm_clip = None

        return bgm_clip, original_bgm_clip

    def _mix_bgm_audio(self, final_video, bgm_clip):
        if bgm_clip is None or final_video.audio is None:
            return final_video

        bgm_clip = self._apply_rms_ducking(
            final_video.audio,
            bgm_clip,
            base_vol=self.config.audio.bgm_volume,
            duck_factor=self.config.audio.ducking_factor,
        )
        mixed_audio = CompositeAudioClip([final_video.audio, bgm_clip])
        return final_video.with_audio(mixed_audio)

    def _apply_sfx_layer(
        self,
        final_video,
        *,
        scene_assets: list[SceneAsset],
        scene_roles: list[str],
        run_dir: Path,
        audio_clips_to_close: list[Any],
    ):
        if not self.config.audio.sfx_enabled:
            return final_video

        sfx_files = self._load_sfx_files(run_dir)
        if not sfx_files:
            return final_video

        scene_durations = [asset.duration_sec for asset in scene_assets]
        sfx_clips = self._build_sfx_clips(scene_roles, scene_durations, sfx_files)
        if not sfx_clips or final_video.audio is None:
            return final_video

        audio_clips_to_close.extend(sfx_clips)
        final_video = final_video.with_audio(CompositeAudioClip([final_video.audio] + sfx_clips))
        logger.info("[SFX] %d effects applied", len(sfx_clips))
        return final_video

    def _build_video_write_kwargs(self, *, target_width: int, target_height: int):
        from shorts_maker_v2.utils.hwaccel import detect_gpu_info, detect_hw_encoder

        hw_codec, hw_params = detect_hw_encoder(self.config.video.hw_accel)

        try:
            gpu_info = detect_gpu_info()
            logger.info(
                "[RENDER] GPU: %s | Encoder: %s | HW Decode: %s",
                gpu_info["gpu_name"],
                gpu_info["encoder"],
                gpu_info["decoder_support"],
            )
        except Exception as gpu_exc:
            logger.debug("[RENDER] GPU info lookup failed: %s", gpu_exc)

        qp = _QUALITY_PROFILES.get(self.config.video.quality_profile, _QUALITY_PROFILES["standard"])
        if hw_codec == "libx264":
            ffmpeg_extra = [
                "-crf",
                str(qp["crf"]),
                "-pix_fmt",
                "yuv420p",
            ]
            if qp["maxrate"]:
                ffmpeg_extra.extend(["-maxrate", qp["maxrate"], "-bufsize", qp["maxrate"]])
            preset = qp["preset"]
        else:
            ffmpeg_extra = list(hw_params)
            preset = None

        ffmpeg_extra.extend(["-s", f"{target_width}x{target_height}"])
        write_kwargs: dict = {
            "fps": self.config.video.fps,
            "codec": hw_codec,
            "audio_codec": "aac",
            "ffmpeg_params": ffmpeg_extra,
        }
        if preset:
            write_kwargs["preset"] = preset
        return hw_codec, write_kwargs

    def _write_output_video(self, final_video, *, output_path: Path, write_kwargs: dict) -> None:
        handle = ClipHandle(
            backend=self._renderer_backend,
            native=final_video,
            duration=final_video.duration,
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

    @staticmethod
    def _log_render_benchmark(*, hw_codec: str, video_duration: float, render_elapsed: float) -> None:
        speed_ratio = video_duration / max(render_elapsed, 0.001)
        logger.info(
            "[BENCHMARK] render complete | codec=%s | video=%.1fs | render=%.1fs | speed=%.2fx (%s)",
            hw_codec,
            video_duration,
            render_elapsed,
            speed_ratio,
            "faster than realtime" if speed_ratio > 1.0 else "slower than realtime",
        )

    @staticmethod
    def _close_render_resources(
        *,
        final_video,
        all_clips: list,
        audio_clips_to_close: list[Any],
        bgm_clip,
        caption_clips_to_close: list[Any],
    ) -> None:
        final_video.close()
        for clip in all_clips:
            with contextlib.suppress(Exception):
                clip.close()
        for clip in audio_clips_to_close:
            with contextlib.suppress(Exception):
                clip.close()
        if bgm_clip is not None:
            with contextlib.suppress(Exception):
                bgm_clip.close()
        for clip in caption_clips_to_close:
            with contextlib.suppress(Exception):
                clip.close()

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

        self._append_bookend_clip(
            path=io_cfg.intro_path,
            duration=io_cfg.intro_duration,
            target_width=target_width,
            target_height=target_height,
            all_clips=all_clips,
            scene_roles=scene_roles,
            role="intro",
            fade_in=0.3,
            label="Intro",
        )
        self._render_scene_sequence(
            scene_plans=scene_plans,
            scene_assets=scene_assets,
            run_dir=run_dir,
            target_width=target_width,
            target_height=target_height,
            all_clips=all_clips,
            scene_roles=scene_roles,
            audio_clips_to_close=_audio_clips_to_close,
            caption_clips_to_close=_caption_clips_to_close,
        )
        all_clips = self._apply_transitions(all_clips, target_width, target_height, roles=scene_roles)

        self._append_bookend_clip(
            path=io_cfg.outro_path,
            duration=io_cfg.outro_duration,
            target_width=target_width,
            target_height=target_height,
            all_clips=all_clips,
            scene_roles=None,
            role=None,
            fade_in=0.4,
            label="Outro",
        )

        output_path = output_dir / output_filename
        final_video = self._concatenate_scene_clips(all_clips, fps=self.config.video.fps)

        # ── YouTube Shorts 하드 리밋 (59초) ──
        MAX_SHORTS_DURATION = 59.0  # noqa: N806  # YouTube Shorts 최대 60초, 1초 마진
        final_video = self._trim_to_shorts_limit(final_video, max_duration=MAX_SHORTS_DURATION)

        # BGM: Lyria AI 생성 (1순위) → local assets 폴백
        bgm_clip, _bgm_clip = self._generate_bgm_clip(
            final_video=final_video,
            run_dir=run_dir,
            title=title,
            topic=topic,
        )

        # RMS 기반 Ducking 적용
        final_video = self._mix_bgm_audio(final_video, bgm_clip)

        # SFX 효과음 레이어
        final_video = self._apply_sfx_layer(
            final_video,
            scene_assets=scene_assets,
            scene_roles=scene_roles,
            run_dir=run_dir,
            audio_clips_to_close=_audio_clips_to_close,
        )

        hw_codec, write_kwargs = self._build_video_write_kwargs(
            target_width=target_width,
            target_height=target_height,
        )

        # Sprint 3: 렌더링 벤치마크
        video_duration = final_video.duration
        render_start_time = time.perf_counter()

        try:
            self._write_output_video(
                final_video,
                output_path=output_path,
                write_kwargs=write_kwargs,
            )
        finally:
            render_elapsed = time.perf_counter() - render_start_time
            self._log_render_benchmark(
                hw_codec=hw_codec,
                video_duration=video_duration,
                render_elapsed=render_elapsed,
            )
            self._close_render_resources(
                final_video=final_video,
                all_clips=all_clips,
                audio_clips_to_close=_audio_clips_to_close,
                bgm_clip=_bgm_clip,
                caption_clips_to_close=_caption_clips_to_close,
            )
        return output_path
