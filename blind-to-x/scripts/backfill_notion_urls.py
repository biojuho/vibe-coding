from __future__ import annotations

import argparse
import asyncio
import csv
import logging
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from blind_scraper import ConfigManager, NotionUploader  # noqa: E402

LOGGER = logging.getLogger("notion_url_backfill")
URL_PATTERN = re.compile(r"https?://[^\s\]>)\"']+", re.IGNORECASE)


def _extract_rich_text_value(prop: dict[str, Any] | None) -> str:
    if not isinstance(prop, dict):
        return ""
    rich_text = prop.get("rich_text")
    if not isinstance(rich_text, list):
        return ""

    chunks: list[str] = []
    for item in rich_text:
        if not isinstance(item, dict):
            continue
        plain_text = item.get("plain_text")
        if plain_text:
            chunks.append(str(plain_text))
            continue
        text_obj = item.get("text")
        if isinstance(text_obj, dict) and text_obj.get("content"):
            chunks.append(str(text_obj["content"]))
    return "".join(chunks).strip()


def _extract_url_property_value(prop: dict[str, Any] | None, prop_type: str) -> str:
    if not isinstance(prop, dict):
        return ""
    if prop_type == "url":
        value = prop.get("url")
        return str(value).strip() if value else ""
    if prop_type == "rich_text":
        return _extract_rich_text_value(prop)
    return ""


def _extract_first_url(text: str) -> str:
    if not text:
        return ""
    match = URL_PATTERN.search(text)
    if not match:
        return ""
    return match.group(0).rstrip(".,);]")


def _build_url_payload(prop_type: str, canonical_url: str) -> dict[str, Any]:
    if prop_type == "url":
        return {"url": canonical_url}
    return {"rich_text": [{"type": "text", "text": {"content": canonical_url[:2000]}}]}


def _resolve_failed_output_path(failed_output: str) -> Path:
    out = Path(failed_output)
    if not out.is_absolute():
        out = ROOT / out
    out.parent.mkdir(parents=True, exist_ok=True)
    return out


def _append_failed_record(
    csv_path: Path,
    page_id: str,
    error: str,
    source_url: str,
    canonical_url: str,
) -> bool:
    file_exists = csv_path.exists()
    with csv_path.open("a", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(
            fp,
            fieldnames=["page_id", "error", "source_url", "canonical_url"],
        )
        if not file_exists:
            writer.writeheader()
        writer.writerow(
            {
                "page_id": page_id,
                "error": error,
                "source_url": source_url,
                "canonical_url": canonical_url,
            }
        )
    return True


async def run_backfill(
    config_path: str,
    page_size: int,
    limit: int,
    apply: bool,
    *,
    start_cursor: str | None = None,
    max_retries: int = 3,
    backoff_seconds: float = 1.5,
    failed_output: str = ".tmp/backfill_failed.csv",
) -> int:
    config = ConfigManager(config_path)
    notion = NotionUploader(config)

    if not await notion.ensure_schema():
        print(f"[FAIL] Notion schema validation failed: {notion.last_error_code}")
        if notion.last_error_message:
            print(f"       {notion.last_error_message}")
        return 2
    if notion.client is None:
        print("[FAIL] Notion client is not initialized.")
        return 2

    page_size = min(max(page_size, 1), 100)
    max_retries = max(max_retries, 1)
    backoff_seconds = max(backoff_seconds, 0.0)
    url_prop_name = notion.props["url"]
    memo_prop_name = notion.props["memo"]
    url_prop_type = notion._db_properties[url_prop_name]["type"]
    client = notion.client
    failed_output_path = _resolve_failed_output_path(failed_output) if apply else None

    stats = {
        "scanned": 0,
        "updated": 0,
        "would_update": 0,
        "already_normalized": 0,
        "missing_source": 0,
        "failed": 0,
        "retried": 0,
        "failed_records_written": 0,
    }

    next_cursor: str | None = start_cursor or None
    stop = False
    while not stop:
        if hasattr(notion, "query_collection"):
            response = await notion.query_collection(page_size=page_size, start_cursor=next_cursor, filter=None)
        else:
            query_args: dict[str, Any] = {"database_id": notion.database_id, "page_size": page_size}
            if next_cursor:
                query_args["start_cursor"] = next_cursor
            response = await client.databases.query(**query_args)
        results = response.get("results", []) or []

        for page in results:
            if limit > 0 and stats["scanned"] >= limit:
                stop = True
                break

            stats["scanned"] += 1
            page_id = page.get("id", "")
            properties = page.get("properties", {}) or {}

            current_url_value = _extract_url_property_value(properties.get(url_prop_name), url_prop_type)
            source_url = current_url_value
            if not source_url:
                memo_text = _extract_rich_text_value(properties.get(memo_prop_name))
                source_url = _extract_first_url(memo_text)

            if not source_url:
                stats["missing_source"] += 1
                continue

            canonical = NotionUploader.canonicalize_url(source_url)
            if not canonical:
                stats["missing_source"] += 1
                continue

            current_canonical = NotionUploader.canonicalize_url(current_url_value) if current_url_value else ""
            if current_canonical and current_canonical == canonical:
                stats["already_normalized"] += 1
                continue

            if apply:
                payload = _build_url_payload(url_prop_type, canonical)
                updated = False
                for attempt in range(1, max_retries + 1):
                    try:
                        await client.pages.update(page_id=page_id, properties={url_prop_name: payload})
                        stats["updated"] += 1
                        updated = True
                        break
                    except Exception as exc:
                        if attempt < max_retries:
                            stats["retried"] += 1
                            sleep_for = backoff_seconds * attempt
                            LOGGER.warning(
                                "Update failed for page %s (%s/%s): %s. Retrying in %.1fs.",
                                page_id,
                                attempt,
                                max_retries,
                                exc,
                                sleep_for,
                            )
                            if sleep_for > 0:
                                await asyncio.sleep(sleep_for)
                        else:
                            stats["failed"] += 1
                            LOGGER.error("Failed to update page %s after %s attempt(s): %s", page_id, max_retries, exc)
                            if failed_output_path and _append_failed_record(
                                failed_output_path,
                                page_id=page_id,
                                error=str(exc),
                                source_url=source_url,
                                canonical_url=canonical,
                            ):
                                stats["failed_records_written"] += 1
                if not updated:
                    continue
            else:
                LOGGER.info("[DRY-RUN] page=%s -> %s", page_id, canonical)
                stats["would_update"] += 1

        if stop or not response.get("has_more"):
            break
        next_cursor = response.get("next_cursor")

    mode = "APPLY" if apply else "DRY-RUN"
    print(f"[SUMMARY] Notion URL backfill ({mode})")
    print(f"  scanned: {stats['scanned']}")
    print(f"  already_normalized: {stats['already_normalized']}")
    print(f"  missing_source: {stats['missing_source']}")
    if apply:
        print(f"  updated: {stats['updated']}")
        print(f"  failed: {stats['failed']}")
        print(f"  retried: {stats['retried']}")
        print(f"  failed_records_written: {stats['failed_records_written']}")
        if stats["failed"] > 0 and failed_output_path:
            print(f"  failed_output: {failed_output_path}")
    else:
        print(f"  would_update: {stats['would_update']}")

    return 1 if stats["failed"] > 0 else 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Backfill canonical source URLs into existing Notion pages."
    )
    parser.add_argument("--config", default="config.yaml", help="Path to config file")
    parser.add_argument("--page-size", type=int, default=50, help="Notion query page size (1-100)")
    parser.add_argument("--limit", type=int, default=0, help="Max pages to scan (0 means all)")
    parser.add_argument("--start-cursor", default="", help="Start cursor for resuming backfill")
    parser.add_argument("--max-retries", type=int, default=3, help="Max retries per page update")
    parser.add_argument("--backoff-seconds", type=float, default=1.5, help="Backoff base seconds")
    parser.add_argument(
        "--failed-output",
        default=".tmp/backfill_failed.csv",
        help="CSV path to write failed updates",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually update Notion pages. Default is dry-run.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    return asyncio.run(
        run_backfill(
            config_path=args.config,
            page_size=args.page_size,
            limit=args.limit,
            apply=args.apply,
            start_cursor=args.start_cursor.strip() or None,
            max_retries=args.max_retries,
            backoff_seconds=args.backoff_seconds,
            failed_output=args.failed_output,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
