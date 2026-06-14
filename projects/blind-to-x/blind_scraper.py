"""Backward-compatible entry point.

This file delegates to the modularized main.py.
All classes and functions are re-exported for any external code that imports them.
"""

from pipeline.stdout_encoding import configure_stdout_encoding

configure_stdout_encoding()

# Initialise environment and logging before any other import
from config import load_env, setup_logging  # noqa: E402

load_env()
setup_logging()

# Re-export all public symbols so `from blind_scraper import X` still works
from config import (  # noqa: E402, F401
    ERROR_BUDGET_EXCEEDED,
    ERROR_DRAFT_GENERATION_FAILED,
    ERROR_DUPLICATE_URL,
    ERROR_FILTERED_EDITORIAL,
    ERROR_FILTERED_LOW_QUALITY,
    ERROR_FILTERED_SHORT,
    ERROR_FILTERED_SPAM,
    ERROR_NOTION_CONFIG_MISSING,
    ERROR_NOTION_DUPLICATE_CHECK_FAILED,
    ERROR_NOTION_SCHEMA_FETCH_FAILED,
    ERROR_NOTION_SCHEMA_MISMATCH,
    ERROR_NOTION_UPLOAD_FAILED,
    ERROR_SCRAPE_FAILED,
    ERROR_SCRAPE_FEED_FAILED,
    ERROR_SCRAPE_PARSE_FAILED,
    QUALITY_SCORE_THRESHOLD,
    ConfigManager,
    ProxyManager,
)

# Delegate to main entry point
from pipeline.cli import run_main as main  # noqa: E402, F401
from pipeline.draft_generator import TweetDraftGenerator  # noqa: E402, F401
from pipeline.image_upload import ImageUploader  # noqa: E402, F401
from pipeline.notification import NotificationManager  # noqa: E402, F401
from pipeline.notion_upload import NotionUploader  # noqa: E402, F401
from pipeline.process import calculate_run_metrics, process_single_post  # noqa: E402, F401
from scrapers.blind import BlindScraper  # noqa: E402, F401

if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
