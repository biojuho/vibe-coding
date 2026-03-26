"""audio_postprocess.py 유닛 테스트."""

from __future__ import annotations

import sys
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest

from shorts_maker_v2.render.audio_postprocess import (
    _apply_compression,
    _apply_subtle_reverb,
    EQ_PRESETS,
    apply_eq,
    detect_voice_gender,
    normalize_audio,
    postprocess_tts_audio,
)

# ── detect_voice_gender ──────────────────────────────────────────────────────


class TestDetectVoiceGender:
    def test_female_sunhi(self):
        assert detect_voice_gender("ko-KR-SunHi-Neural") == "female_voice"

    def test_female_soonbok(self):
        assert detect_voice_gender("ko-KR-SoonBokNeural") == "female_voice"

    def test_male_injoon(self):
        assert detect_voice_gender("ko-KR-InJoon-Neural") == "male_voice"

    def test_male_hyunsu(self):
        assert detect_voice_gender("ko-KR-HyunsuNeural") == "male_voice"

    def test_male_bongjin(self):
        assert detect_voice_gender("ko-KR-BongJin-Neural") == "male_voice"

    def test_male_gookmin(self):
        assert detect_voice_gender("ko-KR-GookMin-Neural") == "male_voice"

    def test_unknown_voice_returns_neutral(self):
        assert detect_voice_gender("en-US-JennyNeural") == "neutral"

    def test_empty_string_returns_neutral(self):
        assert detect_voice_gender("") == "neutral"

    def test_case_insensitive_female(self):
        assert detect_voice_gender("ko-kr-sunhi-neural") == "female_voice"

    def test_case_insensitive_male(self):
        assert detect_voice_gender("ko-kr-injoon-neural") == "male_voice"


# ── EQ_PRESETS ───────────────────────────────────────────────────────────────


class TestEqPresets:
    def test_all_presets_defined(self):
        assert "male_voice" in EQ_PRESETS
        assert "female_voice" in EQ_PRESETS
        assert "neutral" in EQ_PRESETS

    def test_each_preset_has_bands(self):
        for name, bands in EQ_PRESETS.items():
            assert len(bands) > 0, f"{name} has no bands"

    def test_bands_are_3_tuples(self):
        for name, bands in EQ_PRESETS.items():
            for band in bands:
                assert len(band) == 3, f"{name} band {band} not a 3-tuple"
                low, high, gain = band
                assert low < high, f"{name}: low_freq >= high_freq"
                assert isinstance(gain, (int, float))


# ── normalize_audio (pydub fallback) ─────────────────────────────────────────


class TestNormalizeAudio:
    def test_returns_path_when_pydub_missing(self, tmp_path):
        """pydub 없으면 원본 경로 그대로 반환."""
        audio = tmp_path / "test.mp3"
        audio.write_bytes(b"\xff\xfb\x00")  # 더미 mp3

        with patch.dict("sys.modules", {"pydub": None}):
            result = normalize_audio(audio)
        assert result == audio

    def test_normalize_applies_gain(self, tmp_path):
        """pydub 있을 때 gain 적용 및 export 호출 확인."""
        pytest.importorskip("pydub")
        audio = tmp_path / "test.mp3"
        audio.write_bytes(b"\xff\xfb\x00")

        mock_segment = MagicMock()
        mock_segment.dBFS = -30.0  # 목표 -14 → gain +16 필요
        mock_normalized = MagicMock()
        mock_segment.apply_gain.return_value = mock_normalized

        with patch("shorts_maker_v2.render.audio_postprocess.AudioSegment") as MockAudio:
            MockAudio.from_file.return_value = mock_segment
            result = normalize_audio(audio, target_lufs=-14.0)

        mock_segment.apply_gain.assert_called_once()
        gain_arg = mock_segment.apply_gain.call_args[0][0]
        assert abs(gain_arg - 16.0) < 0.1  # -14 - (-30) = 16
        mock_normalized.export.assert_called_once()
        assert result == audio

    def test_normalize_skips_when_silent(self, tmp_path):
        """무음(dBFS=-inf)이면 건너뜀."""
        pytest.importorskip("pydub")
        audio = tmp_path / "silent.mp3"
        audio.write_bytes(b"\x00" * 100)

        mock_segment = MagicMock()
        mock_segment.dBFS = float("-inf")

        with patch("shorts_maker_v2.render.audio_postprocess.AudioSegment") as MockAudio:
            MockAudio.from_file.return_value = mock_segment
            result = normalize_audio(audio)

        mock_segment.apply_gain.assert_not_called()
        assert result == audio

    def test_normalize_skips_when_difference_small(self, tmp_path):
        """차이 < 0.5dB면 export 건너뜀."""
        pytest.importorskip("pydub")
        audio = tmp_path / "test.mp3"
        audio.write_bytes(b"\x00")

        mock_segment = MagicMock()
        mock_segment.dBFS = -14.3  # 목표 -14 → 차이 0.3 < 0.5

        with patch("shorts_maker_v2.render.audio_postprocess.AudioSegment") as MockAudio:
            MockAudio.from_file.return_value = mock_segment
            normalize_audio(audio, target_lufs=-14.0)

        mock_segment.apply_gain.assert_not_called()

    def test_normalize_caps_gain_at_20db(self, tmp_path):
        """과도한 증폭 최대 +20dB로 제한."""
        pytest.importorskip("pydub")
        audio = tmp_path / "quiet.mp3"
        audio.write_bytes(b"\x00")

        mock_segment = MagicMock()
        mock_segment.dBFS = -60.0  # 차이 46dB → 최대 20으로 제한
        mock_normalized = MagicMock()
        mock_segment.apply_gain.return_value = mock_normalized

        with patch("shorts_maker_v2.render.audio_postprocess.AudioSegment") as MockAudio:
            MockAudio.from_file.return_value = mock_segment
            normalize_audio(audio)

        gain_arg = mock_segment.apply_gain.call_args[0][0]
        assert gain_arg <= 20.0

    def test_normalize_fallback_on_exception(self, tmp_path):
        """예외 발생 시 원본 경로 반환 (graceful fallback)."""
        pytest.importorskip("pydub")
        audio = tmp_path / "bad.mp3"
        audio.write_bytes(b"\x00")

        with patch("shorts_maker_v2.render.audio_postprocess.AudioSegment") as MockAudio:
            MockAudio.from_file.side_effect = Exception("corrupt file")
            result = normalize_audio(audio)

        assert result == audio


# ── apply_eq ─────────────────────────────────────────────────────────────────


class TestApplyEq:
    def test_returns_path_when_pydub_missing(self, tmp_path):
        audio = tmp_path / "test.mp3"
        audio.write_bytes(b"\x00")
        with patch.dict("sys.modules", {"pydub": None, "pydub.effects": None}):
            result = apply_eq(audio)
        assert result == audio

    def test_applies_preset_bands(self, tmp_path):
        pytest.importorskip("pydub")
        audio = tmp_path / "test.mp3"
        audio.write_bytes(b"\x00")

        mock_audio = MagicMock()
        mock_band = MagicMock()
        mock_band.apply_gain.return_value = mock_band
        mock_audio.overlay.return_value = mock_audio

        with (
            patch("shorts_maker_v2.render.audio_postprocess.AudioSegment") as MockAudio,
            patch("shorts_maker_v2.render.audio_postprocess.high_pass_filter", return_value=mock_band),
            patch("shorts_maker_v2.render.audio_postprocess.low_pass_filter", return_value=mock_band),
        ):
            MockAudio.from_file.return_value = mock_audio
            result = apply_eq(audio, preset="neutral")

        mock_audio.export.assert_called_once()
        assert result == audio

    def test_invalid_preset_falls_back_to_neutral(self, tmp_path):
        pytest.importorskip("pydub")
        audio = tmp_path / "test.mp3"
        audio.write_bytes(b"\x00")

        mock_audio = MagicMock()
        mock_audio.overlay.return_value = mock_audio

        with (
            patch("shorts_maker_v2.render.audio_postprocess.AudioSegment") as MockAudio,
            patch("shorts_maker_v2.render.audio_postprocess.high_pass_filter", return_value=MagicMock()),
            patch("shorts_maker_v2.render.audio_postprocess.low_pass_filter", return_value=MagicMock()),
        ):
            MockAudio.from_file.return_value = mock_audio
            result = apply_eq(audio, preset="nonexistent_preset")

        assert result == audio

    def test_fallback_on_exception(self, tmp_path):
        pytest.importorskip("pydub")
        audio = tmp_path / "bad.mp3"
        audio.write_bytes(b"\x00")

        with patch("shorts_maker_v2.render.audio_postprocess.AudioSegment") as MockAudio:
            MockAudio.from_file.side_effect = Exception("corrupt")
            result = apply_eq(audio)

        assert result == audio


# ── postprocess_tts_audio ─────────────────────────────────────────────────────


class TestPostprocessTtsAudio:
    def test_nonexistent_file_returns_path(self, tmp_path):
        audio = tmp_path / "nonexistent.mp3"
        result = postprocess_tts_audio(audio)
        assert result == audio

    def test_calls_normalize_and_eq(self, tmp_path):
        audio = tmp_path / "tts.mp3"
        audio.write_bytes(b"\x00")

        with (
            patch("shorts_maker_v2.render.audio_postprocess.normalize_audio", return_value=audio) as mock_norm,
            patch("shorts_maker_v2.render.audio_postprocess.apply_eq", return_value=audio) as mock_eq,
        ):
            result = postprocess_tts_audio(audio, voice_name="ko-KR-InJoon-Neural")

        mock_norm.assert_called_once_with(audio, -14.0)
        mock_eq.assert_called_once_with(audio, "male_voice")
        assert result == audio

    def test_skips_eq_when_no_voice_name(self, tmp_path):
        audio = tmp_path / "tts.mp3"
        audio.write_bytes(b"\x00")

        with (
            patch("shorts_maker_v2.render.audio_postprocess.normalize_audio", return_value=audio),
            patch("shorts_maker_v2.render.audio_postprocess.apply_eq") as mock_eq,
        ):
            postprocess_tts_audio(audio, voice_name="")

        mock_eq.assert_not_called()

    def test_skips_normalize_when_disabled(self, tmp_path):
        audio = tmp_path / "tts.mp3"
        audio.write_bytes(b"\x00")

        with (
            patch("shorts_maker_v2.render.audio_postprocess.normalize_audio") as mock_norm,
            patch("shorts_maker_v2.render.audio_postprocess.apply_eq", return_value=audio),
        ):
            postprocess_tts_audio(audio, voice_name="ko-KR-SunHi", normalize=False)

        mock_norm.assert_not_called()

    def test_skips_eq_when_disabled(self, tmp_path):
        audio = tmp_path / "tts.mp3"
        audio.write_bytes(b"\x00")

        with (
            patch("shorts_maker_v2.render.audio_postprocess.normalize_audio", return_value=audio),
            patch("shorts_maker_v2.render.audio_postprocess.apply_eq") as mock_eq,
        ):
            postprocess_tts_audio(audio, voice_name="ko-KR-SunHi", eq_enabled=False)

        mock_eq.assert_not_called()

    def test_custom_target_lufs(self, tmp_path):
        audio = tmp_path / "tts.mp3"
        audio.write_bytes(b"\x00")

        with (
            patch("shorts_maker_v2.render.audio_postprocess.normalize_audio", return_value=audio) as mock_norm,
            patch("shorts_maker_v2.render.audio_postprocess.apply_eq", return_value=audio),
        ):
            postprocess_tts_audio(audio, voice_name="", target_lufs=-16.0)

        mock_norm.assert_called_once_with(audio, -16.0)

    def test_calls_compression_and_reverb_by_default(self, tmp_path):
        audio = tmp_path / "tts.mp3"
        audio.write_bytes(b"\x00")

        with (
            patch("shorts_maker_v2.render.audio_postprocess.normalize_audio", return_value=audio),
            patch("shorts_maker_v2.render.audio_postprocess.apply_eq", return_value=audio),
            patch("shorts_maker_v2.render.audio_postprocess._apply_compression", return_value=audio) as mock_comp,
            patch("shorts_maker_v2.render.audio_postprocess._apply_subtle_reverb", return_value=audio) as mock_reverb,
        ):
            result = postprocess_tts_audio(audio, voice_name="ko-KR-SunHi")

        mock_comp.assert_called_once_with(audio)
        mock_reverb.assert_called_once_with(audio)
        assert result == audio

    def test_skips_compression_and_reverb_when_disabled(self, tmp_path):
        audio = tmp_path / "tts.mp3"
        audio.write_bytes(b"\x00")

        with (
            patch("shorts_maker_v2.render.audio_postprocess.normalize_audio", return_value=audio),
            patch("shorts_maker_v2.render.audio_postprocess.apply_eq", return_value=audio),
            patch("shorts_maker_v2.render.audio_postprocess._apply_compression") as mock_comp,
            patch("shorts_maker_v2.render.audio_postprocess._apply_subtle_reverb") as mock_reverb,
        ):
            result = postprocess_tts_audio(audio, voice_name="ko-KR-SunHi", compress=False, reverb=False)

        mock_comp.assert_not_called()
        mock_reverb.assert_not_called()
        assert result == audio


class _FakeChunk:
    def __init__(self, dbfs: float):
        self.dBFS = dbfs
        self.applied_gains: list[float] = []
        self.export_calls: list[tuple[str, str]] = []

    def apply_gain(self, gain: float):
        self.applied_gains.append(gain)
        return self

    def __add__(self, other):
        return self

    def export(self, path: str, format: str):
        self.export_calls.append((path, format))


class _FakeAudio:
    def __init__(self):
        self.frame_rate = 44100
        self.overlay_calls: list[tuple[object, object]] = []
        self.applied_gains: list[float] = []
        self.export_calls: list[tuple[str, str]] = []

    def __len__(self):
        return 100

    def __getitem__(self, item):
        return self

    def __add__(self, other):
        return self

    def apply_gain(self, gain: float):
        self.applied_gains.append(gain)
        return self

    def overlay(self, other, gain_during_overlay=None):
        self.overlay_calls.append((other, gain_during_overlay))
        return self

    def export(self, path: str, format: str):
        self.export_calls.append((path, format))


def _install_fake_pydub(
    monkeypatch,
    *,
    from_file_obj,
    silent_obj=None,
    high_pass_filter_fn=None,
    low_pass_filter_fn=None,
):
    fake_pydub = ModuleType("pydub")

    class FakeAudioSegment:
        @staticmethod
        def from_file(path: str, format: str | None = None):
            return from_file_obj

        @staticmethod
        def silent(duration: int = 0, frame_rate: int | None = None):
            if silent_obj is None:
                raise AssertionError("silent() should not be called in this test")
            return silent_obj

    fake_pydub.AudioSegment = FakeAudioSegment

    fake_effects = ModuleType("pydub.effects")
    fake_effects.high_pass_filter = high_pass_filter_fn or (lambda audio, low_freq: audio)
    fake_effects.low_pass_filter = low_pass_filter_fn or (lambda audio, high_freq: audio)

    monkeypatch.setitem(sys.modules, "pydub", fake_pydub)
    monkeypatch.setitem(sys.modules, "pydub.effects", fake_effects)


class TestCompressionAndReverb:
    def test_apply_compression_returns_path_when_pydub_missing(self, tmp_path):
        audio = tmp_path / "test.mp3"
        audio.write_bytes(b"\x00")

        with patch.dict("sys.modules", {"pydub": None}):
            result = _apply_compression(audio)

        assert result == audio

    def test_apply_compression_soft_limits_hot_chunks(self, tmp_path):
        pytest.importorskip("pydub")
        audio = tmp_path / "test.mp3"
        audio.write_bytes(b"\x00")

        chunks = [_FakeChunk(-10.0), _FakeChunk(-25.0)]
        fake_audio = MagicMock()
        fake_audio.__len__.return_value = 100
        fake_audio.__getitem__.side_effect = chunks

        with patch("shorts_maker_v2.render.audio_postprocess.AudioSegment") as MockAudio:
            MockAudio.from_file.return_value = fake_audio
            result = _apply_compression(audio, threshold_db=-20.0, ratio=3.0)

        assert result == audio
        assert chunks[0].applied_gains == [-6.666666666666667]
        assert chunks[1].applied_gains == []
        assert chunks[0].export_calls == [(str(audio), "mp3")]

    def test_apply_compression_falls_back_on_error(self, tmp_path):
        pytest.importorskip("pydub")
        audio = tmp_path / "bad.mp3"
        audio.write_bytes(b"\x00")

        with patch("shorts_maker_v2.render.audio_postprocess.AudioSegment") as MockAudio:
            MockAudio.from_file.side_effect = RuntimeError("broken")
            result = _apply_compression(audio)

        assert result == audio

    def test_apply_subtle_reverb_returns_path_when_pydub_missing(self, tmp_path):
        audio = tmp_path / "test.mp3"
        audio.write_bytes(b"\x00")

        with patch.dict("sys.modules", {"pydub": None}):
            result = _apply_subtle_reverb(audio)

        assert result == audio

    def test_apply_subtle_reverb_builds_overlay_and_exports(self, tmp_path):
        pytest.importorskip("pydub")
        audio = tmp_path / "test.mp3"
        audio.write_bytes(b"\x00")

        fake_audio = _FakeAudio()
        fake_delay = _FakeAudio()

        with patch("shorts_maker_v2.render.audio_postprocess.AudioSegment") as MockAudio:
            MockAudio.from_file.return_value = fake_audio
            MockAudio.silent.return_value = fake_delay
            result = _apply_subtle_reverb(audio)

        assert result == audio
        assert fake_audio.export_calls == [(str(audio), "mp3")]
        assert fake_audio.overlay_calls[0][1] is None
        assert fake_audio.overlay_calls[1][1] is None
        assert fake_delay.applied_gains == [-18, -22]

    def test_apply_subtle_reverb_falls_back_on_error(self, tmp_path):
        pytest.importorskip("pydub")
        audio = tmp_path / "bad.mp3"
        audio.write_bytes(b"\x00")

        with patch("shorts_maker_v2.render.audio_postprocess.AudioSegment") as MockAudio:
            MockAudio.from_file.side_effect = RuntimeError("broken")
            result = _apply_subtle_reverb(audio)

        assert result == audio


def test_normalize_audio_with_fake_pydub_module(monkeypatch, tmp_path):
    audio = tmp_path / "test.mp3"
    audio.write_bytes(b"\x00")

    mock_segment = MagicMock()
    mock_segment.dBFS = -30.0
    mock_normalized = MagicMock()
    mock_segment.apply_gain.return_value = mock_normalized
    _install_fake_pydub(monkeypatch, from_file_obj=mock_segment)

    result = normalize_audio(audio, target_lufs=-14.0)

    assert result == audio
    mock_segment.apply_gain.assert_called_once_with(16.0)
    mock_normalized.export.assert_called_once_with(str(audio), format="mp3")


def test_apply_eq_with_fake_pydub_module(monkeypatch, tmp_path):
    audio = tmp_path / "test.mp3"
    audio.write_bytes(b"\x00")

    mock_audio = MagicMock()
    mock_audio.overlay.return_value = mock_audio
    mock_band = MagicMock()
    mock_band.apply_gain.return_value = mock_band

    _install_fake_pydub(
        monkeypatch,
        from_file_obj=mock_audio,
        high_pass_filter_fn=lambda audio_obj, low_freq: mock_band,
        low_pass_filter_fn=lambda band_obj, high_freq: mock_band,
    )

    result = apply_eq(audio, preset="neutral")

    assert result == audio
    assert mock_band.apply_gain.call_count >= 1
    mock_audio.export.assert_called_once_with(str(audio), format="mp3")


def test_apply_compression_with_fake_pydub_module(monkeypatch, tmp_path):
    audio = tmp_path / "test.mp3"
    audio.write_bytes(b"\x00")

    chunks = [_FakeChunk(-10.0), _FakeChunk(-25.0)]
    fake_audio = MagicMock()
    fake_audio.__len__.return_value = 100
    fake_audio.__getitem__.side_effect = chunks
    _install_fake_pydub(monkeypatch, from_file_obj=fake_audio)

    result = _apply_compression(audio, threshold_db=-20.0, ratio=3.0)

    assert result == audio
    assert len(chunks[0].applied_gains) == 1
    assert abs(chunks[0].applied_gains[0] - (-6.666666666666667)) < 1e-9
    assert chunks[1].applied_gains == []
    assert chunks[0].export_calls == [(str(audio), "mp3")]


def test_apply_subtle_reverb_with_fake_pydub_module(monkeypatch, tmp_path):
    audio = tmp_path / "test.mp3"
    audio.write_bytes(b"\x00")

    fake_audio = _FakeAudio()
    fake_delay = _FakeAudio()
    _install_fake_pydub(monkeypatch, from_file_obj=fake_audio, silent_obj=fake_delay)

    result = _apply_subtle_reverb(audio)

    assert result == audio
    assert fake_audio.export_calls == [(str(audio), "mp3")]
    assert len(fake_audio.overlay_calls) == 2
    assert fake_delay.applied_gains == [-18, -22]
