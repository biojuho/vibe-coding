"""PipelineStatusTracker + 유틸리티 함수 테스트."""

from __future__ import annotations

import time

import pytest

from shorts_maker_v2.utils.pipeline_status import (
    _STATUS_COLORS,
    _STATUS_ICONS,
    PipelineStatusTracker,
    StepStatus,
    format_status_line,
    get_status_color,
    get_status_icon,
)

# ── StepStatus enum ──────────────────────────────────────────────


class TestStepStatus:
    def test_all_values(self):
        assert set(StepStatus) == {
            StepStatus.THINKING,
            StepStatus.EXECUTING,
            StepStatus.COMPLETED,
            StepStatus.ERROR,
            StepStatus.RETRY,
            StepStatus.SKIPPED,
        }

    def test_str_values(self):
        assert StepStatus.THINKING.value == "thinking"
        assert StepStatus.ERROR.value == "error"

    def test_is_str_subclass(self):
        assert isinstance(StepStatus.COMPLETED, str)
        assert StepStatus.COMPLETED == "completed"


# ── get_status_color ─────────────────────────────────────────────


class TestGetStatusColor:
    @pytest.mark.parametrize("status", list(StepStatus))
    def test_hex_format(self, status: StepStatus):
        color = get_status_color(status, "hex")
        assert color.startswith("#")
        assert len(color) == 7

    @pytest.mark.parametrize("status", list(StepStatus))
    def test_ansi_format(self, status: StepStatus):
        color = get_status_color(status, "ansi")
        assert color.startswith("\033[")

    def test_unknown_format_returns_empty(self):
        result = get_status_color(StepStatus.THINKING, "rgb")
        assert result == ""

    def test_all_statuses_have_colors(self):
        for status in StepStatus:
            assert status in _STATUS_COLORS


# ── get_status_icon ──────────────────────────────────────────────


class TestGetStatusIcon:
    @pytest.mark.parametrize("status", list(StepStatus))
    def test_known_icons(self, status: StepStatus):
        icon = get_status_icon(status)
        assert icon != "❓"
        assert len(icon) >= 1

    def test_all_statuses_have_icons(self):
        for status in StepStatus:
            assert status in _STATUS_ICONS


# ── format_status_line ───────────────────────────────────────────


class TestFormatStatusLine:
    def test_basic_format(self):
        line = format_status_line("script", StepStatus.THINKING, use_color=False)
        assert "[script]" in line
        assert "thinking" in line

    def test_with_detail(self):
        line = format_status_line("render", StepStatus.EXECUTING, detail="encoding", use_color=False)
        assert "— encoding" in line

    def test_with_elapsed(self):
        line = format_status_line("media", StepStatus.COMPLETED, elapsed_sec=3.14, use_color=False)
        assert "(3.1s)" in line

    def test_with_color(self):
        line = format_status_line("test", StepStatus.ERROR, use_color=True)
        assert "\033[" in line  # ANSI escape present

    def test_without_color(self):
        line = format_status_line("test", StepStatus.ERROR, use_color=False)
        assert "\033[" not in line

    def test_icon_present(self):
        line = format_status_line("script", StepStatus.COMPLETED, use_color=False)
        assert "✅" in line

    def test_all_parts_combined(self):
        line = format_status_line(
            "render",
            StepStatus.RETRY,
            detail="attempt 2",
            elapsed_sec=5.0,
            use_color=False,
        )
        assert "[render]" in line
        assert "retry" in line
        assert "— attempt 2" in line
        assert "(5.0s)" in line


# ── PipelineStatusTracker ────────────────────────────────────────


class TestPipelineStatusTracker:
    def test_init(self):
        tracker = PipelineStatusTracker(job_id="test-123")
        assert tracker.job_id == "test-123"
        assert tracker.quiet is False

    def test_init_quiet(self):
        tracker = PipelineStatusTracker(job_id="q", quiet=True)
        assert tracker.quiet is True

    def test_update_records_step(self):
        tracker = PipelineStatusTracker(job_id="t1", quiet=True)
        tracker.update("script", StepStatus.THINKING, detail="gemini")
        summary = tracker.summary()
        assert "script" in summary
        assert summary["script"]["status"] == "thinking"
        assert summary["script"]["detail"] == "gemini"

    def test_start_sets_thinking(self):
        tracker = PipelineStatusTracker(job_id="t2", quiet=True)
        tracker.start("media", detail="downloading")
        summary = tracker.summary()
        assert summary["media"]["status"] == "thinking"

    def test_complete_convenience(self):
        tracker = PipelineStatusTracker(job_id="t3", quiet=True)
        tracker.start("render")
        tracker.complete("render", detail="done")
        assert tracker.summary()["render"]["status"] == "completed"

    def test_fail_convenience(self):
        tracker = PipelineStatusTracker(job_id="t4", quiet=True)
        tracker.start("script")
        tracker.fail("script", detail="timeout")
        assert tracker.summary()["script"]["status"] == "error"
        assert tracker.summary()["script"]["detail"] == "timeout"

    def test_retry_convenience(self):
        tracker = PipelineStatusTracker(job_id="t5", quiet=True)
        tracker.retry("media", detail="attempt 2")
        assert tracker.summary()["media"]["status"] == "retry"

    def test_auto_elapsed_on_complete(self):
        tracker = PipelineStatusTracker(job_id="t6", quiet=True)
        tracker.start("render")
        time.sleep(0.05)
        tracker.complete("render")
        elapsed = tracker.summary()["render"]["elapsed_sec"]
        assert elapsed is not None
        assert elapsed >= 0.04

    def test_auto_elapsed_on_error(self):
        tracker = PipelineStatusTracker(job_id="t7", quiet=True)
        tracker.start("script")
        time.sleep(0.05)
        tracker.fail("script")
        elapsed = tracker.summary()["script"]["elapsed_sec"]
        assert elapsed is not None
        assert elapsed >= 0.04

    def test_auto_elapsed_on_skipped(self):
        tracker = PipelineStatusTracker(job_id="t8", quiet=True)
        tracker.start("research")
        tracker.update("research", StepStatus.SKIPPED)
        elapsed = tracker.summary()["research"]["elapsed_sec"]
        assert elapsed is not None

    def test_no_auto_elapsed_for_thinking(self):
        tracker = PipelineStatusTracker(job_id="t9", quiet=True)
        tracker.start("script")
        tracker.update("script", StepStatus.THINKING, detail="switch model")
        assert tracker.summary()["script"]["elapsed_sec"] is None

    def test_manual_elapsed_overrides(self):
        tracker = PipelineStatusTracker(job_id="t10", quiet=True)
        tracker.start("render")
        tracker.update("render", StepStatus.COMPLETED, elapsed_sec=99.9)
        assert tracker.summary()["render"]["elapsed_sec"] == 99.9

    def test_multiple_steps_tracking(self):
        tracker = PipelineStatusTracker(job_id="multi", quiet=True)
        tracker.start("script")
        tracker.complete("script")
        tracker.start("media")
        tracker.complete("media")
        tracker.start("render")
        tracker.fail("render")

        summary = tracker.summary()
        assert len(summary) == 3
        assert summary["script"]["status"] == "completed"
        assert summary["media"]["status"] == "completed"
        assert summary["render"]["status"] == "error"

    def test_status_color_in_record(self):
        tracker = PipelineStatusTracker(job_id="c1", quiet=True)
        tracker.update("x", StepStatus.ERROR)
        assert tracker.summary()["x"]["status_color"] == "#EF4444"

    def test_timestamp_recorded(self):
        tracker = PipelineStatusTracker(job_id="ts", quiet=True)
        before = time.time()
        tracker.update("step", StepStatus.THINKING)
        after = time.time()
        ts = tracker.summary()["step"]["timestamp"]
        assert before <= ts <= after


# ── to_log_record ────────────────────────────────────────────────


class TestToLogRecord:
    def test_structure(self):
        tracker = PipelineStatusTracker(job_id="log-1", quiet=True)
        tracker.update("a", StepStatus.COMPLETED)
        tracker.update("b", StepStatus.ERROR)
        tracker.update("c", StepStatus.SKIPPED)

        record = tracker.to_log_record()
        assert record["job_id"] == "log-1"
        assert record["total_steps"] == 3
        assert record["completed"] == 1
        assert record["failed"] == 1
        assert "steps" in record

    def test_empty_tracker(self):
        tracker = PipelineStatusTracker(job_id="empty", quiet=True)
        record = tracker.to_log_record()
        assert record["total_steps"] == 0
        assert record["completed"] == 0
        assert record["failed"] == 0

    def test_all_completed(self):
        tracker = PipelineStatusTracker(job_id="all-ok", quiet=True)
        for name in ("script", "media", "render"):
            tracker.update(name, StepStatus.COMPLETED)
        record = tracker.to_log_record()
        assert record["completed"] == 3
        assert record["failed"] == 0

    def test_all_failed(self):
        tracker = PipelineStatusTracker(job_id="all-fail", quiet=True)
        for name in ("script", "media"):
            tracker.update(name, StepStatus.ERROR)
        record = tracker.to_log_record()
        assert record["completed"] == 0
        assert record["failed"] == 2


# ── CLI 출력 ─────────────────────────────────────────────────────


class TestCLIOutput:
    def test_quiet_suppresses_print(self, capsys):
        tracker = PipelineStatusTracker(job_id="quiet", quiet=True)
        tracker.update("x", StepStatus.THINKING)
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_non_quiet_prints(self, capsys):
        tracker = PipelineStatusTracker(job_id="loud", quiet=False)
        tracker.update("x", StepStatus.COMPLETED, detail="ok")
        captured = capsys.readouterr()
        assert "[x]" in captured.out
        assert "completed" in captured.out


# ── 상태 전이 시나리오 ───────────────────────────────────────────


class TestStatusTransitions:
    def test_thinking_to_completed(self):
        tracker = PipelineStatusTracker(job_id="tr1", quiet=True)
        tracker.start("step")
        tracker.complete("step")
        assert tracker.summary()["step"]["status"] == "completed"

    def test_thinking_to_retry_to_completed(self):
        tracker = PipelineStatusTracker(job_id="tr2", quiet=True)
        tracker.start("step")
        tracker.retry("step", detail="attempt 2")
        tracker.complete("step")
        assert tracker.summary()["step"]["status"] == "completed"

    def test_thinking_to_error(self):
        tracker = PipelineStatusTracker(job_id="tr3", quiet=True)
        tracker.start("step")
        tracker.fail("step", detail="crash")
        assert tracker.summary()["step"]["status"] == "error"
        assert tracker.summary()["step"]["detail"] == "crash"

    def test_overwrite_preserves_latest(self):
        tracker = PipelineStatusTracker(job_id="tr4", quiet=True)
        tracker.update("step", StepStatus.THINKING, detail="v1")
        tracker.update("step", StepStatus.EXECUTING, detail="v2")
        tracker.update("step", StepStatus.COMPLETED, detail="v3")
        assert tracker.summary()["step"]["status"] == "completed"
        assert tracker.summary()["step"]["detail"] == "v3"
