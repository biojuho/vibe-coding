from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from config import ConfigManager, load_env, setup_logging
from pipeline.feedback_loop import FeedbackLoop
from pipeline.notion_upload import NotionUploader


def _render_report(payload: dict) -> str:
    totals = payload.get("totals", {})
    lines = [
        "# Blind-to-X Weekly Report",
        "",
        "## Summary",
        f"- Total records: {totals.get('total', 0)}",
        f"- Review queue: {totals.get('review_queue', 0)}",
        f"- Approved: {totals.get('approved', 0)}",
        f"- Published: {totals.get('published', 0)}",
        "",
        "## Top Topics",
    ]
    for label, count in payload.get("top_topics", []):
        lines.append(f"- {label}: {count}")

    lines.extend(["", "## Top Hooks"])
    for label, count in payload.get("top_hooks", []):
        lines.append(f"- {label}: {count}")

    lines.extend(["", "## Top Emotions"])
    for label, count in payload.get("top_emotions", []):
        lines.append(f"- {label}: {count}")

    lines.extend(["", "## Top Performers"])
    for item in payload.get("top_performers", []):
        lines.append(
            f"- {item['title']} | views={item['views']} likes={item['likes']} retweets={item['retweets']} | "
            f"{item['topic_cluster']} / {item['hook_type']} / {item['emotion_axis']}"
        )
    return "\n".join(lines) + "\n"


async def run(days: int, config_path: str, output_path: str) -> int:
    config_mgr = ConfigManager(config_path)
    notion_uploader = NotionUploader(config_mgr)
    feedback_loop = FeedbackLoop(notion_uploader, config_mgr)
    payload = await feedback_loop.build_weekly_report_payload(days=days)
    report = _render_report(payload)

    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report, encoding="utf-8")
    print(report)
    return 0


def main():
    parser = argparse.ArgumentParser(description="Build Blind-to-X weekly report.")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--output", default=".tmp/weekly_report.md")
    args = parser.parse_args()

    load_env()
    setup_logging()
    raise SystemExit(asyncio.run(run(days=args.days, config_path=args.config, output_path=args.output)))


if __name__ == "__main__":
    main()
