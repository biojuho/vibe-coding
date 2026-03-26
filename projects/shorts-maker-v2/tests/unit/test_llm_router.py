from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from shorts_maker_v2.providers.llm_router import LLMRouter

ALL_PROVIDERS = [
    "openai",
    "google",
    "anthropic",
    "xai",
    "deepseek",
    "moonshot",
    "zhipuai",
    "groq",
    "mimo",
]


def _make_router(*, providers: list[str] | None = None, max_retries: int = 2) -> LLMRouter:
    selected = providers or ALL_PROVIDERS
    router = LLMRouter(
        providers=selected,
        max_retries=max_retries,
        request_timeout_sec=5,
    )
    router.api_keys = {provider: f"{provider}-key" for provider in selected}
    return router


def _make_policy(
    *,
    mode: str = "enforce",
    fallback_providers: tuple[str, ...] = ("openai",),
    repair_attempts: int = 1,
) -> SimpleNamespace:
    return SimpleNamespace(
        mode=mode,
        fallback_providers=fallback_providers,
        repair_attempts=repair_attempts,
    )


def _validation(
    *,
    passed: bool = False,
    is_empty: bool = False,
    json_valid: bool = False,
    reason_codes: tuple[str, ...] = ("policy",),
) -> SimpleNamespace:
    return SimpleNamespace(
        passed=passed,
        is_empty=is_empty,
        json_valid=json_valid,
        reason_codes=list(reason_codes),
    )


def _make_bridge(
    *,
    text_validations: list[SimpleNamespace],
    json_validations: list[SimpleNamespace] | None = None,
    normalized_payload=None,  # noqa: ANN001
):
    text_iter = iter(text_validations)
    json_iter = iter(json_validations or [])

    def build_repair_messages(**kwargs):  # noqa: ANN003
        del kwargs
        return ("repair-system", "repair-user")

    return {
        "BridgePolicy": SimpleNamespace,
        "preferred_provider_order": lambda providers, policy: list(providers),
        "build_bridge_system_prompt": lambda system_prompt, policy, json_mode: f"bridge::{json_mode}:{system_prompt}",
        "build_repair_messages": build_repair_messages,
        "normalize_json_payload": normalized_payload or (lambda payload: payload),
        "normalize_prompt_text": lambda user_prompt, json_mode: f"user::{json_mode}:{user_prompt}",
        "validate_json_payload": lambda payload, policy: next(json_iter),
        "validate_text_content": lambda content, policy, json_mode: next(text_iter),
    }


def test_normalize_providers_deduplicates_aliases_and_defaults() -> None:
    assert LLMRouter._normalize_providers([" GPT ", "chatgpt", "gemini", "google", "unknown"]) == [
        "openai",
        "google",
    ]
    assert LLMRouter._normalize_providers(["", "???"]) == ["openai"]


def test_enabled_providers_and_enabled_from_order_filter_to_keys() -> None:
    router = _make_router(providers=["openai", "google", "anthropic"])
    router.api_keys = {
        "openai": "",
        "google": "google-key",
        "anthropic": None,
    }

    assert router.enabled_providers() == ["google"]
    assert router._enabled_from_order(["claude", "gemini", "chatgpt", "unknown"]) == ["google"]


def test_clean_json_and_parse_json_response_strip_fences() -> None:
    router = _make_router(providers=["openai"])

    fenced = '```json\n{"ok": true}\n```'

    assert router._clean_json(fenced) == '{"ok": true}'
    assert router._parse_json_response(fenced) == {"ok": True}


def test_generate_json_reaches_ninth_provider_after_eight_failures() -> None:
    router = _make_router(max_retries=1)
    calls: list[str] = []

    def fake_generate_once(  # noqa: ANN001
        provider,
        system_prompt,
        user_prompt,
        temperature,
        *,
        json_mode,
        thinking_level=None,
    ):
        del system_prompt, user_prompt, temperature, json_mode, thinking_level
        calls.append(provider)
        if provider != "mimo":
            raise RuntimeError(f"{provider} temporary outage")
        return '{"provider":"mimo","ok":true}'

    router._generate_once = fake_generate_once  # type: ignore[method-assign]

    with patch("shorts_maker_v2.providers.llm_router.time.sleep") as sleep_mock:
        result = router.generate_json(system_prompt="system", user_prompt="user")

    assert result == {"provider": "mimo", "ok": True}
    assert calls == ALL_PROVIDERS
    sleep_mock.assert_not_called()


def test_generate_json_retries_timeout_before_fallback() -> None:
    router = _make_router(providers=["openai", "google"], max_retries=2)
    calls: list[str] = []

    def fake_generate_once(  # noqa: ANN001
        provider,
        system_prompt,
        user_prompt,
        temperature,
        *,
        json_mode,
        thinking_level=None,
    ):
        del system_prompt, user_prompt, temperature, json_mode, thinking_level
        calls.append(provider)
        if provider == "openai":
            raise TimeoutError("request timed out")
        return '{"provider":"google","ok":true}'

    router._generate_once = fake_generate_once  # type: ignore[method-assign]

    with patch("shorts_maker_v2.providers.llm_router.time.sleep") as sleep_mock:
        result = router.generate_json(system_prompt="system", user_prompt="user")

    assert result == {"provider": "google", "ok": True}
    assert calls == ["openai", "openai", "google"]
    sleep_mock.assert_called_once_with(2)


def test_generate_json_skips_remaining_retries_on_non_retryable_error() -> None:
    router = _make_router(providers=["openai", "google"], max_retries=3)
    calls: list[str] = []

    def fake_generate_once(  # noqa: ANN001
        provider,
        system_prompt,
        user_prompt,
        temperature,
        *,
        json_mode,
        thinking_level=None,
    ):
        del system_prompt, user_prompt, temperature, json_mode, thinking_level
        calls.append(provider)
        if provider == "openai":
            raise RuntimeError("invalid_api_key")
        return '{"provider":"google","ok":true}'

    router._generate_once = fake_generate_once  # type: ignore[method-assign]

    with patch("shorts_maker_v2.providers.llm_router.time.sleep") as sleep_mock:
        result = router.generate_json(system_prompt="system", user_prompt="user")

    assert result == {"provider": "google", "ok": True}
    assert calls == ["openai", "google"]
    sleep_mock.assert_not_called()


def test_generate_json_retries_json_parse_error_then_falls_back() -> None:
    router = _make_router(providers=["openai", "google"], max_retries=2)
    calls: list[str] = []

    def fake_generate_once(  # noqa: ANN001
        provider,
        system_prompt,
        user_prompt,
        temperature,
        *,
        json_mode,
        thinking_level=None,
    ):
        del system_prompt, user_prompt, temperature, json_mode, thinking_level
        calls.append(provider)
        if provider == "openai":
            return "not-json"
        return '{"provider":"google","ok":true}'

    router._generate_once = fake_generate_once  # type: ignore[method-assign]

    with patch("shorts_maker_v2.providers.llm_router.time.sleep") as sleep_mock:
        result = router.generate_json(system_prompt="system", user_prompt="user")

    assert result == {"provider": "google", "ok": True}
    assert calls == ["openai", "openai", "google"]
    sleep_mock.assert_called_once_with(2)


def test_generate_text_retries_before_fallback() -> None:
    router = _make_router(providers=["openai", "google"], max_retries=2)
    calls: list[str] = []

    def fake_generate_once(  # noqa: ANN001
        provider,
        system_prompt,
        user_prompt,
        temperature,
        *,
        json_mode,
        thinking_level=None,
    ):
        del system_prompt, user_prompt, temperature, json_mode, thinking_level
        calls.append(provider)
        if provider == "openai":
            raise TimeoutError("request timed out")
        return "google text"

    router._generate_once = fake_generate_once  # type: ignore[method-assign]

    with patch("shorts_maker_v2.providers.llm_router.time.sleep") as sleep_mock:
        result = router.generate_text(system_prompt="system", user_prompt="user")

    assert result == "google text"
    assert calls == ["openai", "openai", "google"]
    sleep_mock.assert_called_once_with(2)


def test_generate_text_raises_when_no_provider_is_enabled() -> None:
    router = _make_router(providers=["openai"])
    router.api_keys = {"openai": None}

    with pytest.raises(RuntimeError, match="No LLM providers available"):
        router.generate_text(system_prompt="system", user_prompt="user")


def test_generate_text_bridged_mode_off_delegates_to_plain_text_path() -> None:
    router = _make_router(providers=["openai"])
    policy = _make_policy(mode="off")
    bridge = _make_bridge(text_validations=[_validation(passed=True)])

    with (
        patch("shorts_maker_v2.providers.llm_router._get_bridge", return_value=bridge),
        patch.object(router, "generate_text", return_value="plain text") as generate_text_mock,
    ):
        result = router.generate_text_bridged(
            system_prompt="system",
            user_prompt="user",
            temperature=0.4,
            policy=policy,
        )

    assert result == "plain text"
    generate_text_mock.assert_called_once_with(
        system_prompt="system",
        user_prompt="user",
        temperature=0.4,
    )


def test_generate_text_bridged_repairs_invalid_response() -> None:
    router = _make_router(providers=["openai"], max_retries=1)
    policy = _make_policy(mode="enforce", fallback_providers=("openai",), repair_attempts=1)
    bridge = _make_bridge(
        text_validations=[
            _validation(passed=False, is_empty=False, reason_codes=("policy",)),
            _validation(passed=True),
        ]
    )
    calls: list[tuple[str, str, str, float, bool]] = []
    responses = iter(["draft answer", "fixed answer"])

    def fake_generate_once(  # noqa: ANN001
        provider,
        system_prompt,
        user_prompt,
        temperature,
        *,
        json_mode,
        thinking_level=None,
    ):
        del thinking_level
        calls.append((provider, system_prompt, user_prompt, temperature, json_mode))
        return next(responses)

    router._generate_once = fake_generate_once  # type: ignore[method-assign]

    with patch("shorts_maker_v2.providers.llm_router._get_bridge", return_value=bridge):
        result = router.generate_text_bridged(
            system_prompt="system",
            user_prompt="user",
            temperature=0.7,
            policy=policy,
        )

    assert result == "fixed answer"
    assert calls == [
        ("openai", "bridge::False:system", "user::False:user", 0.7, False),
        ("openai", "repair-system", "repair-user", 0.2, False),
    ]


def test_generate_text_bridged_shadow_returns_non_empty_warning_content() -> None:
    router = _make_router(providers=["openai"], max_retries=1)
    policy = _make_policy(mode="shadow", fallback_providers=("openai",), repair_attempts=1)
    bridge = _make_bridge(text_validations=[_validation(passed=False, is_empty=False, reason_codes=("style",))])

    router._generate_once = lambda *args, **kwargs: "shadow text"  # type: ignore[assignment]

    with patch("shorts_maker_v2.providers.llm_router._get_bridge", return_value=bridge):
        result = router.generate_text_bridged(
            system_prompt="system",
            user_prompt="user",
            policy=policy,
        )

    assert result == "shadow text"


def test_generate_json_bridged_mode_off_delegates_to_plain_json_path() -> None:
    router = _make_router(providers=["openai"])
    policy = _make_policy(mode="off")
    bridge = _make_bridge(
        text_validations=[_validation(json_valid=True)],
        json_validations=[_validation(passed=True)],
    )

    with (
        patch("shorts_maker_v2.providers.llm_router._get_bridge", return_value=bridge),
        patch.object(router, "generate_json", return_value={"ok": True}) as generate_json_mock,
    ):
        result = router.generate_json_bridged(
            system_prompt="system",
            user_prompt="user",
            temperature=0.4,
            policy=policy,
        )

    assert result == {"ok": True}
    generate_json_mock.assert_called_once_with(
        system_prompt="system",
        user_prompt="user",
        temperature=0.4,
    )


def test_generate_json_bridged_normalizes_valid_payload() -> None:
    router = _make_router(providers=["openai"], max_retries=1)
    policy = _make_policy(mode="enforce", fallback_providers=("openai",), repair_attempts=1)
    bridge = _make_bridge(
        text_validations=[_validation(json_valid=True)],
        json_validations=[_validation(passed=True)],
        normalized_payload=lambda payload: {**payload, "normalized": True},
    )

    router._generate_once = lambda *args, **kwargs: '```json\n{"ok": true}\n```'  # type: ignore[assignment]

    with patch("shorts_maker_v2.providers.llm_router._get_bridge", return_value=bridge):
        result = router.generate_json_bridged(
            system_prompt="system",
            user_prompt="user",
            policy=policy,
        )

    assert result == {"ok": True, "normalized": True}


def test_generate_json_bridged_repairs_after_payload_validation_failure() -> None:
    router = _make_router(providers=["openai"], max_retries=1)
    policy = _make_policy(mode="enforce", fallback_providers=("openai",), repair_attempts=1)
    bridge = _make_bridge(
        text_validations=[
            _validation(json_valid=True),
            _validation(json_valid=True),
        ],
        json_validations=[
            _validation(passed=False, reason_codes=("shape",)),
            _validation(passed=True),
        ],
    )
    calls: list[tuple[str, str, str, float, bool]] = []
    responses = iter(['{"draft": true}', '{"fixed": true}'])

    def fake_generate_once(  # noqa: ANN001
        provider,
        system_prompt,
        user_prompt,
        temperature,
        *,
        json_mode,
        thinking_level=None,
    ):
        del thinking_level
        calls.append((provider, system_prompt, user_prompt, temperature, json_mode))
        return next(responses)

    router._generate_once = fake_generate_once  # type: ignore[method-assign]

    with patch("shorts_maker_v2.providers.llm_router._get_bridge", return_value=bridge):
        result = router.generate_json_bridged(
            system_prompt="system",
            user_prompt="user",
            policy=policy,
        )

    assert result == {"fixed": True}
    assert calls == [
        ("openai", "bridge::True:system", "user::True:user", 0.7, True),
        ("openai", "repair-system", "repair-user", 0.2, True),
    ]


def test_get_client_initializes_providers_correctly() -> None:
    router = _make_router(providers=["google", "anthropic", "deepseek", "openai"])
    router.api_keys = {"google": "g-key", "anthropic": "a-key", "deepseek": "d-key", "openai": "o-key"}

    with (
        patch("google.genai.Client") as mock_genai,
        patch("anthropic.Anthropic") as mock_anthropic,
        patch("openai.OpenAI") as mock_openai,
    ):
        mock_genai.return_value = "google_client"
        mock_anthropic.return_value = "anthropic_client"
        mock_openai.side_effect = ["deepseek_client", "openai_client"]

        assert router._get_client("google") == "google_client"
        mock_genai.assert_called_once_with(api_key="g-key")

        assert router._get_client("anthropic") == "anthropic_client"
        mock_anthropic.assert_called_once_with(api_key="a-key")

        assert router._get_client("deepseek") == "deepseek_client"
        mock_openai.assert_any_call(api_key="d-key", base_url="https://api.deepseek.com", timeout=5)

        assert router._get_client("openai") == "openai_client"
        mock_openai.assert_any_call(api_key="o-key", timeout=5)

        # Test Unknown provider
        with pytest.raises(ValueError, match="Unknown provider"):
            router.api_keys["unknown"] = "key"
            router._get_client("unknown")


def test_generate_once_dispatches_to_correct_impl() -> None:
    router = _make_router(providers=["openai", "google", "anthropic"])

    # Fake clients
    def _openai_create(**kw):
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="openai-res"))])

    fake_openai = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=_openai_create)))

    class FakeGeminiResp:
        text = "google-res"

    fake_google = SimpleNamespace(models=SimpleNamespace(generate_content=lambda **kw: FakeGeminiResp()))

    fake_anthropic = SimpleNamespace(
        messages=SimpleNamespace(create=lambda **kw: SimpleNamespace(content=[SimpleNamespace(text="anthropic-res")]))
    )

    def fake_get_client(provider):
        if provider == "openai":
            return fake_openai
        if provider == "google":
            return fake_google
        if provider == "anthropic":
            return fake_anthropic

    router._get_client = fake_get_client

    res_openai = router._generate_once("openai", "sys", "user", 0.5, True)
    assert res_openai == "openai-res"

    # Mock google.genai types for google test
    with patch("google.genai.types") as mock_types:
        mock_types.GenerateContentConfig.return_value = object()
        mock_types.ThinkingConfig.return_value = object()
        res_google = router._generate_once("google", "sys", "user", 0.5, True, thinking_level="high")
        assert res_google == "google-res"

    res_anthropic = router._generate_once("anthropic", "sys", "user", 0.5, False)
    assert res_anthropic == "anthropic-res"

    with pytest.raises(ValueError, match="Unsupported provider"):
        router._generate_once("unknown", "sys", "user", 0.5, False)
