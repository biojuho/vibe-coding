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

    @staticmethod
    def _scene_id_from_path(path):
        import re

        match = re.search(r"scene_(\d+)", Path(path).stem)
        return int(match.group(1)) if match else None


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


def test_generate_audio_raises_on_empty_narration(tmp_path):
    config = _make_config(use_whisperx=False)
    mixin = _StubMixin(config=config)
    audio = tmp_path / "narration.wav"

    with pytest.raises(ValueError, match="narration_ko must not be empty"):
        mixin._generate_audio("", audio, role="hook")

    with pytest.raises(ValueError, match="narration_ko must not be empty"):
        mixin._generate_audio("   ", audio, role="body")


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


# ── degraded_steps propagation ─────────────────────────────────────────────
# The lazy import inside _generate_audio goes through shorts_maker_v2.render.__init__
# which imports caption_pillow → PIL. We inject a fake module to avoid PIL entirely.

import sys
import types


def _inject_fake_whisperx(is_available_fn, align_fn=None, write_fn=None):
    """Return a context that injects a stub whisperx_aligner into sys.modules."""
    import contextlib

    @contextlib.contextmanager
    def _ctx():
        fake_render = types.ModuleType("shorts_maker_v2.render")
        fake_aligner = types.ModuleType("shorts_maker_v2.render.whisperx_aligner")
        fake_aligner.is_available = is_available_fn
        fake_aligner.align_audio_words = align_fn or (lambda *a, **kw: [])
        fake_aligner.write_words_json = write_fn or (lambda *a, **kw: None)

        old_render = sys.modules.get("shorts_maker_v2.render")
        old_aligner = sys.modules.get("shorts_maker_v2.render.whisperx_aligner")
        sys.modules["shorts_maker_v2.render"] = fake_render
        sys.modules["shorts_maker_v2.render.whisperx_aligner"] = fake_aligner
        try:
            yield
        finally:
            if old_render is None:
                sys.modules.pop("shorts_maker_v2.render", None)
            else:
                sys.modules["shorts_maker_v2.render"] = old_render
            if old_aligner is None:
                sys.modules.pop("shorts_maker_v2.render.whisperx_aligner", None)
            else:
                sys.modules["shorts_maker_v2.render.whisperx_aligner"] = old_aligner

    return _ctx()


def test_whisperx_failure_appends_to_pending_audio_warnings(tmp_path, monkeypatch):
    """WhisperX 정렬 실패 시 _pending_audio_warnings 에 기록되어야 한다."""
    audio = tmp_path / "scene_02.mp3"
    _patch_tts_factory(monkeypatch, audio)

    def _explode():
        raise RuntimeError("GPU OOM")

    with _inject_fake_whisperx(is_available_fn=_explode):
        config = _make_config(use_whisperx=True, sync_whisper=False)
        mixin = _StubMixin(config=config)
        mixin._pending_audio_warnings = []

        result = mixin._generate_audio("안녕하세요 오늘도 좋은 하루", audio)

    assert result == audio
    assert len(mixin._pending_audio_warnings) == 1
    warn = mixin._pending_audio_warnings[0]
    assert warn["step"] == "whisperx_align"
    assert warn["error_type"] == "sync_loss"
    assert "GPU OOM" in warn["message"]


def test_whisper_sync_failure_appends_to_pending_audio_warnings(tmp_path, monkeypatch):
    """Whisper word-sync 실패 시 _pending_audio_warnings 에 기록되어야 한다."""
    audio = tmp_path / "scene_03.mp3"
    _patch_tts_factory(monkeypatch, audio)

    fake_client = MagicMock()
    fake_client.transcribe_audio.side_effect = ConnectionError("timeout")

    config = _make_config(use_whisperx=False, sync_whisper=True)
    mixin = _StubMixin(config=config, openai_client=fake_client)
    mixin._pending_audio_warnings = []

    result = mixin._generate_audio("안녕하세요 오늘도 좋은 하루", audio)

    assert result == audio
    assert len(mixin._pending_audio_warnings) == 1
    warn = mixin._pending_audio_warnings[0]
    assert warn["step"] == "whisper_sync"
    assert warn["error_type"] == "sync_loss"
    assert "timeout" in warn["message"]


def test_no_pending_warnings_attr_does_not_crash(tmp_path, monkeypatch):
    """_pending_audio_warnings 속성이 없는 경우도 안전하게 폴백해야 한다."""
    audio = tmp_path / "scene_01.mp3"
    _patch_tts_factory(monkeypatch, audio)

    def _explode():
        raise RuntimeError("no GPU")

    with _inject_fake_whisperx(is_available_fn=_explode):
        config = _make_config(use_whisperx=True, sync_whisper=False)
        mixin = _StubMixin(config=config)
        # deliberately NOT setting _pending_audio_warnings — tests getattr guard
        result = mixin._generate_audio("안녕하세요 오늘도 좋은 하루", audio)

    assert result == audio  # must not raise
