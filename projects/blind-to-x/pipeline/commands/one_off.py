"""One-off report commands: digest and sentiment report."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


async def run_digest(config_mgr, notion_uploader, date=None):
    """Generate and send daily digest.

    Args:
        config_mgr: ConfigManager instance.
        notion_uploader: NotionUploader instance.
        date: Optional date string (YYYY-MM-DD). Defaults to today.

    Returns:
        DigestResult with total_collected and total_published counts.
    """
    from pipeline.daily_digest import generate_and_send

    digest = await generate_and_send(
        config_mgr,
        notion_uploader=notion_uploader,
        date=date,
    )
    logger.info("Daily digest generated: %d posts, %d published", digest.total_collected, digest.total_published)
    return digest


def run_sentiment_report(config_mgr=None):
    """Print current emotion trend snapshot to stdout.

    Args:
        config_mgr: ConfigManager instance (currently unused, reserved).
    """
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
