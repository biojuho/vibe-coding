"""Golden render test — verify that both MoviePy and FFmpeg backends
produce a valid 9:16 video with audio from raw test assets.

Test assets are generated on-the-fly:
  - 3 solid-color PNG images (1080×1920) via Pillow
  - 1 silent WAV audio (5 seconds, 44100 Hz) via the `wave` module

Each backend runs:
  load_image×3 → set_duration(5s) → concatenate → set_audio → write
Then ffprobe validates the output: resolution, duration, audio stream.

Usage:
    pytest tests/integration/test_golden_render.py -v --tb=short
"""

from __future__ import annotations

import json
import shutil
import struct
import subprocess
import tempfile
import wave
from pathlib import Path
from typing import Any

import PIL.Image as PILImage
import pytest

from shorts_maker_v2.render.video_renderer import (
    ClipHandle,
    VideoRendererBackend,
    create_renderer,
)

# ── ffprobe availability check ─────────────────────────────────────────────

_ffprobe_available = shutil.which("ffprobe") is not None
if not _ffprobe_available:
    try:
        import imageio_ffmpeg

        _ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        if _ffmpeg_exe:
            candidate = Path(_ffmpeg_exe).parent / "ffprobe"
            if not candidate.exists():
                candidate = Path(_ffmpeg_exe).parent / "ffprobe.exe"
            _ffprobe_available = candidate.exists()
    except Exception:
        pass

pytestmark = pytest.mark.skipif(
    not _ffprobe_available,
    reason="ffprobe not available in this environment",
)

# ── Helpers ────────────────────────────────────────────────────────────────

TARGET_W, TARGET_H = 1080, 1920
SCENE_DURATION = 5.0  # seconds per scene
SCENE_COLORS = (
    (255, 0, 0),
    (255, 128, 0),
    (255, 255, 0),
    (0, 200, 0),
    (0, 120, 255),
    (128, 0, 255),
)
EXPECTED_TOTAL = SCENE_DURATION * len(SCENE_COLORS)  # 30 seconds
DURATION_TOLERANCE = 2.0  # ffprobe tolerance (seconds)
AUDIO_VIDEO_SYNC_TOLERANCE = 0.5  # allow small AAC padding/encoder drift


def _make_test_image(path: Path, color: tuple[int, int, int]) -> Path:
    """Create a solid-color PNG test image at 1080×1920."""
    img = PILImage.new("RGB", (TARGET_W, TARGET_H), color)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(path), format="PNG")
    return path


def _make_silent_wav(path: Path, duration_sec: float = 5.0, sample_rate: int = 44100) -> Path:
    """Create a silent WAV file using the `wave` module (no ffmpeg needed)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    n_frames = int(sample_rate * duration_sec)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        # Write silence (zeros)
        wf.writeframes(struct.pack(f"<{n_frames}h", *([0] * n_frames)))
    return path


def _ffprobe(video_path: Path) -> dict[str, Any]:
    """Run ffprobe and return parsed JSON metadata."""
    # Resolve ffprobe binary (imageio_ffmpeg bundles it alongside ffmpeg)
    ffprobe_bin = "ffprobe"
    try:
        import imageio_ffmpeg

        _ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        if _ffmpeg_exe:
            candidate = Path(_ffmpeg_exe).parent / "ffprobe.exe"
            if not candidate.exists():
                candidate = Path(_ffmpeg_exe).parent / "ffprobe"
            if candidate.exists():
                ffprobe_bin = str(candidate)
    except Exception:
        pass

    cmd = [
        ffprobe_bin,
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(video_path),
    ]
    result = subprocess.run(
        cmd,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        stdin=subprocess.DEVNULL,
        timeout=30,
    )
    assert result.returncode == 0, f"ffprobe failed (rc={result.returncode}): {result.stderr}"
    assert result.stdout, f"ffprobe returned empty output for {video_path}"
    return json.loads(result.stdout)


def _stream_duration(stream: dict[str, Any], fallback: float) -> float:
    """Read a stream duration from ffprobe, falling back to the container value."""
    raw = stream.get("duration")
    if raw in (None, "N/A", ""):
        tags = stream.get("tags", {})
        raw = tags.get("DURATION")
    if isinstance(raw, str) and ":" in raw:
        hours, minutes, seconds = raw.split(":")
        return (int(hours) * 3600) + (int(minutes) * 60) + float(seconds)
    if raw not in (None, "N/A", ""):
        return float(raw)
    return fallback


def _validate_output(video_path: Path) -> None:
    """Assert output video meets golden criteria."""
    assert video_path.exists(), f"Output file missing: {video_path}"
    assert video_path.stat().st_size > 10_000, f"Output too small: {video_path.stat().st_size} bytes"

    info = _ffprobe(video_path)

    # Check format duration
    fmt_duration = float(info["format"]["duration"])
    assert abs(fmt_duration - EXPECTED_TOTAL) < DURATION_TOLERANCE, (
        f"Duration mismatch: {fmt_duration:.1f}s (expected ~{EXPECTED_TOTAL}s)"
    )

    # Find video and audio streams
    video_stream = None
    audio_stream = None
    for s in info.get("streams", []):
        if s["codec_type"] == "video" and video_stream is None:
            video_stream = s
        elif s["codec_type"] == "audio" and audio_stream is None:
            audio_stream = s

    assert video_stream is not None, "No video stream found"
    assert audio_stream is not None, "No audio stream found"

    # Check resolution
    width = int(video_stream["width"])
    height = int(video_stream["height"])
    assert width == TARGET_W, f"Width mismatch: {width} (expected {TARGET_W})"
    assert height == TARGET_H, f"Height mismatch: {height} (expected {TARGET_H})"

    video_duration = _stream_duration(video_stream, fmt_duration)
    audio_duration = _stream_duration(audio_stream, fmt_duration)
    assert abs(video_duration - EXPECTED_TOTAL) < DURATION_TOLERANCE, (
        f"Video duration mismatch: {video_duration:.2f}s (expected ~{EXPECTED_TOTAL}s)"
    )
    assert abs(audio_duration - EXPECTED_TOTAL) < DURATION_TOLERANCE, (
        f"Audio duration mismatch: {audio_duration:.2f}s (expected ~{EXPECTED_TOTAL}s)"
    )
    assert abs(video_duration - audio_duration) < AUDIO_VIDEO_SYNC_TOLERANCE, (
        f"Audio/video drift too large: video={video_duration:.2f}s audio={audio_duration:.2f}s"
    )


def _generate_assets(base_dir: Path) -> dict[str, Any]:
    """Generate test images and audio in the given directory."""
    images = [
        _make_test_image(base_dir / f"scene_{index}.png", color) for index, color in enumerate(SCENE_COLORS, start=1)
    ]
    audio = _make_silent_wav(base_dir / "silence.wav", duration_sec=EXPECTED_TOTAL)
    output_dir = base_dir / "output"
    output_dir.mkdir(exist_ok=True)
    return {"images": images, "audio": audio, "output_dir": output_dir}


# ── Fixtures ───────────────────────────────────────────────────────────────


@pytest.fixture
def test_assets(tmp_path: Path) -> dict[str, Any]:
    """Generate test images and audio in a temp directory."""
    return _generate_assets(tmp_path)


@pytest.fixture
def ascii_test_assets():
    """Generate test assets in an ASCII-safe temp directory.

    FFmpeg on Windows cannot handle non-ASCII (e.g. Korean) characters in
    file paths used by the concat demuxer, so we create a temp dir under
    C:\\Temp (or the system temp root when it's ASCII-safe).
    """
    # Try ASCII-safe locations
    ascii_root = Path("C:/Temp")
    if not ascii_root.exists():
        ascii_root.mkdir(parents=True, exist_ok=True)
    td = Path(tempfile.mkdtemp(prefix="golden_ffmpeg_", dir=str(ascii_root)))
    try:
        yield _generate_assets(td)
    finally:
        shutil.rmtree(td, ignore_errors=True)


# ── Render pipeline helper ─────────────────────────────────────────────────


def _run_golden_pipeline(
    renderer: VideoRendererBackend,
    assets: dict[str, Any],
    output_name: str,
) -> Path:
    """Execute the golden render pipeline and return the output path."""
    clips: list[ClipHandle] = []
    for img_path in assets["images"]:
        clip = renderer.load_image(img_path, duration=SCENE_DURATION)
        clips.append(clip)

    # Concatenate scenes
    video = renderer.concatenate(clips)

    # Load and attach audio
    audio = renderer.load_audio(assets["audio"])
    final = renderer.set_audio(video, audio)

    # Write output
    output_path = assets["output_dir"] / output_name
    renderer.write(final, output_path, fps=30, codec="libx264", audio_codec="aac")

    # Cleanup
    renderer.close_all([*clips, video, audio, final])

    return output_path


# ── Tests ──────────────────────────────────────────────────────────────────


@pytest.mark.slow
def test_golden_render_moviepy(test_assets: dict[str, Any]) -> None:
    """MoviePy backend: 3-scene concatenation with audio → valid MP4."""
    renderer = create_renderer("moviepy")
    output = _run_golden_pipeline(renderer, test_assets, "golden_moviepy.mp4")
    _validate_output(output)


@pytest.mark.slow
def test_golden_render_ffmpeg(ascii_test_assets: dict[str, Any]) -> None:
    """FFmpeg backend: 3-scene concatenation with audio → valid MP4."""
    renderer = create_renderer("ffmpeg", tmp_dir=str(ascii_test_assets["output_dir"] / "_ffmpeg_tmp"))
    output = _run_golden_pipeline(renderer, ascii_test_assets, "golden_ffmpeg.mp4")
    _validate_output(output)
