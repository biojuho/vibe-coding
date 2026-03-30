"""pytest conftest: 프로젝트 루트를 sys.path에 추가해 pipeline 등 패키지를 임포트 가능하게 합니다."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
