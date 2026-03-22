from __future__ import annotations

import json
import sys
from types import ModuleType, SimpleNamespace

import execution.content_writer as content_writer


def test_load_prompt_template_prefers_project_template(tmp_path, monkeypatch) -> None:
    (tmp_path / "notebooklm_demo.yaml").write_text(
        "system: custom\nuser_prefix: prefix\noutput_format: markdown\n",
        encoding="utf-8",
    )
    (tmp_path / "notebooklm_default.yaml").write_text(
        "system: default\nuser_prefix: fallback\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(content_writer, "_PROMPTS_DIR", tmp_path)

    template = content_writer.load_prompt_template("demo")
    missing_template = content_writer.load_prompt_template("missing")

    assert template["system"] == "custom"
    assert missing_template["system"] == "default"


def test_build_user_message_truncates_long_text() -> None:
    long_text = "A" * 60_100

    message = content_writer._build_user_message(
        long_text,
        {"user_prefix": "Prefix", "language": "ko", "output_format": "markdown"},
    )

    assert message.startswith("Prefix")
    assert "[... 텍스트가 너무 길어 일부 생략됨 ...]" in message
    assert "언어: ko" in message


def test_write_with_gemini_uses_configured_model(monkeypatch) -> None:
    calls: dict[str, object] = {}

    fake_genai = ModuleType("google.generativeai")

    def fake_configure(*, api_key: str) -> None:
        calls["api_key"] = api_key

    class FakeModel:
        def __init__(self, *, model_name: str, system_instruction: str) -> None:
            calls["model_name"] = model_name
            calls["system_instruction"] = system_instruction

        def generate_content(self, user_message: str):
            calls["user_message"] = user_message
            return SimpleNamespace(text="  # Gemini Title\nBody  ")

    fake_genai.configure = fake_configure
    fake_genai.GenerativeModel = FakeModel

    fake_google = sys.modules.get("google", ModuleType("google"))
    fake_google.generativeai = fake_genai

    monkeypatch.setitem(sys.modules, "google", fake_google)
    monkeypatch.setitem(sys.modules, "google.generativeai", fake_genai)
    monkeypatch.setenv("GOOGLE_AI_API_KEY", "gemini-key")

    result = content_writer._write_with_gemini("source text", {"system": "system"})

    assert result == "# Gemini Title\nBody"
    assert calls["api_key"] == "gemini-key"
    assert calls["model_name"] == "gemini-2.0-flash"
    assert "source text" in str(calls["user_message"])


def test_write_with_claude_uses_messages_api(monkeypatch) -> None:
    calls: dict[str, object] = {}
    fake_anthropic = ModuleType("anthropic")

    class FakeMessages:
        def create(self, **kwargs):
            calls.update(kwargs)
            return SimpleNamespace(content=[SimpleNamespace(text="  # Claude Title\nText  ")])

    class FakeAnthropic:
        def __init__(self, *, api_key: str) -> None:
            calls["api_key"] = api_key
            self.messages = FakeMessages()

    fake_anthropic.Anthropic = FakeAnthropic
    monkeypatch.setitem(sys.modules, "anthropic", fake_anthropic)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "claude-key")

    result = content_writer._write_with_claude("draft me", {"system": "sys"})

    assert result == "# Claude Title\nText"
    assert calls["api_key"] == "claude-key"
    assert calls["model"] == "claude-opus-4-5"


def test_write_with_gpt_uses_chat_completions(monkeypatch) -> None:
    calls: dict[str, object] = {}
    fake_openai = ModuleType("openai")

    class FakeCompletions:
        def create(self, **kwargs):
            calls.update(kwargs)
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="  # GPT Title\nBody  "))]
            )

    class FakeOpenAIClient:
        def __init__(self, *, api_key: str) -> None:
            calls["api_key"] = api_key
            self.chat = SimpleNamespace(completions=FakeCompletions())

    fake_openai.OpenAI = FakeOpenAIClient
    monkeypatch.setitem(sys.modules, "openai", fake_openai)
    monkeypatch.setenv("OPENAI_API_KEY", "openai-key")

    result = content_writer._write_with_gpt("source", {"system": "sys"})

    assert result == "# GPT Title\nBody"
    assert calls["api_key"] == "openai-key"
    assert calls["model"] == "gpt-4o"


def test_write_article_falls_back_and_extracts_title(monkeypatch) -> None:
    monkeypatch.setattr(content_writer, "load_prompt_template", lambda project: {"system": "ok"})

    def fail(*args, **kwargs):
        raise RuntimeError("primary failed")

    monkeypatch.setattr(content_writer, "_write_with_gemini", fail)
    monkeypatch.setattr(content_writer, "_write_with_claude", lambda text, template: "# Final Title\nBody")

    result = content_writer.write_article("input", project="demo", provider="gemini")

    assert result["provider"] == "claude"
    assert result["title"] == "Final Title"
    assert result["char_count"] == len("# Final Title\nBody")


def test_write_article_raises_when_all_providers_fail(monkeypatch) -> None:
    monkeypatch.setattr(content_writer, "load_prompt_template", lambda project: {})

    def fail(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(content_writer, "_write_with_gemini", fail)
    monkeypatch.setattr(content_writer, "_write_with_claude", fail)
    monkeypatch.setattr(content_writer, "_write_with_gpt", fail)

    try:
        content_writer.write_article("input", provider="gemini")
    except RuntimeError as exc:
        assert "모든 AI provider 실패" in str(exc)
    else:
        raise AssertionError("Expected RuntimeError")


def test_main_writes_json_output_file(tmp_path, monkeypatch, capsys) -> None:
    output_path = tmp_path / "result.json"
    expected = {
        "article": "# Title\nBody",
        "title": "Title",
        "provider": "gemini",
        "project": "demo",
        "char_count": 12,
        "generated_at": "2026-03-21T00:00:00Z",
    }

    monkeypatch.setattr(content_writer, "write_article", lambda text, project, provider: expected)
    monkeypatch.setattr(
        sys,
        "argv",
        ["content_writer.py", "write", "--text", "hello", "--project", "demo", "--output", str(output_path)],
    )

    content_writer.main()

    stdout = capsys.readouterr().out
    assert "결과 저장" in stdout
    assert json.loads(output_path.read_text(encoding="utf-8")) == expected
