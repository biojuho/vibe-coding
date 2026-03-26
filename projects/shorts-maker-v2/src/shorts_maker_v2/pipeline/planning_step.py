"""PlanningStep — Gate 1: 기획서 자동 생성 + 검증.

13단계 워크플로우의 STEP 1-3 (기획서 작성, 레퍼런스 분석, 페르소나 정의)을
LLM 1회 호출로 자동화. Gate 1 검증 내장 (자체 retry loop).
"""

from __future__ import annotations

import logging
from typing import Any

from shorts_maker_v2.config import AppConfig
from shorts_maker_v2.models import GateVerdict, ProductionPlan
from shorts_maker_v2.providers.llm_router import LLMRouter

logger = logging.getLogger(__name__)


class PlanningStep:
    """기획서 자동 생성 + Gate 1 검증."""

    MAX_RETRIES = 2  # Gate 1 재시도 상한

    # 채널별 기획 힌트 (LLM에 추가 맥락 제공)
    _CHANNEL_PLANNING_HINTS: dict[str, str] = {
        "ai_tech": (
            "Focus on specific AI tools, frameworks, or tech products. "
            "The persona should be a developer or tech worker. "
            "Numbers and benchmarks make this channel's content stand out."
        ),
        "psychology": (
            "Focus on emotional validation and self-understanding. "
            "The persona should be someone going through a relatable emotional struggle. "
            "Warmth and empathy are paramount."
        ),
        "history": (
            "Focus on a dramatic historical moment with unexpected twists. "
            "The persona should be a curious audience who loves 'what they didn't teach in school'. "
            "Build tension through paradox or irony."
        ),
        "space": (
            "Focus on cosmic scale, awe, and wonder. "
            "The persona should be someone fascinated by the universe. "
            "Use mind-bending analogies to convey scale."
        ),
        "health": (
            "Focus on evidence-based health tips with specific citations. "
            "The persona should be health-conscious but busy. "
            "Avoid alarmist language; empower the viewer."
        ),
    }

    _SYSTEM_PROMPT = (
        "You are a YouTube Shorts production planner. "
        "Given a topic and channel context, create a detailed production plan.\n\n"
        "Output ONLY valid JSON with these fields:\n"
        "{\n"
        '  "concept": "영상 컨셉 한 줄 요약 (한국어)",\n'
        '  "target_persona": "타겟 페르소나 (나이대/직업/핵심 고민 포함, 한국어)",\n'
        '  "core_message": "이 영상이 전달할 핵심 메시지 딱 1개 (한국어)",\n'
        '  "visual_keywords": ["비주얼 컨셉 키워드 3개 이상 (영어)"],\n'
        '  "forbidden_elements": ["금지 요소 1개 이상 (한국어)"],\n'
        '  "tone": "영상 전체의 톤 (한국어, 예: 차분하고 논리적인)"\n'
        "}\n\n"
        "Rules:\n"
        "- concept: 시청자가 왜 이 영상을 클릭할지 명확히\n"
        "- target_persona: '20대 직장인'처럼 추상적이면 안됨. "
        "'28세 주니어 개발자, AI에 밀릴까 불안한'처럼 구체적으로\n"
        "- core_message: 영상이 끝난 후 시청자가 기억할 한 문장\n"
        "- visual_keywords: DALL-E/Pexels에서 검색할 수 있는 구체적 영어 키워드\n"
        "- forbidden_elements: 이 영상에서 절대 사용하지 말아야 할 표현이나 접근\n"
    )

    def __init__(self, config: AppConfig, llm_router: LLMRouter):
        self.config = config
        self.llm_router = llm_router

    def run(
        self,
        topic: str,
        channel_key: str = "",
    ) -> tuple[ProductionPlan, GateVerdict]:
        """기획서 생성 + Gate 1 검증.

        Returns:
            (ProductionPlan, GateVerdict)
            - PASS: 기획서 검증 통과
            - FAIL_RETRY: MAX_RETRIES 초과 시에도 폴백 기획서 + PASS 반환
        """
        channel_hint = self._CHANNEL_PLANNING_HINTS.get(channel_key, "")

        for attempt in range(1, self.MAX_RETRIES + 1):
            logger.info(
                "[Planning] attempt %d/%d for topic='%s' channel='%s'",
                attempt, self.MAX_RETRIES, topic, channel_key,
            )

            user_prompt = f"Topic: {topic}\n"
            if channel_hint:
                user_prompt += f"Channel context: {channel_hint}\n"
            if attempt > 1:
                user_prompt += (
                    "IMPORTANT: The previous plan was rejected. "
                    "Make the persona MORE specific (include age, job title, exact worry), "
                    "and ensure visual_keywords has at least 3 items.\n"
                )

            try:
                result = self.llm_router.generate_json(
                    system_prompt=self._SYSTEM_PROMPT,
                    user_prompt=user_prompt,
                    temperature=0.7,
                )
                if not isinstance(result, dict):
                    logger.warning("[Planning] LLM returned non-dict: %s", type(result))
                    continue

                plan = self._parse_plan(result)
                verdict, issues = self._gate1_check(plan)

                if verdict == GateVerdict.PASS:
                    logger.info("[Planning] Gate 1 PASS ✅")
                    return plan, GateVerdict.PASS

                logger.warning(
                    "[Planning] Gate 1 FAIL (attempt %d): %s",
                    attempt, "; ".join(issues),
                )
            except Exception as exc:
                logger.warning("[Planning] attempt %d error: %s", attempt, exc)

        # 모든 재시도 실패 → 폴백 기획서
        logger.warning("[Planning] All retries exhausted, using fallback plan")
        fallback = self._fallback_plan(topic, channel_key)
        return fallback, GateVerdict.PASS

    def _parse_plan(self, data: dict[str, Any]) -> ProductionPlan:
        """LLM JSON → ProductionPlan 변환."""
        return ProductionPlan(
            concept=str(data.get("concept", "")).strip(),
            target_persona=str(data.get("target_persona", "")).strip(),
            core_message=str(data.get("core_message", "")).strip(),
            visual_keywords=[
                str(k).strip()
                for k in data.get("visual_keywords", [])
                if str(k).strip()
            ],
            forbidden_elements=[
                str(f).strip()
                for f in data.get("forbidden_elements", [])
                if str(f).strip()
            ],
            tone=str(data.get("tone", "")).strip(),
        )

    @staticmethod
    def _gate1_check(plan: ProductionPlan) -> tuple[GateVerdict, list[str]]:
        """Gate 1: 기획서 품질 검증.

        Returns:
            (verdict, issues_list)
        """
        issues: list[str] = []

        if not plan.concept or len(plan.concept) < 5:
            issues.append("concept too short or missing")
        if not plan.target_persona or len(plan.target_persona) < 10:
            issues.append("target_persona too vague (need age/job/worry)")
        if not plan.core_message or len(plan.core_message) < 5:
            issues.append("core_message missing or too short")
        if len(plan.visual_keywords) < 3:
            issues.append(f"visual_keywords only {len(plan.visual_keywords)}, need 3+")
        if len(plan.forbidden_elements) < 1:
            issues.append("forbidden_elements empty")

        verdict = GateVerdict.PASS if not issues else GateVerdict.FAIL_RETRY
        return verdict, issues

    @staticmethod
    def _fallback_plan(topic: str, channel_key: str) -> ProductionPlan:
        """폴백 기획서 (모든 재시도 실패 시)."""
        return ProductionPlan(
            concept=f"{topic}에 대한 핵심 인사이트",
            target_persona="25-35세, 해당 주제에 관심 있는 직장인/학생",
            core_message=f"{topic}의 핵심을 40초 안에 전달",
            visual_keywords=["modern", "minimalist", "infographic"],
            forbidden_elements=["과장된 표현", "검증되지 않은 주장"],
            tone="차분하고 신뢰감 있는",
        )
