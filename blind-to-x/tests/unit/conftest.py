"""Shared pytest fixtures for blind-to-x unit tests."""

import pytest


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
