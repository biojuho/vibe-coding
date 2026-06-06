"""
whisper_aligner.py — faster-whisper 기반 word-level 타임스탬프 추출.

EdgeTTS WordBoundary 이벤트가 비어 있을 때 호출되는 정밀 fallback.
faster-whisper가 설치되지 않은 환경에서는 graceful하게 비어 있는 목록을 반환.

반환 포맷은 karaoke.load_words_json()과 100% 호환:
    [{"word": str, "start": float, "end": float}, ...]
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def _normalize_whisper_language(language: str | None) -> str:
    normalized = (language or "ko").strip().lower()
    if "-" in normalized:
        normalized = normalized.split("-", 1)[0]
    if "_" in normalized:
        normalized = normalized.split("_", 1)[0]
    return normalized or "ko"


def is_whisper_available() -> bool:
    """faster-whisper가 설치되어 import 가능한지 확인."""
    try:
        import faster_whisper  # noqa: F401

        return True
    except ImportError:
        return False


def is_whisperx_available() -> bool:
    """whisperx가 설치되어 import 가능한지 확인."""
    try:
        import whisperx  # noqa: F401

        return True
    except ImportError:
        return False


def _build_word_timing(word: str, start: float, end: float) -> dict | None:
    cleaned = word.strip()
    if not cleaned:
        return None
    return {
        "word": cleaned,
        "start": round(float(start), 4),
        "end": round(float(end), 4),
    }


def _word_timing_from_mapping(word_info: dict) -> dict | None:
    if "start" not in word_info or "end" not in word_info:
        return None
    return _build_word_timing(str(word_info.get("word", "")), word_info["start"], word_info["end"])


def _collect_mapping_word_timings(segments: list[dict]) -> list[dict]:
    result_words: list[dict] = []
    for segment in segments:
        for word_info in segment.get("words", []):
            timing = _word_timing_from_mapping(word_info)
            if timing:
                result_words.append(timing)
    return result_words


def _collect_faster_whisper_word_timings(segments) -> list[dict]:
    result_words: list[dict] = []
    for segment in segments:
        if segment.words is None:
            continue
        for word in segment.words:
            timing = _build_word_timing(word.word, word.start, word.end)
            if timing:
                result_words.append(timing)
    return result_words


def _transcribe_with_whisperx(audio_path: Path, model_size: str, whisper_language: str) -> list[dict]:
    import whisperx

    logger.info("whisper_aligner: whisperx (%s, cpu, int8) loading", model_size)
    model = whisperx.load_model(model_size, device="cpu", compute_type="int8")

    logger.info("whisper_aligner: whisperx '%s' transcribe start (lang: %s)", audio_path.name, whisper_language)
    audio = whisperx.load_audio(str(audio_path))
    result = model.transcribe(audio, batch_size=16, language=whisper_language)

    result_words: list[dict] = []
    try:
        logger.info("whisper_aligner: whisperx alignment model loading")
        model_a, metadata = whisperx.load_align_model(language_code=whisper_language, device="cpu")

        logger.info("whisper_aligner: whisperx alignment running")
        result_aligned = whisperx.align(
            result["segments"],
            model_a,
            metadata,
            audio,
            device="cpu",
            return_char_alignments=False,
        )
        result_words = _collect_mapping_word_timings(result_aligned.get("segments", []))
    except Exception as align_exc:
        logger.warning("whisper_aligner: whisperx alignment failed; using segment words: %s", align_exc)

    if not result_words:
        logger.info("whisper_aligner: parsing whisperx segments directly")
        result_words = _collect_mapping_word_timings(result.get("segments", []))
    return result_words


def _transcribe_with_faster_whisper(audio_path: Path, model_size: str, whisper_language: str) -> list[dict]:
    from faster_whisper import WhisperModel

    logger.info("whisper_aligner: faster-whisper (%s, cpu, int8) loading", model_size)
    model = WhisperModel(model_size, device="cpu", compute_type="int8")

    logger.info("whisper_aligner: faster-whisper '%s' analysis start", audio_path.name)
    segments, _info = model.transcribe(
        str(audio_path),
        word_timestamps=True,
        beam_size=1,
        vad_filter=True,
        language=whisper_language,
    )
    return _collect_faster_whisper_word_timings(segments)


def transcribe_to_word_timings(
    audio_path: Path,
    model_size: str = "base",
    language: str = "ko",
) -> list[dict]:
    """TTS 오디오를 로컬 WhisperX / faster-whisper로 분석해 word-level 타임스탬프 반환.

    우선 whisperx를 사용해 정밀한 단어 정렬(Alignment)을 시도하며,
    실패하거나 패키지가 없는 경우 faster-whisper 기반 분석으로 fallback합니다.
    모두 실패할 경우 빈 리스트를 반환하여 상위 OpenAI API fallback이 동작하도록 설계되었습니다.

    Args:
        audio_path: 분석할 오디오 파일 경로 (mp3 / wav 등 ffmpeg 지원 형식).
        model_size: Whisper 모델 크기. CPU 환경에서는 "base" 또는 "small" 권장.
                    선택 가능: "tiny", "base", "small", "medium", "large-v3"
        language: Whisper 언어 코드 또는 locale (`ko`, `en`, `ko-KR`, `en-US` 등).

    Returns:
        [{"word": str, "start": float, "end": float}] 포맷의 단어 타이밍 목록.
        실패 시 빈 리스트 반환.
    """
    if not audio_path.exists() or audio_path.stat().st_size == 0:
        logger.warning("whisper_aligner: 오디오 파일 없음 또는 크기 0 — %s", audio_path)
        return []

    whisper_language = _normalize_whisper_language(language)

    # 1. WhisperX 시도
    if is_whisperx_available():
        try:
            result_words = _transcribe_with_whisperx(audio_path, model_size, whisper_language)

            if result_words:
                logger.info(
                    "whisper_aligner: whisperx 성공! %d개 단어 추출 완료 (%s)",
                    len(result_words),
                    audio_path.name,
                )
                return result_words

        except Exception as wx_exc:
            logger.warning("whisper_aligner: whisperx 전사 실패 -> faster-whisper fallback 시도: %s", wx_exc)

    # 2. faster-whisper Fallback 시도
    if is_whisper_available():
        try:
            result_words = _transcribe_with_faster_whisper(audio_path, model_size, whisper_language)

            if result_words:
                logger.info(
                    "whisper_aligner: faster-whisper 성공! %d개 단어 추출 완료 (%s)",
                    len(result_words),
                    audio_path.name,
                )
                return result_words

        except Exception as fw_exc:
            logger.warning("whisper_aligner: faster-whisper 분석 실패 — %s", fw_exc)

    logger.warning("whisper_aligner: 로컬 전사 모델 (WhisperX / faster-whisper) 모두 실패")
    return []
