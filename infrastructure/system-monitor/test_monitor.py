import json
import sys

from server import get_system_stats


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def main() -> int:
    try:
        stats = get_system_stats()
        print("[PASS] System Monitor Test Passed!")
        print(json.dumps(stats, indent=2, ensure_ascii=False))
        return 0
    except Exception as exc:
        print(f"[FAIL] Test Failed: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
