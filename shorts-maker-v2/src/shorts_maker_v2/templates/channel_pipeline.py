"""채널 전용 쇼츠 파이프라인.

채널 키 + 템플릿 이름으로 적절한 생성기를 로드하고
파이프라인 설정(컬러 프리셋, 키워드 하이라이트 등)을 자동 적용합니다.
"""

from __future__ import annotations

import importlib
import logging
from typing import Any

from shorts_maker_v2 import templates
from shorts_maker_v2.render.karaoke import build_keyword_color_map

logger = logging.getLogger(__name__)


class ChannelPipeline:
    """채널별 쇼츠 생성 파이프라인."""

    def __init__(self, channel_key: str, profile: dict[str, Any] | None = None):
        self.channel_key = channel_key
        self._profile = profile or self._load_profile(channel_key)
        self._keyword_map = self._build_keywords()

    @staticmethod
    def _load_profile(channel_key: str) -> dict[str, Any]:
        try:
            from shorts_maker_v2.utils.channel_router import ChannelRouter

            return ChannelRouter().get_profile(channel_key)
        except Exception:
            return {}

    def _build_keywords(self) -> dict[str, tuple[int, int, int, int]] | None:
        kws = self._profile.get("highlight_keywords")
        color = self._profile.get("highlight_color", "#E879F9")
        if kws:
            km = build_keyword_color_map(kws, color)
            logger.info("[ChannelPipeline] 키워드 %d개 → %d개 토큰 매핑", len(kws), len(km))
            return km
        return None

    def list_templates(self) -> list[dict[str, Any]]:
        return templates.list_for_channel(self.channel_key)

    def get_generator(self, template_name: str, **kwargs):
        """템플릿 이름으로 생성기 인스턴스 반환.

        Args:
            template_name: 예) "psychology_experiment"
            **kwargs: 생성기 초기화 인자들
        """
        tmpl = templates.get(template_name)
        if not tmpl:
            available = [t["name"] for t in self.list_templates()]
            raise ValueError(f"템플릿 '{template_name}' 없음. 사용 가능: {available}")
        if tmpl["channel"] != self.channel_key:
            raise ValueError(
                f"템플릿 '{template_name}'은 채널 '{tmpl['channel']}'용입니다. 현재 채널: '{self.channel_key}'"
            )
        mod = importlib.import_module(tmpl["module"])
        cls = getattr(mod, tmpl["generator_cls"])
        return cls(**kwargs)

    def generate(self, template_name: str, output_path: str, **kwargs) -> str:
        """템플릿으로 쇼츠 생성.

        Args:
            template_name: 템플릿 이름
            output_path: 출력 파일 경로
            **kwargs: 생성기 초기화 인자들

        Returns:
            생성된 파일 경로
        """
        gen = self.get_generator(template_name, **kwargs)
        result = gen.generate(output_path)
        logger.info(
            "[ChannelPipeline] ✅ %s/%s → %s",
            self.channel_key,
            template_name,
            result,
        )
        return result

    @property
    def keyword_map(self):
        return self._keyword_map

    @property
    def caption_combo(self) -> tuple[str, str, str]:
        combo = self._profile.get("caption_combo", ["default", "default", "default"])
        return tuple(combo[:3])  # type: ignore[return-value]

    def info(self) -> dict[str, Any]:
        """채널 파이프라인 현황 요약."""
        tmpls = self.list_templates()
        return {
            "channel": self.channel_key,
            "display_name": self._profile.get("display_name", self.channel_key),
            "caption_combo": self.caption_combo,
            "keyword_count": len(self._keyword_map) if self._keyword_map else 0,
            "templates": [t["name"] for t in tmpls],
            "template_details": tmpls,
        }
