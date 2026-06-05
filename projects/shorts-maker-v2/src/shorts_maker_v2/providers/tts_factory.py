"""TTS client factory for premium providers, Edge TTS, and OpenAI TTS."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from shorts_maker_v2.config import AppConfig

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class _TTSRequest:
    config: AppConfig
    text: str
    output_path: Path
    words_json_path: Path
    voice: str
    role: str
    channel_key: str


@dataclass(frozen=True)
class _ProviderSpec:
    availability_error: str
    loader: Callable[[], tuple[Callable[[], bool], type[Any]]]
    client_kwargs: Callable[[_TTSRequest], dict[str, Any]]


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
        """Route to the configured TTS provider and preserve the Edge fallback cascade."""
        request = TTSFactory._build_request(config, text, output_path, words_json_path, voice, role, channel_key)
        if tts_provider in _provider_specs():
            return TTSFactory._try_provider_with_edge_fallback(tts_provider, request)
        if tts_provider == "edge-tts":
            return TTSFactory._generate_edge_tts_request(request)
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
        request = TTSFactory._build_request(config, text, output_path, words_json_path, voice, role, channel_key)
        return TTSFactory._try_provider_with_edge_fallback("chatterbox", request)

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
        request = TTSFactory._build_request(config, text, output_path, words_json_path, voice, role, channel_key)
        return TTSFactory._try_provider_with_edge_fallback("cosyvoice", request)

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
        request = TTSFactory._build_request(config, text, output_path, words_json_path, voice, role, channel_key)
        return TTSFactory._try_provider_with_edge_fallback("openvoice", request)

    @staticmethod
    def _try_provider_with_edge_fallback(provider: str, request: _TTSRequest) -> Path:
        spec = _provider_specs()[provider]
        try:
            is_available, client_cls = spec.loader()
            if not is_available():
                raise ImportError(spec.availability_error)
            client = client_cls(**spec.client_kwargs(request))
            return TTSFactory._generate_with_client(client, request)
        except Exception as exc:
            logger.warning(
                "[TTSFactory] %s TTS failed; using edge-tts fallback: %s",
                provider,
                exc,
            )
            request.output_path.unlink(missing_ok=True)
            return TTSFactory._generate_edge_tts_request(request)

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
        request = TTSFactory._build_request(config, text, output_path, words_json_path, voice, role, channel_key)
        return TTSFactory._generate_edge_tts_request(request)

    @staticmethod
    def _generate_edge_tts_request(request: _TTSRequest) -> Path:
        from shorts_maker_v2.providers.edge_tts_client import EdgeTTSClient

        return TTSFactory._generate_with_client(EdgeTTSClient(), request)

    @staticmethod
    def _generate_with_client(client: Any, request: _TTSRequest) -> Path:
        return client.generate_tts(
            model=request.config.providers.tts_model,
            voice=request.voice,
            speed=request.config.providers.tts_speed,
            text=request.text,
            output_path=request.output_path,
            words_json_path=request.words_json_path,
            role=request.role,
            channel_key=request.channel_key,
            language=request.config.project.language,
        )

    @staticmethod
    def _build_request(
        config: AppConfig,
        text: str,
        output_path: Path,
        words_json_path: Path,
        voice: str,
        role: str,
        channel_key: str,
    ) -> _TTSRequest:
        return _TTSRequest(
            config=config,
            text=text,
            output_path=output_path,
            words_json_path=words_json_path,
            voice=voice,
            role=role,
            channel_key=channel_key,
        )


def _provider_specs() -> dict[str, _ProviderSpec]:
    return {
        "chatterbox": _ProviderSpec(
            availability_error="chatterbox-tts not installed",
            loader=_load_chatterbox,
            client_kwargs=lambda request: {
                "ref_audio_path": getattr(request.config.providers, "tts_ref_audio", None),
            },
        ),
        "cosyvoice": _ProviderSpec(
            availability_error="cosyvoice not installed",
            loader=_load_cosyvoice,
            client_kwargs=lambda request: {
                "ref_audio_path": getattr(request.config.providers, "tts_ref_audio", None),
                "ref_audio_text": getattr(request.config.providers, "tts_ref_audio_text", ""),
            },
        ),
        "openvoice": _ProviderSpec(
            availability_error="openvoice not installed",
            loader=_load_openvoice,
            client_kwargs=lambda request: {
                "checkpoint_dir": getattr(request.config.providers, "tts_openvoice_checkpoint_dir", "checkpoints_v2"),
                "ref_audio_path": getattr(request.config.providers, "tts_ref_audio", None),
            },
        ),
    }


def _load_chatterbox() -> tuple[Callable[[], bool], type[Any]]:
    from shorts_maker_v2.providers.chatterbox_client import ChatterboxTTSClient, is_chatterbox_available

    return is_chatterbox_available, ChatterboxTTSClient


def _load_cosyvoice() -> tuple[Callable[[], bool], type[Any]]:
    from shorts_maker_v2.providers.cosyvoice_client import CosyVoiceTTSClient, is_cosyvoice_available

    return is_cosyvoice_available, CosyVoiceTTSClient


def _load_openvoice() -> tuple[Callable[[], bool], type[Any]]:
    from shorts_maker_v2.providers.openvoice_client import OpenVoiceTTSClient, is_openvoice_available

    return is_openvoice_available, OpenVoiceTTSClient
