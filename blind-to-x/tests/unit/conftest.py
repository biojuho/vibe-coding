"""Shared pytest fixtures for blind-to-x unit tests."""

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
def clear_runtime_state():
    """Reset in-memory and SQLite-backed caches between tests."""
    from pipeline.cost_db import CostDatabase
    from pipeline.draft_cache import DraftCache
    from pipeline.ml_scorer import _MODEL_PATH

    DraftCache().clear()
    with CostDatabase()._conn() as conn:
        conn.execute("DELETE FROM daily_text_costs")
        conn.execute("DELETE FROM daily_image_costs")
        conn.execute("DELETE FROM draft_analytics")
        conn.execute("DELETE FROM provider_failures")
    if _MODEL_PATH.exists():
        _MODEL_PATH.unlink()
    yield
    DraftCache().clear()
    with CostDatabase()._conn() as conn:
        conn.execute("DELETE FROM daily_text_costs")
        conn.execute("DELETE FROM daily_image_costs")
        conn.execute("DELETE FROM draft_analytics")
        conn.execute("DELETE FROM provider_failures")
    if _MODEL_PATH.exists():
        _MODEL_PATH.unlink()
