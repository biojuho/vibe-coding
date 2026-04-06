"""Prompt building, tone mapping, and example formatting for draft generation."""

from __future__ import annotations

import hashlib
import logging
import re
from typing import Any

from pipeline.rules_loader import load_rules

logger = logging.getLogger(__name__)

_draft_rules_cache: dict | None = None


def _load_draft_rules() -> dict:
    """Load merged rule sections with in-module caching."""
    global _draft_rules_cache
    if _draft_rules_cache is not None:
        return _draft_rules_cache
    _draft_rules_cache = load_rules()
    return _draft_rules_cache


class DraftPromptsMixin:
    """Mixin providing prompt-building helpers for TweetDraftGenerator.

    Expects the host class to have: ``self.config``, ``self.tone``,
    ``self.max_length``, ``self.threads_tone``, ``self.threads_max_length``,
    ``self.threads_hashtags_count``, ``self.blog_tone``, ``self.blog_min_length``,
    ``self.blog_max_length``, ``self.blog_seo_tags_count``,
    ``self.regulation_checker``.
    """

    # ------------------------------------------------------------------
    # Tone resolution
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Content essence extraction
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_content_essence(post_data: dict[str, Any]) -> dict[str, Any]:
        """원문에서 핵심 요소를 결정론적으로 추출 (LLM 호출 없음).

        Returns:
            {key_numbers, quotes, emotional_peaks, opening, closing}
        """
        content = str(post_data.get("content", ""))
        title = str(post_data.get("title", ""))

        # 1. 숫자 + 맥락 추출 (전후 15자)
        key_numbers: list[str] = []
        for m in re.finditer(r"\d[\d,.]*\d?[만천백억원%명개월년일시위등배]?", content):
            start = max(0, m.start() - 15)
            end = min(len(content), m.end() + 15)
            snippet = content[start:end].strip()
            if snippet and snippet not in key_numbers:
                key_numbers.append(snippet)
        key_numbers = key_numbers[:8]  # 최대 8개

        # 2. 인용/발언 추출
        quotes: list[str] = re.findall(
            r"""['\"\u201c\u201d\u2018\u2019「」『』](.{5,80}?)['\"\u201c\u201d\u2018\u2019「」『』]""",
            content,
        )
        quotes = quotes[:5]  # 최대 5개

        # 3. 감정 고조 문장 (emotion_rules 키워드 기반)
        rules = _load_draft_rules()
        emotion_keywords: list[str] = []
        for rule in rules.get("emotion_rules", []):
            emotion_keywords.extend(rule.get("keywords", []))

        sentences = [s.strip() for s in re.split(r"[.!?\n]+", content) if len(s.strip()) > 10]
        emotional_peaks: list[str] = []
        for s in sentences:
            if any(kw in s for kw in emotion_keywords):
                emotional_peaks.append(s)
                if len(emotional_peaks) >= 3:
                    break

        # 4. 내러티브 북엔드 (첫/끝 문장)
        opening = sentences[0] if sentences else ""
        closing = sentences[-1] if len(sentences) > 1 else ""

        return {
            "title": title,
            "key_numbers": key_numbers,
            "quotes": quotes,
            "emotional_peaks": emotional_peaks,
            "opening": opening,
            "closing": closing,
        }

    # ------------------------------------------------------------------
    # Example formatting
    # ------------------------------------------------------------------

    @staticmethod
    def _format_examples(
        top_examples: list[dict[str, Any]] | None,
        topic_cluster: str = "",
        seed_text: str = "",
    ) -> str:
        """성과 우수 예시 포맷팅. YAML 골든 예시도 자동 병합 (랜덤 로테이션)."""
        merged: list[dict[str, Any]] = []
        example_seed = f"{topic_cluster}|{seed_text or 'default'}"

        # 1. YAML 골든 예시에서 해당 토픽 예시 로드 (3개 이상이면 랜덤 2개)
        rules = _load_draft_rules()
        golden = rules.get("golden_examples", {})
        if topic_cluster and topic_cluster in golden:
            golden_list = golden[topic_cluster]
            selected = DraftPromptsMixin._select_examples_deterministically(
                golden_list,
                limit=2,
                seed_text=example_seed,
            )
            for ge in selected:
                merged.append(
                    {
                        "views": "(골든 예시)",
                        "topic_cluster": topic_cluster,
                        "hook_type": ge.get("hook_type", "공감형"),
                        "emotion_axis": "-",
                        "draft_style": ge.get("hook_type", "공감형"),
                        "text": ge.get("text", ""),
                        "grade": ge.get("grade", ""),
                    }
                )

        # 2. cost_db에서 실제 성과 우수 포스트 자동 추가
        try:
            from pipeline.cost_db import get_cost_db

            db = get_cost_db()
            top_from_db = db.get_top_performing_drafts(topic_cluster=topic_cluster, limit=2)
            for row in top_from_db:
                merged.append(
                    {
                        "views": row.get("yt_views", 0),
                        "topic_cluster": row.get("topic_cluster", ""),
                        "hook_type": row.get("hook_type", ""),
                        "emotion_axis": row.get("emotion_axis", ""),
                        "draft_style": row.get("draft_style", ""),
                        "text": row.get("text", ""),
                        "grade": "실적우수",
                    }
                )
        except Exception:
            pass  # cost_db 미가용 시 무시

        # 3. 실시간 성과 예시 추가
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

    @staticmethod
    def _select_examples_deterministically(
        examples: list[dict[str, Any]],
        limit: int,
        seed_text: str,
    ) -> list[dict[str, Any]]:
        if len(examples) <= limit:
            return list(examples)

        seed = seed_text or "default"
        ordered = sorted(
            examples,
            key=lambda example: (
                hashlib.sha256(f"{seed}|{str(example.get('text', '')).strip()}".encode("utf-8")).hexdigest(),
                str(example.get("text", "")).strip(),
            ),
        )
        offset = int(hashlib.sha256(seed.encode("utf-8")).hexdigest()[:8], 16) % len(ordered)
        rotated = ordered[offset:] + ordered[:offset]
        return rotated[:limit]

    # ------------------------------------------------------------------
    # Main prompt builder
    # ------------------------------------------------------------------

    def _build_prompt(
        self,
        post_data: dict[str, Any],
        top_examples: list[dict[str, Any]] | None,
        output_formats: list[str],
        draft_format: str = "standard",
    ) -> str:
        """YAML 기반 프롬프트 조립. YAML 로드 실패 시 하드코딩 fallback."""
        # P0-1: 원문 핵심 추출
        essence = self._extract_content_essence(post_data)
        content = str(post_data.get("content", ""))
        if len(content) > 700:
            logger.info("Content truncated from %s chars to 700 for API prompt.", len(content))
            content = f"{content[:700]}..."

        source = post_data.get("source", "블라인드")
        tone = self._resolve_tone(post_data)
        profile = post_data.get("content_profile", {}) or {}
        topic_cluster = profile.get("topic_cluster", "기타")
        recommended_draft_type = profile.get("recommended_draft_type", "공감형")
        empathy_anchor = profile.get("empathy_anchor", "")
        spinoff_angle = profile.get("spinoff_angle", "")
        audience_need = profile.get("audience_need", "")
        emotion_lane = profile.get("emotion_lane", "")

        rules = _load_draft_rules()
        templates = rules.get("prompt_templates", {})
        system_role = templates.get("system_role", "당신은 직장인 대상 콘텐츠를 큐레이션하는 시니어 에디터입니다.")

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
                # Hardcoded fallback (Viral/Empathetic focus - V2.0 Phase 2)
                twitter_block = f"""\n[트위터(X) 초안 — 바이럴 및 공감 극대화]

당신은 X(트위터)에서 수만 명의 팔로워를 보유한 '바이럴 제조기' 직장인 에디터입니다.
사람들이 무심코 스크롤을 내리다가 멈추고, '이거 내 얘긴데?' 하며 알티(RT)를 누르게 만드는 것이 목표입니다.

[콘텐츠 분석 데이터]
- 타겟 니즈: {audience_need}
- 감정선: {emotion_lane}
- 킬링 포인트(Anchor): {empathy_anchor}
- 확장 가능성(Spinoff): {spinoff_angle}

[작성 지침]
1. 말투: 퇴근 후 친구와 맥주 한 잔 하며 말하듯, 혹은 카톡하듯 자연스럽게 (AI 말투 절대 금지).
2. 훅(Hook): 첫 문장에서 원문의 가장 '킹받는' 포인트나 '배아픈' 포인트, 혹은 '극공감' 포인트를 터뜨리세요.
3. 생략과 강조: 원문의 모든 내용을 담으려 하지 마세요. 가장 자극적이거나 공감 가는 지점 {empathy_anchor} 하나에만 집중하세요.
4. 마무리: 독자에게 질문을 던지거나, 본인의 생각을 덧붙여 답글을 유도하세요.
5. 형식: {self.max_length}자 이내. 출처 '{source}'를 문맥에 맞게 자연스럽게 언급.

[기타]
- 본문에 링크나 해시태그는 넣지 마세요 (답글에 넣을 것).
- 3가지 버전 작성: [추천안], [대조안], [실험안]. [추천안]은 '{recommended_draft_type}' 스타일로 작성.
- 반드시 <twitter> 와 </twitter> 태그 안에만 작성.
- 답글(원문 링크 포함)은 <reply> 와 </reply> 태그 안에 작성.
"""

        newsletter_block = ""
        if "newsletter" in output_formats:
            nl_tmpl = templates.get("newsletter", "")
            newsletter_block = (
                nl_tmpl
                if nl_tmpl
                else f"""\n[뉴스레터 초안 — 심층 큐레이션 및 인사이트]
1. 목표: 바쁜 직장인에게 이 글이 왜 중요한지, 어떤 시사점이 있는지 '시니어 에디터'의 시각에서 정리합니다.
2. 구조:
   - 📢 헤드라인: 클릭을 유도하는 호기심 자극형 제목
   - 📝 한 줄 요약: 핵심 내용 요약
   - 💡 에디터의 시선: {empathy_anchor}를 중심으로 한 심층 분석 및 {spinoff_angle} 제언
   - ✅ 한 줄 결론/Action Item: 독자가 적용해볼 점
3. 분량: 450자 이상 900자 이하.
4. 말투: 신뢰감 있으면서도 친절한 전문 에디터 톤.
5. 반드시 <newsletter> 와 </newsletter> 태그 안에만 작성하세요.
"""
            )

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
                threads_block = f"""\n[Threads 초안 — 친근한 스토리텔링 및 공감]
1. 목표: 인스타그램/스레드 감성에 맞춰, 텍스트 위주지만 따뜻하고 친근하게 말을 겁니다.
2. 전략:
   - {empathy_anchor}를 내 이야기처럼 자연스럽게 풀어서 시작하세요.
   - 트위터보다 조금 더 호흡이 길어도 좋으니 대화하듯 작성하세요.
   - {spinoff_angle}을 활용해 독자의 개인적인 경험을 묻는 질문으로 마무리하세요.
3. 형식:
   - {self.threads_max_length}자 이내.
   - 해시태그 {self.threads_hashtags_count}개 이내.
   - 출처 '{source}'를 문맥에 맞게 언급.
4. 참고 톤: '{resolved_threads_tone}'
5. 반드시 <threads> 와 </threads> 태그 안에만 작성하세요.
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
                naver_blog_block = f"""\n[네이버 블로그 — 해설형 큐레이션 초안 작성 조건]
★ 핵심 전환: 단일 게시물 확장이 아니라, 여러 소스의 유사 시그널을 묶어 해설하는 '패턴 리포트'를 작성하세요.
1. {self.blog_min_length}자 이상 {self.blog_max_length}자 이하로 작성하세요.
2. 아래 구조를 따르세요:
   ## 이번 주 직장인 커뮤니티에서 감지된 시그널
   (도입부: 여러 커뮤니티에서 동시에 터진 주제가 무엇인지)
   ## 무슨 일이 벌어지고 있나
   (본문: 각 소스별 반응 요약 — 원문 복붙 금지, 패턴 요약만)
   ## 왜 지금 이 주제가 뜨는가
   (인사이트: 구조적 원인 해설)
   ## 실무자가 알아야 할 것
   (결론: 독자가 얻는 실용 포인트 + CTA)
3. 검색 유입을 고려해 핵심 키워드를 자연스럽게 반복하세요.
4. SEO 해시태그를 {self.blog_seo_tags_count}개 글 끝에 추가하세요.
5. 정중하지만 위트 있는 해설자 톤을 유지하세요. 참고 톤: '{resolved_blog_tone}'
6. 반드시 <creator_take> 태그 안에 운영자의 핵심 해석 1문장을 작성하세요.
7. 원문 '{source}'을 서두 또는 본문에서 간접적으로 언급하세요.
8. 반드시 <naver_blog> 와 </naver_blog> 태그 안에만 작성하세요.
"""

        # ── Image prompt 블록 (YAML 템플릿 우선) ──────────────────────
        img_tmpl = templates.get("image_prompt", "")
        image_block = (
            img_tmpl
            if img_tmpl
            else """[이미지 프롬프트 작성 조건]
1. 마지막에 영어 이미지 프롬프트를 작성하세요.
2. 텍스트 없는 장면 중심 이미지여야 합니다.
3. 직장인 커뮤니티 상황이 한눈에 보이게 묘사하세요.
4. 반드시 <image_prompt> 와 </image_prompt> 태그 안에만 작성하세요.
"""
        )

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

        # ── 브랜드 보이스 가이드 주입 ────────────────────────────────────
        voice_block = ""
        brand_voice = rules.get("brand_voice", {})
        if brand_voice:
            traits = "\n".join(f"  - {t}" for t in brand_voice.get("voice_traits", []))
            forbidden = "\n".join(f"  - {f}" for f in brand_voice.get("forbidden_expressions", []))
            good_ex = brand_voice.get("examples", {}).get("good", "")
            bad_ex = brand_voice.get("examples", {}).get("bad", "")
            voice_block = f"""
[보이스 가이드 — 반드시 준수]
페르소나: {brand_voice.get("persona", "")}
말투 규칙:
{traits}
좋은 예: {good_ex}
나쁜 예: {bad_ex}

[절대 사용 금지 표현]
아래 표현은 AI스럽거나 상투적이므로 절대 사용하지 마세요:
{forbidden}
"""

        # ── P0-3: 클리셰 목록 사전 주입 ─────────────────────────────────
        cliches = rules.get("cliche_watchlist", [])
        if cliches:
            cliche_str = "\n".join(f'  - "{c}"' for c in cliches[:20])
            voice_block += f"""
[절대 사용 금지 — 클리셰 목록]
아래 표현을 하나라도 사용하면 재생성 대상입니다:
{cliche_str}
"""

        # ── P0-1: 원문 핵심 추출 블록 구성 ───────────────────────────────
        essence_block = ""
        if essence.get("key_numbers") or essence.get("quotes") or essence.get("emotional_peaks"):
            parts = []
            if essence["key_numbers"]:
                parts.append(f"핵심 수치: {' | '.join(essence['key_numbers'])}")
            if essence["quotes"]:
                parts.append(f"인용/발언: {' | '.join(essence['quotes'])}")
            if essence["emotional_peaks"]:
                parts.append(f"감정 고조점: {' / '.join(essence['emotional_peaks'])}")
            if essence.get("opening"):
                parts.append(f"원문 도입부: {essence['opening']}")
            if essence.get("closing") and essence["closing"] != essence.get("opening"):
                parts.append(f"원문 결론부: {essence['closing']}")
            essence_block = "\n[원문 핵심 추출 — 초안에 반드시 활용]\n" + "\n".join(parts)

        # ── P0-2: Chain-of-Thought 사고 과정 블록 ────────────────────────
        thinking_tmpl = templates.get("thinking_framework", "")
        thinking_block = ""
        if thinking_tmpl:
            thinking_block = thinking_tmpl
        else:
            thinking_block = """
[사고 과정 — <thinking> 태그 안에 작성]
초안을 작성하기 전에 반드시 아래를 먼저 분석하세요:
1. 이 글의 핵심 인사이트는 무엇인가? (한 문장)
2. 직장인이 공유하고 싶은 포인트는? (공감/분노/놀라움 중 택1과 이유)
3. 가장 강한 훅이 될 숫자/인용구/대비는?
4. 피해야 할 함정은? (상투적 표현, 원문에 없는 내용 날조)
반드시 <thinking> 와 </thinking> 태그 안에만 작성하세요.
"""

        # ── P1-1: 토픽별 프롬프트 전략 블록 ──────────────────────────────
        topic_strategy_block = ""
        topic_strategies = rules.get("topic_prompt_strategies", {})
        ts = topic_strategies.get(topic_cluster, {})
        if ts:
            ts_parts = [f"[토픽별 작성 전략 — {topic_cluster}]"]
            if ts.get("emphasis"):
                ts_parts.append(f"강조: {ts['emphasis']}")
            if ts.get("avoid"):
                ts_parts.append(f"피하기: {ts['avoid']}")
            if ts.get("hook_template"):
                ts_parts.append(f"훅 구조: {ts['hook_template']}")
            if ts.get("example_structure"):
                ts_parts.append(f"글 구조: {ts['example_structure']}")
            topic_strategy_block = "\n" + "\n".join(ts_parts)

        # ── P1-2: 나쁜 예시 (anti-examples) ──────────────────────────────
        anti_examples_block = ""
        anti_examples = rules.get("anti_examples", {})
        generic_bad = anti_examples.get("generic_bad", [])
        topic_bad = anti_examples.get(topic_cluster, [])
        all_bad = (topic_bad + generic_bad)[:3]
        if all_bad:
            ae_lines = ["\n[나쁜 예시 — 이렇게 쓰지 마세요]"]
            for idx, ae in enumerate(all_bad, 1):
                ae_lines.append(f"- 나쁜 예시 {idx}: {ae.get('text', '')}")
                if ae.get("reason"):
                    ae_lines.append(f"  이유: {ae['reason']}")
            anti_examples_block = "\n".join(ae_lines)

        selection_brief_lines = [
            "[X 편집 브리프]",
            f"왜 고름: {profile.get('selection_summary', '') or '직장인이 자기 일처럼 반응할 이유가 있는 글'}",
            f"독자 욕구: {profile.get('audience_need', '') or '직장인 현실 비교 욕구'}",
            f"감정선: {profile.get('emotion_lane', '') or '공감과 웃음의 균형'}",
            f"공감 앵커: {profile.get('empathy_anchor', '') or essence.get('opening', '')}",
            f"파생각: {profile.get('spinoff_angle', '') or '현실 비교, 댓글 반응, 자기 경험'}",
            "",
            "[반드시 지킬 것]",
            "1. 첫 문장은 장면, 대사, 숫자 중 하나로 시작할 것",
            "2. 본문 안에 같이 웃거나 같이 한숨 쉬게 하는 포인트를 분명히 넣을 것",
            "3. 원문이 재밌는 이유와 더 확장되는 이유를 분리해서 반영할 것",
            "4. 마지막 CTA는 구체적 선택형 또는 자기 경험 유도형 질문으로 쓸 것",
            "5. '여러분 생각은?' 같은 generic CTA는 금지",
        ]
        if "twitter" in output_formats:
            selection_brief_lines.append(
                "6. <twitter> 안에는 [추천안]을 맨 위에 두고 결이 다른 2개 옵션을 더 제시할 것"
            )
        selection_brief_block = "\n".join(selection_brief_lines)

        examples_block = self._format_examples(
            top_examples,
            topic_cluster=topic_cluster,
            seed_text=f"{post_data.get('title', '')}|{profile.get('selection_summary', '')}",
        )
        return f"""{system_role}
아래 게시글을 기반으로 발행 가능한 초안을 작성하세요.
{voice_block}

[게시글 정보]
출처: {source}
제목: {post_data.get("title", "")}
본문: {content}
카테고리: {post_data.get("category", "general")}
공감수: {post_data.get("likes", 0)} | 댓글수: {post_data.get("comments", 0)}
{essence_block}

[콘텐츠 프로필]
토픽 클러스터: {topic_cluster}
훅 타입: {profile.get("hook_type", "공감형")}
감정 축: {profile.get("emotion_axis", "공감")}
대상 독자: {profile.get("audience_fit", "범용")}
추천 초안 타입: {recommended_draft_type}
발행 적합도 점수: {profile.get("publishability_score", 0)}
성과 예측 점수: {profile.get("performance_score", 0)}
{selection_brief_block}
{topic_strategy_block}
{regulation_context}
{thinking_block}
{examples_block}
{anti_examples_block}
{twitter_block}
{threads_block}
{newsletter_block}
{naver_blog_block}
{image_block}
{regulation_check_block}
[톤 가이드]
{tone}
"""

    # ------------------------------------------------------------------
    # Retry prompt
    # ------------------------------------------------------------------

    # P0-4: 품질 게이트 실패 유형별 구체적 수정 지침
    _FIX_INSTRUCTIONS: dict[str, str] = {
        "최소 글자 수": "글이 너무 짧습니다. 원문의 구체적인 사례, 숫자, 인용구를 추가하여 더 풍성하게 작성하세요.",
        "최소 길이": "글이 너무 짧습니다. 원문의 구체적인 사례, 숫자, 인용구를 추가하여 더 풍성하게 작성하세요.",
        "최대 글자 수": "글이 너무 깁니다. 불필요한 수식어와 반복을 제거하고 핵심만 남기세요.",
        "최대 길이": "글이 너무 깁니다. 불필요한 수식어와 반복을 제거하고 핵심만 남기세요.",
        "CTA": "마지막 문장을 구체적인 질문으로 교체하세요. '여러분 생각은?'이 아니라 구체적 선택지를 제시하세요. 예: '3% 인상 vs 이직, 뭘 고르실?'",
        "해시태그": "해시태그 수를 플랫폼 기준에 맞추세요. 핵심 키워드 중심으로 정리하세요.",
        "클리셰": "상투적 표현을 원문의 구체적인 디테일(숫자, 인용, 에피소드)로 대체하세요.",
        "한글 비율": "영어/특수문자 비율이 너무 높습니다. 한국어 문장을 자연스럽게 늘리세요.",
        "금지 패턴": "외부 링크 등 금지된 패턴이 포함되어 있습니다. 제거하세요.",
        "소제목": "소제목(##)을 3~4개 사용하여 글을 구조화하세요.",
        "SEO 태그": "글 끝에 검색 키워드 태그를 추가하세요.",
    }

    def _build_retry_prompt(
        self,
        original_prompt: str,
        quality_feedback: list[dict[str, Any]],
    ) -> str:
        """품질 게이트 실패 피드백을 기반으로 재생성 프롬프트를 조립합니다.

        Args:
            original_prompt: 원래 사용된 프롬프트.
            quality_feedback: [{platform, issues, score}] 형태의 실패 정보.

        Returns:
            피드백이 포함된 재생성용 프롬프트.
        """
        feedback_lines = [
            "",
            "━" * 40,
            "[이전 초안 품질 게이트 실패 — 아래 피드백을 반영하여 재작성하세요]",
        ]
        for fb in quality_feedback:
            platform = fb.get("platform", "unknown")
            score = fb.get("score", 0)
            issues = fb.get("issues", [])
            feedback_lines.append(f"\n❌ {platform} (점수: {score}/100):")
            for issue in issues:
                feedback_lines.append(f"  - {issue}")
                # P0-4: 실패 유형별 구체적 수정 지침 매칭
                for key, instruction in self._FIX_INSTRUCTIONS.items():
                    if key in str(issue):
                        feedback_lines.append(f"    → 수정 방법: {instruction}")
                        break

        feedback_lines.extend(
            [
                "",
                "[재작성 지침]",
                "1. 위에서 지적된 문제점과 '수정 방법'을 반드시 반영하세요.",
                "2. 글자 수, CTA, 해시태그 등 플랫폼 규칙을 정확히 준수하세요.",
                "3. 기존 초안의 좋은 점은 유지하되, 문제점만 개선하세요.",
                "4. 원문에 없는 숫자나 사실을 날조하지 마세요.",
                "━" * 40,
            ]
        )

        return original_prompt + "\n".join(feedback_lines)
