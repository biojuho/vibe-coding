from __future__ import annotations

import sys
from importlib import import_module
from importlib.util import find_spec

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
    if name in _EXPORTS:
        module_name, attribute_name = _EXPORTS[name]
        value = getattr(import_module(f"{__name__}.{module_name}"), attribute_name)
        globals()[name] = value
        return value
    submodule_name = f"{__name__}.{name}"
    existing = sys.modules.get(submodule_name)
    if existing is not None:
        globals()[name] = existing
        return existing
    if find_spec(submodule_name) is not None:
        module = import_module(submodule_name)
        globals()[name] = module
        return module
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
