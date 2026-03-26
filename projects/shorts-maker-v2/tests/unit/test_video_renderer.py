"""video_renderer 단위 테스트.

MoviePyRenderer와 FFmpegRenderer의 인터페이스 동작을 검증합니다.
MoviePy import는 실제 MoviePy가 설치되어 있으므로 정상 동작합니다.
"""

from pathlib import Path
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
