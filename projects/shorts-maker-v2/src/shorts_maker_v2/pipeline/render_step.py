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
            if base.duration < duration_sec:
                base = base.with_effects([vfx.Loop(duration=duration_sec)])
            elif base.duration > duration_sec:
                base = base.subclipped(0, duration_sec)
        else:
            base = self._load_image_clip(asset.visual_path, duration=duration_sec)
        return self._fit_vertical(base, target_width, target_height)

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
            if role == "hook":
                style = self.hook_style
            elif role == "cta":
                style = self.cta_style
            elif role == "closing":
                style = self.closing_style
            else:
                style = self.body_style

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
                except Exception as exc:
                    logger.warning("[RenderStep] B-Roll PiP 생성 실패 (씬 %s, 스킵): %s", plan.scene_id, exc)

            # 7) HUD 오버레이 — 비활성화 (깔끔한 화면 유지)
            # 8) 제목 오버레이 — 비활성화

            # 9) Closing 씬: 부드러운 페이드아웃 (여운 연출)
            if role == "closing":
                fade_dur = min(1.5, duration_sec * 0.4)
                base = base.with_effects([vfx.FadeOut(fade_dur)])

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
                f"({speed_ratio:.2f}x {'fast' if speed_ratio > 1.0 else 'slow'})\n"
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
