from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import blind_scraper as bs  # noqa: E402
import pipeline.notion_upload as notion_mod  # noqa: E402


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


def make_async_client(schema, query_results=None):
    holder = {}

    class DummyDatabases:
        def __init__(self, _schema, _query_results):
            self.schema = _schema
            self.query_results = _query_results or []
            self.last_query_kwargs = None

        async def retrieve(self, database_id):
            return {"id": database_id, "properties": self.schema}

        async def query(self, **kwargs):
            self.last_query_kwargs = kwargs
            return {"results": self.query_results}

    class DummyPages:
        def __init__(self):
            self.last_create_kwargs = None

        async def create(self, **kwargs):
            self.last_create_kwargs = kwargs
            return {"url": "https://notion.so/fake-page", "id": "page-123"}

        async def update(self, **kwargs):
            return kwargs

    class DummyClient:
        def __init__(self, _schema, _query_results):
            self.databases = DummyDatabases(_schema, _query_results)
            self.pages = DummyPages()
            self.search_results = _query_results or []
            self.last_search_kwargs = None

        async def search(self, **kwargs):
            self.last_search_kwargs = kwargs
            return {"results": self.search_results}

    def _factory(auth=None):  # noqa: ARG001
        client = DummyClient(schema, query_results)
        holder["client"] = client
        return client

    return _factory, holder


def build_default_config():
    return FakeConfig(
        {
            "notion": {
                "api_key": "test-key",
                "database_id": "db-id",
                "properties": {
                    "title": "콘텐츠",
                    "memo": "메모",
                    "status": "상태",
                    "date": "생성일",
                    "image_needed": "이미지 필요",
                    "tweet_body": "트윗 본문",
                    "url": "Source URL",
                    "tweet_url": "트윗 링크",
                    "views": "24h 조회수",
                    "likes": "24h 좋아요",
                    "retweets": "24h 리트윗",
                    "source": "원본 소스",
                    "feed_mode": "피드 모드",
                    "topic_cluster": "토픽 클러스터",
                    "hook_type": "훅 타입",
                    "emotion_axis": "감정 축",
                    "audience_fit": "대상 독자",
                    "scrape_quality_score": "스크랩 품질 점수",
                    "publishability_score": "발행 적합도 점수",
                    "performance_score": "성과 예측 점수",
                    "final_rank_score": "최종 랭크 점수",
                    "review_status": "승인 상태",
                    "review_note": "검토 메모",
                    "chosen_draft_type": "선택 초안 타입",
                    "newsletter_body": "뉴스레터 초안",
                    "publish_channel": "발행 채널",
                    "published_at": "발행 시각",
                    "performance_grade": "성과 등급",
                    "image_variant_id": "이미지 변형 ID",
                    "image_variant_type": "이미지 변형 타입",
                    "threads_body": "Threads 본문",
                    "blog_body": "블로그 본문",
                    "publish_platforms": "발행 플랫폼",
                    "threads_url": "Threads 링크",
                    "blog_url": "블로그 링크",
                    "publish_scheduled_at": "발행 예정일",
                    "regulation_status": "규제 검증",
                },
                "status_default": "검토필요",
            }
        }
    )


def test_canonicalize_url_rules():
    url = "http://Example.com/Post/?utm_source=x&utm_medium=y&b=2&a=1#frag"
    got = bs.NotionUploader.canonicalize_url(url)
    assert got == "https://example.com/Post?a=1&b=2"
    assert bs.NotionUploader.canonicalize_url("example.com/path/") == "https://example.com/path"
    assert bs.NotionUploader.canonicalize_url("https://example.com/path?ref=abc&x=1") == "https://example.com/path?x=1"


def test_auto_detect_schema_with_status_type(monkeypatch):
    schema = {
        "Name": {"type": "title"},
        "Summary": {"type": "rich_text"},
        "Draft": {"type": "rich_text"},
        "Status": {"type": "status"},
        "Created": {"type": "date"},
        "Image Required": {"type": "checkbox"},
        "Source URL": {"type": "url"},
    }
    factory, _holder = make_async_client(schema)
    monkeypatch.setattr(notion_mod, "AsyncClient", factory)

    uploader = bs.NotionUploader(build_default_config())
    ok = asyncio.run(uploader.ensure_schema())
    assert ok
    assert uploader.props["title"] in schema
    assert uploader.props["status"] in schema
    assert uploader.props["url"] in schema


def test_env_override_has_priority(monkeypatch):
    schema = {
        "콘텐츠": {"type": "title"},
        "메모": {"type": "rich_text"},
        "상태": {"type": "status"},
        "생성일": {"type": "date"},
        "이미지 필요": {"type": "checkbox"},
        "트윗 본문": {"type": "rich_text"},
        "URL_ENV": {"type": "url"},
    }
    monkeypatch.setenv("NOTION_PROP_URL", "URL_ENV")
    factory, _holder = make_async_client(schema)
    monkeypatch.setattr(notion_mod, "AsyncClient", factory)

    uploader = bs.NotionUploader(build_default_config())
    ok = asyncio.run(uploader.ensure_schema())
    assert ok
    assert uploader.props["url"] == "URL_ENV"


def test_exact_duplicate_check_uses_equals(monkeypatch):
    schema = {
        "콘텐츠": {"type": "title"},
        "메모": {"type": "rich_text"},
        "상태": {"type": "status"},
        "생성일": {"type": "date"},
        "이미지 필요": {"type": "checkbox"},
        "트윗 본문": {"type": "rich_text"},
        "Source URL": {"type": "url"},
    }
    # query_collection은 httpx를 직접 사용하므로 메서드 자체를 mock
    factory, _holder = make_async_client(schema)
    monkeypatch.setattr(notion_mod, "AsyncClient", factory)

    uploader = bs.NotionUploader(build_default_config())

    # 캐시 빌드용 query_collection mock: URL이 포함된 페이지 반환
    async def _mock_query(**_kwargs):
        return {"results": [{"properties": {"Source URL": {"url": "https://example.com/a"}}}]}

    async def _mock_cache_fail():
        return False

    monkeypatch.setattr(uploader, "_ensure_url_cache", _mock_cache_fail)
    monkeypatch.setattr(uploader, "query_collection", _mock_query)

    is_dup = asyncio.run(uploader.is_duplicate("http://example.com/a/?utm_source=x"))
    assert is_dup is True


def test_schema_missing_url_property_returns_error(monkeypatch):
    schema = {
        "콘텐츠": {"type": "title"},
        "메모": {"type": "rich_text"},
        "상태": {"type": "status"},
        "생성일": {"type": "date"},
        "이미지 필요": {"type": "checkbox"},
        "트윗 본문": {"type": "rich_text"},
    }
    factory, _holder = make_async_client(schema)
    monkeypatch.setattr(notion_mod, "AsyncClient", factory)

    uploader = bs.NotionUploader(build_default_config())
    ok = asyncio.run(uploader.ensure_schema())
    assert not ok
    assert uploader.last_error_code == bs.ERROR_NOTION_SCHEMA_MISMATCH


@pytest.mark.parametrize("status_type", ["status", "select"])
def test_upload_payload_supports_status_and_select(monkeypatch, status_type):
    schema = {
        "콘텐츠": {"type": "title"},
        "메모": {"type": "rich_text"},
        "상태": {"type": status_type},
        "생성일": {"type": "date"},
        "이미지 필요": {"type": "checkbox"},
        "트윗 본문": {"type": "rich_text"},
        "Source URL": {"type": "url"},
        "승인 상태": {"type": status_type},
        "토픽 클러스터": {"type": "select"},
        "훅 타입": {"type": "select"},
        "감정 축": {"type": "select"},
        "대상 독자": {"type": "select"},
        "스크랩 품질 점수": {"type": "number"},
        "발행 적합도 점수": {"type": "number"},
        "성과 예측 점수": {"type": "number"},
        "최종 랭크 점수": {"type": "number"},
        "선택 초안 타입": {"type": "select"},
    }
    factory, holder = make_async_client(schema)
    monkeypatch.setattr(notion_mod, "AsyncClient", factory)

    uploader = bs.NotionUploader(build_default_config())
    post_data = {
        "title": "제목",
        "url": "https://example.com/post?utm_source=a",
        "content": "본문",
        "review_status": "검토필요",
    }
    notion_result = asyncio.run(
        uploader.upload(
            post_data,
            "https://img",
            {"twitter": "draft body"},
            analysis={
                "topic_cluster": "연봉",
                "hook_type": "공감형",
                "emotion_axis": "공감",
                "audience_fit": "전직장인",
                "scrape_quality_score": 88,
                "publishability_score": 77,
                "performance_score": 66,
                "final_rank_score": 78,
                "recommended_draft_type": "공감형",
                "rationale": ["topic_cluster_detected"],
            },
        )
    )
    assert notion_result == ("https://notion.so/fake-page", "page-123")

    props = holder["client"].pages.last_create_kwargs["properties"]
    assert props["Source URL"]["url"] == "https://example.com/post"
    if status_type == "status":
        assert "status" in props["상태"]
        assert "status" in props["승인 상태"]
    else:
        assert "select" in props["상태"]
        assert "select" in props["승인 상태"]


def test_duplicate_query_error_returns_none_and_error_code(monkeypatch):
    schema = {
        "콘텐츠": {"type": "title"},
        "메모": {"type": "rich_text"},
        "상태": {"type": "status"},
        "생성일": {"type": "date"},
        "이미지 필요": {"type": "checkbox"},
        "트윗 본문": {"type": "rich_text"},
        "Source URL": {"type": "url"},
    }
    factory, _holder = make_async_client(schema)
    monkeypatch.setattr(notion_mod, "AsyncClient", factory)

    uploader = bs.NotionUploader(build_default_config())

    async def _mock_query(**_kwargs):
        raise ValueError("Network timeout")

    async def _mock_cache_fail():
        return False

    monkeypatch.setattr(uploader, "_ensure_url_cache", _mock_cache_fail)
    monkeypatch.setattr(uploader, "query_collection", _mock_query)

    is_dup = asyncio.run(uploader.is_duplicate("https://example.com/b"))
    assert is_dup is None
    assert uploader.last_error_code == bs.ERROR_NOTION_DUPLICATE_CHECK_FAILED
    assert "Network timeout" in uploader.last_error_message
