"""
base_template.py — 모든 템플릿의 기반 클래스
"""
from __future__ import annotations
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from ShortsFactory.engines.text_engine import TextEngine
from ShortsFactory.engines.transition_engine import TransitionEngine
from ShortsFactory.engines.background_engine import BackgroundEngine
from ShortsFactory.engines.color_engine import ColorEngine
from ShortsFactory.engines.layout_engine import LayoutEngine
from ShortsFactory.engines.hook_engine import HookEngine

logger = logging.getLogger(__name__)

@dataclass
class Scene:
    """하나의 씬 데이터."""
    role: str          # hook / body / cta / disclaimer
    text: str = ""
    keywords: list[str] = field(default_factory=list)
    image_path: Path | None = None
    text_image_path: Path | None = None
    duration: float = 5.0
    start_time: float | None = None   # 절대 시작 시간 (초), None이면 순차
    animation: str = "none"           # none / slide_up / slide_in_right / slide_out_left / fade_in / glow
    extra: dict[str, Any] = field(default_factory=dict)


class BaseTemplate:
    """모든 템플릿의 기반 클래스.

    엔진 인스턴스를 생성하고 공통 로직(면책조항, 진행률)을 제공합니다.
    """

    template_name: str = "base"

    def __init__(self, channel_config: dict[str, Any]) -> None:
        self.channel_config = channel_config
        self.text = TextEngine(channel_config)
        self.transition = TransitionEngine(channel_config)
        self.background = BackgroundEngine(channel_config)
        color_preset = channel_config.get("color_preset", "")
        self.color = ColorEngine(color_preset) if color_preset else None
        self.layout = LayoutEngine(channel_config)
        self.hook = HookEngine(channel_config)
        self._has_disclaimer = channel_config.get("disclaimer", False)

    def build_scenes(self, data: dict[str, Any]) -> list[Scene]:
        """데이터로부터 씬 리스트를 만듭니다. 서브클래스에서 구현."""
        raise NotImplementedError

    def finalize_scenes(self, scenes: list[Scene]) -> list[Scene]:
        """면책조항 등 공통 후처리 적용."""
        if self._has_disclaimer:
            scenes = self.add_disclaimer(scenes)
        return scenes

    def add_disclaimer(self, scenes: list[Scene]) -> list[Scene]:
        """health 채널 면책조항 자동 삽입."""
        disclaimer = Scene(
            role="disclaimer",
            text="⚠️ 이 영상은 의학적 조언이 아닙니다.\n전문의와 상담하세요.",
            duration=3.0,
        )
        # CTA 앞에 삽입
        cta_idx = next((i for i, s in enumerate(scenes) if s.role == "cta"), len(scenes))
        scenes.insert(cta_idx, disclaimer)
        return scenes

    def render_scene_assets(self, scenes: list[Scene], output_dir: Path) -> list[Scene]:
        """각 씬의 자막/레이아웃 이미지를 렌더링합니다."""
        output_dir.mkdir(parents=True, exist_ok=True)
        for i, scene in enumerate(scenes):
            if scene.text:
                img_path = output_dir / f"scene_{i:02d}_{scene.role}_text.png"
                self.text.render_subtitle(
                    scene.text, keywords=scene.keywords,
                    role=scene.role, output_path=img_path,
                )
                scene.text_image_path = img_path
        return scenes
