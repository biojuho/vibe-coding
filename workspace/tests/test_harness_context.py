"""execution/harness_context.py 테스트.

ContextWindow의 메시지 관리, 오프로딩, 압축 로직을 검증.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from execution.harness_context import ContextWindow, Message


# ── Message ──────────────────────────────────────────────────────


class TestMessage:
    def test_create_estimates_tokens(self):
        m = Message.create("user", "Hello world")
        assert m.role == "user"
        assert m.token_estimate > 0
        assert m.timestamp > 0

    def test_long_content_higher_tokens(self):
        short = Message.create("user", "Hi")
        long = Message.create("user", "x" * 3000)
        assert long.token_estimate > short.token_estimate


# ── ContextWindow basics ─────────────────────────────────────────


class TestContextWindowBasics:
    def test_add_message(self):
        ctx = ContextWindow(max_tokens_estimate=10000)
        ctx.add_message("system", "You are helpful.")
        ctx.add_message("user", "What is 2+2?")
        assert ctx.message_count == 2

    def test_total_tokens(self):
        ctx = ContextWindow()
        ctx.add_message("user", "a" * 300)  # ~100 tokens
        assert ctx.total_tokens > 0

    def test_usage_pct(self):
        ctx = ContextWindow(max_tokens_estimate=100)
        ctx.add_message("user", "a" * 300)  # ~100 tokens = 100%
        assert ctx.usage_pct > 50

    def test_to_messages_list(self):
        ctx = ContextWindow()
        ctx.add_message("system", "Sys prompt")
        ctx.add_message("user", "Hello")
        msgs = ctx.to_messages_list()
        assert len(msgs) == 2
        assert msgs[0] == {"role": "system", "content": "Sys prompt"}
        assert msgs[1] == {"role": "user", "content": "Hello"}

    def test_stats(self):
        ctx = ContextWindow(max_tokens_estimate=10000)
        ctx.add_message("user", "Test")
        s = ctx.stats()
        assert s["message_count"] == 1
        assert s["compaction_count"] == 0
        assert "usage_pct" in s


# ── Tool output offloading ───────────────────────────────────────


class TestToolOffloading:
    def test_small_output_stays_in_context(self):
        ctx = ContextWindow(offload_threshold_chars=1000)
        msg = ctx.add_tool_result("file_read", "short content", path="/f.py")
        assert msg.content == "short content"
        assert msg.metadata.get("offloaded") is None

    def test_large_output_offloaded(self, tmp_path):
        ctx = ContextWindow(
            offload_threshold_chars=100,
            offload_dir=tmp_path / "offload",
        )
        big_content = "x" * 5000
        msg = ctx.add_tool_result("file_read", big_content, path="/big.py")

        # Message should contain summary, not full content
        assert "[Tool output offloaded" in msg.content
        assert "5,000 chars" in msg.content
        assert msg.metadata.get("offloaded") is True

        # File should exist on disk
        offload_path = Path(msg.metadata["offload_path"])
        assert offload_path.exists()
        assert offload_path.read_text(encoding="utf-8") == big_content

    def test_offload_dir_created(self, tmp_path):
        offload_dir = tmp_path / "new_dir" / "offload"
        ctx = ContextWindow(
            offload_threshold_chars=10,
            offload_dir=offload_dir,
        )
        ctx.add_tool_result("grep", "a" * 100)
        assert offload_dir.exists()


# ── Compaction ───────────────────────────────────────────────────


class TestCompactionTruncation:
    """Compaction without LLM (truncation strategy)."""

    def test_should_compact_threshold(self):
        ctx = ContextWindow(max_tokens_estimate=100, compact_at_pct=80)
        # Each char ~0.33 tokens, need ~80 tokens → ~240 chars
        ctx.add_message("user", "a" * 300)
        assert ctx.should_compact() is True

    def test_not_enough_messages(self):
        ctx = ContextWindow(max_tokens_estimate=10, compact_at_pct=1)
        ctx.add_message("system", "sys")
        ctx.add_message("user", "u")
        result = ctx.compact()
        assert result["compacted"] is False

    def test_truncation_compaction(self):
        ctx = ContextWindow(max_tokens_estimate=1000, keep_recent=2)

        ctx.add_message("system", "System prompt")
        for i in range(10):
            ctx.add_message("user", f"Message {i}: " + "x" * 100)

        before = ctx.message_count
        result = ctx.compact()  # No session → truncation

        assert result["compacted"] is True
        assert result["strategy"] == "truncation"
        assert ctx.message_count < before
        # Should have: system + summary + 2 recent = 4
        assert ctx.message_count == 4
        assert result["compaction_round"] == 1

    def test_system_message_preserved(self):
        ctx = ContextWindow(keep_recent=2)
        ctx.add_message("system", "IMPORTANT SYSTEM PROMPT")
        for i in range(10):
            ctx.add_message("user", f"msg {i}" + "x" * 50)

        ctx.compact()
        assert ctx.messages[0].role == "system"
        assert ctx.messages[0].content == "IMPORTANT SYSTEM PROMPT"

    def test_recent_messages_preserved(self):
        ctx = ContextWindow(keep_recent=3)
        ctx.add_message("system", "sys")
        for i in range(10):
            ctx.add_message("user", f"msg_{i}")

        ctx.compact()
        # Last 3 non-system messages should be preserved
        content_list = [m.content for m in ctx.messages]
        assert "msg_9" in content_list
        assert "msg_8" in content_list
        assert "msg_7" in content_list

    def test_double_compaction_increments_round(self):
        ctx = ContextWindow(keep_recent=2)
        ctx.add_message("system", "sys")
        for i in range(10):
            ctx.add_message("user", f"batch1_{i}" + "x" * 50)
        ctx.compact()

        for i in range(10):
            ctx.add_message("user", f"batch2_{i}" + "x" * 50)
        result = ctx.compact()

        assert result["compaction_round"] == 2


class TestCompactionWithLLM:
    """Compaction using mocked LLM session."""

    def test_llm_summary_strategy(self):
        mock_session = MagicMock()
        mock_session.generate_text.return_value = "Summary: discussed file paths and API design."

        ctx = ContextWindow(keep_recent=2)
        ctx.add_message("system", "sys")
        for i in range(8):
            ctx.add_message("user", f"msg {i}")

        result = ctx.compact(session=mock_session)

        assert result["compacted"] is True
        assert result["strategy"] == "llm_summary"
        mock_session.generate_text.assert_called_once()

        # Summary message should contain the LLM output
        summary_msg = ctx.messages[1]  # After system msg
        assert "Summary: discussed file paths" in summary_msg.content

    def test_llm_failure_falls_back(self):
        mock_session = MagicMock()
        mock_session.generate_text.side_effect = RuntimeError("LLM down")

        ctx = ContextWindow(keep_recent=2)
        ctx.add_message("system", "sys")
        for i in range(8):
            ctx.add_message("user", f"msg {i}")

        result = ctx.compact(session=mock_session)

        assert result["compacted"] is True
        assert result["strategy"] == "truncation_fallback"


# ── YAML factory integration ─────────────────────────────────────


class TestHarnessSessionFromYaml:
    """Test HarnessSession.from_yaml() factory."""

    def test_loads_known_agent(self):
        from execution.harness_middleware import HarnessSession

        yaml_path = Path(__file__).resolve().parents[1] / "directives" / "agent_permissions.yaml"
        if not yaml_path.exists():
            pytest.skip("agent_permissions.yaml not found")

        session = HarnessSession.from_yaml(
            "blind-to-x-pipeline",
            yaml_path=str(yaml_path),
        )
        assert session.agent_id == "blind-to-x-pipeline"
        assert session.budget.max_tokens == 500_000
        assert session.budget.max_cost_usd == 2.0
        assert session.budget.max_calls == 100

    def test_unknown_agent_gets_default(self):
        from execution.harness_middleware import HarnessSession

        yaml_path = Path(__file__).resolve().parents[1] / "directives" / "agent_permissions.yaml"
        if not yaml_path.exists():
            pytest.skip("agent_permissions.yaml not found")

        session = HarnessSession.from_yaml(
            "nonexistent-agent",
            yaml_path=str(yaml_path),
        )
        assert session.agent_id == "nonexistent-agent"
        assert session.budget.max_tokens == 100_000  # default profile
        assert session.budget.max_cost_usd == 0.5
