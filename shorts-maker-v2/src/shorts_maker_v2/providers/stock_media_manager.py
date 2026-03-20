"""StockMediaManager — Pexels + Unsplash 채널별 통합 미디어 관리자."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Literal

import yaml

from shorts_maker_v2.providers.pexels_client import PexelsClient
from shorts_maker_v2.providers.unsplash_client import UnsplashClient

logger = logging.getLogger(__name__)

MediaType = Literal["video", "photo"]


# ──────────────────────────────────────────────────────────────────
# 채널별 기본 검색 키워드 매핑
# (channel_profiles.yaml의 visual_styles 첫 번째 항목에서 자동 추출도 가능)
# ──────────────────────────────────────────────────────────────────
_CHANNEL_KEYWORDS: dict[str, dict[str, str]] = {
    "ai_tech": {
        "hook": "futuristic cyberpunk neon technology hologram digital interface",
        "body": "artificial intelligence robot neural network server data center",
        "cta": "technology innovation future smart city digital transformation",
    },
    "psychology": {
        "hook": "human emotion psychology mindset",
        "body": "lifestyle people emotion warm cozy",
        "cta": "mindfulness calm happiness life",
    },
    "history": {
        "hook": "ancient history archaeology vintage",
        "body": "historical heritage ancient civilization",
        "cta": "history culture heritage journey",
    },
    "space": {
        "hook": "galaxy universe cosmos stars nebula",
        "body": "space astronomy planet cosmic",
        "cta": "universe exploration space science",
    },
    "health": {
        "hook": "medical healthcare doctor health",
        "body": "healthy lifestyle nutrition fitness",
        "cta": "wellness health life vitality",
    },
}

_DEFAULT_KEYWORD = "beautiful nature abstract background"


class StockMediaManager:
    """채널·씬 역할별로 Pexels/Unsplash에서 미디어를 검색·다운로드하는 통합 관리자.

    Fallback 체인:
        1. Pexels 영상 (video)
        2. Pexels 이미지 (photo)
        3. Unsplash 이미지 (photo)

    Usage::

        manager = StockMediaManager.from_env()
        path = manager.get_media_for_scene(
            channel="ai_tech",
            scene_role="body",
            visual_prompt="neural network brain AI",
            output_path=Path("assets/scene_01.mp4"),
        )
    """

    def __init__(
        self,
        pexels_client: PexelsClient,
        unsplash_client: UnsplashClient | None = None,
        profiles_path: Path | None = None,
    ):
        self.pexels = pexels_client
        self.unsplash = unsplash_client
        self._channel_keywords = _CHANNEL_KEYWORDS.copy()

        # channel_profiles.yaml에서 visual_styles 보강 (선택)
        if profiles_path and profiles_path.exists():
            self._load_profiles(profiles_path)

    # ──────────────────────────────────────────────
    # 팩토리
    # ──────────────────────────────────────────────

    @classmethod
    def from_env(cls, profiles_path: Path | None = None) -> StockMediaManager:
        """환경 변수에서 API 키를 읽어 인스턴스 생성."""
        pexels_key = os.getenv("PEXELS_API_KEY", "")
        unsplash_key = os.getenv("UNSPLASH_API_KEY", "")

        if not pexels_key:
            raise OSError("PEXELS_API_KEY가 설정되지 않았습니다. .env 파일을 확인하세요.")

        pexels = PexelsClient(api_key=pexels_key)
        unsplash = UnsplashClient(access_key=unsplash_key) if unsplash_key else None

        # 프로젝트 루트의 channel_profiles.yaml 자동 탐색
        if profiles_path is None:
            candidate = Path(__file__).parents[4] / "channel_profiles.yaml"
            if candidate.exists():
                profiles_path = candidate

        return cls(pexels, unsplash, profiles_path)

    # ──────────────────────────────────────────────
    # 핵심 진입점
    # ──────────────────────────────────────────────

    def get_media_for_scene(
        self,
        *,
        channel: str,
        scene_role: str,
        visual_prompt: str,
        output_path: Path,
        prefer: MediaType = "video",
    ) -> Path:
        """씬에 맞는 미디어를 Fallback 체인으로 검색·다운로드.

        Args:
            channel: 채널 ID (ex. 'ai_tech', 'psychology')
            scene_role: 씬 역할 ('hook' | 'body' | 'cta')
            visual_prompt: AI가 생성한 시각 프롬프트 (영문)
            output_path: 저장 경로
            prefer: 'video' 우선 시도 | 'photo' 는 이미지만

        Returns:
            다운로드된 파일의 Path

        Raises:
            RuntimeError: 모든 소스에서 미디어를 구하지 못한 경우
        """
        output_path = Path(output_path)
        query = self._build_query(channel, scene_role, visual_prompt)
        logger.info("[StockMedia] 검색 쿼리: %r (channel=%s, role=%s)", query, channel, scene_role)

        errors: list[str] = []

        # ── Step 1: Pexels 영상 ──────────────────────
        if prefer == "video":
            try:
                video_path = output_path.with_suffix(".mp4")
                result = self.pexels.download_video(query=query, output_path=video_path)
                logger.info("[StockMedia] ✅ Pexels 영상 다운로드 성공: %s", result)
                return result
            except Exception as exc:
                msg = f"Pexels video: {exc}"
                logger.warning("[StockMedia] ⚠️ %s", msg)
                errors.append(msg)

        # ── Step 2: Pexels 이미지 ───────────────────
        try:
            photo_path = output_path.with_suffix(".jpg")
            result = self.pexels.download_photo(query=query, output_path=photo_path)
            logger.info("[StockMedia] ✅ Pexels 이미지 다운로드 성공: %s", result)
            return result
        except Exception as exc:
            msg = f"Pexels photo: {exc}"
            logger.warning("[StockMedia] ⚠️ %s", msg)
            errors.append(msg)

        # ── Step 3: Unsplash 이미지 ─────────────────
        if self.unsplash is not None:
            try:
                photo_path = output_path.with_suffix(".jpg")
                result = self.unsplash.download_photo(query=query, output_path=photo_path)
                logger.info("[StockMedia] ✅ Unsplash 이미지 다운로드 성공: %s", result)
                return result
            except Exception as exc:
                msg = f"Unsplash photo: {exc}"
                logger.warning("[StockMedia] ⚠️ %s", msg)
                errors.append(msg)

        raise RuntimeError(
            "[StockMedia] 모든 소스에서 미디어를 가져오지 못했습니다.\n" + "\n".join(f"  - {e}" for e in errors)
        )

    # ──────────────────────────────────────────────
    # 키워드 빌드
    # ──────────────────────────────────────────────

    def _build_query(
        self,
        channel: str,
        scene_role: str,
        visual_prompt: str,
    ) -> str:
        """채널 + 역할 기본 키워드에 visual_prompt를 혼합해 검색 쿼리 생성.

        visual_prompt (AI 생성 영문)를 35자 이내로 잘라 붙여서
        Pexels/Unsplash 검색 정확도를 높인다.
        """
        channel_kw = self._channel_keywords.get(channel, {}).get(scene_role, _DEFAULT_KEYWORD)
        # visual_prompt 앞 35자 추출 (단어 단위 절삭)
        truncated = " ".join(visual_prompt.split()[:5])
        query = f"{truncated} {channel_kw}".strip()
        return query[:100]  # API 쿼리 길이 제한

    def get_search_query(
        self,
        channel: str,
        scene_role: str,
        visual_prompt: str,
    ) -> str:
        """검색 쿼리만 반환 (테스트·디버그 용도)."""
        return self._build_query(channel, scene_role, visual_prompt)

    # ──────────────────────────────────────────────
    # 프로필 로딩
    # ──────────────────────────────────────────────

    def _load_profiles(self, profiles_path: Path) -> None:
        """channel_profiles.yaml에서 채널별 visual_styles 첫 항목을 키워드로 보강."""
        try:
            with profiles_path.open(encoding="utf-8") as f:
                data = yaml.safe_load(f)
            for ch_id, ch_cfg in (data.get("channels") or {}).items():
                styles: list[str] = ch_cfg.get("visual_styles", [])
                if styles and ch_id not in self._channel_keywords:
                    # 첫 번째 visual_style을 body 키워드로 사용
                    self._channel_keywords[ch_id] = {
                        "hook": styles[0],
                        "body": styles[min(1, len(styles) - 1)],
                        "cta": styles[0],
                    }
        except Exception as exc:
            logger.warning("[StockMedia] channel_profiles.yaml 로딩 실패: %s", exc)
