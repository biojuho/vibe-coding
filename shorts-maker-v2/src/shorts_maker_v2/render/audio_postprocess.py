"""TTS 음성 후처리 — 노멀라이제이션 + EQ 프리셋.

pydub 기반. 없으면 graceful fallback (원본 반환).
"""
from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


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
    try:
        from pydub import AudioSegment
    except ImportError:
        logger.debug("[AudioPost] pydub 없음, 노멀라이제이션 건너뜀")
        return audio_path

    try:
        ext = audio_path.suffix.lower().lstrip(".")
        audio = AudioSegment.from_file(str(audio_path), format=ext if ext else "mp3")

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
            audio_path.name, current_dbfs, target_lufs, gain_needed,
        )
        return audio_path

    except Exception as exc:
        logger.warning("[AudioPost] 노멀라이제이션 실패: %s — %s", audio_path.name, exc)
        return audio_path


# ── EQ 프리셋 ──────────────────────────────────────────────────────────────────

# EQ bands: (low_freq, high_freq, gain_db)
EQ_PRESETS: dict[str, list[tuple[int, int, float]]] = {
    "male_voice": [
        (80, 250, 3.0),     # 저음 풍성하게
        (250, 1000, 1.0),   # 중저음 약간 부스트
        (2000, 4000, 2.0),  # 명료도 향상
        (6000, 12000, -1.0), # 치찰음 억제
    ],
    "female_voice": [
        (80, 200, -1.0),    # 저음 약간 컷
        (200, 800, 1.5),    # 중음 따뜻하게
        (2000, 4000, 3.0),  # 명료도 + 존재감
        (8000, 16000, 1.0), # 에어리 질감
    ],
    "neutral": [
        (100, 300, 1.0),    # 저음 약간 부스트
        (1000, 3000, 1.5),  # 명료도
        (5000, 10000, -0.5), # 하이 약간 컷
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
    try:
        from pydub import AudioSegment
        from pydub.effects import low_pass_filter, high_pass_filter
    except ImportError:
        logger.debug("[AudioPost] pydub 없음, EQ 건너뜀")
        return audio_path

    bands = EQ_PRESETS.get(preset, EQ_PRESETS["neutral"])
    if not bands:
        return audio_path

    try:
        ext = audio_path.suffix.lower().lstrip(".")
        audio = AudioSegment.from_file(str(audio_path), format=ext if ext else "mp3")

        # 간이 EQ: 전체 대역에 high_pass → low_pass 범위의 gain 적용
        # pydub 한계로 정밀 밴드 EQ는 불가, 주요 대역만 gain 조정
        for low_freq, high_freq, gain_db in bands:
            if abs(gain_db) < 0.3:
                continue
            # 해당 대역을 추출 (근사)
            band = high_pass_filter(audio, low_freq)
            band = low_pass_filter(band, high_freq)
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


def postprocess_tts_audio(
    audio_path: Path,
    voice_name: str = "",
    *,
    normalize: bool = True,
    eq_enabled: bool = True,
    target_lufs: float = -14.0,
) -> Path:
    """TTS 오디오 후처리 파이프라인 (노멀라이즈 + EQ).

    Args:
        audio_path: TTS 출력 오디오 파일.
        voice_name: EdgeTTS 음성 이름 (EQ 프리셋 자동 선택용).
        normalize: 라우드니스 노멀라이제이션 활성화.
        eq_enabled: EQ 적용 활성화.
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

    return audio_path
