# HANDOFF.md

## Current Addendum (2026-06-11 / Codex autonomous debug loop)

- **Refactor continuation (T-2374, 2026-06-12 01:54 KST)**:
  - Continued the shared rendering-helper refactor loop after T-2373.
  - Converted `history_timeline.py` and `psychology_quiz.py` to `tools/_rendering_helpers.py` using the same dual-import pattern.
  - Project-local `.ai/TOOL_MATRIX.md` was missing during rehydrate; used available HANDOFF/TASKS/CONTEXT/DECISIONS plus `session_orient.py --json`.
- **T-2374 verification**:
  - Loop 22: `test_tool_pillow_deprecations.py` baseline and focused -> `9 passed`; standalone `tools\history_timeline.py --help` passed; Ruff and diff-check passed.
  - Loop 23: `test_tool_pillow_deprecations.py` baseline and focused -> `9 passed`; standalone `tools\psychology_quiz.py --help` passed; Ruff and diff-check passed.
  - Project QC after the final loop: `python execution/project_qc_runner.py --project shorts-maker-v2 --json` -> passed (`1655 passed, 12 skipped, 1 warning`; lint passed).
- **Refactor next-loop note**:
  - Continue one warning-as-error-covered generated tool at a time. Good next candidates are `psychology_shorts.py` or `psychology_quote.py`.

- **Refactor continuation (T-2373, 2026-06-12 01:21 KST)**:
  - Continued the shared rendering-helper refactor loop after T-2372.
  - Converted `health_mental_message.py` and `history_mystery.py` to `tools/_rendering_helpers.py` using the same dual-import pattern that preserves both `spec_from_file_location` tests and standalone script usage.
  - Kept transient resize/crop `Image.fromarray(...)` calls local where they are not final image materialization helpers.
- **T-2373 verification**:
  - Loop 20: `test_tool_pillow_deprecations.py` baseline and focused -> `9 passed`; standalone `tools\health_mental_message.py` printed expected `--demo` guidance; Ruff and diff-check passed.
  - Loop 21: `test_tool_pillow_deprecations.py` baseline and focused -> `9 passed`; standalone `tools\history_mystery.py --help` passed; Ruff and diff-check passed.
  - Project QC after the final loop: `python execution/project_qc_runner.py --project shorts-maker-v2 --json` -> passed (`1655 passed, 12 skipped, 1 warning`; lint passed).
- **Refactor next-loop note**:
  - Continue one generated tool at a time. Good next candidates are `history_timeline.py` or `psychology_quiz.py`, already covered by `test_tool_pillow_deprecations.py`.

- **Refactor continuation (T-2372, 2026-06-12 00:55 KST)**:
  - Continued the behavior-preserving refactor loop beyond the Pillow mode sweep into font/rendering helper consolidation.
  - Added `tools/_rendering_helpers.py` with shared array-to-image and font lookup/loading helpers.
  - Converted one file at a time with focused baselines and standalone script smoke checks: `space_scale.py`, `space_fact_bomb.py`, `health_do_vs_dont.py`, and `health_medical_study.py`.
  - Also extracted file-local font helpers in `history_fact_shorts.py` for both `HistoryFactGenerator` and `HistoryCountdownGenerator` without changing render behavior.
- **T-2372 verification**:
  - Focused checks passed per loop: `test_history_fact_shorts.py` -> `8 passed`; `test_space_scale.py + test_tool_pillow_deprecations.py` -> `12 passed`; `test_tool_pillow_deprecations.py` -> `9 passed`.
  - Standalone script smoke passed for `tools\space_scale.py`, `tools\space_fact_bomb.py`, `tools\health_do_vs_dont.py`, and `tools\health_medical_study.py` (all printed the expected `--demo` guidance).
  - Project QC after the final loop: `python execution/project_qc_runner.py --project shorts-maker-v2 --json` -> passed (`1655 passed, 12 skipped, 1 warning`; lint passed).
- **Refactor next-loop note**:
  - Next safe continuation is another single generated tool already covered by warning-as-error render tests, likely `health_mental_message.py` or `history_mystery.py`, converting it to `tools/_rendering_helpers.py` with the same dual-import pattern and standalone smoke.

- **Refactor continuation (T-2371, 2026-06-11 23:15 KST)**:
  - Continued the user-approved behavior-preserving refactor loop after the prior Pillow mode-argument sweep was green.
  - Extracted explicit RGB/RGBA array-to-image helper functions in generated render tools so final image materialization is named and consistent: `history_mystery.py`, `space_fact_bomb.py`, `health_do_vs_dont.py`, `health_medical_study.py`, `health_mental_message.py`, `space_scale.py`, and follow-up cleanup in `history_fact_shorts.py`.
  - Extended `tests/unit/test_tool_pillow_deprecations.py` from 7 to 9 renderer cases by adding `health_mental_message` and a dedicated `space_scale` demo render guard; extracted `_assert_rgb_frame`.
  - Strengthened `tests/unit/test_history_fact_shorts.py` so countdown renders also run under `DeprecationWarning` as error.
- **T-2371 verification**:
  - Loop focused checks passed: `test_tool_pillow_deprecations.py` -> `9 passed`; `test_history_fact_shorts.py` -> `8 passed`; targeted Ruff checks passed; targeted `git diff --check` passed.
  - Project QC after the final loop: `python execution/project_qc_runner.py --project shorts-maker-v2 --json` -> passed (`1655 passed, 12 skipped, 1 warning`; lint passed).
  - The remaining warning is the known external `google-genai` `_UnionGenericAlias` deprecation from site-packages.
- **Refactor next-loop note**:
  - The Pillow array materialization axis is now limited to helper bodies or temporary resize/crop conversions. A next refactor loop should switch to another small, tested axis rather than continuing to churn these helper bodies.

- **Goal this session**: Start from phase 0, list reproducible bugs/anomalies, then run root-cause debug loops without speculative fixes.
- **0-stage triage**:
  - Reproduced local Pillow deprecation failure by running `pytest ... -W error::DeprecationWarning`; `tools/ai_tech_shorts.py` and `tools/psychology_quote.py` used deprecated `Image.fromarray(..., "RGB"/"RGBA")`.
  - Reproduced external `google-genai` `_UnionGenericAlias` DeprecationWarning on Python 3.14. `google-genai==1.69.0` and latest `2.8.0` both warn. Official upstream issue googleapis/python-genai#1640 is open, and fix PR #1939 is still unmerged, so this is upstream/current-external rather than a project root fix.
  - Reproduced bare `python -m pytest ...` environment failure because shell `python` resolves outside the project `.venv`; project QC runner resolves `.venv` correctly.
  - `tests/legacy/__pycache__/` TODO is stale: `Test-Path tests/legacy/__pycache__` returned `False`.
  - Reproduced standalone archived ShortsFactory workflow/runbook drift: `.github/workflows/visual-regression.yml` and `docs/runbook.md` referenced deleted `requirements.txt` and moved `tests/unit/test_visual_regression.py` paths.
  - Reproduced README local verification drift: `python -m pytest --no-cov ...` failed before tests ran because bare `python` resolves outside the project `.venv` in the Windows/Codex shell.
  - Reproduced seven additional generated tool renderer Pillow failures by calling each demo renderer with `DeprecationWarning` as error: `health_do_vs_dont`, `health_medical_study`, `history_mystery`, `history_timeline`, `psychology_quiz`, `psychology_shorts`, and `space_fact_bomb`.
  - Reproduced `python execution/handoff_rotator.py --repo-root projects/shorts-maker-v2 --check --json` falsely returning `skip / Current Addendum heading not found` even though the project HANDOFF begins with `## Current Addendum (2026-06-11 / ...)`.
  - Reproduced `python execution/tasks_done_rotator.py --repo-root projects/shorts-maker-v2 --check --json` returning `kept: 0, archived: 0` even though the project TASKS DONE section had many `- [x] T-...` entries.
  - Reproduced the debug inventory `input evidence unavailable` state with an artificially low 5s helper timeout, then reran with 30s and confirmed it was an execution-timeout artifact rather than a new local product bug.
- **Completed**:
  - Removed deprecated Pillow `mode` arguments from generated Shorts render helpers.
  - Added warning-as-error regression guards to `tests/unit/test_ai_tech_shorts.py` and `tests/unit/test_psychology_quote.py`.
  - Completed the remaining Pillow mode-argument sweep across generated demo tool renderers and added `tests/unit/test_tool_pillow_deprecations.py`.
  - Fixed `execution/handoff_rotator.py` to detect `## Current Addendum` headings with descriptor suffixes and added workspace regression coverage for suffixed table/prose project HANDOFFs.
  - Fixed `execution/tasks_done_rotator.py` to parse project-local checklist DONE entries, normalize plain `## DONE` headings on rotation, and added workspace regression coverage.
  - Regenerated `.tmp/debug-loop-known-bugs-current.json` and `.tmp/debug-loop-known-bugs-current.md` with a 30s helper timeout; current inventory reports 5 blocked items, 0 actionable items, 0 reproduction-unclear items, and completion not allowed.
  - Converted the nested archived ShortsFactory workflow to a manual compatibility lane using `archive/tests_legacy_v1` paths and `pip install -e ".[dev]"`.
  - Updated `docs/runbook.md` to use the pyproject install command.
  - Updated `README.md` and `docs/README.md` local verification commands to use `.\.venv\Scripts\python.exe` with `--no-cov` for Windows/Codex.
  - Added `tests/unit/test_project_hygiene.py` to guard workflow/runbook dependency/path drift.
  - Extended `tests/unit/test_project_hygiene.py` to guard local verification docs against bare-`python` drift.
  - Recorded the Windows/Codex bare-`python` venv mismatch in `.ai/CONTEXT.md`.
  - Updated `.ai/TASKS.md`: removed stale `tests/legacy/__pycache__`, archived workflow, and full-PR-gate TODOs; added upstream `google-genai` warning TODO plus T-2362/T-2365/T-2366 DONE.
- **Verification**:
  - Focused repro after fix: `.venv\Scripts\python.exe -m pytest tests/unit/test_ai_tech_shorts.py tests/unit/test_psychology_quote.py -q --tb=short --maxfail=1 -o addopts= -W error::DeprecationWarning --basetemp .tmp/pytest-pillow-warning-final` -> `18 passed`.
  - Archived compatibility slice: `.venv\Scripts\python.exe -m pytest archive/tests_legacy_v1/unit/test_visual_regression.py archive/tests_legacy_v1/unit/test_engines_v2.py archive/tests_legacy_v1/unit/test_interfaces.py -q --tb=short --maxfail=1 -o addopts= --basetemp .tmp/pytest-legacy-visual-fixed` -> `57 passed`.
  - Hygiene regression: `.venv\Scripts\python.exe -m pytest tests/unit/test_project_hygiene.py -q --tb=short --maxfail=1 -o addopts=` -> `2 passed`.
  - Combined focused slice after import fix -> `59 passed`.
  - Local verification doc guard after README/docs update: `.venv\Scripts\python.exe -m pytest --no-cov tests/unit/test_project_hygiene.py -q --tb=short --maxfail=1` -> `3 passed`.
  - Project hygiene with addopts disabled -> `3 passed`; `ruff check tests/unit/test_project_hygiene.py` -> passed.
  - Tool renderer warning sweep repro after fix -> seven demo renderers passed with `DeprecationWarning` as error.
  - `.\.venv\Scripts\python.exe -m pytest --no-cov tests/unit/test_tool_pillow_deprecations.py -q --tb=short --maxfail=1 -o addopts= -W error::DeprecationWarning --basetemp .tmp/pytest-tool-pillow-deprecation` -> `7 passed`.
  - `rg` confirmed no remaining `Image.fromarray(..., "mode")` or single-quoted mode pattern under `tools`, `src`, or `tests`.
  - Project QC: `projects\shorts-maker-v2\.venv\Scripts\python.exe execution/project_qc_runner.py --project shorts-maker-v2 --json` from workspace root -> passed (`1653 passed, 12 skipped, 1 warning`; lint passed).
  - Handoff rotator repro after fix: `python execution/handoff_rotator.py --repo-root projects/shorts-maker-v2 --check --json` -> `{"status": "noop", "kept": 0, "archived": 0, ...}` instead of false `skip`.
  - `python -m pytest workspace/tests/test_handoff_rotator.py -q --tb=short --maxfail=1 -o addopts=` -> `19 passed`.
  - `python -m ruff check execution/handoff_rotator.py workspace/tests/test_handoff_rotator.py` -> passed.
  - Tasks DONE rotator dry-run after fix: `python execution/tasks_done_rotator.py --repo-root projects/shorts-maker-v2 --check --json` -> `{"status": "rotated", "kept": 5, "archived": 22, ...}`.
  - Real project DONE rotation after recording T-2369: `python execution/tasks_done_rotator.py --repo-root projects/shorts-maker-v2 --json` -> `{"status": "rotated", "kept": 5, "archived": 23, ...}` and `.ai/TASKS.md` now has `## DONE (Latest 5)`.
  - Post-rotation dry-run: `python execution/tasks_done_rotator.py --repo-root projects/shorts-maker-v2 --check --json` -> `{"status": "noop", "kept": 5, "archived": 0, ...}`.
  - `python -m pytest workspace/tests/test_tasks_done_rotator.py -q --tb=short --maxfail=1 -o addopts=` -> `12 passed`.
  - `python -m ruff check execution/tasks_done_rotator.py workspace/tests/test_tasks_done_rotator.py` -> passed.
  - `python .agents/skills/auto-research/scripts/debug_loop_inventory.py --root . --output-md .tmp/debug-loop-known-bugs-current.md --output-json .tmp/debug-loop-known-bugs-current.json --timeout 30 --json` -> expected exit `1` because completion remains blocked; output files were written and report `item_count=5`, `actionable=0`, `blocked=5`, `reproduction_unclear=0`.
  - `.\.venv\Scripts\python.exe -m ruff check .` -> passed.
  - `.\.venv\Scripts\python.exe -m pip check` -> `No broken requirements found.`
  - `git diff --check` on touched paths -> clean.
- **Next loops**:
  - No project-side reproducible test/lint failure remains in `shorts-maker-v2` after QC.
  - Remaining known `shorts-maker-v2` items are upstream `google-genai` warning tracking (issue #1640 / PR #1939) and the paid real-LLM retention simulator E2E, which needs explicit user approval before token use.
  - Workspace-level debug inventory is blocked by dirty handoff/commit authorization, push authorization for current-head Actions, and user-owned Hanwoo T-251; do not call `update_goal`.

## Last Session (2026-05-23 / Claude — goal 이어하기)

- **Goal this session**: 개발된 스킬 대비 코드가 부족한 부분을 찾아 제품 완성도를 끌어올린다.
- **Completed (1 commit)**:
  - **T-410 `1aeb9eaa`** — safe-zone QC 자막 높이 측정을 문자 수 추정 → 픽셀 측정으로 교체.
    `gate_safe_zone` 이 자막 높이를 `len(narration_ko)//20` 줄로 추정했는데, 이는
    `shorts-subtitle-safezone` 스킬이 안티패턴으로 명시 금지하는 문자 수 기반 방식이다
    (한글·영문 글자 폭이 달라 같은 글자 수도 줄 수가 다름). 또 자막 mode 를 무시해
    karaoke 모드의 긴 나레이션(청크 단위 한 줄 렌더)을 다줄 세로 오버플로우로 오탐했다.
    `caption_pillow.py` 에 `estimate_caption_height()` 신설 — `render_caption_image`
    (static) / `render_karaoke_image` (karaoke) 의 레이아웃 산식을 2x 슈퍼샘플링 +
    `//scale` 다운샘플까지 그대로 재현해 실제 렌더 PNG 와 픽셀 단위로 일치한다.
    `gate_safe_zone` 에 `canvas_width` + 역할별 `styles` 인자 추가, orchestrator 가
    RenderStep 의 hook/body/cta/closing 스타일과 config 해상도를 넘겨 QC 가 실제
    폰트·여백·글로우·모드로 측정하게 함.
- **Verification**: `pytest --no-cov tests/unit tests/integration` — exit 0 (전부 통과,
  회귀 없음). `ruff check` + `ruff format --check` — 변경 파일 전부 clean.
- **주의 (지뢰밭)**:
  - 이 워크스페이스에는 git 작업 사이에 `.ai/*` 및 다른 프로젝트 파일을 인덱스에 자동
    스테이징하는 외부 프로세스가 있다. 깨끗한 단일-프로젝트 커밋은
    `git commit --only -- <명시적 경로>` 로 인덱스를 우회할 것 (`-m`은 `--` 앞에 둘 것).
  - **`estimate_caption_height` 는 렌더 함수 산식의 복제다.** `render_caption_image` /
    `render_karaoke_image` 의 패딩·스케일·spacing 산식을 바꾸면 `estimate_caption_height`
    도 함께 고칠 것. `test_caption_pillow.py::TestEstimateCaptionHeight` 가 렌더 PNG 와
    `==`(정확 일치)로 비교하므로 드리프트는 CI 가 잡지만, 렌더 수정 시 같이 손볼 것.
  - pre-commit code-review-gate 가 FAIL 로 떠도 advisory 라 커밋은 통과한다. 보고된
    "test gap" 다수는 본 변경과 무관한 다른 워크스페이스 파일(confidence.ts 등)이다.

## Next Steps

1. 리텐션 시뮬레이터를 실제 LLM 으로 1회 E2E 실행해 예측 곡선 품질을 눈으로 검증
   (`retention_sim_enabled: true`, 영상 1편 생성, `runs/<job>/retention_report.md` 확인).
   — 유료 토큰 사용이므로 사용자 승인 필요.
2. T-410 같은 회귀를 더 빨리 잡으려면 pre-commit `--cov-fail-under=65` 외에
   PR 단위 full 단위/통합 테스트 게이트 도입 검토.
3. `gate_safe_zone` 은 static/karaoke 자막 높이를 픽셀 측정한다. word-highlight 모드
   (`render_karaoke_highlight_image`, 활성 단어 1.15x 확대)는 청크 단위라 현재
   karaoke 측정과 근사하지만, 확대 폰트까지 반영하는 정밀화 여지가 있다.

## Previous Sessions

- **2026-05-22 / Claude** — T-408 edge-tts `channel_key` 회귀 수정(`c9d1493f`),
  T-409 `shorts-tts-quality` 스킬↔YAML 정합 정정 + drift guard 신설(`d775a360`).
- **2026-05-22 / Claude** — T-321 리텐션 시뮬레이터 출하(`e194784b`), T-322 미디어 실패
  레코드 `scene_id` 각인(`ce5808a2`), T-323 safe-zone QC 매니페스트 표면화(`9e8531da`).
- **2026-05-20 / Antigravity** — T-320 OpenVoice v2 + MeloTTS 로컬 voice cloning 통합.
  `test_openvoice_client.py` 전역 moviepy mock 오염을 `importlib.util.find_spec` 격리로 해결.
