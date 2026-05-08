"""Retention Hints — YouTube Shorts 완주율 최적화 힌트 생성.

2026 알고리즘 연구 기반:
  - Shorts 완주율(watch-through rate)은 알고리즘 추천의 핵심 지표
  - 40~45초가 최적 구간 (60초 제한 대비 여유)
  - 씬 전환 리듬이 일정하면 이탈율 증가 → 변주 필요
  - 마지막 5초에 반전/여운이 있으면 루핑(재시청) 유도

이 모듈은 대본 구조를 분석하여 리텐션 개선 힌트를 제공합니다.
QC Step 또는 대본 리뷰 후처리에서 optional로 호출됩니다.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class RetentionHint:
    """개별 리텐션 개선 힌트."""

    category: str  # "pacing" | "loop" | "duration" | "hook" | "structure"
    severity: str  # "info" | "warning" | "critical"
    message: str
    scene_id: int | None = None


@dataclass
class RetentionReport:
    """전체 리텐션 분석 보고서."""

    estimated_retention_score: float = 0.0  # 0.0 ~ 1.0
    hints: list[RetentionHint] = field(default_factory=list)
    loop_potential: float = 0.0  # 루핑 가능성 0.0 ~ 1.0

    def to_dict(self) -> dict:
        return {
            "estimated_retention_score": round(self.estimated_retention_score, 3),
            "loop_potential": round(self.loop_potential, 3),
            "hint_count": len(self.hints),
            "hints": [
                {
                    "category": h.category,
                    "severity": h.severity,
                    "message": h.message,
                    "scene_id": h.scene_id,
                }
                for h in self.hints
            ],
        }


@dataclass
class SceneInfo:
    """씬 정보 (경량 입력 DTO — ScenePlan에서 필요한 필드만 추출)."""

    scene_id: int
    duration_sec: float
    structure_role: str  # "hook" | "body" | "cta" | "closing"
    narration_length: int  # 나레이션 글자 수


# ── 최적 구간 상수 ───────────────────────────────────────────────

_OPTIMAL_TOTAL_MIN = 38.0
_OPTIMAL_TOTAL_MAX = 45.0
_SHORTS_HARD_LIMIT = 60.0

_MIN_SCENE_DURATION = 2.5
_MAX_SCENE_DURATION = 12.0


def analyze_retention(scenes: list[SceneInfo]) -> RetentionReport:
    """대본 구조 기반 리텐션 분석.

    Args:
        scenes: 씬 정보 리스트 (SceneInfo DTO).

    Returns:
        RetentionReport with hints and estimated scores.
    """
    hints: list[RetentionHint] = []
    total_duration = sum(s.duration_sec for s in scenes)

    # 1. 총 길이 체크
    if total_duration > _SHORTS_HARD_LIMIT:
        hints.append(
            RetentionHint(
                category="duration",
                severity="critical",
                message=f"총 {total_duration:.1f}초 → 60초 제한 초과. 씬 축소 필수.",
            )
        )
    elif total_duration > _OPTIMAL_TOTAL_MAX:
        hints.append(
            RetentionHint(
                category="duration",
                severity="warning",
                message=(
                    f"총 {total_duration:.1f}초 → 최적 구간({_OPTIMAL_TOTAL_MIN}"
                    f"~{_OPTIMAL_TOTAL_MAX}초) 초과. 완주율 하락 우려."
                ),
            )
        )
    elif total_duration < _OPTIMAL_TOTAL_MIN:
        hints.append(
            RetentionHint(
                category="duration",
                severity="info",
                message=f"총 {total_duration:.1f}초 → 최적 구간보다 짧음. 내용 보강 가능.",
            )
        )

    # 2. Hook 씬 길이 체크 (1~3초가 이상적)
    hook_scenes = [s for s in scenes if s.structure_role == "hook"]
    for hs in hook_scenes:
        if hs.duration_sec > 5.0:
            hints.append(
                RetentionHint(
                    category="hook",
                    severity="warning",
                    message=f"Hook(씬{hs.scene_id}) {hs.duration_sec:.1f}초 → 3초 이하 권장.",
                    scene_id=hs.scene_id,
                )
            )

    # 3. 씬 전환 리듬 분석 (변주 체크)
    durations = [s.duration_sec for s in scenes]
    if len(durations) >= 3:
        avg_dur = sum(durations) / len(durations)
        variance = sum((d - avg_dur) ** 2 for d in durations) / len(durations)
        # 분산이 매우 낮으면 단조로움
        if variance < 1.0:
            hints.append(
                RetentionHint(
                    category="pacing",
                    severity="warning",
                    message=(f"씬 길이 분산={variance:.2f} (매우 균일). 전환 리듬에 변주를 주면 이탈율 감소."),
                )
            )

    # 4. 개별 씬 길이 이상 감지
    for s in scenes:
        if s.duration_sec < _MIN_SCENE_DURATION:
            hints.append(
                RetentionHint(
                    category="pacing",
                    severity="info",
                    message=f"씬{s.scene_id} {s.duration_sec:.1f}초 → 너무 짧아 내용 전달 어려움.",
                    scene_id=s.scene_id,
                )
            )
        elif s.duration_sec > _MAX_SCENE_DURATION:
            hints.append(
                RetentionHint(
                    category="pacing",
                    severity="warning",
                    message=f"씬{s.scene_id} {s.duration_sec:.1f}초 → 길어서 이탈 위험.",
                    scene_id=s.scene_id,
                )
            )

    # 5. 루핑 잠재력 평가
    loop_score = _estimate_loop_potential(scenes)

    # 6. 전체 리텐션 점수 추정
    retention_score = _estimate_retention(
        total_duration=total_duration,
        scene_count=len(scenes),
        hint_count=len(hints),
        critical_count=sum(1 for h in hints if h.severity == "critical"),
        warning_count=sum(1 for h in hints if h.severity == "warning"),
    )

    report = RetentionReport(
        estimated_retention_score=retention_score,
        hints=hints,
        loop_potential=loop_score,
    )

    logger.info(
        "[RetentionHints] score=%.3f loop=%.3f hints=%d (critical=%d warn=%d)",
        retention_score,
        loop_score,
        len(hints),
        sum(1 for h in hints if h.severity == "critical"),
        sum(1 for h in hints if h.severity == "warning"),
    )

    return report


def _estimate_retention(
    *,
    total_duration: float,
    scene_count: int,
    hint_count: int,
    critical_count: int,
    warning_count: int,
) -> float:
    """경험적 리텐션 점수 추정 (0.0 ~ 1.0)."""
    score = 0.8  # 기본 점수

    # 최적 구간 보너스
    if _OPTIMAL_TOTAL_MIN <= total_duration <= _OPTIMAL_TOTAL_MAX:
        score += 0.1

    # 씬 수 적절성 (5~8씬이 최적)
    if 5 <= scene_count <= 8:
        score += 0.05

    # 패널티
    score -= critical_count * 0.2
    score -= warning_count * 0.05

    return max(0.0, min(1.0, score))


def _estimate_loop_potential(scenes: list[SceneInfo]) -> float:
    """루핑(재시청) 가능성 추정.

    마지막 씬이 짧고 hook과 연결되면 루핑 가능성이 높음.
    """
    if not scenes:
        return 0.0

    score = 0.3  # 기본

    last = scenes[-1]
    first = scenes[0]

    # 마지막 씬이 짧으면 여운 → 루핑 유도
    if last.duration_sec <= 4.0:
        score += 0.2

    # closing이 아닌 body로 끝나면 열린 결말 느낌
    if last.structure_role == "body":
        score += 0.1

    # Hook과 Closing의 나레이션 길이 비율이 비슷하면 리듬 순환
    if first.narration_length > 0 and last.narration_length > 0:
        ratio = min(first.narration_length, last.narration_length) / max(first.narration_length, last.narration_length)
        if ratio > 0.6:
            score += 0.15

    return min(1.0, score)
