from __future__ import annotations

import io
import sys

# Windows cp949 콘솔/파이프 인코딩 문제 방지 — subprocess에서도 동일하게 적용
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from shorts_maker_v2.cli import run_cli  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(run_cli())
