"""edge-tts client with WordBoundary timing capture and retry fallbacks.

SSML 태그 제거 — edge-tts의 rate/pitch 파라미터를 직접 사용합니다.
이전 버전에서 SSMLCommunicate + _apply_ssml_by_role 방식으로 SSML 태그를
텍스트에 삽입했으나, edge-tts가 이 태그를 리터럴 텍스트로 읽는 버그가 있어
plain text 방식으로 전환합니다.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re as _re
from pathlib import Path

import edge_tts

logger = logging.getLogger(__name__)


# ── 음성 매핑 ─────────────────────────────────────────────────────────────────

_OPENAI_TO_EDGE_VOICE: dict[str, str] = {
    "alloy": "ko-KR-SunHiNeural",
    "echo": "ko-KR-InJoonNeural",
    "fable": "ko-KR-SunHiNeural",
    "onyx": "ko-KR-InJoonNeural",
    "nova": "ko-KR-SunHiNeural",
    "shimmer": "ko-KR-SunHiNeural",
    "sage": "ko-KR-HyunsuNeural",
    "coral": "ko-KR-BongJinNeural",
    "ash": "ko-KR-SoonBokNeural",
    "verse": "ko-KR-GookMinNeural",
}
_DEFAULT_VOICE = "ko-KR-SunHiNeural"


def _speed_to_rate(speed: float) -> str:
    pct = round((speed - 1.0) * 100)
    return f"+{pct}%" if pct >= 0 else f"{pct}%"


def _get_role_prosody(role: str, base_rate: str = "+0%") -> tuple[str, str]:
    """역할 기반 rate/pitch 반환 (SSML 없이 파라미터 직접 사용).

    Returns:
        (rate, pitch) 튜플
    """
    if role == "hook":
        return "+15%", "+8Hz"
    if role == "cta":
        return "-10%", "+5Hz"
    # body: base_rate 사용, pitch 기본값
    return base_rate, "+0Hz"


# ── 근사 타이밍 (WordBoundary 미지원 시 fallback) ──────────────────────────────


def _approximate_word_timings(text: str, audio_path: Path) -> list[dict]:
    """음절 가중치 기반 근사 타이밍."""
    plain = _re.sub(r"\s+", " ", text).strip()
    if not plain:
        return []

    words = [word for word in plain.split() if word.strip()]
    if not words:
        return []

    try:
        from mutagen.mp3 import MP3

        audio_dur = MP3(str(audio_path)).info.length
    except Exception:
        return []

    if audio_dur <= 0:
        return []

    def _weight(word: str) -> float:
        hangul = len(_re.findall(r"[가-힣]", word))
        latin = len(_re.findall(r"[A-Za-z0-9]", word))
        return max(1.0, hangul * 1.0 + latin * 0.5)

    weights = [_weight(word) for word in words]
    total_weight = sum(weights)
    cursor = 0.0
    result: list[dict] = []
    for word, weight in zip(words, weights, strict=False):
        dur = (weight / total_weight) * audio_dur
        result.append(
            {
                "word": word,
                "start": round(cursor, 4),
                "end": round(cursor + dur, 4),
            }
        )
        cursor += dur
    return result


# ── 비동기 TTS 생성 ──────────────────────────────────────────────────────────


async def _generate_async(
    text: str,
    voice: str,
    rate: str,
    pitch: str,
    output_path: Path,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    communicate = edge_tts.Communicate(text, voice=voice, rate=rate, pitch=pitch)
    await communicate.save(str(output_path))


async def _generate_async_with_timing(
    text: str,
    voice: str,
    rate: str,
    pitch: str,
    output_path: Path,
    words_json_path: Path,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    words_json_path.parent.mkdir(parents=True, exist_ok=True)

    communicate = edge_tts.Communicate(text, voice=voice, rate=rate, pitch=pitch)
    words: list[dict] = []
    audio_chunks: list[bytes] = []

    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_chunks.append(chunk["data"])
        elif chunk["type"] == "WordBoundary":
            offset_sec = chunk["offset"] / 10_000_000
            duration_sec = chunk["duration"] / 10_000_000
            words.append(
                {
                    "word": chunk["text"],
                    "start": round(offset_sec, 4),
                    "end": round(offset_sec + duration_sec, 4),
                }
            )

    with output_path.open("wb") as handle:
        for data in audio_chunks:
            handle.write(data)

    if words:
        words_json_path.write_text(
            json.dumps(words, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info("EdgeTTS: %d word timings saved to %s", len(words), words_json_path)
    else:
        # 1순위 fallback: faster-whisper로 TTS 오디오 재분석 (정밀)
        whisper_words: list[dict] = []
        try:
            from shorts_maker_v2.providers.whisper_aligner import (
                is_whisper_available,
                transcribe_to_word_timings,
            )

            if is_whisper_available():
                logger.info("EdgeTTS: WordBoundary 없음 → faster-whisper fallback 시도")
                whisper_words = transcribe_to_word_timings(output_path)
        except Exception as _whisper_exc:
            logger.debug("EdgeTTS: whisper_aligner 호출 실패 (%s) — 근사치로 진행", _whisper_exc)

        if whisper_words:
            words_json_path.write_text(
                json.dumps(whisper_words, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            logger.info(
                "EdgeTTS: whisper word timings saved for %d words: %s",
                len(whisper_words),
                words_json_path,
            )
        else:
            # 2순위 fallback: 음절 가중치 기반 근사치
            approx = _approximate_word_timings(text, output_path)
            if approx:
                words_json_path.write_text(
                    json.dumps(approx, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                logger.info(
                    "EdgeTTS: approximate timings saved for %d words: %s",
                    len(approx),
                    words_json_path,
                )

    # plain text 저장 (이전 SSML 호환: render_step의 break 보정에 사용)
    (words_json_path.parent / f"{words_json_path.stem}_ssml.txt").write_text(
        text,
        encoding="utf-8",
    )


def _run_coroutine(coro_factory) -> None:
    try:
        asyncio.run(coro_factory())
    except RuntimeError:
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(asyncio.run, coro_factory())
            future.result()


class EdgeTTSClient:
    """Wrapper compatible with OpenAIClient.generate_tts().

    SSML 태그 없이 plain text를 edge-tts에 전달합니다.
    역할(hook/cta/body)별 속도/피치 조절은 edge-tts의
    rate/pitch 파라미터로 직접 처리합니다.
    """

    def generate_tts(
        self,
        *,
        model: str,
        voice: str,
        speed: float,
        text: str,
        output_path: Path,
        words_json_path: Path | None = None,
        role: str = "body",
    ) -> Path:
        del model

        if output_path.exists() and output_path.stat().st_size > 0:
            return output_path
        output_path.unlink(missing_ok=True)

        if "Neural" in voice or "neural" in voice:
            edge_voice = voice
        else:
            edge_voice = _OPENAI_TO_EDGE_VOICE.get(voice, _DEFAULT_VOICE)

        # 역할별 rate/pitch 결정 (SSML 태그 없음)
        base_rate = _speed_to_rate(speed)
        rate, pitch = _get_role_prosody(role, base_rate=base_rate)

        # 시도 계획: 기본 음성 → 폴백 음성
        attempt_plan: list[tuple[str, str, str, str]] = [
            (edge_voice, rate, pitch, "primary"),
        ]
        if edge_voice != _DEFAULT_VOICE:
            attempt_plan.append(
                (_DEFAULT_VOICE, rate, pitch, "default_voice"),
            )

        last_exc: Exception | None = None
        for attempt_index, (attempt_voice, attempt_rate, attempt_pitch, attempt_label) in enumerate(
            attempt_plan, start=1
        ):
            logger.info(
                "EdgeTTS: voice=%s rate=%s pitch=%s text_len=%d role=%s attempt=%s",
                attempt_voice,
                attempt_rate,
                attempt_pitch,
                len(text),
                role,
                attempt_label,
            )

            def _make_coro():
                if words_json_path is not None:
                    return _generate_async_with_timing(
                        text,
                        attempt_voice,
                        attempt_rate,
                        attempt_pitch,
                        output_path,
                        words_json_path,
                    )
                return _generate_async(text, attempt_voice, attempt_rate, attempt_pitch, output_path)

            try:
                _run_coroutine(_make_coro)
                if output_path.exists() and output_path.stat().st_size > 0:
                    logger.info("EdgeTTS: saved %s", output_path)
                    return output_path
                raise RuntimeError("No audio was received. Please verify that your parameters are correct.")
            except Exception as exc:
                last_exc = exc
                logger.warning(
                    "EdgeTTS retryable failure (%d/%d): voice=%s mode=%s error=%s",
                    attempt_index,
                    len(attempt_plan),
                    attempt_voice,
                    attempt_label,
                    exc,
                )
                output_path.unlink(missing_ok=True)
                if words_json_path is not None:
                    words_json_path.unlink(missing_ok=True)
                    (words_json_path.parent / f"{words_json_path.stem}_ssml.txt").unlink(missing_ok=True)

        assert last_exc is not None
        raise last_exc
