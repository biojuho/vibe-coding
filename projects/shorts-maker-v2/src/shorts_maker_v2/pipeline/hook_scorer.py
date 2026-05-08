"""Hook Strength Scorer — 대본 Hook 씬의 스크롤 정지력을 정량 평가.

YouTube Shorts 2026 알고리즘 기준:
  - 1~3초 내 스크롤 정지 (scroll-stop) 가 핵심 리텐션 지표
  - 짧고 강렬한 Hook이 완주율(watch-through rate)을 결정

점수 체계 (0.0 ~ 1.0):
  - brevity_score    : 짧을수록 높음 (15자 이하 최고점)
  - punch_score      : 강렬한 패턴 매칭 (질문, 숫자, 감탄사 등)
  - curiosity_score  : 호기심 유발 요소 (정보 갭, 반전, 비밀)
  - specificity_score: 구체적 수치/사실 포함 여부

최종 hook_strength = weighted average → 0.6 이상 PASS.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# ── 강렬함 패턴 (한국어) ─────────────────────────────────────────

# 질문형 Hook
_QUESTION_PATTERNS = re.compile(
    r"(할까[요]?|일까[요]?|인가[요]?|맞을까|알고.*(있|계신)|"
    r"어떨까|몰랐|뭘까|왜\s|무엇|진짜|정말|과연|혹시)",
    re.IGNORECASE,
)

# 숫자/통계 Hook
_NUMBER_PATTERN = re.compile(r"\d+[%초분배만억천조개년월일]")

# 감탄/충격 Hook
_SHOCK_WORDS = frozenset(
    [
        "충격",
        "경악",
        "반전",
        "소름",
        "놀라운",
        "믿기 힘든",
        "역대급",
        "최초",
        "세계 최초",
        "아무도 몰랐",
        "숨겨진",
        "비밀",
        "폭로",
        "드디어",
        "결국",
        "마침내",
        "실화",
    ]
)

# 호기심 갭 패턴
_CURIOSITY_PATTERNS = re.compile(
    r"(알고 보니|사실은|근데|그런데|문제는|하지만|의외로|반대로|오히려)",
    re.IGNORECASE,
)


@dataclass
class HookScore:
    """Hook 씬 평가 결과."""

    brevity_score: float = 0.0
    punch_score: float = 0.0
    curiosity_score: float = 0.0
    specificity_score: float = 0.0
    hook_strength: float = 0.0
    passed: bool = False
    feedback: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "brevity_score": round(self.brevity_score, 3),
            "punch_score": round(self.punch_score, 3),
            "curiosity_score": round(self.curiosity_score, 3),
            "specificity_score": round(self.specificity_score, 3),
            "hook_strength": round(self.hook_strength, 3),
            "passed": self.passed,
            "feedback": self.feedback,
        }


# ── 가중치 ───────────────────────────────────────────────────────
_WEIGHTS = {
    "brevity": 0.30,
    "punch": 0.30,
    "curiosity": 0.25,
    "specificity": 0.15,
}

_PASS_THRESHOLD = 0.6


def score_hook(narration: str, *, threshold: float = _PASS_THRESHOLD) -> HookScore:
    """Hook 나레이션의 스크롤 정지력을 평가한다.

    Args:
        narration: Hook 씬의 한국어 나레이션 텍스트.
        threshold: 통과 기준 (기본 0.6).

    Returns:
        HookScore 데이터 객체.
    """
    result = HookScore()
    text = narration.strip()
    length = len(text)
    feedback: list[str] = []

    # 1. Brevity (짧을수록 좋음)
    if length <= 10:
        result.brevity_score = 1.0
    elif length <= 15:
        result.brevity_score = 0.9
    elif length <= 25:
        result.brevity_score = 0.7
    elif length <= 40:
        result.brevity_score = 0.4
    else:
        result.brevity_score = 0.2
        feedback.append(f"Hook이 너무 깁니다 ({length}자). 15자 이하 권장.")

    # 2. Punch (강렬함)
    punch = 0.0
    if _QUESTION_PATTERNS.search(text):
        punch += 0.4
    shock_hits = sum(1 for w in _SHOCK_WORDS if w in text)
    punch += min(shock_hits * 0.3, 0.6)
    result.punch_score = min(punch, 1.0)
    if result.punch_score < 0.3:
        feedback.append("강렬한 표현이 부족합니다. 질문이나 충격적 단어 추가 권장.")

    # 3. Curiosity (호기심)
    curiosity = 0.0
    if _CURIOSITY_PATTERNS.search(text):
        curiosity += 0.5
    # 정보 갭: "~인 이유", "~하는 방법" 패턴
    if re.search(r"(이유|방법|비결|원인|진실)", text):
        curiosity += 0.5
    result.curiosity_score = min(curiosity, 1.0)

    # 4. Specificity (구체성)
    specificity = 0.0
    if _NUMBER_PATTERN.search(text):
        specificity += 0.6
    # 고유명사나 구체적 대상 (따옴표, 이름 등)
    if re.search(r"['\"]|NASA|MIT|WHO|한국|미국|일본|중국", text):
        specificity += 0.4
    result.specificity_score = min(specificity, 1.0)

    # 최종 점수 (가중 평균)
    result.hook_strength = (
        result.brevity_score * _WEIGHTS["brevity"]
        + result.punch_score * _WEIGHTS["punch"]
        + result.curiosity_score * _WEIGHTS["curiosity"]
        + result.specificity_score * _WEIGHTS["specificity"]
    )
    result.passed = result.hook_strength >= threshold
    result.feedback = feedback

    logger.info(
        "[HookScorer] strength=%.3f (brevity=%.2f punch=%.2f curiosity=%.2f spec=%.2f) passed=%s",
        result.hook_strength,
        result.brevity_score,
        result.punch_score,
        result.curiosity_score,
        result.specificity_score,
        result.passed,
    )

    return result
