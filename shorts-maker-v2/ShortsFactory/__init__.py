"""ShortsFactory — 5채널 통합 쇼츠 파이프라인.

Config: channel_profiles.yaml (Single Source of Truth)
Registry: shorts_maker_v2.templates (Single Source of Truth)
"""
from .pipeline import ShortsFactory, ChannelConfig, RenderJob
from .batch import batch_render

__all__ = [
    "ShortsFactory",
    "ChannelConfig",
    "RenderJob",
    "batch_render",
]
