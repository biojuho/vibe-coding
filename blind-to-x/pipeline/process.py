"""Post processing pipeline and run metrics calculation."""

from __future__ import annotations

import asyncio
import logging
import os
import re
import tempfile

import aiohttp

from config import (
    ERROR_DUPLICATE_CONTENT,
    ERROR_DUPLICATE_URL,
    ERROR_FILTERED_LOW_QUALITY,
    ERROR_FILTERED_SHORT,
    ERROR_FILTERED_SPAM,
    ERROR_NOTION_DUPLICATE_CHECK_FAILED,
    ERROR_NOTION_SCHEMA_MISMATCH,
    ERROR_NOTION_UPLOAD_FAILED,
    ERROR_SCRAPE_FAILED,
    ERROR_SCRAPE_FEED_FAILED,
    ERROR_SCRAPE_PARSE_FAILED,
    QUALITY_SCORE_THRESHOLD,
)
from pipeline.content_intelligence import build_content_profile
from pipeline.dedup import find_similar_in_notion
from pipeline.draft_analytics import record_draft_event, refresh_ml_scorer_if_needed
from pipeline.review_queue import build_review_decision

# P7: 플랫폼 규제 점검 시스템
try:
    from pipeline.regulation_checker import RegulationChecker
    _regulation_checker: RegulationChecker | None = RegulationChecker()
except Exception:
    _regulation_checker = None

# P6: 성과 피드백 루프 (선택적 — 실패 시 무시)
try:
    from pipeline.performance_tracker import PerformanceTracker
    _perf_tracker: PerformanceTracker | None = PerformanceTracker()
except Exception:
    _perf_tracker = None

logger = logging.getLogger(__name__)

# 파이프라인 에러 자동 캡처 + 품질 히스토리 기록 (debug_history_db 연동)
try:
    import importlib.util as _ilu
    import pathlib as _pl
    _spec = _ilu.spec_from_file_location(
        "execution.debug_history_db",
        _pl.Path(__file__).resolve().parent.parent.parent / "execution" / "debug_history_db.py",
    )
    _dbmod = _ilu.module_from_spec(_spec)  # type: ignore[arg-type]
    _spec.loader.exec_module(_dbmod)  # type: ignore[union-attr]
    _auto_log_error = _dbmod.auto_log_error
    _log_scrape_quality = _dbmod.log_scrape_quality  # P2-C: 품질 히스토리
except Exception:
    _auto_log_error = None  # type: ignore[assignment]
    _log_scrape_quality = None  # type: ignore[assignment]

SPAM_KEYWORDS = [
    "추천인",
    "스팸대출",
    "스팸채팅",
    "리퍼럴",
    "수익 보장",
    "부업 문의",
]

# 스팸 키워드가 게시글의 주요 주제인지 확인 (단순 언급 vs 스팸성 주제)
# "광고", "코드" 등은 맥락에 따라 다르므로 제외 — 오탐이 잦음
SPAM_TITLE_KEYWORDS = [
    "추천인",
    "스팸대출",
    "스팸채팅",
    "리퍼럴",
    "수익 보장",
    "부업 문의",
    "카톡상담",
    "텔레그램상담",
]

DRAFT_STYLE_LABELS = {
    "공감형": "공감형 트윗",
    "논쟁형": "논쟁형 트윗",
    "정보전달형": "정보전달형 트윗",
}


def extract_preferred_tweet_text(drafts: dict | str | None, preferred_style: str | None = None) -> str:
    if not drafts:
        return ""

    twitter_drafts = drafts.get("twitter", "") if isinstance(drafts, dict) else str(drafts)
    if not twitter_drafts.strip():
        return ""

    style_candidates: list[str] = []
    if preferred_style:
        style_candidates.append(preferred_style)
    style_candidates.extend(["공감형", "논쟁형", "정보전달형"])

    for style in style_candidates:
        label = DRAFT_STYLE_LABELS.get(style, style)
        pattern = rf"\[{re.escape(label)}\](.*?)(?=\[[^\]]+\]|$)"
        match = re.search(pattern, twitter_drafts, re.DOTALL)
        if match:
            text = re.sub(r"\[.*?\]", "", match.group(1)).strip()
            return re.sub(r"\n{3,}", "\n\n", text)

    return re.sub(r"\n{3,}", "\n\n", twitter_drafts).strip()


async def _upload_images(url, post_data, image_generator, image_uploader):
    """AI 이미지와 스크린샷을 독립적으로 업로드. 둘 다 Notion에 삽입."""
    ai_image_url = None
    screenshot_url = None
    ai_temp_url = None
    errors: list[str] = []

    # 1) AI 이미지 생성 + CDN 업로드
    image_prompt = post_data.get("image_prompt")
    can_generate_ai_image = image_generator is not None
    can_upload_ai_image = hasattr(image_uploader, "upload_from_url")

    if post_data.get("image_urls") and can_upload_ai_image:
        first_img = post_data["image_urls"][0]
        ai_temp_url = first_img
        ai_image_url = await image_uploader.upload_from_url(first_img)
        if not ai_image_url:
            errors.append("Original image CDN upload failed")
            logger.warning("Failed to upload original image to CDN. %s", first_img)
    elif image_prompt and can_generate_ai_image:
        _topic = post_data.get("content_profile", {}).get("topic_cluster", "")
        _emotion = post_data.get("content_profile", {}).get("emotion_axis", "")
        ai_temp_url = await image_generator.generate_image(
            image_prompt, topic_cluster=_topic, emotion_axis=_emotion
        )
        if ai_temp_url:
            # Pollinations returns a local file path; DALL-E returns a URL
            if os.path.exists(ai_temp_url):
                ai_image_url = await image_uploader.upload(ai_temp_url)
            elif can_upload_ai_image:
                ai_image_url = await image_uploader.upload_from_url(ai_temp_url)
            if not ai_image_url:
                errors.append("AI image CDN upload failed")
                logger.warning("Failed to upload AI image to CDN. %s", url)
        else:
            errors.append("AI image generation failed")
            logger.warning("Failed to generate AI image. %s", url)

    # 2) 스크린샷 CDN 업로드 (항상 시도)
    if post_data.get("screenshot_path"):
        screenshot_url = await image_uploader.upload(post_data["screenshot_path"])
        if not screenshot_url:
            errors.append("Screenshot upload failed")

    return ai_image_url, screenshot_url, ai_temp_url, errors


async def _post_to_twitter(twitter_poster, tweet_text: str, ai_temp_url: str | None, screenshot_path: str | None):
    if not twitter_poster or not twitter_poster.enabled or not tweet_text:
        return None

    media_path = None
    temp_file_path = None
    try:
        if ai_temp_url:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(ai_temp_url) as response:
                        if response.status == 200:
                            image_data = await response.read()
                            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as handle:
                                handle.write(image_data)
                                temp_file_path = handle.name
                                media_path = temp_file_path
            except Exception as exc:  # pragma: no cover - defensive network branch
                logger.warning("Failed to download AI image for Twitter: %s", exc)

        if not media_path and screenshot_path:
            media_path = screenshot_path

        return await twitter_poster.post_tweet(text=tweet_text, image_path=media_path)
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except OSError:
                pass


async def process_single_post(
    url,
    scraper,
    image_uploader,
    image_generator=None,
    draft_generator=None,
    notion_uploader=None,
    twitter_poster=None,
    top_tweets=None,
    source_name=None,
    output_formats=None,
    config=None,
    feed_mode=None,
    review_only=False,
    post_data_hint=None,
):
    result = {
        "url": url,
        "success": False,
        "error": None,
        "error_code": None,
        "notion_url": None,
        "quality_score": None,
        "failure_stage": None,
        "failure_reason": None,
    }

    try:
        duplicate = await notion_uploader.is_duplicate(url)
        if duplicate is None:
            result["error"] = notion_uploader.last_error_message or "Notion schema validation failed"
            result["error_code"] = notion_uploader.last_error_code or ERROR_NOTION_SCHEMA_MISMATCH
            result["failure_stage"] = "upload"
            result["failure_reason"] = "duplicate_check_failed_or_schema_invalid"
            return result
        if duplicate:
            result["error"] = "Duplicate (already in Notion)"
            result["error_code"] = ERROR_DUPLICATE_URL
            result["success"] = True
            result["notion_url"] = "(skipped-duplicate)"
            logger.info("Skipping duplicate: %s", url)
            return result

        # Title similarity check against Notion DB (before expensive scraping)
        feed_title = (post_data_hint or {}).get("feed_title", "")
        notion_check_enabled = bool(config.get("dedup.notion_check_enabled", True)) if config else True
        if feed_title and notion_check_enabled and notion_uploader:
            sim_threshold = float(config.get("dedup.title_similarity_threshold", 0.6)) if config else 0.6
            lookback = int(config.get("dedup.lookback_days", 14)) if config else 14
            similar = await find_similar_in_notion(
                notion_uploader, feed_title, threshold=sim_threshold, lookback_days=lookback,
            )
            if similar:
                best = similar[0]
                result["error"] = f"Similar content exists (sim={best['similarity']:.2f}: '{best['title'][:40]}')"
                result["error_code"] = ERROR_DUPLICATE_CONTENT
                result["success"] = True
                result["notion_url"] = "(skipped-similar)"
                logger.info("SKIP [similar content] %s sim=%.2f with '%s'", url, best["similarity"], best["title"][:50])
                return result

        post_data = await scraper.scrape_post(url)
        if not post_data:
            result["error"] = "Scraping failed"
            result["error_code"] = ERROR_SCRAPE_FAILED
            result["failure_stage"] = "post_fetch"
            result["failure_reason"] = "empty_scrape_result"
            return result

        if post_data.get("_scrape_error"):
            result["error"] = post_data.get("error_message", "Scraping failed")
            result["error_code"] = post_data.get("error_code", ERROR_SCRAPE_FAILED)
            result["failure_stage"] = post_data.get("failure_stage", "post_fetch")
            result["failure_reason"] = post_data.get("failure_reason", "scrape_error")
            return result

        post_data["source"] = source_name or post_data.get("source") or "blind"
        post_data["feed_mode"] = feed_mode or post_data.get("feed_mode") or "trending"

        content_text = post_data.get("content", "")
        quality = scraper.assess_quality(post_data)
        result["quality_score"] = quality["score"]

        # P2-C: 스크랩 품질 히스토리 기록 (소스별 추이 분석용)
        if _log_scrape_quality is not None:
            try:
                _log_scrape_quality(
                    source=post_data.get("source", "unknown"),
                    url=url,
                    quality_score=quality["score"],
                    issues=quality.get("reasons", []),
                )
            except Exception:
                pass

        # 이미지/스크린샷이 있는 글은 텍스트가 짧아도 허용 (이미지 중심 커뮤니티 대응)
        has_visual_content = bool(post_data.get("screenshot_path") or post_data.get("images"))
        effective_min_length = 0 if has_visual_content else scraper.min_content_length
        if len(content_text) < effective_min_length:
            result["error"] = "Content too short (potential spam/empty)"
            result["error_code"] = ERROR_FILTERED_SHORT
            result["success"] = True
            result["notion_url"] = "(skipped-filtered)"
            result["failure_stage"] = "filter"
            result["failure_reason"] = "content_too_short"
            return result

        # 제목에서 스팸 키워드 확인 (제목은 더 엄격한 키워드 사용)
        title_text = post_data.get("title", "")
        matched_spam = [k for k in SPAM_TITLE_KEYWORDS if k in title_text]
        # 본문에서 스팸 키워드 확인 (본문은 기본 키워드 사용)
        matched_spam.extend([k for k in SPAM_KEYWORDS if k in content_text])
        if matched_spam:
            result["error"] = "Spam keywords detected"
            result["error_code"] = ERROR_FILTERED_SPAM
            result["success"] = True
            result["notion_url"] = "(skipped-filtered)"
            result["failure_stage"] = "filter"
            result["failure_reason"] = "spam_keywords_detected"
            return result

        # 이미지가 있는 글은 텍스트 품질 점수만으로 판단하면 오탐 → threshold 완화
        effective_quality_threshold = QUALITY_SCORE_THRESHOLD - 20 if has_visual_content else QUALITY_SCORE_THRESHOLD
        if quality["score"] < effective_quality_threshold:
            result["error"] = "Low quality content"
            result["error_code"] = ERROR_FILTERED_LOW_QUALITY
            result["success"] = True
            result["notion_url"] = "(skipped-filtered)"
            result["failure_stage"] = "filter"
            result["failure_reason"] = quality["reasons"][0] if quality["reasons"] else "low_quality_score"
            return result

        ranking_weights = config.get("ranking.weights", {}) if config else {}
        llm_viral_boost = bool(config.get("ranking.llm_viral_boost", False)) if config else False
        profile = build_content_profile(
            post_data,
            scrape_quality_score=quality["score"],
            historical_examples=top_tweets,
            ranking_weights=ranking_weights,
            llm_viral_boost=llm_viral_boost,
        ).to_dict()
        decision = build_review_decision(config, post_data, profile) if config else {
            "should_queue": True,
            "review_status": "검토필요",
            "review_reason": "queued_for_review",
            "review_priority": "normal",
        }

        result["quality_score"] = profile["scrape_quality_score"]
        result["publishability_score"] = profile["publishability_score"]
        result["performance_score"] = profile["performance_score"]
        result["final_rank_score"] = profile["final_rank_score"]
        result["review_status"] = decision["review_status"]

        if not decision["should_queue"]:
            result["error"] = "Below review threshold"
            result["error_code"] = ERROR_FILTERED_LOW_QUALITY
            result["success"] = True
            result["notion_url"] = "(skipped-filtered)"
            result["failure_stage"] = "filter"
            result["failure_reason"] = decision["review_reason"]
            return result

        post_data["content_profile"] = profile
        post_data["review_status"] = decision["review_status"]
        post_data["review_reason"] = decision["review_reason"]
        post_data["review_priority"] = decision["review_priority"]

        # ── 스크린샷 업로드와 draft 생성 병렬 실행 ──────────────────────
        # 스크린샷 업로드는 LLM 호출(~45s)과 독립적이므로 먼저 시작
        screenshot_task = None
        if post_data.get("screenshot_path"):
            screenshot_task = asyncio.ensure_future(
                image_uploader.upload(post_data["screenshot_path"])
            )

        drafts_output = await draft_generator.generate_drafts(
            post_data,
            top_tweets=top_tweets,
            output_formats=output_formats,
        )
        if isinstance(drafts_output, tuple):
            drafts = drafts_output[0]
            image_prompt = drafts_output[1] if len(drafts_output) > 1 else None
        else:
            drafts = drafts_output
            image_prompt = None

        # ── 드래프트 품질 검증 ─────────────────────────────────────────
        twitter_draft = drafts.get("twitter", "") if isinstance(drafts, dict) else ""
        if twitter_draft and len(twitter_draft) > 560:
            logger.warning("Tweet draft too long (%d chars), will be truncated on publish.", len(twitter_draft))
        newsletter_draft = drafts.get("newsletter", "") if isinstance(drafts, dict) else ""
        if newsletter_draft and len(newsletter_draft.split()) < 30:
            logger.warning("Newsletter draft too short (%d words).", len(newsletter_draft.split()))
        # P6: Threads / 네이버 블로그 품질 검증
        threads_draft = drafts.get("threads", "") if isinstance(drafts, dict) else ""
        if threads_draft and len(threads_draft) > 500:
            logger.warning("Threads draft too long (%d chars), consider shortening.", len(threads_draft))
        blog_draft = drafts.get("naver_blog", "") if isinstance(drafts, dict) else ""
        if blog_draft and len(blog_draft) < 1500:
            logger.warning("Blog draft too short (%d chars), may not rank well in search.", len(blog_draft))

        post_data["image_prompt"] = image_prompt

        # ── P7: 드래프트 규제 검증 ────────────────────────────────────────
        regulation_report_text = ""
        if _regulation_checker and isinstance(drafts, dict):
            try:
                validation_reports = _regulation_checker.validate_all_drafts(drafts)
                regulation_report_text = _regulation_checker.format_validation_summary(
                    validation_reports
                )
                post_data["regulation_report"] = regulation_report_text

                # LLM 자체 검증 리포트가 있으면 추가
                llm_check = drafts.get("_regulation_check", "")
                if llm_check:
                    post_data["regulation_report"] += f"\n\n[LLM 자체 검증]\n{llm_check}"

                # 규제 검증 실패 시 경고 로그
                for plat, rpt in validation_reports.items():
                    if not rpt.passed:
                        logger.warning(
                            "Regulation check FAILED for %s: score=%d, %s",
                            plat, rpt.score, url,
                        )
            except Exception as exc:
                logger.debug("Regulation check skipped: %s", exc)

        # ── 소스별 이미지 전략 ──────────────────────────────────────────
        # 뽐뿌/에펨: 원본 이미지(유머 게시판 짤) 또는 스크린샷만 사용, AI 생성 불필요
        # 블라인드:  AI 애니/삽화 이미지 필수 생성 + 스크린샷
        ai_image_task = None
        original_image_url = None
        _source = (post_data.get("source") or "").lower()
        _is_blind = _source in {"blind", "블라인드"}
        _is_community = _source in {"ppomppu", "뽐뿌", "fmkorea", "에펨코리아"}

        image_urls = post_data.get("image_urls")

        if _is_community:
            # ── 뽐뿌/에펨: 원본 이미지만 사용 (AI 생성 스킵) ─────────
            if image_urls and isinstance(image_urls, list) and len(image_urls) > 0:
                original_image_url = image_urls[0]
                logger.info("[%s] Using original image from post: %s", _source, original_image_url)
            else:
                logger.info("[%s] No original image found, will use screenshot only.", _source)

        elif _is_blind and image_generator:
            # ── 블라인드: AI 애니/삽화 이미지 필수 생성 ────────────────
            _topic = profile.get("topic_cluster", "")
            _emotion = profile.get("emotion_axis", "")

            # [QA 수정] 항상 애니 스타일로 빌드 (LLM 프롬프트 유무 무관)
            from pipeline.image_generator import ImageGenerator
            image_prompt = ImageGenerator.build_image_prompt(
                topic_cluster=_topic,
                emotion_axis=_emotion,
                title=post_data.get("title", ""),
                source="blind",
            )
            logger.info("[blind] Anime image prompt: %s", image_prompt[:80])

            post_data["image_prompt"] = image_prompt

            # Image A/B Test Integration (P4-L4)
            try:
                ab_active = config.get("image_ab_testing.enabled", False) if config else False
                if ab_active:
                    from pipeline.image_ab_tester import ImageABTester
                    import random
                    tester = ImageABTester(config)
                    title = post_data.get("title", "")
                    variants = tester.generate_variants(_topic, _emotion, title=title, max_variants=3)
                    if variants:
                        chosen_variant = random.choice(variants)
                        post_data["image_variant_id"] = chosen_variant.variant_id
                        post_data["image_variant_type"] = chosen_variant.variant_type
                        logger.info("A/B Testing active: Selected variant %s (%s), keeping anime prompt style.", chosen_variant.variant_id, chosen_variant.variant_type)
            except Exception as exc:
                logger.warning("Failed to inject A/B variants: %s", exc)

            ai_image_task = asyncio.ensure_future(
                image_generator.generate_image(
                    image_prompt,
                    topic_cluster=_topic,
                    emotion_axis=_emotion,
                )
            )

        else:
            # ── 기타 소스: 기존 로직 (원본 이미지 우선 → AI 이미지) ────
            if image_urls and isinstance(image_urls, list) and len(image_urls) > 0:
                original_image_url = image_urls[0]
                logger.info("Found original image URL: %s", original_image_url)
            elif image_prompt and image_generator:
                _topic = profile.get("topic_cluster", "")
                _emotion = profile.get("emotion_axis", "")
                ai_image_task = asyncio.ensure_future(
                    image_generator.generate_image(
                        image_prompt,
                        topic_cluster=_topic,
                        emotion_axis=_emotion,
                    )
                )

        # 스크린샷 업로드 결과 수집 (대부분 이미 완료)
        screenshot_url = None
        errors: list[str] = []
        if screenshot_task:
            try:
                screenshot_url = await screenshot_task
                if not screenshot_url:
                    errors.append("Screenshot upload failed")
            except Exception as exc:
                errors.append(f"Screenshot upload error: {exc}")
                logger.exception("Screenshot upload failed for %s: %s", url, exc)

        # AI 이미지 CDN 업로드
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
                        logger.warning("Failed to upload AI image to CDN. %s", url)
                else:
                    errors.append("AI image generation failed")
                    logger.warning("Failed to generate AI image. %s", url)
            except Exception as exc:
                errors.append(f"AI image error: {exc}")
                logger.exception("AI image generation/upload failed for %s: %s", url, exc)

        notion_url = None
        notion_page_id = None
        
        # 대표 이미지 우선순위: 1. 원본 이미지(Ppomppu) 2. AI 이미지(Blind).
        # 스크린샷은 별도 필드(Screenshot URL)로 전송됨.
        image_url = original_image_url or ai_image_url
        
        notion_result = await notion_uploader.upload(
            post_data, image_url, drafts,
            analysis=profile, screenshot_url=screenshot_url,
        )
        if notion_result:
            notion_url, notion_page_id = notion_result
            result["success"] = True
            if errors:
                result["error"] = "Partial Success: " + "; ".join(errors)
        else:
            errors.append("Notion upload failed")
            result["error_code"] = notion_uploader.last_error_code or ERROR_NOTION_UPLOAD_FAILED
            result["failure_stage"] = "upload"
            result["failure_reason"] = "notion_upload_failed"

        require_human_approval = True if config is None else config.get("content_strategy.require_human_approval", True)
        should_publish = not review_only and not require_human_approval

        twitter_url = None
        chosen_draft_type = profile.get("recommended_draft_type")
        if should_publish:
            tweet_text = extract_preferred_tweet_text(drafts, preferred_style=chosen_draft_type)
            twitter_url = await _post_to_twitter(
                twitter_poster,
                tweet_text=tweet_text,
                ai_temp_url=ai_temp_url,
                screenshot_path=post_data.get("screenshot_path"),
            )
            if twitter_url:
                result["twitter_url"] = twitter_url
                if notion_page_id:
                    await notion_uploader.update_page_properties(
                        notion_page_id,
                        {
                            "tweet_url": twitter_url,
                            "publish_channel": "twitter",
                            "published_at": "now",
                            "status": "발행완료",
                            "review_status": "발행완료",
                            "chosen_draft_type": chosen_draft_type,
                        },
                    )
            elif twitter_poster and twitter_poster.enabled:
                errors.append("Twitter post failed")
        elif notion_page_id:
            await notion_uploader.update_page_properties(
                notion_page_id,
                {
                    "status": decision["review_status"],
                    "review_status": decision["review_status"],
                    "chosen_draft_type": chosen_draft_type,
                    "review_note": decision["review_reason"],
                },
            )

        if notion_page_id:
            provider_used = drafts.get("_provider_used", "") if isinstance(drafts, dict) else ""
            record_draft_event(
                source=post_data.get("source", ""),
                topic_cluster=profile.get("topic_cluster", ""),
                hook_type=profile.get("hook_type", ""),
                emotion_axis=profile.get("emotion_axis", ""),
                draft_style=chosen_draft_type or "",
                provider_used=provider_used,
                final_rank_score=float(profile.get("final_rank_score", 0.0) or 0.0),
                published=bool(twitter_url),
                content_url=url,
                notion_page_id=notion_page_id,
                hook_score=float(drafts.get("_hook_score", 0.0) if isinstance(drafts, dict) else 0.0),
                virality_score=float(drafts.get("_virality_score", 0.0) if isinstance(drafts, dict) else 0.0),
                fit_score=float(drafts.get("_fit_score", 0.0) if isinstance(drafts, dict) else 0.0),
            )
            refresh_ml_scorer_if_needed()

        result["notion_url"] = notion_url
        result["title"] = post_data.get("title", "")
        result["drafts"] = drafts
        result["content_profile"] = profile
        if errors:
            result["error"] = "; ".join(errors)

    except Exception as exc:  # pragma: no cover - defensive fallback
        logger.error("Error processing %s: %s", url, exc)
        result["error"] = str(exc)
        result["error_code"] = "INTERNAL_EXCEPTION"
        result["failure_stage"] = "upload"
        result["failure_reason"] = "internal_exception"
        if _auto_log_error is not None:
            _auto_log_error(exc, module="blind-to-x/process", context=url[:80])

    return result


def calculate_run_metrics(results, dry_run=False):
    successful = [item for item in results if item.get("success")]
    failed = [item for item in results if not item.get("success")]
    duplicate_skips = [item for item in results if item.get("error_code") == ERROR_DUPLICATE_URL]
    content_duplicate_skips = [item for item in results if item.get("error_code") == ERROR_DUPLICATE_CONTENT]
    filtered_skips = [
        item
        for item in results
        if item.get("error_code") in (ERROR_FILTERED_SHORT, ERROR_FILTERED_SPAM, ERROR_FILTERED_LOW_QUALITY)
    ]
    filtered_low_quality = [item for item in results if item.get("error_code") == ERROR_FILTERED_LOW_QUALITY]
    schema_mismatches = [item for item in results if item.get("error_code") == ERROR_NOTION_SCHEMA_MISMATCH]
    duplicate_check_failures = [
        item for item in results if item.get("error_code") == ERROR_NOTION_DUPLICATE_CHECK_FAILED
    ]
    feed_fetch_failures = [item for item in results if item.get("error_code") == ERROR_SCRAPE_FEED_FAILED]
    parse_failures = [item for item in results if item.get("error_code") == ERROR_SCRAPE_PARSE_FAILED]

    quality_scores = [
        item.get("quality_score") for item in successful if isinstance(item.get("quality_score"), (int, float))
    ]
    avg_quality_score = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0

    live_upload_attempts = max(0, len(results) - len(duplicate_skips) - len(content_duplicate_skips) - len(filtered_skips)) if not dry_run else 0
    live_upload_success = [
        item
        for item in results
        if item.get("success")
        and item.get("notion_url")
        and item.get("notion_url") not in {"(skipped-duplicate)", "(skipped-filtered)", "(skipped-similar)", "(dry-run)"}
    ]
    upload_success_rate = (
        (len(live_upload_success) / live_upload_attempts * 100) if live_upload_attempts > 0 else 0.0
    )

    return {
        "successful": successful,
        "failed": failed,
        "duplicate_skips": duplicate_skips,
        "content_duplicate_skips": content_duplicate_skips,
        "filtered_skips": filtered_skips,
        "filtered_low_quality": filtered_low_quality,
        "schema_mismatches": schema_mismatches,
        "duplicate_check_failures": duplicate_check_failures,
        "feed_fetch_failures": feed_fetch_failures,
        "parse_failures": parse_failures,
        "avg_quality_score": avg_quality_score,
        "live_upload_attempts": live_upload_attempts,
        "live_upload_success": live_upload_success,
        "upload_success_rate": upload_success_rate,
    }
