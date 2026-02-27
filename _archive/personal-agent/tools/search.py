from __future__ import annotations

import logging
import sys
import time
import warnings
from pathlib import Path

try:
    # New package name.
    from ddgs import DDGS
except ImportError:
    # Backward compatibility.
    from duckduckgo_search import DDGS

try:
    from execution.api_usage_tracker import log_api_call
except Exception:
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
        from execution.api_usage_tracker import log_api_call
    except Exception:  # pragma: no cover - optional integration
        def log_api_call(**_kwargs):
            return None


def search_web(query, max_results=3):
    """
    Perform a web search using DuckDuckGo.
    Returns a string summary of the results.
    """
    last_error = None
    for attempt in range(3):
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)
                results = list(DDGS().text(query, max_results=max_results))
            log_api_call(
                provider="duckduckgo",
                endpoint="search text",
                caller_script="projects/personal-agent/tools/search.py",
            )
            if not results:
                return None

            summary = ""
            for i, r in enumerate(results):
                summary += f"{i+1}. {r.get('title', '')}\n   {r.get('body', '')}\n   Source: {r.get('href', '')}\n\n"
            return summary
        except Exception as e:
            last_error = e
            if attempt < 2:
                time.sleep(0.8 * (2 ** attempt))
                continue
            break
    logging.error(f"Search failed: {last_error}")
    return None

if __name__ == "__main__":
    # Test
    print(search_web("python 3.14 release date"))
