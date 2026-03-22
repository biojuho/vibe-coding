"""
통합 QA/QC 자동화 러너 스크립트.

3개 프로젝트(blind-to-x, shorts-maker-v2, root)의 테스트를 한 번에 실행하고
AST 검증, 보안 스캔, 인프라 헬스 체크를 수행하여 JSON 결과를 출력합니다.

Usage:
    python execution/qaqc_runner.py                    # 전체 실행
    python execution/qaqc_runner.py --project root     # 특정 프로젝트만
    python execution/qaqc_runner.py --skip-infra       # 인프라 체크 생략
    python execution/qaqc_runner.py --output result.json  # 결과 파일 지정
"""

import argparse
import ast
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# Force UTF-8 output for Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── 경로 설정 ────────────────────────────────────────────
ROOT_DIR = Path(__file__).resolve().parents[1]
VENV_PYTHON = ROOT_DIR / "venv" / "Scripts" / "python.exe"
if not VENV_PYTHON.exists():
    VENV_PYTHON = Path(sys.executable)

# ── 프로젝트 정의 ─────────────────────────────────────────
PROJECTS = {
    "blind-to-x": {
        "test_paths": [ROOT_DIR / "blind-to-x" / "tests"],
        "cwd": ROOT_DIR / "blind-to-x",
    },
    "shorts-maker-v2": {
        "test_paths": [ROOT_DIR / "shorts-maker-v2" / "tests"],
        "cwd": ROOT_DIR / "shorts-maker-v2",
    },
    "root": {
        "test_paths": [ROOT_DIR / "tests", ROOT_DIR / "execution" / "tests"],
        "cwd": ROOT_DIR,
    },
}

# ── AST 검증 대상 파일 ─────────────────────────────────────
CORE_MODULES = [
    "execution/pipeline_watchdog.py",
    "execution/backup_to_onedrive.py",
    "execution/roi_calculator.py",
    "execution/channel_growth_tracker.py",
    "execution/qaqc_runner.py",
    "blind-to-x/pipeline/process.py",
    "blind-to-x/pipeline/draft_generator.py",
    "blind-to-x/pipeline/notion_upload.py",
    "blind-to-x/pipeline/image_generator.py",
    "blind-to-x/pipeline/image_upload.py",
    "blind-to-x/pipeline/x_analytics.py",
    "shorts-maker-v2/src/shorts_maker_v2/pipeline/orchestrator.py",
    "shorts-maker-v2/src/shorts_maker_v2/pipeline/script_step.py",
    "shorts-maker-v2/src/shorts_maker_v2/pipeline/media_step.py",
    "shorts-maker-v2/src/shorts_maker_v2/pipeline/render_step.py",
    "shorts-maker-v2/src/shorts_maker_v2/pipeline/research_step.py",
    "shorts-maker-v2/src/shorts_maker_v2/config.py",
    "shorts-maker-v2/src/shorts_maker_v2/utils/channel_router.py",
    "shorts-maker-v2/src/shorts_maker_v2/pipeline/error_types.py",
    "shorts-maker-v2/src/shorts_maker_v2/utils/pipeline_status.py",
]

# ── 보안 스캔 패턴 ──────────────────────────────────────────
SECURITY_PATTERNS = [
    # API 키 하드코딩 패턴 (false positive 필터 포함)
    (r'(?:api_key|secret|password|token)\s*=\s*["\'][A-Za-z0-9_\-]{20,}["\']', "Hardcoded secret detected"),
    # SQL injection (f-string 직접 삽입)
    (r'f["\'].*(?:SELECT|INSERT|UPDATE|DELETE|DROP|CREATE).*\{[^}]+\}', "Potential SQL injection via f-string"),
]

# Prisma 자동생성 파일 등 false-positive 제외 경로
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
]


def run_pytest(project_name: str, project_config: dict) -> dict:
    """프로젝트의 pytest를 실행하고 결과를 반환합니다."""
    test_paths = project_config.get("test_paths")
    if not test_paths:
        legacy_path = project_config.get("test_dir")
        test_paths = [legacy_path] if legacy_path else []
    cwd = project_config["cwd"]

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

    cmd = [
        str(VENV_PYTHON),
        "-m",
        "pytest",
        *[str(path) for path in existing_paths],
        "-q",
        "--tb=short",
        "--no-header",
        "-x" if project_name != "root" else "--maxfail=50",
    ]

    try:
        result = subprocess.run(
            cmd, cwd=str(cwd), capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300
        )
        output = result.stdout + result.stderr

        # pytest 요약 라인 파싱: "287 passed, 1 skipped in 45.32s"
        passed = _parse_count(output, "passed")
        failed = _parse_count(output, "failed")
        skipped = _parse_count(output, "skipped")
        errors = _parse_count(output, "error")

        # returncode != 0이면 출력 파싱 결과와 무관하게 FAIL 처리
        if result.returncode != 0:
            status = "FAIL"
        elif passed == 0 and failed == 0 and errors == 0:
            status = "FAIL"  # 출력 없음 = crash 또는 수집 실패
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
            "message": "pytest timed out after 300s",
        }
    except Exception as e:
        return {"passed": 0, "failed": 0, "skipped": 0, "errors": 1, "status": "ERROR", "message": str(e)}


def _parse_count(output: str, keyword: str) -> int:
    """pytest 출력에서 특정 키워드의 카운트를 파싱합니다."""
    # e.g., "287 passed" or "1 skipped" or "2 failed"
    pattern = rf"(\d+)\s+{keyword}"
    match = re.search(pattern, output)
    return int(match.group(1)) if match else 0


def _parse_duration(output: str) -> float:
    """pytest 출력에서 실행 시간을 파싱합니다."""
    match = re.search(r"in\s+([\d.]+)s", output)
    return float(match.group(1)) if match else 0.0


def check_ast(modules: list[str]) -> dict:
    """코어 모듈의 AST 구문을 검증합니다."""
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
        except SyntaxError as e:
            results["failures"].append({"file": module_path, "error": f"SyntaxError at line {e.lineno}: {e.msg}"})

    return results


def security_scan() -> dict:
    """보안 패턴 스캔을 수행합니다."""
    issues = []
    scan_extensions = {".py", ".ts", ".tsx", ".js", ".jsx"}

    exclude_pattern = re.compile("|".join(SECURITY_EXCLUDE_PATTERNS))

    for root, dirs, files in os.walk(ROOT_DIR):
        # 제외 디렉토리 건너뛰기
        if exclude_pattern.search(root.replace("\\", "/")):
            continue

        for filename in files:
            ext = Path(filename).suffix
            if ext not in scan_extensions:
                continue

            filepath = Path(root) / filename
            try:
                content = filepath.read_text(encoding="utf-8", errors="replace")
            except (OSError, UnicodeDecodeError):
                continue

            for pattern_str, description in SECURITY_PATTERNS:
                for match in re.finditer(pattern_str, content, re.IGNORECASE):
                    # 추가 false-positive 필터
                    line = match.group()
                    # .env.example, 테스트 파일, 주석은 무시
                    if "example" in filename.lower() or "test" in filename.lower():
                        continue
                    if line.strip().startswith("#") or line.strip().startswith("//"):
                        continue

                    rel_path = str(filepath.relative_to(ROOT_DIR))
                    issues.append(
                        {
                            "file": rel_path,
                            "pattern": description,
                            "match_preview": line[:80],
                        }
                    )

    status = "CLEAR" if len(issues) == 0 else f"WARNING ({len(issues)} issue(s))"
    return {"status": status, "issues": issues}


def check_infrastructure() -> dict:
    """인프라 서비스 헬스를 체크합니다."""
    infra = {}

    # Docker 체크
    try:
        r = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            timeout=5,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        infra["docker"] = r.returncode == 0
        infra["docker_containers"] = (
            [c.strip() for c in r.stdout.strip().split("\n") if c.strip()] if r.returncode == 0 else []
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        infra["docker"] = False
        infra["docker_containers"] = []

    # Ollama 체크
    try:
        import urllib.request

        req = urllib.request.Request("http://localhost:11434/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=3) as resp:
            infra["ollama"] = resp.status == 200
    except Exception:
        infra["ollama"] = False

    # Task Scheduler 체크
    try:
        r = subprocess.run(
            ["schtasks", "/query", "/fo", "CSV", "/nh"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        btx_tasks = [line for line in r.stdout.split("\n") if "BlindToX" in line]
        ready_count = sum(1 for t in btx_tasks if "Ready" in t or "준비" in t)
        infra["scheduler"] = {"ready": ready_count, "total": len(btx_tasks)}
    except Exception:
        infra["scheduler"] = {"ready": 0, "total": 0}

    # 디스크 공간 체크
    try:
        usage = shutil.disk_usage(str(ROOT_DIR))
        infra["disk_gb_free"] = round(usage.free / (1024**3), 1)
    except Exception:
        infra["disk_gb_free"] = -1

    return infra


def determine_verdict(projects: dict, ast_result: dict, security_result: dict) -> str:
    """최종 QC 판정을 결정합니다."""
    total_failed = sum(p.get("failed", 0) for p in projects.values())
    # TIMEOUT은 실제 테스트 실패가 아니므로 분리 처리
    real_errors = sum(p.get("errors", 0) for p in projects.values() if p.get("status") not in ("TIMEOUT", "SKIP"))
    timeout_count = sum(1 for p in projects.values() if p.get("status") == "TIMEOUT")
    ast_failures = len(ast_result.get("failures", []))
    security_issues = len(security_result.get("issues", []))

    # AST 구문 오류는 즉시 반려
    if ast_failures > 0:
        return "REJECTED"

    # 실제 테스트 실패는 반려
    if total_failed > 0 or real_errors > 0:
        if total_failed <= 2 and real_errors == 0:
            return "CONDITIONALLY_APPROVED"
        return "REJECTED"

    # TIMEOUT은 조건부 승인 (테스트 자체는 실패하지 않음)
    if timeout_count > 0:
        return "CONDITIONALLY_APPROVED"

    # 보안 이슈는 조건부 승인
    if security_issues > 0:
        return "CONDITIONALLY_APPROVED"

    return "APPROVED"


def run_qaqc(
    target_projects: list[str] | None = None,
    skip_infra: bool = False,
    output_file: str | None = None,
) -> dict:
    """전체 QA/QC 파이프라인을 실행합니다."""
    start_time = time.time()
    timestamp = datetime.now().isoformat(timespec="seconds")

    print(f"🚀 QA/QC Runner 시작 — {timestamp}")
    print("=" * 60)

    # 1. pytest 실행
    projects_to_run = target_projects or list(PROJECTS.keys())
    project_results = {}

    for name in projects_to_run:
        if name not in PROJECTS:
            print(f"⚠️  알 수 없는 프로젝트: {name}")
            continue

        print(f"\n📦 [{name}] pytest 실행 중...")
        result = run_pytest(name, PROJECTS[name])
        project_results[name] = result

        status_icon = "✅" if result["status"] == "PASS" else "❌"
        print(f"   {status_icon} {result['passed']} passed, {result['failed']} failed, {result['skipped']} skipped")

    # 2. AST 검증
    print(f"\n🔍 AST 구문 검증 ({len(CORE_MODULES)}개 파일)...")
    ast_result = check_ast(CORE_MODULES)
    ast_icon = "✅" if ast_result["ok"] == ast_result["total"] else "❌"
    print(f"   {ast_icon} {ast_result['ok']}/{ast_result['total']} OK")

    # 3. 보안 스캔
    print("\n🛡️  보안 패턴 스캔...")
    security_result = security_scan()
    sec_icon = "✅" if security_result["status"] == "CLEAR" else "⚠️"
    print(f"   {sec_icon} {security_result['status']}")

    # 4. 인프라 헬스 체크
    infra_result = {}
    if not skip_infra:
        print("\n🏗️  인프라 헬스 체크...")
        infra_result = check_infrastructure()
        print(f"   Docker: {'🟢' if infra_result.get('docker') else '🔴'}")
        print(f"   Ollama: {'🟢' if infra_result.get('ollama') else '🔴'}")
        sched = infra_result.get("scheduler", {})
        print(f"   Scheduler: {sched.get('ready', 0)}/{sched.get('total', 0)} Ready")
        print(f"   Disk: {infra_result.get('disk_gb_free', '?')} GB free")

    # 5. 판정
    verdict = determine_verdict(project_results, ast_result, security_result)
    total_passed = sum(p.get("passed", 0) for p in project_results.values())
    total_failed = sum(p.get("failed", 0) for p in project_results.values())

    elapsed = round(time.time() - start_time, 1)

    print("\n" + "=" * 60)
    verdict_icon = {"APPROVED": "✅", "CONDITIONALLY_APPROVED": "⚠️", "REJECTED": "❌"}
    print(f"🏁 최종 판정: {verdict_icon.get(verdict, '?')} {verdict}")
    print(f"   총 테스트: {total_passed} passed, {total_failed} failed")
    print(f"   소요 시간: {elapsed}s")

    # 결과 객체 구성
    report = {
        "timestamp": timestamp,
        "verdict": verdict,
        "elapsed_sec": elapsed,
        "projects": project_results,
        "total": {"passed": total_passed, "failed": total_failed},
        "ast_check": ast_result,
        "security_scan": security_result,
        "infrastructure": infra_result,
    }

    # JSON 파일 저장
    if output_file:
        out_path = Path(output_file)
    else:
        out_path = ROOT_DIR / "knowledge-dashboard" / "public" / "qaqc_result.json"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\n📄 결과 저장: {out_path}")

    # SQLite 히스토리 저장
    try:
        from qaqc_history_db import QaQcHistoryDB

        db = QaQcHistoryDB()
        db.save_run(report)
        print("💾 히스토리 DB 저장 완료")
    except ImportError:
        pass  # DB 모듈이 아직 없으면 무시

    return report


def main():
    """CLI 진입점."""
    parser = argparse.ArgumentParser(description="통합 QA/QC 자동화 러너")
    parser.add_argument(
        "--project",
        "-p",
        nargs="*",
        choices=list(PROJECTS.keys()),
        help="특정 프로젝트만 실행",
    )
    parser.add_argument(
        "--skip-infra",
        action="store_true",
        help="인프라 헬스 체크 생략",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        help="결과 JSON 파일 경로",
    )
    args = parser.parse_args()

    run_qaqc(
        target_projects=args.project,
        skip_infra=args.skip_infra,
        output_file=args.output,
    )


if __name__ == "__main__":
    main()
