"""72h 성과 수집 루프: 발행 후 72시간 이내 콘텐츠의 성과를 자동 수집.

Notion DB에서 '발행완료' 상태이며 '성과 등급'이 미설정인 콘텐츠를 조회하고,
PerformanceTracker로 기록한 뒤 Notion에 등급을 업데이트합니다.

플랫폼별 API 연동:
  - Twitter/X: X_BEARER_TOKEN 환경변수 필요 (x_analytics.py 위임)
  - Threads:   THREADS_ACCESS_TOKEN 환경변수 필요 (Meta Graph API)
  - Naver Blog: 공개 성과 수집 API 없음 → 수동 입력 안내

사용법:
    python -m pipeline.performance_collector          # CLI 독립 실행
    await run_performance_collection(config)          # 파이프라인 내 호출
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)

# 성과 수집 대상 시간 (발행 후 72h)
COLLECTION_WINDOW_HOURS = 72

# Threads API 엔드포인트
_THREADS_API_BASE = "https://graph.threads.net/v1.0"

# URL에서 ID 추출용 패턴
_TWITTER_URL_RE = re.compile(r"x\.com/[^/]+/status/(\d+)|twitter\.com/[^/]+/status/(\d+)")
_THREADS_URL_RE = re.compile(r"threads\.net/t/([A-Za-z0-9_-]+)")


# ── URL 파싱 ──────────────────────────────────────────────────────────────


def _parse_tweet_id(url: str) -> str | None:
    """Tweet URL에서 tweet_id 추출."""
    m = _TWITTER_URL_RE.search(url or "")
    if m:
        return m.group(1) or m.group(2)
    return None


def _parse_threads_media_id(url: str) -> str | None:
    """Threads 게시물 URL에서 media shortcode 추출.

    Threads Graph API는 shortcode가 아닌 numeric media_id를 요구하므로,
    URL에서 shortcode만 추출하고 실제 ID 조회는 별도 API로 처리됩니다.
    """
    m = _THREADS_URL_RE.search(url or "")
    if m:
        return m.group(1)
    return None


# ── 플랫폼별 API 연동 ────────────────────────────────────────────────────


def _fetch_twitter_metrics(tweet_id: str) -> dict[str, float] | None:
    """X API v2로 트윗 성과 지표 수집.

    X_BEARER_TOKEN 환경변수가 없거나 API 오류 시 None 반환.
    (x_analytics.py의 collect_tweet_stats를 직접 위임)
    """
    bearer_token = os.getenv("X_BEARER_TOKEN", "")
    if not bearer_token:
        logger.info("[PerfCollector] X_BEARER_TOKEN 없음 — Twitter 성과 수집 스킵")
        return None

    try:
        import requests  # type: ignore[import-untyped]

        resp = requests.get(
            "https://api.twitter.com/2/tweets",
            params={
                "ids": tweet_id,
                "tweet.fields": "public_metrics",
            },
            headers={"Authorization": f"Bearer {bearer_token}"},
            timeout=15,
        )

        if resp.status_code == 429:
            logger.warning("[PerfCollector] Twitter API rate limit (429) — 스킵")
            return None

        if resp.status_code != 200:
            logger.warning(
                "[PerfCollector] Twitter API 오류 %d: %s",
                resp.status_code,
                resp.text[:200],
            )
            return None

        data = resp.json().get("data", [])
        if not data:
            logger.debug("[PerfCollector] tweet_id=%s 결과 없음", tweet_id)
            return None

        pm = data[0].get("public_metrics", {})
        return {
            "likes": float(pm.get("like_count", 0)),
            "retweets": float(pm.get("retweet_count", 0)),
            "impressions": float(pm.get("impression_count", 0)),
            "replies": float(pm.get("reply_count", 0)),
        }

    except Exception as exc:
        logger.warning("[PerfCollector] Twitter 지표 수집 실패: %s", exc)
        return None


def _fetch_threads_metrics(shortcode: str) -> dict[str, float] | None:
    """Threads Graph API로 미디어 성과 지표 수집.

    THREADS_ACCESS_TOKEN 환경변수가 없거나 API 오류 시 None 반환.

    Note:
        Threads는 shortcode → numeric media_id 변환이 필요합니다.
        access_token을 소유한 계정의 미디어만 조회 가능합니다.
    """
    access_token = os.getenv("THREADS_ACCESS_TOKEN", "")
    if not access_token:
        logger.info("[PerfCollector] THREADS_ACCESS_TOKEN 없음 — Threads 성과 수집 스킵")
        return None

    try:
        import requests  # type: ignore[import-untyped]

        # Step 1: shortcode → media_id (사용자 미디어 목록에서 검색)
        media_resp = requests.get(
            f"{_THREADS_API_BASE}/me/threads",
            params={
                "fields": "id,permalink",
                "limit": 100,
                "access_token": access_token,
            },
            timeout=15,
        )

        if media_resp.status_code != 200:
            logger.warning(
                "[PerfCollector] Threads 미디어 목록 조회 실패 %d: %s",
                media_resp.status_code,
                media_resp.text[:200],
            )
            return None

        media_id = None
        for item in media_resp.json().get("data", []):
            permalink = item.get("permalink", "")
            if shortcode in permalink:
                media_id = item.get("id")
                break

        if not media_id:
            logger.debug("[PerfCollector] Threads shortcode=%s → media_id 못 찾음", shortcode)
            return None

        # Step 2: media_id → insights
        insights_resp = requests.get(
            f"{_THREADS_API_BASE}/{media_id}/insights",
            params={
                "metric": "likes,replies,reposts,quotes,views",
                "access_token": access_token,
            },
            timeout=15,
        )

        if insights_resp.status_code != 200:
            logger.warning(
                "[PerfCollector] Threads insights 조회 실패 %d: %s",
                insights_resp.status_code,
                insights_resp.text[:200],
            )
            return None

        metrics: dict[str, float] = {}
        for entry in insights_resp.json().get("data", []):
            name = entry.get("name", "")
            value = float(entry.get("values", [{}])[0].get("value", 0) if entry.get("values") else 0)
            if name in ("likes", "replies", "reposts", "quotes", "views"):
                key = "comments" if name == "replies" else name
                metrics[key] = value

        logger.info(
            "[PerfCollector] Threads 지표 수집 완료 (shortcode=%s): %s",
            shortcode,
            metrics,
        )
        return metrics if metrics else None

    except Exception as exc:
        logger.warning("[PerfCollector] Threads 지표 수집 실패: %s", exc)
        return None


def _fetch_platform_metrics(
    platform: str,
    page_info: dict[str, Any],
) -> dict[str, float] | None:
    """플랫폼별 실제 성과 지표를 수집합니다.

    Returns:
        수집된 지표 dict, 또는 수집 불가 시 None.
        None이면 PerformanceTracker 기록을 스킵합니다 (수동 입력 대기).
    """
    if platform == "twitter":
        tweet_url = page_info.get("tweet_url", "")
        tweet_id = _parse_tweet_id(tweet_url)
        if not tweet_id:
            logger.debug(
                "[PerfCollector] 트윗 ID 없음 (page_id=%s) — 수동 입력 대기",
                page_info.get("page_id", "")[:8],
            )
            return None
        return _fetch_twitter_metrics(tweet_id)

    elif platform == "threads":
        threads_url = page_info.get("threads_url", "")
        shortcode = _parse_threads_media_id(threads_url)
        if not shortcode:
            logger.debug(
                "[PerfCollector] Threads shortcode 없음 (page_id=%s) — 수동 입력 대기",
                page_info.get("page_id", "")[:8],
            )
            return None
        return _fetch_threads_metrics(shortcode)

    elif platform == "naver_blog":
        logger.info(
            "[PerfCollector] Naver Blog 공개 성과 API 없음 — 수동 입력 필요 (page_id=%s)",
            page_info.get("page_id", "")[:8],
        )
        return None

    else:
        logger.debug("[PerfCollector] 알 수 없는 플랫폼: %s", platform)
        return None


# ── Notion 조회 ──────────────────────────────────────────────────────────


async def _query_published_pages(
    notion_uploader: Any,
    window_hours: int = COLLECTION_WINDOW_HOURS,
) -> list[dict[str, Any]]:
    """Notion DB에서 성과 미수집 발행 콘텐츠 조회.

    조건:
      - 승인 상태 = '발행완료'
      - 성과 등급 이 비어 있음
      - 생성일 이 최근 window_hours 이내
    """
    cutoff = (datetime.now(tz=timezone.utc) - timedelta(hours=window_hours)).isoformat()

    filter_payload = {
        "and": [
            {
                "property": notion_uploader.props.get("status", "상태"),
                "select": {"equals": "발행완료"},
            },
            {
                "property": notion_uploader.props.get("performance_grade", "성과 등급"),
                "select": {"is_empty": True},
            },
            {
                "property": notion_uploader.props.get("date", "생성일"),
                "date": {"on_or_after": cutoff},
            },
        ]
    }

    try:
        response = await notion_uploader.query_collection(
            page_size=50,
            filter=filter_payload,
        )
        pages = response.get("results", [])
        logger.info("72h 성과 미수집 콘텐츠 %d건 발견", len(pages))
        return pages
    except Exception as exc:
        logger.warning("성과 수집 대상 조회 실패: %s", exc)
        return []


def _extract_page_info(page: dict[str, Any]) -> dict[str, Any]:
    """Notion 페이지에서 성과 수집에 필요한 메타데이터 추출."""
    props = page.get("properties", {})
    page_id = page.get("id", "")

    def _get_text(prop_data: dict) -> str:
        """rich_text 또는 title에서 텍스트 추출."""
        for key in ("title", "rich_text"):
            items = prop_data.get(key, [])
            if items:
                return items[0].get("plain_text", "")
        return ""

    def _get_url(prop_data: dict) -> str:
        return prop_data.get("url", "") or ""

    def _get_select(prop_data: dict) -> str:
        sel = prop_data.get("select")
        return sel.get("name", "") if sel else ""

    def _get_multi_select(prop_data: dict) -> list[str]:
        items = prop_data.get("multi_select", [])
        return [item.get("name", "") for item in items]

    title = ""
    for prop_name, prop_data in props.items():
        if prop_data.get("type") == "title":
            title = _get_text(prop_data)
            break

    topic_cluster = ""
    emotion_axis = ""
    platforms: list[str] = []
    tweet_url = ""
    threads_url = ""

    for prop_name, prop_data in props.items():
        ptype = prop_data.get("type", "")
        name_lower = prop_name.lower()

        if "토픽" in prop_name or "topic" in name_lower:
            topic_cluster = _get_select(prop_data) if ptype == "select" else _get_text(prop_data)
        elif "감정" in prop_name or "emotion" in name_lower:
            emotion_axis = _get_select(prop_data) if ptype == "select" else _get_text(prop_data)
        elif "플랫폼" in prop_name or "platform" in name_lower:
            if ptype == "multi_select":
                platforms = _get_multi_select(prop_data)
        elif ("트윗 링크" in prop_name or "tweet" in name_lower) and ptype == "url":
            tweet_url = _get_url(prop_data)
        elif ("threads 링크" in prop_name or "threads" in name_lower) and ptype == "url":
            threads_url = _get_url(prop_data)

    return {
        "page_id": page_id,
        "title": title,
        "topic_cluster": topic_cluster,
        "emotion_axis": emotion_axis,
        "platforms": platforms or ["twitter"],  # 기본값
        "tweet_url": tweet_url,
        "threads_url": threads_url,
    }


# ── 메인 실행 ─────────────────────────────────────────────────────────────


async def run_performance_collection(
    config: Any = None,
    notion_uploader: Any = None,
) -> dict[str, Any]:
    """72h 성과 수집 루프 실행.

    Returns:
        수집 결과 요약 dict.
    """
    from pipeline.performance_tracker import PerformanceTracker

    tracker = PerformanceTracker(config)

    if notion_uploader is None:
        logger.warning("notion_uploader가 없어 성과 수집을 건너뜁니다.")
        return {"collected": 0, "skipped": 0, "error": "no_notion_uploader"}

    pages = await _query_published_pages(notion_uploader)
    if not pages:
        return {"collected": 0, "skipped": 0, "message": "수집 대상 없음"}

    collected = 0
    skipped = 0

    for page in pages:
        info = _extract_page_info(page)
        page_id = info["page_id"]

        if not page_id:
            skipped += 1
            continue

        for platform in info["platforms"]:
            platform_key = platform.lower().replace(" ", "_")
            if platform_key not in ("twitter", "threads", "naver_blog"):
                # 알려진 플랫폼 이름으로 변환
                if "x" in platform_key or "트위터" in platform:
                    platform_key = "twitter"
                elif "쓰레드" in platform:
                    platform_key = "threads"
                elif "블로그" in platform:
                    platform_key = "naver_blog"
                else:
                    continue

            # 실제 API 수집 시도 (키 없으면 None)
            metrics = _fetch_platform_metrics(platform_key, info)

            if metrics is None:
                # API 키 없거나 수집 불가 → 수동 입력 대기
                logger.debug(
                    "[PerfCollector] %s (%s) — 지표 없음, 수동 입력 대기",
                    info["title"][:30],
                    platform_key,
                )
                skipped += 1
                continue

            try:
                record = tracker.record_performance(
                    notion_page_id=page_id,
                    platform=platform_key,
                    metrics=metrics,
                    topic_cluster=info["topic_cluster"],
                    emotion_axis=info["emotion_axis"],
                )

                # Notion에 성과 등급 업데이트
                if notion_uploader and record.grade:
                    await notion_uploader.update_page_properties(
                        page_id=page_id,
                        updates={"performance_grade": record.grade},
                    )

                collected += 1
                logger.info(
                    "성과 수집 완료: %s (%s) → %s등급",
                    info["title"][:30],
                    platform_key,
                    record.grade,
                )
            except Exception as exc:
                logger.warning("성과 수집 실패 (%s): %s", page_id[:8], exc)
                skipped += 1

    result = {
        "collected": collected,
        "skipped": skipped,
        "total_pages": len(pages),
    }
    logger.info("72h 성과 수집 완료: %s", result)
    return result


# CLI 독립 실행
if __name__ == "__main__":
    import sys

    sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    from config import ConfigManager

    async def _main():
        config = ConfigManager()
        # Notion uploader 초기화
        from pipeline.notion_upload import NotionUploader

        uploader = NotionUploader(config)

        result = await run_performance_collection(config=config, notion_uploader=uploader)
        print(f"수집 결과: {result}")

    asyncio.run(_main())
