#!/usr/bin/env python3
"""
code_improver.py — 정적 코드 분석 게이트웨이 (slim orchestrator).

이 파일은 언어별 Analyzer, 데이터 모델, 리포트 생성 등 세부 로직을
하위 모듈에 위임하고 CLI 진입점과 CodeImprover 오케스트레이터만 보유합니다.

서브모듈:
  execution._ci_models    — 데이터 클래스 & 공유 상수
  execution._ci_utils     — 파일 읽기 / 스킵 / Python 복잡도 헬퍼
  execution._ci_analyzers — 언어별 Analyzer 클래스 (Base, Python, JS, Java, Go, C)
  execution._ci_report    — ReportGenerator (JSON / Markdown)

Usage:
    python code_improver.py <path> [--format json|markdown] [--severity low|medium|high]
                                   [--category readability|performance|security]
                                   [--exclude patterns]
"""

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, Optional

from execution._ci_models import (
    DEFAULT_EXCLUDES,
    SEVERITY_ORDER,
    AnalysisReport,
    FileReport,
    detect_language,
)
from execution._ci_utils import read_file_safe, should_skip
from execution._ci_analyzers import (
    BaseAnalyzer,
    CAnalyzer,
    GoAnalyzer,
    JavaAnalyzer,
    JSAnalyzer,
    PythonAnalyzer,
)
from execution._ci_report import ReportGenerator

# ---------------------------------------------------------------------------
# Public re-exports (backward-compat for existing importers)
# ---------------------------------------------------------------------------
# 기존 코드가 code_improver 에서 직접 임포트하는 심볼을 유지합니다.
from execution._ci_models import (  # noqa: F401
    Issue,
    FileMetrics,
)

# ---------------------------------------------------------------------------
# Analyzer registry
# ---------------------------------------------------------------------------

ANALYZERS: Dict[str, Callable[[], BaseAnalyzer]] = {
    "python": PythonAnalyzer,
    "javascript": lambda: JSAnalyzer(is_typescript=False),
    "typescript": lambda: JSAnalyzer(is_typescript=True),
    "java": JavaAnalyzer,
    "go": GoAnalyzer,
    "c": CAnalyzer,
    "cpp": CAnalyzer,
}


# ---------------------------------------------------------------------------
# Main Orchestrator
# ---------------------------------------------------------------------------


class CodeImprover:
    def __init__(
        self,
        severity_filter: Optional[str] = None,
        category_filter: Optional[str] = None,
        max_file_size: int = 1_048_576,
        exclude_patterns: Optional[set] = None,
    ):
        self.severity_filter = severity_filter
        self.category_filter = category_filter
        self.max_file_size = max_file_size
        self.exclude_patterns = exclude_patterns or DEFAULT_EXCLUDES

    def _get_analyzer(self, language: str) -> BaseAnalyzer:
        factory = ANALYZERS.get(language)
        if factory is None:
            return BaseAnalyzer()
        return factory()

    def analyze_file(self, file_path: str) -> FileReport:
        fp = str(Path(file_path))
        language = detect_language(fp) or "unknown"

        report = FileReport(path=fp, language=language)

        source = read_file_safe(fp)
        if source is None:
            report.skipped = True
            report.skipped_reason = "Could not read file (encoding or permission error)"
            return report

        skip, reason = should_skip(fp, source, self.max_file_size)
        if skip:
            report.skipped = True
            report.skipped_reason = reason
            return report

        if language == "unknown":
            analyzer = BaseAnalyzer()
        else:
            analyzer = self._get_analyzer(language)

        issues, metrics = analyzer.analyze(source, fp)

        if self.severity_filter:
            min_sev = SEVERITY_ORDER.get(self.severity_filter, 0)
            issues = [i for i in issues if SEVERITY_ORDER.get(i.severity, 0) >= min_sev]

        if self.category_filter:
            issues = [i for i in issues if i.category == self.category_filter]

        report.issues = issues
        report.metrics = metrics
        return report

    def analyze_directory(self, dir_path: str) -> AnalysisReport:
        report = AnalysisReport(timestamp=datetime.now().isoformat())
        dir_p = Path(dir_path)

        for root, dirs, files in os.walk(dir_p):
            dirs[:] = [d for d in dirs if d not in self.exclude_patterns]

            for fname in sorted(files):
                fpath = os.path.join(root, fname)
                if detect_language(fpath) is None:
                    continue

                file_report = self.analyze_file(fpath)
                report.files.append(file_report)

        report.summary = self._compute_summary(report)
        return report

    # [FIX #9] Raise ValueError instead of sys.exit() in library method
    def analyze_path(self, path: str) -> AnalysisReport:
        p = Path(path)
        if p.is_file():
            report = AnalysisReport(timestamp=datetime.now().isoformat())
            file_report = self.analyze_file(path)
            report.files.append(file_report)
            report.summary = self._compute_summary(report)
            return report
        elif p.is_dir():
            return self.analyze_directory(path)
        else:
            raise ValueError(f"'{path}' is not a valid file or directory.")

    @staticmethod
    def _compute_summary(report: AnalysisReport) -> Dict:
        total = 0
        by_sev = {"high": 0, "medium": 0, "low": 0}
        by_cat = {"readability": 0, "performance": 0, "security": 0}
        analyzed = 0
        skipped = 0

        for fr in report.files:
            if fr.skipped:
                skipped += 1
                continue
            analyzed += 1
            for issue in fr.issues:
                total += 1
                by_sev[issue.severity] = by_sev.get(issue.severity, 0) + 1
                by_cat[issue.category] = by_cat.get(issue.category, 0) + 1

        return {
            "files_analyzed": analyzed,
            "files_skipped": skipped,
            "total_issues": total,
            "by_severity": by_sev,
            "by_category": by_cat,
        }


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Deterministic static code analysis tool.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("path", help="File or directory to analyze")
    parser.add_argument("--format", choices=["json", "markdown"], default="json", help="Output format (default: json)")
    parser.add_argument(
        "--severity", choices=["low", "medium", "high"], default=None, help="Minimum severity to report (default: all)"
    )
    parser.add_argument(
        "--category",
        choices=["readability", "performance", "security"],
        default=None,
        help="Filter by category (default: all)",
    )
    parser.add_argument("--max-file-size", type=int, default=1_048_576, help="Max file size in bytes (default: 1MB)")
    parser.add_argument("--exclude", type=str, default=None, help="Comma-separated directory names to exclude")

    args = parser.parse_args()

    exclude = DEFAULT_EXCLUDES.copy()
    if args.exclude:
        exclude.update(p.strip() for p in args.exclude.split(","))

    improver = CodeImprover(
        severity_filter=args.severity,
        category_filter=args.category,
        max_file_size=args.max_file_size,
        exclude_patterns=exclude,
    )

    try:
        report = improver.analyze_path(args.path)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if not report.files:
        print("No analyzable files found.", file=sys.stderr)
        sys.exit(2)

    if args.format == "json":
        print(ReportGenerator.to_json(report))
    else:
        print(ReportGenerator.to_markdown(report))

    sys.exit(0)


if __name__ == "__main__":
    main()
