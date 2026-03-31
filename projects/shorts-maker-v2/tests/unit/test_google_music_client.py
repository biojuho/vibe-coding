from __future__ import annotations

import asyncio
import wave
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from shorts_maker_v2.providers.google_music_client import (
    GoogleMusicClient,
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


class _AsyncConnectContext:
    def __init__(self, session: object) -> None:
        self._session = session

    async def __aenter__(self) -> object:
        return self._session

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False


def _make_client(session: object | None = None, request_timeout_sec: int = 5) -> GoogleMusicClient:
    client = object.__new__(GoogleMusicClient)
    if session is None:
        session = SimpleNamespace()
    client.client = SimpleNamespace(
        aio=SimpleNamespace(
            live=SimpleNamespace(
                music=SimpleNamespace(
                    connect=lambda **_: _AsyncConnectContext(session),
                )
            )
        )
    )
    client.request_timeout_sec = request_timeout_sec
    return client


def _make_session(messages: list[object]) -> SimpleNamespace:
    async def _receive():
        for message in messages:
            yield message

    return SimpleNamespace(
        set_weighted_prompts=AsyncMock(),
        set_music_generation_config=AsyncMock(),
        play=AsyncMock(),
        stop=AsyncMock(),
        receive=_receive,
    )


def test_parse_pcm_mime_type_reads_bitdepth_override() -> None:
    rate, channels, sample_width = _parse_pcm_mime_type(
        "audio/pcm; rate=16000; channels=1; bitdepth=24",
        fallback_sample_width_bytes=2,
    )

    assert rate == 16000
    assert channels == 1
    assert sample_width == 3


def test_pcm_audio_accumulator_ignores_empty_chunk_but_updates_format() -> None:
    accumulator = PcmAudioAccumulator(target_duration_sec=0.1)

    accumulator.add_chunk(b"", mime_type="audio/l24;rate=16000;channels=1")

    assert accumulator.byte_count == 0
    assert accumulator.sample_rate_hz == 16000
    assert accumulator.channels == 1
    assert accumulator.sample_width_bytes == 3


def test_pcm_audio_accumulator_returns_zero_duration_for_invalid_format() -> None:
    accumulator = PcmAudioAccumulator(target_duration_sec=0.1, sample_rate_hz=0)

    assert accumulator.duration_sec == 0.0


def test_google_music_client_requires_api_key() -> None:
    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        GoogleMusicClient(api_key="")


@patch.dict("os.environ", {}, clear=True)
def test_google_music_client_from_env_requires_key() -> None:
    with pytest.raises(OSError, match="GEMINI_API_KEY"):
        GoogleMusicClient.from_env()


@patch.dict("os.environ", {"TEST_GEMINI_KEY": "secret"}, clear=True)
@patch("shorts_maker_v2.providers.google_music_client.genai.Client")
def test_google_music_client_from_env_uses_requested_env_key(mock_client: MagicMock) -> None:
    client = GoogleMusicClient.from_env(
        env_key="TEST_GEMINI_KEY",
        request_timeout_sec=17,
        api_version="v9",
    )

    mock_client.assert_called_once_with(api_key="secret", http_options={"api_version": "v9"})
    assert client.request_timeout_sec == 17


def test_generate_music_file_returns_existing_output(tmp_path: Path) -> None:
    output_path = tmp_path / "existing.wav"
    output_path.write_bytes(b"already-generated")
    client = _make_client()

    result = asyncio.run(
        client.generate_music_file(
            prompt="ambient synth",
            output_path=output_path,
        )
    )

    assert result == output_path


def test_generate_music_file_validates_arguments(tmp_path: Path) -> None:
    client = _make_client()

    with pytest.raises(ValueError, match="prompt"):
        asyncio.run(client.generate_music_file(prompt="   ", output_path=tmp_path / "a.wav"))
    with pytest.raises(ValueError, match="duration_sec"):
        asyncio.run(client.generate_music_file(prompt="ok", output_path=tmp_path / "a.wav", duration_sec=0))
    with pytest.raises(ValueError, match="bpm"):
        asyncio.run(client.generate_music_file(prompt="ok", output_path=tmp_path / "a.wav", bpm=0))
    with pytest.raises(ValueError, match=r"\.wav or \.mp3"):
        asyncio.run(client.generate_music_file(prompt="ok", output_path=tmp_path / "a.ogg"))


def test_receive_until_complete_skips_empty_messages_and_stops_when_complete() -> None:
    chunk = b"\x01" * 192
    session = _make_session(
        [
            SimpleNamespace(server_content=None),
            SimpleNamespace(server_content=SimpleNamespace(audio_chunks=[])),
            SimpleNamespace(
                server_content=SimpleNamespace(
                    audio_chunks=[SimpleNamespace(data=chunk, mime_type="audio/l16;rate=48000;channels=2")]
                )
            ),
        ]
    )
    client = _make_client()
    accumulator = PcmAudioAccumulator(target_duration_sec=0.001)

    asyncio.run(client._receive_until_complete(session=session, accumulator=accumulator))

    assert accumulator.is_complete
    assert accumulator.byte_count == len(chunk)


def test_generate_music_file_writes_wav_and_stops_session(tmp_path: Path) -> None:
    chunk = b"\x02" * 192
    session = _make_session(
        [
            SimpleNamespace(
                server_content=SimpleNamespace(
                    audio_chunks=[SimpleNamespace(data=chunk, mime_type="audio/l16;rate=48000;channels=2")]
                )
            )
        ]
    )
    client = _make_client(session=session)
    output_path = tmp_path / "generated.wav"

    result = asyncio.run(
        client.generate_music_file(
            prompt="clean piano loop",
            output_path=output_path,
            duration_sec=0.001,
            bpm=96,
        )
    )

    assert result == output_path
    assert output_path.exists()
    assert session.play.await_count == 1
    assert session.stop.await_count == 1


def test_generate_music_file_raises_when_stream_has_no_audio(tmp_path: Path) -> None:
    session = _make_session([SimpleNamespace(server_content=SimpleNamespace(audio_chunks=[]))])
    client = _make_client(session=session)

    with pytest.raises(RuntimeError, match="no audio chunks"):
        asyncio.run(
            client.generate_music_file(
                prompt="silent track",
                output_path=tmp_path / "silent.wav",
                duration_sec=0.001,
            )
        )

    assert session.stop.await_count == 1


def test_generate_music_file_transcodes_mp3_and_removes_intermediate_wav(tmp_path: Path) -> None:
    chunk = b"\x03" * 192
    session = _make_session(
        [
            SimpleNamespace(
                server_content=SimpleNamespace(
                    audio_chunks=[SimpleNamespace(data=chunk, mime_type="audio/l16;rate=48000;channels=2")]
                )
            )
        ]
    )
    client = _make_client(session=session)
    output_path = tmp_path / "generated.mp3"

    def _fake_transcode(*, wav_path: Path, mp3_path: Path) -> Path:
        assert wav_path.exists()
        mp3_path.write_bytes(b"mp3")
        return mp3_path

    with patch.object(GoogleMusicClient, "_transcode_wav_to_mp3", side_effect=_fake_transcode):
        result = asyncio.run(
            client.generate_music_file(
                prompt="uplifting beat",
                output_path=output_path,
                duration_sec=0.001,
            )
        )

    assert result == output_path
    assert output_path.exists()
    assert not output_path.with_suffix(".wav").exists()


@patch("shorts_maker_v2.providers.google_music_client.shutil.which", return_value=None)
def test_transcode_wav_to_mp3_requires_ffmpeg(mock_which: MagicMock, tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="ffmpeg is required"):
        GoogleMusicClient._transcode_wav_to_mp3(
            wav_path=tmp_path / "input.wav",
            mp3_path=tmp_path / "output.mp3",
        )


@patch("shorts_maker_v2.providers.google_music_client.shutil.which", return_value="ffmpeg")
@patch("shorts_maker_v2.providers.google_music_client.subprocess.run")
def test_transcode_wav_to_mp3_raises_when_output_missing(
    mock_run: MagicMock,
    mock_which: MagicMock,
    tmp_path: Path,
) -> None:
    wav_path = tmp_path / "input.wav"
    wav_path.write_bytes(b"fake-wav")

    with pytest.raises(RuntimeError, match="produced no mp3 output"):
        GoogleMusicClient._transcode_wav_to_mp3(
            wav_path=wav_path,
            mp3_path=tmp_path / "output.mp3",
        )

    mock_run.assert_called_once()


@patch("shorts_maker_v2.providers.google_music_client.shutil.which", return_value="ffmpeg")
@patch("shorts_maker_v2.providers.google_music_client.subprocess.run")
def test_transcode_wav_to_mp3_writes_output(
    mock_run: MagicMock,
    mock_which: MagicMock,
    tmp_path: Path,
) -> None:
    wav_path = tmp_path / "input.wav"
    wav_path.write_bytes(b"fake-wav")
    mp3_path = tmp_path / "output.mp3"

    def _run_side_effect(*args, **kwargs) -> None:
        mp3_path.write_bytes(b"fake-mp3")

    mock_run.side_effect = _run_side_effect

    result = GoogleMusicClient._transcode_wav_to_mp3(
        wav_path=wav_path,
        mp3_path=mp3_path,
    )

    assert result == mp3_path
    assert mp3_path.exists()
    assert mock_run.call_args.kwargs["check"] is True
