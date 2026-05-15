"""
Worker nodes for the LangGraph-based coding workflow.

Each worker is intentionally lightweight:
- `CoderWorker` asks the LLM for code
- `DebuggerWorker` analyzes failures
- `TesterWorker` executes generated code in a temp file
- `ReviewerWorker` produces a structured review plus a deterministic security score
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

try:
    from pydantic import BaseModel, Field, ValidationError

    _HAS_PYDANTIC = True
except ImportError:  # graceful degradation
    BaseModel = object  # type: ignore[assignment]
    ValidationError = ValueError  # type: ignore[assignment]

    def Field(default: Any = None, **_: Any) -> Any:
        return default

    _HAS_PYDANTIC = False

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from execution._logging import logger  # noqa: E402


if _HAS_PYDANTIC:

    class ReviewPayload(BaseModel):
        """Structured reviewer payload validated with Pydantic when available."""

        verdict: Literal["approve", "revise"] = Field(default="revise")
        overall_score: int = Field(default=5, ge=0, le=10)
        correctness_score: int = Field(default=5, ge=0, le=10)
        maintainability_score: int = Field(default=5, ge=0, le=10)
        performance_score: int = Field(default=5, ge=0, le=10)
        issues: list[str] = Field(default_factory=list)
        suggestions: list[str] = Field(default_factory=list)
        reflection: str = Field(default="")


_SECURITY_RULES = (
    {
        "rule_id": "SEC001",
        "severity": "high",
        "penalty": 4,
        "pattern": re.compile(r"\beval\s*\("),
        "message": "Avoid eval(); use safe parsing or explicit dispatch instead.",
    },
    {
        "rule_id": "SEC002",
        "severity": "high",
        "penalty": 4,
        "pattern": re.compile(r"\bexec\s*\("),
        "message": "Avoid exec(); it executes arbitrary code.",
    },
    {
        "rule_id": "SEC003",
        "severity": "high",
        "penalty": 4,
        "pattern": re.compile(
            r"subprocess\.(?:run|Popen|call|check_call|check_output)\([^)]*shell\s*=\s*True",
            re.DOTALL,
        ),
        "message": "Avoid subprocess shell=True unless arguments are strictly controlled.",
    },
    {
        "rule_id": "SEC004",
        "severity": "high",
        "penalty": 3,
        "pattern": re.compile(r"\bos\.system\s*\("),
        "message": "Avoid os.system(); prefer subprocess with explicit arguments.",
    },
    {
        "rule_id": "SEC005",
        "severity": "medium",
        "penalty": 3,
        "pattern": re.compile(r"\b(?:pickle|dill)\.loads\s*\("),
        "message": "Avoid unsafe deserialization with pickle.loads/dill.loads on untrusted input.",
    },
    {
        "rule_id": "SEC006",
        "severity": "medium",
        "penalty": 2,
        "pattern": re.compile(r"\byaml\.load\s*\("),
        "message": "Prefer yaml.safe_load() for untrusted YAML.",
    },
    {
        "rule_id": "SEC007",
        "severity": "high",
        "penalty": 3,
        "pattern": re.compile(
            r'(?:api_key|secret|password|token)\s*=\s*["\'][A-Za-z0-9_\-]{20,}["\']',
            re.IGNORECASE,
        ),
        "message": "Remove hardcoded credentials and load them from environment or secrets storage.",
    },
    {
        "rule_id": "SEC008",
        "severity": "high",
        "penalty": 3,
        "pattern": re.compile(
            r'f["\'].*\b(?:SELECT|INSERT|UPDATE|DELETE|DROP|CREATE)\b.*\{[^}]+\}',
            re.IGNORECASE,
        ),
        "message": "Avoid composing SQL with f-strings; parameterize values and validate identifiers.",
    },
)


def _extract_json_object(text: str) -> dict[str, Any] | None:
    """Best-effort JSON extraction from a free-form LLM response."""
    cleaned = text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    try:
        parsed = json.loads(cleaned)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if not match:
        return None

    try:
        parsed = json.loads(match.group())
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        return None


def _coerce_int(value: Any, *, default: int = 5) -> int:
    try:
        return max(0, min(10, int(value)))
    except (TypeError, ValueError):
        return default


def _normalize_review_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    payload = dict(payload or {})

    if "overall_score" not in payload and "score" in payload:
        payload["overall_score"] = payload.get("score")

    normalized = {
        "verdict": str(payload.get("verdict", "revise")).lower(),
        "overall_score": _coerce_int(payload.get("overall_score"), default=5),
        "correctness_score": _coerce_int(
            payload.get("correctness_score", payload.get("overall_score")),
            default=5,
        ),
        "maintainability_score": _coerce_int(
            payload.get("maintainability_score", payload.get("overall_score")),
            default=5,
        ),
        "performance_score": _coerce_int(
            payload.get("performance_score", payload.get("overall_score")),
            default=5,
        ),
        "issues": [str(item).strip() for item in payload.get("issues", []) if str(item).strip()],
        "suggestions": [str(item).strip() for item in payload.get("suggestions", []) if str(item).strip()],
        "reflection": str(payload.get("reflection", "")).strip(),
    }

    if normalized["verdict"] not in {"approve", "revise"}:
        normalized["verdict"] = "revise"

    if not normalized["reflection"]:
        if normalized["suggestions"]:
            normalized["reflection"] = "Apply these fixes before the next attempt: " + "; ".join(
                normalized["suggestions"][:3]
            )
        elif normalized["issues"]:
            normalized["reflection"] = "Resolve these issues before the next attempt: " + "; ".join(
                normalized["issues"][:3]
            )
        else:
            normalized["reflection"] = (
                "Tighten correctness, defensive handling, and maintainability before the next attempt."
            )

    return normalized


def _validate_review_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    normalized = _normalize_review_payload(payload)
    if not _HAS_PYDANTIC:
        return normalized

    try:
        if hasattr(ReviewPayload, "model_validate"):
            review = ReviewPayload.model_validate(normalized)  # type: ignore[attr-defined]
            return review.model_dump()

        review = ReviewPayload.parse_obj(normalized)  # type: ignore[attr-defined]
        return review.dict()
    except ValidationError as exc:
        logger.warning("[ReviewerWorker] Structured review validation failed: %s", exc)
        return _normalize_review_payload(normalized)


def _analyze_security(code: str) -> dict[str, Any]:
    """Run a deterministic lightweight security scan on generated code."""
    findings: list[dict[str, str]] = []
    penalty = 0

    for rule in _SECURITY_RULES:
        if rule["pattern"].search(code):
            findings.append(
                {
                    "rule_id": rule["rule_id"],
                    "severity": rule["severity"],
                    "detail": rule["message"],
                }
            )
            penalty += int(rule["penalty"])

    score = max(0, 10 - penalty)
    verdict = "approve" if score >= 8 and not any(f["severity"] == "high" for f in findings) else "revise"
    return {
        "score": score,
        "verdict": verdict,
        "findings": findings,
    }


def _format_review_summary(review: dict[str, Any], security_scan: dict[str, Any]) -> str:
    issue_lines = [f"- {item}" for item in review.get("issues", [])[:4]]
    suggestion_lines = [f"- {item}" for item in review.get("suggestions", [])[:4]]
    security_lines = [
        f"- {finding['rule_id']} ({finding['severity']}): {finding['detail']}"
        for finding in security_scan.get("findings", [])[:4]
    ]

    parts = [
        f"Verdict: {review.get('verdict', 'revise')}",
        (
            "Scores: overall={overall}/10, correctness={correctness}/10, "
            "maintainability={maintainability}/10, performance={performance}/10, security={security}/10"
        ).format(
            overall=review.get("overall_score", 5),
            correctness=review.get("correctness_score", 5),
            maintainability=review.get("maintainability_score", 5),
            performance=review.get("performance_score", 5),
            security=security_scan.get("score", 5),
        ),
    ]

    if issue_lines:
        parts.append("Issues:\n" + "\n".join(issue_lines))
    if suggestion_lines:
        parts.append("Suggestions:\n" + "\n".join(suggestion_lines))
    if security_lines:
        parts.append("Security Findings:\n" + "\n".join(security_lines))

    parts.append("Self-Reflection:\n" + review.get("reflection", "Regenerate with clearer structure and safer code."))
    return "\n\n".join(parts)


@dataclass
class WorkerResult:
    """Worker execution result."""

    worker_type: str
    task_id: str
    status: str  # "success" | "error" | "needs_revision"
    content: str = ""
    confidence: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


class CoderWorker:
    """Worker that asks the LLM to generate code."""

    def __init__(self, llm_client: Any) -> None:
        self.llm = llm_client

    def execute(self, task: dict[str, Any]) -> WorkerResult:
        task_id = task.get("id", "unknown")
        description = task.get("description", "")
        context = task.get("context", "")

        system_prompt = textwrap.dedent(
            """\
            You are a senior software engineer.
            Produce clean, well-structured Python code for the requested task.
            Include type hints, docstrings, and practical error handling where helpful.
            Return code only.
            """
        )

        user_prompt = f"Task: {description}"
        if context:
            user_prompt += f"\n\nContext:\n{context}"

        try:
            result = self.llm.generate_text(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )
            logger.info("[CoderWorker] Code generated (task=%s, %d chars)", task_id, len(result))
            return WorkerResult(
                worker_type="coder",
                task_id=task_id,
                status="success",
                content=result,
                confidence=0.8,
                metadata={"char_count": len(result)},
            )
        except Exception as exc:
            logger.warning("[CoderWorker] Failed (task=%s): %s", task_id, exc)
            return WorkerResult(
                worker_type="coder",
                task_id=task_id,
                status="error",
                content=str(exc),
                confidence=0.0,
            )


class DebuggerWorker:
    """Worker that analyzes a failing code path."""

    def __init__(self, llm_client: Any) -> None:
        self.llm = llm_client

    def execute(self, task: dict[str, Any]) -> WorkerResult:
        task_id = task.get("id", "unknown")
        error_log = task.get("error_log", "")
        source_code = task.get("source_code", "")

        system_prompt = textwrap.dedent(
            """\
            You are a senior debugger.
            Analyze the failure and provide:
            1. Root cause
            2. A concrete fix
            3. A prevention note
            """
        )

        user_prompt = f"Error log:\n{error_log}"
        if source_code:
            user_prompt += f"\n\nSource code:\n{source_code}"

        try:
            result = self.llm.generate_text(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )
            logger.info("[DebuggerWorker] Analysis complete (task=%s)", task_id)
            return WorkerResult(
                worker_type="debugger",
                task_id=task_id,
                status="success",
                content=result,
                confidence=0.75,
            )
        except Exception as exc:
            logger.warning("[DebuggerWorker] Failed: %s", exc)
            return WorkerResult(
                worker_type="debugger",
                task_id=task_id,
                status="error",
                content=str(exc),
                confidence=0.0,
            )


class TesterWorker:
    """Worker that executes generated Python code in a temp file."""

    TIMEOUT_SEC = 30

    def execute(self, task: dict[str, Any]) -> WorkerResult:
        task_id = task.get("id", "unknown")
        code = task.get("code", "")
        tmp_path: str | None = None
        stdout_path: str | None = None
        stderr_path: str | None = None

        if not code.strip():
            return WorkerResult(
                worker_type="tester",
                task_id=task_id,
                status="error",
                content="Empty code; nothing to execute.",
                confidence=0.0,
            )

        clean_code = self._extract_python_code(code)

        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                suffix=".py",
                delete=False,
                encoding="utf-8",
            ) as handle:
                handle.write(clean_code)
                tmp_path = handle.name

            with tempfile.NamedTemporaryFile(delete=False) as stdout_handle:
                stdout_path = stdout_handle.name
            with tempfile.NamedTemporaryFile(delete=False) as stderr_handle:
                stderr_path = stderr_handle.name

            child_env = os.environ.copy()
            child_env.setdefault("PYTHONUTF8", "1")
            with (
                open(os.devnull, "rb") as stdin_handle,
                open(stdout_path, "wb") as stdout_handle,
                open(stderr_path, "wb") as stderr_handle,
            ):
                proc = subprocess.run(
                    [sys.executable, "-X", "utf8", tmp_path],
                    stdin=stdin_handle,
                    stdout=stdout_handle,
                    stderr=stderr_handle,
                    timeout=self.TIMEOUT_SEC,
                    cwd=str(WORKSPACE_ROOT),
                    env=child_env,
                )

            stdout_text = getattr(proc, "stdout", None)
            stderr_text = getattr(proc, "stderr", None)
            if stdout_text is None:
                stdout_text = Path(stdout_path).read_text(encoding="utf-8", errors="replace")
            if stderr_text is None:
                stderr_text = Path(stderr_path).read_text(encoding="utf-8", errors="replace")

            _safe_unlink(tmp_path)
            _safe_unlink(stdout_path)
            _safe_unlink(stderr_path)

            if proc.returncode == 0:
                logger.info("[TesterWorker] Execution passed (task=%s)", task_id)
                return WorkerResult(
                    worker_type="tester",
                    task_id=task_id,
                    status="success",
                    content=stdout_text[:2000] if stdout_text else "(no output)",
                    confidence=0.9,
                    metadata={"returncode": 0},
                )

            logger.warning("[TesterWorker] Execution failed (task=%s, rc=%d)", task_id, proc.returncode)
            return WorkerResult(
                worker_type="tester",
                task_id=task_id,
                status="needs_revision",
                content=f"STDERR:\n{stderr_text[:2000]}",
                confidence=0.2,
                metadata={"returncode": proc.returncode},
            )

        except subprocess.TimeoutExpired:
            _safe_unlink(tmp_path)
            _safe_unlink(stdout_path)
            _safe_unlink(stderr_path)
            return WorkerResult(
                worker_type="tester",
                task_id=task_id,
                status="error",
                content=f"Timeout exceeded ({self.TIMEOUT_SEC}s).",
                confidence=0.0,
            )
        except Exception as exc:
            _safe_unlink(tmp_path)
            _safe_unlink(stdout_path)
            _safe_unlink(stderr_path)
            return WorkerResult(
                worker_type="tester",
                task_id=task_id,
                status="error",
                content=str(exc),
                confidence=0.0,
            )

    @staticmethod
    def _extract_python_code(text: str) -> str:
        pattern = r"```(?:python)?\s*\n(.*?)```"
        matches = re.findall(pattern, text, re.DOTALL)
        if matches:
            return "\n\n".join(matches)
        return text


def _safe_unlink(path: str | None) -> None:
    if not path:
        return
    try:
        Path(path).unlink(missing_ok=True)
    except PermissionError:
        logger.debug("Temp file still locked during cleanup: %s", path)


class ReviewerWorker:
    """Worker that performs structured code review and security scoring."""

    def __init__(self, llm_client: Any) -> None:
        self.llm = llm_client

    def execute(self, task: dict[str, Any]) -> WorkerResult:
        task_id = task.get("id", "unknown")
        code = task.get("code", "")
        security_scan = _analyze_security(code)

        system_prompt = textwrap.dedent(
            """\
            You are a senior code reviewer.
            Review the code and respond with JSON only.
            Use these fields:
            {
              "overall_score": 0-10,
              "correctness_score": 0-10,
              "maintainability_score": 0-10,
              "performance_score": 0-10,
              "issues": ["issue", ...],
              "suggestions": ["suggestion", ...],
              "reflection": "one concise paragraph telling the next coding attempt what to improve",
              "verdict": "approve" | "revise"
            }
            Focus on correctness, maintainability, performance, and error handling.
            Security is scored separately by a deterministic scan, so do not add extra keys.
            """
        )

        security_context = "None detected."
        if security_scan["findings"]:
            security_context = "\n".join(
                f"- {finding['rule_id']} ({finding['severity']}): {finding['detail']}"
                for finding in security_scan["findings"]
            )

        user_prompt = f"Code to review:\n{code}\n\nDeterministic security scan findings:\n{security_context}"

        try:
            raw_payload: dict[str, Any] | None = None
            json_generator = getattr(self.llm, "generate_json", None)
            if callable(json_generator):
                try:
                    candidate = json_generator(
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                    )
                    if isinstance(candidate, dict):
                        raw_payload = candidate
                except Exception as exc:
                    logger.debug("[ReviewerWorker] generate_json fallback: %s", exc)

            raw_text = ""
            if raw_payload is None:
                raw_text = self.llm.generate_text(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                )
                raw_payload = _extract_json_object(raw_text)

            review = _validate_review_payload(raw_payload)
            dimension_average = (
                review["correctness_score"]
                + review["maintainability_score"]
                + review["performance_score"]
                + security_scan["score"]
            ) / 4
            combined_score = round((review["overall_score"] + dimension_average) / 2, 1)

            verdict = "approve"
            if review["verdict"] != "approve" or security_scan["verdict"] != "approve" or combined_score < 7.0:
                verdict = "revise"

            review_summary = _format_review_summary(review, security_scan)

            logger.info(
                "[ReviewerWorker] Review complete (task=%s, score=%.2f, security=%d, verdict=%s)",
                task_id,
                combined_score / 10.0,
                security_scan["score"],
                verdict,
            )

            return WorkerResult(
                worker_type="reviewer",
                task_id=task_id,
                status="success" if verdict == "approve" else "needs_revision",
                content=review_summary,
                confidence=combined_score / 10.0,
                metadata={
                    "verdict": verdict,
                    "review": review,
                    "security_score": security_scan["score"],
                    "security_findings": security_scan["findings"],
                    "reflection": review["reflection"],
                    "raw_text": raw_text,
                },
            )

        except Exception as exc:
            logger.warning("[ReviewerWorker] Failed: %s", exc)
            fallback_review = _validate_review_payload(
                {
                    "overall_score": 3,
                    "correctness_score": 3,
                    "maintainability_score": 3,
                    "performance_score": 3,
                    "issues": [f"Reviewer failed: {exc}"],
                    "suggestions": ["Regenerate the code with simpler control flow and explicit validation."],
                    "reflection": (
                        "The previous review step failed. Produce a simpler, safer implementation "
                        "with explicit validation and error handling."
                    ),
                    "verdict": "revise",
                }
            )
            review_summary = _format_review_summary(fallback_review, security_scan)
            return WorkerResult(
                worker_type="reviewer",
                task_id=task_id,
                status="needs_revision",
                content=review_summary,
                confidence=0.3,
                metadata={
                    "verdict": "revise",
                    "review": fallback_review,
                    "security_score": security_scan["score"],
                    "security_findings": security_scan["findings"],
                    "reflection": fallback_review["reflection"],
                    "review_error": str(exc),
                },
            )
