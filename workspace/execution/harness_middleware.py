"""Harness Middleware Stack — observability, loop detection, and budget enforcement.

Part of Harness Engineering AI Phase 1 (ADR-025).

Three middleware layers wrap every LLM call through ``HarnessSession``:

1. **Observability**: request-ID correlation, latency timing, structured event log.
2. **Loop detection**: sliding-window pattern detector for repetitive calls.
3. **Budget enforcement**: per-session token/cost limits with early-stop.

The middleware composes *around* the existing ``LLMClient`` via
``HarnessSession`` — no changes to ``LLMClient`` internals required.

Usage::

    from execution.harness_middleware import HarnessSession

    session = HarnessSession(
        agent_id="blind-to-x-pipeline",
        max_tokens=500_000,
        max_cost_usd=2.0,
    )

    # Use generate_* just like LLMClient
    result = session.generate_json(system_prompt="...", user_prompt="...")

    # Inspect session state
    print(session.summary())
"""

from __future__ import annotations

import hashlib
import logging
import time
import uuid
from collections import deque
from dataclasses import dataclass
from typing import Any, Callable

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class CallRecord:
    """Immutable record of a single LLM call through the harness."""

    request_id: str
    agent_id: str
    timestamp: float
    system_prompt_hash: str
    user_prompt_hash: str
    json_mode: bool
    temperature: float

    # Filled after call completes
    provider: str = ""
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    success: bool = False
    error: str = ""
    cache_hit: bool = False

    @property
    def prompt_fingerprint(self) -> str:
        """Short fingerprint combining system+user prompt hashes + mode."""
        return f"{self.system_prompt_hash[:8]}:{self.user_prompt_hash[:8]}:{self.json_mode}"


@dataclass
class SessionBudget:
    """Mutable budget tracker for a single session."""

    max_tokens: int = 0  # 0 = unlimited
    max_cost_usd: float = 0.0  # 0.0 = unlimited
    max_calls: int = 0  # 0 = unlimited

    used_tokens: int = 0
    used_cost_usd: float = 0.0
    used_calls: int = 0

    @property
    def tokens_remaining(self) -> int | None:
        if self.max_tokens <= 0:
            return None
        return max(0, self.max_tokens - self.used_tokens)

    @property
    def cost_remaining(self) -> float | None:
        if self.max_cost_usd <= 0.0:
            return None
        return max(0.0, self.max_cost_usd - self.used_cost_usd)

    @property
    def calls_remaining(self) -> int | None:
        if self.max_calls <= 0:
            return None
        return max(0, self.max_calls - self.used_calls)

    def check(self) -> str | None:
        """Return a denial reason, or *None* if budget allows."""
        if self.max_tokens > 0 and self.used_tokens >= self.max_tokens:
            return f"Token budget exhausted ({self.used_tokens:,}/{self.max_tokens:,})"
        if self.max_cost_usd > 0 and self.used_cost_usd >= self.max_cost_usd:
            return f"Cost budget exhausted (${self.used_cost_usd:.4f}/${self.max_cost_usd:.4f})"
        if self.max_calls > 0 and self.used_calls >= self.max_calls:
            return f"Call budget exhausted ({self.used_calls}/{self.max_calls})"
        return None

    def record(self, tokens: int, cost: float) -> None:
        self.used_tokens += tokens
        self.used_cost_usd += cost
        self.used_calls += 1


class BudgetExceededError(RuntimeError):
    """Raised when a session budget is exhausted."""


class LoopDetectedWarning(RuntimeWarning):
    """Issued when repetitive call patterns are detected."""


# ---------------------------------------------------------------------------
# Loop detector
# ---------------------------------------------------------------------------


class LoopDetector:
    """Sliding-window detector for repetitive LLM call patterns.

    Tracks prompt fingerprints over the last *window_size* calls.
    When the same fingerprint appears *threshold* times within the window,
    it signals a likely loop.
    """

    def __init__(self, window_size: int = 10, threshold: int = 3) -> None:
        self.window_size = window_size
        self.threshold = threshold
        self._window: deque[str] = deque(maxlen=window_size)

    def record(self, fingerprint: str) -> str | None:
        """Record a fingerprint and return a warning message if loop detected."""
        self._window.append(fingerprint)
        count = sum(1 for fp in self._window if fp == fingerprint)
        if count >= self.threshold:
            return (
                f"Loop detected: prompt fingerprint '{fingerprint}' appeared "
                f"{count}x in the last {len(self._window)} calls"
            )
        return None

    def reset(self) -> None:
        self._window.clear()


# ---------------------------------------------------------------------------
# Harness Session
# ---------------------------------------------------------------------------


class HarnessSession:
    """Middleware wrapper around ``LLMClient`` providing observability,
    loop detection, and budget enforcement.

    Parameters
    ----------
    agent_id:
        Identifier for the agent using this session.
    max_tokens:
        Maximum total tokens (input + output) allowed per session.
        ``0`` means unlimited.
    max_cost_usd:
        Maximum total cost in USD allowed per session.
        ``0.0`` means unlimited.
    max_calls:
        Maximum number of LLM calls per session.
        ``0`` means unlimited.
    loop_window:
        Number of recent calls to consider for loop detection.
    loop_threshold:
        How many identical-fingerprint calls within the window
        triggers a loop warning.
    on_budget_exceeded:
        Callback ``(reason: str) -> bool``.  Return *True* to override
        the budget limit (e.g. after human approval).  Default: raise.
    on_loop_detected:
        Callback ``(warning: str) -> bool``.  Return *True* to proceed
        despite the loop.  Default: log warning and proceed.
    llm_kwargs:
        Extra keyword arguments forwarded to ``LLMClient.__init__``.
    """

    def __init__(
        self,
        agent_id: str = "default",
        *,
        max_tokens: int = 0,
        max_cost_usd: float = 0.0,
        max_calls: int = 0,
        loop_window: int = 10,
        loop_threshold: int = 3,
        on_budget_exceeded: Callable[[str], bool] | None = None,
        on_loop_detected: Callable[[str], bool] | None = None,
        **llm_kwargs: Any,
    ) -> None:
        self.agent_id = agent_id
        self.session_id = uuid.uuid4().hex[:12]
        self.started_at = time.time()

        self.budget = SessionBudget(
            max_tokens=max_tokens,
            max_cost_usd=max_cost_usd,
            max_calls=max_calls,
        )
        self.loop_detector = LoopDetector(
            window_size=loop_window,
            threshold=loop_threshold,
        )
        self._on_budget_exceeded = on_budget_exceeded
        self._on_loop_detected = on_loop_detected
        self._call_log: list[CallRecord] = []
        self._call_counter: int = 0
        self._llm_kwargs = llm_kwargs
        self._llm_client: Any = None  # Lazy init to avoid import-time side effects

    @property
    def call_log(self) -> list[CallRecord]:
        return list(self._call_log)

    # -- Lazy LLM client ---------------------------------------------------

    def _get_client(self) -> Any:
        if self._llm_client is None:
            from execution.llm_client import LLMClient

            self._llm_client = LLMClient(
                caller_script=f"harness:{self.agent_id}",
                **self._llm_kwargs,
            )
        return self._llm_client

    # -- Prompt hashing ----------------------------------------------------

    @staticmethod
    def _hash_prompt(text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()[:16]

    # -- Core middleware pipeline ------------------------------------------

    def _pre_call(
        self,
        system_prompt: str,
        user_prompt: str,
        json_mode: bool,
        temperature: float,
    ) -> CallRecord:
        """Pre-call checks: budget enforcement, loop detection, record creation."""
        request_id = f"{self.session_id}-{self._call_counter:04d}"
        self._call_counter += 1

        record = CallRecord(
            request_id=request_id,
            agent_id=self.agent_id,
            timestamp=time.time(),
            system_prompt_hash=self._hash_prompt(system_prompt),
            user_prompt_hash=self._hash_prompt(user_prompt),
            json_mode=json_mode,
            temperature=temperature,
        )

        # 1. Budget enforcement
        budget_reason = self.budget.check()
        if budget_reason:
            if self._on_budget_exceeded and self._on_budget_exceeded(budget_reason):
                logger.info(
                    "[harness:%s] Budget override approved: %s",
                    request_id,
                    budget_reason,
                )
            else:
                record.error = budget_reason
                record.success = False
                self._call_log.append(record)
                raise BudgetExceededError(
                    f"[{self.agent_id}] {budget_reason}. "
                    f"Session: {self.budget.used_calls} calls, "
                    f"{self.budget.used_tokens:,} tokens, "
                    f"${self.budget.used_cost_usd:.4f}"
                )

        # 2. Loop detection
        loop_warning = self.loop_detector.record(record.prompt_fingerprint)
        if loop_warning:
            if self._on_loop_detected and self._on_loop_detected(loop_warning):
                logger.info(
                    "[harness:%s] Loop override approved: %s",
                    request_id,
                    loop_warning,
                )
            else:
                logger.warning("[harness:%s] %s", request_id, loop_warning)

        return record

    def _post_call(
        self,
        record: CallRecord,
        *,
        content: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        provider: str = "",
        model: str = "",
        cost_usd: float = 0.0,
        start_time: float = 0.0,
    ) -> None:
        """Post-call bookkeeping: update record, budget, and event log."""
        record.provider = provider
        record.model = model
        record.input_tokens = input_tokens
        record.output_tokens = output_tokens
        record.cost_usd = cost_usd
        record.latency_ms = (time.time() - start_time) * 1000 if start_time else 0.0
        record.success = True

        self.budget.record(input_tokens + output_tokens, cost_usd)
        self._call_log.append(record)

        logger.info(
            "[harness:%s] OK %s/%s in=%-5d out=%-5d $%.4f %dms",
            record.request_id,
            provider,
            model,
            input_tokens,
            output_tokens,
            cost_usd,
            int(record.latency_ms),
        )

    def _post_error(self, record: CallRecord, error: Exception) -> None:
        """Record a failed call."""
        record.error = str(error)
        record.success = False
        self.budget.used_calls += 1
        self._call_log.append(record)

        logger.error(
            "[harness:%s] FAIL %s",
            record.request_id,
            str(error)[:200],
        )

    # -- Public API (mirrors LLMClient) ------------------------------------

    def generate_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
    ) -> dict[str, Any]:
        """Generate JSON with full harness middleware."""
        record = self._pre_call(system_prompt, user_prompt, json_mode=True, temperature=temperature)
        start = time.time()
        try:
            client = self._get_client()
            result = client.generate_json(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=temperature,
            )
            # Extract usage from the most recent api_calls row
            usage = self._extract_last_usage()
            self._post_call(
                record,
                content=str(result),
                input_tokens=usage.get("input_tokens", 0),
                output_tokens=usage.get("output_tokens", 0),
                provider=usage.get("provider", "unknown"),
                model=usage.get("model", ""),
                cost_usd=usage.get("cost_usd", 0.0),
                start_time=start,
            )
            return result
        except BudgetExceededError:
            raise
        except Exception as e:
            self._post_error(record, e)
            raise

    def generate_text(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
    ) -> str:
        """Generate text with full harness middleware."""
        record = self._pre_call(system_prompt, user_prompt, json_mode=False, temperature=temperature)
        start = time.time()
        try:
            client = self._get_client()
            result = client.generate_text(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=temperature,
            )
            usage = self._extract_last_usage()
            self._post_call(
                record,
                content=result,
                input_tokens=usage.get("input_tokens", 0),
                output_tokens=usage.get("output_tokens", 0),
                provider=usage.get("provider", "unknown"),
                model=usage.get("model", ""),
                cost_usd=usage.get("cost_usd", 0.0),
                start_time=start,
            )
            return result
        except BudgetExceededError:
            raise
        except Exception as e:
            self._post_error(record, e)
            raise

    def generate_text_bridged(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        policy: Any = None,
    ) -> str:
        """Generate bridged text with full harness middleware."""
        record = self._pre_call(system_prompt, user_prompt, json_mode=False, temperature=temperature)
        start = time.time()
        try:
            client = self._get_client()
            kwargs: dict[str, Any] = {
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "temperature": temperature,
            }
            if policy is not None:
                kwargs["policy"] = policy
            result = client.generate_text_bridged(**kwargs)
            usage = self._extract_last_usage()
            self._post_call(
                record,
                content=result,
                input_tokens=usage.get("input_tokens", 0),
                output_tokens=usage.get("output_tokens", 0),
                provider=usage.get("provider", "unknown"),
                model=usage.get("model", ""),
                cost_usd=usage.get("cost_usd", 0.0),
                start_time=start,
            )
            return result
        except BudgetExceededError:
            raise
        except Exception as e:
            self._post_error(record, e)
            raise

    def generate_json_bridged(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        policy: Any = None,
    ) -> dict[str, Any]:
        """Generate bridged JSON with full harness middleware."""
        record = self._pre_call(system_prompt, user_prompt, json_mode=True, temperature=temperature)
        start = time.time()
        try:
            client = self._get_client()
            kwargs: dict[str, Any] = {
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "temperature": temperature,
            }
            if policy is not None:
                kwargs["policy"] = policy
            result = client.generate_json_bridged(**kwargs)
            usage = self._extract_last_usage()
            self._post_call(
                record,
                content=str(result),
                input_tokens=usage.get("input_tokens", 0),
                output_tokens=usage.get("output_tokens", 0),
                provider=usage.get("provider", "unknown"),
                model=usage.get("model", ""),
                cost_usd=usage.get("cost_usd", 0.0),
                start_time=start,
            )
            return result
        except BudgetExceededError:
            raise
        except Exception as e:
            self._post_error(record, e)
            raise

    # -- Usage extraction --------------------------------------------------

    @staticmethod
    def _extract_last_usage() -> dict[str, Any]:
        """Pull the most recent api_calls row from workspace.db."""
        try:
            import sqlite3
            from pathlib import Path

            db_path = Path(__file__).resolve().parent.parent / ".tmp" / "workspace.db"
            if not db_path.exists():
                return {}
            conn = sqlite3.connect(str(db_path))
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT provider, model, tokens_input, tokens_output, cost_usd FROM api_calls ORDER BY id DESC LIMIT 1"
            ).fetchone()
            conn.close()
            if row:
                return {
                    "provider": row["provider"],
                    "model": row["model"],
                    "input_tokens": row["tokens_input"] or 0,
                    "output_tokens": row["tokens_output"] or 0,
                    "cost_usd": row["cost_usd"] or 0.0,
                }
        except Exception:
            pass
        return {}

    # -- Session summary ---------------------------------------------------

    def summary(self) -> dict[str, Any]:
        """Return a structured summary of this harness session."""
        successful = [r for r in self._call_log if r.success]
        failed = [r for r in self._call_log if not r.success]
        providers_used = sorted({r.provider for r in successful if r.provider})
        avg_latency = sum(r.latency_ms for r in successful) / len(successful) if successful else 0.0

        return {
            "session_id": self.session_id,
            "agent_id": self.agent_id,
            "duration_sec": round(time.time() - self.started_at, 1),
            "total_calls": len(self._call_log),
            "successful_calls": len(successful),
            "failed_calls": len(failed),
            "total_tokens": self.budget.used_tokens,
            "total_cost_usd": round(self.budget.used_cost_usd, 6),
            "avg_latency_ms": round(avg_latency, 1),
            "providers_used": providers_used,
            "budget": {
                "tokens": f"{self.budget.used_tokens:,}/{self.budget.max_tokens:,}"
                if self.budget.max_tokens
                else "unlimited",
                "cost": f"${self.budget.used_cost_usd:.4f}/${self.budget.max_cost_usd:.4f}"
                if self.budget.max_cost_usd
                else "unlimited",
                "calls": f"{self.budget.used_calls}/{self.budget.max_calls}" if self.budget.max_calls else "unlimited",
            },
        }

    def reset(self) -> None:
        """Reset session state for reuse."""
        self.session_id = uuid.uuid4().hex[:12]
        self.started_at = time.time()
        self.budget.used_tokens = 0
        self.budget.used_cost_usd = 0.0
        self.budget.used_calls = 0
        self.loop_detector.reset()
        self._call_log.clear()
        self._call_counter = 0

    # -- Factory -----------------------------------------------------------

    @classmethod
    def from_yaml(
        cls,
        agent_id: str,
        *,
        yaml_path: str | None = None,
        on_budget_exceeded: Callable[[str], bool] | None = None,
        on_loop_detected: Callable[[str], bool] | None = None,
        **llm_kwargs: Any,
    ) -> "HarnessSession":
        """Create a session pre-configured from ``agent_permissions.yaml``.

        Looks up *agent_id* in the YAML's ``agents`` map and loads the
        budget fields.  Falls back to the ``default`` profile if the
        agent ID is not found.

        Parameters
        ----------
        agent_id:
            Key to look up under ``agents:`` in the YAML file.
        yaml_path:
            Explicit path to the YAML file.  Defaults to
            ``workspace/directives/agent_permissions.yaml``.
        """
        import yaml as _yaml
        from pathlib import Path

        if yaml_path is None:
            yaml_path = str(Path(__file__).resolve().parents[1] / "directives" / "agent_permissions.yaml")

        with open(yaml_path, encoding="utf-8") as fh:
            data = _yaml.safe_load(fh)

        agents = data.get("agents", {})
        config = agents.get(agent_id, agents.get("default", {}))
        budget = config.get("budget", {})

        return cls(
            agent_id=agent_id,
            max_tokens=budget.get("max_tokens_per_session", 0),
            max_cost_usd=budget.get("max_cost_per_session_usd", 0.0),
            max_calls=budget.get("max_calls_per_session", 0),
            on_budget_exceeded=on_budget_exceeded,
            on_loop_detected=on_loop_detected,
            **llm_kwargs,
        )
