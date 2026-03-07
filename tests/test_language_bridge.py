from __future__ import annotations

from execution.language_bridge import (
    BridgePolicy,
    normalize_text,
    validate_json_payload,
    validate_text_content,
)


def test_normalize_text_uses_nfc() -> None:
    decomposed = "\u1112\u1161\u11ab\u1100\u1173\u11af"
    assert normalize_text(decomposed) == "한글"


def test_validate_text_detects_mixed_language() -> None:
    policy = BridgePolicy(mode="enforce")

    result = validate_text_content("이 문장은 中文 이 섞여 있습니다.", policy=policy)

    assert not result.passed
    assert "mixed_language" in result.reason_codes


def test_validate_text_allows_whitelisted_terms() -> None:
    strict_policy = BridgePolicy(mode="enforce")
    whitelisted_policy = BridgePolicy(mode="enforce", allowed_terms=("淘宝",))
    text = "한국 사용자가 보는 브랜드명 淘宝 리뷰입니다."

    strict_result = validate_text_content(text, policy=strict_policy)
    whitelisted_result = validate_text_content(text, policy=whitelisted_policy)

    assert "mixed_language" in strict_result.reason_codes
    assert whitelisted_result.passed


def test_validate_text_detects_mojibake() -> None:
    policy = BridgePolicy(mode="enforce")

    result = validate_text_content("ì•ˆë…•í•˜ì„¸ìš”", policy=policy)

    assert not result.passed
    assert result.has_mojibake is True
    assert "mojibake" in result.reason_codes


def test_validate_json_payload_checks_string_values() -> None:
    policy = BridgePolicy(mode="enforce")
    payload = {"topics": ["한국어 제목", "中文 제목"]}

    result = validate_json_payload(payload, policy=policy)

    assert not result.passed
    assert "mixed_language" in result.reason_codes


def test_bridge_policy_from_env_reads_thresholds(monkeypatch) -> None:
    monkeypatch.setenv("LLM_BRIDGE_MODE", "enforce")
    monkeypatch.setenv("LLM_BRIDGE_REPAIR_ATTEMPTS", "3")
    monkeypatch.setenv("LLM_BRIDGE_MIN_HANGUL_RATIO", "0.6")
    monkeypatch.setenv("LLM_BRIDGE_MAX_CJK_RATIO", "0.1")
    monkeypatch.setenv("LLM_BRIDGE_MAX_JAMO_RATIO", "0.2")
    monkeypatch.setenv("LLM_BRIDGE_STRICT_KOREAN", "false")
    monkeypatch.setenv("LLM_BRIDGE_ENFORCE_JSON_SCHEMA", "false")
    monkeypatch.setenv("LLM_BRIDGE_JSON_KEY_EXEMPTIONS", "title,url")

    policy = BridgePolicy.from_env()

    assert policy.mode == "enforce"
    assert policy.repair_attempts == 3
    assert policy.min_hangul_ratio == 0.6
    assert policy.max_cjk_ratio == 0.1
    assert policy.max_jamo_ratio == 0.2
    assert policy.strict_korean is False
    assert policy.enforce_json_schema is False
    assert policy.json_key_exemptions == ("title", "url")
