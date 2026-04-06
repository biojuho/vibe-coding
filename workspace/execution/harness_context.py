"""Context Management Middleware — auto-compaction and tool-output offloading.

Part of Harness Engineering AI Phase 2-3 (ADR-025).

Two problems this module solves:

1. **Context bloat**: Long agent sessions accumulate messages that
   eventually fill the context window, causing degraded output quality.
   ``ContextWindow`` auto-compacts older messages when a configurable
   threshold is reached.

2. **Large tool outputs**: A single tool call can return megabytes of
   data.  ``ContextWindow.add_tool_result()`` detects oversized outputs
   and offloads them to ``.tmp/`` files, keeping only a summary + path
   reference in the context.

Usage::

    from execution.harness_context import ContextWindow

    ctx = ContextWindow(max_tokens_estimate=100_000, compact_at_pct=80)

    ctx.add_message("system", "You are a helpful assistant.")
    ctx.add_message("user", "Analyze this codebase.")
    ctx.add_message("assistant", "I'll start by reading the main files...")
    ctx.add_tool_result("file_read", large_content, path="/some/file.py")

    # When context is getting full:
    if ctx.should_compact():
        ctx.compact(session)  # Uses HarnessSession to summarize
"""

from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Rough estimate: 1 token ~ 4 characters for English, ~2 for Korean
_CHARS_PER_TOKEN = 3  # Conservative average


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class Message:
    """A single message in the context window."""

    role: str  # "system", "user", "assistant", "tool"
    content: str
    timestamp: float
    token_estimate: int
    metadata: dict[str, Any]

    @classmethod
    def create(cls, role: str, content: str, **meta: Any) -> "Message":
        return cls(
            role=role,
            content=content,
            timestamp=time.time(),
            token_estimate=max(1, len(content) // _CHARS_PER_TOKEN),
            metadata=meta,
        )


# ---------------------------------------------------------------------------
# Context Window
# ---------------------------------------------------------------------------


class ContextWindow:
    """Managed context window with auto-compaction and offloading.

    Parameters
    ----------
    max_tokens_estimate:
        Approximate token budget for the context window.
    compact_at_pct:
        Trigger compaction when usage exceeds this percentage.
    offload_threshold_chars:
        Tool outputs larger than this are saved to disk.
    offload_dir:
        Directory for offloaded tool outputs.
    keep_recent:
        Number of recent messages to preserve during compaction
        (never summarized away).
    """

    def __init__(
        self,
        max_tokens_estimate: int = 100_000,
        compact_at_pct: int = 80,
        offload_threshold_chars: int = 5_000,
        offload_dir: str | Path | None = None,
        keep_recent: int = 6,
    ) -> None:
        self.max_tokens = max_tokens_estimate
        self.compact_at_pct = compact_at_pct
        self.offload_threshold = offload_threshold_chars
        self.offload_dir = (
            Path(offload_dir) if offload_dir else (Path(__file__).resolve().parents[1] / ".tmp" / "context_offload")
        )
        self.keep_recent = keep_recent
        self._messages: list[Message] = []
        self._compaction_count: int = 0

    # -- Properties --------------------------------------------------------

    @property
    def messages(self) -> list[Message]:
        return list(self._messages)

    @property
    def total_tokens(self) -> int:
        return sum(m.token_estimate for m in self._messages)

    @property
    def usage_pct(self) -> float:
        if self.max_tokens <= 0:
            return 0.0
        return (self.total_tokens / self.max_tokens) * 100

    @property
    def message_count(self) -> int:
        return len(self._messages)

    # -- Adding messages ---------------------------------------------------

    def add_message(self, role: str, content: str, **meta: Any) -> Message:
        """Add a message to the context window."""
        msg = Message.create(role, content, **meta)
        self._messages.append(msg)
        return msg

    def add_tool_result(
        self,
        tool_name: str,
        content: str,
        *,
        path: str = "",
    ) -> Message:
        """Add a tool result, offloading to disk if oversized.

        When the content exceeds ``offload_threshold_chars``, the full
        content is written to ``offload_dir`` and replaced with a
        summary + file path reference in the context.
        """
        if len(content) <= self.offload_threshold:
            return self.add_message(
                "tool",
                content,
                tool_name=tool_name,
                path=path,
            )

        # Offload to disk
        self.offload_dir.mkdir(parents=True, exist_ok=True)
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:12]
        filename = f"{tool_name}_{content_hash}.txt"
        offload_path = self.offload_dir / filename
        offload_path.write_text(content, encoding="utf-8")

        # Keep a summary in context
        preview = content[:500]
        line_count = content.count("\n") + 1
        char_count = len(content)
        summary = (
            f"[Tool output offloaded: {tool_name}]\n"
            f"Path: {path or 'N/A'}\n"
            f"Size: {char_count:,} chars, ~{line_count:,} lines\n"
            f"Offloaded to: {offload_path}\n"
            f"Preview (first 500 chars):\n{preview}"
        )

        logger.info(
            "Offloaded %s output (%d chars) to %s",
            tool_name,
            char_count,
            offload_path,
        )

        return self.add_message(
            "tool",
            summary,
            tool_name=tool_name,
            path=path,
            offloaded=True,
            offload_path=str(offload_path),
            original_chars=char_count,
        )

    # -- Compaction --------------------------------------------------------

    def should_compact(self) -> bool:
        """Check if context usage exceeds the compaction threshold."""
        return self.usage_pct >= self.compact_at_pct

    def compact(self, session: Any = None) -> dict[str, Any]:
        """Compact older messages into a summary.

        Preserves the system message (first message if role=system) and
        the most recent ``keep_recent`` messages.  Everything in between
        is summarized by the LLM.

        Parameters
        ----------
        session:
            A ``HarnessSession`` (or anything with ``generate_text``).
            If *None*, uses a simple truncation strategy instead of
            LLM-powered summarization.

        Returns
        -------
        dict with compaction stats: messages_before, messages_after,
        tokens_before, tokens_after, strategy.
        """
        tokens_before = self.total_tokens
        messages_before = len(self._messages)

        if messages_before <= self.keep_recent + 1:
            return {
                "compacted": False,
                "reason": "Not enough messages to compact",
                "messages": messages_before,
            }

        # Split: system | middle (to summarize) | recent (to keep)
        system_msgs = []
        rest = list(self._messages)
        if rest and rest[0].role == "system":
            system_msgs = [rest[0]]
            rest = rest[1:]

        if len(rest) <= self.keep_recent:
            return {
                "compacted": False,
                "reason": "Not enough non-system messages to compact",
                "messages": messages_before,
            }

        to_summarize = rest[: -self.keep_recent]
        to_keep = rest[-self.keep_recent :]

        # Build conversation text for summarization
        conversation_text = "\n".join(f"[{m.role}] {m.content[:500]}" for m in to_summarize)

        if session is not None:
            try:
                summary_text = session.generate_text(
                    system_prompt=(
                        "Summarize the following conversation excerpt concisely. "
                        "Preserve key decisions, facts, file paths, and action items. "
                        "Output only the summary, no preamble."
                    ),
                    user_prompt=conversation_text,
                    temperature=0.3,
                )
                strategy = "llm_summary"
            except Exception as e:
                logger.warning("LLM compaction failed: %s — falling back to truncation", e)
                summary_text = self._truncation_summary(to_summarize)
                strategy = "truncation_fallback"
        else:
            summary_text = self._truncation_summary(to_summarize)
            strategy = "truncation"

        # Rebuild context
        summary_msg = Message.create(
            "system",
            f"[Context compacted — round {self._compaction_count + 1}]\n"
            f"Summary of {len(to_summarize)} earlier messages:\n{summary_text}",
            compaction_round=self._compaction_count + 1,
            messages_summarized=len(to_summarize),
        )

        self._messages = system_msgs + [summary_msg] + to_keep
        self._compaction_count += 1

        result = {
            "compacted": True,
            "strategy": strategy,
            "messages_before": messages_before,
            "messages_after": len(self._messages),
            "tokens_before": tokens_before,
            "tokens_after": self.total_tokens,
            "messages_summarized": len(to_summarize),
            "compaction_round": self._compaction_count,
        }

        logger.info(
            "Context compacted: %d→%d messages, ~%d→%d tokens (%s)",
            messages_before,
            len(self._messages),
            tokens_before,
            self.total_tokens,
            strategy,
        )
        return result

    @staticmethod
    def _truncation_summary(messages: list[Message]) -> str:
        """Deterministic summary without LLM — keeps key facts."""
        lines = []
        for m in messages:
            preview = m.content[:200].replace("\n", " ")
            lines.append(f"- [{m.role}] {preview}")
        return "\n".join(lines[-20:])  # Keep last 20 items max

    # -- Serialization (for session resume) --------------------------------

    def to_messages_list(self) -> list[dict[str, str]]:
        """Export as OpenAI-style messages list."""
        return [{"role": m.role, "content": m.content} for m in self._messages]

    def stats(self) -> dict[str, Any]:
        """Return context window statistics."""
        return {
            "message_count": len(self._messages),
            "total_tokens_estimate": self.total_tokens,
            "max_tokens": self.max_tokens,
            "usage_pct": round(self.usage_pct, 1),
            "compaction_count": self._compaction_count,
            "should_compact": self.should_compact(),
        }
