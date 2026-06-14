"""Data source modules for academic search."""

from .arxiv import ArxivSource
from .crossref import CrossRefSource
from .pubmed import PubMedSource

__all__ = ["CrossRefSource", "PubMedSource", "ArxivSource"]
