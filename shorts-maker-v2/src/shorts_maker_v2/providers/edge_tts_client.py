"""edge-tts client with WordBoundary timing capture and retry fallbacks."""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from xml.sax.saxutils import escape

import edge_tts

logger = logging.getLogger(__name__)


class SSMLCommunicate(edge_tts.Communicate):
    """Allow raw SSML input without re-escaping the text body."""

    def _create_ssml(self) -> str:
        return (
            f"<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xml:lang='en-US'>"
            f"<voice name='{self.voice}'>"
            f"<prosody rate='{self.rate}' pitch='{self.pitch}' volume='{self.volume}'>"
            f"{self.text}"
            f"</prosody></voice></speak>"
        )


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
    pct = int((speed - 1.0) * 100)
    return f"+{pct}%" if pct >= 0 else f"{pct}%"


def _apply_ssml_by_role(text: str, role: str) -> str:
    safe_text = escape(text)
    if role == "hook":
        return (
            '<prosody rate="+15%" pitch="+8Hz">'
            f'<emphasis level="strong">{safe_text}</emphasis>'
            "</prosody>"
        )
    if role == "cta":
        return (
            '<break time="300ms"/>'
            '<prosody rate="-10%" pitch="+5Hz">'
            f'<emphasis level="moderate">{safe_text}</emphasis>'
            "</prosody>"
        )
    return safe_text.replace(". ", '.<break time="200ms"/> ')


def _approximate_word_timings(ssml_text: str, audio_path: Path) -> list[dict]:
    import re

    plain = re.sub(r"<[^>]+>", " ", ssml_text)
    plain = re.sub(r"\s+", " ", plain).strip()
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
        hangul = len(re.findall(r"[가-힣]", word))
        latin = len(re.findall(r"[A-Za-z0-9]", word))
        return max(1.0, hangul * 1.0 + latin * 0.5)

    weights = [_weight(word) for word in words]
    total_weight = sum(weights)
    cursor = 0.0
    result: list[dict] = []
    for word, weight in zip(words, weights):
        dur = (weight / total_weight) * audio_dur
        result.append({
            "word": word,
            "start": round(cursor, 4),
            "end": round(cursor + dur, 4),
        })
        cursor += dur
    return result


async def _generate_async(text: str, voice: str, rate: str, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    communicate = SSMLCommunicate(text, voice=voice, rate=rate)
    await communicate.save(str(output_path))


async def _generate_async_with_timing(
    text: str,
    voice: str,
    rate: str,
    output_path: Path,
    words_json_path: Path,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    words_json_path.parent.mkdir(parents=True, exist_ok=True)

    communicate = SSMLCommunicate(text, voice=voice, rate=rate)
    words: list[dict] = []
    audio_chunks: list[bytes] = []

    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_chunks.append(chunk["data"])
        elif chunk["type"] == "WordBoundary":
            offset_sec = chunk["offset"] / 10_000_000
            duration_sec = chunk["duration"] / 10_000_000
            words.append({
                "word": chunk["text"],
                "start": round(offset_sec, 4),
                "end": round(offset_sec + duration_sec, 4),
            })

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
    """Wrapper compatible with OpenAIClient.generate_tts()."""

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

        rate = _speed_to_rate(speed)
        ssml_text = _apply_ssml_by_role(text, role)
        attempt_plan: list[tuple[str, str, str]] = [
            (edge_voice, ssml_text, "primary_ssml"),
            (edge_voice, escape(text), "primary_plain"),
        ]
        if edge_voice != _DEFAULT_VOICE:
            attempt_plan.extend([
                (_DEFAULT_VOICE, ssml_text, "default_voice_ssml"),
                (_DEFAULT_VOICE, escape(text), "default_voice_plain"),
            ])

        last_exc: Exception | None = None
        for attempt_index, (attempt_voice, attempt_text, attempt_label) in enumerate(attempt_plan, start=1):
            logger.info(
                "EdgeTTS: voice=%s rate=%s text_len=%d role=%s attempt=%s",
                attempt_voice,
                rate,
                len(text),
                role,
                attempt_label,
            )

            def _make_coro():
                if words_json_path is not None:
                    return _generate_async_with_timing(
                        attempt_text,
                        attempt_voice,
                        rate,
                        output_path,
                        words_json_path,
                    )
                return _generate_async(attempt_text, attempt_voice, rate, output_path)

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
