"""Freesound BGM / 효과음 프로바이더.

Freesound API v2:
  - https://freesound.org/docs/api/
  - 검색 엔드포인트: GET /apiv2/search/text/
  - 상세 + 다운로드: GET /apiv2/sounds/<id>/download/
"""

from __future__ import annotations

import logging
import os
import random
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

# 채널별 BGM 에너지 → Freesound 검색 태그 매핑
# 키워드는 각 채널 분위기에 맞게 정밀 조정 (단순 generics 배제)
BGM_ENERGY_TAGS: dict[str, str] = {
    # AI/기술: 사이버펑크 미래감 + 구동감
    "high": "synthwave electronic driving futuristic cyberpunk upbeat loop",
    # 역사: 다큐멘터리 오케스트라 + 서사적 긴장감
    "medium": "cinematic orchestral epic historical documentary tension background",
    # 심리학: 따뜻하고 감성적인 피아노 + 앰비언트
    "calm": "calm ambient warm piano emotional gentle healing loop",
    # 우주: 한스 짐머 스타일 웅장함 + 광활한 공간감
    "epic": "epic orchestral space cosmos wonder cinematic dramatic majestic",
    # 건강: 밝고 긍정적인 어쿠스틱 — 실천 의지 고취
    "warm_uplifting": "upbeat acoustic positive cheerful motivating healthy lifestyle loop",
}

# 채널 ID → BGM 에너지 기본값 (channel_profiles.yaml와 동기)
CHANNEL_BGM_ENERGY: dict[str, str] = {
    "ai_tech": "high",
    "psychology": "calm",
    "history": "medium",
    "space": "epic",
    "health": "warm_uplifting",  # medium → warm_uplifting (밝고 편안한 톤)
}


class FreesoundClient:
    """Freesound API v2 클라이언트 — BGM/효과음 검색 + 다운로드.

    Usage::

        client = FreesoundClient.from_env()
        path = client.download_bgm_for_channel(
            channel="space",
            output_path=Path("assets/bgm_space.mp3"),
        )
    """

    SEARCH_URL = "https://freesound.org/apiv2/search/text/"
    SOUND_URL = "https://freesound.org/apiv2/sounds/{sound_id}/"
    DOWNLOAD_URL = "https://freesound.org/apiv2/sounds/{sound_id}/download/"

    def __init__(self, api_key: str, request_timeout_sec: int = 60):
        if not api_key:
            raise ValueError("FREESOUND_API_KEY is required.")
        self.api_key = api_key
        self.request_timeout_sec = request_timeout_sec
        self._auth = {"token": self.api_key}

    # ──────────────────────────────────────────────
    # 팩토리
    # ──────────────────────────────────────────────

    @classmethod
    def from_env(cls) -> FreesoundClient:
        """환경 변수에서 API 키를 읽어 인스턴스 생성."""
        key = os.getenv("FREESOUND_API_KEY", "")
        if not key:
            raise OSError("FREESOUND_API_KEY가 설정되지 않았습니다. .env 파일을 확인하세요.")
        return cls(api_key=key)

    # ──────────────────────────────────────────────
    # 검색
    # ──────────────────────────────────────────────

    def search(
        self,
        *,
        query: str,
        duration_min: float = 10.0,
        duration_max: float = 180.0,
        license_filter: str = "Attribution,Attribution NonCommercial,Creative Commons 0",
        per_page: int = 5,
    ) -> list[dict]:
        """Freesound에서 사운드를 검색해 결과 목록 반환.

        Args:
            query: 검색 텍스트 (예: "epic orchestral loop")
            duration_min: 최소 길이(초) — 너무 짧은 효과음 제외
            duration_max: 최대 길이(초) — 너무 긴 트랙 제외
            license_filter: 허용 라이선스 (쉼표 구분)
            per_page: 반환 결과 수

        Returns:
            Freesound sound 오브젝트 리스트
        """
        resp = requests.get(
            self.SEARCH_URL,
            params={
                **self._auth,
                "query": query,
                "filter": (f'duration:[{duration_min} TO {duration_max}] license:("{license_filter}")'),
                "fields": "id,name,duration,license,previews,download",
                "sort": "score",
                "page_size": per_page,
            },
            timeout=self.request_timeout_sec,
        )
        resp.raise_for_status()
        return resp.json().get("results", [])

    # ──────────────────────────────────────────────
    # 다운로드
    # ──────────────────────────────────────────────

    def download_preview(
        self,
        *,
        sound: dict,
        output_path: Path,
    ) -> Path:
        """Freesound 미리듣기(HQ MP3)를 다운로드.

        정식 다운로드는 OAuth2가 필요하므로,
        API 토큰으로 접근 가능한 HQ preview를 사용합니다.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if output_path.exists():
            return output_path

        previews: dict = sound.get("previews", {})
        url = previews.get("preview-hq-mp3") or previews.get("preview-lq-mp3")
        if not url:
            raise RuntimeError(f"No preview URL in sound id={sound.get('id')!r}")

        # Freesound preview URL은 token 파라미터로 인증
        resp = requests.get(
            url,
            params=self._auth,
            timeout=self.request_timeout_sec,
            stream=True,
        )
        resp.raise_for_status()

        with output_path.open("wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)

        logger.info(
            "[Freesound] ✅ 다운로드 완료: %s (%.1fs)",
            output_path.name,
            sound.get("duration", 0),
        )
        return output_path

    # ──────────────────────────────────────────────
    # 채널별 BGM 다운로드 (메인 진입점)
    # ──────────────────────────────────────────────

    def download_bgm_for_channel(
        self,
        *,
        channel: str,
        output_path: Path,
        energy: str | None = None,
        duration_min: float = 30.0,
        duration_max: float = 120.0,
    ) -> Path:
        """채널 ID에 맞는 BGM을 검색·다운로드.

        Args:
            channel: 채널 ID (ex. 'ai_tech', 'space')
            output_path: 저장 경로 (.mp3)
            energy: BGM 에너지 레벨 ('high'|'medium'|'calm'|'epic').
                    None이면 채널 기본값 사용.
            duration_min: 최소 길이(초)
            duration_max: 최대 길이(초)

        Returns:
            다운로드된 BGM 파일 Path
        """
        output_path = Path(output_path)
        if output_path.exists():
            logger.info("[Freesound] 캐시 히트: %s", output_path)
            return output_path

        energy = energy or CHANNEL_BGM_ENERGY.get(channel, "medium")
        query = BGM_ENERGY_TAGS.get(energy, "background music loop")

        logger.info(
            "[Freesound] BGM 검색 — channel=%s, energy=%s, query=%r",
            channel,
            energy,
            query,
        )

        results = self.search(
            query=query,
            duration_min=duration_min,
            duration_max=duration_max,
        )
        if not results:
            raise RuntimeError(f"[Freesound] 검색 결과 없음 — channel={channel!r}, query={query!r}")

        # 상위 결과 중 랜덤 선택 (다양성 확보 — 매번 같은 BGM 반복 방지)
        sound = random.choice(results[:min(3, len(results))])
        logger.info(
            "[Freesound] 선택된 BGM: %r (%.1fs)",
            sound.get("name", "unknown"),
            sound.get("duration", 0),
        )
        return self.download_preview(sound=sound, output_path=output_path)

    def download_sfx(
        self,
        *,
        query: str,
        output_path: Path,
        duration_max: float = 10.0,
    ) -> Path:
        """효과음(SFX) 검색·다운로드.

        Args:
            query: 효과음 설명 (예: "whoosh transition", "notification ding")
            output_path: 저장 경로
            duration_max: 최대 길이(초) — 효과음이므로 짧게

        Returns:
            다운로드된 효과음 파일 Path
        """
        output_path = Path(output_path)
        if output_path.exists():
            return output_path

        results = self.search(
            query=query,
            duration_min=0.1,
            duration_max=duration_max,
        )
        if not results:
            raise RuntimeError(f"[Freesound] 효과음 검색 결과 없음: {query!r}")

        sound = results[0]
        return self.download_preview(sound=sound, output_path=output_path)

    # ──────────────────────────────────────────────
    # 편의: 채널 에너지 조회
    # ──────────────────────────────────────────────

    @staticmethod
    def get_energy_for_channel(channel: str) -> str:
        """채널 ID의 기본 BGM 에너지 레벨 반환."""
        return CHANNEL_BGM_ENERGY.get(channel, "medium")

    @staticmethod
    def get_query_for_energy(energy: str) -> str:
        """에너지 레벨의 Freesound 검색 쿼리 반환."""
        return BGM_ENERGY_TAGS.get(energy, "background music loop")
