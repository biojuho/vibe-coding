#!/usr/bin/env python3
"""Audit completion claims against concrete evidence.

The manifest format is intentionally small:

{
  "objective": "Ship the product",
  "success_criteria": ["Every explicit requirement is mapped to evidence"],
  "items": [
    {
      "requirement": "Inventory GitHub projects",
      "artifacts": ["projects/hanwoo-dashboard"],
      "evidence": ["python ...github_project_inventory.py --include-prs"],
      "verified": true,
      "coverage": "complete"
    }
  ]
}
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


PASSING_COVERAGE = {"complete", "covered", "pass", "passed"}


def _read_manifest_text(path: Path) -> str:
    try:
        raw = path.read_bytes()
    except FileNotFoundError as exc:
        raise SystemExit(f"manifest not found: {path}") from exc

    for encoding in ("utf-8-sig", "utf-16"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue

    raise SystemExit(f"manifest must be readable as UTF-8 or UTF-16 JSON: {path}")


def _load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(_read_manifest_text(path))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit("manifest root must be a JSON object")
    return data


def _string_list(value: Any) -> list[str]:
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        if isinstance(item, str) and item.strip():
            result.append(item.strip())
    return result


def _item_issue(
    index: int,
    code: str,
    message: str,
    *,
    requirement: str = "",
    blockers: list[str] | None = None,
) -> dict[str, Any]:
    issue: dict[str, Any] = {"index": index, "code": code, "message": message}
    if requirement:
        issue["requirement"] = requirement
    if blockers:
        issue["blockers"] = blockers
    return issue


def audit_manifest(data: dict[str, Any]) -> dict[str, Any]:
    objective = data.get("objective")
    if not isinstance(objective, str) or not objective.strip():
        raise SystemExit("manifest must include a non-empty objective")

    raw_items = data.get("items", data.get("checklist"))
    if not isinstance(raw_items, list) or not raw_items:
        raise SystemExit("manifest must include non-empty items or checklist")

    issues: list[dict[str, Any]] = []
    normalized_items: list[dict[str, Any]] = []
    complete_count = 0
    blocked_count = 0

    for index, raw_item in enumerate(raw_items, start=1):
        if not isinstance(raw_item, dict):
            issues.append(_item_issue(index, "invalid_item", "Checklist item must be an object."))
            continue

        requirement = raw_item.get("requirement")
        requirement_text = requirement.strip() if isinstance(requirement, str) else ""
        artifacts = _string_list(raw_item.get("artifacts"))
        evidence = _string_list(raw_item.get("evidence"))
        blockers = _string_list(raw_item.get("blockers"))
        verified = raw_item.get("verified") is True
        coverage = str(raw_item.get("coverage", "")).strip().lower()
        item_issues: list[str] = []

        if not requirement_text:
            item_issues.append("missing_requirement")
            issues.append(_item_issue(index, "missing_requirement", "Requirement text is missing."))
        if not artifacts:
            item_issues.append("missing_artifacts")
            issues.append(_item_issue(index, "missing_artifacts", "Requirement is not mapped to artifacts."))
        if not evidence:
            item_issues.append("missing_evidence")
            issues.append(_item_issue(index, "missing_evidence", "Requirement is not mapped to evidence."))
        if not verified:
            item_issues.append("not_verified")
            issues.append(_item_issue(index, "not_verified", "Requirement has not been verified."))
        if coverage not in PASSING_COVERAGE:
            item_issues.append("incomplete_coverage")
            issues.append(
                _item_issue(
                    index,
                    "incomplete_coverage",
                    f"Coverage must be one of {sorted(PASSING_COVERAGE)}.",
                )
            )
        if blockers:
            blocked_count += 1
            item_issues.append("blocked")
            issues.append(
                _item_issue(
                    index,
                    "blocked",
                    "Requirement has unresolved blocker(s): " + "; ".join(blockers),
                    requirement=requirement_text,
                    blockers=blockers,
                )
            )

        passed = not item_issues
        if passed:
            complete_count += 1
        normalized_items.append(
            {
                "index": index,
                "requirement": requirement_text,
                "artifacts": artifacts,
                "evidence": evidence,
                "verified": verified,
                "coverage": coverage,
                "blockers": blockers,
                "passed": passed,
                "issues": item_issues,
            }
        )

    status = "complete" if not issues and complete_count == len(raw_items) else "incomplete"
    return {
        "objective": objective.strip(),
        "status": status,
        "summary": {
            "item_count": len(raw_items),
            "complete_count": complete_count,
            "issue_count": len(issues),
            "blocked_count": blocked_count,
        },
        "items": normalized_items,
        "issues": issues,
    }


def build_template(objective: str) -> dict[str, Any]:
    return {
        "objective": objective,
        "success_criteria": [
            "Restate the objective as concrete deliverables.",
            "Map every explicit requirement to artifacts and real evidence.",
            "Mark complete only when every item is verified with complete coverage.",
        ],
        "items": [
            {
                "requirement": "Replace this with an explicit user requirement",
                "artifacts": ["path/or/url/or/commit"],
                "evidence": ["command output, test result, CI run, screenshot, or PR state"],
                "verified": False,
                "coverage": "missing",
                "blockers": [],
            }
        ],
    }


def _print_text(result: dict[str, Any]) -> None:
    print(f"status: {result['status']}")
    print(f"objective: {result['objective']}")
    summary = result["summary"]
    print(
        "summary: "
        f"{summary['complete_count']}/{summary['item_count']} complete, "
        f"{summary['issue_count']} issue(s), {summary['blocked_count']} blocked"
    )
    if result["issues"]:
        print("issues:")
        for issue in result["issues"]:
            print(f"  - item {issue['index']}: {issue['code']} - {issue['message']}")
            blockers = issue.get("blockers")
            if isinstance(blockers, list):
                for blocker in blockers:
                    print(f"    blocker: {blocker}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", nargs="?", type=Path, help="Completion audit manifest JSON")
    parser.add_argument("--template", action="store_true", help="Print a starter manifest and exit")
    parser.add_argument("--objective", default="Define the product objective here", help="Objective for --template")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text")
    parser.add_argument("--allow-incomplete", action="store_true", help="Exit 0 even when the audit is incomplete")
    args = parser.parse_args(argv)

    if args.template:
        template = build_template(args.objective)
        json.dump(template, sys.stdout, ensure_ascii=True, indent=2)
        print()
        return 0

    if args.manifest is None:
        raise SystemExit("manifest is required unless --template is used")

    result = audit_manifest(_load_json(args.manifest))
    if args.json:
        json.dump(result, sys.stdout, ensure_ascii=True, indent=2)
        print()
    else:
        _print_text(result)

    if result["status"] != "complete" and not args.allow_incomplete:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
