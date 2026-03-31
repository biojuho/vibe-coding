"""NotebookLM 파이프라인 — 콘텐츠 자동 작성 모듈 v2.

Blind-to-X 파이프라인에서 포스트 주제 또는 Google Drive 새 파일을 기반으로
AI 아티클을 자동 생성하고 Notion에 삽입할 준비를 합니다.

동작 모드 (NOTEBOOKLM_MODE):
    topic  [기본] — post_data의 topic_cluster / 제목을 텍스트로 content_writer에 전달
    gdrive — Google Drive 폴더에서 새 PDF/이미지 감지 → 텍스트 추출 → content_writer

환경 변수:
    NOTEBOOKLM_ENABLED=true           기능 활성화 (기본: false)
    NOTEBOOKLM_MODE=topic|gdrive      동작 모드 (기본: topic)
    NOTEBOOKLM_TIMEOUT=120            타임아웃 초 (기본: 120)
    GOOGLE_DRIVE_FOLDER_ID            GDrive 모니터링 폴더 ID (gdrive 모드 필수)
    GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON 서비스 계정 키 경로 (gdrive 모드)
    CONTENT_WRITER_AI_MODEL           AI 모델 선택 (기본: gemini)
"""

from __future__ import annotations

import asyncio
import importlib.util
import logging
import os
import pathlib
import time
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# ── 공유 스크립트 경로 (root execution/ 폴더) ──────────────────────────────
_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
_CONTENT_WRITER_PATH = _ROOT / "execution" / "content_writer.py"
_GDRIVE_EXTRACTOR_PATH = _ROOT / "execution" / "gdrive_pdf_extractor.py"


def _load_module(name: str, path: pathlib.Path):
    """Python 파일을 동적으로 모듈로 로드합니다."""
    if not path.exists():
        logger.warning("[NLM Enricher] 모듈 없음: %s", path)
        return None
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
        return mod
    except Exception as exc:
        logger.warning("[NLM Enricher] %s 로드 실패: %s", name, exc)
        return None


# ── 데이터 클래스 ─────────────────────────────────────────────────────────


@dataclass
class NotebookLMAssets:
    """NotebookLM Enricher가 생성한 자산 컨테이너."""

    topic: str
    notebook_id: str = ""  # 하위 호환성 유지 (이전 버전 필드)
    infographic_url: str = ""  # (현재 미사용, 하위 호환)
    infographic_local: str = ""  # (현재 미사용, 하위 호환)
    slides_local: str = ""  # (현재 미사용, 하위 호환)
    mind_map_local: str = ""  # (현재 미사용, 하위 호환)
    article: str = ""  # AI 자동 생성 아티클 (Markdown)
    article_title: str = ""  # 아티클 제목
    ai_provider: str = ""  # 사용한 AI 제공자
    source_text: str = ""  # 기반 텍스트 (topic 요약 or PDF 추출 텍스트)
    drive_url: str = ""  # GDrive 원본 파일 URL
    elapsed_sec: float = 0.0
    errors: list[str] = field(default_factory=list)

    @property
    def has_assets(self) -> bool:
        return bool(self.article or self.infographic_url or self.infographic_local)


# ── 메인 enricher 함수 ────────────────────────────────────────────────────


async def enrich_post_with_assets(
    topic: str,
    *,
    image_uploader=None,  # 하위 호환용 (현재 미사용)
    timeout: int | None = None,
) -> NotebookLMAssets:
    """포스트 주제 또는 GDrive 파일로 NotebookLM 자산을 자동 생성합니다.

    Args:
        topic: 리서치할 주제 (포스트 제목 또는 topic_cluster)
        image_uploader: 하위 호환용 인자 (현재 버전에서는 미사용)
        timeout: 최대 대기 시간 (초). None이면 NOTEBOOKLM_TIMEOUT 환경 변수

    Returns:
        NotebookLMAssets — 실패해도 예외 미전파 (파이프라인 안전)
    """
    start = time.monotonic()
    assets = NotebookLMAssets(topic=topic)

    # 기능 비활성화 체크
    if os.environ.get("NOTEBOOKLM_ENABLED", "false").lower() not in {"true", "1", "yes"}:
        logger.debug("[NLM Enricher] NOTEBOOKLM_ENABLED 미설정 — 스킵")
        return assets

    _timeout = timeout or int(os.environ.get("NOTEBOOKLM_TIMEOUT", "120"))

    try:
        result = await asyncio.wait_for(
            _run_enricher(topic, assets),
            timeout=_timeout,
        )
        assets = result
    except asyncio.TimeoutError:
        assets.errors.append(f"타임아웃 ({_timeout}초 초과)")
        logger.warning("[NLM Enricher] '%s' — 타임아웃", topic[:40])
    except Exception as exc:
        assets.errors.append(str(exc))
        logger.warning("[NLM Enricher] 예외 발생 (파이프라인 계속): %s", exc)

    assets.elapsed_sec = round(time.monotonic() - start, 2)
    if assets.has_assets:
        logger.info(
            "[NLM Enricher] 완료 (%.1fs): article=%d자, provider=%s",
            assets.elapsed_sec,
            len(assets.article),
            assets.ai_provider,
        )
    return assets


async def _run_enricher(topic: str, assets: NotebookLMAssets) -> NotebookLMAssets:
    """실제 enricher 로직 (비동기 래퍼)."""
    mode = os.environ.get("NOTEBOOKLM_MODE", "topic").lower()

    loop = asyncio.get_event_loop()

    if mode == "gdrive":
        # ── GDrive 모드: 새 파일 감지 → 텍스트 추출 ─────────────────────
        assets = await loop.run_in_executor(
            None,
            lambda: _gdrive_extract(assets),
        )
        if assets.errors and not assets.source_text:
            # GDrive 실패 → topic 모드로 폴백
            logger.info("[NLM Enricher] GDrive 실패, topic 모드로 폴백")
            assets.source_text = _build_topic_text(topic)
    else:
        # ── Topic 모드: 주제 텍스트 직접 사용 ────────────────────────────
        assets.source_text = _build_topic_text(topic)

    if not assets.source_text.strip():
        assets.errors.append("소스 텍스트 없음 — 아티클 생성 스킵")
        return assets

    # ── AI 아티클 작성 ────────────────────────────────────────────────
    assets = await loop.run_in_executor(
        None,
        lambda: _write_article(assets, topic),
    )

    return assets


# ── GDrive 추출 (동기, executor 실행용) ──────────────────────────────────


def _gdrive_extract(assets: NotebookLMAssets) -> NotebookLMAssets:
    """GDrive에서 최신 파일을 감지하고 텍스트를 추출합니다."""
    mod = _load_module("gdrive_pdf_extractor", _GDRIVE_EXTRACTOR_PATH)
    if mod is None:
        assets.errors.append("gdrive_pdf_extractor 모듈 없음")
        return assets

    folder_id = os.environ.get("GOOGLE_DRIVE_FOLDER_ID")
    if not folder_id:
        assets.errors.append("GOOGLE_DRIVE_FOLDER_ID 환경 변수 미설정")
        return assets

    try:
        # 최근 24시간 이내 새 파일 감지
        from datetime import datetime, timezone, timedelta

        since_iso = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()

        files = mod.list_new_files_since(
            folder_id=folder_id,
            since_iso=since_iso,
            mime_filter=["application/pdf", "image/png", "image/jpeg", "text/plain"],
        )

        if not files:
            assets.errors.append("GDrive 폴더에 신규 파일 없음 (24h)")
            return assets

        # 가장 최근 파일 처리
        latest = files[0]
        logger.info("[NLM Enricher] GDrive 파일 처리: %s", latest.get("name", ""))

        result = mod.download_and_extract(latest["id"])
        assets.source_text = result.get("text", "")
        assets.drive_url = result.get("drive_url", "")

        if result.get("warning"):
            assets.errors.append(result["warning"])

        logger.info(
            "[NLM Enricher] GDrive 텍스트 추출 완료: %d자 (%s)",
            len(assets.source_text),
            latest.get("name", ""),
        )

    except Exception as exc:
        assets.errors.append(f"GDrive 추출 오류: {exc}")
        logger.warning("[NLM Enricher] GDrive 추출 실패: %s", exc)

    return assets


def _build_topic_text(topic: str) -> str:
    """topic 모드에서 content_writer에 전달할 텍스트를 구성합니다."""
    return (
        f"주제: {topic}\n\n"
        "위 주제에 대해 일반 직장인 독자를 대상으로 한 블로그 아티클을 작성해주세요.\n"
        "독자들이 공감하고 실용적인 인사이트를 얻을 수 있도록 구성하세요.\n"
    )


# ── AI 아티클 작성 (동기, executor 실행용) ────────────────────────────────


def _write_article(assets: NotebookLMAssets, topic: str) -> NotebookLMAssets:
    """content_writer 모듈로 아티클을 생성합니다."""
    mod = _load_module("content_writer", _CONTENT_WRITER_PATH)
    if mod is None:
        assets.errors.append("content_writer 모듈 없음")
        return assets

    # 프로젝트 키 결정 (blind-to-x 전용 템플릿 없으면 default 사용)
    project = os.environ.get("NOTEBOOKLM_CONTENT_PROJECT", "btx")

    try:
        result = mod.write_article(
            assets.source_text,
            project=project,
            provider=os.environ.get("CONTENT_WRITER_AI_MODEL"),
        )
        assets.article = result.get("article", "")
        assets.article_title = result.get("title", "") or topic
        assets.ai_provider = result.get("provider", "unknown")
        logger.info(
            "[NLM Enricher] 아티클 작성 완료: %d자 (%s)",
            len(assets.article),
            assets.ai_provider,
        )
    except Exception as exc:
        assets.errors.append(f"아티클 작성 실패: {exc}")
        logger.warning("[NLM Enricher] 아티클 작성 실패: %s", exc)

    return assets
