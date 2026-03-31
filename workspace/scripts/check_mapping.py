"""Directive ↔ Execution mapping validator.

Parses `workspace/directives/INDEX.md` through the shared governance check logic
and exits non-zero when mapping drift is detected.

Usage:
    python workspace/scripts/check_mapping.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from execution.governance_checks import audit_directive_mapping  # noqa: E402


def check() -> int:
    result = audit_directive_mapping()
    print(result["detail"])

    issues = list(result.get("issues", []))
    if issues:
        print(f"\n{len(issues)} issue(s) found:\n")
        for issue in issues:
            print(f"  {issue}")
        return 1

    print("\nAll mappings valid.")
    return 0


if __name__ == "__main__":
    sys.exit(check())
