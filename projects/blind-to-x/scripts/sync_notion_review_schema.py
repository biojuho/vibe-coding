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


def _option(name: str, color: str) -> dict[str, str]:
    return {"name": name, "color": color}


REVIEW_SCHEMA: dict[str, dict] = {
    "creator_take": {"rich_text": {}},
    "review_focus": {"rich_text": {}},
    "feedback_request": {"rich_text": {}},
    "evidence_anchor": {"rich_text": {}},
    "risk_flags": {
        "multi_select": {
            "options": [
                _option("근거 약함", "yellow"),
                _option("팩트 경계", "red"),
                _option("클리셰", "orange"),
                _option("CTA 약함", "brown"),
                _option("후속 반응 약함", "gray"),
                _option("독자 핏 약함", "blue"),
                _option("갈등 과열", "pink"),
                _option("해석 약함", "purple"),
                _option("품질 이상", "default"),
            ]
        }
    },
    "rejection_reasons": {
        "multi_select": {
            "options": [
                _option("근거 약함", "yellow"),
                _option("팩트 경계", "red"),
                _option("클리셰", "orange"),
                _option("CTA 약함", "brown"),
                _option("독자 핏 약함", "blue"),
                _option("갈등 과열", "pink"),
                _option("원문 힘 약함", "default"),
                _option("중복 소재", "gray"),
                _option("채널 부적합", "purple"),
            ]
        }
    },
    "publish_platforms": {
        "multi_select": {
            "options": [
                _option("숏폼", "blue"),
                _option("Threads", "purple"),
                _option("뉴스레터", "green"),
                _option("블로그", "orange"),
            ]
        }
    },
}


def _merge_multi_select_options(current_prop: dict, desired_options: list[dict[str, str]]) -> list[dict[str, str]]:
    current_options = list((current_prop.get("multi_select") or {}).get("options") or [])
    merged_by_name: dict[str, dict[str, str]] = {}

    for option in current_options:
        name = option.get("name")
        if name:
            merged_by_name[name] = {k: v for k, v in option.items() if k in {"id", "name", "color"} and v}

    for option in desired_options:
        name = option.get("name")
        if not name:
            continue
        existing = merged_by_name.get(name, {})
        existing.setdefault("name", name)
        existing.setdefault("color", option.get("color", "default"))
        merged_by_name[name] = existing

    return list(merged_by_name.values())


def build_schema_patch(notion: NotionUploader) -> tuple[dict[str, dict], list[str]]:
    patch: dict[str, dict] = {}
    skipped: list[str] = []

    for semantic_key, definition in REVIEW_SCHEMA.items():
        prop_name = notion.props.get(semantic_key) or notion.DEFAULT_PROPS.get(semantic_key, semantic_key)
        current = notion._db_properties.get(prop_name)
        expected_type = next(iter(definition.keys()))

        if not current:
            patch[prop_name] = definition
            continue

        current_type = current.get("type")
        if current_type != expected_type:
            skipped.append(f"{prop_name}: existing type={current_type}, expected={expected_type}")
            continue

        if expected_type == "multi_select":
            desired_options = definition["multi_select"]["options"]
            merged = _merge_multi_select_options(current, desired_options)
            current_names = {item.get("name") for item in (current.get("multi_select") or {}).get("options") or []}
            merged_names = {item.get("name") for item in merged}
            if merged_names != current_names:
                patch[prop_name] = {"multi_select": {"options": merged}}

    return patch, skipped


async def run(config_path: str, apply_changes: bool) -> int:
    load_env()
    config = ConfigManager(config_path)
    notion = NotionUploader(config)

    if not await notion.ensure_schema():
        print("[SYNC REVIEW SCHEMA]")
        print("  status: FAIL")
        print(f"  error: {notion.last_error_message}")
        return 2

    patch, skipped = build_schema_patch(notion)

    print("[SYNC REVIEW SCHEMA]")
    print(f"  collection_kind: {notion.collection_kind}")
    print(f"  missing_or_updatable: {list(patch.keys()) or '(none)'}")
    if skipped:
        print("  skipped:")
        for item in skipped:
            print(f"    - {item}")

    if not patch:
        print("  status: NOOP")
        return 0

    if not apply_changes:
        print("  status: DRY-RUN")
        print("  action: rerun with --apply to add these review columns/options to Notion")
        return 0

    await notion.update_collection_properties(patch)
    print("  status: APPLIED")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Add reviewer-centered columns/options to the blind-to-x Notion DB.")
    parser.add_argument("--config", default="config.yaml", help="Path to config file")
    parser.add_argument("--apply", action="store_true", help="Actually patch the Notion schema")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    return asyncio.run(run(args.config, args.apply))


if __name__ == "__main__":
    raise SystemExit(main())
