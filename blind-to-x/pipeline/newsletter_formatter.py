"""3-part newsletter formatter for blind-to-x content (Phase 4-D).

Transforms a raw Twitter draft into a structured newsletter piece:
    [HOOK]         — 주의를 사로잡는 첫 문장 (감정 + 맥락)
    [STORY]        — 핵심 내용 전개 (팩트 + 공감)
    [INSIGHT+CTA]  — 시사점 + 행동 유도

Supports two output modes:
    format_from_draft(draft_text, profile) — draft string → formatted dict
    format_with_llm(post_data, profile, generator) — LLM-powered enrichment

Usage:
    formatter = NewsletterFormatter()
    result = formatter.format_from_draft(twitter_draft, content_profile.to_dict())
    print(result["full_text"])   # 완성된 뉴스레터 본문
    print(result["hook"])        # HOOK 섹션만
"""

from __future__ import annotations

import logging
import re
import textwrap
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

# 뉴스레터 최소·최대 글자 수 기준
_MIN_CHARS = 300
_MAX_CHARS = 1000

# CTA 템플릿 (emotion_axis → CTA)
_CTA_BY_EMOTION: dict[str, str] = {
    "분노": "이런 상황, 여러분은 어떻게 대처하셨나요? 댓글로 경험 나눠주세요.",
    "허탈": "비슷한 허탈감 느끼신 분 계신가요? 같이 공감해봐요.",
    "공감": "같은 경험 있으신 분들, 댓글로 이야기해주세요. 우리 혼자가 아닙니다.",
    "웃김": "더 웃긴 직장 썰 있으신 분은 댓글로 제보해주세요 😂",
    "경악": "이게 실화라니… 여러분도 비슷한 경험 있으신가요?",
    "현타": "현타 오는 순간, 여러분은 어떻게 극복하시나요?",
    "통찰": "이 관점, 어떻게 생각하세요? 댓글로 의견 남겨주세요.",
    # P2-C1: 신규 감정 축 CTA
    "자부심": "이런 보람, 여러분도 느끼신 적 있나요? 자랑 좀 해주세요! 🏆",
    "불안": "같은 고민 하시는 분들, 함께 이야기 나눠볼까요?",
    "기대감": "기대되는 변화, 여러분은 어떻게 준비하고 계세요? 💪",
}
_DEFAULT_CTA = "직장인이라면 한 번쯤 공감할 이야기, 댓글로 함께 나눠요 💬"

# 인사이트 템플릿 (topic_cluster → 시사점 힌트)
_INSIGHT_BY_TOPIC: dict[str, str] = {
    "연봉": "연봉은 숫자가 아니라 나의 시장가치를 반영합니다.",
    "이직": "이직은 배신이 아닙니다. 성장을 선택하는 것입니다.",
    "회사문화": "조직 문화는 채용공고가 아닌 실제 구성원의 이야기에서 드러납니다.",
    "상사": "좋은 상사 하나가 커리어를 바꿉니다. 반대도 마찬가지입니다.",
    "복지": "복지는 숫자보다 철학입니다. 회사가 구성원을 어떻게 보는지를 보여줍니다.",
    "재테크": "월급만으로는 부족합니다. 자산을 키우는 습관이 필요합니다.",
    "직장개그": "웃을 수 있는 여유가 남아있다면, 아직 괜찮은 겁니다.",
    # P2-C1: 신규 토픽 인사이트
    "부동산": "내 집 마련은 연봉만큼이나 직장인의 큰 고민입니다. 전략이 필요합니다.",
    "IT": "기술 트렌드를 아는 직장인이 결국 살아남습니다. 꾸준히 업데이트하세요.",
    "건강": "건강은 최고의 복지입니다. 번아웃 전에 관리해야 합니다.",
    "정치": "정책 변화는 직장인의 삶에 직접적 영향을 미칩니다. 관심이 곧 경쟁력입니다.",
    "자기계발": "성장은 선택이 아닌 생존 전략입니다. 작은 루틴이 큰 차이를 만듭니다.",
}
_DEFAULT_INSIGHT = "직장 생활의 크고 작은 경험들이 결국 우리를 성장시킵니다."


@dataclass
class NewsletterResult:
    hook: str
    story: str
    insight: str
    cta: str
    full_text: str
    word_count: int
    char_count: int
    topic_cluster: str
    emotion_axis: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "hook": self.hook,
            "story": self.story,
            "insight": self.insight,
            "cta": self.cta,
            "full_text": self.full_text,
            "word_count": self.word_count,
            "char_count": self.char_count,
            "topic_cluster": self.topic_cluster,
            "emotion_axis": self.emotion_axis,
        }


def _clean_draft(text: str) -> str:
    """Draft 텍스트에서 태그, 이모지 과잉, 트위터 특수문자 정리."""
    # XML 태그 제거
    text = re.sub(r"<[^>]+>", "", text)
    # 해시태그 제거 (뉴스레터에서는 자연스럽지 않음)
    text = re.sub(r"#\w+", "", text)
    # 연속 공백 정리
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _extract_best_sentence(text: str, position: str = "first") -> str:
    """텍스트에서 훅/핵심 문장 추출."""
    sentences = [s.strip() for s in re.split(r"[.!?。\n]", text) if len(s.strip()) >= 10]
    if not sentences:
        return text[:100].strip()
    if position == "first":
        return sentences[0]
    if position == "last":
        return sentences[-1]
    # middle: longest sentence
    return max(sentences, key=len)


class NewsletterFormatter:
    """Transforms drafts into structured 3-part newsletter pieces."""

    def format_from_draft(
        self,
        draft_text: str,
        profile: dict[str, Any],
        post_data: dict[str, Any] | None = None,
    ) -> NewsletterResult:
        """Rule-based formatting (no LLM, always available).

        Args:
            draft_text: Raw draft string (Twitter or raw content).
            profile: ContentProfile.to_dict() output.
            post_data: Original post data for enrichment (optional).

        Returns:
            NewsletterResult with structured sections.
        """
        topic_cluster = profile.get("topic_cluster", "기타")
        emotion_axis = profile.get("emotion_axis", "공감")
        hook_type = profile.get("hook_type", "공감형")

        cleaned = _clean_draft(draft_text)
        title = str((post_data or {}).get("title", "")).strip() if post_data else ""
        content = str((post_data or {}).get("content", "")).strip() if post_data else ""

        # ── HOOK: 첫 문장 + 감정 강화 ──────────────────────────────
        hook_base = _extract_best_sentence(cleaned, "first")
        if not hook_base and title:
            hook_base = title[:80]
        if not hook_base:
            hook_base = cleaned[:80]

        # 훅 타입별 접두어 강화
        hook_intensifier = {
            "논쟁형": "솔직히 말하면, ",
            "공감형": "",
            "한줄팩폭형": "",
            "정보형": "알아두면 쓸데있는 직장 이야기: ",
            "짤형": "웃픈 직장 현실: ",
        }.get(hook_type, "")

        hook = f"{hook_intensifier}{hook_base}".strip()
        if len(hook) > 120:
            hook = hook[:117] + "…"

        # ── STORY: 본문 전개 ────────────────────────────────────────
        story_source = content if (content and len(content) > 50) else cleaned
        story_lines = [l.strip() for l in story_source.split("\n") if len(l.strip()) > 15]

        if len(story_lines) >= 2:
            story = "\n".join(story_lines[:5])  # 최대 5줄
        else:
            story = story_source[:400].strip()

        # 너무 짧으면 cleaned 에서 보충
        if len(story) < 80 and len(cleaned) > 80:
            story = cleaned[:350].strip()

        # 뉴스레터 줄 너비 맞춤
        story = textwrap.fill(story, width=60, break_long_words=False, break_on_hyphens=False)

        # ── INSIGHT: 시사점 ─────────────────────────────────────────
        insight = _INSIGHT_BY_TOPIC.get(topic_cluster, _DEFAULT_INSIGHT)

        # publishability·performance 점수 기반 인사이트 강화
        pub_score = float(profile.get("publishability_score", 0))
        rank_6d = float(profile.get("rank_6d", 0))
        if pub_score >= 80 or rank_6d >= 75:
            insight += " 오늘의 콘텐츠는 특히 높은 공감 잠재력을 가지고 있습니다."

        # ── CTA ─────────────────────────────────────────────────────
        cta = _CTA_BY_EMOTION.get(emotion_axis, _DEFAULT_CTA)

        # classification_rules.yaml의 topic_hooks CTA 우선 적용
        try:
            from pipeline.content_intelligence import get_topic_hook
            yaml_cta = get_topic_hook(topic_cluster).get("cta", "")
            if yaml_cta:
                cta = yaml_cta
        except Exception:
            pass

        # ── Assemble full text ──────────────────────────────────────
        full_text = self._assemble(hook, story, insight, cta)

        # 길이 조정
        if len(full_text) > _MAX_CHARS:
            # story 축약
            story = story[: _MAX_CHARS - len(hook) - len(insight) - len(cta) - 50]
            story = story.rsplit(" ", 1)[0] + "…"
            full_text = self._assemble(hook, story, insight, cta)

        return NewsletterResult(
            hook=hook,
            story=story,
            insight=insight,
            cta=cta,
            full_text=full_text,
            word_count=len(full_text.split()),
            char_count=len(full_text),
            topic_cluster=topic_cluster,
            emotion_axis=emotion_axis,
        )

    def _assemble(self, hook: str, story: str, insight: str, cta: str) -> str:
        """3-part 구조 조합."""
        parts = [
            f"🔥 {hook}",
            "",
            story,
            "",
            f"💡 {insight}",
            "",
            f"👉 {cta}",
        ]
        return "\n".join(parts).strip()

    async def format_with_llm(
        self,
        post_data: dict[str, Any],
        profile: dict[str, Any],
        draft_text: str,
        llm_fn=None,
    ) -> NewsletterResult:
        """LLM으로 뉴스레터 초안 고도화. llm_fn 미제공 시 rule-based로 폴백.

        Args:
            post_data: Original post data.
            profile: ContentProfile.to_dict().
            draft_text: Existing draft text (Twitter/raw).
            llm_fn: async callable(prompt: str) -> str | None.
                    None이면 rule-based format_from_draft() 사용.
        """
        # Rule-based base
        base = self.format_from_draft(draft_text, profile, post_data)

        if llm_fn is None:
            return base

        topic_cluster = profile.get("topic_cluster", "기타")
        emotion_axis = profile.get("emotion_axis", "공감")

        prompt = f"""당신은 직장인 뉴스레터 에디터입니다.
아래 콘텐츠를 3파트 뉴스레터 형식으로 재작성하세요.

[원본 정보]
토픽: {topic_cluster} | 감정: {emotion_axis}
제목: {post_data.get('title', '')}
본문: {str(post_data.get('content', ''))[:400]}

[기존 초안]
{draft_text[:500]}

[작성 지침]
1. HOOK (1-2문장): 독자가 멈추게 만드는 강렬한 첫 문장
2. STORY (3-5문장): 구체적 사례와 공감 포인트로 전개
3. INSIGHT (1문장): 직장인에게 줄 수 있는 핵심 시사점
4. CTA (1문장): 댓글/공유를 유도하는 행동 유도 문장

반드시 아래 형식으로만 출력하세요:
<hook>...</hook>
<story>...</story>
<insight>...</insight>
<cta>...</cta>"""

        try:
            import asyncio
            raw = await asyncio.wait_for(llm_fn(prompt), timeout=15.0)
            if raw:
                hook = _extract_tag(raw, "hook") or base.hook
                story = _extract_tag(raw, "story") or base.story
                insight = _extract_tag(raw, "insight") or base.insight
                cta = _extract_tag(raw, "cta") or base.cta
                full_text = self._assemble(hook, story, insight, cta)
                return NewsletterResult(
                    hook=hook, story=story, insight=insight, cta=cta,
                    full_text=full_text,
                    word_count=len(full_text.split()),
                    char_count=len(full_text),
                    topic_cluster=topic_cluster,
                    emotion_axis=emotion_axis,
                )
        except Exception as exc:
            logger.warning("NewsletterFormatter.format_with_llm failed: %s. Using rule-based.", exc)

        return base


def _extract_tag(text: str, tag: str) -> str:
    """Extract content between <tag>...</tag>."""
    match = re.search(rf"<{tag}>(.*?)</{tag}>", text, re.DOTALL)
    return match.group(1).strip() if match else ""


# Module-level convenience function
def format_newsletter(
    draft_text: str,
    profile: dict[str, Any],
    post_data: dict[str, Any] | None = None,
) -> NewsletterResult:
    """Convenience wrapper for rule-based newsletter formatting."""
    return NewsletterFormatter().format_from_draft(draft_text, profile, post_data)


# ── P2-C1: 블로그/브런치 포맷 변환 ──────────────────────────────────

def format_for_blog(
    newsletter: NewsletterResult | dict[str, Any],
    platform: str = "naver",
) -> str:
    """뉴스레터 결과를 네이버 블로그 / 브런치 포맷으로 변환 (P2-C1).

    Args:
        newsletter: NewsletterResult 또는 to_dict() 결과.
        platform: 'naver' 또는 'brunch'.

    Returns:
        플랫폼에 맞게 포맷된 텍스트.
    """
    if isinstance(newsletter, NewsletterResult):
        data = newsletter.to_dict()
    else:
        data = newsletter

    hook = data.get("hook", "")
    story = data.get("story", "")
    insight = data.get("insight", "")
    cta = data.get("cta", "")
    topic = data.get("topic_cluster", "직장") or "직장"

    if platform == "brunch":
        # 브런치: 에세이 스타일, 긴 문단, 감성적
        return (
            f"# {hook}\n\n"
            f"{story}\n\n"
            f"---\n\n"
            f"*{insight}*\n\n"
            f"{cta}\n\n"
            f"#직장인 #{topic} #블라인드"
        )
    else:
        # 네이버 블로그: 제목+본문+태그, 볼드 강조
        return (
            f"[직장인 라이프] {hook}\n\n"
            f"{story}\n\n"
            f"💡 핵심 인사이트\n{insight}\n\n"
            f"👉 {cta}\n\n"
            f"---\n"
            f"#직장인 #{topic} #블라인드 #직장생활 #회사원\n"
        )


# ── P6: Threads 포맷 변환 ──────────────────────────────────────────

# Threads CTA (저장/댓글 유도, Instagram 감성)
_THREADS_CTA_BY_EMOTION: dict[str, str] = {
    "분노": "이런 상황 겪어본 사람 🙋 댓글로 알려줘요",
    "허탈": "같은 기분인 사람 여기 모여라 😮‍💨",
    "공감": "나만 그런 게 아니었으면… 저장해두고 나중에 또 보자 📌",
    "웃김": "직장인 밈 맞잖아 ㅋㅋ 더 웃긴 거 있으면 댓글 ⬇️",
    "경악": "실화냐… 너네 회사도 이래? 🫠",
    "현타": "퇴근하고 읽으면 더 현타 옴 ㅎ 공감되면 저장 📌",
    "통찰": "이 시각 어떻게 생각해? 댓글로 이야기하자 💭",
    "자부심": "이런 보람 있으면 버틸 만하지 않아? 🏆",
    "불안": "같은 고민하는 사람 여기 있어요. 댓글로 속마음 나눠봐요 💬",
    "기대감": "기대되는 변화, 준비하는 사람 손! ✋",
}
_DEFAULT_THREADS_CTA = "직장인이면 공감할 듯 💬 댓글로 이야기해요"


def format_for_threads(
    newsletter: NewsletterResult | dict[str, Any],
    max_length: int = 500,
    hashtags_count: int = 3,
) -> str:
    """뉴스레터 결과를 Threads 포맷으로 변환 (P6).

    Args:
        newsletter: NewsletterResult 또는 to_dict() 결과.
        max_length: 최대 글자수 (기본 500).
        hashtags_count: 해시태그 개수 (기본 3).

    Returns:
        Threads에 적합한 캐주얼 톤 텍스트.
    """
    if isinstance(newsletter, NewsletterResult):
        data = newsletter.to_dict()
    else:
        data = newsletter

    hook = data.get("hook", "")
    story = data.get("story", "")
    emotion = data.get("emotion_axis", "공감") or "공감"
    topic = data.get("topic_cluster", "직장") or "직장"

    cta = _THREADS_CTA_BY_EMOTION.get(emotion, _DEFAULT_THREADS_CTA)

    # Threads는 캐주얼 톤 → 이모지 강화, 짧은 문장
    # story를 3문장으로 압축
    story_sentences = [s.strip() for s in re.split(r"[.!?\n]", story) if len(s.strip()) >= 10]
    short_story = ". ".join(story_sentences[:3]) + "." if story_sentences else story[:200]

    # 해시태그 생성
    _HASHTAG_POOL: dict[str, list[str]] = {
        "연봉": ["연봉", "직장인연봉", "연봉협상"],
        "이직": ["이직", "이직준비", "커리어"],
        "회사문화": ["회사문화", "직장생활", "조직문화"],
        "상사": ["직장상사", "회사생활", "직장인"],
        "복지": ["복지", "회사복지", "직장인혜택"],
        "재테크": ["재테크", "직장인재테크", "월급관리"],
        "직장개그": ["직장인밈", "회사짤", "직장유머"],
        "IT": ["IT", "개발자", "테크"],
        "건강": ["번아웃", "직장인건강", "워라밸"],
    }
    topic_tags = _HASHTAG_POOL.get(topic, ["직장인", "직장생활", topic])[:hashtags_count]
    hashtags = " ".join(f"#{t}" for t in topic_tags)

    # 조립
    body = f"{hook}\n\n{short_story}\n\n{cta}\n\n{hashtags}"

    # 길이 제한
    if len(body) > max_length:
        over = len(body) - max_length + 3
        short_story = short_story[:-over] + "…"
        body = f"{hook}\n\n{short_story}\n\n{cta}\n\n{hashtags}"

    return body


def curate_newsletter_from_records(
    records: list[dict[str, Any]],
    max_items: int = 5,
) -> list[dict[str, Any]]:
    """성과 기반 뉴스레터 콘텐츠 자동 큐레이션 (P2-C1).

    상위 성과 레코드를 선별하고 토픽 다양성을 보장합니다.

    Args:
        records: Notion 레코드 리스트.
        max_items: 최대 선별 건수.

    Returns:
        선별된 레코드 리스트 (토픽 다양성 보장).
    """
    # 성과 점수 계산
    scored = []
    for r in records:
        views = float(r.get("views", 0) or 0)
        likes = float(r.get("likes", 0) or 0)
        retweets = float(r.get("retweets", 0) or 0)
        rank = float(r.get("final_rank_score", 0) or 0)
        # 복합 점수: 성과 + 랭크
        score = views + likes * 10 + retweets * 20 + rank * 5
        scored.append((score, r))

    scored.sort(key=lambda x: x[0], reverse=True)

    # 토픽 다양성 보장: 같은 토픽은 최대 2개
    selected = []
    topic_counts: dict[str, int] = {}
    for _, r in scored:
        topic = r.get("topic_cluster", "기타")
        if topic_counts.get(topic, 0) >= 2:
            continue
        selected.append(r)
        topic_counts[topic] = topic_counts.get(topic, 0) + 1
        if len(selected) >= max_items:
            break

    return selected
