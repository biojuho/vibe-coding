"""Shared pytest fixtures for blind-to-x unit tests."""

import logging
import pytest

# Kiwi C 확장이 non-ASCII Windows 경로에서 segfault하므로 테스트 시 로드 방지.
# kiwipiepy 자체 import도 안전하지 않으므로 sys.modules에 dummy를 주입.
import os as _os

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


@pytest.fixture(autouse=True)
def clear_runtime_state(tmp_path, monkeypatch):
    """각 테스트마다 SQLite DB를 tmp_path로 격리한다.

    핵심 문제 (T-128):
    - CostDatabase / DraftCache 모두 .tmp/*.db 공유 파일을 기본 경로로 사용
    - 모듈 레벨 _db_singleton이 테스트 간에 살아남아 이전 테스트의 경로를 가리킴
    - try/except:pass 방식의 DELETE는 SQLite 락 실패 시 조용히 누락

    해결책:
    - monkeypatch로 _DEFAULT_DB_PATH를 pytest tmp_path로 교체 → 파일 격리
    - monkeypatch로 _db_singleton을 None으로 초기화 → get_cost_db()가
      새 tmp_path 기반 인스턴스를 생성하도록 강제
    - monkeypatch는 테스트 종료 시 자동으로 원래 값 복원
    """
    import pipeline.cost_db as _cost_db_mod
    import pipeline.draft_cache as _draft_cache_mod
    from pipeline.ml_scorer import _MODEL_PATH

    # DB 경로를 테스트 전용 tmp_path로 교체
    monkeypatch.setattr(_cost_db_mod, "_DEFAULT_DB_PATH", tmp_path / "btx_costs.db")
    monkeypatch.setattr(_draft_cache_mod, "_DEFAULT_DB_PATH", tmp_path / "draft_cache.db")
    # 모듈 레벨 싱글톤 초기화 → 다음 get_cost_db() 호출 시 tmp_path 기반으로 재생성
    monkeypatch.setattr(_cost_db_mod, "_db_singleton", None)

    if _MODEL_PATH.exists():
        try:
            _MODEL_PATH.unlink()
        except Exception:
            pass

    yield

    if _MODEL_PATH.exists():
        try:
            _MODEL_PATH.unlink()
        except Exception:
            pass


@pytest.fixture(autouse=True)
def _block_external_api_keys(monkeypatch):
    """테스트 중 외부 API 호출 유발 환경변수를 강제 제거.

    T-BUG-SLOW-TEST 근본 원인 보완:
    enrichment_engine.py의 asyncio.sleep(0.5) 제거 후에도
    .env가 로드된 환경에서 EXA_API_KEY / PERPLEXITY_API_KEY가 주입되면
    실제 네트워크 호출이 발생해 테스트가 느려질 수 있다.
    이 픽스처로 모든 테스트에서 Fallback 경로(즉시 반환)를 강제한다.
    """
    monkeypatch.delenv("EXA_API_KEY", raising=False)
    monkeypatch.delenv("PERPLEXITY_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("NOTION_API_KEY", raising=False)
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("SUPABASE_KEY", raising=False)
    yield


@pytest.fixture(autouse=True)
def _fast_sleeps(monkeypatch):
    """테스트 속도를 높이기 위해 기나긴 time.sleep과 asyncio.sleep을 0에 가깝게 패치합니다."""
    import time
    import asyncio
    
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
