"""MediaAudioMixin — TTS 생성 및 프로바이더 라우팅 로직.

MediaStep.__init__에서 설정된 self.config, self._tts_voice 등을 사용합니다.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from shorts_maker_v2.config import AppConfig

from shorts_maker_v2.providers.tts_factory import TTSFactory

logger = logging.getLogger(__name__)


class MediaAudioMixin:
    """TTS 생성 관련 메서드를 제공하는 Mixin."""

    config: AppConfig
    _tts_voice: str
    openai_client: Any

    def _generate_audio(self, narration_ko: str, output_path: Path, *, role: str = "body") -> Path:
        """TTS 프로바이더 라우팅 → 오디오 생성 + Whisper sync."""
        if not narration_ko or not narration_ko.strip():
            raise ValueError(f"narration_ko must not be empty (scene role={role!r})")

        # 역할별 음성 매핑 (tts_voice_roles 설정 시)
        voice_roles = self.config.providers.tts_voice_roles
        voice = voice_roles[role] if voice_roles and role in voice_roles else self._tts_voice

        tts_provider = self.config.providers.tts
        words_json_path = output_path.parent / f"{output_path.stem}_words.json"

        # Delegate TTS generation to TTSFactory
        audio_result = TTSFactory.generate_tts_with_fallback(
            config=self.config,
            tts_provider=tts_provider,
            text=narration_ko,
            output_path=output_path,
            words_json_path=words_json_path,
            voice=voice,
            role=role,
            channel_key=getattr(self, "_channel_key", ""),
            openai_client=getattr(self, "openai_client", None),
        )

        # 옵트인 WhisperX 정렬 — 모든 TTS 결과에 단어-레벨 정렬 덮어쓰기 가능 (T-19)
        if getattr(self.config.audio, "use_whisperx_alignment", False):
            try:
                from shorts_maker_v2.render.whisperx_aligner import (
                    align_audio_words,
                    is_available,
                    write_words_json,
                )

                if is_available():
                    words = align_audio_words(
                        audio_result,
                        narration_ko,
                        language=getattr(self.config.audio, "whisperx_language", "ko"),
                        model_size=getattr(self.config.audio, "whisperx_model_size", "base"),
                    )
                    if words:
                        target = audio_result.parent / f"{audio_result.stem}_words.json"
                        write_words_json(words, target)
                        logger.info(
                            "[MediaStep] WhisperX 정렬 적용 — %d words → %s",
                            len(words),
                            target.name,
                        )
                        return audio_result
                    logger.info("[MediaStep] WhisperX 정렬 결과 비어있음 → 기본 동기화로 폴백")
                else:
                    logger.debug("[MediaStep] whisperx 미설치 → 기본 동기화 유지")
            except Exception as exc:
                logger.warning("[MediaStep] WhisperX 정렬 실패 (기본 동기화 폴백): %s", exc)
                scene_id = self._scene_id_from_path(audio_result)
                pending = getattr(self, "_pending_audio_warnings", None)
                if pending is not None:
                    pending.append(
                        {
                            "step": "whisperx_align",
                            "code": type(exc).__name__,
                            "message": f"scene {scene_id}: WhisperX 정렬 실패 — {str(exc)[:120]}",
                            "error_type": "sync_loss",
                        }
                    )

        # chatterbox/cosyvoice/openvoice/edge-tts는 자체적으로 _words.json을 생성
        # OpenAI TTS만 Whisper fallback 필요
        if (
            tts_provider not in {"edge-tts", "chatterbox", "cosyvoice", "openvoice"}
            and self.config.audio.sync_with_whisper
            and getattr(self, "openai_client", None)
        ):
            try:
                import json

                words = self.openai_client.transcribe_audio(audio_result)
                words_json_path = audio_result.parent / f"{audio_result.stem}_words.json"
                words_json_path.write_text(json.dumps(words, ensure_ascii=False, indent=2), encoding="utf-8")
            except Exception as exc:
                logger.warning("[MediaStep] Whisper sync 실패 (자막 동기화 스킵): %s", exc)
                scene_id = self._scene_id_from_path(audio_result)
                pending = getattr(self, "_pending_audio_warnings", None)
                if pending is not None:
                    pending.append(
                        {
                            "step": "whisper_sync",
                            "code": type(exc).__name__,
                            "message": f"scene {scene_id}: Whisper sync 실패 — {str(exc)[:120]}",
                            "error_type": "sync_loss",
                        }
                    )

        return audio_result
