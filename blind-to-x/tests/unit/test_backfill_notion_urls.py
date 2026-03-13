from __future__ import annotations

import asyncio
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import backfill_notion_urls as bf  # noqa: E402


def _make_page(page_id: str, url_value: str = "", memo_text: str = ""):
    return {
        "id": page_id,
        "properties": {
            "Source URL": {"url": url_value or None},
            "Memo": {"rich_text": [{"plain_text": memo_text}]},
        },
    }


def _install_dummy_dependencies(monkeypatch, pages, *, fail_times=0, always_fail=False):
    holder = {"query_calls": [], "update_calls": []}
    canonicalize = bf.NotionUploader.canonicalize_url

    class DummyConfigManager:
        def __init__(self, _config_path):
            self.config = {}

    class DummyDatabases:
        async def query(self, **kwargs):
            holder["query_calls"].append(kwargs)
            return {"results": pages, "has_more": False, "next_cursor": None}

    class DummyPages:
        def __init__(self):
            self.remaining_failures = fail_times

        async def update(self, page_id, properties):
            holder["update_calls"].append({"page_id": page_id, "properties": properties})
            if self.remaining_failures > 0:
                self.remaining_failures -= 1
                raise RuntimeError("temporary update failure")
            if always_fail:
                raise RuntimeError("permanent update failure")
            return {"id": page_id}

    class DummyClient:
        def __init__(self):
            self.databases = DummyDatabases()
            self.pages = DummyPages()

    class DummyNotionUploader:
        canonicalize_url = staticmethod(canonicalize)

        def __init__(self, _config):
            self.client = DummyClient()
            self.database_id = "db-id"
            self.props = {"url": "Source URL", "memo": "Memo"}
            self._db_properties = {"Source URL": {"type": "url"}}
            self.last_error_code = None
            self.last_error_message = None

        async def ensure_schema(self):
            return True

    monkeypatch.setattr(bf, "ConfigManager", DummyConfigManager)
    monkeypatch.setattr(bf, "NotionUploader", DummyNotionUploader)
    return holder


def test_backfill_retries_then_succeeds(monkeypatch, tmp_path):
    pages = [_make_page("page-1", memo_text="source: https://example.com/a?utm_source=x")]
    holder = _install_dummy_dependencies(monkeypatch, pages, fail_times=1, always_fail=False)
    failed_output = tmp_path / "failed.csv"

    rc = asyncio.run(
        bf.run_backfill(
            config_path="config.yaml",
            page_size=50,
            limit=0,
            apply=True,
            max_retries=3,
            backoff_seconds=0.0,
            failed_output=str(failed_output),
        )
    )

    assert rc == 0
    assert len(holder["update_calls"]) == 2
    assert not failed_output.exists()


def test_backfill_retry_exhaustion_writes_failed_csv(monkeypatch, tmp_path):
    pages = [_make_page("page-2", memo_text="https://example.com/b?utm_source=x")]
    holder = _install_dummy_dependencies(monkeypatch, pages, fail_times=0, always_fail=True)
    failed_output = tmp_path / "failed.csv"

    rc = asyncio.run(
        bf.run_backfill(
            config_path="config.yaml",
            page_size=50,
            limit=0,
            apply=True,
            max_retries=2,
            backoff_seconds=0.0,
            failed_output=str(failed_output),
        )
    )

    assert rc == 1
    assert len(holder["update_calls"]) == 2
    assert failed_output.exists()
    rows = list(csv.DictReader(failed_output.read_text(encoding="utf-8").splitlines()))
    assert len(rows) == 1
    assert rows[0]["page_id"] == "page-2"
    assert rows[0]["source_url"].startswith("https://example.com/b")


def test_backfill_start_cursor_is_used(monkeypatch, tmp_path):
    pages = [_make_page("page-3", memo_text="https://example.com/c")]
    holder = _install_dummy_dependencies(monkeypatch, pages, fail_times=0, always_fail=False)

    rc = asyncio.run(
        bf.run_backfill(
            config_path="config.yaml",
            page_size=25,
            limit=1,
            apply=False,
            start_cursor="cursor-123",
            failed_output=str(tmp_path / "unused.csv"),
        )
    )

    assert rc == 0
    assert holder["query_calls"][0]["start_cursor"] == "cursor-123"
    assert holder["query_calls"][0]["page_size"] == 25
