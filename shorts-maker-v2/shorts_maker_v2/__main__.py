import io
import sys
from pathlib import Path

# Windows cp949 인코딩 문제 방지
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf_8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# execution/ 모듈이 있는 루트 경로를 sys.path에 추가
_VIBE_ROOT = Path(__file__).resolve().parents[2]
if str(_VIBE_ROOT) not in sys.path:
    sys.path.insert(0, str(_VIBE_ROOT))

from shorts_maker_v2.cli import run_cli


if __name__ == "__main__":
    raise SystemExit(run_cli())

