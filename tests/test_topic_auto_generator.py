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


# ---------------------------------------------------------------------------
# get_trending_topics (lines 46-48)
# ---------------------------------------------------------------------------


def test_get_trending_topics_success(monkeypatch):
    """Mocked pytrends returns trending keywords."""
    import types as _types

    class FakeTrendReq:
        def __init__(self, **kw):
            pass

        def trending_searches(self, pn="south_korea"):
            # Return a fake DataFrame-like object with [0].tolist()
            class FakeDF:
                def __init__(self):
                    self._data = {0: self}
                    self._items = ["키워드1", "키워드2", "키워드3"]

                def __getitem__(self, key):
                    if key == 0:
                        return self
                    raise KeyError(key)

                def tolist(self):
                    return self._items
            return FakeDF()

    fake_pytrends = _types.ModuleType("pytrends")
    fake_request = _types.ModuleType("pytrends.request")
    fake_request.TrendReq = FakeTrendReq
    fake_pytrends.request = fake_request

    monkeypatch.setitem(sys.modules, "pytrends", fake_pytrends)
    monkeypatch.setitem(sys.modules, "pytrends.request", fake_request)

    result = tag.get_trending_topics(count=2)
    assert result == ["키워드1", "키워드2"]


def test_get_trending_topics_import_error(monkeypatch):
    """pytrends not installed -> returns empty list."""
    # Remove pytrends from modules if present
    monkeypatch.delitem(sys.modules, "pytrends", raising=False)
    monkeypatch.delitem(sys.modules, "pytrends.request", raising=False)

    import builtins
    original_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "pytrends.request" or name == "pytrends":
            raise ImportError("No module named 'pytrends'")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    result = tag.get_trending_topics()
    assert result == []


# ---------------------------------------------------------------------------
# generate_topics with trending_keywords (line 98)
# ---------------------------------------------------------------------------


def test_generate_topics_with_trending_keywords(monkeypatch):
    """trending_keywords are included in the prompt."""
    fake = _FakeLLMClient(json_result={"topics": ["Trend Topic A"]})
    monkeypatch.setattr(tag, "LLMClient", lambda **kwargs: fake)

    topics = tag.generate_topics(
        "space",
        ["old"],
        count=1,
        trending_keywords=["트렌드1", "트렌드2"],
    )

    assert topics == ["Trend Topic A"]
    prompt = fake.calls[0]["user_prompt"]
    assert "트렌드1" in prompt
    assert "트렌드2" in prompt


# ---------------------------------------------------------------------------
# generate_topics non-bridged fallback (line 122)
# ---------------------------------------------------------------------------


def test_generate_topics_uses_non_bridged_fallback(monkeypatch):
    """When generate_json_bridged is not available, falls back to generate_json."""
    class _NoBridgeLLMClient:
        def __init__(self):
            self.calls = []

        def enabled_providers(self):
            return ["google"]

        def generate_json(self, *, system_prompt, user_prompt, temperature=0.7):
            self.calls.append("generate_json")
            return {"topics": ["Fallback Topic"]}

    fake = _NoBridgeLLMClient()
    monkeypatch.setattr(tag, "LLMClient", lambda **kwargs: fake)

    topics = tag.generate_topics("space", ["old"], count=1)

    assert topics == ["Fallback Topic"]
    assert fake.calls == ["generate_json"]


# ---------------------------------------------------------------------------
# _COMMUNITY_TRENDS_OK = False (lines 35-36)
# ---------------------------------------------------------------------------


def test_check_and_replenish_without_community_trends(monkeypatch, caplog):
    """When _COMMUNITY_TRENDS_OK is False, community trend collection is skipped."""
    monkeypatch.setattr(tag, "_COMMUNITY_TRENDS_OK", False)
    monkeypatch.setattr(tag, "get_channels", lambda: ["space"])
    monkeypatch.setattr(
        tag,
        "get_all",
        lambda channel=None: [{"topic": "old topic", "status": "pending"}],
    )
    monkeypatch.setattr(tag, "get_top_performing_topics", lambda limit=10, channel=None: [])
    monkeypatch.setattr(tag, "get_trending_topics", lambda count=10: [])
    monkeypatch.setattr(
        tag,
        "generate_topics",
        lambda channel, existing, count=0, top_performers=None, **kwargs: ["new topic"],
    )
    added = []
    monkeypatch.setattr(tag, "add_topic", lambda topic, channel="", notes="": added.append(topic))

    with caplog.at_level("INFO", logger="execution.topic_auto_generator"):
        result = tag.check_and_replenish(threshold=3, count=1, dry_run=False)

    assert result == {"space": ["new topic"]}
    assert added == ["new topic"]


# ---------------------------------------------------------------------------
# community trend collection in auto_generate_all (lines 172-175, 177)
# ---------------------------------------------------------------------------


def test_check_and_replenish_with_community_trends_success(monkeypatch, caplog):
    """Community trends are appended to trending keywords."""
    monkeypatch.setattr(tag, "_COMMUNITY_TRENDS_OK", True)
    monkeypatch.setattr(tag, "get_channels", lambda: ["space"])
    monkeypatch.setattr(
        tag,
        "get_all",
        lambda channel=None: [{"topic": "old topic", "status": "pending"}],
    )
    monkeypatch.setattr(tag, "get_top_performing_topics", lambda limit=10, channel=None: [])
    monkeypatch.setattr(tag, "get_trending_topics", lambda count=10: ["trending1"])

    captured_kwargs = {}

    def fake_generate(channel, existing, count=0, top_performers=None, **kwargs):
        captured_kwargs.update(kwargs)
        return ["community topic"]

    monkeypatch.setattr(tag, "generate_topics", fake_generate)

    # Mock community trend function
    monkeypatch.setattr(
        tag,
        "get_community_trend_titles",
        lambda limit=5: ["커뮤니티1", "커뮤니티2"],
    )
    added = []
    monkeypatch.setattr(tag, "add_topic", lambda topic, channel="", notes="": added.append(topic))

    with caplog.at_level("DEBUG", logger="execution.topic_auto_generator"):
        result = tag.check_and_replenish(threshold=3, count=1, dry_run=False)

    assert result == {"space": ["community topic"]}
    # Verify community trends were appended to trending_keywords
    assert "커뮤니티1" in captured_kwargs.get("trending_keywords", [])
    assert "trending1" in captured_kwargs.get("trending_keywords", [])


def test_check_and_replenish_community_trends_failure(monkeypatch, caplog):
    """Community trend collection fails -> warning logged, continues normally."""
    monkeypatch.setattr(tag, "_COMMUNITY_TRENDS_OK", True)
    monkeypatch.setattr(tag, "get_channels", lambda: ["space"])
    monkeypatch.setattr(
        tag,
        "get_all",
        lambda channel=None: [{"topic": "old topic", "status": "pending"}],
    )
    monkeypatch.setattr(tag, "get_top_performing_topics", lambda limit=10, channel=None: [])
    monkeypatch.setattr(tag, "get_trending_topics", lambda count=10: [])
    monkeypatch.setattr(
        tag,
        "get_community_trend_titles",
        lambda limit=5: (_ for _ in ()).throw(RuntimeError("scrape fail")),
    )
    monkeypatch.setattr(
        tag,
        "generate_topics",
        lambda channel, existing, count=0, top_performers=None, **kwargs: ["fallback topic"],
    )
    added = []
    monkeypatch.setattr(tag, "add_topic", lambda topic, channel="", notes="": added.append(topic))

    with caplog.at_level("WARNING", logger="execution.topic_auto_generator"):
        result = tag.check_and_replenish(threshold=3, count=1, dry_run=False)

    assert result == {"space": ["fallback topic"]}
    assert "커뮤니티 트렌드 수집 실패" in caplog.text
