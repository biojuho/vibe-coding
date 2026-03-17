"""edge-tts 클라이언트 — Microsoft Edge TTS (무료, 한국어 지원).

OpenAIClient.generate_tts()와 동일한 인터페이스를 제공합니다.
비용: $0 (무료)
한국어 음성 6종:
  - ko-KR-SunHiNeural (여, 밝고 자연)
  - ko-KR-InJoonNeural (남, 강하고 권위)
  - ko-KR-HyunsuNeural (남, 차분 지적)
  - ko-KR-BongJinNeural (남, 따뜻 친근)
  - ko-KR-SoonBokNeural (여, 부드러운 안정)
  - ko-KR-GookMinNeural (남, 또렷 낮음)
"""
from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

# Subclass edge_tts.Communicate to allow raw SSML (bypassing xml.sax.saxutils.escape)
import edge_tts

class SSMLCommunicate(edge_tts.Communicate):
    def _create_ssml(self) -> str:
        # Instead of escaping self.text, we assume it's already properly formatted SSML or plain text.
        # We only apply basic escaping to specific characters if needed, but here we trust the input.
        return (
            f"<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xml:lang='en-US'>"
            f"<voice name='{self.voice}'>"
            f"<prosody rate='{self.rate}' pitch='{self.pitch}' volume='{self.volume}'>"
            f"{self.text}"
            f"</prosody></voice></speak>"
        )

logger = logging.getLogger(__name__)

# OpenAI 음성 이름 → edge-tts 한국어 음성 매핑
_OPENAI_TO_EDGE_VOICE: dict[str, str] = {
    "alloy":   "ko-KR-SunHiNeural",
    "echo":    "ko-KR-InJoonNeural",
    "fable":   "ko-KR-SunHiNeural",
    "onyx":    "ko-KR-InJoonNeural",
    "nova":    "ko-KR-SunHiNeural",
    "shimmer": "ko-KR-SunHiNeural",
    "sage":    "ko-KR-HyunsuNeural",
    "coral":   "ko-KR-BongJinNeural",
    "ash":     "ko-KR-SoonBokNeural",
    "verse":   "ko-KR-GookMinNeural",
}
_DEFAULT_VOICE = "ko-KR-SunHiNeural"


def _speed_to_rate(speed: float) -> str:
    """OpenAI speed(0.25~4.0) → edge-tts rate(±%) 변환."""
    pct = int((speed - 1.0) * 100)
    if pct >= 0:
        return f"+{pct}%"
    return f"{pct}%"

def _apply_ssml_by_role(text: str, role: str) -> str:
    """역할에 따른 SSML 태그 주입 (Raw 텍스트 이스케이프 포함).

    Phase 4-B: Enhanced role-based SSML with emphasis and breath pauses.
    """
    import xml.sax.saxutils
    safe_text = xml.sax.saxutils.escape(text)
    if role == "hook":
        # Hook: 빠르고 높은 톤 + 강조 → 시선 집중
        return (
            f'<prosody rate="+15%" pitch="+8Hz">'
            f'<emphasis level="strong">{safe_text}</emphasis>'
            f'</prosody>'
        )
    elif role == "cta":
        # CTA: 느리고 명확 + 강조 → 행동 유도
        return (
            f'<break time="300ms"/>'
            f'<prosody rate="-10%" pitch="+5Hz">'
            f'<emphasis level="moderate">{safe_text}</emphasis>'
            f'</prosody>'
        )
    else:
        # Body: 자연스러운 톤, 문장 사이 미세 호흡
        return safe_text.replace(". ", '.<break time="200ms"/> ')


def _approximate_word_timings(ssml_text: str, audio_path: Path) -> list[dict]:
    """WordBoundary 이벤트 미수신 시 오디오 길이 기반 근사 단어 타이밍 생성.

    SSML 태그를 제거하고 순수 텍스트를 추출한 뒤,
    오디오 총 길이를 단어 수로 균등 분배합니다.
    """
    import re
    # SSML 태그 제거 → 순수 텍스트 추출
    plain = re.sub(r"<[^>]+>", " ", ssml_text)
    plain = re.sub(r"\s+", " ", plain).strip()
    if not plain:
        return []

    # 한국어: 공백 + 조사 경계로 분리, 영어: 공백 분리
    words = [w for w in plain.split() if w.strip()]
    if not words:
        return []

    # 오디오 길이 읽기
    try:
        from mutagen.mp3 import MP3
        audio_dur = MP3(str(audio_path)).info.length
    except Exception:
        return []

    if audio_dur <= 0:
        return []

    # 한글 음절 수 기반 가중 분배 (한글이 영문보다 발화 시간이 긺)
    def _weight(word: str) -> float:
        hangul = len(re.findall(r"[가-힣]", word))
        latin = len(re.findall(r"[A-Za-z0-9]", word))
        return max(1.0, hangul * 1.0 + latin * 0.5)

    weights = [_weight(w) for w in words]
    total_weight = sum(weights)

    result: list[dict] = []
    cursor = 0.0
    for w, wt in zip(words, weights):
        dur = (wt / total_weight) * audio_dur
        result.append({
            "word": w,
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
    """TTS 음성 생성 + WordBoundary 이벤트로 단어별 타이밍 추출.

    edge-tts의 WordBoundary 이벤트를 캡처하여 Whisper 없이도
    정확한 단어별 시작/종료 시간을 _words.json으로 저장합니다.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    words_json_path.parent.mkdir(parents=True, exist_ok=True)

    communicate = SSMLCommunicate(text, voice=voice, rate=rate)
    words: list[dict] = []

    # stream()으로 오디오 + WordBoundary 이벤트를 동시에 수신
    audio_chunks: list[bytes] = []
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_chunks.append(chunk["data"])
        elif chunk["type"] == "WordBoundary":
            # offset: hundred-nanoseconds (HNS), duration: HNS
            offset_sec = chunk["offset"] / 10_000_000
            duration_sec = chunk["duration"] / 10_000_000
            words.append({
                "word": chunk["text"],
                "start": round(offset_sec, 4),
                "end": round(offset_sec + duration_sec, 4),
            })

    # 오디오 파일 저장
    with output_path.open("wb") as f:
        for data in audio_chunks:
            f.write(data)

    # 단어 타이밍 JSON 저장
    if words:
        words_json_path.write_text(
            json.dumps(words, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info("EdgeTTS: %d word timings saved to %s", len(words), words_json_path)
    else:
        # WordBoundary 이벤트 미수신 (SSML 사용 시 발생 가능) → 근사 타이밍 생성
        approx = _approximate_word_timings(text, output_path)
        if approx:
            words_json_path.write_text(
                json.dumps(approx, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            logger.info(
                "EdgeTTS: WordBoundary 미수신, 근사 타이밍 %d words 생성: %s",
                len(approx), words_json_path,
            )

    # Phase 2: SSML 원문 저장 → render_step의 apply_ssml_break_correction에서 활용
    ssml_txt_path = words_json_path.parent / f"{words_json_path.stem}_ssml.txt"
    ssml_txt_path.write_text(text, encoding="utf-8")



class EdgeTTSClient:
    """Microsoft edge-tts 래퍼 — OpenAIClient.generate_tts()와 호환."""

    def generate_tts(
        self,
        *,
        model: str,      # 사용 안 함 (호환성 유지)
        voice: str,
        speed: float,
        text: str,
        output_path: Path,
        words_json_path: Path | None = None,
        role: str = "body",
    ) -> Path:
        """edge-tts로 TTS 생성. 파일이 이미 존재하면 스킵.

        Args:
            words_json_path: 지정 시 WordBoundary 이벤트로 단어별
                타이밍을 _words.json으로 저장합니다.
        """
        if output_path.exists():
            return output_path

        # OpenAI 음성 이름을 edge-tts 음성으로 변환 (Neural 포함된 이름은 직접 사용)
        if "Neural" in voice or "neural" in voice:
            edge_voice = voice
        else:
            edge_voice = _OPENAI_TO_EDGE_VOICE.get(voice, _DEFAULT_VOICE)

        rate = _speed_to_rate(speed)
        ssml_text = _apply_ssml_by_role(text, role)
        logger.info("EdgeTTS: voice=%s rate=%s text_len=%d role=%s", edge_voice, rate, len(text), role)

        def _make_coro():
            if words_json_path is not None:
                return _generate_async_with_timing(ssml_text, edge_voice, rate, output_path, words_json_path)
            return _generate_async(ssml_text, edge_voice, rate, output_path)

        # Phase 1-D: asyncio.run() creates a fresh loop — safe in threads.
        # Fallback to dedicated thread only when called from an already-running loop.
        try:
            asyncio.run(_make_coro())
        except RuntimeError:
            # "cannot be called from a running event loop" — delegate to new thread
            # Must create a fresh coroutine since the previous one was consumed
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(asyncio.run, _make_coro())
                future.result()

        logger.info("EdgeTTS: saved %s", output_path)
        return output_path
