"""
YouTube Analytics → Notion 통합 실행 스크립트.

YouTube Data API v3 OAuth로 업로드된 Shorts 영상의 통계(조회수/좋아요/댓글)를
수집하여 Notion 'Shorts 생산 트래킹' DB에 자동 업데이트합니다.

Usage:
    python execution/yt_analytics_to_notion.py
    python execution/yt_analytics_to_notion.py --channel "의학/건강"
    python execution/yt_analytics_to_notion.py --dry-run
    python execution/yt_analytics_to_notion.py --days 7

Required .env (루트):
    NOTION_API_KEY=ntn_xxxxx
    NOTION_TRACKING_DB_ID=xxxxx  (Shorts 생산 트래킹 DB)

Required (최초 1회 OAuth 인증):
    credentials.json  → Google Cloud Console에서 다운로드
    token.json        → youtube_uploader.py --auth-only 실행 후 자동 생성
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests
from dotenv import load_dotenv

# ── 경로 설정 ────────────────────────────────────────────────
_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env")
sys.path.insert(0, str(_ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger(__name__)

# ── 상수 ─────────────────────────────────────────────────────
_NOTION_API_BASE = "https://api.notion.com/v1"
_NOTION_VERSION = "2022-06-28"
_RATE_LIMIT_DELAY = 0.35  # Notion 3 req/s 제한


# ── Notion 헬퍼 ──────────────────────────────────────────────

def _notion_headers() -> dict:
    return {
        "Authorization": f"Bearer {os.getenv('NOTION_API_KEY', '')}",
        "Content-Type": "application/json",
        "Notion-Version": _NOTION_VERSION,
    }


def _notion_request(method: str, endpoint: str, **kwargs) -> requests.Response:
    url = f"{_NOTION_API_BASE}/{endpoint.lstrip('/')}"
    resp = requests.request(method, url, headers=_notion_headers(), timeout=30, **kwargs)
    time.sleep(_RATE_LIMIT_DELAY)
    return resp


# ── YouTube API 헬퍼 ─────────────────────────────────────────

def _fetch_yt_stats(video_ids: list[str]) -> dict[str, dict]:
    """YouTube Data API v3 API Key로 영상 통계 수집 (최대 50개 배치).

    API Key 방식은 공개 정보(조회수/좋아요/댓글)에 OAuth 없이 동작.
    Required .env: YOUTUBE_API_KEY=AIza...
    """
    api_key = os.getenv("YOUTUBE_API_KEY", "")
    if not api_key:
        raise ValueError(
            "YOUTUBE_API_KEY 환경변수가 없습니다.\n"
            ".env에 YOUTUBE_API_KEY=AIza... 를 추가하세요."
        )

    stats: dict[str, dict] = {}

    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i + 50]
        resp = requests.get(
            "https://www.googleapis.com/youtube/v3/videos",
            params={
                "part": "statistics",
                "id": ",".join(batch),
                "key": api_key,
            },
            timeout=30,
        )
        if resp.status_code != 200:
            raise RuntimeError(f"YouTube API 오류: {resp.status_code} {resp.text[:200]}")

        for item in resp.json().get("items", []):
            vid = item["id"]
            s = item.get("statistics", {})
            stats[vid] = {
                "views": int(s.get("viewCount", 0)),
                "likes": int(s.get("likeCount", 0)),
                "comments": int(s.get("commentCount", 0)),
            }

    return stats


# ── Notion DB 조회 ───────────────────────────────────────────

def _get_uploaded_pages(channel: str | None = None, days: int | None = None) -> list[dict]:
    """Notion Shorts 생산 트래킹 DB에서 업로드된 영상 페이지 조회."""
    db_id = os.getenv("NOTION_TRACKING_DB_ID", "")
    if not db_id:
        raise ValueError("NOTION_TRACKING_DB_ID 환경변수 없음")

    filters = [{"property": "유튜브 상태", "select": {"equals": "업로드됨"}}]

    if channel:
        filters.append({"property": "채널", "select": {"equals": channel}})

    if days:
        since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        filters.append({"property": "생성일", "date": {"on_or_after": since}})

    payload: dict = {
        "page_size": 100,
        "filter": {"and": filters} if len(filters) > 1 else filters[0],
    }

    pages = []
    while True:
        resp = _notion_request("POST", f"databases/{db_id}/query", json=payload)
        if resp.status_code != 200:
            logger.error("Notion DB 조회 실패: %s", resp.text[:200])
            break
        data = resp.json()
        pages.extend(data.get("results", []))
        if not data.get("has_more"):
            break
        payload["start_cursor"] = data["next_cursor"]

    return pages


# ── Notion 페이지 업데이트 ───────────────────────────────────

def _update_notion_page(page_id: str, stats: dict, video_id: str | None = None) -> bool:
    """조회수/좋아요/댓글 수집 결과를 Notion 페이지에 업데이트."""
    now_iso = datetime.now().strftime("%Y-%m-%d")
    properties: dict = {
        "조회수": {"number": stats["views"]},
        "좋아요": {"number": stats["likes"]},
        "댓글 수": {"number": stats["comments"]},
        "마지막 수집": {"date": {"start": now_iso}},
    }
    if video_id:
        properties["YouTube Video ID"] = {"rich_text": [{"text": {"content": video_id}}]}

    resp = _notion_request("PATCH", f"pages/{page_id}", json={"properties": properties})
    return resp.status_code == 200


# ── 메인 실행 ────────────────────────────────────────────────

def run(
    channel: str | None = None,
    days: int | None = None,
    dry_run: bool = False,
) -> dict:
    """
    전체 파이프라인 실행.
    Returns: {"updated": int, "skipped": int, "errors": list}
    """
    logger.info("📊 YouTube Analytics 수집 시작 (dry_run=%s)", dry_run)

    pages = _get_uploaded_pages(channel=channel, days=days)
    logger.info("수집 대상: %d개 Notion 페이지", len(pages))

    # YouTube Video ID 추출 (유튜브 URL에서)
    page_info: list[dict] = []
    for page in pages:
        props = page.get("properties", {})
        yt_url = (props.get("유튜브 URL") or {}).get("url") or ""
        yt_video_id = ""

        # URL에서 video ID 파싱: youtu.be/ID 또는 ?v=ID
        if "youtu.be/" in yt_url:
            yt_video_id = yt_url.split("youtu.be/")[-1].split("?")[0]
        elif "?v=" in yt_url:
            yt_video_id = yt_url.split("?v=")[-1].split("&")[0]
        elif "shorts/" in yt_url:
            yt_video_id = yt_url.split("shorts/")[-1].split("?")[0]

        # Notion에 저장된 YouTube Video ID 우선 사용
        existing_vid = ""
        vid_prop = props.get("YouTube Video ID", {})
        rt = vid_prop.get("rich_text", [])
        if rt:
            existing_vid = rt[0].get("plain_text", "")

        video_id = existing_vid or yt_video_id
        if video_id:
            page_info.append({"page_id": page["id"], "video_id": video_id})

    if not page_info:
        logger.info("업로드된 YouTube 영상 없음 (YouTube Video ID 미설정)")
        return {"updated": 0, "skipped": len(pages), "errors": []}

    video_ids = [p["video_id"] for p in page_info]
    logger.info("YouTube API 호출: %d개 영상", len(video_ids))

    if dry_run:
        logger.info("[DRY RUN] 실제 업데이트 없이 종료")
        logger.info("수집 대상 video_ids: %s", video_ids[:5])
        return {"updated": 0, "skipped": len(page_info), "errors": []}

    try:
        stats_map = _fetch_yt_stats(video_ids)
    except ValueError as exc:
        logger.error("YouTube API Key 필요: %s", exc)
        return {"updated": 0, "skipped": len(page_info), "errors": [str(exc)]}
    except Exception as exc:
        logger.error("YouTube API 실패: %s", exc)
        return {"updated": 0, "skipped": len(page_info), "errors": [str(exc)]}

    updated = 0
    skipped = 0
    errors: list[str] = []

    for info in page_info:
        vid = info["video_id"]
        if vid not in stats_map:
            skipped += 1
            continue
        ok = _update_notion_page(info["page_id"], stats_map[vid], video_id=vid)
        if ok:
            updated += 1
            logger.info("✅ 업데이트: %s → 조회수 %d", vid, stats_map[vid]["views"])
        else:
            errors.append(f"page={info['page_id']} vid={vid}")

    logger.info("완료: 업데이트 %d / 스킵 %d / 에러 %d", updated, skipped, len(errors))
    return {"updated": updated, "skipped": skipped, "errors": errors}


def _cli() -> None:
    parser = argparse.ArgumentParser(description="YouTube Analytics → Notion 자동화")
    parser.add_argument("--channel", default="", help="채널 필터 (예: '의학/건강')")
    parser.add_argument("--days", type=int, default=0, help="최근 N일 이내 영상만 수집")
    parser.add_argument("--dry-run", action="store_true", help="Notion 업데이트 없이 테스트 실행")
    args = parser.parse_args()

    result = run(
        channel=args.channel or None,
        days=args.days or None,
        dry_run=args.dry_run,
    )
    print(f"\n📊 결과: 업데이트 {result['updated']}개 / 스킵 {result['skipped']}개 / 에러 {len(result['errors'])}개")
    for err in result["errors"]:
        print(f"  ❌ {err}")


if __name__ == "__main__":
    _cli()
