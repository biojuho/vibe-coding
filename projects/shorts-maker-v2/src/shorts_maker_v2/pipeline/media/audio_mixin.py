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

        return audio_result
