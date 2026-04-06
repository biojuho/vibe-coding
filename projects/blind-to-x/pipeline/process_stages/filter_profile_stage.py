"""Filter/profile stage for `process_single_post()`.

이 모듈은 단일 책임 원칙에 따라 5개의 독립 필터 함수로 구성됩니다.
각 함수는 `ProcessRunContext`를 변경하고 `bool`을 반환합니다:
  - True  → 필터 통과, 다음 단계 진행
  - False → 필터 거부, pipeline 중단

오케스트레이터 함수 `run_filter_profile_stage()`는 이 함수들을 순서대로 호출합니다.
"""

from __future__ import annotations

from config import (
    ERROR_BUDGET_EXCEEDED,
    ERROR_FILTERED_LOW_QUALITY,
    ERROR_FILTERED_SHORT,
    ERROR_FILTERED_SPAM,
    QUALITY_SCORE_THRESHOLD,
)
from pipeline.content_intelligence import build_content_profile
from pipeline.review_queue import build_review_decision

from .context import ProcessRunContext, mark_stage
from .runtime import (
    INAPPROPRIATE_TITLE_KEYWORDS,
    REJECT_EMOTION_AXES,
    SPAM_KEYWORDS,
    SPAM_TITLE_KEYWORDS,
    get_viral_filter,
    logger,
    sentiment_tracker,
)


# ---------------------------------------------------------------------------
# 내부 필터 함수들 — 각각 단일 필터 책임
# ---------------------------------------------------------------------------


def _check_length(ctx: ProcessRunContext, scraper) -> bool:
    """콘텐츠 최소 길이 필터.

    시각 콘텐츠(스크린샷/이미지)가 있으면 길이 제한을 0으로 완화합니다.
    """
    post_data = ctx.post_data
    content_text = ctx.content_text
    has_visual_content = bool(post_data.get("screenshot_path") or post_data.get("images"))
    effective_min_length = 0 if has_visual_content else scraper.min_content_length

    if len(content_text) < effective_min_length:
        ctx.result["error"] = "Content too short (potential spam/empty)"
        ctx.result["error_code"] = ERROR_FILTERED_SHORT
        ctx.result["success"] = True
        ctx.result["notion_url"] = "(skipped-filtered)"
        ctx.result["failure_stage"] = "filter"
        ctx.result["failure_reason"] = "content_too_short"
        mark_stage(ctx, "filter_profile", "skipped", "content_too_short")
        return False
    return True


def _check_spam(ctx: ProcessRunContext) -> bool:
    """스팸 및 부적절 콘텐츠 키워드 필터."""
    post_data = ctx.post_data
    content_text = ctx.content_text
    title_text = post_data.get("title", "")

    matched_inappropriate = [kw for kw in INAPPROPRIATE_TITLE_KEYWORDS if kw in title_text]
    if matched_inappropriate:
        ctx.result["error"] = f"Inappropriate content detected: {matched_inappropriate[0]}"
        ctx.result["error_code"] = ERROR_FILTERED_SPAM
        ctx.result["success"] = True
        ctx.result["notion_url"] = "(skipped-filtered)"
        ctx.result["failure_stage"] = "filter"
        ctx.result["failure_reason"] = "inappropriate_content"
        logger.info("SKIP [inappropriate] %s - keyword: %s", ctx.url, matched_inappropriate[0])
        mark_stage(ctx, "filter_profile", "skipped", "inappropriate_content")
        return False

    matched_spam = [kw for kw in SPAM_TITLE_KEYWORDS if kw in title_text]
    matched_spam.extend([kw for kw in SPAM_KEYWORDS if kw in content_text])
    if matched_spam:
        ctx.result["error"] = "Spam keywords detected"
        ctx.result["error_code"] = ERROR_FILTERED_SPAM
        ctx.result["success"] = True
        ctx.result["notion_url"] = "(skipped-filtered)"
        ctx.result["failure_stage"] = "filter"
        ctx.result["failure_reason"] = "spam_keywords_detected"
        mark_stage(ctx, "filter_profile", "skipped", "spam_keywords_detected")
        return False

    return True


def _check_quality(ctx: ProcessRunContext, config) -> bool:
    """스크레이프 품질 점수 필터.

    품질 점수가 임계값 미만이면 False 반환합니다.
    """
    quality = ctx.quality
    post_data = ctx.post_data

    has_visual_content = bool(post_data.get("screenshot_path") or post_data.get("images"))
    effective_quality_threshold = QUALITY_SCORE_THRESHOLD - 20 if has_visual_content else QUALITY_SCORE_THRESHOLD

    if quality["score"] < effective_quality_threshold:
        ctx.result["error"] = "Low quality content"
        ctx.result["error_code"] = ERROR_FILTERED_LOW_QUALITY
        ctx.result["success"] = True
        ctx.result["notion_url"] = "(skipped-filtered)"
        ctx.result["failure_stage"] = "filter"
        ctx.result["failure_reason"] = quality["reasons"][0] if quality["reasons"] else "low_quality_score"
        mark_stage(ctx, "filter_profile", "skipped", "low_quality_score")
        return False

    return True


def _build_profile_and_decision(ctx: ProcessRunContext, config, top_tweets, review_only: bool) -> bool:
    """콘텐츠 프로파일 생성 및 리뷰 결정, 감정 필터 적용.

    통과 시 ctx.profile, ctx.decision, ctx.result 업데이트.
    감정 축 거부 대상이면 False 반환.
    """
    post_data = ctx.post_data
    quality = ctx.quality

    ranking_weights = config.get("ranking.weights", {}) if config else {}
    llm_viral_boost = bool(config.get("ranking.llm_viral_boost", False)) if config else False
    profile = build_content_profile(
        post_data,
        scrape_quality_score=quality["score"],
        historical_examples=top_tweets,
        ranking_weights=ranking_weights,
        llm_viral_boost=llm_viral_boost,
    ).to_dict()
    decision = (
        build_review_decision(config, post_data, profile)
        if config
        else {
            "should_queue": True,
            "status": "검토필요",
            "review_reason": "queued_for_review",
            "review_priority": "normal",
        }
    )

    ctx.profile = profile
    ctx.result["quality_score"] = profile["scrape_quality_score"]
    ctx.result["publishability_score"] = profile["publishability_score"]
    ctx.result["performance_score"] = profile["performance_score"]
    ctx.result["final_rank_score"] = profile["final_rank_score"]

    # 감정 축 거부 필터
    if profile.get("emotion_axis") in REJECT_EMOTION_AXES:
        ctx.result["error"] = f"Rejected: emotion_axis='{profile['emotion_axis']}' not suitable for publishing"
        ctx.result["error_code"] = ERROR_FILTERED_SPAM
        ctx.result["success"] = True
        ctx.result["notion_url"] = "(skipped-filtered)"
        ctx.result["failure_stage"] = "filter"
        ctx.result["failure_reason"] = "rejected_emotion_axis"
        logger.info("SKIP [emotion_filter] %s - emotion=%s", ctx.url, profile["emotion_axis"])
        mark_stage(ctx, "filter_profile", "skipped", "rejected_emotion_axis")
        return False

    # 세분화 감정 프로파일 (KOTE 44차원) — 실패 시 무시
    try:
        from pipeline.emotion_analyzer import get_emotion_profile

        emotion_profile = get_emotion_profile(f"{post_data.get('title', '')} {str(post_data.get('content', ''))[:300]}")
        if emotion_profile.confidence > 0:
            post_data["emotion_profile"] = {
                "top_emotions": emotion_profile.top_emotions[:3],
                "valence": emotion_profile.valence,
                "arousal": emotion_profile.arousal,
                "dominant_group": emotion_profile.dominant_group,
            }
    except Exception:
        pass

    # 감정 트래킹 — 실패 시 무시
    if sentiment_tracker is not None:
        try:
            sentiment_tracker.record(
                url=ctx.url,
                title=post_data.get("title", ""),
                content=str(ctx.content_text)[:1000],
                emotion_axis=profile.get("emotion_axis", ""),
                source=post_data.get("source", ""),
            )
        except Exception as tracker_exc:
            logger.debug("Sentiment tracking failed: %s", tracker_exc)

    # review_only 오버라이드
    if review_only and not decision["should_queue"]:
        logger.info("[review_only] overriding review queue decision for %s: %s", ctx.url, decision["review_reason"])
        decision = {
            **decision,
            "should_queue": True,
            "status": "검토필요",
            "review_reason": f"review_only_override:{decision['review_reason']}",
        }

    ctx.decision = decision
    ctx.result["status"] = decision.get("status", "검토필요")

    if not decision["should_queue"]:
        ctx.result["error"] = "Below review threshold"
        ctx.result["error_code"] = ERROR_FILTERED_LOW_QUALITY
        ctx.result["success"] = True
        ctx.result["notion_url"] = "(skipped-filtered)"
        ctx.result["failure_stage"] = "filter"
        ctx.result["failure_reason"] = decision["review_reason"]
        mark_stage(ctx, "filter_profile", "skipped", decision["review_reason"])
        return False

    post_data["content_profile"] = profile
    post_data["status"] = decision.get("status", "검토필요")
    post_data["review_reason"] = decision.get("review_reason", "")
    post_data["review_priority"] = decision["review_priority"]
    return True


async def _check_viral_and_calendar(ctx: ProcessRunContext, config) -> bool:
    """바이럴 필터 + 콘텐츠 캘린더 다양성 + 예산 초과 확인."""
    post_data = ctx.post_data
    profile = ctx.profile

    # 바이럴 필터 — LLM 기반
    viral_filter = get_viral_filter(config)
    if viral_filter is not None:
        try:
            viral_score = await viral_filter.score(
                title=post_data.get("title", ""),
                content=str(ctx.content_text)[:2000],
                source=post_data.get("source", ""),
                likes=int(post_data.get("likes", 0) or 0),
                comments=int(post_data.get("comments", 0) or 0),
            )
            post_data["viral_score"] = viral_score.to_dict()
            if not viral_score.pass_filter:
                ctx.result["error"] = (
                    f"Viral filter: score {viral_score.score:.0f} < threshold ({viral_score.reasoning})"
                )
                ctx.result["error_code"] = ERROR_FILTERED_LOW_QUALITY
                ctx.result["success"] = True
                ctx.result["notion_url"] = "(skipped-viral-filter)"
                ctx.result["failure_stage"] = "filter"
                ctx.result["failure_reason"] = "viral_filter_below_threshold"
                logger.info(
                    "[ViralFilter] SKIP %s: score=%.0f reason=%s", ctx.url, viral_score.score, viral_score.reasoning
                )
                mark_stage(ctx, "filter_profile", "skipped", "viral_filter_below_threshold")
                return False
        except Exception as viral_exc:
            logger.debug("Viral filter skipped: %s", viral_exc)

    # 콘텐츠 캘린더 다양성 체크
    try:
        from pipeline.content_calendar import ContentCalendar
        from pipeline.cost_db import get_cost_db

        calendar = ContentCalendar(cost_db=get_cost_db())
        calendar_ok, calendar_reason = calendar.should_post_topic(
            topic_cluster=profile.get("topic_cluster", ""),
            hook_type=profile.get("hook_type", ""),
            emotion_axis=profile.get("emotion_axis", ""),
        )
        if not calendar_ok:
            ctx.result["error"] = f"Calendar skip: {calendar_reason}"
            ctx.result["error_code"] = ERROR_FILTERED_LOW_QUALITY
            ctx.result["success"] = True
            ctx.result["notion_url"] = "(skipped-calendar)"
            ctx.result["failure_stage"] = "filter"
            ctx.result["failure_reason"] = "content_calendar_diversity"
            logger.info("[Calendar] SKIP %s: %s", ctx.url, calendar_reason)
            mark_stage(ctx, "filter_profile", "skipped", "content_calendar_diversity")
            return False
    except Exception as exc:
        logger.debug("Content calendar check skipped: %s", exc)

    # 일일 API 예산 한도 확인
    try:
        from pipeline.cost_db import get_cost_db

        budget_limit = float(config.get("limits.daily_api_budget", 3.0)) if config else 3.0
        if get_cost_db().is_daily_budget_exceeded(budget_limit):
            ctx.result["error"] = f"Daily API budget exceeded (limit ${budget_limit:.2f})"
            ctx.result["error_code"] = ERROR_BUDGET_EXCEEDED
            ctx.result["failure_stage"] = "budget"
            ctx.result["failure_reason"] = "daily_budget_exceeded"
            logger.warning("SKIP [budget exceeded] %s: limit=$%.2f", ctx.url, budget_limit)
            mark_stage(ctx, "filter_profile", "failed", "daily_budget_exceeded")
            return False
    except Exception as exc:
        logger.debug("Budget check skipped: %s", exc)

    return True


# ---------------------------------------------------------------------------
# 오케스트레이터 — 5개 필터를 순서대로 호출
# ---------------------------------------------------------------------------


async def run_filter_profile_stage(
    ctx: ProcessRunContext,
    scraper,
    config,
    top_tweets,
    review_only: bool = False,
) -> bool:
    """필터/프로파일 스테이지 오케스트레이터.

    실행 순서:
        1. 길이 필터
        2. 스팸/부적절 키워드 필터
        3. 품질 점수 필터
        4. 콘텐츠 프로파일 + 감정 필터 + 리뷰 결정
        5. 바이럴 필터 + 캘린더 + 예산

    각 단계가 False를 반환하면 즉시 중단합니다.
    """
    mark_stage(ctx, "filter_profile", "running")

    if not _check_length(ctx, scraper):
        return False
    if not _check_spam(ctx):
        return False
    if not _check_quality(ctx, config):
        return False
    if not _build_profile_and_decision(ctx, config, top_tweets, review_only):
        return False
    if not await _check_viral_and_calendar(ctx, config):
        return False

    mark_stage(ctx, "filter_profile", "completed")
    return True
