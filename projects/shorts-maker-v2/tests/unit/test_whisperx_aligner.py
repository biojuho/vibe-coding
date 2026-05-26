"""WhisperX 단어-레벨 정렬 모듈 회귀 테스트.

WhisperX 가 미설치된 환경(현재 로컬)에서도 안전하게 동작해야 한다.
- is_available() 캐시 동작
- align_audio_words 가 미설치 시 None 반환
- 정상 정렬 결과 → WordSegment 리스트 정규화
- 예외 발생 시 None (caller 폴백 유지)
- 빈/잘못된 입력 sanitization
"""

from __future__ import annotations

import json
import sys
import types

import pytest

from shorts_maker_v2.render.karaoke import WordSegment
from shorts_maker_v2.render.whisperx_aligner import (
    _word_segments_from_whisperx,
    align_audio_words,
    is_available,
    reset_availability_cache,
    write_words_json,
)


@pytest.fixture(autouse=True)
def _reset_cache():
    reset_availability_cache()
    yield
    reset_availability_cache()


def _install_fake_whisperx(monkeypatch, *, transcribe_segments, aligned_segments, raise_on=None):
    """가짜 whisperx 모듈을 sys.modules 에 주입."""
    fake = types.ModuleType("whisperx")
    state = {"calls": []}

    class _FakeWhisperModel:
        def transcribe(self, audio_path, language="ko"):  # noqa: ARG002
            state["calls"].append(("transcribe", audio_path, language))
            if raise_on == "transcribe":
                raise RuntimeError("synthetic transcribe failure")
            return {"segments": transcribe_segments, "language": language}

    def load_model(model_size, device="cpu", compute_type="int8", language="ko"):  # noqa: ARG001
        state["calls"].append(("load_model", model_size, device, compute_type, language))
        if raise_on == "load_model":
            raise RuntimeError("synthetic load_model failure")
        return _FakeWhisperModel()

    def load_align_model(language_code="ko", device="cpu"):  # noqa: ARG001
        state["calls"].append(("load_align_model", language_code, device))
        if raise_on == "load_align_model":
            raise RuntimeError("synthetic load_align_model failure")
        return ("align_model_stub", {"language_code": language_code})

    def align(  # noqa: D401
        segments, align_model, metadata, audio_path, device="cpu", return_char_alignments=False
    ):
        state["calls"].append(("align", len(segments), align_model, audio_path, device, return_char_alignments))
        if raise_on == "align":
            raise RuntimeError("synthetic align failure")
        return {"segments": aligned_segments}

    fake.load_model = load_model
    fake.load_align_model = load_align_model
    fake.align = align
    monkeypatch.setitem(sys.modules, "whisperx", fake)
    reset_availability_cache()
    return state


def test_is_available_returns_false_when_module_missing(monkeypatch):
    monkeypatch.setitem(sys.modules, "whisperx", None)
    reset_availability_cache()
    assert is_available() is False


def test_is_available_caches_result_between_calls(monkeypatch):
    monkeypatch.setitem(sys.modules, "whisperx", None)
    reset_availability_cache()
    first = is_available()
    monkeypatch.setitem(sys.modules, "whisperx", types.ModuleType("whisperx"))
    # 캐시되어 있으므로 모듈 주입 후에도 첫 결과 유지
    assert is_available() == first
    reset_availability_cache()
    # 캐시 리셋 후에는 새 모듈이 보임
    assert is_available() is True


def test_align_audio_words_returns_none_when_whisperx_missing(monkeypatch, tmp_path):
    monkeypatch.setitem(sys.modules, "whisperx", None)
    reset_availability_cache()
    audio = tmp_path / "fake.wav"
    audio.write_bytes(b"fake audio")
    assert align_audio_words(audio, "안녕하세요 좋은 아침이에요") is None


def test_align_audio_words_returns_none_when_audio_missing(monkeypatch, tmp_path):
    _install_fake_whisperx(monkeypatch, transcribe_segments=[], aligned_segments=[])
    missing = tmp_path / "does_not_exist.wav"
    assert align_audio_words(missing, "안녕") is None


def test_align_audio_words_normalizes_whisperx_output(monkeypatch, tmp_path):
    audio = tmp_path / "narration.wav"
    audio.write_bytes(b"fake")

    aligned_segments = [
        {
            "words": [
                {"word": "안녕", "start": 0.0, "end": 0.5},
                {"word": "  ", "start": 0.5, "end": 0.6},  # 공백 토큰 → 스킵
                {"word": "좋은", "start": 0.6, "end": 0.9},
                {"word": "아침", "start": 0.9, "end": 1.4},
                # end <= start → 스킵
                {"word": "이에요", "start": 1.4, "end": 1.4},
                # start None → 스킵
                {"word": "추가", "start": None, "end": 2.0},
                # 잘못된 타입 → 스킵
                {"word": "이상", "start": "abc", "end": "def"},
            ]
        }
    ]
    _install_fake_whisperx(monkeypatch, transcribe_segments=[{"text": "안녕"}], aligned_segments=aligned_segments)

    words = align_audio_words(audio, "안녕 좋은 아침이에요", language="ko")

    assert words is not None
    assert len(words) == 3
    assert [w.word for w in words] == ["안녕", "좋은", "아침"]
    assert words[0].start == 0.0
    assert words[1].end == 0.9


def test_align_audio_words_returns_none_when_no_words_after_filter(monkeypatch, tmp_path):
    audio = tmp_path / "n.wav"
    audio.write_bytes(b"fake")
    _install_fake_whisperx(
        monkeypatch,
        transcribe_segments=[{"text": ""}],
        aligned_segments=[{"words": [{"word": "  ", "start": 0, "end": 1}]}],
    )
    assert align_audio_words(audio, "안녕") is None


@pytest.mark.parametrize("raise_stage", ["load_model", "transcribe", "load_align_model", "align"])
def test_align_audio_words_swallows_exceptions(monkeypatch, tmp_path, raise_stage):
    audio = tmp_path / "n.wav"
    audio.write_bytes(b"fake")
    _install_fake_whisperx(
        monkeypatch,
        transcribe_segments=[{"text": "안녕"}],
        aligned_segments=[{"words": [{"word": "안녕", "start": 0, "end": 1}]}],
        raise_on=raise_stage,
    )
    # 어떤 단계에서 실패해도 caller 폴백을 위해 None 을 리턴해야 한다
    assert align_audio_words(audio, "안녕") is None


def test_word_segments_from_whisperx_handles_garbage_input():
    assert _word_segments_from_whisperx(None) == []
    assert _word_segments_from_whisperx({"segments": "nope"}) == []
    assert _word_segments_from_whisperx({"segments": [None, 42, "string"]}) == []
    assert _word_segments_from_whisperx({"segments": [{"words": "not-a-list"}]}) == []
    assert _word_segments_from_whisperx({"segments": [{"words": [None, 42]}]}) == []


def test_write_words_json_round_trips_through_karaoke_loader(tmp_path):
    """write_words_json 산출물이 karaoke.load_words_json 으로 다시 읽혀야 한다."""
    from shorts_maker_v2.render.karaoke import load_words_json

    words = [
        WordSegment(word="안녕", start=0.0, end=0.5),
        WordSegment(word="세상", start=0.6, end=1.1),
    ]
    dest = tmp_path / "narration_words.json"
    write_words_json(words, dest)

    payload = json.loads(dest.read_text(encoding="utf-8"))
    assert payload[0]["word"] == "안녕"
    assert payload[1]["end"] == 1.1

    reloaded = load_words_json(dest)
    assert len(reloaded) == 2
    assert reloaded[0].word == "안녕"
    assert reloaded[1].start == pytest.approx(0.6, abs=1e-3)
