from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.sync_notion_review_schema import (
    _merge_multi_select_options,
    _merge_select_options,
    REVIEW_SCHEMA,
    build_schema_patch,
)  # noqa: E402


class _FakeNotion:
    def __init__(self, props: dict[str, str], db_properties: dict[str, dict]):
        self.props = props
        self._db_properties = db_properties
        self.DEFAULT_PROPS = {"creator_take": "creator_take"}


def test_merge_multi_select_options_keeps_existing_id_and_color_and_adds_new():
    current_prop = {
        "multi_select": {
            "options": [
                {"name": "A", "color": "yellow", "id": "id-a"},
                {"name": "B", "color": "blue", "id": "id-b"},
            ]
        }
    }
    desired_options = [
        {"name": "A", "color": "green"},
        {"name": "C", "color": "red"},
    ]

    merged = _merge_multi_select_options(current_prop, desired_options)

    assert merged == [
        {"id": "id-a", "name": "A", "color": "yellow"},
        {"id": "id-b", "name": "B", "color": "blue"},
        {"name": "C", "color": "red"},
    ]


def test_merge_select_options_keeps_existing_id_and_color_and_adds_new():
    current_prop = {
        "select": {
            "options": [
                {"name": "X", "color": "purple", "id": "id-x"},
                {"name": "Y", "color": "brown"},
            ]
        }
    }
    desired_options = [
        {"name": "X", "color": "yellow"},
        {"name": "Z", "color": "green"},
    ]

    merged = _merge_select_options(current_prop, desired_options)

    assert merged == [
        {"id": "id-x", "name": "X", "color": "purple"},
        {"name": "Y", "color": "brown"},
        {"name": "Z", "color": "green"},
    ]


def test_build_schema_patch_adds_missing_or_updated_properties():
    review_schema = REVIEW_SCHEMA
    existing_risk_name = review_schema["risk_flags"]["multi_select"]["options"][0]["name"]
    existing_status_name = review_schema["x_publish_status"]["select"]["options"][0]["name"]
    notion = _FakeNotion(
        props={"creator_take": "creator_take"},
        db_properties={
            # Missing creator_take currently -> should be added from REVIEW_SCHEMA.
            "risk_flags": {
                "multi_select": {
                    "options": [
                        {"name": existing_risk_name, "color": "yellow", "id": "id-existing"},
                    ]
                },
                "type": "multi_select",
            },
            "x_publish_status": {
                "type": "select",
                "select": {
                    "options": [
                        {"name": existing_status_name, "color": "blue", "id": "id-ready"},
                        {"name": "Archived", "color": "default", "id": "id-archived"},
                    ]
                },
            },
            "publish_platforms": {
                "multi_select": {
                    "options": [
                        {"name": "X", "color": "blue", "id": "id-x"},
                    ]
                },
                "type": "multi_select",
            },
        },
    )

    patch, skipped = build_schema_patch(notion)

    required_keys = {"creator_take", "risk_flags", "publish_platforms", "x_publish_status"}
    assert required_keys.issubset(set(patch))
    assert "rich_text" in patch["creator_take"]

    expected_risk_names = {
        option.get("name")
        for option in review_schema["risk_flags"]["multi_select"]["options"]
    } | {existing_risk_name}
    assert {
        option["name"] for option in patch["risk_flags"]["multi_select"]["options"]
    } == expected_risk_names
    assert any(option.get("id") == "id-existing" for option in patch["risk_flags"]["multi_select"]["options"])

    expected_publish_names = {
        option.get("name")
        for option in review_schema["publish_platforms"]["multi_select"]["options"]
    } | {"X"}
    assert {
        option["name"] for option in patch["publish_platforms"]["multi_select"]["options"]
    } == expected_publish_names

    expected_status_names = {
        option.get("name")
        for option in review_schema["x_publish_status"]["select"]["options"]
    } | {"Archived"}
    assert {
        option["name"] for option in patch["x_publish_status"]["select"]["options"]
    } == expected_status_names
    assert any(option.get("id") == "id-ready" for option in patch["x_publish_status"]["select"]["options"])
    assert skipped == []


def test_build_schema_patch_skips_mismatched_type_and_reports_skip():
    notion = _FakeNotion(
        props={},
        db_properties={
            "x_publish_status": {
                "type": "rich_text",
            },
        },
    )

    patch, skipped = build_schema_patch(notion)

    assert patch["creator_take"] == {"rich_text": {}}
    assert "x_publish_status: existing type=rich_text, expected=select" in skipped
