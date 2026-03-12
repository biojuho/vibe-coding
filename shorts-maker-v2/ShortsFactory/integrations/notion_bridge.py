"""notion_bridge.py — Notion DB <-> ShortsFactory 연동.

Notion 콘텐츠 DB에서 'ready' 상태의 항목을 가져와
ShortsFactory 렌더링용 데이터로 변환합니다.

Usage:
    from ShortsFactory.integrations.notion_bridge import NotionContentFetcher
    
    fetcher = NotionContentFetcher(database_id="your_db_id")
    jobs = fetcher.fetch_ready_content()
    for job in jobs:
        factory = ShortsFactory(channel=job["channel"])
        factory.create(job["template"], job["data"])
        factory.render(job["output_path"])
        fetcher.mark_done(job["page_id"])
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("ShortsFactory.notion")

# Notion DB 스키마 정의
NOTION_SCHEMA = {
    "title":       {"type": "title",      "field": "제목"},
    "channel":     {"type": "select",     "field": "채널"},
    "template":    {"type": "select",     "field": "템플릿"},
    "script_data": {"type": "rich_text",  "field": "스크립트 데이터"},
    "status":      {"type": "status",     "field": "상태"},
    "scheduled":   {"type": "date",       "field": "예약일"},
    "output_path": {"type": "url",        "field": "영상경로"},
    "error":       {"type": "rich_text",  "field": "에러"},
}

STATUS_FLOW = ["draft", "ready", "rendering", "done", "uploaded", "error"]


class NotionContentFetcher:
    """Notion 콘텐츠 DB에서 렌더링할 항목을 가져옵니다."""

    def __init__(self, database_id: str, token: str | None = None):
        self.database_id = database_id
        self.token = token or os.environ.get("NOTION_TOKEN", "")
        if not self.token:
            logger.warning("NOTION_TOKEN not set. Notion API calls will fail.")

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28",
        }

    def fetch_ready_content(self, limit: int = 10) -> list[dict[str, Any]]:
        """status='ready'인 콘텐츠를 가져와 ShortsFactory 형식으로 변환.

        Returns:
            [{page_id, channel, template, data, title, output_path}, ...]
        """
        try:
            import requests
        except ImportError:
            logger.error("requests 패키지 필요: pip install requests")
            return []

        url = f"https://api.notion.com/v1/databases/{self.database_id}/query"
        payload = {
            "filter": {
                "property": "상태",
                "status": {"equals": "ready"},
            },
            "page_size": limit,
            "sorts": [{"property": "예약일", "direction": "ascending"}],
        }

        resp = requests.post(url, json=payload, headers=self._headers())
        if resp.status_code != 200:
            logger.error(f"Notion API error: {resp.status_code} {resp.text[:200]}")
            return []

        results = []
        for page in resp.json().get("results", []):
            props = page["properties"]
            try:
                title = self._extract_title(props.get("제목", {}))
                channel = self._extract_select(props.get("채널", {}))
                template = self._extract_select(props.get("템플릿", {}))
                script_raw = self._extract_rich_text(props.get("스크립트 데이터", {}))
                # [QA 수정] invalid JSON 명시 처리
                try:
                    data = json.loads(script_raw) if script_raw else {}
                except json.JSONDecodeError as je:
                    logger.warning(f"Invalid script JSON in page {page.get('id','?')}: {je}")
                    continue

                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                safe_title = "".join(c if c.isalnum() or c in "_ -" else "_" for c in title[:30])
                output = f"output/{channel}_{template}_{ts}_{safe_title}.mp4"

                results.append({
                    "page_id": page["id"],
                    "channel": channel,
                    "template": template,
                    "data": data,
                    "title": title,
                    "output_path": output,
                })
            except Exception as e:
                logger.warning(f"Page parse error: {e}")
                continue

        logger.info(f"Fetched {len(results)} ready items from Notion")
        return results

    def update_status(self, page_id: str, status: str, **extra_fields) -> bool:
        """페이지 상태 업데이트."""
        try:
            import requests
        except ImportError:
            return False

        url = f"https://api.notion.com/v1/pages/{page_id}"
        props: dict = {"상태": {"status": {"name": status}}}

        if "output_path" in extra_fields:
            props["영상경로"] = {"url": extra_fields["output_path"]}
        if "error" in extra_fields:
            props["에러"] = {
                "rich_text": [{"text": {"content": str(extra_fields["error"])[:2000]}}]
            }

        resp = requests.patch(url, json={"properties": props}, headers=self._headers())
        ok = resp.status_code == 200
        if not ok:
            logger.error(f"Status update failed: {resp.status_code}")
        return ok

    def mark_rendering(self, page_id: str) -> bool:
        return self.update_status(page_id, "rendering")

    def mark_done(self, page_id: str, output_path: str = "") -> bool:
        return self.update_status(page_id, "done", output_path=output_path)

    def mark_error(self, page_id: str, error: str) -> bool:
        return self.update_status(page_id, "error", error=error)

    # ── 헬퍼 ──
    @staticmethod
    def _extract_title(prop: dict) -> str:
        return "".join(t.get("plain_text", "") for t in prop.get("title", []))

    @staticmethod
    def _extract_select(prop: dict) -> str:
        sel = prop.get("select")
        return sel["name"] if sel else ""

    @staticmethod
    def _extract_rich_text(prop: dict) -> str:
        return "".join(t.get("plain_text", "") for t in prop.get("rich_text", []))


def auto_render_from_notion(database_id: str, output_dir: str = "output") -> list[dict]:
    """Notion에서 ready 콘텐츠를 가져와 자동 렌더링하는 편의 함수.

    Returns:
        렌더링 결과 리스트
    """
    from ShortsFactory.pipeline import ShortsFactory

    fetcher = NotionContentFetcher(database_id)
    jobs = fetcher.fetch_ready_content()
    results = []

    for job in jobs:
        fetcher.mark_rendering(job["page_id"])
        try:
            factory = ShortsFactory(channel=job["channel"])
            factory.create(job["template"], job["data"])
            out = factory.render(job["output_path"])
            fetcher.mark_done(job["page_id"], output_path=out)
            results.append({"page_id": job["page_id"], "status": "done", "output": out})
        except Exception as e:
            fetcher.mark_error(job["page_id"], str(e))
            results.append({"page_id": job["page_id"], "status": "error", "error": str(e)})

    logger.info(f"Auto-render: {len(results)} jobs processed")
    return results
