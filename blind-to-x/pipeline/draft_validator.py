"""초안 검증 + 자동 재시도 래퍼.

QualityGate 결과를 기반으로 실패한 초안을 자동 수정 지시와 함께
LLM에 재시도를 요청합니다. Guardrails AI의 핵심 패턴(validate → retry)을
기존 LLM 인프라로 경량 구현합니다.

사용법:
    from pipeline.draft_validator import validate_and_fix_drafts
    fixed = await validate_and_fix_drafts(drafts, post_data, generator, config)
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# 게이트 실패 코드 → LLM 수정 지시 매핑
_FIX_INSTRUCTIONS: dict[str, str] = {
    "too_short": "초안이 너무 짧습니다. 원문의 핵심 포인트를 더 담아 분량을 늘려주세요.",
    "too_long": "초안이 너무 깁니다. 핵심만 남기고 간결하게 줄여주세요.",
    "cliche_overuse": "상투적 표현이 3개 이상 사용되었습니다. 클리셰를 모두 제거하고 구체적인 표현으로 바꿔주세요.",
    "forbidden_expression": "금지된 표현이 포함되어 있습니다. 해당 표현을 완전히 제거하고 다시 작성하세요.",
    "repetition": "동일한 문장이 반복됩니다. 반복을 제거하고 각 문장에 새로운 정보를 담으세요.",
    "toxic_or_pii": "부적절한 표현이나 개인정보가 포함되어 있습니다. 즉시 제거하세요.",
    "potential_fabrication": "원문에 없는 수치가 초안에 포함된 것으로 보입니다. 원문에 실제로 있는 숫자만 사용하세요.",
}

_MAX_RETRIES = 1  # 재시도 최대 1회 (비용 절감)


async def validate_and_fix_drafts(
    drafts: dict[str, str | Any],
    post_data: dict[str, Any],
    generator: Any = None,
    config: Any = None,
) -> dict[str, str | Any]:
    """모든 플랫폼 초안을 검증하고, 실패 시 자동 수정을 시도합니다.

    Args:
        drafts: {platform: draft_text} 딕셔너리
        post_data: 원문 데이터
        generator: DraftGenerator 인스턴스 (재시도용, 없으면 재시도 스킵)
        config: ConfigManager 인스턴스

    Returns:
        검증/수정된 drafts 딕셔너리 (원본 구조 유지)
    """
    from pipeline.quality_gate import QualityGate

    gate = QualityGate()
    source_content = str(post_data.get("content", ""))
    validation_results: dict[str, dict] = {}
    fixed_drafts = dict(drafts)

    for platform, draft_text in list(drafts.items()):
        if platform.startswith("_") or not isinstance(draft_text, str):
            continue

        result = gate.check(draft_text, source_content, platform=platform, post_data=post_data)
        validation_results[platform] = {
            "passed": result.passed,
            "score": result.score,
            "failures": result.failures,
            "warnings": result.warnings,
        }

        if result.passed:
            logger.info("[QualityGate] %s PASS (score=%.0f)", platform, result.score)
            continue

        logger.warning(
            "[QualityGate] %s FAIL (score=%.0f, failures=%s)",
            platform, result.score, result.failures,
        )

        # 자동 수정 시도
        if generator is None:
            continue

        fix_instructions = []
        for failure in result.failures:
            code = failure.split(":")[0].strip()
            instruction = _FIX_INSTRUCTIONS.get(code, "")
            if instruction:
                fix_instructions.append(instruction)

        if not fix_instructions:
            continue

        for retry in range(_MAX_RETRIES):
            try:
                retry_prompt = _build_retry_prompt(
                    draft_text, fix_instructions, platform, post_data,
                )
                retried = await generator._call_llm_with_fallback(retry_prompt)
                if not retried or not retried.strip():
                    break

                # 재검증
                recheck = gate.check(retried, source_content, platform=platform)
                if recheck.score > result.score:
                    fixed_drafts[platform] = retried
                    logger.info(
                        "[QualityGate] %s RETRY %d: score %.0f → %.0f",
                        platform, retry + 1, result.score, recheck.score,
                    )
                    break
                else:
                    logger.info(
                        "[QualityGate] %s RETRY %d: no improvement (%.0f)",
                        platform, retry + 1, recheck.score,
                    )
            except Exception as exc:
                logger.debug("[QualityGate] %s retry failed: %s", platform, exc)
                break

    # 검증 결과를 메타데이터에 기록
    post_data["quality_gate"] = validation_results
    return fixed_drafts


def _build_retry_prompt(
    draft_text: str,
    fix_instructions: list[str],
    platform: str,
    post_data: dict[str, Any],
) -> str:
    """수정 지시를 포함한 재시도 프롬프트를 구성."""
    fixes = "\n".join(f"- {inst}" for inst in fix_instructions)
    return f"""아래 {platform} 초안에 품질 문제가 발견되었습니다. 수정 지시에 따라 다시 작성하세요.

[원본 초안]
{draft_text}

[수정 지시]
{fixes}

[원문 제목] {post_data.get('title', '')}
[원문 요약] {str(post_data.get('content', ''))[:500]}

수정된 초안만 출력하세요. 설명이나 태그 없이 초안 텍스트만 반환하세요."""
