"""ShortsFactory Render — 씬 리스트를 최종 MP4로 합성하는 렌더 엔진.

Main Pipeline의 render_from_plan()이 Scene 리스트를 전달하면
이 모듈이 MoviePy를 사용하여 최종 영상을 합성합니다.

아키텍처:
    ShortsFactory.pipeline.render_from_plan()
        → ShortsFactory.render.SFRenderStep.render_scenes()
            → 6대 엔진 (Text/Color/Background/Layout/Hook/Transition)

사용법:
    from ShortsFactory.render import SFRenderStep
    renderer = SFRenderStep(channel_config)
    output = renderer.render_scenes(scenes, "output.mp4")
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger("ShortsFactory.render")


def _lazy_moviepy():
    """moviepy lazy import (ffmpeg 미설치 환경 대응)."""
    from moviepy import (
        AudioFileClip,
        CompositeVideoClip,
        ImageClip,
        VideoFileClip,
        concatenate_videoclips,
        vfx,
    )
    return {
        "AudioFileClip": AudioFileClip,
        "CompositeVideoClip": CompositeVideoClip,
        "ImageClip": ImageClip,
        "VideoFileClip": VideoFileClip,
        "concatenate_videoclips": concatenate_videoclips,
        "vfx": vfx,
    }


class SFRenderStep:
    """ShortsFactory 전용 렌더 스텝.

    6대 엔진을 활용하여 채널별 스타일이 적용된 최종 영상을 합성합니다.

    Args:
        channel_config: ChannelConfig 또는 채널 설정 dict
    """

    # 세로 9:16 (YouTube Shorts 기본)
    TARGET_WIDTH = 1080
    TARGET_HEIGHT = 1920
    FPS = 30
    _CHANNEL_SUBTITLE_OFFSETS = {
        "ai_tech": {"hook": 280, "body": 300, "cta": 320},
        "psychology": {"hook": 300, "body": 330, "cta": 340},
    }

    def __init__(self, channel_config: Any) -> None:
        # ChannelConfig 객체 또는 dict 모두 지원
        if hasattr(channel_config, "_raw"):
            self._channel_dict = {
                "id": channel_config.id,
                "palette": channel_config.palette,
                "font": channel_config.font,
                "color_preset": channel_config.color_preset,
                "caption_combo": channel_config.caption_combo,
                "hook_style": channel_config.hook_style,
                "transition": channel_config.transition,
                "disclaimer": channel_config.disclaimer,
                "highlight_color": getattr(channel_config, "highlight_color", "#FFFFFF"),
                "keyword_highlights": getattr(channel_config, "keyword_highlights", {}),
            }
            self._color_preset = channel_config.color_preset
        else:
            self._channel_dict = dict(channel_config) if channel_config else {}
            self._color_preset = self._channel_dict.get("color_preset", "")

    def render_scenes(
        self,
        scenes: list,
        output: str,
        *,
        bgm_path: str | None = None,
        bgm_volume: float = 0.12,
    ) -> str:
        """Scene 리스트를 최종 영상으로 합성합니다.

        Args:
            scenes: ShortsFactory Scene 객체 리스트
            output: 최종 출력 MP4 경로
            bgm_path: BGM 오디오 파일 경로 (선택)
            bgm_volume: BGM 음량 (0.0-1.0)

        Returns:
            렌더링된 MP4 파일 경로
        """
        mp = _lazy_moviepy()
        ImageClip = mp["ImageClip"]
        VideoFileClip = mp["VideoFileClip"]
        CompositeVideoClip = mp["CompositeVideoClip"]
        concatenate_videoclips = mp["concatenate_videoclips"]
        vfx = mp["vfx"]
        AudioFileClip = mp["AudioFileClip"]

        w, h = self.TARGET_WIDTH, self.TARGET_HEIGHT
        scene_clips: list = []
        roles: list[str] = []

        for i, scene in enumerate(scenes):
            duration = getattr(scene, "duration", 5.0)
            role = getattr(scene, "role", "body")
            image_path = getattr(scene, "image_path", None)
            audio_path = getattr(scene, "extra", {}).get("audio_path")
            roles.append(role)

            # 1) 베이스 비주얼 클립
            base = self._build_visual_clip(
                image_path, duration, w, h, mp
            )

            # 2) 자막/텍스트 오버레이 (image_path가 Scene에 의해 렌더링된 텍스트 이미지)
            text_overlay = self._build_text_overlay(scene, duration, w, h, mp)
            if text_overlay is not None:
                base = CompositeVideoClip([base, text_overlay])

            # 3) 오디오 합성
            if audio_path and Path(audio_path).exists():
                try:
                    audio = AudioFileClip(str(audio_path))
                    if audio.duration > duration:
                        audio = audio.subclipped(0, duration)
                    base = base.with_audio(audio)
                except Exception as exc:
                    logger.warning("[SFRender] 오디오 로드 실패 (scene %d): %s", i, exc)

            # 4) 역할별 컬러 그레이딩
            base = self._apply_color_grading(base, role)

            # 5) Hook 효과
            if role == "hook":
                base = self._apply_hook_effect(base, w, h)

            scene_clips.append(base)

        if not scene_clips:
            raise RuntimeError("[SFRender] 렌더링할 씬이 없습니다.")

        # 6) 전환 효과 적용
        scene_clips = self._apply_transitions(scene_clips, roles)

        # 7) 최종 합성
        final = concatenate_videoclips(scene_clips, method="compose")

        # 8) BGM 믹싱
        if bgm_path and Path(bgm_path).exists():
            final = self._mix_bgm(final, bgm_path, bgm_volume, mp)

        # 출력
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(
            "[SFRender] writing MP4: %s (%.1fs, %d scenes)",
            output, final.duration, len(scenes),
        )
        try:
            final.write_videofile(
                str(output_path),
                fps=self.FPS,
                codec="libx264",
                audio_codec="aac",
                preset="medium",
                logger=None,
            )
        finally:
            # [QA 수정] MoviePy 클립 리소스 해제 (메모리 누수 방지)
            try:
                final.close()
            except Exception:
                pass
            for clip in scene_clips:
                try:
                    clip.close()
                except Exception:
                    pass

        return str(output_path)

    # ── 내부 메서드 ────────────────────────────────────────────────────

    def _build_visual_clip(
        self,
        image_path: Path | str | None,
        duration: float,
        w: int,
        h: int,
        mp: dict,
    ):
        """이미지/비디오 → 9:16 맞춤 클립 생성."""
        ImageClip = mp["ImageClip"]
        VideoFileClip = mp["VideoFileClip"]
        vfx = mp["vfx"]

        if image_path is None or not Path(image_path).exists():
            # 소재 없으면 그라데이션 배경 생성
            bg = self._create_gradient_bg(w, h)
            return ImageClip(bg).with_duration(duration)

        path = Path(image_path)
        ext = path.suffix.lower()

        if ext in (".mp4", ".mov", ".avi", ".webm"):
            clip = VideoFileClip(str(path)).without_audio()
            if clip.duration < duration:
                clip = clip.with_effects([vfx.Loop(duration=duration)])
            elif clip.duration > duration:
                clip = clip.subclipped(0, duration)
        elif ext in (".png", ".jpg", ".jpeg", ".webp"):
            clip = ImageClip(str(path)).with_duration(duration)
        else:
            bg = self._create_gradient_bg(w, h)
            return ImageClip(bg).with_duration(duration)

        return self._fit_vertical(clip, w, h, mp)

    @staticmethod
    def _fit_vertical(clip, w: int, h: int, mp: dict):
        """클립을 9:16 세로에 맞춤 (crop+resize)."""
        scale = max(w / clip.w, h / clip.h)
        resized = clip.resized(scale)
        x1 = max(0, (resized.w - w) / 2)
        y1 = max(0, (resized.h - h) / 2)
        return resized.cropped(x1=x1, y1=y1, x2=x1 + w, y2=y1 + h)

    def _create_gradient_bg(self, w: int, h: int) -> np.ndarray:
        """채널 팔레트 기반 그라데이션 배경 생성."""
        palette = self._channel_dict.get("palette", {})
        primary = palette.get("primary", "#1a1a2e")
        secondary = palette.get("secondary", "#16213e")

        c1 = self._hex_to_rgb(primary)
        c2 = self._hex_to_rgb(secondary)

        # 세로 그라데이션
        gradient = np.zeros((h, w, 3), dtype=np.uint8)
        for y in range(h):
            ratio = y / max(h - 1, 1)
            for c in range(3):
                gradient[y, :, c] = int(c1[c] * (1 - ratio) + c2[c] * ratio)

        return gradient

    def _build_text_overlay(self, scene, duration: float, w: int, h: int, mp: dict):
        """Scene의 텍스트를 오버레이 이미지로 변환."""
        # [QA 수정] image_path는 베이스 비주얼로 이미 사용되므로
        # 별도의 텍스트 렌더링 이미지(text_image_path)만 오버레이
        text = getattr(scene, "text", "")
        if not text:
            return None

        text_img_path = getattr(scene, "text_image_path", None)
        if text_img_path and Path(text_img_path).exists():
            ImageClip = mp["ImageClip"]
            try:
                clip = ImageClip(str(text_img_path), transparent=True)
                role = getattr(scene, "role", "body")
                offset = self._CHANNEL_SUBTITLE_OFFSETS.get(
                    self._channel_dict.get("id", ""),
                    {},
                ).get(role, 300)
                y = max(80, int(h - clip.h - offset))
                return clip.with_duration(duration).with_position(("center", y))
            except Exception:
                pass

        return None

    def _apply_color_grading(self, clip, role: str):
        """역할별 컬러 그레이딩 적용."""
        if not self._color_preset:
            return clip

        try:
            from ShortsFactory.engines.color_engine import ColorEngine
            engine = ColorEngine(self._color_preset)
            return engine.apply_role_grading(clip, role=role)
        except Exception as exc:
            logger.debug("[SFRender] 컬러 그레이딩 실패: %s", exc)
            return clip

    def _apply_hook_effect(self, clip, w: int, h: int):
        """Hook 씬에 시선 집중 효과 적용."""
        try:
            from ShortsFactory.engines.hook_engine import HookEngine
            engine = HookEngine(self._channel_dict)
            return engine.create_hook(clip)
        except Exception as exc:
            logger.debug("[SFRender] Hook 효과 실패: %s", exc)
            return clip

    def _apply_transitions(self, clips: list, roles: list[str]) -> list:
        """전환 효과 적용."""
        if len(clips) <= 1:
            return clips

        try:
            from ShortsFactory.engines.transition_engine import TransitionEngine
            engine = TransitionEngine(self._channel_dict)
            return engine.apply(clips, roles=roles)
        except Exception as exc:
            logger.debug("[SFRender] 전환 효과 실패: %s", exc)
            return clips

    def _mix_bgm(self, video_clip, bgm_path: str, volume: float, mp: dict):
        """BGM 오디오 믹싱."""
        AudioFileClip = mp["AudioFileClip"]

        try:
            from moviepy import CompositeAudioClip
            from moviepy.audio.fx import AudioLoop, MultiplyVolume

            bgm = AudioFileClip(str(bgm_path))
            bgm = bgm.with_effects([AudioLoop(duration=video_clip.duration)])
            bgm = bgm.with_effects([MultiplyVolume(volume)])

            if video_clip.audio is not None:
                mixed = CompositeAudioClip([video_clip.audio, bgm])
                return video_clip.with_audio(mixed)
            else:
                return video_clip.with_audio(bgm)
        except Exception as exc:
            logger.warning("[SFRender] BGM 믹싱 실패: %s", exc)
            return video_clip

    @staticmethod
    def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
        h = hex_color.lstrip("#")
        if len(h) != 6:
            return (30, 30, 60)
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


# pipeline.py 호환 alias: `from ShortsFactory.render import RenderStep`
RenderStep = SFRenderStep
