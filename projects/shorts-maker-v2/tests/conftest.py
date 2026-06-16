from __future__ import annotations

import os
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock

import pytest


def _inject_optional_sdk_stubs() -> None:
    """Inject lightweight stubs for optional provider SDKs.

    Must run before any test module imports production code that does
    ``from google import genai`` or ``import anthropic`` at module level.
    conftest.py is loaded first by pytest, so module-level injection here
    ensures stubs are in place for every test file in the suite.
    """
    if "google" not in sys.modules:
        google_mod = ModuleType("google")
        sys.modules["google"] = google_mod
    else:
        google_mod = sys.modules["google"]

    if not hasattr(google_mod, "genai") or "google.genai" not in sys.modules:
        genai_mod = ModuleType("google.genai")
        genai_mod.Client = MagicMock()  # type: ignore[attr-defined]
        # Use MagicMock for types so attribute access (e.g. types.GenerateVideosConfig)
        # returns a MagicMock automatically rather than raising AttributeError
        types_stub = MagicMock()
        genai_mod.types = types_stub  # type: ignore[attr-defined]
        sys.modules["google.genai"] = genai_mod
        sys.modules["google.genai.types"] = types_stub
        google_mod.genai = genai_mod  # type: ignore[attr-defined]

    if "anthropic" not in sys.modules:
        anthropic_mod = ModuleType("anthropic")
        anthropic_mod.Anthropic = MagicMock()  # type: ignore[attr-defined]
        sys.modules["anthropic"] = anthropic_mod


_inject_optional_sdk_stubs()

_LIVE_LLM_ENV_KEYS = (
    "OPENAI_API_KEY",
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "ANTHROPIC_API_KEY",
    "XAI_API_KEY",
    "GROK_API_KEY",
    "DEEPSEEK_API_KEY",
    "MOONSHOT_API_KEY",
    "ZHIPUAI_API_KEY",
    "GROQ_API_KEY",
    "MIMO_API_KEY",
    "XIAOMI_API_KEY",
)

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
VIBE_ROOT = ROOT.parent  # execution/ 모듈 경로 (blind-to-x 상위)

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(VIBE_ROOT) not in sys.path:
    sys.path.insert(0, str(VIBE_ROOT))

# ── imageio_ffmpeg 번들 ffmpeg를 PATH/환경변수에 등록 ──
# moviepy 등이 import 시점에 ffmpeg를 탐색하므로 conftest 최상위에서 설정
try:
    import imageio_ffmpeg

    _ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    if _ffmpeg_exe:
        os.environ.setdefault("IMAGEIO_FFMPEG_EXE", _ffmpeg_exe)
        os.environ.setdefault("FFMPEG_BINARY", _ffmpeg_exe)
        _ffmpeg_dir = str(Path(_ffmpeg_exe).parent)
        if _ffmpeg_dir not in os.environ.get("PATH", ""):
            os.environ["PATH"] = _ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")
except Exception:
    pass


# ── 글로벌 상태 격리 (테스트 간 순서 의존성 방지) ──────────────────────────────


@pytest.fixture(autouse=True)
def _isolate_live_llm_env_for_non_smoke(monkeypatch, request):
    """Keep unit/integration tests from calling live LLM APIs via local env."""
    if request.node.get_closest_marker("smoke"):
        return
    for key in _LIVE_LLM_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


@pytest.fixture(autouse=True)
def _reset_channel_router_singleton():
    """channel_router._router_singleton 을 매 테스트마다 초기화."""
    yield
    try:
        from shorts_maker_v2.utils import channel_router

        channel_router._router_singleton = None
    except Exception:
        pass


@pytest.fixture(autouse=True)
def _clear_hwaccel_lru_caches():
    """hwaccel.detect_hw_encoder / detect_gpu_info LRU 캐시를 매 테스트마다 초기화."""
    yield
    try:
        from shorts_maker_v2.utils.hwaccel import detect_gpu_info, detect_hw_encoder

        detect_hw_encoder.cache_clear()
        detect_gpu_info.cache_clear()
    except Exception:
        pass


@pytest.fixture(autouse=True)
def _reset_llm_bridge_cache():
    """llm_router._bridge_cache 를 매 테스트마다 초기화."""
    yield
    try:
        from shorts_maker_v2.providers import llm_router

        llm_router._bridge_cache = None
    except Exception:
        pass


@pytest.fixture(autouse=True)
def _clear_tts_model_caches():
    """cosyvoice_client / chatterbox_client 의 _model_cache를 매 테스트마다 초기화."""
    yield
    try:
        from shorts_maker_v2.providers import cosyvoice_client

        cosyvoice_client._model_cache.clear()
    except Exception:
        pass
    try:
        from shorts_maker_v2.providers import chatterbox_client

        chatterbox_client._model_cache.clear()
    except Exception:
        pass
