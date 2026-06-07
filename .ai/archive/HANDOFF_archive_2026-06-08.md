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

## Rotation 2026-06-08 (archived addenda older than 2026-06-01)

| Field | Value |
|---|---|
| Date | 2026-06-07 |
| Tool | Codex |
| Work | **T-1527 Hanwoo CattleForm mobile modal footer/field polish**. Continued the Hanwoo browser-click quality loop without pushing and without retrying user-owned T-251. Baseline authenticated mobile QA at `390x844` found the `새 개체 등록` modal had two sub-44px controls and the sticky save action bar covering `구입가격`/`구입일자` fields. `projects/hanwoo-dashboard/src/components/forms/CattleForm.js` now separates the field scroller from the visible save action bar, raises close/history lookup/genetic controls to at least `44px`, and keeps footer action labels on one line. Candidate browser QA measured initial, purchase-field scrolled, and memo scrolled states with `smallControls=0`, `coveredFields=0`, `scrollFooterOverlap=0`, horizontal overflow false, and bad responses `0`; expected degraded Supabase warnings only. A/B selected `adopt_candidate` (`score_delta=0.7142857142857143`). Verification passed Hanwoo source tests (`533 passed`), Hanwoo lint, Hanwoo project QC test/lint/build/smoke, graph refresh, and code-review gate advisory WARN (`risk_score=0.30`) covered by focused/browser/project evidence. Code commit `24b6046d` is local only. |
| Next Priorities | No new local Hanwoo blocker is open. Remaining release boundaries are explicit push/current-head GitHub Actions plus user-owned Hanwoo T-251 Supabase credential reset/live Prisma CRUD E2E. Do not push without explicit authorization and do not retry T-251 before credential reset/resync. |

## Rotation 2026-06-08 (archived addenda older than 2026-06-01)

| Field | Value |
|---|---|
| Date | 2026-06-07 |
| Tool | Codex |
| Work | **T-1529 full canonical QC/readiness refresh**. Refreshed the canonical local active-project gates after T-1527 Hanwoo CattleForm mobile modal polish and T-1528 Shorts Analytics channel-label/mobile-tab polish. `python execution\project_qc_runner.py --json --artifact .tmp\project_qc_runner_latest.json --timeout-seconds 700` passed at code/QC baseline `8870fe71`; later `.ai` commits are documentation-only and readiness reports no relevant active-project changes since the QC artifact. Results: Blind-to-X `1844 passed`, `9 skipped`, lint pass; Shorts Maker V2 `1640 passed`, `12 skipped`, `29 warnings`, lint pass; Hanwoo `533 passed`, lint/build/smoke passed; Knowledge Dashboard `62 passed`, lint/build/smoke passed. `product_readiness_score.py --json` reports score `96`, clean worktree, fresh QC artifacts, local blockers `0`, agent tasks `0`, publish blockers `1`, external blockers `1`; `session_orient.py --json` reports a current graph, no open PRs, and no stale HANDOFF head claim after this wording correction. |
| Next Priorities | No new local active-project QC blocker is open on the checked current workspace. Remaining release boundaries are explicit push/current-head GitHub Actions plus user-owned Hanwoo T-251 Supabase credential reset/live Prisma CRUD E2E. Do not push without explicit authorization and do not retry T-251 before credential reset/resync. |

## Rotation 2026-06-08 (archived addenda older than 2026-06-01)

| Field | Value |
|---|---|
| Date | 2026-06-07 |
| Tool | Codex |
| Work | **T-1530 Hanwoo outbox notification copy repair**. Continued the output-quality loop on a concrete final-output defect: `projects/hanwoo-dashboard/scripts/outbox-worker.mjs` could persist broken Korean calving notification text with replacement-character mojibake in read-model notification snapshots. The worker now emits the usable copy `분만 예정일이 ${daysLeft}일 남았습니다.` and the section comments no longer contain corrupted characters. Added `projects/hanwoo-dashboard/src/lib/outbox-worker-copy.test.mjs` to lock valid Korean estrus/calving notification copy and reject replacement/mojibake text. Verification passed: `rg` found no replacement characters in the touched worker/test files; `node --check scripts\outbox-worker.mjs` passed; Hanwoo source tests passed (`534 passed`); Hanwoo lint passed; Hanwoo project QC passed via `.tmp\project_qc_runner_hanwoo_t1530.json` (`534 passed`, lint/build/smoke passed); `git diff --check` passed with CRLF warning only. Code-review gate was advisory WARN (`risk_score=0.45`) for broader worker coverage gaps, covered by the direct copy guard plus full Hanwoo QC. Code commit `9e9ec78a` is local only. |
| Next Priorities | Do not mix this product-output polish with T-251. Remaining release boundaries are explicit push/current-head GitHub Actions plus user-owned Hanwoo T-251 Supabase credential reset/live Prisma CRUD E2E. Do not push without explicit authorization and do not retry T-251 before credential reset/resync. Preserve unrelated unstaged WIP if present. |

## Rotation 2026-06-08 (archived addenda older than 2026-06-01)

| Field | Value |
|---|---|
| Date | 2026-06-07 |
| Tool | Codex |
| Work | **T-1532 Channel Growth mobile control polish**. Continued the Shorts workflow/browser-click quality loop on `workspace/execution/pages/channel_growth.py`. Baseline mobile QA at `390x844` found the page title taking `194px` height, Streamlit form buttons and BaseWeb controls below the 44px app touch target, and Plotly modebar buttons creating 24 tiny chart controls. The candidate switches the title to compact Korean operator copy, injects mobile-only 44px touch-target CSS for Streamlit buttons/forms/BaseWeb input/select controls, and hides Plotly modebars with `_PLOTLY_CHART_CONFIG` while keeping charts responsive. Candidate browser QA measured title height `48.8px`, `small_app_button_count=0`, `small_baseweb_control_count=0`, `modebar_button_count=0`, no horizontal overflow, console messages `0`, and failed requests `0`; A/B selected `adopt_candidate` (`score_delta=0.7351730815783104`). Verification passed focused Channel Growth pytest (`6 passed`), related Channel Growth pytest with repo-local basetemp (`16 passed`), targeted Ruff, `py_compile`, `git diff --check`, graph refresh, and Shorts Maker V2 project QC (`1640 passed`, `12 skipped`, `29 warnings`, lint pass). Code commit `8ac5b2c0` is local only. |
| Next Priorities | Current HEAD later advanced to Hanwoo `8cfc353b` (`fix(hanwoo): keep settings controls clear of tabbar`). Do not mix T-1532 with those later Hanwoo commits. Remaining release boundaries are explicit push/current-head GitHub Actions plus user-owned Hanwoo T-251 Supabase credential reset/live Prisma CRUD E2E. Do not push without explicit authorization and do not retry T-251 before credential reset/resync. |

## Rotation 2026-06-08 (archived addenda older than 2026-06-01)

| Field | Value |
|---|---|
| Date | 2026-06-07 |
| Tool | Codex |
| Work | **T-1535 Hanwoo settings tabbar-safe controls polish**. Continued the Hanwoo browser-click quality loop on the dashboard settings tab. Baseline/candidate audit used `.tmp/hanwoo-t1530-tabbar-safe-audit.py`; final artifact `.tmp/hanwoo-t1530-tabbar-safe-current.json` reports mobile and desktop `covered=0`, `small=0`, `xOverflowTabs=0`, bad responses `0`. `SettingsTab.js` now gives farm settings fields a mobile scroll viewport; `globals.css` preserves mobile form spacing so settings/farm/building controls do not sit behind the fixed tab bar; source tests lock the CSS variables/classes. Verification passed full Hanwoo source tests (`535 passed`), Hanwoo lint, Hanwoo project QC (`test/lint/build/smoke` passed), `git diff --check`, graph refresh, and staged code-review gate exit 0 with advisory WARN (`risk_score=0.30`) covered by direct/source/browser/project evidence. Code commit `8cfc353b` is local only. |
| Next Priorities | Worktree should be checked with `python execution/session_orient.py --json` before continuing. Remaining release boundaries are explicit push/current-head GitHub Actions plus user-owned Hanwoo T-251 Supabase credential reset/live Prisma CRUD E2E. Do not push without explicit authorization and do not retry T-251 before credential reset/resync. |

## Rotation 2026-06-08 (archived addenda older than 2026-06-01)

| Field | Value |
|---|---|
| Date | 2026-06-07 |
| Tool | Codex |
| Work | **T-1537 Shorts Manager mobile readiness controls polish**. Continued the Shorts Manager operator-output quality loop. `workspace/execution/pages/shorts_manager.py` now raises Streamlit number stepper buttons and checkbox labels to the 44px mobile target, keeps number steppers at least 44px wide, and localizes channel-readiness `voice/style` captions to `음성/스타일`. `workspace/tests/test_shorts_manager.py` locks the mobile CSS selectors and rejects the old English readiness labels. Verification passed focused Shorts Manager pytest (`45 passed`), targeted Ruff check, Ruff format check, `py_compile`, browser QA at `390x844` (`hasEnglishVoiceStyle=false`, `koreanVoiceStyleCount=5`, `horizontalOverflow=false`, screenshot `output/playwright/shorts-manager-t1537-channel-readiness-copy.png`), and staged/commit code-review gate exit 0 with advisory WARN (`risk_score=0.30`) covered by direct source/render/browser tests. Code commit `273a511a` is local only. |
| Next Priorities | Worktree should be checked with `python execution/session_orient.py --json` before continuing. Remaining release boundaries are explicit push/current-head GitHub Actions plus user-owned Hanwoo T-251 Supabase credential reset/live Prisma CRUD E2E. Do not push without explicit authorization and do not retry T-251 before credential reset/resync. |

| Field | Value |
|---|---|
| Date | 2026-06-07 |
| Tool | Codex |
| Work | **T-1536 Hanwoo dashboard content-shell scroll bound**. Follow-up to T-1535. `globals.css` now bounds the mobile `.dashboard-content-shell` to the safe viewport height with contained vertical scrolling and resets the bound on desktop; `home-market-copy.test.mjs` locks max-height/overflow/overscroll/fallback contracts. Final browser-click QA still reports mobile and desktop `covered=0`, `small=0`, `xOverflowTabs=0`, bad responses `0`, and `.tmp/project_qc_runner_hanwoo_t1535.json` passed Hanwoo `test/lint/build/smoke`. Code commit `28e7946c` is local only. |
| Next Priorities | Worktree should be checked with `python execution/session_orient.py --json` before continuing. Remaining release boundaries are explicit push/current-head GitHub Actions plus user-owned Hanwoo T-251 Supabase credential reset/live Prisma CRUD E2E. Do not push without explicit authorization and do not retry T-251 before credential reset/resync. |
