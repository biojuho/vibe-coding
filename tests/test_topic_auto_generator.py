from __future__ import annotations

import importlib
import io
import sys
import types

import execution.topic_auto_generator as tag


class _FakeOpenAIClient:
    def __init__(self, content: str):
        self._content = content
        self.calls = []
        self.chat = types.SimpleNamespace(
            completions=types.SimpleNamespace(create=self._create)
        )

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        return types.SimpleNamespace(
            choices=[
                types.SimpleNamespace(
                    message=types.SimpleNamespace(content=self._content)
                )
            ]
        )


def test_generate_topics_returns_empty_without_api_key(monkeypatch, caplog):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with caplog.at_level("WARNING", logger="execution.topic_auto_generator"):
        topics = tag.generate_topics("space", ["old"], count=3)

    assert topics == []
    assert "OPENAI_API_KEY" in caplog.text


def test_generate_topics_uses_openai_and_trims_results(monkeypatch):
    created = {}

    def fake_openai(*, api_key, timeout):
        client = _FakeOpenAIClient('{"topics": ["  Topic A  ", "", "Topic B"]}')
        created["client"] = client
        created["api_key"] = api_key
        created["timeout"] = timeout
        return client

    monkeypatch.setattr(tag, "OpenAI", fake_openai)

    topics = tag.generate_topics("space", [f"old-{idx}" for idx in range(40)], count=2, api_key="sk-test")

    assert topics == ["Topic A", "Topic B"]
    assert created["api_key"] == "sk-test"
    assert created["timeout"] == 60
    call = created["client"].calls[0]
    assert call["model"] == tag.MODEL
    assert call["response_format"] == {"type": "json_object"}
    assert "old-39" in call["messages"][1]["content"]
    assert "old-0" not in call["messages"][1]["content"]


def test_generate_topics_includes_top_performers_and_dict_topics(monkeypatch):
    created = {}

    def fake_openai(*, api_key, timeout):
        client = _FakeOpenAIClient('{"topics": [{"topic": "Topic A"}, {"topic": "  Topic B  "}, {"other": "skip"}, 123]}')
        created["client"] = client
        return client

    monkeypatch.setattr(tag, "OpenAI", fake_openai)

    topics = tag.generate_topics(
        "space",
        ["old"],
        count=2,
        api_key="sk-test",
        top_performers=[{"topic": "Best topic", "cost_usd": 0.1234}],
    )

    assert topics == ["Topic A", "Topic B"]
    prompt = created["client"].calls[0]["messages"][1]["content"]
    assert "Best topic" in prompt
    assert "$0.123" in prompt


def test_generate_topics_returns_empty_when_model_returns_blank(monkeypatch):
    monkeypatch.setattr(tag, "OpenAI", lambda **kwargs: _FakeOpenAIClient("   "))

    topics = tag.generate_topics("space", ["old"], api_key="sk-test")

    assert topics == []


def test_check_and_replenish_returns_empty_without_channels(monkeypatch):
    monkeypatch.setattr(tag, "get_channels", lambda: [])

    assert tag.check_and_replenish() == {}


def test_check_and_replenish_dry_run(monkeypatch, caplog):
    monkeypatch.setattr(tag, "get_channels", lambda: ["space"])
    monkeypatch.setattr(
        tag,
        "get_all",
        lambda channel=None: [
            {"topic": "old topic", "status": "pending"},
            {"topic": "done topic", "status": "success"},
        ],
    )
    monkeypatch.setattr(tag, "get_top_performing_topics", lambda limit=10, channel=None: [])
    monkeypatch.setattr(
        tag,
        "generate_topics",
        lambda channel, existing, count=0, top_performers=None, **kwargs: ["fresh one", "fresh two"],
    )
    monkeypatch.setattr(tag, "add_topic", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("unexpected")))

    with caplog.at_level("INFO", logger="execution.topic_auto_generator"):
        result = tag.check_and_replenish(threshold=1, count=2, dry_run=True)

    assert result == {"space": ["fresh one", "fresh two"]}
    assert "[DRY] fresh one" in caplog.text
    assert "[DRY] fresh two" in caplog.text


def test_check_and_replenish_adds_topics_when_below_threshold(monkeypatch, caplog):
    monkeypatch.setattr(tag, "get_channels", lambda: ["space", "history"])

    def fake_get_all(channel=None):
        if channel == "space":
            return [
                {"topic": "old topic", "status": "pending"},
                {"topic": "done topic", "status": "success"},
            ]
        return [{"topic": f"queued-{idx}", "status": "pending"} for idx in range(4)]

    added = []
    monkeypatch.setattr(tag, "get_all", fake_get_all)
    monkeypatch.setattr(tag, "get_top_performing_topics", lambda limit=10, channel=None: [])
    monkeypatch.setattr(
        tag,
        "generate_topics",
        lambda channel, existing, count=0, top_performers=None, **kwargs: ["fresh one"] if channel == "space" else [],
    )
    monkeypatch.setattr(tag, "add_topic", lambda topic, channel="", notes="": added.append((topic, channel, notes)))

    with caplog.at_level("INFO", logger="execution.topic_auto_generator"):
        result = tag.check_and_replenish(threshold=2, count=1, dry_run=False)

    assert result == {"space": ["fresh one"]}
    assert added == [("fresh one", "space", "auto-generated")]
    assert "[ADD] fresh one" in caplog.text


def test_check_and_replenish_prints_when_generation_returns_nothing(monkeypatch, caplog):
    monkeypatch.setattr(tag, "get_channels", lambda: ["space"])
    monkeypatch.setattr(tag, "get_all", lambda channel=None: [{"topic": "old topic", "status": "pending"}])
    monkeypatch.setattr(tag, "get_top_performing_topics", lambda limit=10, channel=None: [])
    monkeypatch.setattr(
        tag,
        "generate_topics",
        lambda channel, existing, count=0, top_performers=None, **kwargs: [],
    )

    with caplog.at_level("WARNING", logger="execution.topic_auto_generator"):
        result = tag.check_and_replenish(threshold=3, count=2, dry_run=False)

    assert result == {}
    assert "생성 실패 또는 결과 없음" in caplog.text


def test_main_prints_added_summary(monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(sys, "argv", ["topic_auto_generator.py", "--threshold", "2", "--count", "3", "--dry-run"])
    monkeypatch.setattr(tag, "load_dotenv", lambda *args, **kwargs: calls.append((args, kwargs)))
    monkeypatch.setattr(tag, "init_db", lambda: calls.append("init"))
    monkeypatch.setattr(
        tag,
        "check_and_replenish",
        lambda threshold, count, dry_run: {"space": ["a", "b"]},
    )

    result = tag.main()

    assert result == 0
    output = capsys.readouterr().out
    assert "threshold=2, count=3, dry-run=True" in output
    assert "총 2개 주제 미리보기" in output
    assert calls


def test_main_prints_no_work_summary(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["topic_auto_generator.py"])
    monkeypatch.setattr(tag, "load_dotenv", lambda *args, **kwargs: None)
    monkeypatch.setattr(tag, "init_db", lambda: None)
    monkeypatch.setattr(tag, "check_and_replenish", lambda threshold, count, dry_run: {})

    result = tag.main()

    assert result == 0
    assert "보충 필요 없음" in capsys.readouterr().out


def test_reload_wraps_stdout_for_non_utf8(monkeypatch):
    original_stdout = sys.stdout
    original_stderr = sys.stderr
    fake_stdout = io.TextIOWrapper(io.BytesIO(), encoding="cp949")
    fake_stderr = io.TextIOWrapper(io.BytesIO(), encoding="cp949")

    monkeypatch.setattr(sys, "stdout", fake_stdout)
    monkeypatch.setattr(sys, "stderr", fake_stderr)

    importlib.reload(tag)

    assert sys.stdout.encoding.lower() == "utf-8"
    assert sys.stderr.encoding.lower() == "utf-8"

    monkeypatch.setattr(sys, "stdout", original_stdout)
    monkeypatch.setattr(sys, "stderr", original_stderr)
    importlib.reload(tag)
