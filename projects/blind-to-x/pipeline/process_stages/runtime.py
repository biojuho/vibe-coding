"""Shared runtime state for staged post processing."""

from __future__ import annotations

import logging
import os
import re
import tempfile
from pathlib import Path

import aiohttp

logger = logging.getLogger(__name__)
AI_IMAGE_DOWNLOAD_TIMEOUT = aiohttp.ClientTimeout(total=15, connect=5, sock_read=10)

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


# ---------------------------------------------------------------------------
# Debug history DB — optional, workspace-independent integration.
#
# Resolution order:
#   1. BLIND_DEBUG_DB_PATH env-var → load that specific file
#   2. Search the canonical workspace path (parents[4]/workspace/execution/...)
#      as a convenience fallback *without* breaking if it doesn't exist.
#   3. No-op callables if neither is available.
# ---------------------------------------------------------------------------

auto_log_error = None  # type: ignore[assignment]
log_scrape_quality = None  # type: ignore[assignment]


def _try_load_debug_db() -> None:
    """Attempt to load debug_history_db and wire up auto_log_error / log_scrape_quality."""
    global auto_log_error, log_scrape_quality

    import importlib.util as _ilu

    # 1) Explicit env-var path
    env_path = os.environ.get("BLIND_DEBUG_DB_PATH", "")
    candidate: Path | None = Path(env_path) if env_path else None

    # 2) Conventional workspace path (best-effort, no error if missing)
    if candidate is None or not candidate.exists():
        conventional = Path(__file__).resolve().parents[4] / "workspace" / "execution" / "debug_history_db.py"
        if conventional.exists():
            candidate = conventional

    if candidate is None or not candidate.exists():
        logger.debug("debug_history_db not found — auto_log_error / log_scrape_quality disabled.")
        return

    try:
        spec = _ilu.spec_from_file_location("workspace.execution.debug_history_db", candidate)
        if spec is None:  # [QA 수정] spec_from_file_location이 None을 반환할 수 있음
            logger.debug("debug_history_db spec could not be created for %s", candidate)
            return
        mod = _ilu.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
        auto_log_error = mod.auto_log_error
        log_scrape_quality = mod.log_scrape_quality
        logger.debug("debug_history_db loaded from %s", candidate)
    except Exception as exc:
        logger.debug("debug_history_db load failed (non-fatal): %s", exc)


_try_load_debug_db()


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
                async with aiohttp.ClientSession(timeout=AI_IMAGE_DOWNLOAD_TIMEOUT) as session:
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
