from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timedelta

from config import ConfigManager, load_env, setup_logging
from pipeline.content_intelligence import build_content_profile
from pipeline.feedback_loop import FeedbackLoop
from pipeline.notion_upload import NotionUploader


async def run(days: int, limit: int, config_path: str) -> int:
    config_mgr = ConfigManager(config_path)
    notion_uploader = NotionUploader(config_mgr)
    feedback_loop = FeedbackLoop(notion_uploader, config_mgr)
    top_examples = await feedback_loop.get_few_shot_examples()
    pages = await notion_uploader.get_recent_pages(days=days, limit=limit)

    updated = 0
    for page in pages:
        record = notion_uploader.extract_page_record(page)
        content = record.get("memo") or record.get("text") or ""
        post_data = {
            "title": record.get("title", ""),
            "content": content,
            "likes": record.get("likes", 0) or 0,
            "comments": 0,
        }
        scrape_quality_score = float(record.get("scrape_quality_score") or 70)
        profile = build_content_profile(
            post_data,
            scrape_quality_score=scrape_quality_score,
            historical_examples=top_examples,
            ranking_weights=config_mgr.get("ranking.weights", {}),
        ).to_dict()
        ok = await notion_uploader.update_page_properties(
            record["page_id"],
            {
                "topic_cluster": profile["topic_cluster"],
                "hook_type": profile["hook_type"],
                "emotion_axis": profile["emotion_axis"],
                "audience_fit": profile["audience_fit"],
                "scrape_quality_score": profile["scrape_quality_score"],
                "publishability_score": profile["publishability_score"],
                "performance_score": profile["performance_score"],
                "final_rank_score": profile["final_rank_score"],
                "chosen_draft_type": profile["recommended_draft_type"],
            },
        )
        if ok:
            updated += 1

    print(f"recompute_scores complete: updated={updated} total={len(pages)} days={days}")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Recompute Blind-to-X Notion scores.")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()

    load_env()
    setup_logging()
    raise SystemExit(asyncio.run(run(days=args.days, limit=args.limit, config_path=args.config)))


if __name__ == "__main__":
    main()
