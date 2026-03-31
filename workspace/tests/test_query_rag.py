from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PA_CANDIDATES = [
    ROOT / "workspace",
    ROOT.parent / "_archive" / "personal-agent",
]


def _resolve_pa_root() -> Path | None:
    for candidate in PA_CANDIDATES:
        if (candidate / "rag" / "query.py").exists():
            return candidate
    return None


PA_ROOT = _resolve_pa_root()
if PA_ROOT is None:
    pytest.skip(
        "legacy workspace app not found (checked: workspace, _archive/personal-agent)",
        allow_module_level=True,
    )

if str(PA_ROOT) not in sys.path:
    sys.path.insert(0, str(PA_ROOT))

from rag.query import detect_intent, query_rag  # noqa: E402


def test_detect_intent_game():
    intent, _meta = detect_intent("끝말잇기 게임 켜줘")
    assert intent == "launch_game"


def test_detect_intent_system_monitor():
    intent, _meta = detect_intent("시스템 상태 어때?")
    assert intent == "system_monitor"


def test_query_rag_memo_path(monkeypatch):
    import rag.query as rq

    monkeypatch.setattr(rq, "add_memo", lambda content: f"memo:{content}")
    response = query_rag("우유 사기 메모해줘")
    assert response.startswith("memo:")


def test_query_rag_no_context(monkeypatch):
    import rag.query as rq

    monkeypatch.setattr(rq, "get_vector_db", None)
    monkeypatch.setattr(rq, "search_web", lambda _q: None)
    response = query_rag("완전히 새로운 질문")
    assert "couldn't find" in response.lower()
