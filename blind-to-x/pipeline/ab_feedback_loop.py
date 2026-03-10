"""A/B Testing Feedback Loop for Analytics.

Fetches recent post performance from Notion, evaluates the winning A/B test variants
using ImageABTester, and saves tuned base styles for the Image Generator to use.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from collections import defaultdict
from typing import Any

from pipeline.image_ab_tester import ImageABTester

logger = logging.getLogger(__name__)

# Cache file in data directory
CACHE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "tuned_image_styles.json")


class ABFeedbackLoop:
    """Feedback loop to tune image generation styles based on A/B test results."""

    def __init__(self, notion_uploader, config):
        self.notion_uploader = notion_uploader
        self.config = config
        self.ab_tester = ImageABTester(config_mgr=config)
        
        # Ensure data directory exists
        os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)

    async def fetch_manual_winners(self, pages: list[dict]) -> dict[str, str]:
        """Notion에서 운영자가 수동으로 선택한 A/B 위너를 가져옵니다.

        Args:
            pages: Notion API에서 가져온 페이지 목록.

        Returns:
            {topic_cluster: winner_variant_type} 형태의 딕셔너리.
        """
        manual_winners: dict[str, str] = {}
        ab_winner_prop = self.config.get("notion.properties.ab_winner", "A/B 위너") if self.config else "A/B 위너"

        for page in pages:
            props = page.get("properties", {})
            # A/B 위너 select 속성 읽기
            ab_prop = props.get(ab_winner_prop, {})
            selected = None
            if ab_prop.get("type") == "select" and ab_prop.get("select"):
                selected = ab_prop["select"].get("name")
            elif isinstance(ab_prop, dict) and ab_prop.get("name"):
                selected = ab_prop["name"]

            if not selected:
                continue

            # 토픽 클러스터 읽기
            topic_prop_name = self.config.get("notion.properties.topic_cluster", "토픽 클러스터") if self.config else "토픽 클러스터"
            topic_prop = props.get(topic_prop_name, {})
            topic = None
            if topic_prop.get("type") == "select" and topic_prop.get("select"):
                topic = topic_prop["select"].get("name")

            if topic and selected:
                manual_winners[topic] = selected
                logger.info(f"Manual A/B winner for '{topic}': {selected}")

        return manual_winners

    async def run_feedback_loop(self, days: int = 14) -> dict[str, dict[str, str]]:
        """Fetch recent records, analyze A/B performance, and save tuned styles.

        수동 위너 선택(Notion UI)이 자동 판정보다 우선 적용됩니다.
        """
        logger.info(f"Running A/B Feedback Loop for the last {days} days...")
        try:
            pages = await self.notion_uploader.get_recent_pages(days=days, limit=100)
            records = [self.notion_uploader.extract_page_record(page) for page in pages]
        except Exception as e:
            logger.error(f"Failed to fetch Notion pages: {e}")
            return {}

        # 수동 위너 선택 가져오기
        manual_winners = await self.fetch_manual_winners(pages)

        # Filter valid records that have actual views and a topic cluster
        valid_records = [
            r for r in records
            if r.get("views") and float(r.get("views") or 0) > 0 and r.get("topic_cluster")
        ]
        
        if not valid_records:
            logger.info("No valid records with views found for A/B testing feedback.")
            return self.load_tuned_styles()

        # Aggregate metrics by topic_cluster -> variant (chosen_draft_type)
        # We assume chosen_draft_type acts as the 'variant' in our current pipeline
        # e.g., topic_stats = { "연봉": { "공감형": {"views": ..., "likes": ..., "retweets": ..., "count": ...} } }
        topic_stats: dict[str, dict[str, dict[str, float]]] = defaultdict(
            lambda: defaultdict(lambda: {"views": 0.0, "likes": 0.0, "retweets": 0.0, "count": 0.0})
        )

        for r in valid_records:
            topic = r.get("topic_cluster", "기타")
            variant = r.get("chosen_draft_type") or r.get("recommended_draft_type") or "공감형"
            
            stats = topic_stats[topic][variant]
            stats["views"] += float(r.get("views", 0) or 0)
            stats["likes"] += float(r.get("likes", 0) or 0)
            stats["retweets"] += float(r.get("retweets", 0) or 0)
            stats["count"] += 1.0

        tuned_styles = self.load_tuned_styles()
        updates_made = 0
        
        # draft_type → 이미지 mood 매핑 (한국어 draft_type을 영어 mood 디스크립터로 변환)
        _DRAFT_TYPE_TO_MOOD = {
            "공감형": "warm, empathetic, soft lighting",
            "논쟁형": "bold, dramatic, high contrast",
            "정보전달형": "professional, clean, minimal",
            "유머형": "playful, bright, colorful",
            "스토리형": "cinematic, narrative, atmospheric",
        }

        for topic, variants in topic_stats.items():
            # 수동 위너가 있으면 자동 판정 건너뛰기
            if topic in manual_winners:
                manual_winner = manual_winners[topic]
                logger.info(f"Topic '{topic}' Manual Winner Override: {manual_winner}")
                if topic not in tuned_styles:
                    tuned_styles[topic] = {}
                mood = _DRAFT_TYPE_TO_MOOD.get(manual_winner, "professional, clean, minimal")
                tuned_styles[topic]["mood"] = mood
                tuned_styles[topic]["winning_draft_type"] = manual_winner
                tuned_styles[topic]["source"] = "manual"
                updates_made += 1
                continue

            if len(variants) < 2:
                logger.debug(f"Topic '{topic}': Not enough variants for AB testing.")
                continue

            variant_metrics: dict[str, dict[str, float]] = {}
            for variant, stats in variants.items():
                count = stats["count"]
                if count > 0:
                    variant_metrics[variant] = {
                        "views": stats["views"] / count,
                        "likes": stats["likes"] / count,
                        "retweets": stats["retweets"] / count
                    }

            result = self.ab_tester.compare_results(variant_metrics)
            if result.winner:
                logger.info(f"Topic '{topic}' AB Test Winner: {result.winner} (Reason: {result.winner_reason})")

                if topic not in tuned_styles:
                    tuned_styles[topic] = {}

                # draft_type을 이미지 mood 디스크립터로 변환 (한국어 직접 삽입 방지)
                mood = _DRAFT_TYPE_TO_MOOD.get(result.winner, "professional, clean, minimal")
                tuned_styles[topic]["mood"] = mood
                tuned_styles[topic]["winning_draft_type"] = result.winner
                tuned_styles[topic]["source"] = "auto"
                updates_made += 1
            else:
                logger.debug(f"Topic '{topic}' AB Test No clear winner: {result.winner_reason}")

        if updates_made > 0:
            self.save_tuned_styles(tuned_styles)
            logger.info(f"Successfully tuned {updates_made} topics.")
        else:
            logger.info("No style updates were necessary from A/B feedback.")
            
        return tuned_styles

    @staticmethod
    def load_tuned_styles() -> dict[str, dict[str, str]]:
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Could not load tuned styles: {e}")
        return {}

    @staticmethod
    def save_tuned_styles(styles: dict[str, dict[str, str]]):
        try:
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(styles, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Could not save tuned styles: {e}")


if __name__ == "__main__":
    import asyncio
    
    # Simple dry-run script behavior
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from config import ConfigManager, load_env
    from pipeline.notion_upload import NotionUploader
    
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    
    async def main():
        load_env()
        config_mgr = ConfigManager()
        notion_uploader = NotionUploader(config_mgr)
        loop = ABFeedbackLoop(notion_uploader, config_mgr)
        
        logger.info("Starting dry-run of ABFeedbackLoop...")
        styles = await loop.run_feedback_loop()
        print("\n--- Current Tuned Styles ---")
        print(json.dumps(styles, indent=2, ensure_ascii=False))
            
    asyncio.run(main())
