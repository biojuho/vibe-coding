"""A/B Testing Feedback Loop for Analytics.

Fetches recent post performance from Notion, evaluates the winning A/B test variants
using ImageABTester, and saves tuned base styles for the Image Generator to use.
"""

from __future__ import annotations

import json
import logging
import math
import os
import sys
from collections import defaultdict

from pipeline.image_ab_tester import ImageABTester
from pipeline.style_bandit import get_style_bandit

logger = logging.getLogger(__name__)

# Reward mapping from Notion performance_grade → bandit reward scalar
# S≠A 구분 (T-AB025): Thompson Sampling이 바이럴(S)과 우수(A)를 다르게 학습하도록
_GRADE_TO_REWARD: dict[str, float] = {
    "S": 1.0,  # 바이럴/역대급
    "A": 0.85,  # 우수 (기존 1.0과 동일하여 신호 없음 → 0.85로 분리)
    "B": 0.7,
    "C": 0.5,
    "D": 0.2,
}

# Cache file in data directory
CACHE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "tuned_image_styles.json")


def _safe_float(value, default: float = 0.0) -> float:
    """Convert a Notion field value to float, returning default on non-numeric or non-finite."""
    try:
        f = float(value or 0)
        return f if math.isfinite(f) else default
    except (ValueError, TypeError, OverflowError):
        return default


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
            topic_prop_name = (
                self.config.get("notion.properties.topic_cluster", "토픽 클러스터") if self.config else "토픽 클러스터"
            )
            topic_prop = props.get(topic_prop_name, {})
            topic = None
            if topic_prop.get("type") == "select" and topic_prop.get("select"):
                topic = topic_prop["select"].get("name")

            if topic and selected:
                manual_winners[topic] = selected
                logger.info(f"Manual A/B winner for '{topic}': {selected}")

        return manual_winners

    def _update_style_bandit(self, records: list[dict]) -> None:
        """Feed per-record engagement rewards back into the Thompson Sampling bandit.

        Called once per feedback loop run. Only records with a known draft style
        and topic cluster contribute to bandit learning. Reward is derived from
        the Notion performance_grade field; missing grade falls back to views-only
        heuristic.
        """
        try:
            bandit = get_style_bandit()
        except Exception as exc:
            logger.warning("StyleBandit unavailable, skipping reward update: %s", exc)
            return
        updated = 0
        for record in records:
            topic = record.get("topic_cluster") or ""
            style = record.get("chosen_draft_type") or record.get("recommended_draft_type") or ""
            if not topic or not style:
                continue

            grade = str(record.get("performance_grade") or "").strip().upper()
            if grade in _GRADE_TO_REWARD:
                reward = _GRADE_TO_REWARD[grade]
            else:
                # Fallback: derive reward from raw views (normalised to [0, 1])
                views = _safe_float(record.get("views"))
                if views <= 0:
                    reward = 0.3  # generated but no observed engagement yet
                elif views >= 1000:
                    reward = 1.0
                else:
                    reward = min(0.9, 0.3 + (views / 1000) * 0.6)

            try:
                bandit.update(topic, style, reward)
                updated += 1
            except Exception as exc:
                logger.debug("StyleBandit.update skipped for %s/%s: %s", topic, style, exc)

        if updated:
            logger.info("StyleBandit: updated %d arms from engagement records.", updated)

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
        valid_records = [r for r in records if _safe_float(r.get("views")) > 0 and r.get("topic_cluster")]

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
            stats["views"] += _safe_float(r.get("views", 0))
            stats["likes"] += _safe_float(r.get("likes", 0))
            stats["retweets"] += _safe_float(r.get("retweets", 0))
            stats["count"] += 1.0

        # ── Style Bandit reward update ────────────────────────────────────────
        # Feed per-record engagement back into Thompson Sampling so select_style()
        # learns which draft style wins per topic cluster from real published data.
        self._update_style_bandit(records)

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
                        "retweets": stats["retweets"] / count,
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
                with open(CACHE_FILE, encoding="utf-8") as f:
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
