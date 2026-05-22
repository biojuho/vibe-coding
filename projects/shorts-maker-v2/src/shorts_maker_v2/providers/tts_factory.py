"""TTS Client Factory — chatterbox, cosyvoice, openvoice, edge-tts, and openai TTS.

Encapsulates import checks, dynamic loads, and fallback/construction.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from shorts_maker_v2.config import AppConfig

logger = logging.getLogger(__name__)


class TTSFactory:
    """Factory to create and invoke TTS engines with fallback routing."""

    @staticmethod
    def generate_tts_with_fallback(
        config: AppConfig,
        tts_provider: str,
        text: str,
        output_path: Path,
        words_json_path: Path,
        voice: str,
        role: str,
        channel_key: str = "",
        openai_client: Any = None,
    ) -> Path:
        """TTS 프로바이더 라우팅 (cascade: 선택 프로바이더 → edge-tts fallback 또는 openai)"""
        if tts_provider == "chatterbox":
            return TTSFactory._try_chatterbox(
                config=config,
                text=text,
                output_path=output_path,
                words_json_path=words_json_path,
                voice=voice,
                role=role,
                channel_key=channel_key,
            )
        elif tts_provider == "cosyvoice":
            return TTSFactory._try_cosyvoice(
                config=config,
                text=text,
                output_path=output_path,
                words_json_path=words_json_path,
                voice=voice,
                role=role,
                channel_key=channel_key,
            )
        elif tts_provider == "openvoice":
            return TTSFactory._try_openvoice(
                config=config,
                text=text,
                output_path=output_path,
                words_json_path=words_json_path,
                voice=voice,
                role=role,
                channel_key=channel_key,
            )
        elif tts_provider == "edge-tts":
            from shorts_maker_v2.providers.edge_tts_client import EdgeTTSClient

            return EdgeTTSClient().generate_tts(
                model=config.providers.tts_model,
                voice=voice,
                speed=config.providers.tts_speed,
                text=text,
                output_path=output_path,
                words_json_path=words_json_path,
                role=role,
                channel_key=channel_key,
                language=config.project.language,
            )
        else:
            if openai_client is None:
                raise ValueError("OpenAI client is required for OpenAI TTS provider")
            return openai_client.generate_tts(
                model=config.providers.tts_model,
                voice=voice,
                speed=config.providers.tts_speed,
                text=text,
                output_path=output_path,
            )

    @staticmethod
    def _try_chatterbox(
        config: AppConfig,
        text: str,
        output_path: Path,
        words_json_path: Path,
        voice: str,
        role: str,
        channel_key: str,
    ) -> Path:
        try:
            from shorts_maker_v2.providers.chatterbox_client import (
                ChatterboxTTSClient,
                is_chatterbox_available,
            )

            if not is_chatterbox_available():
                raise ImportError("chatterbox-tts not installed")
            client = ChatterboxTTSClient(
                ref_audio_path=getattr(config.providers, "tts_ref_audio", None),
            )
            return client.generate_tts(
                model=config.providers.tts_model,
                voice=voice,
                speed=config.providers.tts_speed,
                text=text,
                output_path=output_path,
                words_json_path=words_json_path,
                role=role,
                channel_key=channel_key,
                language=config.project.language,
            )
        except Exception as exc:
            logger.warning(
                "[TTSFactory] chatterbox TTS 실패 → edge-tts fallback: %s",
                exc,
            )
            output_path.unlink(missing_ok=True)
            return TTSFactory._generate_edge_tts_fallback(
                config, text, output_path, words_json_path, voice, role, channel_key
            )

    @staticmethod
    def _try_cosyvoice(
        config: AppConfig,
        text: str,
        output_path: Path,
        words_json_path: Path,
        voice: str,
        role: str,
        channel_key: str,
    ) -> Path:
        try:
            from shorts_maker_v2.providers.cosyvoice_client import (
                CosyVoiceTTSClient,
                is_cosyvoice_available,
            )

            if not is_cosyvoice_available():
                raise ImportError("cosyvoice not installed")
            client = CosyVoiceTTSClient(
                ref_audio_path=getattr(config.providers, "tts_ref_audio", None),
                ref_audio_text=getattr(config.providers, "tts_ref_audio_text", ""),
            )
            return client.generate_tts(
                model=config.providers.tts_model,
                voice=voice,
                speed=config.providers.tts_speed,
                text=text,
                output_path=output_path,
                words_json_path=words_json_path,
                role=role,
                channel_key=channel_key,
                language=config.project.language,
            )
        except Exception as exc:
            logger.warning(
                "[TTSFactory] cosyvoice TTS 실패 → edge-tts fallback: %s",
                exc,
            )
            output_path.unlink(missing_ok=True)
            return TTSFactory._generate_edge_tts_fallback(
                config, text, output_path, words_json_path, voice, role, channel_key
            )

    @staticmethod
    def _try_openvoice(
        config: AppConfig,
        text: str,
        output_path: Path,
        words_json_path: Path,
        voice: str,
        role: str,
        channel_key: str,
    ) -> Path:
        try:
            from shorts_maker_v2.providers.openvoice_client import (
                OpenVoiceTTSClient,
                is_openvoice_available,
            )

            if not is_openvoice_available():
                raise ImportError("openvoice not installed")
            client = OpenVoiceTTSClient(
                checkpoint_dir=getattr(config.providers, "tts_openvoice_checkpoint_dir", "checkpoints_v2"),
                ref_audio_path=getattr(config.providers, "tts_ref_audio", None),
            )
            return client.generate_tts(
                model=config.providers.tts_model,
                voice=voice,
                speed=config.providers.tts_speed,
                text=text,
                output_path=output_path,
                words_json_path=words_json_path,
                role=role,
                channel_key=channel_key,
                language=config.project.language,
            )
        except Exception as exc:
            logger.warning(
                "[TTSFactory] openvoice TTS 실패 → edge-tts fallback: %s",
                exc,
            )
            output_path.unlink(missing_ok=True)
            return TTSFactory._generate_edge_tts_fallback(
                config, text, output_path, words_json_path, voice, role, channel_key
            )

    @staticmethod
    def _generate_edge_tts_fallback(
        config: AppConfig,
        text: str,
        output_path: Path,
        words_json_path: Path,
        voice: str,
        role: str,
        channel_key: str = "",
    ) -> Path:
        from shorts_maker_v2.providers.edge_tts_client import EdgeTTSClient

        return EdgeTTSClient().generate_tts(
            model=config.providers.tts_model,
            voice=voice,
            speed=config.providers.tts_speed,
            text=text,
            output_path=output_path,
            words_json_path=words_json_path,
            role=role,
            channel_key=channel_key,
            language=config.project.language,
        )
