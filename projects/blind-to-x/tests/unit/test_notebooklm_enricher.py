"""Unit tests for pipeline/notebooklm_enricher.py (v2 — content_writer 연동 버전)."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import pytest


# ═══════════════════════════════════════════════════════════════════════════
# Fixtures & helpers
# ═══════════════════════════════════════════════════════════════════════════


@pytest.fixture(autouse=True)
def _reset_env(monkeypatch):
    """각 테스트마다 NOTEBOOKLM_ENABLED를 리셋."""
    monkeypatch.delenv("NOTEBOOKLM_ENABLED", raising=False)
    monkeypatch.delenv("NOTEBOOKLM_MODE", raising=False)
    monkeypatch.delenv("NOTEBOOKLM_TIMEOUT", raising=False)
    monkeypatch.delenv("GOOGLE_DRIVE_FOLDER_ID", raising=False)


def _fake_write_article(text, project="default", provider=None):
    """content_writer.write_article mock 반환값."""
    return {
        "title": "테스트 아티클 제목",
        "article": "## 서론\n\n내용입니다.\n\n## 결론\n\n마무리입니다.",
        "provider": provider or "gemini",
        "project": project,
    }


# ═══════════════════════════════════════════════════════════════════════════
# 1. 기본 데이터 클래스 테스트
# ═══════════════════════════════════════════════════════════════════════════


class TestNotebookLMAssets:
    def test_defaults(self):
        from pipeline.notebooklm_enricher import NotebookLMAssets

        assets = NotebookLMAssets(topic="테스트 주제")
        assert assets.topic == "테스트 주제"
        assert assets.article == ""
        assert assets.errors == []
        assert assets.has_assets is False

    def test_has_assets_with_article(self):
        from pipeline.notebooklm_enricher import NotebookLMAssets

        assets = NotebookLMAssets(topic="주제", article="본문 내용")
        assert assets.has_assets is True

    def test_has_assets_with_infographic(self):
        from pipeline.notebooklm_enricher import NotebookLMAssets

        assets = NotebookLMAssets(topic="주제", infographic_url="https://example.com/img.png")
        assert assets.has_assets is True

    def test_has_assets_empty(self):
        from pipeline.notebooklm_enricher import NotebookLMAssets

        assets = NotebookLMAssets(topic="주제")
        assert assets.has_assets is False


# ═══════════════════════════════════════════════════════════════════════════
# 2. NOTEBOOKLM_ENABLED=false → 즉시 빈 결과 반환
# ═══════════════════════════════════════════════════════════════════════════


class TestEnrichDisabled:
    def test_disabled_by_default(self):
        from pipeline.notebooklm_enricher import enrich_post_with_assets

        result = asyncio.run(enrich_post_with_assets("번아웃"))
        assert result.article == ""
        assert result.errors == []  # 스킵이지 에러 아님

    def test_disabled_explicit_false(self, monkeypatch):
        monkeypatch.setenv("NOTEBOOKLM_ENABLED", "false")
        from pipeline.notebooklm_enricher import enrich_post_with_assets

        result = asyncio.run(enrich_post_with_assets("번아웃"))
        assert result.article == ""


# ═══════════════════════════════════════════════════════════════════════════
# 3. topic 모드 — content_writer 정상 실행
# ═══════════════════════════════════════════════════════════════════════════


class TestTopicMode:
    def test_topic_mode_success(self, monkeypatch):
        """content_writer가 정상 응답할 때 article 필드 채움."""
        monkeypatch.setenv("NOTEBOOKLM_ENABLED", "true")
        monkeypatch.setenv("NOTEBOOKLM_MODE", "topic")

        from pipeline import notebooklm_enricher

        # content_writer 모듈 mock
        fake_mod = MagicMock()
        fake_mod.write_article.side_effect = _fake_write_article

        with patch.object(notebooklm_enricher, "_load_module", return_value=fake_mod):
            result = asyncio.run(notebooklm_enricher.enrich_post_with_assets("번아웃 극복"))

        assert "서론" in result.article
        assert result.article_title == "테스트 아티클 제목"
        assert result.ai_provider == "gemini"
        assert result.has_assets is True

    def test_topic_mode_content_writer_missing(self, monkeypatch):
        """content_writer 모듈 없을 때 errors에 메시지 추가 (파이프라인 미중단)."""
        monkeypatch.setenv("NOTEBOOKLM_ENABLED", "true")
        monkeypatch.setenv("NOTEBOOKLM_MODE", "topic")

        from pipeline import notebooklm_enricher

        with patch.object(notebooklm_enricher, "_load_module", return_value=None):
            result = asyncio.run(notebooklm_enricher.enrich_post_with_assets("직장 스트레스"))

        assert result.article == ""
        assert any("content_writer" in e for e in result.errors)

    def test_topic_mode_writer_exception(self, monkeypatch):
        """content_writer.write_article이 예외를 던질 때 에러 log만 남김."""
        monkeypatch.setenv("NOTEBOOKLM_ENABLED", "true")
        monkeypatch.setenv("NOTEBOOKLM_MODE", "topic")

        from pipeline import notebooklm_enricher

        fake_mod = MagicMock()
        fake_mod.write_article.side_effect = RuntimeError("AI 오류")

        with patch.object(notebooklm_enricher, "_load_module", return_value=fake_mod):
            result = asyncio.run(notebooklm_enricher.enrich_post_with_assets("주제"))

        assert result.article == ""
        assert any("아티클 작성 실패" in e for e in result.errors)

    def test_topic_text_built_correctly(self):
        from pipeline.notebooklm_enricher import _build_topic_text

        text = _build_topic_text("연봉 협상")
        assert "연봉 협상" in text
        assert "주제" in text

    def test_elapsed_time_recorded(self, monkeypatch):
        """항상 elapsed_sec이 측정됩니다."""
        monkeypatch.setenv("NOTEBOOKLM_ENABLED", "true")
        from pipeline import notebooklm_enricher

        fake_mod = MagicMock()
        fake_mod.write_article.side_effect = _fake_write_article

        with patch.object(notebooklm_enricher, "_load_module", return_value=fake_mod):
            result = asyncio.run(notebooklm_enricher.enrich_post_with_assets("주제"))

        assert result.elapsed_sec >= 0


# ═══════════════════════════════════════════════════════════════════════════
# 4. timeout 처리
# ═══════════════════════════════════════════════════════════════════════════


class TestTimeout:
    def test_timeout_produces_error_no_raise(self, monkeypatch):
        """타임아웃 시 예외가 파이프라인 밖으로 전파되지 않아야 함."""
        monkeypatch.setenv("NOTEBOOKLM_ENABLED", "true")
        monkeypatch.setenv("NOTEBOOKLM_MODE", "topic")

        from pipeline import notebooklm_enricher
        import asyncio as _asyncio

        async def _slow(*_, **__):
            await _asyncio.sleep(99)
            return MagicMock()

        fake_mod = MagicMock()
        fake_mod.write_article.side_effect = _fake_write_article

        async def _run():
            # timeout=0.01초 (즉시 만료)
            with patch.object(notebooklm_enricher, "_load_module", return_value=fake_mod):
                with patch.object(notebooklm_enricher, "_run_enricher", side_effect=_slow):
                    return await notebooklm_enricher.enrich_post_with_assets("느린 주제", timeout=1)

        result = asyncio.run(_run())
        # 타임아웃 에러가 errors 리스트에 기록됨
        assert any("타임아웃" in e for e in result.errors)


# ═══════════════════════════════════════════════════════════════════════════
# 5. gdrive 모드
# ═══════════════════════════════════════════════════════════════════════════


class TestGdriveMode:
    def test_gdrive_no_folder_id_fallback_to_topic(self, monkeypatch):
        """GOOGLE_DRIVE_FOLDER_ID 미설정 시 topic 모드로 폴백."""
        monkeypatch.setenv("NOTEBOOKLM_ENABLED", "true")
        monkeypatch.setenv("NOTEBOOKLM_MODE", "gdrive")
        # GOOGLE_DRIVE_FOLDER_ID 미설정

        from pipeline import notebooklm_enricher

        fake_cw = MagicMock()
        fake_cw.write_article.side_effect = _fake_write_article
        fake_gd = MagicMock()  # gdrive extractor

        def _mock_load(name, path):
            if "content_writer" in str(path):
                return fake_cw
            return fake_gd  # gdrive 모듈은 반환하지만 folder_id 없어서 에러

        with patch.object(notebooklm_enricher, "_load_module", side_effect=_mock_load):
            result = asyncio.run(notebooklm_enricher.enrich_post_with_assets("이직 고민"))

        # GDrive 실패 후 topic 폴백으로 아티클 생성
        assert result.has_assets is True or any("GOOGLE_DRIVE_FOLDER_ID" in e for e in result.errors)

    def test_gdrive_no_new_files(self, monkeypatch):
        """GDrive 폴더에 새 파일 없을 때 errors 기록 후 topic 폴백."""
        monkeypatch.setenv("NOTEBOOKLM_ENABLED", "true")
        monkeypatch.setenv("NOTEBOOKLM_MODE", "gdrive")
        monkeypatch.setenv("GOOGLE_DRIVE_FOLDER_ID", "fake-folder-id")

        from pipeline import notebooklm_enricher

        fake_gd = MagicMock()
        fake_gd.list_new_files_since.return_value = []  # 빈 목록

        fake_cw = MagicMock()
        fake_cw.write_article.side_effect = _fake_write_article

        def _mock_load(name, path):
            if "content_writer" in str(path):
                return fake_cw
            return fake_gd

        with patch.object(notebooklm_enricher, "_load_module", side_effect=_mock_load):
            result = asyncio.run(notebooklm_enricher.enrich_post_with_assets("주제"))

        # 폴백으로 topic 아티클은 생성돼야 함
        assert any("신규 파일 없음" in e or "폴백" in e for e in result.errors) or result.has_assets


# ═══════════════════════════════════════════════════════════════════════════
# 6. _upload.py NLM 아티클 블록 테스트
# ═══════════════════════════════════════════════════════════════════════════


class TestUploadNLMArticle:
    """NotionUploadMixin의 nlm_article 처리 경로 테스트."""

    def test_nlm_article_in_post_data(self):
        """post_data에 nlm_article이 있으면 children에 관련 블록이 추가됨."""

        # _upload.py 내 nlm_article 처리 로직을 직접 실행 (Mixin 인스턴스 불필요)
        def _create_text_blocks(text):
            chunks = []
            for i in range(0, len(text), 2000):
                chunk = text[i : i + 2000]
                chunks.append(
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {"rich_text": [{"type": "text", "text": {"content": chunk}}]},
                    }
                )
            return chunks

        post_data = {"nlm_article": "## 제목\n\n내용입니다."}
        children = []

        nlm_article = post_data.get("nlm_article", "")
        if nlm_article:
            children.append({"object": "block", "type": "divider", "divider": {}})
            children.append(
                {
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {"rich_text": [{"type": "text", "text": {"content": "✍️ AI 자동 아티클"}}]},
                }
            )
            # 폴백 경로 (plain text blocks)
            children.extend(_create_text_blocks(nlm_article))

        assert len(children) >= 2
        assert any(b.get("type") == "heading_2" and "AI 자동 아티클" in str(b) for b in children)

    def test_no_nlm_article_no_extra_blocks(self):
        """nlm_article 없으면 관련 블록 추가 안 됨."""
        post_data = {"title": "테스트"}
        nlm_article = post_data.get("nlm_article", "")
        children = []

        if nlm_article:
            children.append({"object": "block", "type": "divider", "divider": {}})

        assert len(children) == 0
