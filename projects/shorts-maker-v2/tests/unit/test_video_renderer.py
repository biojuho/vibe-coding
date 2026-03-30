"""video_renderer 단위 테스트.

MoviePyRenderer와 FFmpegRenderer의 인터페이스 동작을 검증합니다.
MoviePy import는 실제 MoviePy가 설치되어 있으므로 정상 동작합니다.
"""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from shorts_maker_v2.render.video_renderer import (
    ClipHandle,
    FFmpegRenderer,
    MoviePyRenderer,
    VideoRendererBackend,
    create_renderer,
)


class TestClipHandle:
    def test_defaults(self):
        ch = ClipHandle(backend="test", native=None)
        assert ch.duration == 0.0
        assert ch.width == 0
        assert ch.has_audio is False
        assert ch.metadata == {}

    def test_with_values(self):
        ch = ClipHandle(
            backend="moviepy", native="obj",
            duration=5.0, width=1080, height=1920, has_audio=True,
        )
        assert ch.duration == 5.0
        assert ch.width == 1080
        assert ch.has_audio is True


class TestCreateRenderer:
    def test_create_moviepy(self):
        r = create_renderer("moviepy")
        assert isinstance(r, MoviePyRenderer)

    def test_create_ffmpeg(self):
        r = create_renderer("ffmpeg")
        assert isinstance(r, FFmpegRenderer)

    def test_unknown_raises(self):
        try:
            create_renderer("unknown")
            raise AssertionError("Should have raised")
        except ValueError as e:
            assert "unknown" in str(e)


class TestMoviePyRenderer:
    def test_is_backend(self):
        r = MoviePyRenderer()
        assert isinstance(r, VideoRendererBackend)

    def test_wrap_clip(self):
        r = MoviePyRenderer()
        mock_clip = MagicMock()
        mock_clip.duration = 5.0
        mock_clip.w = 1080
        mock_clip.h = 1920
        mock_clip.audio = MagicMock()
        handle = r._wrap(mock_clip)
        assert handle.backend == "moviepy"
        assert handle.duration == 5.0
        assert handle.width == 1080
        assert handle.has_audio is True

    def test_wrap_no_audio(self):
        r = MoviePyRenderer()
        mock_clip = MagicMock()
        mock_clip.duration = 3.0
        mock_clip.w = 720
        mock_clip.h = 1280
        mock_clip.audio = None
        handle = r._wrap(mock_clip)
        assert handle.has_audio is False

    def test_close_noop_on_none(self):
        r = MoviePyRenderer()
        ch = ClipHandle(backend="moviepy", native=None)
        r.close(ch)  # should not raise

    def test_close_calls_native_close(self):
        r = MoviePyRenderer()
        mock_native = MagicMock()
        ch = ClipHandle(backend="moviepy", native=mock_native)
        r.close(ch)
        mock_native.close.assert_called_once()

    def test_close_all(self):
        r = MoviePyRenderer()
        clips = [
            ClipHandle(backend="moviepy", native=MagicMock()),
            ClipHandle(backend="moviepy", native=MagicMock()),
        ]
        r.close_all(clips)
        for c in clips:
            c.native.close.assert_called_once()

    def test_subclip(self):
        r = MoviePyRenderer()
        mock_clip = MagicMock()
        mock_result = MagicMock()
        mock_result.duration = 2.0
        mock_result.w = 1080
        mock_result.h = 1920
        mock_result.audio = None
        mock_clip.subclipped.return_value = mock_result
        ch = ClipHandle(backend="moviepy", native=mock_clip, duration=5.0)
        result = r.subclip(ch, 1.0, 3.0)
        mock_clip.subclipped.assert_called_once_with(1.0, 3.0)
        assert result.duration == 2.0

    def test_set_duration(self):
        r = MoviePyRenderer()
        mock_clip = MagicMock()
        mock_result = MagicMock()
        mock_result.duration = 10.0
        mock_result.w = 0
        mock_result.h = 0
        mock_result.audio = None
        mock_clip.with_duration.return_value = mock_result
        ch = ClipHandle(backend="moviepy", native=mock_clip)
        result = r.set_duration(ch, 10.0)
        assert result.duration == 10.0

    def test_set_opacity(self):
        r = MoviePyRenderer()
        mock_clip = MagicMock()
        mock_result = MagicMock()
        mock_result.duration = 0
        mock_result.w = 0
        mock_result.h = 0
        mock_result.audio = None
        mock_clip.with_opacity.return_value = mock_result
        ch = ClipHandle(backend="moviepy", native=mock_clip)
        r.set_opacity(ch, 0.5)
        mock_clip.with_opacity.assert_called_once_with(0.5)


class TestFFmpegRenderer:
    def test_is_backend(self):
        r = FFmpegRenderer(tmp_dir=".tmp/test_ffmpeg")
        assert isinstance(r, VideoRendererBackend)

    def test_next_tmp_increments(self):
        r = FFmpegRenderer(tmp_dir=".tmp/test_ffmpeg")
        p1 = r._next_tmp()
        p2 = r._next_tmp()
        assert p1 != p2
        assert p1.suffix == ".mp4"

    def test_next_tmp_custom_ext(self):
        r = FFmpegRenderer(tmp_dir=".tmp/test_ffmpeg")
        p = r._next_tmp(ext=".aac")
        assert p.suffix == ".aac"

    def test_close_noop(self):
        r = FFmpegRenderer(tmp_dir=".tmp/test_ffmpeg")
        ch = ClipHandle(backend="ffmpeg", native="some_path.mp4")
        r.close(ch)  # should not raise

    def test_set_position_stores_metadata(self):
        r = FFmpegRenderer(tmp_dir=".tmp/test_ffmpeg")
        ch = ClipHandle(backend="ffmpeg", native="path.mp4")
        result = r.set_position(ch, (100, 200))
        assert result.metadata["position"] == (100, 200)

    def test_set_opacity_stores_metadata(self):
        r = FFmpegRenderer(tmp_dir=".tmp/test_ffmpeg")
        ch = ClipHandle(backend="ffmpeg", native="path.mp4")
        result = r.set_opacity(ch, 0.7)
        assert result.metadata["opacity"] == 0.7

    def test_concatenate_single_clip(self):
        r = FFmpegRenderer(tmp_dir=".tmp/test_ffmpeg")
        ch = ClipHandle(backend="ffmpeg", native="a.mp4", duration=5.0)
        result = r.concatenate([ch])
        assert result is ch

    def test_concatenate_empty_raises(self):
        r = FFmpegRenderer(tmp_dir=".tmp/test_ffmpeg")
        try:
            r.concatenate([])
            raise AssertionError
        except ValueError:
            pass

    def test_composite_single_returns_same(self):
        r = FFmpegRenderer(tmp_dir=".tmp/test_ffmpeg")
        ch = ClipHandle(backend="ffmpeg", native="a.mp4")
        assert r.composite([ch]) is ch

    def test_composite_empty_raises(self):
        r = FFmpegRenderer(tmp_dir=".tmp/test_ffmpeg")
        try:
            r.composite([])
            raise AssertionError
        except ValueError:
            pass

    def test_write_accepts_moviepy_native_clip(self, tmp_path: Path):
        """MoviePy composite도 intermediate export 후 ffmpeg encode로 처리한다."""
        r = FFmpegRenderer(tmp_dir=tmp_path / ".tmp_ffmpeg")
        moviepy_clip = MagicMock()
        handle = ClipHandle(backend="ffmpeg", native=moviepy_clip, duration=5.0)

        with patch.object(r, "_run_ffmpeg") as run_ffmpeg:
            output = tmp_path / "encoded.mp4"
            result = r.write(
                handle,
                output,
                fps=24,
                codec="libx264",
                audio_codec="aac",
                preset="slow",
                ffmpeg_params=["-crf", "20"],
            )

        moviepy_clip.write_videofile.assert_called_once()
        args = run_ffmpeg.call_args.args[0]
        assert args[0] == "-i"
        assert str(output) == args[-1]
        assert result == output


class TestMoviePyRendererExtended:
    def test_load_video(self):
        r = MoviePyRenderer()
        native = MagicMock()
        native.duration = 4.0
        native.w = 1920
        native.h = 1080
        native.audio = MagicMock()
        r._VideoFileClip = MagicMock(return_value=native)

        result = r.load_video("clip.mp4", audio=False)

        r._VideoFileClip.assert_called_once_with("clip.mp4", audio=False)
        assert result.duration == 4.0
        assert result.has_audio is True

    def test_load_image(self):
        r = MoviePyRenderer()
        image_clip = MagicMock()
        native = MagicMock()
        native.duration = 6.0
        native.w = 1080
        native.h = 1920
        native.audio = None
        image_clip.with_duration.return_value = native
        r._ImageClip = MagicMock(return_value=image_clip)

        result = r.load_image("frame.png", duration=6.0)

        r._ImageClip.assert_called_once_with("frame.png")
        image_clip.with_duration.assert_called_once_with(6.0)
        assert result.duration == 6.0

    def test_load_audio(self):
        r = MoviePyRenderer()
        native = MagicMock()
        native.duration = 8.0
        native.w = 0
        native.h = 0
        native.audio = MagicMock()
        r._AudioFileClip = MagicMock(return_value=native)

        result = r.load_audio("narration.wav")

        r._AudioFileClip.assert_called_once_with("narration.wav")
        assert result.duration == 8.0

    def test_composite(self):
        r = MoviePyRenderer()
        native = MagicMock()
        native.duration = 5.0
        native.w = 1080
        native.h = 1920
        native.audio = None
        r._CompositeVideoClip = MagicMock(return_value=native)
        clips = [ClipHandle(backend="moviepy", native="bg"), ClipHandle(backend="moviepy", native="fg")]

        result = r.composite(clips, size=(1080, 1920))

        r._CompositeVideoClip.assert_called_once_with(["bg", "fg"], size=(1080, 1920))
        assert result.width == 1080

    def test_concatenate(self):
        r = MoviePyRenderer()
        native = MagicMock()
        native.duration = 9.0
        native.w = 1080
        native.h = 1920
        native.audio = None
        r._concatenate = MagicMock(return_value=native)
        clips = [ClipHandle(backend="moviepy", native="a"), ClipHandle(backend="moviepy", native="b")]

        result = r.concatenate(clips, method="chain")

        r._concatenate.assert_called_once_with(["a", "b"], method="chain")
        assert result.duration == 9.0

    def test_set_audio(self):
        r = MoviePyRenderer()
        video_native = MagicMock()
        result_native = MagicMock()
        result_native.duration = 3.0
        result_native.w = 1080
        result_native.h = 1920
        result_native.audio = MagicMock()
        video_native.with_audio.return_value = result_native

        result = r.set_audio(
            ClipHandle(backend="moviepy", native=video_native),
            ClipHandle(backend="moviepy", native="audio"),
        )

        video_native.with_audio.assert_called_once_with("audio")
        assert result.has_audio is True

    def test_mix_audio(self):
        r = MoviePyRenderer()
        native = MagicMock()
        native.duration = 12.0
        native.w = 0
        native.h = 0
        native.audio = MagicMock()
        r._CompositeAudioClip = MagicMock(return_value=native)

        result = r.mix_audio(
            [ClipHandle(backend="moviepy", native="track1"), ClipHandle(backend="moviepy", native="track2")]
        )

        r._CompositeAudioClip.assert_called_once_with(["track1", "track2"])
        assert result.duration == 12.0

    def test_resize(self):
        r = MoviePyRenderer()
        native = MagicMock()
        native.duration = 1.0
        native.w = 720
        native.h = 1280
        native.audio = None
        source = MagicMock()
        source.resized.return_value = native

        result = r.resize(ClipHandle(backend="moviepy", native=source), 720, 1280)

        source.resized.assert_called_once_with((720, 1280))
        assert result.width == 720

    def test_set_position(self):
        r = MoviePyRenderer()
        native = MagicMock()
        native.duration = 1.0
        native.w = 100
        native.h = 100
        native.audio = None
        source = MagicMock()
        source.with_position.return_value = native

        result = r.set_position(ClipHandle(backend="moviepy", native=source), ("center", 40))

        source.with_position.assert_called_once_with(("center", 40))
        assert result.height == 100

    def test_fade_in(self):
        r = MoviePyRenderer()
        native = MagicMock()
        native.duration = 2.0
        native.w = 640
        native.h = 480
        native.audio = None
        source = MagicMock()
        source.with_effects.return_value = native
        r._vfx = SimpleNamespace(FadeIn=MagicMock(return_value="fade-in"))

        result = r.fade_in(ClipHandle(backend="moviepy", native=source), 0.5)

        r._vfx.FadeIn.assert_called_once_with(0.5)
        source.with_effects.assert_called_once_with(["fade-in"])
        assert result.duration == 2.0

    def test_fade_out(self):
        r = MoviePyRenderer()
        native = MagicMock()
        native.duration = 2.0
        native.w = 640
        native.h = 480
        native.audio = None
        source = MagicMock()
        source.with_effects.return_value = native
        r._vfx = SimpleNamespace(FadeOut=MagicMock(return_value="fade-out"))

        result = r.fade_out(ClipHandle(backend="moviepy", native=source), 0.5)

        r._vfx.FadeOut.assert_called_once_with(0.5)
        source.with_effects.assert_called_once_with(["fade-out"])
        assert result.duration == 2.0

    def test_write_passes_preset(self, tmp_path: Path):
        r = MoviePyRenderer()
        native = MagicMock()
        handle = ClipHandle(backend="moviepy", native=native)
        output = tmp_path / "moviepy.mp4"

        result = r.write(handle, output, fps=24, codec="libx264", audio_codec="aac", preset="slow")

        native.write_videofile.assert_called_once()
        kwargs = native.write_videofile.call_args.kwargs
        assert kwargs["preset"] == "slow"
        assert Path(kwargs["temp_audiofile"]).parent == output.parent
        assert Path(kwargs["temp_audiofile"]).suffix == ".m4a"
        assert result == output


class TestFFmpegRendererExtended:
    @patch("subprocess.run")
    def test_probe_duration_reads_ffprobe_json(self, mock_run: MagicMock):
        mock_run.return_value.stdout = '{"format": {"duration": "12.5"}}'
        r = FFmpegRenderer(tmp_dir=".tmp/test_ffmpeg")

        result = r._probe_duration("clip.mp4")

        assert result == 12.5

    @patch("subprocess.run")
    def test_probe_duration_returns_zero_on_invalid_json(self, mock_run: MagicMock):
        mock_run.return_value.stdout = "not-json"
        r = FFmpegRenderer(tmp_dir=".tmp/test_ffmpeg")

        result = r._probe_duration("clip.mp4")

        assert result == 0.0

    def test_load_video_uses_probe_duration(self):
        r = FFmpegRenderer(tmp_dir=".tmp/test_ffmpeg")
        with patch.object(r, "_probe_duration", return_value=7.25) as probe:
            result = r.load_video("input.mp4", audio=False)

        probe.assert_called_once_with("input.mp4")
        assert result.duration == 7.25
        assert result.has_audio is False

    def test_load_image_runs_ffmpeg(self, tmp_path: Path):
        r = FFmpegRenderer(tmp_dir=tmp_path / ".tmp_ffmpeg")

        with patch.object(r, "_run_ffmpeg") as run_ffmpeg:
            result = r.load_image("frame.png", duration=2.5)

        args = run_ffmpeg.call_args.args[0]
        assert args[:4] == ["-loop", "1", "-i", "frame.png"]
        assert result.duration == 2.5
        assert result.width == 1080
        assert result.height == 1920

    def test_load_audio_uses_probe_duration(self):
        r = FFmpegRenderer(tmp_dir=".tmp/test_ffmpeg")
        with patch.object(r, "_probe_duration", return_value=11.0) as probe:
            result = r.load_audio("track.wav")

        probe.assert_called_once_with("track.wav")
        assert result.duration == 11.0
        assert result.has_audio is True

    def test_composite_multiple_clips_builds_overlay_graph(self, tmp_path: Path):
        r = FFmpegRenderer(tmp_dir=tmp_path / ".tmp_ffmpeg")
        clips = [
            ClipHandle(backend="ffmpeg", native="base.mp4", duration=4.0),
            ClipHandle(backend="ffmpeg", native="top1.mp4", duration=4.0),
            ClipHandle(backend="ffmpeg", native="top2.mp4", duration=4.0),
        ]

        with patch.object(r, "_run_ffmpeg") as run_ffmpeg:
            result = r.composite(clips)

        args = run_ffmpeg.call_args.args[0]
        assert "-filter_complex" in args
        assert "[0:v][1:v]overlay=0:0[tmp1];[tmp1][2:v]overlay=0:0[out]" in args
        assert result.duration == 4.0

    def test_concatenate_multiple_clips_writes_concat_list(self, tmp_path: Path):
        r = FFmpegRenderer(tmp_dir=tmp_path / ".tmp_ffmpeg")
        clips = [
            ClipHandle(backend="ffmpeg", native="first.mp4", duration=1.5),
            ClipHandle(backend="ffmpeg", native="second.mp4", duration=2.5),
        ]

        with patch.object(r, "_run_ffmpeg") as run_ffmpeg:
            result = r.concatenate(clips)

        args = run_ffmpeg.call_args.args[0]
        list_file = Path(args[5])
        assert list_file.exists()
        assert "file 'first.mp4'" in list_file.read_text()
        assert result.duration == 4.0

    def test_set_audio_runs_ffmpeg(self, tmp_path: Path):
        r = FFmpegRenderer(tmp_dir=tmp_path / ".tmp_ffmpeg")

        with patch.object(r, "_run_ffmpeg") as run_ffmpeg:
            result = r.set_audio(
                ClipHandle(backend="ffmpeg", native="video.mp4", duration=6.0),
                ClipHandle(backend="ffmpeg", native="music.aac", duration=10.0),
            )

        args = run_ffmpeg.call_args.args[0]
        assert args[:6] == ["-i", "video.mp4", "-i", "music.aac", "-c:v", "copy"]
        assert result.duration == 6.0
        assert result.has_audio is True

    def test_mix_audio_single_clip_returns_same_handle(self):
        r = FFmpegRenderer(tmp_dir=".tmp/test_ffmpeg")
        clip = ClipHandle(backend="ffmpeg", native="solo.aac", duration=3.0)

        assert r.mix_audio([clip]) is clip

    def test_mix_audio_multiple_clips_uses_amix(self, tmp_path: Path):
        r = FFmpegRenderer(tmp_dir=tmp_path / ".tmp_ffmpeg")
        clips = [
            ClipHandle(backend="ffmpeg", native="a.aac", duration=3.0),
            ClipHandle(backend="ffmpeg", native="b.aac", duration=5.0),
        ]

        with patch.object(r, "_run_ffmpeg") as run_ffmpeg:
            result = r.mix_audio(clips)

        args = run_ffmpeg.call_args.args[0]
        assert "amix=inputs=2:duration=longest" in args
        assert result.duration == 5.0

    def test_resize_runs_ffmpeg(self, tmp_path: Path):
        r = FFmpegRenderer(tmp_dir=tmp_path / ".tmp_ffmpeg")

        with patch.object(r, "_run_ffmpeg") as run_ffmpeg:
            result = r.resize(ClipHandle(backend="ffmpeg", native="clip.mp4", duration=4.0), 720, 1280)

        args = run_ffmpeg.call_args.args[0]
        assert args == ["-i", "clip.mp4", "-vf", "scale=720:1280", "-c:a", "copy", str(result.native)]
        assert result.width == 720
        assert result.height == 1280

    def test_subclip_runs_ffmpeg(self, tmp_path: Path):
        r = FFmpegRenderer(tmp_dir=tmp_path / ".tmp_ffmpeg")

        with patch.object(r, "_run_ffmpeg") as run_ffmpeg:
            result = r.subclip(ClipHandle(backend="ffmpeg", native="clip.mp4", duration=8.0), 1.0, 4.0)

        args = run_ffmpeg.call_args.args[0]
        assert args[:6] == ["-ss", "1.0", "-to", "4.0", "-i", "clip.mp4"]
        assert result.duration == 3.0

    def test_set_duration_runs_ffmpeg(self, tmp_path: Path):
        r = FFmpegRenderer(tmp_dir=tmp_path / ".tmp_ffmpeg")

        with patch.object(r, "_run_ffmpeg") as run_ffmpeg:
            result = r.set_duration(ClipHandle(backend="ffmpeg", native="clip.mp4"), 9.0)

        run_ffmpeg.assert_called_once()
        assert result.duration == 9.0

    def test_fade_in_runs_ffmpeg(self, tmp_path: Path):
        r = FFmpegRenderer(tmp_dir=tmp_path / ".tmp_ffmpeg")

        with patch.object(r, "_run_ffmpeg") as run_ffmpeg:
            result = r.fade_in(ClipHandle(backend="ffmpeg", native="clip.mp4", duration=7.0), 1.25)

        args = run_ffmpeg.call_args.args[0]
        assert args[3] == "fade=in:d=1.25"
        assert result.duration == 7.0

    def test_fade_out_clamps_start_to_zero(self, tmp_path: Path):
        r = FFmpegRenderer(tmp_dir=tmp_path / ".tmp_ffmpeg")

        with patch.object(r, "_run_ffmpeg") as run_ffmpeg:
            result = r.fade_out(ClipHandle(backend="ffmpeg", native="clip.mp4", duration=0.5), 1.0)

        args = run_ffmpeg.call_args.args[0]
        assert args[3] == "fade=out:st=0:d=1.0"
        assert result.duration == 0.5

    def test_ensure_input_path_accepts_path_native(self, tmp_path: Path):
        r = FFmpegRenderer(tmp_dir=tmp_path / ".tmp_ffmpeg")
        native = tmp_path / "native.mp4"

        result = r._ensure_input_path(
            ClipHandle(backend="ffmpeg", native=native),
            fps=30,
            audio_codec="aac",
        )

        assert result == str(native)

    def test_ensure_input_path_accepts_string_native(self, tmp_path: Path):
        r = FFmpegRenderer(tmp_dir=tmp_path / ".tmp_ffmpeg")

        result = r._ensure_input_path(
            ClipHandle(backend="ffmpeg", native="native.mp4"),
            fps=30,
            audio_codec="aac",
        )

        assert result == "native.mp4"

    def test_write_without_optional_preset_or_extra_params(self, tmp_path: Path):
        r = FFmpegRenderer(tmp_dir=tmp_path / ".tmp_ffmpeg")
        handle = ClipHandle(backend="ffmpeg", native="ready.mp4")

        with patch.object(r, "_ensure_input_path", return_value="ready.mp4") as ensure_path, patch.object(
            r,
            "_run_ffmpeg",
        ) as run_ffmpeg:
            result = r.write(handle, tmp_path / "out.mp4", preset=None, ffmpeg_params=None)

        ensure_path.assert_called_once()
        args = run_ffmpeg.call_args.args[0]
        assert "-preset" not in args
        assert result == tmp_path / "out.mp4"

    def test_cleanup_removes_tmp_dir(self, tmp_path: Path):
        r = FFmpegRenderer(tmp_dir=tmp_path / ".tmp_ffmpeg")
        temp_file = r._next_tmp()
        temp_file.write_text("data")

        r.cleanup()

        assert not r._tmp.exists()
