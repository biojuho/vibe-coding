"""
Notion API 클라이언트 - Joolife Hub용.
태스크 데이터베이스 CRUD 작업 처리.

Usage:
    python execution/notion_client.py list-tasks [--status "In Progress"]
    python execution/notion_client.py update-task --id PAGE_ID --status "Done"
    python execution/notion_client.py create-task --title "New Task" --status "To Do"

Required .env:
    NOTION_API_KEY=ntn_xxxxx
    NOTION_TASK_DATABASE_ID=xxxxx
"""

import argparse
import json
import os
from functools import lru_cache
from typing import Dict, List, Optional

import requests
from dotenv import load_dotenv

try:
    from execution.api_usage_tracker import log_api_call
except Exception:  # pragma: no cover - optional integration
    def log_api_call(**_kwargs):
        return None

load_dotenv()

NOTION_API_KEY = os.getenv("NOTION_API_KEY", "")
NOTION_TASK_DB = os.getenv("NOTION_TASK_DATABASE_ID", "") or os.getenv("NOTION_DATABASE_ID", "")
NOTION_BASE_URL = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"
NOTION_TASK_TITLE_PROPERTY = os.getenv("NOTION_TASK_TITLE_PROPERTY", "").strip() or None
NOTION_TASK_STATUS_PROPERTY = os.getenv("NOTION_TASK_STATUS_PROPERTY", "").strip() or None
NOTION_TASK_DUE_PROPERTY = os.getenv("NOTION_TASK_DUE_PROPERTY", "").strip() or None


def _headers() -> Dict:
    return {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


def is_configured() -> bool:
    return bool(NOTION_API_KEY and NOTION_TASK_DB)


def _request(method: str, endpoint: str, **kwargs) -> requests.Response:
    timeout = kwargs.pop("timeout", 30)
    resp = requests.request(
        method=method,
        url=f"{NOTION_BASE_URL}/{endpoint}",
        headers=_headers(),
        timeout=timeout,
        **kwargs,
    )
    log_api_call(
        provider="notion",
        endpoint=f"{method.upper()} /{endpoint}",
        caller_script="execution/notion_client.py",
    )
    return resp


@lru_cache(maxsize=1)
def _get_database_schema() -> Dict:
    if not is_configured():
        return {}
    resp = _request("GET", f"databases/{NOTION_TASK_DB}")
    if resp.status_code != 200:
        return {}
    return resp.json()


def _pick_property_by_type(properties: Dict, prop_type: str) -> Optional[str]:
    for prop_name, prop_val in properties.items():
        if prop_val.get("type") == prop_type:
            return prop_name
    return None


def _resolve_task_schema() -> Dict[str, Optional[str]]:
    schema = _get_database_schema()
    properties = schema.get("properties", {})

    title_name = NOTION_TASK_TITLE_PROPERTY or _pick_property_by_type(properties, "title")
    status_name = (
        NOTION_TASK_STATUS_PROPERTY
        or _pick_property_by_type(properties, "status")
        or _pick_property_by_type(properties, "select")
    )
    due_name = NOTION_TASK_DUE_PROPERTY or _pick_property_by_type(properties, "date")

    status_type = properties.get(status_name, {}).get("type") if status_name else None
    due_type = properties.get(due_name, {}).get("type") if due_name else None
    title_type = properties.get(title_name, {}).get("type") if title_name else None

    return {
        "title_name": title_name,
        "title_type": title_type,
        "status_name": status_name,
        "status_type": status_type,
        "due_name": due_name,
        "due_type": due_type,
    }


def _extract_title(props: Dict, schema: Dict[str, Optional[str]]) -> str:
    title_prop_name = schema.get("title_name")
    if title_prop_name and title_prop_name in props:
        title_prop = props.get(title_prop_name, {})
        title_arr = title_prop.get("title", [])
        return title_arr[0].get("plain_text", "") if title_arr else ""

    for prop_val in props.values():
        if prop_val.get("type") == "title":
            title_arr = prop_val.get("title", [])
            return title_arr[0].get("plain_text", "") if title_arr else ""
    return ""


def _extract_status(props: Dict, schema: Dict[str, Optional[str]]) -> str:
    status_prop_name = schema.get("status_name")
    if not status_prop_name or status_prop_name not in props:
        return ""

    prop = props.get(status_prop_name, {})
    prop_type = prop.get("type")
    if prop_type == "status":
        node = prop.get("status")
        return node.get("name", "") if node else ""
    if prop_type == "select":
        node = prop.get("select")
        return node.get("name", "") if node else ""
    return ""


def _extract_due_date(props: Dict, schema: Dict[str, Optional[str]]) -> Optional[str]:
    due_prop_name = schema.get("due_name")
    if due_prop_name and due_prop_name in props:
        prop = props.get(due_prop_name, {})
        if prop.get("type") == "date" and prop.get("date"):
            return prop["date"].get("start")

    for prop_val in props.values():
        if prop_val.get("type") == "date" and prop_val.get("date"):
            return prop_val["date"].get("start")
    return None


def list_tasks(status_filter: Optional[str] = None) -> List[Dict]:
    """태스크 목록 조회. status_filter로 상태별 필터링 가능."""
    if not is_configured():
        return []

    schema = _resolve_task_schema()
    payload = {"page_size": 100}
    status_prop_name = schema.get("status_name")
    status_prop_type = schema.get("status_type")
    if status_filter and status_prop_name:
        if status_prop_type == "status":
            payload["filter"] = {
                "property": status_prop_name,
                "status": {"equals": status_filter},
            }
        elif status_prop_type == "select":
            payload["filter"] = {
                "property": status_prop_name,
                "select": {"equals": status_filter},
            }

    resp = _request("POST", f"databases/{NOTION_TASK_DB}/query", json=payload, timeout=30)
    if resp.status_code != 200:
        return []

    tasks = []
    for page in resp.json().get("results", []):
        props = page.get("properties", {})
        title = _extract_title(props, schema)
        status = _extract_status(props, schema)
        due_date = _extract_due_date(props, schema)

        tasks.append(
            {
                "id": page["id"],
                "title": title,
                "status": status,
                "due_date": due_date,
                "url": page.get("url", ""),
            }
        )
    return tasks


def update_task_status(page_id: str, new_status: str) -> bool:
    """태스크 상태 업데이트."""
    if not is_configured():
        return False

    schema = _resolve_task_schema()
    status_name = schema.get("status_name")
    status_type = schema.get("status_type")
    if not status_name or status_type not in {"status", "select"}:
        return False

    if status_type == "status":
        status_payload = {"status": {"name": new_status}}
    else:
        status_payload = {"select": {"name": new_status}}

    resp = _request(
        "PATCH",
        f"pages/{page_id}",
        json={"properties": {status_name: status_payload}},
        timeout=30,
    )
    return resp.status_code == 200


def create_task(
    title: str, status: str = "To Do", due_date: Optional[str] = None
) -> Optional[str]:
    """새 태스크 생성. 생성된 page_id 반환."""
    if not is_configured():
        return None

    schema = _resolve_task_schema()
    title_name = schema.get("title_name")
    if not title_name:
        return None

    properties: Dict[str, Dict] = {
        title_name: {"title": [{"text": {"content": title}}]},
    }

    status_name = schema.get("status_name")
    status_type = schema.get("status_type")
    if status_name and status_type == "status":
        properties[status_name] = {"status": {"name": status}}
    elif status_name and status_type == "select":
        properties[status_name] = {"select": {"name": status}}

    due_name = schema.get("due_name")
    due_type = schema.get("due_type")
    if due_date and due_name and due_type == "date":
        properties[due_name] = {"date": {"start": due_date}}

    resp = _request(
        "POST",
        "pages",
        json={"parent": {"database_id": NOTION_TASK_DB}, "properties": properties},
        timeout=30,
    )
    if resp.status_code in {200, 201}:
        return resp.json().get("id")
    return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Joolife Notion Client")
    sub = parser.add_subparsers(dest="cmd")

    p_list = sub.add_parser("list-tasks")
    p_list.add_argument("--status")

    p_update = sub.add_parser("update-task")
    p_update.add_argument("--id", required=True)
    p_update.add_argument("--status", required=True)

    p_create = sub.add_parser("create-task")
    p_create.add_argument("--title", required=True)
    p_create.add_argument("--status", default="To Do")
    p_create.add_argument("--due-date")

    args = parser.parse_args()

    if args.cmd == "list-tasks":
        tasks = list_tasks(args.status)
        print(json.dumps(tasks, indent=2, ensure_ascii=False))
    elif args.cmd == "update-task":
        ok = update_task_status(args.id, args.status)
        print("Updated" if ok else "Failed")
    elif args.cmd == "create-task":
        pid = create_task(args.title, args.status, getattr(args, "due_date", None))
        print(f"Created: {pid}" if pid else "Failed")
    else:
        parser.print_help()
