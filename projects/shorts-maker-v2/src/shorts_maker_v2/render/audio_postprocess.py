"""TTS 음성 후처리 — 노멀라이제이션 + EQ 프리셋.

pydub 기반. 없으면 graceful fallback (원본 반환).
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_PYDUB_UNSET = object()
AudioSegment = _PYDUB_UNSET
high_pass_filter = _PYDUB_UNSET
low_pass_filter = _PYDUB_UNSET


def _resolve_pydub():
    audio_segment = None if AudioSegment is _PYDUB_UNSET else AudioSegment
    high_pass = None if high_pass_filter is _PYDUB_UNSET else high_pass_filter
    low_pass = None if low_pass_filter is _PYDUB_UNSET else low_pass_filter

    if audio_segment is not None and high_pass is not None and low_pass is not None:
        return audio_segment, high_pass, low_pass

    try:
        from pydub import AudioSegment as imported_audio_segment
        from pydub.effects import (
            high_pass_filter as imported_high_pass_filter,
            low_pass_filter as imported_low_pass_filter,
        )
    except ImportError:
        return audio_segment, high_pass, low_pass

    return (
        audio_segment or imported_audio_segment,
        high_pass or imported_high_pass_filter,
        low_pass or imported_low_pass_filter,
    )


def normalize_audio(
    audio_path: Path,
    target_lufs: float = -14.0,
) -> Path:
    """음성 파일의 라우드니스를 YouTube 권장 -14 LUFS로 노멀라이즈.

    pydub의 dBFS 기반 간이 노멀라이제이션 (true LUFS는 아니지만 충분한 근사).

    Args:
        audio_path: 입력 오디오 파일 경로 (mp3/wav).
        target_lufs: 목표 라우드니스 (dBFS 근사). 기본 -14.

    Returns:
        노멀라이즈된 오디오 파일 경로 (in-place).
    """
    audio_segment, _, _ = _resolve_pydub()
    if audio_segment is None:
        logger.debug("[AudioPost] pydub 없음, 노멀라이제이션 건너뜀")
        return audio_path

    try:
        ext = audio_path.suffix.lower().lstrip(".")
        audio = audio_segment.from_file(str(audio_path), format=ext if ext else "mp3")

        current_dbfs = audio.dBFS
        if current_dbfs == float("-inf"):
            logger.warning("[AudioPost] 무음 파일, 노멀라이제이션 건너뜀: %s", audio_path.name)
            return audio_path

        gain_needed = target_lufs - current_dbfs
        # 과도한 증폭 방지 (최대 +20dB)
        gain_needed = max(-20.0, min(20.0, gain_needed))

        if abs(gain_needed) < 0.5:
            logger.debug("[AudioPost] 노멀라이제이션 불필요 (차이 %.1fdB): %s", gain_needed, audio_path.name)
            return audio_path

        normalized = audio.apply_gain(gain_needed)
        normalized.export(str(audio_path), format=ext if ext else "mp3")
        logger.info(
            "[AudioPost] 노멀라이즈 완료: %s (%.1f → %.1f dBFS, gain=%.1fdB)",
            audio_path.name,
            current_dbfs,
            target_lufs,
            gain_needed,
        )
        return audio_path

    except Exception as exc:
        logger.warning("[AudioPost] 노멀라이제이션 실패: %s — %s", audio_path.name, exc)
        return audio_path


# ── EQ 프리셋 ──────────────────────────────────────────────────────────────────

# EQ bands: (low_freq, high_freq, gain_db)
EQ_PRESETS: dict[str, list[tuple[int, int, float]]] = {
    "male_voice": [
        (80, 250, 3.0),  # 저음 풍성하게
        (250, 1000, 1.0),  # 중저음 약간 부스트
        (2000, 4000, 2.0),  # 명료도 향상
        (6000, 12000, -1.0),  # 치찰음 억제
    ],
    "female_voice": [
        (80, 200, -1.0),  # 저음 약간 컷
        (200, 800, 1.5),  # 중음 따뜻하게
        (2000, 4000, 3.0),  # 명료도 + 존재감
        (8000, 16000, 1.0),  # 에어리 질감
    ],
    "neutral": [
        (100, 300, 1.0),  # 저음 약간 부스트
        (1000, 3000, 1.5),  # 명료도
        (5000, 10000, -0.5),  # 하이 약간 컷
    ],
}


def apply_eq(
    audio_path: Path,
    preset: str = "neutral",
) -> Path:
    """pydub 기반 간이 EQ 적용.

    pydub는 band-pass EQ를 직접 지원하지 않으므로,
    low_pass/high_pass 필터와 gain 조합으로 근사.

    Args:
        audio_path: 입력 오디오 파일 경로.
        preset: EQ 프리셋 ("male_voice" | "female_voice" | "neutral").

    Returns:
        EQ 적용된 오디오 파일 경로 (in-place).
    """
    audio_segment, high_pass, low_pass = _resolve_pydub()
    if audio_segment is None or high_pass is None or low_pass is None:
        logger.debug("[AudioPost] pydub 없음, EQ 건너뜀")
        return audio_path

    bands = EQ_PRESETS.get(preset, EQ_PRESETS["neutral"])
    if not bands:
        return audio_path

    try:
        ext = audio_path.suffix.lower().lstrip(".")
        audio = audio_segment.from_file(str(audio_path), format=ext if ext else "mp3")

        # 간이 EQ: 전체 대역에 high_pass → low_pass 범위의 gain 적용
        # pydub 한계로 정밀 밴드 EQ는 불가, 주요 대역만 gain 조정
        for low_freq, high_freq, gain_db in bands:
            if abs(gain_db) < 0.3:
                continue
            # 해당 대역을 추출 (근사)
            band = high_pass(audio, low_freq)
            band = low_pass(band, high_freq)
            band = band.apply_gain(gain_db)
            # 원본에 블렌딩 (overlay)
            audio = audio.overlay(band, gain_during_overlay=0)

        audio.export(str(audio_path), format=ext if ext else "mp3")
        logger.info("[AudioPost] EQ 적용 완료: %s (preset=%s)", audio_path.name, preset)
        return audio_path

    except Exception as exc:
        logger.warning("[AudioPost] EQ 적용 실패: %s — %s", audio_path.name, exc)
        return audio_path


def detect_voice_gender(voice_name: str) -> str:
    """EdgeTTS 음성 이름으로 성별 추론 → EQ 프리셋 매핑.

    Returns: "male_voice" | "female_voice" | "neutral"
    """
    female_voices = {"SunHi", "SoonBok"}
    male_voices = {"InJoon", "Hyunsu", "BongJin", "GookMin"}
    for name in female_voices:
        if name.lower() in voice_name.lower():
            return "female_voice"
    for name in male_voices:
        if name.lower() in voice_name.lower():
            return "male_voice"
    return "neutral"


def _apply_compression(
    audio_path: Path,
    *,
    threshold_db: float = -20.0,
    ratio: float = 3.0,
    attack_ms: float = 5.0,
    release_ms: float = 50.0,
) -> Path:
    """간이 컴프레서: 다이나믹 레인지를 줄여 음량 일관성 향상.

    pydub는 전문 컴프레서를 지원하지 않으므로,
    세그먼트 단위로 소프트 리미팅을 적용하는 근사 방식.
    """
    audio_segment, _, _ = _resolve_pydub()
    if audio_segment is None:
        logger.debug("[AudioPost] pydub 없음, 컴프레서 건너뜀")
        return audio_path

    try:
        ext = audio_path.suffix.lower().lstrip(".")
        audio = audio_segment.from_file(str(audio_path), format=ext if ext else "mp3")

        # 50ms 청크 단위로 소프트 리미팅
        chunk_ms = 50
        chunks = [audio[i : i + chunk_ms] for i in range(0, len(audio), chunk_ms)]
        compressed_chunks = []
        for chunk in chunks:
            if chunk.dBFS > threshold_db:
                # threshold 초과분을 ratio로 감쇠
                overshoot = chunk.dBFS - threshold_db
                gain_reduction = overshoot * (ratio - 1) / ratio
                chunk = chunk.apply_gain(-gain_reduction)
            compressed_chunks.append(chunk)

        compressed = sum(compressed_chunks[1:], compressed_chunks[0]) if compressed_chunks else audio
        compressed.export(str(audio_path), format=ext if ext else "mp3")
        logger.info(
            "[AudioPost] 컴프레서 적용: %s (threshold=%.0fdB, ratio=%.1f)", audio_path.name, threshold_db, ratio
        )
        return audio_path

    except Exception as exc:
        logger.warning("[AudioPost] 컴프레서 실패: %s — %s", audio_path.name, exc)
        return audio_path


def _apply_subtle_reverb(
    audio_path: Path,
    *,
    room_size: float = 0.15,
    wet_mix: float = 0.08,
) -> Path:
    """미량 리버브: 드라이한 AI 음성에 자연스러운 공간감 추가.

    pydub 기반 간이 리버브 (원본에 0.08 비율로 살짝 딜레이된 복사본 믹스).
    전문 리버브 대비 품질은 낮지만, AI 음성의 '무무방향' 느낌을 줄여줌.
    """
    audio_segment, _, _ = _resolve_pydub()
    if audio_segment is None:
        logger.debug("[AudioPost] pydub 없음, 리버브 건너뜀")
        return audio_path

    try:
        ext = audio_path.suffix.lower().lstrip(".")
        audio = audio_segment.from_file(str(audio_path), format=ext if ext else "mp3")

        # 미세 딜레이(25ms, 50ms)를 겹쳐 공간감 생성
        delay_1 = audio_segment.silent(duration=25, frame_rate=audio.frame_rate) + audio
        delay_2 = audio_segment.silent(duration=50, frame_rate=audio.frame_rate) + audio

        # 원본 길이에 맞춰 트림
        target_len = len(audio)
        delay_1 = delay_1[:target_len]
        delay_2 = delay_2[:target_len]

        # wet 신호: 딜레이 두 개를 혼합 후 감쇠 (-18dB, -22dB 고정)
        reverbed = audio.overlay(delay_1.apply_gain(-18)).overlay(delay_2.apply_gain(-22))
        reverbed.export(str(audio_path), format=ext if ext else "mp3")
        logger.info("[AudioPost] 리버브 적용: %s (room=%.2f, wet=%.2f)", audio_path.name, room_size, wet_mix)
        return audio_path

    except Exception as exc:
        logger.warning("[AudioPost] 리버브 실패: %s — %s", audio_path.name, exc)
        return audio_path


def postprocess_tts_audio(
    audio_path: Path,
    voice_name: str = "",
    *,
    normalize: bool = True,
    eq_enabled: bool = True,
    compress: bool = True,
    reverb: bool = True,
    target_lufs: float = -14.0,
) -> Path:
    """TTS 오디오 후처리 파이프라인 (노멀라이즈 + EQ + 컴프레서 + 리버브).

    Args:
        audio_path: TTS 출력 오디오 파일.
        voice_name: EdgeTTS 음성 이름 (EQ 프리셋 자동 선택용).
        normalize: 라우드니스 노멀라이제이션 활성화.
        eq_enabled: EQ 적용 활성화.
        compress: 컴프레서 적용 (다이나믹 레인지 축소).
        reverb: 미량 리버브 적용 (공간감 추가).
        target_lufs: 목표 라우드니스.

    Returns:
        후처리된 오디오 파일 경로.
    """
    if not audio_path.exists():
        return audio_path

    if normalize:
        audio_path = normalize_audio(audio_path, target_lufs)

    if eq_enabled and voice_name:
        preset = detect_voice_gender(voice_name)
        audio_path = apply_eq(audio_path, preset)

    if compress:
        audio_path = _apply_compression(audio_path)

    if reverb:
        audio_path = _apply_subtle_reverb(audio_path)

    return audio_path
