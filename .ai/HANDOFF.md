# HANDOFF - AI Context Relay

> See `SESSION_LOG.md` for detailed history and `DECISIONS.md` for settled architecture decisions.

## Last Session

| Field | Value |
|------|------|
| Date | 2026-03-28 |
| Tool | Codex |
| Work | Implemented the code-generation Self-Reflection evaluator loop (`T-071`) plus structured reviewer outputs and deterministic security scoring (`T-072`) in `workspace/execution/graph_engine.py` and `workspace/execution/workers.py`, with targeted verification green. |

## Current State

- **shorts-maker-v2 core pipeline coverage uplift is now complete for the four main hotspots**:
  - `script_step.py`: targeted verification `tests/unit/test_script_step.py` + `tests/unit/test_script_step_i18n.py` => **29 passed, 1 warning**; targeted coverage **93%**
  - `orchestrator.py`: targeted verification `tests/unit/test_orchestrator_unit.py` + `tests/integration/test_orchestrator_manifest.py` => **38 passed, 1 warning**; targeted coverage **97%**
  - `render_step.py`: targeted verification `tests/unit/test_render_step.py` + `tests/unit/test_render_step_phase5.py` + `tests/unit/test_render_quality_controls.py` + `tests/unit/test_render_utils.py` => **141 passed, 1 warning**; targeted coverage **87%**
  - `media_step.py`: targeted verification `tests/unit/test_parallel_media.py` + `tests/unit/test_media_step_branches.py` + `tests/integration/test_media_fallback.py` => **28 passed, 1 warning**; targeted coverage **90%**
- **Shared quality context**:
  - Latest shared QC run on `2026-03-28` is **`APPROVED`**
  - Totals: **2660 passed, 0 failed, 0 errors, 29 skipped**
  - Project breakdown:
    - `blind-to-x`: **551 passed, 0 failed, 16 skipped**
    - `shorts-maker-v2`: **1075 passed, 0 failed, 12 skipped**
    - `root`: **1034 passed, 0 failed, 1 skipped**
  - `workspace/execution/qaqc_runner.py` splits `blind-to-x` into unit/integration runs and uses a 900s budget, removing the prior false timeout
- **Maintained dashboard verification on `2026-03-28`**:
  - `knowledge-dashboard`: `npm run lint` and `npm run build` both pass after fixing the conditional `useMemo` path in `ActivityTimeline.tsx` and replacing the empty `InputProps` interface with a type alias
  - `hanwoo-dashboard`: `npm run build` passes again after reinstalling with `npm install --legacy-peer-deps` and bumping `lucide-react` to a React 19-compatible release; `npm run lint` still reports one `@next/next/no-page-custom-font` warning in `src/app/layout.js`
- **Graph-engine evaluator upgrade on `2026-03-28`**:
  - `workspace/execution/workers.py` now returns structured reviewer metadata with optional Pydantic validation, a deterministic security score, and an explicit self-reflection brief
  - `workspace/execution/graph_engine.py` now feeds evaluator reflection back into the next coding attempt and weights security in the final confidence score instead of averaging all historical worker results
  - Targeted verification: `venv\Scripts\python.exe -m ruff check workspace\execution\graph_engine.py workspace\execution\workers.py workspace\tests\test_graph_engine.py` => **clean**
  - Targeted verification: `venv\Scripts\python.exe -m pytest workspace\tests\test_graph_engine.py -q -o addopts=` => **34 passed**

## Next Priorities

1. T-069: broaden `src/shorts_maker_v2` overall coverage by folding in more existing provider/render suites, then choose the next non-pipeline hotspot
2. T-058: investigate `shorts-maker-v2` full-suite order-dependent failure
3. T-056: verify the next Blind-to-X scheduled run creates `scheduled_*.log` and reports `LastTaskResult=0`

## Notes

- `pytest-cov` can fail on this machine for targeted `shorts-maker-v2` coverage with `ImportError: cannot load module more than once per process`; `coverage run` is the reliable fallback.
- On this Windows machine, `coverage report` against a direct source path can sometimes show `0%` unexpectedly for `render_step.py`; `coverage report -m --include="*render_step.py"` is the reliable report pattern when that happens.
- `shorts-maker-v2` full-suite flakiness is still unresolved. Treat isolated passes as encouraging but not as a fix for the order-dependence issue.
- `blind-to-x` draft-generation mocks in tests now need the current output contract: `twitter` responses should include `reply` and `creator_take` tags when validated via `generate_drafts()`.
- `hanwoo-dashboard` currently installs cleanly only with `npm install --legacy-peer-deps`; the remaining blocker is peer-range drift (`next-auth@5.0.0-beta.25` vs Next 16, plus Toss type-package TypeScript peer warnings).
- `npm install --legacy-peer-deps` in `projects/hanwoo-dashboard` reported 15 vulnerabilities (8 moderate, 7 high); no audit remediation was done in this session.
- `workspace/execution/workers.py` treats Pydantic as optional. If it is unavailable, reviewer payloads still normalize into the same structured dict shape before scoring.
- The new evaluator only scores the latest coder/tester/reviewer cycle; this avoids stale low-confidence attempts polluting later iterations and is important if future tests exercise multi-iteration recovery.
