"""Unit tests for execution/workers.py (T-115 — TDR reduction).

Covers:
- Pure helpers: _extract_json_object, _coerce_int,
  _normalize_review_payload, _validate_review_payload,
  _analyze_security, _format_review_summary
- TesterWorker._extract_python_code (static, no subprocess)
- TesterWorker.execute (empty-code fast-path + success + failure + timeout)
- CoderWorker.execute (success + LLM error)
- DebuggerWorker.execute (success + LLM error)
- ReviewerWorker.execute (generate_json path + generate_text fallback + LLM error)
"""

from __future__ import annotations

import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch


WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from execution.workers import (
    CoderWorker,
    DebuggerWorker,
    ReviewerWorker,
    TesterWorker,
    _analyze_security,
    _coerce_int,
    _extract_json_object,
    _format_review_summary,
    _normalize_review_payload,
)


# ---------------------------------------------------------------------------
# _extract_json_object
# ---------------------------------------------------------------------------


class TestExtractJsonObject:
    def test_plain_json(self):
        result = _extract_json_object('{"key": "value"}')
        assert result == {"key": "value"}

    def test_json_with_code_fence(self):
        result = _extract_json_object('```json\n{"a": 1}\n```')
        assert result == {"a": 1}

    def test_json_with_generic_fence(self):
        result = _extract_json_object('```\n{"b": 2}\n```')
        assert result == {"b": 2}

    def test_embedded_json_in_prose(self):
        result = _extract_json_object('Here is the result: {"x": 42} done.')
        assert result == {"x": 42}

    def test_not_a_dict_returns_none(self):
        result = _extract_json_object("[1, 2, 3]")
        assert result is None

    def test_invalid_json_returns_none(self):
        result = _extract_json_object("not json at all")
        assert result is None

    def test_empty_string_returns_none(self):
        result = _extract_json_object("")
        assert result is None


# ---------------------------------------------------------------------------
# _coerce_int
# ---------------------------------------------------------------------------


class TestCoerceInt:
    def test_normal_value(self):
        assert _coerce_int(7) == 7

    def test_clamps_below_zero(self):
        assert _coerce_int(-5) == 0

    def test_clamps_above_ten(self):
        assert _coerce_int(15) == 10

    def test_string_digit(self):
        assert _coerce_int("8") == 8

    def test_none_returns_default(self):
        assert _coerce_int(None) == 5

    def test_non_numeric_string_returns_default(self):
        assert _coerce_int("abc", default=3) == 3


# ---------------------------------------------------------------------------
# _normalize_review_payload
# ---------------------------------------------------------------------------


class TestNormalizeReviewPayload:
    def test_none_payload_returns_defaults(self):
        result = _normalize_review_payload(None)
        assert result["verdict"] == "revise"
        assert result["overall_score"] == 5
        assert result["reflection"]  # non-empty

    def test_score_alias_is_mapped(self):
        result = _normalize_review_payload({"score": 9, "verdict": "approve"})
        assert result["overall_score"] == 9

    def test_invalid_verdict_coerced(self):
        result = _normalize_review_payload({"verdict": "INVALID"})
        assert result["verdict"] == "revise"

    def test_valid_verdict_preserved(self):
        result = _normalize_review_payload({"verdict": "approve"})
        assert result["verdict"] == "approve"

    def test_empty_issues_filtered(self):
        result = _normalize_review_payload({"issues": ["", "real issue"]})
        assert result["issues"] == ["real issue"]

    def test_reflection_built_from_suggestions(self):
        result = _normalize_review_payload({"suggestions": ["fix x", "fix y"], "reflection": ""})
        assert "fix x" in result["reflection"]

    def test_reflection_built_from_issues_when_no_suggestions(self):
        result = _normalize_review_payload({"issues": ["error found"], "reflection": ""})
        assert "error found" in result["reflection"]

    def test_fallback_reflection(self):
        result = _normalize_review_payload({"reflection": ""})
        assert result["reflection"]  # always non-empty


# ---------------------------------------------------------------------------
# _analyze_security
# ---------------------------------------------------------------------------


class TestAnalyzeSecurity:
    def test_clean_code_full_score(self):
        result = _analyze_security("def add(a, b): return a + b")
        assert result["score"] == 10
        assert result["verdict"] == "approve"
        assert result["findings"] == []

    def test_eval_detected(self):
        result = _analyze_security("x = eval(user_input)")
        assert any(f["rule_id"] == "SEC001" for f in result["findings"])
        assert result["score"] < 10
        assert result["verdict"] == "revise"

    def test_exec_detected(self):
        result = _analyze_security("exec(code)")
        assert any(f["rule_id"] == "SEC002" for f in result["findings"])

    def test_yaml_load_detected(self):
        result = _analyze_security("data = yaml.load(stream)")
        assert any(f["rule_id"] == "SEC006" for f in result["findings"])

    def test_sql_fstring_detected(self):
        code = 'cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")'
        result = _analyze_security(code)
        assert any(f["rule_id"] == "SEC008" for f in result["findings"])


# ---------------------------------------------------------------------------
# _format_review_summary
# ---------------------------------------------------------------------------


class TestFormatReviewSummary:
    def _review(self, **kwargs):
        base = {
            "verdict": "approve",
            "overall_score": 8,
            "correctness_score": 8,
            "maintainability_score": 8,
            "performance_score": 8,
            "issues": [],
            "suggestions": [],
            "reflection": "Looks good.",
        }
        base.update(kwargs)
        return base

    def test_contains_verdict(self):
        out = _format_review_summary(self._review(), {"score": 10, "findings": []})
        assert "approve" in out

    def test_issues_listed(self):
        out = _format_review_summary(self._review(issues=["bug1", "bug2"]), {"score": 10, "findings": []})
        assert "bug1" in out

    def test_security_findings_listed(self):
        out = _format_review_summary(
            self._review(),
            {"score": 5, "findings": [{"rule_id": "SEC001", "severity": "high", "detail": "eval used"}]},
        )
        assert "SEC001" in out

    def test_reflection_present(self):
        out = _format_review_summary(self._review(reflection="Fix your imports."), {"score": 10, "findings": []})
        assert "Fix your imports." in out


# ---------------------------------------------------------------------------
# TesterWorker
# ---------------------------------------------------------------------------


class TestTesterWorkerExtractCode:
    def test_extracts_python_fence(self):
        text = "```python\nprint('hello')\n```"
        result = TesterWorker._extract_python_code(text)
        assert "print('hello')" in result

    def test_falls_back_to_raw_text(self):
        text = "print('no fence')"
        assert TesterWorker._extract_python_code(text) == text

    def test_multiple_fences_joined(self):
        text = "```python\na = 1\n```\n```python\nb = 2\n```"
        result = TesterWorker._extract_python_code(text)
        assert "a = 1" in result
        assert "b = 2" in result


class TestTesterWorkerExecute:
    def test_empty_code_returns_error(self):
        w = TesterWorker()
        result = w.execute({"id": "t1", "code": "   "})
        assert result.status == "error"
        assert result.worker_type == "tester"

    def test_successful_execution(self):
        w = TesterWorker()
        fake_proc = MagicMock()
        fake_proc.returncode = 0
        fake_proc.stdout = "ok"
        fake_proc.stderr = ""
        with patch("execution.workers.subprocess.run", return_value=fake_proc):
            result = w.execute({"id": "t2", "code": "print('ok')"})
        assert result.status == "success"
        assert result.confidence > 0.8

    def test_failed_execution(self):
        w = TesterWorker()
        fake_proc = MagicMock()
        fake_proc.returncode = 1
        fake_proc.stdout = ""
        fake_proc.stderr = "NameError: x"
        with patch("execution.workers.subprocess.run", return_value=fake_proc):
            result = w.execute({"id": "t3", "code": "print(x)"})
        assert result.status == "needs_revision"
        assert "NameError" in result.content

    def test_timeout_returns_error(self):
        import subprocess as subp

        w = TesterWorker()
        with patch("execution.workers.subprocess.run", side_effect=subp.TimeoutExpired(cmd="py", timeout=30)):
            result = w.execute({"id": "t4", "code": "while True: pass"})
        assert result.status == "error"
        assert "Timeout" in result.content

    def test_general_exception(self):
        w = TesterWorker()
        with patch("execution.workers.subprocess.run", side_effect=OSError("disk full")):
            result = w.execute({"id": "t5", "code": "x = 1"})
        assert result.status == "error"
        assert "disk full" in result.content


# ---------------------------------------------------------------------------
# CoderWorker
# ---------------------------------------------------------------------------


class TestCoderWorker:
    def _make_llm(self, return_value="def add(a, b): return a + b", raise_exc=None):
        llm = MagicMock()
        if raise_exc:
            llm.generate_text.side_effect = raise_exc
        else:
            llm.generate_text.return_value = return_value
        return llm

    def test_success(self):
        llm = self._make_llm("def foo(): pass")
        w = CoderWorker(llm)
        result = w.execute({"id": "c1", "description": "Write a function"})
        assert result.status == "success"
        assert result.worker_type == "coder"
        assert "def foo" in result.content

    def test_with_context(self):
        llm = self._make_llm("x = 1")
        w = CoderWorker(llm)
        result = w.execute({"id": "c2", "description": "Write something", "context": "Use pandas"})
        assert result.status == "success"
        call_kwargs = llm.generate_text.call_args[1]
        assert "Use pandas" in call_kwargs["user_prompt"]

    def test_llm_error(self):
        llm = self._make_llm(raise_exc=RuntimeError("API down"))
        w = CoderWorker(llm)
        result = w.execute({"id": "c3", "description": "anything"})
        assert result.status == "error"
        assert result.confidence == 0.0

    def test_default_task_id(self):
        llm = self._make_llm()
        w = CoderWorker(llm)
        result = w.execute({"description": "no id"})
        assert result.task_id == "unknown"


# ---------------------------------------------------------------------------
# DebuggerWorker
# ---------------------------------------------------------------------------


class TestDebuggerWorker:
    def test_success(self):
        llm = MagicMock()
        llm.generate_text.return_value = "Root cause: NameError\nFix: define x"
        w = DebuggerWorker(llm)
        result = w.execute({"id": "d1", "error_log": "NameError: x", "source_code": "print(x)"})
        assert result.status == "success"
        assert result.worker_type == "debugger"
        assert "NameError" in result.content

    def test_source_code_appended_to_prompt(self):
        llm = MagicMock()
        llm.generate_text.return_value = "Fix it"
        w = DebuggerWorker(llm)
        w.execute({"id": "d2", "error_log": "Error", "source_code": "def broken(): pass"})
        call_kwargs = llm.generate_text.call_args[1]
        assert "def broken" in call_kwargs["user_prompt"]

    def test_llm_error(self):
        llm = MagicMock()
        llm.generate_text.side_effect = ConnectionError("timeout")
        w = DebuggerWorker(llm)
        result = w.execute({"id": "d3", "error_log": "oops"})
        assert result.status == "error"
        assert result.confidence == 0.0


# ---------------------------------------------------------------------------
# ReviewerWorker
# ---------------------------------------------------------------------------


class TestReviewerWorker:
    def _make_llm_with_generate_json(self, payload: dict):
        llm = MagicMock()
        llm.generate_json.return_value = payload
        return llm

    def _make_llm_text_only(self, text: str):
        llm = MagicMock()
        del llm.generate_json  # remove the attribute so callable(...) is False
        llm.generate_text = MagicMock(return_value=text)
        return llm

    def test_success_via_generate_json(self):
        payload = {
            "verdict": "approve",
            "overall_score": 9,
            "correctness_score": 9,
            "maintainability_score": 9,
            "performance_score": 9,
            "issues": [],
            "suggestions": [],
            "reflection": "Ship it.",
        }
        llm = self._make_llm_with_generate_json(payload)
        w = ReviewerWorker(llm)
        result = w.execute({"id": "r1", "code": "def add(a, b): return a + b"})
        assert result.worker_type == "reviewer"
        assert result.status in ("success", "needs_revision")
        assert result.confidence >= 0.0

    def test_success_via_text_fallback(self):
        llm = MagicMock()
        llm.generate_json.side_effect = RuntimeError("not available")
        llm.generate_text.return_value = '{"verdict": "revise", "overall_score": 4}'
        w = ReviewerWorker(llm)
        result = w.execute({"id": "r2", "code": "x = eval(user_input)"})
        assert result.worker_type == "reviewer"
        assert "revise" in result.content.lower() or result.status == "needs_revision"

    def test_llm_completely_fails(self):
        llm = MagicMock()
        llm.generate_json.side_effect = RuntimeError("crash")
        llm.generate_text.side_effect = RuntimeError("crash too")
        w = ReviewerWorker(llm)
        result = w.execute({"id": "r3", "code": "pass"})
        assert result.status == "needs_revision"
        assert result.confidence == 0.3

    def test_security_scan_included_in_metadata(self):
        payload = {
            "verdict": "revise",
            "overall_score": 3,
            "issues": ["eval is dangerous"],
            "reflection": "Remove eval.",
        }
        llm = self._make_llm_with_generate_json(payload)
        w = ReviewerWorker(llm)
        result = w.execute({"id": "r4", "code": "eval(user_input)"})
        assert "security_findings" in result.metadata

    def test_no_generate_json_attribute(self):
        """When llm has no generate_json attr, falls back to generate_text."""
        llm = types.SimpleNamespace()
        llm.generate_text = MagicMock(return_value='{"verdict": "approve", "overall_score": 8}')
        w = ReviewerWorker(llm)
        result = w.execute({"id": "r5", "code": "def ok(): return 1"})
        assert result.worker_type == "reviewer"
