from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.draft_generator import (  # noqa: E402
    TweetDraftGenerator,
    classify_provider_failure,
    summarize_provider_failures,
)


class FakeConfig:
    def __init__(self, data):
        self.data = data

    def get(self, key, default=None):
        cur = self.data
        for part in key.split("."):
            if isinstance(cur, dict):
                cur = cur.get(part)
            else:
                return default
        return default if cur is None else cur


def _build_config():
    return FakeConfig(
        {
            "llm": {
                "providers": ["anthropic", "gemini", "xai", "openai"],
                "max_retries_per_provider": 1,
                "request_timeout_seconds": 5,
            },
            "anthropic": {"enabled": True, "api_key": "anthropic-key", "model": "claude-sonnet-4-6"},
            "gemini": {"enabled": True, "api_key": "gemini-key", "model": "gemini-2.5-flash"},
            "xai": {"enabled": True, "api_key": "xai-key", "model": "grok-4-1-fast-reasoning"},
            "openai": {"chat_enabled": True, "api_key": "openai-key", "chat_model": "gpt-4.1-mini"},
            "tweet_style": {"tone": "casual", "max_length": 280},
        }
    )


def _valid_twitter_payload(text: str) -> str:
    return (
        f"<twitter>{text}</twitter>"
        "<reply>원문: (링크)\n#연봉 #직장인</reply>"
        "<creator_take>숫자 하나로 직장인 비교 심리를 건드리는 글입니다.</creator_take>"
        "<image_prompt>prompt</image_prompt>"
    )


def test_generator_falls_back_to_next_provider(monkeypatch):
    generator = TweetDraftGenerator(_build_config())

    async def _fail(_prompt):
        raise RuntimeError("Your credit balance is too low to access the Anthropic API.")

    called = {"gemini": 0, "openai": 0}

    async def _gemini(prompt):
        del prompt
        called["gemini"] += 1
        return (
            _valid_twitter_payload(
                "연봉 280 찍고도 회의가 조용해지진 않더라. 3% 인상 버티기 vs 이직 준비, 지금 뭐가 현실적이세요?"
            ),
            10,
            20,
            0,
            0,
        )

    async def _openai(prompt):
        del prompt
        called["openai"] += 1
        return _valid_twitter_payload("openai fallback"), 1, 1, 0, 0

    monkeypatch.setattr(generator, "_generate_with_anthropic", _fail)
    monkeypatch.setattr(generator, "_generate_with_gemini", _gemini)
    monkeypatch.setattr(generator, "_generate_with_openai", _openai)

    drafts, image_prompt = asyncio.run(
        generator.generate_drafts(
            {
                "title": "연봉 280 찍고 회의가 조용해진 줄 알았는데",
                "content": "연봉과 이직 사이에서 흔들리는 직장인 공감 글",
                "content_profile": {"selection_summary": "직장인 비교 심리를 건드리는 연봉 글"},
            },
            output_formats=["twitter"],
        )
    )

    assert drafts["_provider_used"] == "gemini"
    assert "회의가 조용해지진 않더라" in drafts["twitter"]
    assert drafts["reply_text"].startswith("원문:")
    assert drafts["creator_take"]
    assert image_prompt == "prompt"
    assert called["gemini"] == 1
    assert called["openai"] == 0


def test_generator_returns_generation_failed_when_no_provider_enabled(monkeypatch):
    for key in (
        "ANTHROPIC_API_KEY",
        "GEMINI_API_KEY",
        "GOOGLE_API_KEY",
        "XAI_API_KEY",
        "GROK_API_KEY",
        "OPENAI_API_KEY",
    ):
        monkeypatch.delenv(key, raising=False)
    config = FakeConfig({"llm": {"providers": ["anthropic"]}, "tweet_style": {"max_length": 280}})
    generator = TweetDraftGenerator(config)
    drafts, image_prompt = asyncio.run(
        generator.generate_drafts(
            {"title": "제목", "content": "본문", "content_profile": {}}, output_formats=["twitter"]
        )
    )
    assert drafts["_generation_failed"] is True
    assert "No enabled LLM providers available" in drafts["_generation_error"]
    assert image_prompt is None


def test_classify_provider_failure_maps_operator_categories():
    rate_limit = classify_provider_failure(
        "gemini",
        "gemini-2.5-flash",
        RuntimeError("429 RESOURCE_EXHAUSTED: rate limit exceeded"),
        attempt=1,
        max_attempts=2,
        latency_ms=123.456,
    )
    auth = classify_provider_failure(
        "openai",
        "gpt-4.1-mini",
        RuntimeError("Invalid API key"),
        attempt=1,
        max_attempts=1,
        latency_ms=7,
    )
    overloaded = classify_provider_failure(
        "anthropic",
        "claude-sonnet-4-6",
        RuntimeError("529 overloaded_error: API is temporarily overloaded"),
        attempt=1,
        max_attempts=2,
        latency_ms=42,
    )

    assert rate_limit == {
        "provider": "gemini",
        "model": "gemini-2.5-flash",
        "attempt": 1,
        "max_attempts": 2,
        "category": "rate_limit",
        "retryable": True,
        "circuit_breaker_candidate": False,
        "latency_ms": 123.5,
        "error_preview": "429 RESOURCE_EXHAUSTED: rate limit exceeded",
        "operator_action_required": True,
        "operator_action": "Wait for provider rate-limit reset or reduce request volume before retrying.",
    }
    assert auth["category"] == "auth"
    assert auth["retryable"] is False
    assert auth["circuit_breaker_candidate"] is True
    assert auth["operator_action_required"] is True
    assert overloaded["category"] == "overloaded"
    assert overloaded["retryable"] is True
    assert overloaded["circuit_breaker_candidate"] is False
    assert "exponential backoff" in overloaded["operator_action"]


def test_generator_returns_structured_provider_failure_summary(monkeypatch):
    config = _build_config()
    config.data["llm"]["providers"] = ["gemini", "openai"]
    config.data["llm"]["max_retries_per_provider"] = 1
    generator = TweetDraftGenerator(config)

    async def _fake_generate_once(provider, prompt):
        del prompt
        if provider == "gemini":
            raise RuntimeError("429 RESOURCE_EXHAUSTED: rate limit exceeded")
        raise RuntimeError("Invalid API key")

    monkeypatch.setattr(generator, "_generate_once", _fake_generate_once)

    drafts, image_prompt = asyncio.run(
        generator.generate_drafts(
            {"title": "provider failure", "content": "provider failure content", "content_profile": {}},
            output_formats=["twitter"],
        )
    )

    assert image_prompt is None
    assert drafts["_generation_failed"] is True
    assert "All providers failed to generate candidate" in drafts["_generation_error"]
    failures = drafts["_provider_failures"]
    assert failures[0]["latency_ms"] >= 0.0
    assert failures[1]["latency_ms"] >= 0.0
    comparable_failures = [{**failure, "latency_ms": 0.0} for failure in failures]
    assert comparable_failures == [
        {
            "provider": "gemini",
            "model": "gemini-2.5-flash",
            "attempt": 1,
            "max_attempts": 1,
            "category": "rate_limit",
            "retryable": True,
            "circuit_breaker_candidate": False,
            "latency_ms": 0.0,
            "error_preview": "429 RESOURCE_EXHAUSTED: rate limit exceeded",
            "operator_action_required": True,
            "operator_action": "Wait for provider rate-limit reset or reduce request volume before retrying.",
        },
        {
            "provider": "openai",
            "model": "gpt-4.1-mini",
            "attempt": 1,
            "max_attempts": 1,
            "category": "auth",
            "retryable": False,
            "circuit_breaker_candidate": True,
            "latency_ms": 0.0,
            "error_preview": "Invalid API key",
            "operator_action_required": True,
            "operator_action": "Check provider API key, env wiring, and enabled flags before rerunning.",
        },
    ]
    summary = drafts["_provider_failure_summary"]
    assert summary["total_latency_ms"] >= 0.0
    assert summary["max_latency_ms"] >= 0.0
    comparable_summary = {**summary, "total_latency_ms": 0.0, "max_latency_ms": 0.0}
    assert comparable_summary == {
        "total_failures": 2,
        "providers_attempted": ["gemini", "openai"],
        "categories": {"auth": 1, "rate_limit": 1},
        "circuit_breaker_providers": ["openai"],
        "retryable_count": 1,
        "non_retryable_count": 1,
        "total_latency_ms": 0.0,
        "max_latency_ms": 0.0,
        "last_failure": {
            "provider": "openai",
            "model": "gpt-4.1-mini",
            "category": "auth",
            "retryable": False,
            "circuit_breaker_candidate": True,
            "error_preview": "Invalid API key",
            "operator_action": "Check provider API key, env wiring, and enabled flags before rerunning.",
        },
        "primary_failure": {
            "provider": "openai",
            "model": "gpt-4.1-mini",
            "category": "auth",
            "retryable": False,
            "circuit_breaker_candidate": True,
            "error_preview": "Invalid API key",
            "operator_action": "Check provider API key, env wiring, and enabled flags before rerunning.",
        },
        "operator_action_required": True,
        "primary_operator_action": "Check provider API key, env wiring, and enabled flags before rerunning.",
    }


def test_provider_failure_summary_prioritizes_repair_before_retry_wait():
    summary = summarize_provider_failures(
        [
            classify_provider_failure(
                "gemini",
                "gemini-2.5-flash",
                RuntimeError("429 RESOURCE_EXHAUSTED: rate limit exceeded"),
                attempt=1,
                max_attempts=1,
                latency_ms=20,
            ),
            classify_provider_failure(
                "openai",
                "gpt-4.1-mini",
                RuntimeError("401 invalid api key"),
                attempt=1,
                max_attempts=1,
                latency_ms=10,
            ),
            classify_provider_failure(
                "anthropic",
                "claude-sonnet-4-6",
                RuntimeError("529 overloaded_error: API is temporarily overloaded"),
                attempt=1,
                max_attempts=1,
                latency_ms=30,
            ),
        ]
    )

    assert summary["providers_attempted"] == ["gemini", "openai", "anthropic"]
    assert summary["categories"] == {"auth": 1, "overloaded": 1, "rate_limit": 1}
    assert summary["retryable_count"] == 2
    assert summary["non_retryable_count"] == 1
    assert summary["circuit_breaker_providers"] == ["openai"]
    assert summary["primary_failure"]["provider"] == "openai"
    assert summary["primary_failure"]["category"] == "auth"
    assert summary["primary_failure"]["retryable"] is False
    assert (
        summary["primary_operator_action"] == "Check provider API key, env wiring, and enabled flags before rerunning."
    )


def test_provider_failure_summary_parses_string_false_flags():
    summary = summarize_provider_failures(
        [
            {
                "provider": "gemini",
                "model": "gemini-test",
                "category": "provider_error",
                "retryable": "false",
                "circuit_breaker_candidate": "false",
                "latency_ms": 0,
                "error_preview": "manual fixture",
                "operator_action": "inspect",
            }
        ]
    )

    assert summary["retryable_count"] == 0
    assert summary["non_retryable_count"] == 1
    assert summary["circuit_breaker_providers"] == []
    assert summary["primary_failure"]["retryable"] is False
    assert summary["primary_failure"]["circuit_breaker_candidate"] is False


def test_generator_rejects_missing_tags_and_uses_next_provider(monkeypatch):
    config = _build_config()
    config.data["llm"]["providers"] = ["gemini", "openai"]
    generator = TweetDraftGenerator(config)

    async def _fake_generate_once(provider, prompt):
        del prompt
        if provider == "gemini":
            return "<twitter>reply tag missing</twitter>", 8, 4, 0, 0
        return (
            _valid_twitter_payload("연봉 300 찍고도 승진은 막혔더라. 버티기 vs 이직 준비, 어디에 더 마음이 가세요?"),
            6,
            3,
            0,
            0,
        )

    monkeypatch.setattr(generator, "_generate_once", _fake_generate_once)

    drafts, _image_prompt = asyncio.run(
        generator.generate_drafts(
            {"title": "연봉 3000 vs 이직", "content": "직장인 공감 본문", "content_profile": {}},
            output_formats=["twitter"],
        )
    )

    assert drafts["_provider_used"] == "openai"
    assert "연봉 300" in drafts["twitter"]


def test_generator_allows_missing_creator_take(monkeypatch):
    config = _build_config()
    config.data["llm"]["providers"] = ["gemini"]
    generator = TweetDraftGenerator(config)

    async def _fake_generate_once(provider, prompt):
        del provider, prompt
        return (
            "<twitter>연봉 280에서 흔들리는 마음, 버티기 vs 이직 중 뭐가 더 현실적일까요?</twitter>"
            "<reply>원문: (링크)</reply>",
            8,
            4,
            0,
            0,
        )

    monkeypatch.setattr(generator, "_generate_once", _fake_generate_once)

    drafts, _image_prompt = asyncio.run(
        generator.generate_drafts(
            {"title": "연봉 280", "content": "직장인 공감 본문", "content_profile": {}},
            output_formats=["twitter"],
        )
    )

    assert drafts["_provider_used"] == "gemini"
    assert "연봉 280" in drafts["twitter"]
    assert drafts["reply_text"].startswith("원문:")
    assert drafts.get("creator_take", "") == ""


def test_generator_accepts_json_payload_without_tags(monkeypatch):
    config = _build_config()
    config.data["llm"]["providers"] = ["gemini"]
    generator = TweetDraftGenerator(config)

    async def _fake_generate_once(provider, prompt):
        del provider, prompt
        return (
            '{"twitter": "연봉 협상에서 가장 먼저 확인할 숫자는 기준연봉입니다.", '
            '"reply": "원문: (링크)", '
            '"creator_take": "숫자 비교의 기준점을 먼저 잡아주는 글입니다."}',
            8,
            4,
            0,
            0,
        )

    monkeypatch.setattr(generator, "_generate_once", _fake_generate_once)

    drafts, _image_prompt = asyncio.run(
        generator.generate_drafts(
            {"title": "연봉 협상", "content": "직장인 공감 본문", "content_profile": {}},
            output_formats=["twitter"],
        )
    )

    assert drafts["_provider_used"] == "gemini"
    assert "기준연봉" in drafts["twitter"]
    assert drafts["reply_text"] == "원문: (링크)"
    assert "creator_take" in drafts


def test_generator_allows_partial_output_when_requested(monkeypatch):
    config = _build_config()
    config.data["llm"]["providers"] = ["gemini"]
    generator = TweetDraftGenerator(config)

    async def _fake_generate_once(provider, prompt):
        del provider, prompt
        return (
            "<twitter>연봉 협상에서 숫자 기준점부터 맞추는 게 핵심입니다.</twitter><reply>원문: (링크)</reply>",
            8,
            4,
            0,
            0,
        )

    monkeypatch.setattr(generator, "_generate_once", _fake_generate_once)

    drafts, _image_prompt = asyncio.run(
        generator.generate_drafts(
            {"title": "연봉 협상", "content": "직장인 공감 본문", "content_profile": {}},
            output_formats=["twitter", "threads", "naver_blog"],
            allow_partial=True,
        )
    )

    assert drafts["_provider_used"] == "gemini"
    assert "숫자 기준점" in drafts["twitter"]
    assert drafts["_missing_requested_formats"] == ["threads", "naver_blog"]


def test_call_llm_with_fallback_returns_requested_platform_text(monkeypatch):
    config = _build_config()
    config.data["llm"]["providers"] = ["gemini"]
    generator = TweetDraftGenerator(config)

    async def _fake_generate_once(provider, prompt):
        del provider, prompt
        return ("리트라이 이후에는 한 문단의 초안만 반환합니다.", 3, 2, 0, 0)

    monkeypatch.setattr(generator, "_generate_once", _fake_generate_once)

    draft_text = asyncio.run(generator._call_llm_with_fallback("retry prompt", platform="twitter"))

    assert "한 문단의 초안" in draft_text


def test_prompt_includes_editorial_brief():
    generator = TweetDraftGenerator(_build_config())
    prompt = generator._build_prompt(
        {
            "title": "연봉 280 찍고 회의가 조용해진 줄 알았는데",
            "content": "회의에서 연봉 280 이야기가 나왔고 다들 잠깐 조용해졌다.",
            "source": "blind",
            "content_profile": {
                "topic_cluster": "연봉",
                "recommended_draft_type": "공감형",
                "hook_type": "공감형",
                "emotion_axis": "현타",
                "audience_fit": "재직중 직장인",
                "publishability_score": 82,
                "performance_score": 61,
                "selection_summary": "직장인 박탈감과 비교 심리를 바로 건드리는 연봉 글",
                "audience_need": "내 급여와 비교하며 해석하고 싶음",
                "emotion_lane": "씁쓸하지만 공감",
                "empathy_anchor": "연봉 280",
                "spinoff_angle": "이직 전후 체감, 댓글 반응",
            },
        },
        top_examples=None,
        output_formats=["twitter"],
    )

    assert "직장인 박탈감과 비교 심리를 바로 건드리는 연봉 글" in prompt
    assert "씁쓸하지만 공감" in prompt
    assert "이직 전후 체감, 댓글 반응" in prompt
    # 새 톤(shorts 철학): selection_brief가 CTA 금지를 명시해야 함
    assert "여운이 남는 한 줄" in prompt
    assert "인플루언서 어휘" in prompt
    assert "아래 게시글을 기반으로 발행 가능한 초안을 작성하세요." in prompt.anthropic_system_prompt
    assert "[게시글 정보]" in prompt.anthropic_user_prompt
    assert "연봉 280 찍고 회의가 조용해진 줄 알았는데" in prompt.anthropic_user_prompt
    assert "연봉 280 찍고 회의가 조용해진 줄 알았는데" not in prompt.anthropic_system_prompt


def test_prompt_includes_research_context_in_user_prompt_only():
    generator = TweetDraftGenerator(_build_config())
    killer_sentence = "이건 편하게 일하자는 게 아니라 일과 삶의 경계를 지키자는 말입니다"
    prompt = generator._build_prompt(
        {
            "title": "팀장이 먼저 퇴근하라고 해놓고 평가에서 태도를 봤다",
            "content": "야근하지 않았다는 이유로 낮은 평가를 받았다는 사연입니다.",
            "source": "blind",
            "research_context": {
                "source_frame": "개인이 편하게 일하고 싶다는 문제",
                "real_issue": "일의 책임과 개인 시간의 경계",
                "universal_value": "경계 존중",
                "killer_sentence": killer_sentence,
                "closure": "open",
                "conflict_risk": 0.2,
                "anchor": "팀장이 먼저 퇴근하라고 해놓고",
            },
            "content_profile": {"topic_cluster": "직장문화"},
        },
        top_examples=None,
        output_formats=["twitter"],
    )

    assert "[오토리서치 컨텍스트 - 반드시 반영]" in prompt.anthropic_user_prompt
    assert killer_sentence in prompt.anthropic_user_prompt
    assert "가치 선언" in prompt.anthropic_user_prompt
    assert killer_sentence not in prompt.anthropic_system_prompt


def test_reviewer_memory_moves_to_anthropic_system_prompt():
    generator = TweetDraftGenerator(_build_config())
    prompt = generator._build_prompt(
        {
            "title": "회의가 갑자기 조용해진 이유",
            "content": "연봉 이야기가 나오자 모두가 말이 없어졌다.",
            "source": "blind",
            "content_profile": {"topic_cluster": "연봉"},
        },
        top_examples=[
            {
                "example_source": "reviewer_memory",
                "memory_label": "최근 패스 사유",
                "text": "원문에 없는 숫자를 만들지 말 것",
                "reason": "팩트 오류로 보류됨",
            }
        ],
        output_formats=["twitter"],
    )

    assert "원문에 없는 숫자를 만들지 말 것" in prompt
    assert "원문에 없는 숫자를 만들지 말 것" in prompt.anthropic_system_prompt
    assert "원문에 없는 숫자를 만들지 말 것" not in prompt.anthropic_user_prompt


def test_cache_generated_drafts_logs_debug_on_failure(caplog, monkeypatch):
    """BTX-DG001: cache write 실패 시 silent pass 대신 debug 로그를 남긴다."""
    import logging

    generator = TweetDraftGenerator(_build_config())

    def _raise(*_args, **_kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(generator.draft_cache, "set", _raise)
    with caplog.at_level(logging.DEBUG, logger="pipeline.draft_generator"):
        generator._cache_generated_drafts("key-x", {"_provider_used": "anthropic"}, None)

    assert any("disk full" in r.message for r in caplog.records), "Expected debug log for cache failure"


def test_get_available_providers_logs_debug_on_cost_db_failure(caplog, monkeypatch):
    """BTX-DG002: cost_db.get_skipped_providers 실패 시 silent pass 대신 debug 로그를 남긴다."""
    import logging

    generator = TweetDraftGenerator(_build_config())

    def _bad_import():
        raise RuntimeError("db unavailable")

    monkeypatch.setattr("pipeline.cost_db.get_cost_db", _bad_import, raising=False)

    with caplog.at_level(logging.DEBUG, logger="pipeline.draft_generator"):
        providers = generator._available_providers_after_recent_failures()

    assert isinstance(providers, list)
    assert any("cost_db" in r.message or "non-critical" in r.message for r in caplog.records)
