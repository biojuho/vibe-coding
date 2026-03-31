"""Persist/publish stage for `process_single_post()`."""

from __future__ import annotations

import asyncio
import os

from config import ERROR_NOTION_UPLOAD_FAILED
from pipeline.draft_analytics import record_draft_event, refresh_ml_scorer_if_needed

from .context import ProcessRunContext, mark_stage
from .runtime import extract_preferred_tweet_text, logger, notebooklm_enricher, post_to_twitter, regulation_checker


async def run_persist_stage(
    ctx: ProcessRunContext,
    image_uploader,
    image_generator,
    notion_uploader,
    twitter_poster,
    config,
    review_only: bool,
) -> bool:
    mark_stage(ctx, "persist", "running")

    if notion_uploader is None:
        ctx.result["error"] = "Notion uploader not configured"
        ctx.result["error_code"] = ERROR_NOTION_UPLOAD_FAILED
        ctx.result["failure_stage"] = "upload"
        ctx.result["failure_reason"] = "missing_notion_uploader"
        mark_stage(ctx, "persist", "failed", "missing_notion_uploader")
        return False

    post_data = ctx.post_data
    profile = ctx.profile
    drafts = ctx.drafts
    image_prompt = ctx.image_prompt

    nlm_task = None
    if notebooklm_enricher is not None and os.environ.get("NOTEBOOKLM_ENABLED") == "true":
        nlm_topic = profile.get("topic_cluster") or post_data.get("title", "")
        nlm_task = asyncio.ensure_future(notebooklm_enricher(nlm_topic, image_uploader=image_uploader))

    if regulation_checker and isinstance(drafts, dict):
        try:
            validation_reports = regulation_checker.validate_all_drafts(drafts)
            regulation_report_text = regulation_checker.format_validation_summary(validation_reports)
            post_data["regulation_report"] = regulation_report_text

            llm_check = drafts.get("_regulation_check", "")
            if llm_check:
                post_data["regulation_report"] += f"\n\n[LLM 자체 검증]\n{llm_check}"

            for platform, report in validation_reports.items():
                if not report.passed:
                    logger.warning(
                        "Regulation check FAILED for %s: score=%d, %s",
                        platform,
                        report.score,
                        ctx.url,
                    )
        except Exception as exc:
            logger.debug("Regulation check skipped: %s", exc)

    ai_image_task = None
    original_image_url = None
    source = (post_data.get("source") or "").lower()
    is_blind = source in {"blind", "블라인드"}
    is_community = source in {"ppomppu", "뽐뿌", "fmkorea", "에펨코리아"}
    image_urls = post_data.get("image_urls")

    if is_community:
        if image_urls and isinstance(image_urls, list):
            original_image_url = image_urls[0]
            logger.info("[%s] Using original image from post: %s", source, original_image_url)
        else:
            logger.info("[%s] No original image found, will use screenshot only.", source)
    elif is_blind and image_generator:
        topic_cluster = profile.get("topic_cluster", "")
        emotion_axis = profile.get("emotion_axis", "")

        from pipeline.image_generator import ImageGenerator

        image_prompt = ImageGenerator.build_image_prompt(
            topic_cluster=topic_cluster,
            emotion_axis=emotion_axis,
            title=post_data.get("title", ""),
            source="blind",
        )
        logger.info("[blind] Anime image prompt: %s", image_prompt[:80])
        post_data["image_prompt"] = image_prompt

        try:
            ab_active = config.get("image_ab_testing.enabled", False) if config else False
            if ab_active:
                import random

                from pipeline.image_ab_tester import ImageABTester

                tester = ImageABTester(config)
                title = post_data.get("title", "")
                variants = tester.generate_variants(topic_cluster, emotion_axis, title=title, max_variants=3)
                if variants:
                    chosen_variant = random.choice(variants)
                    post_data["image_variant_id"] = chosen_variant.variant_id
                    post_data["image_variant_type"] = chosen_variant.variant_type
                    logger.info(
                        "A/B Testing active: Selected variant %s (%s), keeping anime prompt style.",
                        chosen_variant.variant_id,
                        chosen_variant.variant_type,
                    )
        except Exception as exc:
            logger.warning("Failed to inject A/B variants: %s", exc)

        ai_image_task = asyncio.ensure_future(
            image_generator.generate_image(
                image_prompt,
                topic_cluster=topic_cluster,
                emotion_axis=emotion_axis,
            )
        )
    elif image_urls and isinstance(image_urls, list):
        original_image_url = image_urls[0]
        logger.info("Found original image URL: %s", original_image_url)
    elif image_prompt and image_generator:
        topic_cluster = profile.get("topic_cluster", "")
        emotion_axis = profile.get("emotion_axis", "")
        ai_image_task = asyncio.ensure_future(
            image_generator.generate_image(
                image_prompt,
                topic_cluster=topic_cluster,
                emotion_axis=emotion_axis,
            )
        )

    screenshot_url = None
    errors: list[str] = []
    if ctx.screenshot_task:
        try:
            screenshot_url = await ctx.screenshot_task
            if not screenshot_url:
                errors.append("Screenshot upload failed")
        except Exception as exc:
            errors.append(f"Screenshot upload error: {exc}")
            logger.exception("Screenshot upload failed for %s: %s", ctx.url, exc)

    ai_image_url = None
    ai_temp_url = None
    if ai_image_task:
        try:
            ai_temp_url = await ai_image_task
            if ai_temp_url:
                if os.path.exists(ai_temp_url):
                    ai_image_url = await image_uploader.upload(ai_temp_url)
                elif hasattr(image_uploader, "upload_from_url"):
                    ai_image_url = await image_uploader.upload_from_url(ai_temp_url)
                if not ai_image_url:
                    errors.append("AI image CDN upload failed")
                    logger.warning("Failed to upload AI image to CDN. %s", ctx.url)
            else:
                errors.append("AI image generation failed")
                logger.warning("Failed to generate AI image. %s", ctx.url)
        except Exception as exc:
            errors.append(f"AI image error: {exc}")
            logger.exception("AI image generation/upload failed for %s: %s", ctx.url, exc)

    image_url = original_image_url or ai_image_url

    if nlm_task:
        try:
            nlm_assets = await nlm_task
            if nlm_assets.infographic_url:
                post_data["nlm_infographic_url"] = nlm_assets.infographic_url
                logger.info("[NLM] 인포그래픽 CDN URL: %s", nlm_assets.infographic_url)
            if nlm_assets.slides_local:
                post_data["nlm_slides_path"] = nlm_assets.slides_local
            if nlm_assets.infographic_local and not image_url:
                image_url = nlm_assets.infographic_url or image_url
        except Exception as exc:
            logger.warning("[NLM] 자산 수집 실패 (파이프라인 계속): %s", exc)

    notion_result = await notion_uploader.upload(
        post_data,
        image_url,
        drafts,
        analysis=profile,
        screenshot_url=screenshot_url,
    )
    if notion_result:
        ctx.notion_url, ctx.notion_page_id = notion_result
        ctx.result["success"] = True
        logger.info("[%s] Uploaded to Notion: %s", ctx.trace_id, ctx.notion_url)
        if errors:
            ctx.result["error"] = "Partial Success: " + "; ".join(errors)
    else:
        ctx.result["error"] = "Notion upload failed"
        ctx.result["error_code"] = notion_uploader.last_error_code or ERROR_NOTION_UPLOAD_FAILED
        ctx.result["failure_stage"] = "upload"
        ctx.result["failure_reason"] = "notion_upload_failed"
        logger.error("[%s] Notion upload failed for %s", ctx.trace_id, ctx.url)
        mark_stage(ctx, "persist", "failed", "notion_upload_failed")
        return False

    require_human_approval = True if config is None else config.get("content_strategy.require_human_approval", True)
    should_publish = not review_only and not require_human_approval

    chosen_draft_type = profile.get("recommended_draft_type")
    if should_publish:
        tweet_text = extract_preferred_tweet_text(drafts, preferred_style=chosen_draft_type)
        ctx.twitter_url = await post_to_twitter(
            twitter_poster,
            tweet_text=tweet_text,
            ai_temp_url=ai_temp_url,
            screenshot_path=post_data.get("screenshot_path"),
        )
        if ctx.twitter_url:
            ctx.result["twitter_url"] = ctx.twitter_url
            if ctx.notion_page_id:
                await notion_uploader.update_page_properties(
                    ctx.notion_page_id,
                    {
                        "status": "발행완료",
                    },
                )
        elif twitter_poster and twitter_poster.enabled:
            errors.append("Twitter post failed")
    elif ctx.notion_page_id:
        await notion_uploader.update_page_properties(
            ctx.notion_page_id,
            {
                "status": ctx.decision.get("status", "검토필요"),
            },
        )

    if ctx.notion_page_id:
        provider_used = drafts.get("_provider_used", "") if isinstance(drafts, dict) else ""
        record_draft_event(
            source=post_data.get("source", ""),
            topic_cluster=profile.get("topic_cluster", ""),
            hook_type=profile.get("hook_type", ""),
            emotion_axis=profile.get("emotion_axis", ""),
            draft_style=chosen_draft_type or "",
            provider_used=provider_used,
            final_rank_score=float(profile.get("final_rank_score", 0.0) or 0.0),
            published=bool(ctx.twitter_url),
            content_url=ctx.url,
            notion_page_id=ctx.notion_page_id,
            hook_score=float(drafts.get("_hook_score", 0.0) if isinstance(drafts, dict) else 0.0),
            virality_score=float(drafts.get("_virality_score", 0.0) if isinstance(drafts, dict) else 0.0),
            fit_score=float(drafts.get("_fit_score", 0.0) if isinstance(drafts, dict) else 0.0),
        )
        refresh_ml_scorer_if_needed()

    ctx.result["notion_url"] = ctx.notion_url
    ctx.result["title"] = post_data.get("title", "")
    ctx.result["drafts"] = drafts
    ctx.result["content_profile"] = profile
    if errors:
        ctx.errors.extend(errors)
        ctx.result["error"] = "; ".join(ctx.errors)

    mark_stage(ctx, "persist", "completed")
    return True
