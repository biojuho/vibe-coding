"""
LangGraph-based multi-agent coding workflow.

Architecture:
    supervisor -> worker team -> evaluator -> (loop or output)

The workflow now carries explicit self-reflection between iterations so the next
coding attempt can respond to tester/reviewer/evaluator feedback instead of
blindly regenerating code.
"""

from __future__ import annotations

import sys
from operator import add
from pathlib import Path
from typing import Annotated, Any

from typing_extensions import TypedDict

try:
    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.constants import Send
    from langgraph.graph import END, START, StateGraph

    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    END = "__end__"
    START = "__start__"

    class MemorySaver:  # type: ignore[override]
        """No-op checkpointer when LangGraph is unavailable."""

        pass

    class Send:  # type: ignore[override]
        """Minimal Send shim for fallback mode."""

        def __init__(self, name: str, payload: dict[str, Any]):
            self.name = name
            self.payload = payload


WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from execution._logging import logger  # noqa: E402
from execution.workers import (  # noqa: E402
    CoderWorker,
    DebuggerWorker,
    ReviewerWorker,
    TesterWorker,
    WorkerResult,
)


class GraphState(TypedDict, total=False):
    """Shared state passed through the coding graph."""

    vibe_input: str
    tasks: list[dict[str, Any]]
    current_task_idx: int
    results: Annotated[list[Any], add]
    iteration: int
    max_iterations: int
    confidence: float
    next_worker: str
    final_output: str
    context: str
    context_files: list[str]
    complexity: str
    variant_tasks: list[dict[str, Any]]
    task_variant: dict[str, Any]
    variant_results: Annotated[list[dict[str, Any]], add]
    errors: Annotated[list[dict[str, Any]], add]
    reflection_notes: str
    evaluator_summary: str


DEFAULT_STATE: dict[str, Any] = {
    "vibe_input": "",
    "tasks": [],
    "current_task_idx": 0,
    "results": [],
    "iteration": 0,
    "max_iterations": 3,
    "confidence": 0.0,
    "next_worker": "prepare_variants",
    "final_output": "",
    "context": "",
    "context_files": [],
    "complexity": "simple",
    "variant_tasks": [],
    "variant_results": [],
    "errors": [],
    "reflection_notes": "",
    "evaluator_summary": "",
}


class _FallbackCompiledGraph:
    """Sequential fallback orchestrator for environments without LangGraph."""

    def __init__(self, owner: "VibeCodingGraph") -> None:
        self.owner = owner

    def invoke(self, initial_state: dict[str, Any], config: dict[str, Any] | None = None) -> dict[str, Any]:
        state = dict(initial_state)
        state.setdefault("results", [])
        state.setdefault("variant_results", [])
        state.setdefault("errors", [])
        state.setdefault("reflection_notes", "")
        state.setdefault("evaluator_summary", "")

        state.update(self.owner.supervisor_node(state))

        while True:
            state.update(self.owner.prepare_variants_node(state))

            for task_variant in state.get("variant_tasks", []):
                patch = self.owner.variant_coder_node({"task_variant": task_variant})
                if patch.get("variant_results"):
                    state["variant_results"] = state.get("variant_results", []) + patch["variant_results"]
                if patch.get("errors"):
                    state["errors"] = state.get("errors", []) + patch["errors"]

            reduce_patch = self.owner.reduce_variants_node(state)
            if reduce_patch.get("results"):
                state["results"] = state.get("results", []) + reduce_patch["results"]
            state["next_worker"] = reduce_patch.get("next_worker", state.get("next_worker", "tester"))

            tester_patch = self.owner.tester_node(state)
            if tester_patch.get("results"):
                state["results"] = state.get("results", []) + tester_patch["results"]
            state["next_worker"] = tester_patch.get("next_worker", state.get("next_worker", "reviewer"))

            if state["next_worker"] == "debugger":
                debugger_patch = self.owner.debugger_node(state)
                if debugger_patch.get("results"):
                    state["results"] = state.get("results", []) + debugger_patch["results"]
                state["next_worker"] = debugger_patch.get("next_worker", "prepare_variants")
                continue

            reviewer_patch = self.owner.reviewer_node(state)
            if reviewer_patch.get("results"):
                state["results"] = state.get("results", []) + reviewer_patch["results"]

            state.update(self.owner.evaluator_node(state))
            if self.owner.route_after_evaluator(state) == "output":
                state.update(self.owner.output_node(state))
                return state


class VibeCodingGraph:
    """Supervisor-worker graph for code generation with evaluator feedback loops."""

    def __init__(
        self,
        llm_client: Any | None = None,
        max_iterations: int = 3,
        checkpointer: Any | None = None,
    ) -> None:
        self.max_iterations = max_iterations
        self.checkpointer = checkpointer or MemorySaver()

        if llm_client is not None:
            self.llm = llm_client
        else:
            try:
                from execution.llm_client import LLMClient

                self.llm = LLMClient()
            except Exception:
                self.llm = None

        self.coder = CoderWorker(self.llm) if self.llm else None
        self.debugger = DebuggerWorker(self.llm) if self.llm else None
        self.tester = TesterWorker()
        self.reviewer = ReviewerWorker(self.llm) if self.llm else None

        try:
            from execution.smart_router import SmartRouter

            self.router = SmartRouter()
        except Exception:
            self.router = None

        try:
            from execution.confidence_verifier import ConfidenceVerifier

            self.verifier = ConfidenceVerifier(llm_client=self.llm) if self.llm else None
        except Exception:
            self.verifier = None

        try:
            from execution.context_selector import ContextProfile, ContextSelector

            self.context_selector = ContextSelector()
            self.context_profile = ContextProfile
        except Exception:
            self.context_selector = None
            self.context_profile = None

        self._graph = self._build_graph()

    def supervisor_node(self, state: dict[str, Any]) -> dict[str, Any]:
        """Classify complexity and decompose the request into tasks."""
        vibe = state.get("vibe_input", "")
        logger.info("[Supervisor] Analyze request: '%s'", vibe[:80])

        complexity = "simple"
        if self.router:
            classification = self.router.classify(vibe)
            complexity = classification.complexity.value
            logger.info("[Supervisor] Complexity=%s (score=%.2f)", complexity, classification.score)

        context = state.get("context", "")
        context_files: list[str] = []
        if self.context_selector and self.context_profile and vibe:
            try:
                selected = self.context_selector.select(
                    vibe, existing_context=context, profile=self.context_profile.CODER
                )
                if selected.text:
                    context = self._merge_context(context, selected.text)
                    context_files = selected.files
                    logger.info("[Supervisor] Selected %d repo context file(s)", len(context_files))
            except Exception as exc:
                logger.warning("[Supervisor] ContextSelector failed; continuing without repo map: %s", exc)

        tasks = self._decompose_tasks(vibe, complexity)
        logger.info("[Supervisor] Decomposed into %d task(s)", len(tasks))

        return {
            "tasks": tasks,
            "current_task_idx": 0,
            "complexity": complexity,
            "next_worker": "prepare_variants",
            "iteration": 0,
            "context": context,
            "context_files": context_files,
            "reflection_notes": "",
            "evaluator_summary": "",
        }

    def prepare_variants_node(self, state: dict[str, Any]) -> dict[str, Any]:
        """Prepare several coding variants, enriched with reflection context."""
        task = self._get_current_task(state)
        if not task or not self.coder:
            return {"variant_tasks": []}

        base_context = state.get("context", "")
        reflection_notes = state.get("reflection_notes", "").strip()
        if reflection_notes:
            base_context += f"\n\nSelf-reflection from the previous attempt:\n{reflection_notes}"

        prev_results = state.get("results", [])
        if prev_results:
            last = prev_results[-1]
            if isinstance(last, WorkerResult) and last.status == "needs_revision":
                base_context += f"\n\nPrevious feedback:\n{last.content}"

        attempt = sum(
            1 for result in prev_results if isinstance(result, WorkerResult) and result.worker_type == "coder"
        )

        variants = [
            {
                **task,
                "id": f"{task.get('id', 't')}-v1",
                "attempt": attempt,
                "context": base_context + "\n\nUse a balanced, straightforward implementation.",
            },
            {
                **task,
                "id": f"{task.get('id', 't')}-v2",
                "attempt": attempt,
                "context": base_context + "\n\nPrioritize defensive programming and edge cases.",
            },
            {
                **task,
                "id": f"{task.get('id', 't')}-v3",
                "attempt": attempt,
                "context": base_context + "\n\nPrioritize a simple and efficient implementation.",
            },
        ]

        logger.info("[PrepareVariants] Prepared %d code variants", len(variants))
        return {"variant_tasks": variants}

    def variant_coder_node(self, state: dict[str, Any]) -> dict[str, Any]:
        """Generate a single code variant and score it with the reviewer."""
        task = state.get("task_variant", {})
        if not task or not self.coder:
            return {}

        logger.info("[VariantCoder] Start variant %s", task.get("id"))
        try:
            result = self.coder.execute(task)

            score = result.confidence
            review_text = ""
            review_metadata: dict[str, Any] = {}
            security_score = int(round(score * 10))

            if result.status == "success" and self.reviewer:
                review_result = self.reviewer.execute({"id": f"rev-{task.get('id')}", "code": result.content})
                score = review_result.confidence
                review_text = review_result.content
                review_metadata = dict(review_result.metadata)
                security_score = int(review_metadata.get("security_score", security_score))

            logger.info(
                "[VariantCoder] Finished %s (score=%.2f, security=%d)",
                task.get("id"),
                score,
                security_score,
            )

            return {
                "variant_results": [
                    {
                        "task_id": task.get("id"),
                        "attempt": task.get("attempt", 0),
                        "code": result.content,
                        "score": score,
                        "security_score": security_score,
                        "review": review_text,
                        "review_metadata": review_metadata,
                        "worker_result": result,
                    }
                ]
            }
        except Exception as exc:
            logger.error("[VariantCoder] Variant failed: %s - %s", task.get("id"), exc)
            return {
                "errors": [
                    {
                        "task_id": task.get("id"),
                        "attempt": task.get("attempt", 0),
                        "error_type": type(exc).__name__,
                        "message": str(exc),
                    }
                ]
            }

    def reduce_variants_node(self, state: dict[str, Any]) -> dict[str, Any]:
        """Choose the best current-attempt variant."""
        variant_results = state.get("variant_results", [])
        errors = state.get("errors", [])

        max_attempt_vr = max((item.get("attempt", 0) for item in variant_results), default=-1)
        max_attempt_err = max((item.get("attempt", 0) for item in errors), default=-1)
        max_attempt = max(max_attempt_vr, max_attempt_err)

        current_vr = [item for item in variant_results if item.get("attempt", 0) == max_attempt]
        current_errors = [item for item in errors if item.get("attempt", 0) == max_attempt]

        if current_errors:
            logger.warning(
                "[ReduceVariants] %d variant error(s): %s",
                len(current_errors),
                [item["message"] for item in current_errors],
            )

        if not current_vr:
            logger.error("[ReduceVariants] All variants failed; falling back to tester with an error payload.")
            error_summary = str([item["message"] for item in current_errors])
            fallback_result = WorkerResult(
                "coder",
                "none",
                "error",
                f"# Fallback: all variants failed\nError summary: {error_summary}",
            )
            fallback_result.confidence = 0.0
            return {"results": [fallback_result], "next_worker": "tester"}

        best_variant = max(
            current_vr,
            key=lambda item: (item.get("score", 0.0), item.get("security_score", 0)),
        )
        logger.info(
            "[ReduceVariants] Selected %s (score=%.2f, security=%s)",
            best_variant["task_id"],
            best_variant.get("score", 0.0),
            best_variant.get("security_score", "n/a"),
        )

        best_result = best_variant["worker_result"]
        best_result.confidence = best_variant.get("score", best_result.confidence)
        best_result.metadata = {
            **best_result.metadata,
            "variant_review": best_variant.get("review_metadata", {}),
            "variant_review_summary": best_variant.get("review", ""),
        }

        return {"results": [best_result], "next_worker": "tester"}

    def debugger_node(self, state: dict[str, Any]) -> dict[str, Any]:
        """Analyze the latest failing tester result."""
        task = self._get_current_task(state)
        if not task or not self.debugger:
            return {"results": [WorkerResult("debugger", "none", "error", "No task or no LLM available")]}

        prev_results = state.get("results", [])
        for result in reversed(prev_results):
            if isinstance(result, WorkerResult) and result.worker_type == "tester" and result.status != "success":
                task["error_log"] = result.content
                break

        for result in reversed(prev_results):
            if isinstance(result, WorkerResult) and result.worker_type == "coder":
                task["source_code"] = result.content
                break

        result = self.debugger.execute(task)
        logger.info("[DebuggerNode] Result=%s", result.status)
        return {"results": [result], "next_worker": "prepare_variants"}

    def tester_node(self, state: dict[str, Any]) -> dict[str, Any]:
        """Execute the latest successful coder output."""
        prev_results = state.get("results", [])
        code = ""
        for result in reversed(prev_results):
            if isinstance(result, WorkerResult) and result.worker_type == "coder" and result.status == "success":
                code = result.content
                break

        task = {"id": f"test-{state.get('iteration', 0)}", "code": code}
        result = self.tester.execute(task)
        logger.info("[TesterNode] Result=%s (rc=%s)", result.status, result.metadata.get("returncode"))

        if result.status == "needs_revision":
            return {"results": [result], "next_worker": "debugger"}
        return {"results": [result], "next_worker": "reviewer"}

    def reviewer_node(self, state: dict[str, Any]) -> dict[str, Any]:
        """Review the latest successful coder output."""
        if not self.reviewer:
            return {"results": [WorkerResult("reviewer", "none", "success", "No LLM available; review skipped", 0.7)]}

        prev_results = state.get("results", [])
        code = ""
        for result in reversed(prev_results):
            if isinstance(result, WorkerResult) and result.worker_type == "coder" and result.status == "success":
                code = result.content
                break

        task = {"id": f"review-{state.get('iteration', 0)}", "code": code}
        result = self.reviewer.execute(task)
        logger.info(
            "[ReviewerNode] Result=%s (confidence=%.2f, security=%s)",
            result.status,
            result.confidence,
            result.metadata.get("security_score"),
        )
        return {"results": [result]}

    def evaluator_node(self, state: dict[str, Any]) -> dict[str, Any]:
        """Combine the latest worker results into a final confidence score."""
        results = state.get("results", [])
        iteration = state.get("iteration", 0)

        latest_coder = self._latest_result(results, "coder")
        latest_tester = self._latest_result(results, "tester")
        latest_reviewer = self._latest_result(results, "reviewer")

        worker_confidences = [
            result.confidence
            for result in (latest_coder, latest_tester, latest_reviewer)
            if isinstance(result, WorkerResult) and result.confidence > 0
        ]
        avg_confidence = sum(worker_confidences) / len(worker_confidences) if worker_confidences else 0.0

        coder_confidence = latest_coder.confidence if latest_coder else avg_confidence
        tester_confidence = latest_tester.confidence if latest_tester else avg_confidence
        reviewer_confidence = latest_reviewer.confidence if latest_reviewer else avg_confidence
        security_confidence = reviewer_confidence
        if latest_reviewer:
            security_confidence = float(latest_reviewer.metadata.get("security_score", reviewer_confidence * 10)) / 10.0

        sage_confidence = avg_confidence
        if self.verifier and latest_coder and latest_coder.status == "success" and avg_confidence > 0.3:
            try:
                verification = self.verifier.verify(
                    question=state.get("vibe_input", ""),
                    answer=latest_coder.content[:500],
                )
                sage_confidence = verification.confidence
                logger.info("[Evaluator] SAGE confidence=%.2f (avg=%.2f)", sage_confidence, avg_confidence)
            except Exception as exc:
                logger.warning("[Evaluator] SAGE verification failed: %s", exc)

        final_confidence = (
            0.20 * coder_confidence
            + 0.25 * tester_confidence
            + 0.25 * reviewer_confidence
            + 0.15 * security_confidence
            + 0.15 * sage_confidence
        )
        reflection_notes = ""
        if final_confidence < 0.7:
            reflection_notes = self._build_reflection_notes(
                latest_tester=latest_tester,
                latest_reviewer=latest_reviewer,
                sage_confidence=sage_confidence,
            )

        evaluator_summary = (
            "coder={coder:.2f}, tester={tester:.2f}, reviewer={reviewer:.2f}, security={security:.2f}, sage={sage:.2f}"
        ).format(
            coder=coder_confidence,
            tester=tester_confidence,
            reviewer=reviewer_confidence,
            security=security_confidence,
            sage=sage_confidence,
        )

        logger.info(
            "[Evaluator] iteration=%d, final=%.2f (%s)",
            iteration,
            final_confidence,
            evaluator_summary,
        )

        return {
            "confidence": final_confidence,
            "iteration": iteration + 1,
            "reflection_notes": reflection_notes,
            "evaluator_summary": evaluator_summary,
        }

    def output_node(self, state: dict[str, Any]) -> dict[str, Any]:
        """Assemble the final output from the latest successful results."""
        results = state.get("results", [])

        final_code = ""
        for result in reversed(results):
            if isinstance(result, WorkerResult) and result.worker_type == "coder" and result.status == "success":
                final_code = result.content
                break

        review_feedback = ""
        for result in reversed(results):
            if isinstance(result, WorkerResult) and result.worker_type == "reviewer":
                review_feedback = result.content
                break

        final_output = f"=== Generated Code ===\n{final_code}"
        if review_feedback:
            final_output += f"\n\n=== Review Feedback ===\n{review_feedback}"
        if state.get("evaluator_summary"):
            final_output += f"\n\n=== Evaluator Summary ===\n{state['evaluator_summary']}"

        logger.info(
            "[Output] Final output assembled (confidence=%.2f, iterations=%d, results=%d)",
            state.get("confidence", 0.0),
            state.get("iteration", 0),
            len(results),
        )
        return {"final_output": final_output}

    def route_after_evaluator(self, state: dict[str, Any]) -> str:
        """Decide whether to loop or terminate after evaluation."""
        confidence = state.get("confidence", 0.0)
        iteration = state.get("iteration", 0)
        max_iter = state.get("max_iterations", self.max_iterations)

        if confidence >= 0.7 or iteration >= max_iter:
            if iteration >= max_iter and confidence < 0.7:
                logger.warning(
                    "[Router] Max iterations reached (iter=%d, confidence=%.2f) -> forcing output",
                    iteration,
                    confidence,
                )
            return "output"

        logger.info("[Router] Looping again (iter=%d, confidence=%.2f < 0.7)", iteration, confidence)
        return "prepare_variants"

    def route_after_tester(self, state: dict[str, Any]) -> str:
        """Route tester results to the appropriate next worker."""
        return state.get("next_worker", "reviewer")

    def _build_worker_subgraph(self) -> Any:
        """Build the worker-team subgraph used by the main graph."""
        if not LANGGRAPH_AVAILABLE:
            return None

        builder = StateGraph(GraphState)
        builder.add_node("prepare_variants", self.prepare_variants_node)
        builder.add_node("variant_coder", self.variant_coder_node)
        builder.add_node("reduce_variants", self.reduce_variants_node)
        builder.add_node("tester", self.tester_node)
        builder.add_node("reviewer", self.reviewer_node)
        builder.add_node("debugger", self.debugger_node)

        builder.add_edge(START, "prepare_variants")

        def map_variants(state: dict[str, Any]) -> list[Send]:
            return [
                Send("variant_coder", {"task_variant": task_variant}) for task_variant in state.get("variant_tasks", [])
            ]

        builder.add_conditional_edges("prepare_variants", map_variants, ["variant_coder"])
        builder.add_edge("variant_coder", "reduce_variants")
        builder.add_edge("reduce_variants", "tester")
        builder.add_edge("reduce_variants", "reviewer")
        builder.add_edge("reviewer", END)

        def route_tester(state: dict[str, Any]) -> str:
            next_worker = self.route_after_tester(state)
            return END if next_worker == "reviewer" else next_worker

        builder.add_conditional_edges("tester", route_tester, {END: END, "debugger": "debugger"})
        builder.add_edge("debugger", "prepare_variants")
        return builder.compile()

    def _build_graph(self) -> Any:
        """Build the main StateGraph or a fallback runner."""
        if not LANGGRAPH_AVAILABLE:
            logger.warning("LangGraph not installed; using fallback orchestration.")
            return _FallbackCompiledGraph(self)

        builder = StateGraph(GraphState)
        worker_subgraph = self._build_worker_subgraph()

        builder.add_node("supervisor", self.supervisor_node)
        builder.add_node("worker_team", worker_subgraph)
        builder.add_node("evaluator", self.evaluator_node)
        builder.add_node("output", self.output_node)

        builder.add_edge(START, "supervisor")
        builder.add_edge("supervisor", "worker_team")
        builder.add_edge("worker_team", "evaluator")

        def route_eval(state: dict[str, Any]) -> str:
            return "worker_team" if self.route_after_evaluator(state) == "prepare_variants" else "output"

        builder.add_conditional_edges(
            "evaluator",
            route_eval,
            {"output": "output", "worker_team": "worker_team"},
        )
        builder.add_edge("output", END)
        return builder.compile(checkpointer=self.checkpointer)

    def run(
        self,
        vibe_input: str,
        *,
        context: str = "",
        max_iterations: int | None = None,
        thread_id: str = "vibe_session_001",
    ) -> dict[str, Any]:
        """Execute the full coding workflow."""
        initial_state = {
            **DEFAULT_STATE,
            "vibe_input": vibe_input,
            "context": context,
            "max_iterations": max_iterations or self.max_iterations,
            "results": [],
        }

        logger.info("=== VibeCodingGraph start ===")
        logger.info("Request: '%s' (thread=%s)", vibe_input[:100], thread_id)

        try:
            config = {"configurable": {"thread_id": thread_id}}
            final_state = self._graph.invoke(initial_state, config=config)
            logger.info(
                "=== VibeCodingGraph done: confidence=%.2f, iterations=%d ===",
                final_state.get("confidence", 0.0),
                final_state.get("iteration", 0),
            )
            return final_state
        except Exception as exc:
            logger.error("VibeCodingGraph failed: %s", exc)
            return {
                **initial_state,
                "final_output": f"Error: {exc}",
                "confidence": 0.0,
            }

    @property
    def graph(self) -> Any:
        """Return the compiled graph object."""
        return self._graph

    def _decompose_tasks(self, vibe: str, complexity: str) -> list[dict[str, Any]]:
        """Use the thought decomposer for non-trivial tasks when available."""
        if complexity in ("moderate", "complex") and self.llm:
            try:
                from execution.thought_decomposer import ThoughtDecomposer

                decomposer = ThoughtDecomposer(llm_client=self.llm)
                tree_result = decomposer.decompose(vibe)
                if tree_result and tree_result.children:
                    return [
                        {"id": f"task-{index}", "description": child.task_text, "type": "code"}
                        for index, child in enumerate(tree_result.children)
                    ]
            except Exception as exc:
                logger.warning("[Supervisor] ThoughtDecomposer failed; using a single task: %s", exc)

        return [{"id": "task-0", "description": vibe, "type": "code"}]

    def _get_current_task(self, state: dict[str, Any]) -> dict[str, Any] | None:
        tasks = state.get("tasks", [])
        idx = state.get("current_task_idx", 0)
        if idx < len(tasks):
            return dict(tasks[idx])
        return None

    @staticmethod
    def _latest_result(results: list[Any], worker_type: str) -> WorkerResult | None:
        for result in reversed(results):
            if isinstance(result, WorkerResult) and result.worker_type == worker_type:
                return result
        return None

    @staticmethod
    def _build_reflection_notes(
        *,
        latest_tester: WorkerResult | None,
        latest_reviewer: WorkerResult | None,
        sage_confidence: float,
    ) -> str:
        """Build a concise optimizer brief for the next coding attempt."""
        notes: list[str] = []

        if latest_tester and latest_tester.status != "success":
            notes.append("Fix the failing execution path before optimizing style.")
            excerpt = latest_tester.content.strip()
            if excerpt:
                notes.append(f"Latest test failure:\n{excerpt[:400]}")

        if latest_reviewer:
            reflection = str(latest_reviewer.metadata.get("reflection", "")).strip()
            if reflection:
                notes.append(f"Reviewer reflection:\n{reflection}")

            review_data = latest_reviewer.metadata.get("review", {})
            issues = list(review_data.get("issues", [])) if isinstance(review_data, dict) else []
            if issues:
                notes.append("Highest priority issues:\n" + "\n".join(f"- {issue}" for issue in issues[:3]))

            security_score = latest_reviewer.metadata.get("security_score")
            security_findings = latest_reviewer.metadata.get("security_findings", [])
            if security_score is not None and float(security_score) < 8:
                notes.append(f"Security score is {security_score}/10; remove risky patterns before the next attempt.")
                if security_findings:
                    notes.append(
                        "Security findings:\n"
                        + "\n".join(
                            f"- {finding.get('rule_id')}: {finding.get('detail')}" for finding in security_findings[:3]
                        )
                    )

        if sage_confidence < 0.7:
            notes.append("Simplify assumptions and make the solution easier to verify end-to-end.")

        if not notes:
            notes.append("Tighten correctness, safety, and maintainability before the next attempt.")

        return "\n\n".join(notes)

    @staticmethod
    def _merge_context(existing: str, selected: str) -> str:
        existing = existing.strip()
        selected = selected.strip()
        if not existing:
            return selected
        if not selected:
            return existing
        return f"{existing}\n\n{selected}"


def main() -> None:
    """Minimal CLI for manual graph testing."""
    import argparse

    parser = argparse.ArgumentParser(description="VibeCodingGraph CLI")
    parser.add_argument("vibe", nargs="?", default="Build a Python fibonacci function")
    parser.add_argument("--max-iter", type=int, default=3)
    args = parser.parse_args()

    graph = VibeCodingGraph(max_iterations=args.max_iter)
    result = graph.run(args.vibe, max_iterations=args.max_iter)

    print("\n" + "=" * 60)
    print(f"  Confidence: {result.get('confidence', 0):.2f}")
    print(f"  Iterations: {result.get('iteration', 0)}")
    print(f"  Results: {len(result.get('results', []))} items")
    print("=" * 60)
    print(result.get("final_output", "(no output)")[:2000])


if __name__ == "__main__":
    main()
