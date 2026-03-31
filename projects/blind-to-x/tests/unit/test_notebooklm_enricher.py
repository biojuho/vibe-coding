"""Tests for pipeline.notebooklm_enricher."""

import pytest
import asyncio
import os
from unittest.mock import MagicMock, patch

from pipeline.notebooklm_enricher import (
    enrich_post_with_assets,
    NotebookLMAssets,
    _load_module,
    _run_enricher,
    _gdrive_extract,
    _write_article,
)

@pytest.fixture(autouse=True)
def clean_env():
    # Remove env vars to have clean state
    for k in ["NOTEBOOKLM_ENABLED", "NOTEBOOKLM_MODE", "NOTEBOOKLM_TIMEOUT", "GOOGLE_DRIVE_FOLDER_ID", "NOTEBOOKLM_CONTENT_PROJECT"]:
        if k in os.environ:
            del os.environ[k]
    yield

@pytest.mark.asyncio
async def test_enrich_disabled():
    # disabled by default
    res = await enrich_post_with_assets("topic")
    assert not res.has_assets
    assert len(res.errors) == 0

@pytest.mark.asyncio
@patch.dict(os.environ, {"NOTEBOOKLM_ENABLED": "true", "NOTEBOOKLM_TIMEOUT": "1"})
async def test_enrich_timeout():
    async def slow_enricher(*args, **kwargs):
        await asyncio.sleep(2.0)
        return NotebookLMAssets("t")

    with patch("pipeline.notebooklm_enricher._run_enricher", side_effect=slow_enricher):
        res = await enrich_post_with_assets("topic", timeout=1)
        assert not res.has_assets
        assert any("타임아웃" in e for e in res.errors)

@pytest.mark.asyncio
@patch.dict(os.environ, {"NOTEBOOKLM_ENABLED": "true"})
async def test_enrich_exception():
    async def fail_enricher(*args, **kwargs):
        raise ValueError("Intentional crash")

    with patch("pipeline.notebooklm_enricher._run_enricher", side_effect=fail_enricher):
        res = await enrich_post_with_assets("topic")
        assert not res.has_assets
        assert any("Intentional crash" in e for e in res.errors)

@pytest.mark.asyncio
@patch.dict(os.environ, {"NOTEBOOKLM_ENABLED": "true"})
async def test_enrich_success():
    async def mock_enricher(topic, assets):
        assets.article = "Here is the article"
        assets.ai_provider = "gemini"
        return assets

    with patch("pipeline.notebooklm_enricher._run_enricher", side_effect=mock_enricher):
        res = await enrich_post_with_assets("topic")
        assert res.has_assets
        assert res.article == "Here is the article"

@pytest.mark.asyncio
@patch.dict(os.environ, {"NOTEBOOKLM_ENABLED": "true", "NOTEBOOKLM_MODE": "topic"})
async def test_run_enricher_topic_mode():
    assets = NotebookLMAssets("test_topic")

    with patch("pipeline.notebooklm_enricher._write_article") as mock_write:
        def fake_write(a, t):
            a.article = "written"
            return a
        mock_write.side_effect = fake_write

        res = await _run_enricher("test_topic", assets)
        assert res.source_text.startswith("주제: test_topic")
        assert res.article == "written"

@pytest.mark.asyncio
@patch.dict(os.environ, {"NOTEBOOKLM_ENABLED": "true", "NOTEBOOKLM_MODE": "gdrive"})
async def test_run_enricher_gdrive_fallback():
    assets = NotebookLMAssets("test_topic")

    with patch("pipeline.notebooklm_enricher._gdrive_extract") as mock_extract, \
         patch("pipeline.notebooklm_enricher._write_article") as mock_write:

        # gdrive fails
        def fake_extract(a):
            a.errors.append("gdrive failed")
            return a
        mock_extract.side_effect = fake_extract

        def fake_write(a, t):
            a.article = "written"
            return a
        mock_write.side_effect = fake_write

        res = await _run_enricher("test_topic", assets)
        # Should fallback to topic mode
        assert res.source_text.startswith("주제: test_topic")
        assert res.article == "written"

@patch.dict(os.environ, {"GOOGLE_DRIVE_FOLDER_ID": "f123"})
def test_gdrive_extract_success():
    a = NotebookLMAssets("test")

    mock_mod = MagicMock()
    mock_mod.list_new_files_since.return_value = [{"id": "1", "name": "doc.pdf"}]
    mock_mod.download_and_extract.return_value = {"text": "pdf content", "drive_url": "http://"}

    with patch("pipeline.notebooklm_enricher._load_module", return_value=mock_mod):
        res = _gdrive_extract(a)
        assert res.source_text == "pdf content"
        assert res.drive_url == "http://"

def test_load_module_not_exists():
    path_mock = MagicMock()
    path_mock.exists.return_value = False
    assert _load_module("name", path_mock) is None

def test_write_article_success():
    a = NotebookLMAssets("test")
    a.source_text = "abc"

    mock_mod = MagicMock()
    mock_mod.write_article.return_value = {"article": "final content", "title": "my title", "provider": "openai"}

    with patch("pipeline.notebooklm_enricher._load_module", return_value=mock_mod):
        res = _write_article(a, "test")
        assert res.article == "final content"
        assert res.article_title == "my title"
        assert res.ai_provider == "openai"
        assert len(res.errors) == 0

def test_write_article_no_module():
    a = NotebookLMAssets("test")
    with patch("pipeline.notebooklm_enricher._load_module", return_value=None):
        res = _write_article(a, "test")
        assert "content_writer 모듈 없음" in res.errors
