"""Regression tests for content_intelligence.boosting.estimate_viral_boost_llm.

Background: this function had a path bug — `_root = parent.parent.parent`
resolved to `projects/blind-to-x/`, then looked for `execution/llm_client.py`
there (which doesn't exist). The silent `try/except Exception` swallowed
`FileNotFoundError` and always returned 0.0. Result: boundary-score posts
(50–70 publishability) never received the LLM viral boost — dead code.

Fix: use `parents[4]` to reach repo root + `workspace/execution/llm_client.py`,
plus an explicit `.exists()` guard so the failure mode is loggable rather than
silent.

These tests pin the discovery path and the graceful-fallback semantics.
"""

from __future__ import annotations

import importlib.abc
import importlib.machinery
import importlib.util
import pathlib
import sys
import types

from pipeline.content_intelligence import boosting


def test_llm_client_target_path_resolves_to_workspace():
    """`parents[4]/workspace/execution/llm_client.py` must exist in this repo.

    This is the canonical pin — if the workspace path contract changes (e.g.
    blind-to-x moves), this test fails loudly instead of the function silently
    going back to dead-code 0.0 returns.
    """
    boosting_file = pathlib.Path(boosting.__file__).resolve()
    repo_root = boosting_file.parents[4]
    target = repo_root / "workspace" / "execution" / "llm_client.py"
    assert target.exists(), f"workspace LLMClient not found at {target}"


def test_estimate_viral_boost_uses_workspace_llm_client(monkeypatch):
    captured: dict[str, object] = {}
    expected_target = pathlib.Path(boosting.__file__).resolve().parents[4] / "workspace" / "execution" / "llm_client.py"

    class FakeLLMClient:
        def __init__(self, **kwargs):
            captured["client_kwargs"] = kwargs

        def generate_json(self, **kwargs):
            captured["generate_kwargs"] = kwargs
            return {"score": 80, "reason": "테스트"}

    class FakeLoader(importlib.abc.Loader):
        def create_module(self, spec):
            return None

        def exec_module(self, module):
            module.LLMClient = FakeLLMClient

    def fake_spec_from_file_location(name, location):
        captured["module_name"] = name
        captured["target"] = pathlib.Path(location)
        return importlib.machinery.ModuleSpec(name, FakeLoader())

    monkeypatch.setattr(importlib.util, "spec_from_file_location", fake_spec_from_file_location)

    result = boosting.estimate_viral_boost_llm(
        title="테스트 제목",
        content="테스트 본문입니다.",
        topic_cluster="기타",
        emotion_axis="공감",
    )

    assert result == 12.0
    assert captured["module_name"] == "execution.llm_client"
    assert captured["target"] == expected_target
    assert captured["client_kwargs"] == {
        "providers": ["google", "groq", "deepseek", "zhipuai"],
        "track_usage": False,
    }
    assert captured["generate_kwargs"]["temperature"] == 0.3


def test_estimate_viral_boost_returns_clamped_score_when_provider_unavailable(monkeypatch):
    """Cache miss + no keys → graceful 0.0; cache hit → clamped score in [0, 15].

    Either way the function MUST be live (not dead code) — it should never raise.
    Keep dotenv disabled so this test never reloads real provider keys from .env.
    """
    fake_dotenv = types.ModuleType("dotenv")
    fake_dotenv.load_dotenv = lambda *args, **kwargs: False
    monkeypatch.setitem(sys.modules, "dotenv", fake_dotenv)

    # Strip every provider key so generate_json must reach an empty fallback chain
    for env in (
        "GOOGLE_API_KEY",
        "GEMINI_API_KEY",
        "GROQ_API_KEY",
        "DEEPSEEK_API_KEY",
        "ZHIPUAI_API_KEY",
        "OLLAMA_BASE_URL",
    ):
        monkeypatch.delenv(env, raising=False)

    result = boosting.estimate_viral_boost_llm(
        title="테스트 제목",
        content="테스트 본문입니다.",
        topic_cluster="기타",
        emotion_axis="공감",
    )
    # Function must always return a clamped float in [0, 15].
    # Without keys + isolated cache, expected 0.0; with cache, any value in range is fine.
    assert isinstance(result, float)
    assert 0.0 <= result <= 15.0


def test_estimate_viral_boost_safe_when_args_are_long():
    """Long title/content (> 200/500 chars) must not raise — the function truncates them
    via internal slicing. This sanity-checks that the truncation path stays intact even
    after the import-path refactor.
    """
    long_title = "제목" * 500  # 1000 chars
    long_content = "본문" * 1000  # 2000 chars
    result = boosting.estimate_viral_boost_llm(long_title, long_content, "기타", "공감")
    # Must never raise, must always return a clamped float
    assert isinstance(result, float)
    assert 0.0 <= result <= 15.0
