"""Main entry point for the Blind-to-X pipeline."""

from __future__ import annotations

import argparse
import asyncio
from contextlib import AsyncExitStack
from datetime import datetime
import logging
import os
from pathlib import Path
import sys
import time

if hasattr(sys.stdout, "reconfigure") and sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

from config import ConfigManager, load_env, setup_logging
from pipeline import (
    FeedbackLoop,
    ImageGenerator,
    ImageUploader,
    NotionUploader,
    NotificationManager,
    TweetDraftGenerator,
    TwitterPoster,
    calculate_run_metrics,
    process_single_post,
)
from pipeline.analytics_tracker import AnalyticsTracker
from pipeline.content_intelligence import build_content_profile
from pipeline.dedup import check_cross_source_duplicates
from pipeline.draft_analytics import record_draft_event, refresh_ml_scorer_if_needed
from pipeline.process import SPAM_KEYWORDS, extract_preferred_tweet_text
from pipeline.review_queue import build_review_decision
from pipeline.cost_tracker import CostTracker
from scrapers import get_scraper

logger = logging.getLogger(__name__)


def _build_parser():
    parser = argparse.ArgumentParser(description="Blind to X Automation Pipeline")
    parser.add_argument("--config", default="config.yaml", help="Path to config file")
    parser.add_argument("--urls", nargs="+", help="Specific URLs to process")
    parser.add_argument("--trending", action="store_true", help="Fetch trending posts automatically")
    parser.add_argument("--popular", action="store_true", help="Fetch popular posts automatically")
    parser.add_argument("--limit", type=int, help="Limit number of posts (default from config)")
    parser.add_argument("--dry-run", action="store_true", help="Scrape and generate drafts without uploading")
    parser.add_argument("--parallel", type=int, default=3, metavar="N", help="Process up to N posts concurrently (default: 3)")
    parser.add_argument("--source", default="blind", help="Source scraper to use")
    parser.add_argument("--review-only", action="store_true", help="Queue items for review without publishing")
    parser.add_argument("--reprocess-approved", action="store_true", help="Publish approved Notion items only")
    parser.add_argument("--newsletter-build", action="store_true", help="Build newsletter edition from approved Notion items")
    parser.add_argument("--newsletter-preview", action="store_true", help="Preview newsletter edition without publishing")
    parser.add_argument("--digest", action="store_true", help="Generate and send daily digest")
    parser.add_argument("--digest-date", type=str, default=None, help="Digest date (YYYY-MM-DD, default: today)")
    parser.add_argument("--sentiment-report", action="store_true", help="Show current emotion trends")
    return parser


def _resolve_input_sources(config_mgr, args):
    configured_sources = config_mgr.get("input_sources", ["blind"])
    primary_source = config_mgr.get("content_strategy.primary_source", "blind")

    if args.source != "blind":
        return [args.source]

    if primary_source in configured_sources and primary_source != "multi":
        return [primary_source]

    return configured_sources or ["blind"]


async def _load_feedback_examples(config_mgr, notion_uploader):
    feedback_loop = FeedbackLoop(notion_uploader, config_mgr)
    try:
        return await feedback_loop.get_few_shot_examples()
    except Exception as exc:  # pragma: no cover - defensive fallback
        logger.warning("Failed to load feedback examples: %s", exc)
        return []


async def _dry_run_single(item, config_mgr, draft_generator, notion_uploader, top_examples):
    scraper = item["scraper"]
    url = item["url"]
    source_name = item["source"]
    post_data = await scraper.scrape_post(url)
    if not post_data or post_data.get("_scrape_error"):
        return {
            "url": url,
            "success": False,
            "error": (post_data or {}).get("error_message", "Scraping failed"),
            "error_code": (post_data or {}).get("error_code", "SCRAPE_FAILED"),
            "quality_score": None,
            "failure_stage": (post_data or {}).get("failure_stage", "post_fetch"),
            "failure_reason": (post_data or {}).get("failure_reason", "dry_run_scrape_failed"),
        }

    duplicate = await notion_uploader.is_duplicate(url)
    if duplicate:
        return {
            "url": url,
            "success": True,
            "title": post_data.get("title", ""),
            "notion_url": "(skipped-duplicate)",
            "error_code": "DUPLICATE_URL",
        }

    post_data["source"] = source_name
    post_data["feed_mode"] = item.get("feed_mode", "trending")
    quality = scraper.assess_quality(post_data)
    content_text = post_data.get("content", "")
    if len(content_text) < scraper.min_content_length:
        return {
            "url": url,
            "success": True,
            "title": post_data.get("title", ""),
            "notion_url": "(skipped-filtered)",
            "error_code": "FILTERED_SHORT",
            "quality_score": quality["score"],
            "failure_stage": "filter",
            "failure_reason": "content_too_short",
        }
    if any(keyword in content_text for keyword in SPAM_KEYWORDS):
        return {
            "url": url,
            "success": True,
            "title": post_data.get("title", ""),
            "notion_url": "(skipped-filtered)",
            "error_code": "FILTERED_SPAM",
            "quality_score": quality["score"],
            "failure_stage": "filter",
            "failure_reason": "spam_keywords_detected",
        }

    profile = build_content_profile(
        post_data,
        scrape_quality_score=quality["score"],
        historical_examples=top_examples,
        ranking_weights=config_mgr.get("ranking.weights", {}),
    ).to_dict()
    decision = build_review_decision(config_mgr, post_data, profile)
    if not decision["should_queue"]:
        return {
            "url": url,
            "success": True,
            "title": post_data.get("title", ""),
            "notion_url": "(skipped-filtered)",
            "error_code": "FILTERED_LOW_QUALITY",
            "quality_score": profile["scrape_quality_score"],
            "failure_stage": "filter",
            "failure_reason": decision["review_reason"],
        }

    post_data["content_profile"] = profile
    drafts, _image_prompt = await draft_generator.generate_drafts(
        post_data,
        top_tweets=top_examples,
        output_formats=config_mgr.get("output_formats", ["twitter"]),
    )
    return {
        "url": url,
        "success": True,
        "title": post_data.get("title", ""),
        "notion_url": "(dry-run)",
        "drafts_preview": str(drafts)[:160],
        "quality_score": profile["scrape_quality_score"],
        "publishability_score": profile["publishability_score"],
        "performance_score": profile["performance_score"],
        "final_rank_score": profile["final_rank_score"],
        "review_status": decision["review_status"],
    }


async def _reprocess_approved_posts(config_mgr, notion_uploader, twitter_poster, limit):
    if not twitter_poster.enabled:
        logger.warning("Twitter posting is disabled. Skipping approved reprocess flow.")
        return []

    pages = await notion_uploader.get_pages_by_review_status("승인됨", limit=limit)
    results = []
    for page in pages:
        record = notion_uploader.extract_page_record(page)
        tweet_text = extract_preferred_tweet_text(
            {"twitter": record.get("tweet_body", "")},
            preferred_style=record.get("chosen_draft_type"),
        )
        if not tweet_text:
            results.append(
                {
                    "page_id": record["page_id"],
                    "success": False,
                    "error": "Missing tweet draft text",
                }
            )
            continue

        twitter_url = await twitter_poster.post_tweet(text=tweet_text, image_path=None)
        if twitter_url:
            await notion_uploader.update_page_properties(
                record["page_id"],
                {
                    "tweet_url": twitter_url,
                    "publish_channel": "twitter",
                    "published_at": "now",
                    "status": "발행완료",
                    "review_status": "발행완료",
                },
            )
            record_draft_event(
                source=record.get("source", ""),
                topic_cluster=record.get("topic_cluster", ""),
                hook_type=record.get("hook_type", ""),
                emotion_axis=record.get("emotion_axis", ""),
                draft_style=record.get("chosen_draft_type") or record.get("draft_style") or "",
                provider_used="",
                final_rank_score=float(record.get("final_rank_score", 0.0) or 0.0),
                published=True,
                content_url=record.get("url", ""),
                notion_page_id=record["page_id"],
            )
            refresh_ml_scorer_if_needed()
            results.append({"page_id": record["page_id"], "success": True, "twitter_url": twitter_url})
        else:
            results.append({"page_id": record["page_id"], "success": False, "error": "Twitter post failed"})
    return results


_LOCK_FILE = Path(".tmp/.running.lock")
_LOCK_MAX_AGE_SECONDS = 3600  # 1시간 초과 lock은 stale로 간주


def _is_process_alive(pid: int) -> bool:
    """Windows/Unix 호환 프로세스 생존 확인."""
    try:
        os.kill(pid, 0)
        return True
    except PermissionError:
        # Windows: 프로세스 존재하지만 권한 없음 → 살아있다고 판단
        return True
    except (OSError, ValueError):
        return False


async def main():
    parser = _build_parser()
    args = parser.parse_args()

    # ── 중복 실행 가드 ──────────────────────────────────────────────
    _LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    if _LOCK_FILE.exists():
        try:
            lock_content = _LOCK_FILE.read_text().strip()
            parts = lock_content.split(":", 1)
            pid = int(parts[0])
            lock_ts = float(parts[1]) if len(parts) > 1 else 0.0

            lock_age = time.time() - lock_ts if lock_ts else float("inf")

            if lock_age > _LOCK_MAX_AGE_SECONDS:
                logger.warning("Stale lock 감지 (%.0f초 경과, PID=%s). 덮어씁니다.", lock_age, pid)
            elif _is_process_alive(pid):
                logger.warning("이미 실행 중인 프로세스가 있습니다 (PID=%s). 종료합니다.", pid)
                return
            else:
                logger.info("프로세스 %s 종료됨. Stale lock 제거.", pid)
        except (ValueError, IndexError):
            pass  # 잘못된 lock 파일 → 덮어쓰기
    _LOCK_FILE.write_text(f"{os.getpid()}:{time.time()}")

    try:
        config_mgr = ConfigManager(args.config)
    except Exception:
        logger.warning("Could not load %s. Using empty config and environment variables.", args.config)
        config_mgr = ConfigManager("nonexistent")
        config_mgr.config = {}

    notifier = NotificationManager(config_mgr)
    notion_uploader = NotionUploader(config_mgr)
    twitter_poster = TwitterPoster(config_mgr)

    if args.reprocess_approved:
        results = await _reprocess_approved_posts(
            config_mgr,
            notion_uploader,
            twitter_poster,
            limit=args.limit or config_mgr.get("review.queue_limit_per_run", 10),
        )
        success_count = len([item for item in results if item.get("success")])
        fail_count = len(results) - success_count
        if results:
            logger.info("Approved reprocess completed. success=%s fail=%s", success_count, fail_count)
        if fail_count:
            await notifier.send_message(
                f"Blind-to-X 승인 재발행 완료\n성공 {success_count}건 / 실패 {fail_count}건"
            )
        return

    # ── 일일 다이제스트 모드 ──────────────────────────────────────
    if getattr(args, "digest", False):
        from pipeline.daily_digest import generate_and_send
        digest = await generate_and_send(
            config_mgr, notion_uploader=notion_uploader, date=args.digest_date,
        )
        logger.info("Daily digest generated: %d posts, %d published", digest.total_collected, digest.total_published)
        return

    # ── 감성 트렌드 리포트 모드 ────────────────────────────────────
    if getattr(args, "sentiment_report", False):
        from pipeline.sentiment_tracker import get_sentiment_tracker
        tracker = get_sentiment_tracker()
        snapshot = tracker.get_snapshot(hours=24)
        print(f"\n=== Sentiment Report ({snapshot.timestamp.strftime('%Y-%m-%d %H:%M KST')}) ===")
        print(f"Posts analyzed: {snapshot.total_posts}")
        print(f"Dominant emotion: {snapshot.dominant_emotion}")
        if snapshot.top_emotions:
            print("\nTop emotions:")
            for emo, cnt in snapshot.top_emotions[:5]:
                print(f"  {emo}: {cnt}")
        if snapshot.trending_keywords:
            print("\nTrending keywords:")
            for t in snapshot.trending_keywords:
                arrow = "^" if t.direction == "rising" else ("v" if t.direction == "falling" else "=")
                print(f"  {t.keyword} {arrow} (x{t.spike_ratio}, count={t.current_count})")
        return

    # ── 뉴스레터 빌드 모드 ───────────────────────────────────────
    if getattr(args, "newsletter_build", False) or getattr(args, "newsletter_preview", False):
        from pipeline.newsletter_scheduler import NewsletterScheduler
        scheduler = NewsletterScheduler(config_mgr, notion_uploader)
        edition = await scheduler.build_newsletter_edition()
        print(edition["preview"])
        if edition["can_publish"] and not getattr(args, "newsletter_preview", False):
            outputs = scheduler.format_for_platforms(edition)
            for platform, text in outputs.items():
                logger.info("뉴스레터 %s 포맷 생성 완료 (%d자)", platform, len(text))
            logger.info("뉴스레터 에디션 빌드 완료. %d건 콘텐츠.", edition["item_count"])
        elif not edition["can_publish"]:
            logger.info("뉴스레터 에디션 불가: 콘텐츠 부족 (%d/%d)", edition["item_count"], scheduler.min_items)
        return

    input_sources = _resolve_input_sources(config_mgr, args)
    scrapers = {}
    for source in input_sources:
        try:
            scrapers[source] = get_scraper(source)(config_mgr)
        except Exception as exc:
            logger.warning("Could not init scraper %s: %s", source, exc)

    if not scrapers:
        logger.error("No valid scrapers found.")
        sys.exit(1)

    cost_tracker = CostTracker(config_mgr)
    if cost_tracker.is_budget_exceeded():
        logger.error(
            "Daily API budget exceeded: $%.3f >= $%.3f",
            cost_tracker.current_cost,
            cost_tracker.daily_budget,
        )
        await notifier.send_message(
            f"Blind-to-X budget exceeded\nCurrent Cost: ${cost_tracker.current_cost:.3f} / Limit: ${cost_tracker.daily_budget:.3f}",
            level="CRITICAL"
        )
        logger.error("Exit 1 due to Budget Exceeded. Current Cost: $%.3f / Limit: $%.3f", cost_tracker.current_cost, cost_tracker.daily_budget)
        sys.exit(1)

    image_uploader = ImageUploader(config_mgr)
    image_generator = None if args.dry_run else ImageGenerator(config_mgr, cost_tracker=cost_tracker)
    draft_generator = TweetDraftGenerator(config_mgr, cost_tracker=cost_tracker)
    analytics_tracker = AnalyticsTracker(config_mgr)

    for scraper in scrapers.values():
        scraper.cleanup_old_screenshots()

    top_examples = []
    if config_mgr.get("twitter.enabled", False):
        try:
            await analytics_tracker.sync_metrics()
        except Exception as exc:
            logger.warning("Analytics sync failed before run: %s", exc)
    top_examples = await _load_feedback_examples(config_mgr, notion_uploader)

    # ── Notion URL 캐시 웜업 (중복 체크 O(1) 확보) ──────────────────
    await notion_uploader.warm_cache()

    # ── 실시간 트렌드 모니터 초기화 (opt-in) ──────────────────────────
    trend_monitor = None
    if config_mgr.get("trends.enabled", False):
        try:
            from pipeline.trend_monitor import TrendMonitor
            trend_monitor = TrendMonitor(config_mgr)
            await trend_monitor.get_trending_keywords()  # 캐시 웜업
            logger.info("TrendMonitor 초기화 완료")
        except Exception as exc:
            logger.warning("TrendMonitor 초기화 실패 (무시): %s", exc)
            trend_monitor = None

    # ── 성과 기반 가중치 자동 조정 ──────────────────────────────────
    feedback_loop = FeedbackLoop(notion_uploader, config_mgr)
    adaptive_weights = await feedback_loop.compute_adaptive_weights()
    if adaptive_weights:
        config_mgr.config.setdefault("ranking", {})["weights"] = adaptive_weights
        logger.info("랭킹 가중치 적응형으로 교체: %s", adaptive_weights)
    else:
        logger.info("기본 랭킹 가중치 유지 (성과 데이터 부족 또는 상관관계 없음)")

    try:
        async with AsyncExitStack() as stack:
            for scraper in scrapers.values():
                await stack.enter_async_context(scraper)

            effective_limit = args.limit or config_mgr.get("scrape_limit", 5)
            fetch_multiplier = int(config_mgr.get("feed_filter.fetch_multiplier", 2))
            min_engagement = float(config_mgr.get("feed_filter.min_engagement_score", 0))
            title_blacklist = [
                kw.lower() for kw in (config_mgr.get("feed_filter.title_blacklist") or [])
            ]
            low_engagement_skips = 0
            blacklist_skips = 0

            urls_to_process = []
            for source_name, scraper in scrapers.items():
                feed_mode = "trending"
                if args.urls and source_name == input_sources[0]:
                    # Manual URLs: wrap in items directly
                    for u in args.urls:
                        urls_to_process.append({
                            "url": u, "source": source_name, "scraper": scraper,
                            "feed_mode": "manual", "feed_title": "", "feed_engagement": 0,
                        })
                    continue

                if args.popular:
                    feed_mode = "popular"
                elif args.trending or config_mgr.get("schedule.enabled", True):
                    feed_mode = "trending"

                candidates = await scraper.get_feed_candidates(
                    mode=feed_mode, limit=effective_limit * fetch_multiplier,
                )
                for candidate in candidates:
                    # 제목 블랙리스트 필터
                    if title_blacklist and candidate.title:
                        _title_lower = candidate.title.lower()
                        if any(kw in _title_lower for kw in title_blacklist):
                            logger.info(
                                "SKIP [blacklist] %s '%s' %s",
                                source_name, candidate.title[:40], candidate.url,
                            )
                            blacklist_skips += 1
                            continue
                    if min_engagement > 0 and candidate.engagement_score < min_engagement:
                        logger.info(
                            "SKIP [low engagement] %s (score=%.1f, likes=%d, comments=%d) %s",
                            source_name, candidate.engagement_score,
                            candidate.likes, candidate.comments, candidate.url,
                        )
                        low_engagement_skips += 1
                        continue
                    urls_to_process.append({
                        "url": candidate.url, "source": source_name, "scraper": scraper,
                        "feed_mode": feed_mode, "feed_title": candidate.title,
                        "feed_engagement": candidate.engagement_score,
                    })

            # Sort all candidates by engagement (cross-source)
            urls_to_process.sort(key=lambda c: c.get("feed_engagement", 0), reverse=True)

            # Cross-source dedup (before individual scraping)
            cross_source_dedup_count = 0
            if config_mgr.get("dedup.cross_source_enabled", True):
                before_count = len(urls_to_process)
                sim_threshold = float(config_mgr.get("dedup.title_similarity_threshold", 0.6))
                urls_to_process = check_cross_source_duplicates(urls_to_process, threshold=sim_threshold)
                cross_source_dedup_count = before_count - len(urls_to_process)

            # Per-source limit (독식 방지: 소스별 최대 선택 수 적용)
            per_source_limits = config_mgr.get("scrape_limits_per_source", {})
            if per_source_limits:
                source_counts: dict[str, int] = {}
                limited_items = []
                for item in urls_to_process:
                    src = item["source"]
                    src_limit = int(per_source_limits.get(src, effective_limit))
                    source_counts[src] = source_counts.get(src, 0) + 1
                    if source_counts[src] <= src_limit:
                        limited_items.append(item)
                    else:
                        logger.debug("Per-source limit reached for %s (%d/%d), skipping: %s",
                                     src, source_counts[src], src_limit, item.get("url", ""))
                per_source_skips = len(urls_to_process) - len(limited_items)
                if per_source_skips:
                    logger.info("Per-source limit applied: %d items skipped", per_source_skips)
                urls_to_process = limited_items

            # Apply limit after sorting + dedup
            urls_to_process = urls_to_process[:effective_limit]

            # URL dedup
            seen = set()
            deduped_items = []
            for item in urls_to_process:
                if item["url"] not in seen and item["url"].startswith(("http://", "https://")):
                    seen.add(item["url"])
                    deduped_items.append(item)
            urls_to_process = deduped_items

            if not urls_to_process:
                logger.info("No valid posts to process.")
                return

            results = []
            start_time = datetime.now()
            output_formats = config_mgr.get("output_formats", ["twitter"])
            effective_review_only = args.review_only or config_mgr.get("content_strategy.require_human_approval", True)

            if args.dry_run or args.parallel <= 1:
                for index, item in enumerate(urls_to_process, start=1):
                    print(f"  [{index}/{len(urls_to_process)}] [{item['source']}] {item['url']}")
                    if args.dry_run:
                        result = await _dry_run_single(item, config_mgr, draft_generator, notion_uploader, top_examples)
                    else:
                        result = await process_single_post(
                            url=item["url"],
                            scraper=item["scraper"],
                            image_uploader=image_uploader,
                            image_generator=image_generator,
                            draft_generator=draft_generator,
                            notion_uploader=notion_uploader,
                            twitter_poster=twitter_poster,
                            top_tweets=top_examples,
                            source_name=item["source"],
                            output_formats=output_formats,
                            config=config_mgr,
                            feed_mode=item["feed_mode"],
                            review_only=effective_review_only,
                            post_data_hint={"feed_title": item.get("feed_title", "")},
                        )
                    results.append(result)
            else:
                semaphore = asyncio.Semaphore(max(1, args.parallel))
                counter = {"done": 0}
                counter_lock = asyncio.Lock()

                async def _bounded(item):
                    async with semaphore:
                        async with counter_lock:
                            counter["done"] += 1
                            index = counter["done"]
                        print(f"  [{index}/{len(urls_to_process)}] [{item['source']}] {item['url']}")
                        return await process_single_post(
                            url=item["url"],
                            scraper=item["scraper"],
                            image_uploader=image_uploader,
                            image_generator=image_generator,
                            draft_generator=draft_generator,
                            notion_uploader=notion_uploader,
                            twitter_poster=twitter_poster,
                            top_tweets=top_examples,
                            source_name=item["source"],
                            output_formats=output_formats,
                            config=config_mgr,
                            feed_mode=item["feed_mode"],
                            review_only=effective_review_only,
                            post_data_hint={"feed_title": item.get("feed_title", "")},
                        )

                results = await asyncio.gather(*[_bounded(item) for item in urls_to_process])

            # ── 크로스소스 인사이트 생성 (다중 소스 교차 분석) ────────────
            if not args.dry_run and config_mgr.get("cross_source_insight.enabled", True):
                try:
                    from pipeline.cross_source_insight import process_cross_source_insights
                    insight_results = await process_cross_source_insights(
                        results=list(results),
                        draft_generator=draft_generator,
                        notion_uploader=notion_uploader,
                        image_uploader=image_uploader,
                        image_generator=image_generator,
                        config=config_mgr,
                        output_formats=output_formats,
                        top_examples=top_examples,
                        trend_monitor=trend_monitor,
                    )
                    if insight_results:
                        results = list(results) + insight_results
                        logger.info("크로스소스 인사이트 %d건 추가", len(insight_results))
                except Exception as exc:
                    logger.warning("크로스소스 인사이트 생성 실패 (무시): %s", exc)

            # ── 트렌드 스파이크 기록 ──────────────────────────────────────
            if trend_monitor and not args.dry_run:
                try:
                    spikes = await trend_monitor.detect_spikes()
                    if spikes:
                        from pipeline.cost_db import get_cost_db
                        db = get_cost_db()
                        for spike in spikes[:10]:  # 최대 10건 기록
                            matched = trend_monitor.match_topic_cluster(spike["keyword"])
                            db.record_trend_spike(
                                keyword=spike["keyword"],
                                source=spike["source"],
                                score=spike["score"],
                                matched_topic=matched or "",
                            )
                except Exception as exc:
                    logger.debug("트렌드 스파이크 기록 실패: %s", exc)

            elapsed = (datetime.now() - start_time).total_seconds()
            metrics = calculate_run_metrics(results, dry_run=args.dry_run)
            successful = metrics["successful"]
            failed = metrics["failed"]

            content_dup_skips = len(metrics.get("content_duplicate_skips", []))

            print(f"\n{'=' * 55}")
            print(f"  EXECUTION SUMMARY  ({elapsed:.1f}s)")
            print(f"  Total: {len(results)}  |  OK {len(successful)}  |  FAIL {len(failed)}")
            print(f"  Duplicate Skips: {len(metrics['duplicate_skips'])}")
            print(f"  Content Similarity Skips: {content_dup_skips}")
            print(f"  Low Engagement Skips: {low_engagement_skips}")
            print(f"  Blacklist Skips: {blacklist_skips}")
            print(f"  Cross-Source Dedup: {cross_source_dedup_count}")
            print(f"  Filtered Skips: {len(metrics['filtered_skips'])}")
            print(f"  Avg Quality Score (success): {metrics['avg_quality_score']:.1f}")
            if not args.dry_run:
                print(
                    f"  Upload Success Rate: {metrics['upload_success_rate']:.1f}% "
                    f"({len(metrics['live_upload_success'])}/{metrics['live_upload_attempts']})"
                )
            print(f"{'=' * 55}")

            if not args.dry_run:
                review_ready = len([item for item in results if item.get("review_status") == "검토필요"])
                level = "INFO"
                if len(failed) > 0:
                    level = "WARNING"
                if failed and not successful:
                    level = "CRITICAL"
                    
                await notifier.send_message(
                    "Blind-to-X 실행 완료\n"
                    f"수집 {len(results)}건 / 성공 {len(successful)}건 / 실패 {len(failed)}건\n"
                    f"검토필요 {review_ready}건 / 평균 품질점수 {metrics['avg_quality_score']:.1f}",
                    level=level
                )

            if failed and not successful:
                error_reasons = "; ".join([str(f.get('error', 'unknown')) for f in failed])
                logger.error(f"Exit 1: All {len(failed)} items failed. Reasons: {error_reasons}")
                sys.exit(1)

            # Auto-send daily digest if configured (end of pipeline run)
            if config_mgr.get("digest.enabled", False) and config_mgr.get("digest.telegram_enabled", False):
                try:
                    from pipeline.daily_digest import generate_and_send
                    await generate_and_send(config_mgr, notion_uploader=notion_uploader)
                except Exception as _dg_exc:
                    logger.debug("Auto digest skipped: %s", _dg_exc)
    except Exception as exc:
        logger.exception("Critical error in main: %s", exc)
        await notifier.send_message(f"Blind-to-X pipeline crash\nError: `{exc}`", level="CRITICAL")
        sys.exit(1)
    finally:
        _LOCK_FILE.unlink(missing_ok=True)


if __name__ == "__main__":
    load_env()
    setup_logging()
    asyncio.run(main())
