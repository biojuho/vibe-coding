from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
VIBE_ROOT = ROOT.parent  # execution/ 모듈 경로 (blind-to-x 상위)

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(VIBE_ROOT) not in sys.path:
    sys.path.insert(0, str(VIBE_ROOT))

# ── imageio_ffmpeg 번들 ffmpeg를 PATH/환경변수에 등록 ──
# moviepy 등이 import 시점에 ffmpeg를 탐색하므로 conftest 최상위에서 설정
try:
    import imageio_ffmpeg

    _ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    if _ffmpeg_exe:
        os.environ.setdefault("IMAGEIO_FFMPEG_EXE", _ffmpeg_exe)
        os.environ.setdefault("FFMPEG_BINARY", _ffmpeg_exe)
        _ffmpeg_dir = str(Path(_ffmpeg_exe).parent)
        if _ffmpeg_dir not in os.environ.get("PATH", ""):
            os.environ["PATH"] = _ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")
except Exception:
    pass
