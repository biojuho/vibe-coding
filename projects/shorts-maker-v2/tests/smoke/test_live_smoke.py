from __future__ import annotations

import os
from pathlib import Path

import pytest

from shorts_maker_v2.cli import run_cli

pytestmark = pytest.mark.smoke


def test_live_smoke_single_run() -> None:
    if os.getenv("SHORTS_LIVE_SMOKE") != "1":
        pytest.skip("Enable SHORTS_LIVE_SMOKE=1 for live API smoke test.")
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY is required.")
    if not os.getenv("GEMINI_API_KEY"):
        pytest.skip("GEMINI_API_KEY is required.")

    root = Path(__file__).resolve().parents[2]
    exit_code = run_cli(
        [
            "run",
            "--topic",
            "블랙홀에 대한 과학 상식 5가지",
            "--config",
            str(root / "config.yaml"),
            "--out",
            "smoke_test.mp4",
        ]
    )
    assert exit_code == 0
