"""
YouTube Data MCP Server.

YouTube Data API v3를 활용한 MCP 서버.
채널 통계, 최신 영상, 영상 상세 분석, 트렌딩 검색 기능을 제공합니다.

Usage:
    python server.py
"""
from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
except ImportError:
    Request = None
    Credentials = None
    build = None

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    FastMCP = None

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(_PROJECT_ROOT / ".env")

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

_TOKEN_FILE = str(_PROJECT_ROOT / "token.json")
_SCOPES = [
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]

# ---------------------------------------------------------------------------
# YouTube 서비스 (캐싱)
# ---------------------------------------------------------------------------

_cached_service = None
_cached_creds = None


def _get_youtube_service():
    """YouTube API 서비스를 캐싱하여 반환합니다. 토큰 만료 시에만 재빌드."""
    global _cached_service, _cached_creds

    if Credentials is None or build is None:
        raise ImportError("google-api-python-client 패키지가 설치되지 않았습니다.")

    token_path = os.environ.get("YOUTUBE_TOKEN_PATH", _TOKEN_FILE)

    # 캐시된 서비스가 유효하면 재사용
    if _cached_service is not None and _cached_creds is not None and _cached_creds.valid:
        return _cached_service

    try:
        creds = Credentials.from_authorized_user_file(token_path, _SCOPES)
    except FileNotFoundError:
        raise FileNotFoundError(
            "OAuth 토큰 파일을 찾을 수 없습니다. youtube_uploader.py의 인증 흐름을 먼저 실행하세요."
        )

    if not creds.valid:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            try:
                with open(token_path, "w", encoding="utf-8") as f:
                    f.write(creds.to_json())
            except OSError:
                logger.warning("OAuth 토큰 파일 저장 실패 (권한 문제 가능)")
            logger.info("OAuth 토큰 갱신 완료")
        else:
            raise RuntimeError("OAuth 토큰 만료 및 refresh 불가. 재인증이 필요합니다.")

    _cached_creds = creds
    _cached_service = build("youtube", "v3", credentials=creds)
    return _cached_service


def _fetch_video_stats_batch(youtube, video_ids: list[str]) -> dict[str, dict]:
    """영상 통계를 일괄 조회하는 공통 헬퍼."""
    if not video_ids:
        return {}
    stats_response = youtube.videos().list(
        part="statistics,contentDetails",
        id=",".join(video_ids),
    ).execute()

    stats_map: dict[str, dict] = {}
    for item in stats_response.get("items", []):
        s = item.get("statistics", {})
        cd = item.get("contentDetails", {})
        stats_map[item["id"]] = {
            "views": int(s.get("viewCount", 0)),
            "likes": int(s.get("likeCount", 0)),
            "comments": int(s.get("commentCount", 0)),
            "duration": cd.get("duration", ""),
        }
    return stats_map


# ---------------------------------------------------------------------------
# 도구 함수들
# ---------------------------------------------------------------------------


def _get_channel_stats(channel_id: str) -> dict[str, Any]:
    """채널의 구독자 수, 총 조회수, 영상 수를 조회합니다."""
    try:
        youtube = _get_youtube_service()
        response = youtube.channels().list(
            part="snippet,statistics",
            id=channel_id,
        ).execute()

        items = response.get("items", [])
        if not items:
            return {"error": f"채널을 찾을 수 없습니다: {channel_id}"}

        channel = items[0]
        snippet = channel.get("snippet", {})
        stats = channel.get("statistics", {})

        return {
            "channel_id": channel_id,
            "title": snippet.get("title", ""),
            "description": snippet.get("description", "")[:200],
            "custom_url": snippet.get("customUrl", ""),
            "published_at": snippet.get("publishedAt", ""),
            "subscriber_count": int(stats.get("subscriberCount", 0)),
            "total_views": int(stats.get("viewCount", 0)),
            "video_count": int(stats.get("videoCount", 0)),
            "hidden_subscriber_count": stats.get("hiddenSubscriberCount", False),
            "retrieved_at": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error("채널 통계 조회 실패: %s", e)
        return {"error": f"채널 통계 조회 실패: {e}"}


def _get_recent_videos(channel_id: str, limit: int = 10) -> dict[str, Any]:
    """채널의 최신 영상 목록과 각 영상의 통계를 조회합니다."""
    try:
        youtube = _get_youtube_service()

        ch_response = youtube.channels().list(
            part="contentDetails",
            id=channel_id,
        ).execute()

        ch_items = ch_response.get("items", [])
        if not ch_items:
            return {"error": f"채널을 찾을 수 없습니다: {channel_id}"}

        uploads_playlist_id = (
            ch_items[0]
            .get("contentDetails", {})
            .get("relatedPlaylists", {})
            .get("uploads", "")
        )
        if not uploads_playlist_id:
            return {"error": "업로드 재생목록을 찾을 수 없습니다."}

        playlist_response = youtube.playlistItems().list(
            part="snippet",
            playlistId=uploads_playlist_id,
            maxResults=min(limit, 50),
        ).execute()

        video_ids: list[str] = []
        video_snippets: dict[str, dict] = {}
        for item in playlist_response.get("items", []):
            vid = item["snippet"]["resourceId"]["videoId"]
            video_ids.append(vid)
            video_snippets[vid] = {
                "title": item["snippet"].get("title", ""),
                "published_at": item["snippet"].get("publishedAt", ""),
                "description": item["snippet"].get("description", "")[:150],
            }

        if not video_ids:
            return {"channel_id": channel_id, "videos": [], "count": 0}

        stats_map = _fetch_video_stats_batch(youtube, video_ids)

        videos: list[dict] = []
        for vid in video_ids:
            videos.append({
                "video_id": vid,
                **video_snippets.get(vid, {}),
                **stats_map.get(vid, {}),
            })

        return {
            "channel_id": channel_id,
            "count": len(videos),
            "videos": videos,
            "retrieved_at": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error("최신 영상 조회 실패: %s", e)
        return {"error": f"최신 영상 조회 실패: {e}"}


def _get_video_analytics(video_id: str) -> dict[str, Any]:
    """영상의 상세 통계(조회수, 좋아요, 댓글, 길이 등)를 조회합니다."""
    try:
        youtube = _get_youtube_service()

        response = youtube.videos().list(
            part="snippet,statistics,contentDetails,topicDetails",
            id=video_id,
        ).execute()

        items = response.get("items", [])
        if not items:
            return {"error": f"영상을 찾을 수 없습니다: {video_id}"}

        video = items[0]
        snippet = video.get("snippet", {})
        stats = video.get("statistics", {})
        content = video.get("contentDetails", {})
        topics = video.get("topicDetails", {})

        views = int(stats.get("viewCount", 0))
        likes = int(stats.get("likeCount", 0))
        comments = int(stats.get("commentCount", 0))

        engagement_rate = 0.0
        if views > 0:
            engagement_rate = round(((likes + comments) / views) * 100, 4)

        return {
            "video_id": video_id,
            "title": snippet.get("title", ""),
            "channel_title": snippet.get("channelTitle", ""),
            "published_at": snippet.get("publishedAt", ""),
            "description": snippet.get("description", "")[:300],
            "tags": snippet.get("tags", [])[:20],
            "category_id": snippet.get("categoryId", ""),
            "views": views,
            "likes": likes,
            "comments": comments,
            "engagement_rate_pct": engagement_rate,
            "duration": content.get("duration", ""),
            "definition": content.get("definition", ""),
            "caption": content.get("caption", "false"),
            "topic_categories": topics.get("topicCategories", []),
            "retrieved_at": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error("영상 분석 조회 실패: %s", e)
        return {"error": f"영상 분석 조회 실패: {e}"}


def _search_trending(
    query: str, region: str = "KR", limit: int = 10
) -> dict[str, Any]:
    """키워드로 트렌딩 영상을 검색합니다."""
    try:
        youtube = _get_youtube_service()

        search_response = youtube.search().list(
            part="snippet",
            q=query,
            type="video",
            order="viewCount",
            regionCode=region,
            maxResults=min(limit, 50),
        ).execute()

        video_ids: list[str] = []
        snippets_map: dict[str, dict] = {}
        for item in search_response.get("items", []):
            vid = item["id"]["videoId"]
            video_ids.append(vid)
            s = item.get("snippet", {})
            snippets_map[vid] = {
                "title": s.get("title", ""),
                "channel_title": s.get("channelTitle", ""),
                "published_at": s.get("publishedAt", ""),
                "description": s.get("description", "")[:150],
            }

        if not video_ids:
            return {"query": query, "region": region, "results": [], "count": 0}

        stats_map = _fetch_video_stats_batch(youtube, video_ids)

        results: list[dict] = []
        for vid in video_ids:
            results.append({
                "video_id": vid,
                **snippets_map.get(vid, {}),
                **stats_map.get(vid, {}),
            })

        return {
            "query": query,
            "region": region,
            "count": len(results),
            "results": results,
            "retrieved_at": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error("트렌딩 검색 실패: %s", e)
        return {"error": f"트렌딩 검색 실패: {e}"}


# ---------------------------------------------------------------------------
# MCP 서버 등록
# ---------------------------------------------------------------------------

if FastMCP is not None:
    mcp = FastMCP("youtube-data")

    @mcp.tool()
    def get_channel_stats(channel_id: str) -> dict[str, Any]:
        """채널의 구독자 수, 총 조회수, 영상 수를 조회합니다."""
        return _get_channel_stats(channel_id)

    @mcp.tool()
    def get_recent_videos(channel_id: str, limit: int = 10) -> dict[str, Any]:
        """채널의 최신 영상 목록과 각 영상의 통계를 조회합니다."""
        return _get_recent_videos(channel_id, limit)

    @mcp.tool()
    def get_video_analytics(video_id: str) -> dict[str, Any]:
        """영상의 상세 통계(조회수, 좋아요, 댓글, 길이 등)를 조회합니다."""
        return _get_video_analytics(video_id)

    @mcp.tool()
    def search_trending(query: str, region: str = "KR", limit: int = 10) -> dict[str, Any]:
        """키워드로 트렌딩 영상을 검색합니다."""
        return _search_trending(query, region, limit)

else:
    mcp = None
    get_channel_stats = _get_channel_stats
    get_recent_videos = _get_recent_videos
    get_video_analytics = _get_video_analytics
    search_trending = _search_trending


if __name__ == "__main__":
    if mcp is None:
        print("mcp 패키지 미설치. pip install 'mcp[cli]' 후 다시 실행하세요.")
    else:
        mcp.run()
