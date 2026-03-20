"""ShortsFactory — 5채널 통합 쇼츠 파이프라인.

Config: channel_profiles.yaml (Single Source of Truth)
Registry: shorts_maker_v2.templates (Single Source of Truth)
Interface: ShortsFactory.interfaces (Pipeline ↔ ShortsFactory 통합)
"""

from .batch import batch_render
from .interfaces import RenderAdapter, RenderRequest, RenderResult
from .pipeline import ChannelConfig, RenderJob, ShortsFactory

__all__ = [
    "ShortsFactory",
    "ChannelConfig",
    "RenderJob",
    "batch_render",
    "RenderAdapter",
    "RenderRequest",
    "RenderResult",
]
