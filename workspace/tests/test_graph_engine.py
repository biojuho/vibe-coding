"""
Unit and integration-style tests for graph_engine.py and workers.py.

All LLM calls are mocked so the workflow stays deterministic.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from execution.workers import (  # noqa: E402
    CoderWorker,
    DebuggerWorker,
    ReviewerWorker,
    TesterWorker,
    WorkerResult,
)


@pytest.fixture
def mock_llm() -> MagicMock:
    llm = MagicMock()
    llm.generate_text.return_value = (
        "```python\n"
        "def fibonacci(n):\n"
        "    if n <= 1:\n"
        "        return n\n"
        "    return fibonacci(n - 1) + fibonacci(n - 2)\n"
        "```"
    )
    llm.generate_json.side_effect = RuntimeError("no structured json path")
    return llm


@pytest.fixture
def mock_llm_reviewer() -> MagicMock:
    llm = MagicMock()
    llm.generate_json.return_value = {
        "overall_score": 8,
        "correctness_score": 8,
        "maintainability_score": 8,
        "performance_score": 8,
        "issues": ["Docstring could be clearer"],
        "suggestions": ["Add one small usage example"],
        "reflection": "Keep the implementation but clarify intent and examples.",
        "verdict": "approve",
    }
    llm.generate_text.return_value = '{"overall_score": 8, "verdict": "approve"}'
    return llm


@pytest.fixture
def mock_llm_low_review() -> MagicMock:
    llm = MagicMock()
    llm.generate_json.return_value = {
        "overall_score": 3,
        "correctness_score": 3,
        "maintainability_score": 3,
        "performance_score": 3,
        "issues": ["Input validation is missing"],
        "suggestions": ["Validate inputs before use"],
        "reflection": "Regenerate this with explicit validation and safer control flow.",
        "verdict": "revise",
    }
    llm.generate_text.return_value = '{"overall_score": 3, "verdict": "revise"}'
    return llm


class TestCoderWorker:
    def test_success(self, mock_llm: MagicMock) -> None:
        worker = CoderWorker(mock_llm)
        result = worker.execute({"id": "t1", "description": "Build fibonacci"})

        assert result.status == "success"
        assert result.worker_type == "coder"
        assert result.task_id == "t1"
        assert result.confidence > 0
        assert "fibonacci" in result.content

    def test_with_context(self, mock_llm: MagicMock) -> None:
        worker = CoderWorker(mock_llm)
        worker.execute(
            {
                "id": "t2",
                "description": "Build an API",
                "context": "Use Flask and keep the code minimal.",
            }
        )

        call_args = mock_llm.generate_text.call_args
        assert "Flask" in call_args.kwargs.get("user_prompt", "")

    def test_llm_failure(self, mock_llm: MagicMock) -> None:
        mock_llm.generate_text.side_effect = RuntimeError("API error")
        worker = CoderWorker(mock_llm)
        result = worker.execute({"id": "t3", "description": "test"})

        assert result.status == "error"
        assert result.confidence == 0.0
        assert "API error" in result.content

    def test_empty_description(self, mock_llm: MagicMock) -> None:
        worker = CoderWorker(mock_llm)
        result = worker.execute({"id": "t4", "description": ""})
        assert result.status == "success"


class TestDebuggerWorker:
    def test_success(self, mock_llm: MagicMock) -> None:
        mock_llm.generate_text.return_value = "Root cause: IndexError\nFix: guard the index."
        worker = DebuggerWorker(mock_llm)
        result = worker.execute(
            {
                "id": "d1",
                "error_log": "IndexError: list index out of range",
                "source_code": "x = arr[10]",
            }
        )

        assert result.status == "success"
        assert result.worker_type == "debugger"
        assert result.confidence > 0

    def test_failure(self, mock_llm: MagicMock) -> None:
        mock_llm.generate_text.side_effect = Exception("timeout")
        worker = DebuggerWorker(mock_llm)
        result = worker.execute({"id": "d2", "error_log": "err"})
        assert result.status == "error"


class TestTesterWorker:
    def test_successful_code(self) -> None:
        worker = TesterWorker()
        result = worker.execute({"id": "t1", "code": "print('hello world')"})

        assert result.status == "success"
        assert "hello world" in result.content
        assert result.confidence > 0

    def test_failing_code(self) -> None:
        worker = TesterWorker()
        result = worker.execute({"id": "t2", "code": "raise ValueError('test error')"})

        assert result.status == "needs_revision"
        assert "ValueError" in result.content

    def test_empty_code(self) -> None:
        worker = TesterWorker()
        result = worker.execute({"id": "t3", "code": ""})

        assert result.status == "error"
        assert result.confidence == 0.0

    def test_markdown_code_block(self) -> None:
        worker = TesterWorker()
        result = worker.execute({"id": "t4", "code": "```python\nprint('extracted')\n```"})

        assert result.status == "success"
        assert "extracted" in result.content

    def test_syntax_error(self) -> None:
        worker = TesterWorker()
        result = worker.execute({"id": "t5", "code": "def foo(\n    print('broken')"})
        assert result.status == "needs_revision"

    def test_timeout(self) -> None:
        worker = TesterWorker()
        worker.TIMEOUT_SEC = 2
        result = worker.execute({"id": "t6", "code": "import time; time.sleep(10)"})

        assert result.status == "error"
        assert "Timeout exceeded" in result.content


class TestReviewerWorker:
    def test_approve(self, mock_llm_reviewer: MagicMock) -> None:
        worker = ReviewerWorker(mock_llm_reviewer)
        result = worker.execute({"id": "r1", "code": "def foo():\n    return 1"})

        assert result.status == "success"
        assert result.confidence > 0.8
        assert result.metadata.get("verdict") == "approve"
        assert result.metadata.get("security_score") == 10
        assert "Self-Reflection" in result.content

    def test_revise(self, mock_llm_low_review: MagicMock) -> None:
        worker = ReviewerWorker(mock_llm_low_review)
        result = worker.execute({"id": "r2", "code": "def foo(x):\n    return x"})

        assert result.status == "needs_revision"
        assert result.confidence < 0.5
        assert result.metadata.get("verdict") == "revise"
        assert "validation" in result.metadata["reflection"].lower()

    def test_security_score_penalizes_risky_code(self, mock_llm_reviewer: MagicMock) -> None:
        worker = ReviewerWorker(mock_llm_reviewer)
        result = worker.execute({"id": "r3", "code": "user_code = input()\neval(user_code)"})

        assert result.status == "needs_revision"
        assert result.metadata["security_score"] < 8
        assert any(finding["rule_id"] == "SEC001" for finding in result.metadata["security_findings"])

    def test_non_json_response_falls_back_to_default_review(self, mock_llm: MagicMock) -> None:
        mock_llm.generate_json.side_effect = RuntimeError("no json")
        mock_llm.generate_text.return_value = "Looks mostly okay to me."
        worker = ReviewerWorker(mock_llm)
        result = worker.execute({"id": "r4", "code": "pass"})

        assert result.status == "needs_revision"
        assert result.metadata["review"]["overall_score"] == 5
        assert result.metadata["reflection"]

    def test_reviewer_failure_returns_structured_fallback(self, mock_llm: MagicMock) -> None:
        mock_llm.generate_json.side_effect = RuntimeError("json fail")
        mock_llm.generate_text.side_effect = RuntimeError("text fail")
        worker = ReviewerWorker(mock_llm)
        result = worker.execute({"id": "r5", "code": "pass"})

        assert result.status == "needs_revision"
        assert result.confidence == 0.3
        assert "review_error" in result.metadata


class TestVibeCodingGraph:
    def _make_graph(self, llm: MagicMock):
        from execution.graph_engine import VibeCodingGraph

        return VibeCodingGraph(llm_client=llm, max_iterations=2)

    def test_graph_builds(self, mock_llm: MagicMock) -> None:
        graph = self._make_graph(mock_llm)
        assert graph.graph is not None

    def test_supervisor_decomposes_task(self, mock_llm: MagicMock) -> None:
        graph = self._make_graph(mock_llm)
        result = graph.supervisor_node({"vibe_input": "Build fibonacci"})

        assert "tasks" in result
        assert len(result["tasks"]) >= 1
        assert result["tasks"][0]["id"] == "task-0"

    def test_prepare_and_variant_nodes(self, mock_llm: MagicMock) -> None:
        graph = self._make_graph(mock_llm)
        state = {
            "tasks": [{"id": "t-0", "description": "Build fibonacci"}],
            "current_task_idx": 0,
            "context": "",
            "results": [],
            "iteration": 0,
            "reflection_notes": "",
        }

        prep_result = graph.prepare_variants_node(state)
        assert len(prep_result["variant_tasks"]) == 3

        task_variant = prep_result["variant_tasks"][0]
        coder_result = graph.variant_coder_node({"task_variant": task_variant})
        assert "variant_results" in coder_result
        assert len(coder_result["variant_results"]) == 1

        reducer_state = {"variant_results": coder_result["variant_results"], "iteration": 0}
        reduce_result = graph.reduce_variants_node(reducer_state)
        assert len(reduce_result["results"]) == 1
        assert reduce_result["results"][0].worker_type == "coder"
        assert reduce_result["results"][0].status == "success"

    def test_tester_node_success_routes_to_reviewer(self, mock_llm: MagicMock) -> None:
        graph = self._make_graph(mock_llm)
        result = graph.tester_node(
            {
                "results": [WorkerResult("coder", "t-0", "success", "print('hello')", 0.8)],
                "iteration": 0,
            }
        )

        assert result["next_worker"] == "reviewer"

    def test_tester_node_failure_routes_to_debugger(self, mock_llm: MagicMock) -> None:
        graph = self._make_graph(mock_llm)
        result = graph.tester_node(
            {
                "results": [WorkerResult("coder", "t-0", "success", "raise Exception('boom')", 0.8)],
                "iteration": 0,
            }
        )

        assert result["next_worker"] == "debugger"

    def test_evaluator_passes_high_confidence(self, mock_llm: MagicMock) -> None:
        graph = self._make_graph(mock_llm)
        graph.verifier = None
        state = {
            "results": [
                WorkerResult("coder", "t-0", "success", "code", 0.9),
                WorkerResult("tester", "t-0", "success", "ok", 0.9),
                WorkerResult(
                    "reviewer",
                    "t-0",
                    "success",
                    "good",
                    0.85,
                    metadata={"security_score": 9, "reflection": "Keep it clean."},
                ),
            ],
            "iteration": 0,
            "vibe_input": "test",
        }
        result = graph.evaluator_node(state)

        assert result["confidence"] >= 0.8
        assert result["reflection_notes"] == ""

    def test_evaluator_uses_security_score_and_reflection(self, mock_llm: MagicMock) -> None:
        graph = self._make_graph(mock_llm)
        graph.verifier = None
        state = {
            "results": [
                WorkerResult("coder", "t-0", "success", "code", 0.9),
                WorkerResult("tester", "t-0", "success", "ok", 0.9),
                WorkerResult(
                    "reviewer",
                    "t-0",
                    "needs_revision",
                    "review",
                    0.6,
                    metadata={
                        "security_score": 0,
                        "security_findings": [{"rule_id": "SEC001", "detail": "Avoid eval()"}],
                        "reflection": "Remove eval() and validate inputs.",
                        "review": {"issues": ["Dynamic execution is unsafe"]},
                    },
                ),
            ],
            "iteration": 0,
            "vibe_input": "test",
        }
        result = graph.evaluator_node(state)

        assert result["confidence"] < 0.7
        assert "Remove eval()" in result["reflection_notes"]
        assert "Security score is 0/10" in result["reflection_notes"]

    def test_router_passes_to_output(self, mock_llm: MagicMock) -> None:
        graph = self._make_graph(mock_llm)
        assert graph.route_after_evaluator({"confidence": 0.85, "iteration": 1, "max_iterations": 3}) == "output"

    def test_router_loops_back_to_prepare_variants(self, mock_llm: MagicMock) -> None:
        graph = self._make_graph(mock_llm)
        assert (
            graph.route_after_evaluator({"confidence": 0.4, "iteration": 1, "max_iterations": 3}) == "prepare_variants"
        )

    def test_router_max_iterations_forces_output(self, mock_llm: MagicMock) -> None:
        graph = self._make_graph(mock_llm)
        assert graph.route_after_evaluator({"confidence": 0.3, "iteration": 3, "max_iterations": 3}) == "output"

    def test_output_node_assembles_final(self, mock_llm: MagicMock) -> None:
        graph = self._make_graph(mock_llm)
        result = graph.output_node(
            {
                "results": [
                    WorkerResult("coder", "t-0", "success", "def foo(): pass", 0.8),
                    WorkerResult("reviewer", "t-0", "success", "LGTM", 0.9),
                ],
                "confidence": 0.85,
                "iteration": 1,
                "evaluator_summary": "coder=0.80, tester=0.90",
            }
        )

        assert "def foo(): pass" in result["final_output"]
        assert "LGTM" in result["final_output"]
        assert "Evaluator Summary" in result["final_output"]

    def test_e2e_full_graph_run(self, mock_llm: MagicMock) -> None:
        def dynamic_generate(*, system_prompt: str = "", user_prompt: str = "", **_: object) -> str:
            if "review" in system_prompt.lower():
                return (
                    '{"overall_score": 9, "correctness_score": 9, "maintainability_score": 9, '
                    '"performance_score": 9, "issues": [], "suggestions": [], '
                    '"reflection": "No major changes needed.", "verdict": "approve"}'
                )
            return (
                "```python\n"
                "def fibonacci(n):\n"
                "    if n <= 1:\n"
                "        return n\n"
                "    return fibonacci(n - 1) + fibonacci(n - 2)\n\n"
                "print(fibonacci(10))\n"
                "```"
            )

        mock_llm.generate_text.side_effect = dynamic_generate
        graph = self._make_graph(mock_llm)
        graph.verifier = None

        result = graph.run("Build fibonacci", max_iterations=2)

        assert result.get("final_output", "")
        assert "fibonacci" in result["final_output"]
        assert result.get("iteration", 0) >= 1

    def test_e2e_with_test_failure_triggers_debug(self, mock_llm: MagicMock) -> None:
        call_count = {"coder": 0}

        def dynamic_generate(*, system_prompt: str = "", user_prompt: str = "", **_: object) -> str:
            if "review" in system_prompt.lower():
                return (
                    '{"overall_score": 9, "correctness_score": 9, "maintainability_score": 9, '
                    '"performance_score": 9, "issues": [], "suggestions": [], '
                    '"reflection": "Looks good.", "verdict": "approve"}'
                )
            if "debugger" in system_prompt.lower():
                return "Root cause: SyntaxError\nFix:\n```python\nprint('fixed')\n```"

            call_count["coder"] += 1
            if call_count["coder"] <= 3:
                return "```python\ndef foo(\n    print('broken')\n```"
            return "```python\nprint('fixed successfully')\n```"

        mock_llm.generate_text.side_effect = dynamic_generate
        graph = self._make_graph(mock_llm)
        graph.verifier = None

        result = graph.run("Build a simple function", max_iterations=3)

        assert result.get("final_output", "")
        assert result.get("iteration", 0) >= 1

    def test_no_llm_client(self) -> None:
        from execution.graph_engine import VibeCodingGraph

        with patch.dict("sys.modules", {"execution.llm_client": None}):
            graph = VibeCodingGraph(llm_client=None)

        assert graph.graph is not None
        assert graph.coder is None

    def test_debugger_node_extracts_context(self, mock_llm: MagicMock) -> None:
        mock_llm.generate_text.return_value = "Fix: check index bounds"
        graph = self._make_graph(mock_llm)
        result = graph.debugger_node(
            {
                "tasks": [{"id": "t-0", "description": "test"}],
                "current_task_idx": 0,
                "results": [
                    WorkerResult("coder", "t-0", "success", "x = arr[10]", 0.8),
                    WorkerResult("tester", "t-0", "needs_revision", "IndexError", 0.2),
                ],
            }
        )

        assert result["results"][0].worker_type == "debugger"
        assert result["results"][0].status == "success"

    def test_prepare_variants_incorporates_feedback(self, mock_llm: MagicMock) -> None:
        graph = self._make_graph(mock_llm)
        result = graph.prepare_variants_node(
            {
                "tasks": [{"id": "t-0", "description": "Fix function"}],
                "current_task_idx": 0,
                "iteration": 1,
                "context": "",
                "reflection_notes": "",
                "results": [
                    WorkerResult("reviewer", "t-0", "needs_revision", "Security issue detected", 0.3),
                ],
            }
        )

        assert len(result["variant_tasks"]) > 0
        assert "Security issue detected" in result["variant_tasks"][0]["context"]

    def test_prepare_variants_incorporates_reflection_notes(self, mock_llm: MagicMock) -> None:
        graph = self._make_graph(mock_llm)
        result = graph.prepare_variants_node(
            {
                "tasks": [{"id": "t-0", "description": "Fix function"}],
                "current_task_idx": 0,
                "iteration": 1,
                "context": "",
                "reflection_notes": "Remove eval() and validate inputs.",
                "results": [],
            }
        )

        assert "Remove eval()" in result["variant_tasks"][0]["context"]
