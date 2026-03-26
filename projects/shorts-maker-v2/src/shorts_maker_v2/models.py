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
# cta: 마무리 (43-50s)
# body: 기존 호환용 (listicle 등 프리셋에서 사용)
VALID_STRUCTURE_ROLES = {"hook", "problem", "insight", "solution", "cta", "body",
                         "rank1", "rank2", "rank3", "rank4", "rank5",
                         "setup", "conflict", "climax", "resolution", "lesson",
                         "question", "hint", "answer", "explain", "bonus",
                         "pro1", "con1", "pro2", "con2", "verdict"}


class GateVerdict(str, Enum):
    """피드백 게이트 판정 결과."""
    PASS = "pass"
    FAIL_RETRY = "fail_retry"   # 이전 단계로 되돌아가 재생성
    HOLD = "hold"               # 수동 리뷰 대기


@dataclass(frozen=True)
class ProductionPlan:
    """Gate 1 출력: 기획서 (PlanningStep이 생성)."""
    concept: str                    # 영상 컨셉 한 줄 요약
    target_persona: str             # 타겟 페르소나 (나이/직업/고민)
    core_message: str               # 핵심 메시지 1개
    visual_keywords: list[str]      # 비주얼 컨셉 키워드 3+개
    forbidden_elements: list[str]   # 금지 요소 리스트
    tone: str = ""                  # 톤 (옵션)
    reference_notes: str = ""       # 레퍼런스 참고 메모 (옵션)

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
        return "\n".join(lines)


@dataclass
class QCReport:
    """Gate 3/4 출력: 품질 검수 결과."""
    checks: dict[str, bool] = field(default_factory=dict)
    verdict: str = "pass"           # "pass" | "fail_retry" | "hold"
    issues: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ScenePlan:
    scene_id: int
    narration_ko: str
    visual_prompt_en: str
    target_sec: float
    structure_role: str = "body"  # "hook"|"problem"|"insight"|"solution"|"cta"|"body"

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
