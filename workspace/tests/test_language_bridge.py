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


# ---------------------------------------------------------------------------
# BridgePolicy.from_env — invalid mode defaults to "shadow" (line 65)
# ---------------------------------------------------------------------------


def test_bridge_policy_from_env_invalid_mode(monkeypatch) -> None:
    monkeypatch.setenv("LLM_BRIDGE_MODE", "invalid_mode")
    policy = BridgePolicy.from_env()
    assert policy.mode == "shadow"


# ---------------------------------------------------------------------------
# as_dict (line 81)
# ---------------------------------------------------------------------------


def test_bridge_policy_as_dict() -> None:
    policy = BridgePolicy(mode="enforce", allowed_terms=("test",))
    d = policy.as_dict()
    assert d["mode"] == "enforce"
    assert d["allowed_terms"] == ["test"]
    assert d["target_language"] == "ko-KR"
    assert isinstance(d["fallback_providers"], list)
    assert isinstance(d["min_hangul_ratio"], float)
    assert isinstance(d["json_key_exemptions"], list)


# ---------------------------------------------------------------------------
# build_repair_messages — non-json mode instruction (line 181)
# ---------------------------------------------------------------------------


def test_build_repair_messages_non_json_mode() -> None:
    from execution.language_bridge import build_repair_messages, BridgeValidationResult

    validation = BridgeValidationResult(
        passed=False,
        reason_codes=("low_hangul_ratio",),
        hangul_ratio=0.3,
        cjk_ratio=0.0,
        has_mojibake=False,
        is_empty=False,
        json_valid=True,
        jamo_ratio=0.0,
        language_score=0.3,
        dominant_language="mixed",
    )
    policy = BridgePolicy(mode="enforce")
    sys_prompt, user_prompt = build_repair_messages(
        original_system_prompt="test system",
        original_user_prompt="test user",
        raw_content="some mixed content",
        validation=validation,
        policy=policy,
        json_mode=False,
    )
    assert "최종 텍스트만 반환" in user_prompt
    assert "JSON" not in user_prompt.split("[수정 지시]")[-1] or "JSON" not in user_prompt


# ---------------------------------------------------------------------------
# validate_text_content — mojibake detection (line 212)
# ---------------------------------------------------------------------------


def test_validate_text_detects_replacement_char() -> None:
    """U+FFFD replacement character triggers mojibake."""
    policy = BridgePolicy(mode="enforce")
    result = validate_text_content("정상 텍스트 \ufffd 깨짐", policy=policy)
    assert result.has_mojibake is True
    assert "mojibake" in result.reason_codes


# ---------------------------------------------------------------------------
# validate_text_content — decomposed_jamo detection (line 220)
# ---------------------------------------------------------------------------


def test_validate_text_detects_decomposed_jamo() -> None:
    policy = BridgePolicy(mode="enforce", strict_korean=False, max_jamo_ratio=0.01)
    # Compatibility jamo (U+3130-U+318F) remain as jamo even after NFC
    jamo_text = "\u3131\u3134\u3137\u3139\u3141\u3142\u3145\u3147\u3148\u314a\u314b\u314c\u314d\u314e"
    result = validate_text_content(jamo_text, policy=policy)
    assert "decomposed_jamo" in result.reason_codes


# ---------------------------------------------------------------------------
# validate_json_payload — json string validation paths (lines 250, 264)
# ---------------------------------------------------------------------------


def test_validate_json_payload_non_dict_schema_mismatch() -> None:
    """enforce_json_schema=True + non-dict payload → json_schema_mismatch."""
    policy = BridgePolicy(mode="enforce", enforce_json_schema=True)
    result = validate_json_payload("plain string", policy=policy)
    assert not result.passed
    assert "json_schema_mismatch" in result.reason_codes


def test_validate_json_payload_empty_strings() -> None:
    """No string values → passes with ratio 1.0."""
    policy = BridgePolicy(mode="enforce")
    result = validate_json_payload({"count": 42, "flag": True}, policy=policy)
    assert result.passed
    assert result.hangul_ratio == 1.0


# ---------------------------------------------------------------------------
# normalize_json_payload — tuple and dict normalization (lines 318, 321)
# ---------------------------------------------------------------------------


def test_normalize_json_payload_tuple() -> None:
    from execution.language_bridge import normalize_json_payload

    decomposed = "\u1112\u1161\u11ab\u1100\u1173\u11af"
    result = normalize_json_payload((decomposed, "plain"))
    assert isinstance(result, tuple)
    assert result[0] == "한글"
    assert result[1] == "plain"


def test_normalize_json_payload_dict() -> None:
    from execution.language_bridge import normalize_json_payload

    decomposed = "\u1112\u1161\u11ab\u1100\u1173\u11af"
    result = normalize_json_payload({"key": decomposed})
    assert isinstance(result, dict)
    assert result["key"] == "한글"


def test_normalize_json_payload_non_string() -> None:
    from execution.language_bridge import normalize_json_payload

    assert normalize_json_payload(42) == 42
    assert normalize_json_payload(None) is None


# ---------------------------------------------------------------------------
# _dominant_language — zh path (line 365)
# ---------------------------------------------------------------------------


def test_dominant_language_zh() -> None:
    from execution.language_bridge import _dominant_language

    assert _dominant_language(hangul_ratio=0.1, cjk_ratio=0.5) == "zh"


def test_dominant_language_mixed() -> None:
    from execution.language_bridge import _dominant_language

    assert _dominant_language(hangul_ratio=0.3, cjk_ratio=0.1) == "mixed"


# ---------------------------------------------------------------------------
# _env_float / _env_int / _env_bool — invalid and edge values
# ---------------------------------------------------------------------------


def test_env_float_invalid(monkeypatch) -> None:
    from execution.language_bridge import _env_float

    monkeypatch.setenv("TEST_FLOAT_VAR", "not_a_number")
    assert _env_float("TEST_FLOAT_VAR", 0.5) == 0.5


def test_env_float_empty(monkeypatch) -> None:
    from execution.language_bridge import _env_float

    monkeypatch.delenv("TEST_FLOAT_VAR", raising=False)
    assert _env_float("TEST_FLOAT_VAR", 0.75) == 0.75


def test_env_int_invalid(monkeypatch) -> None:
    from execution.language_bridge import _env_int

    monkeypatch.setenv("TEST_INT_VAR", "abc")
    assert _env_int("TEST_INT_VAR", 10) == 10


def test_env_int_empty(monkeypatch) -> None:
    from execution.language_bridge import _env_int

    monkeypatch.delenv("TEST_INT_VAR", raising=False)
    assert _env_int("TEST_INT_VAR", 5) == 5


def test_env_bool_true_values(monkeypatch) -> None:
    from execution.language_bridge import _env_bool

    for val in ("1", "true", "yes", "on"):
        monkeypatch.setenv("TEST_BOOL_VAR", val)
        assert _env_bool("TEST_BOOL_VAR", False) is True


def test_env_bool_false_values(monkeypatch) -> None:
    from execution.language_bridge import _env_bool

    for val in ("0", "false", "no", "off"):
        monkeypatch.setenv("TEST_BOOL_VAR", val)
        assert _env_bool("TEST_BOOL_VAR", True) is False


def test_env_bool_invalid_returns_default(monkeypatch) -> None:
    from execution.language_bridge import _env_bool

    monkeypatch.setenv("TEST_BOOL_VAR", "maybe")
    assert _env_bool("TEST_BOOL_VAR", True) is True
    assert _env_bool("TEST_BOOL_VAR", False) is False


def test_env_bool_empty_returns_default(monkeypatch) -> None:
    from execution.language_bridge import _env_bool

    monkeypatch.delenv("TEST_BOOL_VAR", raising=False)
    assert _env_bool("TEST_BOOL_VAR", True) is True


# ---------------------------------------------------------------------------
# validate_text_content: empty content → empty_content reason (line 212)
# ---------------------------------------------------------------------------


def test_validate_text_content_empty() -> None:
    from execution.language_bridge import BridgePolicy, validate_text_content

    policy = BridgePolicy(mode="enforce")
    result = validate_text_content("", policy=policy, json_mode=False)
    assert not result.passed
    assert "empty_content" in result.reason_codes


def test_validate_text_content_whitespace_only() -> None:
    from execution.language_bridge import BridgePolicy, validate_text_content

    policy = BridgePolicy(mode="enforce")
    result = validate_text_content("   \n\t  ", policy=policy, json_mode=False)
    assert "empty_content" in result.reason_codes
