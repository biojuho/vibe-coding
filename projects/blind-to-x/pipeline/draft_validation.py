"""Output validation and response parsing for draft generation."""

from __future__ import annotations

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

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _validate_provider_output(
        self,
        response_text: str,
        drafts_dict: dict[str, str],
        output_formats: list[str],
    ) -> str | None:
        if self._looks_like_error_response(response_text):
            return "provider_error_text"

        lowered_response = (response_text or "").lower()
        missing_tags = [tag for tag in self._required_tags(output_formats) if f"<{tag}>" not in lowered_response]
        if missing_tags:
            return f"missing_tags:{','.join(missing_tags)}"

        for platform in output_formats:
            draft_text = str(drafts_dict.get(platform, "") or "").strip()
            if not draft_text:
                return f"empty_{platform}"
            if self._looks_like_error_response(draft_text):
                return f"error_like_{platform}"
            if self._korean_ratio(draft_text) < 0.25:
                return f"low_korean_ratio_{platform}"

        required_auxiliary_keys: list[str] = []
        if "twitter" in output_formats:
            required_auxiliary_keys.append("reply_text")

        for extra_key in required_auxiliary_keys:
            extra_text = str(drafts_dict.get(extra_key, "") or "").strip()
            if not extra_text:
                return f"empty_{extra_key}"
            if self._looks_like_error_response(extra_text):
                return f"error_like_{extra_key}"

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

        # ── P0-2: <thinking> 태그 제거 (사고 과정은 출력에 포함하지 않음) ──
        response_text = re.sub(r"<thinking>.*?</thinking>", "", response_text, flags=re.DOTALL).strip()

        # ── 스레드형 파싱 (P0-A1) ──────────────────────────────────────
        thread_match = re.search(r"<twitter_thread>(.*?)</twitter_thread>", response_text, re.DOTALL)
        if thread_match:
            drafts_dict["twitter_thread"] = thread_match.group(1).strip()
            # 스레드 내용을 twitter 키에도 넣어 호환성 유지
            if "twitter" in output_formats:
                drafts_dict["twitter"] = thread_match.group(1).strip()

        # ── 기존 트위터 파싱 ───────────────────────────────────────────
        twitter_match = re.search(r"<twitter>(.*?)</twitter>", response_text, re.DOTALL)
        if twitter_match and "twitter" not in drafts_dict:
            drafts_dict["twitter"] = twitter_match.group(1).strip()
        elif "twitter" in output_formats and "twitter" not in drafts_dict:
            drafts_dict["twitter"] = response_text.strip()

        newsletter_match = re.search(r"<newsletter>(.*?)</newsletter>", response_text, re.DOTALL)
        if newsletter_match:
            drafts_dict["newsletter"] = newsletter_match.group(1).strip()

        # ── Threads 파싱 ──────────────────────────────────────────────
        threads_match = re.search(r"<threads>(.*?)</threads>", response_text, re.DOTALL)
        if threads_match:
            drafts_dict["threads"] = threads_match.group(1).strip()

        # ── 네이버 블로그 파싱 ────────────────────────────────────────
        naver_blog_match = re.search(r"<naver_blog>(.*?)</naver_blog>", response_text, re.DOTALL)
        if naver_blog_match:
            drafts_dict["naver_blog"] = naver_blog_match.group(1).strip()

        # ── 답글(Reply) 파싱 — 링크-인-리플라이 전략 ─────────────────
        reply_match = re.search(r"<reply>(.*?)</reply>", response_text, re.DOTALL)
        if reply_match:
            drafts_dict["reply_text"] = reply_match.group(1).strip()
        elif "twitter" in output_formats:
            # reply 태그가 없으면 placeholder — process.py에서 원문 URL 주입
            drafts_dict["reply_text"] = ""

        image_prompt = None
        prompt_match = re.search(r"<image_prompt>(.*?)</image_prompt>", response_text, re.DOTALL)
        if prompt_match:
            image_prompt = prompt_match.group(1).strip()

        # ── P7: 규제 검증 리포트 파싱 ─────────────────────────────────
        regulation_match = re.search(r"<regulation_check>(.*?)</regulation_check>", response_text, re.DOTALL)
        if regulation_match:
            drafts_dict["_regulation_check"] = regulation_match.group(1).strip()

        # ── creator_take 파싱 (피벗: 운영자 해석 1문장) ──────────────────
        creator_take_match = re.search(r"<creator_take>(.*?)</creator_take>", response_text, re.DOTALL)
        if creator_take_match:
            drafts_dict["creator_take"] = creator_take_match.group(1).strip()

        if "twitter" in output_formats and "twitter" not in drafts_dict:
            if prompt_match:
                drafts_dict["twitter"] = response_text.replace(prompt_match.group(0), "").strip()
            else:
                drafts_dict["twitter"] = response_text.strip()

        return drafts_dict, image_prompt
