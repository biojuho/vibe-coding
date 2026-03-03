"""
YouTube Analytics 수집 스크립트.
YouTube Data API v3로 업로드된 영상의 조회수/좋아요/댓글/CTR/평균 시청 시간을 수집하여
content_db에 저장합니다.

Usage:
    python execution/youtube_analytics_collector.py
    python execution/youtube_analytics_collector.py --channel "건강/과학"
"""
from __future__ import annotations

import argparse
import logging
import os
from datetime import datetime
from typing import Any

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

_TOKEN_FILE = os.path.join(os.path.dirname(__file__), "..", "token.json")
_SCOPES = [
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]


def _build_youtube_service():
    """YouTube Data API v3 서비스 빌드."""
    if not os.path.exists(_TOKEN_FILE):
        raise FileNotFoundError(
            f"OAuth 토큰 없음: {_TOKEN_FILE}\n"
            "youtube_uploader.py의 인증 흐름을 먼저 실행하세요."
        )
    creds = Credentials.from_authorized_user_file(_TOKEN_FILE, _SCOPES)
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            from google.auth.transport.requests import Request
            creds.refresh(Request())
            logger.info("OAuth 토큰 갱신 완료")
        else:
            raise RuntimeError(
                "OAuth 토큰 만료 및 refresh 불가. youtube_uploader.py로 재인증 필요."
            )
    return build("youtube", "v3", credentials=creds)


def fetch_video_stats(video_ids: list[str]) -> dict[str, dict[str, Any]]:
    """
    YouTube Data API로 영상 통계 일괄 조회.
    50개씩 배치 처리 (API 제한).
    Returns: {video_id: {views, likes, comments}}
    """
    youtube = _build_youtube_service()
    stats: dict[str, dict[str, Any]] = {}

    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i + 50]
        response = youtube.videos().list(
            part="statistics",
            id=",".join(batch),
        ).execute()

        for item in response.get("items", []):
            vid = item["id"]
            s = item.get("statistics", {})
            stats[vid] = {
                "views": int(s.get("viewCount", 0)),
                "likes": int(s.get("likeCount", 0)),
                "comments": int(s.get("commentCount", 0)),
            }
    return stats


def collect_and_update(channel: str | None = None) -> dict[str, Any]:
    """
    업로드된 모든 영상의 YouTube 통계를 수집하여 content_db에 업데이트.
    Returns: {updated: int, skipped: int, errors: list}
    """
    from execution.content_db import get_all, init_db, update_job

    init_db()
    items = get_all(channel=channel)

    # youtube_video_id가 있는 업로드 완료 항목만 필터
    uploaded = [
        item for item in items
        if item.get("youtube_status") == "uploaded"
        and item.get("youtube_video_id")
    ]

    if not uploaded:
        logger.info("수집 대상 없음")
        return {"updated": 0, "skipped": 0, "errors": []}

    video_ids = [item["youtube_video_id"] for item in uploaded]
    logger.info("YouTube 통계 수집 시작: %d개 영상", len(video_ids))

    try:
        stats = fetch_video_stats(video_ids)
    except Exception as exc:
        logger.error("YouTube API 호출 실패: %s", exc)
        return {"updated": 0, "skipped": len(uploaded), "errors": [str(exc)]}

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    updated = 0
    errors: list[str] = []

    for item in uploaded:
        vid = item["youtube_video_id"]
        if vid not in stats:
            continue
        s = stats[vid]
        try:
            update_job(
                item["id"],
                yt_views=s["views"],
                yt_likes=s["likes"],
                yt_comments=s["comments"],
                yt_stats_updated_at=now,
            )
            updated += 1
        except Exception as exc:
            errors.append(f"id={item['id']}: {exc}")

    logger.info("수집 완료: %d개 업데이트, %d개 에러", updated, len(errors))
    return {
        "updated": updated,
        "skipped": len(uploaded) - updated - len(errors),
        "errors": errors,
    }


def _cli() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description="YouTube Analytics 수집")
    parser.add_argument("--channel", default="", help="채널 필터")
    args = parser.parse_args()

    result = collect_and_update(channel=args.channel or None)
    print(f"결과: {result['updated']}개 업데이트, {result['skipped']}개 스킵, {len(result['errors'])}개 에러")
    for err in result["errors"]:
        print(f"  에러: {err}")


if __name__ == "__main__":
    _cli()
