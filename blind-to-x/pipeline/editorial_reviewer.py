"""Editorial Reviewer — LLM 자가 검수 및 폴리시 패스.

Gemini Flash(무료)를 사용하여 초안의 실질 품질을 평가하고,
점수가 낮으면 자동 리라이트합니다.

사용법:
    reviewer = EditorialReviewer(config=config)
    result = await reviewer.review_and_polish(drafts, post_data)
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import aiohttp

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

_RULES_FILE = Path(__file__).parent.parent / "classification_rules.yaml"
_brand_voice_cache: dict | None = None

# 리뷰 통과 기준 (평균 이 점수 이상이면 원본 유지, 미만이면 리라이트)
_REWRITE_THRESHOLD = 6.0
_REVIEW_TIMEOUT_SECONDS = 15
_REVIEW_MODEL = "gemini-2.5-flash"


def _load_brand_voice() -> dict:
    """classification_rules.yaml에서 brand_voice 섹션을 1회 로드 후 캐시."""
    global _brand_voice_cache
    if _brand_voice_cache is not None:
        return _brand_voice_cache
    if yaml is None or not _RULES_FILE.exists():
        _brand_voice_cache = {}
        return _brand_voice_cache
    try:
        with open(_RULES_FILE, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        _brand_voice_cache = data.get("brand_voice", {})
    except Exception:
        _brand_voice_cache = {}
    return _brand_voice_cache


@dataclass
class EditorialResult:
    """에디토리얼 리뷰 결과."""

    polished_drafts: dict[str, str] = field(default_factory=dict)
    scores: dict[str, int] = field(default_factory=dict)
    avg_score: float = 0.0
    suggestions: list[str] = field(default_factory=list)
    original_drafts: dict[str, str] = field(default_factory=dict)


class EditorialReviewer:
    """LLM 기반 에디토리얼 리뷰어.

    생성된 초안을 5가지 축으로 평가하고, 기준 미달 시 리라이트합니다.
    Gemini Flash(무료)를 사용하여 추가 비용 없이 품질을 높입니다.
    """

    def __init__(self, config: Any = None):
        self.config = config
        self.api_key = (
            os.environ.get("GEMINI_API_KEY")
            or os.environ.get("GOOGLE_API_KEY")
            or (config.get("gemini.api_key") if config else None)
        )
        self.model = _REVIEW_MODEL
        self.timeout = _REVIEW_TIMEOUT_SECONDS
        self.brand_voice = _load_brand_voice()

    def _build_review_prompt(
        self,
        platform: str,
        draft_text: str,
        post_data: dict[str, Any],
    ) -> str:
        """플랫폼별 리뷰 프롬프트를 구성합니다."""
        source_title = post_data.get("title", "")
        source_content = str(post_data.get("content", ""))[:500]
        profile = post_data.get("content_profile", {}) or {}

        voice_guide = ""
        if self.brand_voice:
            persona = self.brand_voice.get("persona", "")
            traits = ", ".join(self.brand_voice.get("voice_traits", []))
            forbidden = ", ".join(self.brand_voice.get("forbidden_expressions", []))
            voice_guide = f"""
페르소나: {persona}
말투 규칙: {traits}
금지 표현: {forbidden}"""

        # 원문에서 숫자/고유명사 추출 (구체성 평가용)
        source_numbers = re.findall(r"\d[\d,.]*\d|\d+[만천백억원%]", source_content)
        numbers_hint = f"원문 숫자/수치: {', '.join(source_numbers[:10])}" if source_numbers else ""

        return f"""당신은 직장인 콘텐츠 시니어 에디터입니다. 아래 초안을 5가지 축으로 엄격히 평가하세요.

[원문 정보]
제목: {source_title}
본문 요약: {source_content}
토픽: {profile.get('topic_cluster', '기타')}
{numbers_hint}

[플랫폼]: {platform}

[검수 대상 초안]
{draft_text}

[브랜드 보이스]{voice_guide}

[평가 기준 (각 1~10점)]
1. hook (훅 강도): 첫 문장이 스크롤을 멈추게 하는가? 숫자/질문/대비/감정어가 있는가?
2. specificity (구체성): 원문의 숫자/사례/고유명사가 반영되었는가? "높은 연봉" 같은 뭉뚱그린 표현은 감점.
3. voice (보이스 일관성): 페르소나에 맞는가? 금지 표현을 사용했는가? AI스러운 표현은 없는가?
4. engagement (참여 유도력): 읽은 사람이 댓글/공유하고 싶은가? 마무리가 강한가?
5. readability (가독성): 문장이 자연스럽고 읽기 쉬운가? 긴 문장이나 수동태가 과다하지 않은가?

[응답 형식 — 반드시 JSON으로만 응답]
{{
  "scores": {{"hook": N, "specificity": N, "voice": N, "engagement": N, "readability": N}},
  "suggestions": ["개선 제안 1", "개선 제안 2"],
  "rewritten": "평균 6점 미만일 경우에만 리라이트한 전체 초안. 6점 이상이면 빈 문자열."
}}"""

    async def _call_gemini(self, prompt: str) -> dict:
        """Gemini Flash API를 호출하여 JSON 응답을 파싱합니다."""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.3, "responseMimeType": "application/json"},
        }
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                url,
                params={"key": self.api_key},
                json=payload,
                headers={"Content-Type": "application/json"},
            ) as response:
                text_body = await response.text()
                if response.status >= 400:
                    raise RuntimeError(f"Gemini review API error {response.status}: {text_body[:200]}")
                data = json.loads(text_body)

        candidates = data.get("candidates", [])
        if not candidates:
            raise RuntimeError("Gemini review returned no candidates")

        parts = candidates[0].get("content", {}).get("parts", [])
        raw_text = "".join(part.get("text", "") for part in parts if part.get("text"))

        # JSON 추출 (마크다운 코드블록 안에 있을 수 있음)
        json_match = re.search(r"\{[\s\S]*\}", raw_text)
        if not json_match:
            raise RuntimeError(f"Gemini review returned non-JSON: {raw_text[:200]}")
        return json.loads(json_match.group())

    async def _review_single_platform(
        self,
        platform: str,
        draft_text: str,
        post_data: dict[str, Any],
    ) -> tuple[str, dict[str, int], list[str]]:
        """단일 플랫폼 초안을 리뷰하고 (폴리시된 텍스트, 점수, 제안) 반환."""
        prompt = self._build_review_prompt(platform, draft_text, post_data)
        result = await self._call_gemini(prompt)

        scores = result.get("scores", {})
        # 점수 정규화 (1-10 범위 보장)
        for key in ("hook", "specificity", "voice", "engagement", "readability"):
            val = scores.get(key, 5)
            scores[key] = max(1, min(10, int(val)))

        suggestions = result.get("suggestions", [])
        avg = sum(scores.values()) / max(len(scores), 1)

        # 평균 6점 미만이면 리라이트 사용
        rewritten = result.get("rewritten", "")
        if avg < _REWRITE_THRESHOLD and rewritten and rewritten.strip():
            logger.info(
                "[Editorial] %s 리라이트 적용 (avg=%.1f < %.1f)",
                platform, avg, _REWRITE_THRESHOLD,
            )
            return rewritten.strip(), scores, suggestions

        return draft_text, scores, suggestions

    async def review_and_polish(
        self,
        drafts: dict[str, str | Any],
        post_data: dict[str, Any],
    ) -> EditorialResult:
        """모든 플랫폼 초안을 리뷰하고 폴리시합니다.

        Args:
            drafts: {platform: draft_text} 딕셔너리 (내부 키 '_'로 시작하는 건 무시)
            post_data: 원문 데이터 (title, content, content_profile 등)

        Returns:
            EditorialResult: 폴리시된 초안, 점수, 제안 등
        """
        if not self.api_key:
            logger.debug("Editorial review skipped: no Gemini API key")
            return EditorialResult(
                polished_drafts=dict(drafts),
                original_drafts=dict(drafts),
            )

        result = EditorialResult(original_drafts={})
        all_scores: dict[str, int] = {}
        all_suggestions: list[str] = []

        # 플랫폼별 초안만 필터링 (내부 메타 키 제외)
        platform_drafts = {
            k: v for k, v in drafts.items()
            if not k.startswith("_") and isinstance(v, str) and v.strip()
        }

        for platform, draft_text in platform_drafts.items():
            result.original_drafts[platform] = draft_text
            try:
                polished, scores, suggestions = await self._review_single_platform(
                    platform, draft_text, post_data,
                )
                result.polished_drafts[platform] = polished
                # 점수는 플랫폼별로 저장
                for dim, val in scores.items():
                    all_scores[f"{platform}_{dim}"] = val
                all_suggestions.extend(
                    f"[{platform}] {s}" for s in suggestions
                )
            except Exception as exc:
                logger.warning("[Editorial] %s review failed (using original): %s", platform, exc)
                result.polished_drafts[platform] = draft_text

        # 내부 메타 키 보존 (_regulation_check 등)
        for k, v in drafts.items():
            if k.startswith("_"):
                result.polished_drafts[k] = v

        result.scores = all_scores
        result.suggestions = all_suggestions
        result.avg_score = (
            sum(all_scores.values()) / max(len(all_scores), 1)
            if all_scores else 0.0
        )

        logger.info(
            "[Editorial] Review complete: avg=%.1f, platforms=%d, suggestions=%d",
            result.avg_score, len(platform_drafts), len(all_suggestions),
        )
        return result
