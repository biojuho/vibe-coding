# HANDOFF - AI Context Relay

> See `SESSION_LOG.md` for detailed history and `DECISIONS.md` for settled architecture decisions.

## Last Session

| Field | Value |
|------|------|
| Date | 2026-03-28 |
| Tool | Codex |
| Work | Hardened repeated `shorts-maker-v2` MoviePy golden-render runs on Windows by changing `MoviePyRenderer.write()` to use per-output temp audio files, after reproducing the historical flake as a `PermissionError` in `test_golden_render_moviepy`. |

## Current State

- **shorts-maker-v2 core pipeline coverage uplift is now complete for the four main hotspots**:
  - `script_step.py`: targeted verification `tests/unit/test_script_step.py` + `tests/unit/test_script_step_i18n.py` => **29 passed, 1 warning**; targeted coverage **93%**
  - `orchestrator.py`: targeted verification `tests/unit/test_orchestrator_unit.py` + `tests/integration/test_orchestrator_manifest.py` => **38 passed, 1 warning**; targeted coverage **97%**
  - `render_step.py`: targeted verification `tests/unit/test_render_step.py` + `tests/unit/test_render_step_phase5.py` + `tests/unit/test_render_quality_controls.py` + `tests/unit/test_render_utils.py` => **141 passed, 1 warning**; targeted coverage **87%**
  - `media_step.py`: targeted verification `tests/unit/test_parallel_media.py` + `tests/unit/test_media_step_branches.py` + `tests/integration/test_media_fallback.py` => **28 passed, 1 warning**; targeted coverage **90%**
- **shorts-maker-v2 package-wide coverage milestone was exceeded on `2026-03-28`**:
  - Full verification: `venv\Scripts\python.exe -m coverage run --source=src/shorts_maker_v2 -m pytest tests\unit tests\integration -q -o addopts=` => **1144 passed, 12 skipped, 1 warning**
  - Full package report: `coverage report -m` => `src/shorts_maker_v2` **87% total coverage** (`8046 stmts / 1016 miss`)
  - Newly uplifted modules: `google_music_client.py` **99%**, `pexels_client.py` **95%**, `unsplash_client.py` **100%**, `video_renderer.py` **100%**, `hwaccel.py` **96%**
  - The next low non-pipeline cluster after this milestone is `style_tracker.py` **54%** plus optional-provider clients `chatterbox_client.py` **49%** and `cosyvoice_client.py` **53%**
- **shorts-maker-v2 repeatability sweep on `2026-03-28`**:
  - `tests/integration/test_golden_render.py::test_golden_render_moviepy` failed once after 4 clean isolated reruns with `PermissionError: [WinError 32]` while MoviePy tried to delete `golden_moviepyTEMP_MPY_wvf_snd.mp4`
  - Root cause: `MoviePyRenderer.write()` let MoviePy create a fixed-name temp audio file in the current working directory, so repeated Windows runs could collide with a still-open handle
  - Fix: `projects/shorts-maker-v2/src/shorts_maker_v2/render/video_renderer.py` now passes a per-output unique `temp_audiofile` path and creates the output directory first
  - Regression checks after the fix: `tests/unit/test_video_renderer.py` => **56 passed**, `test_golden_render_moviepy` repeated **5/5 passed**, full `tests/unit + tests/integration` => **1144 passed, 12 skipped, 1 warning**
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

1. T-056: verify the next Blind-to-X scheduled run creates `scheduled_*.log` and reports `LastTaskResult=0`
2. T-075: raise the next non-pipeline `shorts-maker-v2` coverage cluster (`style_tracker`, `chatterbox_client`, `cosyvoice_client`)
3. Re-run shared QC after the next substantial `shorts-maker-v2` or dashboard change to ensure the new MoviePy temp-audio behavior stays green in the broader workspace runner

## Notes

- `pytest-cov` can fail on this machine for targeted `shorts-maker-v2` coverage with `ImportError: cannot load module more than once per process`; `coverage run` is the reliable fallback.
- On this Windows machine, `coverage report` against a direct source path can sometimes show `0%` unexpectedly for `render_step.py`; `coverage report -m --include="*render_step.py"` is the reliable report pattern when that happens.
- `shorts-maker-v2` repeatability is materially better after the `MoviePyRenderer.write()` temp-audio fix: the previously flaky `test_golden_render_moviepy` now passes 5 isolated reruns, and the full suite still passes end-to-end.
- `blind-to-x` draft-generation mocks in tests now need the current output contract: `twitter` responses should include `reply` and `creator_take` tags when validated via `generate_drafts()`.
- `hanwoo-dashboard` currently installs cleanly only with `npm install --legacy-peer-deps`; the remaining blocker is peer-range drift (`next-auth@5.0.0-beta.25` vs Next 16, plus Toss type-package TypeScript peer warnings).
- `npm install --legacy-peer-deps` in `projects/hanwoo-dashboard` reported 15 vulnerabilities (8 moderate, 7 high); no audit remediation was done in this session.
- `workspace/execution/workers.py` treats Pydantic as optional. If it is unavailable, reviewer payloads still normalize into the same structured dict shape before scoring.
- The new evaluator only scores the latest coder/tester/reviewer cycle; this avoids stale low-confidence attempts polluting later iterations and is important if future tests exercise multi-iteration recovery.
