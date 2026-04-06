"""Pydantic models for data validation across the pipeline."""

from typing import Any

from pydantic import BaseModel, Field, HttpUrl, field_validator


class ScrapedPost(BaseModel):
    """Raw data structure returned by scrapers."""

    url: HttpUrl
    title: str = Field(..., min_length=1)
    content: str = Field(..., min_length=1)
    category: str = "general"
    likes: int = 0
    comments: int = 0
    views: int = 0
    screenshot_path: str | None = None
    image_urls: list[HttpUrl] = Field(default_factory=list)
    source: str = "unknown"
    extraction_method: str = "selector"

    @field_validator("title", "content", mode="before")
    @classmethod
    def clean_strings(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v.strip()
        return v


class ProcessResult(BaseModel):
    """Simplified result structure for stages."""

    success: bool = False
    error: str | None = None
    error_code: str | None = None
    failure_stage: str | None = None
    failure_reason: str | None = None
    quality_score: int | None = None
    notion_page_id: str | None = None
    tweet_id: str | None = None
    trace_id: str


class ContentProfile(BaseModel):
    """Enriched content profile used for AI drafting and persistence."""

    source_url: HttpUrl
    title: str
    body: str
    summary: str | None = None
    keywords: list[str] = Field(default_factory=list)
    sentiment: str = "neutral"
    category: str
    engagement: dict[str, int] = Field(default_factory=dict)
    screenshot_path: str | None = None
    images: list[str] = Field(default_factory=list)
    source_name: str
    trace_id: str
