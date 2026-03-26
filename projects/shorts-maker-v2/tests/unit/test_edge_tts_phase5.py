from __future__ import annotations

import asyncio
import json
import types
from pathlib import Path
from unittest.mock import patch

import pytest

from shorts_maker_v2.providers.edge_tts_client import (
    EdgeTTSClient,
    _add_silence_padding,
    _generate_async,
    _generate_async_with_timing,
)


def test_add_silence_padding_success(tmp_path: Path) -> None:
    audio = tmp_path / "audio.mp3"
    audio.write_bytes(b"original")

    class FakeSegment:
        def __init__(self, frame_rate: int = 44100):
            self.frame_rate = frame_rate

        def __add__(self, other):  # noqa: ANN001
            return self

        def export(self, path: str, format: str) -> None:
            Path(path).write_bytes(f"padded-{format}".encode())

    fake_pydub = types.ModuleType("pydub")
    fake_pydub.AudioSegment = types.SimpleNamespace(
        from_file=lambda _: FakeSegment(),
        silent=lambda duration, frame_rate: FakeSegment(frame_rate=frame_rate),
    )

    with patch.dict("sys.modules", {"pydub": fake_pydub}):
        _add_silence_padding(audio)

    assert audio.read_bytes() == b"padded-mp3"


def test_generate_async_saves_audio_and_applies_padding(tmp_path: Path) -> None:
    audio = tmp_path / "async.mp3"

    class FakeCommunicate:
        def __init__(self, text: str, voice: str, rate: str, pitch: str):
            self.args = (text, voice, rate, pitch)

        async def save(self, path: str) -> None:
            Path(path).write_bytes(b"edge-audio")

    with (
        patch("shorts_maker_v2.providers.edge_tts_client.edge_tts.Communicate", FakeCommunicate),
        patch("shorts_maker_v2.providers.edge_tts_client._add_silence_padding") as pad,
    ):
        asyncio.run(_generate_async("hello", "ko-KR-SunHiNeural", "+0%", "+0Hz", audio))

    assert audio.read_bytes() == b"edge-audio"
    pad.assert_called_once_with(audio)


def test_generate_async_with_timing_saves_shifted_word_boundaries(tmp_path: Path) -> None:
    audio = tmp_path / "timed.mp3"
    words = tmp_path / "timed_words.json"

    class FakeCommunicate:
        def __init__(self, text: str, voice: str, rate: str, pitch: str):
            self.args = (text, voice, rate, pitch)

        async def stream(self):
            yield {"type": "audio", "data": b"abc"}
            yield {"type": "WordBoundary", "offset": 0, "duration": 1_000_000, "text": "hello"}
            yield {"type": "audio", "data": b"def"}

    with (
        patch("shorts_maker_v2.providers.edge_tts_client.edge_tts.Communicate", FakeCommunicate),
        patch("shorts_maker_v2.providers.edge_tts_client._add_silence_padding") as pad,
    ):
        asyncio.run(
            _generate_async_with_timing(
                "hello",
                "ko-KR-SunHiNeural",
                "+0%",
                "+0Hz",
                audio,
                words,
            )
        )

    assert audio.read_bytes() == b"abcdef"
    assert json.loads(words.read_text(encoding="utf-8")) == [{"word": "hello", "start": 0.05, "end": 0.15}]
    assert (tmp_path / "timed_words_ssml.txt").read_text(encoding="utf-8") == "hello"
    pad.assert_called_once_with(audio)


def test_generate_async_with_timing_uses_whisper_fallback_when_no_word_boundaries(tmp_path: Path) -> None:
    audio = tmp_path / "whisper.mp3"
    words = tmp_path / "whisper_words.json"

    class FakeCommunicate:
        def __init__(self, text: str, voice: str, rate: str, pitch: str):
            self.args = (text, voice, rate, pitch)

        async def stream(self):
            yield {"type": "audio", "data": b"audio"}

    whisper_words = [{"word": "테스트", "start": 0.0, "end": 0.2}]

    with (
        patch("shorts_maker_v2.providers.edge_tts_client.edge_tts.Communicate", FakeCommunicate),
        patch("shorts_maker_v2.providers.edge_tts_client._add_silence_padding"),
        patch("shorts_maker_v2.providers.whisper_aligner.is_whisper_available", return_value=True),
        patch("shorts_maker_v2.providers.whisper_aligner.transcribe_to_word_timings", return_value=whisper_words),
    ):
        asyncio.run(
            _generate_async_with_timing(
                "테스트",
                "ko-KR-SunHiNeural",
                "+0%",
                "+0Hz",
                audio,
                words,
            )
        )

    assert json.loads(words.read_text(encoding="utf-8")) == [{"word": "테스트", "start": 0.05, "end": 0.25}]


def test_generate_async_with_timing_uses_approximate_fallback_when_whisper_empty(tmp_path: Path) -> None:
    audio = tmp_path / "approx.mp3"
    words = tmp_path / "approx_words.json"

    class FakeCommunicate:
        def __init__(self, text: str, voice: str, rate: str, pitch: str):
            self.args = (text, voice, rate, pitch)

        async def stream(self):
            yield {"type": "audio", "data": b"audio"}

    approx_words = [{"word": "approx", "start": 0.1, "end": 0.4}]

    with (
        patch("shorts_maker_v2.providers.edge_tts_client.edge_tts.Communicate", FakeCommunicate),
        patch("shorts_maker_v2.providers.edge_tts_client._add_silence_padding"),
        patch("shorts_maker_v2.providers.whisper_aligner.is_whisper_available", return_value=False),
        patch("shorts_maker_v2.providers.edge_tts_client._approximate_word_timings", return_value=approx_words),
    ):
        asyncio.run(
            _generate_async_with_timing(
                "approx",
                "ko-KR-SunHiNeural",
                "+0%",
                "+0Hz",
                audio,
                words,
            )
        )

    assert json.loads(words.read_text(encoding="utf-8")) == [{"word": "approx", "start": 0.15, "end": 0.45}]


def test_generate_tts_uses_plain_async_path_when_words_json_path_is_missing(tmp_path: Path) -> None:
    audio = tmp_path / "plain.mp3"

    async def fake_generate(text, voice, rate, pitch, output_path):  # noqa: ANN001
        output_path.write_bytes(b"plain-audio")

    with patch("shorts_maker_v2.providers.edge_tts_client._generate_async", side_effect=fake_generate) as generate:
        result = EdgeTTSClient().generate_tts(
            model="tts-1",
            voice="alloy",
            speed=1.0,
            text="plain",
            output_path=audio,
            role="hook",
            channel_key="ai_tech",
        )

    assert result == audio
    assert audio.read_bytes() == b"plain-audio"
    assert generate.call_count == 1
    assert generate.call_args.args[1] == "ko-KR-SunHiNeural"


def test_generate_tts_preserves_neural_voice_without_remapping(tmp_path: Path) -> None:
    audio = tmp_path / "passthrough.mp3"

    async def fake_generate(text, voice, rate, pitch, output_path):  # noqa: ANN001
        output_path.write_bytes(b"audio")

    with patch("shorts_maker_v2.providers.edge_tts_client._generate_async", side_effect=fake_generate) as generate:
        EdgeTTSClient().generate_tts(
            model="tts-1",
            voice="ko-KR-SoonBokNeural",
            speed=1.0,
            text="테스트",
            output_path=audio,
        )

    assert generate.call_args.args[1] == "ko-KR-SoonBokNeural"


def test_generate_tts_falls_back_to_default_voice_after_primary_failure(tmp_path: Path) -> None:
    audio = tmp_path / "fallback.mp3"
    words = tmp_path / "fallback_words.json"
    attempted_voices: list[str] = []

    async def fake_generate(text, voice, rate, pitch, output_path, words_json_path, language):  # noqa: ANN001
        attempted_voices.append(voice)
        if len(attempted_voices) == 1:
            output_path.write_bytes(b"broken")
            words_json_path.write_text("[]", encoding="utf-8")
            (words_json_path.parent / f"{words_json_path.stem}_ssml.txt").write_text("temp", encoding="utf-8")
            raise RuntimeError("primary failed")
        output_path.write_bytes(b"ok")
        words_json_path.write_text(json.dumps([{"word": "ok", "start": 0.0, "end": 0.1}]), encoding="utf-8")
        (words_json_path.parent / f"{words_json_path.stem}_ssml.txt").write_text(text, encoding="utf-8")

    with patch("shorts_maker_v2.providers.edge_tts_client._generate_async_with_timing", side_effect=fake_generate):
        result = EdgeTTSClient().generate_tts(
            model="tts-1",
            voice="ko-KR-SoonBokNeural",
            speed=1.0,
            text="fallback",
            output_path=audio,
            words_json_path=words,
        )

    assert result == audio
    assert attempted_voices == ["ko-KR-SoonBokNeural", "ko-KR-SunHiNeural"]
    assert audio.read_bytes() == b"ok"
    assert words.exists()


def test_generate_tts_cleans_temp_files_when_all_attempts_fail(tmp_path: Path) -> None:
    audio = tmp_path / "failed.mp3"
    words = tmp_path / "failed_words.json"
    attempted_voices: list[str] = []

    async def fake_generate(text, voice, rate, pitch, output_path, words_json_path, language):  # noqa: ANN001
        attempted_voices.append(voice)
        output_path.write_bytes(b"broken")
        words_json_path.write_text("[]", encoding="utf-8")
        (words_json_path.parent / f"{words_json_path.stem}_ssml.txt").write_text(text, encoding="utf-8")
        raise RuntimeError("still broken")

    with (
        patch("shorts_maker_v2.providers.edge_tts_client._generate_async_with_timing", side_effect=fake_generate),
        pytest.raises(RuntimeError, match="still broken"),
    ):
            EdgeTTSClient().generate_tts(
                model="tts-1",
                voice="ko-KR-SoonBokNeural",
                speed=1.0,
                text="cleanup",
                output_path=audio,
                words_json_path=words,
            )

    assert attempted_voices == ["ko-KR-SoonBokNeural", "ko-KR-SunHiNeural"]
    assert not audio.exists()
    assert not words.exists()
    assert not (tmp_path / "failed_words_ssml.txt").exists()
