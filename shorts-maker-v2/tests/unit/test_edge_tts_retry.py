from __future__ import annotations

import json
from pathlib import Path

from shorts_maker_v2.providers.edge_tts_client import EdgeTTSClient


def test_generate_tts_retries_after_no_audio(monkeypatch, tmp_path: Path) -> None:
    audio = tmp_path / "retry.mp3"
    words = tmp_path / "retry_words.json"
    calls = {"count": 0}

    async def fake_generate_with_timing(text, voice, rate, output_path, words_json_path):  # noqa: ANN001
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("No audio was received. Please verify that your parameters are correct.")
        output_path.write_bytes(b"audio")
        words_json_path.write_text(json.dumps([{"word": "GPT", "start": 0.0, "end": 0.4}]), encoding="utf-8")
        (words_json_path.parent / f"{words_json_path.stem}_ssml.txt").write_text(text, encoding="utf-8")

    monkeypatch.setattr(
        "shorts_maker_v2.providers.edge_tts_client._generate_async_with_timing",
        fake_generate_with_timing,
    )

    result = EdgeTTSClient().generate_tts(
        model="tts-1",
        voice="ko-KR-SoonBokNeural",
        speed=1.0,
        text="GPT가 다시 공개됐습니다",
        output_path=audio,
        words_json_path=words,
        role="body",
    )

    assert result == audio
    assert audio.exists()
    assert words.exists()
    assert calls["count"] >= 2
