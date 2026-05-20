"""OpenVoice v2 TTS client.

MyShell OpenVoice V2 오픈소스 Voice Cloning & TTS (MIT 라이선스).
MeloTTS를 Base로 하고 ToneColorConverter를 활용해 타겟 목소리로 합성.
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_model_cache: dict[str, object] = {}


def _get_converter(checkpoint_dir: str = "checkpoints_v2/converter", device: str = "cpu") -> object:
    """Lazy-load ToneColorConverter."""
    cache_key = f"converter_{checkpoint_dir}_{device}"
    if cache_key not in _model_cache:
        try:
            from openvoice.api import ToneColorConverter

            config_path = Path(checkpoint_dir) / "config.json"
            ckpt_path = Path(checkpoint_dir) / "checkpoint.pth"

            if not config_path.exists() or not ckpt_path.exists():
                raise FileNotFoundError(
                    f"OpenVoice v2 컨버터 체크포인트가 없습니다: {checkpoint_dir}. "
                    "config.json 및 checkpoint.pth가 해당 경로에 있어야 합니다."
                )

            converter = ToneColorConverter(str(config_path), device=device)
            converter.load_ckpt(str(ckpt_path))
            _model_cache[cache_key] = converter
            logger.info("[OpenVoice] ToneColorConverter 로드 완료: %s", checkpoint_dir)
        except ImportError as exc:
            raise ImportError("openvoice 패키지가 설치되지 않았습니다.") from exc
    return _model_cache[cache_key]


def _get_base_tts(language: str = "KR", device: str = "cpu") -> object:
    """Lazy-load MeloTTS."""
    cache_key = f"melo_{language}_{device}"
    if cache_key not in _model_cache:
        try:
            from melo.api import TTS

            # ko-KR 등은 KR로 매핑
            lang_code = "KR" if "KO" in language.upper() else "EN"
            if language.upper() in {"ZH", "CN"}:
                lang_code = "ZH"
            elif language.upper() in {"JA", "JP"}:
                lang_code = "JP"
            elif language.upper() in {"ES"}:
                lang_code = "ES"
            elif language.upper() in {"FR"}:
                lang_code = "FR"

            tts_model = TTS(language=lang_code, device=device)
            _model_cache[cache_key] = tts_model
            logger.info("[OpenVoice] MeloTTS %s 로드 완료", lang_code)
        except ImportError as exc:
            raise ImportError("melo 패키지(MeloTTS)가 설치되지 않았습니다.") from exc
    return _model_cache[cache_key]


class OpenVoiceTTSClient:
    """OpenVoice v2 Voice Cloning TTS Client."""

    def __init__(
        self,
        *,
        checkpoint_dir: str = "checkpoints_v2",
        ref_audio_path: str | Path | None = None,
        device: str | None = None,
    ) -> None:
        self._checkpoint_dir = checkpoint_dir
        self._ref_audio_path = str(ref_audio_path) if ref_audio_path else None

        import torch

        if device is None:
            self._device = "cuda:0" if torch.cuda.is_available() else "cpu"
        else:
            self._device = device

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
        """텍스트를 음성으로 변환하고 타겟 목소리로 톤 변환하여 저장."""
        del model, voice, role, channel_key  # OpenVoice는 복제 모델이므로 reference audio 대체

        if output_path.exists() and output_path.stat().st_size > 0:
            return output_path

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.unlink(missing_ok=True)

        # 1. 모델 준비
        converter_path = Path(self._checkpoint_dir) / "converter"
        converter = _get_converter(str(converter_path), device=self._device)

        lang_map = {
            "ko-KR": "KR",
            "en-US": "EN",
            "ja-JP": "JP",
            "zh-CN": "ZH",
        }
        lang_code = lang_map.get(language, "KR")
        base_tts = _get_base_tts(lang_code, device=self._device)

        # 2. Reference Speaker SE 추출
        ref_wav = self._ref_audio_path or self._get_default_ref_audio()
        if not ref_wav:
            raise FileNotFoundError("OpenVoice: reference audio(참조 목소리) 파일이 없습니다.")

        from openvoice import se_extractor

        target_se, _ = se_extractor.get_se(ref_wav, converter, vad=True)

        # 3. Base TTS로 임시 오디오 생성
        base_output_path = output_path.parent / f"{output_path.stem}_base.wav"
        base_output_path.unlink(missing_ok=True)

        speaker_ids = base_tts.hps.data.spk2id
        # 해당 언어의 기본 화자 탐색 (예: 'KR-Default', 'EN-Default' 등)
        base_speaker_key = f"{lang_code}-Default"
        if base_speaker_key not in speaker_ids:
            # 존재하지 않으면 첫 번째 화자 사용
            base_speaker_key = list(speaker_ids.keys())[0]

        base_tts.tts_to_file(text, speaker_ids[base_speaker_key], str(base_output_path), speed=speed)

        # 4. 톤 컬러 변환 (OpenVoice v2 Cloning)
        converter.convert(
            audio_src_path=str(base_output_path),
            src_se=None,
            tgt_se=target_se,
            output_path=str(output_path),
            message="@MyShell",
        )

        # 임시 base audio 삭제
        base_output_path.unlink(missing_ok=True)

        # 5. Whisper로 단어 타이밍 추출 (자막 동기화)
        if words_json_path is not None:
            self._generate_word_timings(output_path, text, words_json_path, language)

        logger.info("[OpenVoice] 음성 복제 완료: %s", output_path)
        return output_path

    @staticmethod
    def _get_default_ref_audio() -> str | None:
        candidates = [
            Path("assets/ref_voice/korean_female.wav"),
            Path("assets/ref_voice/korean_male.wav"),
        ]
        for p in candidates:
            if p.exists():
                return str(p)
        return None

    @staticmethod
    def _generate_word_timings(
        audio_path: Path,
        text: str,
        words_json_path: Path,
        language: str,
    ) -> None:
        import json

        words_json_path.parent.mkdir(parents=True, exist_ok=True)

        # 1순위: whisper_aligner 로컬
        try:
            from shorts_maker_v2.providers.whisper_aligner import (
                is_whisper_available,
                transcribe_to_word_timings,
            )

            if is_whisper_available():
                words = transcribe_to_word_timings(audio_path, language=language)
                if words:
                    words_json_path.write_text(json.dumps(words, ensure_ascii=False, indent=2), encoding="utf-8")
                    logger.info("[OpenVoice] whisper 타이밍 %d words 추출 성공", len(words))
                    return
        except Exception as exc:
            logger.debug("[OpenVoice] whisper_aligner 실패: %s", exc)

        # 2순위: edge_tts 근사치 fallback
        try:
            from shorts_maker_v2.providers.edge_tts_client import _approximate_word_timings

            approx = _approximate_word_timings(text, audio_path)
            if approx:
                words_json_path.write_text(json.dumps(approx, ensure_ascii=False, indent=2), encoding="utf-8")
                logger.info("[OpenVoice] 근사치 타이밍 %d words 추출 성공", len(approx))
        except Exception as exc:
            logger.debug("[OpenVoice] 근사치 타이밍 실패: %s", exc)


def is_openvoice_available() -> bool:
    try:
        from melo.api import TTS  # noqa: F401
        from openvoice.api import ToneColorConverter  # noqa: F401

        return True
    except ImportError:
        return False
