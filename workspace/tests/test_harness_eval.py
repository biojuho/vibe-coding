"""execution/harness_eval.py 테스트.

Generator-Evaluator 패턴의 오케스트레이션 로직을 검증.
실제 LLM 호출 없이 mock으로 테스트.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from execution.harness_eval import (
    EvaluationResult,
    GeneratorEvaluator,
    _build_evaluator_prompt,
    _build_repair_prompt,
)


# ── Prompt builders ──────────────────────────────────────────────


class TestPromptBuilders:
    def test_evaluator_prompt_includes_criteria(self):
        prompt = _build_evaluator_prompt(
            "Write a poem",
            "Roses are red...",
            ["Must rhyme", "Must be 4 lines"],
        )
        assert "Must rhyme" in prompt
        assert "Must be 4 lines" in prompt
        assert "Write a poem" in prompt
        assert "Roses are red" in prompt

    def test_repair_prompt_includes_feedback(self):
        prompt = _build_repair_prompt(
            "Be creative",
            "Write something",
            "Bad output",
            "Needs more detail",
        )
        assert "Bad output" in prompt
        assert "Needs more detail" in prompt
        assert "Be creative" in prompt


# ── EvaluationResult ─────────────────────────────────────────────


class TestEvaluationResult:
    def test_basic_creation(self):
        r = EvaluationResult(
            passed=True,
            score=1.0,
            feedback="All criteria met.",
            criteria_results={"criterion_1": True},
        )
        assert r.passed is True
        assert r.score == 1.0


# ── GeneratorEvaluator (mocked) ──────────────────────────────────


class TestGeneratorEvaluatorPassOnFirst:
    """Generator output passes evaluation on first try."""

    def test_single_round_pass(self):
        mock_session = MagicMock()
        mock_session.generate_text.return_value = "Perfect output"
        mock_session.generate_json.return_value = {
            "passed": True,
            "score": 1.0,
            "feedback": "All criteria met.",
            "criteria_results": {"is_valid": True},
        }

        ge = GeneratorEvaluator(
            evaluator_criteria=["Output must be valid."],
            max_rounds=3,
            session=mock_session,
        )
        result = ge.run(system_prompt="Be helpful", user_prompt="Do task")

        assert result.passed is True
        assert result.rounds_used == 1
        assert result.final_output == "Perfect output"
        assert len(result.evaluation_log) == 1
        assert result.evaluation_log[0]["passed"] is True

        # Only 1 generate_text call (generator), 1 generate_json call (evaluator)
        assert mock_session.generate_text.call_count == 1
        assert mock_session.generate_json.call_count == 1


class TestGeneratorEvaluatorRepairLoop:
    """Generator output fails first, succeeds on repair."""

    def test_repair_on_second_round(self):
        mock_session = MagicMock()

        # Generator: first output bad, second output good
        mock_session.generate_text.side_effect = [
            "Bad output",  # Round 1: generator
            "Fixed output",  # Round 2: repair
        ]
        # Evaluator: first fails, second passes
        mock_session.generate_json.side_effect = [
            {
                "passed": False,
                "score": 0.5,
                "feedback": "Missing required field 'title'.",
                "criteria_results": {"has_title": False, "is_korean": True},
            },
            {
                "passed": True,
                "score": 1.0,
                "feedback": "All criteria met.",
                "criteria_results": {"has_title": True, "is_korean": True},
            },
        ]

        ge = GeneratorEvaluator(
            evaluator_criteria=["Must have title", "Must be Korean"],
            max_rounds=3,
            session=mock_session,
        )
        result = ge.run(system_prompt="sys", user_prompt="task")

        assert result.passed is True
        assert result.rounds_used == 2
        assert result.final_output == "Fixed output"
        assert len(result.evaluation_log) == 2
        assert result.evaluation_log[0]["passed"] is False
        assert result.evaluation_log[1]["passed"] is True


class TestGeneratorEvaluatorMaxRoundsExhausted:
    """All rounds fail — returns best output."""

    def test_exhausted_returns_best(self):
        mock_session = MagicMock()

        mock_session.generate_text.side_effect = [
            "Output v1",
            "Output v2",
        ]
        mock_session.generate_json.side_effect = [
            {"passed": False, "score": 0.3, "feedback": "Bad.", "criteria_results": {}},
            {"passed": False, "score": 0.6, "feedback": "Better but not enough.", "criteria_results": {}},
        ]

        ge = GeneratorEvaluator(
            evaluator_criteria=["Must be perfect"],
            max_rounds=2,
            session=mock_session,
        )
        result = ge.run(system_prompt="sys", user_prompt="task")

        assert result.passed is False
        assert result.rounds_used == 2
        # Best score was 0.6 from "Output v2"
        assert result.final_output == "Output v2"


class TestGeneratorEvaluatorWithThreshold:
    """Pass threshold below 1.0 allows partial passes."""

    def test_threshold_below_one(self):
        mock_session = MagicMock()
        mock_session.generate_text.return_value = "Decent output"
        mock_session.generate_json.return_value = {
            "passed": False,  # Evaluator says no, but score above threshold
            "score": 0.8,
            "feedback": "Minor issues.",
            "criteria_results": {"a": True, "b": True, "c": False},
        }

        ge = GeneratorEvaluator(
            evaluator_criteria=["a", "b", "c"],
            max_rounds=2,
            pass_threshold=0.7,  # 0.8 >= 0.7 → pass
            session=mock_session,
        )
        result = ge.run(system_prompt="sys", user_prompt="task")

        assert result.passed is True
        assert result.rounds_used == 1


class TestGeneratorEvaluatorEvalError:
    """Evaluator LLM call fails gracefully."""

    def test_evaluator_error_treated_as_fail(self):
        mock_session = MagicMock()
        mock_session.generate_text.return_value = "Some output"
        mock_session.generate_json.side_effect = RuntimeError("Provider down")

        ge = GeneratorEvaluator(
            evaluator_criteria=["Must work"],
            max_rounds=1,
            session=mock_session,
        )
        result = ge.run(system_prompt="sys", user_prompt="task")

        assert result.passed is False
        assert result.rounds_used == 1
        assert "error" in result.evaluation_log[0]["feedback"].lower()
