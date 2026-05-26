"""audio_mixin._generate_audio 의 WhisperX 옵트인 경로 회귀 테스트.

T-19 해결을 위한 wiring 이 다음 계약을 지켜야 한다:
- config.audio.use_whisperx_alignment == False → 기존 동작 그대로 (whisperx 호출 0회)
- True + whisperx 미설치 → 기존 폴백 유지
- True + whisperx 성공 → _words.json 가 WhisperX 결과로 덮어쓰기, OpenAI Whisper 우회
- True + whisperx 실패 → 기존 OpenAI Whisper 폴백 동작
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from shorts_maker_v2.pipeline.media.audio_mixin import MediaAudioMixin


class _StubMixin(MediaAudioMixin):
    """audio_mixin._generate_audio 만 단독 호출하기 위한 최소 래퍼."""

    def __init__(self, config, openai_client=None):
        self.config = config
        self._tts_voice = "alloy"
        self.openai_client = openai_client
        self._channel_key = "test-channel"


def _make_config(*, use_whisperx: bool, sync_whisper: bool = False) -> SimpleNamespace:
    return SimpleNamespace(
        providers=SimpleNamespace(
            tts="openai",
            tts_voice_roles={},
        ),
        audio=SimpleNamespace(
            sync_with_whisper=sync_whisper,
            use_whisperx_alignment=use_whisperx,
            whisperx_model_size="base",
            whisperx_language="ko",
        ),
    )


def _patch_tts_factory(monkeypatch, audio_path: Path):
    audio_path.write_bytes(b"fake audio data")

    def _fake_generate_tts(**kwargs):
        return kwargs["output_path"]

    monkeypatch.setattr(
        "shorts_maker_v2.pipeline.media.audio_mixin.TTSFactory.generate_tts_with_fallback",
        _fake_generate_tts,
    )


def test_whisperx_disabled_keeps_existing_behavior_and_skips_module(monkeypatch, tmp_path):
    audio = tmp_path / "narration.wav"
    _patch_tts_factory(monkeypatch, audio)

    sentinel = {"called": False}

    def _trip(*args, **kwargs):
        sentinel["called"] = True
        return None

    monkeypatch.setattr("shorts_maker_v2.render.whisperx_aligner.align_audio_words", _trip)

    config = _make_config(use_whisperx=False)
    mixin = _StubMixin(config=config)

    result = mixin._generate_audio("안녕하세요", audio)

    assert result == audio
    assert sentinel["called"] is False  # whisperx 모듈은 호출조차 되지 않아야 한다
    assert not (audio.parent / f"{audio.stem}_words.json").exists()


def test_whisperx_enabled_but_unavailable_falls_back_silently(monkeypatch, tmp_path):
    audio = tmp_path / "narration.wav"
    _patch_tts_factory(monkeypatch, audio)

    monkeypatch.setattr("shorts_maker_v2.render.whisperx_aligner.is_available", lambda: False)
    align_calls = {"count": 0}

    def _align(*args, **kwargs):
        align_calls["count"] += 1
        return None

    monkeypatch.setattr("shorts_maker_v2.render.whisperx_aligner.align_audio_words", _align)

    config = _make_config(use_whisperx=True)
    mixin = _StubMixin(config=config)

    result = mixin._generate_audio("안녕하세요", audio)

    assert result == audio
    assert align_calls["count"] == 0  # is_available()=False → align 자체를 호출하지 않음


def test_whisperx_success_overwrites_words_json_and_skips_openai_whisper(monkeypatch, tmp_path):
    audio = tmp_path / "narration.wav"
    _patch_tts_factory(monkeypatch, audio)

    from shorts_maker_v2.render.karaoke import WordSegment

    monkeypatch.setattr("shorts_maker_v2.render.whisperx_aligner.is_available", lambda: True)
    monkeypatch.setattr(
        "shorts_maker_v2.render.whisperx_aligner.align_audio_words",
        lambda *a, **k: [
            WordSegment(word="안녕", start=0.0, end=0.5),
            WordSegment(word="세상", start=0.5, end=1.0),
        ],
    )

    openai_client = MagicMock()
    openai_client.transcribe_audio = MagicMock(side_effect=AssertionError("OpenAI Whisper 가 호출되면 안 된다"))

    # sync_with_whisper=True 라도 whisperx 성공 시 OpenAI 우회되어야 함
    config = _make_config(use_whisperx=True, sync_whisper=True)
    mixin = _StubMixin(config=config, openai_client=openai_client)

    result = mixin._generate_audio("안녕 세상", audio)

    words_json = audio.parent / f"{audio.stem}_words.json"
    assert result == audio
    assert words_json.exists()
    payload = json.loads(words_json.read_text(encoding="utf-8"))
    assert [w["word"] for w in payload] == ["안녕", "세상"]
    assert payload[1]["end"] == pytest.approx(1.0)
    openai_client.transcribe_audio.assert_not_called()


def test_whisperx_failure_falls_back_to_openai_whisper(monkeypatch, tmp_path):
    audio = tmp_path / "narration.wav"
    _patch_tts_factory(monkeypatch, audio)

    monkeypatch.setattr("shorts_maker_v2.render.whisperx_aligner.is_available", lambda: True)
    monkeypatch.setattr(
        "shorts_maker_v2.render.whisperx_aligner.align_audio_words",
        lambda *a, **k: None,  # 정렬 실패 시뮬레이션
    )

    openai_client = MagicMock()
    openai_client.transcribe_audio = MagicMock(return_value=[{"word": "오픈", "start": 0.0, "end": 0.3}])

    config = _make_config(use_whisperx=True, sync_whisper=True)
    mixin = _StubMixin(config=config, openai_client=openai_client)

    result = mixin._generate_audio("오픈", audio)

    words_json = audio.parent / f"{audio.stem}_words.json"
    assert result == audio
    assert words_json.exists()
    openai_client.transcribe_audio.assert_called_once_with(audio)
    payload = json.loads(words_json.read_text(encoding="utf-8"))
    assert payload[0]["word"] == "오픈"


def test_whisperx_internal_exception_does_not_break_pipeline(monkeypatch, tmp_path):
    audio = tmp_path / "narration.wav"
    _patch_tts_factory(monkeypatch, audio)

    def _explode():
        raise RuntimeError("synthetic")

    monkeypatch.setattr("shorts_maker_v2.render.whisperx_aligner.is_available", _explode)

    config = _make_config(use_whisperx=True, sync_whisper=False)
    mixin = _StubMixin(config=config)

    # 예외가 발생해도 audio_result 는 반환되어야 한다
    result = mixin._generate_audio("안녕", audio)
    assert result == audio
