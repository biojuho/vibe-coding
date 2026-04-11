"""Notion page query and data extraction.

Mixin: NotionQueryMixin — 조회·검색·레코드 추출.
"""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)

_STATUS_ALIASES: dict[str, tuple[str, ...]] = {
    "검토필요": ("검토필요", "검토 필요", "검토대기", "대기", "보류"),
    "승인됨": ("승인됨", "승인", "발행승인", "발행 승인", "게시승인"),
    "업로드완료": ("업로드완료", "업로드 완료", "발행완료", "게시완료"),
    "패스": ("패스", "반려", "거절"),
    "초안생성": ("초안생성", "초안 생성", "초안", "생성됨"),
    "수정중": ("수정중", "수정 중"),
}


def _utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _parse_isoish_naive(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(tzinfo=None)
    except (TypeError, ValueError):
        return None


def _normalize_status_token(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"[\W_]+", "", str(value).strip(), flags=re.UNICODE).lower()


def _canonical_status_name(value: Any) -> str:
    normalized = _normalize_status_token(value)
    if not normalized:
        return ""

    for canonical, aliases in _STATUS_ALIASES.items():
        alias_tokens = {_normalize_status_token(alias) for alias in aliases}
        if normalized in alias_tokens:
            return canonical

    return str(value).strip()


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
            value = (data.get("status") or {}).get("name", default)
            if semantic_key == "status":
                return _canonical_status_name(value) or default
            return value
        if prop_type == "select":
            value = (data.get("select") or {}).get("name", default)
            if semantic_key == "status":
                return _canonical_status_name(value) or default
            return value
        if prop_type == "multi_select":
            values = [item.get("name", "") for item in data.get("multi_select", []) if item.get("name")]
            return values or default
        if prop_type == "date":
            return (data.get("date") or {}).get("start", default)
        return default

    def _status_option_names(self) -> list[str]:
        prop_name = self.props.get("status")
        if not prop_name:
            return []

        meta = self._db_properties.get(prop_name) or {}
        prop_type = meta.get("type")
        if prop_type not in {"status", "select"}:
            return []

        raw_options = ((meta.get(prop_type) or {}).get("options")) or []
        return [str(option.get("name", "")).strip() for option in raw_options if str(option.get("name", "")).strip()]

    def _resolve_status_filter_value(self, requested_status: str) -> str:
        option_names = self._status_option_names()
        if not option_names:
            return requested_status

        requested_token = _normalize_status_token(requested_status)
        for option_name in option_names:
            if option_name == requested_status or _normalize_status_token(option_name) == requested_token:
                return option_name

        requested_canonical = _canonical_status_name(requested_status)
        if requested_canonical:
            for option_name in option_names:
                if _canonical_status_name(option_name) == requested_canonical:
                    return option_name

        return requested_status

    def _status_matches(self, actual_status: Any, requested_status: str) -> bool:
        actual_token = _normalize_status_token(actual_status)
        requested_token = _normalize_status_token(requested_status)
        if actual_token and actual_token == requested_token:
            return True

        actual_canonical = _canonical_status_name(actual_status)
        requested_canonical = _canonical_status_name(requested_status)
        return bool(actual_canonical and requested_canonical and actual_canonical == requested_canonical)

    async def _scan_pages_by_status(self, status_name: str, limit: int) -> list[dict[str, Any]]:
        matched: list[dict[str, Any]] = []
        start_cursor = None
        page_size = min(100, max(limit * 5, 50))

        for _ in range(5):
            query_kwargs: dict[str, Any] = {"page_size": page_size}
            if start_cursor:
                query_kwargs["start_cursor"] = start_cursor

            response = await self.query_collection(**query_kwargs)
            for page in response.get("results", []):
                actual_status = self.get_page_property_value(page, "status")
                if self._status_matches(actual_status, status_name):
                    matched.append(page)
                    if len(matched) >= limit:
                        return matched[:limit]

            next_cursor = response.get("next_cursor")
            if not response.get("has_more") or not next_cursor:
                break
            start_cursor = next_cursor

        return matched[:limit]

    def extract_page_record(self, page: dict[str, Any]) -> dict[str, Any]:
        """Notion 페이지를 정제된 dict 레코드로 변환."""
        record = {"page_id": page.get("id"), "page_url": page.get("url")}
        for semantic_key in self.DEFAULT_PROPS:
            record[semantic_key] = self.get_page_property_value(page, semantic_key)
        record["text"] = record.get("tweet_body") or ""
        record["draft_style"] = record.get("chosen_draft_type") or "공감형"
        return record

    async def get_top_performing_posts(self, limit=5, lookback_days=30, minimum_posts=20, allow_fallback_examples=True):
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
            cutoff = _utcnow_naive() - timedelta(days=lookback_days)
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
            if len(filtered) < minimum_posts and allow_fallback_examples:
                approved = await self.get_recent_approved_posts(limit=limit, lookback_days=lookback_days)
                if approved:
                    return approved[:limit]
            return filtered[:limit]
        except Exception as exc:
            logger.error("Failed to fetch top performing posts: %s", exc)
            return []

    async def get_recent_approved_posts(self, limit=5, lookback_days=30):
        """최근 승인된 인간 선택 포스트를 few-shot 후보로 조회."""
        if not await self.ensure_schema():
            return []
        try:
            pages = await self.get_pages_by_status("승인됨", limit=max(limit * 4, 20))
            cutoff = _utcnow_naive() - timedelta(days=lookback_days)
            records: list[dict[str, Any]] = []
            for page in pages:
                record = self.extract_page_record(page)
                start = record.get("published_at") or record.get("date")
                if start:
                    try:
                        normalized = datetime.fromisoformat(str(start).replace("Z", "+00:00")).replace(tzinfo=None)
                        if normalized < cutoff:
                            continue
                    except ValueError:
                        pass
                if record.get("text"):
                    records.append(record)

            records.sort(
                key=lambda item: (
                    str(item.get("published_at") or item.get("date") or ""),
                    float(item.get("final_rank_score", 0) or 0),
                ),
                reverse=True,
            )
            return records[:limit]
        except Exception as exc:
            logger.error("Failed to fetch approved fallback posts: %s", exc)
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

    async def get_pages_by_status(self, status_name: str, limit=20):
        """리뷰 상태별 페이지 목록 조회."""
        if not await self.ensure_schema():
            return []

        semantic_key = "status"
        prop_name = self.props.get(semantic_key)
        if not prop_name:
            return []
        prop_type = self._db_properties[prop_name]["type"]
        resolved_status = self._resolve_status_filter_value(status_name)
        if prop_type == "status":
            filter_payload = {"property": prop_name, "status": {"equals": resolved_status}}
        else:
            filter_payload = {"property": prop_name, "select": {"equals": resolved_status}}
        try:
            response = await self.query_collection(filter=filter_payload, page_size=limit)
            return response.get("results", [])
        except Exception as exc:
            logger.warning(
                "get_pages_by_status query failed (status=%s, resolved=%s): %s. Falling back to collection scan.",
                status_name,
                resolved_status,
                exc,
            )
            try:
                return await self._scan_pages_by_status(status_name, limit=limit)
            except Exception as scan_exc:
                logger.warning("get_pages_by_status fallback scan failed (status=%s): %s. Returning empty.", status_name, scan_exc)
                return []

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

        cutoff = _utcnow_naive() - timedelta(days=days)
        try:
            response = await self._safe_notion_call(
                self.client.search,
                query="",
                filter={"value": "page", "property": "object"},
                sort={"direction": "descending", "timestamp": "last_edited_time"},
                page_size=min(100, max(limit, 20)),  # API limit 100 per request
            )

            all_results = response.get("results", [])
            results = []

            for r in all_results:
                parent = r.get("parent", {})
                p_type = parent.get("type")
                p_id = parent.get(p_type, "") if p_type else ""

                # Check DB match
                if p_type in ["database_id", "data_source_id"] and p_id.replace("-", "") == self.database_id.replace(
                    "-", ""
                ):
                    # Filter by date if applicable
                    normalized = _parse_isoish_naive(r.get("created_time"))
                    if normalized and normalized < cutoff:
                        continue
                    results.append(r)

            if results:
                return results[:limit]
        except Exception as exc:
            logger.warning("get_recent_pages search failed: %s", exc)

        try:
            date_prop = self.props.get("date")
            sorts = (
                [{"property": date_prop, "direction": "descending"}]
                if date_prop and date_prop in self._db_properties
                else [{"timestamp": "last_edited_time", "direction": "descending"}]
            )
            response = await self.query_collection(
                page_size=min(100, max(limit, 20)),
                sorts=sorts,
            )
            results = []
            for page in response.get("results", []):
                normalized = _parse_isoish_naive(self.get_page_property_value(page, "date"))
                if normalized is None:
                    normalized = _parse_isoish_naive(page.get("created_time") or page.get("last_edited_time"))
                if normalized and normalized < cutoff:
                    continue
                results.append(page)
            return results[:limit]
        except Exception as exc:
            logger.warning("get_recent_pages collection fallback failed: %s", exc)
            return []

    async def fetch_recent_records(self, lookback_days: int = 30, limit: int = 100) -> list[dict]:
        """최근 등록된 페이지를 조회하고 파싱된 레코드 구조로 반환합니다.

        뉴스레터 스케줄러 등에서 정제된 데이터 기반 큐레이션 시 사용됩니다.
        """
        pages = await self.get_recent_pages(days=lookback_days, limit=limit)
        return [self.extract_page_record(page) for page in pages]
