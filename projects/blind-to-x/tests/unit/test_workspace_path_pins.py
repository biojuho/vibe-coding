"""Pin tests for cross-directory imports from blind-to-x into workspace/execution.

Background: multiple modules in `projects/blind-to-x/` load shared scripts from
`workspace/execution/` via `pathlib.Path(__file__).parents[N]`. The N must be
chosen so the result is the repo root — otherwise `_target.exists()` is False
and the dynamic import silently fails (`try/except Exception: return ...`).

This dead-code pattern was found and fixed in 3 places (2026-05-12):
  - `pipeline/content_intelligence/boosting.py`    (parents[4])
  - `pipeline/notion/_upload.py`                    (parents[4])
  - `pipeline/notebooklm_enricher.py`               (parents[3])

These tests pin each path so the next refactor that moves/renames a file fails
loudly instead of regressing into silent dead code.
"""

from __future__ import annotations

import pathlib


def _repo_root_from(file_path: str) -> pathlib.Path:
    """Walk up from a project file until we reach a directory that contains both
    `workspace/` and `projects/` siblings — that's the repo root by definition."""
    p = pathlib.Path(file_path).resolve()
    for ancestor in p.parents:
        if (ancestor / "workspace").is_dir() and (ancestor / "projects").is_dir():
            return ancestor
    raise AssertionError(f"could not locate repo root above {p}")


def test_boosting_path_pin():
    """boosting.py uses parents[4] → workspace/execution/llm_client.py."""
    from pipeline.content_intelligence import boosting

    boost_file = pathlib.Path(boosting.__file__).resolve()
    repo_root = boost_file.parents[4]
    expected_repo = _repo_root_from(boosting.__file__)
    assert repo_root == expected_repo, f"boosting.py parents[4] = {repo_root}, expected repo root {expected_repo}"
    target = repo_root / "workspace" / "execution" / "llm_client.py"
    assert target.exists(), f"LLMClient not found at {target}"


def test_upload_uploader_path_pin():
    """`pipeline/notion/_upload.py` references parents[4]/workspace/execution/notion_article_uploader.py."""
    from pipeline.notion import _upload as upload_mod

    upload_file = pathlib.Path(upload_mod.__file__).resolve()
    repo_root = upload_file.parents[4]
    expected_repo = _repo_root_from(upload_mod.__file__)
    assert repo_root == expected_repo
    target = repo_root / "workspace" / "execution" / "notion_article_uploader.py"
    assert target.exists(), f"notion_article_uploader.py not found at {target}"


def test_notebooklm_enricher_path_pin():
    """notebooklm_enricher.py uses parents[3] (one less depth than others) — verify both targets."""
    from pipeline import notebooklm_enricher as nlm

    # The module computes _REPO_ROOT itself; assert it matches actual repo root
    assert nlm._REPO_ROOT == _repo_root_from(nlm.__file__), f"notebooklm_enricher._REPO_ROOT = {nlm._REPO_ROOT}"
    # Both shared scripts must exist at the computed location
    assert nlm._CONTENT_WRITER_PATH.exists(), f"content_writer.py not found at {nlm._CONTENT_WRITER_PATH}"
    assert nlm._GDRIVE_EXTRACTOR_PATH.exists(), f"gdrive_pdf_extractor.py not found at {nlm._GDRIVE_EXTRACTOR_PATH}"


def test_all_pins_agree_on_repo_root():
    """All three modules — regardless of parents[N] — must arrive at the same repo root."""
    from pipeline import notebooklm_enricher as nlm
    from pipeline.content_intelligence import boosting
    from pipeline.notion import _upload as upload_mod

    boost_root = pathlib.Path(boosting.__file__).resolve().parents[4]
    upload_root = pathlib.Path(upload_mod.__file__).resolve().parents[4]
    nlm_root = nlm._REPO_ROOT

    assert boost_root == upload_root == nlm_root, (
        f"path pins disagree: boost={boost_root}, upload={upload_root}, nlm={nlm_root}"
    )
