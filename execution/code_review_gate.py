"""Risk-aware gate that wraps `code_review_graph` for pre-commit / CI use.

The repo already builds and incrementally updates a code-review knowledge
graph (~11.5k nodes, ~85k edges). Most sessions only call `detect-changes`
manually. This script promotes the graph from an ad-hoc lookup into a
deterministic gate:

1. Run `detect_changes_func` against the configured diff base.
2. Optionally fetch `get_impact_radius` for added blast-radius context when
   the change is risky.
3. Optionally fetch `get_architecture_overview_func` when `--include-architecture`
   is passed (useful for monthly drift checks, not per-commit).
4. Classify the result against `--warn-threshold` and `--fail-threshold` and
   exit non-zero so it can be wired into hooks or CI.

Exit codes:
    0  pass   (risk < warn-threshold and no test gaps)
    1  warn   (advisory; promoted to fail only with `--strict`)
    2  fail   (risk >= fail-threshold)
    3  error  (graph not built, CLI not available, etc.)
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT_DEFAULT = Path(__file__).resolve().parents[1]


@dataclass
class GateReport:
    status: str  # "pass" | "warn" | "fail" | "error"
    risk_score: float
    warn_threshold: float
    fail_threshold: float
    changed_files: list[str]
    affected_flows: list[str]
    test_gaps: list[str]
    review_priorities: list[str]
    reasons: list[str] = field(default_factory=list)
    impact_radius: dict[str, Any] | None = None
    architecture_overview: dict[str, Any] | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _load_graph_tools():
    """Import the graph helpers lazily so a missing install reports cleanly."""
    try:
        from code_review_graph.tools import (
            detect_changes_func,
            get_architecture_overview_func,
            get_impact_radius,
        )
    except ImportError as exc:
        raise RuntimeError(
            "code_review_graph is not importable from this Python interpreter. "
            "Install it (e.g. `pip install code-review-graph`) or run with the "
            "Python that has it on path (commonly `py -3.13`)."
        ) from exc
    return detect_changes_func, get_impact_radius, get_architecture_overview_func


def _summarize_priorities(priorities: list[Any]) -> list[str]:
    """Render a stable list of human-readable priority strings."""
    out: list[str] = []
    for item in priorities or []:
        if isinstance(item, str):
            out.append(item)
        elif isinstance(item, dict):
            label = item.get("title") or item.get("name") or item.get("file") or ""
            reason = item.get("reason") or item.get("why") or ""
            score = item.get("score") or item.get("priority")
            parts = [str(label)]
            if reason:
                parts.append(f"— {reason}")
            if score is not None:
                parts.append(f"(score={score})")
            out.append(" ".join(parts).strip(" —"))
    return out


def _summarize_test_gaps(gaps: list[Any]) -> list[str]:
    """Render test-gap entries as `name :: file` strings (best-effort)."""
    out: list[str] = []
    for entry in gaps or []:
        if isinstance(entry, str):
            out.append(entry)
        elif isinstance(entry, dict):
            name = entry.get("name") or entry.get("symbol") or "?"
            file = entry.get("file") or entry.get("path") or ""
            out.append(f"{name} :: {file}".rstrip(" :"))
    return out


def get_staged_files(repo_root: Path) -> list[str]:
    """Return staged file paths (Added/Copied/Modified/Renamed) for pre-commit use."""
    import subprocess

    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(repo_root),
            check=False,
        )
    except (OSError, FileNotFoundError):
        return []
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def evaluate(
    *,
    base: str,
    repo_root: Path,
    warn_threshold: float,
    fail_threshold: float,
    include_architecture: bool,
    detail_level: str = "standard",
    changed_files: list[str] | None = None,
    tools: tuple | None = None,
) -> GateReport:
    """Run the underlying graph queries and classify the result.

    `tools` is exposed so unit tests can inject mocks without monkey-patching
    the import path. `changed_files`, when provided, overrides `base` and asks
    `detect_changes_func` to analyze that explicit list (e.g. for staged
    pre-commit use).
    """
    if warn_threshold > fail_threshold:
        raise ValueError("warn-threshold must be <= fail-threshold")

    if tools is None:
        try:
            tools = _load_graph_tools()
        except RuntimeError as exc:
            return GateReport(
                status="error",
                risk_score=0.0,
                warn_threshold=warn_threshold,
                fail_threshold=fail_threshold,
                changed_files=[],
                affected_flows=[],
                test_gaps=[],
                review_priorities=[],
                error=str(exc),
            )

    detect_changes_func, get_impact_radius, get_architecture_overview_func = tools

    detect_kwargs: dict[str, Any] = {
        "repo_root": str(repo_root),
        "detail_level": detail_level,
    }
    if changed_files is not None:
        detect_kwargs["changed_files"] = changed_files
    else:
        detect_kwargs["base"] = base

    try:
        change_result = detect_changes_func(**detect_kwargs)
    except Exception as exc:  # graph backend may raise FileNotFoundError, sqlite, etc.
        return GateReport(
            status="error",
            risk_score=0.0,
            warn_threshold=warn_threshold,
            fail_threshold=fail_threshold,
            changed_files=[],
            affected_flows=[],
            test_gaps=[],
            review_priorities=[],
            error=f"detect_changes failed: {exc}",
        )

    risk_score = float(change_result.get("risk_score", 0.0) or 0.0)
    affected_flows = [
        flow.get("name") if isinstance(flow, dict) else str(flow)
        for flow in change_result.get("affected_flows", []) or []
    ]
    test_gaps = _summarize_test_gaps(change_result.get("test_gaps", []) or [])
    review_priorities = _summarize_priorities(change_result.get("review_priorities", []) or [])
    changed_files_raw = change_result.get("changed_files", []) or []
    changed_files = [f.get("path") if isinstance(f, dict) else str(f) for f in changed_files_raw]

    reasons: list[str] = []
    if risk_score >= fail_threshold:
        status = "fail"
        reasons.append(f"risk_score {risk_score:.2f} >= fail-threshold {fail_threshold:.2f}")
    elif risk_score >= warn_threshold:
        status = "warn"
        reasons.append(f"risk_score {risk_score:.2f} >= warn-threshold {warn_threshold:.2f}")
    else:
        status = "pass"

    if test_gaps:
        if status == "pass":
            status = "warn"
        reasons.append(f"{len(test_gaps)} test gap(s) detected")

    impact_radius: dict[str, Any] | None = None
    if status in {"warn", "fail"} and changed_files:
        try:
            impact_radius = get_impact_radius(
                changed_files=[c for c in changed_files if c],
                repo_root=str(repo_root),
                base=base,
            )
        except Exception as exc:  # advisory; never escalates the status
            impact_radius = {"error": f"impact_radius failed: {exc}"}

    architecture_overview: dict[str, Any] | None = None
    if include_architecture:
        try:
            architecture_overview = get_architecture_overview_func(repo_root=str(repo_root))
        except Exception as exc:
            architecture_overview = {"error": f"architecture_overview failed: {exc}"}

    return GateReport(
        status=status,
        risk_score=risk_score,
        warn_threshold=warn_threshold,
        fail_threshold=fail_threshold,
        changed_files=[c for c in changed_files if c],
        affected_flows=[f for f in affected_flows if f],
        test_gaps=test_gaps,
        review_priorities=review_priorities,
        reasons=reasons,
        impact_radius=impact_radius,
        architecture_overview=architecture_overview,
    )


def status_to_exit_code(status: str, *, strict: bool) -> int:
    if status == "pass":
        return 0
    if status == "warn":
        return 1 if strict else 0
    if status == "fail":
        return 2
    return 3  # error


def render_text(report: GateReport) -> str:
    if report.status == "error":
        return f"[code-review-gate] error: {report.error}"
    lines = [
        f"[code-review-gate] {report.status.upper()} "
        f"(risk={report.risk_score:.2f}, "
        f"warn>={report.warn_threshold:.2f}, fail>={report.fail_threshold:.2f})"
    ]
    if report.reasons:
        lines.append("  reasons:")
        for reason in report.reasons:
            lines.append(f"    - {reason}")
    if report.changed_files:
        head = report.changed_files[:5]
        suffix = f" (+ {len(report.changed_files) - len(head)} more)" if len(report.changed_files) > len(head) else ""
        lines.append(f"  changed: {', '.join(head)}{suffix}")
    if report.test_gaps:
        lines.append(f"  test gaps: {len(report.test_gaps)}")
        for gap in report.test_gaps[:5]:
            lines.append(f"    - {gap}")
    if report.review_priorities:
        lines.append(f"  review priorities: {len(report.review_priorities)}")
        for p in report.review_priorities[:3]:
            lines.append(f"    - {p}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=("Risk-aware code review gate built on the code_review_graph knowledge graph."),
    )
    parser.add_argument("--base", default="HEAD~1", help="Git diff base (default: HEAD~1)")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=REPO_ROOT_DEFAULT,
        help="Repository root for the graph queries.",
    )
    parser.add_argument(
        "--warn-threshold",
        type=float,
        default=0.3,
        help="Risk score that triggers a warn (advisory). Default: 0.3",
    )
    parser.add_argument(
        "--fail-threshold",
        type=float,
        default=0.7,
        help="Risk score that triggers a fail. Default: 0.7",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Promote warn to a non-zero exit code (useful in CI).",
    )
    parser.add_argument(
        "--include-architecture",
        action="store_true",
        help="Also include get_architecture_overview output (heavier).",
    )
    parser.add_argument(
        "--detail-level",
        default="standard",
        choices=["brief", "standard", "verbose"],
        help="detect_changes detail level. Default: standard",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the report as JSON (suppresses the text summary).",
    )
    parser.add_argument(
        "--staged",
        action="store_true",
        help=(
            "Use staged changes (`git diff --cached --name-only`) instead of `--base`. Intended for pre-commit hooks."
        ),
    )
    args = parser.parse_args(argv)

    changed_files: list[str] | None = None
    if args.staged:
        changed_files = get_staged_files(args.repo_root)
        if not changed_files:
            # Nothing staged -> trivial pass without invoking the graph.
            trivial = GateReport(
                status="pass",
                risk_score=0.0,
                warn_threshold=args.warn_threshold,
                fail_threshold=args.fail_threshold,
                changed_files=[],
                affected_flows=[],
                test_gaps=[],
                review_priorities=[],
            )
            if args.json:
                print(json.dumps(trivial.to_dict(), ensure_ascii=False))
            else:
                print("[code-review-gate] PASS (no staged files)")
            return 0

    report = evaluate(
        base=args.base,
        repo_root=args.repo_root,
        warn_threshold=args.warn_threshold,
        fail_threshold=args.fail_threshold,
        include_architecture=args.include_architecture,
        detail_level=args.detail_level,
        changed_files=changed_files,
    )

    if args.json:
        print(json.dumps(report.to_dict(), ensure_ascii=False))
    else:
        print(render_text(report))

    return status_to_exit_code(report.status, strict=args.strict)


if __name__ == "__main__":
    sys.exit(main())
