"""Notion 기반 콘텐츠 캘린더 — 주제 관리, 상태 추적, 중복 방지, 트렌드 제안.

사용법:
    # CLI에서 주제 추가
    python -m shorts_maker_v2.utils.content_calendar add "GPT-5 발표 임박" --channel ai_tech

    # pending 주제 조회
    python -m shorts_maker_v2.utils.content_calendar list --channel ai_tech --status pending

    # orchestrator에서 --from-db 모드로 사용
    python -m shorts_maker_v2 batch --from-db --channel ai_tech --limit 3

    # 다음 예정 주제 가져오기 (scheduled_date 기준 정렬)
    calendar.get_next_topics(channel="ai_tech", count=3)

    # 트렌드 기반 주제 제안 (기존 주제와 중복 제거)
    calendar.suggest_topics_from_trends(trends, existing_topics)

    # 주간 주제 다양성 보장
    calendar.balance_weekly_topics(channel="ai_tech", topics=candidate_list)

    # 주제 사용 처리 (pending → in_progress)
    calendar.mark_topic_used(notion_page_id="abc-123")
"""
from __future__ import annotations

import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)

try:
    import requests as _req
except ImportError:
    _req = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_title(prop: dict) -> str:
    """Notion title 속성에서 텍스트 추출."""
    if isinstance(prop, dict):
        title_list = prop.get("title", [])
        if title_list and isinstance(title_list, list):
            return title_list[0].get("text", {}).get("content", "")
    return ""


def _extract_select(prop: dict) -> str:
    """Notion select 속성에서 선택값 추출."""
    select = prop.get("select")
    if isinstance(select, dict):
        return select.get("name", "")
    return ""


def _extract_date(prop: dict) -> str:
    """Notion date 속성에서 시작일 문자열 추출 (YYYY-MM-DD 등)."""
    date_obj = prop.get("date")
    if isinstance(date_obj, dict):
        return date_obj.get("start", "")
    return ""


def _tokenize(text: str) -> set[str]:
    """텍스트를 소문자 단어 토큰 집합으로 변환.

    한국어/영어 혼합 텍스트에서 공백·구두점 기준 분리.
    """
    import re
    return set(re.findall(r"[\w]+", text.lower()))


def _jaccard_similarity(a: str, b: str) -> float:
    """두 문자열 간의 Jaccard 유사도 (0.0 ~ 1.0)."""
    tokens_a = _tokenize(a)
    tokens_b = _tokenize(b)
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = tokens_a & tokens_b
    union = tokens_a | tokens_b
    return len(intersection) / len(union)


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------

class NotionContentCalendar:
    """Notion DB 기반 콘텐츠 캘린더 (주제 CRUD + 상태 추적 + 트렌드 제안)."""

    NOTION_API_URL = "https://api.notion.com/v1"
    NOTION_VERSION = "2022-06-28"

    # Jaccard 임계값: 이보다 높으면 "너무 유사"로 판정
    SIMILARITY_THRESHOLD = 0.5

    def __init__(
        self,
        api_key: str | None = None,
        database_id: str | None = None,
    ):
        self.api_key = api_key or os.getenv("NOTION_API_KEY", "")
        self.database_id = database_id or os.getenv("NOTION_TRACKING_DB_ID", "")
        if not self.api_key or not self.database_id:
            raise ValueError("NOTION_API_KEY and NOTION_TRACKING_DB_ID are required.")
        self._headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Notion-Version": self.NOTION_VERSION,
        }

    # ------------------------------------------------------------------
    # Low-level API
    # ------------------------------------------------------------------

    def _request(self, method: str, endpoint: str, json_body: dict | None = None) -> dict:
        """Notion API 호출 래퍼."""
        if _req is None:
            raise ImportError("requests package is required for Notion integration.")
        url = f"{self.NOTION_API_URL}{endpoint}"
        resp = _req.request(method, url, headers=self._headers, json=json_body, timeout=30)
        resp.raise_for_status()
        return resp.json()

    # ------------------------------------------------------------------
    # Existing methods (backward-compatible)
    # ------------------------------------------------------------------

    def get_pending_topics(self, channel: str = "", limit: int = 5) -> list[dict[str, Any]]:
        """Notion DB에서 pending 상태의 주제 조회."""
        filter_body: dict[str, Any] = {
            "filter": {
                "and": [
                    {"property": "Status", "status": {"equals": "pending"}},
                ]
            },
            "page_size": min(limit, 100),
            "sorts": [{"property": "Created", "direction": "ascending"}],
        }
        if channel:
            filter_body["filter"]["and"].append(
                {"property": "Channel", "select": {"equals": channel}}
            )

        try:
            result = self._request("POST", f"/databases/{self.database_id}/query", filter_body)
            pages = result.get("results", [])
        except Exception as exc:
            logger.warning("Notion query failed: %s", exc)
            return []

        topics = []
        for page in pages[:limit]:
            props = page.get("properties", {})
            topic = _extract_title(props.get("Topic") or props.get("Name") or props.get("title", {}))
            ch = _extract_select(props.get("Channel", {}))
            topics.append({
                "id": page["id"],
                "topic": topic,
                "channel": ch,
                "status": "pending",
            })
        return topics

    def update_status(
        self,
        page_id: str,
        status: str,
        job_id: str = "",
        video_path: str = "",
        cost_usd: float = 0,
        duration_sec: float = 0,
    ) -> None:
        """주제의 상태를 업데이트합니다."""
        properties: dict[str, Any] = {
            "Status": {"status": {"name": status}},
        }
        if job_id:
            properties["Job ID"] = {"rich_text": [{"text": {"content": job_id}}]}
        if video_path:
            properties["Video Path"] = {"rich_text": [{"text": {"content": video_path[:2000]}}]}
        if cost_usd > 0:
            properties["Cost USD"] = {"number": round(cost_usd, 4)}
        if duration_sec > 0:
            properties["Duration"] = {"number": round(duration_sec, 1)}

        try:
            self._request("PATCH", f"/pages/{page_id}", {"properties": properties})
        except Exception as exc:
            logger.warning("Notion update failed for %s: %s", page_id, exc)

    def add_topic(self, topic: str, channel: str = "", scheduled_date: str = "") -> str | None:
        """새로운 주제를 Notion DB에 추가합니다. 중복 체크 포함."""
        # 중복 체크
        existing = self._check_duplicate(topic)
        if existing:
            logger.info("Topic already exists in DB: %s", topic)
            return None

        properties: dict[str, Any] = {
            "Name": {"title": [{"text": {"content": topic}}]},
            "Status": {"status": {"name": "pending"}},
        }
        if channel:
            properties["Channel"] = {"select": {"name": channel}}
        if scheduled_date:
            properties["Scheduled Date"] = {"date": {"start": scheduled_date}}

        try:
            result = self._request("POST", "/pages", {
                "parent": {"database_id": self.database_id},
                "properties": properties,
            })
            return result.get("id")
        except Exception as exc:
            logger.warning("Notion add topic failed: %s", exc)
            return None

    def _check_duplicate(self, topic: str) -> bool:
        """주제 중복 체크 (제목 기반 필터)."""
        try:
            result = self._request("POST", f"/databases/{self.database_id}/query", {
                "filter": {
                    "property": "Name",
                    "title": {"equals": topic},
                },
                "page_size": 1,
            })
            return len(result.get("results", [])) > 0
        except Exception:
            return False  # API 실패 시 중복 아님으로 간주

    # ------------------------------------------------------------------
    # New: get_next_topics
    # ------------------------------------------------------------------

    def get_next_topics(self, channel: str, count: int = 3) -> list[dict[str, Any]]:
        """채널별 다음 예정 주제를 scheduled_date 오름차순으로 반환.

        Args:
            channel: 채널 이름 (예: ``"ai_tech"``).
            count: 반환할 최대 주제 수.

        Returns:
            각 항목은 ``{"topic", "channel", "scheduled_date", "notion_page_id"}``
            키를 가진 dict 리스트. API 실패 시 빈 리스트.
        """
        filter_body: dict[str, Any] = {
            "filter": {
                "and": [
                    {"property": "Status", "status": {"equals": "pending"}},
                    {"property": "Channel", "select": {"equals": channel}},
                ]
            },
            "page_size": min(count, 100),
            "sorts": [{"property": "Scheduled Date", "direction": "ascending"}],
        }

        try:
            result = self._request(
                "POST", f"/databases/{self.database_id}/query", filter_body,
            )
            pages = result.get("results", [])
        except Exception as exc:
            logger.warning("get_next_topics failed for channel=%s: %s", channel, exc)
            return []

        topics: list[dict[str, Any]] = []
        for page in pages[:count]:
            props = page.get("properties", {})
            topic = _extract_title(
                props.get("Topic") or props.get("Name") or props.get("title", {}),
            )
            ch = _extract_select(props.get("Channel", {}))
            scheduled = _extract_date(props.get("Scheduled Date", {}))
            topics.append({
                "topic": topic,
                "channel": ch,
                "scheduled_date": scheduled,
                "notion_page_id": page["id"],
            })
        return topics

    # ------------------------------------------------------------------
    # New: mark_topic_used
    # ------------------------------------------------------------------

    def mark_topic_used(self, notion_page_id: str) -> bool:
        """주제 상태를 ``pending`` → ``in_progress`` 로 변경.

        Args:
            notion_page_id: Notion 페이지 ID.

        Returns:
            성공 시 ``True``, 실패 시 ``False``.
        """
        try:
            self._request("PATCH", f"/pages/{notion_page_id}", {
                "properties": {
                    "Status": {"status": {"name": "in_progress"}},
                },
            })
            logger.info("Marked topic %s as in_progress", notion_page_id)
            return True
        except Exception as exc:
            logger.warning("mark_topic_used failed for %s: %s", notion_page_id, exc)
            return False

    # ------------------------------------------------------------------
    # New: suggest_topics_from_trends
    # ------------------------------------------------------------------

    @staticmethod
    def suggest_topics_from_trends(
        trends: list[str],
        existing_topics: list[str],
    ) -> list[str]:
        """트렌드 목록에서 기존 주제와 겹치지 않는 제안만 필터링.

        단어 겹침 기반 Jaccard 유사도를 사용하며, 임계값(0.5)을 초과하면
        해당 트렌드를 제외합니다. LLM 호출 없이 동작합니다.

        Args:
            trends: 후보 트렌드 문자열 리스트.
            existing_topics: 이미 존재하는 주제 리스트.

        Returns:
            기존 주제와 유사하지 않은 트렌드 리스트.
        """
        threshold = NotionContentCalendar.SIMILARITY_THRESHOLD
        suggestions: list[str] = []
        seen_normalized: set[str] = set()

        for trend in trends:
            trend_stripped = trend.strip()
            if not trend_stripped:
                continue

            # 트렌드 내 자체 중복 제거 (정규화된 소문자 비교)
            norm = trend_stripped.lower()
            if norm in seen_normalized:
                continue

            # 기존 주제와 유사도 비교
            too_similar = any(
                _jaccard_similarity(trend_stripped, existing)
                >= threshold
                for existing in existing_topics
            )
            if not too_similar:
                suggestions.append(trend_stripped)
                seen_normalized.add(norm)

        return suggestions

    # ------------------------------------------------------------------
    # New: balance_weekly_topics
    # ------------------------------------------------------------------

    def balance_weekly_topics(
        self,
        channel: str,
        topics: list[str],
    ) -> list[str]:
        """최근 7일 게시 주제와 유사한 후보를 제거하여 다양성 보장.

        Args:
            channel: 채널 이름.
            topics: 후보 주제 리스트.

        Returns:
            최근 게시 주제와 겹치지 않는 후보만 포함한 리스트.
            API 실패 시 원본 ``topics`` 를 그대로 반환 (안전한 폴백).
        """
        recent_topics = self._get_recent_topics(channel, days=7)
        if not recent_topics:
            # API 실패이거나 최근 주제가 없으면 필터 없이 반환
            return list(topics)

        recent_titles = [t["topic"] for t in recent_topics if t.get("topic")]
        threshold = self.SIMILARITY_THRESHOLD

        balanced: list[str] = []
        for candidate in topics:
            candidate_stripped = candidate.strip()
            if not candidate_stripped:
                continue
            too_similar = any(
                _jaccard_similarity(candidate_stripped, recent)
                >= threshold
                for recent in recent_titles
            )
            if not too_similar:
                balanced.append(candidate_stripped)

        return balanced

    def _get_recent_topics(
        self,
        channel: str,
        days: int = 7,
    ) -> list[dict[str, Any]]:
        """최근 N일 내에 ``in_progress`` 또는 ``done`` 상태인 주제 조회.

        Args:
            channel: 채널 이름.
            days: 조회할 과거 일수.

        Returns:
            ``{"topic", "channel", "status"}`` dict 리스트. 실패 시 빈 리스트.
        """
        since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")

        filter_body: dict[str, Any] = {
            "filter": {
                "and": [
                    {"property": "Channel", "select": {"equals": channel}},
                    {
                        "or": [
                            {"property": "Status", "status": {"equals": "in_progress"}},
                            {"property": "Status", "status": {"equals": "done"}},
                        ],
                    },
                    {
                        "property": "Scheduled Date",
                        "date": {"on_or_after": since},
                    },
                ],
            },
            "page_size": 100,
            "sorts": [{"property": "Scheduled Date", "direction": "descending"}],
        }

        try:
            result = self._request(
                "POST", f"/databases/{self.database_id}/query", filter_body,
            )
            pages = result.get("results", [])
        except Exception as exc:
            logger.warning("_get_recent_topics failed for channel=%s: %s", channel, exc)
            return []

        topics: list[dict[str, Any]] = []
        for page in pages:
            props = page.get("properties", {})
            topic = _extract_title(
                props.get("Topic") or props.get("Name") or props.get("title", {}),
            )
            ch = _extract_select(props.get("Channel", {}))
            status_prop = props.get("Status", {})
            status_val = ""
            if isinstance(status_prop, dict):
                status_inner = status_prop.get("status")
                if isinstance(status_inner, dict):
                    status_val = status_inner.get("name", "")
            topics.append({
                "topic": topic,
                "channel": ch,
                "status": status_val,
            })
        return topics
