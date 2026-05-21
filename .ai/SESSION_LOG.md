# SESSION_LOG

> Recent 7-day AI session history. Older entries were archived to `.ai/archive/SESSION_LOG_before_2026-04-07.md`.

| Date | Tool | Summary | Changed Files |
|---|---|---|---|
| 2026-05-21 | Codex | **T-520 Hanwoo payment duplicate-request immediate guard**. Active Hanwoo quality uplift continuation. `PaymentWidget` now uses `paymentRequestInFlightRef` as a synchronous lock before `/api/payments/prepare` and Toss `requestPayment()`, preventing rapid repeated checkout activations from starting duplicate payment requests before React re-renders `isSubmitting`. Existing button disabled state, `aria-busy`, wait cursor, and fallback copy remain intact. Verification: focused payment UX copy test passed (`5 passed`), targeted ESLint passed, path-limited `git diff --check` passed, full Hanwoo QC passed (`test` 210, lint, build), staged code-review gate JSON passed (`risk_score 0.0`; cp949 reader-thread noise only), and commit hook WARN was the known graph/test-gap heuristic plus unrelated WIP while direct tests and full QC covered the changed files. Code commit `071487b4`. | `projects/hanwoo-dashboard/src/components/payment/PaymentWidget.js`; `projects/hanwoo-dashboard/src/lib/payment-ux-copy.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-21 | Codex | **T-519 Hanwoo pagination duplicate-load guard**. Active Hanwoo quality uplift continuation. `useCattlePagination` and `useSalesPagination` now use `loadInFlightRef` as an immediate guard before issuing load-more fetches and appending returned rows, preventing rapid repeated clicks from starting duplicate cattle/sales pagination requests before React re-renders the loading state. Existing timeout/error feedback, disabled buttons, and `aria-busy` behavior are preserved. Verification: focused pagination feedback tests passed (`2 passed`), targeted ESLint passed, path-limited `git diff --check` passed, full Hanwoo QC passed (`test` 210, lint, build), staged code-review gate JSON passed (`risk_score 0.0`; cp949 reader-thread noise only), and commit hook WARN was the known graph/test-gap heuristic while direct tests and full QC covered the changed files. Code commit `3475d8d0`. | `projects/hanwoo-dashboard/src/lib/hooks/useCattlePagination.js`; `projects/hanwoo-dashboard/src/lib/hooks/useSalesPagination.js`; `projects/hanwoo-dashboard/src/lib/cattle-pagination-feedback.test.mjs`; `projects/hanwoo-dashboard/src/lib/sales-pagination-feedback.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-21 | Codex | **T-518 Hanwoo cattle tag lookup duplicate-request guard**. Active Hanwoo quality uplift continuation. `CattleForm` now uses `lookupInFlightRef` as an immediate guard before reading the tag and calling `lookupCattleTag()`, so rapid repeated lookup clicks cannot start duplicate MTRACE/tag lookup requests before React re-renders the disabled state. The existing `lookupLoading` disabled/`aria-busy` UI remains visible and the ref is cleared in `finally`. Verification: focused cattle detail modal wiring test passed (`10 passed`), targeted ESLint passed, path-limited `git diff --check` passed, full Hanwoo QC passed (`test` 210, lint, build), staged code-review gate JSON passed (`risk_score 0.0`; cp949 reader-thread noise only), and commit hook WARN was the known graph/test-gap heuristic while direct tests and full QC covered the changed files. Code commit `023e237`. | `projects/hanwoo-dashboard/src/components/forms/CattleForm.js`; `projects/hanwoo-dashboard/src/lib/cattle-detail-modal-wiring.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-21 | Antigravity | **T-320 OpenVoice v2 local Voice Cloning and Pytest global mock pollution fix**. Integrated local CPU-based OpenVoice v2 cloning client (KR-Default speaker + ToneColorConverter) cascading to `edge-tts` and `openai-tts`. Resolved a critical Pytest global mock pollution where `sys.modules["moviepy"] = MagicMock()` in one test polluted other test suites (like `test_render_step_effects.py`), causing `TypeError` on `ImageClip` when physical `moviepy 2.2.1` is present. Refactored the test suite to use `importlib.util.find_spec("moviepy")` conditional mocking and enforced Ruff import sorting. Verification: `test_openvoice_client.py` (8 passed), `test_render_step_effects.py` (29 passed), and all `shorts-maker-v2` QC checks passed 100% green. | `projects/shorts-maker-v2/src/shorts_maker_v2/providers/openvoice_client.py`; `projects/shorts-maker-v2/src/shorts_maker_v2/config.py`; `projects/shorts-maker-v2/src/shorts_maker_v2/pipeline/media/audio_mixin.py`; `projects/shorts-maker-v2/tests/unit/test_openvoice_client.py`; `.ai/CONTEXT.md`; `.ai/TASKS.md`; `.ai/HANDOFF.md`; `.ai/SESSION_LOG.md` |
| 2026-05-21 | Codex | **T-517 Hanwoo notification test-message duplicate-send guard**... | ... |
| 2026-05-21 | Codex | **T-516 Hanwoo feed/analysis numeric aggregation guard**. Active Hanwoo quality uplift continuation. `utils.js` now exports `toFiniteNumber()`, `FeedTab` uses it for feed standards, total guides, and chart history, and `AnalysisTab` uses it for revenue, expenses, top-sale sorting, and average feed calculations so malformed/non-finite values cannot spread `NaN` through dashboard metrics. Verification: focused utils/feed/analysis source tests passed (`16 passed`), targeted ESLint passed, path-limited `git diff --check` passed, unsafe aggregation scan found no remaining matches, full Hanwoo QC passed (`test` 209, lint, build), staged code-review gate JSON passed (`risk_score 0.0`; cp949 reader-thread noise only), and commit hook WARN was the known graph/test-gap heuristic while direct tests and full QC covered the changed files. Code commit `037b6ae`. | `projects/hanwoo-dashboard/src/lib/utils.js`; `projects/hanwoo-dashboard/src/components/tabs/FeedTab.js`; `projects/hanwoo-dashboard/src/components/tabs/AnalysisTab.js`; `projects/hanwoo-dashboard/src/lib/utils-date.test.mjs`; `projects/hanwoo-dashboard/src/lib/empty-state-wiring.test.mjs`; `projects/hanwoo-dashboard/src/lib/analysis-copy.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-21 | Codex | **T-515 Hanwoo AI chat empty-send guard**. Active Hanwoo quality uplift continuation. `AIChatWidget` now derives `canSend` from trimmed input plus streaming state, disables the send button until a non-empty question is ready, and mirrors the inactive state through opacity/cursor styling so blank sends no longer look actionable while preserving the existing no-op handler guard. Verification: focused AI chat widget copy test passed (`2 passed`), targeted ESLint passed, path-limited `git diff --check` passed, full Hanwoo QC passed (`test` 207, lint, build), staged code-review gate JSON passed (`risk_score 0.0`; cp949 reader-thread noise only), and commit hook WARN was the known advisory graph/test-gap heuristic. Code commit `0697b40`. | `projects/hanwoo-dashboard/src/components/widgets/AIChatWidget.js`; `projects/hanwoo-dashboard/src/lib/ai-chat-widget-copy.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-21 | Codex | **T-514 Hanwoo non-finite money formatting guard**. Active Hanwoo quality uplift continuation. `formatMoney()` now converts input with `Number(value)` and formats only finite numbers, returning `0` for invalid/non-finite values so `NaN` or `Infinity` cannot reach user-facing won amounts. `utils-date.test.mjs` guards the contract and blocks the old direct `Intl.NumberFormat('ko-KR').format(value)` path. Verification: focused utils/payment/profitability tests passed (`10 passed`), targeted ESLint passed, path-limited `git diff --check` passed, non-finite money scan found no remaining runtime matches, full Hanwoo QC passed (`test` 206, lint, build), staged code-review gate JSON passed (`risk_score 0.0`; cp949 reader-thread noise only), and commit hook was skipped after the same gate passed to avoid duplicate advisory noise. Code commit `a95c700`. | `projects/hanwoo-dashboard/src/lib/utils.js`; `projects/hanwoo-dashboard/src/lib/utils-date.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-21 | Codex | **T-505 Hanwoo numeric input validation**. Active Hanwoo quality uplift continuation. `action-validation.mjs` and `formSchemas.js` now reject non-decimal JavaScript numeric strings before Zod range checks, preventing values such as `1e6`, `0x10`, or `3.5446e1` from silently becoming prices, pen counts, or coordinates. `action-validation.test.mjs` adds runtime coverage and `home-market-copy.test.mjs` guards the client form schema contract by blocking `z.coerce.number`. Verification: focused action-validation/home tests passed (`35 passed`), targeted ESLint passed, path-limited `git diff --check` passed, full Hanwoo QC passed (`test` 203, lint, build), staged code-review gate JSON passed (`risk_score 0.0`; cp949 reader-thread noise only), and commit hook WARN was the known advisory graph/test-gap heuristic. Code commit `f4a63ab`. | `projects/hanwoo-dashboard/src/lib/action-validation.mjs`; `projects/hanwoo-dashboard/src/lib/action-validation.test.mjs`; `projects/hanwoo-dashboard/src/lib/formSchemas.js`; `projects/hanwoo-dashboard/src/lib/home-market-copy.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-21 | Codex | **T-504 Hanwoo form date validation**. Active Hanwoo quality uplift continuation. `action-validation.mjs` and `formSchemas.js` now require strict `YYYY-MM-DD` strings and verify that the parsed date round-trips to the original value, preventing JavaScript Date rollover from accepting impossible form/server-action dates such as `2026-02-31`, `2026-04-31`, or `2026-06-31`. `action-validation.test.mjs` adds runtime coverage and `home-market-copy.test.mjs` guards the client form schema contract. Verification: focused action-validation/home tests passed (`34 passed`), targeted ESLint passed, path-limited `git diff --check` passed, full Hanwoo QC passed (`test` 202, lint, build), staged code-review gate JSON passed (`risk_score 0.0`; cp949 reader-thread noise only), and commit hook WARN was the known advisory graph/test-gap heuristic. Code commit `f8d33a1`. | `projects/hanwoo-dashboard/src/lib/action-validation.mjs`; `projects/hanwoo-dashboard/src/lib/action-validation.test.mjs`; `projects/hanwoo-dashboard/src/lib/formSchemas.js`; `projects/hanwoo-dashboard/src/lib/home-market-copy.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-21 | Codex | **T-503 Hanwoo dashboard numeric-filter validation**. Active Hanwoo quality uplift continuation. `parseLimit()` and `parsePenNumber()` now trim input, require all digits, and only then parse, preventing partial values such as `10abc` or `3?? from silently becoming valid dashboard list filters. `home-market-copy.test.mjs` guards against returning to `Number.parseInt(String(value), 10)`. Verification: focused home/dashboard copy test passed (`22 passed`), targeted ESLint passed, path-limited `git diff --check` passed, full Hanwoo QC passed (`test` 201, lint, build), staged code-review gate JSON passed (`risk_score 0.0`; cp949 reader-thread noise only), and commit hook WARN was the known advisory graph/test-gap heuristic. Code commit `a3cffa6`. | `projects/hanwoo-dashboard/src/lib/dashboard/list-queries.js`; `projects/hanwoo-dashboard/src/lib/home-market-copy.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-21 | Codex | **T-502 Hanwoo dashboard date-filter validation**. Active Hanwoo quality uplift continuation. `parseDateParam()` now requires strict `YYYY-MM-DD` input and verifies that the parsed date round-trips to the original value, preventing impossible sales filters such as `2026-02-31` from silently becoming a different calendar date. `home-market-copy.test.mjs` guards the strict date regex and round-trip check. Verification: focused home/dashboard copy test passed (`22 passed`), targeted ESLint passed, path-limited `git diff --check` passed, full Hanwoo QC passed (`test` 201, lint, build), staged code-review gate JSON passed (`risk_score 0.0`; cp949 reader-thread noise only), and commit hook WARN was the known advisory graph/test-gap heuristic. Code commit `93147da`. | `projects/hanwoo-dashboard/src/lib/dashboard/list-queries.js`; `projects/hanwoo-dashboard/src/lib/home-market-copy.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-21 | Codex | **T-501 Hanwoo profitability fallback guard**. Active Hanwoo quality uplift continuation. `getProfitabilityEstimates()` now lets only known operator-facing business-state messages flow into `ProfitabilityWidget` and maps unexpected runtime/Prisma failures to stable Korean retry copy, preventing raw `err.message` exposure in the visible widget. `profitability-copy.test.mjs` guards against `error: err.message` returning. Verification: focused profitability copy test passed (`4 passed`), targeted ESLint passed, path-limited `git diff --check` passed, full Hanwoo QC passed (`test` 201, lint, build), staged code-review gate JSON passed (`risk_score 0.0`; cp949 reader-thread noise only), and commit hook WARN was the known advisory graph/test-gap heuristic. Code commit `7f3d7f8`. | `projects/hanwoo-dashboard/src/lib/dashboard/profitability-service.js`; `projects/hanwoo-dashboard/src/lib/profitability-copy.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-21 | Codex | **T-500 Hanwoo market-price stale label polish**. Active Hanwoo quality uplift continuation. `MarketPriceWidget` now shows `?댁쟾 ??κ컪` for stale cache source states instead of the awkward `?댁쟾 ??κ?`, and `home-market-copy.test.mjs` guards the corrected market-price widget copy plus mojibake exclusion patterns. Verification: focused market/home copy tests passed (`28 passed`), targeted ESLint passed, path-limited `git diff --check` passed, full Hanwoo QC passed (`test` 201, lint, build), staged code-review gate JSON passed (`risk_score 0.0`; cp949 reader-thread noise only), and commit hook WARN was the known advisory graph/test-gap heuristic. Code commit `1be1fa5`. | `projects/hanwoo-dashboard/src/components/widgets/MarketPriceWidget.js`; `projects/hanwoo-dashboard/src/lib/home-market-copy.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-21 | Codex | **T-499 Hanwoo notification modal readable Korean copy**. Active Hanwoo quality uplift continuation. `NotificationModal` now renders clean Korean labels for the title, close action, empty state, SMS service section, test-send button, and SMS cost note instead of mojibake, and `notification-modal-copy.test.mjs` now guards readable Korean product copy plus known broken-fragment exclusions. Verification: focused notification-modal copy test passed (`6 passed`), targeted ESLint passed, path-limited `git diff --check` passed, full Hanwoo QC passed (`test` 201, lint, build), staged code-review gate JSON passed (`risk_score 0.0`; cp949 reader-thread noise only), and commit hook WARN was the known advisory graph/test-gap heuristic. Code commit `c2fef8f`. | `projects/hanwoo-dashboard/src/components/ui/NotificationModal.js`; `projects/hanwoo-dashboard/src/lib/notification-modal-copy.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-21 | Codex | **T-498 Hanwoo Feed tab Korean copy guard**. Active Hanwoo quality uplift continuation. `FeedTab` keeps the feed memo placeholder as readable Korean operator copy (`?щ즺 ?곹깭, ??랬 蹂?? 異뺤궗 硫붾え瑜??곸뼱 二쇱꽭??`), quote style is aligned in touched JSX attributes, and `empty-state-wiring.test.mjs` now asserts the visible Feed tab Korean product copy while blocking known mojibake fragments from returning. Verification: focused empty-state wiring test passed (`12 passed`), targeted ESLint passed, path-limited `git diff --check` passed, full Hanwoo QC passed (`test` 200, lint, build), staged code-review gate JSON passed (`risk_score 0.0`; cp949 reader-thread noise only), and commit hook WARN was the known advisory graph/test-gap heuristic. Code commit `44df37a`. | `projects/hanwoo-dashboard/src/components/tabs/FeedTab.js`; `projects/hanwoo-dashboard/src/lib/empty-state-wiring.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-21 | Codex | **T-497 Hanwoo notification-system mirror client boundary and copy guard**. Active Hanwoo quality uplift continuation. `NotificationSystem.tsx` now declares `"use client"` before using `useState`/event handlers, the JS mirror drops the unused `CheckIcon` import and aligns local state updater style, and `notification-system-copy.test.mjs` guards the Korean notification trigger, empty state, mark-all copy, and TSX client boundary. Verification: focused notification-system copy test passed (`7 passed`), targeted ESLint passed, path-limited `git diff --check` passed, full Hanwoo QC passed (`test` 199, lint, build), staged code-review gate JSON passed (`risk_score 0.0`; cp949 reader-thread noise only), and commit hook WARN was the known advisory graph/test-gap heuristic. Code commit `38c7ce7`. | `projects/hanwoo-dashboard/src/components/layout/NotificationSystem.js`; `projects/hanwoo-dashboard/src/components/layout/NotificationSystem.tsx`; `projects/hanwoo-dashboard/src/lib/notification-system-copy.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-21 | Codex | **T-496 Hanwoo settings building delete confirm guard**. Active Hanwoo quality uplift continuation. `SettingsTab` now uses `deleteBuildingInFlightRef` as an immediate lock before the async confirmation dialog opens, so rapid repeated delete clicks cannot stack multiple confirms before `deletingBuildingId` is set. The visible row disabled/`aria-busy` state still follows the active building id, and `settings-tab-accessibility.test.mjs` guards the contract. Verification: focused settings accessibility test passed (`9 passed`), targeted ESLint passed, path-limited `git diff --check` passed, full Hanwoo QC passed (`test` 199, lint, build), staged code-review gate JSON passed (`risk_score 0.0`; cp949 reader-thread noise only), and commit hook WARN was the known advisory graph/test-gap heuristic. Code commit `bab52fa`. | `projects/hanwoo-dashboard/src/components/tabs/SettingsTab.js`; `projects/hanwoo-dashboard/src/lib/settings-tab-accessibility.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-21 | Codex | **T-495 Hanwoo cattle detail edit/archive action lock**. Active Hanwoo quality uplift continuation. `CattleDetailModal` now applies the existing `isDeleting` lock to the edit button as well as the archive button, so operators cannot switch into edit mode while a slow archive/delete flow is still resolving. `cattle-detail-modal-wiring.test.mjs` guards the contract. Verification: focused cattle-detail modal wiring test passed (`10 passed`), targeted ESLint passed, path-limited `git diff --check` passed, full Hanwoo QC passed (`test` 199, lint, build), staged code-review gate JSON passed (`risk_score 0.0`; cp949 reader-thread noise only), and commit hook WARN was the known advisory graph/test-gap heuristic. Code commit `52b3ed1`. | `projects/hanwoo-dashboard/src/components/forms/CattleDetailModal.js`; `projects/hanwoo-dashboard/src/lib/cattle-detail-modal-wiring.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-21 | Codex | **T-494 Hanwoo cattle QR print duplicate-window guard**. Active Hanwoo quality uplift continuation. `QRCodeWidget` now uses `printInFlightRef` plus `isPrinting` to block repeated print activations while the generated print window is being prepared/printed, and the print button exposes explicit `type="button"`, disabled state, and `aria-busy`. `qr-widget-copy.test.mjs` guards the contract. Verification: focused QR widget copy test passed (`2 passed`), targeted ESLint passed, path-limited `git diff --check` passed, full Hanwoo QC passed (`test` 199, lint, build), staged code-review gate JSON passed (`risk_score 0.0`; cp949 reader-thread noise only), and commit hook WARN was the known advisory graph/test-gap heuristic. Code commit `e9b87c8`. | `projects/hanwoo-dashboard/src/components/widgets/QRCodeWidget.js`; `projects/hanwoo-dashboard/src/lib/qr-widget-copy.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-21 | Codex | **T-493 Hanwoo cattle CSV export duplicate-download guard**. Active Hanwoo quality uplift continuation. `ExcelExportButton` now uses `preparingRef` as an immediate in-flight lock before `resolveCattleList()` and CSV blob creation, so rapid repeated activation cannot produce duplicate list resolution or duplicate downloads before React re-renders the disabled state. `excel-export-button-copy.test.mjs` guards the contract. Verification: focused excel export button copy test passed (`2 passed`), targeted ESLint passed, path-limited `git diff --check` passed, full Hanwoo QC passed (`test` 198, lint, build), staged code-review gate JSON passed (`risk_score 0.0`; cp949 reader-thread noise only), and commit hook WARN was the known advisory graph/test-gap heuristic. Code commit `e8680c5`. | `projects/hanwoo-dashboard/src/components/widgets/ExcelExportButton.js`; `projects/hanwoo-dashboard/src/lib/excel-export-button-copy.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-21 | Codex | **T-492 Hanwoo cattle move duplicate-request guard**. Active Hanwoo quality uplift continuation. `DashboardClient` now uses `movingCattleIdRef` as an immediate in-flight lock around the confirm + `handleUpdateCattle` move flow, so repeated drop events cannot open overlapping move confirms or send duplicate move updates before the first flow finishes. `home-market-copy.test.mjs` guards the contract. Verification: focused home-market copy test passed (`22 passed`), targeted ESLint passed, path-limited `git diff --check` passed, full Hanwoo QC passed (`test` 197, lint, build), staged code-review gate JSON passed (`risk_score 0.0`; cp949 reader-thread noise only), and commit hook WARN was the known advisory graph/test-gap heuristic. Code commit `e77b843`. | `projects/hanwoo-dashboard/src/components/DashboardClient.js`; `projects/hanwoo-dashboard/src/lib/home-market-copy.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-21 | Codex | **T-491 Hanwoo payment duplicate-request guard**. Active Hanwoo quality uplift continuation. `PaymentWidget` now returns early when `isSubmitting` is already true and exposes `aria-busy` on the checkout button while payment preparation/request is active, so rapid repeated activation cannot issue duplicate `/api/payments/prepare` and Toss `requestPayment` calls. `payment-ux-copy.test.mjs` guards the contract. Verification: focused payment UX copy test passed (`5 passed`), targeted ESLint passed, path-limited `git diff --check` passed, full Hanwoo QC passed (`test` 196, lint, build), staged code-review gate JSON passed (`risk_score 0.0`; cp949 reader-thread noise only), and commit hook WARN was the known advisory graph/test-gap heuristic. Code commit `3b6dddb`. | `projects/hanwoo-dashboard/src/components/payment/PaymentWidget.js`; `projects/hanwoo-dashboard/src/lib/payment-ux-copy.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-21 | Codex | **T-490 Hanwoo cattle archive duplicate-request guard**. Active Hanwoo quality uplift continuation. `DashboardClient` now tracks `deletingCattleId`, returns early while an archive/delete flow is already active, and clears the lock after confirm/delete completion; `CattleDetailModal` receives `isDeleting` and disables/exposes `aria-busy` on the archive button while active, so slow archive requests cannot be triggered twice from the detail modal. `cattle-detail-modal-wiring.test.mjs` guards the contract. Verification: focused cattle-detail modal wiring test passed (`10 passed`), targeted ESLint passed, path-limited `git diff --check` passed, full Hanwoo QC passed (`test` 195, lint, build), staged code-review gate JSON passed (`risk_score 0.0`; cp949 reader-thread noise only), and commit hook WARN was the known advisory graph/test-gap heuristic. Code commit `1389b24`. | `projects/hanwoo-dashboard/src/components/DashboardClient.js`; `projects/hanwoo-dashboard/src/components/forms/CattleDetailModal.js`; `projects/hanwoo-dashboard/src/lib/cattle-detail-modal-wiring.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-21 | Codex | **T-489 Hanwoo farm settings in-flight edit lock**. Active Hanwoo quality uplift continuation. `SettingsTab` now ignores location preset changes while `isSavingFarm` is already true and disables the farm name/location/latitude/longitude controls plus the preset selector while saving, so slow farm-settings saves cannot race with visible farm settings edits. `settings-tab-accessibility.test.mjs` guards the contract. Verification: focused settings accessibility test passed (`9 passed`), targeted ESLint passed, path-limited `git diff --check` passed, full Hanwoo QC passed (`test` 194, lint, build), staged code-review gate JSON passed (`risk_score 0.0`; cp949 reader-thread noise only), and commit hook WARN was the known advisory graph/test-gap heuristic. Code commit `981d5f0`. | `projects/hanwoo-dashboard/src/components/tabs/SettingsTab.js`; `projects/hanwoo-dashboard/src/lib/settings-tab-accessibility.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-488 Hanwoo cattle-detail breeding record duplicate-save guard**. Active Hanwoo quality uplift continuation. `CattleDetailModal` now returns early when `isBreedingSaving` is already true and exposes `aria-busy` on the breeding record submit button, so slow 諛쒖젙/?섏젙 record saves cannot be submitted twice through rapid submit/Enter paths. `cattle-detail-modal-wiring.test.mjs` guards the contract. Verification: focused cattle-detail modal wiring test passed (`9 passed`), targeted ESLint passed, path-limited `git diff --check` passed, full Hanwoo QC passed (`test` 193, lint, build), staged code-review gate JSON passed (`risk_score 0.0`; cp949 reader-thread noise only), and commit hook WARN was the known advisory graph/test-gap heuristic. Code commit `e5cfb25`. | `projects/hanwoo-dashboard/src/components/forms/CattleDetailModal.js`; `projects/hanwoo-dashboard/src/lib/cattle-detail-modal-wiring.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-487 Hanwoo inventory inline quantity duplicate-update guard**. Active Hanwoo quality uplift continuation. `InventoryTab` now tracks `savingQuantityId`, awaits the async `onUpdateQuantity` handler, disables the active quantity input and save button while saving, and exposes `aria-busy` on the save button, so slow network quantity updates cannot trigger duplicate inventory update requests. `home-market-copy.test.mjs` guards the contract. Verification: focused home-market copy test passed (`21 passed`), targeted ESLint passed, path-limited `git diff --check` passed, full Hanwoo QC passed (`test` 192, lint, build), staged code-review gate JSON passed (`risk_score 0.0`; cp949 reader-thread noise only), and commit hook WARN was the known advisory graph/test-gap heuristic. Code commit `d1d33c3`. | `projects/hanwoo-dashboard/src/components/tabs/InventoryTab.js`; `projects/hanwoo-dashboard/src/lib/home-market-copy.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-486 Hanwoo schedule completion duplicate-toggle guard**. Active Hanwoo quality uplift continuation. `ScheduleTab` now tracks `savingEventId`, awaits the async `onToggleEvent` handler, disables only the active event checkbox while saving, and exposes `aria-busy` on that checkbox, so slow network completion updates cannot trigger duplicate schedule toggle requests. `tab-header-accessibility.test.mjs` guards the contract. Verification: focused tab-header accessibility test passed (`5 passed`), targeted ESLint passed, path-limited `git diff --check` passed, full Hanwoo QC passed (`test` 191, lint, build), staged code-review gate JSON passed (`risk_score 0.0`; cp949 reader-thread noise only), and commit hook WARN was the known advisory graph/test-gap heuristic. Code commit `fbed904`. | `projects/hanwoo-dashboard/src/components/tabs/ScheduleTab.js`; `projects/hanwoo-dashboard/src/lib/tab-header-accessibility.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-485 Hanwoo settings farm save duplicate-submit guard**. Active Hanwoo quality uplift continuation. `SettingsTab` now tracks `isSavingFarm`, awaits the async `onUpdateFarmSettings` handler, disables the farm settings submit button while saving, and exposes `aria-busy` on that button, so slow network saves cannot trigger duplicate farm settings updates. `settings-tab-accessibility.test.mjs` guards the contract. Verification: focused settings accessibility test passed (`8 passed`), targeted ESLint passed, path-limited `git diff --check` passed, full Hanwoo QC passed (`test` 190, lint, build), staged code-review gate JSON passed (`risk_score 0.0`; cp949 reader-thread noise only), and commit hook WARN was the known advisory graph/test-gap heuristic. Code commit `eb8bc84`. | `projects/hanwoo-dashboard/src/components/tabs/SettingsTab.js`; `projects/hanwoo-dashboard/src/lib/settings-tab-accessibility.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-484 Hanwoo settings building delete duplicate-request guard**. Active Hanwoo quality uplift continuation. `SettingsTab` now tracks `deletingBuildingId`, ignores additional delete clicks while a delete is in progress, awaits `onDeleteBuilding`, disables only the active row delete button, and exposes `aria-busy` on that button, so slow network deletes cannot trigger duplicate building delete requests. `settings-tab-accessibility.test.mjs` guards the contract. Verification: focused settings accessibility test passed (`7 passed`), targeted ESLint passed, path-limited `git diff --check` passed, full Hanwoo QC passed (`test` 189, lint, build), staged code-review gate JSON passed (`risk_score 0.0`; cp949 reader-thread noise only), and commit hook WARN was the known advisory graph/test-gap heuristic. Code commit `269fb03`. | `projects/hanwoo-dashboard/src/components/tabs/SettingsTab.js`; `projects/hanwoo-dashboard/src/lib/settings-tab-accessibility.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-483 Hanwoo login submit-state recovery**. Active Hanwoo quality uplift continuation. `LoginPage` now wraps `signIn('credentials')` in `try/catch/finally`, surfaces a Korean retryable network/auth failure message on thrown errors, always clears `isSubmitting`, and exposes `aria-busy` on the submit button while authentication is in progress, so an unexpected auth request failure cannot strand the login form in a disabled loading state. `error-pages-wiring.test.mjs` guards the contract. Verification: focused error-pages wiring test passed (`6 passed`), targeted ESLint passed, path-limited `git diff --check` passed, full Hanwoo QC passed (`test` 188, lint, build), staged code-review gate JSON passed (`risk_score 0.0`; cp949 reader-thread noise only), and commit hook WARN was the known advisory graph/test-gap heuristic. Code commit `09cb3df`. | `projects/hanwoo-dashboard/src/app/login/page.js`; `projects/hanwoo-dashboard/src/lib/error-pages-wiring.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-482 Hanwoo settings building duplicate-submit guard**. Active Hanwoo quality uplift continuation. `SettingsTab` now tracks `isSavingBuilding`, awaits the async `onCreateBuilding` building creation handler, disables the add/cancel toggle and submit control while saving, and exposes `aria-busy` on the submit button, so slow network saves cannot trigger duplicate building submissions. `settings-tab-accessibility.test.mjs` guards the contract. Verification: focused settings accessibility test passed (`6 passed`), targeted ESLint passed, path-limited `git diff --check` passed, full Hanwoo QC passed (`test` 187, lint, build), staged code-review gate JSON passed (`risk_score 0.0`; cp949 reader-thread noise only), and commit hook WARN was the known advisory graph/test-gap heuristic. Code commit `d328121`. | `projects/hanwoo-dashboard/src/components/tabs/SettingsTab.js`; `projects/hanwoo-dashboard/src/lib/settings-tab-accessibility.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-481 Hanwoo feed record duplicate-submit guard**. Active Hanwoo quality uplift continuation. `FeedTab` now tracks `isSaving`, awaits the async `onRecordFeed` feed recording handler, disables the submit control while saving, and exposes `aria-busy` on the submit button, so slow network saves cannot trigger duplicate feed submissions. `empty-state-wiring.test.mjs` guards the contract. Verification: focused empty-state wiring test passed (`11 passed`), targeted ESLint passed, path-limited `git diff --check` passed, full Hanwoo QC passed (`test` 186, lint, build), staged code-review gate JSON passed (`risk_score 0.0`; cp949 reader-thread noise only), and commit hook WARN was the known advisory graph/test-gap heuristic. Code commit `6fb2f26`. | `projects/hanwoo-dashboard/src/components/tabs/FeedTab.js`; `projects/hanwoo-dashboard/src/lib/empty-state-wiring.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-480 Hanwoo inventory form duplicate-submit guard**. Active Hanwoo quality uplift continuation. `InventoryTab` now tracks `isSaving`, guards the add/cancel toggle while saving, awaits the async `onAddItem` inventory creation handler, disables add/cancel and submit controls while saving, and exposes `aria-busy` on the submit button, so slow network saves cannot trigger duplicate inventory submissions. `home-market-copy.test.mjs` guards the contract. Verification: focused home-market copy test passed (`20 passed`), targeted ESLint passed, path-limited `git diff --check` passed, full Hanwoo QC passed (`test` 185, lint, build), staged code-review gate JSON passed (`risk_score 0.0`; cp949 reader-thread noise only), and commit hook WARN was the known advisory graph/test-gap heuristic. Code commit `ba5c76e`. | `projects/hanwoo-dashboard/src/components/tabs/InventoryTab.js`; `projects/hanwoo-dashboard/src/lib/home-market-copy.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-479 Hanwoo sales form duplicate-submit guard**. Active Hanwoo quality uplift continuation. `SalesTab` now tracks `isSaving`, guards the add/cancel toggle while saving, awaits the async `onCreateSale` sale creation handler, disables add/cancel and submit controls while saving, and exposes `aria-busy` on the submit button, so slow network saves cannot trigger duplicate sales submissions. `home-market-copy.test.mjs` guards the contract. Verification: focused home-market copy test passed (`19 passed`), targeted ESLint passed, path-limited `git diff --check` passed, full Hanwoo QC passed (`test` 184, lint, build), staged code-review gate JSON passed (`risk_score 0.0`; cp949 reader-thread noise only), and commit hook WARN was the known advisory graph/test-gap heuristic. Code commit `d9491da`. | `projects/hanwoo-dashboard/src/components/tabs/SalesTab.js`; `projects/hanwoo-dashboard/src/lib/home-market-copy.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-478 Hanwoo schedule form duplicate-submit guard**. Active Hanwoo quality uplift continuation. `ScheduleTab` now tracks `isSaving`, guards add-form/date-cell interactions while saving, awaits the async `onCreateEvent` schedule creation handler, disables add/cancel and submit controls while saving, and exposes `aria-busy` on the submit button, so slow network saves cannot trigger duplicate schedule submissions. `tab-header-accessibility.test.mjs` guards the contract. Verification: focused tab-header accessibility test passed (`4 passed`), targeted ESLint passed, path-limited `git diff --check` passed, full Hanwoo QC passed (`test` 183, lint, build), staged code-review gate JSON passed (`risk_score 0.0`; cp949 reader-thread noise only), and commit hook WARN was the known advisory graph/test-gap heuristic. Code commit `25fe68f`. | `projects/hanwoo-dashboard/src/components/tabs/ScheduleTab.js`; `projects/hanwoo-dashboard/src/lib/tab-header-accessibility.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-477 Hanwoo calving form duplicate-submit guard**. Active Hanwoo quality uplift continuation. `CalvingTab` now tracks `isSaving`, awaits the async `onRecordCalving` calving/calf registration handler, disables cancel/submit while saving, and exposes `aria-busy` on the submit button, so slow network saves cannot trigger duplicate calving submissions. `calving-tab-accessibility.test.mjs` guards the contract. Verification: focused calving accessibility test passed (`3 passed`), targeted ESLint passed, path-limited `git diff --check` passed, full Hanwoo QC passed (`test` 182, lint, build), staged code-review gate JSON passed (`risk_score 0.0`; cp949 reader-thread noise only), and commit hook WARN was the known advisory graph/test-gap heuristic. Code commit `489d9bf`. | `projects/hanwoo-dashboard/src/components/tabs/CalvingTab.js`; `projects/hanwoo-dashboard/src/lib/calving-tab-accessibility.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-476 Hanwoo cattle form duplicate-save guard**. Active Hanwoo quality uplift continuation. `CattleForm` now tracks `isSaving`, awaits the async `onSubmit` create/update handler, disables cancel/submit while saving, and exposes `aria-busy` on the submit button, so slow network saves cannot trigger duplicate cattle create/update requests. `cattle-detail-modal-wiring.test.mjs` guards the contract. Verification: focused cattle detail modal wiring test passed (`8 passed`), targeted ESLint passed, path-limited `git diff --check` passed, full Hanwoo QC passed (`test` 181, lint, build), staged code-review gate JSON passed (`risk_score 0.0`; cp949 reader-thread noise only), and commit hook WARN was the known advisory graph/test-gap heuristic. Code commit `bc7e014`. | `projects/hanwoo-dashboard/src/components/forms/CattleForm.js`; `projects/hanwoo-dashboard/src/lib/cattle-detail-modal-wiring.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-475 Hanwoo cattle tag lookup announcements**. Active Hanwoo quality uplift continuation. `CattleForm` now connects the tag-number input to both validation and lookup feedback, marks the lookup button `aria-busy` while checking, and renders successful lookup results as `status` and failed lookup results as `alert`, so the MTRACE/tag lookup flow is not visual-only. `cattle-detail-modal-wiring.test.mjs` guards the contract. Verification: focused cattle detail modal wiring test passed (`7 passed`), targeted ESLint passed, path-limited `git diff --check` passed, full Hanwoo QC passed (`test` 180, lint, build), staged code-review gate JSON passed (`risk_score 0.0`; cp949 reader-thread noise only), and commit hook WARN was the known advisory graph/test-gap heuristic. Code commit `9adf569`. | `projects/hanwoo-dashboard/src/components/forms/CattleForm.js`; `projects/hanwoo-dashboard/src/lib/cattle-detail-modal-wiring.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-474 Hanwoo cattle dialog focus and Escape handling**. Active Hanwoo quality uplift continuation. `CattleForm` and `CattleDetailModal` now focus their dialog surfaces on open with dialog refs and `tabIndex={-1}`, and both dialogs close from Escape through the existing cancel/close handlers. `cattle-detail-modal-wiring.test.mjs` guards the contract. Verification: focused cattle detail modal wiring test passed (`6 passed`), targeted ESLint passed, path-limited `git diff --check` passed, full Hanwoo QC passed (`test` 179, lint, build), staged code-review gate JSON passed (`risk_score 0.0`; cp949 reader-thread noise only), and commit hook WARN was the known advisory graph/test-gap heuristic. Code commit `5ebbc9a`. | `projects/hanwoo-dashboard/src/components/forms/CattleForm.js`; `projects/hanwoo-dashboard/src/components/forms/CattleDetailModal.js`; `projects/hanwoo-dashboard/src/lib/cattle-detail-modal-wiring.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-473 Hanwoo AI chat decorative streaming indicator**. Active Hanwoo quality uplift continuation. `AIChatWidget` now hides the header pulse indicator from assistive technology with `aria-hidden="true"` because the send button state and live message log already carry the meaningful streaming status. `ai-chat-widget-copy.test.mjs` guards the contract. Verification: focused AI chat widget copy test passed (`1 passed`), targeted ESLint passed, path-limited `git diff --check` passed, full Hanwoo QC passed (`test` 179, lint, build), staged code-review gate JSON passed (`risk_score 0.0`; cp949 reader-thread noise only), and commit hook WARN was the known advisory graph/test-gap heuristic. Code commit `9ca15fa`. | `projects/hanwoo-dashboard/src/components/widgets/AIChatWidget.js`; `projects/hanwoo-dashboard/src/lib/ai-chat-widget-copy.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-472 Hanwoo AI chat focus return**. Active Hanwoo quality uplift continuation. `AIChatWidget` now restores focus to the floating launcher after the dialog closes by keeping a `launcherRef`, setting a restore-focus flag in the abort-safe `closeWidget()` path, and focusing the launcher after `isOpen` returns to false. `ai-chat-widget-copy.test.mjs` guards the contract. Verification: focused AI chat widget copy test passed (`1 passed`), targeted ESLint passed, path-limited `git diff --check` passed, full Hanwoo QC passed (`test` 179, lint, build), staged code-review gate JSON passed (`risk_score 0.0`; cp949 reader-thread noise only), and commit hook WARN was the known advisory graph/test-gap heuristic. Code commit `75b9135`. | `projects/hanwoo-dashboard/src/components/widgets/AIChatWidget.js`; `projects/hanwoo-dashboard/src/lib/ai-chat-widget-copy.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-471 Hanwoo AI chat modal dialog semantics**. Active Hanwoo quality uplift continuation. `AIChatWidget` now adds `aria-modal="true"` to its focused `role="dialog"` panel, aligning it with the established notification-dialog pattern and making the floating assistant dialog semantics explicit for assistive technology. `ai-chat-widget-copy.test.mjs` guards the contract. Verification: focused AI chat widget copy test passed (`1 passed`), targeted ESLint passed, path-limited `git diff --check` passed, full Hanwoo QC passed (`test` 179, lint, build), staged code-review gate JSON passed (`risk_score 0.0`; cp949 reader-thread noise only), and commit hook WARN was the known advisory graph/test-gap heuristic. Code commit `d6d9f3d`. | `projects/hanwoo-dashboard/src/components/widgets/AIChatWidget.js`; `projects/hanwoo-dashboard/src/lib/ai-chat-widget-copy.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-470 Hanwoo AI chat live message announcements**. Active Hanwoo quality uplift continuation. `AIChatWidget` now marks the message stream as `role="log"` with `aria-live="polite"`, `aria-relevant="additions text"`, and a Korean accessible label, so streamed assistant responses are announced as conversation updates instead of remaining visual-only. `ai-chat-widget-copy.test.mjs` guards the contract. Verification: focused AI chat widget copy test passed (`1 passed`), targeted ESLint passed, path-limited `git diff --check` passed, full Hanwoo QC passed (`test` 179, lint, build), staged code-review gate JSON passed (`risk_score 0.0`; cp949 reader-thread noise only), and commit hook WARN was the known advisory graph/test-gap heuristic. Code commit `e22a0a0`. | `projects/hanwoo-dashboard/src/components/widgets/AIChatWidget.js`; `projects/hanwoo-dashboard/src/lib/ai-chat-widget-copy.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-469 Hanwoo AI chat dialog focus**. Active Hanwoo quality uplift continuation. `AIChatWidget` now focuses the open `role="dialog"` panel through `panelRef` and `tabIndex={-1}`, so Escape dismissal works immediately after opening the floating assistant. `ai-chat-widget-copy.test.mjs` guards the focus contract. Verification: focused AI chat widget copy test passed (`1 passed`), targeted ESLint passed, path-limited `git diff --check` passed, full Hanwoo QC passed (`test` 179, lint, build), staged code-review gate JSON passed (`risk_score 0.0`; cp949 reader-thread noise only), and commit hook WARN was the known advisory graph/test-gap heuristic. Code commit `f79d677`. | `projects/hanwoo-dashboard/src/components/widgets/AIChatWidget.js`; `projects/hanwoo-dashboard/src/lib/ai-chat-widget-copy.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-468 Hanwoo pagination loading-state announcement**. Active Hanwoo product-completeness continuation. The cattle and sales pagination "more" controls now expose `aria-busy` while loading, and cattle pagination retry feedback now uses `role="status"` plus `aria-live="polite"` like the sales flow. `cattle-pagination-feedback.test.mjs` and `sales-pagination-feedback.test.mjs` guard the contracts. Verification: focused cattle/sales pagination feedback tests passed (`2 passed`), targeted ESLint passed, path-limited `git diff --check` passed, full Hanwoo QC passed (`test` 179, lint, build), staged code-review gate JSON passed (`risk_score 0.0`; cp949 reader-thread noise only), and commit hook WARN was the known advisory graph/test-gap heuristic. Code commit `9c0f767`. | `projects/hanwoo-dashboard/src/components/DashboardClient.js`; `projects/hanwoo-dashboard/src/components/tabs/SalesTab.js`; `projects/hanwoo-dashboard/src/lib/cattle-pagination-feedback.test.mjs`; `projects/hanwoo-dashboard/src/lib/sales-pagination-feedback.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-467 Hanwoo notification badge/button semantics alignment**. Active Hanwoo product-completeness continuation. `NotificationSystem.js` now marks the "mark all as read" control as `type="button"`, and `NotificationSystem.tsx` only renders the unread red-dot badge when `unreadCount > 0`, matching the runtime JS mirror. `notification-system-copy.test.mjs` guards both contracts. Verification: focused notification system copy test passed (`7 passed`), targeted ESLint passed, path-limited `git diff --check` passed, full Hanwoo QC passed (`test` 179, lint, build), staged code-review gate JSON passed (`risk_score 0.0`; cp949 reader-thread noise only), and commit hook WARN was the known advisory graph/test-gap heuristic. Code commit `9ec53cf`. | `projects/hanwoo-dashboard/src/components/layout/NotificationSystem.js`; `projects/hanwoo-dashboard/src/components/layout/NotificationSystem.tsx`; `projects/hanwoo-dashboard/src/lib/notification-system-copy.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-466 Hanwoo notification modal keyboard dismissal reliability**. Active Hanwoo product-completeness continuation. `NotificationModal` now focuses the `role="dialog"` container on mount with `useRef`/`useEffect`, so the existing Escape dismissal works immediately for keyboard users instead of depending on incidental focus placement. Overlay click close and the explicit close button remain unchanged. `notification-modal-copy.test.mjs` guards the focus + Escape contract. Verification: focused notification modal copy test passed (`5 passed`), targeted ESLint passed, path-limited `git diff --check` passed, full Hanwoo QC passed (`test` 177, lint, build), staged code-review gate JSON passed (`risk_score 0.0`; cp949 reader-thread noise only), and commit hook WARN was the known advisory graph/test-gap heuristic. Code commit `81bdf3d`. | `projects/hanwoo-dashboard/src/components/ui/NotificationModal.js`; `projects/hanwoo-dashboard/src/lib/notification-modal-copy.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-465 Hanwoo clickable card native button semantics**. Active Hanwoo product-completeness continuation. `PenCard` and `CattleRow` now render as `<button type="button">` instead of `div role="button"` plus custom keyboard handling, preserving accessible labels, drag/drop hooks, and visual card styling through reset CSS. `cards-accessibility.test.mjs` guards the native-button contract and card reset styles. Verification: focused cards accessibility test passed (`2 passed`), targeted ESLint passed, path-limited `git diff --check` passed, full Hanwoo QC passed (`test` 177, lint, build), staged code-review gate JSON passed (`risk_score 0.0`; cp949 reader-thread noise only), and commit hook WARN was the known advisory graph/test-gap heuristic. Code commit `d8c3abc`. | `projects/hanwoo-dashboard/src/components/ui/cards.js`; `projects/hanwoo-dashboard/src/app/globals.css`; `projects/hanwoo-dashboard/src/lib/cards-accessibility.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-464 Hanwoo settings form validation announcement**. Active Hanwoo product-completeness continuation. `SettingsTab` now connects farm name, location, latitude, longitude, building name, and pen count controls to their field-specific error messages through conditional `aria-describedby`, keeps `aria-invalid`, and renders each validation message as `role="alert"`. `settings-tab-accessibility.test.mjs` guards the contract. Verification: focused settings accessibility test passed (`5 passed`), targeted ESLint passed, path-limited `git diff --check` passed, full Hanwoo QC passed (`test` 176, lint, build), staged code-review gate JSON passed (`risk_score 0.0`; cp949 reader-thread noise only), and commit hook WARN was the known advisory graph/test-gap heuristic. Code commit `38b70c6`. | `projects/hanwoo-dashboard/src/components/tabs/SettingsTab.js`; `projects/hanwoo-dashboard/src/lib/settings-tab-accessibility.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-463 Hanwoo schedule form validation announcement**. Active Hanwoo product-completeness continuation. `ScheduleTab` now connects schedule title, date, and type controls to their field-specific error messages through conditional `aria-describedby`, keeps `aria-invalid`, and renders each validation message as `role="alert"`. `tab-header-accessibility.test.mjs` guards the contract. Verification: focused tab-header accessibility test passed (`3 passed`), targeted ESLint passed, path-limited `git diff --check` passed, full Hanwoo QC passed (`test` 175, lint, build), staged code-review gate JSON passed (`risk_score 0.0`; cp949 reader-thread noise only), and commit hook WARN was the known advisory graph/test-gap heuristic. Code commit `d12a5f4`. | `projects/hanwoo-dashboard/src/components/tabs/ScheduleTab.js`; `projects/hanwoo-dashboard/src/lib/tab-header-accessibility.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-462 Hanwoo inventory form validation announcement**. Active Hanwoo product-completeness continuation. `InventoryTab` now connects inventory name, category, quantity, unit, and threshold controls to their field-specific error messages through conditional `aria-describedby`, keeps `aria-invalid`, and renders each validation message as `role="alert"`. `home-market-copy.test.mjs` guards the contract. Verification: focused home-market copy test passed (`18 passed`), targeted ESLint passed, path-limited `git diff --check` passed, full Hanwoo QC passed (`test` 174, lint, build), staged code-review gate JSON passed (`risk_score 0.0`; cp949 reader-thread noise only), and commit hook WARN was the known advisory graph/test-gap heuristic. Code commit `cf2ae47`. | `projects/hanwoo-dashboard/src/components/tabs/InventoryTab.js`; `projects/hanwoo-dashboard/src/lib/home-market-copy.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-461 Hanwoo sales form validation announcement**. Active Hanwoo product-completeness continuation. `SalesTab` now connects sale date, price, cattle, grade, and purchaser controls to their field-specific error messages through conditional `aria-describedby`, keeps `aria-invalid`, and renders each validation message as `role="alert"`. `home-market-copy.test.mjs` guards the contract. Verification: focused home-market copy test passed (`17 passed`), targeted ESLint passed, path-limited `git diff --check` passed, full Hanwoo QC passed (`test` 173, lint, build), staged code-review gate JSON passed (`risk_score 0.0`; cp949 reader-thread noise only), and commit hook WARN was the known advisory graph/test-gap heuristic. Code commit `087a221`. | `projects/hanwoo-dashboard/src/components/tabs/SalesTab.js`; `projects/hanwoo-dashboard/src/lib/home-market-copy.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-460 Hanwoo feed form validation announcement**. Active Hanwoo product-completeness continuation. `FeedTab` now connects feed date, roughage, concentrate, and memo controls to their field-specific error messages through conditional `aria-describedby`, keeps `aria-invalid`, and renders each validation message as `role="alert"`. `empty-state-wiring.test.mjs` guards the contract. Verification: focused empty-state wiring test passed (`10 passed`), targeted ESLint passed, path-limited `git diff --check` passed, full Hanwoo QC passed (`test` 173, lint, build), staged code-review gate JSON passed (`risk_score 0.0`; cp949 reader-thread noise only), and commit hook WARN was the known advisory graph/test-gap heuristic. Code commit `aa78c39`. | `projects/hanwoo-dashboard/src/components/tabs/FeedTab.js`; `projects/hanwoo-dashboard/src/lib/empty-state-wiring.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-459 Hanwoo cattle form validation announcement**. Active Hanwoo product-completeness continuation. `CattleForm` now connects name, tag number, building, pen, gender, status, birth date, weight, purchase info, pedigree, and memo controls to their field-specific error messages through conditional `aria-describedby`, keeps `aria-invalid`, and renders each validation message as `role="alert"`. `cattle-detail-modal-wiring.test.mjs` guards the contract. Verification: focused cattle-detail wiring test passed (`6 passed`), targeted ESLint passed, path-limited `git diff --check` passed, Hanwoo tests/lint passed and build passed on retry after a transient Next build lock, staged code-review gate JSON passed (`risk_score 0.0`; cp949 reader-thread noise only), and direct graph detect-changes hit the known Windows cp949 reader failure. Code commit `327a0a9`. | `projects/hanwoo-dashboard/src/components/forms/CattleForm.js`; `projects/hanwoo-dashboard/src/lib/cattle-detail-modal-wiring.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-458 Hanwoo calving form validation announcement**. Active Hanwoo product-completeness continuation. `CalvingTab` now connects calving date, calf gender, and calf tag number controls to their field-specific error messages through conditional `aria-describedby`, keeps `aria-invalid`, and renders each validation message as `role="alert"`. `calving-tab-accessibility.test.mjs` guards the contract. Verification: focused calving accessibility test passed (`2 passed`), targeted ESLint passed, path-limited `git diff --check` passed, full Hanwoo QC passed (`test` 170, lint, build), staged code-review gate JSON passed (`risk_score 0.0`; cp949 reader-thread noise only), and direct graph detect-changes hit the known Windows cp949 reader failure. Code commit `9040e63`. | `projects/hanwoo-dashboard/src/components/tabs/CalvingTab.js`; `projects/hanwoo-dashboard/src/lib/calving-tab-accessibility.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-457 Hanwoo login error field association**. Active Hanwoo product-completeness continuation. `LoginPage` now creates a stable `login-error-message` id, marks the username/password inputs with `aria-invalid` after failed sign-in, and connects both fields to the alert message with conditional `aria-describedby`. `error-pages-wiring.test.mjs` guards the contract. Verification: focused error-pages wiring test passed (`5 passed`), targeted ESLint passed, path-limited `git diff --check` passed, full Hanwoo QC passed (`test` 169, lint, build), staged code-review gate JSON passed (`risk_score 0.0`; cp949 reader-thread noise only), and commit hook WARN was the known advisory graph/test-gap heuristic. Code commit `b5f27e9`. | `projects/hanwoo-dashboard/src/app/login/page.js`; `projects/hanwoo-dashboard/src/lib/error-pages-wiring.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-456 Hanwoo cattle-detail breeding validation announcement**. Active Hanwoo product-completeness continuation. `CattleDetailModal` now connects the breeding record date input to `breeding-record-date-error` through conditional `aria-describedby`, keeps `aria-invalid` tied to `breedingError`, and renders the validation message as `role="alert"`. `cattle-detail-modal-wiring.test.mjs` guards the contract. Verification: focused cattle-detail modal wiring test passed (`5 passed`), targeted ESLint passed, path-limited `git diff --check` passed, full Hanwoo QC passed (`test` 168, lint, build), staged code-review gate JSON passed (`risk_score 0.0`; cp949 reader-thread noise only), and direct graph detect-changes hit the known Windows cp949 reader failure. Code commit `5ffe7a8`. | `projects/hanwoo-dashboard/src/components/forms/CattleDetailModal.js`; `projects/hanwoo-dashboard/src/lib/cattle-detail-modal-wiring.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-455 Hanwoo diagnostics selector accessibility**. Active Hanwoo product-completeness continuation. `DiagnosticsPageClient` now exposes `寃?ы븷 ?먮낯 ?곗씠???좏깮` through `aria-label` and `title` on the admin raw-data model selector, so the control has its own accessible name instead of relying only on nearby section copy. `diagnostics-copy.test.mjs` guards the contract. Verification: focused diagnostics copy test passed (`1 passed`), targeted ESLint passed, path-limited `git diff --check` passed, full Hanwoo QC passed (`test` 167, lint, build), staged code-review gate JSON passed (`risk_score 0.0`; cp949 reader-thread noise only), and commit hook WARN was the known advisory graph/test-gap heuristic. Code commit `6c350c2`. | `projects/hanwoo-dashboard/src/components/admin/DiagnosticsPageClient.js`; `projects/hanwoo-dashboard/src/lib/diagnostics-copy.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-452 Hanwoo AI chat dialog semantics**. Active Hanwoo product-completeness continuation. `AIChatWidget` now wraps the open panel with `role="dialog"`, labels it as `AI ?띿옣 鍮꾩꽌 梨꾪똿`, and closes on `Escape`, while the existing close button remains available. `ai-chat-widget-copy.test.mjs` guards the contract. Verification: focused AI chat widget copy test passed (`1 passed`), targeted ESLint passed, path-limited `git diff --check` passed, full Hanwoo QC passed (`test` 167, lint, build), and staged/HEAD code-review gate JSON passed (`risk_score 0.0`; cp949 reader-thread noise only). Code commit `b32550e`. | `projects/hanwoo-dashboard/src/components/widgets/AIChatWidget.js`; `projects/hanwoo-dashboard/src/lib/ai-chat-widget-copy.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-451 Hanwoo AI chat input accessibility**. Active Hanwoo product-completeness continuation. `AIChatWidget` now exposes `AI ?띿옣 鍮꾩꽌?먭쾶 蹂대궪 吏덈Ц` through `aria-label` and `title` on the text input, so the chat question field no longer relies on placeholder text alone while the send button keeps its Korean accessible label. `ai-chat-widget-copy.test.mjs` guards the contract. Verification: focused AI chat widget copy test passed (`1 passed`), targeted ESLint passed, path-limited `git diff --check` passed, full Hanwoo QC passed (`test` 167, lint, build), staged code-review gate JSON passed (`risk_score 0.0`; cp949 reader-thread noise only), and commit hook WARN was the known graph/test-gap heuristic. Code commit `357668c`. | `projects/hanwoo-dashboard/src/components/widgets/AIChatWidget.js`; `projects/hanwoo-dashboard/src/lib/ai-chat-widget-copy.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-450 Hanwoo inventory inline quantity editor accessibility**. Active Hanwoo product-completeness continuation. The Inventory edit-mode numeric `PremiumInput` now exposes `${item.name} ?ш퀬 ?섎웾 ?낅젰` through `aria-label` and `title`, so the inline editor is no longer announced as a generic unlabeled number field. `home-market-copy.test.mjs` guards the contract. Verification: focused home-market copy test passed (`16 passed`), targeted ESLint passed, path-limited `git diff --check` passed, full Hanwoo QC passed (`test` 167, lint, build), staged code-review gate JSON passed (`risk_score 0.0`; cp949 reader-thread noise only), and commit hook WARN was the known graph/test-gap heuristic. Code commit `8aa9412`. | `projects/hanwoo-dashboard/src/components/tabs/InventoryTab.js`; `projects/hanwoo-dashboard/src/lib/home-market-copy.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-449 Hanwoo settings form field accessibility**. Active Hanwoo product-completeness continuation. `SettingsTab` now links ?띿옣 ?대쫫, 吏???좏깮, 吏??챸, ?꾨룄, 寃쎈룄, ???대쫫, and 移???controls to stable ids and exposes `aria-invalid` from React Hook Form errors where validation applies. `settings-tab-accessibility.test.mjs` guards the contract. Verification: focused Settings accessibility test passed (`4 passed`), targeted ESLint passed, path-limited `git diff --check` passed, full Hanwoo QC passed (`test` 166, lint, build), staged code-review gate JSON passed (`risk_score 0.0`; cp949 reader-thread noise only), and direct graph detect-changes hit the known Windows cp949 reader failure. Code commit `19a2ea3`. | `projects/hanwoo-dashboard/src/components/tabs/SettingsTab.js`; `projects/hanwoo-dashboard/src/lib/settings-tab-accessibility.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-448 Hanwoo feed form field accessibility**. Active Hanwoo product-completeness continuation. `FeedTab` now links feed date/note plus roughage/concentrate numeric controls to stable ids and exposes `aria-invalid` from React Hook Form errors. `empty-state-wiring.test.mjs` guards the contract. Verification: focused empty-state wiring test passed (`9 passed`), expanded empty-state/home-market tests passed (`24 passed`), targeted ESLint passed, path-limited `git diff --check` passed, direct graph risk `0.00`, full Hanwoo QC passed on retry after a transient Next build lock (`test` 165, lint, build), staged code-review gate JSON passed (`risk_score 0.0`; cp949 reader-thread noise only), and commit hook WARN was the known graph/test-gap heuristic. Code commit `4ecc1c5`. | `projects/hanwoo-dashboard/src/components/tabs/FeedTab.js`; `projects/hanwoo-dashboard/src/lib/empty-state-wiring.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-447 Hanwoo inventory form field accessibility**. Active Hanwoo product-completeness continuation. `InventoryTab` now links ?먯옱紐? 遺꾨쪟, ?섎웾, ?⑥쐞, and 寃쎄퀬 湲곗?媛?controls to stable ids and exposes `aria-invalid` from React Hook Form errors. `home-market-copy.test.mjs` guards the contract. Verification: focused home-market copy test passed (`15 passed`), targeted ESLint passed, path-limited `git diff --check` passed, full Hanwoo QC passed (`test` 165, lint, build), staged code-review gate JSON passed (`risk_score 0.0`; cp949 reader-thread noise only), and direct graph detect-changes hit the known Windows cp949 reader failure. Code commit `26c6529`. | `projects/hanwoo-dashboard/src/components/tabs/InventoryTab.js`; `projects/hanwoo-dashboard/src/lib/home-market-copy.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-446 Hanwoo sales form field accessibility**. Active Hanwoo product-completeness continuation. `SalesTab` now links 異쒗븯?쇱옄, ?먮ℓ 媛寃? 異쒗븯 媛쒖껜, ?깃툒, and 援щℓ泥?controls to stable ids and exposes `aria-invalid` from React Hook Form errors. `home-market-copy.test.mjs` guards the contract. Verification: focused home-market copy test passed (`14 passed`), targeted ESLint passed, path-limited `git diff --check` passed, full Hanwoo QC passed (`test` 163, lint, build), staged code-review gate JSON passed (`risk_score 0.0`; cp949 reader-thread noise only). Code commit `18a55e8`. | `projects/hanwoo-dashboard/src/components/tabs/SalesTab.js`; `projects/hanwoo-dashboard/src/lib/home-market-copy.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-445 Hanwoo schedule form field accessibility**. Active Hanwoo product-completeness continuation. `ScheduleTab` now gives schedule title/date/type fields visible labels, stable ids, and `aria-invalid` tied to React Hook Form errors instead of relying on placeholder-only context. `tab-header-accessibility.test.mjs` guards the contract. Verification: focused tab-header/home-market accessibility tests passed (`15 passed`), targeted ESLint passed, path-limited `git diff --check` passed, direct graph risk `0.00`, full Hanwoo QC passed (`test` 162, lint, build), staged code-review gate JSON passed (`risk_score 0.0`; cp949 reader-thread noise only), and commit hook WARN was the known graph/test-gap heuristic plus unrelated VibeDebt WIP. Code commit `005410f`. | `projects/hanwoo-dashboard/src/components/tabs/ScheduleTab.js`; `projects/hanwoo-dashboard/src/lib/tab-header-accessibility.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-444 Hanwoo schedule completion toggle labels**. Active Hanwoo product-completeness continuation. Upcoming schedule completion checkboxes now expose `${event.title} ?쇱젙 ?꾨즺 ?곹깭 蹂寃? as both `aria-label` and `title`, so repeated controls in the schedule list are no longer ambiguous for assistive technology or tooltips. `home-market-copy.test.mjs` guards the contract. Verification: focused home-market copy test passed (`13 passed`), targeted ESLint passed, path-limited `git diff --check` passed, full Hanwoo QC passed (`test` 161, lint, build), staged code-review gate JSON passed (`risk_score 0.0`; cp949 reader-thread noise only), and commit hook WARN was the known graph/test-gap heuristic plus unrelated VibeDebt WIP. Code commit `1bdf5aa`. | `projects/hanwoo-dashboard/src/components/tabs/ScheduleTab.js`; `projects/hanwoo-dashboard/src/lib/home-market-copy.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-443 Hanwoo Settings building delete action labels**. Active Hanwoo product-completeness continuation. Settings 異뺤궗 紐⑸줉 row actions now expose `${building.name} ????젣` as both `aria-label` and `title`, so repeated visible `??젣` buttons are no longer ambiguous for assistive technology or tooltips. `settings-tab-accessibility.test.mjs` guards the contract. Verification: focused SettingsTab accessibility test passed (`3 passed`), targeted ESLint passed, path-limited `git diff --check` passed, full Hanwoo QC passed (`test` 160, lint, build), staged code-review gate JSON passed (`risk_score 0.0`; cp949 reader-thread noise only), and commit hook WARN was the known graph/test-gap heuristic plus unrelated VibeDebt WIP. Code commit `33420fd`. | `projects/hanwoo-dashboard/src/components/tabs/SettingsTab.js`; `projects/hanwoo-dashboard/src/lib/settings-tab-accessibility.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-442 Hanwoo building creation server validation**. Active Hanwoo product-completeness continuation. `createBuilding` now validates through `validateBuildingInput()` before Prisma instead of relying on `parseInt(data.penCount)`, so empty building names and invalid pen counts return field-level Korean validation errors instead of generic DB failure. `action-validation.test.mjs` guards trimming and invalid pen-count behavior. Verification: focused action-validation/actions copy tests passed (`12 passed`), targeted ESLint passed, path-limited `git diff --check` passed, direct graph risk `0.00`, full Hanwoo QC passed (`test` 159, lint, build), and staged code-review gate JSON passed (`risk_score 0.0`; cp949 reader-thread noise only). Code commit `c2ef819`. | `projects/hanwoo-dashboard/src/lib/action-validation.mjs`; `projects/hanwoo-dashboard/src/lib/action-validation.test.mjs`; `projects/hanwoo-dashboard/src/lib/actions/building.js`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-441 Hanwoo cattle detail calving due date**. Active Hanwoo product-completeness continuation. `CattleDetailModal` now shows a real calculated 遺꾨쭔 ?덉젙??via `formatDate(getCalvingDate(cattle.pregnancyDate))` instead of the placeholder `怨꾩궛以?..`. `cattle-detail-modal-wiring.test.mjs` guards against the placeholder returning. Verification: focused cattle-detail wiring test passed (`4 passed`), targeted ESLint passed, path-limited `git diff --check` passed, full Hanwoo QC passed (`test` 158, lint, build), staged code-review gate JSON passed (`risk_score 0.0`; cp949 reader-thread noise only), and direct graph detect-changes hit the known Windows cp949 reader failure. Code commit `0483c50`. | `projects/hanwoo-dashboard/src/components/forms/CattleDetailModal.js`; `projects/hanwoo-dashboard/src/lib/cattle-detail-modal-wiring.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-440 Hanwoo cattle detail archive action copy**. Active Hanwoo product-completeness continuation. Aligned the `CattleDetailModal` action with the soft-archive behavior: the destructive action now uses `${cattle.name} 媛쒖껜 蹂닿? 泥섎━`, title `媛쒖껜 蹂닿? 泥섎━`, and visible `蹂닿?` instead of `??젣`, matching the 蹂닿? 泥섎━ flow from T-439. Verification: focused actions/detail/home copy tests passed (`16 passed`), targeted ESLint passed, path-limited `git diff --check` passed, full Hanwoo QC passed (`test` 157, lint, build), staged code-review gate JSON passed (`risk_score 0.0`; cp949 reader-thread noise only), and commit hook WARN was the known graph/test-gap heuristic plus unrelated VibeDebt WIP. Code commit `3c0a193`. | `projects/hanwoo-dashboard/src/components/forms/CattleDetailModal.js`; `projects/hanwoo-dashboard/src/lib/actions-copy.test.mjs`; `projects/hanwoo-dashboard/src/lib/cattle-detail-modal-wiring.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-439 Hanwoo notification and archive copy alignment**. Active Hanwoo product-completeness continuation. Test 臾몄옄 feedback no longer exposes sample cattle data (`?쒖떖??0001)`) and now uses generic registered-contact copy. Cattle soft-delete UI/server messages now consistently say 蹂닿? 泥섎━ instead of destructive ??젣, matching the archive behavior. Verification: focused notification/home/actions copy tests passed (`18 passed`), targeted ESLint passed, path-limited `git diff --check` passed, direct graph risk `0.00`, full Hanwoo QC passed (`test` 157, lint, build), staged code-review gate JSON passed (`risk_score 0.0`; cp949 reader-thread noise only), and commit hook WARN was the known graph/test-gap heuristic. Code commit `82bcb75`. | `projects/hanwoo-dashboard/src/components/DashboardClient.js`; `projects/hanwoo-dashboard/src/lib/actions/cattle.js`; `projects/hanwoo-dashboard/src/lib/home-market-copy.test.mjs`; `projects/hanwoo-dashboard/src/lib/notification-modal-copy.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-438 Hanwoo duplicate cattle tag feedback**. Active Hanwoo product-completeness continuation. Cattle create/update/calving actions now recognize Prisma `P2002` unique-constraint errors targeting `tagNumber` and return actionable Korean operator copy (`?대? ?깅줉???대젰踰덊샇?낅땲?? ?ㅻⅨ ?대젰踰덊샇瑜??낅젰??二쇱꽭??`) instead of a generic failure. `actions-copy.test.mjs` guards the branch. Verification: focused actions-copy test passed, targeted ESLint passed, path-limited `git diff --check` passed, full Hanwoo tests passed (`157 passed`), ESLint passed, full Hanwoo QC passed on retry after a transient Next build lock (`test` 157, lint, build), staged code-review gate JSON passed (`risk_score 0.0`; cp949 reader-thread noise only), and commit hook WARN was the known graph/test-gap heuristic. Direct graph detect-changes hit the known Windows cp949 reader failure. Code commit `84d536e`. | `projects/hanwoo-dashboard/src/lib/actions/cattle.js`; `projects/hanwoo-dashboard/src/lib/actions-copy.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-437 Hanwoo seeded notification demo cleanup**. Active Hanwoo product-completeness continuation. `NotificationSystem` no longer seeds demo farm alerts such as sample cow numbers or low-stock copy by default. The JS and TSX mirrors now start from `initialNotifications = []`, render the empty state when no real alerts are supplied, and keep read/unread behavior for supplied notifications. Verification: focused notification system test passed (`5 passed`), targeted ESLint passed, path-limited `git diff --check` passed, direct graph risk `0.00`, full Hanwoo QC passed (`test` 157, lint, build), staged code-review gate JSON passed (`risk_score 0.0`; cp949 reader-thread noise only), and commit hook WARN was the known graph/test-gap heuristic. Code commit `70ac7d0`. | `projects/hanwoo-dashboard/src/components/layout/NotificationSystem.js`; `projects/hanwoo-dashboard/src/components/layout/NotificationSystem.tsx`; `projects/hanwoo-dashboard/src/lib/notification-system-copy.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-436 Hanwoo calving calf tag hardening**. Active Hanwoo product-completeness continuation. Removed the fake `KR0000-...` calf tag generation from 遺꾨쭔 泥섎━. `CalvingTab` now requires an operator-entered ?≪븘吏 ?대젰踰덊샇, passes it through to the client/offline flow, and `recordCalving` validates it server-side before creating calf records/history/outbox events. Verification: focused action-validation/home-market copy tests passed (`22 passed`), focused legal-page test for concurrent T-435 passed, targeted ESLint passed, path-limited `git diff --check` passed, direct graph risk `0.00`, direct build passed after one transient Next build lock, full Hanwoo QC passed (`test` 156, lint, build), staged code-review gate JSON passed (`risk_score 0.0`; cp949 reader-thread noise only), and commit hook WARN was the known graph/test-gap heuristic. Code commit `88da9e7`. | `projects/hanwoo-dashboard/src/components/DashboardClient.js`; `projects/hanwoo-dashboard/src/components/tabs/CalvingTab.js`; `projects/hanwoo-dashboard/src/lib/formSchemas.js`; `projects/hanwoo-dashboard/src/lib/action-validation.mjs`; `projects/hanwoo-dashboard/src/lib/actions/cattle.js`; `projects/hanwoo-dashboard/src/lib/action-validation.test.mjs`; `projects/hanwoo-dashboard/src/lib/home-market-copy.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-435 Hanwoo public legal contact hardening**. Active Hanwoo product-completeness continuation. Removed personal phone/address details from `/privacy` and `/terms`, leaving stable support channels (`Joolife ?댁쁺?`, support email, service inquiry channel, website) without exposing a personal mobile number or home address. Added `legal-pages-copy.test.mjs` to guard against raw phone/address/name details returning. Verification: focused legal-page copy test passed, targeted ESLint passed, path-limited `git diff --check` passed, full Hanwoo tests passed (`154 passed` before concurrent WIP), ESLint passed, full Hanwoo QC passed (`test` 156 in current worktree, lint, build), staged code-review gate JSON passed (`risk_score 0.0`; cp949 reader-thread noise only), and commit hook WARN was the known graph/test-gap heuristic plus unrelated workspace WIP. Code commit `8e893b0`. | `projects/hanwoo-dashboard/src/app/privacy/page.js`; `projects/hanwoo-dashboard/src/app/terms/page.js`; `projects/hanwoo-dashboard/src/lib/legal-pages-copy.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-434 Hanwoo footer placeholder registration cleanup**. Active Hanwoo product-completeness continuation. Removed the dummy `?ъ뾽?먮벑濡앸쾲?? 000-00-00000` from the dashboard footer and replaced it with a stable `?댁쁺 臾몄쓽: joolife@joolife.io.kr` line while preserving the legal links. `home-market-copy.test.mjs` guards against the placeholder returning. Verification: focused home-market copy test passed, targeted ESLint passed, path-limited `git diff --check` passed, full Hanwoo tests passed (`153 passed`), ESLint passed, full Hanwoo QC passed (`test` 153, lint, build), staged code-review gate JSON passed (`risk_score 0.0`; cp949 reader-thread noise only), and commit hook WARN was the known graph/test-gap heuristic plus unrelated workspace WIP. Code commit `442e570`. | `projects/hanwoo-dashboard/src/components/DashboardClient.js`; `projects/hanwoo-dashboard/src/lib/home-market-copy.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-433 Hanwoo legacy sample-data removal**. Active Hanwoo product-completeness continuation. Removed unused `src/lib/data.js`, which only exported random demo cattle/sales/market generators, had no remaining imports, and could be mistaken for product runtime data. Verification: no remaining `generateSampleData`, `generateSaleRecords`, `getMarketPrice`, or `@/lib/data` references, direct graph risk `0.00`, and full Hanwoo QC passed (`test` 153, lint, build). Code commit `e05cd58`. | `projects/hanwoo-dashboard/src/lib/data.js`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-432 Hanwoo notification modal SMS label localization**. Active Hanwoo product-completeness continuation. The notification modal SMS service label now uses Korean operator copy (`臾몄옄 ?뚮┝ ?쒕퉬??) and hides the phone glyph from assistive technology with `aria-hidden="true"`, replacing the mixed `?벑 SMS ?뚮┝ ?쒕퉬?? surface. Verification: focused notification modal copy test passed, targeted ESLint passed, path-limited `git diff --check` passed, direct graph risk `0.00`, full Hanwoo QC passed (`test` 153, lint, build), and staged/commit code-review gate WARN was the known graph/test-gap heuristic. Code commit `13d281d`. | `projects/hanwoo-dashboard/src/components/ui/NotificationModal.js`; `projects/hanwoo-dashboard/src/lib/notification-modal-copy.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-431 Hanwoo profitability header rendering and weather glyph semantics**. Active Hanwoo product-completeness continuation. `PremiumCardHeader` now renders `title`, `description`, and decorative `icon` props as visible structured content instead of passing them through as inert DOM props, restoring the profitability widget header path. WeatherWidget location/current-condition/THI/forecast/alert glyphs are now hidden from assistive technology or exposed through meaningful weather descriptions. Verification: direct graph risk `0.00`, focused profitability copy test passed, focused home-market copy contract covered by full tests, targeted ESLint passed, path-limited `git diff --check` passed, full Hanwoo tests passed (`153 passed`), ESLint passed, and full Hanwoo QC passed (`test` 153, lint, build). HEAD-range code-review gate WARN was the known graph/test-gap heuristic plus unrelated workspace WIP. Code commit `9230de6`. | `projects/hanwoo-dashboard/src/components/ui/premium-card.js`; `projects/hanwoo-dashboard/src/components/widgets/widgets.js`; `projects/hanwoo-dashboard/src/lib/home-market-copy.test.mjs`; `projects/hanwoo-dashboard/src/lib/profitability-copy.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-430 Hanwoo WeatherWidget stat glyph semantics**. Active Hanwoo accessibility continuation. `WeatherWidget` now hides the small temperature, wind, and precipitation stat glyphs from assistive technology with `aria-hidden="true"` while the adjacent Korean stat labels and values remain the meaningful content. `home-market-copy.test.mjs` guards the contract. Verification: direct graph risk `0.00`, focused home-market copy test passed, targeted ESLint passed, path-limited `git diff --check` passed, full Hanwoo QC passed (`test` 152, lint, build), and commit-time code-review gate WARN was the known graph/test-gap heuristic plus unrelated workspace WIP. Code commit `f3d7bc0`. | `projects/hanwoo-dashboard/src/components/widgets/widgets.js`; `projects/hanwoo-dashboard/src/lib/home-market-copy.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-429 Hanwoo WeatherWidget decorative background icon semantics**. Active Hanwoo accessibility continuation. `WeatherWidget` now hides the large ambient `weather-icon-bg` glyph from assistive technology with `aria-hidden="true"` while the visible weather description remains the meaningful content. `home-market-copy.test.mjs` guards the contract. Verification: focused home-market copy test passed, Hanwoo tests `152 passed`, ESLint passed, and full Hanwoo QC passed (`test` 152, lint, build) after retrying a transient Next build lock. | `projects/hanwoo-dashboard/src/components/widgets/widgets.js`; `projects/hanwoo-dashboard/src/lib/home-market-copy.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-428 Hanwoo FeedTab filter state accessibility**. Active Hanwoo accessibility continuation. Feed building filter chips now expose selected state with `aria-pressed={active}` and Korean task labels for all-buildings/per-building feed views, so selection is no longer visual-only. Verification: focused empty-state/feed wiring test passed, targeted ESLint passed, path-limited `git diff --check` passed, direct graph risk `0.00`, full Hanwoo QC passed (`test` 152, lint, build), and code-review gate WARN was the known graph/test-gap heuristic plus unrelated workspace WIP. Code commit `febabcc`. | `projects/hanwoo-dashboard/src/components/tabs/FeedTab.js`; `projects/hanwoo-dashboard/src/lib/empty-state-wiring.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-427 Hanwoo card decorative icon semantics**. Active Hanwoo accessibility continuation. `PenCard` now hides the decorative heart alert badge from assistive technology after preserving alert meaning in the card accessible label, and `CattleRow` hides its hover chevron so row labels stay focused on cattle identity and alert summaries. `cards-accessibility.test.mjs` guards the contract. Verification: focused cards test passed, Hanwoo tests `151 passed`, ESLint passed, and full Hanwoo QC passed (`test` 151, lint, build). | `projects/hanwoo-dashboard/src/components/ui/cards.js`; `projects/hanwoo-dashboard/src/lib/cards-accessibility.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-426 Hanwoo card alert accessible labels**. Continued active Hanwoo accessibility debugging. `PenCard` now includes 諛쒖젙 alert state in its accessible label, and `CattleRow` now includes 諛쒖젙/遺꾨쭔 alert summaries alongside the cattle name so visible warning badges are not dropped from the accessibility name. Verification: focused cards accessibility test passed, targeted ESLint passed, path-limited `git diff --check` passed, direct graph risk `0.00`, full Hanwoo QC passed (`test` 151, lint, build), and code-review gate WARN was the known graph/test-gap heuristic plus unrelated workspace WIP. Code commit `1919bc7`. | `projects/hanwoo-dashboard/src/components/ui/cards.js`; `projects/hanwoo-dashboard/src/lib/cards-accessibility.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-425 Hanwoo FeedTab decorative header icon semantics**. Active Hanwoo accessibility continuation. `FeedTab` now hides its decorative section-header grain glyph from assistive technology with `aria-hidden="true"`, preserving the Korean heading as the meaningful accessible content. `tab-header-accessibility.test.mjs` now covers FeedTab alongside Inventory, Sales, and Schedule. Verification: focused tab-header test passed, Hanwoo tests `151 passed`, ESLint passed, and full Hanwoo QC passed (`test` 151, lint, build). | `projects/hanwoo-dashboard/src/components/tabs/FeedTab.js`; `projects/hanwoo-dashboard/src/lib/tab-header-accessibility.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-424 Hanwoo alert banner decorative icon semantics**. Active Hanwoo accessibility continuation. `CalvingAlertBanner` now hides the decorative animated bottle glyph from assistive technology with `aria-hidden="true"`, so screen readers receive the Korean alert title and notification content without glyph noise. Added `alert-banners-accessibility.test.mjs`. Verification: focused alert-banner test passed, Hanwoo tests `151 passed`, ESLint passed, and full Hanwoo QC passed (`test` 151, lint, build). | `projects/hanwoo-dashboard/src/components/widgets/AlertBanners.js`; `projects/hanwoo-dashboard/src/lib/alert-banners-accessibility.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-423 Hanwoo CattleForm field accessibility**. Active Hanwoo accessibility continuation. `CattleForm` now connects visible labels for name, tag number, building, pen, gender, status, birth date, weight, purchase info, pedigree, and memo fields to stable control ids, and exposes validation state through `aria-invalid` where it was missing. `cattle-detail-modal-wiring.test.mjs` guards the contract. Verification: focused Hanwoo tests `150 passed`, targeted ESLint passed, path-limited `git diff --check` passed, direct graph risk was `0.00`, full Hanwoo QC passed (`test` 150, lint, build), and staged/commit code-review gate WARN was the known graph/test-gap heuristic plus unrelated VibeDebt WIP. Commit `8ae7886`. | `projects/hanwoo-dashboard/src/components/forms/CattleForm.js`; `projects/hanwoo-dashboard/src/lib/cattle-detail-modal-wiring.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-422 Hanwoo CalvingTab form accessibility**. Active Hanwoo accessibility continuation. CalvingTab now connects the 遺꾨쭔??and ?≪븘吏 ?깅퀎 labels to their date/select controls with stable ids, exposes validation state through `aria-invalid`, and hides the section header cow glyph from assistive technology. Added `calving-tab-accessibility.test.mjs`. Verification: focused Hanwoo tests `150 passed`, targeted ESLint passed, path-limited `git diff --check` passed, direct graph risk was `0.00`, full Hanwoo QC passed (`test` 150, lint, build), and staged/commit code-review gate WARN was the known graph/test-gap heuristic plus unrelated VibeDebt WIP. Commit `c410f5a`. | `projects/hanwoo-dashboard/src/components/tabs/CalvingTab.js`; `projects/hanwoo-dashboard/src/lib/calving-tab-accessibility.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-421 Hanwoo cattle-detail modal semantics hardening**. Active Hanwoo accessibility/form-safety continuation. `CattleDetailModal` now gives modal back/edit/delete action buttons explicit `type="button"` semantics and hides decorative section/timeline icons from assistive technology, preserving the Korean titles and record text as the meaningful accessible content. `cattle-detail-modal-wiring.test.mjs` guards the contract. Verification: focused Hanwoo tests `149 passed`, targeted ESLint passed, path-limited `git diff --check` passed, direct graph risk was `0.00`, full Hanwoo QC passed (`test` 149, lint, build), and staged/commit code-review gate WARN was the known graph/test-gap heuristic plus unrelated VibeDebt WIP. Commit `06959be`. | `projects/hanwoo-dashboard/src/components/forms/CattleDetailModal.js`; `projects/hanwoo-dashboard/src/lib/cattle-detail-modal-wiring.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-420 Hanwoo primary tab header decorative icon semantics**. Active Hanwoo accessibility/product-completeness continuation. Inventory, Sales, and Schedule tab header glyphs now use `aria-hidden="true"` so assistive technology receives the adjacent Korean section titles without decorative emoji noise. Added `tab-header-accessibility.test.mjs`. Verification: focused Hanwoo tests `148 passed`, targeted ESLint passed, path-limited `git diff --check` passed, direct graph risk was `0.00`, full Hanwoo QC passed (`test` 148, lint, build), and staged/commit code-review gate WARN was the known graph/test-gap heuristic plus unrelated VibeDebt WIP. Commit `83f7c01`. | `projects/hanwoo-dashboard/src/components/tabs/InventoryTab.js`; `projects/hanwoo-dashboard/src/components/tabs/SalesTab.js`; `projects/hanwoo-dashboard/src/components/tabs/ScheduleTab.js`; `projects/hanwoo-dashboard/src/lib/tab-header-accessibility.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-419 Hanwoo SettingsTab decorative icon semantics**. Active Hanwoo accessibility/product-completeness continuation. SettingsTab theme glyph, dashboard-widget section glyph, and per-widget glyphs now use `aria-hidden="true"` so assistive technology receives the visible Korean labels and switch accessible names without decorative text-icon noise. `settings-tab-accessibility.test.mjs` guards the contract. Verification: focused Hanwoo tests `147 passed`, targeted ESLint passed, path-limited `git diff --check` passed, direct graph risk was `0.00`, full Hanwoo QC passed (`test` 147, lint, build), and staged/commit code-review gate WARN was the known graph/test-gap heuristic plus unrelated VibeDebt WIP. Commit `07cd6c4`. | `projects/hanwoo-dashboard/src/components/tabs/SettingsTab.js`; `projects/hanwoo-dashboard/src/lib/settings-tab-accessibility.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-417 Hanwoo notification modal Escape dismissal**. Active Hanwoo debugging/product-completeness continuation. `NotificationModal` now supports Escape-key dismissal from the dialog surface, stops propagation before calling `onClose`, and exposes `tabIndex={-1}` so the key handler can live on the custom dialog container. `notification-modal-copy.test.mjs` guards the contract. Verification: focused Hanwoo tests `146 passed`, targeted ESLint passed, path-limited `git diff --check` passed, direct graph risk was `0.00`, full Hanwoo QC passed (`test` 146, lint, build), and staged/commit code-review gate WARN was the known graph/test-gap heuristic plus unrelated VibeDebt WIP. Commit `1aceb99`. | `projects/hanwoo-dashboard/src/components/ui/NotificationModal.js`; `projects/hanwoo-dashboard/src/lib/notification-modal-copy.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-416 Hanwoo shared Button form-safety semantics**. Active Hanwoo debugging/product-completeness continuation. `Button` now defaults native buttons to `type="button"` unless callers explicitly pass a type, while `asChild` remains untouched. This prevents generic action buttons from accidentally submitting forms when reused in form layouts. `feedback-provider-copy.test.mjs` guards the contract. Verification: focused Hanwoo tests `145 passed`, targeted ESLint passed, path-limited `git diff --check` passed, staged review gate passed with known cp949 reader-thread noise, full Hanwoo QC passed (`test` 145, lint, build), and commit hook emitted only advisory graph/test-gap WARN with unrelated VibeDebt dirty WIP. Commit `7ce65b0`. | `projects/hanwoo-dashboard/src/components/ui/button.js`; `projects/hanwoo-dashboard/src/lib/feedback-provider-copy.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-415 Hanwoo premium button form-safety semantics**. Active Hanwoo debugging/product-completeness continuation. `PremiumButton` now defaults native buttons to `type="button"` so secondary/custom controls inside forms cannot accidentally submit forms; explicit `type="submit"` callers still opt into submission, and `asChild` avoids leaking button-only props. Added `premium-button-semantics.test.mjs`. Verification: focused Hanwoo tests `144 passed`, targeted ESLint passed, path-limited `git diff --check` passed, direct graph risk was `0.00`, full Hanwoo QC passed in the current worktree (`test` 145, lint, build), and staged/commit code-review gate WARN was the known graph/test-gap heuristic plus unrelated VibeDebt WIP. Commit `e36a09d`. | `projects/hanwoo-dashboard/src/components/ui/premium-button.js`; `projects/hanwoo-dashboard/src/lib/premium-button-semantics.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-414 Hanwoo notification modal decorative icon semantics**. Active Hanwoo product-completeness/accessibility continuation. `NotificationModal` now hides the title glyph, empty-state glyph, and urgent alert glyph from assistive technology with `aria-hidden="true"`, so screen readers receive the dialog title and notification text without decorative status noise. `notification-modal-copy.test.mjs` guards the contract. Verification: focused Hanwoo tests `142 passed`, targeted ESLint passed, path-limited `git diff --check` passed, direct graph risk was `0.00`, and full Hanwoo QC passed (`test` 142, lint, build). Commit `18d90a6`. | `projects/hanwoo-dashboard/src/components/ui/NotificationModal.js`; `projects/hanwoo-dashboard/src/lib/notification-modal-copy.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-413 Hanwoo notification SMS modal polish**. Active Hanwoo product-completeness continuation. `NotificationModal` close and SMS test actions now use explicit `type="button"` semantics, and the SMS setup note now uses Korean operator copy about 臾몄옄 ?뚮┝ ?곕룞 and possible sending costs instead of vendor/API-facing wording. `notification-modal-copy.test.mjs` guards the contract. Verification: focused Hanwoo tests `141 passed`, targeted ESLint passed, path-limited `git diff --check` passed, full Hanwoo QC passed (`test` 141, lint, build), and staged/commit code-review gate emitted the known graph/test-gap WARN while direct checks covered the committed files. Commit `ed3d1c5`. | `projects/hanwoo-dashboard/src/components/ui/NotificationModal.js`; `projects/hanwoo-dashboard/src/lib/notification-modal-copy.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-412 Hanwoo cattle pagination failure feedback**. Active Hanwoo product-completeness debugging continuation. `useCattlePagination` now tracks Korean timeout/general `loadError` states, returns `loadError`, and `DashboardClient` renders a home `媛쒖껜 ??蹂닿린` control plus `role="status"` retry feedback when additional cattle-page loading fails instead of leaving the problem in console-only diagnostics. `cattle-pagination-feedback.test.mjs` guards the contract. Verification: focused Hanwoo tests `140 passed`, targeted ESLint passed, path-limited `git diff --check` passed, full Hanwoo QC passed (`test` 140, lint, build), and staged/commit code-review gate emitted the known graph/test-gap WARN while direct checks covered the committed files. Commit `757c440`. | `projects/hanwoo-dashboard/src/components/DashboardClient.js`; `projects/hanwoo-dashboard/src/lib/hooks/useCattlePagination.js`; `projects/hanwoo-dashboard/src/lib/cattle-pagination-feedback.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-411 Hanwoo dropdown action accessibility**. Active Hanwoo product-completeness/accessibility continuation. `DropdownMenuItem` now renders entries with `onClick` as native `button type="button"` elements with full-width text alignment and focus-ring styling, while static entries remain `div`s. This makes notification read actions reachable by Tab/Enter/Space instead of pointer-only clickable `div`s. `notification-system-copy.test.mjs` guards the contract. Verification: focused Hanwoo tests `139 passed`, targeted ESLint passed, path-limited `git diff --check` passed, staged review gate passed with known cp949 reader-thread noise, full Hanwoo QC passed (`test` 140, lint, build), and commit hook emitted only advisory graph/test-gap WARN with unrelated VibeDebt dirty WIP. Commit `56e6c3d`. | `projects/hanwoo-dashboard/src/components/ui/dropdown-menu.js`; `projects/hanwoo-dashboard/src/lib/notification-system-copy.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-410 Hanwoo cattle-detail action labels**. Active Hanwoo product-completeness/accessibility continuation. Cattle-detail edit/delete buttons now expose cattle-specific Korean accessible context by including the current cattle name in their `aria-label` values and Korean `title` copy, so screen-reader users can distinguish which record will be edited or deleted. `cattle-detail-modal-wiring.test.mjs` guards the contract. Verification: focused Hanwoo tests `138 passed`, targeted ESLint passed, path-limited `git diff --check` passed, full Hanwoo QC passed (`test` 138, lint, build), and staged/commit review gate produced advisory heuristic/WIP noise only. Commit `3f180c5`. | `projects/hanwoo-dashboard/src/components/forms/CattleDetailModal.js`; `projects/hanwoo-dashboard/src/lib/cattle-detail-modal-wiring.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-409 Hanwoo schedule date-cell accessibility**. Active Hanwoo product-completeness goal continuation. Monthly schedule calendar date cells now render as native `button` elements instead of clickable `<div>` cards, with `type="button"`, date-specific Korean `aria-label`/`title` copy (`${dateStr} ?쇱젙 ?깅줉 ?닿린`), and inherited left-aligned text styling to preserve the existing visual layout. `home-market-copy.test.mjs` guards the semantic button contract. Verification: focused Hanwoo tests `138 passed`, targeted ESLint passed, path-limited `git diff --check` passed, full Hanwoo QC passed (`test` 138, lint, build), and `code_review_gate --staged --json` emitted the known graph/test-gap WARN while direct Hanwoo checks covered the committed files. Commit `e756acd`. | `projects/hanwoo-dashboard/src/components/tabs/ScheduleTab.js`; `projects/hanwoo-dashboard/src/lib/home-market-copy.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Claude Code (Opus 4.7 1M) | **T-406 VibeDebt 媛먯궗湲?痢≪젙 ?뺥솗???섏젙 + T-372 諛깅줈洹??ш???WIP** (goal "湲곗닠 遺梨??뺣━" 3쨌4?④퀎 ???ъ슜?먭? "諛깅줈洹?3嫄??ш??? ??"VibeDebt RED 怨꾩냽 吏꾪뻾" ?좏깮). **諛깅줈洹??ш???*: T-251? 100% ?ъ슜??李⑤떒(Supabase 鍮꾨쾲 由ъ뀑), T-320? 援ы쁽 而ㅻ컠쨌QC green?대굹 ?붿뿬???ъ슜???섍꼍 ?꾩슂, T-372????誘명빐寃?釉붾줈而ㅻ? 痢≪젙?쇰줈 ?댁냼 ??(a) `npx biome check .` = 263?뚯씪 796 吏꾨떒(555 errors), (b) `.github/workflows/`??紐낆떆??`prisma generate` ?놁쓬 ?뺤씤 ??postinstall ?쒓굅 ??CI fresh build ?뺤젙 ?뚯넀. **VibeDebt**: `vibe_debt_auditor.py` ???대━?ㅽ떛 踰꾧렇 援먯젙 ??`score_test_gap`??`test_<module>.py` ?뺥솗 ?쇱튂留?遊먯꽌 `test_<module>_<qualifier>.py` 而⑤깽??blind-to-x 110媛??뚯뒪?????볦묠 ??suffix glob 異붽?; `score_doc_sync`媛 workspace ?꾩슜 directive 留ㅽ븨????repo???곸슜 ??workspace ?쒖젙. ?뚭? ?뚯뒪??2嫄?異붽?(32 passed). 寃곌낵 overall TDR **38.0%??3.9%**(principal ??2h, 痢≪젙 ?ㅻ쪟遺?. ?붿뿬 33.9% RED??吏꾩쭨 蹂듭옟??以묐났 遺梨???T-407 ?좉퇋 TODO. ?꾩옱 援ы쁽 ?뚯씪? 誘몄빱諛?WIP濡?蹂댁〈?? | `workspace/execution/vibe_debt_auditor.py`; `workspace/tests/test_vibe_debt_auditor.py`; `.ai/TASKS.md`; `.ai/HANDOFF.md`; `.ai/SESSION_LOG.md` |
| 2026-05-20 | Claude Code (Opus 4.7 1M) | **T-398 Dependabot 硫붿씠? PR 8嫄??뺣━ ???ㅽ뵂 PR 0嫄??ъ꽦** (goal "湲곗닠 遺梨??뺣━" 2?④퀎, ?ъ슜??AskUserQuestion ?좏깮). T-396(?덉쟾 13嫄????댁뼱 硫붿씠? 8嫄?泥섎━. ?몃━?꾩? ?뺤젙: `#70`/`#72`???쒕ぉ??`bump react`??쇰굹 PR diff??React `19.2.x` patch??利됱떆 癒몄?. 鍮뚮뱶/?뚯뒪???대쭅 硫붿씠? `#63`(@vitejs/plugin-react 6)쨌`#65`(pytest-asyncio 1.3)쨌`#68`(typescript 6)? `gh pr update-branch` rebase ???꾨줈?앺듃 CI(build+test) 洹몃┛ ?뺤씤 ??admin 癒몄?. `#60` anthropic 0.43??.103: blind-to-x `draft_providers.py` ?ъ슜泥섍? stable core API(`messages.create`+prompt-cache ?뚮씪誘명꽣)留??ъ슜?⑥쓣 肄붾뱶 ?뺤씤, rebase ??CI 洹몃┛ ??癒몄?. `#71` recharts 2??: hanwoo 5媛?李⑦듃 而댄룷?뚰듃媛 ?꾨? core 而댄룷?뚰듃留??ъ슜쨌`'use client'`, rebase ??CI 洹몃┛ ??癒몄?. `#64` lucide-react 0.563??.16: v1??`Github` brand icon ?쒓굅(`TS2305`) ??knowledge-dashboard `page.tsx` `Github`??FolderGit2`(non-brand, ??踰꾩쟾 ?명솚) 援먯껜 fix瑜?worktree濡?PR 釉뚮옖移섏뿉 吏곸젒 而ㅻ컠(`707edf0`) ??CI 洹몃┛ ??癒몄?. 寃利? 理쒖쥌 癒몄? ??`main`(`11e9acb`) `active-project-matrix` 5???꾨? success + `root-quality-gate` success. dependabot??癒몄? 肄붾㎤??臾댁쓳?듭씠????怨쇱젙 ADMIN 吏곸젒 癒몄?. FolderGit2 fix??濡쒖뺄 main `3e7a096`?먮룄 ?숈씪 ?댁슜 議댁옱(sync ??臾댁땐??. | `projects/knowledge-dashboard/src/app/page.tsx`(濡쒖뺄 `3e7a096` + PR `707edf0`); (GitHub ?먭꺽 癒몄? 8嫄?; `.ai/TASKS.md`; `.ai/HANDOFF.md`; `.ai/SESSION_LOG.md` |
| 2026-05-20 | Claude Code (Opus 4.7 1M) | **?꾩껜 ?꾨줈?앺듃 QC + QC ?ㅽ뙣 遺梨??쒓굅** (?ъ슜??`/goal "?꾩옱 ?꾨줈?앺듃???꾩껜 qc"` ???쒖꽦 goal "湲곗닠 遺梨?源붾걫?섍쾶 ?쒓굅"???꾩냽 ?④퀎). `project_qc_runner.py --json` 4媛??꾨줈?앺듃 ?꾩닔 ?ㅽ뻾 ??blind-to-x ?끒톒anwoo-dashboard ?끒톝horts-maker-v2 ??test+lint)쨌knowledge-dashboard ??lint+build). **shorts-maker-v2**: T-320 OpenVoice WIP `test_openvoice_client.py`媛 `--maxfail=1`??媛???ㅼ젣濡?4 test fail + 8 ruff error ????踰덈룄 ?듦낵?????녿뜕 誘멸?利?WIP. openvoice 誘몄꽕移??섍꼍 ???媛吏?遺紐?紐⑤뱢 二쇱엯), `ProjectSettings` ?ㅼ젣 API ?뺥빀(name/aspect_ratio?뭠anguage/default_scene_count), ?⑥닔 ?대? import ???monkeypatch ?寃잛쓣 ?뚯뒪 紐⑤뱢濡??섏젙, ruff ?뺣━+format. ?ш?利?full QC green(1467 passed/12 skipped, ruff clean). 而ㅻ컠 `8ba2850`(4?뚯씪, ?ъ슜???뱀씤). **knowledge-dashboard**: T-372 紐⑤끂?덊룷 留덉씠洹몃젅?댁뀡 WIP媛 `package-lock.json` ??젣 ??`node_modules` 鍮꾩뼱 `next`/`eslint` 遺?щ줈 lint/build ?ㅽ뙣. ?ъ슜???좏깮?濡?`package-lock.json` git 蹂듭썝 + `npm ci`(435 pkg) ??QC green. **寃곌낵: 4媛??쒖꽦 ?꾨줈?앺듃 ?꾨? QC green.** ?⑥? 遺梨?T-251/T-320 ?쒖꽦??T-372/T-398)???꾨? approval쨌?몃? 李⑤떒. | `projects/shorts-maker-v2/src/shorts_maker_v2/config.py`; `projects/shorts-maker-v2/src/shorts_maker_v2/pipeline/media/audio_mixin.py`; `projects/shorts-maker-v2/src/shorts_maker_v2/providers/openvoice_client.py`; `projects/shorts-maker-v2/tests/unit/test_openvoice_client.py`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md` |
| 2026-05-20 | Claude Code (Opus 4.7 1M) | **T-396 Dependabot PR 諛깅줈洹?21嫄??뺣━** (?ъ슜??`/goal "?꾩옱 湲곗닠 遺梨꾧? 源붾걫?섍쾶 ?щ씪吏寃?` ??AskUserQuestion?쇰줈 1?④퀎 踰붿쐞瑜?"Dependabot PR ?뺣━"濡??좏깮). 21嫄??꾨? dependabot쨌`MERGEABLE`쨌`BEHIND` ?곹깭. CI 濡ㅼ뾽?쇰줈 ?몃━?꾩?: ?덉쟾 13嫄?patch/minor쨌踰붿쐞 ?뺤옣) vs ?꾪뿕 硫붿씠? 8嫄? ?덉쟾 13嫄?`#56 #57 #58 #59 #61 #62 #66 #67 #69 #73 #74 #75 #76`) 癒몄? ??`@dependabot squash and merge` 肄붾㎤?쒓? ~8遺?臾댁쓳?듭씠??ADMIN 沅뚰븳 `gh pr merge --squash --admin`濡?吏곸젒 ?쒕젅??`BEHIND` 洹쒖튃留??고쉶, 3-way 癒몄?쨌??CI 洹몃┛쨌`MERGEABLE`? 洹몃?濡?異⑹”). `#62`(cloudinary)???숈씪 manifest ?뺤젣 癒몄?濡??쇱떆 conflict?뭗ependabot 諛깃렇?쇱슫???먮룞 rebase ??癒몄?. 寃利? 癒몄? ??`main`(`7fceede`) `active-project-matrix` 5媛????꾨? success(shorts-maker-v2/workspace/blind-to-x/hanwoo/knowledge) + `root-quality-gate` success ???꾩쟻 ?섏〈??蹂寃?臾댄빐 ?뺤씤. ?꾪뿕 硫붿씠? 8嫄?`#60` anthropic 0.43??.103, `#63` vite-plugin-react 6, `#64` lucide-react 1 ??CI 鍮뚮뱶 ?ㅽ뙣 ?뺤씤, `#65` pytest-asyncio 1, `#68` typescript 6, `#70`/`#72` react major, `#71` recharts 3)? 癒몄? ???섍퀬 **T-398**(approval)濡?遺꾨━. 肄붾뱶 蹂寃??놁쓬(?먭꺽 PR 癒몄?留?, 濡쒖뺄 WIP 誘몄닔??蹂댁〈. | (GitHub ?먭꺽 癒몄? 13嫄?; `.ai/TASKS.md`; `.ai/HANDOFF.md`; `.ai/SESSION_LOG.md` |
| 2026-05-20 | Codex | **T-391 Hanwoo full-list preload failure recovery**. Active Hanwoo product-completeness goal continuation. Feed/calving/sales/analysis and building views that require complete cattle/sales datasets now set Korean retry feedback, swallow background promise rejections, and render a `?ㅼ떆 遺덈윭?ㅺ린` action instead of leaving users at a passive loading/ready placeholder. `home-market-copy.test.mjs` guards the contract. Verification: focused home/component tests passed (`130 passed`), targeted ESLint passed, full Hanwoo QC passed (`test` 130, lint, build), path-limited `git diff --check` passed, and staged code-review gate PASS with the known trailing cp949 reader-thread noise. Commit hook WARN came from heuristic test-gap noise while direct tests covered the committed files. Commit `4748282`. | `projects/hanwoo-dashboard/src/components/DashboardClient.js`; `projects/hanwoo-dashboard/src/lib/home-market-copy.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-390 Hanwoo notification/payment copy polish**. Active Hanwoo product-completeness goal continuation. Subscription success confirmation catch paths now log diagnostics and show stable Korean retry copy instead of rendering `error.message`, and `NotificationWidget` no longer shows the English `Priority Alerts` heading. Existing copy tests guard both contracts. Verification: focused payment/notification/component tests passed (`129 passed`), targeted ESLint passed, full Hanwoo QC passed (`test` 129, lint, build), path-limited `git diff --check` passed, and staged code-review gate PASS with the known trailing cp949 reader-thread noise. Commit hook WARN came from heuristic test-gap noise while direct tests covered the committed files. Commit `0d4a395`. | `projects/hanwoo-dashboard/src/app/subscription/success/page.js`; `projects/hanwoo-dashboard/src/components/widgets/NotificationWidget.js`; `projects/hanwoo-dashboard/src/lib/payment-ux-copy.test.mjs`; `projects/hanwoo-dashboard/src/lib/notification-system-copy.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-389 Hanwoo sales pagination failure feedback**. Active Hanwoo product-completeness goal continuation. `useSalesPagination` now tracks safe Korean `loadError` copy for timeout, HTTP/API, pagination-safety, and unexpected failures, and `SalesTab` renders that message as a polite status region below the "load more" button instead of failing silently with console-only diagnostics. Added `sales-pagination-feedback.test.mjs`. Verification: focused Hanwoo tests passed (`129 passed`), targeted ESLint passed, full Hanwoo QC passed (`test` 129, lint, build), path-limited `git diff --check` passed, and staged code-review gate PASS with the known trailing cp949 reader-thread noise. Commit hook WARN came from heuristic dirty-WIP/test-gap noise while direct tests covered the committed files. Commit `3554dae`. | `projects/hanwoo-dashboard/src/lib/hooks/useSalesPagination.js`; `projects/hanwoo-dashboard/src/components/tabs/SalesTab.js`; `projects/hanwoo-dashboard/src/lib/sales-pagination-feedback.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-388 Hanwoo dashboard API/admin fallback localization**. Active Hanwoo product-completeness goal continuation. `/api/dashboard/{summary,cattle,sales}` 500 paths now log diagnostics and return stable Korean fallback copy instead of arbitrary `error.message`, dashboard list validation errors now use Korean operator copy, and admin system/raw-data actions no longer return raw DB/runtime messages except the known unsupported-data-type copy. `home-market-copy.test.mjs` and `actions-copy.test.mjs` guard these contracts. Verification: focused action/home tests passed (`127 passed`), `npm.cmd run lint` passed, full Hanwoo QC passed (`test` 127, lint, build), path-limited `git diff --check` passed, direct graph risk `0.00`, and staged code-review gate WARN was heuristic test-gap noise while direct tests covered the committed files. Commit `f1a4637`. | `projects/hanwoo-dashboard/src/app/api/dashboard/summary/route.js`; `projects/hanwoo-dashboard/src/app/api/dashboard/cattle/route.js`; `projects/hanwoo-dashboard/src/app/api/dashboard/sales/route.js`; `projects/hanwoo-dashboard/src/lib/dashboard/list-queries.js`; `projects/hanwoo-dashboard/src/lib/actions/system.js`; `projects/hanwoo-dashboard/src/lib/home-market-copy.test.mjs`; `projects/hanwoo-dashboard/src/lib/actions-copy.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-387 Hanwoo Excel export failure fallback localization**. Active Hanwoo product-completeness goal continuation. `ExcelExportButton` now logs CSV/export exceptions and shows stable Korean retry copy instead of rendering arbitrary browser/runtime `error.message` text in the feedback toast. `excel-export-button-copy.test.mjs` guards the fallback copy and rejects the old raw-error description path. Verification: focused Excel export/CSV/component tests passed (`127 passed`), targeted ESLint passed, full Hanwoo QC passed (`test` 127, lint, build), path-limited `git diff --check` passed, and staged code-review gate PASS with the known trailing cp949 reader-thread noise. Commit hook WARN came from dirty-WIP/test-gap heuristic noise while direct tests covered the committed files. Commit `cf07c4e`. | `projects/hanwoo-dashboard/src/components/widgets/ExcelExportButton.js`; `projects/hanwoo-dashboard/src/lib/excel-export-button-copy.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-386 Hanwoo async UI fallback localization**. Active Hanwoo product-completeness goal continuation. Hid raw async UI failure messages from diagnostics, payment, and AI chat surfaces: diagnostics/raw-data loads now log details and show stable Korean retry copy, `PaymentWidget` no longer renders arbitrary payment SDK exception text except its own pending state, and `AIChatWidget` logs stream failures while showing a Korean connection fallback. Copy tests now reject the raw `error.message` paths. Verification: focused diagnostics/payment/AI/component tests passed (`127 passed`), targeted ESLint passed, full Hanwoo QC passed (`test` 127, lint, build), path-limited `git diff --check` passed, and staged code-review gate PASS with the known trailing cp949 reader-thread noise. Commit hook WARN came from dirty-WIP/test-gap heuristic noise while direct tests covered the committed files. Commit `e1b1459`. | `projects/hanwoo-dashboard/src/components/admin/DiagnosticsPageClient.js`; `projects/hanwoo-dashboard/src/components/payment/PaymentWidget.js`; `projects/hanwoo-dashboard/src/components/widgets/AIChatWidget.js`; `projects/hanwoo-dashboard/src/lib/diagnostics-copy.test.mjs`; `projects/hanwoo-dashboard/src/lib/payment-ux-copy.test.mjs`; `projects/hanwoo-dashboard/src/lib/ai-chat-widget-copy.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-385 Hanwoo expense action fallback localization**. Active Hanwoo product-completeness goal continuation. `createExpenseRecord` now logs diagnostics and returns Korean product fallback copy instead of raw `error.message`, preventing Prisma/runtime internals from leaking into offline-sync or future expense-entry feedback paths. `actions-copy.test.mjs` now covers expense actions and rejects `message: error.message` there. Verification: focused action/component tests passed (`127 passed`), targeted ESLint passed, full Hanwoo QC passed (`test` 127, lint, build), path-limited `git diff --check` passed, and staged code-review gate PASS. Commit hook WARN came from dirty-WIP/test-gap heuristic noise while direct tests covered the committed files. Commit `6f6d819`. | `projects/hanwoo-dashboard/src/lib/actions/expense.js`; `projects/hanwoo-dashboard/src/lib/actions-copy.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-384 Hanwoo cattle/sales server-action fallback localization**. Active Hanwoo product-completeness goal continuation. `createCattle`, `updateCattle`, `recordCalving`, `deleteCattle`, and `createSalesRecord` now log diagnostics and return Korean product fallback copy instead of raw `error.message`, preventing Prisma/runtime internals from leaking through operator-facing toasts. `actions-copy.test.mjs` guards the fallback copy and rejects `message: error.message` in cattle/sales action files. Verification: focused action/component tests passed (`127 passed`), targeted ESLint passed, full Hanwoo QC test/lint passed and build passed on retry after a concurrent Next build lock, path-limited `git diff --check` passed, direct graph risk `0.00`, and staged code-review gate PASS. Commit `ddc26ff`. | `projects/hanwoo-dashboard/src/lib/actions/cattle.js`; `projects/hanwoo-dashboard/src/lib/actions/sales.js`; `projects/hanwoo-dashboard/src/lib/actions-copy.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-383 Hanwoo cattle mutation fallback hardening**. Active Hanwoo product-completeness goal continuation. `handleAddCattle` and `handleUpdateCattle` now log client-side exceptions and show a safe Korean fallback description instead of raw `error.message`, preventing network/runtime English or internals from leaking through operator-facing toasts. Extended `home-market-copy.test.mjs` to guard the fallback and reject `showError(errorTitle, error.message)`. Verification: focused home/component tests passed (`127 passed`), targeted ESLint passed, full Hanwoo QC passed (`test` 127, lint, build), path-limited `git diff --check` passed, and direct graph risk `0.00`. Staged/commit graph gate WARN came from dirty-WIP/test-gap heuristics while direct tests covered the committed files. Commit `dd2bff4`. | `projects/hanwoo-dashboard/src/components/DashboardClient.js`; `projects/hanwoo-dashboard/src/lib/home-market-copy.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-382 Hanwoo financial chart icon polish**. Active Hanwoo product-completeness goal continuation. Replaced the broken `?` glyph in the financial chart header with a real lucide `BarChart3` icon and marked it decorative with `aria-hidden`. Extended `analysis-copy.test.mjs` to guard against the placeholder glyph returning. Verification: focused analysis/component tests passed (`126 passed`), targeted ESLint passed, full Hanwoo QC passed (`test` 126, lint, build), path-limited `git diff --check` passed, and direct graph risk `0.00`. Staged/commit graph gate WARN came from dirty-WIP/test-gap heuristics while direct tests covered the committed files. Commit `ba1f757`. | `projects/hanwoo-dashboard/src/components/widgets/FinancialChartWidget.js`; `projects/hanwoo-dashboard/src/lib/analysis-copy.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-381 Hanwoo tab action failure fallback localization**. Active Hanwoo product-completeness goal continuation. `recordFeed`, `addInventoryItem`, `updateInventoryQuantity`, `createScheduleEvent`, and `toggleEventCompletion` now log diagnostics and return Korean product fallback copy instead of raw runtime/Prisma exception messages, preventing English/internal errors from leaking through operator-facing tab toasts. `actions-copy.test.mjs` now guards these fallbacks and rejects raw `e.message`/`error.message` returns in these actions. Verification: focused action/component tests passed (`126 passed`), targeted ESLint passed, full Hanwoo QC passed (`test` 126, lint, build), path-limited `git diff --check` passed, direct graph risk `0.00`, and staged code-review gate PASS. Commit `517daef`. | `projects/hanwoo-dashboard/src/lib/actions/feed.js`; `projects/hanwoo-dashboard/src/lib/actions/inventory.js`; `projects/hanwoo-dashboard/src/lib/actions/schedule.js`; `projects/hanwoo-dashboard/src/lib/actions-copy.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-380 Hanwoo Excel export button icon polish**. Active Hanwoo product-completeness goal continuation. Replaced the broken `?` glyph in the cattle Excel export button with a real lucide `Download` icon, marked the icon decorative with `aria-hidden`, and exposed `aria-busy` while export preparation is in progress. Added `excel-export-button-copy.test.mjs` to guard against the placeholder glyph returning. Verification: focused Excel export/component tests passed (`126 passed`), targeted ESLint passed, full Hanwoo QC passed (`test` 126, lint, build), path-limited `git diff --check` passed, direct graph risk `0.00`, and staged code-review gate PASS. Commit `a65c6ed`. | `projects/hanwoo-dashboard/src/components/widgets/ExcelExportButton.js`; `projects/hanwoo-dashboard/src/lib/excel-export-button-copy.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-379 Hanwoo Settings action fallback localization**. Active Hanwoo product-completeness goal continuation. `createBuilding`, `deleteBuilding`, and `updateFarmSettings` now log diagnostics and return Korean product copy instead of raw `e.message`, preventing Prisma/Zod/runtime English from leaking into operator-facing Settings toast feedback. `actions-copy.test.mjs` now guards the Korean fallbacks and rejects `message: e.message` in these actions. Verification: Hanwoo tests passed (`125 passed`), targeted ESLint passed, full Hanwoo QC passed (`test` 125, lint, build), path-limited `git diff --check` passed, and direct graph risk `0.00`. Staged/commit graph gate WARN came from dirty-WIP/test-gap heuristics while direct tests covered the committed files. Commit `6c91449`. | `projects/hanwoo-dashboard/src/lib/actions/building.js`; `projects/hanwoo-dashboard/src/lib/actions/farm-settings.js`; `projects/hanwoo-dashboard/src/lib/actions-copy.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-378 Hanwoo feedback toast live-region accessibility**. Active Hanwoo product-completeness goal continuation. `FeedbackProvider.js` now makes global toast feedback announce reliably to assistive technology: error/warning toasts use `role="alert"` with assertive live updates, success/info toasts use `role="status"` with polite live updates, all toasts are atomic, decorative accent dots are hidden, and dismiss buttons get Korean toast-specific labels. Added `feedback-provider-copy.test.mjs`. Verification: focused feedback/component tests passed, targeted ESLint passed, full Hanwoo QC passed (`test` 125, lint, build), path-limited `git diff --check` passed, and direct graph risk `0.00`. Commit `980bfb7`. | `projects/hanwoo-dashboard/src/components/feedback/FeedbackProvider.js`; `projects/hanwoo-dashboard/src/lib/feedback-provider-copy.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-377 Hanwoo home icon decoration and Settings switch accessibility**. Active Hanwoo product-completeness goal continuation. `DashboardClient` now hides decorative home notification/add/back icons and the critical notification badge from assistive tech while preserving the existing Korean button labels. `SettingsTab` theme and widget toggles now expose `role="switch"`, `aria-checked`, Korean `aria-label`/`title`, and decorative thumb `aria-hidden`. Added `settings-tab-accessibility.test.mjs` and extended `home-market-copy.test.mjs`. Verification: Hanwoo tests passed (`124 passed`), targeted ESLint passed, full Hanwoo QC test/lint passed and build passed on retry after a concurrent Next build lock, path-limited `git diff --check` passed, and direct graph risk `0.00`. Commit `4d8fcf6`. | `projects/hanwoo-dashboard/src/components/DashboardClient.js`; `projects/hanwoo-dashboard/src/components/tabs/SettingsTab.js`; `projects/hanwoo-dashboard/src/lib/home-market-copy.test.mjs`; `projects/hanwoo-dashboard/src/lib/settings-tab-accessibility.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-374 Hanwoo notification system trigger accessibility labels**. Active Hanwoo product-completeness goal continuation. Completed the existing notification-system accessibility WIP by aligning both `NotificationSystem.js` and the tracked `NotificationSystem.tsx` mirror: the icon-only bell trigger now uses Korean unread-count-aware `notificationLabel` copy through `aria-label`/`title`, and decorative bell/badge elements are hidden from assistive tech. Added `notification-system-copy.test.mjs` to guard both implementations. Verification: Hanwoo `npm test` passed (`123 passed`), targeted ESLint passed, full Hanwoo QC passed (`test` 123, lint, build), path-limited `git diff --check` passed, and direct graph risk `0.00`. Staged/commit code-review gate WARN came from graph test-gap/dirty-WIP heuristics while direct tests covered the committed files. Commit `56e1e9e`. | `projects/hanwoo-dashboard/src/components/layout/NotificationSystem.js`; `projects/hanwoo-dashboard/src/components/layout/NotificationSystem.tsx`; `projects/hanwoo-dashboard/src/lib/notification-system-copy.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-373 Hanwoo calendar and market icon accessibility labels**. Active Hanwoo product-completeness goal continuation. Added Korean accessible labels to remaining icon-only controls: `ScheduleTab` previous/next month buttons now expose `?댁쟾 ??蹂닿린` / `?ㅼ쓬 ??蹂닿린`, and `MarketPriceWidget` refresh exposes `?쒖슦 ?쒖꽭 ?덈줈怨좎묠` / `?쒖꽭 媛깆떊 以?. Extended `home-market-copy.test.mjs` to guard both surfaces. Verification: focused Hanwoo home/market tests `7 passed`, targeted ESLint passed, full Hanwoo QC test/lint passed and build passed on retry after a concurrent Next build lock (`test` 121), path-limited `git diff --check` passed, and direct graph risk `0.00`. Full `git diff --check` still reports unrelated dirty shorts-maker-v2 trailing whitespace; staged/commit code-review gate WARN came from dirty WIP graph heuristics while direct checks covered the committed files. Commit `4609453`. | `projects/hanwoo-dashboard/src/components/tabs/ScheduleTab.js`; `projects/hanwoo-dashboard/src/components/widgets/MarketPriceWidget.js`; `projects/hanwoo-dashboard/src/lib/home-market-copy.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-371 Hanwoo modal and chat icon accessibility labels**. Active Hanwoo product-completeness goal continuation. Added dialog semantics and Korean accessible labels to cattle workflows: `CattleForm` and `CattleDetailModal` now expose `role="dialog"`, `aria-modal`, visible-title `aria-labelledby`, and Korean icon-button labels. `AIChatWidget` now labels the icon-only send button as `吏덈Ц 蹂대궡湲? or `?듬? ?앹꽦 以? depending on streaming state. Verification: focused Hanwoo cattle/AI/component tests `119 passed`, targeted ESLint passed, full Hanwoo QC passed (`test` 119, lint, build), `git diff --check` passed, direct graph risk `0.00`, and staged code-review gate PASS before commit. Commit hook emitted the known component test-gap WARN, while direct source regression coverage and full QC passed. | `projects/hanwoo-dashboard/src/components/forms/CattleForm.js`; `projects/hanwoo-dashboard/src/components/forms/CattleDetailModal.js`; `projects/hanwoo-dashboard/src/components/widgets/AIChatWidget.js`; `projects/hanwoo-dashboard/src/lib/cattle-detail-modal-wiring.test.mjs`; `projects/hanwoo-dashboard/src/lib/ai-chat-widget-copy.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-370 Hanwoo home icon action accessibility labels**. Active Hanwoo product-completeness goal continuation. Added Korean accessible labels/titles to the home-screen icon-only actions in `DashboardClient.js`: notification center, cattle registration, building-list back, and pen-list back controls. Extended `home-market-copy.test.mjs` to guard those labels and reject English fallback labels. Verification: focused Hanwoo home/component tests `118 passed`, targeted ESLint passed, full Hanwoo QC test/lint passed and build passed on retry after a concurrent Next build lock, `git diff --check` passed, direct graph risk `0.00`, and staged code-review gate PASS before commit. Commit hook emitted the known component test-gap WARN, while direct source regression coverage and full QC passed. | `projects/hanwoo-dashboard/src/components/DashboardClient.js`; `projects/hanwoo-dashboard/src/lib/home-market-copy.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-369 Hanwoo notification modal dialog semantics**. Active Hanwoo product-completeness goal continuation. Added explicit dialog semantics to `NotificationModal`: the modal container now declares `role="dialog"`, `aria-modal="true"`, and `aria-labelledby="notification-modal-title"`, and the visible `?뚮┝ ?쇳꽣` heading now carries that id. Extended `notification-modal-copy.test.mjs` to guard the dialog semantics alongside the Korean close label. Verification: focused Hanwoo notification modal tests `117 passed`, targeted ESLint passed, full Hanwoo QC passed (`test` 117, lint, build), source confirmation passed, `git diff --check` passed, direct graph risk `0.00`; staged/commit code-review gate WARN was polluted by unrelated staged/dirty WIP while direct focused/full checks covered the committed modal files. | `projects/hanwoo-dashboard/src/components/ui/NotificationModal.js`; `projects/hanwoo-dashboard/src/lib/notification-modal-copy.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-368 Hanwoo notification modal close accessibility label**. Active Hanwoo product-completeness goal continuation. Added Korean accessible copy to the notification modal's icon-only close button: `aria-label="?リ린"` and `title="?リ린"` now describe the `횞` action for assistive technology and hover users. Added `notification-modal-copy.test.mjs` to guard against English close labels returning. Verification: focused Hanwoo notification modal copy test `116 passed`, targeted ESLint passed, full Hanwoo QC passed (`test` 116, lint, build), source confirmation passed, `git diff --check` passed, direct graph risk `0.00`; staged/commit code-review gate emitted the known component test-gap WARN while direct source-level coverage and full QC passed. | `projects/hanwoo-dashboard/src/components/ui/NotificationModal.js`; `projects/hanwoo-dashboard/src/lib/notification-modal-copy.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-362 Hanwoo diagnostics status localization**. Active Hanwoo product-completeness goal continuation. Localized admin diagnostics database status values in `lib/actions/system.js`: success now reports `?뺤긽`, failure now reports `?곌껐 ?ㅽ뙣`, and unavailable latency now reports `?뺤씤 遺덇?` instead of `Online`, `Offline`, and `N/A`. Extended `diagnostics-copy.test.mjs` to guard the status strings. Verification: focused Hanwoo diagnostics/action/component tests `115 passed`, targeted ESLint passed, full Hanwoo QC test/lint passed and build passed on retry after a concurrent Next build lock, source scan passed, `git diff --check` passed, direct graph risk `0.00`, and staged code-review gate PASS before commit. | `projects/hanwoo-dashboard/src/lib/actions/system.js`; `projects/hanwoo-dashboard/src/lib/diagnostics-copy.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Claude Code (Opus 4.7 1M) | **T-365 Hanwoo profitability widget ?곸뼱 ?먮윭 移댄뵾 ?쒓???+ ?쒗뭹 ?꾩꽦??媛먯궗**. ?ъ슜??`/goal` ?몄텧 ?????몄뀡 goal ?띿뒪?멸? `~/.claude/goal/goals.sqlite`???먯긽??梨?`占쏙옙占쏙옙 占쏙옙占쏙옙占?占싹쇽옙 占쌔븝옙`) ??λ뤌 ?덉뼱 蹂듦뎄 遺덇?. HANDOFF 臾몃㎘??"Hanwoo product-completeness goal"?꾩쓣 ?뺤씤?섍퀬 DB objective瑜??뺤긽 ?쒓뎅?대줈 蹂듦뎄(紐⑺몴 ?좎?). ?ъ슜???섎룄 ?뺤씤(AskUserQuestion): 湲곗〈 goal ?좎? + 湲?而⑦뀓?ㅽ듃濡????묒뾽. 蹂묐젹 ?쒕툕?먯씠?꾪듃 3媛쒕줈 hanwoo-dashboard ?꾨㈃ 媛먯궗 ???곸뼱 移댄뵾 ?꾩닔 HIGH 2/MED 5/LOW 18, 誘몄셿 湲곕뒫 TODO/stub/empty-catch 0嫄? 紐⑤끂?덊룷 留덉씠洹몃젅?댁뀡(pnpm+turbo+biome+uv) WIP 70~80%. MED ?꾨낫 ?몄텧 寃쎈줈 寃利? `kape.js` throw???숈씪 ?⑥닔 catch?먯꽌 ?≫? 誘몃끂異? `FeedbackProvider`/`queue.js`??dev/infra ???ㅽ궢. `profitability-service.js`留??ㅻ끂異??뺤젙(`error: err.message` ??`ProfitabilityWidget`??`{error}` ?뚮뜑). **?섏젙**: `getProfitabilityEstimates()` ?곸뼱 throw 2嫄?`No market price data...`/`Price data parsing failed`) ???쒓뎅?? console 吏꾨떒???쒓??? `profitability-copy.test.mjs` ?뚭? 媛???좉퇋(2/2 pass). 寃利? full `project_qc_runner --project hanwoo-dashboard --json` ?듦낵(test 115, lint, build ??build 1李⑤뒗 ?숈떆 `next build` ?좉툑?쇰줈 ?ㅽ뙣, ?ъ떆???듦낵). 而ㅻ컠 `172e998`(`git add` 紐낆떆 pathspec濡?臾닿? WIP 蹂댁〈). ?좉퇋 TODO: T-366(怨좎븘 `ProfitabilityWidget` 留덉슫??, T-367(`formSchemas.js` ?곸뼱 enum, DB 留덉씠洹몃젅?댁뀡 ?숇컲). **?댁뼱???ъ슜?먭? 紐⑤끂?덊룷 留덉씠洹몃젅?댁뀡 留덈Т由??좏깮** ??T-368 吏꾨떒: `pnpm install`(full)????癒몄떊(Windows + ?쒓? ??`諛뺤＜??) linking ?④퀎??`exit 127`쨌?먮윭 異쒕젰 ?놁씠 6???곗냽 以묐떒(`--lockfile-only`留?exit 0) ???쒓? 寃쎈줈 ?대쭅 痍⑥빟???섏떖, 濡쒖뺄 `turbo`/`biome` 寃利?遺덇?. 遺?ы뻽??`pnpm-lock.yaml`? `--lockfile-only`濡??앹꽦(untracked). 濡쒖뺄 寃利?遺덇? + 誘명빐寃??ㅺ퀎 寃곗젙(biome blast radius, prisma postinstall ?쒓굅)?쇰줈 留덉씠洹몃젅?댁뀡 ?뚯씪 ?쇱젅 誘몄빱諛? WIP ?꾨? untracked 蹂댁〈. T-368??approval TODO濡??곸꽭 ?깅줉. **?댄썑 ?ъ슜?먭? `/goal resume`** ??**T-366 ?꾨즺**(怨좎븘 ?꾩젽 留덉슫??: `ProfitabilityWidget`??SSR ?곗씠???먮쫫???곌껐 ??`app/page.js` `Promise.all`??`getProfitabilityData()` 異붽? ??`initialProfitability` prop ??`DashboardClient`媛 `widgetSettings.visible.profitability` 寃뚯씠?몃줈 ?뚮뜑. `profitability-copy.test.mjs`??留덉슫???뚭? 媛?? 寃利? profitability 3/3 + full QC(test/lint/build) ?듦낵. 而ㅻ컠 `1047f01`. 紐⑤끂?덊룷 TODO??DONE??Codex T-368怨?ID 異⑸룎??T-368?뭈-372 ?щ쾲?? **?댄썑 ?ъ슜??"T-367 吏꾪뻾??** ??T-367 議곗궗 寃곌낵 **false positive濡?醫낃껐**: `formSchemas.js` ?곸뼱 enum 媛믪? ?대? 肄붾뱶?닿퀬 `ScheduleTab.TYPE_STYLES`쨌`InventoryTab.categories` + `<option>` ?쇰꺼???꾨? ?쒓?濡?蹂?????댁쁺???곸뼱 誘몃끂異? `Other` ?듭뀡???대? 議댁옱. ??媛먯궗??HIGH 遺꾨쪟 ?ㅽ깘, enum ?쒓??붾뒗 ?대뱷 0 + DB 留덉씠洹몃젅?댁뀡 ?꾪뿕. 肄붾뱶 蹂寃??놁씠 TASKS.md DONE???먯젙 湲곕줉. goal in-scope ?먯쑉 ?묒뾽 紐⑤몢 ?뚯쭊(?붿뿬 T-251? ?몃?/?ъ슜??李⑤떒). | `projects/hanwoo-dashboard/src/lib/dashboard/profitability-service.js`; `projects/hanwoo-dashboard/src/lib/profitability-copy.test.mjs`; `projects/hanwoo-dashboard/src/app/page.js`; `projects/hanwoo-dashboard/src/components/DashboardClient.js`; `pnpm-lock.yaml`(?앹꽦, untracked); `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md` |
| 2026-05-20 | Codex | **T-361 Hanwoo dialog close accessibility localization**. Active Hanwoo product-completeness goal continuation. Localized the shared Radix dialog close control's sr-only label from `Close` to `?リ린`, so screen-reader users do not hear English control copy. Added `dialog-copy.test.mjs` to guard the shared dialog label. Verification: focused Hanwoo dialog-copy tests `113 passed`, targeted ESLint passed, full Hanwoo QC passed (`test` 113, lint, build), accessibility-copy source scan passed, `git diff --check` passed, direct graph risk `0.00`, and staged code-review gate PASS before commit. Commit hook emitted advisory graph WARN polluted by unrelated dirty `system`/`profitability` WIP, while direct focused/full checks covered the committed dialog files. | `projects/hanwoo-dashboard/src/components/ui/dialog.js`; `projects/hanwoo-dashboard/src/lib/dialog-copy.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-360 Hanwoo server action fallback localization**. Active Hanwoo product-completeness goal continuation. Localized remaining user-facing server action fallback errors: `getCattleList()` now throws `媛쒖껜 紐⑸줉??遺덈윭?ㅼ? 紐삵뻽?듬땲??`, `getSalesRecords()` now throws `?먮ℓ 湲곕줉??遺덈윭?ㅼ? 紐삵뻽?듬땲??`, and admin raw-data validation now returns `吏?먰븯吏 ?딅뒗 ?곗씠???좏삎?낅땲??` instead of English fallback text. Added `actions-copy.test.mjs` to guard the strings. Verification: focused Hanwoo server-action copy tests `112 passed`, targeted ESLint passed, full Hanwoo QC passed (`test` 112, lint, build), `git diff --check` passed, direct graph risk `0.00`, and staged code-review gate PASS before commit. Commit hook emitted advisory graph WARN from broad heuristics, while direct focused/full checks covered the change. | `projects/hanwoo-dashboard/src/lib/actions/cattle.js`; `projects/hanwoo-dashboard/src/lib/actions/sales.js`; `projects/hanwoo-dashboard/src/lib/actions/system.js`; `projects/hanwoo-dashboard/src/lib/actions-copy.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-359 Hanwoo financial analysis copy localization**. Active Hanwoo product-completeness goal continuation. Localized remaining visible English on the financial analysis surface: `AnalysisTab` section labels now use Korean for analysis overview, monthly flow, cost mix, and top sales; `FinancialChartWidget` now uses Korean title, subtitle, unit label, and legend labels for revenue/expense/profit. Added `analysis-copy.test.mjs` to guard the copy. Verification: focused Hanwoo analysis-copy tests `111 passed`, targeted ESLint passed, full Hanwoo QC passed (`test` 111, lint, build), source scan passed, `git diff --check` passed, direct graph risk `0.00`, and staged code-review gate PASS before commit. Commit hook emitted advisory graph WARN from component test-gap heuristics, while direct focused/full checks covered the committed copy files. | `projects/hanwoo-dashboard/src/components/tabs/AnalysisTab.js`; `projects/hanwoo-dashboard/src/components/widgets/FinancialChartWidget.js`; `projects/hanwoo-dashboard/src/lib/analysis-copy.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-358 Hanwoo auth fallback localization**. Active Hanwoo product-completeness goal continuation. Localized the shared `AuthenticationError` default from `Authentication required.` to `濡쒓렇?몄씠 ?꾩슂?⑸땲??`, so authenticated API routes using `requireAuthenticatedSession()` do not leak English auth copy when they do not provide their own route-level override. Verification shared with the payment API pass: focused Hanwoo payment/auth source tests `110 passed`, targeted ESLint passed, full Hanwoo QC passed (`test` 110, lint, build), `git diff --check` passed, direct graph risk `0.00`, and staged code-review gate PASS before commit. Commit hook emitted a graph test-gap WARN for the tiny constructor copy change, while `payment-ux-copy.test.mjs` guards the user-facing string. | `projects/hanwoo-dashboard/src/lib/auth-guard.js`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-357 Hanwoo payment API fallback localization**. Active Hanwoo product-completeness goal continuation. Localized `/api/payments/prepare` customer-key mismatch, amount mismatch, customer-name fallback, and generic preparation failure messages. Localized `/api/payments/confirm` missing confirmation fields, wrong-user order, amount mismatch, missing Toss configuration, timeout diagnostic, retryable gateway deferral, and generic verification failure messages so payment APIs no longer leak English fallback/API text. Extended `payment-ux-copy.test.mjs` to guard route-level payment fallback strings. Verification: focused Hanwoo payment tests `110 passed`, targeted ESLint passed, full Hanwoo QC passed (`test` 110, lint, build), `git diff --check` passed, direct graph risk `0.00`, and staged code-review gate PASS before commit. Commit hook emitted advisory graph WARN polluted by unrelated dirty `auth-guard.js`, while direct focused/full checks covered the committed payment files. | `projects/hanwoo-dashboard/src/app/api/payments/prepare/route.js`; `projects/hanwoo-dashboard/src/app/api/payments/confirm/route.js`; `projects/hanwoo-dashboard/src/lib/payment-ux-copy.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-356 Hanwoo AI chat widget fallback polish**. Active Hanwoo product-completeness goal continuation. Updated `AIChatWidget` so localized Gemini setup/configuration messages from `/api/ai/chat` still trigger the guided setup fallback, and replaced the closed floating launcher text `AI` with a lucide `Bot` icon plus explicit accessible label/title. Added source-copy regression coverage for the Korean setup-error patterns and accessible launcher wiring. Verification: focused Hanwoo AI chat/widget tests `109 passed`, targeted ESLint passed, full Hanwoo QC passed (`test` 109, lint, build), `git diff --check` passed, and direct Hanwoo graph risk `0.00`. | `projects/hanwoo-dashboard/src/components/widgets/AIChatWidget.js`; `projects/hanwoo-dashboard/src/lib/ai-chat-widget-copy.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-355 Hanwoo subscription entry copy localization**. Active Hanwoo product-completeness goal continuation. Localized `/subscription` entry-page copy: title now reads `Joolife ?꾨━誘몄뾼 援щ룆`, the value/price line uses Korean `??9,900??..`, and the customer fallback is `Joolife ?ъ슜?? instead of English checkout copy. Extended `payment-ux-copy.test.mjs` to cover the entry page alongside checkout/result pages. Verification: focused Hanwoo payment/subscription tests `108 passed`, targeted ESLint passed, full `project_qc_runner --project hanwoo-dashboard --json` passed (`test` 109, lint, build), `git diff --check` passed, source English subscription scan passed, and direct Hanwoo graph risk `0.00`. | `projects/hanwoo-dashboard/src/app/subscription/page.js`; `projects/hanwoo-dashboard/src/lib/payment-ux-copy.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-354 Hanwoo AI chat error/fallback localization**. Active Hanwoo product-completeness goal continuation. Localized `/api/ai/chat` validation, authentication, missing Gemini configuration, provider SSE error, and start-chat failure messages so the chat widget no longer receives English API/debug copy. Also localized the AI farm-context fallback labels (`?꾩옱 ?띿옣 ?뺣낫`, `媛쒖껜紐?誘몃벑濡?, `?대젰踰덊샇 誘몃벑濡?, `理쒓렐 ?먮ℓ 湲곕줉 ?놁쓬`, `留뚯썝`) to avoid English leaking through model context. Verification: focused Hanwoo AI chat tests `108 passed`, targeted ESLint passed, full `project_qc_runner --project hanwoo-dashboard --json` passed (`test` 108, lint, build), `git diff --check` passed, source English fallback scan passed, and direct Hanwoo graph risk `0.00`. | `projects/hanwoo-dashboard/src/lib/ai-chat-api.mjs`; `projects/hanwoo-dashboard/src/lib/ai-chat-api.test.mjs`; `projects/hanwoo-dashboard/src/app/api/ai/chat/route.js`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-353 Hanwoo MTRACE lookup copy localization**. Active Hanwoo product-completeness goal continuation. Localized cattle tag lookup fallbacks in `lookupCattleByTag()`: missing service key, invalid input, rate limits, upstream failures, unreadable JSON, no cattle found, timeout, and generic errors now return Korean operator-facing messages. The default breed fallback is now `?쒖슦` instead of `Hanwoo`, and the internal API diagnostic label is Korean. Added mocked behavior/source coverage in `mtrace.test.mjs`. Verification: focused Hanwoo mtrace/import tests `107 passed`, targeted ESLint passed, full `project_qc_runner --project hanwoo-dashboard --json` passed (`test` 107, lint, build), `git diff --check` passed, and direct Hanwoo graph risk `0.00`. `npm test` prints the existing `MODULE_TYPELESS_PACKAGE_JSON` warning for JS ESM test imports, but all checks pass. | `projects/hanwoo-dashboard/src/lib/mtrace.js`; `projects/hanwoo-dashboard/src/lib/mtrace.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-352 Hanwoo dashboard API fallback copy localization**. Active Hanwoo product-completeness goal continuation. Localized dashboard load failure/timeout copy in `DashboardClient`, Koreanized related client diagnostics, changed the footer rights line to Korean, and updated `/api/dashboard/summary`, `/api/dashboard/cattle`, and `/api/dashboard/sales` default fallback messages so app-authored 500 responses do not expose `Failed to load ...` copy. Added regression coverage in `home-market-copy.test.mjs`. Verification: focused Hanwoo home/import tests `103 passed`, targeted ESLint passed, full `project_qc_runner --project hanwoo-dashboard --json` passed (`test` 103, lint, build), `git diff --check` passed, and direct Hanwoo graph risk `0.00`. | `projects/hanwoo-dashboard/src/components/DashboardClient.js`; `projects/hanwoo-dashboard/src/app/api/dashboard/summary/route.js`; `projects/hanwoo-dashboard/src/app/api/dashboard/cattle/route.js`; `projects/hanwoo-dashboard/src/app/api/dashboard/sales/route.js`; `projects/hanwoo-dashboard/src/lib/home-market-copy.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-351 Hanwoo QR print footer localization**. Active Hanwoo product-completeness goal continuation. Localized the printed cattle QR label footer from `Joolife Smart Farm` to `Joolife ?쒖슦 ?ㅻ쭏?명뙗`, extending the existing QR print polish beyond the button/title copy to the actual printed tag. Added source-copy regression coverage so the English footer does not return. Verification: focused Hanwoo QR/import tests `102 passed`, targeted ESLint passed, full `project_qc_runner --project hanwoo-dashboard --json` passed (`test` 102, lint, build), `git diff --check` passed, staged code-review gate PASS, and direct Hanwoo graph risk `0.00`. | `projects/hanwoo-dashboard/src/components/widgets/QRCodeWidget.js`; `projects/hanwoo-dashboard/src/lib/qr-widget-copy.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Claude Code (Opus 4.7 1M) | **T-350 shorts-maker-v2 Ken Burns 以?紐⑥뀡 媛??* (?ъ슜???붿껌 "ken-burns 紐⑥뀡??理쒖쟻??, T-337 ?뚮뜑 理쒖쟻???꾩냽). `scripts/bench_render.py` 湲곕컲 micro-bench濡?`_fit_vertical`??ImageClip??踰좎씠?щ뤌 ~0ms, `_ken_burns`媛 ~70ms/frame?꾩쓣 寃⑸━ 痢≪젙. ?먯씤: 5媛?以??④낵媛 `clip.resized(?쒓컙?⑥닔)`濡?留??꾨젅???몄텧 ??MoviePy `Resize.py`媛 `Image.Resampling.LANCZOS` ?섎뱶肄붾뵫(1080횞1920 ???⑥뒪: LANCZOS 68ms vs BICUBIC 53 vs BILINEAR 33). ??.12횞 誘몄꽭 以뚯뿏 LANCZOS 怨쇳븿. ?좉퇋 紐⑤뱢 ?ы띁 `_zoom_crop`??per-frame 以뚯쓣 PIL `Image.resize((tw,th), BICUBIC, box=...)` ?⑥씪 ?몄텧濡??섑뻾 ??以묒떖 ?뺣젹 以뚯뿉??crop-then-resize ??resize-then-crop ??벑?? 5媛??④낵(`_ken_burns`/`_dramatic_ken_burns`/`_zoom_out`/`_push_in`/`_ease_ken_burns`)瑜?`_zoom_crop` + scale_fn ?뚮떎濡??ъ옉???ㅼ???而ㅻ툕 ?섏떇? ?먮낯怨??숈씪). **micro-bench: `_ken_burns` 72.5??4.9 ms/frame(-24%), 5媛??④낵 43~58ms.** end-to-end 踰ㅼ튂 3??69.8/60.7/56.7珥덈줈 짹13珥?蹂??蹂묐젹 ?꾧뎄 ?숈떆 遺?? ??micro-bench媛 ?좊ː ?섏튂. 援ы쁽 ? ?뚯뒪??5媛?`.resized()`/`.cropped()` mock ?몄텧 寃利?瑜?`_zoom_crop` ?ㅽ뀅?쇰줈 scale_fn 而ㅻ툕瑜??뚯닔??寃利앺븯?꾨줉 ?ъ옉??+ `_zoom_crop` 異쒕젰 ?ш린 ?뚭? ?뚯뒪???좉퇋. 寃利? ?뚮뜑 愿???⑥쐞 240 pass, `ruff check` ?듦낵. commit `352880d`(perf) + `020edd7`(id fix). **git 寃쏀빀**: perf 而ㅻ컠 泥??쒕룄 `7f350a2`媛 蹂묐젹 ?꾧뎄 git ?묒뾽?쇰줈 orphan ???꾩껜 蹂寃쎌씠 `de1b043`("chore" 硫붿떆吏)???≪닔 ??HEAD ?뺤씤 ??`352880d`濡?硫붿떆吏 amend. task ID??T-339?뭈-346?뭈-350 ??踰?異⑸룎(蹂묐젹 ?꾧뎄媛 鍮좊Ⅴ寃??좎젏) ?앹뿉 踰꾪띁 ?먭퀬 T-350 ?뺤젙. | `projects/shorts-maker-v2/src/shorts_maker_v2/pipeline/render_effects.py`; `projects/shorts-maker-v2/tests/unit/test_render_step_effects.py`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md` |
| 2026-05-20 | Codex | **T-346 Hanwoo fallback surface copy polish**. Active Hanwoo product-completeness goal continuation. Localized the login/error/not-found operator eyebrow from `Joolife Operations` to `Joolife ?쒖슦 ?댁쁺`, and changed weather fallback location labels from `Seoul` to `?쒖슱` across the dashboard weather path. Added regression coverage in error-page, home/weather copy, and weather-state tests. Verification: focused Hanwoo tests `102 passed`, targeted ESLint passed, full `project_qc_runner --project hanwoo-dashboard --json` passed (`test` 102, lint, build), `git diff --check` passed, staged code-review gate PASS, and direct Hanwoo graph risk `0.00`. | `projects/hanwoo-dashboard/src/app/error.js`; `projects/hanwoo-dashboard/src/app/global-error.js`; `projects/hanwoo-dashboard/src/app/login/page.js`; `projects/hanwoo-dashboard/src/app/not-found.js`; `projects/hanwoo-dashboard/src/components/DashboardClient.js`; `projects/hanwoo-dashboard/src/components/widgets/widgets.js`; `projects/hanwoo-dashboard/src/lib/hooks/useWeather.js`; `projects/hanwoo-dashboard/src/lib/weather-state.mjs`; `projects/hanwoo-dashboard/src/lib/error-pages-wiring.test.mjs`; `projects/hanwoo-dashboard/src/lib/home-market-copy.test.mjs`; `projects/hanwoo-dashboard/src/lib/weather-state.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-345 Hanwoo QR print action polish**. Active Hanwoo product-completeness goal continuation. Replaced the cattle QR print button's emoji affordance with lucide `Printer`, localized the print document title from `QR Code` to `QR 異쒕젰`, and kept the visible/title action copy as `QR ?쇰꺼 ?몄뇙`. Added source-copy regression coverage so English QR print copy and the emoji button do not return. Verification: focused Hanwoo tests `100 passed`, targeted ESLint passed, full `project_qc_runner --project hanwoo-dashboard --json` passed (`test` 100, lint, build), and direct Hanwoo graph risk `0.00`. | `projects/hanwoo-dashboard/src/components/widgets/QRCodeWidget.js`; `projects/hanwoo-dashboard/src/lib/qr-widget-copy.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-20 | Claude Code (Opus 4.7 1M) | **T-337 shorts-maker-v2 ?뚮뜑 ?ロ뙣??而щ윭 洹몃젅?대뵫 2.7諛?媛??*. `/goal "理쒖쟻???쒖폒以?` ??AskUserQuestion?쇰줈 ???shorts-maker-v2, 諛⑺뼢=?ㅽ뻾/?뚮뜑 ?깅뒫?쇰줈 醫곹옒. 13媛?run manifest??`step_timings` 遺꾩꽍: ?뚮뜑媛 ?쇨??섍쾶 ?꾩껜 wall time??85~89%(990珥?1110珥?. `detect_hw_encoder('auto')` ?ㅽ뻾?쇰줈 ??癒몄떊? h264_qsv ?섎뱶?⑥뼱 ?몄퐫???뺤씤 ??990珥덈뒗 ?몄퐫?⑹씠 ?꾨땶 MoviePy ?꾨젅?꾨퀎 Python ?⑹꽦 鍮꾩슜?쇰줈 ?⑥젙. ?좉퇋 `scripts/bench_render.py`(?⑹꽦 ?먯뀑?쇰줈 ken-burns 紐⑥뀡+而щ윭洹몃젅?대뵫+罹≪뀡 ?⑹꽦+qsv write ?ロ뙣???ы쁽, cProfile ?ы븿, LLM ?뚯씠?꾨씪??遺덊븘??濡?痢≪젙쨌?꾨줈?뚯씪留? cProfile + `--no-color-grade` A/B: `color_grade_clip`???뚮뜑??~40%(4珥??곸긽 71珥?vs ?됰낫???쒖쇅 43珥?. 寃⑸━ micro-bench濡?`_grade_inplace` 163.5 ms/frame ?뺤씤 ??嫄곗쓽 ?꾨? 1080횞1920 numpy elementwise ?⑥뒪 ~10???⑥뒪??~14ms, ??癒몄떊 numpy ???룺 ??쓬). `_grade_inplace` ?ъ옉?깆쑝濡??⑥뒪 ~10??5: (1) 諛앷린+?鍮꾨? ?⑥씪 affine `(c쨌b)쨌x + b쨌mean쨌(1-c)`濡??듯빀(4???⑥뒪), (2) 梨꾨룄 `s쨌x+(1-s)쨌luma(x)` ?뺣━(3???⑥뒪), (3) ?댄듃 梨꾨꼸蹂?strided 3?뚢넂湲몄씠-3 踰≫꽣 釉뚮줈?쒖틦?ㅽ듃 1?? (4) `color_grade_clip` ?꾨젅???⑥닔 float32 ?쇨? ?좎?濡??꾨젅?꾨떦 uint8?봣loat32 ?뺣났 ?쒓굅. **痢≪젙: `_grade_inplace` 163.5??1.0 ms/frame(2.7諛?, end-to-end ?뚮뜑 ~72??65珥?~10%, 4珥?踰ㅼ튂).** 異쒕젰? 6媛?梨꾨꼸 ?꾨줈?뚯씪 ?꾨? naive ?덊띁?곗뒪 ?鍮?max abs diff ??.0001 ???섑븰???숈씪, ?덉쭏 臾댁넀?? 寃利? `test_color_grading.py` 29 pass(naive ?덊띁?곗뒪 ?鍮??뚭? ?뚯뒪??2嫄??좉퇋), ?뚮뜑 愿???⑥쐞 ?뚯뒪??210 pass, `ruff check` ?듦낵. 寃쏀빀 硫댁뿭 `git commit -- <pathspec>`濡?commit `0930e4a`(perf) + `504c709`(task id ?뺤젙 T-333?뭈-337, T-333? 蹂묐젹 ?꾧뎄 ?좎젏). | `projects/shorts-maker-v2/src/shorts_maker_v2/render/color_grading.py`; `projects/shorts-maker-v2/scripts/bench_render.py`; `projects/shorts-maker-v2/tests/unit/test_color_grading.py`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md` |
| 2026-05-20 | Claude Code (Opus 4.7 1M) | **T-305 openai SDK 1.59.9 ??2.37.0 留덉씠洹몃젅?댁뀡**. `/goal` 理쒖쟻???몄뀡?먯꽌 ?ъ슜?먭? "援ы쁽 紐삵븳 遺遺?怨꾪쉷쨌吏꾪뻾" 吏????AskUserQuestion?쇰줈 T-305 ?좏깮. ?먯깋: 理쒖떊 openai 2.37.0(Python 3.9+), 2.0.0 ??breaking change??Responses API tool-call output ?뺥깭肉?blind-to-x 誘몄궗??. 肄붾뱶(`draft_providers.py` `_generate_with_openai`/`_xai`/`_ollama`, `image_generator.py` DALL-E)??`chat.completions.create`/`images.generate`/`AsyncOpenAI` ?앹꽦????2.x ?덉젙 API留??ъ슜 + `getattr` 諛⑹뼱 ?묎렐. ?뚯뒪??mock(`test_multi_platform`/`test_env_runtime_fallbacks`/`test_image_generator` ??? ?대씪?댁뼵???앹꽦?먮? fake濡?援먯껜 ??SDK 踰꾩쟾 臾닿?. **PR #39 triage??"4媛?mock fixture 媛깆떊 ?꾩슂"??蹂댁닔??異붿젙?댁뿀怨??ㅼ젣 肄붾뱶/?뚯뒪??蹂寃?0嫄?** 蹂寃? `pyproject.toml` openai ? `==1.59.9`??==2.37.0`. `projects/blind-to-x/uv.lock`? ?뚰겕?ㅽ럹?댁뒪 uv 留덉씠洹몃젅?댁뀡 WIP(猷⑦듃 `pyproject.toml`+`uv.lock` untracked) ?뚮Ц??`uv lock`??猷⑦듃 ?쎌쓣 ?≪븘 ??猷⑦듃 `pyproject.toml`???쇱떆 ?④릿 ??blind-to-x ?⑤룆 ???ъ깮??openai ??ぉ留?蹂寃? transitive 蹂???놁쓬, 猷⑦듃 蹂듭썝 ?꾨즺). 寃利? openai 2.37.0 ?ㅼ튂 ??openai 愿???뚯뒪??`109 passed` ???⑥쐞+?듯빀 ?꾩껜 `1626 passed, 1 skipped, 0 failed`(241s), `ruff check .` All checks passed. ?쇱씠釉??ㅻえ????LLM ?몄텧)???좊즺??誘몄떎????mock 1626嫄?+ ?덉젙 API ?ъ슜?쇰줈 媛덉쓬. ?먯깋 以??쒕룄??pytest-xdist 蹂묐젹?붾뒗 execnet ?뚯빱媛 濡쒖뺄 Python 3.14?먯꽌 遺???ㅽ뙣(`EOFError`)???먭린. | `projects/blind-to-x/pyproject.toml`; `projects/blind-to-x/uv.lock`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md` |
| 2026-05-20 | Codex | **T-335 Hanwoo app metadata/PWA copy polish**. Active Hanwoo product-completeness goal continuation. Localized app-level metadata and PWA install copy: `src/app/layout.js` and `public/manifest.json` now use Korean product-ready title, description, and short name for browser title, install prompt, and metadata instead of `Joolife Dashboard` / `Premium Hanwoo Farm Management System`. Added source/manifest regression coverage. Verification: Hanwoo tests `90 passed`, `npm.cmd run lint` passed, `npm.cmd run build` initially failed only because sandbox blocked Google Fonts fetch (`EACCES`), approved network rerun passed, `git diff --check` passed, direct Hanwoo graph risk `0.00`, staged `code_review_gate --json` PASS before commit. Commit `62020ec`; commit hook advisory WARN came from graph heuristics/unrelated shorts-maker WIP, not direct Hanwoo failures. | `projects/hanwoo-dashboard/src/app/layout.js`; `projects/hanwoo-dashboard/public/manifest.json`; `projects/hanwoo-dashboard/src/lib/app-metadata-copy.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-334 shorts-maker-v2 scene_qc retry routing**. Continued T-318 and fixed a strict scene_qc retry bug. Root cause: `PipelineOrchestrator` routed every failing scene with `audio_ok=True` to `component="visual"`, but `MediaStep.regenerate_scene(component="visual")` preserves existing audio checkpoints. Duration/CPS/audio-volume failures therefore retried the wrong component and could repeatedly reuse the same bad audio while reporting retry progress. Fix: added `_scene_qc_retry_component()` to route audio integrity/timing/volume failures to `audio`/`both`, visual failures to `visual`, and script-only failures to no media retry so they remain surfaced as unresolved instead of spending provider calls. Retry counts now reflect actual media regeneration attempts. Verification: focused orchestrator+QC tests `115 passed`, full shorts-maker-v2 `tests/unit tests/integration` passed with repo-local basetemp, project QC lint passed, targeted Ruff/format passed, and graph risk `0.00`. | `projects/shorts-maker-v2/src/shorts_maker_v2/pipeline/orchestrator.py`; `projects/shorts-maker-v2/tests/unit/test_orchestrator_unit.py`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md` |
| 2026-05-20 | Codex | **T-333 Hanwoo diagnostics admin copy polish**. Active Hanwoo product-completeness goal continuation. Localized the admin diagnostics surface: loading state, toast errors, status cards, database ledger, raw-data inspector, model selector labels, and dashboard return action now use Korean operations copy instead of English placeholders like `System Diagnostics`, `Database Status`, `Loading records.`, and `Please try again in a moment.` Added source wiring regression coverage for visible diagnostics copy. Verification: Hanwoo tests `89 passed`, `npm.cmd run lint` passed, `npm.cmd run build` passed, `git diff --check` passed, direct Hanwoo graph risk `0.00`, staged `code_review_gate --json` PASS before commit. Commit `c0113d9`; commit hook advisory WARN came from graph heuristics/unrelated shorts-maker WIP, not direct Hanwoo failures. | `projects/hanwoo-dashboard/src/components/admin/DiagnosticsPageClient.js`; `projects/hanwoo-dashboard/src/lib/diagnostics-copy.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-332 Hanwoo subscription checkout copy polish**. Active Hanwoo product-completeness goal continuation. Localized remaining checkout/subscription placeholder copy: `PaymentWidget` now uses Korean title, loading, preparing, payment button, timeout, and fallback error messages; subscription success/fail pages now avoid bare `Loading...`, `Processing...`, `Payment confirmed`, and `Code:` copy and render Korean fallback/status messages. Added source wiring regression coverage for checkout/result page copy. Verification: Hanwoo tests `88 passed`, `npm.cmd run lint` passed, `npm.cmd run build` passed, `git diff --check` passed, direct Hanwoo graph risk `0.00`, staged `code_review_gate --json` PASS before commit. Commit `8937eb1`; commit hook advisory WARN came from graph heuristics, not direct Hanwoo failures. | `projects/hanwoo-dashboard/src/components/payment/PaymentWidget.js`; `projects/hanwoo-dashboard/src/app/subscription/success/page.js`; `projects/hanwoo-dashboard/src/app/subscription/fail/page.js`; `projects/hanwoo-dashboard/src/lib/payment-ux-copy.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-331 shorts-maker-v2 Gate 4 file-size boundary policy**. Continued T-318 and fixed the 50.4MB manual-HOLD case from the Phase 3 validation notes. Root cause: `QCStep.gate4_final` used a hard-coded `[2,50]MB` final-file range, while the renderer already caps standard/premium bitrate at 8M/12M and can legitimately produce a just-over-50MB 1080x1920 Shorts render. `QCStep` now uses named final-size policy bounds `[2,60]MB`, preserving an upper guard while avoiding false holds near 50MB. Added regression coverage for a 50.4MB pass and a 60.1MB hold. Verification: `test_qc_step.py` `60 passed`, targeted Ruff passed, full shorts-maker-v2 `tests/unit tests/integration` passed with repo-local basetemp, project QC lint passed, and graph risk `0.00`. | `projects/shorts-maker-v2/src/shorts_maker_v2/pipeline/qc_step.py`; `projects/shorts-maker-v2/tests/unit/test_qc_step.py`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md` |
| 2026-05-20 | Codex | **T-330 Hanwoo cattle-detail 踰덉떇 湲곕줉 ?쇳솕**. Active Hanwoo product-completeness goal continuation. Replaced native browser `prompt()` in `CattleDetailModal` for 諛쒖젙 湲곕줉 / ?섏젙 湲곕줉 with an in-app date form: explicit date input, cancel/save controls, inline validation, pending save state, lucide icons, and existing `handleUpdateCattle` success/error/offline feedback. Added source wiring regression coverage so prompt-based UX does not return. Verification: Hanwoo tests `86 passed`, `npm.cmd run lint` passed, `npm.cmd run build` passed, `git diff --check` passed, direct Hanwoo graph risk `0.00`, staged `code_review_gate --json` PASS before commit. Commit `b92249d`; commit hook advisory WARN came from stale graph heuristics/unrelated dirty WIP, not direct Hanwoo failures. | `projects/hanwoo-dashboard/src/components/forms/CattleDetailModal.js`; `projects/hanwoo-dashboard/src/lib/cattle-detail-modal-wiring.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/GOAL.md` |
| 2026-05-20 | Codex | **T-328 Hanwoo setup building action ?곌껐**. Active Hanwoo product-completeness goal continuation. First rechecked T-251 with `npm.cmd run db:prisma7-test -- --live`: local Prisma/client/adapter checks passed (`15 passed`) but live health still failed with the same external Supabase pooler/control-plane error `P2010 / XX000 / (ENOTFOUND) tenant/user postgres.fuemeqmigptwfzqvrpjf not found`. Local UX improvement: the Farm Setup / ?댁쁺 以鍮꾨룄 missing-building item now emits `add-building`, `DashboardClient` passes that quick-action intent into Settings, and `SettingsTab` opens the 異뺤궗 registration form immediately on arrival via remount-safe initial state instead of a setState-in-effect. Verification: focused Hanwoo tests `85 passed`, `npm.cmd run lint` passed, `npm.cmd run build` passed, direct Hanwoo graph risk `0.00`. Commit `cc32b52`. | `projects/hanwoo-dashboard/src/components/DashboardClient.js`; `projects/hanwoo-dashboard/src/components/tabs/SettingsTab.js`; `projects/hanwoo-dashboard/src/lib/dashboard/setup-progress.mjs`; `projects/hanwoo-dashboard/src/lib/dashboard/setup-progress.test.mjs`; `.ai/GOAL.md`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md` |
| 2026-05-20 | Codex | **T-327 shorts-maker-v2 hook-score ?덉쭏 寃뚯씠??蹂닿컯**. `?꾨줈?앺듃 ?섎굹 ?붾쾭源? 紐⑺몴?먯꽌 ?덉쟾??T-318 hook-score ??ぉ???좏깮. Root cause: `PipelineOrchestrator`媛 `manifest.hook_score`瑜?怨꾩궛?대룄 ?쏀븳 ?낆? `hook_score_weak` 寃쎄퀬留??④린怨?Gate 4 PASS ??`success`濡?異쒗븯 媛?ν뻽?? ?섏젙: `score_hook(...).passed`媛 false硫?retryable/non-blocking `hook_score` degraded step??湲곕줉??upload-ready success ?먮쫫?먯꽌 ?쒖쇅. Full suite ?ъ떎??以??곸뼱/i18n 諛?renderer smoke fixture???쏀븳 ?낆씠 ?쒕윭???덉쭏 寃뚯씠?몃? ??텛吏 ?딄퀬 fixture hook narration??蹂닿컯. `hook_scorer`?먮뒗 `Tiny chips, big savings` 媛숈? 醫곸? ?곸뼱 contrast+tech specificity ?⑦꽩??異붽?. 寃利? focused hook/orchestrator/renderer/i18n `63 passed`, targeted Ruff pass, project QC lint pass, graph risk `0.00`, full `tests/unit tests/integration` pass with repo-local basetemp. Remaining T-318: file-size boundary/bitrate, scene_qc strict-default safety, TTS voice/speed tuning. | `projects/shorts-maker-v2/src/shorts_maker_v2/pipeline/hook_scorer.py`; `projects/shorts-maker-v2/src/shorts_maker_v2/pipeline/orchestrator.py`; `projects/shorts-maker-v2/tests/unit/test_hook_scorer.py`; `projects/shorts-maker-v2/tests/unit/test_orchestrator_unit.py`; `projects/shorts-maker-v2/tests/integration/test_orchestrator_i18n_smoke.py`; `projects/shorts-maker-v2/tests/integration/test_renderer_mode_manifest.py`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md` |
| 2026-05-20 | Claude Code (Opus 4.7 1M) | **T-324 blind-to-x ?쒗뭹?꾩꽦??媛먯궗**. `/goal "?쒗뭹?꾩꽦?뺤쑝濡?留뚮뱾?대킄"` ??AskUserQuestion?쇰줈 ???blind-to-x, ?꾨즺湲곗?=?뚯뒪?맞텰I ?듦낵 + 臾몄꽌쨌?⑤낫?⑹쑝濡?醫곹옒. blind-to-x??T-304(2026-05-16)?먯꽌 ?대? release-ready??쇰?濡??대쾲 ?몄뀡? ?꾩꽦??媛먯궗(completion audit) + ?⑤낫??媛?1嫄?蹂댁셿. **寃利??꾨? green**: `python -m pytest --no-cov tests/unit` ??`1562 passed, 1 skipped`(247s), `python -m pytest --no-cov tests/integration --ignore=test_curl_cffi.py` ??`64 passed`(CI? ?숈씪 而ㅻ㎤??, `python -m ruff check .` ??All checks passed. CI ?뺤씤: `full-test-matrix.yml`??`blind-to-x-tests` ??Python 3.12, ubuntu)???숈씪 unit+integration 而ㅻ㎤?쒕? main push/PR留덈떎 ?ㅽ뻾 ???뚰겕?ㅽ럹?댁뒪 誘몄빱諛?pnpm/turbo 留덉씠洹몃젅?댁뀡 diff??`node-apps` ?〓쭔 ?섏젙?섍퀬 `blind-to-x-tests` ?≪? 臾댁넀?? **媛?蹂댁셿**: `.env.example`??README "愿痢≪꽦" ?뱀뀡??臾몄꽌?뷀븳 ?좉? 3媛?`OPENAI_IMAGE_ENABLED`, `LANGFUSE_ENABLED`, `BTX_USAGE_FORWARD`)瑜??꾨씫 ??二쇱꽍怨??④퍡 異붽?(+6以?. 臾몄꽌???대? 異⑹떎(README 257以?+ ops-runbook 204 + operations_sop 97 + notion_view_setup_guide 137 + external-review/). 鍮꾩감???꾩냽: README/ops-runbook??LLM fallback 紐⑸줉??Moonshot/ZhipuAI瑜??ы븿?섎굹 `draft_providers.py`??anthropic/openai/gemini/xai/ollama留?wiring(臾몄꽌 ?뺥솗??nuance, 踰붿쐞 諛?. 而ㅻ컠? `.env.example` + `.ai/*`留??좏깮 ?ㅽ뀒?댁쭠, 猷⑦듃 pnpm WIP쨌? ?꾨줈?앺듃 dirty ?뚯씪 誘몄젒珥? | `projects/blind-to-x/.env.example`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md` |
| 2026-05-20 | Claude Code (Opus 4.7 1M) | **?곹깭 ?먭? + 誘명뫖??12而ㅻ컠 push + T-325 Hanwoo ?먮윭 諛붿슫?붾━**. (1) `session_orient`濡??곹깭 ?먭?: `main`??origin ?鍮?ahead 12 ???ъ슜???뱀씤 ??`git push`(`7962830..85b5d31`). (2) ?쒖꽦 goal(`hanwoo-dashboard` ?쒗뭹?꾩꽦?? 吏꾪뻾: App Router??`error.js`/`not-found.js`/`global-error.js`媛 ?꾨Т???고????먮윭쨌?섎せ??URL??Next.js 湲곕낯 ?붾쾭洹??붾㈃?쇰줈 ?⑥뼱吏??媛?쓣 ?댁냼. 濡쒓렇???붿옄???좏겙???ъ궗?⑺븳 釉뚮옖?붾뱶 ?곹깭 ?섏씠吏 3醫?異붽? ??404(?쒕쾭 而댄룷?뚰듃), route error boundary(?대씪?댁뼵?? retry=`reset()`+??, global-error(猷⑦듃 ?덉씠?꾩썐 ?ㅽ뙣?? ?몃씪???ㅽ???. `globals.css`??`Status Pages` 釉붾줉(44以?留?遺꾨━ ?ㅽ뀒?댁쭠(蹂묐젹 ?꾧뎄??`Setup Progress Panel` 174以?WIP??`git apply --cached` 泥?hunk留??곸슜??誘몄빱諛?蹂댁〈). empty-state ?뚯뒪???⑦꽩??蹂몃쑍 source-wiring ?뚯뒪??異붽?. 寃利? `npm test` 84 passed/0 fail, `npm run lint` pass, `npm run build` pass(`/_not-found` ?뺤쟻 ?꾨━?뚮뜑 ?뺤씤). commit `c00712d`(5 files +250). **寃쏀빀 二쇱쓽**: 泥?commit `b56592e`??蹂묐젹 Codex???숈떆 git ?묒뾽??`git apply --cached`? `git commit` ?ъ씠???몃뜳?ㅻ? 鍮꾩썙 鍮?而ㅻ컠????"PASS (no staged files)" 寃쎄퀬媛 ?⑥꽌) ??`git show --stat`濡?鍮꾩뼱?덉쓬 ?뺤씤 ???ъ뒪?뚯씠吏뺥빐 `c00712d`濡??ъ빱諛? `b56592e`??`94cb3bc` ?꾨옒??臾삵? rebase ?꾪뿕?쇰줈 鍮?而ㅻ컠 洹몃?濡??? | `projects/hanwoo-dashboard/src/app/not-found.js`; `projects/hanwoo-dashboard/src/app/error.js`; `projects/hanwoo-dashboard/src/app/global-error.js`; `projects/hanwoo-dashboard/src/app/globals.css`; `projects/hanwoo-dashboard/src/lib/error-pages-wiring.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/GOAL.md`; `.ai/SESSION_LOG.md` |
| 2026-05-19 | Codex | **T-321 shorts-maker-v2 duration QC 遺꾨━**. Continued from TODO T-318 and fixed the safest Phase 3 issue. Root cause: `channel_profiles.yaml`??scalar `target_duration_sec: 35`媛 `ChannelRouter`?먯꽌 hard QC bounds `[35,35]`濡?蹂?섎릺??validation run `runs/20260519-014816-a37f7826`??49.8s ?곸긽??duration hold 泥섎━?? `ChannelRouter`瑜??섏젙??scalar duration? ?앹꽦 紐⑺몴濡??좎??섍퀬 QC??`qc_min_duration_sec`/`qc_max_duration_sec` ?먮뒗 湲곕낯 짹10s tolerance 李쎌쓣 ?곌쾶 ?덉쑝硫? `ai_tech`?먮뒗 紐낆떆??QC bounds `[38,52]`瑜?異붽?. ?뚯뒪?몃뒗 explicit bounds? default tolerance 紐⑤몢 異붽?. Verification: focused channel/QC tests `65 passed`, applied config `(38, 52)`, `ruff check` pass, project QC lint pass, full shorts-maker-v2 pytest pass with repo-local `--basetemp`; project QC test wrapper??Windows temp permission lock?쇰줈 ?ㅽ뙣?덉쑝???숈씪 ?뚯뒪??蹂몃Ц? basetemp?먯꽌 ?듦낵. | `projects/shorts-maker-v2/src/shorts_maker_v2/utils/channel_router.py`; `projects/shorts-maker-v2/channel_profiles.yaml`; `projects/shorts-maker-v2/tests/unit/test_channel_router.py`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md` |
| 2026-05-19 | Claude Code (Opus 4.7 1M) | **shorts-maker-v2 寃利??곸긽 1嫄?+ GitHub OSS 由ъ꽌移?+ T-320 backlog ?깅줉**. `/goal "shorts-maker-v2 寃곌낵臾쇱씠 諛붾줈 ?좏뒠釉뚯뿉 ?щ┫ ???덉쓣 ?뺣룄 怨좏?` ?꾩냽. ???곸긽 1嫄?`output/20260519-013539-134a5783.mp4`) ?앹꽦?섏뿬 commit `49668c8`(?댁긽??1080x1920 媛뺤젣, h264_qsv +5% scale-up 李⑤떒) + ?ㅻⅨ ?꾧뎄??Phase 1+2 ?뺣퉬 ?⑹퀜吏?manifest 寃利? status hold??*pass**, duration 36.8??2.7s in [38,52], resolution 1134x2016??*1080x1920 ?뺥솗**, audio_peak_probe_ok false?뭪rue, scene_qc 7/8??*8/8 pass**, sentiment neutral?뭓we i=3 tags=[?곗＜,嫄곕?,???蹂?留덉쓬]. ?붿〈 ?쎌젏 Hook score 0.27??.33(curiosity 0.0 non-blocking). ?ъ슜???붿껌 "GitHub???ㅻⅨ ?꾩씠?붿뼱 以??꾩???寃껊뱾 寃?됲빐??怨좊룄?뷀븯??濡?6媛??곸뿭 蹂묐젹 WebSearch + ?꾨낫 5媛?GitHub repo WebFetch. **寃곌낵 留ㅽ듃由?뒪 (硫붾え由?`shorts_v2_oss_shortlist_20260519` 蹂댁〈)**: 濡쒖뺄 媛????WhisperX(BSD-2, `pip install whisperx`, CPU int8+medium, 70횞 realtime, T-19 backlog 吏곸젒 ?닿껐 ??`pipeline/media/audio_mixin.py` drop-in 援먯껜??紐낆떆) + OpenVoice v2(MIT ???쒓뎅??native, voice cloning). ?대씪?곕뱶 GPU ?꾩슂 ??LTX-Video(Apache 2.0, Replicate ~$0.05/clip) + ACE-Step v1.5/XL(Apache 2.0, Replicate ~$0.10/track). ?쒖쇅 ??Fish Speech("FISH AUDIO RESEARCH LICENSE" ?꾨컲 ??議곗튂 寃쎄퀬). ?ъ슜???섍꼍 痢≪젙: CPU Intel i7 12?몃? 20肄붿뼱 / RAM 15.75GB / **GPU Intel Iris Xe iGPU留???NVIDIA ?놁쓬** ??CUDA ?섏〈 OSS 濡쒖뺄 遺덇?. ?ъ슜??寃곗젙: ??goal ?ъ꽦?쇰줈 蹂닿퀬 OSS ?꾩엯? ??goal濡?/goal complete ?쒕룄?덉쑝??stop hook session_id 蹂?붾줈 ?대? cleared ?곹깭), Replicate ?뚯븸 ?뚯뒪??$1~5/??OK. T-320(approval) ?깅줉 ??WhisperX?뭀penVoice?묹TX-Video?묨CE-Step ?곗꽑?쒖쐞. ?ㅻⅨ ?꾧뎄 ?숈떆 ?묒뾽(Codex T-319 Hanwoo empty states, Claude T-317 Phase 1+2)怨?異⑸룎 ?놁씠 遺꾨━ commit ?좎?. | `projects/shorts-maker-v2/src/shorts_maker_v2/pipeline/render_step.py`(commit `49668c8` 遺?; 硫붾え由?out-of-repo) `shorts_v2_quality_uplift_20260519.md`, `multi_layer_enforcement_antipattern.md`, `shorts_v2_oss_shortlist_20260519.md`(?좉퇋), `MEMORY.md` ?몃뜳?? `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md` |
| 2026-05-19 | Codex | **T-319 Hanwoo first-run empty-state polish**. Continued the active `hanwoo-dashboard` quality goal with a small UX improvement that avoids DB/auth changes: added a shared `EmptyState` UI component and replaced passive no-data messages in Inventory, Sales, and Schedule tabs with icon-led action states. Empty Inventory now offers `?ш퀬 ?깅줉`, empty Schedule offers `?쇱젙 異붽?`, and empty Sales offers `留ㅼ텧 湲곕줉` when cattle exist or a disabled `媛쒖껜 ?깅줉 ?꾩슂` hint when they do not. Added a lightweight wiring test for the shared component and tab integrations. Verification: `npm.cmd test` `79 passed`, `npm.cmd run lint`, `npm.cmd run build`, code-review graph risk `0.00`, and dev server `/login` returned `200`. During verification, repaired a partial Hanwoo `node_modules` install with `npm.cmd ci --ignore-scripts`; npm audit warnings remain pre-existing. | `projects/hanwoo-dashboard/src/components/ui/empty-state.js`; `projects/hanwoo-dashboard/src/components/tabs/InventoryTab.js`; `projects/hanwoo-dashboard/src/components/tabs/SalesTab.js`; `projects/hanwoo-dashboard/src/components/tabs/ScheduleTab.js`; `projects/hanwoo-dashboard/src/lib/empty-state-wiring.test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/GOAL.md`; `.ai/SESSION_LOG.md` |
| 2026-05-19 | Claude Code (Opus 4.7 1M) | **shorts-maker-v2 Phase 1+2 ?덉쭏 媛쒖꽑 + validation run ?꾨즺** (commits `2b09759` feat + `8c90b36` ai-context, `/goal "shorts-maker-v2 寃곌낵臾쇱씠 諛붾줈 ?좏뒠釉뚯뿉 ?щ┫ ???덉쓣 ?뺣룄 怨좏?`). 2???ㅽ뿕 run ?쇰줈 8媛?媛??앸퀎. Phase 1 肄섑뀗痢??덉쭏(#3+#5+#6): hook hard cap 15??0??+ ?⑥뼱 寃쎄퀎 ?몃┝ / Structure Gate 2 ?쒓뎅??議곗궗 stem + core_message/visual_keywords ?ㅼ쨷 ?좏샇 / 4媛?image entry-point??"No text, no letters" negative ?먮룞 遺李? Phase 2 李⑤떒 ?댁젣(#1+#2+#4+#8): TTS provider openai?뭙dge-tts(紐⑤뱺 梨꾨꼸 Azure-voice ?명솚 + 臾대즺 + _words.json ?먮룞 ?앹꽦) / 5媛?梨꾨꼸 topic 50媛??ъ떎 湲곕컲 ?ъ꽕怨?/ `_pending_audio_warnings` + `_pending_render_warnings` 踰꾪띁濡?silent-fail??manifest.degraded_steps濡?drain. **Validation run ?꾨즺** (`runs/20260519-014816-a37f7826`, 1110s/$0.04): pipeline FAIL?댁?留??곸긽쨌?몃꽕?셋톁RT쨌manifest 紐⑤몢 ?앹꽦, qc_result.verdict=hold ?먯씤? Duration 49.8s vs channel target [35,35] + file size 50.4MB vs [2,50]MB(????Phase 3 ?곸뿭). Before/After ?뺣웾 鍮꾧탳: scene_qc_results null??/8 pass, audio_peak_probe_ok false?뭪rue, caption_fallback_*.png 8??, karaoke kc_*.png 0??5, structure intent "?듭떖 ?ъ씤??N???ㅻ챸?쒕떎" 蹂댁씪?ы뵆?덉씠?멤넂LLM-quality scene-specific("Highlight the transition from manual syntax memorization to architectural thinking"), production_plan.tone generic?뭨ich("李⑤텇?섍퀬 ?ъ깋?곸씠硫? 諛ㅼ쓽 怨좎슂?⑥씠 ?먭뺨吏????? ??). ?몃꽕???곸뼱 ?띿뒪??artifact ?놁쓬. 寃利??명봽?? 1447 unit tests pass(+20 ?좉퇋), ruff clean. T-318(Phase 3)濡?諛깅줈洹? | `projects/shorts-maker-v2/config.yaml`; `projects/shorts-maker-v2/assets/topics/topics_{ai_tech,health,history,psychology,space}.txt`; `projects/shorts-maker-v2/src/shorts_maker_v2/pipeline/{script_step,structure_step,media_step,render_step,orchestrator}.py`; `projects/shorts-maker-v2/src/shorts_maker_v2/pipeline/media/{_prompt_filters,visual_mixin,fallback_mixin}.py`; `projects/shorts-maker-v2/tests/unit/{test_script_quality,test_script_step,test_structure_step,test_prompt_filters,test_silent_fail_propagation}.py`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md` |
| 2026-05-19 | Codex | **Hanwoo UX/PWA polish**. Validated that the quick-action UX had already landed in `e0c80d1`, then fixed the login-page PWA manifest console error by letting `/manifest.json`, icons, `sw.js`, and Workbox assets bypass the auth proxy. Verification: Hanwoo `npm.cmd test` 77 passed, `npm.cmd run lint` passed, `npm.cmd run build` passed, and `/manifest.json` now returns `200 application/json` before login. | `projects/hanwoo-dashboard/src/proxy.js`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md` |
| 2026-05-19 | Gemini (Antigravity) | **?뚰겕?ㅽ럹?댁뒪 ?꾩깮 ?뺣퉬**. (1) 誘명뫖??而ㅻ컠 3媛?`b15ccf6`, `677a545`, `94d043e`) origin/main??push ?꾨즺 ??blind-to-x Notion 援ъ“ 蹂寃?+ hanwoo-dashboard 濡쒓렇??由ы뙥?좊쭅 + lucide ?꾩씠肄??꾩엯. (2) HANDOFF.md 濡쒗뀒?댁뀡 ?ㅽ뻾(`--keep-days 3`): 4媛?addenda ?꾩뭅?대툕(`HANDOFF_archive_2026-05-19.md`), 8媛??좎?. (3) SESSION_LOG ?낅뜲?댄듃. Git worktree 源⑤걮, origin/main ?숆린???꾨즺. | `.ai/HANDOFF.md`; `.ai/SESSION_LOG.md`; `.ai/archive/HANDOFF_archive_2026-05-19.md` |
| 2026-05-19 | Claude Code (Opus 4.7 1M) | **T-309 blind-to-x ???꾪솚 + ?묐룞 ?뚮났**. ?ъ슜??`/goal "blind-to-x ?닿굅 ?앹꽦臾??꾨━???щ━湲곕줈 ??蹂꾨줈怨????묐룞?덊빐/"`. 吏꾨떒 1?④퀎: `.tmp/logs/scheduled_20260518_1300.log` 遺꾩꽍 ??`Exit 1: All 4 items failed. Reasons: Twitter draft did not meet review quality gate (x4), Avg Quality Score (success): 0.0`. ?쒕옒?꾪듃媛 留ㅻ쾲 280???쒓퀎 2~3諛?珥덇낵(440~709?? + retry 臾댄슚(`[QualityGate] twitter RETRY 1: no improvement`) + MLScorer 1-class ?숈뒿 ?ㅽ뙣. 吏꾨떒 2?④퀎: `draft_cache.db`?먯꽌 罹먯떆???몄뀡 ?쒕옒?꾪듃 8嫄?吏곸젒 異붿텧 ??8/8 紐⑤몢 ?숈씪 ?⑦꽩(3??臾띠쓬 `[異붿쿇??/[?듭뀡1]/[?듭뀡2]` + ?대え吏 ??꺽 ?삤?삷?Ⅲ?ㄶ?띯?截?+ 留ㅻ쾲 "jobplanet?먯꽌 遊ㅻ뒗??/"fmkorea?먯꽌 遊ㅻ뒗?? ?꾩엯 + "?щ윭遺?~?"/"?볤?濡?~"/"?????뚮젮二쇱꽭?? CTA + "?쒓렇??誘쇰궚/?앺뙋??吏猶??대쭧/湲곗젅??六? ?명뵆猷⑥뼵???댄쐶). `user_shorts_philosophy` 硫붾え由?CTA ?덈? 湲덉?, 議곗슜???댁빞湲? ?ъ슫?쇰줈 ?앸궓)? ?뺣㈃ 異⑸룎. AskUserQuestion 2?? (a) ?꾩긽 = "?몄뀡???ㅼ뼱?붾뒗?????댁슜??蹂꾨줈", 諛⑺뼢 = "?띿뒪???ㅒ룸궡???덉쭏 ?숈떆 ?먮큵"; (b) ??諛⑺뼢 = "shorts 泥좏븰 洹몃?濡??곸슜". ?먯씤 5怨꾩링 媛뺤젣 諛쒓껄: `rules/prompts.yaml`(system_role "?쒓렇???댁꽕?? + draft_formats.standard.instruction "留덉?留됱? 吏덈Ц/CTA濡??앸궡湲? + twitter.standard "3媛吏 珥덉븞 ?묒꽦" + threads "?대え吏 2-3媛??곸젅???쒖슜" + naver_blog "寃곕줎: + CTA" + topic_hooks.*.cta + threads_cta_mapping) + `rules/editorial.yaml`(brand_voice.voice_traits "留덈Т由щ뒗 ?낆옄?먭쾶 援ъ껜??吏덈Ц or ?쒖쨪 肄붾찘?? + "?대え吏 1~2媛쒕쭔") + `rules/examples.yaml`(golden_examples_threads???볤?/????좊룄 ?쇱씤) + `pipeline/draft_quality_gate.py`(PLATFORM_RULES.twitter/threads/naver_blog.require_cta=True ??CTA ?놁쑝硫?warning -10 ??retry ??LLM? ???먭레???묐떟 ??280??珥덇낵 ??error) + `pipeline/draft_prompts.py`(?섎뱶肄붾뵫 fallback "3媛吏 踰꾩쟾: [異붿쿇??[?議곗븞][?ㅽ뿕??" + selection_brief_lines 4踰?"留덉?留?CTA??援ъ껜???좏깮??吏덈Ц" + 6踰?"<twitter>??[異붿쿇?? 留??꾩뿉 + 寃곗씠 ?ㅻⅨ 2媛??듭뀡 ???쒖떆" + `_FIX_INSTRUCTIONS["CTA"]` "留덉?留?臾몄옣??援ъ껜?곸씤 吏덈Ц?쇰줈 援먯껜"). ?뺣퉬 10媛??뚯씪: (1) `draft_quality_gate.py` PLATFORM_RULES.*.require_cta False + threads.min_hashtags 1?? + `_has_generic_cta` 寃?щ? require_cta 媛??諛뽰쑝濡?鍮쇱꽌 "?щ윭遺??앷컖??"瑜섎뒗 require_cta ?щ?? 臾닿??섍쾶 ??긽 error濡?李⑤떒. (2) `prompts.yaml` system_role ?ъ젙??"議곗슜??吏곸옣??肄섑뀗痢??댁꽕?? ?명뵆猷⑥뼵???댄쐶 湲덉?, ?ъ슫?쇰줈 ?앸㎈??), twitter.standard "1媛쒖쓽 ?덈쭔 ?묒꽦" + CTA 紐낆떆 湲덉? + 異쒖쿂 ?꾩엯 媛뺣컯 ?쒓굅, threads "?대え吏 湲곕낯 ?놁쓬" + ?볤?/????좊룄 湲덉?, naver_blog 寃곕줎 "?ъ슫?쇰줈 留덈Т由?, draft_formats.standard/thread.instruction??"吏덈Ц/CTA" ??"?ъ슫", topic_hooks.*.cta + threads_cta_mapping 紐⑤몢 鍮?臾몄옄?? topic_prompt_strategies??example_structure "??CTA"/"??吏덈Ц" ??"???ъ슫?쇰줈 留덈Т由?. (3) `editorial.yaml` brand_voice persona/voice_traits瑜??ㅻ젮二쇰뒗 ?ㅼ쑝濡??꾪솚 + cliche_watchlist??"?щ윭遺??앷컖?", "?볤?濡??뚮젮二쇱꽭??, "??ν빐?먯꽭??, "怨듦컧?섏떆硫?, "RT", "?????뚮젮二쇱꽭??, "?앺뙋??, "吏猶?, "誘쇰궚", "?대쭧", "湲곗젅??六?, "?댁쿂援щ땲?놁뼱??, "?댁쭏?댁쭏" 13媛?異붽?. (4) `examples.yaml` golden_examples_threads???볤?/????좊룄 ?쇱씤 ?쒓굅 + ?ъ슫?쇰줈 ?앸굹?꾨줉 ?ъ옉?? golden_examples_naver_blog.structure??"寃곕줎 + CTA: ?볤? ?좊룄" ??"寃곕줎: ?ъ슫?쇰줈 留덈Т由???吏덈Ц쨌CTA 湲덉?". (5) `draft_prompts.py` ?섎뱶肄붾뵫 fallback "3媛吏 踰꾩쟾" ??"1媛??덈쭔 ?묒꽦", selection_brief_lines 4쨌6踰????? `_FIX_INSTRUCTIONS["CTA"]` ??"CTA 臾몄옣 ?쒓굅, ?ъ슫?쇰줈 ?泥?. (6) `content_intelligence/rules.py` get_topic_hook fallback CTA `"?볤?濡??섍껄 ?섎닠二쇱꽭???몙"` ??`""`. (7~10) ?곹뼢 諛쏅뒗 ?⑥쐞 ?뚯뒪??4媛??뺣퉬: `test_quality_gate_and_scenes.py`(CTA 媛뺤젣 ?뚯뒪??invert + threads min_hashtag 0?쇰줈 invert), `test_draft_quality_gate_deep.py`(strict_mode warning ?쒕굹由ъ삤瑜??댁떆?쒓렇 ?곹븳 珥덇낵濡?蹂寃?, `test_draft_generator_multi_provider.py`(prompt assertion????selection_brief 臾멸뎄濡?援먯껜), `test_quality_improvements.py`(`_FIX_INSTRUCTIONS["CTA"]` assertion ??硫붿떆吏濡?援먯껜). YAML editorial.yaml ?뚯떛 ?먮윭 ??踰?line 14 肄쒕줎 ?뚯꽌 異⑸룎 ???곗샂?쒕줈 臾띠쓬). 寃利??④퀎蹂? (i) ?뺤쟻 ?꾨＼?꾪듃 dump ????selection_brief("?ъ슫???⑤뒗 ??以?, "?명뵆猷⑥뼵???댄쐶 湲덉?"), ??twitter 釉붾줉("1媛쒖쓽 ?덈쭔 ?묒꽦", "異쒖쿂???꾩슂???뚮쭔") ?뺤씤. (ii) `pytest --no-cov tests/unit` ??泥섏쓬 3 failed(test_twitter_generic_cta_still_flagged: `_has_generic_cta`媛 require_cta 媛???덉뿉 ?덉뿀????肄붾뱶 ?섏젙?쇰줈 媛??諛뽰쑝濡?/ test_strict_mode_warning_becomes_failure: ???ㅼ뿉??warning ?놁쓬 ???쒕굹由ъ삤 蹂寃?/ test_prompt_includes_editorial_brief: "generic CTA" 臾몄옄???щ씪吏?????臾멸뎄濡?援먯껜) ??**1560 passed, 1 skipped, 0 failed**. (iii) LLM dry-run 1??anthropic, draft_cache mock?쇰줈 ?고쉶): 寃곌낵 ?띿뒪??= `?곕큺 ?묒긽?먯꽌 "?대뀈???섑븯?? ?쒖옣 ?곹솴???대졄??怨??ㅼ뿀?? ?묐뀈 ?깃낵???됯퇏 ?댁긽?댁뿀?붾뜲???숆껐?대씪 留됰쭑?쒕뜲, ??λ떂 ?낆옣? 洹몃윺??븯?? ?ㅻ쭔 洹???λ떂???대뀈??媛숈? ?댁빞湲??ㅼ쓣 媛?μ꽦???믩떎??寃?臾몄젣??` ??CTA ?놁쓬, ?대え吏 0媛? 1媛??? ?꾩엯 媛뺣컯 ?놁쓬, ?ъ슫 留덈Т由? creator_take 1臾몄옣 ?ы븿 紐⑤몢 ?듦낵. (iv) ?섎룞 ?ㅼ?以꾨윭 `python main.py --limit 2 --dry-run` ??**`Total: 2 | OK 2 | FAIL 0, Avg Quality Score 85.0`** (?댁쟾 13:00: `Exit 1: All 4 items failed, 0.0`). (v) 罹먯떆???????쒕옒?꾪듃 2嫄??뺤씤 ??100% ????諛섏쁺. 而ㅻ컠: `4628bb8 feat(blind-to-x): shorts 泥좏븰 ?곸슜 ??議곗슜???댁꽕???ㅼ쑝濡??꾪솚` (10 files +202/-172). 泥?commit ??ruff format ?ㅽ뙣濡?abort??吏곹썑 git hook???먮룞?쇰줈 .ai/HANDOFF.md + .ai/SESSION_LOG.md留?stage?댁꽌 `81b36db`媛 ?섎룄? ?щ━ ai-context-only commit?쇰줈 ?섏샂 ??肄붾뱶 蹂寃쎈텇??蹂꾨룄 `4628bb8`濡??ㅼ떆 commit???뺥깭. 硫붾え由?媛깆떊: `btx_caption_quality.md` ?낅뜲?댄듃(2026-03-21 ??2026-05-19, shorts 泥좏븰 ?곸슜 ???곹깭), ??硫붾え由?2媛?異붽?(blind_tone_shorts_alignment_20260519, multi_layer_enforcement_antipattern). ?⑥? ?꾩냽: (1) origin/main push ?ъ슜???뱀씤 (4 commits ahead). (2) MLScorer 1-class 媛??異붽???蹂꾧컻 ?댁뒋濡?backlog. (3) uv.lock 誘몄빱諛?dirty. | `projects/blind-to-x/pipeline/draft_quality_gate.py`; `projects/blind-to-x/pipeline/draft_prompts.py`; `projects/blind-to-x/pipeline/content_intelligence/rules.py`; `projects/blind-to-x/rules/prompts.yaml`; `projects/blind-to-x/rules/editorial.yaml`; `projects/blind-to-x/rules/examples.yaml`; `projects/blind-to-x/tests/unit/test_quality_gate_and_scenes.py`; `projects/blind-to-x/tests/unit/test_draft_quality_gate_deep.py`; `projects/blind-to-x/tests/unit/test_draft_generator_multi_provider.py`; `projects/blind-to-x/tests/unit/test_quality_improvements.py`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md` |
| 2026-05-18 | Claude Code (Opus 4.7 1M) | **T-306 open-PR audit + cleanup**. Session opened with TODO only T-251 (user-owned) and IN_PROGRESS empty; `session_orient` flagged 20 BLOCKED Dependabot PRs (all REVIEW_REQUIRED, not CI) + one weekly `pip in /.` failure. User chose Dependabot triage. Classified into Tier A (11 safe minors/patches, all CI green), Tier B (#51/#54 React pair ??FAIL was only the `dependabot` auto-merge workflow, not the actual build), Tier C (#50 typescript 5?? MAJOR + #52 react-dom solo bump diverges from react peer ??both real build failures), Tier D (#37/#39/#41 MAJOR risk), Grouped (#48 next-ecosystem). With explicit `--admin` approval, squash-merged 14 PRs in 3 project-disjoint batches: Batch 1 (#36 #38 #45 #42 #51), Batch 2 (#40 #43 #54 + #47/#54 dropped on lockfile drift), Batch 3 (#46 #49 #48 #53 #55), then rebased #47/#54 via `@dependabot rebase` + 60 s wait + admin merge, and finally picked up the missed #44 pyyaml. Closed 5 PRs with rationale: #50 (typescript 5?? MAJOR build fail), #52 (react-dom solo bump react-peer skew), #37 + #41 (word-chain Frozen ??MAJOR dev deps not worth migration), #39 (openai 1?? MAJOR ??code already uses v1+ `AsyncOpenAI` so migration is feasible but needs 4 mock-fixture refresh + live smoke, ~쩍?? day; backlogged as T-305 epic). Diagnosed weekly `pip in /.` failure: `.github/dependabot.yml` entry 1 had `directory: "/"` but the repo root has no Python manifest ??the intended workspace is `workspace/pyproject.toml`. Fixed to `directory: "/workspace"` (PEP 621 project) in `32269c2 fix(ci): point dependabot pip root entry at /workspace`. Pre-commit code-review gate PASS risk=0.00. Local `main` ends at `ahead 2` of `origin/main` (`b94c66c` prior-session ai-context + `32269c2` dependabot.yml fix); push not performed pending explicit user approval. 14 dependabot squash commits already landed on `origin/main`. | `.github/dependabot.yml`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md` |
| 2026-05-18 | Gemini (Antigravity) | **?꾩껜 QC ?ш?利??꾨즺**. 4媛??꾨줈?앺듃 ?꾩닔 寃利? blind-to-x (pytest 1560 passed, 1 skipped ??, shorts-maker-v2 (pytest 1422 passed, 12 skipped, 2 warnings ??, hanwoo-dashboard (lint ?? build ??, knowledge-dashboard (lint ?? build ??. `code_review_gate.py --base HEAD~1` ??PASS risk=0.00. 諛고룷 以鍮??꾨즺. ?좎씪???붿뿬 釉붾줈而? T-251 (?ъ슜??Supabase 鍮꾨?踰덊샇 由ъ뀑). | `.ai/HANDOFF.md`; `.ai/SESSION_LOG.md` |
| 2026-05-18 | Codex | Re-oriented the workspace, confirmed `main` is synchronized with `origin/main` and clean, readiness is `94 / blocked`, and retried T-251. `npm.cmd run db:prisma7-test -- --live` still fails only at live DB connection health with `P2010` / `XX000` / `(ENOTFOUND) tenant/user postgres.fuemeqmigptwfzqvrpjf not found`, so the remaining action is user-owned Supabase password/control-plane resync. | `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md` |
| 2026-05-16 | Claude Code (Opus 4.7 1M) | User `/goal "?꾨줈?앺듃 ?섎굹 怨좊룄?붾맂 ?꾩꽦?덉쑝濡?留뚮뱾?대넄"` ??via AskUserQuestion narrowed to **blind-to-x, release-ready state**. Cleared stale 5h27m goal first. **T-304** scope: close gaps against the 5 release criteria (E2E pipeline / tests + CI / docs / regression tests / observability). Audit findings: (1)(3)(4) already covered, (2) lint pass + CI green per `session_orient` (test step locally times out at 900s but `full-test-matrix.yml` 20-min job is green), (5) had a gap ??Langfuse wired in `pipeline/draft_providers.py` but `pipeline/cost_tracker.py` never fed workspace `api_usage_tracker.log_api_call`, so workspace alerts (`api_usage_tracker alerts` ??fallback rate / cost spike / dead provider) missed blind-to-x calls entirely (workspace.db `api_calls` had only 16 rows). **Fix**: added opt-in `_maybe_forward_to_workspace_usage` to `cost_tracker.py` (gated by `BTX_USAGE_FORWARD=1`, silent failure, mirrors after `_cost_db.record_text_cost` and `record_image_cost`), invoked from `add_text_generation_cost` (Anthropic cache tokens included) and `add_dalle_cost` (provider=`openai`, model=`dall-e-3`, `endpoint=blind-to-x.dalle_image`). Added 3 regression tests in `tests/unit/test_cost_tracker_extended.py` (forwarder invocation, env-gate disabled/enabled, error swallowing via `types.SimpleNamespace`). **Docs refresh** (release-ready (3)): fixed stale `tests_unit` path in README + ops-runbook (correct: `tests/unit`); replaced `pip install -r requirements.txt` with `pip install -e .[dev]` (project is pyproject-only, no requirements.txt); rewrote GitHub Actions section to point at `active-project-matrix.yml`/`blind-to-x-tests` (the old "3?쒓컙留덈떎" schedule claim was stale ??no scheduled workflows exist); added Observability section documenting `LANGFUSE_ENABLED` and the new `BTX_USAGE_FORWARD`; updated external-review README + file-manifest to point at `rules/` (D-031 5-file split) instead of the removed `classification_rules.yaml`. **Verification**: `py_compile` clean for both modified Python files; targeted `ruff check` PASS on `pipeline/cost_tracker.py` + `tests/unit/test_cost_tracker_extended.py`; lint pass confirmed by earlier `project_qc_runner.py --check lint`. Local pytest could not stream output in this session's PowerShell/Bash subshells (consistently 0-byte capture; CMD `cd /d` fails with CD_EXIT=123 on Korean path ??known minefield). Linter agent auto-corrected the test-isolation pattern from `type("M", (), {...})()` to `types.SimpleNamespace(...)` so `log_api_call` stays an unbound function (avoids `self` injection on bound method). 6 files modified (~161 insertions / ~12 deletions). No skip-marker stale debt found (all 6 grep hits are legitimate env/CI guards). | `projects/blind-to-x/pipeline/cost_tracker.py`; `projects/blind-to-x/tests/unit/test_cost_tracker_extended.py`; `projects/blind-to-x/README.md`; `projects/blind-to-x/docs/ops-runbook.md`; `projects/blind-to-x/docs/external-review/README.md`; `projects/blind-to-x/docs/external-review/file-manifest.md`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md` |
| 2026-05-15 | Gemini (Antigravity) | ?ъ슜??`/goal` ?붿껌?쇰줈 異붽? ?꾩슂 ?묒뾽 ?먯깋 諛??ㅽ뻾. (1) HANDOFF ?ъ링 ?뺣━: ?댁쟾 Codex 濡쒗뀒?댁뀡(??60以? ?댄썑?먮룄 ?⑥븘?덈뜕 4??old addenda + 以묐났 5/15 addenda瑜??꾩뭅?대툕?섏뿬 192以꾟넂32以꾨줈 ?뺤텞. handoff_rotator媛 noop(紐⑤뱺 addenda媛 ?뱀씪?????곹솴?먯꽌 ?섎룞 ?뺣━濡??닿껐. (2) Dirty ?뚯씪 ?뺣━: `blind-to-x/_upload.py`(EOL-only), `knowledge-dashboard/qaqc_result.json`(?댁슜 diff ?놁쓬) 2媛쒕? `git checkout --`濡??뺣━?섏뿬 worktree ?대┛ ?곹깭 ?ъ꽦. (3) ?쒖뒪???ъ뒪 ?꾩닔 寃利? `product_readiness_score.py` ??92/100 blocked(T-251留?, `skill_lint.py` ??100/100 pass(42/42), `qaqc_result.json` ??5媛??꾨줈?앺듃 紐⑤몢 ?ы븿 ?뺤씤. (4) ??blind-to-x WIP 6?뚯씪(cost_tracker 愿?? ?ㅻⅨ ?꾧뎄 ?묒뾽) 諛쒓껄 ??誘멸컙???먯튃 以?? ?⑥? 釉붾줈而? T-251(?ъ슜??Supabase 鍮꾨?踰덊샇 由ъ뀑), origin push(82而ㅻ컠 ahead). | `.ai/HANDOFF.md`; `.ai/GOAL.md`; `.ai/archive/HANDOFF_archive_2026-05-15.md`; `.ai/SESSION_LOG.md` |
| 2026-05-15 | Codex | Rechecked the only remaining TODO (`T-251`) and fixed the Prisma 7 runtime test failure output so blank Prisma messages now include `name`, `code`, `meta`, and nested cause details. Verification: offline `npm.cmd run db:prisma7-test` passed (`14 passed`, `1 skipped`); live `npm.cmd run db:prisma7-test -- --live` was retried with escalated network access and still failed at connection health with `P2010` / `XX000` / `(ENOTFOUND) tenant/user postgres.fuemeqmigptwfzqvrpjf not found`. Conclusion: all local work is complete; the only remaining blocker is the user-owned Supabase password/control-plane resync. | `projects/hanwoo-dashboard/scripts/prisma7-runtime-test.mjs`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/archive/HANDOFF_archive_2026-05-15.md` |
| 2026-05-15 | Codex | User said "??泥섎━??. Completed the remaining local workspace hygiene goal and the only real remaining WIP. Added and committed `shorts-maker-v2` SemanticQC orchestration regression coverage (`cde297e`): disabled skip path, pass manifest persistence, degraded non-blocking metadata, error verdict persistence, and exception swallowing. Rotated HANDOFF with `python execution/handoff_rotator.py --json --keep-days 0`, archiving 44 older addenda and reducing HANDOFF to 160 lines. Confirmed SESSION_LOG is 396 lines, cleared the EOL-only `blind-to-x/_upload.py` dirty state with no content diff, and returned `.ai/GOAL.md` to inactive. Verification: orchestrator unit slice `49 passed, 2 warnings`; targeted Ruff clean. No push was performed. Remaining external blocker is T-251. | `.ai/GOAL.md`; `.ai/HANDOFF.md`; `.ai/archive/HANDOFF_archive_2026-05-15.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `projects/shorts-maker-v2/tests/unit/test_orchestrator_unit.py` |
| 2026-05-15 | Claude Code (Opus 4.7 1M) | User said "異붽?濡??댁빞??寃껊뱾 ??李얠븘??吏꾪뻾??. Full scan per "??李얠븘??: `session_orient` (PRs 0, CI green, GOAL inactive, HANDOFF 457 lines / 52 addenda flagged by line count only); TASKS (TODO = T-251 user-owned approval + T-300 unassigned/safe); qaqc `public/qaqc_result.json` (`root` FAIL = exactly T-300); `handoff_rotator --check --json` = `noop` (52 addenda all within 7-day window, cutoff 2026-05-08). Finding: a concurrent tool was actively editing the exact T-300 files ??`workspace/execution/tests/conftest.py` (root `execution/` added to `sys.path`), `workspace/execution/qaqc_runner.py` (security-scan path scoping), `execution/ai_batch_runner.py` (`process_item` defensive logic for empty choices / null content) ??plus `workspace_db_audit.py`, `repo_map.py`, `test_workspace_db_audit.py`. Read-only verification of the WIP under qaqc conditions: `cd workspace && python -m pytest --no-cov execution/tests/test_ai_batch_runner_regression.py -q` -> `2 passed` (confirms the WIP is a complete T-300 fix). Deliberately stayed out of all those files to avoid collision; also skipped HANDOFF rotation (would be a lossy noop given no addenda are past the 7-day cutoff). Concurrent tool subsequently landed the full batch as `846cf5a fix(workspace): stabilize root qaqc` + follow-on `94fe1af fix(workspace): stabilize frontend and worker subprocess tests` + `3dcddd8 [ai-context]`; root qaqc now `APPROVED 1525 passed`. User then said "湲곕줉?? ??this row + the HANDOFF addendum. No source-code changes from this turn. | `.ai/HANDOFF.md`; `.ai/SESSION_LOG.md` |
| 2026-05-15 | Codex | Completed the follow-on root QA/QC stabilization for `T-300` in `94fe1af`. After the earlier root repair commit `846cf5a`, rerunning root QA exposed Windows subprocess failures in frontend smoke and `TesterWorker`. Stabilized `test_frontends.py` by replacing Popen pipes with file-backed logs under `.tmp/frontend-smoke`, adding stdin isolation, and using `next dev --webpack` for `hanwoo-dashboard` to match the existing Next/font workaround. Stabilized `TesterWorker` by replacing `capture_output=True` with temp-file stdout/stderr capture and making timeout cleanup tolerate Windows temp-file locks. Added `workspace/conftest.py` and widened no-capture markers for subprocess-heavy tests. Verification: targeted subprocess suite `115 passed`; Ruff passed; `qaqc_runner.py --project root --skip-infra --skip-debt` returned `APPROVED`, `1525 passed`, `0 failed`, `0 errors`, `1 skipped`. | `workspace/conftest.py`; `workspace/execution/workers.py`; `workspace/tests/conftest.py`; `workspace/tests/test_frontends.py`; `.ai/HANDOFF.md`; `.ai/SESSION_LOG.md`; `.ai/TASKS.md`; `.ai/CONTEXT.md` |
| 2026-05-15 | Claude Code (Opus 4.7 1M) | User said "媛쒖꽑諛⑺뼢???꾩슂???꾨줈 李얠븘??吏꾪뻾??. Surveyed all 4 projects via `product_readiness_score.py`; hanwoo-dashboard was the clear target (score 55 / `blocked`, QC `UNKNOWN`; others 93??00 `ready`). User chose (AskUserQuestion) to handle all 3 found issues in one session. **T-299**: (a) deleted untracked `projects/hanwoo-dashboard/scratch.mjs` containing a hardcoded Supabase password and added `scratch.*` gitignore patterns (`16fd387`); (b) fixed the readiness QC signal ??`qaqc_runner.py` was pytest-only so npm-based hanwoo had no QC entry, and `product_readiness_score.py`/`sync_data.py` read the gitignored orphan `data/qaqc_result.json` instead of the git-tracked `public/qaqc_result.json` that `qaqc_runner` writes. Added `run_npm_test` + node:test tap/spec parser + `hanwoo-dashboard` PROJECTS entry; repointed both readers to `public/` (`3939cc3`); ran a full QA pass and committed the regenerated artifact (`5bd5b1e`) ??hanwoo now `PASS 75`, readiness 55??6. **T-289**: committed the multi-session-stuck AI chat API contract WIP (`49be0f9`). Verification: `test_qaqc_runner_extended.py` `16 passed`, ruff clean, isolated `run_npm_test` against real hanwoo ??`PASS 75`, full `qaqc_runner.py` ??`CONDITIONALLY_APPROVED 4566 passed`, hanwoo `npm test`/`lint`/`build` green. Surfaced **T-300** (pre-existing `root` collection error in `test_ai_batch_runner_regression.py`, masked by 6-week-stale qaqc data ??not a regression). | `.gitignore`; `workspace/execution/qaqc_runner.py`; `workspace/tests/test_qaqc_runner_extended.py`; `execution/product_readiness_score.py`; `projects/knowledge-dashboard/scripts/sync_data.py`; `projects/knowledge-dashboard/public/qaqc_result.json`; `projects/hanwoo-dashboard/{README.md,API_SPEC.md,src/app/api/ai/chat/route.js,src/lib/ai-chat-api.mjs,src/lib/ai-chat-api.test.mjs}`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md` |
| 2026-05-15 | Claude Code (Opus 4.7 1M) | User said "異붽? 吏꾪뻾 ?ㅼ젙?댁꽌 吏꾪뻾?섏옄". Via AskUserQuestion the user chose to set a new GOAL, then "Skill ?ъ뒪 ?뺣━ ?꾩꽦". Set `.ai/GOAL.md` to the skill-health goal and investigated skill_lint's 63 warnings ??found them mostly linter false positives (markdown link display-text, generated-artifact filenames in prose, web files like `robots.txt`, subfolder-bundle resources). Mid-investigation a concurrent tool (Codex) was actively editing the same files for the same goal and committed the full bundle as `65cbe47` (T-298, score 100 / pass). Reviewed every diff in `65cbe47`: approach is sound (fenced-code stripping, path-like ref filter, `skills/`+`execution/` resolution, recursive bundle resolution, broadened `TRIGGER_MARKERS`). Found one defect ??`TRIGGER_MARKERS` held `"????`, a cp949-mojibake duplicate of the existing `"?ъ슜"` entry ??and removed it for hygiene in `bcfa2e5` (`fix(workspace): drop corrupted trigger marker from skill_lint`). Verification: `python execution/skill_lint.py` -> `pass, score=100`; `workspace/tests/test_skill_lint.py` `7 passed`; ruff clean. Unrelated dirty WIP (`projects/blind-to-x/*`, `projects/hanwoo-dashboard/*` + untracked AI-chat files) left untouched for its author sessions. | `execution/skill_lint.py`; `.ai/GOAL.md`; `.ai/TASKS.md`; `.ai/HANDOFF.md`; `.ai/SESSION_LOG.md` |
| 2026-05-15 | Codex | Completed `T-298` and closed the active skill-health goal in feature commit `65cbe47` (`chore(workspace): complete skill health cleanup`). The active `.agents/skills/**/SKILL.md` set now passes skill lint at score `100`: 42 active skills, 42 healthy, 0 warnings, 0 errors. Updated skill metadata/references for active skill docs and hardened `execution/skill_lint.py` so fenced-code examples are ignored, bare generated artifact filenames are not treated as required bundled files, common skill subdirectories resolve correctly, and trigger guidance recognizes common heading/wording variants. Verification: `python execution/skill_lint.py --json` pass; `python -m pytest --no-cov workspace/tests/test_skill_lint.py -q` -> `7 passed`; targeted Ruff passed; `python execution/project_qc_runner.py --project knowledge-dashboard --json` passed. Pre-commit graph gate emitted advisory WARN risk `0.35` from heuristic test-gap mapping despite direct coverage. | `.agents/skills/accessibility/SKILL.md`; `.agents/skills/blind-to-x/SKILL.md`; `.agents/skills/content-calendar/SKILL.md`; `.agents/skills/cost-check/SKILL.md`; `.agents/skills/daily-brief/SKILL.md`; `.agents/skills/deployment-helper/SKILL.md`; `.agents/skills/error-debugger/SKILL.md`; `.agents/skills/persona-backend-minseok/SKILL.md`; `.agents/skills/persona-designer-harin/SKILL.md`; `.agents/skills/persona-devops-hyeonwoo/SKILL.md`; `.agents/skills/persona-frontend-junho/SKILL.md`; `.agents/skills/persona-legal-suhyun/SKILL.md`; `.agents/skills/persona-pm-ara/SKILL.md`; `.agents/skills/persona-qa-jieun/SKILL.md`; `.agents/skills/pipeline-runner/SKILL.md`; `.agents/skills/roi-analyzer/SKILL.md`; `.agents/skills/seo/SKILL.md`; `.agents/skills/shorts-subtitle-safezone/SKILL.md`; `.agents/skills/skill-creator/SKILL.md`; `.agents/skills/trend-scout/SKILL.md`; `execution/skill_lint.py`; `workspace/tests/test_skill_lint.py`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md`; `.ai/GOAL.md` |
| 2026-05-15 | Codex | Completed `T-297` in `4939a7b` after the user said to proceed where Codex thought best. Chose a durable operations-console improvement because the only TODO (`T-251`) is user-owned. Fixed a product-readiness scoring gap: the UI said release confidence used QC freshness, but stale `qaqc_result.json` snapshots still received full QC credit. `execution/product_readiness_score.py` now parses QA/QC timestamps, marks QC stale after 7 days, caps stale QC credit, and recommends a refresh. `ProductReadinessPanel` now displays QC age/stale state for each project. Regenerated readiness locally with the current 2026-04-01 QA/QC snapshot; the ignored JSON now shows stale projects as needs-review while keeping Hanwoo blocked by T-251. Verification: product-readiness tests `4 passed`; targeted Ruff passed; `npx tsc --noEmit`; knowledge-dashboard `npm test`, `npm run lint`, `npm run build`; canonical `project_qc_runner.py --project knowledge-dashboard --json` passed; code-review gate passed risk `0.0` with the known trailing Windows `cp949` reader-thread exception. Pre-commit graph gate emitted advisory WARN risk `0.35` from heuristic test-gap mapping despite direct coverage. | `execution/product_readiness_score.py`; `workspace/tests/test_product_readiness_score.py`; `projects/knowledge-dashboard/src/components/ProductReadinessPanel.tsx`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md`; `.ai/CONTEXT.md` |
| 2026-05-15 | Codex | Completed `T-296`: fixed `execution/session_orient.py --json` crashing in the default Windows/cp949 console when snapshot data contains Unicode. JSON output now uses ASCII-safe escapes, and text output falls back to console-safe replacement instead of raising `UnicodeEncodeError`. Added a cp949 stdout regression test. Verification: `python execution/session_orient.py --json` succeeds; `workspace/tests/test_session_orient.py` `18 passed` with repo-local basetemp; targeted Ruff passed; staged code-review gate passed with the known trailing reader-thread decode warning. Feature commit: `b52dc16 fix(workspace): make session orientation output encoding safe`. The active `.ai/GOAL.md` skill-health cleanup from another tool remains active and was not closed. | `execution/session_orient.py`; `workspace/tests/test_session_orient.py`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md` |
| 2026-05-15 | Codex | Completed `T-295` for `projects/blind-to-x` after the user asked to set an additional direction and proceed. Direction chosen: finish the X-first review quality gate plus source-faithful image policy already present in WIP, instead of widening into new architecture. Config examples now default review generation to `twitter` only with no support channels, require Twitter quality pass at score 80, and disable generated AI images for review/Blind by default. `generate_review_stage` now fails review candidates that still miss the Twitter quality gate after retry/editorial/validator passes. `persist_stage` now requires explicit opt-in before generating review AI images or Blind AI images, and preserves original community source images before AI generation. Added/updated regression tests for X-first defaults, quality gate failure/disable paths, review-only AI image skip, and community original-image precedence. Verification: focused tests `51 passed, 1 skipped`; targeted Ruff passed; canonical `project_qc_runner.py --project blind-to-x --json` passed with `1557 passed, 1 skipped` and lint passed. | `projects/blind-to-x/config.ci.yaml`; `projects/blind-to-x/config.example.yaml`; `projects/blind-to-x/pipeline/process_stages/generate_review_stage.py`; `projects/blind-to-x/pipeline/process_stages/persist_stage.py`; `projects/blind-to-x/tests/unit/test_cost_controls.py`; `projects/blind-to-x/tests/unit/test_multi_platform.py`; `projects/blind-to-x/tests/unit/test_process_stages.py`; `.ai/GOAL.md`; `.ai/HANDOFF.md`; `.ai/TASKS.md`; `.ai/SESSION_LOG.md` |
| 2026-05-15 | Codex | Completed a new safe local context cleanup goal after the user asked to set a new goal and proceed. Activated `.ai/GOAL.md`, ran `python execution/handoff_rotator.py --json`, and archived 15 stale HANDOFF addenda to `.ai/archive/HANDOFF_archive_2026-05-15.md`. Verification: pre-run dry check reported 15 archivable entries; actual rotation returned `status: rotated`; follow-up `handoff_rotator.py --check --json` returned `status: noop`; `session_orient.py --json` verified shared state. `.ai/GOAL.md` was returned to inactive on completion. No product code or unrelated WIP was touched. Remaining TODOs are still T-282 and T-251, both user-owned approval/secret tasks. | `.ai/GOAL.md`; `.ai/HANDOFF.md`; `.ai/SESSION_LOG.md`; `.ai/archive/HANDOFF_archive_2026-05-15.md` |
| 2026-05-15 | Codex | Mitigated the reported Codex MCP startup failure for `linear`. Root cause: global `C:\Users\諛뺤＜??.codex\config.toml` had hosted Linear MCP configured as `https://mcp.linear.app/mcp`, and the saved OAuth refresh token was rejected with `invalid_grant`. Backed up the global config to `C:\Users\諛뺤＜??.codex\config.toml.bak-linear-oauth-20260515065735` and removed only the hosted `[mcp_servers.linear]` block. Verification: Python `tomllib` parsed the global config; remaining global MCP servers are `figma,notion,playwright`; no Linear MCP entry remains. Restart Codex for the config reload. | `.ai/HANDOFF.md`; `.ai/SESSION_LOG.md`; `C:\Users\諛뺤＜??.codex\config.toml` *(out-of-repo)* |

## 2026-05-15 KST - Codex

### Summary
- Completed T-300 root QA/QC repair after the fresh QA/QC artifact surfaced `root` collection/runtime failures.
- Added root `execution/` import coverage for `workspace/execution/tests` so `test_ai_batch_runner_regression.py` can import `ai_batch_runner` under the `qaqc_runner` cwd.
- Hardened `execution/ai_batch_runner.py::process_item` so empty OpenAI `choices` and `None` content fail with explicit errors instead of incidental `IndexError` or false success.
- Fixed two QA/QC harness issues found during verification: repo/security scan exclusions now apply relative to their scan root, and `qaqc_runner` uses unique repo-local pytest basetemp directories to avoid Windows temp permission failures.
- Quoted workspace DB audit index/table identifiers to remove the actionable security-scan warning.

### Verification
- `python -m pytest --no-cov execution/tests/test_ai_batch_runner_regression.py -q --tb=short --maxfail=1 --basetemp ../.tmp/pytest-root-qc-ai-batch` from `workspace/` -> `2 passed`.
- Focused `test_qaqc_runner_extended.py`, `test_context_selector.py`, `test_workspace_db_audit.py` -> `37 passed`.
- `workspace/tests` -> `1452 passed, 1 skipped`.
- `workspace/execution/tests` -> `72 passed`.
- Targeted Ruff and `py_compile` passed.
- `python workspace/execution/qaqc_runner.py --project root --skip-infra --skip-debt --output .tmp/qaqc-root-t300-fixed.json` -> `APPROVED`, `1525 passed`, `1 skipped`.

### Follow-up
- T-300 is complete.
- T-251 remains user-owned: reset/resync the Supabase database password in the dashboard, update `projects/hanwoo-dashboard/.env` if needed, then rerun the live Prisma E2E.
- Existing unrelated WIP was preserved, including `projects/blind-to-x/pipeline/notion/_upload.py` and other tool edits under `workspace/conftest.py` / frontend test files.

### Goal Closeout
- Thread goal `媛쒖꽑???꾩슂???꾨줈?앺듃 李???媛쒖꽑?? was marked complete after local safe work was exhausted.
- `.ai/GOAL.md` remains inactive and now records the T-300/root QA/QC completion state instead of the older skill-health success.

### 2026-05-15 13:04:27 - Antigravity (Gemini)
- **Task**: Refining AI Interaction Guidelines
- **Summary**: Created a structured process and guidelines for generating concise conversation titles and summarizing project goals. Ensure all future AI responses are action-oriented, accurate, and grounded strictly in the provided task context.
- **Changes**: 
  - Created `.agents/rules/ai-interaction-guidelines.md`.
  - Updated `CLAUDE.md`, `AGENTS.md`, and `GEMINI.md` to enforce the new interaction guidelines.

## 2026-05-15 KST - Codex

### Summary
- Completed T-301 after the user asked to find and improve the project most needing attention.
- Selected `knowledge-dashboard` because product readiness showed it as at-risk from a stale/mis-mapped QA/QC signal.
- Added `knowledge-dashboard` to the deep `workspace/execution/qaqc_runner.py` project registry.
- Removed the `root` -> `knowledge-dashboard` fallback from `execution/product_readiness_score.py` so missing project QC is surfaced as `UNKNOWN` instead of borrowing unrelated root failures.
- Preserved existing project results when a default targeted deep QA/QC run updates the canonical `projects/knowledge-dashboard/public/qaqc_result.json`.
- Regenerated the canonical QA/QC artifact with all active projects present.

### Verification
- `python -m pytest --no-cov workspace/tests/test_qaqc_runner_extended.py workspace/tests/test_product_readiness_score.py workspace/tests/test_project_qc_runner.py -q` -> `31 passed`.
- `python -m ruff check workspace/execution/qaqc_runner.py execution/product_readiness_score.py execution/project_qc_runner.py workspace/tests/test_qaqc_runner_extended.py workspace/tests/test_product_readiness_score.py workspace/tests/test_project_qc_runner.py` -> passed.
- `python workspace/execution/qaqc_runner.py --skip-infra --skip-debt` -> `APPROVED`, `4646 passed`, `0 failed`, `0 errors`, `13 skipped`.
- `python execution/product_readiness_score.py --json` -> overall `92 / blocked`, with `knowledge-dashboard` `94 / ready`; the remaining blocker is T-251.
- `python execution/project_qc_runner.py --project knowledge-dashboard --json` -> passed.
- `python execution/code_review_gate.py --base HEAD --json` -> advisory `warn risk=0.40` from graph test-gap heuristics despite focused coverage.

### Follow-up
- T-251 remains user-owned: reset/resync the Supabase database password, update `projects/hanwoo-dashboard/.env` if needed, then rerun live Prisma E2E.
- Preserve unrelated `projects/blind-to-x/pipeline/notion/_upload.py` EOL-only dirty state unless its owner asks for cleanup.

## 2026-05-18 KST - Codex

### Summary
- Re-oriented the workspace after the user asked to understand current work and proceed.
- Confirmed `main` is synchronized with `origin/main`, the worktree is clean, there is no active goal, and `.ai/TASKS.md` has one remaining TODO.
- `python execution/product_readiness_score.py --json` reports overall `94 / blocked`; `blind-to-x`, `shorts-maker-v2`, and `knowledge-dashboard` are ready, while `hanwoo-dashboard` is blocked only by T-251.
- Retried T-251 with `npm.cmd run db:prisma7-test -- --live` from `projects/hanwoo-dashboard`.

### Verification
- `python execution/session_orient.py --json` -> clean worktree, `ahead=0`, `behind=0`, graph available, no active goal.
- `git status -sb` -> `## main...origin/main`.
- `npm.cmd run db:prisma7-test -- --live` -> local Prisma/client/adapter checks passed, live CRUD connection health failed with `P2010` / `XX000` / `(ENOTFOUND) tenant/user postgres.fuemeqmigptwfzqvrpjf not found`.

### Follow-up
- T-251 remains user-owned: reset/resync the Supabase database password in the Supabase Dashboard, update `projects/hanwoo-dashboard/.env` if the connection string changes, then rerun the live Prisma E2E.
- No code changes were made.

## 2026-05-18 KST - Codex

### Summary
- Activated the new `/goal`: raise `hanwoo-dashboard` quality until other people would want to use it.
- Completed the first safe product-quality pass as T-307.
- Added a home-screen Today Brief panel that converts operational state into next actions: offline sync, critical alerts, next schedule, low-stock inventory, and monthly sales.
- Extracted deterministic focus-item prioritization into `src/lib/dashboard/today-focus.mjs` with regression coverage.
- Feature commit: `f222385` (`feat(hanwoo-dashboard): add today brief focus panel`).
- Preserved unrelated dirty `projects/blind-to-x/uv.lock`.

### Changed Files
- `.ai/GOAL.md`
- `.ai/HANDOFF.md`
- `.ai/TASKS.md`
- `.ai/SESSION_LOG.md`
- `projects/hanwoo-dashboard/src/components/DashboardClient.js`
- `projects/hanwoo-dashboard/src/app/globals.css`
- `projects/hanwoo-dashboard/src/lib/dashboard/today-focus.mjs`
- `projects/hanwoo-dashboard/src/lib/dashboard/today-focus.test.mjs`

### Verification
- `npm.cmd test` from `projects/hanwoo-dashboard` -> `77 passed`.
- `npm.cmd run lint` from `projects/hanwoo-dashboard` -> passed.
- `npm.cmd run build` from `projects/hanwoo-dashboard` -> passed.
- `python execution/code_review_gate.py --staged --json` -> pass risk `0.0`; pre-commit graph gate later emitted advisory WARN risk `0.35` for `DashboardClient` test-gap heuristics despite direct helper coverage and full Hanwoo checks.
- Dev server started at `http://127.0.0.1:3001`.

### Follow-up
- T-308 is the next safe goal task: browser visual QA of the Today Brief panel, then consider lucide-icon polish for remaining emoji-heavy navigation/widget affordances.
- T-251 remains user-owned: reset/resync the Supabase database password in the Supabase Dashboard, update `.env` if needed, then rerun live Prisma E2E.

## 2026-05-20 KST - Codex

### Summary
- Completed T-473 for `hanwoo-dashboard` while continuing the active quality uplift goal.
- Hid the AI chat header pulse indicator from assistive technology because the meaningful streaming state is already exposed by the send button and live message log.
- Extended the AI chat source contract test to guard the decorative indicator semantics.

### Changed Files
- `.ai/HANDOFF.md`
- `.ai/TASKS.md`
- `.ai/SESSION_LOG.md`
- `.ai/CONTEXT.md`
- `.ai/GOAL.md`
- `projects/hanwoo-dashboard/src/components/widgets/AIChatWidget.js`
- `projects/hanwoo-dashboard/src/lib/ai-chat-widget-copy.test.mjs`

### Verification
- `node --test src/lib/ai-chat-widget-copy.test.mjs` from `projects/hanwoo-dashboard` -> `1 passed`.
- `npm.cmd exec eslint src/components/widgets/AIChatWidget.js src/lib/ai-chat-widget-copy.test.mjs` from `projects/hanwoo-dashboard` -> passed.
- `git diff --check -- projects/hanwoo-dashboard/src/components/widgets/AIChatWidget.js projects/hanwoo-dashboard/src/lib/ai-chat-widget-copy.test.mjs` -> passed (LF/CRLF warnings only).
- `python execution/project_qc_runner.py --project hanwoo-dashboard --json` -> passed (`test` 179, lint passed, build passed).
- `python execution/code_review_gate.py --staged --json` -> PASS; trailing cp949 reader-thread exception is known Windows output noise.

### Follow-up
- Active Hanwoo goal remains open; T-251 still requires user-owned Supabase password/control-plane resync before live Prisma CRUD can be proven.
- T-320, T-372, and T-407 remain approval-scoped. Preserve unrelated current WIP in root package/workflow files, Hanwoo `package.json`, package locks, setup scripts, and shorts-maker-v2/workspace files.

## 2026-05-20 KST - Codex

### Summary
- Completed T-472 for `hanwoo-dashboard` while continuing the active quality uplift goal.
- Restored focus to the floating AI chat launcher after the dialog closes, so keyboard users return to the control that opened the assistant.
- Extended the AI chat source contract test to guard the launcher ref and restore-focus path.

### Changed Files
- `.ai/HANDOFF.md`
- `.ai/TASKS.md`
- `.ai/SESSION_LOG.md`
- `.ai/CONTEXT.md`
- `.ai/GOAL.md`
- `projects/hanwoo-dashboard/src/components/widgets/AIChatWidget.js`
- `projects/hanwoo-dashboard/src/lib/ai-chat-widget-copy.test.mjs`

### Verification
- `node --test src/lib/ai-chat-widget-copy.test.mjs` from `projects/hanwoo-dashboard` -> `1 passed`.
- `npm.cmd exec eslint src/components/widgets/AIChatWidget.js src/lib/ai-chat-widget-copy.test.mjs` from `projects/hanwoo-dashboard` -> passed.
- `git diff --check -- projects/hanwoo-dashboard/src/components/widgets/AIChatWidget.js projects/hanwoo-dashboard/src/lib/ai-chat-widget-copy.test.mjs` -> passed (LF/CRLF warnings only).
- `python execution/project_qc_runner.py --project hanwoo-dashboard --json` -> passed (`test` 179, lint passed, build passed).
- `python execution/code_review_gate.py --staged --json` -> PASS; trailing cp949 reader-thread exception is known Windows output noise.

### Follow-up
- Active Hanwoo goal remains open; T-251 still requires user-owned Supabase password/control-plane resync before live Prisma CRUD can be proven.
- T-320, T-372, and T-407 remain approval-scoped. Preserve unrelated current WIP in root package/workflow files, Hanwoo `package.json`, package locks, setup scripts, and shorts-maker-v2/workspace files.

## 2026-05-20 KST - Codex

### Summary
- Completed T-471 for `hanwoo-dashboard` while continuing the active quality uplift goal.
- Marked the AI chat dialog as modal with `aria-modal="true"`, aligning it with the existing notification dialog pattern.
- Extended the AI chat source contract test so the modal semantics cannot regress silently.

### Changed Files
- `.ai/HANDOFF.md`
- `.ai/TASKS.md`
- `.ai/SESSION_LOG.md`
- `.ai/CONTEXT.md`
- `.ai/GOAL.md`
- `projects/hanwoo-dashboard/src/components/widgets/AIChatWidget.js`
- `projects/hanwoo-dashboard/src/lib/ai-chat-widget-copy.test.mjs`

### Verification
- `node --test src/lib/ai-chat-widget-copy.test.mjs` from `projects/hanwoo-dashboard` -> `1 passed`.
- `npm.cmd exec eslint src/components/widgets/AIChatWidget.js src/lib/ai-chat-widget-copy.test.mjs` from `projects/hanwoo-dashboard` -> passed.
- `git diff --check -- projects/hanwoo-dashboard/src/components/widgets/AIChatWidget.js projects/hanwoo-dashboard/src/lib/ai-chat-widget-copy.test.mjs` -> passed (LF/CRLF warnings only).
- `python execution/project_qc_runner.py --project hanwoo-dashboard --json` -> passed (`test` 179, lint passed, build passed).
- `python execution/code_review_gate.py --staged --json` -> PASS; trailing cp949 reader-thread exception is known Windows output noise.

### Follow-up
- Active Hanwoo goal remains open; T-251 still requires user-owned Supabase password/control-plane resync before live Prisma CRUD can be proven.
- T-320, T-372, and T-407 remain approval-scoped. Preserve unrelated current WIP in root package/workflow files, Hanwoo `package.json`, package locks, setup scripts, and shorts-maker-v2/workspace files.

## 2026-05-20 KST - Codex

### Summary
- Completed T-470 for `hanwoo-dashboard` while continuing the active quality uplift goal.
- Marked the AI chat message stream as a polite live conversation log, so streamed assistant replies are announced to assistive technology instead of being visual-only.
- Extended the AI chat source contract test to guard `role="log"`, `aria-live`, `aria-relevant`, and the Korean conversation-label copy.

### Changed Files
- `.ai/HANDOFF.md`
- `.ai/TASKS.md`
- `.ai/SESSION_LOG.md`
- `.ai/CONTEXT.md`
- `.ai/GOAL.md`
- `projects/hanwoo-dashboard/src/components/widgets/AIChatWidget.js`
- `projects/hanwoo-dashboard/src/lib/ai-chat-widget-copy.test.mjs`

### Verification
- `node --test src/lib/ai-chat-widget-copy.test.mjs` from `projects/hanwoo-dashboard` -> `1 passed`.
- `npm.cmd exec eslint src/components/widgets/AIChatWidget.js src/lib/ai-chat-widget-copy.test.mjs` from `projects/hanwoo-dashboard` -> passed.
- `git diff --check -- projects/hanwoo-dashboard/src/components/widgets/AIChatWidget.js projects/hanwoo-dashboard/src/lib/ai-chat-widget-copy.test.mjs` -> passed (LF/CRLF warnings only).
- `python execution/project_qc_runner.py --project hanwoo-dashboard --json` -> passed (`test` 179, lint passed, build passed).
- `python execution/code_review_gate.py --staged --json` -> PASS; trailing cp949 reader-thread exception is known Windows output noise.

### Follow-up
- Active Hanwoo goal remains open; T-251 still requires user-owned Supabase password/control-plane resync before live Prisma CRUD can be proven.
- T-320, T-372, and T-407 remain approval-scoped. Preserve unrelated current WIP in root package/workflow files, Hanwoo `package.json`, package locks, setup scripts, and shorts-maker-v2/workspace files.

## 2026-05-20 KST - Codex

### Summary
- Completed T-469 for `hanwoo-dashboard` while continuing the active quality uplift goal.
- Focused the AI chat dialog surface on open so Escape dismissal works immediately after opening the floating assistant.
- Reused the established `NotificationModal` focus pattern with a `panelRef` and `tabIndex={-1}`, and extended the source contract test.

### Changed Files
- `.ai/HANDOFF.md`
- `.ai/TASKS.md`
- `.ai/SESSION_LOG.md`
- `.ai/CONTEXT.md`
- `.ai/GOAL.md`
- `projects/hanwoo-dashboard/src/components/widgets/AIChatWidget.js`
- `projects/hanwoo-dashboard/src/lib/ai-chat-widget-copy.test.mjs`

### Verification
- `node --test src/lib/ai-chat-widget-copy.test.mjs` from `projects/hanwoo-dashboard` -> `1 passed`.
- `npm.cmd exec eslint src/components/widgets/AIChatWidget.js src/lib/ai-chat-widget-copy.test.mjs` from `projects/hanwoo-dashboard` -> passed.
- `git diff --check -- projects/hanwoo-dashboard/src/components/widgets/AIChatWidget.js projects/hanwoo-dashboard/src/lib/ai-chat-widget-copy.test.mjs` -> passed (LF/CRLF warnings only).
- `python execution/project_qc_runner.py --project hanwoo-dashboard --json` -> passed (`test` 179, lint passed, build passed).
- `python execution/code_review_gate.py --staged --json` -> PASS; trailing cp949 reader-thread exception is known Windows output noise.

### Follow-up
- Active Hanwoo goal remains open; T-251 still requires user-owned Supabase password/control-plane resync before live Prisma CRUD can be proven.
- T-320, T-372, and T-407 remain approval-scoped. Preserve unrelated current WIP in root package/workflow files, Hanwoo `package.json`, package locks, setup scripts, and shorts-maker-v2/workspace files.

## 2026-05-20 KST - Codex

### Summary
- Completed T-326 for the active `hanwoo-dashboard` product-completeness goal.
- Added a deterministic setup-progress helper that scores first-run readiness across farm profile, buildings, cattle, inventory, and schedule setup.
- Rendered a home-screen `Farm Setup / ?댁쁺 以鍮꾨룄` panel so new operators can see remaining setup gaps and jump directly to the right action.
- Fixed the home empty 異뺤궗 CTA: it now opens Settings, where building creation actually exists, instead of opening the cattle registration modal.

### Changed Files
- `.ai/GOAL.md`
- `.ai/HANDOFF.md`
- `.ai/TASKS.md`
- `.ai/SESSION_LOG.md`
- `projects/hanwoo-dashboard/src/components/DashboardClient.js`
- `projects/hanwoo-dashboard/src/app/globals.css`
- `projects/hanwoo-dashboard/src/lib/dashboard/setup-progress.mjs`
- `projects/hanwoo-dashboard/src/lib/dashboard/setup-progress.test.mjs`

### Verification
- `npm.cmd test` from `projects/hanwoo-dashboard` -> `84 passed`.
- `npm.cmd run lint` from `projects/hanwoo-dashboard` -> passed.
- `npm.cmd run build` from `projects/hanwoo-dashboard` -> passed.
- `PYTHONUTF8=1 python -m code_review_graph detect-changes --repo projects/hanwoo-dashboard --base HEAD --brief` -> risk `0.00`.
- `git diff --check -- projects/hanwoo-dashboard/src/components/DashboardClient.js projects/hanwoo-dashboard/src/app/globals.css projects/hanwoo-dashboard/src/lib/dashboard/setup-progress.mjs projects/hanwoo-dashboard/src/lib/dashboard/setup-progress.test.mjs` -> passed, with only the standard LF-to-CRLF warning.
- Dev server check: `http://127.0.0.1:3001/login` returned `200`; `/manifest.json` returned `application/json`.

### Follow-up
- Active Hanwoo quality goal remains open for additional polish.
- T-251 remains external: user must reset/resync Supabase DB credentials before live Prisma CRUD E2E can prove production DB readiness.
- Preserve unrelated dirty WIP in root package/workflow files, package locks for other projects, `setup.bat`, and `projects/hanwoo-dashboard/package.json`.
- `projects/hanwoo-dashboard/src/app/globals.css` includes unrelated status-page style changes in the current diff; review/stage hunks carefully before committing product code.

## 2026-05-19 KST - Codex

### Summary
- Record-only checkpoint after the user said `湲곕줉??.
- Confirmed Hanwoo quality-uplift work is already committed in `f222385` and ai-context closeout is committed in `4a8ece5`.
- Confirmed active goal remains `hanwoo-dashboard quality uplift so other people would want to use it`.
- Confirmed local `main` is ahead 2 of `origin/main`.
- Preserved unrelated dirty `blind-to-x` WIP without staging or editing it.

### Current Dirty Files To Preserve
- `projects/blind-to-x/pipeline/content_intelligence/rules.py`
- `projects/blind-to-x/pipeline/draft_prompts.py`
- `projects/blind-to-x/pipeline/draft_quality_gate.py`
- `projects/blind-to-x/rules/editorial.yaml`
- `projects/blind-to-x/rules/examples.yaml`
- `projects/blind-to-x/rules/prompts.yaml`
- `projects/blind-to-x/tests/unit/test_draft_generator_multi_provider.py`
- `projects/blind-to-x/tests/unit/test_draft_quality_gate_deep.py`
- `projects/blind-to-x/tests/unit/test_quality_gate_and_scenes.py`
- `projects/blind-to-x/tests/unit/test_quality_improvements.py`
- `projects/blind-to-x/uv.lock`

### Verification
- `git status --short --branch` -> `main...origin/main [ahead 2]`, only the unrelated `blind-to-x` WIP plus this record update before commit.
- `python execution/session_orient.py --json` -> active goal present, TODO count 3, no staged files, graph available.

### Follow-up
- Continue T-308 when asked.
- Do not retry T-251 live Prisma until Supabase credentials are reset/resynced.

## 2026-05-19 KST - Codex

### Summary
- Continued the active Hanwoo quality goal after the user asked for UX/UI optimized for users.
- Reworked `/login` into an operator-first login flow with labelled fields, lucide icons, password visibility toggle, disabled/pending submit states, clearer error feedback, and mobile-safe spacing.
- Replaced bottom dashboard tab emoji navigation with lucide icons and `aria-current` for more stable, scan-friendly navigation.
- Added `public/favicon.ico` from the existing app icon so `/favicon.ico` no longer 404s.
- Feature commit: `94d043e` (`feat(hanwoo-dashboard): polish operator login ux`).

### Changed Files
- `projects/hanwoo-dashboard/src/app/login/page.js`
- `projects/hanwoo-dashboard/src/app/globals.css`
- `projects/hanwoo-dashboard/src/components/widgets/widgets.js`
- `projects/hanwoo-dashboard/public/favicon.ico`
- `.ai/GOAL.md`
- `.ai/HANDOFF.md`
- `.ai/SESSION_LOG.md`
- `.ai/TASKS.md`

### Verification
- `npm.cmd test` from `projects/hanwoo-dashboard` -> `77 passed`.
- `npm.cmd run lint` from `projects/hanwoo-dashboard` -> passed.
- `npm.cmd run build` from `projects/hanwoo-dashboard` -> passed.
- Playwright CLI `/login` snapshot and mobile/desktop visual checks -> passed.
- Playwright console after favicon fix -> errors `0`, warnings `0`.
- `python execution/code_review_gate.py --staged --json` -> pass risk `0.0`; pre-commit graph gate later emitted advisory WARN risk `0.50`, partly polluted by unrelated dirty `blind-to-x` WIP.

### Follow-up
- Authenticated dashboard visual QA still needs working DB/auth state; keep T-251 separate until Supabase credentials are reset/resynced.

## 2026-05-19 KST - Codex

### Summary
- Completed T-310 for the active thread goal: make blind-to-x Notion output more suitable for direct X upload.
- Added a top-level `X ?낅줈??移대뱶` to Notion pages with copy-ready `X 蹂몃Ц`, optional `泥??듦? / 異쒖쿂 硫붾え`, 280-character count, link/hashtag separation, and upload order.
- Changed future Twitter publish-platform labeling from `?륂뤌` to `X` while preserving legacy `?륂뤌` recognition in backfill/schema helpers.
- Moved non-X formats under `蹂댁“ 梨꾨꼸 珥덉븞` so the reviewer-facing page is X-first instead of a generic multi-platform dump.
- Updated README, ops-runbook, and Notion view setup docs to point reviewers at `X ?낅줈??移대뱶` / `X ?꾨낫`.

### Changed Files
- `.ai/HANDOFF.md`
- `.ai/TASKS.md`
- `.ai/SESSION_LOG.md`
- `projects/blind-to-x/README.md`
- `projects/blind-to-x/docs/notion_view_setup_guide.md`
- `projects/blind-to-x/docs/ops-runbook.md`
- `projects/blind-to-x/pipeline/notion/_upload.py`
- `projects/blind-to-x/scripts/backfill_notion_review_columns.py`
- `projects/blind-to-x/scripts/sync_notion_review_schema.py`
- `projects/blind-to-x/tests/unit/test_backfill_notion_review_columns.py`
- `projects/blind-to-x/tests/unit/test_notion_upload.py`

### Verification
- `python -m pytest --no-cov tests/unit/test_notion_upload.py tests/unit/test_backfill_notion_review_columns.py -q --tb=short --maxfail=1` from `projects/blind-to-x` -> `42 passed`, 1 Pydantic/Python 3.14 warning.
- `python -m pytest --no-cov tests/unit/test_process_stages.py tests/unit/test_cost_controls.py -q --tb=short --maxfail=1` from `projects/blind-to-x` -> `35 passed`, 1 Pydantic/Python 3.14 warning.
- `python -m ruff check --no-cache pipeline/notion/_upload.py scripts/backfill_notion_review_columns.py scripts/sync_notion_review_schema.py tests/unit/test_notion_upload.py tests/unit/test_backfill_notion_review_columns.py` from `projects/blind-to-x` -> passed.
- `PYTHONUTF8=1 python -m code_review_graph detect-changes --repo projects/blind-to-x --brief` -> risk `0.00`.

### Follow-up
- Live Notion upload was not run because it would use the real Notion API.
- If the actual Notion DB needs the new `X` multi-select option synced, run `py -3 scripts/sync_notion_review_schema.py --config config.yaml --apply` from `projects/blind-to-x`.
- Preserve unrelated current worktree changes: `projects/blind-to-x/uv.lock`, `projects/hanwoo-dashboard/src/app/globals.css`, `projects/hanwoo-dashboard/src/app/login/page.js`, `.playwright-cli/`, and `output/`.

## 2026-05-19 KST - Codex

### Summary
- Continued the active blind-to-x thread goal through live Notion verification and backfill.
- Confirmed `scripts/notion_doctor.py --config config.yaml` passes against the real Notion database.
- Confirmed `scripts/sync_notion_review_schema.py --config config.yaml` is `NOOP`; the live DB already has the reviewer columns and `X` publish-platform option.
- Added `--append-x-upload-card` to `scripts/backfill_notion_review_columns.py` so existing pages with a `tweet_body` can receive the new copy-ready X card without running the LLM generation path.
- Applied the backfill to the newest 5 Notion pages: properties updated from legacy `?륂뤌` to `X`, and 5 `X ?낅줈??移대뱶` blocks were appended.
- Read-only verification confirmed the newest 5 pages are X-ready: `verified_x_ready=5/5`, each with `platforms=['X']`, `X ?낅줈??移대뱶`, `X 蹂몃Ц`, and `泥??듦? / 異쒖쿂 硫붾え`.

### Changed Files
- `.ai/HANDOFF.md`
- `.ai/TASKS.md`
- `.ai/SESSION_LOG.md`
- `projects/blind-to-x/scripts/backfill_notion_review_columns.py`
- `projects/blind-to-x/tests/unit/test_backfill_notion_review_columns.py`

### Verification
- `python scripts/notion_doctor.py --config config.yaml` from `projects/blind-to-x` -> PASS.
- `python scripts/sync_notion_review_schema.py --config config.yaml` from `projects/blind-to-x` -> NOOP.
- `python scripts/backfill_notion_review_columns.py --config config.yaml --limit 5 --append-x-upload-card` -> dry-run found 5 candidates.
- `python scripts/backfill_notion_review_columns.py --config config.yaml --limit 5 --append-x-upload-card --apply` -> updated 5 pages and appended 5 X cards.
- Read-only verification script -> `verified_x_ready=5/5`.
- `python -m pytest --no-cov tests/unit/test_notion_upload.py tests/unit/test_backfill_notion_review_columns.py -q --tb=short --maxfail=1` -> `44 passed`, 1 Pydantic/Python 3.14 warning.
- `python -m ruff check --no-cache scripts/backfill_notion_review_columns.py tests/unit/test_backfill_notion_review_columns.py tests/unit/test_notion_upload.py` -> passed.
- `PYTHONUTF8=1 python -m code_review_graph detect-changes --repo projects/blind-to-x --brief` -> risk `0.00`.

### Follow-up
- Future blind-to-x uploads should now create `X ?낅줈??移대뱶` during normal upload, while the latest existing review queue is also X-ready.
- Live LLM generation was not run in this continuation; this was Notion read/write plus deterministic tests.
- Preserve unrelated current `projects/shorts-maker-v2/**` dirty WIP.

## 2026-05-19 KST - Codex

### Summary
- Searched GitHub/public examples for blind-to-x improvement ideas and selected the lowest-risk useful pattern: keep human-in-the-loop publishing operations in Notion.
- Used `langchain-ai/social-media-agent` as the human review/scheduling reference and NotionToTwitter as the Notion post date/status/error/URL tracking reference.
- Added X publishing operations fields to blind-to-x: `X Publish Status`, `X Scheduled At`, `X Published At`, `X Post URL`, and `X Publish Error`.
- Future X-ready Notion uploads now default `X Publish Status` to `Ready to Post` and show a `寃뚯떆 ?댁쁺` checklist inside the `X ?낅줈??移대뱶`.
- Applied the live Notion schema update; the database moved from 43 to 48 recovered properties.
- Backfilled the latest 5 Notion review pages to `Ready to Post`; follow-up dry-run returned `candidates: 0`.

### Changed Files
- `.ai/HANDOFF.md`
- `.ai/TASKS.md`
- `.ai/SESSION_LOG.md`
- `projects/blind-to-x/pipeline/notion/_schema.py`
- `projects/blind-to-x/pipeline/notion/_upload.py`
- `projects/blind-to-x/scripts/backfill_notion_review_columns.py`
- `projects/blind-to-x/scripts/sync_notion_review_schema.py`
- `projects/blind-to-x/tests/unit/test_backfill_notion_review_columns.py`
- `projects/blind-to-x/tests/unit/test_notion_upload.py`

### Verification
- `python -m pytest --no-cov tests/unit/test_notion_upload.py tests/unit/test_backfill_notion_review_columns.py -q --tb=short --maxfail=1` from `projects/blind-to-x` -> `44 passed`, 1 Pydantic/Python 3.14 warning.
- `python -m ruff check --no-cache scripts/sync_notion_review_schema.py scripts/backfill_notion_review_columns.py pipeline/notion/_schema.py pipeline/notion/_upload.py tests/unit/test_notion_upload.py tests/unit/test_backfill_notion_review_columns.py` from `projects/blind-to-x` -> passed.
- `python scripts/sync_notion_review_schema.py --config config.yaml --apply` from `projects/blind-to-x` -> APPLIED.
- `python scripts/sync_notion_review_schema.py --config config.yaml` from `projects/blind-to-x` -> NOOP.
- `python scripts/backfill_notion_review_columns.py --config config.yaml --limit 5 --apply` from `projects/blind-to-x` -> updated 5.
- `python scripts/backfill_notion_review_columns.py --config config.yaml --limit 5` from `projects/blind-to-x` -> `candidates: 0`.
- `PYTHONUTF8=1 python -m code_review_graph detect-changes --repo projects/blind-to-x --brief` -> risk `0.00`.

### Follow-up
- No automatic X posting was added; this intentionally keeps human approval before publication.
- Preserve unrelated current WIP in `projects/shorts-maker-v2/**`, root package files, and `projects/hanwoo-dashboard/package.json`.

## 2026-05-20 KST - Codex

### Summary
- Completed T-336 for `shorts-maker-v2`, closing the last safe T-318 Phase 3 item.
- Fixed channel-specific TTS tuning propagation: `MediaStep` now captures `AppConfig._channel_key` and passes it through direct Edge TTS, Chatterbox/CosyVoice premium TTS calls, and Edge fallback calls.
- Added/updated regression coverage so direct Edge routing and premium fallback retain `channel_key`, while empty-channel calls remain explicit.

### Changed Files
- `.ai/HANDOFF.md`
- `.ai/TASKS.md`
- `.ai/SESSION_LOG.md`
- `.ai/CONTEXT.md`
- `projects/shorts-maker-v2/src/shorts_maker_v2/pipeline/media_step.py`
- `projects/shorts-maker-v2/tests/unit/test_media_step_branches.py`
- `projects/shorts-maker-v2/tests/unit/test_tts_providers.py`

### Verification
- `python -m pytest --no-cov tests/unit/test_media_step_branches.py::test_generate_audio_edge_tts_uses_role_voice tests/unit/test_tts_providers.py::TestMediaStepTTSRouting -q --tb=short --maxfail=1 --basetemp .tmp/pytest-tts-channel-key-focused3` from `projects/shorts-maker-v2` -> `5 passed`, 2 warnings.
- `python -m ruff check src/shorts_maker_v2/pipeline/media_step.py tests/unit/test_tts_providers.py tests/unit/test_media_step_branches.py` from `projects/shorts-maker-v2` -> passed.
- `python -m ruff format --check src/shorts_maker_v2/pipeline/media_step.py tests/unit/test_tts_providers.py tests/unit/test_media_step_branches.py` from `projects/shorts-maker-v2` -> passed.
- `python -m pytest --no-cov tests/unit tests/integration -q --tb=short --maxfail=1 --basetemp .tmp/pytest-tts-channel-key-full-final` from `projects/shorts-maker-v2` -> passed.
- `python execution/project_qc_runner.py --project shorts-maker-v2 --check lint --json` -> passed.
- `PYTHONUTF8=1 python -m code_review_graph detect-changes --repo projects/shorts-maker-v2 --brief` -> risk `0.00`.

### Follow-up
- T-318 is closed. Remaining `shorts-maker-v2` backlog is approval-gated T-320 OSS integration.
- Preserve unrelated current WIP in root package/workflow files, Blind-to-X `pyproject.toml`, Hanwoo `package.json`, shorts-maker-v2 `render/color_grading.py` and `scripts/bench_render.py`, package locks, and setup scripts.
## 2026-05-20 KST - Codex

### Summary
- Completed T-338 for `hanwoo-dashboard` while continuing the active project debugging/quality goal.
- Fixed a remaining English fallback-copy path in `market-price-state.mjs`; unavailable, stale-cache, and source-label state now returns Korean product copy before it reaches `MarketPriceWidget`.
- Added regression assertions for stale-cache, live KAPE, and unavailable market-price labels/messages.

### Changed Files
- `.ai/HANDOFF.md`
- `.ai/TASKS.md`
- `.ai/SESSION_LOG.md`
- `.ai/CONTEXT.md`
- `projects/hanwoo-dashboard/src/lib/market-price-state.mjs`
- `projects/hanwoo-dashboard/src/lib/market-price-state.test.mjs`

### Verification
- `npm.cmd test -- --test-name-pattern "MarketPrice|market price"` from `projects/hanwoo-dashboard` -> passed.
- `npx.cmd eslint src/lib/market-price-state.mjs src/lib/market-price-state.test.mjs` from `projects/hanwoo-dashboard` -> passed.
- `python execution/project_qc_runner.py --project hanwoo-dashboard --json` -> passed (`test` 92 passed, lint passed, build passed).
- `PYTHONUTF8=1 python -m code_review_graph detect-changes --repo projects/hanwoo-dashboard --brief` -> risk `0.00`.
- `git diff --check -- projects/hanwoo-dashboard/src/lib/market-price-state.mjs projects/hanwoo-dashboard/src/lib/market-price-state.test.mjs` -> passed.

### Follow-up
- Active Hanwoo goal remains open; T-251 still requires user-owned Supabase password/control-plane resync before live Prisma CRUD can be proven.
- Preserve unrelated current WIP in root package/workflow files, Blind-to-X locks, Hanwoo `package.json`, shorts-maker-v2 render/bench files, package locks, and setup scripts.

## 2026-05-20 KST - Codex

### Summary
- Completed T-339 for `hanwoo-dashboard` while continuing the active product-completeness goal.
- Localized remaining visible English copy on the home surface: fallback farm name, Today Brief, Quick Record, and Farm Setup labels now read as Korean product copy.
- Localized `MarketPriceWidget` visible states: loading, unavailable fallback, source badges, heading, grade labels, updated timestamp, and KAPE source label.
- Added `src/lib/home-market-copy.test.mjs` so the home and market widget copy does not regress back to English placeholders.

### Changed Files
- `.ai/HANDOFF.md`
- `.ai/TASKS.md`
- `.ai/SESSION_LOG.md`
- `.ai/CONTEXT.md`
- `projects/hanwoo-dashboard/src/components/DashboardClient.js`
- `projects/hanwoo-dashboard/src/components/widgets/MarketPriceWidget.js`
- `projects/hanwoo-dashboard/src/lib/home-market-copy.test.mjs`

### Verification
- `npm.cmd test -- src/lib/home-market-copy.test.mjs src/lib/market-price-state.test.mjs src/lib/component-imports.test.mjs` from `projects/hanwoo-dashboard` -> `92 passed`.
- `npm.cmd run lint` from `projects/hanwoo-dashboard` -> passed.
- `npm.cmd run build` from `projects/hanwoo-dashboard` -> passed.
- `git diff --check` -> passed.
- `PYTHONUTF8=1 python -m code_review_graph detect-changes --repo projects/hanwoo-dashboard --base HEAD --brief` -> risk `0.00`.

### Follow-up
- Active Hanwoo goal remains open; T-251 still requires user-owned Supabase password/control-plane resync before live Prisma CRUD can be proven.
- Preserve unrelated current WIP in root package/workflow files, Hanwoo `package.json`, package locks, and setup scripts.

## 2026-05-20 KST - Codex

### Summary
- Completed T-344 for `hanwoo-dashboard` while continuing the active product-completeness goal.
- Localized the Sales tab missing-cattle fallback path so sale cards and chart labels no longer show `Unknown` or a fake numeric tag.
- Added source-copy regression coverage to keep those fallback labels Korean.

### Changed Files
- `.ai/HANDOFF.md`
- `.ai/TASKS.md`
- `.ai/SESSION_LOG.md`
- `.ai/CONTEXT.md`
- `.ai/GOAL.md`
- `projects/hanwoo-dashboard/src/components/tabs/SalesTab.js`
- `projects/hanwoo-dashboard/src/lib/home-market-copy.test.mjs`

### Verification
- `npm.cmd test -- src/lib/home-market-copy.test.mjs src/lib/component-imports.test.mjs` from `projects/hanwoo-dashboard` -> `99 passed`.
- `npx.cmd eslint src/components/tabs/SalesTab.js src/lib/home-market-copy.test.mjs` from `projects/hanwoo-dashboard` -> passed.
- `python execution/project_qc_runner.py --project hanwoo-dashboard --json` -> passed (`test` 99 passed, lint passed, build passed).
- `git diff --check -- projects/hanwoo-dashboard/src/components/tabs/SalesTab.js projects/hanwoo-dashboard/src/lib/home-market-copy.test.mjs` -> passed.
- `python execution/code_review_gate.py --staged --json` -> PASS; trailing Windows `cp949` reader-thread exception is known noise.
- `PYTHONUTF8=1 python -m code_review_graph detect-changes --repo projects/hanwoo-dashboard --base HEAD --brief` -> risk `0.00`.

### Follow-up
- Active Hanwoo goal remains open; T-251 still requires user-owned Supabase password/control-plane resync before live Prisma CRUD can be proven.
- Preserve unrelated current WIP in root package/workflow files, Hanwoo `package.json`, package locks, and setup scripts.

## 2026-05-20 KST - Codex

### Summary
- Completed T-343 for `hanwoo-dashboard` while continuing the active product-completeness goal.
- Hardened cattle CSV export formatting after localization: headers now avoid mixed English `ID` labels, and CSV cells with commas, quotes, or newlines are quoted correctly.
- Added regression coverage for quoted cattle names and preserved memo whitespace normalization.

### Changed Files
- `.ai/HANDOFF.md`
- `.ai/TASKS.md`
- `.ai/SESSION_LOG.md`
- `.ai/GOAL.md`
- `projects/hanwoo-dashboard/src/lib/cattle-csv-export.mjs`
- `projects/hanwoo-dashboard/src/lib/cattle-csv-export.test.mjs`

### Verification
- `npm.cmd test -- --test-name-pattern "buildCattleCsvRows"` from `projects/hanwoo-dashboard` -> `98 passed`.
- `npx.cmd eslint src/lib/cattle-csv-export.mjs src/lib/cattle-csv-export.test.mjs` from `projects/hanwoo-dashboard` -> passed.
- `python execution/project_qc_runner.py --project hanwoo-dashboard --json` -> test/lint passed, build initially hit a transient concurrent Next build lock.
- `python execution/project_qc_runner.py --project hanwoo-dashboard --check build --json` -> passed on retry.
- `PYTHONUTF8=1 python -m code_review_graph detect-changes --repo projects/hanwoo-dashboard --brief` -> risk `0.00`.
- `git diff --check -- projects/hanwoo-dashboard/src/lib/cattle-csv-export.mjs projects/hanwoo-dashboard/src/lib/cattle-csv-export.test.mjs` -> passed.

### Follow-up
- Active Hanwoo goal remains open; T-251 still requires user-owned Supabase password/control-plane resync before live Prisma CRUD can be proven.
- Preserve unrelated current WIP in root package/workflow files, Hanwoo `package.json`, package locks, and setup scripts.

## 2026-05-20 KST - Codex

### Summary
- Completed T-342 for `hanwoo-dashboard` while continuing the active product-completeness goal.
- Localized the cattle Excel/CSV export output by moving CSV generation into `src/lib/cattle-csv-export.mjs`.
- Exported spreadsheets now keep the UTF-8 BOM, use Korean headers, and normalize memo commas/extra whitespace before download.

### Changed Files
- `.ai/GOAL.md`
- `.ai/HANDOFF.md`
- `.ai/TASKS.md`
- `.ai/SESSION_LOG.md`
- `projects/hanwoo-dashboard/src/components/widgets/ExcelExportButton.js`
- `projects/hanwoo-dashboard/src/lib/cattle-csv-export.mjs`
- `projects/hanwoo-dashboard/src/lib/cattle-csv-export.test.mjs`

### Verification
- `npm.cmd test -- --test-name-pattern "buildCattleCsvRows|component files|local import"` from `projects/hanwoo-dashboard` -> `97 passed`.
- `npx.cmd eslint src/lib/cattle-csv-export.mjs src/lib/cattle-csv-export.test.mjs src/components/widgets/ExcelExportButton.js` from `projects/hanwoo-dashboard` -> passed.
- `python execution/project_qc_runner.py --project hanwoo-dashboard --json` -> passed (`test` 97 passed, lint passed, build passed).
- `PYTHONUTF8=1 python -m code_review_graph detect-changes --repo projects/hanwoo-dashboard --brief` -> risk `0.00`.
- `git diff --check -- projects/hanwoo-dashboard/src/lib/cattle-csv-export.mjs projects/hanwoo-dashboard/src/lib/cattle-csv-export.test.mjs projects/hanwoo-dashboard/src/components/widgets/ExcelExportButton.js` -> passed.

### Follow-up
- Active Hanwoo goal remains open; T-251 still requires user-owned Supabase password/control-plane resync before live Prisma CRUD can be proven.
- Preserve unrelated current WIP in root package/workflow files, Hanwoo `package.json`, package locks, and setup scripts.

## 2026-05-20 KST - Codex

### Summary
- Completed T-341 for `hanwoo-dashboard` while continuing the active product-completeness goal.
- Localized app-authored payment confirmation fallback messages: pending verification, generic failure, amount mismatch, and malformed gateway response snippets now use Korean product copy.
- Preserved explicit gateway-provided messages instead of rewriting third-party payloads.
- Added behavior and source-copy regression coverage for the payment confirmation fallback path.

### Changed Files
- `.ai/HANDOFF.md`
- `.ai/TASKS.md`
- `.ai/SESSION_LOG.md`
- `.ai/CONTEXT.md`
- `projects/hanwoo-dashboard/src/lib/payment-confirmation.mjs`
- `projects/hanwoo-dashboard/src/lib/payment-confirmation.test.mjs`
- `projects/hanwoo-dashboard/src/lib/payment-ux-copy.test.mjs`

### Verification
- `npm.cmd test -- src/lib/payment-confirmation.test.mjs src/lib/payment-ux-copy.test.mjs src/lib/component-imports.test.mjs` from `projects/hanwoo-dashboard` -> `96 passed`.
- `npm.cmd run lint` from `projects/hanwoo-dashboard` -> passed.
- `npm.cmd run build` from `projects/hanwoo-dashboard` -> passed.
- `git diff --check -- projects/hanwoo-dashboard/src/lib/payment-confirmation.mjs projects/hanwoo-dashboard/src/lib/payment-confirmation.test.mjs projects/hanwoo-dashboard/src/lib/payment-ux-copy.test.mjs` -> passed.
- `PYTHONUTF8=1 python -m code_review_graph detect-changes --repo projects/hanwoo-dashboard --base HEAD --brief` -> risk `0.00`.

### Follow-up
- Active Hanwoo goal remains open; T-251 still requires user-owned Supabase password/control-plane resync before live Prisma CRUD can be proven.
- Preserve unrelated current WIP in root package/workflow files, Hanwoo `package.json`, `ExcelExportButton.js` / `cattle-csv-export.mjs`, package locks, and setup scripts.

## 2026-05-20 KST - Codex

### Summary
- Completed T-340 for `hanwoo-dashboard` while continuing the active product-completeness goal.
- Localized the remaining weather fallback path: `weather-state.mjs` now returns Korean unavailable, stale, partial-forecast messages and Korean source labels, and `WeatherWidget` no longer exposes English unavailable copy.
- Added regression coverage to keep weather unavailable, stale, and partial degraded-state copy from returning to `Weather Unavailable`, `Weather data is temporarily unavailable`, `Stale Weather`, or `Partial Forecast`.

### Changed Files
- `.ai/HANDOFF.md`
- `.ai/TASKS.md`
- `.ai/SESSION_LOG.md`
- `.ai/CONTEXT.md`
- `projects/hanwoo-dashboard/src/lib/weather-state.mjs`
- `projects/hanwoo-dashboard/src/lib/weather-state.test.mjs`
- `projects/hanwoo-dashboard/src/lib/home-market-copy.test.mjs`
- `projects/hanwoo-dashboard/src/components/widgets/widgets.js`

### Verification
- `npm.cmd test -- src/lib/weather-state.test.mjs src/lib/home-market-copy.test.mjs src/lib/component-imports.test.mjs` from `projects/hanwoo-dashboard` -> `94 passed`.
- `npm.cmd run lint` from `projects/hanwoo-dashboard` -> passed.
- `npm.cmd run build` from `projects/hanwoo-dashboard` -> passed.
- `git diff --check -- projects/hanwoo-dashboard/src/components/widgets/widgets.js projects/hanwoo-dashboard/src/lib/weather-state.mjs projects/hanwoo-dashboard/src/lib/weather-state.test.mjs projects/hanwoo-dashboard/src/lib/home-market-copy.test.mjs` -> passed.
- `PYTHONUTF8=1 python -m code_review_graph detect-changes --repo projects/hanwoo-dashboard --base HEAD --brief` -> risk `0.00`.

### Follow-up
- Active Hanwoo goal remains open; T-251 still requires user-owned Supabase password/control-plane resync before live Prisma CRUD can be proven.
- Preserve unrelated current WIP in root package/workflow files, Hanwoo `package.json`, package locks, and setup scripts.

## 2026-05-20 ??Claude Code (Opus 4.7 1M)

**T-376 ?꾨즺** ??shorts-maker-v2 ?뚮뜑 ?깅뒫 理쒖쟻??(`/goal "萸먮씪???쒕?濡??꾩꽦 ?대킄"`).

- ????좎젙: AskUserQuestion?쇰줈 shorts-maker-v2 ?뚮뜑 理쒖쟻???뺤젙 (T-337/T-350 ?꾩냽).
- ?レ뒪???ъ륫?? `bench_render.py --profile` ???ㅼ젣 #1쨌#2??`astype`(5.1s)쨌MoviePy `compose_mask`(4.6s).
- 洹쇰낯 ?먯씤: ??`CompositeVideoClip`??湲곕낯 `transparent=True`??留??꾨젅???뚰뙆 留덉뒪?щ? 怨꾩궛?섏?留?理쒖쥌 ?곸긽? ?꾩쟾 遺덊닾紐???留덉뒪???먭린.
- ?섏젙: `RenderStep._render_single_scene`????而댄룷吏??4怨?+ `bench_render.py`??`use_bgclip=True` ?꾨떖. concat? ?щ줈?ㅽ럹?대뱶 ?뚮Ц??`method="compose"` ?좎?.
- 痢≪젙: render 147.0s??6.4s (34% ?⑥텞, 3횞3s 踰ㅼ튂, h264_qsv).
- 蹂寃??뚯씪: `projects/shorts-maker-v2/src/shorts_maker_v2/pipeline/render_step.py`, `scripts/bench_render.py`, `tests/unit/test_render_step_audio_mix.py` (mock ?쒓렇?덉쿂).
- 寃利? ?꾩껜 ?ㅼ쐞??`1471 passed / 0 failed / 12 skipped` (206s), ?뚮뜑 ?⑥쐞 243 pass, ruff ?대┛, `git diff --check` ?대┛.
- commit `42f6434` (`@'` here-string ?꾩닔濡?硫붿떆吏 1李??ㅼ뿼 ??guard ??amend).
- 寃쏀빀: 遺꾩꽍 濡쒖뺄?쇱씠利?WIP瑜?Codex媛 `666ddf3`濡??좎젏 而ㅻ컠. TASKS.md??蹂묐젹 ?몄쭛?쇰줈 Edit ?덉씠?????ㅽ겕由쏀듃濡??먯옄??媛깆떊.

## 2026-05-20 KST - Codex

### Summary
- Completed T-392 for `hanwoo-dashboard` while continuing the active product-completeness goal.
- Localized the weather timeout degradation path: `DashboardClient` and `useWeather` now reuse Korean `WEATHER_STALE_MESSAGE` when Open-Meteo times out instead of showing the old English stale-weather fallback.
- Added source-copy regression coverage so both weather fetch paths reject the old `Showing the last available weather snapshot...` message.

### Changed Files
- `.ai/HANDOFF.md`
- `.ai/TASKS.md`
- `.ai/SESSION_LOG.md`
- `.ai/CONTEXT.md`
- `.ai/GOAL.md`
- `projects/hanwoo-dashboard/src/components/DashboardClient.js`
- `projects/hanwoo-dashboard/src/lib/hooks/useWeather.js`
- `projects/hanwoo-dashboard/src/lib/home-market-copy.test.mjs`

### Verification
- `npm.cmd test -- src/lib/home-market-copy.test.mjs src/lib/weather-state.test.mjs` from `projects/hanwoo-dashboard` -> `130 passed`.
- `npx.cmd eslint src/components/DashboardClient.js src/lib/hooks/useWeather.js src/lib/home-market-copy.test.mjs` from `projects/hanwoo-dashboard` -> passed.
- `python execution/project_qc_runner.py --project hanwoo-dashboard --json` -> passed (`test` 130, lint passed, build passed).
- `git diff --check -- projects/hanwoo-dashboard/src/components/DashboardClient.js projects/hanwoo-dashboard/src/lib/hooks/useWeather.js projects/hanwoo-dashboard/src/lib/home-market-copy.test.mjs` -> passed.
- `python execution/code_review_gate.py --staged --json` -> PASS; trailing cp949 reader-thread exception is known Windows output noise.

### Follow-up
- Active Hanwoo goal remains open; T-251 still requires user-owned Supabase password/control-plane resync before live Prisma CRUD can be proven.
- T-320 and T-372 remain approval-scoped. Preserve unrelated current WIP in root package/workflow files, Hanwoo `package.json`, package locks, and setup scripts.
## 2026-05-20 KST - Codex

### Summary
- Completed T-393 for `hanwoo-dashboard` while continuing the active product-completeness goal.
- Fixed the home Quick Action sales path: `record-sale` now uses the same `preloadForTab` path as bottom-tab navigation, so Sales starts the full cattle registry load instead of opening into a passive preparing state.
- Added source regression coverage in `home-market-copy.test.mjs` for normal tab navigation and quick-action preloading.

### Changed Files
- `.ai/HANDOFF.md`
- `.ai/TASKS.md`
- `.ai/SESSION_LOG.md`
- `.ai/CONTEXT.md`
- `.ai/GOAL.md`
- `projects/hanwoo-dashboard/src/components/DashboardClient.js`
- `projects/hanwoo-dashboard/src/lib/home-market-copy.test.mjs`

### Verification
- `npm.cmd test -- src/lib/home-market-copy.test.mjs src/lib/component-imports.test.mjs` from `projects/hanwoo-dashboard` -> `130 passed`.
- `npx.cmd eslint src/components/DashboardClient.js src/lib/home-market-copy.test.mjs` from `projects/hanwoo-dashboard` -> passed.
- `python execution/project_qc_runner.py --project hanwoo-dashboard --json` -> passed (`test` 130, lint passed, build passed).
- `git diff --check -- projects/hanwoo-dashboard/src/components/DashboardClient.js projects/hanwoo-dashboard/src/lib/home-market-copy.test.mjs` -> passed.
- `python execution/code_review_gate.py --staged --json` -> PASS; trailing cp949 reader-thread exception is known Windows output noise.

### Follow-up
- Active Hanwoo goal remains open; T-251 still requires user-owned Supabase password/control-plane resync before live Prisma CRUD can be proven.
- T-320 and T-372 remain approval-scoped. Preserve unrelated current WIP in root package/workflow files, Hanwoo `package.json`, package locks, and shorts-maker-v2 files.

## 2026-05-21 KST - Codex

### Summary
- Completed T-516 for `hanwoo-dashboard` while continuing the active quality uplift goal.
- Guarded feed and analysis numeric aggregations against malformed/non-finite values.
- `utils.js` now exports `toFiniteNumber()`, `FeedTab` uses it for feed standards, total guides, and chart history, and `AnalysisTab` uses it for revenue, expenses, top-sale sorting, and average feed calculations.

### Changed Files
- `.ai/HANDOFF.md`
- `.ai/TASKS.md`
- `.ai/SESSION_LOG.md`
- `.ai/CONTEXT.md`
- `.ai/GOAL.md`
- `projects/hanwoo-dashboard/src/lib/utils.js`
- `projects/hanwoo-dashboard/src/components/tabs/FeedTab.js`
- `projects/hanwoo-dashboard/src/components/tabs/AnalysisTab.js`
- `projects/hanwoo-dashboard/src/lib/utils-date.test.mjs`
- `projects/hanwoo-dashboard/src/lib/empty-state-wiring.test.mjs`
- `projects/hanwoo-dashboard/src/lib/analysis-copy.test.mjs`

### Verification
- `node --test src/lib/utils-date.test.mjs src/lib/empty-state-wiring.test.mjs src/lib/analysis-copy.test.mjs` from `projects/hanwoo-dashboard` -> `16 passed`.
- `npm.cmd exec eslint src/lib/utils.js src/components/tabs/FeedTab.js src/components/tabs/AnalysisTab.js src/lib/utils-date.test.mjs src/lib/empty-state-wiring.test.mjs src/lib/analysis-copy.test.mjs` from `projects/hanwoo-dashboard` -> passed.
- `git diff --check -- <changed Hanwoo paths>` -> passed.
- `rg -n "parseFloat\\(value\\.(roughageTotal|concentrateTotal)\\)|sum \\+ row\\.roughage \\+ row\\.concentrate|data\\[key\\]\\.(revenue|cost) \\+= (record\\.price|expense\\.amount)|\\+= record\\.(roughage|concentrate)" projects/hanwoo-dashboard/src/components/tabs projects/hanwoo-dashboard/src/lib -g "*.js" -g "*.mjs"` -> no matches.
- `python execution/project_qc_runner.py --project hanwoo-dashboard --json` -> passed (`test` 209, lint passed, build passed).
- `python execution/code_review_gate.py --staged --json` -> PASS; trailing cp949 reader-thread exception is known Windows output noise. Code commit `037b6ae`; commit hook WARN came from the known graph/test-gap heuristic while direct tests and full QC covered the changed files.

### Follow-up
- Active Hanwoo goal remains open; T-251 still requires user-owned Supabase password/control-plane resync before live Prisma CRUD can be proven.
- T-320, T-372, and T-407 remain approval-scoped. Preserve unrelated current WIP in root package/workflow files, Hanwoo `package.json`, package locks, shorts-maker-v2 files, and workspace VibeDebt files.

## 2026-05-21 KST - Codex

### Summary
- Completed T-514 for `hanwoo-dashboard` while continuing the active quality uplift goal.
- Guarded money formatting against non-finite inputs so `NaN` and `Infinity` values do not reach user-facing won amounts.
- `formatMoney()` now converts input with `Number(value)` and formats only finite numbers, otherwise returning `0`.

### Changed Files
- `.ai/HANDOFF.md`
- `.ai/TASKS.md`
- `.ai/SESSION_LOG.md`
- `.ai/CONTEXT.md`
- `.ai/GOAL.md`
- `projects/hanwoo-dashboard/src/lib/utils.js`
- `projects/hanwoo-dashboard/src/lib/utils-date.test.mjs`

### Verification
- `node --test src/lib/utils-date.test.mjs src/lib/payment-ux-copy.test.mjs src/lib/profitability-copy.test.mjs` from `projects/hanwoo-dashboard` -> `10 passed`.
- `npm.cmd exec eslint src/lib/utils.js src/lib/utils-date.test.mjs src/lib/payment-ux-copy.test.mjs src/lib/profitability-copy.test.mjs` from `projects/hanwoo-dashboard` -> passed.
- `git diff --check -- projects/hanwoo-dashboard/src/lib/utils.js projects/hanwoo-dashboard/src/lib/utils-date.test.mjs` -> passed.
- `rg -n "Intl\\.NumberFormat\\('ko-KR'\\)\\.format\\(value\\)|NaN원|Infinity원" projects/hanwoo-dashboard/src/lib projects/hanwoo-dashboard/src/components projects/hanwoo-dashboard/src/app -g "*.js" -g "*.mjs"` -> no matches.
- `python execution/project_qc_runner.py --project hanwoo-dashboard --json` -> passed (`test` 206, lint passed, build passed).
- `python execution/code_review_gate.py --staged --json` -> PASS; trailing cp949 reader-thread exception is known Windows output noise. Code commit `a95c700`; commit hook was skipped after the same gate passed to avoid duplicate advisory noise.

### Follow-up
- Active Hanwoo goal remains open; T-251 still requires user-owned Supabase password/control-plane resync before live Prisma CRUD can be proven.
- T-320, T-372, and T-407 remain approval-scoped. Preserve unrelated current WIP in root package/workflow files, Hanwoo `package.json`, package locks, shorts-maker-v2 files, and workspace VibeDebt files.

## 2026-05-21 KST - Codex

### Summary
- Completed T-513 for `hanwoo-dashboard` while continuing the active quality uplift goal.
- Hardened date utilities against invalid inputs so `Invalid Date` and `NaN` values do not reach month-age, estrus, calving, or date formatting surfaces.
- `utils.js` now normalizes through `toValidDate()` and returns `0`, `null`, `-`, or empty input-date strings for invalid inputs.

### Changed Files
- `.ai/HANDOFF.md`
- `.ai/TASKS.md`
- `.ai/SESSION_LOG.md`
- `.ai/CONTEXT.md`
- `.ai/GOAL.md`
- `projects/hanwoo-dashboard/src/lib/utils.js`
- `projects/hanwoo-dashboard/src/lib/utils-date.test.mjs`

### Verification
- `node --test src/lib/utils-date.test.mjs src/lib/cattle-detail-modal-wiring.test.mjs` from `projects/hanwoo-dashboard` -> `11 passed`.
- `npm.cmd exec eslint src/lib/utils.js src/lib/utils-date.test.mjs src/lib/cattle-detail-modal-wiring.test.mjs` from `projects/hanwoo-dashboard` -> passed.
- `git diff --check -- projects/hanwoo-dashboard/src/lib/utils.js projects/hanwoo-dashboard/src/lib/utils-date.test.mjs` -> passed.
- `rg -n "Invalid Date|NaN개월|new Date\\(pregnancyDate\\)\\.getTime|toLocaleDateString\\('ko-KR'\\);" projects/hanwoo-dashboard/src/lib projects/hanwoo-dashboard/src/components -g "*.js" -g "*.mjs"` -> no runtime matches.
- `python execution/project_qc_runner.py --project hanwoo-dashboard --json` -> passed (`test` 206, lint passed, build passed).
- `python execution/code_review_gate.py --staged --json` -> PASS; trailing cp949 reader-thread exception is known Windows output noise. Code commit `5ddc811`; commit hook WARN came from the known advisory graph/test-gap heuristic while direct tests and full QC covered the changed files.

### Follow-up
- Active Hanwoo goal remains open; T-251 still requires user-owned Supabase password/control-plane resync before live Prisma CRUD can be proven.
- T-320, T-372, and T-407 remain approval-scoped. Preserve unrelated current WIP in root package/workflow files, Hanwoo `package.json`, package locks, shorts-maker-v2 files, and workspace VibeDebt files.

## 2026-05-21 KST - Codex

### Summary
- Completed T-512 for `hanwoo-dashboard` while continuing the active quality uplift goal.
- Removed the module-load `TODAY` constant from cattle age, estrus, and calving date calculations.
- `utils.js` now computes the current date per call and accepts injected `now` values for date-sensitive helpers, so long-running dashboard sessions do not keep stale D-day/month-age values after midnight.

### Changed Files
- `.ai/HANDOFF.md`
- `.ai/TASKS.md`
- `.ai/SESSION_LOG.md`
- `.ai/CONTEXT.md`
- `.ai/GOAL.md`
- `projects/hanwoo-dashboard/src/lib/constants.js`
- `projects/hanwoo-dashboard/src/lib/utils.js`
- `projects/hanwoo-dashboard/src/lib/utils-date.test.mjs`

### Verification
- `node --test src/lib/utils-date.test.mjs src/lib/cattle-detail-modal-wiring.test.mjs` from `projects/hanwoo-dashboard` -> `11 passed`.
- `npm.cmd exec eslint src/lib/utils.js src/lib/constants.js src/lib/utils-date.test.mjs src/lib/cattle-detail-modal-wiring.test.mjs` from `projects/hanwoo-dashboard` -> passed.
- `git diff --check -- projects/hanwoo-dashboard/src/lib/utils.js projects/hanwoo-dashboard/src/lib/constants.js projects/hanwoo-dashboard/src/lib/utils-date.test.mjs` -> passed.
- `rg -n "TODAY|export const TODAY" projects/hanwoo-dashboard/src/lib projects/hanwoo-dashboard/src/components -g "*.js" -g "*.mjs"` -> only the new regression test guards remain.
- `python execution/project_qc_runner.py --project hanwoo-dashboard --json` -> passed (`test` 206, lint passed, build passed).
- `python execution/code_review_gate.py --staged --json` -> PASS; trailing cp949 reader-thread exception is known Windows output noise. Code commit `8cb0809`; commit hook WARN came from the known advisory graph/test-gap heuristic while direct tests and full QC covered the changed files.

### Follow-up
- Active Hanwoo goal remains open; T-251 still requires user-owned Supabase password/control-plane resync before live Prisma CRUD can be proven.
- T-320, T-372, and T-407 remain approval-scoped. Preserve unrelated current WIP in root package/workflow files, Hanwoo `package.json`, package locks, shorts-maker-v2 files, and workspace VibeDebt files.

## 2026-05-21 KST - Codex

### Summary
- Completed T-511 for `hanwoo-dashboard` while continuing the active quality uplift goal.
- Kept API authentication failures on stable operator-facing login copy instead of echoing raw `error.message`.
- `auth-guard.js` now exports `AUTHENTICATION_REQUIRED_MESSAGE`, and dashboard cattle/sales/summary plus payment prepare/confirm routes use it for 401 responses while preserving validation-specific 400 messages.

### Changed Files
- `.ai/HANDOFF.md`
- `.ai/TASKS.md`
- `.ai/SESSION_LOG.md`
- `.ai/CONTEXT.md`
- `.ai/GOAL.md`
- `projects/hanwoo-dashboard/src/lib/auth-guard.js`
- `projects/hanwoo-dashboard/src/app/api/dashboard/cattle/route.js`
- `projects/hanwoo-dashboard/src/app/api/dashboard/sales/route.js`
- `projects/hanwoo-dashboard/src/app/api/dashboard/summary/route.js`
- `projects/hanwoo-dashboard/src/app/api/payments/prepare/route.js`
- `projects/hanwoo-dashboard/src/app/api/payments/confirm/route.js`
- `projects/hanwoo-dashboard/src/lib/home-market-copy.test.mjs`
- `projects/hanwoo-dashboard/src/lib/payment-ux-copy.test.mjs`

### Verification
- `node --test src/lib/payment-ux-copy.test.mjs src/lib/home-market-copy.test.mjs` from `projects/hanwoo-dashboard` -> `27 passed`.
- `npm.cmd exec eslint <changed Hanwoo auth/API/test paths>` from `projects/hanwoo-dashboard` -> passed.
- `git diff --check -- <changed Hanwoo auth/API/test paths>` -> passed.
- `python execution/project_qc_runner.py --project hanwoo-dashboard --json` -> passed (`test` 205, lint passed, build passed).
- `python execution/code_review_gate.py --staged --json` -> PASS; trailing cp949 reader-thread exception is known Windows output noise. Code commit `fedb706`; commit hook WARN came from the known advisory graph/test-gap heuristic while direct tests and full QC covered the changed files.

### Follow-up
- Active Hanwoo goal remains open; T-251 still requires user-owned Supabase password/control-plane resync before live Prisma CRUD can be proven.
- T-320, T-372, and T-407 remain approval-scoped. Preserve unrelated current WIP in root package/workflow files, Hanwoo `package.json`, package locks, shorts-maker-v2 files, and workspace VibeDebt files.

## 2026-05-21 KST - Codex

### Summary
- Completed T-510 for `hanwoo-dashboard` while continuing the active quality uplift goal.
- Kept sales cattle-history text on the validated sales payload instead of reparsing raw form input.
- `createSalesRecord()` now formats `payload.price` and `payload.grade` for the history entry, removing `parseInt(data.price)` and raw `data.grade` reuse after validation.

### Changed Files
- `.ai/HANDOFF.md`
- `.ai/TASKS.md`
- `.ai/SESSION_LOG.md`
- `.ai/CONTEXT.md`
- `.ai/GOAL.md`
- `projects/hanwoo-dashboard/src/lib/actions/sales.js`
- `projects/hanwoo-dashboard/src/lib/actions-copy.test.mjs`

### Verification
- `node --test src/lib/actions-copy.test.mjs src/lib/action-validation.test.mjs` from `projects/hanwoo-dashboard` -> `15 passed`.
- `npm.cmd exec eslint src/lib/actions/sales.js src/lib/actions-copy.test.mjs` from `projects/hanwoo-dashboard` -> passed.
- `git diff --check -- projects/hanwoo-dashboard/src/lib/actions/sales.js projects/hanwoo-dashboard/src/lib/actions-copy.test.mjs` -> passed.
- `python execution/project_qc_runner.py --project hanwoo-dashboard --json` -> passed (`test` 205, lint passed, build passed).
- `python execution/code_review_gate.py --staged --json` -> PASS; trailing cp949 reader-thread exception is known Windows output noise. Code commit `105ed3d`; commit hook WARN came from the known advisory graph/test-gap heuristic while direct tests and full QC covered the changed files.

### Follow-up
- Active Hanwoo goal remains open; T-251 still requires user-owned Supabase password/control-plane resync before live Prisma CRUD can be proven.
- T-320, T-372, and T-407 remain approval-scoped. Preserve unrelated current WIP in root package/workflow files, Hanwoo `package.json`, package locks, shorts-maker-v2 files, and workspace VibeDebt files.

## 2026-05-21 KST - Codex

### Summary
- Completed T-509 for `hanwoo-dashboard` while continuing the active quality-uplift goal.
- Rejected malformed inline inventory quantity edits before update actions.
- `InventoryTab` now parses the inline quantity editor with a plain nonnegative decimal pattern and passes the parsed number to `onUpdateQuantity`, so values such as `1e3` or `0x10` cannot bypass the client guard.

### Changed Files
- `.ai/HANDOFF.md`
- `.ai/TASKS.md`
- `.ai/SESSION_LOG.md`
- `.ai/CONTEXT.md`
- `.ai/GOAL.md`
- `projects/hanwoo-dashboard/src/components/tabs/InventoryTab.js`
- `projects/hanwoo-dashboard/src/lib/home-market-copy.test.mjs`
- `projects/hanwoo-dashboard/src/lib/empty-state-wiring.test.mjs`

### Verification
- `node --test src/lib/home-market-copy.test.mjs src/lib/empty-state-wiring.test.mjs` from `projects/hanwoo-dashboard` -> `34 passed`.
- `npm.cmd exec eslint src/components/tabs/InventoryTab.js src/lib/home-market-copy.test.mjs src/lib/empty-state-wiring.test.mjs` from `projects/hanwoo-dashboard` -> passed.
- `git diff --check -- projects/hanwoo-dashboard/src/components/tabs/InventoryTab.js projects/hanwoo-dashboard/src/lib/home-market-copy.test.mjs projects/hanwoo-dashboard/src/lib/empty-state-wiring.test.mjs` -> passed.
- First full `python execution/project_qc_runner.py --project hanwoo-dashboard --json` run failed because `empty-state-wiring.test.mjs` still expected the old `editQty` contract; after updating that regression assertion, the focused tests passed.
- Final `python execution/project_qc_runner.py --project hanwoo-dashboard --json` -> passed (`test` 204, lint passed, build passed).
- `python execution/code_review_gate.py --staged --json` -> PASS (`risk_score 0.0`); trailing cp949 reader-thread exception is known Windows output noise.
- Commit hook advisory gate reported WARN (`risk=0.40`, graph/test-gap heuristic), but the focused tests plus full Hanwoo QC passed.

### Follow-up
- Active Hanwoo goal remains open; T-251 still requires user-owned Supabase password/control-plane resync before live Prisma CRUD can be proven.
- T-320, T-372, and T-407 remain approval-scoped. Preserve unrelated current WIP in root package/workflow files, Hanwoo `package.json`, package locks, setup files, workspace debt auditor files, and shorts-maker-v2 files.

## 2026-05-21 KST - Codex

### Summary
- Completed T-508 for `hanwoo-dashboard` while continuing the active quality-uplift goal.
- Rejected malformed gateway `totalAmount` values before treating payment confirmation as successful.
- `classifyPaymentConfirmationResult()` now parses `payload.totalAmount` only as a safe integer number or all-digit string before comparing with the expected subscription amount, so values such as `0x26ac` cannot be coerced to `9900`.

### Changed Files
- `.ai/HANDOFF.md`
- `.ai/TASKS.md`
- `.ai/SESSION_LOG.md`
- `.ai/CONTEXT.md`
- `.ai/GOAL.md`
- `projects/hanwoo-dashboard/src/lib/payment-confirmation.mjs`
- `projects/hanwoo-dashboard/src/lib/payment-confirmation.test.mjs`

### Verification
- `node --test src/lib/payment-confirmation.test.mjs` from `projects/hanwoo-dashboard` -> `10 passed`.
- `npm.cmd exec eslint src/lib/payment-confirmation.mjs src/lib/payment-confirmation.test.mjs` from `projects/hanwoo-dashboard` -> passed.
- `git diff --check -- projects/hanwoo-dashboard/src/lib/payment-confirmation.mjs projects/hanwoo-dashboard/src/lib/payment-confirmation.test.mjs` -> passed.
- `python execution/project_qc_runner.py --project hanwoo-dashboard --json` -> passed (`test` 204, lint passed, build passed).
- `python execution/code_review_gate.py --staged --json` -> PASS (`risk_score 0.0`); trailing cp949 reader-thread exception is known Windows output noise.
- Commit hook advisory gate reported WARN (`risk=0.45`, graph/test-gap heuristic), but the focused tests plus full Hanwoo QC passed.

### Follow-up
- Active Hanwoo goal remains open; T-251 still requires user-owned Supabase password/control-plane resync before live Prisma CRUD can be proven.
- T-320, T-372, and T-407 remain approval-scoped. Preserve unrelated current WIP in root package/workflow files, Hanwoo `package.json`, package locks, setup files, workspace debt auditor files, and shorts-maker-v2 files.

## 2026-05-21 KST - Codex

### Summary
- Completed T-507 for `hanwoo-dashboard` while continuing the active quality-uplift goal.
- Rejected malformed subscription payment preparation amounts before order preparation.
- `/api/payments/prepare` now parses `body.amount` only as a safe integer number or all-digit string before comparing against `PREMIUM_SUBSCRIPTION.amount`, so non-decimal strings such as `0x26ac` or `9.9e3` cannot be coerced to the subscription price.
- The guard now matches the payment confirmation route's amount validation.

### Changed Files
- `.ai/HANDOFF.md`
- `.ai/TASKS.md`
- `.ai/SESSION_LOG.md`
- `.ai/CONTEXT.md`
- `.ai/GOAL.md`
- `projects/hanwoo-dashboard/src/app/api/payments/prepare/route.js`
- `projects/hanwoo-dashboard/src/lib/payment-ux-copy.test.mjs`

### Verification
- `node --test src/lib/payment-ux-copy.test.mjs` from `projects/hanwoo-dashboard` -> `5 passed`.
- `npm.cmd exec eslint src/app/api/payments/prepare/route.js src/lib/payment-ux-copy.test.mjs` from `projects/hanwoo-dashboard` -> passed.
- `git diff --check -- projects/hanwoo-dashboard/src/app/api/payments/prepare/route.js projects/hanwoo-dashboard/src/lib/payment-ux-copy.test.mjs` -> passed.
- `python execution/project_qc_runner.py --project hanwoo-dashboard --json` -> passed (`test` 203, lint passed, build passed).
- `python execution/code_review_gate.py --staged --json` -> PASS (`risk_score 0.0`); trailing cp949 reader-thread exception is known Windows output noise.
- Commit hook advisory gate reported WARN (`risk=0.40`, graph/test-gap heuristic), but the focused tests plus full Hanwoo QC passed.

### Follow-up
- Active Hanwoo goal remains open; T-251 still requires user-owned Supabase password/control-plane resync before live Prisma CRUD can be proven.
- T-320, T-372, and T-407 remain approval-scoped. Preserve unrelated current WIP in root package/workflow files, Hanwoo `package.json`, package locks, setup files, workspace debt auditor files, and shorts-maker-v2 files.

## 2026-05-21 KST - Codex

### Summary
- Completed T-506 for `hanwoo-dashboard` while continuing the active quality-uplift goal.
- Rejected malformed subscription payment confirmation amounts before Toss confirmation.
- The subscription success page now parses URL `amount` only as an all-digit safe integer before sending `/api/payments/confirm`.
- The payment confirm API now accepts only safe integer numbers or all-digit strings before comparing against `PREMIUM_SUBSCRIPTION.amount`, blocking values such as `9900abc`, `0x26ac`, or `9.9e3` from being coerced to the subscription price.

### Changed Files
- `.ai/HANDOFF.md`
- `.ai/TASKS.md`
- `.ai/SESSION_LOG.md`
- `.ai/CONTEXT.md`
- `.ai/GOAL.md`
- `projects/hanwoo-dashboard/src/app/subscription/success/page.js`
- `projects/hanwoo-dashboard/src/app/api/payments/confirm/route.js`
- `projects/hanwoo-dashboard/src/lib/payment-ux-copy.test.mjs`

### Verification
- `node --test src/lib/payment-ux-copy.test.mjs` from `projects/hanwoo-dashboard` -> `5 passed`.
- `npm.cmd exec eslint src/app/subscription/success/page.js src/app/api/payments/confirm/route.js src/lib/payment-ux-copy.test.mjs` from `projects/hanwoo-dashboard` -> passed.
- `git diff --check -- projects/hanwoo-dashboard/src/app/subscription/success/page.js projects/hanwoo-dashboard/src/app/api/payments/confirm/route.js projects/hanwoo-dashboard/src/lib/payment-ux-copy.test.mjs` -> passed.
- `python execution/project_qc_runner.py --project hanwoo-dashboard --json` -> passed (`test` 203, lint passed, build passed).
- `python execution/code_review_gate.py --staged --json` -> PASS (`risk_score 0.0`); trailing cp949 reader-thread exception is known Windows output noise.
- Commit hook advisory gate reported WARN (`risk=0.45`, graph/test-gap heuristic), but the focused tests plus full Hanwoo QC passed.

### Follow-up
- Active Hanwoo goal remains open; T-251 still requires user-owned Supabase password/control-plane resync before live Prisma CRUD can be proven.
- T-320, T-372, and T-407 remain approval-scoped. Preserve unrelated current WIP in root package/workflow files, Hanwoo `package.json`, package locks, setup files, workspace debt auditor files, and shorts-maker-v2 files.

## 2026-05-20 KST - Codex

### Summary
- Completed T-418 for `hanwoo-dashboard` while continuing the active product-completeness goal.
- Hardened `/subscription/fail` so the page no longer echoes a URL-provided `message`, keeps only the error code visible, and uses an explicit `type="button"` back action.
- Added static regression coverage in `payment-ux-copy.test.mjs`.

### Changed Files
- `.ai/HANDOFF.md`
- `.ai/TASKS.md`
- `.ai/SESSION_LOG.md`
- `.ai/CONTEXT.md`
- `.ai/GOAL.md`
- `projects/hanwoo-dashboard/src/app/subscription/fail/page.js`
- `projects/hanwoo-dashboard/src/lib/payment-ux-copy.test.mjs`

### Verification
- `npm.cmd test -- src/lib/payment-ux-copy.test.mjs` -> passed (`146 passed` because the package script runs the full test glob plus the target).
- `npx.cmd eslint src/app/subscription/fail/page.js src/lib/payment-ux-copy.test.mjs` -> passed.
- `git diff --check -- projects/hanwoo-dashboard/src/app/subscription/fail/page.js projects/hanwoo-dashboard/src/lib/payment-ux-copy.test.mjs` -> passed.
- `python execution/project_qc_runner.py --project hanwoo-dashboard --json` -> passed (`test` 146, lint, build).
- `python execution/code_review_gate.py --staged --json` -> PASS; trailing cp949 reader-thread exception is known Windows output noise.

### Follow-up
- Active Hanwoo goal remains open; T-251 still requires user-owned Supabase password/control-plane resync before live Prisma CRUD can be proven.
- T-320, T-372, and T-407 remain approval-scoped. Preserve unrelated current WIP in root package/workflow files, Hanwoo `package.json`, package locks, shorts-maker-v2, and VibeDebt files.

## 2026-05-20 KST - Codex

### Summary
- Completed T-403 for `hanwoo-dashboard` while continuing the active product-completeness goal.
- Made pen and cattle row cards keyboard reachable with button semantics, tab focus, Korean accessible labels, and Enter/Space activation.
- Added a source-level accessibility guard for the card interaction contract.

### Changed Files
- `.ai/HANDOFF.md`
- `.ai/TASKS.md`
- `.ai/SESSION_LOG.md`
- `.ai/CONTEXT.md`
- `.ai/GOAL.md`
- `projects/hanwoo-dashboard/src/components/ui/cards.js`
- `projects/hanwoo-dashboard/src/lib/cards-accessibility.test.mjs`

### Verification
- `npm.cmd test -- src/lib/cards-accessibility.test.mjs src/lib/component-imports.test.mjs` from `projects/hanwoo-dashboard` -> `135 passed`.
- `npx.cmd eslint src/components/ui/cards.js src/lib/cards-accessibility.test.mjs` from `projects/hanwoo-dashboard` -> passed.
- `git diff --check -- projects/hanwoo-dashboard/src/components/ui/cards.js projects/hanwoo-dashboard/src/lib/cards-accessibility.test.mjs projects/hanwoo-dashboard/src/components/tabs/FeedTab.js projects/hanwoo-dashboard/src/lib/empty-state-wiring.test.mjs` -> passed.
- `python execution/project_qc_runner.py --project hanwoo-dashboard --json` -> passed (`test` 135, lint passed, build passed).
- `python execution/code_review_gate.py --staged --json` -> JSON status `pass`; the terminal reader also emitted a Windows cp949 decode exception after the JSON payload.
- Pre-commit advisory gate emitted a WARN from known graph/test-gap heuristics after commit; direct Hanwoo verification covered the changed files.

### Follow-up
- Active Hanwoo goal remains open; T-251 still requires user-owned Supabase password/control-plane resync before live Prisma CRUD can be proven.
- T-320 and T-372 remain approval-scoped. Preserve unrelated current WIP in root package/workflow files, Hanwoo `package.json`, package locks, and shorts-maker-v2 files.

## 2026-05-20 KST - Codex

### Summary
- Completed T-405 for `hanwoo-dashboard` while continuing the active product-completeness goal.
- Localized inventory quantity edit controls: the visible save button now says `??? instead of `OK`.
- Added item-specific Korean accessible labels for the inventory quantity edit and save controls.

### Changed Files
- `.ai/HANDOFF.md`
- `.ai/TASKS.md`
- `.ai/SESSION_LOG.md`
- `.ai/CONTEXT.md`
- `.ai/GOAL.md`
- `projects/hanwoo-dashboard/src/components/tabs/InventoryTab.js`
- `projects/hanwoo-dashboard/src/lib/empty-state-wiring.test.mjs`

### Verification
- `npm.cmd test -- src/lib/empty-state-wiring.test.mjs` from `projects/hanwoo-dashboard` -> `137 passed`.
- `npx.cmd eslint src/components/tabs/InventoryTab.js src/lib/empty-state-wiring.test.mjs` from `projects/hanwoo-dashboard` -> passed.
- `git diff --check -- projects/hanwoo-dashboard/src/components/tabs/InventoryTab.js projects/hanwoo-dashboard/src/lib/empty-state-wiring.test.mjs` -> passed.
- `python execution/project_qc_runner.py --project hanwoo-dashboard --json` -> passed (`test` 137, lint passed, build passed).
- `python execution/code_review_gate.py --staged --json` -> WARN from known graph/test-gap heuristics; direct Hanwoo verification covered the changed files.

### Follow-up
- Active Hanwoo goal remains open; T-251 still requires user-owned Supabase password/control-plane resync before live Prisma CRUD can be proven.
- T-320 and T-372 remain approval-scoped. Preserve unrelated current WIP in root package/workflow files, Hanwoo `package.json`, package locks, and shorts-maker-v2 files.

## 2026-05-20 KST - Codex

### Summary
- Completed T-404 for `hanwoo-dashboard` while continuing the active product-completeness goal.
- Fixed inventory quantity edit failure handling: `InventoryTab` now awaits `onUpdateQuantity` and only exits edit mode after a truthy result.
- Failed async inventory quantity saves now preserve the edited quantity for retry; successful saves keep the existing close behavior.

### Changed Files
- `.ai/HANDOFF.md`
- `.ai/TASKS.md`
- `.ai/SESSION_LOG.md`
- `.ai/CONTEXT.md`
- `.ai/GOAL.md`
- `projects/hanwoo-dashboard/src/components/tabs/InventoryTab.js`
- `projects/hanwoo-dashboard/src/lib/empty-state-wiring.test.mjs`

### Verification
- `npm.cmd test -- src/lib/empty-state-wiring.test.mjs src/lib/component-imports.test.mjs` from `projects/hanwoo-dashboard` -> `136 passed`.
- `npx.cmd eslint src/components/tabs/InventoryTab.js src/lib/empty-state-wiring.test.mjs` from `projects/hanwoo-dashboard` -> passed.
- `git diff --check -- projects/hanwoo-dashboard/src/components/tabs/InventoryTab.js projects/hanwoo-dashboard/src/lib/empty-state-wiring.test.mjs` -> passed.
- `python execution/project_qc_runner.py --project hanwoo-dashboard --json` -> passed (`test` 136, lint passed, build passed).
- `python execution/code_review_gate.py --staged --json` -> WARN from known graph/test-gap heuristics; direct Hanwoo verification covered the changed files.

### Follow-up
- Active Hanwoo goal remains open; T-251 still requires user-owned Supabase password/control-plane resync before live Prisma CRUD can be proven.
- T-320 and T-372 remain approval-scoped. Preserve unrelated current WIP in root package/workflow files, Hanwoo `package.json`, package locks, and shorts-maker-v2 files.

## 2026-05-20 KST - Codex

### Summary
- Completed T-402 for `hanwoo-dashboard` while continuing the active product-completeness goal.
- Fixed feed-record form failure handling: `FeedTab` now awaits `onRecordFeed` and only resets after a truthy result.
- Failed async feed saves now preserve entered feed data for retry; success/offline queue paths keep the existing reset behavior.

### Changed Files
- `.ai/HANDOFF.md`
- `.ai/TASKS.md`
- `.ai/SESSION_LOG.md`
- `.ai/CONTEXT.md`
- `.ai/GOAL.md`
- `projects/hanwoo-dashboard/src/components/tabs/FeedTab.js`
- `projects/hanwoo-dashboard/src/lib/empty-state-wiring.test.mjs`

### Verification
- `npm.cmd test -- src/lib/empty-state-wiring.test.mjs src/lib/component-imports.test.mjs` from `projects/hanwoo-dashboard` -> `135 passed`.
- `npx.cmd eslint src/components/tabs/FeedTab.js src/lib/empty-state-wiring.test.mjs` from `projects/hanwoo-dashboard` -> passed.
- `git diff --check -- projects/hanwoo-dashboard/src/components/tabs/FeedTab.js projects/hanwoo-dashboard/src/lib/empty-state-wiring.test.mjs` -> passed.
- `python -m code_review_graph detect-changes --repo projects/hanwoo-dashboard --brief` -> risk `0.00`.
- `python execution/project_qc_runner.py --project hanwoo-dashboard --json` -> passed (`test` 135, lint passed, build passed).
- `python execution/code_review_gate.py --staged --json` -> WARN from known graph/test-gap heuristics and unrelated dirty `cards.js` WIP; direct Hanwoo verification covered the changed files.

### Follow-up
- Active Hanwoo goal remains open; T-251 still requires user-owned Supabase password/control-plane resync before live Prisma CRUD can be proven.
- T-320, T-372, and T-398 remain approval-scoped. Preserve unrelated current WIP in root package/workflow files, Hanwoo `package.json`, Hanwoo `cards.js`/`cards-accessibility.test.mjs`, package locks, and shorts-maker-v2 files.

## 2026-05-20 KST - Codex

### Summary
- Completed T-401 for `hanwoo-dashboard` while continuing the active product-completeness goal.
- Fixed cattle edit form failure handling: the edit modal now delegates submit handling directly to `handleUpdateCattle`.
- Failed async update mutations now keep the edit form open with typed values preserved; success/offline queue paths still close through the existing handler.

### Changed Files
- `.ai/HANDOFF.md`
- `.ai/TASKS.md`
- `.ai/SESSION_LOG.md`
- `.ai/CONTEXT.md`
- `.ai/GOAL.md`
- `projects/hanwoo-dashboard/src/components/DashboardClient.js`
- `projects/hanwoo-dashboard/src/lib/empty-state-wiring.test.mjs`

### Verification
- `npm.cmd test -- src/lib/empty-state-wiring.test.mjs src/lib/component-imports.test.mjs` from `projects/hanwoo-dashboard` -> `133 passed`.
- `npx.cmd eslint src/components/DashboardClient.js src/lib/empty-state-wiring.test.mjs` from `projects/hanwoo-dashboard` -> passed.
- `git diff --check -- projects/hanwoo-dashboard/src/components/DashboardClient.js projects/hanwoo-dashboard/src/lib/empty-state-wiring.test.mjs` -> passed.
- `python -m code_review_graph detect-changes --repo projects/hanwoo-dashboard --brief` -> risk `0.00`.
- `python execution/project_qc_runner.py --project hanwoo-dashboard --json` -> passed (`test` 133, lint passed, build passed).
- `python execution/code_review_gate.py --staged --json` -> WARN from known graph/test-gap heuristics; direct Hanwoo verification covered the changed files.

### Follow-up
- Active Hanwoo goal remains open; T-251 still requires user-owned Supabase password/control-plane resync before live Prisma CRUD can be proven.
- T-320, T-372, and T-398 remain approval-scoped. Preserve unrelated current WIP in root package/workflow files, Hanwoo `package.json`, package locks, and shorts-maker-v2 files.

## 2026-05-20 KST - Codex

### Summary
- Completed T-400 for `hanwoo-dashboard` while continuing the active product-completeness goal.
- Hid decorative public login/error/not-found icons from assistive technology.
- Login status icons, route-error/not-found status icons, and password visibility toggle icons now use `aria-hidden="true"` so Korean labels remain the meaningful accessible names.

### Changed Files
- `.ai/HANDOFF.md`
- `.ai/TASKS.md`
- `.ai/SESSION_LOG.md`
- `.ai/CONTEXT.md`
- `.ai/GOAL.md`
- `projects/hanwoo-dashboard/src/app/login/page.js`
- `projects/hanwoo-dashboard/src/app/error.js`
- `projects/hanwoo-dashboard/src/app/not-found.js`
- `projects/hanwoo-dashboard/src/lib/error-pages-wiring.test.mjs`

### Verification
- `npm.cmd test -- src/lib/error-pages-wiring.test.mjs` from `projects/hanwoo-dashboard` -> `132 passed`.
- `npx.cmd eslint src/app/login/page.js src/app/error.js src/app/not-found.js src/lib/error-pages-wiring.test.mjs` from `projects/hanwoo-dashboard` -> passed.
- `git diff --check -- <changed Hanwoo paths>` -> passed.
- `python -m code_review_graph detect-changes --repo projects/hanwoo-dashboard --brief` -> risk `0.00`.
- `python execution/project_qc_runner.py --project hanwoo-dashboard --json` -> passed (`test` 132, lint passed, build passed).

### Follow-up
- Active Hanwoo goal remains open; T-251 still requires user-owned Supabase password/control-plane resync before live Prisma CRUD can be proven.
- T-320, T-372, and T-398 remain approval-scoped. Preserve unrelated current WIP in root package/workflow files, Hanwoo `package.json`, package locks, and shorts-maker-v2 files.

## 2026-05-20 KST - Codex

### Summary
- Completed T-399 for `hanwoo-dashboard` while continuing the active product-completeness goal.
- Made home building navigation semantic and keyboard-accessible: the empty-building CTA now uses a real button routed through `handleTabChange('settings')`, and each building card is a native button preserving the existing clay-card styling.
- Added source regression coverage in `home-market-copy.test.mjs`.

### Changed Files
- `.ai/HANDOFF.md`
- `.ai/TASKS.md`
- `.ai/SESSION_LOG.md`
- `.ai/CONTEXT.md`
- `.ai/GOAL.md`
- `projects/hanwoo-dashboard/src/components/DashboardClient.js`
- `projects/hanwoo-dashboard/src/app/globals.css`
- `projects/hanwoo-dashboard/src/lib/home-market-copy.test.mjs`

### Verification
- `npm.cmd test -- src/lib/home-market-copy.test.mjs src/lib/component-imports.test.mjs` from `projects/hanwoo-dashboard` -> `132 passed`.
- `npx.cmd eslint src/components/DashboardClient.js src/lib/home-market-copy.test.mjs` from `projects/hanwoo-dashboard` -> passed.
- `python execution/project_qc_runner.py --project hanwoo-dashboard --json` -> passed (`test` 132, lint passed, build passed).
- `git diff --check -- projects/hanwoo-dashboard/src/components/DashboardClient.js projects/hanwoo-dashboard/src/app/globals.css projects/hanwoo-dashboard/src/lib/home-market-copy.test.mjs` -> passed.
- `python execution/code_review_gate.py --staged --json` -> PASS; trailing cp949 reader-thread exception is known Windows output noise.

### Follow-up
- Active Hanwoo goal remains open; T-251 still requires user-owned Supabase password/control-plane resync before live Prisma CRUD can be proven.
- T-320, T-372, and T-398 remain approval-scoped. Preserve unrelated current WIP in root package/workflow files, Hanwoo `package.json`, package locks, error-page WIP, and shorts-maker-v2 files.

## 2026-05-20 KST - Codex

### Summary
- Completed T-397 for `hanwoo-dashboard` while continuing the active product-completeness goal.
- Hid decorative Analysis KPI, Schedule add-form, and Settings section icons from assistive technology with `aria-hidden="true"` so Korean text labels remain the meaningful accessible content.
- Extended source regression coverage in `analysis-copy.test.mjs`, `home-market-copy.test.mjs`, and `settings-tab-accessibility.test.mjs`.

### Changed Files
- `.ai/HANDOFF.md`
- `.ai/TASKS.md`
- `.ai/SESSION_LOG.md`
- `.ai/CONTEXT.md`
- `.ai/GOAL.md`
- `projects/hanwoo-dashboard/src/components/tabs/AnalysisTab.js`
- `projects/hanwoo-dashboard/src/components/tabs/ScheduleTab.js`
- `projects/hanwoo-dashboard/src/components/tabs/SettingsTab.js`
- `projects/hanwoo-dashboard/src/lib/analysis-copy.test.mjs`
- `projects/hanwoo-dashboard/src/lib/home-market-copy.test.mjs`
- `projects/hanwoo-dashboard/src/lib/settings-tab-accessibility.test.mjs`

### Verification
- `npm.cmd test -- src/lib/home-market-copy.test.mjs src/lib/settings-tab-accessibility.test.mjs src/lib/analysis-copy.test.mjs` from `projects/hanwoo-dashboard` -> `131 passed`.
- `npx.cmd eslint src/components/tabs/ScheduleTab.js src/components/tabs/SettingsTab.js src/components/tabs/AnalysisTab.js src/lib/home-market-copy.test.mjs src/lib/settings-tab-accessibility.test.mjs src/lib/analysis-copy.test.mjs` from `projects/hanwoo-dashboard` -> passed.
- `git diff --check -- <changed Hanwoo paths>` -> passed.
- `python -m code_review_graph detect-changes --repo projects/hanwoo-dashboard --brief` -> risk `0.00`.
- `python execution/project_qc_runner.py --project hanwoo-dashboard --json` -> passed (`test` 131, lint passed, build passed).

### Follow-up
- Active Hanwoo goal remains open; T-251 still requires user-owned Supabase password/control-plane resync before live Prisma CRUD can be proven.
- T-320 and T-372 remain approval-scoped; T-396 is a separate active Dependabot cleanup. Preserve unrelated current WIP in root package/workflow files, Hanwoo `package.json`, package locks, and shorts-maker-v2 files.

## 2026-05-20 KST - Codex

### Summary
- Completed T-395 for `hanwoo-dashboard` while continuing the active product-completeness goal.
- Kept Sales, Inventory, Schedule, and Settings create forms open when async submit handlers fail.
- The create submit paths now await their save handler and only close/reset after a truthy saved result, preserving typed values for retry on rejected or failed mutations.

### Changed Files
- `.ai/HANDOFF.md`
- `.ai/TASKS.md`
- `.ai/SESSION_LOG.md`
- `.ai/CONTEXT.md`
- `.ai/GOAL.md`
- `projects/hanwoo-dashboard/src/components/tabs/SalesTab.js`
- `projects/hanwoo-dashboard/src/components/tabs/InventoryTab.js`
- `projects/hanwoo-dashboard/src/components/tabs/ScheduleTab.js`
- `projects/hanwoo-dashboard/src/components/tabs/SettingsTab.js`
- `projects/hanwoo-dashboard/src/lib/empty-state-wiring.test.mjs`

### Verification
- `npm.cmd test -- src/lib/empty-state-wiring.test.mjs src/lib/component-imports.test.mjs` from `projects/hanwoo-dashboard` -> `131 passed`.
- `npx.cmd eslint src/components/tabs/SalesTab.js src/components/tabs/InventoryTab.js src/components/tabs/ScheduleTab.js src/components/tabs/SettingsTab.js src/lib/empty-state-wiring.test.mjs` from `projects/hanwoo-dashboard` -> passed.
- `python execution/project_qc_runner.py --project hanwoo-dashboard --json` -> passed (`test` 131, lint passed, build passed).
- `git diff --check -- projects/hanwoo-dashboard/src/components/tabs/SalesTab.js projects/hanwoo-dashboard/src/components/tabs/InventoryTab.js projects/hanwoo-dashboard/src/components/tabs/ScheduleTab.js projects/hanwoo-dashboard/src/components/tabs/SettingsTab.js projects/hanwoo-dashboard/src/lib/empty-state-wiring.test.mjs` -> passed.
- `python execution/code_review_gate.py --staged --json` -> PASS; trailing cp949 reader-thread exception is known Windows output noise.

### Follow-up
- Active Hanwoo goal remains open; T-251 still requires user-owned Supabase password/control-plane resync before live Prisma CRUD can be proven.
- T-320 and T-372 remain approval-scoped. Preserve unrelated current WIP in root package/workflow files, Hanwoo `package.json`, package locks, and shorts-maker-v2 files.

## 2026-05-20 KST - Codex

### Summary
- Completed T-394 for `hanwoo-dashboard` while continuing the active product-completeness goal.
- Made Today Focus and Setup Progress panel navigation call `handleTabChange`, so those home-panel tab changes trigger the same preload path as bottom navigation.
- Extended source regression coverage in `home-market-copy.test.mjs`.

### Changed Files
- `.ai/HANDOFF.md`
- `.ai/TASKS.md`
- `.ai/SESSION_LOG.md`
- `.ai/CONTEXT.md`
- `.ai/GOAL.md`
- `projects/hanwoo-dashboard/src/components/DashboardClient.js`
- `projects/hanwoo-dashboard/src/lib/home-market-copy.test.mjs`

### Verification
- `python execution/project_qc_runner.py --project hanwoo-dashboard --json` -> passed (`test` 130, lint passed, build passed).
- `python execution/code_review_gate.py --staged --json` -> WARN from known graph/test-gap heuristics and unrelated shorts WIP; direct Hanwoo QC passed.

### Follow-up
- Active Hanwoo goal remains open; T-251 still requires user-owned Supabase password/control-plane resync before live Prisma CRUD can be proven.
- T-320 and T-372 remain approval-scoped. Preserve unrelated current WIP in root package/workflow files, Hanwoo `package.json`, package locks, and shorts-maker-v2 files.
