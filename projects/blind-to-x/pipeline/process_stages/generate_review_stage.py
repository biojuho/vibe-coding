"""Draft generation/review stage for `process_single_post()`."""

from __future__ import annotations

import asyncio

from config import ERROR_DRAFT_GENERATION_FAILED
from pipeline.draft_contract import iter_publishable_drafts
from pipeline.publish_decision import HOLD, decide_publish
from pipeline.publish_repair import repair_hold_draft
from pipeline.research_context import ensure_research_context

from .context import ProcessRunContext, mark_stage
from .runtime import logger


def _config_int(config, key: str, default: int) -> int:
    if config is None or not hasattr(config, "get"):
        return default
    try:
        value = int(config.get(key, default))
    except (TypeError, ValueError):
        return default
    return max(0, value)


def _config_bool(config, key: str, default: bool) -> bool:
    if config is None or not hasattr(config, "get"):
        return default
    value = config.get(key, default)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _config_float(config, key: str, default: float) -> float:
    if config is None or not hasattr(config, "get"):
        return default
    try:
        return float(config.get(key, default))
    except (TypeError, ValueError):
        return default


def _resolve_quality_gate_retries(config, review_only: bool) -> int:
    if review_only:
        return _config_int(config, "quality_gate.review_only_max_retries", 1)
    return _config_int(config, "quality_gate.max_retries", 2)


def _resolve_publish_repair_attempts(config) -> int:
    return _config_int(config, "publish.self_repair.max_attempts", 2)


def _twitter_quality_failure(drafts: dict, quality_gate, config) -> str | None:
    if not _config_bool(config, "review.require_twitter_quality_pass", False):
        return None

    twitter_text = str(drafts.get("twitter") or "").strip()
    try:
        result = quality_gate.validate("twitter", twitter_text)
        score = int(result.score)
    except Exception:
        return None
    min_score = _config_int(config, "review.min_twitter_quality_score", 80)

    if result.passed and score >= min_score:
        return None

    issues = [
        f"{item.rule}: {item.detail}"
        for item in result.items
        if not item.passed and item.severity in {"error", "warning"}
    ]
    if not issues:
        issues = [f"score {score} below minimum {min_score}"]
    return f"twitter_quality_gate_failed score={score} min={min_score}; " + "; ".join(issues[:3])


def _fail_missing_draft_generator(ctx: ProcessRunContext) -> bool:
    ctx.result["error"] = "Draft generator not configured"
    ctx.result["error_code"] = ERROR_DRAFT_GENERATION_FAILED
    ctx.result["failure_stage"] = "generation"
    ctx.result["failure_reason"] = "missing_draft_generator"
    mark_stage(ctx, "generate_review", "failed", "missing_draft_generator")
    return False


def _start_screenshot_upload(ctx: ProcessRunContext, image_uploader) -> None:
    if ctx.post_data.get("screenshot_path"):
        ctx.screenshot_task = asyncio.ensure_future(image_uploader.upload(ctx.post_data["screenshot_path"]))


def _split_drafts_output(drafts_output, fallback_image_prompt=None):
    if isinstance(drafts_output, tuple):
        drafts = drafts_output[0]
        image_prompt = drafts_output[1] if len(drafts_output) > 1 else fallback_image_prompt
    else:
        drafts = drafts_output
        image_prompt = fallback_image_prompt
    return drafts, image_prompt


def _ensure_twitter_reply_text(ctx: ProcessRunContext, drafts, output_formats) -> None:
    if not isinstance(drafts, dict) or "twitter" not in (output_formats or ["twitter"]):
        return

    reply_text = drafts.get("reply_text", "")
    if not reply_text:
        profile_topic = (ctx.profile or {}).get("topic_cluster", "직장인")
        drafts["reply_text"] = f"원문: {ctx.url}\n#{profile_topic}"
    elif "(링크)" in reply_text:
        drafts["reply_text"] = reply_text.replace("(링크)", ctx.url)


def _handle_generation_failure(ctx: ProcessRunContext, drafts, image_prompt, review_only: bool) -> bool | None:
    if not isinstance(drafts, dict) or not drafts.get("_generation_failed"):
        return None

    generation_error = drafts.get("_generation_error", "Draft generation failed")
    ctx.post_data["draft_generation_failed"] = True
    ctx.post_data["draft_generation_error"] = generation_error
    if review_only:
        logger.warning(
            "[%s] Draft generation failed for %s but continuing review-only upload: %s",
            ctx.trace_id,
            ctx.url,
            generation_error,
        )
        ctx.drafts = drafts
        ctx.image_prompt = image_prompt
        ctx.post_data["image_prompt"] = image_prompt
        mark_stage(ctx, "generate_review", "completed")
        return True

    ctx.result["error"] = drafts.get("_generation_error", "Draft generation failed")
    ctx.result["error_code"] = ERROR_DRAFT_GENERATION_FAILED
    ctx.result["failure_stage"] = "generation"
    ctx.result["failure_reason"] = "generation_failed"
    logger.error("[%s] Draft generation failed for %s: %s", ctx.trace_id, ctx.url, ctx.result["error"])
    mark_stage(ctx, "generate_review", "failed", "generation_failed")
    return False


def _collect_retry_platforms(qg_results, url: str) -> list[dict]:
    retry_platforms = []
    for platform, quality_result in qg_results.items():
        if quality_result.should_retry:
            failed_issues = [f"{item.rule}: {item.detail}" for item in quality_result.items if not item.passed]
            retry_platforms.append(
                {
                    "platform": platform,
                    "score": quality_result.score,
                    "issues": failed_issues,
                }
            )
            logger.warning("Quality gate FAILED for %s: score=%d, %s", platform, quality_result.score, url)
        elif not quality_result.passed:
            logger.warning(
                "Quality gate FAILED (no retry) for %s: score=%d, %s",
                platform,
                quality_result.score,
                url,
            )
        elif quality_result.score < 70:
            logger.info("Quality gate WARNING for %s: score=%d", platform, quality_result.score)
    return retry_platforms


def _refresh_quality_gate_snapshot(ctx: ProcessRunContext, drafts):
    try:
        from pipeline.draft_quality_gate import DraftQualityGate

        quality_gate = DraftQualityGate()
        qg_results = quality_gate.validate_all(drafts)
        ctx.post_data["quality_gate_report"] = quality_gate.format_summary(qg_results)
        ctx.post_data["quality_gate_scores"] = {platform: result.score for platform, result in qg_results.items()}
        return quality_gate
    except Exception as exc:
        logger.warning("[generate_review] DraftQualityGate refresh unavailable: %s", exc)
        return None


async def _run_quality_gate_retries(
    ctx: ProcessRunContext,
    drafts,
    image_prompt,
    draft_generator,
    top_tweets,
    output_formats,
    config,
    review_only: bool,
):
    max_qg_retries = _resolve_quality_gate_retries(config, review_only)
    qg_retry_count = 0
    quality_gate = None
    components_loaded: list[str] = []

    if isinstance(drafts, dict):
        for qg_attempt in range(max_qg_retries + 1):
            try:
                from pipeline.draft_quality_gate import DraftQualityGate

                if qg_attempt == 0:
                    components_loaded.append("DraftQualityGate")
                quality_gate = DraftQualityGate()
                qg_results = quality_gate.validate_all(drafts)
                qg_summary = quality_gate.format_summary(qg_results)
                ctx.post_data["quality_gate_report"] = qg_summary
                ctx.post_data["quality_gate_scores"] = {
                    platform: result.score for platform, result in qg_results.items()
                }

                retry_platforms = _collect_retry_platforms(qg_results, ctx.url)
                if retry_platforms and qg_attempt < max_qg_retries:
                    qg_retry_count += 1
                    logger.info(
                        "[B-5] Quality gate auto-retry %d/%d: regenerating for %s",
                        qg_retry_count,
                        max_qg_retries,
                        ", ".join(feedback["platform"] for feedback in retry_platforms),
                    )
                    drafts_output = await draft_generator.generate_drafts(
                        ctx.post_data,
                        top_tweets=top_tweets,
                        output_formats=output_formats,
                        quality_feedback=retry_platforms,
                        allow_partial=review_only,
                    )
                    drafts, image_prompt = _split_drafts_output(drafts_output, image_prompt)
                    continue
                break
            except Exception as exc:
                logger.warning("[generate_review] DraftQualityGate unavailable: %s", exc)
                break

    ctx.post_data["quality_gate_retries"] = qg_retry_count
    if qg_retry_count > 0:
        logger.info("[B-5] Quality gate retries used: %d/%d", qg_retry_count, max_qg_retries)
    return drafts, image_prompt, qg_retry_count, quality_gate, components_loaded


def _append_publish_decision_log(ctx: ProcessRunContext, *, stage: str, decision) -> None:
    payload = decision.to_dict() if hasattr(decision, "to_dict") else dict(decision or {})
    ctx.post_data.setdefault("publish_decision_log", []).append(
        {
            "stage": stage,
            "decision": payload,
        }
    )


def _twitter_draft_text(drafts) -> str:
    if not isinstance(drafts, dict):
        return ""
    return str(drafts.get("twitter") or "").strip()


def _run_publish_repair_loop(ctx: ProcessRunContext, drafts, config):
    if not isinstance(drafts, dict) or "twitter" not in drafts:
        return drafts, None

    max_attempts = _resolve_publish_repair_attempts(config)
    threshold = _config_float(config, "publish.quality_threshold", 85.0)
    research_context = ctx.post_data.get("research_context")
    attempts: list[dict] = []
    quality_gate = None

    for attempt in range(1, max_attempts + 1):
        decision = decide_publish(
            ctx.post_data.get("quality_gate_scores"),
            None,
            research_context,
            _twitter_draft_text(drafts),
            quality_threshold=threshold,
        )
        _append_publish_decision_log(ctx, stage=f"generate_review.pre_repair.{attempt}", decision=decision)
        if decision.action != HOLD or not decision.fixable:
            ctx.post_data["publish_repair_final_decision"] = decision.to_dict()
            break

        repair = repair_hold_draft(
            _twitter_draft_text(drafts),
            decision,
            research_context if isinstance(research_context, dict) else None,
        )
        attempt_entry = {
            "attempt": attempt,
            "before_decision": decision.to_dict(),
            "repair": repair.to_dict(),
        }
        attempts.append(attempt_entry)
        if not repair.changed:
            ctx.post_data["publish_repair_final_decision"] = decision.to_dict()
            ctx.post_data["publish_repair_exhausted"] = True
            break

        drafts["twitter"] = repair.text
        quality_gate = _refresh_quality_gate_snapshot(ctx, drafts)
        next_decision = decide_publish(
            ctx.post_data.get("quality_gate_scores"),
            None,
            research_context,
            _twitter_draft_text(drafts),
            quality_threshold=threshold,
        )
        attempt_entry["after_decision"] = next_decision.to_dict()
        _append_publish_decision_log(ctx, stage=f"generate_review.post_repair.{attempt}", decision=next_decision)
        if next_decision.action != HOLD:
            ctx.post_data["publish_repair_final_decision"] = next_decision.to_dict()
            break

        if attempt == max_attempts:
            ctx.post_data["publish_repair_final_decision"] = next_decision.to_dict()
            ctx.post_data["publish_repair_exhausted"] = True

    if attempts:
        ctx.post_data["publish_repair_attempts"] = attempts
        logger.info("[publish-repair] attempts used: %d/%d", len(attempts), max_attempts)
    return drafts, quality_gate


async def _apply_editorial_review(ctx: ProcessRunContext, drafts, config, components_loaded: list[str]):
    try:
        from pipeline.editorial_reviewer import EditorialReviewer

        components_loaded.append("EditorialReviewer")
        reviewer = EditorialReviewer(config=config)
        editorial_result = await reviewer.review_and_polish(drafts, ctx.post_data)
        drafts = editorial_result.polished_drafts
        ctx.post_data["editorial_scores"] = editorial_result.scores
        ctx.post_data["editorial_avg_score"] = editorial_result.avg_score
        if editorial_result.suggestions:
            ctx.post_data["editorial_suggestions"] = editorial_result.suggestions
        if editorial_result.avg_score > 0:
            logger.info(
                "[Editorial] avg=%.1f, platforms=%d",
                editorial_result.avg_score,
                len(editorial_result.original_drafts),
            )
    except Exception as exc:
        logger.warning("[generate_review] EditorialReviewer unavailable: %s", exc)
    return drafts


def _apply_fact_checks(ctx: ProcessRunContext, drafts, components_loaded: list[str]) -> None:
    try:
        from pipeline.fact_checker import verify_facts

        components_loaded.append("FactChecker")
        source_content = str(ctx.post_data.get("content", ""))
        for platform, draft_text in iter_publishable_drafts(drafts):
            fact_check = verify_facts(source_content, draft_text)
            if not fact_check.passed:
                logger.warning(
                    "[FactCheck] %s: fabricated %d %s",
                    platform,
                    len(fact_check.fabricated_items),
                    fact_check.fabricated_items[:5],
                )
                ctx.post_data.setdefault("fact_check_warnings", {})[platform] = fact_check.fabricated_items
    except Exception as exc:
        logger.warning("[generate_review] FactChecker unavailable: %s", exc)


def _apply_readability_scores(ctx: ProcessRunContext, drafts, components_loaded: list[str]) -> None:
    try:
        from pipeline.text_polisher import TextPolisher

        components_loaded.append("TextPolisher")
        polisher = TextPolisher(fix_spacing=False, fix_typo=False)
        if polisher.available:
            readability_scores = {}
            for platform, draft_text in iter_publishable_drafts(drafts):
                readability_scores[platform] = polisher.compute_readability(draft_text)
            if readability_scores:
                ctx.post_data["readability_scores"] = readability_scores
                logger.info("[Readability] %s", readability_scores)
    except Exception as exc:
        logger.warning("[generate_review] TextPolisher unavailable: %s", exc)


async def _apply_draft_validator(ctx: ProcessRunContext, drafts, draft_generator, config, components_loaded: list[str]):
    try:
        from pipeline.draft_validator import validate_and_fix_drafts

        components_loaded.append("DraftValidator")
        drafts = await validate_and_fix_drafts(
            drafts,
            ctx.post_data,
            generator=draft_generator,
            config=config,
        )
    except Exception as exc:
        logger.warning("[generate_review] DraftValidator unavailable: %s", exc)
    return drafts


async def _run_post_generation_components(
    ctx: ProcessRunContext,
    drafts,
    draft_generator,
    config,
    components_loaded: list[str],
):
    drafts = await _apply_editorial_review(ctx, drafts, config, components_loaded)
    _apply_fact_checks(ctx, drafts, components_loaded)
    _apply_readability_scores(ctx, drafts, components_loaded)
    return await _apply_draft_validator(ctx, drafts, draft_generator, config, components_loaded)


def _fail_twitter_quality_gate(ctx: ProcessRunContext, failure: str) -> bool:
    ctx.post_data["twitter_quality_failure"] = failure
    ctx.result["error"] = "Twitter draft did not meet review quality gate"
    ctx.result["error_code"] = ERROR_DRAFT_GENERATION_FAILED
    ctx.result["failure_stage"] = "generation"
    ctx.result["failure_reason"] = "twitter_quality_gate_failed"
    logger.warning("[%s] %s: %s", ctx.trace_id, ctx.url, failure)
    mark_stage(ctx, "generate_review", "failed", "twitter_quality_gate_failed")
    return False


def _complete_generate_review_stage(
    ctx: ProcessRunContext,
    drafts,
    image_prompt,
    components_loaded: list[str],
) -> bool:
    ctx.result["components_loaded"] = components_loaded
    if components_loaded:
        logger.debug("[generate_review] loaded components: %s", components_loaded)

    ctx.drafts = drafts
    ctx.image_prompt = image_prompt
    ctx.post_data["image_prompt"] = image_prompt
    mark_stage(ctx, "generate_review", "completed")
    return True


async def run_generate_review_stage(
    ctx: ProcessRunContext,
    draft_generator,
    image_uploader,
    top_tweets,
    output_formats,
    config,
    review_only: bool = False,
) -> bool:
    mark_stage(ctx, "generate_review", "running")
    if draft_generator is None:
        return _fail_missing_draft_generator(ctx)

    _start_screenshot_upload(ctx, image_uploader)
    research_context = ensure_research_context(ctx.post_data)
    if research_context.get("value_reduction_failed"):
        logger.info("[%s] research_context value reduction failed before generation", ctx.trace_id)

    drafts_output = await draft_generator.generate_drafts(
        ctx.post_data,
        top_tweets=top_tweets,
        output_formats=output_formats,
        allow_partial=review_only,
    )
    drafts, image_prompt = _split_drafts_output(drafts_output)
    _ensure_twitter_reply_text(ctx, drafts, output_formats)

    generation_result = _handle_generation_failure(ctx, drafts, image_prompt, review_only)
    if generation_result is not None:
        return generation_result

    drafts, image_prompt, _, quality_gate, components_loaded = await _run_quality_gate_retries(
        ctx,
        drafts,
        image_prompt,
        draft_generator,
        top_tweets,
        output_formats,
        config,
        review_only,
    )

    if isinstance(drafts, dict):
        drafts = await _run_post_generation_components(ctx, drafts, draft_generator, config, components_loaded)
        repaired_drafts, repair_quality_gate = _run_publish_repair_loop(ctx, drafts, config)
        drafts = repaired_drafts
        if repair_quality_gate is not None:
            quality_gate = repair_quality_gate
        if quality_gate is not None and "twitter" in (output_formats or ["twitter"]):
            failure = _twitter_quality_failure(drafts, quality_gate, config)
            if failure:
                return _fail_twitter_quality_gate(ctx, failure)

    return _complete_generate_review_stage(ctx, drafts, image_prompt, components_loaded)
