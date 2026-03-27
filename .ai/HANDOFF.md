# HANDOFF - AI Context Relay

> See `SESSION_LOG.md` for detailed history and `DECISIONS.md` for settled architecture decisions.

## Last Session

| Field | Value |
|------|------|
| Date | 2026-03-27 |
| Tool | Codex |
| Work | shorts-maker-v2 `script_step.py` coverage uplift with mock-heavy unit tests |

## Current State

- **shorts-maker-v2 script_step coverage uplift completed**:
  - Added focused unit tests for helper logic, prompt building, review scoring, research verification, retry behavior, truncation, and topic-unsuitable handling.
  - Targeted verification: `tests/unit/test_script_step.py` + `tests/unit/test_script_step_i18n.py` => **29 passed, 1 warning**
  - Targeted coverage: `coverage run --source=src/shorts_maker_v2/pipeline -m pytest tests/unit/test_script_step.py tests/unit/test_script_step_i18n.py -q -o addopts=` => `script_step.py` **93%**
  - Safe pattern on this machine: use `coverage run` instead of `pytest-cov` for targeted coverage because duplicate root/project `shorts-maker-v2` directories can trigger import collisions.
- **shorts-maker-v2 pipeline upgrade remains in place**:
  - Pipeline flow: `Planning -> Research -> StructureStep -> Script -> Media -> Scene QC -> Gate3 -> Render -> Gate4 -> Upload-ready copy`
  - `structure_step.py` and scene-QC related changes from the previous session are still the latest production-facing pipeline changes.
- **Shared quality context**:
  - Latest shared QC run on `2026-03-26` remained `CONDITIONALLY_APPROVED`: root passes, blind-to-x hits runner timeout, shorts-maker-v2 has suite-only flaky failures, knowledge-dashboard lint fails.

## Next Priorities

1. Extend the same mock-heavy coverage strategy to `projects/shorts-maker-v2/src/shorts_maker_v2/pipeline/orchestrator.py`
2. T-064: archive `projects/shorts-maker-v2/tests/legacy` out of pytest discovery after confirming current ShortsFactory fallback needs
3. T-057: fix blind-to-x false-negative timeout in `workspace/execution/qaqc_runner.py`
4. T-059: fix `knowledge-dashboard` lint errors
5. T-056: verify next natural Blind-to-X scheduled run

## Notes

- `pytest-cov` can fail on this machine for targeted `shorts-maker-v2` coverage with `ImportError: cannot load module more than once per process`; `coverage run` is the reliable fallback.
- `shorts-maker-v2` full-suite flakiness is still unresolved. Treat isolated passes as encouraging but not as a fix for the order-dependence issue.
- Legacy `tests/legacy/` files still mostly target ShortsFactory/V1 paths rather than the V2 pipeline. They were not moved in this session.
