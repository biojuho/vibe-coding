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
