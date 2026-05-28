from __future__ import annotations

import argparse
import asyncio
import logging
from pathlib import Path

from config import ConfigManager, load_env, setup_logging
from pipeline.feedback_loop import FeedbackLoop
from pipeline.notion_upload import NotionUploader

logger = logging.getLogger(__name__)


def _render_best_of_n_section(days: int) -> str:
    """T-1197: tuner 의 dry-run 결과를 weekly report 에 임베드.

    tuner 실패(import 에러 / DB 미존재 / 표본 부족 예외)는 swallow 해서 빈 문자열 반환.
    weekly report 본문이 절대 깨지지 않도록 fail-open.
    """
    try:
        from scripts.tune_best_of_n_weight import build_report, load_recent_rows

        rows = load_recent_rows(days=days)
        text, _summary = build_report(rows, days=days, min_samples=10)
    except Exception as exc:  # pragma: no cover - 환경 의존적
        logger.warning("Best-of-N tuner section skipped: %s", exc)
        return ""

    lines = [
        "",
        "## Best-of-N Comment-Weight Tuning (dry-run)",
        "",
        "```",
        text,
        "```",
        "",
    ]
    return "\n".join(lines)


def _render_report(payload: dict, *, best_of_n_days: int = 30) -> str:
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
    body = "\n".join(lines) + "\n"
    tuner_section = _render_best_of_n_section(best_of_n_days)
    if tuner_section:
        body += tuner_section
    return body


async def run(days: int, config_path: str, output_path: str) -> int:
    config_mgr = ConfigManager(config_path)
    notion_uploader = NotionUploader(config_mgr)
    feedback_loop = FeedbackLoop(notion_uploader, config_mgr)
    payload = await feedback_loop.build_weekly_report_payload(days=days)
    # tuner sweep 은 더 긴 윈도우(30일)로 보는 게 표본 확보에 유리.
    report = _render_report(payload, best_of_n_days=max(days, 30))

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
