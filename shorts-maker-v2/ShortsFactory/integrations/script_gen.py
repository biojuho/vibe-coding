"""script_gen.py — AI 스크립트 자동 생성기.

채널 톤과 템플릿 구조에 맞는 스크립트를 LLM으로 자동 생성합니다.

Usage:
    from ShortsFactory.integrations.script_gen import ScriptGenerator

    gen = ScriptGenerator(channel="ai_tech")
    data = gen.generate("GPT-5 출시 소문", template="ai_news_breaking")
    # data = {"news_title": "...", "points": [...], "hook_text": "..."}

    # 렌더링까지 원스톱
    result = gen.generate_and_render("GPT-5 출시 소문", template="ai_news_breaking")
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger("ShortsFactory.script_gen")

_HERE = Path(__file__).resolve().parent.parent
_PROJECT = _HERE.parent


# 템플릿별 데이터 스키마 정의
TEMPLATE_SCHEMAS: dict[str, dict[str, Any]] = {
    "ai_news_breaking": {
        "required": ["news_title", "hook_text", "points"],
        "points_schema": {"text": "str", "keywords": "list[str]"},
        "example": {
            "news_title": "GPT-5, 성능 3배 향상 확인",
            "hook_text": "AI 역사 다시 쓰인다",
            "points": [
                {"text": "멀티모달 완전 통합", "keywords": ["멀티모달"]},
                {"text": "추론 속도 3배 개선", "keywords": ["3배"]},
                {"text": "API 가격 50% 인하", "keywords": ["50%"]},
            ],
        },
    },
    "psychology_experiment": {
        "required": ["hook_text", "background", "experiment", "result"],
        "example": {
            "hook_text": "이 실험 결과, 충격적입니다",
            "background": "1960년 스탠퍼드 대학에서...",
            "experiment": "참가자들에게 전기충격을...",
            "result": "65%가 최대 전압까지...",
            "keywords": ["밀그램", "복종"],
        },
    },
    "history_timeline": {
        "required": ["title", "events"],
        "events_schema": {"year": "str", "event": "str", "keywords": "list[str]"},
    },
    "space_scale": {
        "required": ["hook_text", "comparisons"],
        "comparisons_schema": {"small": "str", "large": "str", "desc": "str"},
    },
    "health_do_vs_dont": {
        "required": ["hook_text", "do_items", "dont_items"],
    },
    # 나머지 템플릿은 generic schema 사용
}


class ScriptGenerator:
    """채널별 톤에 맞는 스크립트를 LLM으로 자동 생성."""

    def __init__(self, channel: str, api_key: str | None = None, model: str = "gpt-4o-mini"):
        from ShortsFactory.pipeline import ShortsFactory

        self.factory = ShortsFactory(channel=channel)
        self.channel = channel
        self.persona = self.factory.channel._raw.get("persona_channel_context", "")
        self.display_name = self.factory.channel.display_name
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.model = model

    def generate(self, topic: str, template: str, **kwargs) -> dict[str, Any]:
        """주제를 입력하면 템플릿에 맞는 데이터 딕셔너리를 생성.

        Args:
            topic: 콘텐츠 주제 (예: "GPT-5 출시 소문")
            template: 템플릿 이름 (예: "ai_news_breaking")

        Returns:
            ShortsFactory.create()에 전달할 dict
        """
        schema = TEMPLATE_SCHEMAS.get(template, {})
        example = schema.get("example", {})
        required = schema.get("required", [])

        prompt = self._build_prompt(topic, template, required, example)

        if self.api_key:
            return self._call_llm(prompt)
        else:
            logger.warning("OPENAI_API_KEY not set. Returning template structure only.")
            return self._generate_placeholder(topic, template, required)

    def generate_and_render(
        self,
        topic: str,
        template: str,
        output: str | None = None,
        **kwargs,
    ) -> str:
        """주제 → 스크립트 생성 → 렌더링 → MP4 경로 반환."""
        data = self.generate(topic, template, **kwargs)

        # [QA 수정] LLM 응답이 비어있으면 에러
        if not data:
            raise ValueError(f"Failed to generate script for '{topic}' with template '{template}'")

        if output is None:
            from datetime import datetime

            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe = "".join(c if c.isalnum() or c in "_ -" else "_" for c in topic[:20])
            output = f"output/{self.channel}_{template}_{ts}_{safe}.mp4"

        self.factory.create(template, data)
        return self.factory.render(output)

    def _build_prompt(
        self,
        topic: str,
        template: str,
        required: list[str],
        example: dict,
    ) -> str:
        """LLM 프롬프트 생성."""
        example_json = json.dumps(example, ensure_ascii=False, indent=2) if example else "{}"

        return f"""당신은 유튜브 숏츠 스크립트 작성 전문가입니다.

[채널 정보]
채널명: {self.display_name}
채널 특성:
{self.persona}

[과제]
주제: {topic}
템플릿: {template}
필수 필드: {", ".join(required) if required else "자유 형식"}

[결과 형식]
반드시 JSON 형식으로만 응답하세요. 설명 없이 JSON만 출력하세요.
한국어로 작성하세요.
{f"참고 예시: {example_json}" if example else ""}

[주의사항]
- 채널 톤에 맞게 작성하세요
- hook_text는 시청자를 1초 만에 사로잡아야 합니다
- keywords에는 강조할 핵심 단어를 포함하세요
- 30~45초 분량 (200~350자)으로 작성하세요
"""

    def _call_llm(self, prompt: str) -> dict[str, Any]:
        """OpenAI API 호출."""
        try:
            import requests
        except ImportError:
            logger.error("requests 필요: pip install requests")
            return {}

        resp = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.8,
                "max_tokens": 2000,
            },
            timeout=30,
        )

        if resp.status_code != 200:
            logger.error(f"OpenAI API error: {resp.status_code}")
            return {}

        data = resp.json()
        choices = data.get("choices", [])
        if not choices:
            logger.error("OpenAI API returned empty choices")
            return {}
        content = choices[0]["message"]["content"]
        # JSON 추출 (```json ... ``` 포맷 처리)
        content = content.strip()
        if content.startswith("```"):
            lines = content.split("\n")
            content = "\n".join(lines[1:-1])

        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}\nContent: {content[:200]}")
            return {}

    def _generate_placeholder(
        self,
        topic: str,
        template: str,
        required: list[str],
    ) -> dict[str, Any]:
        """API 키 없을 때 플레이스홀더 생성."""
        result: dict[str, Any] = {}
        for field in required:
            if "items" in field or "points" in field:
                result[field] = [{"text": f"{topic} - 항목 {i + 1}", "keywords": []} for i in range(3)]
            elif "text" in field:
                result[field] = f"{topic} - {field}"
            else:
                result[field] = f"[{field}] {topic}"
        if "hook_text" not in result:
            result["hook_text"] = f"당신이 몰랐던 {topic}의 비밀"
        return result
