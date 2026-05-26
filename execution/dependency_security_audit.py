"""Automated python dependency security vulnerability auditor.

This tool introduces 'pypa/pip-audit' to scan the project dependencies for
known security vulnerabilities (CVEs). It outputs a beautiful, styled
Rich TUI table and handles severity color-coding, returning exit code 1
if high-risk vulnerabilities are found to serve as a quality gate.
Now optimized with absolute safety for Windows CP949 encoding environments.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

# Rich imports
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich.align import Align
    from rich.box import ROUNDED, HEAVY, ASCII

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

REPO_ROOT = Path(__file__).resolve().parents[1]
IS_WINDOWS = sys.platform == "win32"

# Windows-safe symbols (Unicode-safe for CP949 console)
SYM_SHIELD = "AUDIT" if IS_WINDOWS else "🛡️"
SYM_WARNING = "WARNING" if IS_WINDOWS else "⚠️"
SYM_CHECK = "PASS" if IS_WINDOWS else "✅"
SYM_OK = "OK" if IS_WINDOWS else "✨"
SYM_SCAN = "SCAN" if IS_WINDOWS else "🔍"
SYM_CROSS = "FAIL" if IS_WINDOWS else "❌"


def _safe_print(text: str) -> None:
    try:
        print(text)
    except UnicodeEncodeError:
        encoding = sys.stdout.encoding or "utf-8"
        safe_text = text.encode(encoding, errors="replace").decode(encoding, errors="replace")
        print(safe_text)


def run_pip_audit() -> dict[str, Any]:
    """Execute pip-audit via subprocess and return JSON results."""
    # We use 'python -m pip_audit' because it respects the current Python environment
    # and bypasses Windows PATH script resolution warnings.
    cmd = [sys.executable, "-m", "pip_audit", "--format", "json"]

    # Critical self-annealing: Force subprocess to run in UTF-8 mode
    # to prevent pip_api decoding crashes in Windows Korean environments.
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"

    try:
        result = subprocess.run(
            cmd,
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            check=False,
        )
    except Exception as exc:
        return {"success": False, "error": f"Failed to execute pip-audit: {exc}"}

    stdout = result.stdout.strip()
    stderr = result.stderr.strip()

    if not stdout:
        return {
            "success": False,
            "error": "No output received from pip-audit",
            "stderr": stderr,
            "exit_code": result.returncode,
        }

    try:
        data = json.loads(stdout)
        return {"success": True, "vulnerabilities": data.get("dependencies", []), "exit_code": result.returncode}
    except json.JSONDecodeError:
        return {
            "success": False,
            "error": "Unparseable non-JSON output from pip-audit",
            "stdout": stdout,
            "stderr": stderr,
            "exit_code": result.returncode,
        }


def render_text_report(audit_result: dict[str, Any]) -> None:
    """Standard fallback text report renderer."""
    _safe_print(f"[{SYM_SHIELD}] Dependency Security Scan Results")
    if not audit_result["success"]:
        _safe_print(f"Error: {audit_result['error']}")
        if "stderr" in audit_result and audit_result["stderr"]:
            _safe_print(f"Details:\n{audit_result['stderr']}")
        return

    vulns = audit_result["vulnerabilities"]
    found_any = False
    for dep in vulns:
        dep_name = dep.get("name")
        version = dep.get("version")
        vuln_list = dep.get("vulns", [])
        if vuln_list:
            found_any = True
            for v in vuln_list:
                _safe_print(
                    f"  [VULNERABLE] {dep_name} @ {version} - {v.get('id')} "
                    f"(Fix: {v.get('fix_versions', 'None')}) - {v.get('description', '')[:60]}..."
                )

    if not found_any:
        _safe_print("  No known security vulnerabilities found. Your dependencies are secure!")


def render_rich_report(audit_result: dict[str, Any]) -> None:
    """Beautiful Rich TUI report renderer with CP949 compatibility guards."""
    console = Console(safe_box=True)
    box_style = ASCII if IS_WINDOWS else ROUNDED

    # 1. Header Banner
    title_text = Text(
        f"\n {SYM_SHIELD} DEPENDENCY SECURITY VULNERABILITY AUDIT {SYM_SHIELD} \n", style="bold white on rgb(40,80,60)"
    )
    title_align = Align.center(title_text)
    console.print(Panel(title_align, box=HEAVY if not IS_WINDOWS else ASCII, border_style="rgb(60,140,80)"))
    console.print()

    if not audit_result["success"]:
        err_msg = f"[bold red]Audit Execution Failed![/]\n\n[bold magenta]Error:[/] {audit_result['error']}\n"
        if "stderr" in audit_result and audit_result["stderr"]:
            err_msg += f"[bold magenta]Details:[/] {audit_result['stderr']}"

        console.print(Panel(err_msg, title=f"{SYM_CROSS} Error", border_style="red", box=box_style))
        return

    dependencies = audit_result["vulnerabilities"]

    # 2. Extract and Flatten Vulnerabilities
    flattened_vulns = []
    total_packages_scanned = len(dependencies)
    vulnerable_packages_count = 0

    for dep in dependencies:
        dep_name = dep.get("name")
        version = dep.get("version")
        vuln_list = dep.get("vulns", [])
        if vuln_list:
            vulnerable_packages_count += 1
            for v in vuln_list:
                flattened_vulns.append(
                    {
                        "package": dep_name,
                        "version": version,
                        "cve_id": v.get("id"),
                        "fix_versions": ", ".join(v.get("fix_versions", [])) if v.get("fix_versions") else "None",
                        "description": v.get("description", "No description available"),
                    }
                )

    # 3. Render Summary Panel
    if flattened_vulns:
        summary_text = (
            f"[bold red]{SYM_WARNING} Warning: Known vulnerabilities detected in your dependencies![/]\n"
            f"Please review the table below and update vulnerable packages immediately.\n\n"
            f"[bold]Packages Scanned:[/] {total_packages_scanned}   "
            f"[bold red]Vulnerable Packages:[/] {vulnerable_packages_count}   "
            f"[bold red]Total CVE Alerts:[/] {len(flattened_vulns)}"
        )
        summary_panel = Panel(summary_text, title=f"{SYM_WARNING} Audit Summary", border_style="orange3", box=box_style)
    else:
        summary_text = (
            f"[bold green]{SYM_CHECK} Excellent! No known vulnerabilities detected in your dependencies.[/]\n"
            f"All third-party packages comply with security baselines.\n\n"
            f"[bold]Packages Scanned:[/] {total_packages_scanned}   "
            f"[bold green]Vulnerable Packages:[/] 0"
        )
        summary_panel = Panel(
            summary_text, title=f"{SYM_CHECK} Audit Summary", border_style="rgb(60,140,80)", box=box_style
        )

    console.print(summary_panel)
    console.print()

    # 4. Render Detailed Table if vulnerabilities exist
    if flattened_vulns:
        table = Table(
            title=f"{SYM_SCAN} Vulnerability Details (CVEs)", box=box_style, border_style="rgb(180,80,80)", expand=True
        )
        table.add_column("Package", style="bold cyan", width=20)
        table.add_column("Current Version", style="yellow", width=15)
        table.add_column("CVE ID", style="bold red", width=15)
        table.add_column("Fix Version", style="green", width=15)
        table.add_column("Description", style="white", ratio=1)

        for v in flattened_vulns:
            desc = v["description"]
            if len(desc) > 100:
                desc = desc[:97] + "..."
            table.add_row(v["package"], v["version"], v["cve_id"], v["fix_versions"], desc)

        console.print(table)
    console.print()


def main() -> int:
    audit_result = run_pip_audit()

    # Output UI Report
    if RICH_AVAILABLE:
        try:
            render_rich_report(audit_result)
        except Exception as exc:
            # Fallback if Rich rendering fails despite encoding guards
            _safe_print(f"Rich rendering failed: {exc}. Falling back to standard text.\n")
            render_text_report(audit_result)
    else:
        render_text_report(audit_result)

    if not audit_result["success"]:
        return 2

    vulnerabilities = audit_result["vulnerabilities"]
    has_vulns = any(len(dep.get("vulns", [])) > 0 for dep in vulnerabilities)

    if has_vulns:
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
