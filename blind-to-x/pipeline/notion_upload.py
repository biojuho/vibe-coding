"""Notion uploader with schema auto-detection and review queue helpers.

이 파일은 역호환성을 위해 보존됩니다.
실제 로직은 pipeline.notion/ 서브패키지의 4개 Mixin으로 분할되어 있습니다:
  - _schema.py : 속성 정의, 자동감지, 검증 (NotionSchemaMixin)
  - _cache.py  : URL 중복 캐시 (NotionCacheMixin)
  - _upload.py : 페이지 생성·수정 (NotionUploadMixin)
  - _query.py  : 조회·검색·레코드 추출 (NotionQueryMixin)

기존 import 경로 `from pipeline.notion_upload import NotionUploader`는 그대로 동작합니다.
"""

from __future__ import annotations

from datetime import datetime
import logging
import os
from typing import Any

from notion_client import AsyncClient

from config import (
    ERROR_NOTION_CONFIG_MISSING,
    ERROR_NOTION_SCHEMA_FETCH_FAILED,
    ERROR_NOTION_SCHEMA_MISMATCH,
)

from pipeline.notion._schema import NotionSchemaMixin
from pipeline.notion._cache import NotionCacheMixin
from pipeline.notion._upload import NotionUploadMixin
from pipeline.notion._query import NotionQueryMixin

logger = logging.getLogger(__name__)


class NotionUploader(
    NotionSchemaMixin,
    NotionCacheMixin,
    NotionUploadMixin,
    NotionQueryMixin,
):
    """Notion DB 연동 통합 클래스.

    4개 Mixin에서 기능을 상속받으며, 이 클래스에는 초기화(``__init__``)와
    Notion API 인프라(ensure_schema, query_collection 등)만 유지합니다.
    """

    def __init__(self, config):
        self.config = config
        api_key = config.get("notion.api_key")
        env_api_key = os.environ.get("NOTION_API_KEY")
        self.api_key = env_api_key or api_key

        raw_db_id = os.environ.get("NOTION_DATABASE_ID") or config.get("notion.database_id") or ""
        self.raw_database_id = str(raw_db_id).strip()
        self.database_id = self.normalize_notion_id(self.raw_database_id)

        self.status_default = config.get("notion.status_default", "검토필요")
        self.review_status_default = config.get("notion.review_status_default", "검토필요")
        props_cfg = config.get("notion.properties", {}) or {}
        self._manual_props = {key: str(props_cfg.get(key, "")).strip() for key in self.DEFAULT_PROPS}
        self._env_props = {
            key: str(os.environ.get(env_name, "")).strip()
            for key, env_name in self.PROP_ENV_OVERRIDES.items()
        }

        self.props = dict(self._manual_props)
        self._db_properties: dict[str, dict[str, Any]] = {}
        self._schema_ready = False
        self.collection_kind = None
        self.last_error_code = None
        self.last_error_message = None
        self.client = AsyncClient(auth=self.api_key) if self.api_key else None

        # P1-B: 중복 감지 bulk 캐시 — 실행 1회 bulk 조회 후 메모리 내 O(1) 체크
        self._url_cache: set[str] = set()
        self._url_cache_ready = False
        self._url_cache_loaded_at: datetime | None = None
        self._url_cache_ttl_seconds: int = int(
            config.get("dedup.cache_ttl_minutes", 30)
        ) * 60
        self._url_cache_lookback_days: int = int(
            config.get("dedup.lookback_days", 14)
        )

    # ── 에러 관리 ──

    def _set_error(self, code, message):
        self.last_error_code = code
        self.last_error_message = message
        logger.error(message)

    def _clear_error(self):
        self.last_error_code = None
        self.last_error_message = None

    # ── Notion API 인프라 ──

    async def _list_accessible_sources(self, limit=5):
        if not self.client:
            return []
        items = []
        try:
            response = await self.client.search(page_size=max(limit * 2, 10))
            for raw in response.get("results", []):
                obj_type = raw.get("object")
                if obj_type not in {"database", "data_source"}:
                    continue
                title = "".join((piece.get("plain_text") or "") for piece in (raw.get("title") or [])).strip()
                items.append(f"{obj_type}:{title or '(untitled)'} ({raw.get('id', '')})")
                if len(items) >= limit:
                    break
        except Exception:
            return []
        return items

    async def list_accessible_sources(self, limit=10):
        return await self._list_accessible_sources(limit=limit)

    async def _retrieve_collection(self):
        if not self.client:
            raise RuntimeError("Notion client is not initialized")

        errors = {}
        try:
            database = await self.client.databases.retrieve(database_id=self.database_id)
            # notion-client 2.2.1 버그 우회: properties가 빈 딕셔너리로 반환될 때
            # httpx로 직접 Notion API를 호출하여 properties를 보정
            if not database.get("properties"):
                logger.warning(
                    "notion-client returned empty properties for database %s. "
                    "Falling back to raw httpx call.",
                    self.database_id,
                )
                try:
                    import httpx

                    resp = httpx.get(
                        f"https://api.notion.com/v1/databases/{self.database_id}",
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "Notion-Version": "2022-06-28",
                        },
                        timeout=15,
                    )
                    if resp.status_code == 200:
                        raw_data = resp.json()
                        if raw_data.get("properties"):
                            database["properties"] = raw_data["properties"]
                            logger.info(
                                "httpx fallback recovered %d properties.",
                                len(raw_data["properties"]),
                            )
                except Exception as fallback_exc:
                    logger.warning("httpx fallback failed: %s", fallback_exc)

            self.collection_kind = "database"
            return database
        except Exception as exc:
            errors["database"] = exc

        try:
            data_source = await self.client.data_sources.retrieve(data_source_id=self.database_id)
            self.collection_kind = "data_source"
            return data_source
        except Exception as exc:
            errors["data_source"] = exc

        detail = " | ".join(f"{kind}: {error}" for kind, error in errors.items())
        previews = await self._list_accessible_sources(limit=5)
        if previews:
            detail += " | Accessible objects: " + "; ".join(previews)
        raise RuntimeError(detail)

    async def query_collection(self, *, page_size=100, start_cursor=None, filter=None, sorts=None):
        if not self._schema_ready:
            ok = await self.ensure_schema()
            if not ok:
                raise RuntimeError(self.last_error_message or "Notion schema is not ready")

        # notion-client 2.2.1 호환성 문제 우회: httpx로 직접 REST API 호출
        import httpx as _httpx

        body: dict = {"page_size": page_size}
        if start_cursor:
            body["start_cursor"] = start_cursor
        if filter is not None:
            body["filter"] = filter
        if sorts:
            body["sorts"] = sorts

        # collection_kind에 따라 적절한 엔드포인트 선택
        if self.collection_kind == "data_source":
            query_url = f"https://api.notion.com/v1/data_sources/{self.database_id}/query"
            api_version = "2025-09-03"
        else:
            query_url = f"https://api.notion.com/v1/databases/{self.database_id}/query"
            api_version = "2022-06-28"

        async def _do_query():
            async with _httpx.AsyncClient(timeout=30) as http:
                resp = await http.post(
                    query_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Notion-Version": api_version,
                        "Content-Type": "application/json",
                    },
                    json=body,
                )
                resp.raise_for_status()
                return resp.json()

        return await self._safe_notion_call(_do_query)

    def _page_parent_payload(self):
        # collection_kind에 따라 적절한 parent 키 사용
        if self.collection_kind == "data_source":
            return {"data_source_id": self.database_id}
        return {"database_id": self.database_id}

    async def _safe_notion_call(self, fn, *args, max_retries: int = 3, **kwargs):
        """Notion API 호출 래퍼 — 429/5xx 시 지수 백오프로 최대 max_retries 재시도.

        Phase 2-B: 네트워크 오류 및 rate limit 처리.
        """
        import asyncio as _asyncio

        last_exc = None
        for attempt in range(max_retries):
            try:
                return await fn(*args, **kwargs)
            except Exception as exc:
                last_exc = exc
                status = getattr(exc, "status", None) or getattr(exc, "code", None)
                retryable = status in (429, 500, 502, 503, 504) or status is None
                if retryable and attempt < max_retries - 1:
                    delay = 2 ** attempt  # 1s, 2s, 4s
                    logger.warning(
                        "Notion API error (status=%s), retrying in %ds (attempt %d/%d): %s",
                        status, delay, attempt + 1, max_retries, exc,
                    )
                    await _asyncio.sleep(delay)
                else:
                    raise
        raise last_exc  # type: ignore[misc]

    async def ensure_schema(self):
        if self._schema_ready:
            return True
        if not self.client or not self.database_id:
            self._set_error(ERROR_NOTION_CONFIG_MISSING, "Notion API key or Database ID is missing.")
            return False

        try:
            collection_meta = await self._safe_notion_call(self._retrieve_collection)
            self._db_properties = collection_meta.get("properties", {}) or {}
            self.props = self._resolve_props(self._auto_detect_props(self._db_properties))
            valid, reason = self._validate_props()
            if not valid:
                self._set_error(
                    ERROR_NOTION_SCHEMA_MISMATCH,
                    f"Notion schema mismatch. {reason}. Resolved props={self.props}. Available={list(self._db_properties.keys())}",
                )
                return False
            self._schema_ready = True
            self._clear_error()
            logger.info("Notion schema resolved (%s): %s", self.collection_kind, self.props)
            return True
        except Exception as exc:
            self._set_error(ERROR_NOTION_SCHEMA_FETCH_FAILED, f"Failed to fetch Notion schema: {exc}")
            return False
