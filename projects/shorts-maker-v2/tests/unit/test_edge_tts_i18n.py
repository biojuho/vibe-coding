from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from shorts_maker_v2.providers.edge_tts_client import (
    EdgeTTSClient,
    _generate_async_with_timing,
    _load_edge_tts_locale_bundle,
    _resolve_edge_voice,
)


def test_load_edge_tts_locale_bundle_reads_ko_kr_yaml() -> None:
    bundle = _load_edge_tts_locale_bundle("ko-KR")

    assert bundle["default_voice"] == "ko-KR-SunHiNeural"
    assert bundle["openai_to_edge_voice"]["sage"] == "ko-KR-HyunsuNeural"


def test_load_edge_tts_locale_bundle_reads_en_us_yaml() -> None:
    bundle = _load_edge_tts_locale_bundle("en-US")

    assert bundle["default_voice"] == "en-US-JennyNeural"
    assert bundle["openai_to_edge_voice"]["ash"] == "en-US-BrianNeural"


def test_resolve_edge_voice_uses_language_specific_mapping() -> None:
    custom_bundle = {
        "default_voice": "en-US-AvaNeural",
        "openai_to_edge_voice": {
            "alloy": "en-US-JennyNeural",
        },
    }

    with patch("shorts_maker_v2.providers.edge_tts_client._load_edge_tts_locale_bundle", return_value=custom_bundle):
        resolved_voice, default_voice = _resolve_edge_voice("alloy", "en-US")

    assert resolved_voice == "en-US-JennyNeural"
    assert default_voice == "en-US-AvaNeural"


def test_generate_tts_falls_back_to_language_specific_default_voice(tmp_path: Path) -> None:
    audio = tmp_path / "edge_i18n.mp3"
    words = tmp_path / "edge_i18n_words.json"
    attempted_voices: list[str] = []
    custom_bundle = {
        "default_voice": "en-US-AvaNeural",
        "openai_to_edge_voice": {
            "alloy": "en-US-JennyNeural",
        },
    }

    async def fake_generate(text, voice, rate, pitch, output_path, words_json_path, language):  # noqa: ANN001
        attempted_voices.append(voice)
        if len(attempted_voices) == 1:
            output_path.write_bytes(b"broken")
            words_json_path.write_text("[]", encoding="utf-8")
            (words_json_path.parent / f"{words_json_path.stem}_ssml.txt").write_text(text, encoding="utf-8")
            raise RuntimeError("primary failed")
        output_path.write_bytes(b"ok")
        words_json_path.write_text(json.dumps([{"word": "ok", "start": 0.0, "end": 0.1}]), encoding="utf-8")
        (words_json_path.parent / f"{words_json_path.stem}_ssml.txt").write_text(text, encoding="utf-8")

    with (
        patch("shorts_maker_v2.providers.edge_tts_client._load_edge_tts_locale_bundle", return_value=custom_bundle),
        patch("shorts_maker_v2.providers.edge_tts_client._generate_async_with_timing", side_effect=fake_generate),
    ):
        result = EdgeTTSClient().generate_tts(
            model="tts-1",
            voice="alloy",
            speed=1.0,
            text="fallback",
            output_path=audio,
            words_json_path=words,
            language="en-US",
        )

    assert result == audio
    assert attempted_voices == ["en-US-JennyNeural", "en-US-AvaNeural"]
    assert audio.read_bytes() == b"ok"


def test_generate_async_with_timing_passes_language_to_whisper_fallback(tmp_path: Path) -> None:
    audio = tmp_path / "timing.mp3"
    words = tmp_path / "timing_words.json"

    class FakeCommunicate:
        def __init__(self, text: str, voice: str, rate: str, pitch: str):
            self.args = (text, voice, rate, pitch)

        async def stream(self):
            yield {"type": "audio", "data": b"audio"}

    whisper_words = [{"word": "hello", "start": 0.0, "end": 0.2}]

    with (
        patch("shorts_maker_v2.providers.edge_tts_client.edge_tts.Communicate", FakeCommunicate),
        patch("shorts_maker_v2.providers.edge_tts_client._add_silence_padding"),
        patch("shorts_maker_v2.providers.whisper_aligner.is_whisper_available", return_value=True),
        patch(
            "shorts_maker_v2.providers.whisper_aligner.transcribe_to_word_timings", return_value=whisper_words
        ) as transcribe,
    ):
        import asyncio

        asyncio.run(
            _generate_async_with_timing(
                "hello",
                "en-US-JennyNeural",
                "+0%",
                "+0Hz",
                audio,
                words,
                "en-US",
            )
        )

    assert transcribe.call_args.kwargs["language"] == "en-US"
