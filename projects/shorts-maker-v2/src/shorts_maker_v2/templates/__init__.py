"""숏츠 템플릿 레지스트리.

채널별 전용 비주얼 템플릿을 등록·관리합니다.
각 템플릿은 tools/ 폴더의 스크립트를 래핑하여
파이프라인에서 호출할 수 있는 통일된 인터페이스를 제공합니다.

Note:
    _REGISTRY — 대본 생성기(tools/) 매핑 (Main Pipeline용)
    TEMPLATE_REGISTRY — 비주얼 렌더링 템플릿(ShortsFactory) 매핑
"""

from __future__ import annotations

from typing import Any

# Re-export: ShortsFactory 비주얼 렌더링 템플릿 (Single Source of Truth)
try:
    from ShortsFactory.templates import TEMPLATE_REGISTRY
except ImportError:
    TEMPLATE_REGISTRY = {}  # ShortsFactory가 설치 안 된 환경 호환

# 템플릿 레지스트리 (lazy-load)
_REGISTRY: dict[str, dict[str, Any]] = {}


def register(name: str, *, channel: str, generator_cls: str, module: str, description: str = ""):
    """템플릿 등록.

    Args:
        name: 템플릿 고유 이름 (예: "psychology_experiment")
        channel: 채널 키 (예: "psychology")
        generator_cls: 생성기 클래스 이름
        module: 파이썬 모듈 경로
        description: 설명
    """
    _REGISTRY[name] = {
        "channel": channel,
        "generator_cls": generator_cls,
        "module": module,
        "description": description,
    }


def get(name: str) -> dict[str, Any] | None:
    return _REGISTRY.get(name)


def list_for_channel(channel: str) -> list[dict[str, Any]]:
    return [{"name": k, **v} for k, v in _REGISTRY.items() if v["channel"] == channel]


def list_all() -> list[dict[str, Any]]:
    return [{"name": k, **v} for k, v in _REGISTRY.items()]


# ── 심리학 채널 템플릿 ──
register(
    "psychology_experiment",
    channel="psychology",
    generator_cls="PsychologyShortsGenerator",
    module="tools.psychology_shorts",
    description="심리학 실험 스토리텔링 (미스터리 훅 → 실험 배경 → 결과 반전 → 교훈)",
)
register(
    "psychology_quiz",
    channel="psychology",
    generator_cls="PsychologyQuizGenerator",
    module="tools.psychology_quiz",
    description="심리학 퀴즈 인터랙티브 (질문 → 선택지 → 정답/해설 → 반전)",
)
register(
    "psychology_quote",
    channel="psychology",
    generator_cls="QuoteShortsGenerator",
    module="tools.psychology_quote",
    description="심리학 기반 자기계발 명언 (블러 배경 + 파티클 + 줄별 페이드인)",
)

# ── 역사 채널 템플릿 ──
register(
    "history_timeline",
    channel="history",
    generator_cls="HistoryTimelineGenerator",
    module="tools.history_timeline",
    description="역사 사건 타임라인 (좌측 타임라인 바 + 이벤트 카드 + 세피아)",
)
register(
    "history_mystery",
    channel="history",
    generator_cls="HistoryMysteryGenerator",
    module="tools.history_mystery",
    description="역사 미스터리 서스펜스 (미스터리 제시 → 배경 → 의문점 → 가설)",
)
register(
    "history_fact_reversal",
    channel="history",
    generator_cls="HistoryFactGenerator",
    module="tools.history_fact_shorts",
    description="역사 반전 팩트 (통념 소개 → '하지만 사실은…' 반전 → 교훈)",
)
register(
    "history_countdown",
    channel="history",
    generator_cls="HistoryCountdownGenerator",
    module="tools.history_fact_shorts",
    description="역사 카운트다운 TOP N (양피지 카드 + 골드 랭킹 넘버)",
)

# ── AI/기술 채널 템플릿 ──
register(
    "ai_news_breaking",
    channel="ai_tech",
    generator_cls="AINewsShortsGenerator",
    module="tools.ai_tech_shorts",
    description="AI 뉴스 브레이킹 (BREAKING 배지 → 핵심 포인트 → 임팩트 → CTA)",
)
register(
    "tech_vs",
    channel="ai_tech",
    generator_cls="TechVSShortsGenerator",
    module="tools.ai_tech_shorts",
    description="기술 비교 A vs B (좌우 분할 → 포인트 비교 → 결론)",
)
register(
    "ai_countdown",
    channel="ai_tech",
    generator_cls="AINewsShortsGenerator",
    module="tools.ai_tech_shorts",
    description="AI/기술 카운트다운 TOP N (countdown 구조 재활용, 뉴스 생성기 기반)",
)

# ── 우주/천문학 채널 템플릿 ──
register(
    "space_scale",
    channel="space",
    generator_cls="SpaceScaleGenerator",
    module="tools.space_scale",
    description="우주 스케일 비교 줌아웃 (별 파티클 + 글로우 링 + 카운트업 + 와프 전환)",
)
register(
    "space_fact_bomb",
    channel="space",
    generator_cls="SpaceFactBombGenerator",
    module="tools.space_fact_bomb",
    description="우주 팩트 폭탄 (글리치 + FACT 카드 + 카운트업 + 딥 스페이스 톤)",
)
register(
    "space_countdown",
    channel="space",
    generator_cls="SpaceFactBombGenerator",
    module="tools.space_fact_bomb",
    description="우주 카운트다운 TOP N (팩트 폭탄 생성기 활용 listicle 구조)",
)

# ── 의학/건강 채널 템플릿 ──
register(
    "health_do_vs_dont",
    channel="health",
    generator_cls="HealthDoVsDontGenerator",
    module="tools.health_do_vs_dont",
    description="건강 DO vs DON'T 비교 (상하 분할 카드 + VS 배지 + 면책 고지)",
)
register(
    "health_medical_study",
    channel="health",
    generator_cls="MedicalStudyGenerator",
    module="tools.health_medical_study",
    description="의학 연구 인포그래픽 (바 차트 + 카운트업 + 연구 배지 + 면책)",
)
register(
    "health_mental_message",
    channel="health",
    generator_cls="MentalHealthMessageGenerator",
    module="tools.health_mental_message",
    description="정신건강 감성 메시지 (호흡 리듬 + 세리프 페이드인 + 민트 하이라이트)",
)
register(
    "health_countdown",
    channel="health",
    generator_cls="HealthDoVsDontGenerator",
    module="tools.health_do_vs_dont",
    description="건강 카운트다운 TOP N (DO/DON'T 구조 재활용 listicle)",
)
