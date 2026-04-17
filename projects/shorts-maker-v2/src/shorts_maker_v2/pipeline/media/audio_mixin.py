"""MediaAudioMixin — TTS 생성 및 프로바이더 라우팅 로직.

MediaStep.__init__에서 설정된 self.config, self._tts_voice 등을 사용합니다.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from shorts_maker_v2.config import AppConfig

from shorts_maker_v2.providers.edge_tts_client import EdgeTTSClient

logger = logging.getLogger(__name__)


class MediaAudioMixin:
    """TTS 생성 관련 메서드를 제공하는 Mixin."""

    config: AppConfig
    _tts_voice: str

    def _generate_audio(self, narration_ko: str, output_path: Path, *, role: str = "body") -> Path:
        """TTS 프로바이더 라우팅 → 오디오 생성 + Whisper sync."""

        # 역할별 음성 매핑 (tts_voice_roles 설정 시)
        voice_roles = self.config.providers.tts_voice_roles
        voice = voice_roles[role] if voice_roles and role in voice_roles else self._tts_voice

        tts_provider = self.config.providers.tts
        words_json_path = output_path.parent / f"{output_path.stem}_words.json"

        # TTS 프로바이더 라우팅 (cascade: 선택 프로바이더 → edge-tts fallback)
        if tts_provider == "chatterbox":
            audio_result = self._try_tts_with_fallback(
                narration_ko,
                output_path,
                words_json_path,
                voice,
                role,
                primary="chatterbox",
            )
        elif tts_provider == "cosyvoice":
            audio_result = self._try_tts_with_fallback(
                narration_ko,
                output_path,
                words_json_path,
                voice,
                role,
                primary="cosyvoice",
            )
        elif tts_provider == "edge-tts":
            audio_result = EdgeTTSClient().generate_tts(
                model=self.config.providers.tts_model,
                voice=voice,
                speed=self.config.providers.tts_speed,
                text=narration_ko,
                output_path=output_path,
                words_json_path=words_json_path,
                role=role,
                language=self.config.project.language,
            )
        else:
            audio_result = self.openai_client.generate_tts(
                model=self.config.providers.tts_model,
                voice=voice,
                speed=self.config.providers.tts_speed,
                text=narration_ko,
                output_path=output_path,
            )

        # chatterbox/cosyvoice/edge-tts는 자체적으로 _words.json을 생성
        # OpenAI TTS만 Whisper fallback 필요
        if (
            tts_provider not in {"edge-tts", "chatterbox", "cosyvoice"}
            and self.config.audio.sync_with_whisper
            and self.openai_client
        ):
            try:
                import json

                words = self.openai_client.transcribe_audio(audio_result)
                words_json_path = audio_result.parent / f"{audio_result.stem}_words.json"
                words_json_path.write_text(json.dumps(words, ensure_ascii=False, indent=2), encoding="utf-8")
            except Exception as exc:
                logger.warning("[MediaStep] Whisper sync 실패 (자막 동기화 스킵): %s", exc)

        return audio_result

    def _try_tts_with_fallback(
        self,
        text: str,
        output_path: Path,
        words_json_path: Path,
        voice: str,
        role: str,
        *,
        primary: str,
    ) -> Path:
        """프리미엄 TTS 시도 → 실패 시 edge-tts fallback."""

        try:
            if primary == "chatterbox":
                from shorts_maker_v2.providers.chatterbox_client import (
                    ChatterboxTTSClient,
                    is_chatterbox_available,
                )

                if not is_chatterbox_available():
                    raise ImportError("chatterbox-tts not installed")
                client = ChatterboxTTSClient(
                    ref_audio_path=getattr(self.config.providers, "tts_ref_audio", None),
                )
                return client.generate_tts(
                    model=self.config.providers.tts_model,
                    voice=voice,
                    speed=self.config.providers.tts_speed,
                    text=text,
                    output_path=output_path,
                    words_json_path=words_json_path,
                    role=role,
                    channel_key=getattr(self, "_channel_key", ""),
                    language=self.config.project.language,
                )

            elif primary == "cosyvoice":
                from shorts_maker_v2.providers.cosyvoice_client import (
                    CosyVoiceTTSClient,
                    is_cosyvoice_available,
                )

                if not is_cosyvoice_available():
                    raise ImportError("cosyvoice not installed")
                client = CosyVoiceTTSClient(
                    ref_audio_path=getattr(self.config.providers, "tts_ref_audio", None),
                    ref_audio_text=getattr(self.config.providers, "tts_ref_audio_text", ""),
                )
                return client.generate_tts(
                    model=self.config.providers.tts_model,
                    voice=voice,
                    speed=self.config.providers.tts_speed,
                    text=text,
                    output_path=output_path,
                    words_json_path=words_json_path,
                    role=role,
                    channel_key=getattr(self, "_channel_key", ""),
                    language=self.config.project.language,
                )

        except Exception as exc:
            logger.warning(
                "[MediaStep] %s TTS 실패 → edge-tts fallback: %s",
                primary,
                exc,
            )
            output_path.unlink(missing_ok=True)

        # edge-tts fallback
        return EdgeTTSClient().generate_tts(
            model=self.config.providers.tts_model,
            voice=voice,
            speed=self.config.providers.tts_speed,
            text=text,
            output_path=output_path,
            words_json_path=words_json_path,
            role=role,
            language=self.config.project.language,
        )
