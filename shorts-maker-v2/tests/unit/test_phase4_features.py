"""Phase 4 feature tests: caption utilities, SSML, style tracker."""

from __future__ import annotations

import json
from pathlib import Path

from shorts_maker_v2.providers.edge_tts_client import _get_role_prosody
from shorts_maker_v2.render.caption_pillow import auto_font_size, complementary_color
from shorts_maker_v2.utils.style_tracker import StyleTracker

# ─── 4-A: complementary color ──────────────────────────────────────────────


def test_complementary_white_to_black() -> None:
    assert complementary_color("#FFFFFF") == "#000000"


def test_complementary_black_to_white() -> None:
    assert complementary_color("#000000") == "#FFFFFF"


def test_complementary_red_to_cyan() -> None:
    assert complementary_color("#FF0000") == "#00FFFF"


def test_complementary_invalid_returns_white() -> None:
    assert complementary_color("#ZZZ") == "#FFFFFF"


# ─── 4-A: auto_font_size ───────────────────────────────────────────────────


def test_auto_font_size_hook_larger() -> None:
    base = auto_font_size(64, 20, "body")
    hook = auto_font_size(64, 20, "hook")
    assert hook > base


def test_auto_font_size_long_text_smaller() -> None:
    short = auto_font_size(64, 10, "body")
    long_ = auto_font_size(64, 60, "body")
    assert long_ < short


def test_auto_font_size_minimum() -> None:
    """Never goes below 32."""
    assert auto_font_size(10, 100, "body") >= 32


# ─── 4-B: get_role_prosody ──────────────────────────────────────────────────


def test_get_role_prosody_hook() -> None:
    rate, pitch = _get_role_prosody("hook")
    assert rate == "+15%"
    assert pitch == "+8Hz"


def test_get_role_prosody_cta() -> None:
    rate, pitch = _get_role_prosody("cta")
    assert rate == "-10%"
    assert pitch == "+5Hz"


def test_get_role_prosody_body_random() -> None:
    import re

    rate, pitch = _get_role_prosody("body")
    assert re.match(r"^[+-]?\d+%$", rate) is not None
    assert re.match(r"^[+-]?\d+Hz$", pitch) is not None


def test_get_role_prosody_body_base_rate() -> None:
    # 테스트 base_rate = "+10%" 일 때, jitter(±5)가 적용되어 5%~15% 여야 함
    rate, _ = _get_role_prosody("body", base_rate="+10%")
    rate_val = int(rate.replace("%", "").replace("+", ""))
    assert 5 <= rate_val <= 15


# ─── 4-E: StyleTracker ─────────────────────────────────────────────────────


def test_style_tracker_empty_dir(tmp_path: Path) -> None:
    tracker = StyleTracker(tmp_path)
    result = tracker.weighted_pick("hook_pattern", ["A", "B", "C"])
    assert result in {"A", "B", "C"}


def test_style_tracker_reads_manifests(tmp_path: Path) -> None:
    for i in range(10):
        manifest = {
            "status": "success",
            "ab_variant": {"hook_pattern": "A" if i < 8 else "B"},
        }
        (tmp_path / f"job{i}_manifest.json").write_text(
            json.dumps(manifest),
            encoding="utf-8",
        )
    tracker = StyleTracker(tmp_path)
    counts = tracker.get_success_counts("hook_pattern")
    assert counts["A"] == 8
    assert counts["B"] == 2


def test_style_tracker_weighted_pick_favors_winner(tmp_path: Path) -> None:
    for i in range(20):
        manifest = {
            "status": "success",
            "ab_variant": {"hook_pattern": "winner" if i < 18 else "loser"},
        }
        (tmp_path / f"job{i}_manifest.json").write_text(
            json.dumps(manifest),
            encoding="utf-8",
        )
    tracker = StyleTracker(tmp_path)
    # Run 100 picks — winner should be picked significantly more
    picks = [tracker.weighted_pick("hook_pattern", ["winner", "loser"]) for _ in range(100)]
    assert picks.count("winner") > picks.count("loser")
