"""Notion page query and data extraction.

Mixin: NotionQueryMixin — 조회·검색·레코드 추출.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


class NotionQueryMixin:
    """Notion 페이지 조회, 검색, 데이터 추출을 담당하는 Mixin.

    사전 조건: ensure_schema, _db_properties, props, client, database_id,
    query_collection, DEFAULT_PROPS 등이 동일 클래스(NotionUploader)에
    합쳐져 있어야 합니다.
    """

    def get_page_property_value(self, page: dict[str, Any], semantic_key: str, default=None):
        """Notion 페이지에서 시맨틱 키에 해당하는 속성 값을 추출."""
        prop_name = self.props.get(semantic_key, semantic_key)
        properties = page.get("properties", {})
        data = properties.get(prop_name)
        if not data:
            return default

        prop_type = data.get("type")
        if prop_type == "title":
            return "".join(item.get("plain_text", "") for item in data.get("title", [])) or default
        if prop_type == "rich_text":
            return "".join(item.get("plain_text", "") for item in data.get("rich_text", [])) or default
        if prop_type == "number":
            return data.get("number", default)
        if prop_type == "checkbox":
            return data.get("checkbox", default)
        if prop_type == "url":
            return data.get("url", default)
        if prop_type == "status":
            return (data.get("status") or {}).get("name", default)
        if prop_type == "select":
            return (data.get("select") or {}).get("name", default)
        if prop_type == "date":
            return (data.get("date") or {}).get("start", default)
        return default

    def extract_page_record(self, page: dict[str, Any]) -> dict[str, Any]:
        """Notion 페이지를 정제된 dict 레코드로 변환."""
        record = {"page_id": page.get("id"), "page_url": page.get("url")}
        for semantic_key in self.DEFAULT_PROPS:
            record[semantic_key] = self.get_page_property_value(page, semantic_key)
        record["text"] = record.get("tweet_body") or ""
        record["draft_style"] = record.get("chosen_draft_type") or "공감형"
        return record

    async def get_top_performing_posts(self, limit=5, lookback_days=30, minimum_posts=20):
        """조회수 기준 상위 성과 포스트를 조회."""
        if not await self.ensure_schema():
            return []
        try:
            views_prop = self.props.get("views")
            if not views_prop or views_prop not in self._db_properties:
                return []
            response = await self.query_collection(
                filter={"property": views_prop, "number": {"greater_than": 0}},
                page_size=max(limit * 4, minimum_posts, 20),
            )
            records = [self.extract_page_record(page) for page in response.get("results", [])]
            cutoff = datetime.utcnow() - timedelta(days=lookback_days)
            filtered = []
            for record in records:
                start = record.get("published_at") or record.get("date")
                if start:
                    try:
                        normalized = datetime.fromisoformat(str(start).replace("Z", "+00:00")).replace(tzinfo=None)
                        if normalized < cutoff:
                            continue
                    except ValueError:
                        pass
                if record.get("text") and (record.get("views") or 0) > 0:
                    filtered.append(record)

            filtered.sort(
                key=lambda item: (
                    float(item.get("views", 0) or 0),
                    float(item.get("likes", 0) or 0),
                    float(item.get("retweets", 0) or 0),
                ),
                reverse=True,
            )
            if len(filtered) < minimum_posts:
                return filtered[:limit]
            return filtered[:limit]
        except Exception as exc:
            logger.error("Failed to fetch top performing posts: %s", exc)
            return []

    async def get_top_performing_tweets(self, limit=3):
        """상위 성과 트윗을 정제된 dict 형태로 반환."""
        records = await self.get_top_performing_posts(limit=limit, lookback_days=30, minimum_posts=0)
        return [
            {
                "views": item.get("views", 0),
                "text": item.get("text", ""),
                "topic_cluster": item.get("topic_cluster", "기타"),
                "hook_type": item.get("hook_type", "공감형"),
                "emotion_axis": item.get("emotion_axis", "공감"),
                "draft_style": item.get("draft_style", "공감형"),
            }
            for item in records
        ]

    async def get_pages_by_review_status(self, status_name: str, limit=20):
        """리뷰 상태별 페이지 목록 조회."""
        if not await self.ensure_schema():
            return []

        semantic_key = "review_status" if self.props.get("review_status") in self._db_properties else "status"
        prop_name = self.props[semantic_key]
        prop_type = self._db_properties[prop_name]["type"]
        if prop_type == "status":
            filter_payload = {"property": prop_name, "status": {"equals": status_name}}
        else:
            filter_payload = {"property": prop_name, "select": {"equals": status_name}}
        response = await self.query_collection(filter=filter_payload, page_size=limit)
        return response.get("results", [])

    async def search_pages_by_title(self, keyword: str, limit: int = 30) -> list:
        """서버사이드 제목 키워드 필터로 Jaccard 비교 후보를 좁힘.

        Notion title.contains 필터 사용 → 로컬 O(n²) 비교 대상을 대폭 감소.
        실패 시 빈 리스트 반환 (호출자가 get_recent_pages 폴백 담당).
        """
        if not await self.ensure_schema():
            return []
        title_prop = self.props.get("title")
        if not title_prop or title_prop not in self._db_properties:
            return []
        try:
            filter_payload = {"property": title_prop, "title": {"contains": keyword}}
            response = await self.query_collection(filter=filter_payload, page_size=limit)
            return response.get("results", [])
        except Exception as exc:
            logger.warning("서버사이드 제목 검색 실패: %s", exc)
            return []

    async def get_recent_pages(self, days=7, limit=100):
        """최근 N일 내 생성된 페이지 조회 (Notion search API 사용)."""
        if not await self.ensure_schema():
            return []

        try:
            response = await self.client.search(
                query="",
                filter={"value": "page", "property": "object"},
                sort={"direction": "descending", "timestamp": "last_edited_time"},
                page_size=min(100, max(limit, 20))  # API limit 100 per request
            )

            all_results = response.get("results", [])
            results = []
            cutoff = datetime.utcnow() - timedelta(days=days)

            for r in all_results:
                parent = r.get("parent", {})
                p_type = parent.get("type")
                p_id = parent.get(p_type, "") if p_type else ""

                # Check DB match
                if p_type in ["database_id", "data_source_id"] and p_id.replace("-", "") == self.database_id.replace("-", ""):
                    # Filter by date if applicable
                    created_time = r.get("created_time")
                    if created_time:
                        try:
                            normalized = datetime.fromisoformat(str(created_time).replace("Z", "+00:00")).replace(tzinfo=None)
                            if normalized < cutoff:
                                continue
                        except Exception:
                            pass
                    results.append(r)

            return results[:limit]
        except Exception as exc:
            logger.warning("get_recent_pages search failed: %s", exc)
            return []

    async def fetch_recent_records(self, lookback_days: int = 30, limit: int = 100) -> list[dict]:
        """최근 등록된 페이지를 조회하고 파싱된 레코드 구조로 반환합니다.

        뉴스레터 스케줄러 등에서 정제된 데이터 기반 큐레이션 시 사용됩니다.
        """
        pages = await self.get_recent_pages(days=lookback_days, limit=limit)
        return [self.extract_page_record(page) for page in pages]
