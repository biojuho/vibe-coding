"""generate_short.py — AI 뉴스 속보 쇼츠 편의 API

사양서 인터페이스:
    generate_ai_news_short(news_title, points, hook_text, bg_music=None) → MP4 Path

내부적으로 ShortsFactory 파이프라인에 위임합니다.

사용 예시:
    from ShortsFactory.generate_short import generate_ai_news_short

    result = generate_ai_news_short(
        news_title="GPT-5 출시 — 성능 3배 향상",
        points=[
            {"text": "멀티모달 성능 대폭 향상", "keywords": ["멀티모달", "대폭"]},
            {"text": "추론 속도 3배 개선", "keywords": ["3배"]},
            {"text": "API 가격 50% 인하", "keywords": ["50%"]},
        ],
        hook_text="🚨 AI 속보",
    )
    print(f"생성된 영상: {result}")
"""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from ShortsFactory.pipeline import ShortsFactory

logger = logging.getLogger(__name__)


def generate_ai_news_short(
    news_title: str,
    points: list[dict[str, Any]],
    hook_text: str = "🚨 AI 속보",
    *,
    channel: str = "ai_tech",
    bg_music: str | Path | None = None,
    cta_text: str | None = None,
    output_path: str | Path | None = None,
    output_dir: str | Path | None = None,
) -> Path:
    """AI/기술 뉴스 속보 스타일 쇼츠 영상을 생성합니다.

    사양서 인터페이스를 ShortsFactory로 위임합니다.

    Args:
        news_title: 핵심 뉴스 제목 (헤드라인).
        points: 본문 포인트 리스트. 각 항목은 {"text": str, "keywords": list[str]}.
        hook_text: 훅 텍스트 (기본: "🚨 AI 속보").
        bg_music: 배경음악 파일 경로 (-12dB 덕킹 자동 적용).
        cta_text: CTA 문구 (None이면 기본값 사용).
        output_path: 출력 MP4 경로 (None이면 자동 생성).
        output_dir: 출력 디렉토리 (output_path 미지정 시 사용).

    Returns:
        생성된 MP4 파일 경로.

    Examples:
        >>> path = generate_ai_news_short(
        ...     "GPT-5 출시",
        ...     [{"text": "성능 3배", "keywords": ["3배"]}],
        ... )
    """
    # 출력 경로 결정
    if output_path is None:
        base_dir = Path(output_dir) if output_dir else Path("./output")
        base_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_title = "".join(c if c.isalnum() or c in "_ -" else "_" for c in news_title[:30])
        output_path = base_dir / f"ai_news_{timestamp}_{safe_title}.mp4"

    # 데이터 구성
    data: dict[str, Any] = {
        "news_title": news_title,
        "points": points,
        "hook_text": hook_text,
    }
    if cta_text is not None:
        data["cta_text"] = cta_text

    # ShortsFactory 파이프라인 실행
    factory = ShortsFactory(channel=channel)
    factory.create("ai_news", data)
    result = factory.render(output_path, bg_music=bg_music)

    logger.info("[generate_ai_news_short] 완료: %s", result)
    return result


def generate_future_countdown_short(
    items: list[dict[str, Any]],
    *,
    channel: str = "ai_tech",
    intro_text: str | None = None,
    outro_text: str | None = None,
    bg_music: str | Path | None = None,
    output_path: str | Path | None = None,
    output_dir: str | Path | None = None,
) -> Path:
    """미래 기술 예측 카운트다운 쇼츠 영상을 생성합니다.

    Args:
        items: 카운트다운 항목 리스트.
            각 항목: {"rank": int, "title": str, "description": str, "image_path": str}
        intro_text: 인트로 텍스트 (None이면 "2030년까지 바뀔 기술 TOP N").
        outro_text: 아웃트로 텍스트.
        bg_music: 배경음악 파일 경로.
        output_path: 출력 MP4 경로.
        output_dir: 출력 디렉토리.

    Returns:
        생성된 MP4 파일 경로.

    Examples:
        >>> path = generate_future_countdown_short(
        ...     items=[
        ...         {"rank": 5, "title": "양자 컴퓨팅", "description": "양자 우위 달성"},
        ...         {"rank": 4, "title": "뇌-컴퓨터 인터페이스", "description": "생각으로 제어"},
        ...         {"rank": 3, "title": "핵융합 에너지", "description": "무한 에너지원"},
        ...         {"rank": 2, "title": "AGI", "description": "범용 인공지능"},
        ...         {"rank": 1, "title": "나노 로봇", "description": "체내 자율 치료"},
        ...     ],
        ... )
    """
    if output_path is None:
        base_dir = Path(output_dir) if output_dir else Path("./output")
        base_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = base_dir / f"future_countdown_{timestamp}.mp4"

    data: dict[str, Any] = {"items": items}
    if intro_text is not None:
        data["intro_text"] = intro_text
    if outro_text is not None:
        data["outro_text"] = outro_text

    factory = ShortsFactory(channel=channel)
    factory.create("future_countdown", data)
    result = factory.render(output_path, bg_music=bg_music)

    logger.info("[generate_future_countdown_short] 완료: %s", result)
    return result


def generate_tech_vs_short(
    item_a: dict[str, Any],
    item_b: dict[str, Any],
    categories: list[str],
    *,
    channel: str = "ai_tech",
    conclusion_text: str | None = None,
    bg_music: str | Path | None = None,
    output_path: str | Path | None = None,
    output_dir: str | Path | None = None,
) -> Path:
    """기술 비교(VS) 쇼츠 영상을 생성합니다.

    Args:
        item_a: A 항목. {"name": str, "image": str, "scores": {항목: 값}}
        item_b: B 항목. {"name": str, "image": str, "scores": {항목: 값}}
        categories: 비교 항목명 리스트.
        conclusion_text: 결론 문구 (None이면 자동 생성).
        bg_music: 배경음악.
        output_path: 출력 경로.
        output_dir: 출력 디렉토리.

    Returns:
        생성된 MP4 파일 경로.

    Examples:
        >>> path = generate_tech_vs_short(
        ...     item_a={"name": "GPT-5", "scores": {"성능": 95, "가격": 70}},
        ...     item_b={"name": "Claude 4", "scores": {"성능": 90, "가격": 85}},
        ...     categories=["성능", "가격"],
        ... )
    """
    if output_path is None:
        base_dir = Path(output_dir) if output_dir else Path("./output")
        base_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        a_name = item_a.get("name", "A")
        b_name = item_b.get("name", "B")
        output_path = base_dir / f"vs_{a_name}_vs_{b_name}_{timestamp}.mp4"

    data: dict[str, Any] = {
        "item_a": item_a,
        "item_b": item_b,
        "categories": categories,
    }
    if conclusion_text is not None:
        data["conclusion_text"] = conclusion_text

    factory = ShortsFactory(channel=channel)
    factory.create("tech_vs", data)
    result = factory.render(output_path, bg_music=bg_music)

    logger.info("[generate_tech_vs_short] 완료: %s", result)
    return result
