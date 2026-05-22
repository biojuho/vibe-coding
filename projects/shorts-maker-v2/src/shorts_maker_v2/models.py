from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Literal

VisualType = Literal["video", "image"]

# ── 5-ACT 구조 역할 (Gate 기반 파이프라인) ─────────────────────────────────────
# hook: 스크롤 멈춤 (0-5s)
# problem: 공감/고통 묘사 (5-18s)
# insight: 반전/핵심 메시지 (18-33s)
# solution: 실천 행동 (33-43s)
# cta: 마무리 (43-50s) — 레거시, closing 권장
# closing: 여운 있는 마무리 (CTA 없이 조용히 끝남)
# body: 기존 호환용 (listicle 등 프리셋에서 사용)
VALID_STRUCTURE_ROLES = {
    "hook",
    "problem",
    "insight",
    "solution",
    "cta",
    "closing",
    "body",
    "rank1",
    "rank2",
    "rank3",
    "rank4",
    "rank5",
    "setup",
    "conflict",
    "climax",
    "resolution",
    "lesson",
    "question",
    "hint",
    "answer",
    "explain",
    "bonus",
    "pro1",
    "con1",
    "pro2",
    "con2",
    "verdict",
}


class GateVerdict(str, Enum):
    """피드백 게이트 판정 결과."""

    PASS = "pass"
    FAIL_RETRY = "fail_retry"  # 이전 단계로 되돌아가 재생성
    HOLD = "hold"  # 수동 리뷰 대기


@dataclass(frozen=True)
class ProductionPlan:
    """Gate 1 출력: 기획서 (PlanningStep이 생성)."""

    concept: str  # 영상 컨셉 한 줄 요약
    target_persona: str  # 타겟 페르소나 (나이/직업/고민)
    core_message: str  # 핵심 메시지 1개
    visual_keywords: list[str]  # 비주얼 컨셉 키워드 3+개
    forbidden_elements: list[str]  # 금지 요소 리스트
    tone: str = ""  # 톤 (옵션)
    reference_notes: str = ""  # 레퍼런스 참고 메모 (옵션)
    audience_profile: dict[str, Any] | None = None  # 청중 분석 결과

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_prompt_block(self) -> str:
        """대본 프롬프트에 주입할 기획서 블록."""
        lines = [
            "=== PRODUCTION PLAN ===",
            f"Concept: {self.concept}",
            f"Target Persona: {self.target_persona}",
            f"Core Message: {self.core_message}",
            f"Visual Keywords: {', '.join(self.visual_keywords)}",
            f"Forbidden: {', '.join(self.forbidden_elements)}",
        ]
        if self.tone:
            lines.append(f"Tone: {self.tone}")
        if self.reference_notes:
            lines.append(f"Reference: {self.reference_notes}")
        if self.audience_profile:
            lines.append("--- Audience Profile ---")
            for k, v in self.audience_profile.items():
                lines.append(f"  {k}: {v}")
        return "\n".join(lines)


@dataclass
class QCReport:
    """Gate 3/4 출력: 품질 검수 결과."""

    checks: dict[str, bool] = field(default_factory=dict)
    verdict: str = "pass"  # "pass" | "fail_retry" | "hold"
    issues: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SceneOutline:
    """구성안의 개별 씬 골격 (대본 아닌 의도+방향만)."""

    scene_id: int
    role: str  # structure_role
    intent: str  # 이 씬이 달성할 것 (1문장)
    visual_direction: str  # 비주얼 방향 (DALL-E 프롬프트 아님, 컨셉)
    emotional_beat: str  # 시청자가 느낄 감정
    target_sec: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class StructureOutline:
    """Gate 2 출력: 씬별 구성안 (대본 이전 단계)."""

    scenes: list[SceneOutline]
    total_estimated_sec: float
    narrative_arc: str = "quiet_storytelling"  # 내러티브 아크 유형
    # True iff StructureStep fell back to a deterministic template after
    # LLM retries were exhausted. Orchestrator surfaces this as a degraded
    # step so silently-shipped boilerplate outlines stop counting as success.
    is_fallback: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenes": [s.to_dict() for s in self.scenes],
            "total_estimated_sec": self.total_estimated_sec,
            "narrative_arc": self.narrative_arc,
            "is_fallback": self.is_fallback,
        }

    def to_prompt_block(self) -> str:
        """ScriptStep 프롬프트에 주입할 구성안 블록."""
        lines = ["=== STRUCTURAL OUTLINE (follow this exactly) ==="]
        for s in self.scenes:
            lines.append(
                f"Scene {s.scene_id} [{s.role}]: "
                f"Intent: {s.intent}. "
                f"Visual direction: {s.visual_direction}. "
                f"Emotional beat: {s.emotional_beat}. "
                f"Target: {s.target_sec}s."
            )
        lines.append("=== End Structure ===")
        lines.append("")
        lines.append("Write full narration_ko and visual_prompt_en for EACH scene above.")
        lines.append("Follow the intent and emotional beat precisely.")
        if self.scenes and self.scenes[-1].role == "closing":
            lines.append("The final scene must end with a lingering thought. NO action demands.")
        return "\n".join(lines)


@dataclass
class SceneQCResult:
    """씬별 품질 검수 결과."""

    scene_id: int
    checks: dict[str, bool] = field(default_factory=dict)
    verdict: str = "pass"  # "pass" | "fail_retry"
    issues: list[str] = field(default_factory=list)
    retry_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SemanticQCResult:
    """LLM 기반 의미 QC 결과 (씬-씬 연결성 + 톤 일관성).

    Post-asset/post-scene_qc 단계에서 영상의 전체 흐름을 LLM judge 가 한 번에
    채점. 개별 씬 QC(`SceneQCResult`)나 script_review 의 글로벌 점수와 달리,
    어느 씬 전환이 약한지 specific 하게 잡아낸다.
    """

    scene_flow_score: int = 0  # 0..10
    tone_consistency_score: int = 0  # 0..10
    overall_score: int = 0  # 0..10
    weak_transitions: list[dict[str, Any]] = field(default_factory=list)  # [{from, to, reason}]
    verdict: str = "pass"  # "pass" | "degraded" | "error"
    feedback: str = ""  # 한 줄 요약
    raw_response: str = ""  # 디버깅용 LLM 원문 (실패 시 비어있을 수 있음)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RetentionSimulationResult:
    """합성 시청자 리텐션 시뮬레이션 결과.

    렌더 직전에 LLM 이 N명의 서로 다른 시청자 페르소나를 시뮬레이션해서,
    각 페르소나가 씬 경계마다 "계속 볼지 / 스와이프할지"를 판단하게 한다.
    그 집계가 곧 예측 리텐션 곡선이다 — `retention_hints` 의 휴리스틱 점수와
    달리, 어느 씬에서 *왜* 이탈이 발생하는지를 페르소나 단위로 잡아낸다.

    LLM 호출이 실패하면 `source="heuristic"` 으로 강등돼 결정론적
    휴리스틱 곡선이 대신 채워진다 — 영상 ship 자체는 막지 않는다.
    """

    predicted_retention: float = 0.0  # 0..1 — 마지막 씬까지 남는 평균 시청자 비율 (AVD 프록시)
    loop_probability: float = 0.0  # 0..1 — 재시청(루핑) 확률
    retention_curve: list[dict[str, Any]] = field(default_factory=list)
    # [{scene_id, role, viewers_remaining: 0..1, drop_reason}]
    persona_breakdown: list[dict[str, Any]] = field(default_factory=list)
    # [{name, swiped_at_scene: int|None, note}]
    first_dropoff_scene_id: int | None = None  # 이탈이 처음 임계치를 넘는 씬
    weakest_scene_id: int | None = None  # 가장 약한 씬
    rewrite_directive: str = ""  # 가장 약한 씬에 대한 실행 가능한 재작성 지시
    verdict: str = "pass"  # "pass" | "degraded" | "error"
    feedback: str = ""  # 한 줄 요약
    source: str = "llm"  # "llm" | "heuristic" — 어떤 엔진이 산출했는지
    raw_response: str = ""  # 디버깅용 LLM 원문

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RetentionAutoFixResult:
    """리텐션 자가 치유(closed-loop) 결과.

    `RetentionSimulationResult` 의 verdict 가 `degraded` 일 때, 가장 약한
    씬의 나레이션을 `rewrite_directive` 기반으로 LLM 이 재작성하고, 그
    재작성본을 다시 시뮬레이션해 *예측 리텐션이 실제로 올라가는지* 검증한다.
    개선이 확인된 재작성만 채택한다(accepted=True).

    이 단계는 현재 렌더 입력을 변경하지 않는다 — 이미 생성된 TTS 오디오와
    desync 되기 때문이다. 검증된 재작성본은 manifest 에 기록되어 다음
    이터레이션/시리즈 후속편에 반영된다 (advisory).
    """

    applied: bool = False  # 재작성이 산출·검증되었는지
    applied_to_render: bool = False  # 재작성이 실제 렌더 입력(scene_plans)에 반영됐는지
    passes: int = 0  # 수행한 재작성 패스 수
    before_retention: float = 0.0  # 자가치유 전 예측 리텐션
    after_retention: float = 0.0  # 자가치유 후 예측 리텐션
    rewrites: list[dict[str, Any]] = field(default_factory=list)
    # [{scene_id, role, before, after, accepted, projected_retention}]
    verdict: str = "skipped"  # "improved" | "no_improvement" | "skipped" | "error"
    feedback: str = ""  # 한 줄 요약
    source: str = "llm"  # "llm" — 재작성 엔진
    raw_response: str = ""  # 디버깅용 LLM 원문

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ScenePlan:
    scene_id: int
    narration_ko: str
    visual_prompt_en: str
    target_sec: float
    structure_role: str = "body"  # "hook"|"problem"|"insight"|"solution"|"cta"|"closing"|"body"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SceneAsset:
    scene_id: int
    audio_path: str
    visual_type: VisualType
    visual_path: str
    duration_sec: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class JobManifest:
    job_id: str
    topic: str
    status: str
    total_duration_sec: float = 0.0
    estimated_cost_usd: float = 0.0
    output_path: str = ""
    title: str = ""
    failed_steps: list[dict[str, str]] = field(default_factory=list)
    scene_count: int = 0
    created_at: str = ""
    thumbnail_path: str = ""
    hook_pattern: str = ""
    srt_path: str = ""
    ab_variant: dict[str, str] = field(default_factory=dict)  # A/B 테스트 변수 기록
    series_suggestion: dict[str, Any] | None = None  # 시리즈 후속편 추천
    step_timings: dict[str, float] = field(default_factory=dict)  # 파이프라인 스텝별 소요 시간(초)
    production_plan: dict[str, Any] | None = None  # Gate 1 기획서
    qc_result: dict[str, Any] | None = None  # Gate 4 최종 QC 결과
    structure_outline: dict[str, Any] | None = None  # Gate 2 구성안
    scene_qc_results: list[dict[str, Any]] | None = None  # 씬별 QC 결과
    scene_qc_summary: dict[str, Any] | None = None  # 씬별 QC 집계: 재시도 후 잔여 실패 표면화
    hook_score: dict[str, Any] | None = None  # Hook Strength Scorer 결과
    retention_hints: dict[str, Any] | None = None  # Retention Hints 분석 결과
    sentiment: dict[str, Any] | None = None  # Content Intelligence 감성 분석
    semantic_qc: dict[str, Any] | None = None  # LLM 기반 씬-씬 의미 QC 결과 (opt-in)
    retention_simulation: dict[str, Any] | None = None  # 합성 시청자 리텐션 시뮬레이션 결과 (opt-in)
    retention_autofix: dict[str, Any] | None = None  # 리텐션 자가 치유(closed-loop) 결과 (opt-in)

    degraded_steps: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class BatchResult:
    topic: str
    channel: str
    status: str
    job_id: str
    cost_usd: float
    duration_sec: float
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
