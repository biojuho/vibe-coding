"""WhisperX 단어-레벨 자막 정렬 (T-19 해결용 옵트인 정렬기).

WhisperX (BSD-2) 는 faster-whisper + wav2vec2 forced alignment 를 결합해
OpenAI Whisper 보다 정확한 단어 타이밍을 만든다. 한국어 native 지원, CPU OK.
torch + whisperx 가 무거우므로 `is_available()` 가 False 면 호출자는 휴리스틱
폴백을 유지해야 한다.

사용 패턴:

    >>> from shorts_maker_v2.render.whisperx_aligner import (
    ...     align_audio_words, is_available,
    ... )
    >>> if is_available():
    ...     words = align_audio_words(audio_path, narration_ko, language="ko")
    ... else:
    ...     words = None  # caller falls back to edge-tts WordBoundary etc.

출력 형식은 `render/karaoke.py` 의 WordSegment 와 호환되도록 정규화한다.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from shorts_maker_v2.render.karaoke import WordSegment

logger = logging.getLogger(__name__)


_AVAILABILITY_CACHE: bool | None = None


def is_available() -> bool:
    """whisperx 패키지가 설치되어 있는지 확인 (결과 캐시)."""
    global _AVAILABILITY_CACHE
    if _AVAILABILITY_CACHE is not None:
        return _AVAILABILITY_CACHE
    try:
        import whisperx  # noqa: F401

        _AVAILABILITY_CACHE = True
    except Exception as exc:
        logger.debug("whisperx not available (optional dependency): %s", exc)
        _AVAILABILITY_CACHE = False
    return _AVAILABILITY_CACHE


def reset_availability_cache() -> None:
    """테스트용 — `is_available()` 결과를 강제로 재평가."""
    global _AVAILABILITY_CACHE
    _AVAILABILITY_CACHE = None


def _word_segments_from_whisperx(result: Any) -> list[WordSegment]:
    """WhisperX align 결과를 WordSegment 리스트로 정규화.

    WhisperX 의 출력은 `{"segments": [{"words": [{"word", "start", "end", ...}, ...]}, ...]}`
    형태. start/end 가 None 인 항목과 빈 토큰은 스킵.
    """
    segments = result.get("segments", []) if isinstance(result, dict) else []
    words: list[WordSegment] = []
    for seg in segments:
        if not isinstance(seg, dict):
            continue
        for w in seg.get("words", []) or []:
            if not isinstance(w, dict):
                continue
            token = str(w.get("word", "")).strip()
            start = w.get("start")
            end = w.get("end")
            if not token or start is None or end is None:
                continue
            try:
                start_f = float(start)
                end_f = float(end)
            except (TypeError, ValueError):
                continue
            if end_f <= start_f:
                continue
            words.append(WordSegment(word=token, start=start_f, end=end_f))
    return words


def align_audio_words(
    audio_path: Path,
    narration_text: str,
    *,
    language: str = "ko",
    model_size: str = "base",
    device: str = "cpu",
    compute_type: str = "int8",
) -> list[WordSegment] | None:
    """오디오와 나레이션 텍스트로 단어-레벨 정렬을 생성한다.

    WhisperX 가 미설치이거나 정렬이 실패하면 None 을 리턴한다 (caller 폴백 필요).
    `language="ko"` 가 기본. CPU 사용을 가정해 `compute_type="int8"` 로 시작.

    이 모듈은 import-time 부작용이 없도록 whisperx import 를 호출 시점에 lazy 로 한다.
    """
    if not is_available():
        logger.debug("[WhisperX] not available — skipping alignment")
        return None

    audio_str = str(audio_path)
    if not audio_path.exists():
        logger.warning("[WhisperX] audio missing: %s", audio_str)
        return None

    try:
        import whisperx  # type: ignore[import-not-found]

        model = whisperx.load_model(model_size, device=device, compute_type=compute_type, language=language)
        transcription = model.transcribe(audio_str, language=language)
        # transcription 이 narration_text 보다 정확도가 낮을 수 있으므로
        # 사용자 텍스트를 정답(reference)으로 강제 (whisperx 의 force_align 패턴)
        if narration_text and isinstance(transcription, dict):
            transcription.setdefault("segments", [])
            if transcription["segments"]:
                transcription["segments"][0]["text"] = narration_text

        align_model, metadata = whisperx.load_align_model(language_code=language, device=device)
        aligned = whisperx.align(
            transcription.get("segments", []),
            align_model,
            metadata,
            audio_str,
            device=device,
            return_char_alignments=False,
        )
        words = _word_segments_from_whisperx(aligned)
        if not words:
            logger.warning("[WhisperX] alignment produced 0 word segments")
            return None
        logger.info("[WhisperX] aligned %d words for %s (lang=%s)", len(words), audio_path.name, language)
        return words
    except Exception as exc:
        logger.warning("[WhisperX] alignment failed (caller should fall back): %s", exc)
        return None


def write_words_json(words: list[WordSegment], destination: Path) -> None:
    """WordSegment 리스트를 karaoke.load_words_json 이 읽을 수 있는 JSON 으로 직렬화."""
    import json

    payload = [{"word": w.word, "start": float(w.start), "end": float(w.end)} for w in words]
    destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
