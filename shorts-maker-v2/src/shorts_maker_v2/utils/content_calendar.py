"""Notion 기반 콘텐츠 캘린더 — 주제 관리, 상태 추적, 중복 방지.

사용법:
    # CLI에서 주제 추가
    python -m shorts_maker_v2.utils.content_calendar add "GPT-5 발표 임박" --channel ai_tech

    # pending 주제 조회
    python -m shorts_maker_v2.utils.content_calendar list --channel ai_tech --status pending

    # orchestrator에서 --from-db 모드로 사용
    python -m shorts_maker_v2 batch --from-db --channel ai_tech --limit 3
"""
from __future__ import annotations

import os
import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

try:
    import requests as _req
except ImportError:
    _req = None  # type: ignore[assignment]


class NotionContentCalendar:
    """Notion DB 기반 콘텐츠 캘린더 (주제 CRUD + 상태 추적)."""

    NOTION_API_URL = "https://api.notion.com/v1"
    NOTION_VERSION = "2022-06-28"

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

    def _request(self, method: str, endpoint: str, json_body: dict | None = None) -> dict:
        """Notion API 호출 래퍼."""
        if _req is None:
            raise ImportError("requests package is required for Notion integration.")
        url = f"{self.NOTION_API_URL}{endpoint}"
        resp = _req.request(method, url, headers=self._headers, json=json_body, timeout=30)
        resp.raise_for_status()
        return resp.json()

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
