from __future__ import annotations

import wave
from pathlib import Path

import pytest

from shorts_maker_v2.providers.google_music_client import (
    PcmAudioAccumulator,
    _parse_pcm_mime_type,
)


def test_parse_pcm_mime_type_reads_stream_metadata() -> None:
    rate, channels, sample_width = _parse_pcm_mime_type("audio/l16;rate=48000;channels=2")

    assert rate == 48000
    assert channels == 2
    assert sample_width == 2


def test_parse_pcm_mime_type_keeps_fallbacks_for_unknown_input() -> None:
    rate, channels, sample_width = _parse_pcm_mime_type(
        "audio/unknown",
        fallback_sample_rate_hz=44100,
        fallback_channels=1,
        fallback_sample_width_bytes=2,
    )

    assert rate == 44100
    assert channels == 1
    assert sample_width == 2


def test_pcm_audio_accumulator_marks_completion_from_byte_count() -> None:
    accumulator = PcmAudioAccumulator(target_duration_sec=1.0)

    accumulator.add_chunk(
        b"\x00" * (48000 * 2 * 2),
        mime_type="audio/l16;rate=48000;channels=2",
    )

    assert accumulator.is_complete
    assert accumulator.duration_sec == pytest.approx(1.0, rel=1e-3)


def test_pcm_audio_accumulator_writes_valid_wav(tmp_path: Path) -> None:
    accumulator = PcmAudioAccumulator(target_duration_sec=0.1)
    raw_pcm = b"\x00\x01" * 400
    accumulator.add_chunk(raw_pcm, mime_type="audio/l16;rate=8000;channels=1")

    output_path = accumulator.write_wav(tmp_path / "sample.wav")

    assert output_path.exists()
    with wave.open(str(output_path), "rb") as wav_file:
        assert wav_file.getframerate() == 8000
        assert wav_file.getnchannels() == 1
        assert wav_file.getsampwidth() == 2
        assert wav_file.readframes(wav_file.getnframes()) == raw_pcm
