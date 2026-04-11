from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import ConfigManager, load_env  # noqa: E402
from pipeline.notion_upload import NotionUploader  # noqa: E402


def _mask_token(value: str) -> str:
    if not value:
        return "(empty)"
    if len(value) <= 8:
        return value
    return f"{value[:4]}...{value[-4:]}"


async def run(config_path: str) -> int:
    load_env()
    config = ConfigManager(config_path)
    notion = NotionUploader(config)

    print("[NOTION DOCTOR]")
    print(f"  token: {_mask_token(notion.api_key or '')}")
    print(f"  raw_id: {notion.raw_database_id or '(empty)'}")
    print(f"  normalized_id: {notion.database_id or '(empty)'}")

    ok = await notion.ensure_schema()
    if ok:
        print("  status: PASS")
        print(f"  collection_kind: {notion.collection_kind}")
        print(f"  resolved_props: {notion.props}")
        return 0

    print("  status: FAIL")
    print(f"  error_code: {notion.last_error_code}")
    print(f"  error_message: {notion.last_error_message}")

    previews = await notion.list_accessible_sources(limit=10)
    if previews:
        print("  accessible_objects:")
        for item in previews:
            print(f"    - {item}")

    print("  action:")
    print("    1) Verify NOTION_DATABASE_ID is a real database/data_source ID")
    print("    2) Share the target Notion DB/Data Source with the integration")
    print("    3) Ensure URL property exists (url or rich_text type)")
    print("    4) If reviewer columns are missing, run: py -3 scripts/sync_notion_review_schema.py --config config.yaml --apply")
    return 2


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Diagnose Notion connection/schema for blind-to-x.")
    parser.add_argument("--config", default="config.yaml", help="Path to config file")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    return asyncio.run(run(args.config))


if __name__ == "__main__":
    raise SystemExit(main())
