#!/usr/bin/env python3
"""
VibeDebt Auditor - Technical debt quantification for vibe-coded projects.

Scans the codebase for 6 debt dimensions, computes per-file debt scores (0-100),
calculates project-level TDR (Technical Debt Ratio), and persists history for
trend analysis.

Usage:
    python vibe_debt_auditor.py                     # Full scan
    python vibe_debt_auditor.py --project blind-to-x  # Single project
    python vibe_debt_auditor.py --format json        # JSON output
    python vibe_debt_auditor.py --top 20             # Top N debtors
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

WORKSPACE_DIR = Path(__file__).resolve().parents[1]
if str(WORKSPACE_DIR) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_DIR))

from path_contract import REPO_ROOT, TMP_ROOT, resolve_project_dir

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEBT_MARKER_PATTERNS = [
    re.compile(r"#\s*(TODO|FIXME|HACK|XXX|WORKAROUND|TEMP|KLUDGE)\b", re.IGNORECASE),
]

SKIP_DIRS = {
    "node_modules",
    "__pycache__",
    ".git",
    "venv",
    ".venv",
    "dist",
    "build",
    ".next",
    ".tmp",
    "vendor",
    "target",
    ".agents",
    ".claude",
    ".codex",
    ".ai",
    "archive",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
}

SUPPORTED_EXTENSIONS = {".py"}

# Dimension weights (must sum to 1.0)
WEIGHTS = {
    "complexity": 0.25,
    "duplication": 0.20,
    "test_gap": 0.20,
    "debt_markers": 0.15,
    "modularity": 0.10,
    "doc_sync": 0.10,
}

# Thresholds
FUNCTION_LENGTH_WARN = 50
FUNCTION_LENGTH_CRITICAL = 150
COMPLEXITY_WARN = 10
COMPLEXITY_CRITICAL = 20
FILE_SIZE_WARN = 500
FILE_SIZE_CRITICAL = 1000
IMPORT_DEPTH_WARN = 15
IMPORT_DEPTH_CRITICAL = 30

# Cost model: estimated minutes to fix per debt point
MINUTES_PER_DEBT_POINT = 2.0
# Interest: estimated extra maintenance minutes per month per debt point
INTEREST_PER_DEBT_POINT_MONTHLY = 0.5

# TDR thresholds
TDR_GREEN = 5.0
TDR_YELLOW = 10.0


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class FunctionInfo:
    name: str
    lineno: int
    length: int
    complexity: int


@dataclass
class FileDebtScore:
    path: str
    relative_path: str
    project: str
    total_lines: int
    code_lines: int
    # Raw metrics
    function_count: int = 0
    max_complexity: int = 0
    avg_complexity: float = 0.0
    max_function_length: int = 0
    avg_function_length: float = 0.0
    debt_marker_count: int = 0
    import_count: int = 0
    duplicate_block_count: int = 0
    # Dimension scores (0-100 each)
    complexity_score: float = 0.0
    duplication_score: float = 0.0
    test_gap_score: float = 0.0
    debt_markers_score: float = 0.0
    modularity_score: float = 0.0
    doc_sync_score: float = 0.0
    # Final weighted score
    total_score: float = 0.0
    # Cost estimates
    principal_minutes: float = 0.0
    interest_monthly_minutes: float = 0.0
    # Top issues
    top_functions: List[Dict] = field(default_factory=list)
    debt_markers: List[Dict] = field(default_factory=list)


@dataclass
class ProjectDebtSummary:
    name: str
    file_count: int = 0
    total_lines: int = 0
    total_code_lines: int = 0
    avg_score: float = 0.0
    max_score: float = 0.0
    tdr_percent: float = 0.0
    tdr_grade: str = "GREEN"
    total_principal_minutes: float = 0.0
    total_interest_monthly: float = 0.0
    top_debtors: List[Dict] = field(default_factory=list)
    dimension_averages: Dict[str, float] = field(default_factory=dict)


@dataclass
class AuditResult:
    timestamp: str
    scan_duration_seconds: float
    projects: List[ProjectDebtSummary] = field(default_factory=list)
    overall_tdr: float = 0.0
    overall_grade: str = "GREEN"
    total_files: int = 0
    total_principal_hours: float = 0.0
    total_interest_monthly_hours: float = 0.0
    file_scores: List[FileDebtScore] = field(default_factory=list)


# ---------------------------------------------------------------------------
# AST analysis helpers
# ---------------------------------------------------------------------------


def _cyclomatic_complexity(node: ast.AST) -> int:
    """Count decision points in a function/method AST node."""
    count = 1
    for child in ast.walk(node):
        if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
            count += 1
        elif isinstance(child, ast.BoolOp):
            count += len(child.values) - 1
        elif isinstance(child, ast.Assert):
            count += 1
        elif isinstance(child, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
            count += sum(1 for _ in child.generators)
    return count


def _function_length(node: ast.AST) -> int:
    """Calculate the line span of a function body."""
    if not hasattr(node, "body") or not node.body:
        return 0
    first_line = node.body[0].lineno
    last_line = node.body[-1].end_lineno or node.body[-1].lineno
    return last_line - first_line + 1


def analyze_python_file(filepath: Path) -> Tuple[List[FunctionInfo], int, int, int]:
    """Parse a Python file and extract function metrics.

    Returns: (functions, total_lines, code_lines, import_count)
    """
    try:
        source = filepath.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return [], 0, 0, 0

    lines = source.splitlines()
    total_lines = len(lines)
    code_lines = sum(1 for line in lines if line.strip() and not line.strip().startswith("#"))

    try:
        tree = ast.parse(source, filename=str(filepath))
    except SyntaxError:
        return [], total_lines, code_lines, 0

    functions: List[FunctionInfo] = []
    import_count = 0

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            length = _function_length(node)
            complexity = _cyclomatic_complexity(node)
            functions.append(
                FunctionInfo(
                    name=node.name,
                    lineno=node.lineno,
                    length=length,
                    complexity=complexity,
                )
            )
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            import_count += 1

    return functions, total_lines, code_lines, import_count


# ---------------------------------------------------------------------------
# Debt marker detection
# ---------------------------------------------------------------------------


def find_debt_markers(filepath: Path) -> List[Dict]:
    """Find TODO/FIXME/HACK/XXX etc. in a file."""
    markers = []
    try:
        lines = filepath.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return markers

    for i, line in enumerate(lines, 1):
        for pattern in DEBT_MARKER_PATTERNS:
            match = pattern.search(line)
            if match:
                markers.append(
                    {
                        "line": i,
                        "type": match.group(1).upper(),
                        "text": line.strip()[:120],
                    }
                )
    return markers


# ---------------------------------------------------------------------------
# Simple duplication detection (hash-based block comparison)
# ---------------------------------------------------------------------------


def detect_duplicate_blocks(filepath: Path, block_size: int = 6) -> int:
    """Count duplicate code blocks (consecutive non-empty line sequences)."""
    try:
        lines = filepath.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return 0

    # Normalize: strip whitespace, skip blanks/comments
    normalized = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            normalized.append(stripped)

    if len(normalized) < block_size * 2:
        return 0

    seen_blocks: set = set()
    dup_count = 0
    for i in range(len(normalized) - block_size + 1):
        block = tuple(normalized[i : i + block_size])
        block_hash = hash(block)
        if block_hash in seen_blocks:
            dup_count += 1
        else:
            seen_blocks.add(block_hash)

    return dup_count


# ---------------------------------------------------------------------------
# Dimension scoring (each returns 0-100, higher = more debt)
# ---------------------------------------------------------------------------


def score_complexity(functions: List[FunctionInfo], code_lines: int) -> float:
    """Score based on cyclomatic complexity and function length."""
    if not functions:
        return 0.0

    max_cc = max(f.complexity for f in functions)
    avg_cc = sum(f.complexity for f in functions) / len(functions)
    max_len = max(f.length for f in functions)
    avg_len = sum(f.length for f in functions) / len(functions)

    # Complexity sub-score (0-50)
    if max_cc >= COMPLEXITY_CRITICAL:
        cc_score = 50.0
    elif max_cc >= COMPLEXITY_WARN:
        cc_score = 25.0 + 25.0 * (max_cc - COMPLEXITY_WARN) / (COMPLEXITY_CRITICAL - COMPLEXITY_WARN)
    else:
        cc_score = min(25.0, avg_cc * 2.5)

    # Length sub-score (0-50)
    if max_len >= FUNCTION_LENGTH_CRITICAL:
        len_score = 50.0
    elif max_len >= FUNCTION_LENGTH_WARN:
        len_score = 25.0 + 25.0 * (max_len - FUNCTION_LENGTH_WARN) / (FUNCTION_LENGTH_CRITICAL - FUNCTION_LENGTH_WARN)
    else:
        len_score = min(25.0, avg_len * 0.5)

    return min(100.0, cc_score + len_score)


def score_duplication(dup_block_count: int, code_lines: int) -> float:
    """Score based on duplicate code blocks."""
    if code_lines < 20:
        return 0.0
    ratio = dup_block_count / max(code_lines / 6, 1)
    return min(100.0, ratio * 200)


def score_test_gap(filepath: Path, project_name: str) -> float:
    """Score based on whether a corresponding test file exists.

    This is a simple heuristic; real coverage data can be integrated later.
    """
    fname = filepath.stem
    if fname.startswith("test_") or fname.startswith("conftest"):
        return 0.0  # Test files have no test gap

    # Check for test file existence
    possible_test_dirs = []
    # Walk up to find tests/ directory
    for parent in filepath.parents:
        test_dir = parent / "tests"
        if test_dir.exists():
            possible_test_dirs.append(test_dir)
        test_dir = parent / "tests" / "unit"
        if test_dir.exists():
            possible_test_dirs.append(test_dir)

    for test_dir in possible_test_dirs:
        # Check tests/test_<name>.py and tests/unit/test_<name>.py
        for subdir in [test_dir, test_dir / "unit"]:
            test_file = subdir / f"test_{fname}.py"
            if test_file.exists():
                return 15.0  # Has test file but coverage unknown

    # No test file found at all
    return 70.0


def score_debt_markers(marker_count: int, code_lines: int) -> float:
    """Score based on TODO/FIXME/HACK density."""
    if code_lines < 10:
        return 0.0
    density = marker_count / (code_lines / 100)  # per 100 LOC
    if density >= 5.0:
        return 100.0
    elif density >= 2.0:
        return 50.0 + 50.0 * (density - 2.0) / 3.0
    else:
        return min(50.0, density * 25.0)


def score_modularity(total_lines: int, import_count: int) -> float:
    """Score based on file size and import count."""
    size_score = 0.0
    if total_lines >= FILE_SIZE_CRITICAL:
        size_score = 50.0
    elif total_lines >= FILE_SIZE_WARN:
        size_score = 25.0 + 25.0 * (total_lines - FILE_SIZE_WARN) / (FILE_SIZE_CRITICAL - FILE_SIZE_WARN)
    else:
        size_score = min(25.0, total_lines * 0.05)

    import_score = 0.0
    if import_count >= IMPORT_DEPTH_CRITICAL:
        import_score = 50.0
    elif import_count >= IMPORT_DEPTH_WARN:
        import_score = 25.0 + 25.0 * (import_count - IMPORT_DEPTH_WARN) / (IMPORT_DEPTH_CRITICAL - IMPORT_DEPTH_WARN)
    else:
        import_score = min(25.0, import_count * 1.67)

    return min(100.0, size_score + import_score)


def score_doc_sync(filepath: Path, mapped_scripts: set) -> float:
    """Score based on whether this file is mapped in directives/INDEX.md."""
    fname = filepath.name
    if fname.startswith("test_") or fname.startswith("conftest") or fname.startswith("_"):
        return 0.0  # Test/internal files don't need mapping

    if fname in mapped_scripts:
        return 0.0
    return 40.0  # Unmapped execution script = moderate debt


# ---------------------------------------------------------------------------
# Scanning engine
# ---------------------------------------------------------------------------


def _load_mapped_scripts() -> set:
    """Parse INDEX.md to get the set of mapped execution scripts."""
    index_path = WORKSPACE_DIR / "directives" / "INDEX.md"
    mapped = set()
    if not index_path.exists():
        return mapped
    try:
        content = index_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return mapped

    for line in content.splitlines():
        if "|" not in line or line.strip().startswith("|--"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 3:
            scripts_cell = parts[2] if len(parts) > 2 else ""
            for script in re.findall(r"(\w+\.py)", scripts_cell):
                mapped.add(script)
    return mapped


def collect_python_files(root: Path, project_name: str = "workspace") -> List[Tuple[Path, str]]:
    """Collect all Python files under a root, returning (filepath, project_name) pairs."""
    results = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fname in filenames:
            if Path(fname).suffix in SUPPORTED_EXTENSIONS:
                results.append((Path(dirpath) / fname, project_name))
    return results


def scan_file(filepath: Path, project_name: str, mapped_scripts: set) -> FileDebtScore:
    """Compute debt score for a single file."""
    functions, total_lines, code_lines, import_count = analyze_python_file(filepath)
    markers = find_debt_markers(filepath)
    dup_count = detect_duplicate_blocks(filepath)

    # Dimension scores
    cx_score = score_complexity(functions, code_lines)
    dup_score = score_duplication(dup_count, code_lines)
    tg_score = score_test_gap(filepath, project_name)
    dm_score = score_debt_markers(len(markers), code_lines)
    mod_score = score_modularity(total_lines, import_count)
    ds_score = score_doc_sync(filepath, mapped_scripts)

    # Weighted total
    total = (
        cx_score * WEIGHTS["complexity"]
        + dup_score * WEIGHTS["duplication"]
        + tg_score * WEIGHTS["test_gap"]
        + dm_score * WEIGHTS["debt_markers"]
        + mod_score * WEIGHTS["modularity"]
        + ds_score * WEIGHTS["doc_sync"]
    )

    # Cost estimates
    principal = total * MINUTES_PER_DEBT_POINT
    interest = total * INTEREST_PER_DEBT_POINT_MONTHLY

    # Top complex functions
    top_funcs = sorted(functions, key=lambda f: f.complexity, reverse=True)[:5]

    try:
        rel_path = str(filepath.relative_to(REPO_ROOT))
    except ValueError:
        rel_path = str(filepath)

    return FileDebtScore(
        path=str(filepath),
        relative_path=rel_path,
        project=project_name,
        total_lines=total_lines,
        code_lines=code_lines,
        function_count=len(functions),
        max_complexity=max((f.complexity for f in functions), default=0),
        avg_complexity=sum(f.complexity for f in functions) / max(len(functions), 1),
        max_function_length=max((f.length for f in functions), default=0),
        avg_function_length=sum(f.length for f in functions) / max(len(functions), 1),
        debt_marker_count=len(markers),
        import_count=import_count,
        duplicate_block_count=dup_count,
        complexity_score=round(cx_score, 1),
        duplication_score=round(dup_score, 1),
        test_gap_score=round(tg_score, 1),
        debt_markers_score=round(dm_score, 1),
        modularity_score=round(mod_score, 1),
        doc_sync_score=round(ds_score, 1),
        total_score=round(total, 1),
        principal_minutes=round(principal, 1),
        interest_monthly_minutes=round(interest, 1),
        top_functions=[
            {"name": f.name, "line": f.lineno, "complexity": f.complexity, "length": f.length} for f in top_funcs
        ],
        debt_markers=[m for m in markers[:10]],
    )


def summarize_project(name: str, file_scores: List[FileDebtScore]) -> ProjectDebtSummary:
    """Aggregate file scores into a project summary."""
    if not file_scores:
        return ProjectDebtSummary(name=name)

    total_score = sum(f.total_score for f in file_scores)
    total_lines = sum(f.total_lines for f in file_scores)
    total_code = sum(f.code_lines for f in file_scores)
    avg_score = total_score / len(file_scores)
    max_score = max(f.total_score for f in file_scores)

    # TDR: ratio of debt-weighted effort vs total development effort
    total_principal = sum(f.principal_minutes for f in file_scores)
    # Estimate dev cost: ~0.5 min per code line
    dev_cost_minutes = max(total_code * 0.5, 1)
    tdr = (total_principal / dev_cost_minutes) * 100

    if tdr < TDR_GREEN:
        grade = "GREEN"
    elif tdr < TDR_YELLOW:
        grade = "YELLOW"
    else:
        grade = "RED"

    top_debtors = sorted(file_scores, key=lambda f: f.total_score, reverse=True)[:10]

    # Dimension averages
    dim_avg = {}
    for dim in WEIGHTS:
        attr = f"{dim}_score"
        dim_avg[dim] = round(sum(getattr(f, attr) for f in file_scores) / len(file_scores), 1)

    return ProjectDebtSummary(
        name=name,
        file_count=len(file_scores),
        total_lines=total_lines,
        total_code_lines=total_code,
        avg_score=round(avg_score, 1),
        max_score=round(max_score, 1),
        tdr_percent=round(tdr, 2),
        tdr_grade=grade,
        total_principal_minutes=round(total_principal, 1),
        total_interest_monthly=round(sum(f.interest_monthly_minutes for f in file_scores), 1),
        top_debtors=[
            {"file": f.relative_path, "score": f.total_score, "principal_min": f.principal_minutes} for f in top_debtors
        ],
        dimension_averages=dim_avg,
    )


# ---------------------------------------------------------------------------
# Main scan orchestrator
# ---------------------------------------------------------------------------

SCAN_TARGETS = {
    "workspace": WORKSPACE_DIR / "execution",
    "blind-to-x": None,  # Resolved dynamically
    "shorts-maker-v2": None,
}


def run_audit(project_filter: Optional[str] = None, top_n: int = 10) -> AuditResult:
    """Run full debt audit across all (or filtered) projects."""
    start = time.time()
    mapped_scripts = _load_mapped_scripts()
    all_file_scores: List[FileDebtScore] = []
    project_summaries: List[ProjectDebtSummary] = []

    targets = {}
    if project_filter:
        if project_filter == "workspace":
            targets["workspace"] = WORKSPACE_DIR / "execution"
        else:
            resolved = resolve_project_dir(project_filter)
            if resolved.exists():
                targets[project_filter] = resolved
            else:
                print(f"Project not found: {project_filter}", file=sys.stderr)
                sys.exit(1)
    else:
        targets["workspace"] = WORKSPACE_DIR / "execution"
        for proj_name in ["blind-to-x", "shorts-maker-v2"]:
            resolved = resolve_project_dir(proj_name)
            if resolved.exists():
                targets[proj_name] = resolved

    for proj_name, proj_dir in targets.items():
        files = collect_python_files(proj_dir, proj_name)
        scores = []
        for fpath, pname in files:
            score = scan_file(fpath, pname, mapped_scripts)
            scores.append(score)

        all_file_scores.extend(scores)
        summary = summarize_project(proj_name, scores)
        project_summaries.append(summary)

    # Overall metrics
    total_principal = sum(s.total_principal_minutes for s in project_summaries)
    total_interest = sum(s.total_interest_monthly for s in project_summaries)
    total_code = sum(s.total_code_lines for s in project_summaries)
    dev_cost = max(total_code * 0.5, 1)
    overall_tdr = (total_principal / dev_cost) * 100

    if overall_tdr < TDR_GREEN:
        overall_grade = "GREEN"
    elif overall_tdr < TDR_YELLOW:
        overall_grade = "YELLOW"
    else:
        overall_grade = "RED"

    duration = time.time() - start

    result = AuditResult(
        timestamp=datetime.now().isoformat(),
        scan_duration_seconds=round(duration, 2),
        projects=project_summaries,
        overall_tdr=round(overall_tdr, 2),
        overall_grade=overall_grade,
        total_files=len(all_file_scores),
        total_principal_hours=round(total_principal / 60, 1),
        total_interest_monthly_hours=round(total_interest / 60, 1),
        file_scores=sorted(all_file_scores, key=lambda f: f.total_score, reverse=True),
    )

    return result


# ---------------------------------------------------------------------------
# Output formatters
# ---------------------------------------------------------------------------


def _grade_emoji(grade: str) -> str:
    return {"GREEN": "[OK]", "YELLOW": "[!!]", "RED": "[XX]"}.get(grade, "[??]")


def print_human(result: AuditResult, top_n: int = 10) -> None:
    """Print human-readable report."""
    print("=" * 70)
    print("  VibeDebt Audit Report")
    print(f"  {result.timestamp}")
    print(f"  Scan: {result.total_files} files in {result.scan_duration_seconds}s")
    print("=" * 70)
    print()

    print(f"  Overall TDR: {result.overall_tdr:.1f}% {_grade_emoji(result.overall_grade)}")
    print(f"  Principal (fix cost): {result.total_principal_hours:.1f} hours")
    print(f"  Interest (monthly):   {result.total_interest_monthly_hours:.1f} hours/month")
    print()

    for proj in result.projects:
        print(f"--- {proj.name} ---")
        print(f"  Files: {proj.file_count} | Lines: {proj.total_code_lines:,}")
        print(f"  TDR: {proj.tdr_percent:.1f}% {_grade_emoji(proj.tdr_grade)}")
        print(f"  Avg Score: {proj.avg_score:.1f} / 100 | Max: {proj.max_score:.1f}")
        print(
            f"  Principal: {proj.total_principal_minutes:.0f} min | Interest: {proj.total_interest_monthly:.0f} min/mo"
        )

        if proj.dimension_averages:
            dims = " | ".join(f"{k}={v:.0f}" for k, v in proj.dimension_averages.items())
            print(f"  Dimensions: {dims}")

        if proj.top_debtors:
            print("  Top debtors:")
            for d in proj.top_debtors[:top_n]:
                print(f"    {d['score']:5.1f}  {d['file']}")
        print()

    print("=" * 70)


def save_json(result: AuditResult) -> Path:
    """Save result as JSON."""
    TMP_ROOT.mkdir(parents=True, exist_ok=True)
    out_path = TMP_ROOT / "debt_audit_result.json"

    # Convert to dict, but limit file_scores to top 50 for readability
    data = asdict(result)
    data["file_scores"] = data["file_scores"][:50]

    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_path


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="VibeDebt Auditor")
    parser.add_argument("--project", type=str, default=None, help="Scan a specific project only")
    parser.add_argument("--format", choices=["human", "json"], default="human", help="Output format")
    parser.add_argument("--top", type=int, default=10, help="Show top N debtors per project")
    parser.add_argument("--save", action="store_true", help="Save result to .tmp/ and history DB")
    args = parser.parse_args()

    result = run_audit(project_filter=args.project, top_n=args.top)

    if args.format == "json":
        json_path = save_json(result)
        print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
    else:
        print_human(result, top_n=args.top)

    # Always save to .tmp and history
    json_path = save_json(result)

    try:
        from execution.debt_history_db import DebtHistoryDB

        db = DebtHistoryDB()
        db.record_audit(result)
        print(f"\n[Saved] JSON: {json_path}")
        print(f"[Saved] History DB: {db.db_path}")
    except Exception as e:
        print(f"\n[Saved] JSON: {json_path}")
        print(f"[Warning] History DB save failed: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
