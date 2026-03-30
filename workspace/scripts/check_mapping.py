"""Directive ↔ Execution 매핑 검증기.

directives/INDEX.md의 매핑을 파싱하고, 실제 파일 존재 여부를 검증합니다.

Usage:
    python workspace/scripts/check_mapping.py
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIRECTIVES_DIR = ROOT / "directives"
EXECUTION_DIR = ROOT / "execution"
INDEX_FILE = DIRECTIVES_DIR / "INDEX.md"


def parse_index() -> tuple[dict[str, list[str]], dict[str, str]]:
    """INDEX.md를 파싱하여 매핑된 SOP, 미매핑 스크립트를 반환."""
    text = INDEX_FILE.read_text(encoding="utf-8")

    # SOP -> scripts 매핑
    sop_map: dict[str, list[str]] = {}
    # 미매핑 스크립트
    unmapped: dict[str, str] = {}

    in_sop_table = False
    in_unmapped_table = False

    for line in text.splitlines():
        line = line.strip()

        if "SOP → Execution" in line:
            in_sop_table = True
            in_unmapped_table = False
            continue
        if "매핑 없는 Execution" in line:
            in_sop_table = False
            in_unmapped_table = True
            continue
        if line.startswith("---"):
            in_sop_table = False
            in_unmapped_table = False
            continue

        if not line.startswith("|") or line.startswith("|--"):
            continue

        cells = [c.strip() for c in line.split("|")[1:-1]]
        if len(cells) < 2:
            continue

        if in_sop_table and cells[0] and not cells[0].startswith("Directive"):
            sop_name = cells[0]
            scripts_raw = cells[1]
            scripts = [s.strip() for s in re.split(r"[,;→]", scripts_raw) if s.strip() and s.strip().endswith(".py")]
            sop_map[sop_name] = scripts

        if in_unmapped_table and cells[0] and not cells[0].startswith("Script"):
            unmapped[cells[0]] = cells[1] if len(cells) > 1 else ""

    return sop_map, unmapped


def check() -> int:
    """Run all checks, return exit code (0=ok, 1=issues found)."""
    sop_map, unmapped = parse_index()
    issues: list[str] = []

    # 1. SOP 파일 존재 확인
    for sop in sop_map:
        if not (DIRECTIVES_DIR / sop).exists():
            issues.append(f"[SOP MISSING] {sop} listed in INDEX but not found")

    # 2. 매핑된 스크립트 파일 존재 확인
    all_mapped_scripts: set[str] = set()
    for sop, scripts in sop_map.items():
        for script in scripts:
            all_mapped_scripts.add(script)
            # execution/ 또는 프로젝트 루트 상대경로로 체크
            candidates = [
                EXECUTION_DIR / script,
                ROOT / script,  # scripts/key_rotation_checker.py 등
            ]
            if not any(c.exists() for c in candidates):
                issues.append(f"[SCRIPT MISSING] {script} (mapped by {sop})")

    # 3. 미매핑 스크립트 존재 확인
    for script in unmapped:
        all_mapped_scripts.add(script)
        if not (EXECUTION_DIR / script).exists():
            issues.append(f"[UNMAPPED MISSING] {script} listed as unmapped but not found")

    # 4. 실제 execution/*.py 중 INDEX에 없는 것 (고아 스크립트)
    actual_scripts = {p.name for p in EXECUTION_DIR.glob("*.py") if not p.name.startswith("__")}
    orphans = actual_scripts - all_mapped_scripts
    for orphan in sorted(orphans):
        issues.append(f"[ORPHAN] {orphan} exists in execution/ but not in INDEX.md")

    # 5. 실제 directives/*.md 중 INDEX에 없는 것 (고아 SOP)
    actual_sops = {p.name for p in DIRECTIVES_DIR.glob("*.md") if p.name != "INDEX.md" and not p.name.startswith("_")}
    indexed_sops = set(sop_map.keys())
    orphan_sops = actual_sops - indexed_sops
    for orphan in sorted(orphan_sops):
        issues.append(f"[ORPHAN SOP] {orphan} exists in directives/ but not in INDEX.md")

    # Report
    print(f"Checked {len(sop_map)} SOP mappings, {len(unmapped)} unmapped scripts")
    print(f"Actual: {len(actual_scripts)} scripts, {len(actual_sops)} SOPs")

    if issues:
        print(f"\n{len(issues)} issue(s) found:\n")
        for issue in issues:
            print(f"  {issue}")
        return 1
    else:
        print("\nAll mappings valid.")
        return 0


if __name__ == "__main__":
    sys.exit(check())
