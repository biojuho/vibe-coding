"""Daily digest generator -- RSSbrew-style content summary.

Aggregates the day's collected posts, generates an AI-summarized digest,
and sends it via Telegram. Can be run as a standalone script or
triggered from the main pipeline.
"""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

_KST = timezone(timedelta(hours=9))


@dataclass
class DigestEntry:
    """A single entry in the daily digest."""

    title: str
    url: str
    source: str
    topic_cluster: str
    emotion_axis: str
    final_rank_score: float
    likes: int = 0
    comments: int = 0
    tweet_preview: str = ""
    viral_score: float = 0.0


@dataclass
class DailyDigest:
    """Complete daily digest ready for delivery."""

    date: str
    total_collected: int
    total_published: int
    top_posts: list[DigestEntry]
    trending_emotions: list[dict]
    topic_distribution: dict[str, int]
    summary: str = ""
    generated_at: str = ""


class DigestGenerator:
    """Generates daily content digests from Notion DB data."""

    def __init__(self, config: dict, notion_uploader=None):
        self._config = config
        self._notion = notion_uploader
        self._max_entries = int(config.get("digest.max_entries", 10))
        self._gemini_key = os.environ.get("GEMINI_API_KEY") or config.get("gemini.api_key", "")

    async def generate(self, date: str | None = None) -> DailyDigest:
        """Generate a daily digest for the given date (default: today KST).

        Args:
            date: Date string in YYYY-MM-DD format. Defaults to today.

        Returns:
            DailyDigest with top posts, trends, and AI summary.
        """
        if date is None:
            date = datetime.now(_KST).strftime("%Y-%m-%d")

        entries = await self._fetch_posts(date)
        trending = await self._get_trending_emotions()
        topic_dist = self._compute_topic_distribution(entries)

        # Sort by rank score
        entries.sort(key=lambda e: e.final_rank_score, reverse=True)
        top = entries[: self._max_entries]

        digest = DailyDigest(
            date=date,
            total_collected=len(entries),
            total_published=sum(1 for e in entries if e.final_rank_score >= 60),
            top_posts=top,
            trending_emotions=trending,
            topic_distribution=topic_dist,
            generated_at=datetime.now(_KST).strftime("%Y-%m-%d %H:%M KST"),
        )

        # Generate AI summary
        digest.summary = await self._generate_summary(digest)

        return digest

    async def _fetch_posts(self, date: str) -> list[DigestEntry]:
        """Fetch today's posts from Notion DB."""
        if not self._notion:
            logger.warning("No Notion uploader available for digest")
            return []

        try:
            # Query Notion for posts created today
            pages = await self._query_notion_by_date(date)
            entries = []
            for page in pages:
                try:
                    props = page.get("properties", {})
                    entry = DigestEntry(
                        title=self._extract_title(props),
                        url=self._extract_rich_text(props, "Source URL"),
                        source=self._extract_select(props, "원본 소스"),
                        topic_cluster=self._extract_select(props, "토픽 클러스터"),
                        emotion_axis=self._extract_select(props, "감정 축"),
                        final_rank_score=self._extract_number(props, "최종 랭크 점수"),
                        likes=int(self._extract_number(props, "24h 좋아요")),
                        comments=0,
                        tweet_preview=self._extract_rich_text(props, "트윗 본문")[:100],
                        viral_score=self._extract_number(props, "성과 예측 점수"),
                    )
                    entries.append(entry)
                except Exception as _entry_exc:
                    logger.debug("Skipping malformed Notion entry: %s", _entry_exc)
            return entries
        except Exception as exc:
            logger.error("Failed to fetch posts for digest: %s", exc)
            return []

    async def _query_notion_by_date(self, date: str) -> list[dict]:
        """Query Notion database for posts created on a specific date."""
        if not self._notion:
            return []

        try:
            import httpx

            notion_key = os.environ.get("NOTION_API_KEY") or self._config.get("notion.api_key", "")
            db_id = os.environ.get("NOTION_DATABASE_ID") or self._config.get("notion.database_id", "")

            if not notion_key or not db_id:
                return []

            date_prop = self._config.get("notion.properties.date", "생성일")

            headers = {
                "Authorization": f"Bearer {notion_key}",
                "Notion-Version": "2022-06-28",
                "Content-Type": "application/json",
            }

            body = {
                "filter": {
                    "property": date_prop,
                    "date": {
                        "on_or_after": date,
                        "before": (datetime.strptime(date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d"),
                    },
                },
                "sorts": [{"property": date_prop, "direction": "descending"}],
            }

            all_results: list[dict] = []
            async with httpx.AsyncClient(timeout=30) as client:
                while True:
                    resp = await client.post(
                        f"https://api.notion.com/v1/databases/{db_id}/query",
                        headers=headers,
                        json=body,
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    all_results.extend(data.get("results", []))
                    if not data.get("has_more") or not data.get("next_cursor"):
                        break
                    body["start_cursor"] = data["next_cursor"]
            return all_results
        except Exception as exc:
            logger.error("Notion query for digest failed: %s", exc)
            return []

    async def _get_trending_emotions(self) -> list[dict]:
        """Get trending emotions from SentimentTracker."""
        try:
            from pipeline.sentiment_tracker import get_sentiment_tracker

            tracker = get_sentiment_tracker()
            trends = tracker.get_trending_emotions(window_hours=24, top_n=5)
            return [
                {
                    "keyword": t.keyword,
                    "spike_ratio": t.spike_ratio,
                    "direction": t.direction,
                    "count": t.current_count,
                }
                for t in trends
            ]
        except Exception:
            return []

    def _compute_topic_distribution(self, entries: list[DigestEntry]) -> dict[str, int]:
        dist: dict[str, int] = {}
        for e in entries:
            topic = e.topic_cluster or "unknown"
            dist[topic] = dist.get(topic, 0) + 1
        return dict(sorted(dist.items(), key=lambda x: -x[1]))

    async def _generate_summary(self, digest: DailyDigest) -> str:
        """Generate an AI summary of the day's content trends."""
        if not self._gemini_key:
            return self._fallback_summary(digest)

        try:
            from google import genai as genai_client

            client = genai_client.Client(api_key=self._gemini_key)

            top_titles = [f"- {e.title} (score:{e.final_rank_score:.0f}, {e.source})" for e in digest.top_posts[:5]]
            topics = ", ".join(f"{k}({v})" for k, v in list(digest.topic_distribution.items())[:5])
            trending = (
                ", ".join(f"{t['keyword']}(x{t['spike_ratio']})" for t in digest.trending_emotions[:3])
                or "none detected"
            )

            prompt = (
                f"Today's Korean workplace community digest ({digest.date}):\n"
                f"- Total posts collected: {digest.total_collected}\n"
                f"- Posts meeting quality bar: {digest.total_published}\n"
                f"- Topic distribution: {topics}\n"
                f"- Trending emotion keywords: {trending}\n"
                f"- Top posts:\n" + "\n".join(top_titles) + "\n\n"
                "Write a 3-4 sentence Korean summary of today's key themes and mood.\n"
                "Focus on: what topics dominated, what emotions are trending, "
                "and any interesting patterns. Write naturally, like a newsletter intro.\n"
                "Keep it under 200 chars."
            )

            response = await asyncio.to_thread(
                client.models.generate_content,
                model="gemini-2.5-flash",
                contents=prompt,
                config={"temperature": 0.7, "max_output_tokens": 300},
            )
            return response.text.strip()

        except Exception as exc:
            logger.warning("AI summary generation failed: %s", exc)
            return self._fallback_summary(digest)

    def _fallback_summary(self, digest: DailyDigest) -> str:
        if not digest.top_posts:
            return f"{digest.date} - No posts collected today."
        top_topic = next(iter(digest.topic_distribution), "unknown")
        return (
            f"{digest.date} daily digest: {digest.total_collected} posts collected, "
            f"{digest.total_published} published. Top topic: {top_topic}."
        )

    # ── Notion property extractors ─────────────────────────────────────
    @staticmethod
    def _extract_title(props: dict) -> str:
        for key in ["콘텐츠", "Name", "title"]:
            p = props.get(key, {})
            title_arr = p.get("title", [])
            if title_arr:
                return title_arr[0].get("plain_text", "")
        return ""

    @staticmethod
    def _extract_rich_text(props: dict, key: str) -> str:
        p = props.get(key, {})
        texts = p.get("rich_text", [])
        return texts[0].get("plain_text", "") if texts else ""

    @staticmethod
    def _extract_select(props: dict, key: str) -> str:
        p = props.get(key, {})
        sel = p.get("select")
        return sel.get("name", "") if sel else ""

    @staticmethod
    def _extract_number(props: dict, key: str) -> float:
        p = props.get(key, {})
        return float(p.get("number", 0) or 0)


# ── Formatting ─────────────────────────────────────────────────────────


def _escape_telegram_md(text: str) -> str:
    """Escape Telegram Markdown special characters in untrusted text."""
    for ch in ("*", "_", "`", "[", "]"):
        text = text.replace(ch, f"\\{ch}")
    return text


def format_digest_telegram(digest: DailyDigest) -> str:
    """Format digest for Telegram message (Markdown)."""
    lines = [
        f"*Daily Digest - {digest.date}*",
        f"Collected: {digest.total_collected} | Published: {digest.total_published}",
        "",
    ]

    if digest.summary:
        lines.append(_escape_telegram_md(digest.summary))
        lines.append("")

    # Top posts
    if digest.top_posts:
        lines.append("*Top Posts:*")
        for i, entry in enumerate(digest.top_posts[:5], 1):
            score_str = f"[{entry.final_rank_score:.0f}]"
            safe_title = _escape_telegram_md(entry.title[:50])
            src = f"({entry.source})" if entry.source else ""
            lines.append(f"{i}. {score_str} {safe_title} {src}")
        lines.append("")

    # Topic distribution
    if digest.topic_distribution:
        topic_str = " | ".join(f"{k}: {_v}" for k, _v in list(digest.topic_distribution.items())[:5])
        lines.append(f"*Topics:* {topic_str}")

    # Trending emotions
    if digest.trending_emotions:
        emo_str = ", ".join(
            f"{t['keyword']}(x{t['spike_ratio']}{'!' if t['direction'] == 'rising' else ''})"
            for t in digest.trending_emotions[:3]
        )
        lines.append(f"*Trending:* {emo_str}")

    return "\n".join(lines)


def format_digest_newsletter(digest: DailyDigest) -> str:
    """Format digest as a newsletter-style email/HTML body."""
    parts = [
        f"# Daily Content Digest - {digest.date}",
        "",
        f"> {digest.summary}" if digest.summary else "",
        "",
        f"**{digest.total_collected}** posts collected, **{digest.total_published}** met quality threshold.",
        "",
    ]

    if digest.top_posts:
        parts.append("## Top Stories")
        for i, entry in enumerate(digest.top_posts[:7], 1):
            parts.append(
                f"{i}. **{entry.title}** (score: {entry.final_rank_score:.0f})\n"
                f"   Source: {entry.source} | Topic: {entry.topic_cluster} | "
                f"Emotion: {entry.emotion_axis}\n"
                f"   {entry.url}\n"
            )

    if digest.topic_distribution:
        parts.append("## Topic Breakdown")
        for topic, count in list(digest.topic_distribution.items())[:8]:
            bar = "+" * min(count, 20)
            parts.append(f"- {topic}: {count} {bar}")

    if digest.trending_emotions:
        parts.append("\n## Trending Emotions")
        for t in digest.trending_emotions:
            arrow = "^" if t["direction"] == "rising" else ("v" if t["direction"] == "falling" else "=")
            parts.append(f"- {t['keyword']} {arrow} (x{t['spike_ratio']})")

    return "\n".join(parts)


# ── Delivery ───────────────────────────────────────────────────────────


async def send_digest_telegram(digest: DailyDigest, config: dict) -> bool:
    """Send digest via Telegram."""
    try:
        from pipeline.notification import NotificationManager

        notifier = NotificationManager(config)
        message = format_digest_telegram(digest)
        await notifier.send_message(message, level="INFO")
        logger.info("Daily digest sent via Telegram for %s", digest.date)
        return True
    except Exception as exc:
        logger.error("Failed to send digest via Telegram: %s", exc)
        return False


async def generate_and_send(config: dict, notion_uploader=None, date: str | None = None) -> DailyDigest:
    """One-shot: generate digest and send via Telegram.

    Can be called from main.py or as a standalone cron job.
    """
    generator = DigestGenerator(config, notion_uploader=notion_uploader)
    digest = await generator.generate(date=date)

    if digest.total_collected > 0:
        await send_digest_telegram(digest, config)
    else:
        logger.info("No posts collected for %s; skipping digest delivery.", digest.date)

    return digest
