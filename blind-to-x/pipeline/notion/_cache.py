"""Notion URL deduplication cache.

Mixin: NotionCacheMixin — bulk 캐시 로드 + O(1) 중복 체크.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
import re

from config import ERROR_NOTION_DUPLICATE_CHECK_FAILED

logger = logging.getLogger(__name__)


class NotionCacheMixin:
    """URL 중복 감지 캐시를 담당하는 Mixin.

    사전 조건: NotionSchemaMixin의 TRACKING_QUERY_KEYS, canonicalize_url,
    그리고 기본 client / ensure_schema / query_collection / get_recent_pages가
    동일 클래스(NotionUploader)에 합쳐져 있어야 합니다.
    """

    @staticmethod
    def canonicalize_url(raw_url):
        """URL 정규화 — 추적 파라미터 제거, scheme/host/path 통일."""
        if not raw_url:
            return ""
        value = str(raw_url).strip()
        if not value:
            return ""
        if not re.match(r"^https?://", value, flags=re.IGNORECASE):
            value = "https://" + value

        parsed = urlsplit(value)
        scheme = "https"
        host = (parsed.hostname or "").lower()
        if not host:
            return value

        port = parsed.port
        netloc = f"{host}:{port}" if port and port not in {80, 443} else host
        path = re.sub(r"/{2,}", "/", parsed.path or "/")
        if path != "/" and path.endswith("/"):
            path = path[:-1]

        # NotionSchemaMixin에서 정의된 TRACKING_QUERY_KEYS 참조
        tracking = getattr(
            type, "TRACKING_QUERY_KEYS",
            {"fbclid", "gclid", "igshid", "ref", "ref_src", "ref_url", "feature"},
        )
        # 클래스에 TRACKING_QUERY_KEYS가 있으면 사용
        if hasattr(type(raw_url), "TRACKING_QUERY_KEYS"):
            tracking = type(raw_url).TRACKING_QUERY_KEYS  # pragma: no cover

        # 실제로는 NotionUploader(NotionSchemaMixin, NotionCacheMixin, ...)에서
        # TRACKING_QUERY_KEYS가 self에 있으므로 하드코딩 폴백 사용
        _TRACKING = {"fbclid", "gclid", "igshid", "ref", "ref_src", "ref_url", "feature"}

        query_items = []
        for key, val in parse_qsl(parsed.query, keep_blank_values=True):
            key_lower = key.lower()
            if key_lower.startswith("utm_") or key_lower in _TRACKING:
                continue
            query_items.append((key, val))
        query_items.sort(key=lambda item: (item[0], item[1]))
        query = urlencode(query_items, doseq=True)
        return urlunsplit((scheme, netloc, path, query, ""))

    async def _ensure_url_cache(self) -> bool:
        """최근 N일 페이지 URL을 1회 bulk 조회 → _url_cache에 적재.

        이후 is_duplicate()는 Notion API를 호출하지 않고 메모리 set을 조회합니다.
        스키마 미준비 또는 API 오류 시 False 반환 (fallback: 개별 API 조회로 전환).
        """
        if self._url_cache_ready:
            # TTL 만료 시 재적재 (기본 30분)
            if self._url_cache_loaded_at is not None:
                age = (datetime.now(timezone.utc) - self._url_cache_loaded_at).total_seconds()
                if age > self._url_cache_ttl_seconds:
                    logger.info(
                        "Notion URL 캐시 TTL 만료 (%.0fs). 재적재 시작.", age
                    )
                    self._url_cache_ready = False
                    self._url_cache.clear()
            if self._url_cache_ready:
                return True
        if not await self.ensure_schema():
            return False

        url_prop = self.props.get("url")
        if not url_prop or url_prop not in self._db_properties:
            return False

        try:
            pages = await self.get_recent_pages(
                days=self._url_cache_lookback_days, limit=200
            )
            url_prop_type = self._db_properties[url_prop]["type"]
            for page in pages:
                raw = page.get("properties", {}).get(url_prop, {})
                if url_prop_type == "url":
                    raw_url = raw.get("url") or ""
                else:
                    parts = raw.get("rich_text", [])
                    raw_url = "".join(p.get("plain_text", "") for p in parts)
                canonical = self.canonicalize_url(raw_url)
                if canonical:
                    self._url_cache.add(canonical)
            self._url_cache_ready = True
            self._url_cache_loaded_at = datetime.now(timezone.utc)
            logger.info(
                "Notion URL 캐시 적재 완료: %d건 (lookback=%d일)",
                len(self._url_cache),
                self._url_cache_lookback_days,
            )
            return True
        except Exception as exc:
            logger.warning("Notion URL 캐시 적재 실패 (fallback: 개별 API 조회): %s", exc)
            return False

    async def warm_cache(self) -> bool:
        """세션 시작 시 Notion URL 캐시를 미리 로드 (공개 API).

        main.py에서 스크래핑 루프 시작 전 1회 호출.
        이후 is_duplicate()는 Notion API 호출 없이 O(1) 메모리 조회.
        Returns True if cache loaded successfully, False on failure (non-fatal).
        """
        result = await self._ensure_url_cache()
        if result:
            logger.info("Notion URL 캐시 웜업 완료: %d개 URL 로드됨", len(self._url_cache))
        else:
            logger.warning("Notion URL 캐시 웜업 실패 → is_duplicate()가 개별 API 조회로 폴백됩니다")
        return result

    def _register_url_in_cache(self, url: str) -> None:
        """업로드 성공 후 캐시에 즉시 등록 (다음 중복 체크에 반영)."""
        canonical = self.canonicalize_url(url)
        if canonical:
            self._url_cache.add(canonical)

    async def is_duplicate(self, url):
        """URL 중복 여부 확인.

        캐시가 준비된 경우 메모리 set을 O(1) 조회.
        캐시 미준비 시 Notion API에 개별 쿼리 (이전 동작과 동일).
        """
        if not await self.ensure_schema():
            return None
        url_value = self.canonicalize_url(url)

        # 캐시 우선 조회 (API 호출 없음)
        cache_ok = await self._ensure_url_cache()
        if cache_ok:
            return url_value in self._url_cache

        # fallback: 기존 개별 API 조회
        url_prop = self.props["url"]
        url_prop_type = self._db_properties[url_prop]["type"]
        try:
            if url_prop_type == "url":
                duplicate_filter = {"property": url_prop, "url": {"equals": url_value}}
            else:
                duplicate_filter = {"property": url_prop, "rich_text": {"equals": url_value}}
            response = await self.query_collection(filter=duplicate_filter, page_size=1)
            return bool(response.get("results"))
        except Exception as exc:
            logger.warning("Notion duplicate check failed: %s", exc)
            self.last_error_code = ERROR_NOTION_DUPLICATE_CHECK_FAILED
            self.last_error_message = str(exc)
            return None
