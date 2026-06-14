from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = WORKSPACE_ROOT.parent
DIRECTIVES_DIR = WORKSPACE_ROOT / "directives"
EXECUTION_DIR = WORKSPACE_ROOT / "execution"
AI_DIR = REPO_ROOT / ".ai"

INDEX_FILE = DIRECTIVES_DIR / "INDEX.md"
TASKS_FILE = AI_DIR / "TASKS.md"
HANDOFF_FILE = AI_DIR / "HANDOFF.md"

AI_CONTEXT_FILES = (
    "HANDOFF.md",
    "TASKS.md",
    "CONTEXT.md",
    "DECISIONS.md",
    "TOOL_MATRIX.md",
    "STATUS.md",
    "SESSION_LOG.md",
)

TRACKED_BACKLOG_FILES = (DIRECTIVES_DIR / "system_audit_action_plan.md",)

TASK_REF_PATTERN = re.compile(r"\[TASK:\s*(T-\d+)\]", re.IGNORECASE)

RELAY_CLAIM_SPECS = (
    {
        "name": "code_evaluator_graph_engine_integration",
        "claim_pattern": re.compile(
            r"`workspace/execution/code_evaluator\.py`\s+integrated into `graph_engine\.py`",
            re.IGNORECASE,
        ),
        "proof_path": EXECUTION_DIR / "graph_engine.py",
        "proof_patterns": (
            re.compile(r"\bCodeEvaluator\b"),
            re.compile(r"code_evaluator", re.IGNORECASE),
        ),
        "failure_detail": (
            "HANDOFF claims `workspace/execution/code_evaluator.py` is integrated into "
            "`graph_engine.py`, but `graph_engine.py` does not reference `CodeEvaluator` "
            "or `code_evaluator`."
        ),
    },
)

STATUS_OK = "ok"
STATUS_WARN = "warn"
STATUS_FAIL = "fail"


def _check_result(name: str, status: str, detail: str = "", **extra: object) -> dict[str, object]:
    result: dict[str, object] = {
        "name": name,
        "category": "governance",
        "status": status,
        "detail": detail,
        "checked_at": datetime.now().isoformat(timespec="seconds"),
    }
    result.update(extra)
    return result


def _index_table_state(line: str) -> tuple[bool, bool] | None:
    if line.startswith("|") and "Directive" in line and "Execution Script" in line:
        return True, False
    if line.startswith("|") and re.match(r"\|\s*Script\s*\|", line):
        return False, True
    if "SOP → Execution" in line:
        return True, False
    if "매핑 없는 Execution" in line:
        return False, True
    if line.startswith("---"):
        return False, False
    return None


def _index_row_cells(line: str) -> list[str] | None:
    if not line.startswith("|") or line.startswith("|--"):
        return None

    cells = [cell.strip() for cell in line.split("|")[1:-1]]
    if len(cells) < 2:
        return None
    return cells


def _index_script_names(scripts_raw: str) -> list[str]:
    return [
        re.sub(r"`", "", script).strip()
        for script in re.split(r"[,;→]", scripts_raw)
        if re.sub(r"`", "", script).strip().endswith(".py")
    ]


def parse_index(index_path: Path = INDEX_FILE) -> tuple[dict[str, list[str]], dict[str, str]]:
    """Parse directives/INDEX.md into mapped SOPs and explicitly-unmapped scripts."""
    text = index_path.read_text(encoding="utf-8")

    sop_map: dict[str, list[str]] = {}
    unmapped: dict[str, str] = {}
    in_sop_table = False
    in_unmapped_table = False

    for line in text.splitlines():
        line = line.strip()

        state = _index_table_state(line)
        if state is not None:
            in_sop_table, in_unmapped_table = state
            continue

        cells = _index_row_cells(line)
        if cells is None:
            continue

        if in_sop_table and cells[0] and not cells[0].startswith("Directive"):
            sop_name = cells[0]
            sop_map[sop_name] = _index_script_names(cells[1])

        if in_unmapped_table and cells[0] and not cells[0].startswith("Script"):
            unmapped[cells[0]] = cells[1] if len(cells) > 1 else ""

    return sop_map, unmapped


def audit_ai_context_files(
    ai_dir: Path = AI_DIR, required_files: tuple[str, ...] = AI_CONTEXT_FILES
) -> dict[str, object]:
    missing = [name for name in required_files if not (ai_dir / name).is_file()]
    if missing:
        return _check_result(
            "ai_context_files",
            STATUS_FAIL,
            f"Missing required AI context file(s): {', '.join(missing)}",
            missing=missing,
        )

    return _check_result(
        "ai_context_files",
        STATUS_OK,
        f"All {len(required_files)} required AI context files are present",
        count=len(required_files),
    )


def audit_relay_claim_consistency(
    *,
    handoff_path: Path = HANDOFF_FILE,
    claim_specs: tuple[dict[str, object], ...] = RELAY_CLAIM_SPECS,
) -> dict[str, object]:
    if not handoff_path.is_file():
        return _check_result(
            "relay_claim_consistency",
            STATUS_FAIL,
            f"Relay file missing: {handoff_path}",
            issues=[f"[MISSING] {handoff_path}"],
        )

    handoff_text = handoff_path.read_text(encoding="utf-8")
    issues: list[str] = []
    checked_claims: list[str] = []

    for spec in claim_specs:
        claim_pattern = spec["claim_pattern"]
        if not isinstance(claim_pattern, re.Pattern):
            continue
        if not claim_pattern.search(handoff_text):
            continue

        checked_claims.append(str(spec["name"]))
        proof_path = Path(spec["proof_path"])
        if not proof_path.is_file():
            issues.append(f"[MISSING PROOF] {proof_path}")
            continue

        proof_text = proof_path.read_text(encoding="utf-8")
        proof_patterns = spec.get("proof_patterns", ())
        if not any(pattern.search(proof_text) for pattern in proof_patterns):
            issues.append(str(spec["failure_detail"]))

    if issues:
        return _check_result(
            "relay_claim_consistency",
            STATUS_FAIL,
            f"Detected {len(issues)} stale relay claim(s)",
            issues=issues,
            checked_claims=checked_claims,
        )

    if checked_claims:
        detail = f"Validated {len(checked_claims)} relay claim(s) against live code"
    else:
        detail = "No targeted relay claims found in HANDOFF.md"

    return _check_result(
        "relay_claim_consistency",
        STATUS_OK,
        detail,
        checked_claims=checked_claims,
    )


def _directive_mapping_repo_root(root: Path) -> Path:
    return root.parent if root.name == "workspace" else root


def _missing_sop_issues(sop_map: dict[str, list[str]], directives_dir: Path) -> list[str]:
    return [
        f"[SOP MISSING] {sop} listed in INDEX but not found" for sop in sop_map if not (directives_dir / sop).exists()
    ]


def _mapped_script_candidates(script: str, *, execution_dir: Path, root: Path, repo_root: Path) -> list[Path]:
    return [
        execution_dir / script,
        root / script,
        repo_root / script,
        repo_root / "execution" / script,
    ]


def _mapped_script_issues(
    sop_map: dict[str, list[str]], *, execution_dir: Path, root: Path, repo_root: Path
) -> tuple[set[str], list[str]]:
    all_mapped_scripts: set[str] = set()
    issues: list[str] = []

    for sop, scripts in sop_map.items():
        for script in scripts:
            all_mapped_scripts.add(script)
            candidates = _mapped_script_candidates(script, execution_dir=execution_dir, root=root, repo_root=repo_root)
            if not any(candidate.exists() for candidate in candidates):
                issues.append(f"[SCRIPT MISSING] {script} (mapped by {sop})")

    return all_mapped_scripts, issues


def _unmapped_script_issues(unmapped: dict[str, str], execution_dir: Path) -> tuple[set[str], list[str]]:
    issues = [
        f"[UNMAPPED MISSING] {script} listed as unmapped but not found"
        for script in unmapped
        if not (execution_dir / script).exists()
    ]
    return set(unmapped), issues


def _actual_execution_scripts(execution_dir: Path) -> set[str]:
    return {path.name for path in execution_dir.glob("*.py") if not path.name.startswith("__")}


def _actual_directive_sops(directives_dir: Path) -> set[str]:
    return {
        path.name for path in directives_dir.glob("*.md") if path.name != "INDEX.md" and not path.name.startswith("_")
    }


def _orphan_script_issues(actual_scripts: set[str], all_mapped_scripts: set[str]) -> list[str]:
    return [
        f"[ORPHAN] {orphan} exists in execution/ but not in INDEX.md"
        for orphan in sorted(actual_scripts - all_mapped_scripts)
    ]


def _orphan_sop_issues(actual_sops: set[str], mapped_sops: set[str]) -> list[str]:
    return [
        f"[ORPHAN SOP] {orphan} exists in directives/ but not in INDEX.md"
        for orphan in sorted(actual_sops - mapped_sops)
    ]


def _directive_mapping_detail_status(sop_count: int, unmapped_count: int, issue_count: int) -> tuple[str, str]:
    detail = f"Checked {sop_count} SOP mappings, {unmapped_count} unmapped scripts"
    if issue_count:
        return f"{detail}; found {issue_count} issue(s)", STATUS_FAIL
    return f"{detail}; no mapping drift detected", STATUS_OK


def audit_directive_mapping(
    *,
    index_path: Path = INDEX_FILE,
    directives_dir: Path = DIRECTIVES_DIR,
    execution_dir: Path = EXECUTION_DIR,
    root: Path = WORKSPACE_ROOT,
) -> dict[str, object]:
    sop_map, unmapped = parse_index(index_path=index_path)
    repo_root = _directive_mapping_repo_root(root)

    issues = _missing_sop_issues(sop_map, directives_dir)
    mapped_scripts, mapped_issues = _mapped_script_issues(
        sop_map,
        execution_dir=execution_dir,
        root=root,
        repo_root=repo_root,
    )
    unmapped_scripts, unmapped_issues = _unmapped_script_issues(unmapped, execution_dir)
    issues.extend(mapped_issues)
    issues.extend(unmapped_issues)

    all_mapped_scripts = mapped_scripts | unmapped_scripts
    actual_scripts = _actual_execution_scripts(execution_dir)
    actual_sops = _actual_directive_sops(directives_dir)
    issues.extend(_orphan_script_issues(actual_scripts, all_mapped_scripts))
    issues.extend(_orphan_sop_issues(actual_sops, set(sop_map.keys())))

    detail, status = _directive_mapping_detail_status(len(sop_map), len(unmapped), len(issues))

    return _check_result(
        "directive_mapping",
        status,
        detail,
        issues=issues,
        sop_count=len(sop_map),
        unmapped_count=len(unmapped),
        actual_script_count=len(actual_scripts),
        actual_sop_count=len(actual_sops),
    )


def parse_tasks_active_ids(tasks_path: Path = TASKS_FILE) -> set[str]:
    """Collect task IDs from TODO and IN_PROGRESS sections in .ai/TASKS.md."""
    if not tasks_path.is_file():
        return set()

    active_ids: set[str] = set()
    current_section = ""

    for raw_line in tasks_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()

        if line.startswith("## "):
            current_section = line[3:].strip().upper()
            continue

        if current_section not in {"TODO", "IN_PROGRESS"}:
            continue
        if not line.startswith("|") or line.startswith("|----"):
            continue

        cells = [cell.strip() for cell in line.split("|")[1:-1]]
        if len(cells) < 2:
            continue
        if cells[0] in {"ID", ""}:
            continue

        active_ids.add(cells[0])

    return active_ids


def parse_open_followups(path: Path) -> list[dict[str, object]]:
    followups: list[dict[str, object]] = []
    for line_no, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = raw_line.strip()
        if not stripped.startswith("- [ ]"):
            continue

        task_refs = TASK_REF_PATTERN.findall(stripped)
        followups.append(
            {
                "path": str(path),
                "line": line_no,
                "text": stripped,
                "task_refs": task_refs,
            }
        )
    return followups


def audit_task_backlog_alignment(
    *,
    tasks_path: Path = TASKS_FILE,
    tracked_files: tuple[Path, ...] = TRACKED_BACKLOG_FILES,
) -> dict[str, object]:
    followups: list[dict[str, object]] = []
    for path in tracked_files:
        if path.is_file():
            followups.extend(parse_open_followups(path))

    if not followups:
        return _check_result(
            "task_backlog_alignment",
            STATUS_OK,
            "No unchecked follow-ups found in tracked planning directives",
            open_followup_count=0,
            active_task_count=0,
        )

    active_task_ids = parse_tasks_active_ids(tasks_path)
    unlinked = [item for item in followups if not item["task_refs"]]
    missing_task_refs = sorted(
        {task_id for item in followups for task_id in item["task_refs"] if task_id not in active_task_ids}
    )

    if unlinked or missing_task_refs:
        detail_parts = []
        if unlinked:
            detail_parts.append(f"{len(unlinked)} follow-up(s) missing [TASK: T-XXX] linkage")
        if missing_task_refs:
            detail_parts.append(f"missing active task(s): {', '.join(missing_task_refs)}")
        return _check_result(
            "task_backlog_alignment",
            STATUS_FAIL,
            "; ".join(detail_parts),
            open_followup_count=len(followups),
            active_task_count=len(active_task_ids),
            unlinked_followups=unlinked,
            missing_task_refs=missing_task_refs,
        )

    linked_task_ids = sorted({task_id for item in followups for task_id in item["task_refs"]})
    return _check_result(
        "task_backlog_alignment",
        STATUS_OK,
        f"All {len(followups)} tracked follow-up(s) are linked to active task(s): {', '.join(linked_task_ids)}",
        open_followup_count=len(followups),
        active_task_count=len(active_task_ids),
        linked_task_ids=linked_task_ids,
    )


def run_governance_checks() -> list[dict[str, object]]:
    return [
        audit_ai_context_files(),
        audit_relay_claim_consistency(),
        audit_directive_mapping(),
        audit_task_backlog_alignment(),
    ]


def summarize_governance_results(results: list[dict[str, object]]) -> dict[str, object]:
    counts = {STATUS_OK: 0, STATUS_WARN: 0, STATUS_FAIL: 0}
    for result in results:
        status = str(result.get("status", STATUS_FAIL))
        counts[status] = counts.get(status, 0) + 1

    if counts[STATUS_FAIL] > 0:
        overall = STATUS_FAIL
    elif counts[STATUS_WARN] > 0:
        overall = STATUS_WARN
    else:
        overall = STATUS_OK

    return {
        "overall": overall,
        "counts": counts,
        "total": len(results),
    }
