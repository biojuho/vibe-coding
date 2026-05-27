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


@pytest.fixture(autouse=True)
def clear_runtime_state(tmp_path, monkeypatch):
    """각 테스트마다 SQLite DB와 모듈 싱글톤을 tmp_path로 격리한다.

    Promoted from tests/unit/conftest.py so the isolation also covers
    integration tests. Integration tests do not directly use cost_db but
    they import modules (draft_generator, scoring_6d, …) that call
    `get_cost_db()` at runtime — without this fixture those calls would
    hit the real `.tmp/btx_costs.db`, pollute it, and cause flake when
    unit tests later assert on empty DB state.

    핵심 문제 (T-128):
    - CostDatabase / DraftCache 모두 .tmp/*.db 공유 파일을 기본 경로로 사용
    - 모듈 레벨 _db_singleton이 테스트 간에 살아남아 이전 테스트의 경로를 가리킴

    해결책:
    - monkeypatch로 _DEFAULT_DB_PATH를 pytest tmp_path로 교체 → 파일 격리
    - _db_singleton을 None으로 초기화 → get_cost_db()가 tmp_path 기반 인스턴스 재생성
    - monkeypatch는 테스트 종료 시 자동 복원
    """
    import pipeline.cost_db as _cost_db_mod
    import pipeline.draft_cache as _draft_cache_mod
    from pipeline.ml_scorer import _MODEL_PATH

    monkeypatch.setattr(_cost_db_mod, "_DEFAULT_DB_PATH", tmp_path / "btx_costs.db")
    monkeypatch.setattr(_draft_cache_mod, "_DEFAULT_DB_PATH", tmp_path / "draft_cache.db")
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
