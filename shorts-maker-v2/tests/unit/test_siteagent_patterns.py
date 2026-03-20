"""Tests for SiteAgent-inspired patterns (#1-#5).

Verifies:
  #1 — Error type classification (9 types)
  #2 — Pipeline status display system
  #3 — MARL self-verification (research consistency)
  #4 — Pydantic schema validation
  #5 — Smart retry strategy (agent loop)
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

# ── Pattern #1: Error Type Classification ─────────────────────────────────
from shorts_maker_v2.pipeline.error_types import (
    PipelineError,
    PipelineErrorType,
    classify_error,
)


class TestErrorClassification:
    """패턴 #1: 에러 타입 세분화."""

    @pytest.mark.parametrize(
        "error_msg, expected_type",
        [
            ("Request timed out after 120s", PipelineErrorType.NETWORK_ERROR),
            ("Connection refused", PipelineErrorType.NETWORK_ERROR),
            ("429 Too Many Requests", PipelineErrorType.RATE_LIMIT),
            ("Rate limit exceeded", PipelineErrorType.RATE_LIMIT),
            ("Invalid API key provided", PipelineErrorType.AUTH_ERROR),
            ("Insufficient_quota", PipelineErrorType.AUTH_ERROR),
            ("500 Internal Server Error", PipelineErrorType.SERVER_ERROR),
            ("Service unavailable", PipelineErrorType.SERVER_ERROR),
            ("JSON parse error: Expecting value", PipelineErrorType.INVALID_RESPONSE),
            ("Content policy violation", PipelineErrorType.CONTENT_FILTER),
            ("Your request was rejected due to safety", PipelineErrorType.CONTENT_FILTER),
            ("Maximum context length exceeded", PipelineErrorType.CONTEXT_LENGTH),
            ("No such file or directory", PipelineErrorType.RESOURCE_ERROR),
            ("Completely unknown error", PipelineErrorType.UNKNOWN),
        ],
    )
    def test_classify_error(self, error_msg: str, expected_type: PipelineErrorType):
        exc = Exception(error_msg)
        result = classify_error(exc)
        assert result == expected_type, f"Expected {expected_type}, got {result} for '{error_msg}'"

    def test_retryable_types(self):
        assert PipelineErrorType.NETWORK_ERROR.is_retryable
        assert PipelineErrorType.RATE_LIMIT.is_retryable
        assert PipelineErrorType.SERVER_ERROR.is_retryable
        assert PipelineErrorType.INVALID_RESPONSE.is_retryable
        assert not PipelineErrorType.AUTH_ERROR.is_retryable
        assert not PipelineErrorType.CONTENT_FILTER.is_retryable
        assert not PipelineErrorType.CONTEXT_LENGTH.is_retryable

    def test_wait_times(self):
        assert PipelineErrorType.RATE_LIMIT.suggested_wait_sec > PipelineErrorType.NETWORK_ERROR.suggested_wait_sec
        assert PipelineErrorType.AUTH_ERROR.suggested_wait_sec == 0.0

    def test_pipeline_error_from_exception(self):
        original = TimeoutError("Request timed out")
        pe = PipelineError.from_exception(original, step="media", provider="openai")
        assert pe.error_type == PipelineErrorType.NETWORK_ERROR
        assert pe.step == "media"
        assert pe.provider == "openai"
        d = pe.to_dict()
        assert d["error_type"] == "network_error"
        assert d["is_retryable"] is True

    def test_icons_exist(self):
        for t in PipelineErrorType:
            assert t.icon, f"Missing icon for {t}"


# ── Pattern #2: Pipeline Status Display ───────────────────────────────────

from shorts_maker_v2.utils.pipeline_status import (
    PipelineStatusTracker,
    StepStatus,
    format_status_line,
    get_status_color,
    get_status_icon,
)


class TestPipelineStatus:
    """패턴 #2: 상태 표시 시스템."""

    def test_status_colors_hex(self):
        assert get_status_color(StepStatus.THINKING, "hex") == "#39B6FF"
        assert get_status_color(StepStatus.COMPLETED, "hex") == "#22C55E"
        assert get_status_color(StepStatus.ERROR, "hex") == "#EF4444"

    def test_status_icons(self):
        assert get_status_icon(StepStatus.THINKING) == "🧠"
        assert get_status_icon(StepStatus.COMPLETED) == "✅"
        assert get_status_icon(StepStatus.ERROR) == "❌"
        assert get_status_icon(StepStatus.RETRY) == "🔄"

    def test_format_status_line_plain(self):
        line = format_status_line("script", StepStatus.THINKING, detail="gemini", use_color=False)
        assert "[script]" in line
        assert "gemini" in line
        assert "thinking" in line

    def test_format_with_elapsed(self):
        line = format_status_line("render", StepStatus.COMPLETED, elapsed_sec=12.5, use_color=False)
        assert "12.5s" in line

    def test_tracker_lifecycle(self):
        tracker = PipelineStatusTracker(job_id="test-123", quiet=True)
        tracker.start("research", "gathering facts")
        tracker.complete("research", "5 facts found")
        tracker.start("script")
        tracker.fail("script", "rate limit")

        summary = tracker.summary()
        assert "research" in summary
        assert summary["research"]["status"] == "completed"
        assert summary["script"]["status"] == "error"

    def test_tracker_log_record(self):
        tracker = PipelineStatusTracker(job_id="test-456", quiet=True)
        tracker.update("step1", StepStatus.COMPLETED)
        tracker.update("step2", StepStatus.ERROR)
        rec = tracker.to_log_record()
        assert rec["completed"] == 1
        assert rec["failed"] == 1
        assert rec["total_steps"] == 2


# ── Pattern #4: Pydantic Schema Validation ────────────────────────────────

try:
    from shorts_maker_v2.pipeline.script_step import _HAS_PYDANTIC, ScriptStep

    if _HAS_PYDANTIC:
        from shorts_maker_v2.pipeline.script_step import SceneOutput, ScriptOutput
except ImportError:
    _HAS_PYDANTIC = False


class TestScriptSchemaValidation:
    """패턴 #4: Pydantic 스키마 출력 검증."""

    @pytest.mark.skipif(not _HAS_PYDANTIC, reason="pydantic not installed")
    def test_valid_payload(self):
        payload = {
            "title": "테스트 영상",
            "scenes": [
                {
                    "narration_ko": "안녕하세요 여러분, 오늘은 특별한 이야기를 해보겠습니다.",
                    "visual_prompt_en": "A wide shot of a sunset over the ocean with warm golden light",
                    "estimated_seconds": 5.0,
                    "structure_role": "hook",
                },
                {
                    "narration_ko": "이것은 많은 사람들이 모르고 있는 사실인데요.",
                    "visual_prompt_en": "Close-up of a person reading a book in a cozy library",
                    "estimated_seconds": 7.0,
                    "structure_role": "body",
                },
            ],
            "no_reliable_source": False,
        }
        errors = ScriptStep._validate_script_schema(payload)
        assert errors == []

    @pytest.mark.skipif(not _HAS_PYDANTIC, reason="pydantic not installed")
    def test_invalid_payload_missing_fields(self):
        payload = {
            "title": "",  # min_length=1 violation
            "scenes": [],  # min_length=1 violation
        }
        errors = ScriptStep._validate_script_schema(payload)
        assert len(errors) > 0

    @pytest.mark.skipif(not _HAS_PYDANTIC, reason="pydantic not installed")
    def test_invalid_scene_structure_role(self):
        payload = {
            "title": "Valid Title",
            "scenes": [
                {
                    "narration_ko": "충분히 긴 나레이션 텍스트입니다",
                    "visual_prompt_en": "A detailed visual prompt in English",
                    "structure_role": "invalid_role",  # invalid
                },
            ],
        }
        errors = ScriptStep._validate_script_schema(payload)
        assert len(errors) > 0

    def test_graceful_without_pydantic(self):
        """Pydantic 없어도 빈 리스트 반환 (graceful degradation)."""
        with patch("shorts_maker_v2.pipeline.script_step._HAS_PYDANTIC", False):
            errors = ScriptStep._validate_script_schema({"title": "", "scenes": []})
            assert errors == []


# ── Pattern #5: Smart Retry Strategy ──────────────────────────────────────

from shorts_maker_v2.pipeline.orchestrator import PipelineOrchestrator


class TestSmartRetryStrategy:
    """패턴 #5: 에이전트 루프 스마트 재시도."""

    def test_retryable_network_error(self):
        error = Exception("Connection timed out")
        strategy = PipelineOrchestrator._smart_retry_strategy(error, "media", attempt=1)
        assert strategy["action"] == "retry"
        assert strategy["error_type"] == PipelineErrorType.NETWORK_ERROR
        assert strategy["wait_sec"] > 0

    def test_non_retryable_auth_error(self):
        error = Exception("Invalid API key")
        strategy = PipelineOrchestrator._smart_retry_strategy(error, "script", attempt=1)
        assert strategy["action"] == "abort"
        assert strategy["error_type"] == PipelineErrorType.AUTH_ERROR

    def test_max_attempts_fallback_for_research(self):
        error = Exception("Server Error 500")
        strategy = PipelineOrchestrator._smart_retry_strategy(error, "research", attempt=3, max_attempts=3)
        assert strategy["action"] == "fallback"  # research는 fallback 허용

    def test_max_attempts_abort_for_script(self):
        error = Exception("Server Error 500")
        strategy = PipelineOrchestrator._smart_retry_strategy(error, "script", attempt=3, max_attempts=3)
        assert strategy["action"] == "abort"  # script는 abort

    def test_rate_limit_progressive_backoff(self):
        error = Exception("Rate limit exceeded")
        s1 = PipelineOrchestrator._smart_retry_strategy(error, "media", attempt=1)
        s2 = PipelineOrchestrator._smart_retry_strategy(error, "media", attempt=2)
        assert s2["wait_sec"] > s1["wait_sec"]

    def test_unknown_error_not_retryable(self):
        error = Exception("Something completely unknown happened")
        strategy = PipelineOrchestrator._smart_retry_strategy(error, "render", attempt=1)
        assert strategy["action"] == "abort"
        assert strategy["error_type"] == PipelineErrorType.UNKNOWN
