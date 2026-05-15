from __future__ import annotations

import sys
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

REPO_ROOT = WORKSPACE_ROOT.parent
ROOT_EXECUTION_DIR = REPO_ROOT / "execution"
if str(ROOT_EXECUTION_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_EXECUTION_DIR))
