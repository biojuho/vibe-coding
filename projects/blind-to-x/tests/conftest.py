"""blind-to-x top-level test conftest — adds project root to sys.path."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture(autouse=True)
def mock_pipeline_process_globals(monkeypatch):
    """
    Disable real API calls globally for unit tests.

    After the global-state refactoring (Phase 1), viral filter / sentiment
    tracker / notebooklm enricher live in pipeline.process_stages.runtime,
    not in pipeline.process.  We patch the canonical location here.
    """
    try:
        import pipeline.process_stages.runtime as _runtime

        monkeypatch.setattr(_runtime, "_ViralFilterCls", None)
        monkeypatch.setattr(_runtime, "_viral_filter_instance", None)
        monkeypatch.setattr(_runtime, "sentiment_tracker", None)
        monkeypatch.setattr(_runtime, "notebooklm_enricher", None)
    except (ImportError, AttributeError):
        pass
