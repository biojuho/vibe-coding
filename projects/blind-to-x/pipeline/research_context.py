"""Deterministic pre-generation research context for X drafts."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ResearchContext:
    source_frame: str | None
    real_issue: str | None
    universal_value: str | None
    killer_sentence: str | None
    closure: str
    conflict_risk: float
    anchor: str
    flags: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def value_reduction_failed(self) -> bool:
        return not self.universal_value or not self.killer_sentence

    @property
    def conflict_requires_value_reduction(self) -> bool:
        return self.conflict_risk > 0.8

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_frame": self.source_frame,
            "real_issue": self.real_issue,
            "universal_value": self.universal_value,
            "killer_sentence": self.killer_sentence,
            "closure": self.closure,
            "conflict_risk": self.conflict_risk,
            "anchor": self.anchor,
            "flags": list(self.flags),
            "notes": list(self.notes),
            "value_reduction_failed": self.value_reduction_failed,
            "conflict_requires_value_reduction": self.conflict_requires_value_reduction,
        }


_FRAME_RULES: tuple[tuple[tuple[str, ...], tuple[str, str, str, str]], ...] = (
    (
        ("연봉", "월급", "성과급", "보상", "인센", "임금", "돈"),
        (
            "돈을 더 받아야 하느냐의 문제",
            "같은 기준으로 보상받고 설명받을 권리",
            "공정성",
            "이건 돈 욕심이 아니라 기준을 투명하게 세우자는 말입니다",
        ),
    ),
    (
        ("야근", "퇴근", "주말", "연차", "휴가", "워라밸", "칼퇴"),
        (
            "개인이 편하게 일하고 싶다는 문제",
            "일의 책임과 개인 시간의 경계를 어디에 둘 것인가",
            "경계 존중",
            "이건 편하게 일하자는 게 아니라 일과 삶의 경계를 지키자는 말입니다",
        ),
    ),
    (
        ("팀장", "상사", "부장", "대표", "임원", "갑질", "혼냈", "막말"),
        (
            "상사와 직원의 감정 싸움",
            "권한을 가진 사람이 책임 있게 말하고 행동해야 한다는 문제",
            "책임 있는 권한",
            "이건 윗사람을 공격하자는 게 아니라 권한에는 책임이 따른다는 말입니다",
        ),
    ),
    (
        ("채용", "면접", "승진", "평가", "인사", "차별", "학벌"),
        (
            "누가 더 유리했느냐의 문제",
            "기회와 평가가 납득 가능한 기준으로 운영됐는가",
            "기회 공정성",
            "이건 누가 이겼냐가 아니라 기회가 공정했느냐의 문제입니다",
        ),
    ),
    (
        ("육아", "임신", "출산", "결혼", "돌봄", "가족"),
        (
            "개인 사정 배려의 문제",
            "누군가의 삶의 조건을 조직이 어디까지 함께 감당할 것인가",
            "상호 배려",
            "이건 특혜가 아니라 같이 일하기 위한 최소한의 배려입니다",
        ),
    ),
)

_CONFLICT_KEYWORDS = (
    "남자",
    "여자",
    "여직원",
    "남직원",
    "한남",
    "페미",
    "맘충",
    "퐁퐁",
    "진보",
    "보수",
    "정치",
    "노조",
    "세대",
    "MZ",
    "꼰대",
)

_CLOSED_KEYWORDS = (
    "불법",
    "성희롱",
    "폭언",
    "갑질",
    "임금체불",
    "괴롭힘",
    "차별",
    "사기",
    "횡령",
)


def _as_text(value: Any) -> str:
    return str(value or "").strip()


def _source_text(post_data: dict[str, Any]) -> str:
    return "\n".join(part for part in (_as_text(post_data.get("title")), _as_text(post_data.get("content"))) if part)


def extract_anchor_words(text: str, *, max_words: int = 12) -> str:
    """Extract an anchor by whitespace tokens, never by mid-word slicing."""
    words = [word.strip() for word in re.split(r"\s+", _as_text(text)) if word.strip()]
    return " ".join(words[:max_words])


def _choose_frame(text: str) -> tuple[str, str, str, str] | None:
    for keywords, frame in _FRAME_RULES:
        if any(keyword in text for keyword in keywords):
            return frame
    if len(text) >= 40:
        return (
            "개인의 하소연처럼 보이는 문제",
            "비슷한 상황을 겪는 사람들이 납득할 수 있는 기준의 문제",
            "납득 가능한 기준",
            "이건 개인의 예민함이 아니라 모두가 납득할 기준의 문제입니다",
        )
    return None


def _estimate_conflict_risk(text: str) -> tuple[float, list[str]]:
    hits = [keyword for keyword in _CONFLICT_KEYWORDS if keyword.lower() in text.lower()]
    if not hits:
        return 0.15, []
    risk = min(0.95, 0.45 + 0.12 * len(set(hits)))
    if any(keyword in hits for keyword in ("한남", "페미", "맘충", "퐁퐁")):
        risk = max(risk, 0.85)
    return round(risk, 2), [f"conflict_keyword:{hit}" for hit in sorted(set(hits))]


def _decide_closure(text: str) -> str:
    if any(keyword in text for keyword in _CLOSED_KEYWORDS):
        return "closed"
    return "open"


def build_research_context(post_data: dict[str, Any]) -> dict[str, Any]:
    """Build the Stage 0 research_context object without network or paid calls."""
    text = _source_text(post_data)
    anchor = extract_anchor_words(text)
    frame = _choose_frame(text)
    conflict_risk, flags = _estimate_conflict_risk(text)

    if frame is None:
        return ResearchContext(
            source_frame=None,
            real_issue=None,
            universal_value=None,
            killer_sentence=None,
            closure="open",
            conflict_risk=conflict_risk,
            anchor=anchor,
            flags=[*flags, "value_reduction_failed"],
            notes=["source text too short for reliable value reduction"],
        ).to_dict()

    source_frame, real_issue, universal_value, killer_sentence = frame
    notes = [
        "stage0_deterministic_context",
        "external_research_not_required_for_local_gate",
    ]
    if conflict_risk > 0.8:
        notes.append("high_conflict_force_universal_value")

    return ResearchContext(
        source_frame=source_frame,
        real_issue=real_issue,
        universal_value=universal_value,
        killer_sentence=killer_sentence,
        closure=_decide_closure(text),
        conflict_risk=conflict_risk,
        anchor=anchor,
        flags=flags,
        notes=notes,
    ).to_dict()


def ensure_research_context(post_data: dict[str, Any]) -> dict[str, Any]:
    existing = post_data.get("research_context")
    if isinstance(existing, dict):
        return existing
    research_context = build_research_context(post_data)
    post_data["research_context"] = research_context
    return research_context
