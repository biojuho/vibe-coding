#!/usr/bin/env python3
"""Build a direction-alignment scorecard for one auto-research loop."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


DEFAULT_DIRECTION = (
    "Vibe coding should operate as a local-first AI product operations OS that turns vague improvement "
    "requests into externally benchmarked, evidence-backed experiments while preserving explicit release, "
    "dirty-worktree, and external-blocker boundaries."
)

DEFAULT_REFERENCES = (
    {
        "label": "OpenAI Codex",
        "url": "https://openai.com/codex/",
        "strength": "Agentic coding command center with parallel worktrees, cloud environments, background work, and review.",
    },
    {
        "label": "Claude Code",
        "url": "https://code.claude.com/docs/ko/overview",
        "strength": "Terminal and IDE coding assistant that reads codebases, edits files, runs commands, and integrates tools.",
    },
    {
        "label": "LangSmith",
        "url": "https://docs.langchain.com/langsmith/observability-concepts",
        "strength": "LLM observability through projects, traces, runs, threads, feedback, tags, and integrations.",
    },
)

CORE_ARTIFACTS = (
    ".ai/HANDOFF.md",
    ".ai/TASKS.md",
    ".ai/CONTEXT.md",
    ".ai/GOAL.md",
    "execution/session_orient.py",
    "execution/product_readiness_score.py",
    "execution/project_qc_runner.py",
)

LOOP_ARTIFACTS = (
    ".agents/skills/auto-research/SKILL.md",
    ".agents/skills/auto-research/scripts/ab_decision.py",
    ".agents/skills/auto-research/scripts/browser_qa_inventory.py",
    ".agents/skills/auto-research/scripts/completion_audit.py",
    ".agents/skills/auto-research/scripts/dirty_worktree_handoff_plan.py",
    ".agents/skills/auto-research/scripts/next_experiment_selector.py",
)

BOUNDARY_ARTIFACTS = (
    ".agents/skills/auto-research/scripts/release_authorization_packet.py",
    ".tmp/scoped-dirty-worktree-handoff-plan-current.json",
    ".tmp/next-experiment-continuation.json",
)


def _rel(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _read_text(root: Path, rel_path: str) -> str:
    try:
        return (root / rel_path).read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return ""


def _load_json(root: Path, rel_path: str) -> dict[str, Any]:
    try:
        parsed = json.loads((root / rel_path).read_text(encoding="utf-8-sig"))
    except (FileNotFoundError, OSError, json.JSONDecodeError, UnicodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _artifact_check(root: Path, rel_path: str) -> dict[str, Any]:
    path = root / rel_path
    return {
        "label": f"artifact exists: {rel_path}",
        "ok": path.exists(),
        "artifacts": [rel_path] if path.exists() else [],
        "evidence": f"{rel_path} exists={path.exists()}",
    }


def _term_check(label: str, text: str, terms: tuple[str, ...], *, minimum: int = 1) -> dict[str, Any]:
    found = [term for term in terms if term.lower() in text.lower()]
    return {
        "label": label,
        "ok": len(found) >= minimum,
        "artifacts": [],
        "evidence": f"found terms {len(found)}/{minimum}: {', '.join(found) if found else 'none'}",
    }


def _json_check(label: str, ok: bool, evidence: str, artifacts: list[str]) -> dict[str, Any]:
    return {
        "label": label,
        "ok": ok,
        "artifacts": artifacts if ok else [],
        "evidence": evidence,
    }


def _score_checks(checks: list[dict[str, Any]]) -> tuple[int, int, float]:
    passed = sum(1 for check in checks if check.get("ok") is True)
    total = len(checks)
    return passed, total, passed / total if total else 0.0


def _pillar(key: str, label: str, checks: list[dict[str, Any]]) -> dict[str, Any]:
    passed, total, score = _score_checks(checks)
    blockers = [f"{check['label']}: {check['evidence']}" for check in checks if check.get("ok") is not True]
    return {
        "key": key,
        "label": label,
        "score": round(score, 4),
        "passed": passed,
        "total": total,
        "checks": checks,
        "blockers": blockers,
    }


def _parse_reference(raw: str) -> dict[str, str]:
    parts = [part.strip() for part in raw.split("|")]
    if len(parts) == 1:
        return {"label": parts[0], "url": "", "strength": ""}
    if len(parts) == 2:
        return {"label": parts[0], "url": parts[1], "strength": ""}
    return {"label": parts[0], "url": parts[1], "strength": "|".join(parts[2:]).strip()}


def _comparison_for(reference: dict[str, str]) -> dict[str, str]:
    label = reference.get("label", "")
    lower = label.lower()
    if "codex" in lower:
        counter = (
            "Keep the multi-agent ambition, but add local dirty-worktree signatures, explicit approval gates, "
            "and completion audits before adoption."
        )
    elif "claude" in lower:
        counter = (
            "Keep terminal-native repo action, but make cross-tool handoff and deterministic evidence files "
            "first-class loop inputs."
        )
    elif "langsmith" in lower:
        counter = (
            "Keep trace/eval discipline, but bind release judgment to local repo state, selector output, "
            "and user-owned external blockers."
        )
    else:
        counter = "Use as a benchmark while preserving local evidence, approval boundaries, and repeatable gates."
    return {
        "reference": label,
        "url": reference.get("url", ""),
        "their_strength": reference.get("strength", ""),
        "vibe_counter_position": counter,
    }


def build_audit(
    root: Path,
    *,
    direction: str = DEFAULT_DIRECTION,
    references: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    refs = references or [dict(item) for item in DEFAULT_REFERENCES]
    combined_text = "\n".join(
        _read_text(root, path)
        for path in (
            ".ai/HANDOFF.md",
            ".ai/TASKS.md",
            ".ai/CONTEXT.md",
            ".ai/GOAL.md",
            ".agents/skills/auto-research/SKILL.md",
        )
    )
    dirty_plan = _load_json(root, ".tmp/scoped-dirty-worktree-handoff-plan-current.json")
    selector = _load_json(root, ".tmp/next-experiment-continuation.json")
    selector_selected = selector.get("selected") if isinstance(selector.get("selected"), dict) else {}
    selector_summary = selector.get("summary") if isinstance(selector.get("summary"), dict) else {}
    selector_guardrails = (
        selector_selected.get("guardrails") if isinstance(selector_selected.get("guardrails"), list) else []
    )
    dirty_decision = dirty_plan.get("decision") if isinstance(dirty_plan.get("decision"), dict) else {}
    dirty_freshness = dirty_plan.get("freshness") if isinstance(dirty_plan.get("freshness"), dict) else {}

    pillars = [
        _pillar(
            "local_first_operations",
            "Local-first product operations OS",
            [
                *[_artifact_check(root, path) for path in CORE_ARTIFACTS],
                _term_check(
                    "relay text mentions local/session/QC operations",
                    combined_text,
                    ("local", "session_orient.py", "project_qc_runner.py", "handoff", "readiness"),
                    minimum=3,
                ),
            ],
        ),
        _pillar(
            "evidence_backed_loop",
            "Externally benchmarked A/B loop with deterministic adoption",
            [
                *[_artifact_check(root, path) for path in LOOP_ARTIFACTS],
                _term_check(
                    "skill text names research, A/B, verification, and official sources",
                    combined_text,
                    ("A/B", "official docs", "current external research", "completion audit", "browser QA"),
                    minimum=3,
                ),
                _json_check(
                    "selector artifact is machine-readable",
                    bool(selector),
                    f"selector status={selector.get('status') or 'missing'}",
                    [".tmp/next-experiment-continuation.json"],
                ),
            ],
        ),
        _pillar(
            "approval_and_release_boundaries",
            "Explicit dirty, publish, and external-blocker boundaries",
            [
                *[_artifact_check(root, path) for path in BOUNDARY_ARTIFACTS],
                _json_check(
                    "dirty handoff is current and handoff-only",
                    dirty_plan.get("status") == "handoff_required"
                    and dirty_freshness.get("current") is True
                    and dirty_decision.get("stage_commit_push_authorized") is False,
                    "dirty handoff status="
                    f"{dirty_plan.get('status') or 'missing'}, freshness={dirty_freshness.get('status')}, "
                    f"stage_commit_push_authorized={dirty_decision.get('stage_commit_push_authorized')}",
                    [".tmp/scoped-dirty-worktree-handoff-plan-current.json"],
                ),
                _json_check(
                    "selector keeps push/T-251 guardrails explicit",
                    any("push" in str(item).lower() for item in selector_guardrails)
                    and any("t-251" in str(item).lower() for item in selector_guardrails),
                    "selector guardrails=" + (" | ".join(str(item) for item in selector_guardrails) or "missing"),
                    [".tmp/next-experiment-continuation.json"],
                ),
                _term_check(
                    "relay text keeps T-251 user-owned",
                    combined_text,
                    ("T-251", "Supabase", "credential reset", "do not retry"),
                    minimum=2,
                ),
            ],
        ),
        _pillar(
            "external_reference_advantage",
            "External reference comparison is part of the loop",
            [
                _json_check(
                    "at least two external references are attached",
                    len(refs) >= 2,
                    f"reference_count={len(refs)}",
                    [],
                ),
                _term_check(
                    "direction states external benchmarking and evidence",
                    direction,
                    ("external", "benchmark", "evidence", "local-first"),
                    minimum=3,
                ),
            ],
        ),
    ]

    passed = sum(int(pillar["passed"]) for pillar in pillars)
    total = sum(int(pillar["total"]) for pillar in pillars)
    overall_score = passed / total if total else 0.0
    critical_blockers: list[str] = []
    selector_status = str(selector.get("status") or "unknown")
    selector_kind = str(selector_selected.get("kind") or selector_summary.get("selected_kind") or "unknown")
    if selector_status == "blocked" and selector_kind == "dirty_worktree_handoff_current":
        critical_blockers.append(
            "Current dirty handoff requires explicit scoped staging/commit authorization before adopting product changes."
        )
    if "t-251" in combined_text.lower():
        critical_blockers.append("T-251 remains user-owned external evidence; do not retry live Prisma without reset.")

    if overall_score >= 0.8 and critical_blockers:
        status = "aligned_blocked"
    elif overall_score >= 0.8:
        status = "aligned"
    elif overall_score >= 0.5:
        status = "partial"
    else:
        status = "weak"

    return {
        "objective": "direction_alignment_audit",
        "generated_at": datetime.now(UTC).isoformat(),
        "root": str(root),
        "direction": direction,
        "status": status,
        "summary": {
            "overall_score": round(overall_score, 4),
            "passed": passed,
            "total": total,
            "reference_count": len(refs),
            "selector_status": selector_status,
            "selector_kind": selector_kind,
        },
        "pillars": pillars,
        "external_references": refs,
        "external_comparison": [_comparison_for(reference) for reference in refs],
        "critical_blockers": critical_blockers,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."), help="Workspace root")
    parser.add_argument("--direction", default=DEFAULT_DIRECTION, help="Direction hypothesis text")
    parser.add_argument(
        "--reference",
        action="append",
        help="External reference as label|url|strength. May be repeated.",
    )
    parser.add_argument("--output", type=Path, help="Write audit JSON to this path")
    parser.add_argument("--json", action="store_true", help="Print JSON to stdout")
    args = parser.parse_args(argv)

    references = [_parse_reference(item) for item in args.reference] if args.reference else None
    audit = build_audit(args.root, direction=args.direction, references=references)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(audit, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    if args.json or not args.output:
        json.dump(audit, sys.stdout, ensure_ascii=True, indent=2)
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
