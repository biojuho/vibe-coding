"""Scraper registry. Import all scrapers here for easy access."""

from scrapers.blind import BlindScraper
from scrapers.fmkorea import FMKoreaScraper
from scrapers.jobplanet import JobplanetScraper
from scrapers.ppomppu import PpomppuScraper

# Registry mapping source name -> scraper class
SCRAPER_REGISTRY = {
    "blind": BlindScraper,
    "fmkorea": FMKoreaScraper,
    "jobplanet": JobplanetScraper,
    "ppomppu": PpomppuScraper,
}


def get_scraper(source_name):
    """Get a scraper class by source name."""
    cls = SCRAPER_REGISTRY.get(source_name)
    if not cls:
        raise ValueError(f"Unknown scraper source: {source_name}. Available: {list(SCRAPER_REGISTRY.keys())}")
    return cls
