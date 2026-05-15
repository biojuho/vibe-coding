"""Unit tests for multi-platform draft generation (P6: Threads + Naver Blog).

Tests cover:
  1. TweetDraftGenerator: Threads/Blog prompt inclusion & response parsing.
  2. newsletter_formatter: format_for_threads() and format_for_blog().
  3. NotionUploader: new property mappings (threads_body, blog_body, etc.).
  4. config.yaml: output_formats & style configs.
"""

from __future__ import annotations

import textwrap
from unittest.mock import MagicMock

import pytest


# ── 1. draft_generator: Threads + Blog 프롬프트 & 파싱 ──────────────────


class TestDraftGeneratorMultiPlatform:
    """TweetDraftGenerator가 Threads/Blog 프롬프트를 생성하고 응답을 올바르게 파싱하는지 검증."""

    def _make_generator(self, output_formats=None):
        """Mock config로 TweetDraftGenerator 인스턴스 생성."""
        config = MagicMock()
        config.get = MagicMock(
            side_effect=lambda key, default=None: {
                "tweet_style": {"tone": "테스트톤", "max_length": 280},
                "threads_style": {"tone": "캐주얼톤", "max_length": 500, "hashtags_count": 3},
                "naver_blog_style": {"tone": "정보톤", "min_length": 1500, "max_length": 3000, "seo_tags_count": 15},
                "llm.strategy": "fallback",
                "llm.providers": None,
                "llm.max_retries_per_provider": 2,
                "llm.request_timeout_seconds": 45,
                "anthropic.api_key": "",
                "openai.api_key": "",
                "openai.chat_model": "gpt-4.1-mini",
                "openai.enabled": False,
                "openai.chat_enabled": False,
                "gemini.api_key": "",
                "gemini.model": "gemini-2.5-flash",
                "gemini.enabled": False,
                "xai.api_key": "",
                "xai.model": "grok-4-1-fast-reasoning",
                "xai.enabled": False,
                "anthropic.model": "claude-haiku-4-5-20251001",
                "anthropic.enabled": False,
            }.get(key, default)
        )
        from pipeline.draft_generator import TweetDraftGenerator

        return TweetDraftGenerator(config)

    def test_threads_style_init(self):
        """Threads 스타일 설정이 올바르게 초기화되는지 검증."""
        gen = self._make_generator()
        assert gen.threads_tone == "캐주얼톤"
        assert gen.threads_max_length == 500
        assert gen.threads_hashtags_count == 3

    def test_blog_style_init(self):
        """네이버 블로그 스타일 설정이 올바르게 초기화되는지 검증."""
        gen = self._make_generator()
        assert gen.blog_tone == "정보톤"
        assert gen.blog_min_length == 1500
        assert gen.blog_max_length == 3000
        assert gen.blog_seo_tags_count == 15

    def test_build_prompt_includes_threads_block(self):
        """output_formats에 'threads'가 포함되면 프롬프트에 Threads 블록이 포함되는지 검증."""
        gen = self._make_generator()
        post_data = {
            "title": "테스트 제목",
            "content": "테스트 본문" * 20,
            "source": "blind",
            "category": "general",
            "likes": 10,
            "comments": 5,
            "content_profile": {
                "topic_cluster": "연봉",
                "hook_type": "공감형",
                "emotion_axis": "공감",
                "audience_fit": "범용",
                "recommended_draft_type": "공감형",
                "publishability_score": 75,
                "performance_score": 60,
            },
        }
        prompt = gen._build_prompt(post_data, None, ["twitter", "threads"])
        assert "Threads 초안 작성 조건" in prompt
        assert "<threads>" in prompt or "threads" in prompt.lower()
        assert "500자" in prompt

    def test_build_prompt_includes_blog_block(self):
        """output_formats에 'naver_blog'가 포함되면 프롬프트에 블로그 블록이 포함되는지 검증."""
        gen = self._make_generator()
        post_data = {
            "title": "테스트 제목",
            "content": "테스트 본문" * 20,
            "source": "blind",
            "content_profile": {
                "topic_cluster": "이직",
                "recommended_draft_type": "정보전달형",
            },
        }
        prompt = gen._build_prompt(post_data, None, ["naver_blog"])
        assert "해설형 큐레이션 초안 작성 조건" in prompt or "네이버 블로그" in prompt
        assert "1500자" in prompt
        assert "3000자" in prompt

    def test_build_prompt_excludes_threads_when_not_in_formats(self):
        """output_formats에 'threads'가 없으면 Threads 블록이 생성되지 않는지 검증."""
        gen = self._make_generator()
        post_data = {
            "title": "테스트",
            "content": "본문",
            "source": "blind",
            "content_profile": {},
        }
        prompt = gen._build_prompt(post_data, None, ["twitter"])
        assert "Threads 초안 작성 조건" not in prompt

    def test_parse_response_threads(self):
        """LLM 응답에서 <threads> 태그를 올바르게 파싱하는지 검증."""
        gen = self._make_generator()
        response = textwrap.dedent("""\
            <twitter>트위터 초안 내용</twitter>
            <threads>Threads에 올릴 캐주얼한 글입니다 #직장인 #이직</threads>
            <image_prompt>A busy office scene</image_prompt>
        """)
        drafts, image_prompt = gen._parse_response(response, ["twitter", "threads"], "gemini")
        assert "threads" in drafts
        assert "Threads에 올릴" in drafts["threads"]
        assert "#직장인" in drafts["threads"]
        assert image_prompt == "A busy office scene"

    def test_parse_response_naver_blog(self):
        """LLM 응답에서 <naver_blog> 태그를 올바르게 파싱하는지 검증."""
        gen = self._make_generator()
        response = textwrap.dedent("""\
            <twitter>짧은 트윗</twitter>
            <naver_blog>## 직장인이 알아야 할 연봉 협상 팁

            연봉 협상은 단순히 숫자를 높이는 것이 아닙니다...

            #직장인 #연봉 #이직</naver_blog>
        """)
        drafts, _ = gen._parse_response(response, ["twitter", "naver_blog"], "gemini")
        assert "naver_blog" in drafts
        assert "연봉 협상" in drafts["naver_blog"]
        assert "#직장인" in drafts["naver_blog"]

    def test_parse_response_all_formats(self):
        """모든 포맷(twitter, threads, newsletter, naver_blog)을 동시에 파싱하는지 검증."""
        gen = self._make_generator()
        response = textwrap.dedent("""\
            <twitter>트위터 본문</twitter>
            <threads>Threads 본문 캐주얼</threads>
            <newsletter>뉴스레터 본문 길게</newsletter>
            <naver_blog>## 블로그 제목
            블로그 본문 매우 길게</naver_blog>
            <image_prompt>office scene</image_prompt>
        """)
        drafts, img = gen._parse_response(
            response,
            ["twitter", "threads", "newsletter", "naver_blog"],
            "gemini",
        )
        assert drafts.get("twitter") == "트위터 본문"
        assert "Threads 본문" in drafts.get("threads", "")
        assert "뉴스레터 본문" in drafts.get("newsletter", "")
        assert "블로그 본문" in drafts.get("naver_blog", "")
        assert img == "office scene"


# ── 2. newsletter_formatter 제거됨 ─────────────────────────────────
# TestFormatForThreads 및 format_for_blog 테스트는 newsletter_formatter.py
# 삭제(2026-03-16)에 따라 제거되었습니다. Threads/Blog 초안 생성은 이제
# draft_generator.py 내에서 LLM이 직접 처리합니다.


# ── 3. NotionUploader: 새 속성 매핑 ────────────────────────────────────


class TestNotionUploaderMultiPlatform:
    """NotionUploader에 P6 멀티 플랫폼 속성이 올바르게 정의되었는지 검증."""

    def test_default_props_include_threads(self):
        """DEFAULT_PROPS에 Threads/Blog 핵심 속성이 포함되어 있는지 검증."""
        from pipeline.notion_upload import NotionUploader

        assert "threads_body" in NotionUploader.DEFAULT_PROPS
        assert "blog_body" in NotionUploader.DEFAULT_PROPS
        assert "publish_platforms" in NotionUploader.DEFAULT_PROPS
        # threads_url, blog_url, publish_scheduled_at는 Phase 2 스키마 경량화로 제거됨

    def test_expected_types_defined(self):
        """EXPECTED_TYPES에 핵심 속성의 타입이 정의되어 있는지 검증."""
        from pipeline.notion_upload import NotionUploader

        assert "rich_text" in NotionUploader.EXPECTED_TYPES["threads_body"]
        assert "rich_text" in NotionUploader.EXPECTED_TYPES["blog_body"]
        assert "multi_select" in NotionUploader.EXPECTED_TYPES["publish_platforms"]
        # threads_url, publish_scheduled_at는 Phase 2 스키마 경량화로 제거됨

    def test_auto_detect_keywords_defined(self):
        """AUTO_DETECT_KEYWORDS에 새 속성의 감지 키워드가 정의되어 있는지 검증."""
        from pipeline.notion_upload import NotionUploader

        assert "threads_body" in NotionUploader.AUTO_DETECT_KEYWORDS
        assert "blog_body" in NotionUploader.AUTO_DETECT_KEYWORDS
        assert "publish_platforms" in NotionUploader.AUTO_DETECT_KEYWORDS

    def test_property_count_includes_new_fields(self):
        """DEFAULT_PROPS가 Phase 2 경량화 후 15개 핵심 속성을 포함하는지 검증."""
        from pipeline.notion_upload import NotionUploader

        assert len(NotionUploader.DEFAULT_PROPS) >= 15


# ── 4. config.yaml: 설정 검증 ──────────────────────────────────────────


class TestConfigMultiPlatform:
    """config.yaml에 멀티 플랫폼 설정이 올바르게 반영되었는지 검증."""

    @pytest.fixture
    def config_data(self):
        import yaml
        from pathlib import Path

        config_path = Path(__file__).resolve().parents[2] / "config.yaml"
        if not config_path.exists():
            pytest.skip("config.yaml not available (CI or clean checkout)")
        with open(config_path, encoding="utf-8") as f:
            return yaml.safe_load(f)

    def test_output_formats_default_to_twitter_only(self, config_data):
        """Default review generation stays X-first; secondary formats remain opt-in."""
        assert config_data["output_formats"] == ["twitter"]
        assert config_data.get("content_strategy", {}).get("support_channels") == []

    @pytest.mark.skip(reason="naver_blog output is currently disabled in config.yaml")
    def test_output_formats_include_naver_blog(self, config_data):
        """output_formats에 'naver_blog'가 포함되어 있는지 검증."""
        assert "naver_blog" in config_data["output_formats"]

    def test_threads_style_exists(self, config_data):
        """threads_style 설정이 존재하고 올바른 키를 가지고 있는지 검증."""
        ts = config_data.get("threads_style", {})
        assert ts.get("max_length") == 500
        assert ts.get("hashtags_count") == 3
        assert ts.get("include_hashtags") is True

    def test_naver_blog_style_exists(self, config_data):
        """naver_blog_style 설정이 존재하고 올바른 키를 가지고 있는지 검증."""
        bs = config_data.get("naver_blog_style", {})
        assert bs.get("min_length") == 1500
        assert bs.get("max_length") == 3000
        assert bs.get("seo_tags_count") == 15

    def test_notion_properties_include_new_fields(self, config_data):
        """notion.properties에 새 멀티 플랫폼 필드가 포함되어 있는지 검증."""
        props = config_data.get("notion", {}).get("properties", {})
        assert props.get("threads_body") == "Threads 본문"
        assert props.get("blog_body") == "블로그 본문"
        assert props.get("publish_platforms") == "발행 플랫폼"
        assert props.get("threads_url") == "Threads 링크"
        assert props.get("blog_url") == "블로그 링크"
        assert props.get("publish_scheduled_at") == "발행 예정일"
