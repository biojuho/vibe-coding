"""Editorial Reviewer — LLM 자가 검수 및 폴리시 패스.

Multi-provider fallback(DeepSeek/Gemini/xAI)으로 초안의 실질 품질을 평가하고,
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
from typing import Any

import aiohttp
from typing_extensions import TypedDict

from pipeline.draft_contract import is_publishable_draft_key, split_draft_bundle
from pipeline.rules_loader import get_rule_section, load_rules

try:
    from langgraph.graph import END, START, StateGraph

    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    END = "__end__"
    START = "__start__"


class EditorialState(TypedDict, total=False):
    """LangGraph 기반 여러 번 반복될 에디토리얼 상태."""

    platform: str
    draft_text: str
    post_data: dict[str, Any]
    scores: dict[str, int]
    suggestions: list[str]
    rewritten_candidate: str
    avg_score: float
    iteration: int
    threshold: float


logger = logging.getLogger(__name__)

_brand_voice_cache: dict | None = None

# 리뷰 통과 기준 (평균 이 점수 이상이면 원본 유지, 미만이면 리라이트)
# 5.0으로 낮춤: 6.0은 자연스러운 캡션도 과도하게 리라이트하여 경직되는 문제
_REWRITE_THRESHOLD = 5.0
_REVIEW_TIMEOUT_SECONDS = 15

# Multi-provider fallback 설정
_PROVIDER_CONFIGS = {
    "gemini": {
        "url_template": "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        "default_model": "gemini-2.5-flash",
        "env_keys": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
        "config_key": "gemini.api_key",
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com/v1/chat/completions",
        "default_model": "deepseek-chat",
        "env_keys": ["DEEPSEEK_API_KEY"],
        "config_key": "deepseek.api_key",
    },
    "xai": {
        "base_url": "https://api.x.ai/v1/chat/completions",
        "default_model": "grok-4-1-fast-reasoning",
        "env_keys": ["XAI_API_KEY", "GROK_API_KEY"],
        "config_key": "xai.api_key",
    },
}


_rules_cache: dict | None = None


def _load_rules() -> dict:
    """Load merged rule sections with in-module caching."""
    global _rules_cache
    if _rules_cache is not None:
        return _rules_cache
    _rules_cache = load_rules()
    return _rules_cache


def _load_brand_voice() -> dict:
    """Load the brand voice section with a small local cache."""
    global _brand_voice_cache
    if _brand_voice_cache is not None:
        return _brand_voice_cache
    _brand_voice_cache = get_rule_section("brand_voice", {})
    return _brand_voice_cache


@dataclass
class EditorialResult:
    """에디토리얼 리뷰 결과."""

    polished_drafts: dict[str, str] = field(default_factory=dict)
    scores: dict[str, int] = field(default_factory=dict)
    avg_score: float = 0.0
    suggestions: list[str] = field(default_factory=list)
    original_drafts: dict[str, str] = field(default_factory=dict)


class _FallbackEditorialGraph:
    """LangGraph 미설치 환경용 최소 editorial loop."""

    def __init__(self, owner: "EditorialReviewer") -> None:
        self.owner = owner

    async def ainvoke(self, initial_state: EditorialState) -> EditorialState:
        state: EditorialState = dict(initial_state)

        while True:
            state.update(await self.owner._reviewer_node(state))
            avg = state.get("avg_score", 0.0)
            threshold = state.get("threshold", 5.0)
            iteration = state.get("iteration", 0)

            if avg >= threshold or iteration >= 2 or not state.get("rewritten_candidate", "").strip():
                return state

            state.update(await self.owner._rewriter_node(state))


class EditorialReviewer:
    """LLM 기반 에디토리얼 리뷰어.

    생성된 초안을 5가지 축으로 평가하고, 기준 미달 시 리라이트합니다.
    Multi-provider fallback으로 가용 LLM을 자동 선택합니다.
    """

    def __init__(self, config: Any = None):
        self.config = config
        self.timeout = _REVIEW_TIMEOUT_SECONDS
        self.brand_voice = _load_brand_voice()
        self._editorial_thresholds = _load_rules().get("editorial_thresholds", {})

        # Multi-provider: config의 llm.providers 순서를 존중하되, editorial에서 지원하는 것만 필터
        self._providers = self._build_provider_chain(config)

        # Build LangGraph workflow
        self._graph = self._build_graph()

    def _build_provider_chain(self, config: Any) -> list[dict]:
        """config의 llm.providers 순서대로 사용 가능한 provider 목록을 구성."""
        supported = set(_PROVIDER_CONFIGS.keys())
        configured_order = []
        if config:
            configured_order = config.get("llm.providers", []) or []
        # config 순서 중 editorial이 지원하는 것만
        order = [p for p in configured_order if p in supported]
        # 누락된 supported provider 추가
        for p in ("gemini", "deepseek", "xai"):
            if p not in order:
                order.append(p)

        providers = []
        for name in order:
            pc = _PROVIDER_CONFIGS[name]
            api_key = None
            for env_key in pc["env_keys"]:
                api_key = os.environ.get(env_key)
                if api_key:
                    break
            if not api_key and config:
                api_key = config.get(pc["config_key"])
            if not api_key:
                continue
            # config에서 enabled 체크
            if config and config.get(f"{name}.enabled", True) is False:
                continue
            model = (config.get(f"{name}.model") if config else None) or pc["default_model"]
            providers.append({"name": name, "api_key": api_key, "model": model})
        return providers

    def _build_graph(self) -> Any:
        """에디토리얼 리뷰(Evaluator)와 리라이트(Optimizer) 루프를 위한 StateGraph 컴파일."""
        if not LANGGRAPH_AVAILABLE:
            logger.warning("[EditorialGraph] langgraph 미설치: fallback loop로 실행합니다.")
            return _FallbackEditorialGraph(self)

        builder = StateGraph(EditorialState)

        builder.add_node("reviewer", self._reviewer_node)
        builder.add_node("rewriter", self._rewriter_node)

        builder.add_edge(START, "reviewer")

        def route_after_review(state: EditorialState) -> str:
            avg = state.get("avg_score", 0.0)
            threshold = state.get("threshold", 5.0)
            iteration = state.get("iteration", 0)

            if avg >= threshold:
                return END

            # 최대 2회 리라이트(iteration) 허용
            if iteration >= 2:
                return END

            if not state.get("rewritten_candidate", "").strip():
                return END

            return "rewriter"

        builder.add_conditional_edges("reviewer", route_after_review, {END: END, "rewriter": "rewriter"})
        builder.add_edge("rewriter", "reviewer")

        return builder.compile()

    async def _reviewer_node(self, state: EditorialState) -> dict:
        """Evaluator 노드: 초안을 평가하고 점수와 캔디데이트를 생성합니다."""
        platform = state["platform"]
        draft_text = state["draft_text"]
        post_data = state["post_data"]

        prompt = self._build_review_prompt(platform, draft_text, post_data)

        try:
            result = await self._call_llm(prompt)
        except Exception as exc:
            logger.warning("[EditorialGraph] Review failure, breaking loop: %s", exc)
            return {"avg_score": 10.0, "rewritten_candidate": ""}  # Break loop smoothly

        scores = result.get("scores", {})
        for key in ("hook", "specificity", "voice", "engagement", "readability"):
            val = scores.get(key, 5)
            scores[key] = max(1, min(10, int(val)))

        suggestions = result.get("suggestions", [])
        avg = sum(scores.values()) / max(len(scores), 1)
        rewritten = result.get("rewritten", "")

        return {"scores": scores, "suggestions": suggestions, "avg_score": avg, "rewritten_candidate": rewritten}

    async def _rewriter_node(self, state: EditorialState) -> dict:
        """Optimizer 노드: 캔디데이트를 현재 초안으로 승격시키고 다음 반복 진행."""
        rewritten = state.get("rewritten_candidate", "")
        iteration = state.get("iteration", 0)

        logger.info(
            "[EditorialGraph] %s 리라이트 적용 (점수=%.1f < 임계값=%.1f), 루프=%d",
            state["platform"],
            state.get("avg_score", 0.0),
            state.get("threshold", 5.0),
            iteration + 1,
        )

        return {"draft_text": rewritten.strip(), "iteration": iteration + 1}

    def _get_threshold(self, platform: str, topic_cluster: str = "") -> float:
        """P1-3: 토픽/플랫폼별 동적 에디토리얼 임계값 반환."""
        if self._editorial_thresholds and topic_cluster:
            topic_overrides = self._editorial_thresholds.get("topic_overrides", {})
            topic_val = topic_overrides.get(topic_cluster, {}).get(platform)
            if topic_val is not None:
                return float(topic_val)
        if self._editorial_thresholds:
            defaults = self._editorial_thresholds.get("defaults", {})
            default_val = defaults.get(platform)
            if default_val is not None:
                return float(default_val)
        return _REWRITE_THRESHOLD

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
토픽: {profile.get("topic_cluster", "기타")}
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
  "rewritten": "평균 5점 미만일 경우에만 리라이트한 전체 초안. 5점 이상이면 빈 문자열. 리라이트 시에도 원본의 자연스러운 톤을 유지하세요."
}}"""

    async def _call_gemini_api(self, prompt: str, api_key: str, model: str) -> str:
        """Gemini REST API 호출 → 텍스트 응답 반환."""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.3, "responseMimeType": "application/json"},
        }
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                url,
                params={"key": api_key},
                json=payload,
                headers={"Content-Type": "application/json"},
            ) as response:
                text_body = await response.text()
                if response.status >= 400:
                    raise RuntimeError(f"Gemini API {response.status}: {text_body[:200]}")
                data = json.loads(text_body)
        candidates = data.get("candidates", [])
        if not candidates:
            raise RuntimeError("Gemini returned no candidates")
        parts = candidates[0].get("content", {}).get("parts", [])
        return "".join(part.get("text", "") for part in parts if part.get("text"))

    async def _call_openai_compatible_api(self, prompt: str, api_key: str, model: str, base_url: str) -> str:
        """OpenAI-compatible REST API 호출 (DeepSeek, xAI 등) → 텍스트 응답 반환."""
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
        }
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                base_url,
                json=payload,
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
            ) as response:
                text_body = await response.text()
                if response.status >= 400:
                    raise RuntimeError(f"{base_url} API {response.status}: {text_body[:200]}")
                data = json.loads(text_body)
        choices = data.get("choices", [])
        if not choices:
            raise RuntimeError(f"No choices from {base_url}")
        return choices[0].get("message", {}).get("content", "")

    async def _call_llm(self, prompt: str) -> dict:
        """Multi-provider fallback으로 LLM 호출 → JSON dict 반환."""
        if not self._providers:
            raise RuntimeError("No editorial review providers available")

        last_error = None
        for provider in self._providers:
            name = provider["name"]
            try:
                if name == "gemini":
                    raw_text = await self._call_gemini_api(
                        prompt,
                        provider["api_key"],
                        provider["model"],
                    )
                else:
                    pc = _PROVIDER_CONFIGS[name]
                    raw_text = await self._call_openai_compatible_api(
                        prompt,
                        provider["api_key"],
                        provider["model"],
                        pc["base_url"],
                    )
                # JSON 추출 (마크다운 코드블록 안에 있을 수 있음)
                json_match = re.search(r"\{[\s\S]*\}", raw_text)
                if not json_match:
                    raise RuntimeError(f"{name} returned non-JSON: {raw_text[:200]}")
                logger.info("[Editorial] LLM provider used: %s", name)
                return json.loads(json_match.group())
            except Exception as exc:
                last_error = exc
                logger.warning("[Editorial] %s failed, trying next: %s", name, exc)

        raise RuntimeError(f"All editorial providers failed. Last: {last_error}")

    async def _review_single_platform(
        self,
        platform: str,
        draft_text: str,
        post_data: dict[str, Any],
    ) -> tuple[str, dict[str, int], list[str]]:
        """단일 플랫폼 초안을 LangGraph 루프로 평가 및 리라이트하여 (최종 텍스트, 점수, 제안) 반환."""
        profile = post_data.get("content_profile", {}) or {}
        topic_cluster = profile.get("topic_cluster", "")
        threshold = self._get_threshold(platform, topic_cluster)

        initial_state = {
            "platform": platform,
            "draft_text": draft_text,
            "post_data": post_data,
            "scores": {},
            "suggestions": [],
            "rewritten_candidate": "",
            "avg_score": 0.0,
            "iteration": 0,
            "threshold": threshold,
        }

        # Graph invoke으로 리뷰 및 리라이트 루프 수행
        final_state = await self._graph.ainvoke(initial_state)

        return (
            final_state.get("draft_text", draft_text),
            final_state.get("scores", {}),
            final_state.get("suggestions", []),
        )

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
        if not self._providers:
            logger.debug("Editorial review skipped: no LLM providers available")
            return EditorialResult(
                polished_drafts=dict(drafts),
                original_drafts=dict(drafts),
            )

        result = EditorialResult(original_drafts={})
        all_scores: dict[str, int] = {}
        all_suggestions: list[str] = []

        # 플랫폼별 초안만 필터링 (내부 메타 키 제외)
        bundle = split_draft_bundle(drafts)
        platform_drafts = {k: v for k, v in bundle["publishable"].items() if isinstance(v, str) and v.strip()}

        for platform, draft_text in platform_drafts.items():
            result.original_drafts[platform] = draft_text
            try:
                polished, scores, suggestions = await self._review_single_platform(
                    platform,
                    draft_text,
                    post_data,
                )
                result.polished_drafts[platform] = polished
                # 점수는 플랫폼별로 저장
                for dim, val in scores.items():
                    all_scores[f"{platform}_{dim}"] = val
                all_suggestions.extend(f"[{platform}] {s}" for s in suggestions)
            except Exception as exc:
                logger.warning("[Editorial] %s review failed (using original): %s", platform, exc)
                result.polished_drafts[platform] = draft_text

        # 내부 메타 키 보존 (_regulation_check 등)
        for section_name in ("auxiliary", "review_meta", "internal", "other"):
            result.polished_drafts.update(bundle[section_name])

        result.scores = all_scores
        result.suggestions = all_suggestions
        result.avg_score = sum(all_scores.values()) / max(len(all_scores), 1) if all_scores else 0.0

        # ── 텍스트 후처리: 맞춤법 + 띄어쓰기 교정 (kiwipiepy) ────────
        # twitter/threads는 구어체·비격식 톤이 핵심이므로 polisher 적용하지 않음
        # (polisher가 구어체를 교정하면 부자연스러워짐)
        _SKIP_POLISH_PLATFORMS = {"twitter", "threads"}
        try:
            from pipeline.text_polisher import TextPolisher

            polisher = TextPolisher()
            if polisher.available:
                for platform, draft_text in list(result.polished_drafts.items()):
                    if platform.startswith("_") or not isinstance(draft_text, str):
                        continue
                    if not is_publishable_draft_key(platform):
                        continue
                    if platform in _SKIP_POLISH_PLATFORMS:
                        logger.debug("[TextPolish] Skipping %s (casual tone preserved)", platform)
                        continue
                    pr = polisher.polish(draft_text)
                    result.polished_drafts[platform] = pr.text
                    if pr.corrections_made > 0:
                        logger.info(
                            "[TextPolish] %s: %d corrections, readability=%.1f",
                            platform,
                            pr.corrections_made,
                            pr.readability,
                        )
        except Exception as exc:
            logger.debug("Text polishing skipped: %s", exc)

        logger.info(
            "[Editorial] Review complete: avg=%.1f, platforms=%d, suggestions=%d",
            result.avg_score,
            len(platform_drafts),
            len(all_suggestions),
        )
        return result
