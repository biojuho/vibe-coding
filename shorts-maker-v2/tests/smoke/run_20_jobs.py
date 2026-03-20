from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from shorts_maker_v2.cli import run_cli  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Run 20-job smoke benchmark")
    parser.add_argument("--config", type=str, default="config.yaml")
    parser.add_argument("--topic", type=str, required=True)
    parser.add_argument("--iterations", type=int, default=20)
    args = parser.parse_args()

    config_path = Path(args.config).resolve()
    success = 0
    for idx in range(1, args.iterations + 1):
        out_name = f"smoke_{idx:02d}.mp4"
        code = run_cli(
            [
                "run",
                "--topic",
                args.topic,
                "--config",
                str(config_path),
                "--out",
                out_name,
            ]
        )
        if code == 0:
            success += 1
        print(f"[{idx:02d}/{args.iterations:02d}] exit_code={code}")

    ratio = success / max(args.iterations, 1)
    print(f"success={success}/{args.iterations} ratio={ratio:.2%}")
    if ratio >= 0.90:
        print("PASS: success ratio >= 90%")
        return 0
    print("FAIL: success ratio < 90%")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
