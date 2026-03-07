from __future__ import annotations

import importlib
import io
import sys

import execution.topic_auto_generator as tag


class _FakeLLMClient:
    """LLMClient를 대체하는 테스트용 fake."""

    def __init__(self, json_result=None, enabled=True):
        self._json_result = json_result or {}
        self._enabled = enabled
        self.calls = []

    def enabled_providers(self):
        return ["google", "openai"] if self._enabled else []

    def generate_json(self, *, system_prompt, user_prompt, temperature=0.7):
        self.calls.append({
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "temperature": temperature,
        })
        return self._json_result

    def generate_json_bridged(self, *, system_prompt, user_prompt, temperature=0.7):
        return self.generate_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
        )


def test_generate_topics_returns_empty_without_api_key(monkeypatch, caplog):
    """모든 LLM 프로바이더 비활성화 시 빈 리스트 반환."""
    fake = _FakeLLMClient(enabled=False)
    monkeypatch.setattr(tag, "LLMClient", lambda **kwargs: fake)

    with caplog.at_level("WARNING", logger="execution.topic_auto_generator"):
        topics = tag.generate_topics("space", ["old"], count=3)

    assert topics == []
    assert "LLM API" in caplog.text


def test_generate_topics_uses_llm_and_trims_results(monkeypatch):
    """LLMClient로 주제 생성 + 공백 trim + 빈 문자열 제거."""
    fake = _FakeLLMClient(json_result={"topics": ["  Topic A  ", "", "Topic B"]})
    monkeypatch.setattr(tag, "LLMClient", lambda **kwargs: fake)

    topics = tag.generate_topics("space", [f"old-{idx}" for idx in range(40)], count=2)

    assert topics == ["Topic A", "Topic B"]
    assert len(fake.calls) == 1
    prompt = fake.calls[0]["user_prompt"]
    assert "old-39" in prompt
    assert "old-0" not in prompt


def test_generate_topics_includes_top_performers_and_dict_topics(monkeypatch):
    """성과 데이터 포함 + dict 형태 주제 파싱."""
    fake = _FakeLLMClient(
        json_result={"topics": [{"topic": "Topic A"}, {"topic": "  Topic B  "}, {"other": "skip"}, 123]}
    )
    monkeypatch.setattr(tag, "LLMClient", lambda **kwargs: fake)

    topics = tag.generate_topics(
        "space",
        ["old"],
        count=2,
        top_performers=[{"topic": "Best topic", "cost_usd": 0.1234}],
    )

    assert topics == ["Topic A", "Topic B"]
    prompt = fake.calls[0]["user_prompt"]
    assert "Best topic" in prompt
    assert "$0.123" in prompt


def test_generate_topics_returns_empty_when_all_providers_fail(monkeypatch, caplog):
    """모든 프로바이더 실패 시 빈 리스트 반환."""
    def fake_client_class(**kwargs):
        c = _FakeLLMClient(enabled=True)

        def raise_error(**kw):
            raise RuntimeError("All providers failed")

        c.generate_json = raise_error
        c.generate_json_bridged = raise_error
        return c

    monkeypatch.setattr(tag, "LLMClient", fake_client_class)

    with caplog.at_level("ERROR", logger="execution.topic_auto_generator"):
        topics = tag.generate_topics("space", ["old"])

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
