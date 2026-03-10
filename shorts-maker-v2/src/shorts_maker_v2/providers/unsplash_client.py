"""Unsplash 스톡 이미지 프로바이더 (무료 API)."""
from __future__ import annotations

from pathlib import Path

import requests


class UnsplashClient:
    """Unsplash API v1 클라이언트 (이미지 검색 + 다운로드)."""

    SEARCH_API = "https://api.unsplash.com/search/photos"

    def __init__(self, access_key: str, request_timeout_sec: int = 60):
        if not access_key:
            raise ValueError("UNSPLASH_API_KEY is required.")
        self.access_key = access_key
        self.request_timeout_sec = request_timeout_sec
        self._headers = {"Authorization": f"Client-ID {self.access_key}"}

    # ──────────────────────────────────────────────
    # 이미지 검색
    # ──────────────────────────────────────────────

    def search_photos(
        self,
        *,
        query: str,
        orientation: str = "portrait",
        per_page: int = 5,
    ) -> list[dict]:
        """Unsplash에서 이미지를 검색해 결과 목록 반환.

        Args:
            query: 검색 쿼리 (영문 권장)
            orientation: 'portrait' | 'landscape' | 'squarish'
            per_page: 결과 수 (최대 30)

        Returns:
            Unsplash photo 오브젝트 리스트
        """
        resp = requests.get(
            self.SEARCH_API,
            headers=self._headers,
            params={
                "query": query,
                "orientation": orientation,
                "per_page": min(per_page, 30),
            },
            timeout=self.request_timeout_sec,
        )
        resp.raise_for_status()
        return resp.json().get("results", [])

    # ──────────────────────────────────────────────
    # 이미지 다운로드
    # ──────────────────────────────────────────────

    def download_photo(
        self,
        *,
        query: str,
        output_path: Path,
        per_page: int = 5,
    ) -> Path:
        """쿼리로 Unsplash 이미지를 검색해 저장 (portrait 최우선).

        Args:
            query: 검색 쿼리
            output_path: 저장 경로 (.jpg / .png)
            per_page: 후보 수

        Returns:
            저장된 파일 Path
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if output_path.exists():
            return output_path

        photos = self.search_photos(query=query, per_page=per_page)
        if not photos:
            raise RuntimeError(
                f"No Unsplash photos found for query: {query!r}"
            )

        # portrait 비율 우선 (h >= w)
        photo = next(
            (
                p for p in photos
                if p.get("height", 0) >= p.get("width", 1)
            ),
            photos[0],
        )

        # full > regular > small 순으로 URL 선택
        urls: dict = photo.get("urls", {})
        url = urls.get("full") or urls.get("regular") or urls.get("small")
        if not url:
            raise RuntimeError(
                f"No usable Unsplash URL for query: {query!r}"
            )

        self._stream_download(url, output_path)
        return output_path

    # ──────────────────────────────────────────────
    # 공통 유틸리티
    # ──────────────────────────────────────────────

    def _stream_download(self, url: str, dest: Path) -> None:
        """URL을 청크 스트림으로 다운로드."""
        resp = requests.get(
            url,
            timeout=self.request_timeout_sec,
            stream=True,
        )
        resp.raise_for_status()
        dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open("wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
