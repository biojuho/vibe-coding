"""Output validation and response parsing for draft generation."""

from __future__ import annotations

import json
import re


class DraftValidationMixin:
    """Mixin providing validation and parsing helpers for TweetDraftGenerator.

    Pure logic -- no ``self`` attributes are required for the static methods.
    ``_validate_provider_output`` calls the static helpers on ``self`` so that
    subclass overrides are respected.
    """

    # ------------------------------------------------------------------
    # Tag / format checks
    # ------------------------------------------------------------------

    @staticmethod
    def _required_tags(output_formats: list[str]) -> list[str]:
        required: list[str] = []
        if "twitter" in output_formats:
            required.extend(["twitter", "reply"])
        if "threads" in output_formats:
            required.append("threads")
        if "newsletter" in output_formats:
            required.append("newsletter")
        if "naver_blog" in output_formats:
            required.append("naver_blog")
        return required

    @staticmethod
    def _looks_like_error_response(text: str) -> bool:
        lowered = (text or "").lower()
        error_signals = (
            "error generating drafts",
            "rate limit",
            "too many requests",
            "429",
            "asyncopenai",
            "attributeerror",
            "traceback",
            "exception:",
            "sdk error",
            "invalid api key",
            "insufficient_quota",
            "service unavailable",
        )
        return any(signal in lowered for signal in error_signals)

    @staticmethod
    def _korean_ratio(text: str) -> float:
        if not text:
            return 0.0
        korean_chars = sum(1 for c in text if "\uac00" <= c <= "\ud7a3")
        visible_chars = sum(1 for c in text if not c.isspace())
        return korean_chars / visible_chars if visible_chars else 0.0

    @staticmethod
    def _normalize_response_key(key: str) -> str | None:
        normalized = str(key or "").strip().lower().replace("-", "_").replace(" ", "_")
        mapping = {
            "x": "twitter",
            "tweet": "twitter",
            "tweet_body": "twitter",
            "twitter": "twitter",
            "reply": "reply_text",
            "reply_text": "reply_text",
            "threads": "threads",
            "thread": "threads",
            "newsletter": "newsletter",
            "naver_blog": "naver_blog",
            "blog": "naver_blog",
            "blog_body": "naver_blog",
            "creator_take": "creator_take",
            "operator_take": "creator_take",
            "image_prompt": "image_prompt",
        }
        return mapping.get(normalized)

    @classmethod
    def _extract_json_payload(cls, response_text: str) -> dict[str, str]:
        candidates = []
        fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", response_text, re.DOTALL | re.IGNORECASE)
        if fenced:
            candidates.append(fenced.group(1))
        inline = re.search(r"(\{.*?\})", response_text, re.DOTALL)
        if inline:
            candidates.append(inline.group(1))

        for candidate in candidates:
            try:
                payload = json.loads(candidate)
            except json.JSONDecodeError:
                continue
            if not isinstance(payload, dict):
                continue
            mapped: dict[str, str] = {}
            for raw_key, raw_value in payload.items():
                key = cls._normalize_response_key(raw_key)
                if not key or raw_value is None:
                    continue
                value = str(raw_value).strip()
                if value:
                    mapped[key] = value
            if mapped:
                return mapped
        return {}

    @staticmethod
    def _strip_thinking_tags(response_text: str) -> str:
        return re.sub(r"<thinking>.*?</thinking>", "", response_text, flags=re.DOTALL).strip()

    @staticmethod
    def _tag_match(response_text: str, tag: str) -> re.Match[str] | None:
        return re.search(rf"<{tag}>(.*?)</{tag}>", response_text, re.DOTALL)

    @classmethod
    def _tag_text(cls, response_text: str, tag: str) -> str | None:
        match = cls._tag_match(response_text, tag)
        return match.group(1).strip() if match else None

    @classmethod
    def _apply_json_payload(cls, drafts_dict: dict[str, str], response_text: str) -> str | None:
        json_payload = cls._extract_json_payload(response_text)
        image_prompt = json_payload.pop("image_prompt", None) if json_payload else None
        if json_payload:
            drafts_dict.update(json_payload)
        return image_prompt

    @classmethod
    def _apply_thread_tag(cls, drafts_dict: dict[str, str], response_text: str, output_formats: list[str]) -> None:
        thread_text = cls._tag_text(response_text, "twitter_thread")
        if not thread_text:
            return
        drafts_dict["twitter_thread"] = thread_text
        if "twitter" in output_formats:
            drafts_dict["twitter"] = thread_text

    @classmethod
    def _apply_platform_tags(cls, drafts_dict: dict[str, str], response_text: str, output_formats: list[str]) -> None:
        twitter_text = cls._tag_text(response_text, "twitter")
        if twitter_text is not None and "twitter" not in drafts_dict:
            drafts_dict["twitter"] = twitter_text

        for tag in ("newsletter", "threads", "naver_blog"):
            tag_text = cls._tag_text(response_text, tag)
            if tag_text is not None:
                drafts_dict[tag] = tag_text

    @classmethod
    def _apply_reply_tag(cls, drafts_dict: dict[str, str], response_text: str, output_formats: list[str]) -> None:
        reply_text = cls._tag_text(response_text, "reply")
        if reply_text is not None:
            drafts_dict["reply_text"] = reply_text
        elif "twitter" in output_formats:
            drafts_dict.setdefault("reply_text", "")

    @classmethod
    def _apply_auxiliary_tags(cls, drafts_dict: dict[str, str], response_text: str) -> None:
        regulation_text = cls._tag_text(response_text, "regulation_check")
        if regulation_text is not None:
            drafts_dict["_regulation_check"] = regulation_text

        creator_take = cls._tag_text(response_text, "creator_take")
        if creator_take is not None:
            drafts_dict["creator_take"] = creator_take

    @classmethod
    def _apply_twitter_fallback(
        cls,
        drafts_dict: dict[str, str],
        response_text: str,
        output_formats: list[str],
        prompt_match: re.Match[str] | None,
    ) -> None:
        if "twitter" not in output_formats or "twitter" in drafts_dict:
            return
        if prompt_match:
            drafts_dict["twitter"] = response_text.replace(prompt_match.group(0), "").strip()
        else:
            drafts_dict["twitter"] = response_text.strip()

    @staticmethod
    def _apply_single_format_fallback(
        drafts_dict: dict[str, str], response_text: str, output_formats: list[str]
    ) -> None:
        if len(output_formats) != 1:
            return
        only_platform = output_formats[0]
        if only_platform in drafts_dict:
            return
        cleaned = response_text.strip()
        if cleaned:
            drafts_dict[only_platform] = cleaned

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _validate_provider_output(
        self,
        response_text: str,
        drafts_dict: dict[str, str],
        output_formats: list[str],
        allow_partial: bool = False,
    ) -> str | None:
        if self._looks_like_error_response(response_text):
            return "provider_error_text"

        missing_publishable: list[str] = []
        for platform in output_formats:
            draft_text = str(drafts_dict.get(platform, "") or "").strip()
            if not draft_text:
                missing_publishable.append(platform)
                continue
            if self._looks_like_error_response(draft_text):
                return f"error_like_{platform}"
            if self._korean_ratio(draft_text) < 0.25:
                return f"low_korean_ratio_{platform}"

        if missing_publishable:
            drafts_dict["_missing_requested_formats"] = missing_publishable
            if not allow_partial or len(missing_publishable) == len(output_formats):
                return f"missing_sections:{','.join(missing_publishable)}"

        reply_text = str(drafts_dict.get("reply_text", "") or "").strip()
        if reply_text and self._looks_like_error_response(reply_text):
            return "error_like_reply_text"

        creator_take = str(drafts_dict.get("creator_take", "") or "").strip()
        if creator_take and self._looks_like_error_response(creator_take):
            return "error_like_creator_take"

        return None

    # ------------------------------------------------------------------
    # Response parsing
    # ------------------------------------------------------------------

    def _parse_response(
        self, response_text: str, output_formats: list[str], provider_used: str
    ) -> tuple[dict[str, str], str | None]:
        drafts_dict: dict[str, str] = {"_provider_used": provider_used}

        response_text = self._strip_thinking_tags(response_text)
        image_prompt = self._apply_json_payload(drafts_dict, response_text)
        self._apply_thread_tag(drafts_dict, response_text, output_formats)
        self._apply_platform_tags(drafts_dict, response_text, output_formats)
        self._apply_reply_tag(drafts_dict, response_text, output_formats)

        prompt_match = self._tag_match(response_text, "image_prompt")
        if prompt_match:
            image_prompt = prompt_match.group(1).strip()

        self._apply_auxiliary_tags(drafts_dict, response_text)
        self._apply_twitter_fallback(drafts_dict, response_text, output_formats, prompt_match)
        self._apply_single_format_fallback(drafts_dict, response_text, output_formats)

        return drafts_dict, image_prompt
