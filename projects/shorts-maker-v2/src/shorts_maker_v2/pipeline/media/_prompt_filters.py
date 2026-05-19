"""이미지 생성기 프롬프트 사후 필터.

씬 비주얼 LLM(`script_step.py`)이 만든 영어 시각 프롬프트가 텍스트/레터링
요청 없이도 DALL-E / Pollinations / Gemini Imagen 이 이미지에 영어 단어를
"장식처럼" 그려넣는 케이스가 잦다(2026-05-11 케이스: 썸네일 배경에
`"MIND UNLEASH"` 유출). YouTube Shorts 업로드 품질에선 외국어
텍스트 artifact 가 즉시 차단 요인이 되므로, 이미지 API 호출 직전에
모든 프롬프트에 텍스트 억제 negative 를 보강한다.
"""

from __future__ import annotations

# 모든 generator 가 인식하는 안전한 자연어 형태.
# DALL-E 3 는 negative prompt 자체를 받지 않지만, 평문에 "no text" 가
# 들어 있으면 생성에 영향을 준다.
_TEXT_SUPPRESSION_SUFFIX: str = (
    " No text, no letters, no labels, no captions, no logos, no watermarks, no typography, no signage."
)

# 이미 텍스트 억제가 들어 있는 프롬프트(예: thumbnail_step.py 채널 프롬프트)는
# 중복 부착 방지. 대소문자 무관 substring 매칭.
_ALREADY_SUPPRESSED_MARKERS: tuple[str, ...] = (
    "no text",
    "no letters",
    "no typography",
    "no signage",
    "text-free",
    "without text",
    "no words",
)


def with_text_suppression(prompt: str) -> str:
    """이미지 프롬프트에 텍스트 억제 negative 를 보강해 반환.

    이미 동등한 negative 가 들어 있으면 원본 그대로 반환(중복 방지).
    빈 문자열/None 는 그대로 통과(상위에서 처리).
    """
    if not prompt:
        return prompt
    lowered = prompt.lower()
    for marker in _ALREADY_SUPPRESSED_MARKERS:
        if marker in lowered:
            return prompt
    return prompt.rstrip() + _TEXT_SUPPRESSION_SUFFIX
