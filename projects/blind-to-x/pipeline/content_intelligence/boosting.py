"""Deterministic scoring and classification for Blind content."""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
import math
import re
from typing import Any

logger = logging.getLogger(__name__)

def estimate_viral_boost_llm(title: str, content: str, topic_cluster: str, emotion_axis: str) -> float:
    """LLM으로 바이럴 잠재력을 추가 추정, 0~15점 반환.

    규칙 기반 스코어링의 보조 신호로 사용됩니다.
    LLM 실패 시 0.0 반환 (graceful degradation).
    비용: Gemini/Groq 무료 tier 사용 시 $0.
    """
    try:
        # 루트 경로에서 LLMClient 접근 (blind-to-x는 루트 venv 사용)
        import importlib.util
        import pathlib

        _root = pathlib.Path(__file__).resolve().parent.parent.parent
        spec = importlib.util.spec_from_file_location("execution.llm_client", _root / "execution" / "llm_client.py")
        if spec is None or spec.loader is None:
            return 0.0
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
        client = mod.LLMClient(
            providers=["google", "groq", "deepseek", "zhipuai"],
            track_usage=False,
        )
    except Exception as exc:
        logger.debug("LLM 바이럴 부스트 클라이언트 초기화 실패: %s", exc)
        return 0.0

    _system = (
        "You are a Korean SNS viral potential analyst. "
        "Given a post's title and content, score its viral potential on Korean Twitter/X from 0 to 100. "
        "Focus on: emotional resonance, relatability, controversy potential, shareability. "
        'Respond ONLY with valid JSON: {"score": <integer 0-100>, "reason": "<one sentence in Korean>"}'
    )
    _user = (
        f"Topic cluster: {topic_cluster}\nEmotion: {emotion_axis}\n\nTitle: {title[:200]}\n\nContent: {content[:500]}"
    )

    try:
        result = client.generate_json(
            system_prompt=_system,
            user_prompt=_user,
            temperature=0.3,
        )
        raw = float(result.get("score", 0))
        # 0~100 점수를 0~15 부스트로 변환 (최대 15점 가산)
        boost = round(max(0.0, min(15.0, raw * 0.15)), 2)
        logger.info("LLM 바이럴 부스트: %.1f/100 → +%.2f pts | %s", raw, boost, result.get("reason", ""))
        return boost
    except Exception as exc:
        logger.debug("LLM 바이럴 부스트 실패: %s", exc)
        return 0.0
