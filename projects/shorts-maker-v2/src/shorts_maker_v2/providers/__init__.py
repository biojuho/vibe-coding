from __future__ import annotations

from importlib import import_module

_EXPORTS = {
    "FreesoundClient": ("freesound_client", "FreesoundClient"),
    "GoogleClient": ("google_client", "GoogleClient"),
    "GoogleMusicClient": ("google_music_client", "GoogleMusicClient"),
    "OpenAIClient": ("openai_client", "OpenAIClient"),
    "PexelsClient": ("pexels_client", "PexelsClient"),
    "StockMediaManager": ("stock_media_manager", "StockMediaManager"),
    "TTSFactory": ("tts_factory", "TTSFactory"),
    "UnsplashClient": ("unsplash_client", "UnsplashClient"),
}

__all__ = [
    "OpenAIClient",
    "GoogleClient",
    "GoogleMusicClient",
    "PexelsClient",
    "UnsplashClient",
    "StockMediaManager",
    "FreesoundClient",
    "TTSFactory",
]


def __getattr__(name: str):
    if name not in _EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attribute_name = _EXPORTS[name]
    value = getattr(import_module(f"{__name__}.{module_name}"), attribute_name)
    globals()[name] = value
    return value
