from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
VIBE_ROOT = ROOT.parent  # execution/ 모듈 경로 (blind-to-x 상위)

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(VIBE_ROOT) not in sys.path:
    sys.path.insert(0, str(VIBE_ROOT))

