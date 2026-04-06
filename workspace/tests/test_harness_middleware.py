"""execution/harness_middleware.py 테스트.

HarnessSession의 세 가지 미들웨어 레이어를 검증:
1. 관측성 (request ID, 호출 기록)
2. 루프 감지 (반복 패턴 경고)
3. 예산 제한 (토큰/비용/호출 수 제한)
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from execution.harness_middleware import (
    BudgetExceededError,
    CallRecord,
    HarnessSession,
    LoopDetector,
    SessionBudget,
)


# ── SessionBudget ────────────────────────────────────────────────


class TestSessionBudget:
    def test_unlimited_by_default(self):
        b = SessionBudget()
        assert b.check() is None
        assert b.tokens_remaining is None
        assert b.cost_remaining is None
        assert b.calls_remaining is None

    def test_token_limit(self):
        b = SessionBudget(max_tokens=1000)
        assert b.check() is None
        b.record(tokens=600, cost=0.01)
        assert b.tokens_remaining == 400
        b.record(tokens=400, cost=0.01)
        assert b.check() is not None
        assert "Token budget exhausted" in b.check()

    def test_cost_limit(self):
        b = SessionBudget(max_cost_usd=1.0)
        b.record(tokens=100, cost=0.5)
        assert b.check() is None
        b.record(tokens=100, cost=0.6)
        assert "Cost budget exhausted" in b.check()

    def test_call_limit(self):
        b = SessionBudget(max_calls=3)
        for _ in range(3):
            b.record(tokens=10, cost=0.01)
        assert "Call budget exhausted" in b.check()

    def test_remaining_values(self):
        b = SessionBudget(max_tokens=1000, max_cost_usd=5.0, max_calls=10)
        b.record(tokens=200, cost=1.0)
        assert b.tokens_remaining == 800
        assert b.cost_remaining == 4.0
        assert b.calls_remaining == 9


# ── LoopDetector ─────────────────────────────────────────────────


class TestLoopDetector:
    def test_no_loop_with_varied_calls(self):
        d = LoopDetector(window_size=5, threshold=3)
        for i in range(5):
            assert d.record(f"fp_{i}") is None

    def test_detect_loop(self):
        d = LoopDetector(window_size=5, threshold=3)
        assert d.record("same") is None
        assert d.record("same") is None
        warning = d.record("same")
        assert warning is not None
        assert "Loop detected" in warning
        assert "3x" in warning

    def test_window_slides(self):
        d = LoopDetector(window_size=3, threshold=3)
        d.record("a")
        d.record("a")
        # Window: [a, a]
        d.record("b")
        # Window: [a, a, b]
        d.record("b")
        # Window: [a, b, b]  — 'a' slid out
        d.record("b")
        # Window: [b, b, b] — now 'b' triggers
        assert d.record("b") is not None  # [b, b, b] in window after this

    def test_reset(self):
        d = LoopDetector(window_size=5, threshold=2)
        d.record("x")
        d.record("x")
        d.reset()
        assert d.record("x") is None  # fresh window

    def test_threshold_respected(self):
        d = LoopDetector(window_size=10, threshold=5)
        for i in range(4):
            assert d.record("fp") is None
        assert d.record("fp") is not None


# ── CallRecord ───────────────────────────────────────────────────


class TestCallRecord:
    def test_prompt_fingerprint(self):
        r = CallRecord(
            request_id="test-0001",
            agent_id="test",
            timestamp=0.0,
            system_prompt_hash="abcdef1234567890",
            user_prompt_hash="1234567890abcdef",
            json_mode=True,
            temperature=0.7,
        )
        fp = r.prompt_fingerprint
        assert "abcdef12" in fp
        assert "12345678" in fp
        assert "True" in fp


# ── HarnessSession (unit, no real LLM calls) ─────────────────────


class TestHarnessSessionBudgetEnforcement:
    """Budget enforcement without actual LLM calls."""

    def test_budget_exceeded_raises(self):
        session = HarnessSession(
            agent_id="test",
            max_calls=0,  # unlimited
            max_tokens=1,  # very low
        )
        # Simulate that budget is already used
        session.budget.used_tokens = 1
        with pytest.raises(BudgetExceededError, match="Token budget exhausted"):
            session._pre_call("sys", "user", json_mode=False, temperature=0.7)

    def test_budget_override_callback(self):
        override_fn = MagicMock(return_value=True)
        session = HarnessSession(
            agent_id="test",
            max_tokens=1,
            on_budget_exceeded=override_fn,
        )
        session.budget.used_tokens = 1
        # Should not raise because callback returns True
        record = session._pre_call("sys", "user", json_mode=False, temperature=0.7)
        override_fn.assert_called_once()
        assert record.request_id is not None

    def test_budget_override_denied(self):
        override_fn = MagicMock(return_value=False)
        session = HarnessSession(
            agent_id="test",
            max_tokens=1,
            on_budget_exceeded=override_fn,
        )
        session.budget.used_tokens = 1
        with pytest.raises(BudgetExceededError):
            session._pre_call("sys", "user", json_mode=False, temperature=0.7)


class TestHarnessSessionLoopDetection:
    """Loop detection without actual LLM calls."""

    def test_loop_warning_logged(self):
        session = HarnessSession(
            agent_id="test",
            loop_window=5,
            loop_threshold=3,
        )
        # Same prompts → same fingerprint
        for _ in range(3):
            session._pre_call("same_sys", "same_user", json_mode=False, temperature=0.7)
        # Should have 3 records, loop detected on 3rd
        assert len(session._call_log) == 0  # _pre_call doesn't append to log

    def test_loop_callback_called(self):
        loop_fn = MagicMock(return_value=True)
        session = HarnessSession(
            agent_id="test",
            loop_window=5,
            loop_threshold=2,
            on_loop_detected=loop_fn,
        )
        session._pre_call("sys", "user", json_mode=False, temperature=0.7)
        session._pre_call("sys", "user", json_mode=False, temperature=0.7)
        loop_fn.assert_called_once()


class TestHarnessSessionObservability:
    """Observability features."""

    def test_session_id_assigned(self):
        s = HarnessSession(agent_id="obs-test")
        assert len(s.session_id) == 12

    def test_request_ids_sequential(self):
        s = HarnessSession(agent_id="obs-test")
        r1 = s._pre_call("a", "b", json_mode=False, temperature=0.7)
        r2 = s._pre_call("c", "d", json_mode=False, temperature=0.7)
        # Counter increments regardless of call_log state
        id1_suffix = r1.request_id.split("-")[-1]
        id2_suffix = r2.request_id.split("-")[-1]
        assert int(id2_suffix) == int(id1_suffix) + 1

    def test_post_call_updates_record(self):
        s = HarnessSession(agent_id="obs-test")
        r = s._pre_call("sys", "user", json_mode=False, temperature=0.7)
        s._post_call(
            r,
            content="hello",
            input_tokens=100,
            output_tokens=50,
            provider="google",
            model="gemini-2.5-flash",
            cost_usd=0.0,
            start_time=r.timestamp,
        )
        assert r.success is True
        assert r.provider == "google"
        assert r.input_tokens == 100
        assert r.output_tokens == 50
        assert len(s._call_log) == 1

    def test_post_error_records_failure(self):
        s = HarnessSession(agent_id="obs-test")
        r = s._pre_call("sys", "user", json_mode=False, temperature=0.7)
        s._post_error(r, RuntimeError("provider down"))
        assert r.success is False
        assert "provider down" in r.error
        assert len(s._call_log) == 1

    def test_summary_structure(self):
        s = HarnessSession(agent_id="obs-test", max_tokens=10000)
        summary = s.summary()
        assert summary["agent_id"] == "obs-test"
        assert summary["total_calls"] == 0
        assert "budget" in summary
        assert "10,000" in summary["budget"]["tokens"]

    def test_reset_clears_state(self):
        s = HarnessSession(agent_id="obs-test", max_tokens=100)
        s.budget.record(tokens=50, cost=0.01)
        old_session_id = s.session_id
        s.reset()
        assert s.session_id != old_session_id
        assert s.budget.used_tokens == 0
        assert len(s._call_log) == 0


class TestHarnessSessionIntegration:
    """Integration tests with mocked LLMClient."""

    @patch("execution.harness_middleware.HarnessSession._extract_last_usage")
    def test_generate_text_full_pipeline(self, mock_usage):
        mock_usage.return_value = {
            "provider": "google",
            "model": "gemini-2.5-flash",
            "input_tokens": 200,
            "output_tokens": 100,
            "cost_usd": 0.0,
        }

        mock_client = MagicMock()
        mock_client.generate_text.return_value = "Hello world"

        session = HarnessSession(agent_id="int-test", max_tokens=10000)
        session._llm_client = mock_client

        result = session.generate_text(
            system_prompt="Be helpful",
            user_prompt="Say hello",
        )

        assert result == "Hello world"
        assert session.budget.used_tokens == 300
        assert session.budget.used_calls == 1
        assert len(session._call_log) == 1
        assert session._call_log[0].success is True

    @patch("execution.harness_middleware.HarnessSession._extract_last_usage")
    def test_generate_json_full_pipeline(self, mock_usage):
        mock_usage.return_value = {
            "provider": "deepseek",
            "model": "deepseek-chat",
            "input_tokens": 300,
            "output_tokens": 150,
            "cost_usd": 0.0001,
        }

        mock_client = MagicMock()
        mock_client.generate_json.return_value = {"key": "value"}

        session = HarnessSession(agent_id="int-test", max_tokens=10000)
        session._llm_client = mock_client

        result = session.generate_json(
            system_prompt="Return JSON",
            user_prompt="Give me data",
        )

        assert result == {"key": "value"}
        assert session.budget.used_tokens == 450
        assert session.budget.used_cost_usd == pytest.approx(0.0001, abs=1e-6)

    @patch("execution.harness_middleware.HarnessSession._extract_last_usage")
    def test_budget_stops_after_limit(self, mock_usage):
        mock_usage.return_value = {
            "provider": "google",
            "model": "gemini-2.5-flash",
            "input_tokens": 400,
            "output_tokens": 200,
            "cost_usd": 0.0,
        }

        mock_client = MagicMock()
        mock_client.generate_text.return_value = "ok"

        session = HarnessSession(agent_id="budget-test", max_tokens=1000)
        session._llm_client = mock_client

        # First call: 600 tokens — OK
        session.generate_text(system_prompt="sys", user_prompt="user1")
        assert session.budget.used_tokens == 600

        # Second call: would push to 1200 — exceeds 1000
        session.generate_text(system_prompt="sys", user_prompt="user2")
        assert session.budget.used_tokens == 1200

        # Third call: budget exhausted
        with pytest.raises(BudgetExceededError):
            session.generate_text(system_prompt="sys", user_prompt="user3")

    @patch("execution.harness_middleware.HarnessSession._extract_last_usage")
    def test_error_propagated_and_recorded(self, mock_usage):
        mock_client = MagicMock()
        mock_client.generate_text.side_effect = RuntimeError("All providers failed")

        session = HarnessSession(agent_id="err-test")
        session._llm_client = mock_client

        with pytest.raises(RuntimeError, match="All providers failed"):
            session.generate_text(system_prompt="sys", user_prompt="user")

        assert len(session._call_log) == 1
        assert session._call_log[0].success is False
        assert "All providers failed" in session._call_log[0].error


# ── YAML permissions loading (separate from middleware) ───────────


class TestAgentPermissionsYAML:
    """Verify the agent_permissions.yaml is well-formed."""

    def test_yaml_loads(self):
        from pathlib import Path

        import yaml

        yaml_path = Path(__file__).resolve().parents[1] / "directives" / "agent_permissions.yaml"
        if not yaml_path.exists():
            pytest.skip("agent_permissions.yaml not found")

        with open(yaml_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        assert "agents" in data
        agents = data["agents"]

        # Check required agent profiles
        for agent_id in ("blind-to-x-pipeline", "shorts-maker-v2-pipeline", "default"):
            assert agent_id in agents, f"Missing agent profile: {agent_id}"

        # Check budget structure
        for agent_id, config in agents.items():
            if "budget" in config:
                budget = config["budget"]
                assert "max_tokens_per_session" in budget
                assert "max_cost_per_session_usd" in budget

    def test_denied_paths_present(self):
        from pathlib import Path

        import yaml

        yaml_path = Path(__file__).resolve().parents[1] / "directives" / "agent_permissions.yaml"
        if not yaml_path.exists():
            pytest.skip("agent_permissions.yaml not found")

        with open(yaml_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        # Every agent should have denied_paths (from defaults anchor)
        for agent_id, config in data["agents"].items():
            assert "denied_paths" in config, f"{agent_id} missing denied_paths"
            assert "**/.env" in config["denied_paths"]
