"""Draft generation/review stage for `process_single_post()`."""

from __future__ import annotations

import asyncio

from config import ERROR_DRAFT_GENERATION_FAILED
from pipeline.draft_contract import iter_publishable_drafts

from .context import ProcessRunContext, mark_stage
from .runtime import logger


async def run_generate_review_stage(
    ctx: ProcessRunContext,
    draft_generator,
    image_uploader,
    top_tweets,
    output_formats,
    config,
) -> bool:
    mark_stage(ctx, "generate_review", "running")
    if draft_generator is None:
        ctx.result["error"] = "Draft generator not configured"
        ctx.result["error_code"] = ERROR_DRAFT_GENERATION_FAILED
        ctx.result["failure_stage"] = "generation"
        ctx.result["failure_reason"] = "missing_draft_generator"
        mark_stage(ctx, "generate_review", "failed", "missing_draft_generator")
        return False

    if ctx.post_data.get("screenshot_path"):
        ctx.screenshot_task = asyncio.ensure_future(image_uploader.upload(ctx.post_data["screenshot_path"]))

    drafts_output = await draft_generator.generate_drafts(
        ctx.post_data,
        top_tweets=top_tweets,
        output_formats=output_formats,
    )
    if isinstance(drafts_output, tuple):
        drafts = drafts_output[0]
        image_prompt = drafts_output[1] if len(drafts_output) > 1 else None
    else:
        drafts = drafts_output
        image_prompt = None

    if isinstance(drafts, dict) and "twitter" in (output_formats or ["twitter"]):
        reply_text = drafts.get("reply_text", "")
        if not reply_text:
            profile_topic = (ctx.profile or {}).get("topic_cluster", "직장인")
            drafts["reply_text"] = f"원문: {ctx.url}\n#{profile_topic}"
        elif "(링크)" in reply_text:
            drafts["reply_text"] = reply_text.replace("(링크)", ctx.url)

    if isinstance(drafts, dict) and drafts.get("_generation_failed"):
        ctx.result["error"] = drafts.get("_generation_error", "Draft generation failed")
        ctx.result["error_code"] = ERROR_DRAFT_GENERATION_FAILED
        ctx.result["failure_stage"] = "generation"
        ctx.result["failure_reason"] = "generation_failed"
        logger.error("[%s] Draft generation failed for %s: %s", ctx.trace_id, ctx.url, ctx.result["error"])
        mark_stage(ctx, "generate_review", "failed", "generation_failed")
        return False

    max_qg_retries = 2
    qg_retry_count = 0
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

                retry_platforms = []
                for platform, quality_result in qg_results.items():
                    if quality_result.should_retry:
                        failed_issues = [
                            f"{item.rule}: {item.detail}" for item in quality_result.items if not item.passed
                        ]
                        retry_platforms.append(
                            {
                                "platform": platform,
                                "score": quality_result.score,
                                "issues": failed_issues,
                            }
                        )
                        logger.warning(
                            "Quality gate FAILED for %s: score=%d, %s", platform, quality_result.score, ctx.url
                        )
                    elif not quality_result.passed:
                        logger.warning(
                            "Quality gate FAILED (no retry) for %s: score=%d, %s",
                            platform,
                            quality_result.score,
                            ctx.url,
                        )
                    elif quality_result.score < 70:
                        logger.info("Quality gate WARNING for %s: score=%d", platform, quality_result.score)

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
                    )
                    if isinstance(drafts_output, tuple):
                        drafts = drafts_output[0]
                        image_prompt = drafts_output[1] if len(drafts_output) > 1 else image_prompt
                    else:
                        drafts = drafts_output
                    continue
                break
            except Exception as exc:
                logger.warning("[generate_review] DraftQualityGate unavailable: %s", exc)
                break

    ctx.post_data["quality_gate_retries"] = qg_retry_count
    if qg_retry_count > 0:
        logger.info("[B-5] Quality gate retries used: %d/%d", qg_retry_count, max_qg_retries)

    if isinstance(drafts, dict):
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

    ctx.result["components_loaded"] = components_loaded
    if components_loaded:
        logger.debug("[generate_review] loaded components: %s", components_loaded)

    ctx.drafts = drafts
    ctx.image_prompt = image_prompt
    ctx.post_data["image_prompt"] = image_prompt
    mark_stage(ctx, "generate_review", "completed")
    return True
