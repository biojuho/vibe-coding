import os
import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock

from pipeline.notion_upload import NotionUploader
from config import ERROR_NOTION_CONFIG_MISSING, ERROR_NOTION_SCHEMA_MISMATCH


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
@patch("httpx.AsyncClient.post")
async def test_query_collection_database(mock_post, mock_config):
    with patch.dict(os.environ, clear=True):
        uploader = NotionUploader(mock_config)
        uploader._schema_ready = True
        uploader.collection_kind = "database"

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"results": []}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

    res = await uploader.query_collection(page_size=10, start_cursor="cur")
    assert res == {"results": []}
    mock_post.assert_called_once()
    args, kwargs = mock_post.call_args
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


# ── 추가 커버리지 테스트 ──────────────────────────────────────────────────────


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


@pytest.mark.asyncio
async def test_ensure_schema_exception_sets_error(mock_config):
    """_safe_notion_call 예외 시 error 코드 설정 후 False 반환."""
    from config import ERROR_NOTION_SCHEMA_FETCH_FAILED

    uploader = NotionUploader(mock_config)
    uploader._safe_notion_call = AsyncMock(side_effect=RuntimeError("connection refused"))

    res = await uploader.ensure_schema()
    assert res is False
    assert uploader.last_error_code == ERROR_NOTION_SCHEMA_FETCH_FAILED
    assert "connection refused" in uploader.last_error_message


@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_query_collection_with_filter_and_sorts(mock_post, mock_config):
    """filter, sorts 파라미터가 body에 포함되는지 확인."""
    with patch.dict(os.environ, clear=True):
        uploader = NotionUploader(mock_config)
        uploader._schema_ready = True
        uploader.collection_kind = "database"

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"results": []}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

    flt = {"property": "Status", "status": {"equals": "Draft"}}
    srt = [{"property": "Date", "direction": "descending"}]
    await uploader.query_collection(filter=flt, sorts=srt)

    args, kwargs = mock_post.call_args
    assert kwargs["json"]["filter"] == flt
    assert kwargs["json"]["sorts"] == srt


@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_query_collection_data_source_endpoint(mock_post, mock_config):
    """collection_kind=data_source 시 data_sources 엔드포인트 사용."""
    with patch.dict(os.environ, clear=True):
        uploader = NotionUploader(mock_config)
        uploader._schema_ready = True
        uploader.collection_kind = "data_source"

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"results": []}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

    await uploader.query_collection()

    args, kwargs = mock_post.call_args
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
