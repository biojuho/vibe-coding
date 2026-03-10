"""Pexels 스톡 비디오/이미지 프로바이더 (무료 API)."""
from __future__ import annotations

import subprocess
from pathlib import Path

import requests


class PexelsClient:
    VIDEO_API = "https://api.pexels.com/videos/search"
    PHOTO_API = "https://api.pexels.com/v1/search"

    def __init__(self, api_key: str, request_timeout_sec: int = 60):
        if not api_key:
            raise ValueError("PEXELS_API_KEY is required.")
        self.api_key = api_key
        self.request_timeout_sec = request_timeout_sec
        self._headers = {"Authorization": self.api_key}

    # ──────────────────────────────────────────────
    # 영상 (Video)
    # ──────────────────────────────────────────────

    def search_videos(
        self,
        *,
        query: str,
        orientation: str = "portrait",
        size: str = "medium",
        per_page: int = 5,
    ) -> list[dict]:
        """Pexels에서 영상 검색 후 결과 목록 반환."""
        resp = requests.get(
            self.VIDEO_API,
            headers=self._headers,
            params={
                "query": query,
                "orientation": orientation,
                "size": size,
                "per_page": per_page,
            },
            timeout=self.request_timeout_sec,
        )
        resp.raise_for_status()
        return resp.json().get("videos", [])

    @staticmethod
    def _pick_best_video_file(
        video_entry: dict,
        target_width: int = 1080,
        target_height: int = 1920,
    ) -> str | None:
        files = video_entry.get("video_files", [])
        if not files:
            return None
        best = None
        best_diff = float("inf")
        for f in files:
            w = f.get("width", 0)
            h = f.get("height", 0)
            if w == 0 or h == 0:
                continue
            diff = abs(w - target_width) + abs(h - target_height)
            if diff < best_diff:
                best_diff = diff
                best = f
        return best.get("link") if best else None

    def download_video(
        self,
        *,
        query: str,
        output_path: Path,
        target_width: int = 1080,
        target_height: int = 1920,
        per_page: int = 5,
    ) -> Path:
        """쿼리로 Pexels 영상을 검색해 세로형으로 크롭·저장."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if output_path.exists():
            return output_path

        videos = self.search_videos(query=query, per_page=per_page)
        if not videos:
            raise RuntimeError(f"No Pexels videos found for query: {query!r}")

        url = None
        for video in videos:
            url = self._pick_best_video_file(video, target_width, target_height)
            if url:
                break
        if not url:
            raise RuntimeError(
                f"No suitable Pexels video file found for query: {query!r}"
            )

        raw_path = output_path.parent / f"{output_path.stem}_raw.mp4"
        self._stream_download(url, raw_path)
        self._crop_to_vertical(raw_path, output_path, target_width, target_height)
        raw_path.unlink(missing_ok=True)
        return output_path

    # ──────────────────────────────────────────────
    # 이미지 (Photo)
    # ──────────────────────────────────────────────

    def search_photos(
        self,
        *,
        query: str,
        orientation: str = "portrait",
        per_page: int = 5,
    ) -> list[dict]:
        """Pexels에서 이미지 검색 후 결과 목록 반환."""
        resp = requests.get(
            self.PHOTO_API,
            headers=self._headers,
            params={
                "query": query,
                "orientation": orientation,
                "per_page": per_page,
            },
            timeout=self.request_timeout_sec,
        )
        resp.raise_for_status()
        return resp.json().get("photos", [])

    def download_photo(
        self,
        *,
        query: str,
        output_path: Path,
        per_page: int = 5,
    ) -> Path:
        """쿼리로 Pexels 이미지를 검색해 저장 (portrait 우선)."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if output_path.exists():
            return output_path

        photos = self.search_photos(query=query, per_page=per_page)
        if not photos:
            raise RuntimeError(f"No Pexels photos found for query: {query!r}")

        # portrait 비율 우선 (h >= w), 없으면 첫 번째
        photo = next(
            (p for p in photos if p.get("height", 0) >= p.get("width", 1)),
            photos[0],
        )
        url = (
            photo.get("src", {}).get("large2x")
            or photo.get("src", {}).get("original")
        )
        if not url:
            raise RuntimeError(f"No usable photo URL for query: {query!r}")

        self._stream_download(url, output_path)
        return output_path

    # ──────────────────────────────────────────────
    # 공통 유틸리티
    # ──────────────────────────────────────────────

    def _stream_download(self, url: str, dest: Path) -> None:
        """URL을 청크 스트림으로 다운로드."""
        resp = requests.get(url, timeout=self.request_timeout_sec, stream=True)
        resp.raise_for_status()
        dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open("wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)

    @staticmethod
    def _crop_to_vertical(
        input_path: Path,
        output_path: Path,
        target_width: int,
        target_height: int,
    ) -> None:
        """FFmpeg로 영상을 세로형(1080×1920)으로 크롭."""
        from shorts_maker_v2.utils.hwaccel import detect_hw_encoder

        vf = (
            f"scale={target_width}:{target_height}:"
            f"force_original_aspect_ratio=increase,"
            f"crop={target_width}:{target_height}"
        )
        hw_codec, _ = detect_hw_encoder()
        cmd = [
            "ffmpeg", "-y", "-i", str(input_path),
            "-vf", vf,
            "-c:v", hw_codec,
            "-preset", "ultrafast" if hw_codec == "libx264" else "p1",
            "-an",
            str(output_path),
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=120)  # noqa: S603
        if result.returncode != 0:
            raise RuntimeError(
                f"ffmpeg crop failed: {result.stderr.decode(errors='replace')[:500]}"
            )
