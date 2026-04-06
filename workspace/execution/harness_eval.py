"""Generator-Evaluator Harness — Anthropic's 3-agent pattern for reliable output.

Part of Harness Engineering AI Phase 2-3 (ADR-025).

Implements the generator-evaluator split:
  1. **Generator**: produces an output from a prompt.
  2. **Evaluator**: scores/validates the output against explicit criteria.
  3. **Orchestrator**: loops generator → evaluator up to N rounds,
     feeding evaluator feedback back into the generator.

This pattern catches hallucinations, format violations, and quality regressions
that a single LLM pass would miss — without changing the model.

Usage::

    from execution.harness_eval import GeneratorEvaluator

    ge = GeneratorEvaluator(
        evaluator_criteria=[
            "Output must be valid JSON with 'title' and 'body' keys.",
            "Title must be under 80 characters.",
            "Body must be in Korean.",
        ],
        max_rounds=3,
    )
    result = ge.run(
        system_prompt="You are a social media content writer.",
        user_prompt="Write a Twitter post about AI harness engineering.",
    )
    print(result.final_output)
    print(result.evaluation_log)
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class EvaluationResult:
    """Outcome of a single evaluator pass."""

    passed: bool
    score: float  # 0.0 to 1.0
    feedback: str  # Human-readable feedback for the generator
    criteria_results: dict[str, bool]  # Per-criterion pass/fail


@dataclass
class GeneratorEvaluatorResult:
    """Final outcome of a generator-evaluator run."""

    final_output: str
    rounds_used: int
    passed: bool
    total_latency_ms: float
    evaluation_log: list[dict[str, Any]]


# ---------------------------------------------------------------------------
# Evaluator
# ---------------------------------------------------------------------------

_EVALUATOR_SYSTEM = """You are a strict quality evaluator. You will receive:
1. The ORIGINAL PROMPT that was given to a generator.
2. The generator's OUTPUT.
3. A list of CRITERIA to check.

For each criterion, determine PASS or FAIL.
Return a JSON object with exactly this structure:
{
  "passed": true/false,        // true only if ALL criteria pass
  "score": 0.0-1.0,           // fraction of criteria that passed
  "criteria_results": {
    "criterion_1": true/false,
    "criterion_2": true/false
  },
  "feedback": "..."           // Specific, actionable feedback for the generator
                              // If all criteria pass, say "All criteria met."
}

Be strict. Do NOT pass anything that clearly violates a criterion."""


def _build_evaluator_prompt(
    original_prompt: str,
    output: str,
    criteria: list[str],
) -> str:
    criteria_text = "\n".join(f"  {i + 1}. {c}" for i, c in enumerate(criteria))
    return f"""## Original Prompt
{original_prompt}

## Generator Output
{output}

## Criteria to Check
{criteria_text}

Evaluate the output against each criterion. Return JSON only."""


_REPAIR_SYSTEM = """You are a content generator that MUST fix issues identified by a quality evaluator.
You will receive:
1. Your previous output that failed evaluation.
2. Specific feedback about what to fix.

Produce a corrected version that addresses ALL feedback points.
Output ONLY the corrected content — no explanations, no markdown fences."""


def _build_repair_prompt(
    original_system: str,
    original_user: str,
    previous_output: str,
    feedback: str,
) -> str:
    return f"""## Original Task
System: {original_system}
User: {original_user}

## Your Previous Output (FAILED evaluation)
{previous_output}

## Evaluator Feedback (MUST address all points)
{feedback}

Produce the corrected output now."""


# ---------------------------------------------------------------------------
# Generator-Evaluator Orchestrator
# ---------------------------------------------------------------------------


class GeneratorEvaluator:
    """Orchestrates generator → evaluator loop with feedback.

    Parameters
    ----------
    evaluator_criteria:
        List of human-readable criteria the output must satisfy.
    max_rounds:
        Maximum generate → evaluate cycles before giving up.
    pass_threshold:
        Minimum score (0.0-1.0) to consider evaluation passed.
        Default ``1.0`` means *all* criteria must pass.
    session:
        Optional ``HarnessSession`` to use for LLM calls.
        If *None*, creates a default session.
    """

    def __init__(
        self,
        evaluator_criteria: list[str],
        *,
        max_rounds: int = 3,
        pass_threshold: float = 1.0,
        session: Any = None,
    ) -> None:
        self.criteria = evaluator_criteria
        self.max_rounds = max(1, max_rounds)
        self.pass_threshold = pass_threshold
        self._session = session

    def _get_session(self) -> Any:
        if self._session is None:
            from execution.harness_middleware import HarnessSession

            self._session = HarnessSession(agent_id="generator-evaluator")
        return self._session

    def _evaluate(self, original_prompt: str, output: str) -> EvaluationResult:
        """Run the evaluator LLM on the generator's output."""
        session = self._get_session()
        eval_prompt = _build_evaluator_prompt(original_prompt, output, self.criteria)

        try:
            raw = session.generate_json(
                system_prompt=_EVALUATOR_SYSTEM,
                user_prompt=eval_prompt,
                temperature=0.1,  # Low temp for consistent evaluation
            )
        except Exception as e:
            logger.warning("Evaluator LLM call failed: %s — treating as FAIL", e)
            return EvaluationResult(
                passed=False,
                score=0.0,
                feedback=f"Evaluator error: {e}",
                criteria_results={},
            )

        # Parse evaluator response
        passed = bool(raw.get("passed", False))
        score = float(raw.get("score", 0.0))
        feedback = str(raw.get("feedback", "No feedback provided."))
        criteria_results = {}
        for key, value in raw.get("criteria_results", {}).items():
            criteria_results[str(key)] = bool(value)

        if score >= self.pass_threshold:
            passed = True

        return EvaluationResult(
            passed=passed,
            score=score,
            feedback=feedback,
            criteria_results=criteria_results,
        )

    def run(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
    ) -> GeneratorEvaluatorResult:
        """Execute the full generator → evaluator loop.

        Returns the best output found within *max_rounds*.
        """
        session = self._get_session()
        start = time.time()
        log: list[dict[str, Any]] = []
        current_output = ""
        best_output = ""
        best_score = -1.0

        for round_num in range(1, self.max_rounds + 1):
            # -- Generate --------------------------------------------------
            if round_num == 1:
                # First round: normal generation
                current_output = session.generate_text(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=temperature,
                )
            else:
                # Subsequent rounds: repair based on feedback
                prev_feedback = log[-1]["feedback"] if log else ""
                repair_prompt = _build_repair_prompt(
                    system_prompt,
                    user_prompt,
                    current_output,
                    prev_feedback,
                )
                current_output = session.generate_text(
                    system_prompt=_REPAIR_SYSTEM,
                    user_prompt=repair_prompt,
                    temperature=max(0.3, temperature - 0.1 * round_num),
                )

            # -- Evaluate --------------------------------------------------
            evaluation = self._evaluate(
                original_prompt=f"{system_prompt}\n\n{user_prompt}",
                output=current_output,
            )

            # Track best
            if evaluation.score > best_score:
                best_score = evaluation.score
                best_output = current_output

            log.append(
                {
                    "round": round_num,
                    "passed": evaluation.passed,
                    "score": evaluation.score,
                    "feedback": evaluation.feedback,
                    "criteria_results": evaluation.criteria_results,
                    "output_preview": current_output[:200],
                }
            )

            logger.info(
                "[gen-eval round %d/%d] score=%.2f passed=%s",
                round_num,
                self.max_rounds,
                evaluation.score,
                evaluation.passed,
            )

            if evaluation.passed:
                break

        elapsed_ms = (time.time() - start) * 1000

        return GeneratorEvaluatorResult(
            final_output=best_output if best_output else current_output,
            rounds_used=len(log),
            passed=any(entry["passed"] for entry in log),
            total_latency_ms=round(elapsed_ms, 1),
            evaluation_log=log,
        )
