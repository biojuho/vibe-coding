"""Cross-source insight generation: detect overlapping topics across sources.

When 3+ posts from 2+ different sources share the same topic_cluster,
generate a "trend analysis" draft that synthesizes multiple perspectives.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any

logger = logging.getLogger(__name__)


def detect_cross_source_trends(
    results: list[dict[str, Any]],
    min_posts: int = 3,
    min_sources: int = 2,
) -> list[dict[str, Any]]:
    """Group processed posts by topic_cluster, return groups meeting thresholds.

    Args:
        results: List of processed post results (each must have content_profile).
        min_posts: Minimum posts in a topic group to qualify.
        min_sources: Minimum unique sources in a topic group to qualify.

    Returns:
        List of trend groups, each containing:
            - topic_cluster: str
            - posts: list of post dicts
            - sources: set of source names
            - avg_rank_score: float
    """
    topic_groups: dict[str, list[dict]] = defaultdict(list)

    for result in results:
        if not result.get("success"):
            continue
        profile = result.get("content_profile") or {}
        topic = profile.get("topic_cluster", "")
        source = result.get("source", "") or profile.get("source", "")
        if not topic or topic == "기타":
            continue

        topic_groups[topic].append(
            {
                "url": result.get("url", ""),
                "title": result.get("title", ""),
                "source": source,
                "content_snippet": str(result.get("content", ""))[:200],
                "final_rank_score": float(profile.get("final_rank_score", 0)),
                "hook_type": profile.get("hook_type", ""),
                "emotion_axis": profile.get("emotion_axis", ""),
                "audience_fit": profile.get("audience_fit", ""),
            }
        )

    trend_groups = []
    for topic, posts in topic_groups.items():
        sources = {p["source"] for p in posts if p["source"]}
        if len(posts) >= min_posts and len(sources) >= min_sources:
            avg_score = sum(p["final_rank_score"] for p in posts) / len(posts)
            trend_groups.append(
                {
                    "topic_cluster": topic,
                    "posts": posts,
                    "sources": sources,
                    "post_count": len(posts),
                    "source_count": len(sources),
                    "avg_rank_score": round(avg_score, 2),
                }
            )

    # Sort by avg_rank_score descending
    trend_groups.sort(key=lambda g: g["avg_rank_score"], reverse=True)

    if trend_groups:
        logger.info(
            "크로스소스 트렌드 %d개 감지: %s",
            len(trend_groups),
            ", ".join(f"{g['topic_cluster']}({g['post_count']}건/{g['source_count']}소스)" for g in trend_groups),
        )

    return trend_groups


def _build_insight_prompt(
    trend_group: dict[str, Any],
    output_formats: list[str],
    top_examples: list[dict] | None = None,
) -> str:
    """Build a cross-source synthesis prompt for the LLM.

    Args:
        trend_group: A single trend group from detect_cross_source_trends.
        output_formats: Target platforms (twitter, threads, naver_blog).
        top_examples: Golden examples for reference.

    Returns:
        LLM prompt string.
    """
    topic = trend_group["topic_cluster"]
    posts = trend_group["posts"]
    sources = trend_group["sources"]

    # Per-source summaries
    source_summaries = defaultdict(list)
    for post in posts:
        source_summaries[post["source"]].append(post)

    summaries_text = ""
    for source, source_posts in source_summaries.items():
        summaries_text += f"\n### {source} ({len(source_posts)}건)\n"
        for sp in source_posts[:3]:  # Max 3 per source
            summaries_text += f"- [{sp['hook_type']}] {sp['title'][:80]}\n"
            if sp["content_snippet"]:
                summaries_text += f"  요약: {sp['content_snippet'][:100]}...\n"

    # Platform-specific blocks
    twitter_block = ""
    if "twitter" in output_formats:
        twitter_block = """
[트위터(X) 트렌드 분석 초안]
1. 280자 이내로 작성하세요.
2. "이번 주 직장인 커뮤니티에서 동시에 터진 주제" 프레임으로 시작하세요.
3. 각 커뮤니티의 핵심 관점을 한 줄씩 대비시키세요.
4. 마지막 줄은 독자 의견을 유도하는 질문으로 마무리하세요.
5. 정중하면서도 위트 있는 톤을 유지하세요.
6. 반드시 <twitter> 와 </twitter> 태그 안에만 작성하세요.
7. 마지막에 <creator_take> 태그로 운영자의 한줄 해석을 추가하세요.
"""

    threads_block = ""
    if "threads" in output_formats:
        threads_block = """
[Threads 트렌드 분석 초안]
1. 500자 이내, 정중하지만 위트 있는 대화체로 작성하세요.
2. 여러 커뮤니티에서 같은 주제가 터진 이유를 분석하세요.
3. 해시태그 3개 이내로 배치하세요.
4. 반드시 <threads> 와 </threads> 태그 안에만 작성하세요.
5. 마지막에 <creator_take> 태그로 운영자의 한줄 해석을 추가하세요.
"""

    naver_blog_block = ""
    if "naver_blog" in output_formats:
        naver_blog_block = """
[네이버 블로그 — 해설형 큐레이션 패턴 리포트]
아래 4부 구조로 작성하세요:

## 1부: 시그널 요약 (200자)
- "이번 주 N개 커뮤니티에서 동시에 터진 시그널" 프레임
- 핵심 현상 1줄 요약

## 2부: 소스별 온도 비교 (각 소스당 2~3줄)
- 각 커뮤니티의 시각 차이를 대비시키세요
- 구체적 게시글 인용 포함

## 3부: 패턴 해석 (500자 이내)
- "왜 동시에 터졌나?" 분석
- 직장인 맥락에서의 의미 해석

## 4부: 액션 시사점 (200자)
- 독자가 가져갈 수 있는 실용적 인사이트
- 정중하면서도 위트 있는 마무리

작성 규칙:
1. 1500~3000자, SEO 태그 10개 이상.
2. 반드시 <naver_blog> 와 </naver_blog> 태그 안에만 작성하세요.
3. 마지막에 <creator_take> 태그로 운영자의 한줄 해석을 추가하세요.
"""

    prompt = f"""당신은 '정중하면서도 위트 있는 직장인 시그널 해설자'입니다.
아래는 여러 커뮤니티에서 동시에 화제가 된 '{topic}' 토픽의 게시글들입니다.
각 커뮤니티의 관점을 비교 분석하여 통합 인사이트를 작성하세요.
톤: 존댓말 기반이되, 은유·비유·살짝 웃음이 들어간 해설. 날카롭되 공격적이지 않게.

[크로스소스 트렌드 분석]
토픽: {topic}
참여 커뮤니티: {", ".join(sorted(sources))} ({len(sources)}개)
총 게시글 수: {len(posts)}건
평균 랭크 점수: {trend_group["avg_rank_score"]}

[커뮤니티별 게시글 요약]
{summaries_text}

[작성 원칙]
1. 단순 요약이 아닌 "비교 분석"과 "인사이트 도출"에 집중하세요.
2. "{len(sources)}개 커뮤니티에서 동시에 화제"라는 프레임을 활용하세요.
3. 각 커뮤니티의 시각 차이를 대비시켜 흥미를 유발하세요.
4. 독자가 "이게 왜 동시에 화제야?"라는 호기심을 해소할 수 있게 작성하세요.
{twitter_block}
{threads_block}
{naver_blog_block}
[이미지 프롬프트 작성 조건]
1. 마지막에 영어 이미지 프롬프트를 작성하세요.
2. 여러 관점이 교차하는 장면을 Pixar 3D 캐릭터 스타일로 묘사하세요.
3. 반드시 <image_prompt> 와 </image_prompt> 태그 안에만 작성하세요.
"""
    return prompt


async def generate_insight_draft(
    trend_group: dict[str, Any],
    draft_generator: Any,
    output_formats: list[str],
    top_examples: list[dict] | None = None,
) -> tuple[dict[str, str], str | None]:
    """Build cross-source synthesis prompt and generate draft.

    Args:
        trend_group: A single trend group from detect_cross_source_trends.
        draft_generator: TweetDraftGenerator instance.
        output_formats: Target platforms.
        top_examples: Golden examples.

    Returns:
        (drafts_dict, image_prompt) — same format as TweetDraftGenerator.generate_drafts.
    """
    prompt = _build_insight_prompt(trend_group, output_formats, top_examples)

    # Reuse the draft generator's provider fallback chain
    providers = draft_generator._enabled_providers()
    if not providers:
        logger.error("No enabled LLM providers for insight generation.")
        return {"twitter": "No providers available for insight."}, None

    for provider in providers:
        for attempt in range(1, draft_generator.max_retries_per_provider + 1):
            try:
                logger.info(
                    "인사이트 초안 생성 via %s (%d/%d) — 토픽: %s",
                    provider,
                    attempt,
                    draft_generator.max_retries_per_provider,
                    trend_group["topic_cluster"],
                )
                response_text, input_tokens, output_tokens = await draft_generator._generate_once(provider, prompt)
                if draft_generator.cost_tracker:
                    draft_generator.cost_tracker.add_text_generation_cost(
                        provider,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                    )
                drafts, image_prompt = draft_generator._parse_response(response_text, output_formats, provider)
                # 태그 파싱 검증: 주요 플랫폼 키가 비어있으면 경고
                _empty_platforms = [
                    fmt for fmt in output_formats if fmt in drafts and (not drafts[fmt] or not drafts[fmt].strip())
                ]
                if _empty_platforms:
                    logger.warning(
                        "인사이트 파싱 불완전 — 빈 플랫폼: %s (provider=%s, topic=%s)",
                        ", ".join(_empty_platforms),
                        provider,
                        trend_group["topic_cluster"],
                    )
                # Mark as insight type
                drafts["_insight_type"] = "cross_source"
                drafts["_topic_cluster"] = trend_group["topic_cluster"]
                drafts["_source_count"] = str(trend_group["source_count"])
                drafts["_post_count"] = str(trend_group["post_count"])
                logger.info("인사이트 초안 생성 성공 via %s — 토픽: %s", provider, trend_group["topic_cluster"])
                return drafts, image_prompt
            except Exception as exc:
                logger.warning(
                    "인사이트 생성 실패 via %s (%d/%d): %s",
                    provider,
                    attempt,
                    draft_generator.max_retries_per_provider,
                    exc,
                )
                import asyncio

                if attempt < draft_generator.max_retries_per_provider:
                    await asyncio.sleep(min(2**attempt, 10))

    logger.error("모든 프로바이더 실패 — 인사이트 초안 생성 불가 (토픽: %s)", trend_group["topic_cluster"])
    return {"twitter": f"Insight generation failed for {trend_group['topic_cluster']}"}, None


async def process_cross_source_insights(
    results: list[dict[str, Any]],
    draft_generator: Any,
    notion_uploader: Any | None = None,
    image_uploader: Any | None = None,
    image_generator: Any | None = None,
    config: Any | None = None,
    output_formats: list[str] | None = None,
    top_examples: list[dict] | None = None,
    trend_monitor: Any | None = None,
) -> list[dict[str, Any]]:
    """End-to-end: detect trends → generate insight drafts → upload to Notion.

    Args:
        results: All processed post results from the current run.
        draft_generator: TweetDraftGenerator instance.
        notion_uploader: NotionUploader instance (optional).
        image_uploader: ImageUploader instance (optional).
        image_generator: ImageGenerator instance (optional).
        config: ConfigManager instance.
        output_formats: Target platforms.
        top_examples: Golden examples.
        trend_monitor: TrendMonitor instance (optional, for trend boost info).

    Returns:
        List of insight result dicts.
    """
    if output_formats is None:
        output_formats = ["twitter"]

    # Config
    min_posts = 3
    min_sources = 2
    if config:
        min_posts = int(config.get("cross_source_insight.min_posts", 3) or 3)
        min_sources = int(config.get("cross_source_insight.min_sources", 2) or 2)

    # Step 1: Detect cross-source trends
    trend_groups = detect_cross_source_trends(results, min_posts=min_posts, min_sources=min_sources)
    if not trend_groups:
        logger.info("크로스소스 트렌드 없음 (min_posts=%d, min_sources=%d)", min_posts, min_sources)
        return []

    insight_results = []
    for group in trend_groups:
        topic = group["topic_cluster"]

        # Step 2: Generate insight draft
        drafts, image_prompt = await generate_insight_draft(group, draft_generator, output_formats, top_examples)

        insight_result: dict[str, Any] = {
            "url": f"cross-source-insight:{topic}",
            "title": f"[트렌드 분석] {topic} — {group['source_count']}개 커뮤니티 동시 화제",
            "success": True,
            "source": "cross_source_insight",
            "content_profile": {
                "topic_cluster": topic,
                "hook_type": "분석형",
                "emotion_axis": "통찰",
                "audience_fit": "전직장인",
                "recommended_draft_type": "분석형",
                "final_rank_score": group["avg_rank_score"],
            },
            "drafts": drafts,
            "image_prompt": image_prompt,
            "insight_meta": {
                "source_count": group["source_count"],
                "post_count": group["post_count"],
                "sources": list(group["sources"]),
                "avg_rank_score": group["avg_rank_score"],
            },
        }

        # Step 3: Upload to Notion (if available)
        if notion_uploader and not (config and config.get("dry_run", False)):
            try:
                # Build post_data-like dict for Notion upload
                post_data_for_notion = {
                    "title": insight_result["title"],
                    "content": f"크로스소스 트렌드 분석: {topic}\n참여 커뮤니티: {', '.join(sorted(group['sources']))}\n총 {group['post_count']}건",
                    "url": insight_result["url"],
                    "source": "cross_source_insight",
                    "content_profile": insight_result["content_profile"],
                    "feed_mode": "insight",
                }

                # Image generation (if available)
                image_url = None
                if image_generator and image_prompt:
                    try:
                        image_url = await image_generator.generate(
                            prompt=image_prompt,
                            topic_cluster=topic,
                            emotion_axis="통찰",
                        )
                    except Exception as exc:
                        logger.debug("인사이트 이미지 생성 실패: %s", exc)

                post_data_for_notion["review_status"] = "검토필요"
                notion_url = await notion_uploader.upload(
                    post_data=post_data_for_notion,
                    image_url=image_url,
                    drafts=drafts,
                )
                insight_result["notion_url"] = notion_url
                logger.info("인사이트 Notion 업로드 완료: %s → %s", topic, notion_url)
            except Exception as exc:
                logger.warning("인사이트 Notion 업로드 실패 (%s): %s", topic, exc)
                insight_result["notion_error"] = str(exc)

        # Step 4: Record to cost DB
        try:
            from pipeline.cost_db import get_cost_db

            db = get_cost_db()
            db.record_cross_source_insight(
                topic_cluster=topic,
                sources=list(group["sources"]),
                post_count=group["post_count"],
                notion_page_id=insight_result.get("notion_url", ""),
            )
        except Exception as exc:
            logger.debug("인사이트 DB 기록 실패: %s", exc)

        insight_results.append(insight_result)

    logger.info("크로스소스 인사이트 %d건 생성 완료", len(insight_results))
    return insight_results
