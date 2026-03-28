# TASKS.md

## TODO

- [ ] T-082 Push the next output-quality pass on `render/caption_pillow.py` plus any remaining thumbnail helper branches. Owner: Codex
- [ ] Decide whether archived ShortsFactory compatibility tests should live in a separate optional CI/manual lane. Owner: TBD
- [ ] Remove or ignore the leftover `tests/legacy/__pycache__/` directory for tree cleanliness. Owner: TBD

## IN_PROGRESS

- [ ] None

## DONE

- [x] T-081 Extend `thumbnail_step.py` live-path hardening with Canva OAuth refresh coverage, video-frame extraction cleanup coverage, and fail-fast HTTP download handling (2026-03-29, Codex)
- [x] T-080 Harden `thumbnail_step.py` temp-artifact cleanup and long-title wrapping (2026-03-29, Codex)
- [x] T-072 Commit expanded V2 pipeline coverage tests for `script_step`, `orchestrator`, `render_step`, and `media_step` (`95b3421`) after validating `218 passed, 1 warning` (2026-03-27, Codex)
- [x] T-071 Remove `--cov=ShortsFactory` from default pytest coverage and archive remaining direct ShortsFactory tests from `tests/unit/` and `tests/integration/` (2026-03-27, Codex)
- [x] T-070 Archive `tests/legacy` V1 tests into `archive/tests_legacy_v1` and exclude them from default collection with `testpaths = tests` (2026-03-27, Codex)
- [x] T-069 Broaden overall `src/shorts_maker_v2` coverage using existing provider/render/utils suites; verified `82%` total coverage (2026-03-27, Codex)
- [x] T-068 Raise `pipeline/media_step.py` targeted coverage to `90%` with branch-heavy mock tests (2026-03-27, Codex)
- [x] T-067 Re-measure aggregate coverage for `src/shorts_maker_v2/pipeline`; verified `87%` total pipeline coverage (2026-03-27, Codex)
- [x] T-066 Raise `pipeline/render_step.py` targeted coverage to `88%` (2026-03-27, Codex)
- [x] T-065 Raise `pipeline/orchestrator.py` targeted coverage to `97%` (2026-03-27, Codex)
- [x] T-063 Raise `pipeline/script_step.py` targeted coverage to `93%` (2026-03-27, Codex)
