"""
Unified QA/QC runner for the workspace.

This runner executes pytest across the root workspace and selected projects,
performs AST validation for key modules, runs lightweight security checks, and
optionally captures a small infrastructure snapshot.

Operator ladder role:
    DEEP shared approval-style pass
"""

from __future__ import annotations

import argparse
import ast
import csv
import json
import locale
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

WORKSPACE_DIR = Path(__file__).resolve().parents[1]
if str(WORKSPACE_DIR) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_DIR))

from execution.governance_checks import run_governance_checks, summarize_governance_results  # noqa: E402
from path_contract import REPO_ROOT, resolve_project_dir  # noqa: E402

ROOT_DIR = REPO_ROOT
VENV_PYTHON = ROOT_DIR / "venv" / "Scripts" / "python.exe"
if not VENV_PYTHON.exists():
    VENV_PYTHON = Path(sys.executable)

BLIND_TO_X_DIR = resolve_project_dir("blind-to-x", required_paths=("tests",))
SHORTS_DIR = resolve_project_dir("shorts-maker-v2", required_paths=("tests",))
KNOWLEDGE_DIR = resolve_project_dir("knowledge-dashboard", required_paths=("public",))

PROJECTS = {
    "blind-to-x": {
        "test_runs": [
            {
                "paths": [BLIND_TO_X_DIR / "tests" / "unit"],
                "relative_to_cwd": True,
            },
            {
                "paths": [BLIND_TO_X_DIR / "tests" / "integration"],
                "relative_to_cwd": True,
                "extra_args": ["--ignore=tests/integration/test_curl_cffi.py"],
            },
        ],
        "cwd": BLIND_TO_X_DIR,
        "timeout": 900,
        "note": "Ignored known env-specific curl_cffi CA Error 77 reproducer",
    },
    "shorts-maker-v2": {
        "test_runs": [
            {
                "paths": [
                    SHORTS_DIR / "tests" / "unit",
                    SHORTS_DIR / "tests" / "integration",
                ]
            }
        ],
        "cwd": SHORTS_DIR,
        "timeout": 1200,
    },
    "root": {
        "test_runs": [
            {"paths": [WORKSPACE_DIR / "tests"]},
            {"paths": [WORKSPACE_DIR / "execution" / "tests"]},
        ],
        "cwd": WORKSPACE_DIR,
        "timeout": 300,
    },
}

CORE_MODULES = [
    "workspace/execution/pipeline_watchdog.py",
    "workspace/execution/backup_to_onedrive.py",
    "workspace/execution/roi_calculator.py",
    "workspace/execution/channel_growth_tracker.py",
    "workspace/execution/qaqc_runner.py",
    "projects/blind-to-x/pipeline/process.py",
    "projects/blind-to-x/pipeline/draft_generator.py",
    "projects/blind-to-x/pipeline/notion_upload.py",
    "projects/blind-to-x/pipeline/image_generator.py",
    "projects/blind-to-x/pipeline/image_upload.py",
    "projects/blind-to-x/pipeline/x_analytics.py",
    "projects/shorts-maker-v2/src/shorts_maker_v2/pipeline/orchestrator.py",
    "projects/shorts-maker-v2/src/shorts_maker_v2/pipeline/script_step.py",
    "projects/shorts-maker-v2/src/shorts_maker_v2/pipeline/media_step.py",
    "projects/shorts-maker-v2/src/shorts_maker_v2/pipeline/render_step.py",
    "projects/shorts-maker-v2/src/shorts_maker_v2/pipeline/research_step.py",
    "projects/shorts-maker-v2/src/shorts_maker_v2/config.py",
    "projects/shorts-maker-v2/src/shorts_maker_v2/utils/channel_router.py",
    "projects/shorts-maker-v2/src/shorts_maker_v2/pipeline/error_types.py",
    "projects/shorts-maker-v2/src/shorts_maker_v2/utils/pipeline_status.py",
]

SECURITY_PATTERNS = [
    (
        r'(?:api_key|secret|password|token)\s*=\s*["\'][A-Za-z0-9_\-]{20,}["\']',
        "Hardcoded secret detected",
        re.IGNORECASE,
    ),
    (r'f["\'].*\b(?:SELECT|INSERT|UPDATE|DELETE|DROP|CREATE)\b.*\{[^}]+\}', "Potential SQL injection via f-string", 0),
]

SECURITY_TRIAGE_RULES = [
    {
        "file": "projects/blind-to-x/pipeline/cost_db.py",
        "match_preview": 'f"SELECT * FROM {table}',
        "classification": "false_positive",
        "reason": (
            "archive_old_data only interpolates table names from the internal"
            " _ARCHIVE_TABLES frozenset; the date cutoff remains parameterized."
        ),
    },
    {
        "file": "projects/blind-to-x/pipeline/cost_db.py",
        "match_preview": 'f"INSERT OR IGNORE INTO {table} VALUES ({placeholders}',
        "classification": "false_positive",
        "reason": (
            "archive_old_data only copies between archive tables chosen from the"
            " internal _ARCHIVE_TABLES frozenset; row values stay parameterized"
            " via executemany()."
        ),
    },
    {
        "file": "projects/blind-to-x/pipeline/cost_db.py",
        "match_preview": 'f"DELETE FROM {table}',
        "classification": "false_positive",
        "reason": (
            "archive_old_data only deletes from archive tables chosen from the"
            " internal _ARCHIVE_TABLES frozenset, with the cutoff value parameterized."
        ),
    },
    {
        "file": "workspace/execution/content_db.py",
        "match_preview": 'f"UPDATE content_queue SET {set_clause}',
        "classification": "false_positive",
        "reason": (
            "update_job validates every update key against UPDATABLE_COLUMNS before"
            " composing the SET clause, and all values remain parameterized."
        ),
    },
    {
        "file": "infrastructure/sqlite-multi-mcp/server.py",
        "match_preview": 'f"SELECT COUNT(*) FROM {safe_name}',
        "classification": "false_positive",
        "reason": (
            "get_table_schema interpolates a table identifier only after"
            " _validate_table_name restricts it to safe SQLite identifier characters."
        ),
    },
    {
        "file": "infrastructure/sqlite-multi-mcp/server.py",
        "match_preview": 'f"SELECT COUNT(*) FROM {safe_t}',
        "classification": "false_positive",
        "reason": (
            "quick_stats interpolates table identifiers only after"
            " _validate_table_name restricts them to safe SQLite identifier characters."
        ),
    },
]

SECURITY_EXCLUDE_PATTERNS = [
    r"node_modules",
    r"\.next",
    r"venv",
    r"__pycache__",
    r"prisma[\\/]generated",
    r"\.git",
    r"\.tmp",
    r"_archive",
    r"[\\/]dist[\\/]",
    r"\.min\.js$",
    r"\.agents?[\\/]",
    r"[\\/]build[\\/]",
]


def run_pytest(project_name: str, project_config: dict) -> dict:
    """Run pytest for a configured project."""
    cwd = project_config["cwd"]
    timeout = project_config.get("timeout", 300)
    runs = _build_test_runs(project_config)
    run_results = [_run_pytest_once(project_name, cwd, run_config, timeout) for run_config in runs]
    merged = _merge_pytest_results(run_results)

    if len(run_results) > 1:
        merged["runs"] = run_results

    note = project_config.get("note")
    if note:
        merged["message"] = " | ".join(part for part in [merged.get("message"), note] if part)

    return merged


def _build_test_runs(project_config: dict) -> list[dict]:
    configured_runs = project_config.get("test_runs")
    if configured_runs:
        return configured_runs

    test_paths = project_config.get("test_paths", [])
    return [{"paths": test_paths}]


def _run_pytest_once(project_name: str, cwd: Path, run_config: dict, timeout: int) -> dict:
    test_paths = [Path(path) for path in run_config.get("paths", [])]
    existing_paths = [path for path in test_paths if path.exists()]
    if not existing_paths:
        return {
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "errors": 0,
            "status": "SKIP",
            "message": f"Test directory not found: {', '.join(str(path) for path in test_paths)}",
        }

    relative_to_cwd = bool(run_config.get("relative_to_cwd"))
    cmd_paths: list[str] = []
    for path in existing_paths:
        if relative_to_cwd:
            try:
                cmd_paths.append(str(path.relative_to(cwd)))
                continue
            except ValueError:
                pass
        cmd_paths.append(str(path))

    cmd = [
        str(VENV_PYTHON),
        "-X",
        "utf8",
        "-m",
        "pytest",
        *cmd_paths,
        "-q",
        "--tb=short",
        "--no-header",
        "-o",
        "addopts=",
        "-x" if project_name != "root" else "--maxfail=50",
        *run_config.get("extra_args", []),
    ]

    try:
        result = subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        output = result.stdout + result.stderr

        passed = _parse_count(output, "passed")
        failed = _parse_count(output, "failed")
        skipped = _parse_count(output, "skipped")
        errors = _parse_count(output, "error")

        if result.returncode != 0:
            status = "FAIL"
        elif passed == 0 and failed == 0 and errors == 0:
            status = "FAIL"
        else:
            status = "PASS" if failed == 0 and errors == 0 else "FAIL"

        return {
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "errors": errors,
            "status": status,
            "duration_sec": _parse_duration(output),
        }
    except subprocess.TimeoutExpired:
        return {
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "errors": 1,
            "status": "TIMEOUT",
            "message": f"pytest timed out after {timeout}s",
        }
    except Exception as exc:
        return {"passed": 0, "failed": 0, "skipped": 0, "errors": 1, "status": "ERROR", "message": str(exc)}


def _merge_pytest_results(results: list[dict]) -> dict:
    if not results:
        return {
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "errors": 0,
            "status": "SKIP",
            "message": "No pytest runs configured",
        }

    merged = {
        "passed": sum(result.get("passed", 0) for result in results),
        "failed": sum(result.get("failed", 0) for result in results),
        "skipped": sum(result.get("skipped", 0) for result in results),
        "errors": sum(result.get("errors", 0) for result in results),
        "duration_sec": round(sum(result.get("duration_sec", 0.0) for result in results), 2),
    }

    statuses = {result.get("status") for result in results}
    if "ERROR" in statuses:
        merged["status"] = "ERROR"
    elif "FAIL" in statuses:
        merged["status"] = "FAIL"
    elif "TIMEOUT" in statuses:
        merged["status"] = "TIMEOUT"
    elif statuses == {"SKIP"}:
        merged["status"] = "SKIP"
    else:
        merged["status"] = "PASS"

    messages = [result.get("message") for result in results if result.get("message")]
    if messages:
        merged["message"] = " | ".join(messages)

    return merged


def _parse_count(output: str, keyword: str) -> int:
    match = re.search(rf"(\d+)\s+{keyword}", output)
    return int(match.group(1)) if match else 0


def _parse_duration(output: str) -> float:
    match = re.search(r"in\s+([\d.]+)s", output)
    return float(match.group(1)) if match else 0.0


def _normalize_rel_path(path: str) -> str:
    return path.replace("\\", "/")


def _triage_security_issue(issue: dict[str, str]) -> dict[str, object]:
    normalized_file = _normalize_rel_path(issue.get("file", ""))
    preview = issue.get("match_preview", "")

    for rule in SECURITY_TRIAGE_RULES:
        if normalized_file == rule["file"] and preview.startswith(rule["match_preview"]):
            return {
                **issue,
                "actionable": False,
                "triage": {
                    "classification": rule["classification"],
                    "reason": rule["reason"],
                },
            }

    return {**issue, "actionable": True}


def check_ast(modules: list[str]) -> dict:
    results = {"total": 0, "ok": 0, "failures": []}

    for module_path in modules:
        full_path = ROOT_DIR / module_path
        results["total"] += 1

        if not full_path.exists():
            results["failures"].append({"file": module_path, "error": "File not found"})
            continue

        try:
            source = full_path.read_text(encoding="utf-8")
            ast.parse(source, filename=str(full_path))
            results["ok"] += 1
        except SyntaxError as exc:
            results["failures"].append({"file": module_path, "error": f"SyntaxError at line {exc.lineno}: {exc.msg}"})

    return results


def security_scan() -> dict:
    raw_issues = []
    scan_extensions = {".py", ".ts", ".tsx", ".js", ".jsx"}
    exclude_pattern = re.compile("|".join(SECURITY_EXCLUDE_PATTERNS))

    for root, _dirs, files in os.walk(ROOT_DIR):
        if exclude_pattern.search(root.replace("\\", "/")):
            continue

        for filename in files:
            if Path(filename).suffix not in scan_extensions:
                continue

            filepath = Path(root) / filename
            try:
                content = filepath.read_text(encoding="utf-8", errors="replace")
            except (OSError, UnicodeDecodeError):
                continue

            lines = content.splitlines()
            for pattern_str, description, flags in SECURITY_PATTERNS:
                for match in re.finditer(pattern_str, content, flags):
                    matched_text = match.group()
                    if "example" in filename.lower() or "test" in filename.lower():
                        continue
                    if matched_text.strip().startswith("#") or matched_text.strip().startswith("//"):
                        continue

                    match_line_no = content[: match.start()].count("\n")
                    full_line = lines[match_line_no] if match_line_no < len(lines) else ""
                    if "# noqa" in full_line or '"match_preview":' in full_line:
                        continue

                    rel_path = str(filepath.relative_to(ROOT_DIR))
                    raw_issues.append(
                        {
                            "file": rel_path,
                            "pattern": description,
                            "match_preview": matched_text[:80],
                        }
                    )

    triaged = [_triage_security_issue(issue) for issue in raw_issues]
    actionable_issues = [issue for issue in triaged if issue.get("actionable", True)]
    triaged_issues = [issue for issue in triaged if not issue.get("actionable", True)]

    if actionable_issues:
        status = "WARNING"
        status_detail = f"WARNING ({len(actionable_issues)} actionable issue(s))"
    elif triaged_issues:
        status = "CLEAR"
        status_detail = f"CLEAR ({len(triaged_issues)} triaged issue(s))"
    else:
        status = "CLEAR"
        status_detail = "CLEAR"

    return {
        "status": status,
        "status_detail": status_detail,
        "issues": actionable_issues,
        "triaged_issues": triaged_issues,
        "raw_issue_count": len(raw_issues),
        "actionable_issue_count": len(actionable_issues),
        "triaged_issue_count": len(triaged_issues),
    }


def governance_scan() -> dict:
    results = run_governance_checks()
    summary = summarize_governance_results(results)
    overall = summary["overall"]

    if overall == "fail":
        status = "FAIL"
        status_detail = f"FAIL ({summary['counts']['fail']} fail / {summary['counts']['warn']} warn)"
    elif overall == "warn":
        status = "WARNING"
        status_detail = f"WARNING ({summary['counts']['warn']} warn)"
    else:
        status = "CLEAR"
        status_detail = "CLEAR"

    flagged = [result for result in results if result.get("status") in {"fail", "warn"}]
    return {
        "status": status,
        "status_detail": status_detail,
        "checks": results,
        "flagged_checks": flagged,
        "counts": summary["counts"],
        "total": summary["total"],
    }


def check_infrastructure() -> dict:
    infra: dict[str, object] = {}

    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            timeout=5,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        infra["docker"] = result.returncode == 0
        infra["docker_containers"] = (
            [item.strip() for item in result.stdout.strip().split("\n") if item.strip()]
            if result.returncode == 0
            else []
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        infra["docker"] = False
        infra["docker_containers"] = []

    try:
        import urllib.request

        request = urllib.request.Request("http://localhost:11434/api/tags", method="GET")
        with urllib.request.urlopen(request, timeout=3) as response:
            infra["ollama"] = response.status == 200
    except Exception:
        infra["ollama"] = False

    try:
        scheduler_encoding_fn = getattr(locale, "getencoding", None)
        if callable(scheduler_encoding_fn):
            scheduler_encoding = scheduler_encoding_fn() or "utf-8"
        else:
            scheduler_encoding = locale.getpreferredencoding(False) or "utf-8"

        result = subprocess.run(
            ["schtasks", "/query", "/fo", "CSV", "/nh"],
            capture_output=True,
            text=True,
            encoding=scheduler_encoding,
            errors="replace",
            timeout=10,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        blind_tasks = []
        ready_count = 0
        for row in csv.reader(line for line in result.stdout.splitlines() if line.strip()):
            if not row or "BlindToX" not in row[0]:
                continue
            blind_tasks.append(row)
            status = row[2].strip() if len(row) > 2 else ""
            if status.casefold() == "ready" or status == "준비":
                ready_count += 1
        infra["scheduler"] = {"ready": ready_count, "total": len(blind_tasks)}
    except Exception:
        infra["scheduler"] = {"ready": 0, "total": 0}

    try:
        usage = shutil.disk_usage(str(ROOT_DIR))
        infra["disk_gb_free"] = round(usage.free / (1024**3), 1)
    except Exception:
        infra["disk_gb_free"] = -1

    return infra


def determine_verdict(
    projects: dict, ast_result: dict, security_result: dict, governance_result: dict | None = None
) -> str:
    total_failed = sum(project.get("failed", 0) for project in projects.values())
    real_errors = sum(
        project.get("errors", 0) for project in projects.values() if project.get("status") not in ("TIMEOUT", "SKIP")
    )
    timeout_count = sum(1 for project in projects.values() if project.get("status") == "TIMEOUT")
    ast_failures = len(ast_result.get("failures", []))
    security_issues = security_result.get("actionable_issue_count", len(security_result.get("issues", [])))
    governance_status = (governance_result or {}).get("status", "CLEAR")

    if ast_failures > 0:
        return "REJECTED"

    defect_sum = total_failed + real_errors
    if defect_sum > 0:
        if defect_sum <= 5:
            return "CONDITIONALLY_APPROVED"
        return "REJECTED"

    if timeout_count > 0:
        return "CONDITIONALLY_APPROVED"

    if security_issues > 0:
        return "CONDITIONALLY_APPROVED"

    if governance_status in {"FAIL", "WARNING"}:
        return "CONDITIONALLY_APPROVED"

    return "APPROVED"


def run_qaqc(
    target_projects: list[str] | None = None,
    skip_infra: bool = False,
    skip_debt: bool = False,
    output_file: str | None = None,
) -> dict:
    start_time = time.time()
    timestamp = datetime.now().isoformat(timespec="seconds")

    print("Role: DEEP shared QA/QC approval pass")
    print(f"[INFO] QA/QC runner started at {timestamp}")
    print("=" * 60)

    projects_to_run = target_projects or list(PROJECTS.keys())
    project_results = {}

    for name in projects_to_run:
        if name not in PROJECTS:
            print(f"[WARN] Unknown project: {name}")
            continue

        print(f"\n[TEST] Running pytest for {name}...")
        result = run_pytest(name, PROJECTS[name])
        project_results[name] = result
        print(
            f"   [{result['status']}] {result['passed']} passed, {result['failed']} failed, {result['skipped']} skipped"
        )

    print(f"\n[AST] Checking {len(CORE_MODULES)} core modules...")
    ast_result = check_ast(CORE_MODULES)
    ast_status = "PASS" if ast_result["ok"] == ast_result["total"] else "FAIL"
    print(f"   [{ast_status}] {ast_result['ok']}/{ast_result['total']} OK")

    print("\n[SEC] Running security scan...")
    security_result = security_scan()
    sec_status = security_result.get("status_detail", security_result["status"])
    print(f"   [{security_result['status']}] {sec_status}")

    print("\n[GOV] Running governance scan...")
    governance_result = governance_scan()
    gov_status = governance_result.get("status_detail", governance_result["status"])
    print(f"   [{governance_result['status']}] {gov_status}")

    debt_result: dict[str, object] = {}
    if not skip_debt:
        print("\n[DEBT] Running VibeDebt audit...")
        try:
            from execution.vibe_debt_auditor import run_audit

            audit = run_audit()
            debt_result = {
                "overall_tdr": audit.overall_tdr,
                "overall_grade": audit.overall_grade,
                "total_files": audit.total_files,
                "total_principal_hours": audit.total_principal_hours,
                "total_interest_monthly_hours": audit.total_interest_monthly_hours,
                "projects": [
                    {"name": p.name, "tdr_percent": p.tdr_percent, "tdr_grade": p.tdr_grade, "avg_score": p.avg_score}
                    for p in audit.projects
                ],
            }
            print(f"   TDR: {audit.overall_tdr:.1f}% [{audit.overall_grade}]")
            principal = f"{audit.total_principal_hours:.1f}h"
            interest = f"{audit.total_interest_monthly_hours:.1f}h/mo"
            print(f"   Principal: {principal} | Interest: {interest}")

            try:
                from execution.debt_history_db import DebtHistoryDB

                db = DebtHistoryDB()
                db.record_audit(audit)
            except Exception:
                pass
        except Exception as exc:
            print(f"   [WARN] Debt audit failed: {exc}")
            debt_result = {"error": str(exc)}

    infra_result: dict[str, object] = {}
    if not skip_infra:
        print("\n[INFRA] Checking local infrastructure...")
        infra_result = check_infrastructure()
        print(f"   Docker: {'yes' if infra_result.get('docker') else 'no'}")
        print(f"   Ollama: {'yes' if infra_result.get('ollama') else 'no'}")
        scheduler = infra_result.get("scheduler", {})
        print(f"   Scheduler: {scheduler.get('ready', 0)}/{scheduler.get('total', 0)} Ready")
        print(f"   Disk: {infra_result.get('disk_gb_free', '?')} GB free")

    verdict = determine_verdict(project_results, ast_result, security_result, governance_result)
    total_passed = sum(project.get("passed", 0) for project in project_results.values())
    total_failed = sum(project.get("failed", 0) for project in project_results.values())
    total_errors = sum(project.get("errors", 0) for project in project_results.values())
    total_skipped = sum(project.get("skipped", 0) for project in project_results.values())
    timeout_projects = [name for name, project in project_results.items() if project.get("status") == "TIMEOUT"]
    elapsed = round(time.time() - start_time, 1)

    print("\n" + "=" * 60)
    print(f"[VERDICT] {verdict}")
    print(f"   Total: {total_passed} passed, {total_failed} failed, {total_errors} errors, {total_skipped} skipped")
    if timeout_projects:
        print(f"   Timed out: {', '.join(timeout_projects)}")
    print(f"   Elapsed: {elapsed}s")

    report = {
        "timestamp": timestamp,
        "verdict": verdict,
        "elapsed_sec": elapsed,
        "projects": project_results,
        "total": {
            "passed": total_passed,
            "failed": total_failed,
            "errors": total_errors,
            "skipped": total_skipped,
            "timeout": timeout_projects,
        },
        "ast_check": ast_result,
        "security_scan": security_result,
        "governance_scan": governance_result,
        "debt_audit": debt_result,
        "infrastructure": infra_result,
    }

    out_path = Path(output_file) if output_file else KNOWLEDGE_DIR / "public" / "qaqc_result.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n[SAVED] {out_path}")

    from execution.qaqc_history_db import QaQcHistoryDB

    try:
        db = QaQcHistoryDB()
        db.save_run(report)
        print("[SAVED] QA/QC history database")
    except Exception:
        pass

    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Unified QA/QC runner (deep shared approval pass)",
        epilog=(
            "Operator ladder: doctor.py = FAST readiness, "
            "quality_gate.py = STANDARD local gate, "
            "qaqc_runner.py = DEEP shared approval, "
            "health_check.py = DIAGNOSTIC drill-down."
        ),
    )
    parser.add_argument("--project", "-p", nargs="*", choices=list(PROJECTS.keys()), help="Run only selected projects")
    parser.add_argument("--skip-infra", action="store_true", help="Skip infrastructure checks")
    parser.add_argument("--skip-debt", action="store_true", help="Skip VibeDebt audit")
    parser.add_argument("--output", "-o", type=str, help="Output JSON path")
    args = parser.parse_args()

    run_qaqc(
        target_projects=args.project,
        skip_infra=args.skip_infra,
        skip_debt=args.skip_debt,
        output_file=args.output,
    )


if __name__ == "__main__":
    main()
