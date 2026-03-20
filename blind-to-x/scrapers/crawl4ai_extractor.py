"""Crawl4AI-based content extraction with LLM structured output.

Provides a fallback extraction layer that uses Crawl4AI's LLM extraction
strategy when CSS selectors fail. This makes the scraper resilient to
site layout changes since the LLM understands page semantics.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

# Lazy import to avoid startup cost when not used
_crawl4ai_available: bool | None = None


def _check_crawl4ai() -> bool:
    global _crawl4ai_available
    if _crawl4ai_available is None:
        try:
            import crawl4ai  # noqa: F401

            _crawl4ai_available = True
        except ImportError:
            _crawl4ai_available = False
            logger.warning("crawl4ai not installed. LLM extraction fallback disabled.")
    return _crawl4ai_available


@dataclass
class ExtractedPost:
    """Structured output from Crawl4AI LLM extraction."""

    title: str = ""
    content: str = ""
    likes: int = 0
    comments: int = 0
    views: int = 0
    category: str = ""
    image_urls: list[str] | None = None
    extraction_method: str = "crawl4ai"

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "content": self.content,
            "likes": self.likes,
            "comments": self.comments,
            "views": self.views,
            "category": self.category,
            "image_urls": self.image_urls or [],
            "extraction_method": self.extraction_method,
        }


# JSON schema for LLM extraction
_POST_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string", "description": "The main title/heading of the post"},
        "content": {"type": "string", "description": "The full body text of the post, preserving paragraph breaks"},
        "likes": {"type": "integer", "description": "Number of likes/upvotes (0 if not found)"},
        "comments": {"type": "integer", "description": "Number of comments/replies (0 if not found)"},
        "views": {"type": "integer", "description": "Number of views (0 if not found)"},
        "category": {"type": "string", "description": "Post category or board name if visible"},
        "image_urls": {
            "type": "array",
            "items": {"type": "string"},
            "description": "URLs of images embedded in the post",
        },
    },
    "required": ["title", "content"],
}

# Schema for feed URL extraction
_FEED_SCHEMA = {
    "type": "object",
    "properties": {
        "posts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Full URL of the post"},
                    "title": {"type": "string", "description": "Post title"},
                    "likes": {"type": "integer", "description": "Like count (0 if unknown)"},
                    "comments": {"type": "integer", "description": "Comment count (0 if unknown)"},
                },
                "required": ["url", "title"],
            },
            "description": "List of post entries found on the page",
        }
    },
    "required": ["posts"],
}


class Crawl4AIExtractor:
    """Wraps Crawl4AI for LLM-powered content extraction.

    Usage:
        extractor = Crawl4AIExtractor(config)
        post = await extractor.extract_post(url)
        feed = await extractor.extract_feed(feed_url, limit=5)
    """

    def __init__(self, config: dict):
        self.config = config
        # LLM provider for extraction (uses Gemini by default - free)
        self._provider = config.get("crawl4ai.provider", "gemini/gemini-2.5-flash")
        self._api_key = (
            config.get("crawl4ai.api_key") or os.environ.get("GEMINI_API_KEY") or config.get("gemini.api_key", "")
        )
        self._timeout = int(config.get("crawl4ai.timeout_seconds", 30))
        self._verbose = bool(config.get("crawl4ai.verbose", False))

    @staticmethod
    def _safe_str(value: Any, default: str = "") -> str:
        """Safely convert LLM output to string."""
        if value is None:
            return default
        return str(value).strip()

    @staticmethod
    def _safe_int(value: Any, default: int = 0) -> int:
        """Safely convert LLM output to int (handles '1,234', 'about 500', etc)."""
        if value is None:
            return default
        if isinstance(value, (int, float)):
            return int(value)
        try:
            import re

            digits = re.sub(r"[^0-9]", "", str(value))
            return int(digits) if digits else default
        except (ValueError, TypeError):
            return default

    @staticmethod
    def _parse_extracted(raw: Any) -> dict:
        """Parse Crawl4AI extracted content into a dict."""
        if isinstance(raw, str):
            data = json.loads(raw)
        else:
            data = raw
        if isinstance(data, list):
            data = data[0] if data else {}
        return data if isinstance(data, dict) else {}

    def _build_post_from_data(self, data: dict, method: str = "crawl4ai") -> ExtractedPost:
        """Build ExtractedPost from parsed LLM output with safe type coercion."""
        return ExtractedPost(
            title=self._safe_str(data.get("title")),
            content=self._safe_str(data.get("content")),
            likes=self._safe_int(data.get("likes")),
            comments=self._safe_int(data.get("comments")),
            views=self._safe_int(data.get("views")),
            category=self._safe_str(data.get("category")),
            image_urls=data.get("image_urls") or [],
            extraction_method=method,
        )

    async def extract_post(self, url: str) -> ExtractedPost | None:
        """Extract structured post data from a URL using Crawl4AI browser.

        Returns:
            ExtractedPost or None on failure.
        """
        if not _check_crawl4ai():
            return None

        try:
            from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
            from crawl4ai.extraction_strategy import LLMExtractionStrategy

            extraction_strategy = LLMExtractionStrategy(
                provider=self._provider,
                api_token=self._api_key,
                schema=_POST_SCHEMA,
                instruction=(
                    "Extract the main post content from this Korean community page. "
                    "The post is typically a user-written article with a title, body text, "
                    "and engagement metrics (likes, comments, views). "
                    "Ignore navigation, ads, sidebars, and comment sections. "
                    "Focus on the primary post content only. "
                    "Preserve the original Korean text without translation."
                ),
            )

            browser_config = BrowserConfig(
                headless=True,
                verbose=self._verbose,
            )

            crawler_config = CrawlerRunConfig(
                extraction_strategy=extraction_strategy,
                bypass_cache=True,
            )

            async with AsyncWebCrawler(config=browser_config) as crawler:
                result = await asyncio.wait_for(
                    crawler.arun(url=url, config=crawler_config),
                    timeout=self._timeout,
                )

                if not result.success:
                    logger.warning("Crawl4AI extraction failed for %s: %s", url, result.error_message)
                    return None

                extracted = result.extracted_content
                if not extracted:
                    logger.warning("Crawl4AI returned empty extraction for %s", url)
                    return None

                data = self._parse_extracted(extracted)
                return self._build_post_from_data(data)

        except asyncio.TimeoutError:
            logger.warning("Crawl4AI extraction timed out after %ds for %s", self._timeout, url)
            return None
        except Exception as exc:
            logger.warning("Crawl4AI extraction error for %s: %s", url, exc)
            return None

    async def extract_post_from_html(self, url: str, html: str) -> ExtractedPost | None:
        """Extract structured post data from pre-fetched HTML using LLM.

        This avoids a second browser launch by sending HTML directly to the LLM.
        Falls back to Gemini API when crawl4ai is not available.
        """
        if not html or not html.strip():
            return None

        # Try direct LLM call (faster, no browser needed)
        return await self._llm_extract_from_html(url, html)

    async def _llm_extract_from_html(self, url: str, html: str) -> ExtractedPost | None:
        """Direct LLM extraction from HTML without Crawl4AI browser."""
        try:
            from google import genai as genai_client

            api_key = self._api_key
            if not api_key:
                logger.debug("No Gemini API key for HTML extraction")
                return None

            # Use client instance instead of global genai.configure() to be thread-safe
            client = genai_client.Client(api_key=api_key)

            # Truncate HTML to avoid token limits (keep first 15k chars)
            truncated = html[:15000] if len(html) > 15000 else html

            prompt = (
                "Extract the main post from this Korean community HTML page.\n"
                "Return ONLY valid JSON with these fields:\n"
                '{"title": "...", "content": "...", "likes": 0, "comments": 0, '
                '"views": 0, "category": "", "image_urls": []}\n\n'
                "Rules:\n"
                "- title: The post's main heading\n"
                "- content: The full body text, preserving paragraphs\n"
                "- likes/comments/views: numeric engagement metrics (0 if not found)\n"
                "- Ignore navigation, ads, comments section, sidebars\n"
                "- Keep original Korean text, do not translate\n\n"
                f"HTML:\n{truncated}"
            )

            response = await asyncio.wait_for(
                asyncio.to_thread(
                    client.models.generate_content,
                    model="gemini-2.5-flash",
                    contents=prompt,
                    config={
                        "response_mime_type": "application/json",
                        "temperature": 0.1,
                    },
                ),
                timeout=self._timeout,
            )

            text = response.text.strip()
            data = self._parse_extracted(text)
            return self._build_post_from_data(data, method="crawl4ai_llm_html")

        except asyncio.TimeoutError:
            logger.warning("LLM HTML extraction timed out after %ds for %s", self._timeout, url)
            return None
        except Exception as exc:
            logger.warning("LLM HTML extraction failed for %s: %s", url, exc)
            return None

    async def extract_feed(self, feed_url: str, limit: int = 10) -> list[dict]:
        """Extract post URLs and metadata from a feed/list page.

        Args:
            feed_url: URL of the feed page.
            limit: Maximum number of posts to extract.

        Returns:
            List of dicts with url, title, likes, comments keys.
        """
        if not _check_crawl4ai():
            return []

        try:
            from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
            from crawl4ai.extraction_strategy import LLMExtractionStrategy

            extraction_strategy = LLMExtractionStrategy(
                provider=self._provider,
                api_token=self._api_key,
                schema=_FEED_SCHEMA,
                instruction=(
                    f"Extract up to {limit} post entries from this Korean community "
                    "feed/list page. Each entry should have a full URL (not relative), "
                    "title, and engagement counts if visible. "
                    "Ignore pinned/promoted posts, ads, and navigation links. "
                    "Only include actual user-posted content."
                ),
            )

            browser_config = BrowserConfig(headless=True, verbose=self._verbose)
            crawler_config = CrawlerRunConfig(
                extraction_strategy=extraction_strategy,
                bypass_cache=True,
            )

            async with AsyncWebCrawler(config=browser_config) as crawler:
                result = await asyncio.wait_for(
                    crawler.arun(url=feed_url, config=crawler_config),
                    timeout=self._timeout,
                )

                if not result.success or not result.extracted_content:
                    logger.warning("Crawl4AI feed extraction failed for %s", feed_url)
                    return []

                data = self._parse_extracted(result.extracted_content)

                posts = data.get("posts", [])
                return [
                    {
                        "url": self._safe_str(p.get("url")),
                        "title": self._safe_str(p.get("title")),
                        "likes": self._safe_int(p.get("likes")),
                        "comments": self._safe_int(p.get("comments")),
                    }
                    for p in posts[:limit]
                    if p.get("url")
                ]

        except asyncio.TimeoutError:
            logger.warning("Crawl4AI feed extraction timed out for %s", feed_url)
            return []
        except Exception as exc:
            logger.warning("Crawl4AI feed extraction error for %s: %s", feed_url, exc)
            return []
