"""Video renderer abstraction layer.

Provides a backend-agnostic interface for video composition and encoding.
Current backends:
  - MoviePyRenderer (default, current production)
  - FFmpegRenderer (subprocess-based alternative, no MoviePy dependency)

Usage:
    renderer = create_renderer("moviepy")  # or "ffmpeg"
    clip = renderer.load_image("bg.png", duration=5.0)
    renderer.write(clip, "output.mp4", fps=30, codec="libx264")
    renderer.close(clip)
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ClipHandle:
    """Backend-agnostic reference to a video/audio/image clip."""

    backend: str
    native: Any  # underlying object (MoviePy clip or FFmpeg file path)
    duration: float = 0.0
    width: int = 0
    height: int = 0
    has_audio: bool = False
    metadata: dict = field(default_factory=dict)


class VideoRendererBackend(ABC):
    """Abstract interface for video rendering backends."""

    # ── Loading ──

    @abstractmethod
    def load_video(self, path: str | Path, audio: bool = True) -> ClipHandle:
        """Load a video file."""

    @abstractmethod
    def load_image(self, path: str | Path, duration: float = 5.0) -> ClipHandle:
        """Load an image as a static video clip."""

    @abstractmethod
    def load_audio(self, path: str | Path) -> ClipHandle:
        """Load an audio file."""

    # ── Composition ──

    @abstractmethod
    def composite(
        self,
        clips: list[ClipHandle],
        size: tuple[int, int] | None = None,
    ) -> ClipHandle:
        """Layer clips on top of each other (z-order = list order)."""

    @abstractmethod
    def concatenate(
        self,
        clips: list[ClipHandle],
        method: str = "compose",
    ) -> ClipHandle:
        """Join clips sequentially."""

    @abstractmethod
    def set_audio(self, video: ClipHandle, audio: ClipHandle) -> ClipHandle:
        """Replace/set audio on a video clip."""

    @abstractmethod
    def mix_audio(self, clips: list[ClipHandle]) -> ClipHandle:
        """Mix multiple audio clips together."""

    # ── Transforms ──

    @abstractmethod
    def resize(self, clip: ClipHandle, width: int, height: int) -> ClipHandle:
        """Resize clip to target dimensions."""

    @abstractmethod
    def subclip(self, clip: ClipHandle, start: float, end: float) -> ClipHandle:
        """Extract a time range from a clip."""

    @abstractmethod
    def set_position(self, clip: ClipHandle, pos: tuple) -> ClipHandle:
        """Set position of a clip within a composite."""

    @abstractmethod
    def set_duration(self, clip: ClipHandle, duration: float) -> ClipHandle:
        """Set/override clip duration."""

    @abstractmethod
    def fade_in(self, clip: ClipHandle, duration: float) -> ClipHandle:
        """Apply fade-in effect."""

    @abstractmethod
    def fade_out(self, clip: ClipHandle, duration: float) -> ClipHandle:
        """Apply fade-out effect."""

    @abstractmethod
    def set_opacity(self, clip: ClipHandle, opacity: float) -> ClipHandle:
        """Set clip opacity (0.0 - 1.0)."""

    # ── Output ──

    @abstractmethod
    def write(
        self,
        clip: ClipHandle,
        output_path: str | Path,
        fps: int = 30,
        codec: str = "libx264",
        audio_codec: str = "aac",
        preset: str | None = "medium",
        ffmpeg_params: list[str] | None = None,
    ) -> Path:
        """Encode and write the final video file."""

    # ── Cleanup ──

    @abstractmethod
    def close(self, clip: ClipHandle) -> None:
        """Release resources held by a clip."""

    def close_all(self, clips: list[ClipHandle]) -> None:
        """Release resources for multiple clips."""
        for c in clips:
            try:
                self.close(c)
            except Exception:
                pass


class MoviePyRenderer(VideoRendererBackend):
    """MoviePy 2.x backend (current production renderer)."""

    def __init__(self) -> None:
        from moviepy import (
            AudioFileClip,
            CompositeAudioClip,
            CompositeVideoClip,
            ImageClip,
            VideoFileClip,
            concatenate_videoclips,
            vfx,
        )

        self._VideoFileClip = VideoFileClip
        self._ImageClip = ImageClip
        self._AudioFileClip = AudioFileClip
        self._CompositeVideoClip = CompositeVideoClip
        self._CompositeAudioClip = CompositeAudioClip
        self._concatenate = concatenate_videoclips
        self._vfx = vfx

    def _wrap(self, native: Any, backend: str = "moviepy") -> ClipHandle:
        dur = getattr(native, "duration", 0.0) or 0.0
        w = getattr(native, "w", 0) or 0
        h = getattr(native, "h", 0) or 0
        has_audio = getattr(native, "audio", None) is not None
        return ClipHandle(
            backend=backend, native=native, duration=dur,
            width=w, height=h, has_audio=has_audio,
        )

    def load_video(self, path: str | Path, audio: bool = True) -> ClipHandle:
        clip = self._VideoFileClip(str(path), audio=audio)
        return self._wrap(clip)

    def load_image(self, path: str | Path, duration: float = 5.0) -> ClipHandle:
        clip = self._ImageClip(str(path)).with_duration(duration)
        return self._wrap(clip)

    def load_audio(self, path: str | Path) -> ClipHandle:
        clip = self._AudioFileClip(str(path))
        return self._wrap(clip)

    def composite(self, clips: list[ClipHandle], size: tuple[int, int] | None = None) -> ClipHandle:
        natives = [c.native for c in clips]
        result = self._CompositeVideoClip(natives, size=size)
        return self._wrap(result)

    def concatenate(self, clips: list[ClipHandle], method: str = "compose") -> ClipHandle:
        natives = [c.native for c in clips]
        result = self._concatenate(natives, method=method)
        return self._wrap(result)

    def set_audio(self, video: ClipHandle, audio: ClipHandle) -> ClipHandle:
        result = video.native.with_audio(audio.native)
        return self._wrap(result)

    def mix_audio(self, clips: list[ClipHandle]) -> ClipHandle:
        natives = [c.native for c in clips]
        result = self._CompositeAudioClip(natives)
        return self._wrap(result)

    def resize(self, clip: ClipHandle, width: int, height: int) -> ClipHandle:
        result = clip.native.resized((width, height))
        return self._wrap(result)

    def subclip(self, clip: ClipHandle, start: float, end: float) -> ClipHandle:
        result = clip.native.subclipped(start, end)
        return self._wrap(result)

    def set_position(self, clip: ClipHandle, pos: tuple) -> ClipHandle:
        result = clip.native.with_position(pos)
        return self._wrap(result)

    def set_duration(self, clip: ClipHandle, duration: float) -> ClipHandle:
        result = clip.native.with_duration(duration)
        return self._wrap(result)

    def fade_in(self, clip: ClipHandle, duration: float) -> ClipHandle:
        result = clip.native.with_effects([self._vfx.FadeIn(duration)])
        return self._wrap(result)

    def fade_out(self, clip: ClipHandle, duration: float) -> ClipHandle:
        result = clip.native.with_effects([self._vfx.FadeOut(duration)])
        return self._wrap(result)

    def set_opacity(self, clip: ClipHandle, opacity: float) -> ClipHandle:
        result = clip.native.with_opacity(opacity)
        return self._wrap(result)

    def write(
        self, clip: ClipHandle, output_path: str | Path,
        fps: int = 30, codec: str = "libx264", audio_codec: str = "aac",
        preset: str | None = "medium", ffmpeg_params: list[str] | None = None,
    ) -> Path:
        kwargs: dict[str, Any] = {
            "fps": fps, "codec": codec, "audio_codec": audio_codec,
            "ffmpeg_params": ffmpeg_params or [],
        }
        if preset:
            kwargs["preset"] = preset
        clip.native.write_videofile(str(output_path), **kwargs)
        return Path(output_path)

    def close(self, clip: ClipHandle) -> None:
        if clip.native is not None:
            try:
                clip.native.close()
            except Exception:
                pass


class FFmpegRenderer(VideoRendererBackend):
    """FFmpeg subprocess backend (MoviePy-free alternative).

    Strategy: each operation generates an intermediate file or FFmpeg filter
    expression. Final write assembles the filter graph and runs ffmpeg.

    This is a minimal viable implementation covering the core pipeline path.
    Advanced features (karaoke, animations) still require MoviePy.
    """

    def __init__(self, tmp_dir: str | Path = ".tmp/ffmpeg_render") -> None:
        self._tmp = Path(tmp_dir).resolve()
        self._tmp.mkdir(parents=True, exist_ok=True)
        self._counter = 0

    def _next_tmp(self, ext: str = ".mp4") -> Path:
        self._counter += 1
        return self._tmp / f"_seg_{self._counter:04d}{ext}"

    def _probe_duration(self, path: str | Path) -> float:
        import json
        import subprocess

        try:
            result = subprocess.run(
                [
                    "ffprobe", "-v", "quiet",
                    "-print_format", "json",
                    "-show_format", str(path),
                ],
                capture_output=True, text=True, timeout=10,
            )
            info = json.loads(result.stdout)
            return float(info.get("format", {}).get("duration", 0))
        except Exception:
            return 0.0

    def _run_ffmpeg(self, args: list[str], timeout: int = 300) -> None:
        import subprocess

        cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "warning"] + args
        logger.debug("[FFmpeg] %s", " ".join(cmd))
        subprocess.run(cmd, check=True, timeout=timeout)

    def load_video(self, path: str | Path, audio: bool = True) -> ClipHandle:
        dur = self._probe_duration(path)
        return ClipHandle(backend="ffmpeg", native=str(path), duration=dur, has_audio=audio)

    def load_image(self, path: str | Path, duration: float = 5.0) -> ClipHandle:
        out = self._next_tmp()
        self._run_ffmpeg([
            "-loop", "1", "-i", str(path),
            "-t", str(duration),
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2",
            str(out),
        ])
        return ClipHandle(backend="ffmpeg", native=str(out), duration=duration, width=1080, height=1920)

    def load_audio(self, path: str | Path) -> ClipHandle:
        dur = self._probe_duration(path)
        return ClipHandle(backend="ffmpeg", native=str(path), duration=dur, has_audio=True)

    def composite(self, clips: list[ClipHandle], size: tuple[int, int] | None = None) -> ClipHandle:
        if not clips:
            raise ValueError("No clips to composite")
        if len(clips) == 1:
            return clips[0]
        # Overlay clips sequentially onto the base
        out = self._next_tmp()
        inputs = []
        for c in clips:
            inputs.extend(["-i", c.native])
        filter_parts = []
        current = "[0:v]"
        for i in range(1, len(clips)):
            next_label = f"[tmp{i}]" if i < len(clips) - 1 else "[out]"
            filter_parts.append(f"{current}[{i}:v]overlay=0:0{next_label}")
            current = next_label
        filter_str = ";".join(filter_parts)
        self._run_ffmpeg(inputs + ["-filter_complex", filter_str, "-map", "[out]", "-map", "0:a?", str(out)])
        return ClipHandle(backend="ffmpeg", native=str(out), duration=clips[0].duration)

    def concatenate(self, clips: list[ClipHandle], method: str = "compose") -> ClipHandle:
        if not clips:
            raise ValueError("No clips to concatenate")
        if len(clips) == 1:
            return clips[0]
        # Use concat demuxer
        list_file = self._next_tmp(ext=".txt")
        with open(list_file, "w") as f:
            for c in clips:
                f.write(f"file '{c.native}'\n")
        out = self._next_tmp()
        self._run_ffmpeg(["-f", "concat", "-safe", "0", "-i", str(list_file), "-c", "copy", str(out)])
        total_dur = sum(c.duration for c in clips)
        return ClipHandle(backend="ffmpeg", native=str(out), duration=total_dur)

    def set_audio(self, video: ClipHandle, audio: ClipHandle) -> ClipHandle:
        out = self._next_tmp()
        self._run_ffmpeg([
            "-i", video.native, "-i", audio.native,
            "-c:v", "copy", "-c:a", "aac", "-map", "0:v", "-map", "1:a",
            "-shortest", str(out),
        ])
        return ClipHandle(backend="ffmpeg", native=str(out), duration=video.duration, has_audio=True)

    def mix_audio(self, clips: list[ClipHandle]) -> ClipHandle:
        if len(clips) == 1:
            return clips[0]
        out = self._next_tmp(ext=".aac")
        inputs = []
        for c in clips:
            inputs.extend(["-i", c.native])
        n = len(clips)
        self._run_ffmpeg(inputs + [
            "-filter_complex", f"amix=inputs={n}:duration=longest",
            str(out),
        ])
        return ClipHandle(backend="ffmpeg", native=str(out), duration=max(c.duration for c in clips))

    def resize(self, clip: ClipHandle, width: int, height: int) -> ClipHandle:
        out = self._next_tmp()
        self._run_ffmpeg([
            "-i", clip.native,
            "-vf", f"scale={width}:{height}",
            "-c:a", "copy", str(out),
        ])
        return ClipHandle(backend="ffmpeg", native=str(out), duration=clip.duration, width=width, height=height)

    def subclip(self, clip: ClipHandle, start: float, end: float) -> ClipHandle:
        out = self._next_tmp()
        self._run_ffmpeg([
            "-ss", str(start), "-to", str(end),
            "-i", clip.native, "-c", "copy", str(out),
        ])
        return ClipHandle(backend="ffmpeg", native=str(out), duration=end - start)

    def set_position(self, clip: ClipHandle, pos: tuple) -> ClipHandle:
        clip.metadata["position"] = pos
        return clip

    def set_duration(self, clip: ClipHandle, duration: float) -> ClipHandle:
        out = self._next_tmp()
        self._run_ffmpeg(["-i", clip.native, "-t", str(duration), "-c", "copy", str(out)])
        return ClipHandle(backend="ffmpeg", native=str(out), duration=duration)

    def fade_in(self, clip: ClipHandle, duration: float) -> ClipHandle:
        out = self._next_tmp()
        self._run_ffmpeg([
            "-i", clip.native,
            "-vf", f"fade=in:d={duration}",
            "-c:a", "copy", str(out),
        ])
        return ClipHandle(backend="ffmpeg", native=str(out), duration=clip.duration)

    def fade_out(self, clip: ClipHandle, duration: float) -> ClipHandle:
        out = self._next_tmp()
        start = max(clip.duration - duration, 0)
        self._run_ffmpeg([
            "-i", clip.native,
            "-vf", f"fade=out:st={start}:d={duration}",
            "-c:a", "copy", str(out),
        ])
        return ClipHandle(backend="ffmpeg", native=str(out), duration=clip.duration)

    def set_opacity(self, clip: ClipHandle, opacity: float) -> ClipHandle:
        clip.metadata["opacity"] = opacity
        return clip

    def write(
        self, clip: ClipHandle, output_path: str | Path,
        fps: int = 30, codec: str = "libx264", audio_codec: str = "aac",
        preset: str | None = "medium", ffmpeg_params: list[str] | None = None,
    ) -> Path:
        out = Path(output_path)
        args = ["-i", clip.native, "-c:v", codec, "-c:a", audio_codec, "-r", str(fps)]
        if preset:
            args.extend(["-preset", preset])
        if ffmpeg_params:
            args.extend(ffmpeg_params)
        args.append(str(out))
        self._run_ffmpeg(args)
        return out

    def close(self, clip: ClipHandle) -> None:
        # FFmpeg backend: intermediate files, no cleanup needed during session
        pass

    def cleanup(self) -> None:
        """Remove all intermediate files."""
        import shutil

        if self._tmp.exists():
            shutil.rmtree(self._tmp, ignore_errors=True)


# ── Factory ──

_BACKENDS: dict[str, type[VideoRendererBackend]] = {
    "moviepy": MoviePyRenderer,
    "ffmpeg": FFmpegRenderer,
}


def create_renderer(backend: str = "moviepy", **kwargs: Any) -> VideoRendererBackend:
    """Create a video renderer backend by name."""
    cls = _BACKENDS.get(backend)
    if cls is None:
        raise ValueError(f"Unknown renderer backend: {backend!r}. Available: {list(_BACKENDS)}")
    return cls(**kwargs)
