from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if hasattr(sys.stdout, "reconfigure") and sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

from config import ConfigManager, load_env  # noqa: E402
from pipeline.notion_upload import NotionUploader  # noqa: E402

REJECTED_STATUSES = {"반려", "반려됨"}


def _plain_text_from_block(block: dict[str, Any]) -> str:
    block_type = block.get("type")
    if not block_type:
        return ""
    payload = block.get(block_type, {})
    parts = [item.get("plain_text", "") for item in payload.get("rich_text", []) or []]
    return "".join(parts).strip()


def _prefixed_value(lines: list[str], prefix: str) -> str:
    for line in lines:
        if line.startswith(prefix):
            return line.split(":", 1)[1].strip()
    return ""


def _extract_selection_summary(record: dict[str, Any], sections: dict[str, list[str]]) -> str:
    memo_lines = [line.strip() for line in str(record.get("memo") or "").splitlines() if line.strip()]
    value = _prefixed_value(memo_lines, "운영자 해석")
    if value:
        return value
    value = _prefixed_value(memo_lines, "왜 고름")
    if value:
        return value

    intel_lines = sections.get("콘텐츠 인텔리전스", [])
    value = _prefixed_value(intel_lines, "왜 고름")
    if value:
        return value
    return ""


def _extract_creator_take(record: dict[str, Any], selection_summary: str) -> str:
    creator_take = str(record.get("creator_take") or "").strip()
    if creator_take:
        return creator_take

    memo_lines = [line.strip() for line in str(record.get("memo") or "").splitlines() if line.strip()]
    creator_take = _prefixed_value(memo_lines, "운영자 해석")
    if creator_take:
        return creator_take

    return selection_summary


def _extract_evidence_anchor(record: dict[str, Any], sections: dict[str, list[str]]) -> str:
    existing = str(record.get("evidence_anchor") or "").strip()
    if existing:
        return existing

    intel_lines = sections.get("콘텐츠 인텔리전스", [])
    value = _prefixed_value(intel_lines, "공감 앵커")
    if value:
        return value

    memo_lines = [line.strip() for line in str(record.get("memo") or "").splitlines() if line.strip()]
    return _prefixed_value(memo_lines, "공감 앵커")


def _extract_quality_gate_report(sections: dict[str, list[str]]) -> str:
    for heading, lines in sections.items():
        if "품질 검증" in heading:
            return "\n".join(line for line in lines if line)
    return ""


def _detect_publish_platforms(record: dict[str, Any], sections: dict[str, list[str]]) -> list[str]:
    existing = record.get("publish_platforms")
    if isinstance(existing, list) and existing:
        return existing

    platforms: list[str] = []
    tweet_body = str(record.get("tweet_body") or "").strip()
    threads_body = str(record.get("threads_body") or "").strip()
    blog_body = str(record.get("blog_body") or "").strip()

    if tweet_body:
        platforms.append("숏폼")
    if threads_body:
        platforms.append("Threads")
    if blog_body:
        platforms.append("블로그")

    for heading in sections:
        if "숏폼 초안" in heading or "X(Twitter) 초안" in heading:
            platforms.append("숏폼")
        elif "Threads 초안" in heading:
            platforms.append("Threads")
        elif "뉴스레터 초안" in heading:
            platforms.append("뉴스레터")
        elif "네이버 블로그 초안" in heading or "블로그 초안" in heading:
            platforms.append("블로그")

    deduped: list[str] = []
    for platform in platforms:
        if platform not in deduped:
            deduped.append(platform)
    return deduped


def _infer_rejection_reasons(
    record: dict[str, Any],
    review_brief: dict[str, Any],
    current_risk_flags: list[str],
    publish_platforms: list[str],
    selection_summary: str,
) -> list[str]:
    current = record.get("rejection_reasons")
    if isinstance(current, list) and current:
        return current
    if str(record.get("status") or "").strip() not in REJECTED_STATUSES:
        return []

    allowed_from_risks = {
        "근거 약함",
        "팩트 경계",
        "클리셰",
        "CTA 약함",
        "독자 핏 약함",
        "갈등 과열",
    }
    combined_flags = list(current_risk_flags) + list(review_brief.get("risk_flags", []))
    inferred = []
    for flag in combined_flags:
        if flag in allowed_from_risks and flag not in inferred:
            inferred.append(flag)
    if not inferred and not selection_summary:
        inferred.append("원문 힘 약함")
    if not inferred and not publish_platforms:
        inferred.append("채널 부적합")
    return inferred[:2]


def build_review_backfill_updates(
    notion: NotionUploader,
    record: dict[str, Any],
    sections: dict[str, list[str]],
) -> dict[str, Any]:
    selection_summary = _extract_selection_summary(record, sections)
    creator_take = _extract_creator_take(record, selection_summary)
    evidence_anchor = _extract_evidence_anchor(record, sections)
    quality_gate_report = _extract_quality_gate_report(sections)
    publish_platforms = _detect_publish_platforms(record, sections)

    drafts: dict[str, Any] = {"creator_take": creator_take}
    if "숏폼" in publish_platforms:
        drafts["twitter"] = "__present__"
    if "Threads" in publish_platforms:
        drafts["threads"] = "__present__"
    if "뉴스레터" in publish_platforms:
        drafts["newsletter"] = "__present__"
    if "블로그" in publish_platforms:
        drafts["naver_blog"] = "__present__"

    analysis = {
        "selection_summary": selection_summary,
        "empathy_anchor": evidence_anchor,
        "hard_reject_reasons": record.get("rejection_reasons") or [],
    }
    post_data = {
        "source": record.get("source") or "blind",
        "quality_gate_report": quality_gate_report,
    }
    review_brief = notion._build_review_brief(post_data, drafts, analysis)
    current_risk_flags = record.get("risk_flags") or []
    if isinstance(current_risk_flags, str):
        current_risk_flags = [item.strip() for item in current_risk_flags.split(",") if item.strip()]

    updates: dict[str, Any] = {}
    for key in (
        "creator_take",
        "review_focus",
        "feedback_request",
        "evidence_anchor",
        "risk_flags",
        "publish_platforms",
    ):
        current = record.get(key)
        if current in (None, "", []):
            value = review_brief.get(key)
            if value not in (None, "", []):
                updates[key] = value

    current_rejections = record.get("rejection_reasons")
    if current_rejections in (None, "", []):
        inferred_rejections = _infer_rejection_reasons(
            record,
            review_brief,
            current_risk_flags,
            publish_platforms,
            selection_summary,
        )
        if inferred_rejections:
            updates["rejection_reasons"] = inferred_rejections

    return updates


async def _fetch_all_pages(notion: NotionUploader, limit: int | None) -> list[dict[str, Any]]:
    pages: list[dict[str, Any]] = []
    cursor = None
    date_prop = notion.props.get("date")
    sorts = (
        [{"property": date_prop, "direction": "descending"}]
        if date_prop and date_prop in notion._db_properties
        else [{"timestamp": "last_edited_time", "direction": "descending"}]
    )

    while True:
        remaining = None if limit is None else max(limit - len(pages), 0)
        if remaining == 0:
            break

        page_size = min(100, remaining or 100)
        response = await notion.query_collection(
            page_size=page_size,
            start_cursor=cursor,
            sorts=sorts,
        )
        batch = response.get("results", [])
        if not batch:
            break

        pages.extend(batch)
        if limit is not None and len(pages) >= limit:
            return pages[:limit]

        if not response.get("has_more") or not response.get("next_cursor"):
            break
        cursor = response.get("next_cursor")

    return pages


async def _fetch_page_sections(notion: NotionUploader, page_id: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    cursor = None
    current_heading = "ROOT"

    while True:
        response = await notion.client.blocks.children.list(
            block_id=page_id,
            page_size=100,
            start_cursor=cursor,
        )
        for block in response.get("results", []):
            block_type = block.get("type")
            text = _plain_text_from_block(block)
            if block_type in {"heading_1", "heading_2", "heading_3"} and text:
                current_heading = text
                sections.setdefault(current_heading, [])
                continue
            if text:
                sections.setdefault(current_heading, []).append(text)

        if not response.get("has_more") or not response.get("next_cursor"):
            break
        cursor = response.get("next_cursor")

    return sections


async def run(config_path: str, apply_changes: bool, limit: int | None) -> int:
    load_env()
    config = ConfigManager(config_path)
    notion = NotionUploader(config)

    if not await notion.ensure_schema():
        print("[BACKFILL REVIEW COLUMNS]")
        print(f"  status: FAIL ({notion.last_error_message})")
        return 2

    pages = await _fetch_all_pages(notion, limit=limit)
    scanned = len(pages)
    candidates = 0
    updated = 0
    samples: list[str] = []

    for page in pages:
        record = notion.extract_page_record(page)
        sections = await _fetch_page_sections(notion, page["id"])
        updates = build_review_backfill_updates(notion, record, sections)
        if not updates:
            continue

        candidates += 1
        if len(samples) < 5:
            samples.append(f"{record.get('title', '(untitled)')} -> {', '.join(updates.keys())}")

        if apply_changes:
            success = await notion.update_page_properties(page["id"], updates)
            if success:
                updated += 1

    print("[BACKFILL REVIEW COLUMNS]")
    print(f"  scanned: {scanned}")
    print(f"  candidates: {candidates}")
    print(f"  updated: {updated if apply_changes else 0}")
    if samples:
        print("  samples:")
        for sample in samples:
            print(f"    - {sample}")

    if not apply_changes:
        print("  status: DRY-RUN")
        print("  action: rerun with --apply to write the derived review columns")
    else:
        print("  status: APPLIED")

    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Backfill reviewer-first Notion columns for existing blind-to-x pages."
    )
    parser.add_argument("--config", default="config.yaml", help="Path to config file")
    parser.add_argument("--limit", type=int, default=None, help="Optional max page count to scan")
    parser.add_argument("--apply", action="store_true", help="Actually update Notion pages")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    return asyncio.run(run(args.config, args.apply, args.limit))


if __name__ == "__main__":
    raise SystemExit(main())
