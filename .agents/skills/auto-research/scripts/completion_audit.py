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


class _WriteFailure(Exception):
    def __init__(self, path: Path, cause: OSError) -> None:
        super().__init__(f"{type(cause).__name__}: {cause}")
        self.path = path
        self.cause = cause


def _read_manifest_text(path: Path) -> str:
    try:
        raw = path.read_bytes()
    except FileNotFoundError as exc:
        raise SystemExit(f"manifest not found: {path}") from exc
    except OSError as exc:
        raise SystemExit(f"manifest unreadable: {path}: {exc}") from exc

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


def _audit_item(
    index: int,
    raw_item: Any,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]], bool, bool]:
    if not isinstance(raw_item, dict):
        return None, [_item_issue(index, "invalid_item", "Checklist item must be an object.")], False, False

    requirement = raw_item.get("requirement")
    requirement_text = requirement.strip() if isinstance(requirement, str) else ""
    artifacts = _string_list(raw_item.get("artifacts"))
    evidence = _string_list(raw_item.get("evidence"))
    blockers = _string_list(raw_item.get("blockers"))
    verified = raw_item.get("verified") is True
    coverage = str(raw_item.get("coverage", "")).strip().lower()
    item_issues: list[str] = []
    issues: list[dict[str, Any]] = []

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
    return (
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
        },
        issues,
        passed,
        bool(blockers),
    )


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
        normalized_item, item_issues, passed, blocked = _audit_item(index, raw_item)
        issues.extend(item_issues)
        if blocked:
            blocked_count += 1
        if passed:
            complete_count += 1
        if normalized_item is not None:
            normalized_items.append(normalized_item)

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


def _format_text(result: dict[str, Any]) -> str:
    lines = [
        f"status: {result['status']}",
        f"objective: {result['objective']}",
    ]
    summary = result["summary"]
    lines.append(
        "summary: "
        f"{summary['complete_count']}/{summary['item_count']} complete, "
        f"{summary['issue_count']} issue(s), {summary['blocked_count']} blocked"
    )
    if result["issues"]:
        lines.append("issues:")
        for issue in result["issues"]:
            lines.append(f"  - item {issue['index']}: {issue['code']} - {issue['message']}")
            blockers = issue.get("blockers")
            if isinstance(blockers, list):
                for blocker in blockers:
                    lines.append(f"    blocker: {blocker}")
    return "\n".join(lines) + "\n"


def _write_output(path: Path, text: str) -> None:
    tmp = path.with_name(f"{path.name}.refresh-tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(text, encoding="utf-8", newline="\n")
        tmp.replace(path)
    except OSError as exc:
        try:
            if tmp.is_file() or tmp.is_symlink():
                tmp.unlink()
        except OSError:
            pass
        raise _WriteFailure(path, exc) from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", nargs="?", type=Path, help="Completion audit manifest JSON")
    parser.add_argument("--template", action="store_true", help="Print a starter manifest and exit")
    parser.add_argument(
        "--template-output",
        type=Path,
        help="Write the starter manifest as UTF-8 without relying on shell redirection",
    )
    parser.add_argument("--objective", default="Define the product objective here", help="Objective for --template")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text")
    parser.add_argument(
        "--output", type=Path, help="Write the audit result as UTF-8 without relying on shell redirection"
    )
    parser.add_argument("--allow-incomplete", action="store_true", help="Exit 0 even when the audit is incomplete")
    args = parser.parse_args(argv)

    if args.template:
        template = build_template(args.objective)
        output_text = json.dumps(template, ensure_ascii=True, indent=2) + "\n"
        if args.template_output is not None:
            try:
                _write_output(args.template_output, output_text)
            except _WriteFailure as exc:
                sys.stdout.write(
                    json.dumps(
                        {
                            "status": "write_failed",
                            "write_error": str(exc),
                            "write_error_path": exc.path.as_posix(),
                        },
                        ensure_ascii=True,
                        indent=2,
                    )
                    + "\n"
                )
                return 4
        sys.stdout.write(output_text)
        return 0

    if args.manifest is None:
        raise SystemExit("manifest is required unless --template is used")

    result = audit_manifest(_load_json(args.manifest))
    if args.json:
        output_text = json.dumps(result, ensure_ascii=True, indent=2) + "\n"
    else:
        output_text = _format_text(result)

    if args.output is not None:
        try:
            _write_output(args.output, output_text)
        except _WriteFailure as exc:
            result["status"] = "write_failed"
            result["write_error"] = str(exc)
            result["write_error_path"] = exc.path.as_posix()
            if args.json:
                sys.stdout.write(json.dumps(result, ensure_ascii=True, indent=2) + "\n")
            else:
                sys.stdout.write(_format_text(result))
                sys.stdout.write(f"write_error_path: {exc.path.as_posix()}\n")
                sys.stdout.write(f"write_error: {exc}\n")
            return 4
    sys.stdout.write(output_text)

    if result["status"] != "complete" and not args.allow_incomplete:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
