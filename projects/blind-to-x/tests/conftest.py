"""blind-to-x top-level test conftest — adds project root to sys.path."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture(autouse=True)
def mock_pipeline_process_globals(monkeypatch):
    """
    Disable real API calls globally for unit tests inside process.py
    """
    try:
        import pipeline.process

        monkeypatch.setattr(pipeline.process, "_ViralFilterCls", None)
        monkeypatch.setattr(pipeline.process, "_sentiment_tracker", None)
        monkeypatch.setattr(pipeline.process, "_nlm_enrich", None)
    except ImportError:
        pass
