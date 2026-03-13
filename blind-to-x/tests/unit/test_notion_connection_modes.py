from __future__ import annotations

import asyncio
import sys
from pathlib import Path

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


def _build_config():
    return FakeConfig(
        {
            "notion": {
                "api_key": "test-key",
                "database_id": "7253f1ef341a4820a1800c56be697a6a",
                "properties": {
                    "title": "Name",
                    "memo": "Summary",
                    "status": "Status",
                    "date": "Created",
                    "image_needed": "Image Required",
                    "tweet_body": "Draft",
                    "url": "Source URL",
                },
                "status_default": "To Do",
            }
        }
    )


def test_normalize_notion_id_from_url():
    raw = "https://www.notion.so/workspace/7253f1ef341a4820a1800c56be697a6a?v=1234"
    assert bs.NotionUploader.normalize_notion_id(raw) == "7253f1ef-341a-4820-a180-0c56be697a6a"


def test_ensure_schema_falls_back_to_data_source(monkeypatch):
    schema = {
        "Name": {"type": "title"},
        "Summary": {"type": "rich_text"},
        "Status": {"type": "status"},
        "Created": {"type": "date"},
        "Image Required": {"type": "checkbox"},
        "Draft": {"type": "rich_text"},
        "Source URL": {"type": "url"},
    }

    class DummyDatabases:
        async def retrieve(self, database_id):  # noqa: ARG002
            raise RuntimeError("Could not find database with ID")

    class DummyDataSources:
        async def retrieve(self, data_source_id):  # noqa: ARG002
            return {"id": "ds-id", "object": "data_source", "properties": schema}

        async def query(self, **kwargs):  # noqa: ARG002
            return {"results": []}

    class DummyPages:
        async def create(self, **kwargs):  # noqa: ARG002
            return {"url": "https://notion.so/page"}

    class DummyClient:
        def __init__(self):
            self.databases = DummyDatabases()
            self.data_sources = DummyDataSources()
            self.pages = DummyPages()

        async def search(self, **kwargs):  # noqa: ARG002
            return {"results": []}

    monkeypatch.setattr(notion_mod, "AsyncClient", lambda auth=None: DummyClient())  # noqa: ARG005

    uploader = bs.NotionUploader(_build_config())
    ok = asyncio.run(uploader.ensure_schema())
    assert ok
    assert uploader.collection_kind == "data_source"


def test_duplicate_check_uses_data_source_query(monkeypatch):
    holder = {"query_kwargs": None}
    schema = {
        "Name": {"type": "title"},
        "Summary": {"type": "rich_text"},
        "Status": {"type": "status"},
        "Created": {"type": "date"},
        "Image Required": {"type": "checkbox"},
        "Draft": {"type": "rich_text"},
        "Source URL": {"type": "url"},
    }

    class DummyDatabases:
        async def retrieve(self, database_id):  # noqa: ARG002
            raise RuntimeError("Could not find database with ID")

    class DummyDataSources:
        async def retrieve(self, data_source_id):  # noqa: ARG002
            return {"id": "ds-id", "object": "data_source", "properties": schema}

    class DummyPages:
        async def create(self, **kwargs):  # noqa: ARG002
            return {"url": "https://notion.so/page"}

    class DummyClient:
        def __init__(self):
            self.databases = DummyDatabases()
            self.data_sources = DummyDataSources()
            self.pages = DummyPages()

        async def search(self, **kwargs):  # noqa: ARG002
            return {"results": []}

    monkeypatch.setattr(notion_mod, "AsyncClient", lambda auth=None: DummyClient())  # noqa: ARG005

    uploader = bs.NotionUploader(_build_config())

    # query_collection은 httpx를 직접 사용하므로 메서드 자체를 mock
    async def _mock_query(**kwargs):
        holder["query_kwargs"] = kwargs
        return {"results": [{"id": "dup", "properties": {"Source URL": {"url": "https://example.com/a"}}}]}

    async def _mock_cache_fail():
        return False

    monkeypatch.setattr(uploader, "_ensure_url_cache", _mock_cache_fail)
    monkeypatch.setattr(uploader, "query_collection", _mock_query)

    dup = asyncio.run(uploader.is_duplicate("https://example.com/a?utm_source=x"))
    assert dup is True
    # 캐시가 query_collection을 사용했는지 확인
    assert holder["query_kwargs"] is not None

