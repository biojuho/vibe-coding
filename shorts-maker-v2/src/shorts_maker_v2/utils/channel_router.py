"""
channel_router.py
=================
채널별 파이프라인 프로파일을 로드하여 AppConfig를 오버라이드합니다.

사용법:
    from shorts_maker_v2.utils.channel_router import ChannelRouter

    router = ChannelRouter()
    config = router.apply(base_config, channel_key="ai_tech")
    # config.providers.tts_voice == "ko-KR-InJoonNeural"

채널 키:
    ai_tech    → 퓨처 시냅스 (AI/기술)
    psychology → 토닥토닥 심리 (심리학)
    history    → 역사팝콘 (역사/고고학)
    space      → 도파민 랩 (우주/천문학)
    health     → 건강 스포일러 (의학/건강)
"""

from __future__ import annotations

import copy
import logging
import os
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

# 기본 채널 프로파일 파일 위치 (프로젝트 루트 기준)
_DEFAULT_PROFILES_PATH = Path(__file__).parents[4] / "channel_profiles.yaml"


class ChannelRouter:
    """
    channel_profiles.yaml을 읽어 채널별 파이프라인 설정을 적용하는 라우터.

    Args:
        profiles_path: channel_profiles.yaml 파일 경로.
                       None이면 프로젝트 루트의 channel_profiles.yaml 사용.
    """

    def __init__(self, profiles_path: Path | None = None) -> None:
        self._path = Path(profiles_path) if profiles_path else _DEFAULT_PROFILES_PATH
        self._profiles: dict[str, Any] = {}
        self._load()

    # ── 내부 메서드 ─────────────────────────────────────────────────────────

    def _load(self) -> None:
        """YAML 파일을 로드합니다."""
        if not self._path.exists():
            logger.warning(
                "[ChannelRouter] 채널 프로파일 파일을 찾을 수 없습니다: %s", self._path
            )
            return
        with self._path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        self._profiles = data.get("channels", {})
        logger.info("[ChannelRouter] %d개 채널 프로파일 로드 완료", len(self._profiles))

    # ── 공개 메서드 ─────────────────────────────────────────────────────────

    def list_channels(self) -> list[dict[str, str]]:
        """등록된 채널 목록을 반환합니다."""
        return [
            {
                "key": key,
                "display_name": profile.get("display_name", key),
                "category": profile.get("category", ""),
                "youtube_url": profile.get("youtube_url", ""),
            }
            for key, profile in self._profiles.items()
        ]

    def get_profile(self, channel_key: str) -> dict[str, Any]:
        """채널 키로 프로파일을 반환합니다."""
        if channel_key not in self._profiles:
            available = list(self._profiles.keys())
            raise ValueError(
                f"[ChannelRouter] 알 수 없는 채널 키: '{channel_key}'. "
                f"사용 가능한 채널: {available}"
            )
        return self._profiles[channel_key]

    def get_channel_context(self, channel_key: str) -> str:
        """페르소나 파이프라인에 주입할 채널 컨텍스트 문자열을 반환합니다."""
        if not channel_key or channel_key not in self._profiles:
            return ""
        return self._profiles[channel_key].get("persona_channel_context", "")

    def get_notion_channel_name(self, channel_key: str) -> str:
        """Notion 숏츠 트래킹 DB의 채널 select 값을 반환합니다."""
        if not channel_key or channel_key not in self._profiles:
            return ""
        return self._profiles[channel_key].get("notion_channel_name", "")

    def apply(self, config: Any, channel_key: str) -> Any:
        """
        채널 프로파일을 AppConfig에 적용하여 새 config를 반환합니다.
        원본 config는 변경되지 않습니다 (deepcopy).

        Args:
            config:      AppConfig 인스턴스.
            channel_key: 채널 키 (예: "ai_tech", "psychology").

        Returns:
            채널 프로파일이 적용된 AppConfig 복사본.
        """
        if not channel_key:
            return config

        if channel_key not in self._profiles:
            logger.warning(
                "[ChannelRouter] 채널 '%s'를 찾을 수 없어 기본 설정을 사용합니다.", channel_key
            )
            return config

        profile = self._profiles[channel_key]
        new_config = copy.deepcopy(config)

        # ── TTS 설정 적용 ────────────────────────────────────────────────
        if "tts_voice" in profile:
            new_config.providers.tts_voice = profile["tts_voice"]
            logger.debug("[ChannelRouter] TTS 음성: %s", profile["tts_voice"])

        if "tts_speed" in profile:
            new_config.providers.tts_speed = profile["tts_speed"]

        if "tts_voice_roles" in profile:
            # 기존 역할 매핑에 채널별 역할 오버라이드
            existing = dict(new_config.providers.tts_voice_roles or {})
            existing.update(profile["tts_voice_roles"])
            new_config.providers.tts_voice_roles = existing

        # ── 시각 스타일 적용 ─────────────────────────────────────────────
        if "visual_styles" in profile:
            new_config.video.visual_styles = profile["visual_styles"]

        # ── 구조 프리셋 적용 ─────────────────────────────────────────────
        if "default_structure" in profile:
            # 기본 구조를 profile 지정 구조로 설정
            # (실제 ScriptStep에서 structure_counter 리셋이 필요)
            new_config._channel_default_structure = profile["default_structure"]

        # ── 자막 스타일 적용 ─────────────────────────────────────────────
        if "caption_style" in profile:
            new_config.captions.style_preset = profile["caption_style"]

        logger.info(
            "[ChannelRouter] '%s' (%s) 프로파일 적용 완료",
            channel_key,
            profile.get("display_name", channel_key),
        )
        return new_config


# ── 편의 함수 ────────────────────────────────────────────────────────────────

_router_singleton: ChannelRouter | None = None


def get_router(profiles_path: Path | None = None) -> ChannelRouter:
    """
    ChannelRouter 싱글톤을 반환합니다.
    프로세스 내에서 YAML 파일을 한 번만 로드합니다.
    """
    global _router_singleton
    if _router_singleton is None:
        _router_singleton = ChannelRouter(profiles_path)
    return _router_singleton
