"""
_ci_report.py — AnalysisReport 직렬화 유틸리티.

제공 클래스:
- ReportGenerator: JSON / Markdown 출력 변환
"""

from __future__ import annotations

import json
from dataclasses import asdict

from execution._ci_models import AnalysisReport


class ReportGenerator:
    @staticmethod
    def to_json(report: AnalysisReport) -> str:
        data = {
            "timestamp": report.timestamp,
            "summary": report.summary,
            "files": [],
        }
        for fr in report.files:
            file_data = {
                "path": fr.path,
                "language": fr.language,
                "skipped": fr.skipped,
                "skipped_reason": fr.skipped_reason,
                "metrics": asdict(fr.metrics) if fr.metrics else None,
                "issues": [asdict(i) for i in fr.issues],
            }
            data["files"].append(file_data)
        return json.dumps(data, indent=2, ensure_ascii=False)

    @staticmethod
    def to_markdown(report: AnalysisReport) -> str:
        lines = []
        lines.append("# Code Analysis Report")
        lines.append(f"\n**Timestamp:** {report.timestamp}")
        s = report.summary
        lines.append(
            f"\n**Files analyzed:** {s.get('files_analyzed', 0)} | "
            f"**Skipped:** {s.get('files_skipped', 0)} | "
            f"**Total issues:** {s.get('total_issues', 0)}"
        )

        by_sev = s.get("by_severity", {})
        lines.append("\n| Severity | Count |\n|----------|-------|")
        for sev in ("high", "medium", "low"):
            lines.append(f"| {sev} | {by_sev.get(sev, 0)} |")

        by_cat = s.get("by_category", {})
        lines.append("\n| Category | Count |\n|----------|-------|")
        for cat in ("security", "performance", "readability"):
            lines.append(f"| {cat} | {by_cat.get(cat, 0)} |")

        for fr in report.files:
            lines.append(f"\n---\n## {fr.path} ({fr.language})")
            if fr.skipped:
                lines.append(f"*Skipped: {fr.skipped_reason}*")
                continue
            if fr.metrics:
                m = fr.metrics
                lines.append(
                    f"Lines: {m.total_lines} | Functions: {m.function_count} | Max complexity: {m.max_complexity}"
                )
            if not fr.issues:
                lines.append("*No issues found.*")
                continue
            for issue in fr.issues:
                severity_icon = {"high": "[HIGH]", "medium": "[MED]", "low": "[LOW]"}.get(issue.severity, "")
                lines.append(f"\n### {severity_icon} {issue.rule_id}: {issue.message}")
                lines.append(f"**Category:** {issue.category} | **Line:** {issue.line}")
                if issue.code_snippet:
                    lines.append(f"```\n{issue.code_snippet}\n```")
                lines.append(f"**Suggestion:** {issue.suggestion_hint}")

        return "\n".join(lines)
