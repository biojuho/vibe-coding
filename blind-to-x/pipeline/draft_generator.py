"""Draft generation with multi-provider fallback support."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import re
from pathlib import Path
from typing import Any

import aiohttp
from anthropic import AsyncAnthropic
from openai import AsyncOpenAI

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]

from pipeline.draft_cache import DraftCache
from pipeline.regulation_checker import RegulationChecker

# ── classification_rules.yaml 로더 ──────────────────────────────────
_RULES_FILE = Path(__file__).parent.parent / "classification_rules.yaml"
_draft_rules_cache: dict | None = None


def _load_draft_rules() -> dict:
    """classification_rules.yaml을 1회 로드 후 캐시. 실패 시 빈 dict."""
    global _draft_rules_cache
    if _draft_rules_cache is not None:
        return _draft_rules_cache
    if yaml is None or not _RULES_FILE.exists():
        _draft_rules_cache = {}
        return _draft_rules_cache
    try:
        with open(_RULES_FILE, encoding="utf-8") as f:
            _draft_rules_cache = yaml.safe_load(f) or {}
    except Exception:
        _draft_rules_cache = {}
    return _draft_rules_cache

logger = logging.getLogger(__name__)

PROVIDER_ALIASES = {
    "claude": "anthropic",
    "anthropic": "anthropic",
    "gemini": "gemini",
    "grok": "xai",
    "xai": "xai",
    "chatgpt": "openai",
    "openai": "openai",
    "ollama": "ollama",
}

DEFAULT_PROVIDER_ORDER = ["anthropic", "gemini", "xai", "openai", "ollama"]


class TweetDraftGenerator:
    def __init__(self, config, cost_tracker=None):
        self.config = config
        self.cost_tracker = cost_tracker

        style = config.get("tweet_style", {})
        self.tone = style.get("tone", "위트 있고 공감 가는")
        self.max_length = style.get("max_length", 280)

        # Threads 스타일 설정
        threads_style = config.get("threads_style", {})
        self.threads_tone = threads_style.get("tone", "캐주얼하고 공감 가능한")
        self.threads_max_length = threads_style.get("max_length", 500)
        self.threads_hashtags_count = threads_style.get("hashtags_count", 3)

        # 네이버 블로그 스타일 설정
        blog_style = config.get("naver_blog_style", {})
        self.blog_tone = blog_style.get("tone", "정보성 있고 검색 친화적인")
        self.blog_min_length = blog_style.get("min_length", 1500)
        self.blog_max_length = blog_style.get("max_length", 3000)
        self.blog_seo_tags_count = blog_style.get("seo_tags_count", 15)

        self.provider_order = self._resolve_provider_order()
        self.provider_strategy = config.get("llm.strategy", "fallback")
        self.max_retries_per_provider = int(config.get("llm.max_retries_per_provider", 2))
        self.request_timeout_seconds = int(config.get("llm.request_timeout_seconds", 45))

        self.anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY") or config.get("anthropic.api_key")
        self.openai_api_key = os.environ.get("OPENAI_API_KEY") or config.get("openai.api_key")
        self.gemini_api_key = (
            os.environ.get("GEMINI_API_KEY")
            or os.environ.get("GOOGLE_API_KEY")
            or config.get("gemini.api_key")
        )
        self.xai_api_key = (
            os.environ.get("XAI_API_KEY")
            or os.environ.get("GROK_API_KEY")
            or config.get("xai.api_key")
        )

        self.anthropic_model = config.get("anthropic.model", "claude-haiku-4-5-20251001")
        self.openai_model = config.get("openai.chat_model", "gpt-4.1-mini")
        self.gemini_model = config.get("gemini.model", "gemini-2.5-flash")
        self.xai_model = config.get("xai.model", "grok-4-1-fast-reasoning")
        self.ollama_model = config.get("ollama.model", "gemma3:4b")
        self.ollama_base_url = config.get("ollama.base_url", "http://localhost:11434/v1")

        self.anthropic_enabled = self._provider_enabled("anthropic", self.anthropic_api_key)
        self.openai_enabled = self._provider_enabled("openai", self.openai_api_key)
        self.gemini_enabled = self._provider_enabled("gemini", self.gemini_api_key)
        self.xai_enabled = self._provider_enabled("xai", self.xai_api_key)
        self.ollama_enabled = self._check_ollama_enabled()

        self.anthropic_client = AsyncAnthropic(api_key=self.anthropic_api_key) if self.anthropic_enabled else None
        self.openai_client = AsyncOpenAI(api_key=self.openai_api_key) if self.openai_enabled else None
        self.xai_client = (
            AsyncOpenAI(api_key=self.xai_api_key, base_url="https://api.x.ai/v1")
            if self.xai_enabled
            else None
        )
        self.ollama_client = (
            AsyncOpenAI(api_key="ollama", base_url=self.ollama_base_url)
            if self.ollama_enabled
            else None
        )

        # P7: 규제 점검 시스템
        self.regulation_checker = RegulationChecker(config=config)

    def _resolve_provider_order(self) -> list[str]:
        configured = self.config.get("llm.providers", None)
        if not configured:
            return DEFAULT_PROVIDER_ORDER

        normalized = []
        for provider in configured:
            provider_name = PROVIDER_ALIASES.get(str(provider).strip().lower())
            if provider_name and provider_name not in normalized:
                normalized.append(provider_name)
        return normalized or DEFAULT_PROVIDER_ORDER

    def _provider_enabled(self, provider: str, api_key: str | None) -> bool:
        if provider == "openai":
            explicit = self.config.get("openai.chat_enabled", None)
            if explicit is None:
                explicit = self.config.get("openai.enabled", None)
        else:
            explicit = self.config.get(f"{provider}.enabled", None)
        if explicit is None:
            explicit = True
        return bool(explicit and api_key)

    def _check_ollama_enabled(self) -> bool:
        """Ollama 서비스가 로컬에서 실행 중인지 확인. 미실행 시 자동 비활성화."""
        explicit = self.config.get("ollama.enabled", None)
        if explicit is False:
            return False
        try:
            import urllib.request
            req = urllib.request.Request("http://localhost:11434/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=2) as resp:
                return resp.status == 200
        except Exception:
            logger.debug("Ollama not available at localhost:11434 — disabled as fallback.")
            return False

    def _resolve_tone(self, post_data: dict[str, Any]) -> str:
        """토픽 클러스터 기반 톤 매핑 (YAML 기반, fallback 포함)."""
        # 1. 토픽 클러스터에서 YAML tone_mapping 조회
        profile = post_data.get("content_profile", {}) or {}
        topic_cluster = profile.get("topic_cluster", "")
        rules = _load_draft_rules()
        tone_map = rules.get("tone_mapping", {})
        if topic_cluster and topic_cluster in tone_map:
            return tone_map[topic_cluster]

        # 2. 기존 카테고리 기반 fallback
        category = post_data.get("category", "general")
        _CATEGORY_TONES = {
            "relationship": "친구에게 말하듯 다정하고 공감이 강한 톤",
            "money": "인사이트와 팩트를 섞어 정리하는 톤",
            "career": "직장인에게 실질적인 도움을 주는 조언형 톤",
            "work-life": "직장 밈과 현실 공감을 섞은 톤",
            "family": "담백하지만 울림이 있는 톤",
        }
        if category in _CATEGORY_TONES:
            return _CATEGORY_TONES[category]

        # 3. YAML 기타 톤 or 기본 톤
        return tone_map.get("기타", self.tone)

    @staticmethod
    def _format_examples(
        top_examples: list[dict[str, Any]] | None,
        topic_cluster: str = "",
    ) -> str:
        """성과 우수 예시 포맷팅. YAML 골든 예시도 자동 병합."""
        merged: list[dict[str, Any]] = []

        # 1. YAML 골든 예시에서 해당 토픽 예시 로드
        rules = _load_draft_rules()
        golden = rules.get("golden_examples", {})
        if topic_cluster and topic_cluster in golden:
            for ge in golden[topic_cluster]:
                merged.append({
                    "views": "(골든 예시)",
                    "topic_cluster": topic_cluster,
                    "hook_type": ge.get("hook_type", "공감형"),
                    "emotion_axis": "-",
                    "draft_style": ge.get("hook_type", "공감형"),
                    "text": ge.get("text", ""),
                    "grade": ge.get("grade", ""),
                })

        # 2. 실시간 성과 예시 추가
        if top_examples:
            merged.extend(top_examples)

        if not merged:
            return ""

        lines = [
            "[성과 우수 레퍼런스]",
            "아래는 높은 성과를 기록한 예시입니다. 말투, 훅, 마무리 질문 방식을 참고하세요.",
        ]
        for index, example in enumerate(merged, start=1):
            grade = f" [등급: {example['grade']}]" if example.get("grade") else ""
            lines.extend(
                [
                    f"- 예시 {index}{grade}",
                    f"  조회수: {example.get('views', 0)}",
                    f"  토픽: {example.get('topic_cluster', '기타')}",
                    f"  훅: {example.get('hook_type', '공감형')}",
                    f"  감정: {example.get('emotion_axis', '공감')}",
                    f"  추천 초안 타입: {example.get('draft_style', '공감형')}",
                    f"  본문: {str(example.get('text', '')).strip()}",
                ]
            )
        return "\n".join(lines)

    def _build_prompt(
        self,
        post_data: dict[str, Any],
        top_examples: list[dict[str, Any]] | None,
        output_formats: list[str],
        draft_format: str = "standard",
    ) -> str:
        """YAML 기반 프롬프트 조립. YAML 로드 실패 시 하드코딩 fallback."""
        content = str(post_data.get("content", ""))
        if len(content) > 700:
            logger.info("Content truncated from %s chars to 700 for API prompt.", len(content))
            content = f"{content[:700]}..."

        source = post_data.get("source", "블라인드")
        tone = self._resolve_tone(post_data)
        profile = post_data.get("content_profile", {}) or {}
        topic_cluster = profile.get("topic_cluster", "기타")
        recommended_draft_type = profile.get("recommended_draft_type", "공감형")

        rules = _load_draft_rules()
        templates = rules.get("prompt_templates", {})
        system_role = templates.get(
            "system_role",
            "당신은 직장인 대상 콘텐츠를 큐레이션하는 시니어 에디터입니다."
        )

        # ── Twitter 블록 (YAML 템플릿 우선) ────────────────────────────
        twitter_block = ""
        if "twitter" in output_formats:
            twitter_templates = templates.get("twitter", {})
            if draft_format == "thread" and "thread" in twitter_templates:
                twitter_block = twitter_templates["thread"].format(
                    source=source,
                    recommended_draft_type=recommended_draft_type,
                )
            elif "standard" in twitter_templates:
                twitter_block = twitter_templates["standard"].format(
                    max_length=self.max_length,
                    source=source,
                    recommended_draft_type=recommended_draft_type,
                )
            else:
                # Hardcoded fallback
                twitter_block = f"""\n[트위터(X) 초안 작성 조건]
1. 아래 3가지 초안을 모두 작성하세요.
   - [공감형 트윗]
   - [논쟁형 트윗]
   - [정보전달형 트윗]
2. 각 초안은 {self.max_length}자 이내로 작성하세요.
3. 출처가 '{source}'임을 자연스럽게 드러내세요.
4. 추천 초안 타입은 '{recommended_draft_type}'입니다. 이 타입은 가장 강하게 만드세요.
5. 마지막 문장은 댓글이나 인용을 유도하는 질문 또는 한 줄 코멘트로 마무리하세요.
6. 반드시 <twitter> 와 </twitter> 태그 안에만 작성하세요.
"""

        # ── Newsletter 블록 (YAML 템플릿 우선) ────────────────────────
        newsletter_block = ""
        if "newsletter" in output_formats:
            nl_tmpl = templates.get("newsletter", "")
            newsletter_block = nl_tmpl if nl_tmpl else """\n[뉴스레터 초안 작성 조건]
1. 한 문단 요약, 인사이트, 한 줄 결론 구조로 작성하세요.
2. 450자 이상 900자 이하로 작성하세요.
3. 직장인 독자가 읽는다는 전제로 해석과 시사점을 덧붙이세요.
4. 반드시 <newsletter> 와 </newsletter> 태그 안에만 작성하세요.
"""

        # ── Threads 블록 ──────────────────────────────────────────────
        threads_block = ""
        if "threads" in output_formats:
            threads_tmpl = templates.get("threads", "")
            # P6: classification_rules.yaml에서 토픽별 Threads 톤 로드
            threads_tone_map = rules.get("tone_mapping_threads", {})
            resolved_threads_tone = threads_tone_map.get(topic_cluster, threads_tone_map.get("기타", self.threads_tone))
            if threads_tmpl:
                try:
                    threads_block = threads_tmpl.format(
                        threads_tone=resolved_threads_tone,
                        source=source,
                        recommended_draft_type=recommended_draft_type,
                    )
                except (KeyError, IndexError):
                    threads_block = threads_tmpl
            else:
                threads_block = f"""\n[Threads 초안 작성 조건]
1. {self.threads_max_length}자 이내의 캐주얼하고 대화체 스타일로 작성하세요.
2. 인스타그램 감성에 가까운 친근한 톤을 사용하세요.
3. 트위터보다 여유 있게 스토리텔링하되, 핵심을 빠르게 전달하세요.
4. 해시태그를 {self.threads_hashtags_count}개 이내로 자연스럽게 문장 끝에 배치하세요.
5. 마지막 문장은 댓글이나 저장을 유도하는 가벼운 질문으로 끝내세요.
6. 출처가 '{source}'임을 자연스럽게 언급하세요.
7. 추천 초안 타입은 '{recommended_draft_type}'입니다.
8. 참고 톤: '{resolved_threads_tone}'
9. 반드시 <threads> 와 </threads> 태그 안에만 작성하세요.
"""

        # ── 네이버 블로그 블록 ─────────────────────────────────────────
        naver_blog_block = ""
        if "naver_blog" in output_formats:
            blog_tmpl = templates.get("naver_blog", "")
            # P6: classification_rules.yaml에서 토픽별 네이버 블로그 톤 로드
            blog_tone_map = rules.get("tone_mapping_naver_blog", {})
            resolved_blog_tone = blog_tone_map.get(topic_cluster, blog_tone_map.get("기타", self.blog_tone))
            if blog_tmpl:
                try:
                    naver_blog_block = blog_tmpl.format(
                        naver_blog_tone=resolved_blog_tone,
                        source=source,
                        recommended_draft_type=recommended_draft_type,
                    )
                except (KeyError, IndexError):
                    naver_blog_block = blog_tmpl
            else:
                naver_blog_block = f"""\n[네이버 블로그 초안 작성 조건]
1. {self.blog_min_length}자 이상 {self.blog_max_length}자 이하로 작성하세요.
2. 검색 친화적(SEO)인 구조로 작성하세요: 명확한 소제목(##) + 본문 + 결론.
3. 독자에게 정보를 전달하는 톤으로, 직장인 경험을 바탕으로 한 인사이트를 포함하세요.
4. 본문 끝에 태그를 {self.blog_seo_tags_count}개 작성하세요 (예: #직장인 #연봉 #이직 ...).
5. 이웃추가나 공감(좋아요)을 유도하는 CTA 문장을 포함하세요.
6. 출처가 '{source}'임을 서두 또는 본문에서 간접적으로 언급하세요.
7. 추천 초안 타입은 '{recommended_draft_type}'입니다.
8. 참고 톤: '{resolved_blog_tone}'
9. 반드시 <naver_blog> 와 </naver_blog> 태그 안에만 작성하세요.
"""

        # ── Image prompt 블록 (YAML 템플릿 우선) ──────────────────────
        img_tmpl = templates.get("image_prompt", "")
        image_block = img_tmpl if img_tmpl else """[이미지 프롬프트 작성 조건]
1. 마지막에 영어 이미지 프롬프트를 작성하세요.
2. 텍스트 없는 장면 중심 이미지여야 합니다.
3. 직장인 커뮤니티 상황이 한눈에 보이게 묘사하세요.
4. 반드시 <image_prompt> 와 </image_prompt> 태그 안에만 작성하세요.
"""

        # ── P7: 규제 컨텍스트 자동 주입 ────────────────────────────────
        regulation_context = ""
        try:
            regulation_context = self.regulation_checker.build_regulation_context(
                platforms=[fmt for fmt in output_formats if fmt in ("twitter", "threads", "naver_blog")]
            )
        except Exception as exc:
            logger.debug("Failed to build regulation context (ignored): %s", exc)

        # P7: 자체 검증 리포트 요청 블록
        regulation_check_block = ""
        if regulation_context:
            regulation_check_block = """\n[자체 규제 검증 리포트 작성 조건]
1. 각 플랫폼 초안 작성 후, 아래 형식의 자체 검증 리포트를 반드시 작성하세요.
2. 반드시 <regulation_check> 와 </regulation_check> 태그 안에만 작성하세요.
3. 형식:
   ✅ 또는 ⚠️ | 플랫폼명 | 검증 항목 | 결과 설명
   예시:
   ✅ X | 글자 수 | 267자 (280자 이내 준수)
   ⚠️ Threads | 외부 링크 | 링크 1개 발견 — 댓글로 분리 권장
"""

        examples_block = self._format_examples(top_examples, topic_cluster=topic_cluster)
        return f"""{system_role}
아래 게시글을 기반으로 발행 가능한 초안을 작성하세요.

[게시글 정보]
출처: {source}
제목: {post_data.get('title', '')}
본문: {content}
카테고리: {post_data.get('category', 'general')}
공감수: {post_data.get('likes', 0)} | 댓글수: {post_data.get('comments', 0)}

[콘텐츠 프로필]
토픽 클러스터: {topic_cluster}
훅 타입: {profile.get('hook_type', '공감형')}
감정 축: {profile.get('emotion_axis', '공감')}
대상 독자: {profile.get('audience_fit', '범용')}
추천 초안 타입: {recommended_draft_type}
발행 적합도 점수: {profile.get('publishability_score', 0)}
성과 예측 점수: {profile.get('performance_score', 0)}
{regulation_context}
{examples_block}
{twitter_block}
{threads_block}
{newsletter_block}
{naver_blog_block}
{image_block}
{regulation_check_block}
[톤 가이드]
{tone}
"""

    def _enabled_providers(self) -> list[str]:
        availability = {
            "anthropic": self.anthropic_enabled,
            "gemini": self.gemini_enabled,
            "xai": self.xai_enabled,
            "openai": self.openai_enabled,
            "ollama": self.ollama_enabled,
        }
        return [provider for provider in self.provider_order if availability.get(provider, False)]

    async def _generate_with_anthropic(self, prompt: str) -> tuple[str, int, int]:
        response = await self.anthropic_client.messages.create(
            model=self.anthropic_model,
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text
        input_tokens = getattr(response.usage, "input_tokens", 0)
        output_tokens = getattr(response.usage, "output_tokens", 0)
        return text, input_tokens, output_tokens

    async def _generate_with_openai(self, prompt: str) -> tuple[str, int, int]:
        response = await self.openai_client.responses.create(
            model=self.openai_model,
            input=prompt,
        )
        text = getattr(response, "output_text", "") or ""
        usage = getattr(response, "usage", None)
        input_tokens = getattr(usage, "input_tokens", 0) if usage else 0
        output_tokens = getattr(usage, "output_tokens", 0) if usage else 0
        return text, input_tokens, output_tokens

    async def _generate_with_xai(self, prompt: str) -> tuple[str, int, int]:
        response = await self.xai_client.chat.completions.create(
            model=self.xai_model,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.choices[0].message.content or ""
        usage = getattr(response, "usage", None)
        input_tokens = getattr(usage, "prompt_tokens", 0) if usage else 0
        output_tokens = getattr(usage, "completion_tokens", 0) if usage else 0
        return text, input_tokens, output_tokens

    async def _generate_with_ollama(self, prompt: str) -> tuple[str, int, int]:
        """Ollama 로컬 LLM으로 초안 생성 (OpenAI 호환 API, CPU 추론)."""
        response = await self.ollama_client.chat.completions.create(
            model=self.ollama_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        text = response.choices[0].message.content or ""
        usage = getattr(response, "usage", None)
        input_tokens = getattr(usage, "prompt_tokens", 0) if usage else 0
        output_tokens = getattr(usage, "completion_tokens", 0) if usage else 0
        return text, input_tokens, output_tokens

    async def _generate_with_gemini(self, prompt: str) -> tuple[str, int, int]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.gemini_model}:generateContent"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.7},
        }
        timeout = aiohttp.ClientTimeout(total=self.request_timeout_seconds)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                url,
                params={"key": self.gemini_api_key},
                json=payload,
                headers={"Content-Type": "application/json"},
            ) as response:
                text_body = await response.text()
                if response.status >= 400:
                    raise RuntimeError(f"Gemini API error {response.status}: {text_body}")
                data = json.loads(text_body)

        candidates = data.get("candidates", [])
        if not candidates:
            raise RuntimeError(f"Gemini returned no candidates: {data}")

        parts = candidates[0].get("content", {}).get("parts", [])
        text = "".join(part.get("text", "") for part in parts if part.get("text"))
        usage = data.get("usageMetadata", {}) or {}
        input_tokens = int(usage.get("promptTokenCount", 0) or 0)
        output_tokens = int(usage.get("candidatesTokenCount", 0) or 0)
        return text, input_tokens, output_tokens

    def _timeout_for(self, provider: str) -> int:
        """프로바이더별 차등 타임아웃: 유료 45s, 무료/저렴 30s, Ollama(CPU) 90s."""
        if provider == "ollama":
            return 90  # CPU 추론은 느림 → 넉넉한 타임아웃
        if provider in {"anthropic", "openai"}:
            return self.request_timeout_seconds
        return min(30, self.request_timeout_seconds)

    async def _generate_once(self, provider: str, prompt: str) -> tuple[str, int, int]:
        timeout = self._timeout_for(provider)
        coro = None
        if provider == "anthropic":
            coro = self._generate_with_anthropic(prompt)
        elif provider == "openai":
            coro = self._generate_with_openai(prompt)
        elif provider == "gemini":
            coro = self._generate_with_gemini(prompt)
        elif provider == "xai":
            coro = self._generate_with_xai(prompt)
        elif provider == "ollama":
            coro = self._generate_with_ollama(prompt)
        else:
            raise RuntimeError(f"Unsupported provider: {provider}")
        return await asyncio.wait_for(coro, timeout=timeout)

    def _parse_response(self, response_text: str, output_formats: list[str], provider_used: str) -> tuple[dict[str, str], str | None]:
        drafts_dict: dict[str, str] = {"_provider_used": provider_used}

        # ── 스레드형 파싱 (P0-A1) ──────────────────────────────────────
        thread_match = re.search(r"<twitter_thread>(.*?)</twitter_thread>", response_text, re.DOTALL)
        if thread_match:
            drafts_dict["twitter_thread"] = thread_match.group(1).strip()
            # 스레드 내용을 twitter 키에도 넣어 호환성 유지
            if "twitter" in output_formats:
                drafts_dict["twitter"] = thread_match.group(1).strip()

        # ── 기존 트위터 파싱 ───────────────────────────────────────────
        twitter_match = re.search(r"<twitter>(.*?)</twitter>", response_text, re.DOTALL)
        if twitter_match and "twitter" not in drafts_dict:
            drafts_dict["twitter"] = twitter_match.group(1).strip()
        elif "twitter" in output_formats and "twitter" not in drafts_dict:
            drafts_dict["twitter"] = response_text.strip()

        newsletter_match = re.search(r"<newsletter>(.*?)</newsletter>", response_text, re.DOTALL)
        if newsletter_match:
            drafts_dict["newsletter"] = newsletter_match.group(1).strip()

        # ── Threads 파싱 ──────────────────────────────────────────────
        threads_match = re.search(r"<threads>(.*?)</threads>", response_text, re.DOTALL)
        if threads_match:
            drafts_dict["threads"] = threads_match.group(1).strip()

        # ── 네이버 블로그 파싱 ────────────────────────────────────────
        naver_blog_match = re.search(r"<naver_blog>(.*?)</naver_blog>", response_text, re.DOTALL)
        if naver_blog_match:
            drafts_dict["naver_blog"] = naver_blog_match.group(1).strip()

        image_prompt = None
        prompt_match = re.search(r"<image_prompt>(.*?)</image_prompt>", response_text, re.DOTALL)
        if prompt_match:
            image_prompt = prompt_match.group(1).strip()

        # ── P7: 규제 검증 리포트 파싱 ─────────────────────────────────
        regulation_match = re.search(r"<regulation_check>(.*?)</regulation_check>", response_text, re.DOTALL)
        if regulation_match:
            drafts_dict["_regulation_check"] = regulation_match.group(1).strip()

        if "twitter" in output_formats and "twitter" not in drafts_dict:
            if prompt_match:
                drafts_dict["twitter"] = response_text.replace(prompt_match.group(0), "").strip()
            else:
                drafts_dict["twitter"] = response_text.strip()

        return drafts_dict, image_prompt

    def _make_cache_key(self, post_data: dict[str, Any], output_formats: list[str]) -> str:
        """Generate a stable cache key from post title + category + output formats."""
        title = str(post_data.get("title", ""))
        category = str(post_data.get("category", ""))
        source = str(post_data.get("source", ""))
        fmt_str = ",".join(sorted(output_formats))
        raw = f"{title}|{category}|{source}|{fmt_str}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    async def generate_drafts(self, post_data, top_tweets=None, output_formats=None):
        if output_formats is None:
            output_formats = ["twitter"]

        # ── 드래프트 캐시 조회 (동일 포스트 재생성 방지) ───────────────
        cache_key = self._make_cache_key(post_data, output_formats)
        try:
            _cache = DraftCache()
            cached = _cache.get(cache_key)
            if cached:
                drafts, image_prompt = cached
                logger.info("Draft cache HIT: %s (provider=%s)", cache_key[:12], drafts.get("_provider_used", "cached"))
                return drafts, image_prompt
        except Exception as exc:
            logger.debug("Draft cache lookup failed (ignored): %s", exc)

        prompt = self._build_prompt(post_data, top_tweets, output_formats)
        providers = self._enabled_providers()

        # ── 실패 이력 기반 provider 스킵 ──────────────────────────────
        try:
            from pipeline.cost_db import get_cost_db
            _cost_db = get_cost_db()
            skipped = _cost_db.get_skipped_providers() if _cost_db else set()
            if skipped:
                before = len(providers)
                providers = [p for p in providers if p not in skipped]
                if len(providers) < before:
                    logger.info("Skipping providers with recent failures: %s", skipped)
        except Exception:
            pass

        if not providers:
            logger.error("No enabled LLM providers available for draft generation.")
            return {"twitter": "No enabled LLM providers available."}, None

        provider_errors = []
        for provider in providers:
            for attempt in range(1, self.max_retries_per_provider + 1):
                try:
                    logger.info("Generating drafts via %s (%s/%s)...", provider, attempt, self.max_retries_per_provider)
                    response_text, input_tokens, output_tokens = await self._generate_once(provider, prompt)
                    if self.cost_tracker:
                        self.cost_tracker.add_text_generation_cost(
                            provider,
                            input_tokens=input_tokens,
                            output_tokens=output_tokens,
                        )
                    drafts_dict, image_prompt = self._parse_response(response_text, output_formats, provider)
                    logger.info("Successfully generated drafts using %s.", provider)

                    # ── 캐시 저장 + circuit breaker close ─────────────
                    try:
                        _cache = DraftCache()
                        _cache.set(cache_key, drafts_dict, image_prompt, provider=provider)
                    except Exception:
                        pass
                    try:
                        from pipeline.cost_db import get_cost_db
                        get_cost_db().record_provider_success(provider)
                    except Exception:
                        pass

                    return drafts_dict, image_prompt
                except Exception as exc:  # pragma: no cover - remote API dependent
                    provider_errors.append(f"{provider}: {exc}")
                    error_text = str(exc).lower()
                    non_retryable = any(
                        token in error_text
                        for token in (
                            "credit balance is too low",
                            "insufficient_quota",
                            "invalid api key",
                            "unauthorized",
                            "permission denied",
                        )
                    )
                    should_retry = attempt < self.max_retries_per_provider
                    if non_retryable:
                        should_retry = False
                        # circuit breaker: 비복구 에러 시 provider 스킵 등록
                        try:
                            from pipeline.cost_db import get_cost_db
                            _cdb = get_cost_db()
                            skip_h = _cdb.get_circuit_skip_hours(provider)
                            _cdb.record_provider_failure(provider, skip_hours=skip_h)
                        except Exception:
                            pass
                    wait_seconds = min(2**attempt, 10)
                    logger.warning(
                        "Draft generation failed via %s (%s/%s): %s",
                        provider,
                        attempt,
                        self.max_retries_per_provider,
                        exc,
                    )
                    if should_retry:
                        await asyncio.sleep(wait_seconds)
            logger.info("Provider %s exhausted. Trying next provider.", provider)

        error_text = " | ".join(provider_errors)
        logger.error("All providers failed for draft generation: %s", error_text)
        return {"twitter": f"Error generating drafts: {error_text}", "_provider_used": "none"}, None
