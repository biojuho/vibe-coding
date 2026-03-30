from __future__ import annotations

import json
import sys
import time
from types import ModuleType

import execution.notion_article_uploader as uploader


def test_markdown_to_notion_blocks_handles_common_syntax() -> None:
    markdown = "# Title\n## Subtitle\n### Detail\n- bullet\n1. numbered\n---\nplain **bold** text\n"

    blocks = uploader.markdown_to_notion_blocks(markdown)

    block_types = [block["type"] for block in blocks]
    assert block_types[:6] == [
        "heading_2",
        "heading_2",
        "heading_3",
        "bulleted_list_item",
        "numbered_list_item",
        "divider",
    ]
    paragraph_blocks = [block for block in blocks if block["type"] == "paragraph" and block["paragraph"]["rich_text"]]
    rich_text = paragraph_blocks[-1]["paragraph"]["rich_text"]
    assert any(part.get("annotations", {}).get("bold") for part in rich_text)


def test_chunk_blocks_splits_at_hundred() -> None:
    blocks = [{"type": "paragraph"}] * 205

    chunks = uploader._chunk_blocks(blocks, size=100)

    assert [len(chunk) for chunk in chunks] == [100, 100, 5]


def test_notion_client_post_retries_after_rate_limit(monkeypatch) -> None:
    calls = {"count": 0}
    fake_httpx = ModuleType("httpx")

    class FakeResponse:
        def __init__(self, status_code: int, payload: dict, headers: dict | None = None) -> None:
            self.status_code = status_code
            self._payload = payload
            self.headers = headers or {}

        def raise_for_status(self) -> None:
            if self.status_code >= 400 and self.status_code != 429:
                raise RuntimeError("http error")

        def json(self) -> dict:
            return self._payload

    def fake_post(url, headers, json, timeout):
        calls["count"] += 1
        if calls["count"] == 1:
            return FakeResponse(429, {}, {"Retry-After": "0"})
        return FakeResponse(200, {"ok": True})

    def fake_patch(url, headers, json, timeout):
        return FakeResponse(200, {"patched": True})

    fake_httpx.post = fake_post
    fake_httpx.patch = fake_patch
    monkeypatch.setitem(sys.modules, "httpx", fake_httpx)
    monkeypatch.setattr(time, "sleep", lambda *_args, **_kwargs: None)

    client = uploader.NotionClient(api_key="secret")

    assert client.post("/pages", {"hello": "world"}) == {"ok": True}
    assert client.patch("/blocks/x/children", {"children": []}) == {"patched": True}
    assert calls["count"] == 2


def test_create_article_page_creates_page_and_chunks_children(monkeypatch) -> None:
    post_calls: list[tuple[str, dict]] = []
    patch_calls: list[tuple[str, dict]] = []

    class FakeClient:
        def __init__(self, api_key=None) -> None:
            self.api_key = api_key

        def post(self, path: str, body: dict, *, max_retries: int = 3) -> dict:
            post_calls.append((path, body))
            return {"id": "page-123", "url": "https://notion/page-123"}

        def patch(self, path: str, body: dict) -> dict:
            patch_calls.append((path, body))
            return {"ok": True}

    monkeypatch.setattr(uploader, "NotionClient", FakeClient)
    monkeypatch.setenv("NOTEBOOKLM_NOTION_DB_ID", "abc-def")
    monkeypatch.setattr(time, "sleep", lambda *_args, **_kwargs: None)

    article = "\n".join(f"Paragraph {i}" for i in range(120))
    result = uploader.create_article_page(
        title="NotebookLM article",
        article=article,
        project="demo",
        ai_provider="gemini",
        drive_url="https://drive.example/file",
        tags=["ai", "ops"],
    )

    assert result["status"] == "created"
    assert post_calls[0][0] == "/pages"
    assert post_calls[0][1]["parent"]["database_id"] == "abcdef"
    assert len(patch_calls) == 2
    assert sum(len(call[1]["children"]) for call in patch_calls) == 120


def test_main_reads_article_file_and_prints_result(tmp_path, monkeypatch, capsys) -> None:
    article_file = tmp_path / "article.json"
    article_file.write_text(
        json.dumps(
            {
                "title": "Loaded title",
                "article": "# Heading\nBody",
                "provider": "gpt",
                "project": "demo",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        uploader,
        "create_article_page",
        lambda **kwargs: {
            "page_id": "page-1",
            "page_url": "https://notion/page-1",
            "title": kwargs["title"],
            "status": "created",
        },
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["notion_article_uploader.py", "upload", "--article-file", str(article_file)],
    )

    uploader.main()

    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "created"
    assert payload["title"] == "Loaded title"
