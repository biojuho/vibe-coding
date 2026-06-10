from __future__ import annotations

import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[1]
workspace_path = str(WORKSPACE)
if workspace_path not in sys.path:
    sys.path.insert(0, workspace_path)

__all__ = ["WORKSPACE"]
