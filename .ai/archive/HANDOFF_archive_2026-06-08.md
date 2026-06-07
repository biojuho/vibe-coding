## Rotation 2026-06-08 (archived addenda older than 2026-06-01)

| Field | Value |
|---|---|
| Date | 2026-06-07 |
| Tool | Codex |
| Work | **T-1524 Shorts Manager channel-settings labels**. Continued the output-quality loop on operator-facing copy without pushing and without retrying user-owned T-251. Baseline browser QA found the Korean Shorts Manager still exposed four English labels in the channel settings form: `Voice`, `Style preset`, `Font color`, and `Image style prefix` (`english_label_count=4`, `korean_label_count=0`). `workspace/execution/pages/shorts_manager.py` now labels those controls as `음성`, `스타일 프리셋`, `자막 색상`, and `이미지 스타일 프롬프트`; `workspace/tests/test_shorts_manager.py` locks the localized labels and rejects the English labels. Candidate browser QA measured `english_label_count=0`, `korean_label_count=4`, horizontal overflow `0`, browser failures `0`, and deterministic A/B selected `adopt_candidate` (`score_delta=1.5714285714285714`). Verification passed focused Shorts Manager pytest (`45 passed`), Ruff, format check, `py_compile`, staged code-review gate PASS (`risk_score=0.05`), full active-project QC, graph refresh, and clean-worktree readiness. Code commit `e1d41f20` is local only. |
| Next Priorities | No local active-project QC blocker is open. Remaining release boundaries are explicit push/current-head GitHub Actions plus user-owned Hanwoo T-251 Supabase credential reset/live Prisma CRUD E2E. Do not push without explicit authorization and do not retry T-251 before credential reset/resync. |

## Rotation 2026-06-08 (archived addenda older than 2026-06-01)

| Field | Value |
|---|---|
| Date | 2026-06-07 |
| Tool | Codex |
| Work | **T-1525 Hanwoo dashboard tabbar scroll targets**. Protected focused/anchored dashboard controls from being hidden under the fixed mobile tabbar. `globals.css` now centralizes the tabbar bottom offset in `--dashboard-tabbar-offset`, applies it to document/dashboard scroll padding, and gives dashboard controls a matching `scroll-margin-bottom`. `home-market-copy.test.mjs` locks the offset, safe-area handling, and control margin contract. Verification passed focused Hanwoo source test (`57 passed`), Hanwoo lint, Hanwoo project QC (`533 passed`, lint/build/smoke passed), browser CSS check at `390x844` (`scrollPaddingBottom=92px`, control `scrollMarginBottom=92px`, horizontal overflow false, console warnings/errors 0), staged code-review gate PASS (`risk_score=0.00`), graph refresh, and full active-project QC. Code commit `e6386296` is local only. |
| Next Priorities | Superseded by T-1527 current-head full canonical QC/readiness refresh. Remaining release boundaries are explicit push/current-head GitHub Actions plus user-owned Hanwoo T-251 Supabase credential reset/live Prisma CRUD E2E. |

## Rotation 2026-06-08 (archived addenda older than 2026-06-01)

| Field | Value |
|---|---|
| Date | 2026-06-07 |
| Tool | Codex |
| Work | **T-1526 Shorts Analytics RPM labeling**. Corrected the Shorts Analytics ROI copy from generic Shorts CPM to Shorts RPM, and added the missing explicit Plotly runtime dependency for the page. `workspace/execution/pages/shorts_analytics.py` now labels the section `채널별 Shorts 수익 잠재력 (RPM 추정)` and explains RPM as revenue per 1,000 engaged views. `workspace/pyproject.toml` declares `plotly>=6.8.0`, `uv.lock` resolves it, and `workspace/tests/test_shorts_analytics.py` locks the copy and dependency contract. Verification passed focused Shorts Analytics pytest (`9 passed`), Ruff, format check, `py_compile`, `py -3.13 -m uv lock --check`, staged code-review gate PASS (`risk_score=0.00`), graph refresh, and full active-project QC. Code commit `c39bde69` is local only. |
| Next Priorities | Superseded by T-1527 current-head full canonical QC/readiness refresh. Remaining release boundaries are explicit push/current-head GitHub Actions plus user-owned Hanwoo T-251 Supabase credential reset/live Prisma CRUD E2E. |

## Rotation 2026-06-08 (archived addenda older than 2026-06-01)

| Field | Value |
|---|---|
| Date | 2026-06-07 |
| Tool | Codex |
| Work | **T-1527 current-head full canonical QC/readiness refresh**. Refreshed full active-project local gates through T-1526 at code/QC head `c39bde69`; later `.ai` context/session commits are documentation-only after that artifact. `python execution\project_qc_runner.py --json --artifact .tmp\project_qc_runner_latest.json --timeout-seconds 700` passed: Blind-to-X `1844 passed`, `9 skipped`, lint pass; Shorts Maker V2 `1640 passed`, `12 skipped`, `29 warnings`, lint pass; Hanwoo `533 passed`, lint/build/smoke passed; Knowledge Dashboard `62 passed`, lint/build/smoke passed. |
| Next Priorities | No local active-project QC blocker is open on the checked current workspace. Remaining release boundaries are explicit push/current-head GitHub Actions plus user-owned Hanwoo T-251 Supabase credential reset/live Prisma CRUD E2E. Do not push without explicit authorization and do not retry T-251 before credential reset/resync. |

## Rotation 2026-06-08 (archived addenda older than 2026-06-01)

| Field | Value |
|---|---|
| Date | 2026-06-07 |
| Tool | Codex |
| Work | **T-1528 Shorts Analytics channel-label/mobile-tab polish**. Continued the Shorts Analytics output-quality loop after the RPM/runtime dependency fix. `workspace/execution/pages/shorts_analytics.py` now normalizes legacy/raw channel labels such as `AI/Tech`, `space`, `history`, and `health` to the canonical Korean display labels, merges channel production/performance summaries by display label, applies display labels in CPV tables, top-video chips, and ROI expanders, and injects mobile tab CSS so Streamlit tab controls meet the 44px target at narrow widths. `workspace/tests/test_shorts_analytics.py` locks alias normalization, grouped stat/performance recomputation, CPV display labels, and mobile tab CSS. Mobile browser QA at `390x844` passed with `moduleErrorCount=0`, `appContentLoaded=true`, `rawLegacyLabelCount=0`, `canonicalLabelCount=6`, `smallTabButtons=[]`, horizontal overflow false, console warnings/errors 0, failed requests 0, screenshot `output/playwright/shorts-analytics-t1525-candidate-mobile.png`. Verification passed focused workspace tests (`27 passed`), Ruff, `py_compile`, `py -3.13 -m uv lock --project workspace --check`, graph refresh, Shorts Maker V2 project QC (`1640 passed`, `12 skipped`, `29 warnings`, lint pass), and advisory code-review gate WARN (`risk_score=0.40`) covered by focused/browser/project QC. Code commit `c4f26ef3` is local only. |
| Next Priorities | Refresh full canonical active-project QC/readiness before any release claim because HEAD advanced past T-1527. Remaining release boundaries are explicit push/current-head GitHub Actions plus user-owned Hanwoo T-251 Supabase credential reset/live Prisma CRUD E2E. Do not push without explicit authorization and do not retry T-251 before credential reset/resync. |
