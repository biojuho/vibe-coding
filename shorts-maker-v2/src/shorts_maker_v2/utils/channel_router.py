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
# channel_router.py → utils/ → shorts_maker_v2/ → src/ → shorts-maker-v2/
_DEFAULT_PROFILES_PATH = Path(__file__).parents[3] / "channel_profiles.yaml"


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
        frozen dataclass이므로 dataclasses.replace()를 사용합니다.

        Args:
            config:      AppConfig 인스턴스.
            channel_key: 채널 키 (예: "ai_tech", "psychology").

        Returns:
            채널 프로파일이 적용된 AppConfig 복사본.
        """
        from dataclasses import replace as dc_replace

        if not channel_key:
            return config

        if channel_key not in self._profiles:
            logger.warning(
                "[ChannelRouter] 채널 '%s'를 찾을 수 없어 기본 설정을 사용합니다.", channel_key
            )
            return config

        profile = self._profiles[channel_key]
        pipeline = profile.get("pipeline", {})

        # ── providers 오버라이드 ──────────────────────────────────────────
        prov_kwargs: dict[str, Any] = {}
        if "tts_voice" in profile:
            prov_kwargs["tts_voice"] = profile["tts_voice"]
        if "tts_speed" in profile:
            prov_kwargs["tts_speed"] = float(profile["tts_speed"])
        if "tts_voice_roles" in profile:
            existing = dict(config.providers.tts_voice_roles or {})
            existing.update(profile["tts_voice_roles"])
            prov_kwargs["tts_voice_roles"] = existing
        if "visual_styles" in profile:
            prov_kwargs["visual_styles"] = tuple(profile["visual_styles"])

        new_providers = dc_replace(config.providers, **prov_kwargs) if prov_kwargs else config.providers

        # ── video 오버라이드 ──────────────────────────────────────────────
        vid_kwargs: dict[str, Any] = {}
        if "target_duration_sec" in profile:
            val = profile["target_duration_sec"]
            if isinstance(val, (list, tuple)):
                vid_kwargs["target_duration_sec"] = (int(val[0]), int(val[1]))
            else:
                vid_kwargs["target_duration_sec"] = (int(val), int(val))

        new_video = dc_replace(config.video, **vid_kwargs) if vid_kwargs else config.video

        # ── captions 오버라이드 ───────────────────────────────────────────
        new_captions = config.captions

        # ── 최종 config 조합 ────────────────────────────────────────────
        new_config = dc_replace(
            config,
            providers=new_providers,
            video=new_video,
            captions=new_captions,
        )

        # 구조 프리셋 (non-frozen 속성이므로 object.__setattr__ 사용)
        if "default_structure" in profile:
            object.__setattr__(new_config, "_channel_default_structure", profile["default_structure"])

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
