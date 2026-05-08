from __future__ import annotations

import sys
from pathlib import Path

from execution.language_bridge import BridgePolicy
from execution.llm_client import LLMClient

ROOT = Path(__file__).resolve().parents[1]
SHORTS_SRC = ROOT.parent / "projects" / "shorts-maker-v2" / "src"
if str(SHORTS_SRC) not in sys.path:
    sys.path.insert(0, str(SHORTS_SRC))

from shorts_maker_v2.providers.llm_router import LLMRouter  # noqa: E402


def _fake_api_keys() -> dict[str, str]:
    return {
        "openai": "key",
        "google": "key",
        "anthropic": "",
        "xai": "",
        "deepseek": "key",
        "moonshot": "",
        "zhipuai": "",
    }


def test_llm_client_generate_json_bridged_repairs_invalid_language(monkeypatch) -> None:
    client = LLMClient(
        providers=["deepseek", "google", "openai"],
        track_usage=False,
        caller_script="test_bridge",
    )
    client.api_keys = _fake_api_keys()

    responses = iter(
        [
            ('{"topics":["中文 제목"]}', 11, 4, 0, 0),
            ('{"topics":["한국어 제목"]}', 7, 3, 0, 0),
        ]
    )

    def fake_generate_once(provider, system_prompt, user_prompt, temperature, json_mode):
        del system_prompt, user_prompt, temperature, json_mode
        assert provider == "deepseek"
        return next(responses)

    monkeypatch.setattr(client, "_generate_once", fake_generate_once)

    result = client.generate_json_bridged(
        system_prompt="JSON만 반환하세요.",
        user_prompt="한국어 주제 1개 생성",
        policy=BridgePolicy(mode="enforce", repair_attempts=1),
    )

    assert result == {"topics": ["한국어 제목"]}


def test_llm_client_generate_json_bridged_falls_back_after_invalid_json(monkeypatch) -> None:
    client = LLMClient(
        providers=["deepseek", "google", "openai"],
        track_usage=False,
        caller_script="test_bridge",
    )
    client.api_keys = _fake_api_keys()

    calls = []
    responses = {
        "deepseek": [("not json at all", 5, 2, 0, 0), ("still not json", 4, 2, 0, 0)],
        "google": [('{"topics":["한국어 주제"]}', 6, 2, 0, 0)],
    }

    def fake_generate_once(provider, system_prompt, user_prompt, temperature, json_mode):
        del system_prompt, user_prompt, temperature, json_mode
        calls.append(provider)
        return responses[provider].pop(0)

    monkeypatch.setattr(client, "_generate_once", fake_generate_once)

    result = client.generate_json_bridged(
        system_prompt="JSON만 반환하세요.",
        user_prompt="한국어 주제 1개 생성",
        policy=BridgePolicy(mode="enforce", repair_attempts=1),
    )

    assert result == {"topics": ["한국어 주제"]}
    assert calls == ["deepseek", "deepseek", "google"]


def test_llm_router_generate_text_bridged_returns_shadow_result(monkeypatch) -> None:
    router = LLMRouter(providers=["deepseek", "google", "openai"])
    router.api_keys = _fake_api_keys()

    def fake_generate_once(provider, system_prompt, user_prompt, temperature, json_mode):
        del provider, system_prompt, user_prompt, temperature, json_mode
        return "中文 문장이 조금 섞인 결과"

    monkeypatch.setattr(router, "_generate_once", fake_generate_once)

    result = router.generate_text_bridged(
        system_prompt="한국어로 답하세요.",
        user_prompt="요약해줘",
        policy=BridgePolicy(mode="shadow"),
    )

    assert result == "中文 문장이 조금 섞인 결과"


def test_llm_router_generate_json_bridged_repairs_response(monkeypatch) -> None:
    router = LLMRouter(providers=["deepseek", "google", "openai"])
    router.api_keys = _fake_api_keys()
    responses = iter(
        [
            '{"topics":["中文 제목"]}',
            '{"topics":["한국어 제목"]}',
        ]
    )

    def fake_generate_once(provider, system_prompt, user_prompt, temperature, json_mode):
        del provider, system_prompt, user_prompt, temperature, json_mode
        return next(responses)

    monkeypatch.setattr(router, "_generate_once", fake_generate_once)

    result = router.generate_json_bridged(
        system_prompt="JSON만 반환하세요.",
        user_prompt="한국어 주제 1개 생성",
        policy=BridgePolicy(mode="enforce", repair_attempts=1),
    )

    assert result == {"topics": ["한국어 제목"]}
