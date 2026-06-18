"""Automated python dependency *hygiene* auditor (declared-vs-imported).

This tool introduces 'fpgmaas/deptry' (https://github.com/fpgmaas/deptry, MIT) to
scan each Python project in the monorepo for dependency-set defects that the
existing gates do NOT cover:

    * DEP001  missing      - imported but absent from the dependency definitions
                             (runtime ``ImportError`` risk in a clean install).
    * DEP002  unused       - declared as a dependency but never imported (bloat,
                             slower installs, larger attack surface).
    * DEP003  transitive   - imported directly while only available transitively
                             (breaks the moment an indirect provider drops it).
    * DEP004  misplaced    - a development dependency used in production code.

It complements the sibling tools rather than overlapping them:

    * ``dependency_security_audit.py``  -> pip-audit, *known CVEs* in deps.
    * auto-research ``dependency_freshness_inventory.py`` -> *outdated* pins.
    * ``dependency_hygiene_audit.py`` (this file) -> *correctness/leanness* of
      the declared dependency set itself.

Design mirrors ``dependency_security_audit.py``: a Rich TUI with CP949-safe
symbols for Windows-Korean consoles, a ``--json`` mode for automation, and
advisory exit codes so it can run as a non-blocking gate.

Each project carries a ``[tool.deptry]`` block in its own ``pyproject.toml`` that
encodes intentional patterns (first-party cross-project imports, optional
graceful-degradation integrations, dev-only tooling, accepted transitive
imports). deptry reads that config per project, so the residual findings this
tool reports are the *trustworthy* ones.

Exit codes:
    0  clean (no residual findings) OR a soft condition while not ``--strict``
    1  one or more residual hygiene findings were detected
    2  deptry execution failed for at least one project
    3  deptry is not installed (only when ``--strict``; otherwise soft -> 0)
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

# Rich imports (optional — degrade to plain text when unavailable)
try:
    from rich.align import Align
    from rich.box import ASCII, HEAVY, ROUNDED
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

REPO_ROOT = Path(__file__).resolve().parents[1]
IS_WINDOWS = sys.platform == "win32"

# Windows-safe symbols (Unicode-safe for CP949 console)
SYM_BROOM = "HYGIENE" if IS_WINDOWS else "🧹"
SYM_WARNING = "WARNING" if IS_WINDOWS else "⚠️"
SYM_CHECK = "PASS" if IS_WINDOWS else "✅"
SYM_SCAN = "SCAN" if IS_WINDOWS else "🔍"
SYM_CROSS = "FAIL" if IS_WINDOWS else "❌"

# Default Python projects with their own pyproject.toml dependency definitions.
DEFAULT_PROJECTS: list[tuple[str, str]] = [
    ("workspace", "workspace"),
    ("blind-to-x", "projects/blind-to-x"),
    ("shorts-maker-v2", "projects/shorts-maker-v2"),
]

# Rule metadata: human label + severity ordering for sorting/summaries.
RULE_INFO: dict[str, dict[str, str]] = {
    "DEP001": {"label": "missing", "severity": "high"},
    "DEP002": {"label": "unused", "severity": "low"},
    "DEP003": {"label": "transitive", "severity": "medium"},
    "DEP004": {"label": "misplaced-dev", "severity": "low"},
}
_SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def _safe_print(text: str) -> None:
    """Print that never dies on a CP949 console with non-encodable glyphs."""
    try:
        print(text)
    except UnicodeEncodeError:
        encoding = sys.stdout.encoding or "utf-8"
        safe_text = text.encode(encoding, errors="replace").decode(encoding, errors="replace")
        print(safe_text)


def deptry_installed() -> bool:
    """Return True if the deptry module can be imported in this interpreter."""
    try:
        import deptry  # noqa: F401

        return True
    except Exception:
        return False


def discover_projects(root: Path, selected: list[str] | None) -> list[tuple[str, Path]]:
    """Resolve the project list (name, absolute path), filtered by ``selected``.

    Only projects that actually contain a ``pyproject.toml`` are returned; a
    missing project is skipped silently so the audit keeps working as the repo
    layout evolves.
    """
    resolved: list[tuple[str, Path]] = []
    for name, rel in DEFAULT_PROJECTS:
        if selected and name not in selected:
            continue
        path = (root / rel).resolve()
        if (path / "pyproject.toml").is_file():
            resolved.append((name, path))
    return resolved


def run_deptry(project_dir: Path, timeout: int) -> dict[str, Any]:
    """Run deptry against a single project and return parsed findings.

    Uses ``--json-output`` to a temp file (unambiguous absolute path) instead of
    parsing stdout, because deptry interleaves human warnings with findings on
    the console. PYTHONUTF8 is forced for the Windows-Korean environment.
    """
    fd, json_path = tempfile.mkstemp(suffix=".json", prefix="deptry_")
    os.close(fd)

    cmd = [sys.executable, "-m", "deptry", ".", "--json-output", json_path]
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"

    try:
        result = subprocess.run(
            cmd,
            cwd=str(project_dir),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        _cleanup(json_path)
        return {"success": False, "error": f"deptry timed out after {timeout}s", "findings": []}
    except Exception as exc:  # pragma: no cover - defensive
        _cleanup(json_path)
        return {"success": False, "error": f"Failed to execute deptry: {exc}", "findings": []}

    # deptry exits 1 when it finds issues, 0 when clean. Either way the JSON
    # report should exist; only a real crash (missing report) is a failure.
    if not os.path.exists(json_path):
        _cleanup(json_path)
        return {
            "success": False,
            "error": "deptry produced no JSON report",
            "stderr": (result.stderr or "").strip()[-800:],
            "exit_code": result.returncode,
            "findings": [],
        }

    try:
        with open(json_path, encoding="utf-8") as handle:
            raw = json.load(handle)
    except (json.JSONDecodeError, OSError) as exc:
        _cleanup(json_path)
        return {"success": False, "error": f"Unparseable deptry report: {exc}", "findings": []}
    finally:
        _cleanup(json_path)

    findings = []
    for item in raw:
        err = item.get("error", {})
        loc = item.get("location", {})
        findings.append(
            {
                "code": err.get("code", "DEP???"),
                "message": err.get("message", ""),
                "module": item.get("module", ""),
                "file": loc.get("file", ""),
                "line": loc.get("line", 0),
            }
        )
    return {"success": True, "exit_code": result.returncode, "findings": findings}


def _cleanup(path: str) -> None:
    try:
        if os.path.exists(path):
            os.remove(path)
    except OSError:
        pass


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate per-project results into totals and per-code/per-module rollups."""
    total = 0
    by_code: dict[str, int] = {}
    by_module: dict[str, int] = {}
    failed_projects: list[str] = []

    for res in results:
        if not res["success"]:
            failed_projects.append(res["project"])
            continue
        for f in res["findings"]:
            total += 1
            by_code[f["code"]] = by_code.get(f["code"], 0) + 1
            by_module[f["module"]] = by_module.get(f["module"], 0) + 1

    return {
        "total_findings": total,
        "by_code": by_code,
        "by_module": by_module,
        "failed_projects": failed_projects,
        "projects_scanned": len([r for r in results if r["success"]]),
    }


def _severity_for(code: str) -> str:
    return RULE_INFO.get(code, {}).get("severity", "low")


def build_json(results: list[dict[str, Any]], summary: dict[str, Any]) -> dict[str, Any]:
    """Build the machine-readable JSON payload for automation/CI."""
    return {
        "tool": "deptry",
        "schema": "dependency_hygiene_audit.v1",
        "summary": summary,
        "projects": [
            {
                "project": r["project"],
                "success": r["success"],
                "error": r.get("error"),
                "finding_count": len(r["findings"]) if r["success"] else None,
                "findings": [
                    {**f, "severity": _severity_for(f["code"]), "label": RULE_INFO.get(f["code"], {}).get("label", "")}
                    for f in r["findings"]
                ]
                if r["success"]
                else [],
            }
            for r in results
        ],
    }


# ── Rendering ────────────────────────────────────────────────────────────────


def render_text_report(results: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    """Plain-text fallback when Rich is unavailable or rendering fails."""
    _safe_print(f"[{SYM_BROOM}] Dependency Hygiene Audit (deptry)")
    for res in results:
        if not res["success"]:
            _safe_print(f"  [{SYM_CROSS}] {res['project']}: {res.get('error', 'failed')}")
            continue
        findings = res["findings"]
        if not findings:
            _safe_print(f"  [{SYM_CHECK}] {res['project']}: clean")
            continue
        _safe_print(f"  [{SYM_WARNING}] {res['project']}: {len(findings)} finding(s)")
        for f in sorted(findings, key=lambda x: (_SEVERITY_ORDER.get(_severity_for(x["code"]), 9), x["code"])):
            label = RULE_INFO.get(f["code"], {}).get("label", "")
            _safe_print(f"      {f['code']} ({label}) '{f['module']}'  {f['file']}:{f['line']}")
    if summary["total_findings"] == 0 and not summary["failed_projects"]:
        _safe_print("  No dependency hygiene issues found.")


def render_rich_report(results: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    """Rich TUI report with CP949 compatibility guards."""
    console = Console(safe_box=True)
    box_style = ASCII if IS_WINDOWS else ROUNDED

    title_text = Text(
        f"\n {SYM_BROOM} DEPENDENCY HYGIENE AUDIT (deptry) {SYM_BROOM} \n", style="bold white on rgb(40,60,90)"
    )
    console.print(
        Panel(Align.center(title_text), box=HEAVY if not IS_WINDOWS else ASCII, border_style="rgb(70,110,160)")
    )
    console.print()

    total = summary["total_findings"]
    failed = summary["failed_projects"]

    if total or failed:
        code_bits = "  ".join(f"[bold]{code}[/] {summary['by_code'][code]}" for code in sorted(summary["by_code"]))
        warn = f"[bold red]{SYM_CROSS} deptry failed for: {', '.join(failed)}[/]\n" if failed else ""
        summary_text = (
            f"{warn}"
            f"[bold red]{SYM_WARNING} {total} dependency hygiene finding(s) across "
            f"{summary['projects_scanned']} project(s).[/]\n\n"
            f"{code_bits}"
        )
        summary_panel = Panel(summary_text, title=f"{SYM_WARNING} Summary", border_style="orange3", box=box_style)
    else:
        summary_text = (
            f"[bold green]{SYM_CHECK} No dependency hygiene issues across "
            f"{summary['projects_scanned']} project(s).[/]\n"
            f"All declared dependency sets are lean and complete."
        )
        summary_panel = Panel(summary_text, title=f"{SYM_CHECK} Summary", border_style="rgb(60,140,80)", box=box_style)

    console.print(summary_panel)
    console.print()

    for res in results:
        if not res["success"]:
            console.print(
                Panel(
                    f"[bold red]{res.get('error', 'failed')}[/]",
                    title=f"{SYM_CROSS} {res['project']}",
                    border_style="red",
                    box=box_style,
                )
            )
            continue
        findings = res["findings"]
        if not findings:
            continue

        table = Table(
            title=f"{SYM_SCAN} {res['project']} — {len(findings)} finding(s)",
            box=box_style,
            border_style="rgb(180,120,80)",
            expand=True,
        )
        table.add_column("Rule", style="bold red", width=8)
        table.add_column("Kind", style="magenta", width=14)
        table.add_column("Module", style="bold cyan", width=24)
        table.add_column("Location", style="white", ratio=1)

        for f in sorted(findings, key=lambda x: (_SEVERITY_ORDER.get(_severity_for(x["code"]), 9), x["code"])):
            label = RULE_INFO.get(f["code"], {}).get("label", "")
            location = f"{f['file']}:{f['line']}" if f["file"] else ""
            table.add_row(f["code"], label, f["module"], location)

        console.print(table)
        console.print()


# ── Entry point ──────────────────────────────────────────────────────────────


def run_audit(root: Path, selected: list[str] | None, timeout: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Scan all resolved projects and return (per-project results, summary)."""
    projects = discover_projects(root, selected)
    results: list[dict[str, Any]] = []
    for name, path in projects:
        res = run_deptry(path, timeout)
        res["project"] = name
        results.append(res)
    return results, summarize(results)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit declared-vs-imported dependency hygiene across the monorepo.")
    parser.add_argument(
        "--project",
        action="append",
        dest="projects",
        metavar="NAME",
        help=f"Limit to a project (repeatable). Default: all. Known: {', '.join(n for n, _ in DEFAULT_PROJECTS)}",
    )
    parser.add_argument("--root", default=str(REPO_ROOT), help="Repository root (default: auto-detected).")
    parser.add_argument("--timeout", type=int, default=180, help="Per-project deptry timeout in seconds (default 180).")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON instead of the TUI report.")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat soft conditions (deptry not installed) as hard failures.",
    )
    args = parser.parse_args(argv)

    if not deptry_installed():
        msg = "deptry is not installed. Install it with: python -m pip install deptry"
        if args.json:
            _safe_print(json.dumps({"tool": "deptry", "error": msg, "installed": False}, ensure_ascii=False))
        else:
            _safe_print(f"[{SYM_WARNING}] {msg}")
        return 3 if args.strict else 0

    results, summary = run_audit(Path(args.root), args.projects, args.timeout)

    if args.json:
        _safe_print(json.dumps(build_json(results, summary), ensure_ascii=False, indent=2))
    else:
        if RICH_AVAILABLE:
            try:
                render_rich_report(results, summary)
            except Exception as exc:  # pragma: no cover - defensive
                _safe_print(f"Rich rendering failed: {exc}. Falling back to text.\n")
                render_text_report(results, summary)
        else:
            render_text_report(results, summary)

    if summary["failed_projects"]:
        return 2
    if summary["total_findings"] > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
