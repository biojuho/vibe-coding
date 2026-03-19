"""NotebookLM 자동 리서치 자산 생성 모듈.

Blind-to-X 파이프라인에서 포스트 주제에 맞는
인포그래픽(.png)과 슬라이드(.pptx)를 자동 생성하고
Cloudinary CDN에 업로드하여 Notion 소셜 미디어 자산으로 연동합니다.

환경 변수:
    NOTEBOOKLM_ENABLED=true   기능 활성화 (기본: false)
    NOTEBOOKLM_TIMEOUT=120    생성 타임아웃 초 (기본: 120)
"""

from __future__ import annotations

import asyncio
import importlib.util
import logging
import os
import pathlib
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# ── notebooklm_integration 동적 import ────────────────────────────────────
_INTEGRATION_PATH = (
    pathlib.Path(__file__).resolve().parent.parent.parent
    / "execution"
    / "notebooklm_integration.py"
)

def _load_notebooklm_module():
    """notebooklm_integration.py를 동적으로 로드합니다."""
    if not _INTEGRATION_PATH.exists():
        return None
    spec = importlib.util.spec_from_file_location(
        "notebooklm_integration", str(_INTEGRATION_PATH)
    )
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
        return mod
    except Exception as exc:
        logger.warning("[NLM Enricher] notebooklm_integration 로드 실패: %s", exc)
        return None


# ── 데이터 클래스 ─────────────────────────────────────────────────────────

@dataclass
class NotebookLMAssets:
    """NotebookLM이 생성한 소셜 미디어 자산 컨테이너."""

    topic: str
    notebook_id: str = ""
    infographic_url: str = ""       # Cloudinary CDN URL (PNG)
    infographic_local: str = ""     # .tmp/ 로컬 경로
    slides_local: str = ""          # .tmp/ PPTX 로컬 경로
    mind_map_local: str = ""        # .tmp/ 마인드맵 JSON 경로
    elapsed_sec: float = 0.0
    errors: list[str] = field(default_factory=list)

    @property
    def has_assets(self) -> bool:
        return bool(self.infographic_url or self.infographic_local or self.slides_local)


# ── 메인 enricher 함수 ────────────────────────────────────────────────────

async def enrich_post_with_assets(
    topic: str,
    *,
    image_uploader=None,
    timeout: int | None = None,
) -> NotebookLMAssets:
    """포스트 주제로 NotebookLM 자산을 자동 생성합니다.

    Args:
        topic: 리서치할 주제 (포스트 제목 또는 topic_cluster)
        image_uploader: ImageUploader 인스턴스 (CDN 업로드용, 없으면 로컬만)
        timeout: 최대 대기 시간 (초). 기본값: NOTEBOOKLM_TIMEOUT 환경 변수

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
            _generate_assets(topic, assets, image_uploader),
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
            "[NLM Enricher] 완료 (%.1fs): infographic=%s, slides=%s",
            assets.elapsed_sec,
            bool(assets.infographic_url),
            bool(assets.slides_local),
        )
    return assets


async def _generate_assets(
    topic: str,
    assets: NotebookLMAssets,
    image_uploader,
) -> NotebookLMAssets:
    """실제 NotebookLM 자산 생성 로직 (비동기 래퍼)."""
    mod = _load_notebooklm_module()
    if mod is None:
        assets.errors.append("notebooklm_integration 모듈 없음")
        return assets

    loop = asyncio.get_event_loop()

    # 1. 노트북 생성 + 딥 리서치 소스 연동 (blocking → executor)
    logger.info("[NLM Enricher] '%s' 리서치 시작...", topic[:40])
    research = await loop.run_in_executor(
        None,
        lambda: _safe_research_workflow(mod, topic),
    )
    if not research or not research.get("notebook_id"):
        assets.errors.append("research_workflow 실패")
        return assets

    assets.notebook_id = research["notebook_id"]
    nb_id = assets.notebook_id
    logger.info("[NLM Enricher] 노트북 생성 완료: %s (%d소스)", nb_id, len(research.get("sources", [])))

    # 2. 소스 인덱싱 대기 (딥 리서치는 30초)
    await asyncio.sleep(30)

    # 3. 아티팩트 생성: mind-map, infographic, slide-deck
    tmp_dir = pathlib.Path(".tmp") / "notebooklm"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    for art_type, local_attr in [
        ("mind-map", "mind_map_local"),
        ("infographic", "infographic_local"),
        ("slide-deck", "slides_local"),
    ]:
        try:
            result = await loop.run_in_executor(
                None,
                lambda t=art_type: _safe_generate_and_download(mod, nb_id, t, tmp_dir, topic),
            )
            if result:
                setattr(assets, local_attr, result)
                logger.info("[NLM Enricher] %s 생성 완료: %s", art_type, result)
            # Rate limit 방지
            await asyncio.sleep(5)
        except Exception as exc:
            assets.errors.append(f"{art_type} 생성 실패: {exc}")
            logger.warning("[NLM Enricher] %s 생성 실패: %s", art_type, exc)

    # 4. 인포그래픽 CDN 업로드
    if assets.infographic_local and image_uploader:
        try:
            cdn_url = await image_uploader.upload(assets.infographic_local)
            if cdn_url:
                assets.infographic_url = cdn_url
                logger.info("[NLM Enricher] 인포그래픽 CDN 업로드 완료: %s", cdn_url)
            else:
                assets.errors.append("인포그래픽 CDN 업로드 실패")
        except Exception as exc:
            assets.errors.append(f"CDN 업로드 예외: {exc}")
            logger.warning("[NLM Enricher] CDN 업로드 실패: %s", exc)

    return assets


def _safe_research_workflow(mod, topic: str) -> dict | None:
    """research_workflow를 안전하게 호출 (동기)."""
    try:
        return mod.research_workflow(
            f"BTX: {topic[:50]}",
            query=topic,
            search_mode="fast",  # 파이프라인 내 속도 우선
        )
    except Exception as exc:
        logger.warning("[NLM Enricher] research_workflow 예외: %s", exc)
        return None


def _safe_generate_and_download(
    mod,
    notebook_id: str,
    art_type: str,
    output_dir: pathlib.Path,
    topic: str,
) -> str | None:
    """generate_content + notebooklm download를 실행하여 로컬 파일 경로 반환."""
    try:
        result = mod.generate_content(notebook_id, art_type)
        if not result:
            return None

        # 파일 확장자 매핑
        ext_map = {
            "mind-map": ".json",
            "infographic": ".png",
            "slide-deck": ".pptx",
        }
        # task_id가 있으면 다운로드 대기 후 경로 반환
        task_id = result.get("task_id") or result.get("id")
        if task_id:
            logger.info("[NLM Enricher] %s task_id=%s (다운로드 미구현 — 경로만 반환)", art_type, task_id)
            # TODO: notebooklm-py에 download API 추가 시 구현 필요
            # 현재는 파일이 실제로 생성되지 않으므로 None 반환
            # (이전에는 빈 경로를 반환하여 하위 코드에서 파일이 있는 것처럼 처리됨)
            return None

        return None
    except Exception as exc:
        logger.warning("[NLM Enricher] generate/download %s 실패: %s", art_type, exc)
        return None
