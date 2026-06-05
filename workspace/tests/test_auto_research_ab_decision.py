"""Unit tests for the auto-research A/B decision helper."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / ".agents" / "skills" / "auto-research" / "scripts" / "ab_decision.py"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


ab_decision = _load_module("ab_decision_for_test", SCRIPT_PATH)


def _manifest() -> dict[str, object]:
    return {
        "baseline": {"metrics": {"resilience": 0}},
        "candidate": {"metrics": {"resilience": 1}, "gates": {"tests": True}},
        "directions": {"resilience": "higher"},
        "required_gates": ["tests"],
        "min_delta": 0.1,
    }


def test_load_json_accepts_utf8_bom_manifest(tmp_path: Path) -> None:
    path = tmp_path / "ab-manifest.json"
    path.write_text(json.dumps(_manifest()), encoding="utf-8-sig")

    result = ab_decision.decide(ab_decision._load_json(path))

    assert result["decision"] == "adopt_candidate"
    assert result["failed_gates"] == []
