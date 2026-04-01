from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import blind_scraper as bs  # noqa: E402


class FakeConfig:
    def __init__(self, data):
        self.data = data

    def get(self, key, default=None):
        cur = self.data
        for part in key.split("."):
            if isinstance(cur, dict):
                cur = cur.get(part)
            else:
                return default
        return default if cur is None else cur


class StubImageUploader:
    async def upload(self, _path):
        return "https://image.example/test.png"


class StubDraftGenerator:
    async def generate_drafts(self, _post_data, _top_tweets=None, **_kwargs):
        return "drafts"


class StubNotionUploaderNoCall:
    last_error_code = None
    last_error_message = None

    async def is_duplicate(self, _url):
        return False

    async def upload(self, *_args, **_kwargs):
        raise AssertionError("upload should not be called for filtered/parse-failed cases")


class ParseFailScraper:
    min_content_length = 20

    async def scrape_post(self, url):
        return {
            "_scrape_error": True,
            "url": url,
            "error_code": bs.ERROR_SCRAPE_PARSE_FAILED,
            "failure_stage": "parse",
            "failure_reason": "main_container_not_found",
            "error_message": "parse failed",
        }

    def assess_quality(self, _post_data):
        return {"score": 0, "reasons": ["parse_failed"], "metrics": {}}


class LowQualityScraper:
    min_content_length = 20

    async def scrape_post(self, url):
        return {
            "url": url,
            "title": "title",
            "content": "this sentence is long enough but mostly english and low korean ratio",
            "screenshot_path": None,
        }

    def assess_quality(self, _post_data):
        return {"score": 40, "reasons": ["low_korean_ratio"], "metrics": {}}


class ShortContentScraper:
    min_content_length = 20

    async def scrape_post(self, url):
        return {"url": url, "title": "title", "content": "짧다", "screenshot_path": None}

    def assess_quality(self, _post_data):
        return {"score": 95, "reasons": [], "metrics": {}}


class SpamContentScraper:
    min_content_length = 20

    async def scrape_post(self, url):
        return {
            "url": url,
            "title": "normal title",
            "content": "회원가입시 추천인 코드를 입력하면 포인트를 줍니다. 추천인 가입 필수입니다.",
            "screenshot_path": None,
        }

    def assess_quality(self, _post_data):
        return {"score": 90, "reasons": [], "metrics": {}}


class InappropriateTitleScraper:
    min_content_length = 20

    async def scrape_post(self, url):
        return {
            "url": url,
            "title": "카페에서 앞에 앉은여자 골반 구경중",
            "content": "본문은 충분히 길고 일반 텍스트처럼 보이지만 제목이 문제입니다.",
            "screenshot_path": None,
        }

    def assess_quality(self, _post_data):
        return {"score": 85, "reasons": [], "metrics": {}}


def test_process_single_post_parse_failure_classified():
    result = asyncio.run(
        bs.process_single_post(
            "https://example.com/a",
            ParseFailScraper(),
            StubImageUploader(),
            draft_generator=StubDraftGenerator(),
            notion_uploader=StubNotionUploaderNoCall(),
        )
    )
    assert result["success"] is False
    assert result["error_code"] == bs.ERROR_SCRAPE_PARSE_FAILED
    assert result["failure_stage"] == "parse"


def test_process_single_post_low_quality_filtered():
    result = asyncio.run(
        bs.process_single_post(
            "https://example.com/a",
            LowQualityScraper(),
            StubImageUploader(),
            draft_generator=StubDraftGenerator(),
            notion_uploader=StubNotionUploaderNoCall(),
        )
    )
    assert result["success"] is True
    assert result["error_code"] == bs.ERROR_FILTERED_LOW_QUALITY
    assert result["notion_url"] == "(skipped-filtered)"
    assert result["failure_stage"] == "filter"
    assert result["failure_reason"] == "low_korean_ratio"


def test_short_filter_regression_still_works():
    result = asyncio.run(
        bs.process_single_post(
            "https://example.com/a",
            ShortContentScraper(),
            StubImageUploader(),
            draft_generator=StubDraftGenerator(),
            notion_uploader=StubNotionUploaderNoCall(),
        )
    )
    assert result["success"] is True
    assert result["error_code"] == bs.ERROR_FILTERED_SHORT


def test_spam_filter_regression_still_works():
    result = asyncio.run(
        bs.process_single_post(
            "https://example.com/a",
            SpamContentScraper(),
            StubImageUploader(),
            draft_generator=StubDraftGenerator(),
            notion_uploader=StubNotionUploaderNoCall(),
        )
    )
    assert result["success"] is True
    assert result["error_code"] == bs.ERROR_FILTERED_SPAM


def test_inappropriate_title_filter_blocks_before_upload():
    result = asyncio.run(
        bs.process_single_post(
            "https://example.com/inappropriate",
            InappropriateTitleScraper(),
            StubImageUploader(),
            draft_generator=StubDraftGenerator(),
            notion_uploader=StubNotionUploaderNoCall(),
        )
    )
    assert result["success"] is True
    assert result["error_code"] == bs.ERROR_FILTERED_SPAM
    assert result["notion_url"] == "(skipped-filtered)"
    assert result["failure_stage"] == "filter"
    assert result["failure_reason"] == "inappropriate_content"


def test_rejected_emotion_axis_blocks_before_upload(monkeypatch):
    class EmotionScraper:
        min_content_length = 20

        async def scrape_post(self, url):
            return {
                "url": url,
                "title": "갈등을 부추기는 자극적인 제목",
                "content": "본문은 길지만 감정 축 분류 결과가 혐오라면 업로드되면 안 됩니다.",
                "screenshot_path": None,
            }

        def assess_quality(self, _post_data):
            return {"score": 88, "reasons": [], "metrics": {}}

    class DummyProfile:
        def to_dict(self):
            return {
                "scrape_quality_score": 88,
                "publishability_score": 82,
                "performance_score": 79,
                "final_rank_score": 84,
                "emotion_axis": "혐오",
                "topic_cluster": "기타",
                "hook_type": "논쟁형",
            }

    monkeypatch.setattr(
        "pipeline.process_stages.filter_profile_stage.build_content_profile", lambda *args, **kwargs: DummyProfile()
    )

    result = asyncio.run(
        bs.process_single_post(
            "https://example.com/hate",
            EmotionScraper(),
            StubImageUploader(),
            draft_generator=StubDraftGenerator(),
            notion_uploader=StubNotionUploaderNoCall(),
            config=FakeConfig(
                {
                    "ranking": {"weights": {}, "llm_viral_boost": False},
                    "review": {
                        "auto_move_to_review_threshold": 65,
                        "reject_on_missing_title": True,
                        "reject_on_missing_content": True,
                    },
                    "content_strategy": {"require_human_approval": True},
                }
            ),
        )
    )
    assert result["success"] is True
    assert result["error_code"] == bs.ERROR_FILTERED_SPAM
    assert result["notion_url"] == "(skipped-filtered)"
    assert result["failure_stage"] == "filter"
    assert result["failure_reason"] == "rejected_emotion_axis"


def test_feed_fetch_intercept_failure_falls_back_to_direct(monkeypatch, tmp_path):
    class DummyElement:
        def __init__(self, href):
            self.href = href

        async def get_attribute(self, _name):
            return self.href

    class DummyPage:
        def __init__(self):
            self.goto_calls = 0

        async def route(self, *_args, **_kwargs):
            return None

        async def unroute(self, *_args, **_kwargs):
            return None

        async def goto(self, _url, wait_until=None, timeout=None):  # noqa: ARG002
            self.goto_calls += 1
            if self.goto_calls == 1 and wait_until == "domcontentloaded":
                raise RuntimeError("intercept mode failed")
            return None

        async def wait_for_selector(self, *_args, **_kwargs):
            return None

        async def query_selector_all(self, *_args, **_kwargs):
            return [DummyElement("/kr/topic/1"), DummyElement("/kr/topic/2")]

        async def close(self):
            return None

    config = FakeConfig(
        {
            "screenshot_dir": str(tmp_path / "shots"),
            "request": {"timeout_seconds": 20, "retries": 1, "backoff_seconds": 0.1},
            "scrape_quality": {"selector_timeout_ms": 1000, "direct_fallback_timeout_ms": 1000},
        }
    )
    scraper = bs.BlindScraper(config)
    page = DummyPage()

    async def _fake_new_page():
        return page

    async def _fake_login(_page):
        return True

    async def _fake_fetch(_url):
        return "<html></html>"

    monkeypatch.setattr(scraper, "_new_page", _fake_new_page)
    monkeypatch.setattr(scraper, "_login", _fake_login)
    monkeypatch.setattr(scraper, "_fetch_html_via_session", _fake_fetch)

    urls = asyncio.run(scraper._fetch_post_urls("https://feed.example", label="feed", limit=2))
    assert len(urls) == 2
    assert urls[0].startswith("https://www.teamblind.com")
    assert page.goto_calls == 2
    assert scraper.last_feed_fetch_error is None


def test_feed_fetch_session_failure_still_uses_direct_navigation(monkeypatch, tmp_path):
    class DummyElement:
        def __init__(self, href):
            self.href = href

        async def get_attribute(self, _name):
            return self.href

    class DummyPage:
        def __init__(self):
            self.goto_calls = 0
            self.routed = False

        async def route(self, *_args, **_kwargs):
            self.routed = True
            return None

        async def unroute(self, *_args, **_kwargs):
            self.routed = False
            return None

        async def goto(self, _url, wait_until=None, timeout=None):  # noqa: ARG002
            self.goto_calls += 1
            return None

        async def wait_for_selector(self, *_args, **_kwargs):
            return None

        async def query_selector_all(self, *_args, **_kwargs):
            return [DummyElement("/kr/topic/10"), DummyElement("/kr/topic/11")]

        async def close(self):
            return None

    config = FakeConfig(
        {
            "screenshot_dir": str(tmp_path / "shots"),
            "request": {"timeout_seconds": 20, "retries": 1, "backoff_seconds": 0.1},
            "scrape_quality": {"selector_timeout_ms": 1000, "direct_fallback_timeout_ms": 1000},
        }
    )
    scraper = bs.BlindScraper(config)
    page = DummyPage()

    async def _fake_new_page():
        return page

    async def _fake_login(_page):
        return True

    async def _fake_fetch(_url):
        raise RuntimeError("curl error 77: error setting certificate verify locations")

    monkeypatch.setattr(scraper, "_new_page", _fake_new_page)
    monkeypatch.setattr(scraper, "_login", _fake_login)
    monkeypatch.setattr(scraper, "_fetch_html_via_session", _fake_fetch)

    urls = asyncio.run(scraper._fetch_post_urls("https://feed.example", label="feed", limit=2))
    assert len(urls) == 2
    assert urls[0].startswith("https://www.teamblind.com")
    assert page.goto_calls == 1
    assert page.routed is False
    assert scraper.last_feed_fetch_error is None
