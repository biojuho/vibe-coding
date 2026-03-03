"""
Notion Shorts 트래킹 동기화 스크립트.

content_db의 영상 생산 결과를 Notion 데이터베이스에 자동 동기화.

Usage:
    python execution/notion_shorts_sync.py --all
    python execution/notion_shorts_sync.py --item-id 1
    python execution/notion_shorts_sync.py --since 2026-03-01
    python execution/notion_shorts_sync.py --channel "의학/건강"
    python execution/notion_shorts_sync.py --all --status success
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# 경로 설정
# ---------------------------------------------------------------------------
_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env")
sys.path.insert(0, str(_ROOT))

# ---------------------------------------------------------------------------
# 상수
# ---------------------------------------------------------------------------
_NOTION_VERSION = "2022-06-28"
_NOTION_API_BASE = "https://api.notion.com/v1"
_RATE_LIMIT_DELAY = 0.35  # Notion API: 3 req/s 제한

# 상태 매핑 (content_db status → Notion select)
_STATUS_MAP = {
    "success": "✅성공",
    "pending": "⏳대기",
    "running": "🔄실행중",
    "failed": "❌실패",
}

# YouTube 상태 매핑
_YT_STATUS_MAP = {
    "uploaded": "업로드됨",
    "failed": "실패",
}


def is_configured() -> bool:
    """NOTION_API_KEY + NOTION_SHORTS_DATABASE_ID 모두 설정 시 True."""
    return bool(os.getenv("NOTION_API_KEY")) and bool(os.getenv("NOTION_SHORTS_DATABASE_ID"))


def get_db_id() -> str:
    """NOTION_SHORTS_DATABASE_ID env var 읽기. 미설정 시 ValueError."""
    db_id = os.getenv("NOTION_SHORTS_DATABASE_ID", "").strip()
    if not db_id:
        raise ValueError("NOTION_SHORTS_DATABASE_ID 환경 변수가 설정되지 않았습니다.")
    return db_id


def _headers() -> dict[str, str]:
    api_key = os.getenv("NOTION_API_KEY", "")
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Notion-Version": _NOTION_VERSION,
    }


def _request(method: str, endpoint: str, **kwargs) -> requests.Response:
    """NOTION_API_KEY 기반 REST 호출."""
    url = f"{_NOTION_API_BASE}/{endpoint.lstrip('/')}"
    resp = requests.request(method, url, headers=_headers(), timeout=30, **kwargs)
    time.sleep(_RATE_LIMIT_DELAY)
    return resp


def _build_page_properties(item: dict) -> dict:
    """content_db 행 → Notion 페이지 properties JSON 변환."""
    title = (item.get("title") or item.get("topic") or "").strip() or "제목 없음"
    channel = item.get("channel", "")
    topic = item.get("topic", "")
    status = _STATUS_MAP.get(item.get("status", ""), "⏳대기")
    duration = float(item.get("duration_sec") or 0)
    cost = float(item.get("cost_usd") or 0)
    job_id = item.get("job_id", "")
    yt_status_raw = item.get("youtube_status", "") or ""
    yt_status = _YT_STATUS_MAP.get(yt_status_raw, "대기중")
    yt_url = item.get("youtube_url", "") or ""
    created_at = item.get("created_at", "") or ""

    props: dict = {
        "제목": {"title": [{"text": {"content": title[:2000]}}]},
        "주제": {"rich_text": [{"text": {"content": topic[:2000]}}]},
        "상태": {"select": {"name": status}},
        "길이(초)": {"number": round(duration, 1)},
        "비용(USD)": {"number": round(cost, 4)},
        "Job ID": {"rich_text": [{"text": {"content": job_id[:500]}}]},
        "유튜브 상태": {"select": {"name": yt_status}},
    }

    if channel:
        props["채널"] = {"select": {"name": channel}}

    if yt_url:
        props["유튜브 URL"] = {"url": yt_url}

    # 날짜 파싱 (YYYY-MM-DD HH:MM:SS 또는 ISO 형식)
    if created_at:
        try:
            dt_str = created_at[:10]  # YYYY-MM-DD
            datetime.strptime(dt_str, "%Y-%m-%d")  # 유효성 검증
            props["생성일"] = {"date": {"start": dt_str}}
        except (ValueError, TypeError):
            pass

    return props


def create_page(item: dict) -> str:
    """Notion DB에 새 페이지 생성. notion_page_id 반환."""
    db_id = get_db_id()
    body = {
        "parent": {"database_id": db_id},
        "properties": _build_page_properties(item),
    }
    resp = _request("POST", "pages", json=body)
    resp.raise_for_status()
    return resp.json()["id"]


def update_page(notion_page_id: str, item: dict) -> bool:
    """기존 페이지 properties 업데이트."""
    body = {"properties": _build_page_properties(item)}
    resp = _request("PATCH", f"pages/{notion_page_id}", json=body)
    resp.raise_for_status()
    return True


def sync_item(item_id: int) -> dict:
    """
    단일 content_db 항목 동기화.
    - notion_page_id가 없으면 create_page() → DB에 저장
    - notion_page_id가 있으면 update_page()
    반환: {"action": "created"|"updated"|"skipped"|"error", "page_id": str, "error": str}
    """
    from execution.content_db import get_by_id, update_job

    item = get_by_id(item_id)
    if not item:
        return {"action": "skipped", "page_id": "", "error": f"item_id={item_id} not found"}

    try:
        existing_page_id = item.get("notion_page_id", "") or ""
        if existing_page_id:
            update_page(existing_page_id, item)
            return {"action": "updated", "page_id": existing_page_id, "error": ""}
        else:
            page_id = create_page(item)
            try:
                update_job(item_id, notion_page_id=page_id)
            except Exception as db_exc:
                # Notion 페이지는 생성됨 — page_id를 반환하되 경고 포함
                return {
                    "action": "created",
                    "page_id": page_id,
                    "error": f"DB 저장 실패(page_id 분실 위험): {db_exc}",
                }
            return {"action": "created", "page_id": page_id, "error": ""}
    except Exception as exc:
        return {"action": "error", "page_id": "", "error": str(exc)}


def sync_all(
    channel: str | None = None,
    since: str | None = None,
    status: str | None = None,
) -> list[dict]:
    """
    content_db에서 조건에 맞는 항목 전체 동기화.
    since: ISO 날짜 문자열 (예: "2026-03-01")
    반환: 각 항목의 sync 결과 목록
    """
    from execution.content_db import get_all, update_job

    items = get_all(channel=channel)
    if since:
        items = [i for i in items if (i.get("created_at") or "") >= since]
    if status:
        items = [i for i in items if i.get("status") == status]

    results = []
    for item in items:
        try:
            existing_page_id = item.get("notion_page_id", "") or ""
            if existing_page_id:
                update_page(existing_page_id, item)
                action, page_id, error = "updated", existing_page_id, ""
            else:
                page_id = create_page(item)
                try:
                    update_job(item["id"], notion_page_id=page_id)
                except Exception as db_exc:
                    action, error = "created", f"DB 저장 실패: {db_exc}"
                else:
                    action, error = "created", ""
        except Exception as exc:
            action, page_id, error = "error", "", str(exc)

        results.append({
            "action": action,
            "page_id": page_id,
            "error": error,
            "item_id": item["id"],
            "topic": item.get("topic", ""),
        })
    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _cli() -> None:
    parser = argparse.ArgumentParser(description="Notion Shorts 동기화")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--all", action="store_true", help="전체 항목 동기화")
    group.add_argument("--item-id", type=int, metavar="N", help="단일 항목 동기화")
    parser.add_argument("--since", default="", metavar="YYYY-MM-DD", help="특정 날짜 이후 항목만")
    parser.add_argument("--channel", default="", help="채널 필터")
    parser.add_argument("--status", default="", help="상태 필터 (success/pending/failed)")
    args = parser.parse_args()

    if not is_configured():
        print("ERROR: NOTION_API_KEY 또는 NOTION_SHORTS_DATABASE_ID 환경 변수가 없습니다.")
        raise SystemExit(1)

    if args.item_id:
        result = sync_item(args.item_id)
        action = result["action"]
        page_id = result.get("page_id", "")[:8]
        error = result.get("error", "")
        print(f"[Notion] {action} | page_id={page_id} | {error}")
    else:
        results = sync_all(
            channel=args.channel or None,
            since=args.since or None,
            status=args.status or None,
        )
        created = sum(1 for r in results if r["action"] == "created")
        updated = sum(1 for r in results if r["action"] == "updated")
        errors = sum(1 for r in results if r["action"] == "error")
        print(
            f"[Notion] 동기화 완료: 생성 {created} / 업데이트 {updated} / 오류 {errors} (총 {len(results)}건)"
        )
        for r in results:
            if r["action"] == "error":
                print(f"  ERROR [{r.get('item_id')}] {r.get('topic', '')}: {r.get('error', '')}")


if __name__ == "__main__":
    _cli()
