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
import ast
import json
import os
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT_DEFAULT = Path(__file__).resolve().parents[1]
GRAPH_RELEVANT_SUFFIXES = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".mjs",
    ".cjs",
    ".go",
    ".rs",
    ".svelte",
    ".vue",
    ".sh",
    ".bash",
    ".ps1",
    ".bat",
    ".cmd",
    ".json",
    ".toml",
    ".yaml",
    ".yml",
}
GRAPH_RELEVANT_FILENAMES = {
    "Dockerfile",
    "Makefile",
    "commit-msg",
    "pre-commit",
}
DYNAMIC_MODULE_LOADER_NAMES = {"_load_gate", "_load_module"}


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
    untracked_files: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    impact_radius: dict[str, Any] | None = None
    architecture_overview: dict[str, Any] | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class _ChangeAnalysis:
    risk_score: float
    changed_files: list[str]
    affected_flows: list[str]
    test_gaps: list[str]
    review_priorities: list[str]


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


def _looks_like_test_path(path: str) -> bool:
    """Return True for paths that should not be treated as production gaps."""
    normalized = path.replace("\\", "/").lower()
    name = normalized.rsplit("/", 1)[-1]
    return "/tests/" in normalized or name.startswith("test_") or name.endswith("_test.py")


def _looks_like_test_node(name: str, path: str) -> bool:
    """Return True for graph nodes that represent tests even when `is_test` is missing."""
    return _looks_like_test_path(path) or name.startswith("Test") or name.startswith("test_")


def _load_tested_sources(repo_root: Path) -> set[str]:
    """Load production nodes that have TESTED_BY edges in the graph.

    code_review_graph currently stores TESTED_BY as:
      source_qualified = production node
      target_qualified = test node

    Its upstream change analyzer checks the inverse direction, so this gate
    performs a narrow post-processing correction instead of hiding all gaps.
    """
    graph_db = repo_root / ".code-review-graph" / "graph.db"
    if not graph_db.exists():
        return set()

    import sqlite3

    try:
        with sqlite3.connect(graph_db) as conn:
            rows = conn.execute("SELECT DISTINCT source_qualified FROM edges WHERE kind = 'TESTED_BY'").fetchall()
    except (OSError, sqlite3.Error):
        return set()
    return {str(row[0]) for row in rows if row and row[0]}


def _changed_python_test_paths(repo_root: Path, changed_files: list[str]) -> list[Path]:
    paths: list[Path] = []
    for file_name in changed_files:
        if not _looks_like_test_path(file_name):
            continue
        path = repo_root / file_name
        if not path.exists() or path.suffix != ".py":
            continue
        paths.append(path)
    return paths


def _parse_python_source(path: Path) -> ast.AST | None:
    try:
        return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, SyntaxError, UnicodeDecodeError):
        return None


def _dynamic_module_aliases(tree: ast.AST) -> set[str]:
    aliases: set[str] = set()
    for node in ast.walk(tree):
        if not (
            isinstance(node, ast.Assign)
            and isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Name)
            and node.value.func.id in DYNAMIC_MODULE_LOADER_NAMES
        ):
            continue
        aliases.update(target.id for target in node.targets if isinstance(target, ast.Name))
    return aliases


def _attribute_mentions(tree: ast.AST, dynamic_module_aliases: set[str]) -> set[str]:
    return {
        node.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and (node.attr.startswith("_") or node.value.id in dynamic_module_aliases)
    }


def _private_import_mentions(tree: ast.AST) -> set[str]:
    mentions: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            mentions.update(alias.name for alias in node.names if alias.name.startswith("_"))
    return mentions


def _test_mentions_from_tree(tree: ast.AST) -> set[str]:
    dynamic_module_aliases = _dynamic_module_aliases(tree)
    return _attribute_mentions(tree, dynamic_module_aliases) | _private_import_mentions(tree)


def _load_changed_test_mentions(repo_root: Path, changed_files: list[str]) -> set[str]:
    """Load helper names referenced through module attributes in changed tests.

    This is a narrow fallback for dynamic scripts that the graph can parse but
    cannot always connect to tests through static TESTED_BY edges.
    """
    mentions: set[str] = set()
    for path in _changed_python_test_paths(repo_root, changed_files):
        tree = _parse_python_source(path)
        if tree is not None:
            mentions.update(_test_mentions_from_tree(tree))
    return mentions


def _allows_unqualified_test_source(path: str) -> bool:
    """Allow name-only coverage only for dynamic script/page trees with weak import paths."""
    normalized = path.replace("\\", "/")
    parts = normalized.split("/")[:-1]
    return (
        ".agents" in parts
        or "/workspace/execution/pages/" in normalized
        or normalized.endswith("/execution/code_review_gate.py")
    )


def _tested_source_keys(name: str, path: str, qname: str) -> set[str]:
    """Return source keys that can represent a covered function in graph edges."""
    keys = {qname} if qname else set()
    if not name or not path:
        return keys

    normalized_path = path.replace("\\", "/")
    stem = Path(normalized_path).stem
    filename = Path(normalized_path).name
    keys.update(
        {
            f"{normalized_path}::{name}",
            f"{filename}::{name}",
            f"{stem}::{name}",
            f"{stem}.{name}",
        }
    )
    if _allows_unqualified_test_source(path):
        keys.add(name)
    return keys


def _has_tested_source(name: str, path: str, qname: str, tested_sources: set[str]) -> bool:
    """Return True when a gap has a matching outgoing TESTED_BY source."""
    return bool(_tested_source_keys(name, path, qname) & tested_sources)


def _filter_test_gaps(raw_gaps: list[Any], *, tested_sources: set[str]) -> list[Any]:
    """Drop false-positive gaps caused by graph test-node and edge-direction drift."""
    filtered: list[Any] = []
    for entry in raw_gaps or []:
        if not isinstance(entry, dict):
            filtered.append(entry)
            continue

        name = str(entry.get("name") or entry.get("symbol") or "")
        path = str(entry.get("file") or entry.get("path") or "")
        qname = str(entry.get("qualified_name") or "")
        if _looks_like_test_node(name, path):
            continue
        if _has_tested_source(name, path, qname, tested_sources):
            continue
        filtered.append(entry)
    return filtered


def _correct_risk_score(
    change_result: dict[str, Any],
    *,
    raw_gap_qnames: set[str],
    tested_sources: set[str],
    filtered_gap_count: int | None = None,
) -> float:
    """Correct coverage-related risk inflation from the TESTED_BY direction bug."""
    changed_functions = change_result.get("changed_functions") or []
    if not changed_functions:
        if raw_gap_qnames and filtered_gap_count == 0 and not (change_result.get("affected_flows") or []):
            return 0.0
        return float(change_result.get("risk_score", 0.0) or 0.0)

    risks: list[float] = []
    coverage_drift_only = (
        bool(raw_gap_qnames) and filtered_gap_count == 0 and not (change_result.get("affected_flows") or [])
    )
    for item in changed_functions:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "")
        path = str(item.get("file_path") or item.get("file") or item.get("path") or "")
        if _looks_like_test_node(name, path):
            continue

        qname = str(item.get("qualified_name") or "")
        risk = float(item.get("risk_score", 0.0) or 0.0)
        has_tested_source = _has_tested_source(name, path, qname, tested_sources)
        if qname in raw_gap_qnames and has_tested_source:
            # Upstream charged 0.30 for "untested"; intended tested charge is 0.05.
            risk = max(0.0, risk - 0.25)
            if coverage_drift_only:
                risk = min(risk, 0.05)
        elif coverage_drift_only and has_tested_source:
            risk = min(risk, 0.05)
        risks.append(risk)

    if not risks:
        return 0.0
    return round(max(risks), 4)


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


def get_untracked_files(repo_root: Path) -> list[str]:
    """Return untracked, non-ignored file paths relative to the repo root."""
    import subprocess

    try:
        result = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"],
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


def is_graph_relevant_file(path: str) -> bool:
    """Return True when a staged path is useful input for the code graph gate."""
    normalized = path.replace("\\", "/")
    name = Path(normalized).name
    if name in GRAPH_RELEVANT_FILENAMES:
        return True
    return Path(normalized).suffix.lower() in GRAPH_RELEVANT_SUFFIXES


def filter_graph_relevant_files(paths: list[str]) -> list[str]:
    """Keep code/config files and skip docs-only changes that make graph output noisy."""
    return [path for path in paths if is_graph_relevant_file(path)]


def _gate_error_report(*, error: str, warn_threshold: float, fail_threshold: float) -> GateReport:
    return GateReport(
        status="error",
        risk_score=0.0,
        warn_threshold=warn_threshold,
        fail_threshold=fail_threshold,
        changed_files=[],
        affected_flows=[],
        test_gaps=[],
        review_priorities=[],
        error=error,
    )


def _detect_kwargs(
    *,
    base: str,
    repo_root: Path,
    detail_level: str,
    changed_files: list[str] | None,
) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "repo_root": str(repo_root),
        "detail_level": detail_level,
    }
    if changed_files is not None:
        kwargs["changed_files"] = changed_files
    else:
        kwargs["base"] = base
    return kwargs


def _change_analysis(change_result: dict[str, Any], *, repo_root: Path) -> _ChangeAnalysis:
    changed_files_raw = change_result.get("changed_files", []) or []
    changed_files = [f.get("path") if isinstance(f, dict) else str(f) for f in changed_files_raw]

    raw_test_gaps = change_result.get("test_gaps", []) or []
    raw_gap_qnames = {
        str(gap.get("qualified_name")) for gap in raw_test_gaps if isinstance(gap, dict) and gap.get("qualified_name")
    }
    tested_sources = _load_tested_sources(repo_root) | _load_changed_test_mentions(
        repo_root,
        [f for f in changed_files if f],
    )
    filtered_test_gaps = _filter_test_gaps(raw_test_gaps, tested_sources=tested_sources)
    risk_score = _correct_risk_score(
        change_result,
        raw_gap_qnames=raw_gap_qnames,
        tested_sources=tested_sources,
        filtered_gap_count=len(filtered_test_gaps),
    )
    affected_flows = [
        flow.get("name") if isinstance(flow, dict) else str(flow)
        for flow in change_result.get("affected_flows", []) or []
    ]
    return _ChangeAnalysis(
        risk_score=risk_score,
        changed_files=[f for f in changed_files if f],
        affected_flows=[f for f in affected_flows if f],
        test_gaps=_summarize_test_gaps(filtered_test_gaps),
        review_priorities=_summarize_priorities(change_result.get("review_priorities", []) or []),
    )


def _gate_status(
    *,
    risk_score: float,
    warn_threshold: float,
    fail_threshold: float,
    test_gaps: list[str],
    untracked_graph_files: list[str],
) -> tuple[str, list[str]]:
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

    if untracked_graph_files:
        if status == "pass":
            status = "warn"
        reasons.append(f"{len(untracked_graph_files)} untracked graph-relevant file(s) require direct review coverage")

    return status, reasons


def _impact_radius_for_status(
    *,
    status: str,
    changed_files: list[str],
    get_impact_radius_func: Any,
    repo_root: Path,
    base: str,
) -> dict[str, Any] | None:
    if status not in {"warn", "fail"} or not changed_files:
        return None
    try:
        return get_impact_radius_func(
            changed_files=changed_files,
            repo_root=str(repo_root),
            base=base,
        )
    except Exception as exc:  # advisory; never escalates the status
        return {"error": f"impact_radius failed: {exc}"}


def _architecture_overview_for_request(
    *,
    include_architecture: bool,
    get_architecture_overview_func: Any,
    repo_root: Path,
) -> dict[str, Any] | None:
    if not include_architecture:
        return None
    try:
        return get_architecture_overview_func(repo_root=str(repo_root))
    except Exception as exc:
        return {"error": f"architecture_overview failed: {exc}"}


def evaluate(
    *,
    base: str,
    repo_root: Path,
    warn_threshold: float,
    fail_threshold: float,
    include_architecture: bool,
    detail_level: str = "standard",
    changed_files: list[str] | None = None,
    untracked_files: list[str] | None = None,
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
            return _gate_error_report(error=str(exc), warn_threshold=warn_threshold, fail_threshold=fail_threshold)

    detect_changes_func, get_impact_radius, get_architecture_overview_func = tools
    detect_kwargs = _detect_kwargs(
        base=base,
        repo_root=repo_root,
        detail_level=detail_level,
        changed_files=changed_files,
    )

    try:
        change_result = detect_changes_func(**detect_kwargs)
    except Exception as exc:  # graph backend may raise FileNotFoundError, sqlite, etc.
        return _gate_error_report(
            error=f"detect_changes failed: {exc}",
            warn_threshold=warn_threshold,
            fail_threshold=fail_threshold,
        )

    analysis = _change_analysis(change_result, repo_root=repo_root)
    untracked_graph_files = filter_graph_relevant_files(untracked_files or [])
    status, reasons = _gate_status(
        risk_score=analysis.risk_score,
        warn_threshold=warn_threshold,
        fail_threshold=fail_threshold,
        test_gaps=analysis.test_gaps,
        untracked_graph_files=untracked_graph_files,
    )

    return GateReport(
        status=status,
        risk_score=analysis.risk_score,
        warn_threshold=warn_threshold,
        fail_threshold=fail_threshold,
        changed_files=analysis.changed_files,
        affected_flows=analysis.affected_flows,
        test_gaps=analysis.test_gaps,
        review_priorities=analysis.review_priorities,
        untracked_files=untracked_graph_files,
        reasons=reasons,
        impact_radius=_impact_radius_for_status(
            status=status,
            changed_files=analysis.changed_files,
            get_impact_radius_func=get_impact_radius,
            repo_root=repo_root,
            base=base,
        ),
        architecture_overview=_architecture_overview_for_request(
            include_architecture=include_architecture,
            get_architecture_overview_func=get_architecture_overview_func,
            repo_root=repo_root,
        ),
    )


def status_to_exit_code(status: str, *, strict: bool) -> int:
    if status == "pass":
        return 0
    if status == "warn":
        return 1 if strict else 0
    if status == "fail":
        return 2
    return 3  # error


def _trivial_pass_report(
    *,
    warn_threshold: float,
    fail_threshold: float,
    reasons: list[str] | None = None,
) -> GateReport:
    return GateReport(
        status="pass",
        risk_score=0.0,
        warn_threshold=warn_threshold,
        fail_threshold=fail_threshold,
        changed_files=[],
        affected_flows=[],
        test_gaps=[],
        review_priorities=[],
        reasons=reasons or [],
    )


def _print_report(report: GateReport, *, as_json: bool, text_override: str | None = None) -> None:
    if as_json:
        print(json.dumps(report.to_dict(), ensure_ascii=False))
    else:
        print(text_override or render_text(report))


def _should_retry_with_py313(report: GateReport) -> bool:
    """Return True when this Windows interpreter lacks the graph package."""
    if sys.platform != "win32":
        return False
    if os.environ.get("CODE_REVIEW_GATE_PY313_FALLBACK"):
        return False
    return report.status == "error" and "not importable" in str(report.error or "")


def _run_py313_fallback(argv: list[str]) -> int:
    """Re-run this CLI with Windows' Python 3.13 launcher and relay output."""
    env = os.environ.copy()
    env["CODE_REVIEW_GATE_PY313_FALLBACK"] = "1"
    env.setdefault("PYTHONUTF8", "1")
    try:
        completed = subprocess.run(
            ["py", "-3.13", str(Path(__file__).resolve()), *argv],
            cwd=str(REPO_ROOT_DEFAULT),
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except (OSError, FileNotFoundError) as exc:
        print(f"[code-review-gate] py -3.13 fallback failed: {exc}", file=sys.stderr)
        return 3
    if completed.stdout:
        sys.stdout.write(completed.stdout)
    if completed.stderr:
        sys.stderr.write(completed.stderr)
    return completed.returncode


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
    if report.untracked_files:
        head = report.untracked_files[:5]
        suffix = (
            f" (+ {len(report.untracked_files) - len(head)} more)" if len(report.untracked_files) > len(head) else ""
        )
        lines.append(f"  untracked: {', '.join(head)}{suffix}")
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
    raw_argv = list(sys.argv[1:] if argv is None else argv)
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
    args = parser.parse_args(raw_argv)

    changed_files: list[str] | None = None
    untracked_files: list[str] | None = None
    if args.staged:
        staged_files = get_staged_files(args.repo_root)
        changed_files = filter_graph_relevant_files(staged_files)
        if not staged_files:
            # Nothing staged -> trivial pass without invoking the graph.
            trivial = _trivial_pass_report(
                warn_threshold=args.warn_threshold,
                fail_threshold=args.fail_threshold,
            )
            _print_report(trivial, as_json=args.json, text_override="[code-review-gate] PASS (no staged files)")
            return 0
        if not changed_files:
            # Docs-only/context-only commits should not inherit stale graph gaps.
            trivial = _trivial_pass_report(
                warn_threshold=args.warn_threshold,
                fail_threshold=args.fail_threshold,
                reasons=[f"{len(staged_files)} staged file(s) ignored as non-code"],
            )
            _print_report(trivial, as_json=args.json, text_override="[code-review-gate] PASS (no staged code files)")
            return 0
    else:
        untracked_files = filter_graph_relevant_files(get_untracked_files(args.repo_root))

    report = evaluate(
        base=args.base,
        repo_root=args.repo_root,
        warn_threshold=args.warn_threshold,
        fail_threshold=args.fail_threshold,
        include_architecture=args.include_architecture,
        detail_level=args.detail_level,
        changed_files=changed_files,
        untracked_files=untracked_files,
    )

    if _should_retry_with_py313(report):
        return _run_py313_fallback(raw_argv)

    _print_report(report, as_json=args.json)

    return status_to_exit_code(report.status, strict=args.strict)


if __name__ == "__main__":
    sys.exit(main())
