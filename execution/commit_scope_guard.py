"""
Commit Scope Guard - AI 과잉 수정 차단 도구

이 도구는 3계층 아키텍처 중 'Execution' 계층에 속하며,
AI가 단일 커밋에서 지나치게 넓은 범위의 파일을 수정하는 것을 감지하고 경고합니다.

사용법:
    # 기본 (staged 파일 기준, 임계값 7개)
    python execution/commit_scope_guard.py

    # 임계값 변경
    python execution/commit_scope_guard.py --threshold 5

    # CI에서 사용 (종료 코드로 판단)
    python execution/commit_scope_guard.py --strict

    # pre-commit hook에서 사용
    # .pre-commit-config.yaml에 local hook으로 등록

종료 코드:
    0 — 정상 (임계값 이내)
    1 — 경고 (임계값 초과, --strict 모드에서만)

설계 원칙:
    - stdlib only (외부 의존성 없음)
    - 결정론적: 동일 입력 → 동일 출력
    - AI 세션 행동 규칙(CLAUDE.md)의 기계적 보완
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from collections import Counter
from pathlib import PurePosixPath


# ── 상수 ──

DEFAULT_THRESHOLD = 7  # CLAUDE.md "~250줄, 7개 파일 이하" 규칙과 일치
FORBIDDEN_PATTERNS = [
    # 보안/인증 관련 (모든 프로젝트 공통)
    ".env",
    "credentials.json",
    "token.json",
    # blind-to-x 금지 영역
    "pipeline/orchestrator.py",
    "config/channel_profiles.yaml",
    "edge_tts_client.py",
    # hanwoo-dashboard 금지 영역
    "src/app/api/",
    "src/lib/auth",
    "prisma/schema.prisma",
    # shorts-maker-v2 금지 영역
    "steps/orchestrate_step.py",
    "config/channels/",
]


def get_staged_files() -> list[str]:
    """git에 staged된 파일 목록을 반환합니다."""
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if result.returncode != 0:
        return []
    return [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]


def get_staged_diff_stats() -> dict[str, tuple[int, int]]:
    """staged된 파일별 추가/삭제 줄 수를 반환합니다.

    Returns:
        dict[str, (added, deleted)]
    """
    result = subprocess.run(
        ["git", "diff", "--cached", "--numstat"],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    stats: dict[str, tuple[int, int]] = {}
    if result.returncode != 0:
        return stats
    for line in result.stdout.strip().split("\n"):
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        added_str, deleted_str, filepath = parts[0], parts[1], parts[2]
        # 바이너리 파일은 '-'로 표시
        added = int(added_str) if added_str != "-" else 0
        deleted = int(deleted_str) if deleted_str != "-" else 0
        stats[filepath] = (added, deleted)
    return stats


def classify_by_project(files: list[str]) -> dict[str, list[str]]:
    """파일 경로를 프로젝트별로 분류합니다."""
    projects: dict[str, list[str]] = {}
    for f in files:
        parts = PurePosixPath(f).parts
        if len(parts) >= 2 and parts[0] == "projects":
            project = parts[1]
        elif len(parts) >= 2 and parts[0] == "workspace":
            project = "workspace"
        else:
            project = "root"
        projects.setdefault(project, []).append(f)
    return projects


def check_forbidden_zones(files: list[str]) -> list[str]:
    """금지 영역에 해당하는 파일을 반환합니다."""
    violations = []
    for f in files:
        for pattern in FORBIDDEN_PATTERNS:
            if pattern in f:
                violations.append(f)
                break
    return violations


def analyze_scope(
    files: list[str],
    stats: dict[str, tuple[int, int]],
    threshold: int,
) -> dict:
    """커밋 범위를 분석하여 리포트를 생성합니다."""
    projects = classify_by_project(files)
    forbidden = check_forbidden_zones(files)

    # 파일 확장자 분포
    extensions = Counter()
    for f in files:
        ext = PurePosixPath(f).suffix or "(no ext)"
        extensions[ext] += 1

    # 총 변경량
    total_added = sum(a for a, _ in stats.values())
    total_deleted = sum(d for _, d in stats.values())

    # 위험 점수 계산 (0~100)
    risk_score = 0
    if len(files) > threshold:
        risk_score += min(30, (len(files) - threshold) * 5)
    if len(projects) > 2:
        risk_score += 20  # 다중 프로젝트 수정
    if total_added > 250:
        risk_score += min(20, (total_added - 250) // 50 * 5)
    if forbidden:
        risk_score += 30  # 금지 영역 접근
    risk_score = min(100, risk_score)

    return {
        "file_count": len(files),
        "threshold": threshold,
        "exceeds_threshold": len(files) > threshold,
        "projects": {k: len(v) for k, v in projects.items()},
        "project_count": len(projects),
        "extensions": dict(extensions.most_common()),
        "total_added": total_added,
        "total_deleted": total_deleted,
        "forbidden_violations": forbidden,
        "risk_score": risk_score,
    }


def format_report(report: dict) -> str:
    """분석 결과를 사람이 읽기 쉬운 형태로 포맷합니다."""
    lines = []
    lines.append("=" * 60)
    lines.append("  Commit Scope Guard - 커밋 범위 분석 리포트")
    lines.append("=" * 60)

    # 파일 수
    status = "[!] EXCEEDS" if report["exceeds_threshold"] else "[OK]"
    lines.append(f"  파일 수:  {report['file_count']} / {report['threshold']}  [{status}]")

    # 변경량
    lines.append(f"  변경량:   +{report['total_added']} / -{report['total_deleted']} lines")

    # 위험 점수
    risk = report["risk_score"]
    if risk >= 50:
        risk_label = "HIGH"
    elif risk >= 20:
        risk_label = "MEDIUM"
    else:
        risk_label = "LOW"
    lines.append(f"  위험 점수: {risk}/100  [{risk_label}]")
    lines.append("")

    # 프로젝트 분포
    lines.append("  [Projects]")
    for proj, count in sorted(report["projects"].items()):
        lines.append(f"     {proj}: {count} files")

    # 확장자 분포
    lines.append("  [Extensions]")
    for ext, count in report["extensions"].items():
        lines.append(f"     {ext}: {count}")

    # 금지 영역
    if report["forbidden_violations"]:
        lines.append("")
        lines.append("  [FORBIDDEN ZONE ACCESS DETECTED]")
        for f in report["forbidden_violations"]:
            lines.append(f"     X {f}")
        lines.append("     -> Manual review required for these files.")

    lines.append("=" * 60)

    # 권장 조치
    if report["risk_score"] >= 50:
        lines.append("  [TIP] Split commit by feature scope.")
        lines.append("     git reset HEAD <file> to unstage some files.")
    elif report["exceeds_threshold"]:
        lines.append("  [NOTE] File count exceeds threshold but risk is low.")
        lines.append("     Use --threshold to raise the limit for single-feature changes.")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="AI commit scope guard - prevents over-modification")
    parser.add_argument(
        "--threshold",
        type=int,
        default=DEFAULT_THRESHOLD,
        help=f"Max allowed files per commit (default: {DEFAULT_THRESHOLD})",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit code 1 when threshold exceeded (CI/pre-commit)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress output when no warnings",
    )

    args = parser.parse_args()

    files = get_staged_files()
    if not files:
        if not args.quiet:
            print("Commit Scope Guard: no staged files. skipping.")
        sys.exit(0)

    stats = get_staged_diff_stats()
    report = analyze_scope(files, stats, args.threshold)

    # quiet mode: suppress output when no issues
    if args.quiet and not report["exceeds_threshold"] and not report["forbidden_violations"]:
        sys.exit(0)

    print(format_report(report))

    # strict mode: fail on risk score >= 50
    if args.strict and report["risk_score"] >= 50:
        print("\n[BLOCKED] Commit Scope Guard: risk score >= 50.")
        sys.exit(1)

    # forbidden zone access: block in strict mode
    if args.strict and report["forbidden_violations"]:
        print("\n[BLOCKED] Commit Scope Guard: forbidden zone access detected.")
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
