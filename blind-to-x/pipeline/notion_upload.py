"""Notion uploader with schema auto-detection and review queue helpers."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import logging
import os
import re
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from notion_client import AsyncClient

from config import (
    ERROR_NOTION_CONFIG_MISSING,
    ERROR_NOTION_DUPLICATE_CHECK_FAILED,
    ERROR_NOTION_SCHEMA_FETCH_FAILED,
    ERROR_NOTION_SCHEMA_MISMATCH,
    ERROR_NOTION_UPLOAD_FAILED,
)

logger = logging.getLogger(__name__)


class NotionUploader:
    DEFAULT_PROPS = {
        "title": "콘텐츠",
        "memo": "메모",
        "status": "상태",
        "date": "생성일",
        "image_needed": "이미지 필요",
        "tweet_body": "트윗 본문",
        "url": "원본 URL",
        "tweet_url": "트윗 링크",
        "views": "24h 조회수",
        "likes": "24h 좋아요",
        "retweets": "24h 리트윗",
        "source": "원본 소스",
        "feed_mode": "피드 모드",
        "topic_cluster": "토픽 클러스터",
        "hook_type": "훅 타입",
        "emotion_axis": "감정 축",
        "audience_fit": "대상 독자",
        "scrape_quality_score": "스크랩 품질 점수",
        "publishability_score": "발행 적합도 점수",
        "performance_score": "성과 예측 점수",
        "final_rank_score": "최종 랭크 점수",
        "review_status": "승인 상태",
        "review_note": "검토 메모",
        "chosen_draft_type": "선택 초안 타입",
        "newsletter_body": "뉴스레터 초안",
        "publish_channel": "발행 채널",
        "published_at": "발행 시각",
        "performance_grade": "성과 등급",
        # P6: 멀티 플랫폼 지원
        "threads_body": "Threads 본문",
        "blog_body": "블로그 본문",
        "publish_platforms": "발행 플랫폼",
        "threads_url": "Threads 링크",
        "blog_url": "블로그 링크",
        "publish_scheduled_at": "발행 예정일",
        # P7: 규제 검증
        "regulation_status": "규제 검증",
        "screenshot_url": "스크린샷 URL",
    }
    PROP_ENV_OVERRIDES = {key: f"NOTION_PROP_{key.upper()}" for key in DEFAULT_PROPS}
    EXPECTED_TYPES = {
        "title": {"title"},
        "memo": {"rich_text"},
        "status": {"status", "select"},
        "date": {"date"},
        "image_needed": {"checkbox"},
        "tweet_body": {"rich_text"},
        "url": {"url", "rich_text"},
        "tweet_url": {"url", "rich_text"},
        "views": {"number"},
        "likes": {"number"},
        "retweets": {"number"},
        "source": {"select", "rich_text"},
        "feed_mode": {"select", "rich_text"},
        "topic_cluster": {"select", "rich_text"},
        "hook_type": {"select", "rich_text"},
        "emotion_axis": {"select", "rich_text"},
        "audience_fit": {"select", "rich_text"},
        "scrape_quality_score": {"number"},
        "publishability_score": {"number"},
        "performance_score": {"number"},
        "final_rank_score": {"number"},
        "review_status": {"status", "select"},
        "review_note": {"rich_text"},
        "chosen_draft_type": {"select", "rich_text"},
        "newsletter_body": {"rich_text"},
        "publish_channel": {"select", "rich_text"},
        "published_at": {"date"},
        "performance_grade": {"select", "rich_text"},
        # P6: 멀티 플랫폼
        "threads_body": {"rich_text"},
        "blog_body": {"rich_text"},
        "publish_platforms": {"multi_select", "rich_text"},
        "threads_url": {"url", "rich_text"},
        "blog_url": {"url", "rich_text"},
        "publish_scheduled_at": {"date"},
        # P7: 규제 검증
        "regulation_status": {"select", "rich_text"},
        "screenshot_url": {"url", "rich_text"},
    }
    AUTO_DETECT_KEYWORDS = {
        "title": ("title", "제목", "name", "콘텐츠"),
        "memo": ("memo", "메모", "summary", "요약"),
        "status": ("status", "상태", "stage"),
        "date": ("date", "생성", "created"),
        "image_needed": ("image", "이미지", "필요"),
        "tweet_body": ("tweet", "트윗", "draft", "초안"),
        "url": ("url", "원본", "source"),
        "tweet_url": ("tweet url", "트윗 링크", "x url"),
        "views": ("조회수", "views", "impressions"),
        "likes": ("좋아요", "likes"),
        "retweets": ("리트윗", "retweets", "repost"),
        "source": ("source", "출처", "원본 소스"),
        "feed_mode": ("feed", "피드", "mode"),
        "topic_cluster": ("topic", "토픽"),
        "hook_type": ("hook", "훅"),
        "emotion_axis": ("emotion", "감정"),
        "audience_fit": ("audience", "독자"),
        "scrape_quality_score": ("스크랩", "품질", "quality"),
        "publishability_score": ("발행", "publish"),
        "performance_score": ("성과 예측", "performance", "prediction"),
        "final_rank_score": ("rank", "랭크", "score"),
        "review_status": ("review", "승인", "approval"),
        "review_note": ("review note", "검토 메모"),
        "chosen_draft_type": ("chosen", "선택 초안", "draft type"),
        "newsletter_body": ("newsletter", "뉴스레터"),
        "publish_channel": ("channel", "발행 채널"),
        "published_at": ("published", "발행 시각"),
        "performance_grade": ("grade", "성과 등급"),
        # P6: 멀티 플랫폼
        "threads_body": ("threads", "쓰레드", "Threads 본문"),
        "blog_body": ("blog", "블로그", "블로그 본문"),
        "publish_platforms": ("platforms", "플랫폼", "발행 플랫폼"),
        "threads_url": ("threads url", "Threads 링크"),
        "blog_url": ("blog url", "블로그 링크"),
        "publish_scheduled_at": ("scheduled", "예정", "발행 예정일"),
        # P7: 규제 검증
        "regulation_status": ("regulation", "규제", "검증"),
        "screenshot_url": ("screenshot", "스크린샷", "Screenshot URL"),
    }
    TRACKING_QUERY_KEYS = {"fbclid", "gclid", "igshid", "ref", "ref_src", "ref_url", "feature"}
    NOTION_ID_REGEX = re.compile(
        r"([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}|[0-9a-fA-F]{32})"
    )

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

    def _set_error(self, code, message):
        self.last_error_code = code
        self.last_error_message = message
        logger.error(message)

    def _clear_error(self):
        self.last_error_code = None
        self.last_error_message = None

    @classmethod
    def normalize_notion_id(cls, raw_id):
        if not raw_id:
            return ""
        value = str(raw_id).strip()
        if not value:
            return ""
        matches = cls.NOTION_ID_REGEX.findall(value)
        if not matches:
            return value
        token = matches[-1].replace("-", "").lower()
        if len(token) != 32:
            return value
        return f"{token[0:8]}-{token[8:12]}-{token[12:16]}-{token[16:20]}-{token[20:32]}"

    @staticmethod
    def canonicalize_url(raw_url):
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

        query_items = []
        for key, val in parse_qsl(parsed.query, keep_blank_values=True):
            key_lower = key.lower()
            if key_lower.startswith("utm_") or key_lower in NotionUploader.TRACKING_QUERY_KEYS:
                continue
            query_items.append((key, val))
        query_items.sort(key=lambda item: (item[0], item[1]))
        query = urlencode(query_items, doseq=True)
        return urlunsplit((scheme, netloc, path, query, ""))

    @staticmethod
    def _pick_by_keywords(candidates, keywords, used, allow_fallback=True):
        lowered_keywords = [item.lower() for item in keywords]
        for candidate in candidates:
            if candidate in used:
                continue
            lower_name = candidate.lower()
            if any(keyword in lower_name for keyword in lowered_keywords):
                return candidate
        if not allow_fallback:
            return None
        for candidate in candidates:
            if candidate not in used:
                return candidate
        return None

    def _auto_detect_props(self, db_props):
        by_type: dict[str, list[str]] = {}
        for prop_name, prop_data in db_props.items():
            by_type.setdefault(prop_data.get("type"), []).append(prop_name)

        detected = {}
        used: set[str] = set()
        for semantic_key, expected_types in self.EXPECTED_TYPES.items():
            candidates: list[str] = []
            for prop_type in expected_types:
                candidates.extend(by_type.get(prop_type, []))
            if not candidates:
                continue
            picked = self._pick_by_keywords(
                candidates,
                self.AUTO_DETECT_KEYWORDS.get(semantic_key, (semantic_key,)),
                used,
                allow_fallback=False,
            )
            if picked:
                detected[semantic_key] = picked
                used.add(picked)
        return detected

    def _resolve_props(self, auto_props):
        resolved = {}
        for key, default_name in self.DEFAULT_PROPS.items():
            env_name = self._env_props.get(key)
            manual_name = self._manual_props.get(key)
            auto_name = auto_props.get(key)
            if env_name:
                resolved[key] = env_name
            elif manual_name and manual_name in self._db_properties:
                resolved[key] = manual_name
            elif auto_name:
                resolved[key] = auto_name
            else:
                resolved[key] = manual_name or default_name
        return resolved

    def _validate_props(self):
        required_keys = {"title", "status", "date", "url", "tweet_body"}
        missing = []
        mismatch = []
        for key, expected_types in self.EXPECTED_TYPES.items():
            prop_name = self.props.get(key)
            if not prop_name:
                if key in required_keys:
                    missing.append(f"{key}(empty)")
                continue

            meta = self._db_properties.get(prop_name)
            if not meta:
                if key in required_keys:
                    missing.append(f"{key}='{prop_name}'")
                continue

            if meta.get("type") not in expected_types:
                mismatch.append(f"{key}='{prop_name}' type={meta.get('type')}, expected={sorted(expected_types)}")

        if missing or mismatch:
            detail = []
            if missing:
                detail.append("missing: " + ", ".join(missing))
            if mismatch:
                detail.append("type_mismatch: " + ", ".join(mismatch))
            return False, "; ".join(detail)
        return True, ""

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

        kwargs = {"page_size": page_size}
        if start_cursor:
            kwargs["start_cursor"] = start_cursor
        if filter is not None:
            kwargs["filter"] = filter
        if sorts:
            kwargs["sorts"] = sorts

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

    def _prepare_property_payload(self, semantic_key: str, value: Any):
        prop_name = self.props.get(semantic_key)
        if not prop_name or prop_name not in self._db_properties or value in (None, ""):
            return None, None

        prop_type = self._db_properties[prop_name]["type"]
        if prop_type == "title":
            return prop_name, {"title": [{"text": {"content": str(value)[:1990]}}]}
        if prop_type == "rich_text":
            return prop_name, {"rich_text": [{"text": {"content": str(value)[:1990]}}]}
        if prop_type == "checkbox":
            return prop_name, {"checkbox": bool(value)}
        if prop_type == "number":
            return prop_name, {"number": float(value)}
        if prop_type == "url":
            return prop_name, {"url": str(value)}
        if prop_type == "status":
            return prop_name, {"status": {"name": str(value)}}
        if prop_type == "select":
            return prop_name, {"select": {"name": str(value)}}
        if prop_type == "date":
            if value == "now":
                iso_value = datetime.utcnow().isoformat()
            elif isinstance(value, datetime):
                iso_value = value.isoformat()
            elif isinstance(value, date):
                iso_value = value.isoformat()
            else:
                iso_value = str(value)
            return prop_name, {"date": {"start": iso_value}}
        return None, None

    def _append_property_if_present(self, properties: dict[str, Any], semantic_key: str, value: Any):
        prop_name, payload = self._prepare_property_payload(semantic_key, value)
        if prop_name and payload is not None:
            properties[prop_name] = payload

    def _create_text_blocks(self, text: str):
        blocks = []
        for start in range(0, len(text), 2000):
            chunk = text[start : start + 2000]
            blocks.append(
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {"rich_text": [{"type": "text", "text": {"content": chunk}}]},
                }
            )
        return blocks

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

    async def upload(self, post_data, image_url, drafts, analysis=None, screenshot_url=None):
        if not await self.ensure_schema():
            return None

        logger.info("Uploading to Notion: %s", post_data.get("title", "(untitled)"))
        try:
            canonical_url = self.canonicalize_url(post_data.get("url", ""))
            properties: dict[str, Any] = {}

            self._append_property_if_present(properties, "title", post_data.get("title", ""))
            memo_text = f"원본 링크: {canonical_url or post_data.get('url', '')}"
            if analysis and analysis.get("rationale"):
                memo_text += f"\n판정 근거: {', '.join(analysis['rationale'])}"
            self._append_property_if_present(properties, "memo", memo_text)
            self._append_property_if_present(properties, "status", post_data.get("review_status") or self.status_default)
            self._append_property_if_present(properties, "date", datetime.now().date())
            self._append_property_if_present(properties, "image_needed", bool(image_url))
            self._append_property_if_present(properties, "url", canonical_url)
            self._append_property_if_present(properties, "source", post_data.get("source", "blind"))
            self._append_property_if_present(properties, "feed_mode", post_data.get("feed_mode", "trending"))
            self._append_property_if_present(
                properties,
                "review_status",
                post_data.get("review_status", self.review_status_default),
            )
            self._append_property_if_present(properties, "review_note", post_data.get("review_reason", "queued_for_review"))

            if isinstance(drafts, dict):
                self._append_property_if_present(properties, "tweet_body", drafts.get("twitter"))
                self._append_property_if_present(properties, "newsletter_body", drafts.get("newsletter"))
                # P6: 멀티 플랫폼 초안 저장
                self._append_property_if_present(properties, "threads_body", drafts.get("threads"))
                self._append_property_if_present(properties, "blog_body", drafts.get("naver_blog"))
            else:
                self._append_property_if_present(properties, "tweet_body", drafts)

            if screenshot_url:
                self._append_property_if_present(properties, "screenshot_url", screenshot_url)

            if analysis:
                analysis_mapping = {
                    "topic_cluster": analysis.get("topic_cluster"),
                    "hook_type": analysis.get("hook_type"),
                    "emotion_axis": analysis.get("emotion_axis"),
                    "audience_fit": analysis.get("audience_fit"),
                    "scrape_quality_score": analysis.get("scrape_quality_score"),
                    "publishability_score": analysis.get("publishability_score"),
                    "performance_score": analysis.get("performance_score"),
                    "final_rank_score": analysis.get("final_rank_score"),
                    "chosen_draft_type": analysis.get("recommended_draft_type"),
                    "image_variant_id": post_data.get("image_variant_id"),
                    "image_variant_type": post_data.get("image_variant_type"),
                }
                for semantic_key, value in analysis_mapping.items():
                    self._append_property_if_present(properties, semantic_key, value)

            children = []
            if image_url:
                children.append(
                    {
                        "object": "block",
                        "type": "image",
                        "image": {"type": "external", "external": {"url": image_url}},
                    }
                )

            if analysis:
                children.append({"object": "block", "type": "divider", "divider": {}})
                children.append(
                    {
                        "object": "block",
                        "type": "heading_2",
                        "heading_2": {"rich_text": [{"type": "text", "text": {"content": "콘텐츠 인텔리전스"}}]},
                    }
                )
                profile_lines = [
                    f"토픽 클러스터: {analysis.get('topic_cluster', '기타')}",
                    f"훅 타입: {analysis.get('hook_type', '공감형')}",
                    f"감정 축: {analysis.get('emotion_axis', '공감')}",
                    f"대상 독자: {analysis.get('audience_fit', '범용')}",
                    f"추천 초안 타입: {analysis.get('recommended_draft_type', '공감형')}",
                    f"스크랩 품질 점수: {analysis.get('scrape_quality_score', 0)}",
                    f"발행 적합도 점수: {analysis.get('publishability_score', 0)}",
                    f"성과 예측 점수: {analysis.get('performance_score', 0)}",
                    f"최종 랭크 점수: {analysis.get('final_rank_score', 0)}",
                ]
                children.extend(self._create_text_blocks("\n".join(profile_lines)))

            if drafts:
                if isinstance(drafts, dict):
                    if drafts.get("twitter"):
                        children.append({"object": "block", "type": "divider", "divider": {}})
                        children.append(
                            {
                                "object": "block",
                                "type": "heading_2",
                                "heading_2": {"rich_text": [{"type": "text", "text": {"content": "X(Twitter) 초안"}}]},
                            }
                        )
                        children.extend(self._create_text_blocks(drafts["twitter"]))
                    if drafts.get("threads"):
                        children.append({"object": "block", "type": "divider", "divider": {}})
                        children.append(
                            {
                                "object": "block",
                                "type": "heading_2",
                                "heading_2": {"rich_text": [{"type": "text", "text": {"content": "Threads 초안"}}]},
                            }
                        )
                        children.extend(self._create_text_blocks(drafts["threads"]))
                    if drafts.get("newsletter"):
                        children.append({"object": "block", "type": "divider", "divider": {}})
                        children.append(
                            {
                                "object": "block",
                                "type": "heading_2",
                                "heading_2": {"rich_text": [{"type": "text", "text": {"content": "뉴스레터 초안"}}]},
                            }
                        )
                        children.extend(self._create_text_blocks(drafts["newsletter"]))
                    if drafts.get("naver_blog"):
                        children.append({"object": "block", "type": "divider", "divider": {}})
                        children.append(
                            {
                                "object": "block",
                                "type": "heading_2",
                                "heading_2": {"rich_text": [{"type": "text", "text": {"content": "네이버 블로그 초안"}}]},
                            }
                        )
                        children.extend(self._create_text_blocks(drafts["naver_blog"]))
                else:
                    children.append({"object": "block", "type": "divider", "divider": {}})
                    children.append(
                        {
                            "object": "block",
                            "type": "heading_2",
                            "heading_2": {"rich_text": [{"type": "text", "text": {"content": "X(Twitter) 초안"}}]},
                        }
                    )
                    children.extend(self._create_text_blocks(str(drafts)))

            if screenshot_url:
                children.append({"object": "block", "type": "divider", "divider": {}})
                children.append(
                    {
                        "object": "block",
                        "type": "heading_2",
                        "heading_2": {"rich_text": [{"type": "text", "text": {"content": "원문 스크린샷"}}]},
                    }
                )
                children.append(
                    {
                        "object": "block",
                        "type": "image",
                        "image": {"type": "external", "external": {"url": screenshot_url}},
                    }
                )

            children.append({"object": "block", "type": "divider", "divider": {}})
            children.append(
                {
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {"rich_text": [{"type": "text", "text": {"content": "원문 내용"}}]},
                }
            )
            if post_data.get("content"):
                children.extend(self._create_text_blocks(str(post_data["content"])))

            # P7: 규제 검증 리포트 저장
            regulation_report = post_data.get("regulation_report", "")
            if regulation_report:
                children.append({"object": "block", "type": "divider", "divider": {}})
                children.append(
                    {
                        "object": "block",
                        "type": "heading_2",
                        "heading_2": {"rich_text": [{"type": "text", "text": {"content": "📋 규제 검증 리포트"}}]},
                    }
                )
                children.extend(self._create_text_blocks(regulation_report))
                # 규제 검증 상태 요약을 속성에도 저장
                self._append_property_if_present(
                    properties, "regulation_status",
                    "통과" if "전체 플랫폼 규제 검증 통과" in regulation_report else "경고"
                )
            response = await self.client.pages.create(
                parent=self._page_parent_payload(),
                properties=properties,
                children=children,
            )
            self._clear_error()
            # 업로드 성공 즉시 캐시에 등록 (동일 세션 내 중복 방지)
            self._register_url_in_cache(post_data.get("url", ""))
            return response.get("url", "Unknown URL"), response.get("id")
        except Exception as exc:
            err_str = str(exc)
            if "is not a property that exists" in err_str:
                self._set_error(
                    ERROR_NOTION_SCHEMA_MISMATCH,
                    "Notion 속성명이 실제 DB와 일치하지 않습니다. notion.properties 또는 NOTION_PROP_* 값을 확인하세요. "
                    f"원본 에러: {err_str}",
                )
            else:
                self._set_error(ERROR_NOTION_UPLOAD_FAILED, f"Failed to upload to Notion: {err_str}")
            return None

    async def update_page_properties(self, page_id: str, updates: dict):
        if not await self.ensure_schema():
            return None
        try:
            properties = {}
            for semantic_key, value in updates.items():
                prop_name, payload = self._prepare_property_payload(semantic_key, value)
                if prop_name and payload is not None:
                    properties[prop_name] = payload
            if not properties:
                return True
            await self.client.pages.update(page_id=page_id, properties=properties)
            logger.info("Successfully updated properties for Notion page %s", page_id)
            return True
        except Exception as exc:
            logger.error("Failed to update Notion page properties: %s", exc)
            return False

    def get_page_property_value(self, page: dict[str, Any], semantic_key: str, default=None):
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
        record = {"page_id": page.get("id"), "page_url": page.get("url")}
        for semantic_key in self.DEFAULT_PROPS:
            record[semantic_key] = self.get_page_property_value(page, semantic_key)
        record["text"] = record.get("tweet_body") or ""
        record["draft_style"] = record.get("chosen_draft_type") or "공감형"
        return record

    async def get_top_performing_posts(self, limit=5, lookback_days=30, minimum_posts=20):
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
        if not await self.ensure_schema():
            return []

        try:
            response = await self.client.search(
                query="",
                filter={"value": "page", "property": "object"},
                sort={"direction": "descending", "timestamp": "last_edited_time"},
                page_size=min(100, max(limit, 20)) # API limit 100 per request
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
