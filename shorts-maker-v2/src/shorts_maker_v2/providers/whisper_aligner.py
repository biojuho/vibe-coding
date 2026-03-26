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


def transcribe_to_word_timings(
    audio_path: Path,
    model_size: str = "base",
    language: str = "ko",
) -> list[dict]:
    """TTS 오디오를 faster-whisper로 분석해 word-level 타임스탬프 반환.

    faster-whisper가 설치되지 않았거나 오디오 분석에 실패하면
    빈 리스트를 반환하여 상위 fallback(_approximate_word_timings)이 동작하게 함.

    Args:
        audio_path: 분석할 오디오 파일 경로 (mp3 / wav 등 ffmpeg 지원 형식).
        model_size: Whisper 모델 크기. CPU 환경에서는 "base" 권장.
                    선택 가능: "tiny", "base", "small", "medium", "large-v3"
        language: Whisper 언어 코드 또는 locale (`ko`, `en`, `ko-KR`, `en-US` 등).

    Returns:
        [{"word": str, "start": float, "end": float}] 포맷의 단어 타이밍 목록.
        실패 시 빈 리스트 반환.
    """
    if not audio_path.exists() or audio_path.stat().st_size == 0:
        logger.warning("whisper_aligner: 오디오 파일 없음 또는 크기 0 — %s", audio_path)
        return []

    try:
        from faster_whisper import WhisperModel
    except ImportError:
        logger.debug("whisper_aligner: faster-whisper 미설치 — fallback 불가")
        return []

    try:
        logger.info("whisper_aligner: faster-whisper (%s, cpu, int8) 로드 중…", model_size)
        model = WhisperModel(model_size, device="cpu", compute_type="int8")
        whisper_language = _normalize_whisper_language(language)

        logger.info("whisper_aligner: '%s' 분석 시작", audio_path.name)
        segments, _info = model.transcribe(
            str(audio_path),
            word_timestamps=True,
            beam_size=1,  # CPU 속도 최적화
            vad_filter=True,  # 무음 구간 제거 → 타임스탬프 안정화
            language=whisper_language,
        )

        result: list[dict] = []
        for segment in segments:
            if segment.words is None:
                continue
            for word in segment.words:
                cleaned = word.word.strip()
                if not cleaned:
                    continue
                result.append(
                    {
                        "word": cleaned,
                        "start": round(float(word.start), 4),
                        "end": round(float(word.end), 4),
                    }
                )

        logger.info(
            "whisper_aligner: %d개 단어 타임스탬프 추출 완료 (%s)",
            len(result),
            audio_path.name,
        )
        return result

    except Exception as exc:
        logger.warning("whisper_aligner: 분석 실패 (%s) — %s", audio_path.name, exc)
        return []
