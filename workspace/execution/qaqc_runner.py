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
HANWOO_DIR = resolve_project_dir("hanwoo-dashboard", required_paths=("package.json",))

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
    "hanwoo-dashboard": {
        "runner": "npm",
        "cwd": HANWOO_DIR,
        "timeout": 600,
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

SECURITY_SCAN_EXTENSIONS = {".py", ".ts", ".tsx", ".js", ".jsx"}


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
        return _pytest_skip_result(f"Test directory not found: {', '.join(str(path) for path in test_paths)}")

    cmd_paths = _pytest_command_paths(
        existing_paths,
        cwd,
        relative_to_cwd=bool(run_config.get("relative_to_cwd")),
    )
    cmd = _build_pytest_command(project_name, cmd_paths, run_config.get("extra_args", []))

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
        return _pytest_result_from_output(output, returncode=result.returncode)
    except subprocess.TimeoutExpired:
        return _pytest_timeout_result(timeout)
    except Exception as exc:
        return _pytest_error_result(str(exc))


def _pytest_skip_result(message: str) -> dict:
    return {
        "passed": 0,
        "failed": 0,
        "skipped": 0,
        "errors": 0,
        "status": "SKIP",
        "message": message,
    }


def _pytest_timeout_result(timeout: int) -> dict:
    return {
        "passed": 0,
        "failed": 0,
        "skipped": 0,
        "errors": 1,
        "status": "TIMEOUT",
        "message": f"pytest timed out after {timeout}s",
    }


def _pytest_error_result(message: str) -> dict:
    return {"passed": 0, "failed": 0, "skipped": 0, "errors": 1, "status": "ERROR", "message": message}


def run_npm_test(project_name: str, project_config: dict) -> dict:
    """Run the Node test suite for an npm-based project (e.g. hanwoo-dashboard)."""
    cwd = project_config["cwd"]
    timeout = project_config.get("timeout", 600)
    if not (cwd / "package.json").exists():
        return _pytest_skip_result(f"package.json not found: {cwd}")

    npm = shutil.which("npm") or shutil.which("npm.cmd") or "npm"
    try:
        result = subprocess.run(
            [npm, "test"],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        output = result.stdout + result.stderr
        return _npm_result_from_output(output, returncode=result.returncode)
    except subprocess.TimeoutExpired:
        return _pytest_timeout_result(timeout)
    except Exception as exc:  # noqa: BLE001 - surface launcher failures as ERROR status
        return _pytest_error_result(str(exc))


def _npm_result_from_output(output: str, *, returncode: int) -> dict:
    """Parse the node:test summary block (tap or spec reporter) into a result dict."""
    passed = _parse_npm_count(output, "pass")
    failed = _parse_npm_count(output, "fail")
    skipped = _parse_npm_count(output, "skipped")
    return {
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "errors": 0,
        "status": _pytest_status(returncode=returncode, passed=passed, failed=failed, errors=0),
        "duration_sec": _parse_npm_duration(output),
    }


def _parse_npm_count(output: str, keyword: str) -> int:
    # node:test summary lines look like "# pass 75" (tap) or "ℹ pass 75" (spec).
    # Anchor on the known summary prefixes so test titles containing the keyword are ignored.
    match = re.search(rf"(?m)^[#ℹ\s]*{keyword}\s+(\d+)\s*$", output)
    return int(match.group(1)) if match else 0


def _parse_npm_duration(output: str) -> float:
    match = re.search(r"duration_ms\s+([\d.]+)", output)
    return round(float(match.group(1)) / 1000, 2) if match else 0.0


def _pytest_command_paths(existing_paths: list[Path], cwd: Path, *, relative_to_cwd: bool) -> list[str]:
    cmd_paths: list[str] = []
    for path in existing_paths:
        if relative_to_cwd:
            try:
                cmd_paths.append(str(path.relative_to(cwd)))
                continue
            except ValueError:
                pass
        cmd_paths.append(str(path))
    return cmd_paths


def _build_pytest_command(project_name: str, cmd_paths: list[str], extra_args: list[str]) -> list[str]:
    return [
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
        *extra_args,
    ]


def _pytest_status(*, returncode: int, passed: int, failed: int, errors: int) -> str:
    if returncode != 0:
        return "FAIL"
    if passed == 0 and failed == 0 and errors == 0:
        return "FAIL"
    return "PASS" if failed == 0 and errors == 0 else "FAIL"


def _pytest_result_from_output(output: str, *, returncode: int) -> dict:
    passed = _parse_count(output, "passed")
    failed = _parse_count(output, "failed")
    skipped = _parse_count(output, "skipped")
    errors = _parse_count(output, "error")

    return {
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "errors": errors,
        "status": _pytest_status(returncode=returncode, passed=passed, failed=failed, errors=errors),
        "duration_sec": _parse_duration(output),
    }


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


def _iter_security_scan_files(root_dir: Path, exclude_pattern: re.Pattern):
    for root, _dirs, files in os.walk(root_dir):
        if exclude_pattern.search(root.replace("\\", "/")):
            continue

        for filename in files:
            if Path(filename).suffix in SECURITY_SCAN_EXTENSIONS:
                yield Path(root) / filename


def _read_security_file(filepath: Path) -> str | None:
    try:
        return filepath.read_text(encoding="utf-8", errors="replace")
    except (OSError, UnicodeDecodeError):
        return None


def _security_issue_from_match(
    *,
    filepath: Path,
    root_dir: Path,
    description: str,
    content: str,
    lines: list[str],
    match: re.Match,
) -> dict[str, str] | None:
    filename = filepath.name
    matched_text = match.group()
    if "example" in filename.lower() or "test" in filename.lower():
        return None
    if matched_text.strip().startswith("#") or matched_text.strip().startswith("//"):
        return None

    match_line_no = content[: match.start()].count("\n")
    full_line = lines[match_line_no] if match_line_no < len(lines) else ""
    if "# noqa" in full_line or '"match_preview":' in full_line:
        return None

    return {
        "file": str(filepath.relative_to(root_dir)),
        "pattern": description,
        "match_preview": matched_text[:80],
    }


def _scan_security_file(filepath: Path, root_dir: Path) -> list[dict[str, str]]:
    content = _read_security_file(filepath)
    if content is None:
        return []

    lines = content.splitlines()
    issues = []
    for pattern_str, description, flags in SECURITY_PATTERNS:
        for match in re.finditer(pattern_str, content, flags):
            issue = _security_issue_from_match(
                filepath=filepath,
                root_dir=root_dir,
                description=description,
                content=content,
                lines=lines,
                match=match,
            )
            if issue:
                issues.append(issue)
    return issues


def _security_scan_result(raw_issues: list[dict[str, str]]) -> dict:
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
    exclude_pattern = re.compile("|".join(SECURITY_EXCLUDE_PATTERNS))

    for filepath in _iter_security_scan_files(ROOT_DIR, exclude_pattern):
        raw_issues.extend(_scan_security_file(filepath, ROOT_DIR))

    return _security_scan_result(raw_issues)


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


def _check_docker() -> tuple[bool, list[str]]:
    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            timeout=5,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        containers = (
            [item.strip() for item in result.stdout.strip().split("\n") if item.strip()]
            if result.returncode == 0
            else []
        )
        return result.returncode == 0, containers
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False, []


def _check_ollama() -> bool:
    try:
        import urllib.request

        request = urllib.request.Request("http://localhost:11434/api/tags", method="GET")
        with urllib.request.urlopen(request, timeout=3) as response:
            return response.status == 200
    except Exception:
        return False


def _scheduler_encoding() -> str:
    scheduler_encoding_fn = getattr(locale, "getencoding", None)
    if callable(scheduler_encoding_fn):
        return scheduler_encoding_fn() or "utf-8"
    return locale.getpreferredencoding(False) or "utf-8"


def _parse_scheduler_csv(output: str) -> dict[str, int]:
    blind_tasks = []
    ready_count = 0
    for row in csv.reader(line for line in output.splitlines() if line.strip()):
        if not row or "BlindToX" not in row[0]:
            continue
        blind_tasks.append(row)
        status = row[2].strip() if len(row) > 2 else ""
        if status.casefold() == "ready" or status == "준비":
            ready_count += 1
    return {"ready": ready_count, "total": len(blind_tasks)}


def _check_scheduler() -> dict[str, int]:
    try:
        result = subprocess.run(
            ["schtasks", "/query", "/fo", "CSV", "/nh"],
            capture_output=True,
            text=True,
            encoding=_scheduler_encoding(),
            errors="replace",
            timeout=10,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return _parse_scheduler_csv(result.stdout)
    except Exception:
        return {"ready": 0, "total": 0}


def _disk_free_gb(root_dir: Path) -> float:
    try:
        usage = shutil.disk_usage(str(root_dir))
        return round(usage.free / (1024**3), 1)
    except Exception:
        return -1


def check_infrastructure() -> dict:
    docker_ok, docker_containers = _check_docker()

    return {
        "docker": docker_ok,
        "docker_containers": docker_containers,
        "ollama": _check_ollama(),
        "scheduler": _check_scheduler(),
        "disk_gb_free": _disk_free_gb(ROOT_DIR),
    }


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


def _run_project_checks(projects_to_run: list[str]) -> dict:
    project_results = {}
    for name in projects_to_run:
        if name not in PROJECTS:
            print(f"[WARN] Unknown project: {name}")
            continue

        config = PROJECTS[name]
        if config.get("runner") == "npm":
            print(f"\n[TEST] Running npm test for {name}...")
            result = run_npm_test(name, config)
        else:
            print(f"\n[TEST] Running pytest for {name}...")
            result = run_pytest(name, config)
        project_results[name] = result
        print(
            f"   [{result['status']}] {result['passed']} passed, {result['failed']} failed, {result['skipped']} skipped"
        )
    return project_results


def _run_ast_scan() -> dict:
    print(f"\n[AST] Checking {len(CORE_MODULES)} core modules...")
    ast_result = check_ast(CORE_MODULES)
    ast_status = "PASS" if ast_result["ok"] == ast_result["total"] else "FAIL"
    print(f"   [{ast_status}] {ast_result['ok']}/{ast_result['total']} OK")
    return ast_result


def _run_security_scan() -> dict:
    print("\n[SEC] Running security scan...")
    security_result = security_scan()
    sec_status = security_result.get("status_detail", security_result["status"])
    print(f"   [{security_result['status']}] {sec_status}")
    return security_result


def _run_governance_scan() -> dict:
    print("\n[GOV] Running governance scan...")
    governance_result = governance_scan()
    gov_status = governance_result.get("status_detail", governance_result["status"])
    print(f"   [{governance_result['status']}] {gov_status}")
    return governance_result


def _run_debt_audit() -> dict[str, object]:
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
        return debt_result
    except Exception as exc:
        print(f"   [WARN] Debt audit failed: {exc}")
        return {"error": str(exc)}


def _run_infrastructure_scan() -> dict[str, object]:
    print("\n[INFRA] Checking local infrastructure...")
    infra_result = check_infrastructure()
    print(f"   Docker: {'yes' if infra_result.get('docker') else 'no'}")
    print(f"   Ollama: {'yes' if infra_result.get('ollama') else 'no'}")
    scheduler = infra_result.get("scheduler", {})
    print(f"   Scheduler: {scheduler.get('ready', 0)}/{scheduler.get('total', 0)} Ready")
    print(f"   Disk: {infra_result.get('disk_gb_free', '?')} GB free")
    return infra_result


def _project_totals(project_results: dict) -> dict[str, object]:
    timeout_projects = [name for name, project in project_results.items() if project.get("status") == "TIMEOUT"]
    return {
        "passed": sum(project.get("passed", 0) for project in project_results.values()),
        "failed": sum(project.get("failed", 0) for project in project_results.values()),
        "errors": sum(project.get("errors", 0) for project in project_results.values()),
        "skipped": sum(project.get("skipped", 0) for project in project_results.values()),
        "timeout": timeout_projects,
    }


def _print_verdict_summary(verdict: str, totals: dict[str, object], elapsed: float) -> None:
    print("\n" + "=" * 60)
    print(f"[VERDICT] {verdict}")
    print(
        f"   Total: {totals['passed']} passed, {totals['failed']} failed, "
        f"{totals['errors']} errors, {totals['skipped']} skipped"
    )
    if totals["timeout"]:
        print(f"   Timed out: {', '.join(totals['timeout'])}")
    print(f"   Elapsed: {elapsed}s")


def _build_report(
    *,
    timestamp: str,
    verdict: str,
    elapsed: float,
    project_results: dict,
    totals: dict[str, object],
    ast_result: dict,
    security_result: dict,
    governance_result: dict,
    debt_result: dict[str, object],
    infra_result: dict[str, object],
) -> dict:
    return {
        "timestamp": timestamp,
        "verdict": verdict,
        "elapsed_sec": elapsed,
        "projects": project_results,
        "total": totals,
        "ast_check": ast_result,
        "security_scan": security_result,
        "governance_scan": governance_result,
        "debt_audit": debt_result,
        "infrastructure": infra_result,
    }


def _save_report(report: dict, output_file: str | None) -> Path:
    out_path = Path(output_file) if output_file else KNOWLEDGE_DIR / "public" / "qaqc_result.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n[SAVED] {out_path}")
    return out_path


def _save_history(report: dict) -> None:
    from execution.qaqc_history_db import QaQcHistoryDB

    try:
        db = QaQcHistoryDB()
        db.save_run(report)
        print("[SAVED] QA/QC history database")
    except Exception:
        pass


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
    project_results = _run_project_checks(projects_to_run)
    ast_result = _run_ast_scan()
    security_result = _run_security_scan()
    governance_result = _run_governance_scan()
    debt_result = {} if skip_debt else _run_debt_audit()
    infra_result = {} if skip_infra else _run_infrastructure_scan()

    verdict = determine_verdict(project_results, ast_result, security_result, governance_result)
    totals = _project_totals(project_results)
    elapsed = round(time.time() - start_time, 1)

    _print_verdict_summary(verdict, totals, elapsed)
    report = _build_report(
        timestamp=timestamp,
        verdict=verdict,
        elapsed=elapsed,
        project_results=project_results,
        totals=totals,
        ast_result=ast_result,
        security_result=security_result,
        governance_result=governance_result,
        debt_result=debt_result,
        infra_result=infra_result,
    )
    _save_report(report, output_file)
    _save_history(report)

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
