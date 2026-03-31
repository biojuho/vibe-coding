"""Chatterbox Multilingual TTS client.

Resemble AI의 오픈소스 다국어 TTS (MIT 라이선스).
23개 언어 지원, 제로샷 음성 클로닝, GPU 4-8GB VRAM.

설치: pip install chatterbox-tts
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_LANGUAGE_MAP: dict[str, str] = {
    "ko-KR": "ko",
    "en-US": "en",
    "ja-JP": "ja",
    "zh-CN": "zh",
    "es-ES": "es",
    "fr-FR": "fr",
    "de-DE": "de",
    "pt-BR": "pt",
    "ru-RU": "ru",
    "hi-IN": "hi",
    "ar-SA": "ar",
    "it-IT": "it",
    "nl-NL": "nl",
    "pl-PL": "pl",
    "sv-SE": "sv",
    "tr-TR": "tr",
}

_model_cache: dict[str, object] = {}


def _get_model():
    """Lazy-load ChatterboxMultilingualTTS (한 번만 로드)."""
    if "mtl" not in _model_cache:
        try:
            import torch
            from chatterbox.mtl_tts import ChatterboxMultilingualTTS

            device = "cuda" if torch.cuda.is_available() else "cpu"
            if device == "cpu":
                logger.warning("[ChatterboxTTS] GPU 미감지 — CPU 모드 (느림)")

            model = ChatterboxMultilingualTTS.from_pretrained(device=device)
            _model_cache["mtl"] = model
            logger.info("[ChatterboxTTS] 모델 로드 완료 (device=%s)", device)
        except ImportError as exc:
            raise ImportError("chatterbox-tts가 설치되지 않았습니다. 설치: pip install chatterbox-tts") from exc
    return _model_cache["mtl"]


class ChatterboxTTSClient:
    """OpenAIClient.generate_tts() 호환 인터페이스.

    config.yaml에서 providers.tts: "chatterbox" 로 설정.
    """

    def __init__(
        self,
        *,
        ref_audio_path: str | Path | None = None,
        exaggeration: float = 0.5,
        cfg_weight: float = 0.5,
    ) -> None:
        self._ref_audio_path = str(ref_audio_path) if ref_audio_path else None
        self._exaggeration = exaggeration
        self._cfg_weight = cfg_weight

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
        """텍스트를 음성으로 변환하여 WAV/MP3로 저장."""
        del model, voice, speed  # Chatterbox는 자체 음성 사용

        if output_path.exists() and output_path.stat().st_size > 0:
            return output_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.unlink(missing_ok=True)

        import torchaudio

        mtl_model = _get_model()
        lang_id = _LANGUAGE_MAP.get(language, "ko")

        # 역할별 표현력 조절
        exaggeration = self._exaggeration
        if role == "hook":
            exaggeration = min(1.0, exaggeration + 0.2)
        elif role == "closing":
            exaggeration = max(0.1, exaggeration - 0.2)

        logger.info(
            "[ChatterboxTTS] lang=%s role=%s exaggeration=%.1f text_len=%d",
            lang_id,
            role,
            exaggeration,
            len(text),
        )

        wav = mtl_model.generate(
            text,
            language_id=lang_id,
            audio_prompt_path=self._ref_audio_path,
            exaggeration=exaggeration,
            cfg_weight=self._cfg_weight,
        )

        # WAV로 저장 (mp3 확장자여도 WAV로 저장 후 후처리에서 변환)
        wav_path = output_path.with_suffix(".wav")
        torchaudio.save(str(wav_path), wav, mtl_model.sr)

        # MP3로 변환 (output_path가 .mp3인 경우)
        if output_path.suffix.lower() == ".mp3":
            try:
                from pydub import AudioSegment

                audio = AudioSegment.from_wav(str(wav_path))
                audio.export(str(output_path), format="mp3")
                wav_path.unlink(missing_ok=True)
            except ImportError:
                # pydub 없으면 WAV 그대로 사용
                output_path = wav_path
                logger.debug("[ChatterboxTTS] pydub 미설치, WAV 사용")
        else:
            output_path = wav_path

        # Whisper로 단어 타이밍 추출 (WordBoundary 미지원)
        if words_json_path is not None:
            self._generate_word_timings(output_path, text, words_json_path, language)

        logger.info("[ChatterboxTTS] 생성 완료: %s", output_path)
        return output_path

    @staticmethod
    def _generate_word_timings(
        audio_path: Path,
        text: str,
        words_json_path: Path,
        language: str,
    ) -> None:
        """Whisper → 근사치 fallback으로 단어 타이밍 생성."""
        import json

        words_json_path.parent.mkdir(parents=True, exist_ok=True)

        # 1순위: faster-whisper
        try:
            from shorts_maker_v2.providers.whisper_aligner import (
                is_whisper_available,
                transcribe_to_word_timings,
            )

            if is_whisper_available():
                words = transcribe_to_word_timings(audio_path, language=language)
                if words:
                    words_json_path.write_text(
                        json.dumps(words, ensure_ascii=False, indent=2),
                        encoding="utf-8",
                    )
                    logger.info(
                        "[ChatterboxTTS] whisper 타이밍 %d words: %s",
                        len(words),
                        words_json_path,
                    )
                    return
        except Exception as exc:
            logger.debug("[ChatterboxTTS] whisper fallback 실패: %s", exc)

        # 2순위: 근사치 (edge_tts_client의 로직 재사용)
        try:
            from shorts_maker_v2.providers.edge_tts_client import (
                _approximate_word_timings,
            )

            approx = _approximate_word_timings(text, audio_path)
            if approx:
                words_json_path.write_text(
                    json.dumps(approx, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                logger.info(
                    "[ChatterboxTTS] 근사 타이밍 %d words: %s",
                    len(approx),
                    words_json_path,
                )
        except Exception as exc:
            logger.debug("[ChatterboxTTS] 근사 타이밍 실패: %s", exc)


def is_chatterbox_available() -> bool:
    """chatterbox-tts 패키지 설치 여부 확인."""
    try:
        import chatterbox.mtl_tts  # noqa: F401

        return True
    except ImportError:
        return False
