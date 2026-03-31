"""
Pixabay Music API를 이용한 BGM 자동 다운로드.
PIXABAY_API_KEY 환경변수 필요 (https://pixabay.com/api/docs/).

Usage:
    python workspace/execution/bgm_downloader.py
    python workspace/execution/bgm_downloader.py --query "calm ambient" --count 5
    python workspace/execution/bgm_downloader.py --output-dir projects/shorts-maker-v2/assets/bgm
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from path_contract import resolve_project_dir

from execution._logging import logger  # noqa: E402

_SHORTS_DIR = resolve_project_dir("shorts-maker-v2", required_paths=("config.yaml",))
_DEFAULT_BGM_DIR = _SHORTS_DIR / "assets" / "bgm"
_PIXABAY_MUSIC_API = "https://pixabay.com/api/music/"


def download_bgm(
    query: str = "calm background",
    count: int = 5,
    output_dir: Path | None = None,
) -> list[Path]:
    """
    Pixabay Music API로 BGM 검색 후 mp3 다운로드.

    Args:
        query: 검색어 (예: "calm ambient", "upbeat korean")
        count: 다운로드할 파일 수
        output_dir: 저장 경로 (기본: projects/shorts-maker-v2/assets/bgm)

    Returns:
        다운로드된 파일 경로 리스트
    """
    api_key = os.getenv("PIXABAY_API_KEY", "")
    if not api_key:
        logger.warning("PIXABAY_API_KEY 없음 — BGM 다운로드 스킵. .env에 PIXABAY_API_KEY=<key> 추가 후 재실행하세요.")
        return []

    dest_dir = output_dir or _DEFAULT_BGM_DIR
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)

    params = {
        "key": api_key,
        "q": query,
        "per_page": min(count, 20),  # Pixabay 최대 200, 안전하게 20
    }

    try:
        resp = requests.get(_PIXABAY_MUSIC_API, params=params, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as exc:
        logger.error("Pixabay API 호출 실패: %s", exc)
        return []

    try:
        hits = resp.json().get("hits", [])
    except ValueError as jde:
        logger.error("Pixabay API 응답 JSON 파싱 실패: %s", jde)
        return []
    if not hits:
        logger.warning("검색 결과 없음: '%s'", query)
        return []

    downloaded: list[Path] = []
    for hit in hits[:count]:
        audio_url = hit.get("audio", "")
        if not audio_url:
            continue

        track_id = hit.get("id", len(downloaded))
        filename = f"bgm_{track_id}.mp3"
        dest = dest_dir / filename

        if dest.exists():
            logger.info("[SKIP] 이미 존재: %s", filename)
            downloaded.append(dest)
            continue

        tmp_dest = dest.with_suffix(".tmp")
        try:
            audio_resp = requests.get(audio_url, timeout=120, stream=True)
            audio_resp.raise_for_status()
            with tmp_dest.open("wb") as f:
                for chunk in audio_resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            tmp_dest.rename(dest)
            title = hit.get("tags", filename)
            logger.info("[OK] %s  (%s)", filename, title)
            downloaded.append(dest)
        except requests.RequestException as exc:
            logger.error("다운로드 실패 (%s): %s", filename, exc)
            if tmp_dest.exists():
                tmp_dest.unlink()

    return downloaded


def _cli() -> int:
    load_dotenv(WORKSPACE_ROOT / ".env")
    load_dotenv(_SHORTS_DIR / ".env", override=False)

    parser = argparse.ArgumentParser(description="Pixabay BGM 자동 다운로드")
    parser.add_argument("--query", default="calm background music", help="검색어 (기본: calm background music)")
    parser.add_argument("--count", type=int, default=5, help="다운로드 수 (기본: 5)")
    parser.add_argument("--output-dir", default="", help="저장 경로 (기본: projects/shorts-maker-v2/assets/bgm)")
    args = parser.parse_args()

    out_dir = Path(args.output_dir) if args.output_dir else None
    print(f"[BGM] 검색: '{args.query}' / 목표: {args.count}개")
    files = download_bgm(query=args.query, count=args.count, output_dir=out_dir)
    total = len(files)
    if total:
        print(f"\n[완료] {total}개 다운로드 → {out_dir or _DEFAULT_BGM_DIR}")
    else:
        print("\n[완료] 다운로드 없음")
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
