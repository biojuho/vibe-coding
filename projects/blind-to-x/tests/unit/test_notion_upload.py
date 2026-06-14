import os
from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from config import ERROR_NOTION_CONFIG_MISSING, ERROR_NOTION_SCHEMA_MISMATCH, ERROR_NOTION_UPLOAD_FAILED
from pipeline.notion_retry_diagnostics import notion_retry_diagnostics
from pipeline.notion_upload import NotionUploader


@pytest.fixture
def mock_config():
    return {
        "notion.api_key": "test_api_key",
        "notion.database_id": "test_db_id",
        "notion.status_default": "Draft",
        "dedup.cache_ttl_minutes": "30",
        "dedup.lookback_days": "14",
    }


def test_init_with_config(mock_config):
    with patch.dict(os.environ, clear=True):
        uploader = NotionUploader(mock_config)
        assert uploader.api_key == "test_api_key"
        assert uploader.raw_database_id == "test_db_id"
        assert uploader.status_default == "Draft"
        assert uploader._url_cache_ttl_seconds == 1800
        assert uploader._url_cache_lookback_days == 14


def test_init_env_vars_override(mock_config):
    with patch.dict(os.environ, {"NOTION_API_KEY": "env_api_key", "NOTION_DATABASE_ID": "env_db_id"}):
        uploader = NotionUploader(mock_config)
        assert uploader.api_key == "env_api_key"
        assert uploader.raw_database_id == "env_db_id"


def test_init_defers_notion_client_creation(mock_config):
    with patch.dict(os.environ, clear=True), patch("pipeline.notion_upload.AsyncClient") as mock_client_cls:
        uploader = NotionUploader(mock_config)
        mock_client_cls.assert_not_called()

        client = uploader.client

    assert client is mock_client_cls.return_value
    mock_client_cls.assert_called_once_with(auth="test_api_key")


def test_client_assignment_marks_initialized(mock_config):
    with patch.dict(os.environ, clear=True), patch("pipeline.notion_upload.AsyncClient") as mock_client_cls:
        uploader = NotionUploader(mock_config)
        injected_client = object()
        uploader.client = injected_client

        assert uploader.client is injected_client
        mock_client_cls.assert_not_called()


def _mock_async_http_client(mock_client_cls, *, response, method="post"):
    mock_http = AsyncMock()
    getattr(mock_http, method).return_value = response
    mock_context = AsyncMock()
    mock_context.__aenter__.return_value = mock_http
    mock_client_cls.return_value = mock_context
    return mock_http


def test_error_management(mock_config):
    uploader = NotionUploader(mock_config)
    uploader._set_error("ERR_123", "Test error message")
    assert uploader.last_error_code == "ERR_123"
    assert uploader.last_error_message == "Test error message"

    uploader._clear_error()
    assert uploader.last_error_code is None
    assert uploader.last_error_message is None


@pytest.mark.asyncio
async def test_list_accessible_sources(mock_config):
    uploader = NotionUploader(mock_config)
    uploader.client = AsyncMock()
    uploader.client.search.return_value = {
        "results": [
            {"object": "database", "title": [{"plain_text": "DB1"}], "id": "id1"},
            {"object": "page", "title": [{"plain_text": "Page"}]},  # Should be ignored
            {"object": "data_source", "id": "id2"},  # Untitled
        ]
    }

    sources = await uploader.list_accessible_sources()
    assert len(sources) == 2
    assert "database:DB1 (id1)" in sources
    assert "data_source:(untitled) (id2)" in sources


@pytest.mark.asyncio
async def test_list_accessible_sources_no_client(mock_config):
    mock_config["notion.api_key"] = ""
    with patch.dict(os.environ, clear=True):
        uploader = NotionUploader(mock_config)
        assert await uploader.list_accessible_sources() == []


@pytest.mark.asyncio
async def test_retrieve_collection_database_success(mock_config):
    uploader = NotionUploader(mock_config)
    uploader.client = AsyncMock()
    uploader.client.databases.retrieve.return_value = {"id": "test_db_id", "properties": {"Prop1": {}}}

    coll = await uploader._retrieve_collection()
    assert coll["id"] == "test_db_id"
    assert uploader.collection_kind == "database"


@pytest.mark.asyncio
async def test_retrieve_collection_data_source_success(mock_config):
    uploader = NotionUploader(mock_config)
    uploader.client = AsyncMock()
    uploader.client.databases.retrieve.side_effect = Exception("Not a database")
    uploader.client.data_sources.retrieve.return_value = {"id": "test_ds_id"}

    coll = await uploader._retrieve_collection()
    assert coll["id"] == "test_ds_id"
    assert uploader.collection_kind == "data_source"


@pytest.mark.asyncio
async def test_retrieve_collection_failure(mock_config):
    uploader = NotionUploader(mock_config)
    uploader.client = AsyncMock()
    uploader.client.databases.retrieve.side_effect = Exception("Not a database")
    uploader.client.data_sources.retrieve.side_effect = Exception("Not a data_source")
    uploader._list_accessible_sources = AsyncMock(return_value=["db1"])

    with pytest.raises(RuntimeError) as exc:
        await uploader._retrieve_collection()
    assert "Not a database" in str(exc.value)
    assert "Accessible objects: db1" in str(exc.value)


@pytest.mark.asyncio
async def test_safe_notion_call_success(mock_config):
    uploader = NotionUploader(mock_config)

    async def mock_fn():
        return "success"

    res = await uploader._safe_notion_call(mock_fn)
    assert res == "success"
    assert uploader.last_notion_retry_report == {
        "attempt_count": 1,
        "retry_count": 0,
        "max_retries": 3,
        "final_state": "success",
        "final_error": None,
        "last_status": None,
        "retryable": None,
        "attempts": [],
    }


@pytest.mark.asyncio
@patch("asyncio.sleep", new_callable=AsyncMock)
async def test_safe_notion_call_retry(mock_sleep, mock_config):
    uploader = NotionUploader(mock_config)
    call_count = 0

    async def mock_fn():
        nonlocal call_count
        call_count += 1
        if call_count < 3:

            class DummyError(Exception):
                status = 429

            raise DummyError("Rate limited")
        return "success"

    res = await uploader._safe_notion_call(mock_fn, max_retries=3)
    assert res == "success"
    assert call_count == 3
    assert mock_sleep.call_count == 2
    report = uploader.last_notion_retry_report
    assert report is not None
    assert report["final_state"] == "success"
    assert report["attempt_count"] == 3
    assert report["retry_count"] == 2
    assert report["last_status"] == 429
    assert report["attempts"] == [
        {
            "attempt": 1,
            "status": 429,
            "retry_after_seconds": None,
            "retryable": True,
            "will_retry": True,
            "delay_seconds": 1,
            "error_type": "DummyError",
            "error": "Rate limited",
        },
        {
            "attempt": 2,
            "status": 429,
            "retry_after_seconds": None,
            "retryable": True,
            "will_retry": True,
            "delay_seconds": 2,
            "error_type": "DummyError",
            "error": "Rate limited",
        },
    ]


@pytest.mark.asyncio
@patch("asyncio.sleep", new_callable=AsyncMock)
async def test_safe_notion_call_retries_httpx_status_error(mock_sleep, mock_config):
    uploader = NotionUploader(mock_config)
    call_count = 0

    async def mock_fn():
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            request = httpx.Request("POST", "https://api.notion.com/v1/pages")
            response = httpx.Response(429, request=request)
            raise httpx.HTTPStatusError("Too Many Requests", request=request, response=response)
        return "success"

    res = await uploader._safe_notion_call(mock_fn, max_retries=3)
    assert res == "success"
    assert call_count == 2
    mock_sleep.assert_awaited_once_with(1)
    report = uploader.last_notion_retry_report
    assert report is not None
    assert report["final_state"] == "success"
    assert report["retry_count"] == 1
    assert report["attempts"][0]["status"] == 429
    assert report["attempts"][0]["delay_seconds"] == 1


@pytest.mark.asyncio
@patch("asyncio.sleep", new_callable=AsyncMock)
async def test_safe_notion_call_uses_retry_after_header(mock_sleep, mock_config):
    uploader = NotionUploader(mock_config)
    call_count = 0

    async def mock_fn():
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            request = httpx.Request("POST", "https://api.notion.com/v1/pages")
            response = httpx.Response(429, headers={"Retry-After": "7"}, request=request)
            raise httpx.HTTPStatusError("Too Many Requests", request=request, response=response)
        return "success"

    res = await uploader._safe_notion_call(mock_fn, max_retries=3)
    assert res == "success"
    assert call_count == 2
    mock_sleep.assert_awaited_once_with(7)
    report = uploader.last_notion_retry_report
    assert report is not None
    assert report["final_state"] == "success"
    assert report["retry_count"] == 1
    assert report["attempts"][0]["status"] == 429
    assert report["attempts"][0]["retry_after_seconds"] == 7
    assert report["attempts"][0]["delay_seconds"] == 7


@pytest.mark.asyncio
@patch("asyncio.sleep", new_callable=AsyncMock)
async def test_safe_notion_call_retries_service_overload_529(mock_sleep, mock_config):
    uploader = NotionUploader(mock_config)
    call_count = 0

    async def mock_fn():
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            request = httpx.Request("POST", "https://api.notion.com/v1/pages")
            response = httpx.Response(529, headers={"Retry-After": "3"}, request=request)
            raise httpx.HTTPStatusError("Service Overload", request=request, response=response)
        return "success"

    res = await uploader._safe_notion_call(mock_fn, max_retries=3)
    assert res == "success"
    assert call_count == 2
    mock_sleep.assert_awaited_once_with(3)
    report = uploader.last_notion_retry_report
    assert report is not None
    assert report["final_state"] == "success"
    assert report["retry_count"] == 1
    assert report["attempts"][0]["status"] == 529
    assert report["attempts"][0]["retryable"] is True
    assert report["attempts"][0]["retry_after_seconds"] == 3


@pytest.mark.asyncio
async def test_ensure_schema_missing_auth(mock_config):
    mock_config["notion.api_key"] = ""
    with patch.dict(os.environ, clear=True):
        uploader = NotionUploader(mock_config)
        res = await uploader.ensure_schema()
        assert not res
        assert uploader.last_error_code == ERROR_NOTION_CONFIG_MISSING


@pytest.mark.asyncio
async def test_ensure_schema_success(mock_config):
    uploader = NotionUploader(mock_config)
    uploader.client = object()
    uploader._retrieve_collection = AsyncMock(return_value={"properties": {"Prop1": {}}})
    uploader._auto_detect_props = MagicMock(return_value={"Prop1": "Detected"})
    uploader._resolve_props = MagicMock(return_value={"Prop1": "Resolved"})
    uploader._validate_props = MagicMock(return_value=(True, ""))

    res = await uploader.ensure_schema()
    assert res
    assert uploader._schema_ready
    assert uploader.props == {"Prop1": "Resolved"}


@pytest.mark.asyncio
async def test_page_parent_payload(mock_config):
    with patch.dict(os.environ, clear=True):
        uploader = NotionUploader(mock_config)
        uploader.collection_kind = "database"
        assert uploader._page_parent_payload() == {"database_id": "test_db_id"}

        uploader.collection_kind = "data_source"
        assert uploader._page_parent_payload() == {"data_source_id": "test_db_id"}


@pytest.mark.asyncio
@patch("httpx.AsyncClient")
async def test_query_collection_database(mock_client_cls, mock_config):
    with patch.dict(os.environ, clear=True):
        uploader = NotionUploader(mock_config)
        uploader._schema_ready = True
        uploader.collection_kind = "database"

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"results": []}
        mock_resp.raise_for_status = MagicMock()
        mock_http = _mock_async_http_client(mock_client_cls, response=mock_resp)

    res = await uploader.query_collection(page_size=10, start_cursor="cur")
    assert res == {"results": []}
    mock_client_cls.assert_called_once_with(timeout=30)
    args, kwargs = mock_http.post.call_args
    assert "databases/test_db_id/query" in args[0]
    assert kwargs["json"] == {"page_size": 10, "start_cursor": "cur"}


@pytest.mark.asyncio
@patch("httpx.get")
async def test_retrieve_collection_httpx_fallback(mock_get, mock_config):
    uploader = NotionUploader(mock_config)
    uploader.client = AsyncMock()
    uploader.client.databases.retrieve.return_value = {"id": "test_db_id"}  # No properties

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"properties": {"FallbackProp": {}}}
    mock_get.return_value = mock_resp

    coll = await uploader._retrieve_collection()
    assert coll["properties"] == {"FallbackProp": {}}


@pytest.mark.asyncio
@patch("pipeline.notion_upload.NotionUploader.ensure_schema", new_callable=AsyncMock)
async def test_upload_success(mock_ensure_schema, mock_config):
    uploader = NotionUploader(mock_config)
    mock_ensure_schema.return_value = True

    uploader.client = AsyncMock()
    uploader.client.pages.create.return_value = {"url": "https://notion.so/test", "id": "page_id"}
    uploader._page_parent_payload = MagicMock(return_value={"database_id": "test_db_id"})
    uploader._register_url_in_cache = MagicMock()

    # Mock some properties
    uploader.props = {"title": "이름", "url": "URL"}
    uploader._db_properties = {"이름": {"type": "title"}, "URL": {"type": "url"}}

    post_data = {"title": "Test Title", "url": "https://test.com", "status": "approved"}
    res_url, res_id = await uploader.upload(post_data, "https://img.com", {"twitter": "test"})

    assert res_url == "https://notion.so/test"
    assert res_id == "page_id"
    uploader._register_url_in_cache.assert_called_once_with("https://test.com")

    # Verify client.pages.create properties payload
    call_kwargs = uploader.client.pages.create.call_args.kwargs
    props = call_kwargs["properties"]
    assert "이름" in props
    assert props["이름"]["title"][0]["text"]["content"] == "Test Title"


@pytest.mark.asyncio
@patch("pipeline.notion_upload.NotionUploader.ensure_schema", new_callable=AsyncMock)
async def test_update_page_properties_success(mock_ensure_schema, mock_config):
    uploader = NotionUploader(mock_config)
    mock_ensure_schema.return_value = True
    uploader.client = AsyncMock()

    uploader.props = {"status": "상태", "number_prop": "숫자"}
    uploader._db_properties = {"상태": {"type": "status"}, "숫자": {"type": "number"}}

    res = await uploader.update_page_properties("page_id", {"status": "완료", "number_prop": 5})
    assert res is True
    uploader.client.pages.update.assert_called_once()

    call_kwargs = uploader.client.pages.update.call_args.kwargs
    assert call_kwargs["page_id"] == "page_id"
    assert "상태" in call_kwargs["properties"]
    assert call_kwargs["properties"]["상태"]["status"]["name"] == "완료"


@pytest.mark.asyncio
@patch("pipeline.notion_upload.NotionUploader.ensure_schema", new_callable=AsyncMock)
@patch("asyncio.sleep", new_callable=AsyncMock)
async def test_update_page_properties_failure_exposes_retry_diagnostics(mock_sleep, mock_ensure_schema, mock_config):
    uploader = NotionUploader(mock_config)
    mock_ensure_schema.return_value = True

    class RateLimitError(Exception):
        status = 429
        headers = {"Retry-After": "4"}

    call_count = 0

    async def mock_update(**kwargs):
        nonlocal call_count
        call_count += 1
        raise RateLimitError("Rate limited")

    uploader.client = AsyncMock()
    uploader.client.pages.update = mock_update
    uploader.props = {"status": "Status"}
    uploader._db_properties = {"Status": {"type": "status"}}

    res = await uploader.update_page_properties("page_id", {"status": "Blocked"})

    assert res is False
    assert call_count == 3
    assert mock_sleep.await_count == 2
    assert uploader.last_error_code == ERROR_NOTION_UPLOAD_FAILED
    assert "Failed to update Notion page properties" in uploader.last_error_message
    report = uploader.last_notion_retry_report
    assert report is not None
    assert report["final_state"] == "failed"
    assert report["last_status"] == 429
    assert report["retry_count"] == 2

    diagnostics = notion_retry_diagnostics(uploader, retry_label="the Notion property update")
    assert diagnostics["notion_retry_summary"] == {
        "final_state": "failed",
        "attempt_count": 3,
        "retry_count": 2,
        "last_status": 429,
        "retryable": True,
    }
    assert diagnostics["notion_failure_classification"] == {
        "category": "rate_limited",
        "status": 429,
        "retryable": True,
        "retry_recommended": True,
        "wait_seconds": 4,
        "primary_repair": "respect_retry_after_or_backoff",
    }
    assert diagnostics["notion_operator_action"] == (
        "Retry the Notion property update after at least 4s, then reduce request rate if it repeats."
    )


@pytest.mark.asyncio
@patch("pipeline.notion_upload.NotionUploader.ensure_schema", new_callable=AsyncMock)
async def test_update_page_properties_schema_failure_sets_schema_error(mock_ensure_schema, mock_config):
    uploader = NotionUploader(mock_config)
    mock_ensure_schema.return_value = True

    class BadRequestError(Exception):
        status = 400

    async def mock_update(**kwargs):
        raise BadRequestError("Status is not a property that exists")

    uploader.client = AsyncMock()
    uploader.client.pages.update = mock_update
    uploader.props = {"status": "Status"}
    uploader._db_properties = {"Status": {"type": "status"}}

    res = await uploader.update_page_properties("page_id", {"status": "Blocked"})

    assert res is False
    assert uploader.last_error_code == ERROR_NOTION_SCHEMA_MISMATCH
    assert "property update schema mismatch" in uploader.last_error_message


def test_prepare_property_payload_multi_select(mock_config):
    uploader = NotionUploader(mock_config)
    uploader.props = {"risk_flags": "위험 신호"}
    uploader._db_properties = {"위험 신호": {"type": "multi_select"}}

    prop_name, payload = uploader._prepare_property_payload("risk_flags", ["팩트 경계", "클리셰"])

    assert prop_name == "위험 신호"
    assert payload == {"multi_select": [{"name": "팩트 경계"}, {"name": "클리셰"}]}


def test_prepare_property_payload_date_values(mock_config, recwarn):
    uploader = NotionUploader(mock_config)
    uploader.props = {"scheduled": "Scheduled At", "created": "Created At"}
    uploader._db_properties = {"Scheduled At": {"type": "date"}, "Created At": {"type": "date"}}

    prop_name, payload = uploader._prepare_property_payload("scheduled", date(2026, 6, 6))
    assert prop_name == "Scheduled At"
    assert payload == {"date": {"start": "2026-06-06"}}

    prop_name, payload = uploader._prepare_property_payload("created", datetime(2026, 6, 6, 9, 30))
    assert prop_name == "Created At"
    assert payload == {"date": {"start": "2026-06-06T09:30:00"}}

    prop_name, payload = uploader._prepare_property_payload("created", "now")
    assert prop_name == "Created At"
    assert isinstance(payload["date"]["start"], str)
    assert payload["date"]["start"].count(":") == 2
    assert not [warning for warning in recwarn if issubclass(warning.category, DeprecationWarning)]


def test_prepare_property_payload_skips_empty_or_unknown_values(mock_config):
    uploader = NotionUploader(mock_config)
    uploader.props = {"memo": "Memo", "unknown_type": "Unknown Type"}
    uploader._db_properties = {"Memo": {"type": "rich_text"}, "Unknown Type": {"type": "files"}}

    assert uploader._prepare_property_payload("memo", "") == (None, None)
    assert uploader._prepare_property_payload("missing", "value") == (None, None)
    assert uploader._prepare_property_payload("unknown_type", "value") == (None, None)


def test_prepare_property_payload_allows_clearing_x_publish_error(mock_config):
    uploader = NotionUploader(mock_config)
    uploader.props = {"x_publish_error": "X Publish Error", "memo": "Memo"}
    uploader._db_properties = {
        "X Publish Error": {"type": "rich_text"},
        "Memo": {"type": "rich_text"},
    }

    prop_name, payload = uploader._prepare_property_payload("x_publish_error", "")

    assert prop_name == "X Publish Error"
    assert payload == {"rich_text": []}
    assert uploader._prepare_property_payload("memo", "") == (None, None)


def test_build_upload_properties_preserves_review_and_x_fields(mock_config):
    uploader = NotionUploader(mock_config)
    uploader.status_default = "Draft"
    uploader.props = {
        "title": "Title",
        "memo": "Memo",
        "status": "Status",
        "url": "URL",
        "source": "Source",
        "creator_take": "Creator Take",
        "review_focus": "Review Focus",
        "feedback_request": "Feedback Request",
        "risk_flags": "Risk Flags",
        "evidence_anchor": "Evidence Anchor",
        "publish_platforms": "Publish Platforms",
        "x_publish_status": "X Publish Status",
        "x_scheduled_at": "X Scheduled At",
        "tweet_body": "Tweet Body",
        "reply_text": "Reply Text",
        "threads_body": "Threads Body",
        "blog_body": "Blog Body",
        "topic_cluster": "Topic Cluster",
        "emotion_axis": "Emotion Axis",
        "final_rank_score": "Final Rank Score",
    }
    uploader._db_properties = {
        "Title": {"type": "title"},
        "Memo": {"type": "rich_text"},
        "Status": {"type": "status"},
        "URL": {"type": "url"},
        "Source": {"type": "select"},
        "Creator Take": {"type": "rich_text"},
        "Review Focus": {"type": "rich_text"},
        "Feedback Request": {"type": "rich_text"},
        "Risk Flags": {"type": "multi_select"},
        "Evidence Anchor": {"type": "rich_text"},
        "Publish Platforms": {"type": "multi_select"},
        "X Publish Status": {"type": "select"},
        "X Scheduled At": {"type": "date"},
        "Tweet Body": {"type": "rich_text"},
        "Reply Text": {"type": "rich_text"},
        "Threads Body": {"type": "rich_text"},
        "Blog Body": {"type": "rich_text"},
        "Topic Cluster": {"type": "select"},
        "Emotion Axis": {"type": "select"},
        "Final Rank Score": {"type": "number"},
    }
    review_brief = {
        "creator_take": "운영자 해석",
        "evidence_anchor": "근거 앵커",
        "risk_flags": ["팩트 경계", "독자 핏 약함"],
        "has_publishable_draft": True,
        "review_focus": "검토 포인트",
        "feedback_request": "피드백 요청",
        "action_steps": [],
        "publish_platforms": ["X", "Threads"],
    }
    post_data = {
        "title": "테스트 제목",
        "url": "https://example.com/post",
        "source": "blind",
        "publish_scheduled_at": "2026-05-20T09:00:00+09:00",
        "editorial_avg_score": 8.62,
        "publish_decision": {"action": "PUBLISH", "reason": "all gates passed", "quality_score": 95},
    }
    drafts = {
        "twitter": "X 본문",
        "reply_text": "첫 답글",
        "threads": "Threads 본문",
        "naver_blog": "블로그 본문",
    }
    analysis = {
        "selection_summary": "선정 요약",
        "topic_cluster": "직장문화",
        "emotion_axis": "공감",
        "final_rank_score": 87,
    }

    properties = uploader._build_upload_properties(
        post_data,
        "https://example.com/post",
        review_brief,
        analysis,
        drafts,
        "openai: invalid_draft_output",
    )

    memo = properties["Memo"]["rich_text"][0]["text"]["content"]
    assert "선정 요약: 선정 요약" in memo
    assert "운영자 해석: 운영자 해석" in memo
    assert "권장 채널: X, Threads" in memo
    assert "최종 랭크: 87" in memo
    assert "초안 생성 오류: openai: invalid_draft_output" in memo
    assert properties["Risk Flags"]["multi_select"] == [{"name": "팩트 경계"}, {"name": "독자 핏 약함"}]
    assert properties["Publish Platforms"]["multi_select"] == [{"name": "X"}, {"name": "Threads"}]
    assert properties["X Publish Status"]["select"]["name"] == "Ready to Post"
    assert properties["X Scheduled At"]["date"]["start"] == "2026-05-20T09:00:00+09:00"
    assert properties["Tweet Body"]["rich_text"][0]["text"]["content"] == "X 본문"
    assert properties["Reply Text"]["rich_text"][0]["text"]["content"] == "첫 답글"
    assert properties["Topic Cluster"]["select"]["name"] == "직장문화"
    assert properties["Final Rank Score"]["number"] == 87.0


def test_x_publish_status_defaults_to_needs_edit_without_decision(mock_config):
    uploader = NotionUploader(mock_config)
    uploader.props = {"x_publish_status": "X Publish Status"}
    uploader._db_properties = {"X Publish Status": {"type": "select"}}

    properties = {}
    uploader._append_x_publish_properties(properties, {})

    assert properties["X Publish Status"]["select"]["name"] == "Needs Edit"


def test_build_review_brief_summarizes_best_of_n_selection_quality(mock_config):
    uploader = NotionUploader(mock_config)
    drafts = {
        "twitter": "바로 게시할 본문",
        "creator_take": "사람들이 자기 상황과 바로 비교할 수 있는 글",
        "_best_of_n_selection_score": 8.73,
        "_quality_gate_score": 9.5,
        "_quality_gate_failures": 0,
        "_quality_gate_warnings": 1,
        "_max_semantic_similarity": 0.42,
    }
    analysis = {
        "selection_summary": "비교 욕구와 공감 포인트가 둘 다 살아 있는 초안",
        "empathy_anchor": "연봉보다 팀장이 더 문제라는 댓글",
    }

    review_brief = uploader._build_review_brief({}, drafts, analysis)

    expected_summary = (
        "검수 후 게시: 경고 1건 확인, 최종 선택점수 8.73, 게시 적합성 9.5, "
        "최근 유사도 0.42(낮을수록 새로움), 실패 0건, 경고 1건"
    )
    assert review_brief["selection_quality_summary"] == expected_summary
    expected_edit_plan = "경고 있음: 경고 문장 1개만 고친 뒤 훅과 근거가 그대로 살아 있는지 확인합니다."
    assert review_brief["edit_plan"] == expected_edit_plan

    memo = uploader._build_upload_memo(
        {"url": "https://example.com/post"},
        "https://example.com/post",
        review_brief,
        analysis,
        "",
    )
    assert f"선택 품질: {expected_summary}" in memo
    assert f"수정 플랜: {expected_edit_plan}" in memo

    blocks = uploader._build_summary_section_blocks({}, review_brief, analysis, "", drafts)
    bullets = [
        block["bulleted_list_item"]["rich_text"][0]["text"]["content"]
        for block in blocks
        if block.get("type") == "bulleted_list_item"
    ]
    assert f"선택 품질: {expected_summary}" in bullets
    assert f"수정 플랜: {expected_edit_plan}" in bullets


def test_build_review_brief_surfaces_provider_failure_triage(mock_config):
    uploader = NotionUploader(mock_config)
    provider_failure_summary = {
        "total_failures": 2,
        "providers_attempted": ["gemini", "openai"],
        "categories": {"rate_limit": 1, "auth": 1},
        "circuit_breaker_providers": ["openai"],
        "retryable_count": 1,
        "non_retryable_count": 1,
        "primary_failure": {
            "provider": "openai",
            "model": "gpt-4o-mini",
            "category": "auth",
            "retryable": False,
            "circuit_breaker_candidate": True,
            "error_preview": "401 invalid api key",
            "operator_action": "Check provider API key, env wiring, and enabled flags before rerunning.",
        },
        "primary_operator_action": "Check provider API key, env wiring, and enabled flags before rerunning.",
    }
    post_data = {
        "url": "https://example.com/post",
        "draft_provider_failure_summary": provider_failure_summary,
    }
    drafts = {
        "twitter": "초안은 fallback으로 생성됐지만 한 provider는 실패했습니다.",
        "creator_take": "운영자가 먼저 provider 상태를 확인해야 하는 후보입니다.",
    }
    analysis = {
        "selection_summary": "provider failure까지 같이 검토해야 하는 초안",
        "empathy_anchor": "연봉 비교 댓글",
    }

    review_brief = uploader._build_review_brief(post_data, drafts, analysis)

    expected_primary = (
        "primary_failure: provider=openai, model=gpt-4o-mini, category=auth, "
        "retryable=false, circuit_breaker=true, error=401 invalid api key"
    )
    expected_action = "primary_operator_action: Check provider API key, env wiring, and enabled flags before rerunning."
    expected_summary = (
        "provider_failure_summary: total_failures=2; categories=auth=1, rate_limit=1; "
        "providers=gemini, openai; circuit_breaker=openai; non_retryable_count=1; retryable_count=1"
    )
    assert review_brief["provider_failure_triage_lines"] == [
        expected_primary,
        expected_action,
        expected_summary,
    ]

    memo = uploader._build_upload_memo(post_data, "https://example.com/post", review_brief, analysis, "")
    assert "Provider failure triage" in memo
    assert expected_primary in memo
    assert expected_action in memo

    blocks = uploader._build_summary_section_blocks(post_data, review_brief, analysis, "", drafts)
    bullets = [
        block["bulleted_list_item"]["rich_text"][0]["text"]["content"]
        for block in blocks
        if block.get("type") == "bulleted_list_item"
    ]
    assert "Provider failure triage" in bullets
    assert expected_primary in bullets
    assert expected_action in bullets
    assert expected_summary in bullets


def test_provider_failure_triage_falls_back_to_draft_summary(mock_config):
    uploader = NotionUploader(mock_config)
    drafts = {
        "_provider_failure_summary": {
            "primary_failure": {
                "provider": "gemini",
                "category": "rate_limit",
                "retryable": True,
            },
            "primary_operator_action": "Wait for provider rate-limit reset before retrying.",
        }
    }

    lines = uploader._build_provider_failure_triage_lines({}, drafts)

    assert lines == [
        "primary_failure: provider=gemini, category=rate_limit, retryable=true",
        "primary_operator_action: Wait for provider rate-limit reset before retrying.",
    ]


def test_build_selection_quality_summary_marks_copy_ready_clean_winner(mock_config):
    uploader = NotionUploader(mock_config)
    drafts = {
        "twitter": "바로 게시할 수 있는 구체적인 X 본문",
        "_best_of_n_selection_score": 8.9,
        "_quality_gate_score": 9.3,
        "_quality_gate_failures": 0,
        "_quality_gate_warnings": 0,
        "_max_semantic_similarity": 0.31,
    }

    summary = uploader._build_selection_quality_summary(drafts)

    assert summary.startswith("바로 게시 가능, ")
    assert "게시 적합성 9.3" in summary
    assert "실패 0건" in summary
    assert "경고 0건" in summary
    assert (
        uploader._build_selection_edit_plan(drafts, [], True)
        == "바로 게시 가능: 오탈자만 보고 X 본문을 복사한 뒤 링크와 해시태그는 첫 답글로 분리합니다."
    )


def test_build_selection_quality_summary_marks_failed_winner_for_edit(mock_config):
    uploader = NotionUploader(mock_config)
    drafts = {
        "twitter": "점수는 있어도 그대로 게시하면 안 되는 X 본문",
        "_best_of_n_selection_score": 8.2,
        "_quality_gate_score": 7.8,
        "_quality_gate_failures": 2,
        "_quality_gate_warnings": 3,
        "_max_semantic_similarity": 0.22,
    }

    summary = uploader._build_selection_quality_summary(drafts)

    assert summary.startswith("수정 필요: 품질 게이트 실패 2건, ")
    assert "게시 적합성 7.8" in summary
    assert "실패 2건" in summary
    assert (
        uploader._build_selection_edit_plan(drafts, [], True)
        == "품질 게이트 실패 2건: 진단 상세의 실패 항목을 먼저 고치고 다시 검수합니다."
    )


def test_build_selection_edit_plan_prioritizes_similarity_rewrite(mock_config):
    uploader = NotionUploader(mock_config)
    drafts = {
        "twitter": "예전 초안과 너무 비슷한 X 본문",
        "_best_of_n_selection_score": 8.5,
        "_quality_gate_score": 8.7,
        "_quality_gate_failures": 0,
        "_quality_gate_warnings": 0,
        "_max_semantic_similarity": 0.81,
    }

    edit_plan = uploader._build_selection_edit_plan(drafts, [], True)

    assert edit_plan == "최근 유사도 0.81: 같은 결론은 유지하되 첫 문장 장면과 표현을 새로 씁니다."


def test_build_selection_edit_plan_requires_selection_confidence_for_copy_ready(mock_config):
    uploader = NotionUploader(mock_config)
    drafts = {
        "twitter": "품질 점수만 높은 X 본문",
        "_best_of_n_selection_score": 7.6,
        "_quality_gate_score": 9.4,
        "_quality_gate_failures": 0,
        "_quality_gate_warnings": 0,
        "_max_semantic_similarity": 0.32,
    }

    edit_plan = uploader._build_selection_edit_plan(drafts, [], True)

    assert edit_plan == "검수 후 게시: 첫 문장 훅, 근거 보존, 톤 자연스러움만 확인한 뒤 복사합니다."


def test_build_review_brief_skips_selection_quality_when_metadata_absent(mock_config):
    uploader = NotionUploader(mock_config)
    drafts = {
        "twitter": "바로 게시할 본문",
        "creator_take": "사람들이 자기 상황과 바로 비교할 수 있는 글",
    }
    analysis = {
        "selection_summary": "비교 욕구와 공감 포인트가 둘 다 살아 있는 초안",
        "empathy_anchor": "연봉보다 팀장이 더 문제라는 댓글",
    }

    review_brief = uploader._build_review_brief({}, drafts, analysis)

    assert review_brief["selection_quality_summary"] == ""
    assert review_brief["edit_plan"] == "검수 후 게시: 첫 문장 훅, 근거 보존, 톤 자연스러움만 확인한 뒤 복사합니다."

    memo = uploader._build_upload_memo(
        {"url": "https://example.com/post"},
        "https://example.com/post",
        review_brief,
        analysis,
        "",
    )
    assert "선택 품질:" not in memo
    assert "수정 플랜: 검수 후 게시: 첫 문장 훅, 근거 보존, 톤 자연스러움만 확인한 뒤 복사합니다." in memo

    blocks = uploader._build_summary_section_blocks({}, review_brief, analysis, "", drafts)
    bullets = [
        block["bulleted_list_item"]["rich_text"][0]["text"]["content"]
        for block in blocks
        if block.get("type") == "bulleted_list_item"
    ]
    assert not any(text.startswith("선택 품질:") for text in bullets)
    assert any(text.startswith("수정 플랜: 검수 후 게시") for text in bullets)


@pytest.mark.asyncio
@patch("pipeline.notion_upload.NotionUploader.ensure_schema", new_callable=AsyncMock)
async def test_upload_populates_review_brief_properties(mock_ensure_schema, mock_config):
    uploader = NotionUploader(mock_config)
    mock_ensure_schema.return_value = True
    uploader.client = AsyncMock()
    uploader.client.pages.create.return_value = {"url": "https://notion.so/review", "id": "page_review"}
    uploader._page_parent_payload = MagicMock(return_value={"database_id": "test_db_id"})
    uploader._register_url_in_cache = MagicMock()

    uploader.props = {
        "title": "콘텐츠",
        "url": "원본 URL",
        "memo": "메모",
        "creator_take": "운영자 해석",
        "review_focus": "검토 포인트",
        "feedback_request": "피드백 요청",
        "risk_flags": "위험 신호",
        "evidence_anchor": "근거 앵커",
        "publish_platforms": "발행 플랫폼",
        "x_publish_status": "X Publish Status",
        "x_scheduled_at": "X Scheduled At",
        "x_post_url": "X Post URL",
        "tweet_body": "트윗 본문",
        "threads_body": "Threads 본문",
        "status": "상태",
        "date": "생성일",
        "source": "원본 소스",
    }
    uploader._db_properties = {
        "콘텐츠": {"type": "title"},
        "원본 URL": {"type": "url"},
        "메모": {"type": "rich_text"},
        "운영자 해석": {"type": "rich_text"},
        "검토 포인트": {"type": "rich_text"},
        "피드백 요청": {"type": "rich_text"},
        "위험 신호": {"type": "multi_select"},
        "근거 앵커": {"type": "rich_text"},
        "발행 플랫폼": {"type": "multi_select"},
        "X Publish Status": {"type": "select"},
        "X Scheduled At": {"type": "date"},
        "X Post URL": {"type": "url"},
        "트윗 본문": {"type": "rich_text"},
        "Threads 본문": {"type": "rich_text"},
        "상태": {"type": "status"},
        "생성일": {"type": "date"},
        "원본 소스": {"type": "select"},
    }

    post_data = {
        "title": "연봉 이야기",
        "url": "https://example.com/post",
        "source": "blind",
        "draft_generation_error": "openai: invalid_draft_output:missing_tags:naver_blog",
        "quality_gate_report": "passed — 구체 장면 있음 / CTA 포함",
        "x_scheduled_at": "2026-05-20T09:00:00+09:00",
        "publish_decision": {"action": "PUBLISH", "reason": "all gates passed", "quality_score": 95},
    }
    drafts = {
        "twitter": "숏폼 초안입니다.",
        "threads": "쓰레드 초안입니다.",
        "creator_take": "연봉 숫자가 직장인의 비교 심리를 바로 건드립니다.",
    }
    analysis = {
        "selection_summary": "직장인이 자기 일처럼 받아들일 숫자 비교 글",
        "empathy_anchor": "연봉 1800 깎고 이직",
        "hard_reject_reasons": ["직장인 맥락 약함"],
    }

    result = await uploader.upload(post_data, None, drafts, analysis=analysis)
    assert result == ("https://notion.so/review", "page_review")

    props = uploader.client.pages.create.call_args.kwargs["properties"]
    assert "invalid_draft_output" in props["메모"]["rich_text"][0]["text"]["content"]
    assert props["운영자 해석"]["rich_text"][0]["text"]["content"].startswith("연봉 숫자가")
    assert "근거 앵커 '연봉 1800 깎고 이직'" in props["검토 포인트"]["rich_text"][0]["text"]["content"]
    assert "반려 사유" in props["피드백 요청"]["rich_text"][0]["text"]["content"]
    assert props["위험 신호"]["multi_select"] == [{"name": "독자 핏 약함"}]
    assert props["발행 플랫폼"]["multi_select"] == [{"name": "X"}, {"name": "Threads"}]
    assert props["X Publish Status"]["select"]["name"] == "Ready to Post"
    assert props["X Scheduled At"]["date"]["start"] == "2026-05-20T09:00:00+09:00"


@pytest.mark.asyncio
@patch("pipeline.notion_upload.NotionUploader.ensure_schema", new_callable=AsyncMock)
async def test_upload_surfaces_missing_draft_next_steps(mock_ensure_schema, mock_config):
    uploader = NotionUploader(mock_config)
    mock_ensure_schema.return_value = True
    uploader.client = AsyncMock()
    uploader.client.pages.create.return_value = {"url": "https://notion.so/review", "id": "page_missing_draft"}
    uploader._page_parent_payload = MagicMock(return_value={"database_id": "test_db_id"})
    uploader._register_url_in_cache = MagicMock()

    uploader.props = {
        "title": "콘텐츠",
        "url": "원본 URL",
        "memo": "메모",
        "creator_take": "운영자 해석",
        "review_focus": "검토 포인트",
        "feedback_request": "피드백 요청",
        "risk_flags": "위험 신호",
        "evidence_anchor": "근거 앵커",
        "publish_platforms": "발행 플랫폼",
        "x_publish_status": "X Publish Status",
        "x_scheduled_at": "X Scheduled At",
        "x_published_at": "X Published At",
        "x_post_url": "X Post URL",
        "x_publish_error": "X Publish Error",
        "tweet_body": "트윗 본문",
        "status": "상태",
        "date": "생성일",
        "source": "원본 소스",
    }
    uploader._db_properties = {
        "콘텐츠": {"type": "title"},
        "원본 URL": {"type": "url"},
        "메모": {"type": "rich_text"},
        "운영자 해석": {"type": "rich_text"},
        "검토 포인트": {"type": "rich_text"},
        "피드백 요청": {"type": "rich_text"},
        "위험 신호": {"type": "multi_select"},
        "근거 앵커": {"type": "rich_text"},
        "발행 플랫폼": {"type": "multi_select"},
        "X Publish Status": {"type": "select"},
        "X Scheduled At": {"type": "date"},
        "X Published At": {"type": "date"},
        "X Post URL": {"type": "url"},
        "X Publish Error": {"type": "rich_text"},
        "트윗 본문": {"type": "rich_text"},
        "상태": {"type": "status"},
        "생성일": {"type": "date"},
        "원본 소스": {"type": "select"},
    }

    post_data = {
        "title": "주식 수익률 이야기",
        "url": "https://example.com/post",
        "source": "blind",
    }
    drafts = {
        "creator_take": "숫자 체감 비교를 잘 살리면 반응이 날 글감입니다.",
    }
    analysis = {
        "selection_summary": "내 돈 감각과 비교해보고 싶은 욕구를 건드리는 글",
        "empathy_anchor": "한달에 20-30%만 꾸준히",
    }

    result = await uploader.upload(post_data, None, drafts, analysis=analysis)
    assert result == ("https://notion.so/review", "page_missing_draft")

    props = uploader.client.pages.create.call_args.kwargs["properties"]
    assert "초안이 비어 있습니다" in props["피드백 요청"]["rich_text"][0]["text"]["content"]
    assert "직접 쓰고 싶은 글감인지" in props["검토 포인트"]["rich_text"][0]["text"]["content"]

    children = uploader.client.pages.create.call_args.kwargs["children"]
    callout_texts = [
        block["callout"]["rich_text"][0]["text"]["content"] for block in children if block.get("type") == "callout"
    ]
    assert any("지금 할 일" in text and "규제 위반이 아니라" in text for text in callout_texts)


@pytest.mark.asyncio
@patch("pipeline.notion_upload.NotionUploader.ensure_schema", new_callable=AsyncMock)
async def test_upload_groups_diagnostics_and_raw_content_into_toggles(mock_ensure_schema, mock_config):
    uploader = NotionUploader(mock_config)
    mock_ensure_schema.return_value = True
    uploader.client = AsyncMock()
    uploader.client.pages.create.return_value = {"url": "https://notion.so/layout", "id": "page_layout"}
    uploader._page_parent_payload = MagicMock(return_value={"database_id": "test_db_id"})
    uploader._register_url_in_cache = MagicMock()

    uploader.props = {
        "title": "콘텐츠",
        "url": "원본 URL",
        "memo": "메모",
        "creator_take": "운영자 해석",
        "review_focus": "검토 포인트",
        "feedback_request": "피드백 요청",
        "risk_flags": "위험 신호",
        "evidence_anchor": "근거 앵커",
        "publish_platforms": "발행 플랫폼",
        "x_publish_status": "X Publish Status",
        "x_scheduled_at": "X Scheduled At",
        "x_published_at": "X Published At",
        "x_post_url": "X Post URL",
        "x_publish_error": "X Publish Error",
        "tweet_body": "트윗 본문",
        "reply_text": "답글 텍스트",
        "status": "상태",
        "date": "생성일",
        "source": "원본 소스",
        "topic_cluster": "토픽 클러스터",
        "emotion_axis": "감정 축",
        "final_rank_score": "최종 랭크 점수",
    }
    uploader._db_properties = {
        "콘텐츠": {"type": "title"},
        "원본 URL": {"type": "url"},
        "메모": {"type": "rich_text"},
        "운영자 해석": {"type": "rich_text"},
        "검토 포인트": {"type": "rich_text"},
        "피드백 요청": {"type": "rich_text"},
        "위험 신호": {"type": "multi_select"},
        "근거 앵커": {"type": "rich_text"},
        "발행 플랫폼": {"type": "multi_select"},
        "X Publish Status": {"type": "select"},
        "X Scheduled At": {"type": "date"},
        "X Published At": {"type": "date"},
        "X Post URL": {"type": "url"},
        "X Publish Error": {"type": "rich_text"},
        "트윗 본문": {"type": "rich_text"},
        "답글 텍스트": {"type": "rich_text"},
        "상태": {"type": "status"},
        "생성일": {"type": "date"},
        "원본 소스": {"type": "select"},
        "토픽 클러스터": {"type": "select"},
        "감정 축": {"type": "select"},
        "최종 랭크 점수": {"type": "number"},
    }

    post_data = {
        "title": "팀장보다 먼저 퇴근하면 안 된대",
        "url": "https://example.com/post",
        "source": "blind",
        "content": "신입인데 팀장보다 먼저 퇴근하면 안 된다고 들었다.",
        "quality_gate_report": "passed — 구체 장면 있음 / CTA 포함",
        "quality_gate_scores": {"twitter": 84, "threads": 79},
        "quality_gate_retries": 1,
        "editorial_avg_score": 8.62,
        "editorial_scores": {"hook": 9.0, "voice": 8.2},
        "readability_scores": {"twitter": 7.8},
        "fact_check_warnings": {"twitter": ["'절반이 이직해'는 과한 추론일 수 있음"]},
        "regulation_report": "전체 플랫폼 규제 검증 통과",
        "publish_decision": {
            "action": "PUBLISH",
            "reason": "all gates passed",
            "quality_score": 95,
            "metrics": {"weighted_length": 39},
        },
    }
    drafts = {
        "twitter": "신입이 먼저 퇴근했다가 팀장한테 혼났다.",
        "reply_text": "원문: https://example.com/post\n#직장문화",
        "creator_take": "직장인이라면 바로 자기 일처럼 느낄 소재다.",
    }
    analysis = {
        "selection_summary": "신입/팀장 갈등이 직장인 현실감과 논쟁을 동시에 건드림",
        "empathy_anchor": "팀장보다 먼저 퇴근하면 안 된다",
        "spinoff_angle": "팀별 문화 차이, 세대 갈등",
        "topic_cluster": "직장문화",
        "hook_type": "논쟁형",
        "emotion_axis": "분노",
        "emotion_lane": "공감",
        "audience_fit": "2030 신입",
        "audience_need": "내 회사도 이런지 비교하고 싶음",
        "recommended_draft_type": "controversy_hook",
        "final_rank_score": 87,
    }

    result = await uploader.upload(
        post_data,
        "https://img.com/thumb.png",
        drafts,
        analysis=analysis,
        screenshot_url="https://img.com/screenshot.png",
    )
    assert result == ("https://notion.so/layout", "page_layout")

    children = uploader.client.pages.create.call_args.kwargs["children"]
    heading_titles = [
        block[block["type"]]["rich_text"][0]["text"]["content"]
        for block in children
        if block.get("type") in {"heading_2", "heading_3"}
    ]
    assert "검토 요약" in heading_titles
    assert "X 업로드 카드" in heading_titles
    assert "X 본문" in heading_titles
    assert "진단 상세" in heading_titles
    assert "원문" in heading_titles

    top_level_bullets = [
        block["bulleted_list_item"]["rich_text"][0]["text"]["content"]
        for block in children
        if block.get("type") == "bulleted_list_item"
    ]
    assert "권장 채널: X" in top_level_bullets
    assert "X 가중 글자 수: 39/280자 (OK)" in top_level_bullets
    assert any("업로드 순서: X 본문 복사" in text for text in top_level_bullets)
    assert "결정: PUBLISH - all gates passed" in top_level_bullets
    assert any("X Post URL" in text for text in top_level_bullets)
    assert "에디토리얼 평균 점수: 8.62" in top_level_bullets
    assert "품질 재시도: 1회" in top_level_bullets

    toggles = {
        block["toggle"]["rich_text"][0]["text"]["content"]: block["toggle"]["children"]
        for block in children
        if block.get("type") == "toggle"
    }
    assert "진단 펼치기" in toggles
    assert "원문 펼치기" in toggles

    diagnostic_children = toggles["진단 펼치기"]
    diagnostic_headings = [
        block[block["type"]]["rich_text"][0]["text"]["content"]
        for block in diagnostic_children
        if block.get("type") in {"heading_1", "heading_2", "heading_3"}
    ]
    assert "콘텐츠 인텔리전스" in diagnostic_headings
    assert "품질 검증 리포트" in diagnostic_headings
    assert "규제 검증 리포트" in diagnostic_headings

    raw_children = toggles["원문 펼치기"]
    raw_headings = [
        block[block["type"]]["rich_text"][0]["text"]["content"]
        for block in raw_children
        if block.get("type") in {"heading_1", "heading_2", "heading_3"}
    ]
    assert "원문 스크린샷" in raw_headings
    assert "원문 내용" in raw_headings


def test_x_upload_check_lines_use_weighted_count_for_korean_body(mock_config):
    uploader = NotionUploader(mock_config)

    lines = uploader._build_x_upload_check_lines({"twitter": "가" * 141})

    assert "X 가중 글자 수: 282/280자 (초과)" in lines


def test_x_upload_check_lines_use_weighted_count_for_urls(mock_config):
    uploader = NotionUploader(mock_config)

    lines = uploader._build_x_upload_check_lines({"twitter": "a https://example.com/very/long/path b"})

    assert "X 가중 글자 수: 27/280자 (OK)" in lines


def test_build_content_intelligence_lines_formats_optional_signals(mock_config):
    uploader = NotionUploader(mock_config)
    post_data = {
        "emotion_profile": {"top_emotions": [("분노", 0.75), ("공감", 1.0), ("", 0.2)], "dominant_group": "분노"},
        "editorial_scores": {"hook": 9.0, "voice": 8.25, "empty": ""},
        "readability_scores": {"twitter": 7.8},
        "quality_gate_scores": {"twitter": 84, "threads": 79.5},
        "quality_gate_retries": 2,
        "fact_check_warnings": {
            "twitter": ["'일반적 이직'이라는 추론은 원문 근거가 약할 수 있음"],
            "threads": [],
        },
        "draft_generation_error": "openai: invalid_draft_output:missing_tags:naver_blog",
    }
    analysis = {
        "topic_cluster": "직장문화",
        "hook_type": "일화형",
        "emotion_axis": "분노",
        "emotion_lane": "공감",
        "audience_fit": "2030 신입",
        "selection_summary": "신입과 대기업 갈등을 동시에 건드림",
        "audience_need": "내 회사가 이상한지 비교하고 싶음",
        "recommended_draft_type": "controversy_hook",
        "spinoff_angle": "대기업 문화 차이",
    }

    lines = uploader._build_content_intelligence_lines(post_data, analysis)

    assert "세부 감정 프로필: 분노=0.75, 공감=1" in lines
    assert "지배 감정 그룹: 분노" in lines
    assert "에디토리얼 점수: hook=9, voice=8.25" in lines
    assert "가독성 점수: twitter=7.8" in lines
    assert "품질 게이트 점수: twitter=84, threads=79.5" in lines
    assert "품질 재시도: 2회" in lines
    assert any(line.startswith("팩트 체크 경고: twitter 1건") for line in lines)
    assert any(line.startswith("초안 생성 오류: openai: invalid_draft_output") for line in lines)


# ── 추가 커버리지 테스트 ──────────────────────────────────────────────────────


def test_review_metric_helpers_filter_empty_values(mock_config):
    uploader = NotionUploader(mock_config)

    assert (
        uploader._format_metric_pairs(
            {
                "twitter": 84,
                "threads": 79.5,
                "empty": "",
                "missing": None,
                "enabled": True,
            }
        )
        == "twitter=84, threads=79.5, enabled=Yes"
    )
    assert uploader._format_metric_pairs([]) == ""
    assert (
        uploader._format_fact_check_warning_counts(
            {
                "twitter": ["warning one", "warning two"],
                "threads": [],
                "blog": "not-a-list",
            }
        )
        == "twitter 2\uac74"
    )


def test_content_intelligence_helpers_preserve_review_details(mock_config):
    uploader = NotionUploader(mock_config)
    lines = uploader._build_content_intelligence_lines(
        {
            "emotion_profile": {
                "top_emotions": [("anger", 0.75), ("", 0.25)],
                "dominant_group": "tension",
            },
            "editorial_scores": {"hook": 9, "voice": 8.2},
            "readability_scores": {"twitter": 7.8},
            "quality_gate_scores": {"twitter": 84, "threads": 79},
            "fact_check_warnings": {"twitter": ["short warning"], "threads": ["second warning"]},
        },
        {
            "topic_cluster": "work",
            "hook_type": "contrast",
            "emotion_axis": "anger",
            "emotion_lane": "empathy",
            "audience_fit": "office",
            "selection_summary": "summary",
            "audience_need": "need",
            "recommended_draft_type": "controversy",
        },
    )
    joined = "\n".join(lines)

    assert "anger=0.75" in joined
    assert "tension" in joined
    assert "hook=9, voice=8.2" in joined
    assert "twitter=7.8" in joined
    assert "twitter=84, threads=79" in joined
    assert "twitter 1\uac74 (short warning); threads 1\uac74 (second warning)" in joined


@pytest.mark.asyncio
async def test_list_accessible_sources_limit_respected(mock_config):
    """limit 이상의 결과가 있을 때 정확히 limit 개수만 반환."""
    uploader = NotionUploader(mock_config)
    uploader.client = AsyncMock()
    uploader.client.search.return_value = {
        "results": [{"object": "database", "title": [{"plain_text": f"DB{i}"}], "id": f"id{i}"} for i in range(20)]
    }
    sources = await uploader.list_accessible_sources(limit=3)
    assert len(sources) == 3


@pytest.mark.asyncio
async def test_list_accessible_sources_exception_returns_empty(mock_config):
    """search 호출 중 예외 발생 시 빈 리스트 반환."""
    uploader = NotionUploader(mock_config)
    uploader.client = AsyncMock()
    uploader.client.search.side_effect = Exception("network error")
    sources = await uploader.list_accessible_sources()
    assert sources == []


@pytest.mark.asyncio
async def test_retrieve_collection_no_client_raises(mock_config):
    """client 없을 때 _retrieve_collection → RuntimeError."""
    mock_config["notion.api_key"] = ""
    with patch.dict(os.environ, clear=True):
        uploader = NotionUploader(mock_config)
    with pytest.raises(RuntimeError, match="Notion client is not initialized"):
        await uploader._retrieve_collection()


@pytest.mark.asyncio
@patch("httpx.get")
async def test_retrieve_collection_httpx_fallback_exception(mock_get, mock_config):
    """httpx fallback 자체가 예외를 던져도 계속 진행."""
    uploader = NotionUploader(mock_config)
    uploader.client = AsyncMock()
    uploader.client.databases.retrieve.return_value = {"id": "test_db_id"}  # properties 없음
    mock_get.side_effect = Exception("httpx timeout")

    coll = await uploader._retrieve_collection()
    # httpx 실패해도 원본 database 반환
    assert coll["id"] == "test_db_id"


@pytest.mark.asyncio
async def test_safe_notion_call_non_retryable_raises_immediately(mock_config):
    """401 같은 non-retryable status는 즉시 raise."""
    uploader = NotionUploader(mock_config)
    call_count = 0

    async def mock_fn():
        nonlocal call_count
        call_count += 1

        class AuthError(Exception):
            status = 401

        raise AuthError("Unauthorized")

    with pytest.raises(Exception, match="Unauthorized"):
        await uploader._safe_notion_call(mock_fn, max_retries=3)

    assert call_count == 1  # 재시도 없이 즉시 종료
    report = uploader.last_notion_retry_report
    assert report is not None
    assert report["final_state"] == "failed"
    assert report["final_error"] == "Unauthorized"
    assert report["last_status"] == 401
    assert report["retry_count"] == 0
    assert report["attempts"][0]["retryable"] is False
    assert report["attempts"][0]["will_retry"] is False


@pytest.mark.asyncio
@patch("asyncio.sleep", new_callable=AsyncMock)
async def test_safe_notion_call_exhausts_retries_raises(mock_sleep, mock_config):
    """max_retries 모두 소진 시 마지막 예외가 raise."""
    uploader = NotionUploader(mock_config)

    async def mock_fn():
        class RateLimitError(Exception):
            status = 429

        raise RateLimitError("Rate limited")

    with pytest.raises(Exception, match="Rate limited"):
        await uploader._safe_notion_call(mock_fn, max_retries=2)

    assert mock_sleep.call_count == 1  # max_retries=2이면 retry 1번
    report = uploader.last_notion_retry_report
    assert report is not None
    assert report["final_state"] == "failed"
    assert report["final_error"] == "Rate limited"
    assert report["last_status"] == 429
    assert report["retry_count"] == 1
    assert report["attempts"][0]["will_retry"] is True
    assert report["attempts"][1]["will_retry"] is False


@pytest.mark.asyncio
async def test_ensure_schema_exception_sets_error(mock_config):
    """_safe_notion_call 예외 시 error 코드 설정 후 False 반환."""
    from config import ERROR_NOTION_SCHEMA_FETCH_FAILED

    uploader = NotionUploader(mock_config)
    uploader.client = object()
    uploader._safe_notion_call = AsyncMock(side_effect=RuntimeError("connection refused"))

    res = await uploader.ensure_schema()
    assert res is False
    assert uploader.last_error_code == ERROR_NOTION_SCHEMA_FETCH_FAILED
    assert "connection refused" in uploader.last_error_message


@pytest.mark.asyncio
@patch("httpx.AsyncClient")
async def test_query_collection_with_filter_and_sorts(mock_client_cls, mock_config):
    """filter, sorts 파라미터가 body에 포함되는지 확인."""
    with patch.dict(os.environ, clear=True):
        uploader = NotionUploader(mock_config)
        uploader._schema_ready = True
        uploader.collection_kind = "database"

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"results": []}
        mock_resp.raise_for_status = MagicMock()
        mock_http = _mock_async_http_client(mock_client_cls, response=mock_resp)

    flt = {"property": "Status", "status": {"equals": "Draft"}}
    srt = [{"property": "Date", "direction": "descending"}]
    await uploader.query_collection(filter=flt, sorts=srt)

    mock_client_cls.assert_called_once_with(timeout=30)
    args, kwargs = mock_http.post.call_args
    assert kwargs["json"]["filter"] == flt
    assert kwargs["json"]["sorts"] == srt


@pytest.mark.asyncio
@patch("httpx.AsyncClient")
async def test_query_collection_data_source_endpoint(mock_client_cls, mock_config):
    """collection_kind=data_source 시 data_sources 엔드포인트 사용."""
    with patch.dict(os.environ, clear=True):
        uploader = NotionUploader(mock_config)
        uploader._schema_ready = True
        uploader.collection_kind = "data_source"

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"results": []}
        mock_resp.raise_for_status = MagicMock()
        mock_http = _mock_async_http_client(mock_client_cls, response=mock_resp)

    await uploader.query_collection()

    mock_client_cls.assert_called_once_with(timeout=30)
    args, kwargs = mock_http.post.call_args
    assert "data_sources" in args[0]


@pytest.mark.asyncio
async def test_query_collection_schema_not_ready_raises(mock_config):
    """schema 준비 실패 시 RuntimeError."""
    uploader = NotionUploader(mock_config)
    uploader._schema_ready = False
    uploader.ensure_schema = AsyncMock(return_value=False)
    uploader.last_error_message = "Schema missing"

    with pytest.raises(RuntimeError, match="Schema missing"):
        await uploader.query_collection()


@pytest.mark.asyncio
async def test_ensure_schema_already_ready_returns_true(mock_config):
    """_schema_ready=True인 경우 즉시 True 반환 (early return)."""
    uploader = NotionUploader(mock_config)
    uploader._schema_ready = True
    res = await uploader.ensure_schema()
    assert res is True


@pytest.mark.asyncio
async def test_ensure_schema_validation_fails_sets_mismatch_error(mock_config):
    """schema prop 검증 실패 시 ERROR_NOTION_SCHEMA_MISMATCH 설정 후 False 반환."""
    uploader = NotionUploader(mock_config)
    uploader.client = object()
    uploader._retrieve_collection = AsyncMock(return_value={"properties": {"PropA": {}}})
    uploader._auto_detect_props = MagicMock(return_value={"PropA": "Detected"})
    uploader._resolve_props = MagicMock(return_value={"PropA": "Resolved"})
    uploader._validate_props = MagicMock(return_value=(False, "required prop missing"))

    res = await uploader.ensure_schema()
    assert res is False
    assert uploader.last_error_code == ERROR_NOTION_SCHEMA_MISMATCH
    assert "mismatch" in uploader.last_error_message.lower()


# ── upload / update_page_properties 재시도 통합 테스트 ─────────────────────


@pytest.mark.asyncio
@patch("pipeline.notion_upload.NotionUploader.ensure_schema", new_callable=AsyncMock)
@patch("asyncio.sleep", new_callable=AsyncMock)
async def test_upload_retries_on_429(mock_sleep, mock_ensure_schema, mock_config):
    """upload()가 429 에러 시 _safe_notion_call을 통해 재시도 후 성공."""
    uploader = NotionUploader(mock_config)
    mock_ensure_schema.return_value = True

    class RateLimitError(Exception):
        status = 429

    call_count = 0

    async def mock_create(**kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RateLimitError("Rate limited")
        return {"url": "https://notion.so/ok", "id": "page_ok"}

    uploader.client = AsyncMock()
    uploader.client.pages.create = mock_create
    uploader._page_parent_payload = MagicMock(return_value={"database_id": "db"})
    uploader._register_url_in_cache = MagicMock()
    uploader.props = {"title": "이름"}
    uploader._db_properties = {"이름": {"type": "title"}}

    res = await uploader.upload({"title": "Test", "url": "https://test.com"}, None, {})
    assert res is not None
    url, pid = res
    assert url == "https://notion.so/ok"
    assert call_count == 2  # 1번 실패 + 1번 성공


@pytest.mark.asyncio
@patch("pipeline.notion_upload.NotionUploader.ensure_schema", new_callable=AsyncMock)
@patch("asyncio.sleep", new_callable=AsyncMock)
async def test_upload_400_not_retried(mock_sleep, mock_ensure_schema, mock_config):
    """upload()가 400 에러 시 재시도 없이 즉시 실패."""
    uploader = NotionUploader(mock_config)
    mock_ensure_schema.return_value = True

    class BadRequestError(Exception):
        status = 400

    call_count = 0

    async def mock_create(**kwargs):
        nonlocal call_count
        call_count += 1
        raise BadRequestError("is not a property that exists")

    uploader.client = AsyncMock()
    uploader.client.pages.create = mock_create
    uploader._page_parent_payload = MagicMock(return_value={"database_id": "db"})
    uploader.props = {"title": "이름"}
    uploader._db_properties = {"이름": {"type": "title"}}

    res = await uploader.upload({"title": "Test", "url": "https://test.com"}, None, {})
    assert res is None  # 에러 → None 반환
    assert call_count == 1  # 재시도 없음


@pytest.mark.asyncio
@patch("pipeline.notion_upload.NotionUploader.ensure_schema", new_callable=AsyncMock)
@patch("asyncio.sleep", new_callable=AsyncMock)
async def test_update_page_properties_retries_on_502(mock_sleep, mock_ensure_schema, mock_config):
    """update_page_properties()가 502 에러 시 재시도 후 성공."""
    uploader = NotionUploader(mock_config)
    mock_ensure_schema.return_value = True

    class ServerError(Exception):
        status = 502

    call_count = 0

    async def mock_update(**kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise ServerError("Bad Gateway")
        return {"id": kwargs.get("page_id")}

    uploader.client = AsyncMock()
    uploader.client.pages.update = mock_update
    uploader.props = {"status": "상태"}
    uploader._db_properties = {"상태": {"type": "status"}}

    res = await uploader.update_page_properties("page_123", {"status": "완료"})
    assert res is True
    assert call_count == 2


@pytest.mark.asyncio
@patch("pipeline.notion_upload.NotionUploader.ensure_schema", new_callable=AsyncMock)
@patch("httpx.AsyncClient")
async def test_update_collection_properties_uses_database_endpoint(mock_client_cls, mock_ensure_schema, mock_config):
    with patch.dict(os.environ, {"NOTION_DATABASE_ID": "test_db_id"}, clear=True):
        uploader = NotionUploader(mock_config)
    mock_ensure_schema.return_value = True
    uploader.collection_kind = "database"

    mock_resp = MagicMock()
    mock_resp.json.return_value = {"id": "test_db_id"}
    mock_resp.raise_for_status = MagicMock()
    mock_http = _mock_async_http_client(mock_client_cls, response=mock_resp, method="patch")

    payload = {"검토 포인트": {"rich_text": {}}}
    result = await uploader.update_collection_properties(payload)

    assert result == {"id": "test_db_id"}
    mock_client_cls.assert_called_once_with(timeout=30)
    args, kwargs = mock_http.patch.call_args
    assert "databases/test_db_id" in args[0]
    assert kwargs["json"] == {"properties": payload}
    assert mock_ensure_schema.await_count == 2
