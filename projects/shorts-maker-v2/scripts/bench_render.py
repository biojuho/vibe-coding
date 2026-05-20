"""Render performance benchmark for shorts-maker-v2.

The render step is ~85-89% of total pipeline wall time (990s of 1110s in
run 20260519-014816-a37f7826). Encoding is hardware-accelerated (h264_qsv
on this machine), so that budget is spent in MoviePy's per-frame Python
compositing: background motion, color grading, and caption overlays.

This script reproduces that hot path on synthetic assets so render-step
optimizations can be measured deterministically -- without a full LLM
pipeline run (which costs API tokens and ~18 minutes).

It is a measurement tool, not a test; it imports the real production
functions (`_fit_vertical`, `_ken_burns`, `color_grade_clip`, the renderer
backend, hw-encoder detection) so the numbers reflect the real pipeline.

Usage:
    python scripts/bench_render.py                      # 2 scenes x 3s
    python scripts/bench_render.py --scenes 4 --duration 5 --profile
    python scripts/bench_render.py --no-color-grade     # isolate motion cost
"""

from __future__ import annotations

import argparse
import cProfile
import io
import pstats
import sys
import tempfile
import time
from pathlib import Path

_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import numpy as np  # noqa: E402
from moviepy import CompositeVideoClip, ImageClip, concatenate_videoclips  # noqa: E402
from PIL import Image  # noqa: E402

from shorts_maker_v2.pipeline.render_effects import RenderEffectsMixin  # noqa: E402
from shorts_maker_v2.render.color_grading import color_grade_clip  # noqa: E402
from shorts_maker_v2.render.video_renderer import ClipHandle, create_renderer  # noqa: E402
from shorts_maker_v2.utils.hwaccel import detect_hw_encoder  # noqa: E402

TW, TH = 1080, 1920


def _make_bg_png(path: Path, size: tuple[int, int] = (1024, 1024)) -> None:
    """Generate a gradient+noise PNG. Content is irrelevant to render timing
    (resize/composite cost depends on pixel count, not pixel values) but the
    entropy keeps the encoder from trivially compressing flat regions."""
    rng = np.random.default_rng(7)
    w, h = size
    base = np.linspace(20, 220, h, dtype=np.float32)[:, None, None]
    base = np.repeat(np.repeat(base, w, axis=1), 3, axis=2)
    noise = rng.integers(0, 40, (h, w, 3)).astype(np.float32)
    Image.fromarray(np.clip(base + noise, 0, 255).astype(np.uint8)).save(path)


def _make_caption_png(path: Path, w: int = TW) -> None:
    """Generate a translucent caption-bar RGBA PNG (mimics a karaoke chunk)."""
    arr = np.zeros((220, w, 4), dtype=np.uint8)
    arr[40:180, 120 : w - 120] = (255, 255, 255, 235)
    Image.fromarray(arr, "RGBA").save(path)


def _build_scene(bg_png: Path, caption_pngs: list[Path], duration: float, *, color_grade: bool):
    """Reproduce the image-scene composite path from RenderStep._render_single_scene."""
    img = ImageClip(str(bg_png)).with_duration(duration)
    base = RenderEffectsMixin._fit_vertical(img, TW, TH)
    base = RenderEffectsMixin._ken_burns(base, TW, TH)
    base = base.with_duration(duration)
    if color_grade:
        base = color_grade_clip(base, "ai_tech", "body")

    caption_clips = []
    seg = duration / max(len(caption_pngs), 1)
    for i, cap_png in enumerate(caption_pngs):
        clip = (
            ImageClip(str(cap_png), transparent=True)
            .with_duration(seg)
            .with_start(i * seg)
            .with_position(("center", TH - 420))
        )
        caption_clips.append(clip)
    # use_bgclip mirrors RenderStep._render_single_scene: the opaque full-frame
    # base is the background, so MoviePy skips the discarded per-frame mask.
    return CompositeVideoClip([base] + caption_clips, size=(TW, TH), use_bgclip=True)


def _build_final(tmp: Path, scenes: int, duration: float, *, color_grade: bool):
    bg = tmp / "bench_bg.png"
    _make_bg_png(bg)
    caption_pngs = []
    for i in range(3):
        cap = tmp / f"bench_cap_{i}.png"
        _make_caption_png(cap)
        caption_pngs.append(cap)
    scene_clips = [_build_scene(bg, caption_pngs, duration, color_grade=color_grade) for _ in range(scenes)]
    return concatenate_videoclips(scene_clips, method="compose")


def _render(final, out_path: Path) -> tuple[float, str]:
    codec, hw_params = detect_hw_encoder("auto")
    ffmpeg_params = list(hw_params) + ["-s", f"{TW}x{TH}"]
    preset = None if codec != "libx264" else "medium"
    renderer = create_renderer("moviepy")
    handle = ClipHandle(backend="moviepy", native=final, duration=final.duration)
    start = time.perf_counter()
    renderer.write(
        handle,
        out_path,
        fps=30,
        codec=codec,
        audio_codec="aac",
        preset=preset,
        ffmpeg_params=ffmpeg_params,
    )
    return time.perf_counter() - start, codec


def main() -> int:
    parser = argparse.ArgumentParser(description="shorts-maker-v2 render hot-path benchmark")
    parser.add_argument("--scenes", type=int, default=2, help="number of scenes (default 2)")
    parser.add_argument("--duration", type=float, default=3.0, help="seconds per scene (default 3.0)")
    parser.add_argument("--profile", action="store_true", help="run cProfile and print top hotspots")
    parser.add_argument("--no-color-grade", dest="color_grade", action="store_false", help="skip color grading")
    parser.add_argument("--keep", action="store_true", help="keep the rendered mp4 for inspection")
    args = parser.parse_args()

    video_sec = args.scenes * args.duration
    print(
        f"[bench_render] scenes={args.scenes} duration={args.duration}s "
        f"video={video_sec:.1f}s color_grade={args.color_grade} profile={args.profile}"
    )

    with tempfile.TemporaryDirectory(prefix="bench_render_") as td:
        tmp = Path(td)
        build_start = time.perf_counter()
        final = _build_final(tmp, args.scenes, args.duration, color_grade=args.color_grade)
        build_elapsed = time.perf_counter() - build_start
        out_path = tmp / "bench_out.mp4"

        if args.profile:
            profiler = cProfile.Profile()
            profiler.enable()
            render_elapsed, codec = _render(final, out_path)
            profiler.disable()
            stats_buf = io.StringIO()
            pstats.Stats(profiler, stream=stats_buf).sort_stats("cumulative").print_stats(15)
            print("\n--- cProfile (top 15 by cumulative time) ---")
            print(stats_buf.getvalue())
        else:
            render_elapsed, codec = _render(final, out_path)

        size_mb = out_path.stat().st_size / 1_048_576 if out_path.exists() else 0.0
        speed = video_sec / max(render_elapsed, 1e-6)
        print("--- result ---")
        print(f"  encoder         : {codec}")
        print(f"  graph build     : {build_elapsed:.2f}s")
        print(f"  render (write)  : {render_elapsed:.2f}s")
        print(f"  output size     : {size_mb:.1f} MB")
        print(f"  speed ratio     : {speed:.2f}x realtime ({'faster' if speed > 1 else 'SLOWER'})")
        print(f"  per-video-sec   : {render_elapsed / max(video_sec, 1e-6):.2f}s render / 1s video")

        if args.keep and out_path.exists():
            kept = Path.cwd() / "bench_out.mp4"
            kept.write_bytes(out_path.read_bytes())
            print(f"  kept output     : {kept}")

    with __import__("contextlib").suppress(Exception):
        final.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
