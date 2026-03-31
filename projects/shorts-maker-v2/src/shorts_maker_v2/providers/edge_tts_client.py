"""edge-tts client with WordBoundary timing capture and retry fallbacks.

SSML 태그 제거 — edge-tts의 rate/pitch 파라미터를 직접 사용합니다.
이전 버전에서 SSMLCommunicate + _apply_ssml_by_role 방식으로 SSML 태그를
텍스트에 삽입했으나, edge-tts가 이 태그를 리터럴 텍스트로 읽는 버그가 있어
plain text 방식으로 전환합니다.
"""

from __future__ import annotations

import asyncio
import copy
import json
import logging
import random
import re as _re
from pathlib import Path
from typing import Any

import edge_tts
import yaml

logger = logging.getLogger(__name__)


# ── 음성 매핑 ─────────────────────────────────────────────────────────────────

_EDGE_TTS_LOCALE_CACHE: dict[str, dict[str, Any]] = {}

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


def _edge_tts_locale_path(language: str) -> Path:
    project_root = Path(__file__).resolve().parents[3]
    return project_root / "locales" / language / "edge_tts.yaml"


def _load_edge_tts_locale_bundle(language: str) -> dict[str, Any]:
    normalized = (language or "ko-KR").strip() or "ko-KR"
    cached = _EDGE_TTS_LOCALE_CACHE.get(normalized)
    if cached is not None:
        return copy.deepcopy(cached)

    locale_path = _edge_tts_locale_path(normalized)
    if not locale_path.exists():
        _EDGE_TTS_LOCALE_CACHE[normalized] = {}
        return {}

    try:
        with locale_path.open(encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
        if not isinstance(data, dict):
            logger.warning("[EdgeTTSI18N] locale bundle is not a mapping: %s", locale_path)
            data = {}
    except Exception as exc:
        logger.warning("[EdgeTTSI18N] failed to load locale bundle %s: %s", locale_path, exc)
        data = {}

    _EDGE_TTS_LOCALE_CACHE[normalized] = copy.deepcopy(data)
    return data


def _get_edge_voice_profile(language: str = "ko-KR") -> tuple[dict[str, str], str]:
    bundle = _load_edge_tts_locale_bundle(language)
    voice_map = dict(_OPENAI_TO_EDGE_VOICE)

    localized_map = bundle.get("openai_to_edge_voice")
    if isinstance(localized_map, dict):
        voice_map.update(
            {
                str(key).strip(): str(value).strip()
                for key, value in localized_map.items()
                if str(key).strip() and str(value).strip()
            }
        )

    default_voice = str(bundle.get("default_voice", _DEFAULT_VOICE)).strip() or _DEFAULT_VOICE
    return voice_map, default_voice


def _resolve_edge_voice(voice: str, language: str = "ko-KR") -> tuple[str, str]:
    voice_map, default_voice = _get_edge_voice_profile(language)
    if "Neural" in voice or "neural" in voice:
        return voice, default_voice
    return voice_map.get(voice, default_voice), default_voice


# ── 채널별 prosody 설정 ───────────────────────────────────────────────────────
# (rate_jitter_range_pct, pitch_jitter_range_hz) — body 씬 기본값
# 채널 특성에 맞게 변주 폭을 다르게 설정하여 AI 티를 줄인다.
# rate 변주: 숫자가 클수록 속도 변화가 크고 생동감 있음
# pitch 변주: 숫자가 클수록 음높이 변화가 크고 감성적임
_CHANNEL_PROSODY: dict[str, tuple[int, int]] = {
    # (rate_jitter_pct, pitch_jitter_hz)
    "ai_tech": (7, 2),  # 빠른 리듬감; rate 변주 ±7%, pitch 변주 소폭
    "history": (4, 3),  # 서사적 호흡; rate ±4%, pitch ±3Hz
    "psychology": (3, 5),  # 공감·감성; rate 소폭, pitch ±5Hz로 부드럽게
    "space": (5, 4),  # 경이로움; 중간 리듬, pitch ±4Hz
    "health": (3, 2),  # 신뢰감; 안정적으로 변주 최소화
}
_DEFAULT_PROSODY: tuple[int, int] = (5, 3)  # 채널 미지정 시 기본값


def _speed_to_rate(speed: float) -> str:
    pct = round((speed - 1.0) * 100)
    return f"+{pct}%" if pct >= 0 else f"{pct}%"


def _get_role_prosody(
    role: str,
    base_rate: str = "+0%",
    channel_key: str = "",
) -> tuple[str, str]:
    """역할 기반 rate/pitch 반환 (SSML 없이 파라미터 직접 사용).

    hook/cta는 고정값, body는 채널별 prosody 테이블의 변주 폭으로
    자연스러운 억양 변화를 적용한다.

    Args:
        role: 씬 역할 (hook / body / cta)
        base_rate: 기본 속도 문자열 (예: "+10%")
        channel_key: 채널 ID (예: 'psychology'). 빈 문자열이면 기본값 사용.

    Returns:
        (rate, pitch) 튜플
    """
    if role == "hook":
        # Hook: 강렬하고 빠르게 — 채널별로 hook pitch 약간 변주
        pitch_hook_map = {
            "psychology": "+6Hz",  # 따뜻한 첫 인상
            "history": "+7Hz",  # 극적인 시작
            "space": "+5Hz",  # 경이감
            "ai_tech": "+10Hz",  # 임팩트있는 개시
            "health": "+6Hz",  # 친근한 시작
        }
        hook_pitch = pitch_hook_map.get(channel_key, "+8Hz")
        return "+15%", hook_pitch
    if role == "cta":
        return "-10%", "+5Hz"
    if role == "closing":
        # 여운 있는 마무리: 느리고 부드럽게, 낮은 pitch로 차분하게 끝남
        return "-15%", "-2Hz"
    # body 및 기타 역할: 채널별 변주 폭으로 자연스러운 억양 적용
    try:
        base_pct = int(base_rate.replace("%", "").replace("+", ""))
    except ValueError:
        base_pct = 0
    rate_jitter, pitch_jitter = _CHANNEL_PROSODY.get(channel_key, _DEFAULT_PROSODY)
    jitter = random.randint(-rate_jitter, rate_jitter)
    final_pct = base_pct + jitter
    rate = f"+{final_pct}%" if final_pct >= 0 else f"{final_pct}%"
    pitch_hz = random.randint(-pitch_jitter, pitch_jitter)
    pitch = f"+{pitch_hz}Hz" if pitch_hz >= 0 else f"{pitch_hz}Hz"
    return rate, pitch


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


def _add_silence_padding(audio_path: Path, pad_ms: int = 50) -> None:
    """오디오 앞뒤에 짧은 무음 패딩을 추가하여 씬 전환 팝/클릭 방지."""
    try:
        from pydub import AudioSegment

        audio = AudioSegment.from_file(str(audio_path))
        silence = AudioSegment.silent(duration=pad_ms, frame_rate=audio.frame_rate)
        padded = silence + audio + silence
        padded.export(str(audio_path), format=audio_path.suffix.lstrip("."))
        logger.debug("EdgeTTS: added %dms silence padding to %s", pad_ms, audio_path.name)
    except ImportError:
        logger.debug("EdgeTTS: pydub not available, skipping silence padding")
    except Exception as exc:
        logger.debug("EdgeTTS: silence padding failed: %s", exc)


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
    _add_silence_padding(output_path)


async def _generate_async_with_timing(
    text: str,
    voice: str,
    rate: str,
    pitch: str,
    output_path: Path,
    words_json_path: Path,
    language: str = "ko-KR",
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
                whisper_words = transcribe_to_word_timings(output_path, language=language)
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

    # silence padding 적용 (씬 전환 팝/클릭 방지)
    _add_silence_padding(output_path)

    # padding offset 적용: word timing을 0.05s 시프트 (앞 50ms 패딩)
    _pad_sec = 0.05
    if words_json_path.exists():
        try:
            _saved_words = json.loads(words_json_path.read_text(encoding="utf-8"))
            for w in _saved_words:
                w["start"] = round(w["start"] + _pad_sec, 4)
                w["end"] = round(w["end"] + _pad_sec, 4)
            words_json_path.write_text(
                json.dumps(_saved_words, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass

    # plain text 저장 (이전 SSML 호환: render_step의 break 보정에 사용)
    (words_json_path.parent / f"{words_json_path.stem}_ssml.txt").write_text(
        text,
        encoding="utf-8",
    )


def _run_coroutine(coro_factory) -> None:
    try:
        asyncio.run(coro_factory())
    except RuntimeError as exc:
        # 기존 이벤트 루프 충돌만 fallback (코루틴 자체 RuntimeError는 전파)
        if "event loop" not in str(exc).lower() and "running" not in str(exc).lower():
            raise
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
        channel_key: str = "",
        language: str = "ko-KR",
    ) -> Path:
        del model

        if output_path.exists() and output_path.stat().st_size > 0:
            return output_path
        output_path.unlink(missing_ok=True)

        edge_voice, default_voice = _resolve_edge_voice(voice, language)

        # 채널별·역할별 rate/pitch 결정 (SSML 태그 없음)
        base_rate = _speed_to_rate(speed)
        rate, pitch = _get_role_prosody(role, base_rate=base_rate, channel_key=channel_key)

        # 시도 계획: 기본 음성 → 폴백 음성
        attempt_plan: list[tuple[str, str, str, str]] = [
            (edge_voice, rate, pitch, "primary"),
        ]
        if edge_voice != default_voice:
            attempt_plan.append(
                (default_voice, rate, pitch, "default_voice"),
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

            def _make_coro(
                _voice: str = attempt_voice,
                _rate: str = attempt_rate,
                _pitch: str = attempt_pitch,
            ):
                if words_json_path is not None:
                    return _generate_async_with_timing(
                        text,
                        _voice,
                        _rate,
                        _pitch,
                        output_path,
                        words_json_path,
                        language,
                    )
                return _generate_async(text, _voice, _rate, _pitch, output_path)

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
