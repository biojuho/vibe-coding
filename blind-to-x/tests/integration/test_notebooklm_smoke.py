"""NotebookLM Enricher 통합 Smoke Test.

NOTEBOOKLM_ENABLED=true 환경에서 enrich_post_with_assets() 함수가
올바르게 동작하는지 검증합니다.

실제 LLM 호출은 mock으로 처리하여 비용 없이:
  - content_writer 모듈 경로 탐색 로직 검증
  - 모듈 로딩 성공 여부 확인
  - 반환 구조 (NotebookLMAssets 필드) 검증
  - NOTEBOOKLM_ENABLED=false 시 조기 반환 확인
"""

from __future__ import annotations

import asyncio
import pathlib
import sys
from unittest.mock import MagicMock, patch

import pytest

# blind-to-x 루트 경로 등록
_PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from pipeline.notebooklm_enricher import NotebookLMAssets, enrich_post_with_assets  # noqa: E402

# content_writer.py 경로
_CONTENT_WRITER = _PROJECT_ROOT / "execution" / "content_writer.py"


# ── 헬퍼 ─────────────────────────────────────────────────────────────────


def _run(coro):
    """새 이벤트 루프로 코루틴 실행 (Python 3.10+ 호환)."""
    return asyncio.run(coro)


# ── 테스트 케이스 ─────────────────────────────────────────────────────────


class TestNotebookLMDisabled:
    """NOTEBOOKLM_ENABLED=false 시 조기 반환."""

    def test_returns_empty_assets_when_disabled(self, monkeypatch):
        monkeypatch.setenv("NOTEBOOKLM_ENABLED", "false")

        assets = _run(enrich_post_with_assets("번아웃 극복"))

        assert isinstance(assets, NotebookLMAssets)
        assert assets.topic == "번아웃 극복"
        assert not assets.has_assets
        assert assets.article == ""
        assert assets.errors == []


class TestNotebookLMContentWriterPath:
    """content_writer.py 경로 탐색 검증."""

    def test_content_writer_path_constant(self):
        """_CONTENT_WRITER_PATH 상수가 execution/ 폴더를 가리키는지 확인."""
        from pipeline.notebooklm_enricher import _CONTENT_WRITER_PATH

        assert "execution" in str(_CONTENT_WRITER_PATH).lower()
        assert _CONTENT_WRITER_PATH.name == "content_writer.py"

    def test_content_writer_file_info(self):
        """content_writer.py 파일 경로 정보 출력."""
        if not _CONTENT_WRITER.exists():
            pytest.skip(
                f"content_writer.py 없음: {_CONTENT_WRITER}  "
                "execution/ 폴더에 content_writer.py를 생성하세요."
            )
        assert _CONTENT_WRITER.is_file()


class TestNotebookLMTopicMode:
    """NOTEBOOKLM_ENABLED=true, NOTEBOOKLM_MODE=topic 실행 검증."""

    def test_topic_mode_returns_assets_structure(self, monkeypatch):
        """topic 모드에서 NotebookLMAssets 반환 구조 확인 (LLM mock)."""
        monkeypatch.setenv("NOTEBOOKLM_ENABLED", "true")
        monkeypatch.setenv("NOTEBOOKLM_MODE", "topic")
        monkeypatch.setenv("NOTEBOOKLM_TIMEOUT", "10")

        # content_writer 모듈의 write_article 함수를 mock
        mock_cw = MagicMock()
        mock_cw.write_article.return_value = {
            "title": "번아웃 극복법 완벽 가이드",
            "content": "# 번아웃 극복\n\n직장인 번아웃을 극복하는 실용적인 방법 5가지를 소개합니다.",
            "provider": "mock",
        }

        with patch("pipeline.notebooklm_enricher._load_module", return_value=mock_cw):
            assets = _run(enrich_post_with_assets("번아웃 극복"))

        assert isinstance(assets, NotebookLMAssets)
        assert assets.topic == "번아웃 극복"
        assert isinstance(assets.elapsed_sec, float)
        assert assets.elapsed_sec >= 0

    def test_topic_mode_no_content_writer_graceful(self, monkeypatch):
        """content_writer 없을 때 예외 없이 빈 assets 반환."""
        monkeypatch.setenv("NOTEBOOKLM_ENABLED", "true")
        monkeypatch.setenv("NOTEBOOKLM_MODE", "topic")
        monkeypatch.setenv("NOTEBOOKLM_TIMEOUT", "5")

        with patch("pipeline.notebooklm_enricher._load_module", return_value=None):
            assets = _run(enrich_post_with_assets("직장 내 갈등"))

        assert isinstance(assets, NotebookLMAssets)
        assert not assets.has_assets  # 아티클 없음

    def test_assets_has_assets_property(self):
        """has_assets 속성이 올바르게 동작하는지 확인."""
        empty_assets = NotebookLMAssets(topic="테스트")
        assert not empty_assets.has_assets

        article_assets = NotebookLMAssets(topic="테스트", article="# 본문")
        assert article_assets.has_assets

        infographic_assets = NotebookLMAssets(
            topic="테스트", infographic_url="https://example.com/img.png"
        )
        assert infographic_assets.has_assets


class TestNotebookLMTimeout:
    """타임아웃 처리 검증."""

    def test_timeout_returns_assets_with_error(self, monkeypatch):
        """타임아웃 발생 시 예외 없이 error 목록에 추가."""
        monkeypatch.setenv("NOTEBOOKLM_ENABLED", "true")
        monkeypatch.setenv("NOTEBOOKLM_MODE", "topic")
        monkeypatch.setenv("NOTEBOOKLM_TIMEOUT", "1")  # 1초 타임아웃

        async def _slow_enricher(topic, assets):
            await asyncio.sleep(5)
            return assets

        with patch("pipeline.notebooklm_enricher._run_enricher", side_effect=_slow_enricher):
            assets = _run(enrich_post_with_assets("슬로우 테스트"))

        assert isinstance(assets, NotebookLMAssets)
        assert any("타임아웃" in e for e in assets.errors), f"타임아웃 에러 없음: {assets.errors}"
        assert not assets.has_assets


class TestEnvVariableVariants:
    """NOTEBOOKLM_ENABLED 다양한 값 처리."""

    @pytest.mark.parametrize("value", ["true", "True", "TRUE", "1", "yes"])
    def test_enabled_values(self, monkeypatch, value):
        """활성화 값들이 모두 올바르게 처리되는지 확인."""
        monkeypatch.setenv("NOTEBOOKLM_ENABLED", value)
        monkeypatch.setenv("NOTEBOOKLM_TIMEOUT", "2")

        async def _instant_enricher(topic, assets):
            return assets

        with patch("pipeline.notebooklm_enricher._run_enricher", side_effect=_instant_enricher) as mock_run:
            _run(enrich_post_with_assets("test"))

        mock_run.assert_called_once()

    @pytest.mark.parametrize("value", ["false", "False", "0", "no", ""])
    def test_disabled_values(self, monkeypatch, value):
        """비활성화 값들이 모두 올바르게 스킵되는지 확인."""
        monkeypatch.setenv("NOTEBOOKLM_ENABLED", value)

        with patch("pipeline.notebooklm_enricher._run_enricher") as mock_run:
            assets = _run(enrich_post_with_assets("test"))

        mock_run.assert_not_called()
        assert not assets.has_assets
