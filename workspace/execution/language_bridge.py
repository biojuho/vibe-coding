from __future__ import annotations

import io
import json
import os
import re
import sys
import unicodedata
from dataclasses import dataclass
from typing import Any, Iterable


_HANGUL_RE = re.compile(r"[가-힣]")
_CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
_JAMO_RE = re.compile(r"[\u1100-\u11ff\u3130-\u318f\ua960-\ua97f\ud7b0-\ud7ff]")
_VISIBLE_CHAR_RE = re.compile(r"\S")
_MOJIBAKE_RE = re.compile(
    r"(Ã.|Â.|ðŸ|ì[^\s]{1,2}ë[^\s]{1,2}|ì[^\s]{1,2}ê[^\s]{1,2}|"
    r"ì[^\s]{1,2}í[^\s]{1,2}|ì[^\s]{1,2}ì[^\s]{1,2})"
)


def ensure_utf8_stdio() -> None:
    """Wrap stdout/stderr in UTF-8 on Windows-style terminals when needed."""
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


def normalize_text(text: str) -> str:
    return unicodedata.normalize("NFC", text or "")


@dataclass(frozen=True)
class BridgePolicy:
    target_language: str = "ko-KR"
    mode: str = "shadow"
    allowed_terms: tuple[str, ...] = ()
    repair_attempts: int = 1
    fallback_providers: tuple[str, ...] = ("deepseek", "google", "openai")
    enforce_json_schema: bool = True
    strict_korean: bool = True
    min_hangul_ratio: float = 0.75
    max_cjk_ratio: float = 0.02
    max_jamo_ratio: float = 0.05
    json_key_exemptions: tuple[str, ...] = ()

    @classmethod
    def from_env(cls) -> "BridgePolicy":
        allowed_terms_raw = os.getenv("LLM_BRIDGE_ALLOWED_TERMS", "")
        allowed_terms = tuple(item.strip() for item in allowed_terms_raw.split(",") if item.strip())
        json_key_exemptions_raw = os.getenv("LLM_BRIDGE_JSON_KEY_EXEMPTIONS", "")
        json_key_exemptions = tuple(item.strip() for item in json_key_exemptions_raw.split(",") if item.strip())
        fallbacks_raw = os.getenv("LLM_BRIDGE_FALLBACKS", "")
        fallback_providers = tuple(item.strip().lower() for item in fallbacks_raw.split(",") if item.strip()) or (
            "deepseek",
            "google",
            "openai",
        )
        mode = (os.getenv("LLM_BRIDGE_MODE", "shadow") or "shadow").strip().lower()
        if mode not in {"off", "shadow", "enforce"}:
            mode = "shadow"
        return cls(
            target_language=os.getenv("LLM_BRIDGE_TARGET_LANGUAGE", "ko-KR") or "ko-KR",
            mode=mode,
            allowed_terms=allowed_terms,
            fallback_providers=fallback_providers,
            repair_attempts=_env_int("LLM_BRIDGE_REPAIR_ATTEMPTS", 1),
            enforce_json_schema=_env_bool("LLM_BRIDGE_ENFORCE_JSON_SCHEMA", True),
            strict_korean=_env_bool("LLM_BRIDGE_STRICT_KOREAN", True),
            min_hangul_ratio=_env_float("LLM_BRIDGE_MIN_HANGUL_RATIO", 0.75),
            max_cjk_ratio=_env_float("LLM_BRIDGE_MAX_CJK_RATIO", 0.02),
            max_jamo_ratio=_env_float("LLM_BRIDGE_MAX_JAMO_RATIO", 0.05),
            json_key_exemptions=json_key_exemptions,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "target_language": self.target_language,
            "mode": self.mode,
            "allowed_terms": list(self.allowed_terms),
            "repair_attempts": self.repair_attempts,
            "fallback_providers": list(self.fallback_providers),
            "enforce_json_schema": self.enforce_json_schema,
            "strict_korean": self.strict_korean,
            "min_hangul_ratio": self.min_hangul_ratio,
            "max_cjk_ratio": self.max_cjk_ratio,
            "max_jamo_ratio": self.max_jamo_ratio,
            "json_key_exemptions": list(self.json_key_exemptions),
        }


@dataclass(frozen=True)
class BridgeValidationResult:
    passed: bool
    reason_codes: tuple[str, ...]
    hangul_ratio: float
    cjk_ratio: float
    has_mojibake: bool
    is_empty: bool
    json_valid: bool
    jamo_ratio: float = 0.0
    language_score: float = 0.0
    dominant_language: str = "unknown"


@dataclass(frozen=True)
class BridgeExecutionMetadata:
    provider_used: str
    repair_count: int
    fallback_used: bool
    bridge_mode: str
    reason_codes: tuple[str, ...]
    language_score: float

    def as_usage_metadata(self) -> dict[str, Any]:
        return {
            "bridge_mode": self.bridge_mode,
            "reason_codes": list(self.reason_codes),
            "repair_count": self.repair_count,
            "fallback_used": self.fallback_used,
            "language_score": self.language_score,
            "provider_used": self.provider_used,
        }


def build_bridge_system_prompt(
    original_system_prompt: str,
    *,
    policy: BridgePolicy,
    json_mode: bool,
) -> str:
    bridge_rules = [
        "당신은 한국어 품질 보정 브릿지 레이어를 통과하는 모델입니다.",
        f"최종 출력 언어는 반드시 {policy.target_language} 한국어입니다.",
        "중국어 원문을 이해할 수는 있지만 최종 설명, 요약, 제목, 문장은 한국어로만 출력하세요.",
        "브랜드명, 제품명, 고유명사, 코드, JSON key 외에는 중국어/한자를 그대로 남기지 마세요.",
        "문자 깨짐, 비정상 치환 문자, 분해된 자모, 혼합 언어가 보이면 스스로 한국어로 정리해 다시 출력하세요.",
    ]
    if json_mode:
        bridge_rules.append(
            "JSON 요청입니다. 설명문 없이 유효한 JSON 객체만 반환하고, string value는 한국어 정책을 지키세요."
        )
    bridge_preamble = "\n".join(f"- {rule}" for rule in bridge_rules)
    return f"{bridge_preamble}\n\n[원래 시스템 프롬프트]\n{original_system_prompt.strip()}"


def normalize_prompt_text(user_prompt: str, *, json_mode: bool) -> str:
    normalized = normalize_text(user_prompt).strip()
    if json_mode and "json" not in normalized.lower():
        normalized = f"{normalized}\n\n반드시 JSON object 형식으로만 응답하세요."
    return normalized


def build_repair_messages(
    *,
    original_system_prompt: str,
    original_user_prompt: str,
    raw_content: str,
    validation: BridgeValidationResult,
    policy: BridgePolicy,
    json_mode: bool,
) -> tuple[str, str]:
    reason_text = ", ".join(validation.reason_codes) or "policy_violation"
    system_prompt = build_bridge_system_prompt(
        original_system_prompt,
        policy=policy,
        json_mode=json_mode,
    )
    instructions = [
        "이전 응답을 같은 의미로 다시 작성하세요.",
        "최종 결과는 자연스러운 한국어만 사용하세요.",
        f"수정 사유: {reason_text}",
    ]
    if json_mode:
        instructions.append("JSON key와 전체 구조는 유지하고, JSON object만 반환하세요.")
    else:
        instructions.append("설명 없이 최종 텍스트만 반환하세요.")
    user_prompt = (
        f"[원래 사용자 프롬프트]\n{normalize_prompt_text(original_user_prompt, json_mode=json_mode)}\n\n"
        f"[이전 응답]\n{normalize_text(raw_content)}\n\n"
        f"[수정 지시]\n" + "\n".join(f"- {line}" for line in instructions)
    )
    return system_prompt, user_prompt


def validate_text_content(
    content: str,
    *,
    policy: BridgePolicy,
    json_mode: bool = False,
) -> BridgeValidationResult:
    normalized = normalize_text(content)
    stripped = normalized.strip()
    masked = _mask_allowed_terms(stripped, policy.allowed_terms)
    visible_chars = max(len(_VISIBLE_CHAR_RE.findall(masked)), 1)
    hangul_count = len(_HANGUL_RE.findall(masked))
    cjk_count = len(_CJK_RE.findall(masked))
    jamo_count = len(_JAMO_RE.findall(masked))
    hangul_ratio = hangul_count / visible_chars if stripped else 0.0
    cjk_ratio = cjk_count / visible_chars if stripped else 0.0
    jamo_ratio = jamo_count / visible_chars if stripped else 0.0
    has_mojibake = "\ufffd" in stripped or bool(_MOJIBAKE_RE.search(stripped))
    is_empty = not bool(stripped)
    reason_codes: list[str] = []
    json_valid = True

    if is_empty:
        reason_codes.append("empty_content")
    if has_mojibake:
        reason_codes.append("mojibake")
    if policy.strict_korean and not is_empty and hangul_ratio < policy.min_hangul_ratio:
        reason_codes.append("low_hangul_ratio")
    if not is_empty and cjk_ratio > policy.max_cjk_ratio:
        reason_codes.append("mixed_language")
    if not is_empty and jamo_ratio > policy.max_jamo_ratio:
        reason_codes.append("decomposed_jamo")
    if json_mode:
        try:
            json.loads(stripped)
        except json.JSONDecodeError:
            json_valid = False
            reason_codes.append("json_parse_error")

    language_score = round(max(0.0, min(1.0, hangul_ratio - (cjk_ratio * 3) - (jamo_ratio * 2))), 4)
    dominant_language = _dominant_language(hangul_ratio, cjk_ratio)
    return BridgeValidationResult(
        passed=not reason_codes,
        reason_codes=tuple(reason_codes),
        hangul_ratio=round(hangul_ratio, 4),
        cjk_ratio=round(cjk_ratio, 4),
        has_mojibake=has_mojibake,
        is_empty=is_empty,
        json_valid=json_valid,
        jamo_ratio=round(jamo_ratio, 4),
        language_score=language_score,
        dominant_language=dominant_language,
    )


def validate_json_payload(
    payload: Any,
    *,
    policy: BridgePolicy,
) -> BridgeValidationResult:
    if policy.enforce_json_schema and not isinstance(payload, dict):
        return BridgeValidationResult(
            passed=False,
            reason_codes=("json_schema_mismatch",),
            hangul_ratio=0.0,
            cjk_ratio=0.0,
            has_mojibake=False,
            is_empty=False,
            json_valid=False,
            jamo_ratio=0.0,
            language_score=0.0,
            dominant_language="unknown",
        )
    string_values = list(_iter_json_strings(payload, exempt_keys=set(policy.json_key_exemptions)))
    if not string_values:
        return BridgeValidationResult(
            passed=True,
            reason_codes=(),
            hangul_ratio=1.0,
            cjk_ratio=0.0,
            has_mojibake=False,
            is_empty=False,
            json_valid=True,
            jamo_ratio=0.0,
            language_score=1.0,
            dominant_language="ko",
        )

    aggregate_reasons: set[str] = set()
    hangul_ratios: list[float] = []
    cjk_ratios: list[float] = []
    jamo_ratios: list[float] = []
    scores: list[float] = []
    has_mojibake = False
    is_empty = False

    for value in string_values:
        result = validate_text_content(value, policy=policy, json_mode=False)
        aggregate_reasons.update(result.reason_codes)
        hangul_ratios.append(result.hangul_ratio)
        cjk_ratios.append(result.cjk_ratio)
        jamo_ratios.append(result.jamo_ratio)
        scores.append(result.language_score)
        has_mojibake = has_mojibake or result.has_mojibake
        is_empty = is_empty or result.is_empty

    return BridgeValidationResult(
        passed=not aggregate_reasons,
        reason_codes=tuple(sorted(aggregate_reasons)),
        hangul_ratio=round(sum(hangul_ratios) / len(hangul_ratios), 4),
        cjk_ratio=round(sum(cjk_ratios) / len(cjk_ratios), 4),
        has_mojibake=has_mojibake,
        is_empty=is_empty,
        json_valid=True,
        jamo_ratio=round(sum(jamo_ratios) / len(jamo_ratios), 4),
        language_score=round(sum(scores) / len(scores), 4),
        dominant_language=_dominant_language(
            sum(hangul_ratios) / len(hangul_ratios),
            sum(cjk_ratios) / len(cjk_ratios),
        ),
    )


def normalize_json_payload(payload: Any) -> Any:
    if isinstance(payload, str):
        return normalize_text(payload)
    if isinstance(payload, list):
        return [normalize_json_payload(item) for item in payload]
    if isinstance(payload, tuple):
        return tuple(normalize_json_payload(item) for item in payload)
    if isinstance(payload, dict):
        return {key: normalize_json_payload(value) for key, value in payload.items()}
    return payload


def build_execution_metadata(
    *,
    provider_used: str,
    repair_count: int,
    fallback_used: bool,
    policy: BridgePolicy,
    validation: BridgeValidationResult,
) -> BridgeExecutionMetadata:
    return BridgeExecutionMetadata(
        provider_used=provider_used,
        repair_count=repair_count,
        fallback_used=fallback_used,
        bridge_mode=policy.mode,
        reason_codes=validation.reason_codes,
        language_score=validation.language_score,
    )


def preferred_provider_order(
    enabled_providers: Iterable[str],
    *,
    policy: BridgePolicy,
) -> list[str]:
    enabled = [item for item in enabled_providers]
    preferred = [item for item in policy.fallback_providers if item in enabled]
    remainder = [item for item in enabled if item not in preferred]
    return preferred + remainder


def _mask_allowed_terms(text: str, allowed_terms: tuple[str, ...]) -> str:
    masked = text
    for term in allowed_terms:
        if term:
            masked = masked.replace(term, " ")
    return masked


def _dominant_language(hangul_ratio: float, cjk_ratio: float) -> str:
    if hangul_ratio >= 0.5:
        return "ko"
    if cjk_ratio >= 0.2:
        return "zh"
    return "mixed"


def _iter_json_strings(payload: Any, *, exempt_keys: set[str], current_key: str = "") -> Iterable[str]:
    if isinstance(payload, str):
        if current_key not in exempt_keys:
            yield payload
        return
    if isinstance(payload, list):
        for item in payload:
            yield from _iter_json_strings(item, exempt_keys=exempt_keys, current_key=current_key)
        return
    if isinstance(payload, dict):
        for key, value in payload.items():
            yield from _iter_json_strings(value, exempt_keys=exempt_keys, current_key=str(key))


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name, "").strip().lower()
    if not raw:
        return default
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    return default
