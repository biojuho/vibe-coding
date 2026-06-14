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
    ERROR_FILTERED_EDITORIAL,
    ERROR_FILTERED_LOW_QUALITY,
    ERROR_FILTERED_SHORT,
    ERROR_FILTERED_SPAM,
    QUALITY_SCORE_THRESHOLD,
)
from config import as_bool as _as_bool
from pipeline.content_intelligence import build_content_profile, evaluate_candidate_editorial_fit
from pipeline.daily_queue_floor import DailyQueueFloorState, is_daily_queue_floor_active
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


def _has_visual_content(post_data: dict) -> bool:
    return bool(post_data.get("screenshot_path") or post_data.get("images"))


def _is_daily_queue_floor_override_active(ctx: ProcessRunContext) -> bool:
    return is_daily_queue_floor_active(getattr(ctx, "daily_queue_floor", None))


def _add_daily_queue_floor_override(ctx: ProcessRunContext, reason: str) -> None:
    overrides = ctx.post_data.setdefault("daily_queue_floor_overrides", [])
    if reason not in overrides:
        overrides.append(reason)


def _set_filter_result(
    ctx: ProcessRunContext,
    *,
    error: str,
    error_code: str,
    failure_stage: str,
    failure_reason: str,
    stage_status: str,
    stage_reason: str | None = None,
    success: bool | None = True,
    notion_url: str | None = "(skipped-filtered)",
    extra: dict | None = None,
) -> None:
    ctx.result["error"] = error
    ctx.result["error_code"] = error_code
    if success is not None:
        ctx.result["success"] = success
    if notion_url is not None:
        ctx.result["notion_url"] = notion_url
    ctx.result["failure_stage"] = failure_stage
    ctx.result["failure_reason"] = failure_reason
    if extra is not None:
        ctx.result.update(extra)
    mark_stage(ctx, "filter_profile", stage_status, stage_reason or failure_reason)


def _set_filter_skip(
    ctx: ProcessRunContext,
    *,
    error: str,
    error_code: str,
    failure_reason: str,
    stage_reason: str | None = None,
    notion_url: str = "(skipped-filtered)",
    extra: dict | None = None,
) -> None:
    _set_filter_result(
        ctx,
        error=error,
        error_code=error_code,
        notion_url=notion_url,
        failure_stage="filter",
        failure_reason=failure_reason,
        stage_status="skipped",
        stage_reason=stage_reason,
        extra=extra,
    )


def _build_content_profile_dict(ctx: ProcessRunContext, config, top_tweets) -> dict:
    ranking_weights = config.get("ranking.weights", {}) if config else {}
    llm_viral_boost = _as_bool(config.get("ranking.llm_viral_boost", False)) if config else False
    return build_content_profile(
        ctx.post_data,
        scrape_quality_score=ctx.quality["score"],
        historical_examples=top_tweets,
        ranking_weights=ranking_weights,
        llm_viral_boost=llm_viral_boost,
    ).to_dict()


def _build_review_queue_decision(config, post_data: dict, profile: dict) -> dict:
    if config:
        return build_review_decision(config, post_data, profile)
    return {
        "should_queue": True,
        "status": "검토필요",
        "review_reason": "queued_for_review",
        "review_priority": "normal",
    }


def _store_profile_scores(ctx: ProcessRunContext, profile: dict) -> None:
    ctx.profile = profile
    ctx.result["quality_score"] = profile["scrape_quality_score"]
    ctx.result["publishability_score"] = profile["publishability_score"]
    ctx.result["performance_score"] = profile["performance_score"]
    ctx.result["final_rank_score"] = profile["final_rank_score"]


def _reject_unsuitable_emotion(ctx: ProcessRunContext, profile: dict) -> bool:
    emotion_axis = profile.get("emotion_axis")
    if emotion_axis not in REJECT_EMOTION_AXES:
        return False

    _set_filter_skip(
        ctx,
        error=f"Rejected: emotion_axis='{emotion_axis}' not suitable for publishing",
        error_code=ERROR_FILTERED_SPAM,
        failure_reason="rejected_emotion_axis",
    )
    logger.info("SKIP [emotion_filter] %s - emotion=%s", ctx.url, emotion_axis)
    return True


def _attach_emotion_profile(ctx: ProcessRunContext) -> None:
    post_data = ctx.post_data
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


def _record_sentiment(ctx: ProcessRunContext, profile: dict) -> None:
    if sentiment_tracker is None:
        return

    try:
        sentiment_tracker.record(
            url=ctx.url,
            title=ctx.post_data.get("title", ""),
            content=str(ctx.content_text)[:1000],
            emotion_axis=profile.get("emotion_axis", ""),
            source=ctx.post_data.get("source", ""),
        )
    except Exception as tracker_exc:
        logger.debug("Sentiment tracking failed: %s", tracker_exc)


def _maybe_force_review_queue(ctx: ProcessRunContext, decision: dict, review_only: bool) -> dict:
    if not review_only or decision["should_queue"]:
        return decision

    override_prefix = (
        "daily_queue_floor_override" if _is_daily_queue_floor_override_active(ctx) else "review_only_override"
    )
    logger.info("[review_only] overriding review queue decision for %s: %s", ctx.url, decision["review_reason"])
    return {
        **decision,
        "should_queue": True,
        "status": "검토필요",
        "review_reason": f"{override_prefix}:{decision['review_reason']}",
    }


def _reject_review_decision(ctx: ProcessRunContext, decision: dict) -> bool:
    if decision["should_queue"]:
        return False

    _set_filter_skip(
        ctx,
        error="Below review threshold",
        error_code=ERROR_FILTERED_LOW_QUALITY,
        failure_reason=decision["review_reason"],
    )
    return True


def _store_review_metadata(ctx: ProcessRunContext, profile: dict, decision: dict) -> None:
    ctx.post_data["content_profile"] = profile
    ctx.post_data["status"] = decision.get("status", "검토필요")
    ctx.post_data["review_reason"] = decision.get("review_reason", "")
    ctx.post_data["review_priority"] = decision["review_priority"]


def _editorial_gate_failure(fit: dict, min_score: float) -> tuple[str, str, list]:
    hard_reject_reasons = list(fit.get("hard_reject_reasons") or [])
    if _as_bool(fit.get("hard_reject")):
        return (
            "editorial_hard_reject",
            "; ".join(hard_reject_reasons) or "편집 적합도 하드 리젝트",
            hard_reject_reasons,
        )
    score = float(fit.get("score", 0.0) or 0.0)
    return (
        "editorial_score_below_threshold",
        f"편집 적합도 {score:.0f} < {min_score:.0f}",
        hard_reject_reasons,
    )


def _reject_editorial_fit(
    ctx: ProcessRunContext,
    *,
    failure_reason: str,
    human: str,
    hard_reject_reasons: list,
    score: float,
) -> bool:
    if _is_daily_queue_floor_override_active(ctx):
        _add_daily_queue_floor_override(ctx, failure_reason)
        logger.info("[daily_queue_floor] override editorial gate for %s: %s", ctx.url, human)
        return True

    _set_filter_skip(
        ctx,
        error=f"Editorial gate: {human}",
        error_code=ERROR_FILTERED_EDITORIAL,
        notion_url="(skipped-editorial)",
        failure_reason=failure_reason,
        extra={"editorial_reject_reasons": hard_reject_reasons},
    )
    logger.info("SKIP [editorial] %s - %s (score=%.0f)", ctx.url, human, score)
    return False


async def _check_viral_filter(ctx: ProcessRunContext, config) -> bool:
    post_data = ctx.post_data
    viral_filter = get_viral_filter(config)
    if viral_filter is None:
        return True

    try:
        viral_score = await viral_filter.score(
            title=post_data.get("title", ""),
            content=str(ctx.content_text)[:2000],
            source=post_data.get("source", ""),
            likes=int(post_data.get("likes", 0) or 0),
            comments=int(post_data.get("comments", 0) or 0),
        )
        post_data["viral_score"] = viral_score.to_dict()
        return _handle_viral_score(ctx, viral_score)
    except Exception as viral_exc:
        logger.debug("Viral filter skipped: %s", viral_exc)
        return True


def _handle_viral_score(ctx: ProcessRunContext, viral_score) -> bool:
    if viral_score.pass_filter:
        return True

    if _is_daily_queue_floor_override_active(ctx):
        _add_daily_queue_floor_override(ctx, "viral_filter_below_threshold")
        logger.info(
            "[daily_queue_floor] override viral filter for %s: score=%.0f",
            ctx.url,
            viral_score.score,
        )
        return True

    _set_filter_skip(
        ctx,
        error=f"Viral filter: score {viral_score.score:.0f} < threshold ({viral_score.reasoning})",
        error_code=ERROR_FILTERED_LOW_QUALITY,
        notion_url="(skipped-viral-filter)",
        failure_reason="viral_filter_below_threshold",
    )
    logger.info("[ViralFilter] SKIP %s: score=%.0f reason=%s", ctx.url, viral_score.score, viral_score.reasoning)
    return False


def _check_content_calendar(ctx: ProcessRunContext) -> bool:
    try:
        from pipeline.content_calendar import ContentCalendar
        from pipeline.cost_db import get_cost_db

        calendar = ContentCalendar(cost_db=get_cost_db())
        calendar_ok, calendar_reason = calendar.should_post_topic(
            topic_cluster=ctx.profile.get("topic_cluster", ""),
            hook_type=ctx.profile.get("hook_type", ""),
            emotion_axis=ctx.profile.get("emotion_axis", ""),
        )
        return _handle_calendar_result(ctx, calendar_ok, calendar_reason)
    except Exception as exc:
        logger.debug("Content calendar check skipped: %s", exc)
        return True


def _check_calendar_diversity(ctx: ProcessRunContext) -> bool:
    return _check_content_calendar(ctx)


def _handle_calendar_result(ctx: ProcessRunContext, calendar_ok: bool, calendar_reason: str) -> bool:
    if calendar_ok:
        return True

    if _is_daily_queue_floor_override_active(ctx):
        _add_daily_queue_floor_override(ctx, "content_calendar_diversity")
        logger.info("[daily_queue_floor] override calendar diversity for %s: %s", ctx.url, calendar_reason)
        return True

    _set_filter_skip(
        ctx,
        error=f"Calendar skip: {calendar_reason}",
        error_code=ERROR_FILTERED_LOW_QUALITY,
        notion_url="(skipped-calendar)",
        failure_reason="content_calendar_diversity",
    )
    logger.info("[Calendar] SKIP %s: %s", ctx.url, calendar_reason)
    return False


def _check_daily_budget(ctx: ProcessRunContext, config) -> bool:
    try:
        from pipeline.cost_db import get_cost_db

        budget_limit = float(config.get("limits.daily_api_budget", 3.0)) if config else 3.0
        if not get_cost_db().is_daily_budget_exceeded(budget_limit):
            return True
    except Exception as exc:
        logger.debug("Budget check skipped: %s", exc)
        return True

    _set_filter_result(
        ctx,
        error=f"Daily API budget exceeded (limit ${budget_limit:.2f})",
        error_code=ERROR_BUDGET_EXCEEDED,
        success=None,
        notion_url=None,
        failure_stage="budget",
        failure_reason="daily_budget_exceeded",
        stage_status="failed",
    )
    logger.warning("SKIP [budget exceeded] %s: limit=$%.2f", ctx.url, budget_limit)
    return False


# ---------------------------------------------------------------------------
# 내부 필터 함수들 — 각각 단일 필터 책임
# ---------------------------------------------------------------------------


def _check_length(ctx: ProcessRunContext, scraper) -> bool:
    """콘텐츠 최소 길이 필터.

    시각 콘텐츠(스크린샷/이미지)가 있으면 길이 제한을 0으로 완화합니다.
    """
    post_data = ctx.post_data
    content_text = ctx.content_text
    effective_min_length = 0 if _has_visual_content(post_data) else scraper.min_content_length

    if len(content_text) < effective_min_length:
        _set_filter_skip(
            ctx,
            error="Content too short (potential spam/empty)",
            error_code=ERROR_FILTERED_SHORT,
            failure_reason="content_too_short",
        )
        return False
    return True


def _check_spam(ctx: ProcessRunContext) -> bool:
    """스팸 및 부적절 콘텐츠 키워드 필터."""
    post_data = ctx.post_data
    content_text = ctx.content_text
    title_text = post_data.get("title", "")

    matched_inappropriate = [kw for kw in INAPPROPRIATE_TITLE_KEYWORDS if kw in title_text]
    if matched_inappropriate:
        _set_filter_skip(
            ctx,
            error=f"Inappropriate content detected: {matched_inappropriate[0]}",
            error_code=ERROR_FILTERED_SPAM,
            failure_reason="inappropriate_content",
        )
        logger.info("SKIP [inappropriate] %s - keyword: %s", ctx.url, matched_inappropriate[0])
        return False

    matched_spam = [kw for kw in SPAM_TITLE_KEYWORDS if kw in title_text]
    matched_spam.extend([kw for kw in SPAM_KEYWORDS if kw in content_text])
    if matched_spam:
        _set_filter_skip(
            ctx,
            error="Spam keywords detected",
            error_code=ERROR_FILTERED_SPAM,
            failure_reason="spam_keywords_detected",
        )
        return False

    return True


def _check_quality(ctx: ProcessRunContext, config) -> bool:
    """스크레이프 품질 점수 필터.

    품질 점수가 임계값 미만이면 False 반환합니다.
    """
    quality = ctx.quality
    post_data = ctx.post_data

    effective_quality_threshold = (
        QUALITY_SCORE_THRESHOLD - 20 if _has_visual_content(post_data) else QUALITY_SCORE_THRESHOLD
    )

    if quality["score"] < effective_quality_threshold:
        if _is_daily_queue_floor_override_active(ctx):
            _add_daily_queue_floor_override(ctx, "low_quality_score")
            logger.info(
                "[daily_queue_floor] override quality filter for %s: score=%.1f < %.1f",
                ctx.url,
                quality["score"],
                effective_quality_threshold,
            )
            return True

        failure_reason = quality["reasons"][0] if quality["reasons"] else "low_quality_score"
        _set_filter_skip(
            ctx,
            error="Low quality content",
            error_code=ERROR_FILTERED_LOW_QUALITY,
            failure_reason=failure_reason,
            stage_reason="low_quality_score",
        )
        return False

    return True


def _build_profile_and_decision(
    ctx: ProcessRunContext,
    config,
    top_tweets,
    review_only: bool,
) -> bool:
    """콘텐츠 프로파일 생성 및 리뷰 결정, 감정 필터 적용.

    통과 시 ctx.profile, ctx.decision, ctx.result 업데이트.
    감정 축 거부 대상이면 False 반환.
    """
    post_data = ctx.post_data
    profile = _build_content_profile_dict(ctx, config, top_tweets)
    decision = _build_review_queue_decision(config, post_data, profile)
    _store_profile_scores(ctx, profile)

    # 감정 축 거부 필터
    if _reject_unsuitable_emotion(ctx, profile):
        return False

    # 세분화 감정 프로파일 (KOTE 44차원) — 실패 시 무시
    _attach_emotion_profile(ctx)

    # 감정 트래킹 — 실패 시 무시
    _record_sentiment(ctx, profile)

    # review_only 오버라이드
    decision = _maybe_force_review_queue(ctx, decision, review_only)

    ctx.decision = decision
    ctx.result["status"] = decision.get("status", "검토필요")

    if _reject_review_decision(ctx, decision):
        return False

    _store_review_metadata(ctx, profile, decision)
    return True


def _check_editorial_fit(ctx: ProcessRunContext, config) -> bool:
    """본문 포함 전체 편집 적합도 게이트 (D-032).

    `feed_collector.py`의 사전 스크리닝은 제목만으로 낮은 bar(`min_pre_editorial_score`)
    를 적용하고 `hard_reject`를 의도적으로 무시한다 (D-029). 본문을 확보한 이 시점에서
    전체 편집 적합도를 다시 평가해 다음을 거른다:

      - `hard_reject` (추상적·파생각 부족·직장인 맥락 약함·갈등 낚시 과다)
      - 편집 적합도 점수 < `feed_filter.min_editorial_score`

    이 게이트는 `final_rank_score`(스크랩 품질·성과 휴리스틱이 섞여 편집 약점을
    가릴 수 있음)와 독립적인 축이다. `daily_queue_floor` 활성 시에는 다른 필터와
    동일하게 override 하고 사유를 기록한다.

    실패 시 `ctx.result`를 채우고 False를 반환한다.
    """
    post_data = ctx.post_data

    fit = evaluate_candidate_editorial_fit(
        title=str(post_data.get("title", "") or ""),
        source=str(post_data.get("source", "") or ""),
        content=str(ctx.content_text or ""),
    )
    # 다운스트림(Notion 메모·진단·run metrics)에서 참조할 수 있게 보존.
    post_data["editorial_fit"] = fit
    ctx.result["editorial_score"] = fit.get("score")

    if config is None or not _as_bool(config.get("feed_filter.editorial_gate_enabled", True), default=True):
        return True

    min_score = float(config.get("feed_filter.min_editorial_score", 60.0))
    score = float(fit.get("score", 0.0) or 0.0)

    if not _as_bool(fit.get("hard_reject")) and score >= min_score:
        return True

    failure_reason, human, hard_reject_reasons = _editorial_gate_failure(fit, min_score)
    return _reject_editorial_fit(
        ctx,
        failure_reason=failure_reason,
        human=human,
        hard_reject_reasons=hard_reject_reasons,
        score=score,
    )


async def _check_viral_and_calendar(ctx: ProcessRunContext, config) -> bool:
    """바이럴 필터 + 콘텐츠 캘린더 다양성 + 예산 초과 확인."""
    if not await _check_viral_filter(ctx, config):
        return False
    if not _check_content_calendar(ctx):
        return False
    return _check_daily_budget(ctx, config)


# ---------------------------------------------------------------------------
# 오케스트레이터 — 5개 필터를 순서대로 호출
# ---------------------------------------------------------------------------


async def run_filter_profile_stage(
    ctx: ProcessRunContext,
    scraper,
    config,
    top_tweets,
    review_only: bool = False,
    daily_queue_floor: DailyQueueFloorState | None = None,
) -> bool:
    """필터/프로파일 스테이지 오케스트레이터.

    실행 순서:
        1. 길이 필터
        2. 스팸/부적절 키워드 필터
        3. 품질 점수 필터
        4. 콘텐츠 프로파일 + 감정 필터 + 리뷰 결정
        5. 본문 포함 편집 적합도 게이트 (D-032)
        6. 바이럴 필터 + 캘린더 + 예산

    각 단계가 False를 반환하면 즉시 중단합니다.

    편집 적합도 게이트(5)는 LLM 바이럴 필터(6)보다 먼저 실행되어,
    편집 약점이 분명한 글에 대한 불필요한 LLM 호출 비용을 절감합니다.
    """
    mark_stage(ctx, "filter_profile", "running")
    ctx.daily_queue_floor = daily_queue_floor

    if not _check_length(ctx, scraper):
        return False
    if not _check_spam(ctx):
        return False
    if not _check_quality(ctx, config):
        return False
    if not _build_profile_and_decision(ctx, config, top_tweets, review_only):
        return False
    if not _check_editorial_fit(ctx, config):
        return False
    if not await _check_viral_and_calendar(ctx, config):
        return False

    mark_stage(ctx, "filter_profile", "completed")
    return True
