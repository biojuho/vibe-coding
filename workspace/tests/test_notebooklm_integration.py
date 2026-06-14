from __future__ import annotations

import execution.notebooklm_integration as notebooklm


def test_research_source_command_adds_import_all_for_deep_mode():
    assert notebooklm._research_source_command("market analysis", "deep") == [
        "source",
        "add-research",
        "market analysis",
        "--mode",
        "deep",
        "--import-all",
    ]


def test_research_source_command_keeps_fast_mode_lightweight():
    assert notebooklm._research_source_command("market analysis", "fast") == [
        "source",
        "add-research",
        "market analysis",
        "--mode",
        "fast",
    ]


def test_add_url_sources_returns_only_successful_source_ids(monkeypatch):
    calls = []
    responses = [
        {"source_id": "src-1"},
        {"status": "failed"},
        {"source_id": "src-3"},
    ]

    def fake_run_json(args):
        calls.append(args)
        return responses.pop(0)

    monkeypatch.setattr(notebooklm, "_run_json", fake_run_json)

    source_ids = notebooklm._add_url_sources(["https://a.example", "https://b.example", "https://c.example"])

    assert source_ids == ["src-1", "src-3"]
    assert calls == [
        ["source", "add", "https://a.example"],
        ["source", "add", "https://b.example"],
        ["source", "add", "https://c.example"],
    ]


def test_wait_for_source_processing_only_sleeps_when_sources_exist(monkeypatch):
    sleeps = []
    monkeypatch.setattr(notebooklm.time, "sleep", lambda seconds: sleeps.append(seconds))

    notebooklm._wait_for_source_processing([])
    notebooklm._wait_for_source_processing(["src-1"], wait_seconds=3)

    assert sleeps == [3]


def test_ask_questions_collects_answer_results(monkeypatch):
    calls = []
    responses = [
        {"answer": "Use the cited source."},
        {"status": "empty"},
    ]

    def fake_run_json(args):
        calls.append(args)
        return responses.pop(0)

    monkeypatch.setattr(notebooklm, "_run_json", fake_run_json)

    answers = notebooklm._ask_questions(["What changed?", "Anything else?"])

    assert answers == [{"question": "What changed?", "answer": "Use the cited source."}]
    assert calls == [["ask", "What changed?"], ["ask", "Anything else?"]]


def test_research_workflow_orchestrates_notebook_sources_research_and_answers(monkeypatch):
    json_calls = []
    run_calls = []

    def fake_run_json(args):
        json_calls.append(args)
        if args == ["create", "Launch research"]:
            return {"id": "nb-1"}
        if args == ["source", "add", "https://example.com"]:
            return {"source_id": "src-1"}
        if args == ["ask", "What matters?"]:
            return {"answer": "The launch blocker is external."}
        raise AssertionError(f"unexpected _run_json args: {args!r}")

    def fake_run(args, *, check=True):
        run_calls.append((args, check))
        return None

    monkeypatch.setattr(notebooklm, "check_auth", lambda: True)
    monkeypatch.setattr(notebooklm, "_run_json", fake_run_json)
    monkeypatch.setattr(notebooklm, "_run", fake_run)
    monkeypatch.setattr(notebooklm.time, "sleep", lambda _seconds: None)

    result = notebooklm.research_workflow(
        "Launch research",
        urls=["https://example.com"],
        query="workspace launch",
        questions=["What matters?"],
        search_mode="deep",
    )

    assert result == {
        "notebook_id": "nb-1",
        "sources": ["src-1"],
        "answers": [{"question": "What matters?", "answer": "The launch blocker is external."}],
    }
    assert json_calls == [
        ["create", "Launch research"],
        ["source", "add", "https://example.com"],
        ["ask", "What matters?"],
    ]
    assert run_calls == [
        (["use", "nb-1"], True),
        (["source", "add-research", "workspace launch", "--mode", "deep", "--import-all"], True),
    ]
