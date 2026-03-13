from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import blind_scraper as bs  # noqa: E402


class FakeConfig:
    def __init__(self):
        self.data = {
            "content_strategy": {"require_human_approval": True},
            "ranking": {
                "final_rank_min": 60,
                "weights": {"scrape_quality": 0.35, "publishability": 0.40, "performance": 0.25},
            },
            "review": {
                "auto_move_to_review_threshold": 65,
                "reject_on_missing_title": True,
                "reject_on_missing_content": True,
            },
        }

    def get(self, key, default=None):
        cur = self.data
        for part in key.split("."):
            if isinstance(cur, dict):
                cur = cur.get(part)
            else:
                return default
        return default if cur is None else cur


class StubScraper:
    min_content_length = 20

    async def scrape_post(self, url):
        return {
            "title": f"title:{url}",
            "url": url,
            "content": "직장인 공감 포인트가 충분히 들어간 꽤 긴 본문입니다. 팀장, 이직, 회사 문화 이야기가 섞여 있습니다.",
            "screenshot_path": None,
        }

    def assess_quality(self, _post_data):
        return {"score": 90, "reasons": [], "metrics": {}}


class StubImageUploader:
    async def upload(self, _path):
        return "https://image.example/test.png"


class StubDraftGenerator:
    async def generate_drafts(self, _post_data, top_tweets=None, output_formats=None):  # noqa: ARG002
        return {"twitter": "[공감형 트윗]\n공감 초안", "newsletter": "뉴스레터 초안"}, None


class StubNotionUploaderDuplicate:
    last_error_code = None
    last_error_message = None

    async def is_duplicate(self, _url):
        return True

    async def upload(self, _post_data, _image_url, _drafts, analysis=None, **kwargs):  # noqa: ARG002
        raise AssertionError("upload should not be called for duplicates")


class StubNotionUploaderSchemaError:
    last_error_code = bs.ERROR_NOTION_SCHEMA_MISMATCH
    last_error_message = "schema mismatch"

    async def is_duplicate(self, _url):
        return None

    async def upload(self, _post_data, _image_url, _drafts, analysis=None, **kwargs):  # noqa: ARG002
        raise AssertionError("upload should not be called when schema is invalid")


class StubNotionUploaderDuplicateCheckError:
    last_error_code = bs.ERROR_NOTION_DUPLICATE_CHECK_FAILED
    last_error_message = "duplicate check failed"

    async def is_duplicate(self, _url):
        return None

    async def upload(self, _post_data, _image_url, _drafts, analysis=None, **kwargs):  # noqa: ARG002
        raise AssertionError("upload should not be called when duplicate check fails")


class StubNotionUploaderOk:
    last_error_code = None
    last_error_message = None
    updated = None

    async def is_duplicate(self, _url):
        return False

    async def upload(self, _post_data, _image_url, _drafts, analysis=None, **kwargs):  # noqa: ARG002
        return "https://notion.so/page", "page-1"

    async def update_page_properties(self, page_id, updates):
        self.updated = {"page_id": page_id, "updates": updates}
        return True


def test_process_single_post_duplicate_sets_error_code():
    result = asyncio.run(
        bs.process_single_post(
            "https://example.com/a",
            StubScraper(),
            StubImageUploader(),
            draft_generator=StubDraftGenerator(),
            notion_uploader=StubNotionUploaderDuplicate(),
            config=FakeConfig(),
        )
    )
    assert result["success"] is True
    assert result["error_code"] == bs.ERROR_DUPLICATE_URL
    assert result["notion_url"] == "(skipped-duplicate)"


def test_process_single_post_schema_error_sets_error_code():
    result = asyncio.run(
        bs.process_single_post(
            "https://example.com/a",
            StubScraper(),
            StubImageUploader(),
            draft_generator=StubDraftGenerator(),
            notion_uploader=StubNotionUploaderSchemaError(),
            config=FakeConfig(),
        )
    )
    assert result["success"] is False
    assert result["error_code"] == bs.ERROR_NOTION_SCHEMA_MISMATCH


def test_process_single_post_duplicate_check_error_sets_error_code():
    result = asyncio.run(
        bs.process_single_post(
            "https://example.com/a",
            StubScraper(),
            StubImageUploader(),
            draft_generator=StubDraftGenerator(),
            notion_uploader=StubNotionUploaderDuplicateCheckError(),
            config=FakeConfig(),
        )
    )
    assert result["success"] is False
    assert result["error_code"] == bs.ERROR_NOTION_DUPLICATE_CHECK_FAILED


def test_process_single_post_success_returns_notion_url_and_review_state():
    uploader = StubNotionUploaderOk()
    result = asyncio.run(
        bs.process_single_post(
            "https://example.com/a",
            StubScraper(),
            StubImageUploader(),
            draft_generator=StubDraftGenerator(),
            notion_uploader=uploader,
            config=FakeConfig(),
            source_name="blind",
            feed_mode="popular",
            review_only=True,
        )
    )
    assert result["success"] is True
    assert result["notion_url"] == "https://notion.so/page"
    assert result["error_code"] is None
    assert result["content_profile"]["topic_cluster"] in {"이직", "회사문화", "상사", "기타"}
    assert uploader.updated["updates"]["review_status"] == "검토필요"
