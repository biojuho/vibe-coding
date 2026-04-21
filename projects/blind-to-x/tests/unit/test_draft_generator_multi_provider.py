from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.draft_generator import TweetDraftGenerator  # noqa: E402


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
            "anthropic": {"enabled": True, "api_key": "anthropic-key", "model": "claude-sonnet-4-20250514"},
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
        )

    async def _openai(prompt):
        del prompt
        called["openai"] += 1
        return _valid_twitter_payload("openai fallback"), 1, 1

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


def test_generator_rejects_missing_tags_and_uses_next_provider(monkeypatch):
    config = _build_config()
    config.data["llm"]["providers"] = ["gemini", "openai"]
    generator = TweetDraftGenerator(config)

    async def _fake_generate_once(provider, prompt):
        del prompt
        if provider == "gemini":
            return "<twitter>reply tag missing</twitter>", 8, 4
        return (
            _valid_twitter_payload("연봉 300 찍고도 승진은 막혔더라. 버티기 vs 이직 준비, 어디에 더 마음이 가세요?"),
            6,
            3,
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
        return ("리트라이 이후에는 한 문단의 초안만 반환합니다.", 3, 2)

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
    assert "generic CTA" in prompt
