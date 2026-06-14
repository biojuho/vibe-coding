from __future__ import annotations

from pathlib import Path

import pytest

from execution import locked_temp_cleanup


def test_find_candidates_is_limited_to_known_temp_dirs(tmp_path: Path) -> None:
    (tmp_path / ".tmp" / "pytest-root").mkdir(parents=True)
    (tmp_path / ".tmp" / "project-qc-temp").mkdir()
    (tmp_path / ".tmp" / "keep").mkdir()
    btx_tmp = tmp_path / "projects" / "blind-to-x" / ".tmp"
    btx_tmp.mkdir(parents=True)
    (btx_tmp / "pytest-btx").mkdir()
    (btx_tmp / "tmpabc").mkdir()
    (btx_tmp / "embedding_cache.db").write_text("{}", encoding="utf-8")
    shorts_tmp = tmp_path / "projects" / "shorts-maker-v2" / ".tmp"
    shorts_tmp.mkdir(parents=True)
    (shorts_tmp / "pytest-shorts").mkdir()
    (tmp_path / "release-evidence" / "tmp-keep").mkdir(parents=True)

    paths = {item["path"] for item in locked_temp_cleanup.find_candidates(tmp_path)}

    assert paths == {
        ".tmp/project-qc-temp",
        ".tmp/pytest-root",
        "projects/blind-to-x/.tmp/pytest-btx",
        "projects/blind-to-x/.tmp/tmpabc",
        "projects/shorts-maker-v2/.tmp/pytest-shorts",
    }


def test_normalize_under_root_rejects_outside_path(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside"

    with pytest.raises(ValueError, match="outside workspace"):
        locked_temp_cleanup.normalize_under_root(outside, tmp_path)
