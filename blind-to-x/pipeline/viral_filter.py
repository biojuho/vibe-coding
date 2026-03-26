"""AI-powered viral potential filter using Gemini Flash.

Scores posts on viral potential and filters out noise before expensive
draft generation. Uses a lightweight LLM call (Gemini Flash, free tier)
to assess whether a post is worth processing further.

Integrates between quality gates (P0-P2) and draft generation (P3).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ViralScore:
    """Result of viral potential assessment."""

    score: float  # 0-100
    hook_strength: float  # 0-10: how attention-grabbing
    relatability: float  # 0-10: how relatable to the audience
    shareability: float  # 0-10: would people share this?
    controversy: float  # 0-10: discussion potential
    timeliness: float  # 0-10: time-sensitive relevance
    reasoning: str  # brief explanation
    pass_filter: bool  # True if post should proceed

    def to_dict(self) -> dict:
        return {
            "viral_score": round(self.score, 1),
            "hook_strength": round(self.hook_strength, 1),
            "relatability": round(self.relatability, 1),
            "shareability": round(self.shareability, 1),
            "controversy": round(self.controversy, 1),
            "timeliness": round(self.timeliness, 1),
            "viral_reasoning": self.reasoning,
            "viral_pass": self.pass_filter,
        }


# Weights for computing final score
_WEIGHTS = {
    "hook_strength": 0.25,
    "relatability": 0.25,
    "shareability": 0.20,
    "controversy": 0.15,
    "timeliness": 0.15,
}


class ViralFilter:
    """Filters posts by viral potential using LLM scoring."""

    def __init__(self, config: dict):
        self._threshold = float(config.get("viral_filter.threshold", 40.0))
        self._enabled = bool(config.get("viral_filter.enabled", True))
        self._timeout = int(config.get("viral_filter.timeout_seconds", 10))
        self._api_key = os.environ.get("GEMINI_API_KEY") or config.get("gemini.api_key", "")

    async def score(self, title: str, content: str, source: str = "", likes: int = 0, comments: int = 0) -> ViralScore:
        """Score a post's viral potential.

        Returns a ViralScore. If scoring fails, returns a permissive default
        so posts aren't incorrectly filtered out.
        """
        if not self._enabled:
            return self._default_pass()

        if not self._api_key:
            logger.debug("No Gemini API key; viral filter returning default pass")
            return self._default_pass()

        try:
            return await asyncio.wait_for(
                self._score_with_llm(title, content, source, likes, comments),
                timeout=self._timeout,
            )
        except asyncio.TimeoutError:
            logger.warning("Viral scoring timed out after %ds", self._timeout)
            return self._default_pass()
        except Exception as exc:
            logger.warning("Viral scoring error: %s", exc)
            return self._default_pass()

    async def _score_with_llm(self, title: str, content: str, source: str, likes: int, comments: int) -> ViralScore:
        """Call Gemini Flash for viral scoring."""
        from google import genai as genai_client

        client = genai_client.Client(api_key=self._api_key)

        # Truncate content to save tokens
        truncated = content[:2000] if len(content) > 2000 else content
        engagement = f"likes={likes}, comments={comments}" if (likes or comments) else "engagement unknown"

        prompt = (
            "You are a Korean social media viral content expert.\n"
            "Score this post's viral potential on Korean Twitter/X.\n\n"
            f"Source: {source}\n"
            f"Title: {title}\n"
            f"Content: {truncated}\n"
            f"Engagement: {engagement}\n\n"
            "Return ONLY valid JSON:\n"
            "{\n"
            '  "hook_strength": 0-10,  // How attention-grabbing is the title/opening?\n'
            '  "relatability": 0-10,   // How relatable to Korean workers?\n'
            '  "shareability": 0-10,   // Would people RT/share this?\n'
            '  "controversy": 0-10,    // Discussion/debate potential?\n'
            '  "timeliness": 0-10,     // Time-sensitive relevance?\n'
            '  "reasoning": "1-2 sentence explanation in Korean"\n'
            "}\n\n"
            "Be strict: most posts should score 4-6. Only truly viral content gets 8+."
        )

        response = await asyncio.to_thread(
            client.models.generate_content,
            model="gemini-2.5-flash",
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "temperature": 0.2,
            },
        )

        data = json.loads(response.text.strip())

        def _clamp(v, lo=0.0, hi=10.0):
            return max(lo, min(hi, float(v)))
        hook = _clamp(data.get("hook_strength", 5))
        relate = _clamp(data.get("relatability", 5))
        share = _clamp(data.get("shareability", 5))
        controversy = _clamp(data.get("controversy", 5))
        timely = _clamp(data.get("timeliness", 5))
        reasoning = str(data.get("reasoning", ""))

        # Weighted score (0-100)
        raw = (
            hook * _WEIGHTS["hook_strength"]
            + relate * _WEIGHTS["relatability"]
            + share * _WEIGHTS["shareability"]
            + controversy * _WEIGHTS["controversy"]
            + timely * _WEIGHTS["timeliness"]
        )
        score = round(raw * 10, 1)  # 0-10 scale -> 0-100

        return ViralScore(
            score=score,
            hook_strength=hook,
            relatability=relate,
            shareability=share,
            controversy=controversy,
            timeliness=timely,
            reasoning=reasoning,
            pass_filter=score >= self._threshold,
        )

    def _default_pass(self) -> ViralScore:
        """Permissive default when scoring fails."""
        return ViralScore(
            score=50.0,
            hook_strength=5.0,
            relatability=5.0,
            shareability=5.0,
            controversy=5.0,
            timeliness=5.0,
            reasoning="scoring unavailable - default pass",
            pass_filter=True,
        )

    def should_process(self, viral_score: ViralScore) -> bool:
        """Check if a post passes the viral filter threshold."""
        return viral_score.pass_filter
