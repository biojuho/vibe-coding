"""Shared runtime state for staged post processing."""

from __future__ import annotations

import importlib.util
import logging
import os
import re
import tempfile
from pathlib import Path

import aiohttp

logger = logging.getLogger(__name__)

try:
    from pipeline.sentiment_tracker import get_sentiment_tracker

    sentiment_tracker = get_sentiment_tracker()
except Exception:
    sentiment_tracker = None

_viral_filter_instance: object | None = None
try:
    from pipeline.viral_filter import ViralFilter as _ViralFilterCls
except Exception:
    _ViralFilterCls = None  # type: ignore[assignment]

try:
    from pipeline.regulation_checker import RegulationChecker

    regulation_checker: RegulationChecker | None = RegulationChecker()
except Exception:
    regulation_checker = None

try:
    from pipeline.notebooklm_enricher import enrich_post_with_assets as notebooklm_enricher
except Exception:
    notebooklm_enricher = None  # type: ignore[assignment]

repo_root = Path(__file__).resolve().parents[4]
debug_history_path = repo_root / "workspace" / "execution" / "debug_history_db.py"
try:
    spec = importlib.util.spec_from_file_location("workspace.execution.debug_history_db", debug_history_path)
    debug_history_module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(debug_history_module)  # type: ignore[union-attr]
    auto_log_error = debug_history_module.auto_log_error
    log_scrape_quality = debug_history_module.log_scrape_quality
except Exception:
    auto_log_error = None  # type: ignore[assignment]
    log_scrape_quality = None  # type: ignore[assignment]

SPAM_KEYWORDS = [
    "추천인",
    "스팸대출",
    "스팸채팅",
    "리퍼럴",
    "수익 보장",
    "부업 문의",
]

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

INAPPROPRIATE_TITLE_KEYWORDS = [
    "골반 구경",
    "몰카",
    "불법촬영",
    "업스커트",
    "노출",
    "야동",
    "훔쳐보",
    "성희롱",
    "성추행",
    "성폭행",
    "아동",
    "미성년",
]

REJECT_EMOTION_AXES = {"혐오"}

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


async def post_to_twitter(twitter_poster, tweet_text: str, ai_temp_url: str | None, screenshot_path: str | None):
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


def get_viral_filter(config):
    global _viral_filter_instance

    if _ViralFilterCls is None or not config:
        return None
    if _viral_filter_instance is None:
        _viral_filter_instance = _ViralFilterCls(config)
    return _viral_filter_instance
