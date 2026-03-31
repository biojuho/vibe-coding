"""CosyVoice 2/3 TTS client.

Alibaba FunAudioLLM 오픈소스 TTS (Apache 2.0 라이선스).
9개+ 언어 지원, 제로샷 음성 클로닝, 스트리밍 150ms.

설치: git clone https://github.com/FunAudioLLM/CosyVoice.git
      pip install -r requirements.txt
모델: huggingface_hub로 다운로드 (CosyVoice2-0.5B 또는 Fun-CosyVoice3-0.5B)
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_LANGUAGE_TAGS: dict[str, str] = {
    "ko-KR": "<|ko|>",
    "en-US": "<|en|>",
    "ja-JP": "<|ja|>",
    "zh-CN": "<|zh|>",
    "yue-CN": "<|yue|>",
}

_model_cache: dict[str, object] = {}


def _get_model(model_dir: str = "pretrained_models/CosyVoice2-0.5B"):
    """Lazy-load CosyVoice 모델 (한 번만 로드)."""
    if "cosyvoice" not in _model_cache:
        try:
            from cosyvoice.cli.cosyvoice import AutoModel

            cosyvoice = AutoModel(model_dir=model_dir)
            _model_cache["cosyvoice"] = cosyvoice
            logger.info("[CosyVoice] 모델 로드 완료: %s", model_dir)
        except ImportError as exc:
            raise ImportError(
                "CosyVoice가 설치되지 않았습니다. "
                "설치: git clone https://github.com/FunAudioLLM/CosyVoice.git && "
                "pip install -r requirements.txt"
            ) from exc
    return _model_cache["cosyvoice"]


class CosyVoiceTTSClient:
    """OpenAIClient.generate_tts() 호환 인터페이스.

    config.yaml에서 providers.tts: "cosyvoice" 로 설정.

    사용 모드:
    1. cross_lingual: 언어 태그로 다국어 TTS (기본)
    2. zero_shot: 참조 오디오 기반 음성 클로닝
    3. instruct: 텍스트 지시로 스타일 제어
    """

    def __init__(
        self,
        *,
        model_dir: str = "pretrained_models/CosyVoice2-0.5B",
        ref_audio_path: str | Path | None = None,
        ref_audio_text: str = "",
        speaker_id: str = "",
        mode: str = "cross_lingual",
    ) -> None:
        self._model_dir = model_dir
        self._ref_audio_path = str(ref_audio_path) if ref_audio_path else None
        self._ref_audio_text = ref_audio_text
        self._speaker_id = speaker_id
        self._mode = mode  # cross_lingual | zero_shot | instruct

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
        del model, voice, speed  # CosyVoice는 자체 설정 사용

        if output_path.exists() and output_path.stat().st_size > 0:
            return output_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.unlink(missing_ok=True)

        import torch
        import torchaudio

        cosyvoice = _get_model(self._model_dir)
        lang_tag = _LANGUAGE_TAGS.get(language, "<|ko|>")

        logger.info(
            "[CosyVoice] mode=%s lang=%s role=%s text_len=%d",
            self._mode, lang_tag, role, len(text),
        )

        # 모드별 추론
        audio_tensors: list[torch.Tensor] = []

        if self._mode == "zero_shot" and self._ref_audio_path:
            # 제로샷 음성 클로닝
            if self._speaker_id:
                # 저장된 스피커 ID 사용
                for result in cosyvoice.inference_zero_shot(
                    text, "", "",
                    zero_shot_spk_id=self._speaker_id,
                    stream=False,
                ):
                    audio_tensors.append(result["tts_speech"])
            else:
                for result in cosyvoice.inference_zero_shot(
                    text,
                    self._ref_audio_text,
                    self._ref_audio_path,
                    stream=False,
                ):
                    audio_tensors.append(result["tts_speech"])

        elif self._mode == "instruct":
            # 텍스트 지시 기반 스타일 제어
            instruct_text = self._get_instruct_text(role, channel_key)
            for result in cosyvoice.inference_instruct2(
                text,
                instruct_text,
                self._ref_audio_path or "",
                stream=False,
            ):
                audio_tensors.append(result["tts_speech"])

        else:
            # cross_lingual (기본): 언어 태그 + 참조 오디오
            tagged_text = f"{lang_tag}{text}"
            ref_wav = self._ref_audio_path or self._get_default_ref_audio()
            if ref_wav:
                for result in cosyvoice.inference_cross_lingual(
                    tagged_text, ref_wav,
                    stream=False,
                ):
                    audio_tensors.append(result["tts_speech"])
            else:
                # 참조 오디오 없으면 SFT 모드 fallback
                sft_voices = getattr(cosyvoice, "list_available_spks", lambda: [])()
                sft_voice = sft_voices[0] if sft_voices else None
                if sft_voice:
                    for result in cosyvoice.inference_sft(
                        text, sft_voice, stream=False,
                    ):
                        audio_tensors.append(result["tts_speech"])
                else:
                    raise RuntimeError(
                        "CosyVoice: 참조 오디오가 필요합니다 "
                        "(config.yaml에 providers.tts_ref_audio 설정)"
                    )

        if not audio_tensors:
            raise RuntimeError("CosyVoice: 음성 생성 결과 없음")

        # 청크들을 결합
        combined = torch.cat(audio_tensors, dim=-1)
        sample_rate = cosyvoice.sample_rate

        # WAV로 저장
        wav_path = output_path.with_suffix(".wav")
        torchaudio.save(str(wav_path), combined, sample_rate)

        # MP3 변환 (필요시)
        if output_path.suffix.lower() == ".mp3":
            try:
                from pydub import AudioSegment

                audio = AudioSegment.from_wav(str(wav_path))
                audio.export(str(output_path), format="mp3")
                wav_path.unlink(missing_ok=True)
            except ImportError:
                output_path = wav_path
                logger.debug("[CosyVoice] pydub 미설치, WAV 사용")
        else:
            output_path = wav_path

        # Whisper로 단어 타이밍 추출
        if words_json_path is not None:
            self._generate_word_timings(output_path, text, words_json_path, language)

        logger.info("[CosyVoice] 생성 완료: %s", output_path)
        return output_path

    @staticmethod
    def _get_instruct_text(role: str, channel_key: str) -> str:
        """역할·채널별 CosyVoice instruct 지시문."""
        instruct_map = {
            "hook": "Speak with high energy, dramatic emphasis, and a faster pace.",
            "cta": "Speak warmly and slowly, with a persuasive and inviting tone.",
            "closing": "Speak softly and gently, with a reflective and calm tone.",
        }
        channel_hints = {
            "ai_tech": " Use a confident, tech-savvy tone.",
            "psychology": " Use an empathetic, thoughtful tone.",
            "history": " Use a narrative, storytelling tone.",
            "space": " Use an awe-inspired, wonder-filled tone.",
            "health": " Use a reassuring, professional tone.",
        }
        base = instruct_map.get(role, "Speak naturally with clear articulation.")
        hint = channel_hints.get(channel_key, "")
        return base + hint

    @staticmethod
    def _get_default_ref_audio() -> str | None:
        """기본 참조 오디오 경로 (assets에서 탐색)."""
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
                        "[CosyVoice] whisper 타이밍 %d words: %s",
                        len(words), words_json_path,
                    )
                    return
        except Exception as exc:
            logger.debug("[CosyVoice] whisper fallback 실패: %s", exc)

        # 2순위: 근사치
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
                    "[CosyVoice] 근사 타이밍 %d words: %s",
                    len(approx), words_json_path,
                )
        except Exception as exc:
            logger.debug("[CosyVoice] 근사 타이밍 실패: %s", exc)


def is_cosyvoice_available() -> bool:
    """CosyVoice 패키지 설치 여부 확인."""
    try:
        from cosyvoice.cli.cosyvoice import AutoModel  # noqa: F401

        return True
    except ImportError:
        return False
