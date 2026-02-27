from __future__ import annotations

import logging
import sys
import time
from pathlib import Path

import requests

try:
    import feedparser
except ImportError:
    feedparser = None

try:
    from execution.api_usage_tracker import log_api_call
except Exception:
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
        from execution.api_usage_tracker import log_api_call
    except Exception:  # pragma: no cover - optional integration
        def log_api_call(**_kwargs):
            return None

logger = logging.getLogger(__name__)


def _fetch_feed(url: str, timeout: int = 8, retries: int = 2):
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            resp = requests.get(
                url,
                timeout=timeout,
                headers={"User-Agent": "Joolife-Agent/1.0"},
            )
            log_api_call(
                provider="rss",
                endpoint=f"GET {url}",
                caller_script="projects/personal-agent/briefing/news.py",
            )
            if resp.status_code != 200:
                raise RuntimeError(f"HTTP {resp.status_code}")
            return feedparser.parse(resp.content)
        except Exception as exc:
            last_error = exc
            if attempt >= retries:
                break
            time.sleep(0.8 * (2 ** attempt))
    raise last_error if last_error else RuntimeError("Unknown RSS fetch failure")

def get_top_news(limit=5):
    """
    Fetches top tech/business news from RSS feeds.
    Returns: String summary
    """
    items = get_news_data(limit)
    return "\n".join([f"- [{item['title']}]({item['link']})" for item in items])

def get_news_data(limit=5):
    """
    Fetches top news and returns a list of dictionaries.
    """
    if feedparser is None:
        print("feedparser is not installed. Returning no news items.")
        return []

    rss_urls = [
        "https://feeds.feedburner.com/TechCrunch/", # TechCrunch
        "https://news.google.com/rss/search?q=technology&hl=en-US&gl=US&ceid=US:en" # Google News Tech
    ]
    
    news_items = []
    
    for url in rss_urls:
        try:
            feed = _fetch_feed(url)
            for entry in feed.entries:
                news_items.append({
                    'title': entry.title,
                    'link': entry.link,
                    'published': entry.get('published', 'Unknown')
                })
                if len(news_items) >= limit:
                    break
        except Exception as e:
            logger.warning(f"News fetch failed for url={url}: {e}")
            
        if len(news_items) >= limit:
            break
            
    return news_items

if __name__ == "__main__":
    print(get_top_news())
