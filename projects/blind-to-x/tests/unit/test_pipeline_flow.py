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
                "auto_move_to_review_threshold": 60,
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
            "title": "실수령 280 듣고 회의실이 조용해진 날",
            "url": url,
            "content": "회의실에서 실수령 280 이야기가 나오자 다들 웃다가도 한숨을 쉬었다. 연봉, 이직, 회사 분위기가 한 번에 겹치는 직장인 공감 글이다.",
            "screenshot_path": None,
        }

    def assess_quality(self, _post_data):
        return {"score": 90, "reasons": [], "metrics": {}}


class StubImageUploader:
    async def upload(self, _path):
        return "https://image.example/test.png"


class StubDraftGenerator:
    async def generate_drafts(self, _post_data, top_tweets=None, output_formats=None, allow_partial=False):  # noqa: ARG002
        return {
            "twitter": "실수령 280 얘기 나오자 회의실이 조용해졌다. 다들 웃는 척했지만 속으로는 한숨 쉬던 날이 있잖아요. 3% 인상 버티기 vs 이직 준비, 지금 더 현실적인 쪽은 뭐였나요?",
            "reply_text": "원문: (링크)\n#연봉 #직장인",
            "creator_take": "숫자 하나로 직장인 비교 심리를 바로 건드리는 글입니다.",
        }, None


class StubDraftGeneratorFailure:
    async def generate_drafts(self, _post_data, top_tweets=None, output_formats=None, allow_partial=False):  # noqa: ARG002
        return {
            "_provider_used": "none",
            "_generation_failed": True,
            "_generation_error": "gemini: 429 | openai: invalid_draft_output:missing_tags:reply",
        }, None


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
    assert result["content_profile"]["topic_cluster"] in {"연봉", "이직", "회사문화", "상사", "기타"}
    assert uploader.updated["updates"]["status"] == "검토필요"


def test_process_single_post_generation_failure_review_only_uploads_card():
    uploader = StubNotionUploaderOk()
    result = asyncio.run(
        bs.process_single_post(
            "https://example.com/a",
            StubScraper(),
            StubImageUploader(),
            draft_generator=StubDraftGeneratorFailure(),
            notion_uploader=uploader,
            config=FakeConfig(),
            source_name="blind",
            feed_mode="popular",
            review_only=True,
        )
    )
    assert result["success"] is True
    assert result["error_code"] is None
    assert result["notion_url"] == "https://notion.so/page"


def test_process_single_post_generation_failure_non_review_stops_before_upload():
    uploader = StubNotionUploaderOk()
    result = asyncio.run(
        bs.process_single_post(
            "https://example.com/a",
            StubScraper(),
            StubImageUploader(),
            draft_generator=StubDraftGeneratorFailure(),
            notion_uploader=uploader,
            config=FakeConfig(),
            source_name="blind",
            feed_mode="popular",
            review_only=False,
        )
    )
    assert result["success"] is False
    assert result["error_code"] == bs.ERROR_DRAFT_GENERATION_FAILED
    assert result["failure_stage"] == "generation"
    assert result["notion_url"] is None


def test_process_single_post_result_contains_trace_id():
    """result dict에 8자 hex trace_id가 포함되어야 함."""
    uploader = StubNotionUploaderOk()
    result = asyncio.run(
        bs.process_single_post(
            "https://example.com/trace",
            StubScraper(),
            StubImageUploader(),
            draft_generator=StubDraftGenerator(),
            notion_uploader=uploader,
            config=FakeConfig(),
            source_name="blind",
            review_only=True,
        )
    )
    assert "trace_id" in result
    tid = result["trace_id"]
    assert len(tid) == 8
    assert all(c in "0123456789abcdef" for c in tid)


def test_process_single_post_trace_id_present_on_error():
    """에러 경로에서도 trace_id가 존재해야 함."""
    result = asyncio.run(
        bs.process_single_post(
            "https://example.com/trace-err",
            StubScraper(),
            StubImageUploader(),
            draft_generator=StubDraftGeneratorFailure(),
            notion_uploader=StubNotionUploaderOk(),
            config=FakeConfig(),
        )
    )
    assert "trace_id" in result
    assert len(result["trace_id"]) == 8


def test_process_single_post_budget_exceeded_skips_draft_generation():
    """예산 초과 시 draft 생성 건너뛰고 BUDGET_EXCEEDED 에러 반환."""
    from unittest.mock import patch, MagicMock

    mock_cost_db = MagicMock()
    mock_cost_db.is_daily_budget_exceeded.return_value = True

    uploader = StubNotionUploaderOk()
    with patch("pipeline.cost_db.get_cost_db", return_value=mock_cost_db):
        result = asyncio.run(
            bs.process_single_post(
                "https://example.com/budget-test",
                StubScraper(),
                StubImageUploader(),
                draft_generator=StubDraftGenerator(),
                notion_uploader=uploader,
                config=FakeConfig(),
                source_name="blind",
            )
        )
    assert result["error_code"] == bs.ERROR_BUDGET_EXCEEDED
    assert result["failure_stage"] == "budget"
    assert result["notion_url"] is None


def test_process_single_post_budget_ok_proceeds_to_draft():
    """예산 미초과 시 정상 진행."""
    from unittest.mock import patch, MagicMock

    mock_cost_db = MagicMock()
    mock_cost_db.is_daily_budget_exceeded.return_value = False

    uploader = StubNotionUploaderOk()
    with patch("pipeline.cost_db.get_cost_db", return_value=mock_cost_db):
        result = asyncio.run(
            bs.process_single_post(
                "https://example.com/budget-ok",
                StubScraper(),
                StubImageUploader(),
                draft_generator=StubDraftGenerator(),
                notion_uploader=uploader,
                config=FakeConfig(),
                source_name="blind",
                review_only=True,
            )
        )
    assert result["success"] is True
    assert result["notion_url"] is not None


class StubScraperNoScreenshot:
    """스크린샷 없는 텍스트 전용 포스트."""

    min_content_length = 20

    async def scrape_post(self, url):
        return {
            "title": "이미지 없는 직장인 고민",
            "url": url,
            "content": "회사에서 자리 이동을 통보받았는데 거부할 수 있을까요? 주변 동료들은 그냥 따르라고 하는데 억울합니다.",
            "screenshot_path": None,
            "images": [],
        }

    def assess_quality(self, _post_data):
        return {"score": 85, "reasons": [], "metrics": {}}


def test_process_single_post_no_image_still_succeeds():
    """이미지/스크린샷 없는 포스트도 정상 업로드."""
    uploader = StubNotionUploaderOk()
    result = asyncio.run(
        bs.process_single_post(
            "https://example.com/no-img",
            StubScraperNoScreenshot(),
            StubImageUploader(),
            draft_generator=StubDraftGenerator(),
            notion_uploader=uploader,
            config=FakeConfig(),
            source_name="blind",
            review_only=True,
        )
    )
    assert result["success"] is True
    assert result["notion_url"] == "https://notion.so/page"
    assert "trace_id" in result


def test_process_single_post_success_has_content_profile():
    """성공 경로에서 content_profile이 result에 포함되어야 함."""
    uploader = StubNotionUploaderOk()
    result = asyncio.run(
        bs.process_single_post(
            "https://example.com/profile-check",
            StubScraper(),
            StubImageUploader(),
            draft_generator=StubDraftGenerator(),
            notion_uploader=uploader,
            config=FakeConfig(),
            source_name="blind",
            review_only=True,
        )
    )
    assert result["success"] is True
    assert "content_profile" in result
    profile = result["content_profile"]
    assert "topic_cluster" in profile
    assert "final_rank_score" in profile
