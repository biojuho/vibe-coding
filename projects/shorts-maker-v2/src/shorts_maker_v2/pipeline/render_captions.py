from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from moviepy import VideoFileClip

from shorts_maker_v2.render.caption_pillow import (
    CaptionStyle,
    calculate_safe_position,
    render_caption_image,
)

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class RenderCaptionsMixin:
    """Static captions, bookend clips (intro/outro), title overlays, and thumbnails.

    Mixed into ``RenderStep`` -- all ``self.*`` access refers to RenderStep
    attributes (``config``, ``_channel_key``, ``_channel_profile``, etc.).
    """

    # ── Caption Y position ────────────────────────────────────────────────────

    @staticmethod
    def _caption_y(clip: Any, target_height: int, style: CaptionStyle, role: str = "body") -> int:
        """Calculate caption Y position with safe zone awareness."""
        if style.safe_zone_enabled:
            return calculate_safe_position(target_height, clip.h, style, role)
        return max(80, int(target_height - clip.h - style.bottom_offset))

    # ── Static caption rendering ──────────────────────────────────────────────

    def _render_static_caption(
        self,
        text: str,
        target_width: int,
        style: CaptionStyle,
        output_path: Path,
        role: str,
    ) -> Path:
        """정적 자막 렌더링. hook 씬에서 그라디언트+글로우를 시도합니다."""
        channel_key: str = self._channel_key  # type: ignore[attr-defined]
        channel_profile: dict = self._channel_profile  # type: ignore[attr-defined]

        if role == "hook" and channel_key:
            try:
                from ShortsFactory.engines.text_engine import TextEngine

                channel_cfg = channel_profile or {}
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

    # ── Bookend clips (intro / outro) ─────────────────────────────────────────

    def _build_bookend_clip(self, path_str: str, duration: float, target_width: int, target_height: int) -> Any | None:
        """인트로/아웃트로 클립 빌드 (이미지 또는 비디오)."""
        path = Path(path_str)
        if not path.exists():
            return None
        ext = path.suffix.lower()
        if ext in (".mp4", ".mov", ".avi", ".webm"):
            clip = self._load_video_clip(path, audio=False)  # type: ignore[attr-defined]
            clip = clip.subclipped(0, min(clip.duration, duration))
        elif ext in (".png", ".jpg", ".jpeg", ".webp"):
            clip = self._load_image_clip(path, duration=duration)  # type: ignore[attr-defined]
        else:
            return None
        return self._fit_vertical(clip, target_width, target_height)  # type: ignore[attr-defined]

    # ── Title overlay ─────────────────────────────────────────────────────────

    def _render_title_image(self, title: str, canvas_width: int, output_path: Path) -> Path:
        """영상 상단에 표시할 제목 오버레이 이미지 렌더링."""
        import PIL.Image as _Image
        import PIL.ImageDraw as _ImageDraw
        import PIL.ImageFont as _ImageFont

        config = self.config  # type: ignore[attr-defined]

        font_size = 38
        font = None
        for fp in config.captions.font_candidates:
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

    # ── Thumbnail extraction ──────────────────────────────────────────────────

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
