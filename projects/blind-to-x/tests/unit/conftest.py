"""Shared pytest fixtures for blind-to-x unit tests."""

import logging

# Kiwi C 확장이 non-ASCII Windows 경로에서 segfault하므로 테스트 시 로드 방지.
# kiwipiepy 자체 import도 안전하지 않으므로 sys.modules에 dummy를 주입.
import os as _os

import pytest

_os.environ.setdefault("BLIND_TO_X_DISABLE_KOTE", "1")

if any(ord(c) > 127 for c in _os.path.expanduser("~")):
    import sys as _sys

    if "kiwipiepy" not in _sys.modules:
        import types as _types

        _dummy = _types.ModuleType("kiwipiepy")
        _dummy.Kiwi = None  # type: ignore[attr-defined]
        _sys.modules["kiwipiepy"] = _dummy
    try:
        import pipeline.text_polisher as _tp

        _tp._kiwi_load_attempted = True
        _tp._kiwi_instance = None
    except ImportError:
        pass


EXTERNAL_API_ENV_VARS = (
    "EXA_API_KEY",
    "PERPLEXITY_API_KEY",
    "GEMINI_API_KEY",
    "GOOGLE_AI_API_KEY",
    "GOOGLE_API_KEY",
    "DEEPSEEK_API_KEY",
    "GROQ_API_KEY",
    "ZHIPUAI_API_KEY",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "XAI_API_KEY",
    "GROK_API_KEY",
    "NOTION_API_KEY",
    "NOTION_DATABASE_ID",
    "TELEGRAM_BOT_TOKEN",
    "SUPABASE_KEY",
)


@pytest.fixture(autouse=True)
def _isolate_logging_handlers():
    """Windows + Python 3.14에서 logging.shutdown() 중 KeyboardInterrupt 방지.

    main.py import 시 setup_logging()이 실행되면 파일/스트림 핸들러가 root logger에
    등록됩니다. 테스트 teardown 중 이 핸들러를 닫을 때 충돌이 발생하므로,
    각 테스트 실행 전 root logger의 핸들러를 snapshot하고 테스트 후 복원합니다.
    """
    root_logger = logging.getLogger()
    snapshot = root_logger.handlers[:]
    yield
    # 테스트 도중 추가된 핸들러를 안전하게 닫고 제거
    for handler in root_logger.handlers[:]:
        if handler not in snapshot:
            try:
                handler.close()
            except Exception:
                pass
            try:
                root_logger.removeHandler(handler)
            except Exception:
                pass


# clear_runtime_state was promoted to tests/conftest.py so SQLite isolation
# also covers integration tests (T-1109, 2026-05-28). Removed here to avoid
# fixture-name collision with the parent conftest.


@pytest.fixture(autouse=True)
def _block_external_api_keys(monkeypatch):
    """테스트 중 외부 API 호출 유발 환경변수를 강제 제거.

    T-BUG-SLOW-TEST 근본 원인 보완:
    enrichment_engine.py의 asyncio.sleep(0.5) 제거 후에도
    .env가 로드된 환경에서 EXA_API_KEY / PERPLEXITY_API_KEY가 주입되면
    실제 네트워크 호출이 발생해 테스트가 느려질 수 있다.
    이 픽스처로 모든 테스트에서 Fallback 경로(즉시 반환)를 강제한다.
    """
    for env_name in EXTERNAL_API_ENV_VARS:
        monkeypatch.delenv(env_name, raising=False)
    for env_name in tuple(_os.environ):
        if env_name.startswith("NOTION_PROP_"):
            monkeypatch.delenv(env_name, raising=False)
    yield


@pytest.fixture(autouse=True)
def _fast_sleeps(monkeypatch):
    """테스트 속도를 높이기 위해 기나긴 time.sleep과 asyncio.sleep을 0에 가깝게 패치합니다."""
    import asyncio
    import time

    _original_time_sleep = time.sleep
    _original_asyncio_sleep = asyncio.sleep

    def _mock_time_sleep(delay):
        if delay > 0.01:
            return _original_time_sleep(0)
        return _original_time_sleep(delay)

    async def _mock_asyncio_sleep(delay, result=None):
        if delay > 0.01:
            return await _original_asyncio_sleep(0, result=result)
        return await _original_asyncio_sleep(delay, result=result)

    monkeypatch.setattr(time, "sleep", _mock_time_sleep)
    monkeypatch.setattr(asyncio, "sleep", _mock_asyncio_sleep)
    yield
