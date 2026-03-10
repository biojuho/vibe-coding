from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

VisualType = Literal["video", "image"]


@dataclass(frozen=True)
class ScenePlan:
    scene_id: int
    narration_ko: str
    visual_prompt_en: str
    target_sec: float
    structure_role: str = "body"  # "hook" | "body" | "cta"

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

