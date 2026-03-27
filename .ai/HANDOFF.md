# HANDOFF - AI Context Relay

> See `SESSION_LOG.md` for detailed history and `DECISIONS.md` for settled architecture decisions.

## Last Session

| Field | Value |
|------|------|
| Date | 2026-03-27 |
| Tool | Codex |
| Work | Raised `projects/shorts-maker-v2` targeted coverage for `orchestrator.py`, `render_step.py`, and `media_step.py`, then re-measured package-wide coverage |

## Current State

- **shorts-maker-v2 core pipeline coverage uplift is now complete for the four main hotspots**:
  - `script_step.py`: targeted verification `tests/unit/test_script_step.py` + `tests/unit/test_script_step_i18n.py` => **29 passed, 1 warning**; targeted coverage **93%**
  - `orchestrator.py`: targeted verification `tests/unit/test_orchestrator_unit.py` + `tests/integration/test_orchestrator_manifest.py` => **38 passed, 1 warning**; targeted coverage **97%**
  - `render_step.py`: targeted verification `tests/unit/test_render_step.py` + `tests/unit/test_render_step_phase5.py` + `tests/unit/test_render_quality_controls.py` + `tests/unit/test_render_utils.py` => **141 passed, 1 warning**; targeted coverage **87%**
  - `media_step.py`: targeted verification `tests/unit/test_parallel_media.py` + `tests/unit/test_media_step_branches.py` + `tests/integration/test_media_fallback.py` => **28 passed, 1 warning**; targeted coverage **90%**
- **Measured coverage milestones**:
  - Pipeline-focused aggregate suite now reports `projects/shorts-maker-v2/src/shorts_maker_v2/pipeline` at **87%** (`411 passed, 1 warning`)
  - The same suite reports `projects/shorts-maker-v2/src/shorts_maker_v2` overall at **57%**, which clears the interim **45%** target but not the long-term **80%** package-wide target
- **shorts-maker-v2 pipeline upgrade remains in place**:
  - Pipeline flow: `Planning -> Research -> StructureStep -> Script -> Media -> Scene QC -> Gate3 -> Render -> Gate4 -> Upload-ready copy`
  - `structure_step.py` and scene-QC related changes from the previous session are still the latest production-facing pipeline changes.
- **Shared quality context**:
  - Latest shared QC run on `2026-03-26` remained `CONDITIONALLY_APPROVED`: root passes, blind-to-x hits runner timeout, shorts-maker-v2 has suite-only flaky failures, knowledge-dashboard lint fails.

## Next Priorities

1. T-069: broaden `src/shorts_maker_v2` overall coverage by folding in more existing provider/render suites, then choose the next non-pipeline hotspot
2. T-064: archive `projects/shorts-maker-v2/tests/legacy` out of pytest discovery
3. T-058: investigate `shorts-maker-v2` full-suite order-dependent failure
4. T-057: fix blind-to-x false-negative timeout in `workspace/execution/qaqc_runner.py`
5. T-059: fix `knowledge-dashboard` lint errors

## Notes

- `pytest-cov` can fail on this machine for targeted `shorts-maker-v2` coverage with `ImportError: cannot load module more than once per process`; `coverage run` is the reliable fallback.
- On this Windows machine, `coverage report` against a direct source path can sometimes show `0%` unexpectedly for `render_step.py`; `coverage report -m --include="*render_step.py"` is the reliable report pattern when that happens.
- `shorts-maker-v2` full-suite flakiness is still unresolved. Treat isolated passes as encouraging but not as a fix for the order-dependence issue.
- Legacy `tests/legacy/` files still mostly target ShortsFactory/V1 paths rather than the V2 pipeline. They were not moved in this session.
