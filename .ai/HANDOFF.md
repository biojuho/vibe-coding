# HANDOFF - AI Context Relay

> See `SESSION_LOG.md` for recent session history and `DECISIONS.md` for stable architecture decisions.

## Current Addendum

| Field | Value |
|---|---|
| Date | 2026-06-15 |
| Tool | Claude Code (Sonnet 4.6) |
| Work | **자율 품질 루프 — 12 commits (context resumed)**: (1) SMV2-CV001/CV002: CTA 금지어 대소문자 무관 검출 + run() 4-tuple 반환 + degraded_steps 표면화 (index race로 `8a81a801`에 흡수); (2) BTX-JP001: `_fetch_post_detail` `page.goto()` 예외 → `_JobplanetScrapeFailure(network_error)` + tests 4건; (3) asyncio.get_event_loop() → asyncio.run() 현대화; (4) hanwoo `<a>` → `<Link>` subscription/error.js; (5) DiagnosticsPageClient 불필요한 requestId 증가 제거; (6) qc_step bare `except` → `ImportError`; (7) hanwoo infra-layer-coverage 84→87건 (health route, building/feed/schedule 검증); (8) SMV2-RS001 후속: `_attach_audio` 구현 커밋 누락 복구 (CI AttributeError 차단). |
| Next Priorities | (a) 품질 루프 계속: hanwoo inventory/farm-settings 검증 커버리지, blind-to-x draft_cache.py/dedup.py 나머지 bare-except, shorts-maker-v2 tts_step.py; (b) `git push origin main` (user action — 1175+ commits ahead); (c) T-251 Supabase 비밀번호 리셋 (user action) |

| Field | Value |
|---|---|
| Date | 2026-06-15 |
| Tool | Claude Code (Sonnet 4.6) |
| Work | **Multi-project quality sweep — 8 commits**: (1) BTX-DG001/002: 4× bare `except Exception: pass` → `logger.debug` in `draft_generator.py` + 2 regression tests; (2) GC-001: guard empty `response.candidates` in `google_client.generate_image` + test; (3) BTX-SC001: jobplanet HTTP 500 guard + fmkorea/ppomppu debug logging + JP-001 test; (4) HW-C01: CalvingTab `getPregnancyDateTime` null guard (`new Date(null)=epoch` bug) + 3 tests; (5) HW-TF01: `estimateDailyFeedConsumptionKg` clamp `lookbackDays≤0` to 30 + shorts sync.py logger; (6) BTX-SB001: `style_bandit.get_arm_stats` alpha+beta==0 ZeroDivisionError guard + test; (7) SM-OBS001: 3× `except pass` → debug log in edge_tts_client/broll_overlay/visual_mixin; (8) BTX-OBS002: KOTE classifier + scoring_6d weight-load fallback debug logging. |
| Next Priorities | (a) **user action required**: `git push origin main` (many commits ahead); (b) Continue quality sweep: remaining `except Exception: pass` in `blind-to-x/pipeline/cost_db.py`, `dedup.py`, `draft_cache.py`; (c) hanwoo-dashboard CalvingTab/ScheduleTab sort patterns checked — focus shifts to `NotificationModal` and `DashboardClient` service layer; (d) T-251 Supabase DB password reset still user-owned blocker |

| Field | Value |
|---|---|
| Date | 2026-06-14 |
| Tool | Claude Code (Sonnet 4.6) |
| Work | **hanwoo-dashboard product quality uplift (3rd session)**: (1) ScheduleTab: "← 오늘로" conditional nav button appears when user is on a different month; (2) InventoryTab: `useMemo` lowStockCount + "부족 경고 N건" summary chip above item list; (3) Subscription page: 6-feature benefits grid (AI insight/profitability/market price/Excel/alerts/sync) above payment widget for conversion. Commits: e8052c93, f2922569. Tests: 542/542 green. Lint clean. |
| Next Priorities | (a) **user action required** T-251: Supabase DB password reset (Supabase Dashboard > Project Settings > Database) then update `projects/hanwoo-dashboard/.env`; (b) **user action required**: `git push origin main` (924+ commits ahead); (c) Vercel project setup + GitHub Secrets (`VERCEL_TOKEN`, `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID_HANWOO`) + env vars (`DATABASE_URL`, `AUTH_SECRET`, `AUTH_URL`, `NEXTAUTH_URL`, `AUTH_TRUST_HOST=true`); (d) Continue product quality sweep — next areas: CattleForm validation UX, FeedTab summary stats, field mode testing |

| Field | Value |
|---|---|
| Date | 2026-06-14 |
| Tool | Claude Code (Sonnet 4.6) |
| Work | **A/B 품질 루프 5개 커밋**: (1) T-AB001 `hook_score` FAIL/MEDIOCRE/GOOD/EXCELLENT 루브릭 + 금지 오프너 목록 (2) T-AB002 `flow_score`/`cta_score` 기준 구체화 (3) hook_rules_ko `script_prompts.py` YAML과 동기화 (4) T-AB003 blind-to-x `_FORBIDDEN_TONE_PATTERNS` 인플루언서 슬랭 3개 추가 + 회귀 테스트 (5) 동기화 검증 테스트 8개. **BIOJUHO-Projects PR#257**: Self-Review Checklist PASS (테스트 2개 추가), QA 문법 오류 수정 완료. |
| Next Priorities | (a) **user auth 필요**: `git push origin main` (b) **user auth 필요**: `gh pr merge 10 --repo biojuho/joolife` (Netlify PR#10 green), (c) BIOJUHO-Projects npm audit `@grpc/grpc-js` 취약점: firebase 트랜지티브 dep, `npm install --prefix apps/desci-platform/frontend` 실행 후 lock file 갱신 필요, (d) `pull-requests: write` 권한 승인 시 pr-self-review.yml 수정 가능, (e) hanwoo T-251 Supabase 자격증명 재설정은 사용자가 직접 필요 |

| Field | Value |
|---|---|
| Date | 2026-06-14 |
| Tool | Claude Code (Sonnet 4.6) |
| Work | **hanwoo-dashboard product quality uplift** (3 commits: 5bfa2e62, 4b004e6c, prior): (1) AnalysisTab market price comparison — grade distribution + recent 3 sales vs KAPE per-kg price, DashboardClient now passes `marketPrice` prop; (2) Fixed `record.auctionLocation` dead field ref in SalesTab (field never in schema), wrapped 4 DashboardClient mutation handlers (handleCreateEvent/handleToggleEvent/handleCreateSale/handleRecordFeed) with try-catch matching handleAddCattle pattern, updated source-grep tests; (3) Added `export const viewport` to layout.js (Next.js 14+ requirement, themeColor #3E2F1C/#1a1814, maximumScale 5 for accessibility). Tests: 541/541 all passing. |
| Next Priorities | Product launch readiness: (a) T-251 Supabase DB password reset still user-owned blocker; (b) push 924+ commits to origin needs explicit user authorization; (c) Vercel project setup + GitHub Secrets still needed; (d) Next: look at performance improvements, remaining empty states, or other product gaps. |

| Field | Value |
|---|---|
| Date | 2026-06-14 |
| Tool | Codex |
| Work | **T-2685 approval phase reference breakdown**. Continued under the dirty-handoff boundary after T-2684. The launch prompt checklist now adds `Approval phase references`, listing each approval phase's dirty reference total plus unique coverage and overlap refs, so the `phase refs 541` aggregate can be audited without opening `.tmp/approval-execution-matrix-current.json`. |
| Next Priorities | Verification passed refresh-current-evidence focused pytest (`130 passed` with `-o addopts=`), Ruff check, Ruff format check (`2 files already formatted`), `py_compile`, live `refresh_current_evidence.py --root . --timeout 360 --json` with all steps `ok`, checklist evidence showing `Approval phase references: ... unique coverage 457/457, overlap refs 84`, and T-2685 A/B decision `adopt_candidate` (`score_delta=0.8`, output `.tmp/ab-decision-t2685-approval-phase-reference-breakdown.json`). Final sanity check observed concurrent workspace movement to head `34af7605` with staged files (`staged 58`) and selector now `candidate / project_qc_refresh`; this run did not perform staging, commit, push, revert, live Prisma/T-251 retry, cleanup apply, or `update_goal`. Completion audit remains `incomplete` (`5/15` complete, `10` blocked). Next safe step is to handle the current `project_qc_refresh` candidate or resolve the staged/dirty handoff boundary without disturbing unrelated staged work. |

| Field | Value |
|---|---|
| Date | 2026-06-14 |
| Tool | Codex |
| Work | **T-2684 approval phase coverage reference totals**. Continued under the dirty-handoff boundary after T-2683. The launch prompt checklist now appends unique dirty-path coverage and phase-reference totals to `Approval phases`, separating true coverage (`457/457`) from overlapping phase references (`541`) so the scoped authorization boundary is easier to audit. |
| Next Priorities | Verification passed refresh-current-evidence focused pytest (`128 passed` with `-o addopts=`), Ruff check, Ruff format check (`2 files already formatted`), `py_compile`, live `refresh_current_evidence.py --root . --timeout 360 --json` with all steps `ok`, checklist evidence showing `Approval phases: ... coverage 457/457, phase refs 541`, and T-2684 A/B decision `adopt_candidate` (`score_delta=0.8`, output `.tmp/ab-decision-t2684-approval-phase-coverage-reference-totals.json`). Selector remains `dirty_worktree_handoff_current`; completion audit remains `incomplete` (`6/15` complete, `9` blocked). Boundary remains blocked-only: no product source edit, real stage, commit, push, revert, live Prisma/T-251 retry, cleanup apply, or `update_goal` was performed. Continue only after explicit scoped staging/commit authorization, explicit push/user push, Supabase credential reset for T-251, or another distinct handoff-only/tooling evidence gap. |

| Field | Value |
|---|---|
| Date | 2026-06-14 |
| Tool | Codex |
| Work | **T-2684 approval phase coverage reference totals**. Continued under the dirty-handoff boundary after T-2683/T-2682. The launch prompt checklist now appends unique approval coverage and phase-reference totals to `Approval phases`, clarifying that phase dirty counts can overlap while current dirty-path coverage is complete. |
| Next Priorities | Verification passed refresh-current-evidence focused pytest (`128 passed` with `-o addopts=`), Ruff check, Ruff format check (`2 files already formatted`), `py_compile`, path-limited `git diff --check`, live `refresh_current_evidence.py --root . --timeout 360 --json` with all steps `ok`, checklist evidence showing `Approval phases: ... omitted 5 phases/113 dirty/44 tokens; coverage 457/457, phase refs 541`, and T-2684 A/B decision `adopt_candidate` (`score_delta=0.8`, output `.tmp/ab-decision-t2684-approval-phase-coverage-reference-totals.json`). Selector remains `dirty_worktree_handoff_current`; completion audit remains `incomplete` (`6/15` complete, `9` blocked). Boundary remains blocked-only: no product source edit, real stage, commit, push, revert, live Prisma/T-251 retry, cleanup apply, or `update_goal` was performed. Continue only after explicit scoped staging/commit authorization, explicit push/user push, Supabase credential reset for T-251, or another distinct handoff-only/tooling evidence gap. |

| Field | Value |
|---|---|
| Date | 2026-06-14 |
| Tool | Codex |
| Work | **T-2683 approval phase token summary**. Continued under the dirty-handoff boundary after T-2682. The launch prompt checklist now adds `Approval phase tokens`, listing representative approval tokens for the visible dirty approval phases so the phase totals can be acted on without opening `.tmp/approval-execution-matrix-current.json`. |
| Next Priorities | Verification passed refresh-current-evidence focused pytest (`127 passed` with `-o addopts=`), Ruff check, Ruff format check (`2 files already formatted`), `py_compile`, live `refresh_current_evidence.py --root . --timeout 360 --json` with all steps `ok`, checklist evidence showing `Approval phase tokens: phase0_context_relay: APPROVE_AI_CONTEXT_RELAY_UPDATE; phase1_loop_tooling: ...; phase2_blind_to_x_dirty_product_paths: ...`, and T-2683 A/B decision `adopt_candidate` (`score_delta=1.3333333333333333`, output `.tmp/ab-decision-t2683-approval-phase-token-summary.json`). Selector remains `dirty_worktree_handoff_current`; completion audit remains `incomplete` (`6/15` complete, `9` blocked). Boundary remains blocked-only: no product source edit, real stage, commit, push, revert, live Prisma/T-251 retry, cleanup apply, or `update_goal` was performed. Continue only after explicit scoped staging/commit authorization, explicit push/user push, Supabase credential reset for T-251, or another distinct handoff-only/tooling evidence gap. |

| Field | Value |
|---|---|
| Date | 2026-06-14 |
| Tool | Codex |
| Work | **T-2682 approval phase omitted totals**. Continued under the dirty-handoff boundary after T-2681/T-2680. The launch prompt checklist now appends omitted approval phase counts plus omitted dirty/token totals to `Approval phases`, so the visible phase summary accounts for the full dirty inventory instead of showing only the first three phases. |
| Next Priorities | Verification passed refresh-current-evidence focused pytest (`126 passed` with `-o addopts=`), Ruff check, Ruff format check (`2 files already formatted`), `py_compile`, path-limited `git diff --check`, live `refresh_current_evidence.py --root . --timeout 360 --json` with all steps `ok`, checklist evidence showing `Approval phases: ... omitted 5 phases/113 dirty/44 tokens`, and T-2682 A/B decision `adopt_candidate` (`score_delta=0.42710280373113285`, output `.tmp/ab-decision-t2682-approval-phase-omitted-totals.json`). Selector remains `dirty_worktree_handoff_current`; completion audit remains `incomplete` (`6/15` complete, `9` blocked). Boundary remains blocked-only: no product source edit, real stage, commit, push, revert, live Prisma/T-251 retry, cleanup apply, or `update_goal` was performed. Continue only after explicit scoped staging/commit authorization, explicit push/user push, Supabase credential reset for T-251, or another distinct handoff-only/tooling evidence gap. |

| Field | Value |
|---|---|
| Date | 2026-06-14 |
| Tool | Codex |
| Work | **T-2681 one-line authorization option details**. Continued under the dirty-handoff boundary after T-2680. The launch prompt checklist now adds `One-line user option details`, mapping each visible one-line approval/stop token to its class, pathspec, and reason, so the user-facing approval surface is actionable without opening the scoped authorization menu JSON. |
| Next Priorities | Verification passed refresh-current-evidence focused pytest (`125 passed` with `-o addopts=`), Ruff check, Ruff format check (`2 files already formatted`), `py_compile`, live `refresh_current_evidence.py --root . --timeout 360 --json` with all steps `ok`, checklist evidence showing `One-line user option details: shown 6/6`, and T-2681 A/B decision `adopt_candidate` (`score_delta=1.3333333333333333`, output `.tmp/ab-decision-t2681-one-line-authorization-option-details.json`). Selector remains `dirty_worktree_handoff_current`; completion audit remains `incomplete` (`6/15` complete, `9` blocked). Boundary remains blocked-only: no product source edit, real stage, commit, push, revert, live Prisma/T-251 retry, cleanup apply, or `update_goal` was performed. Continue only after explicit scoped staging/commit authorization, explicit push/user push, Supabase credential reset for T-251, or another distinct handoff-only/tooling evidence gap. |

| Field | Value |
|---|---|
| Date | 2026-06-14 |
| Tool | Codex |
| Work | **T-2680 release commit encoding omitted count**. Continued under the dirty-handoff boundary after T-2679/T-2678. The launch prompt checklist now appends the omitted non-ASCII example count to `Release commit encoding`, so the current evidence shows `non-ascii 18` with five examples plus `omitted 13 non-ascii examples` instead of hiding the truncation. |
| Next Priorities | Verification passed refresh-current-evidence focused pytest (`125 passed` with `-o addopts=`), Ruff check, Ruff format check (`2 files already formatted`), `py_compile`, live `refresh_current_evidence.py --root . --timeout 360 --json` with all steps `ok`, checklist evidence showing `Release commit encoding ... omitted 13 non-ascii examples`, and T-2680 A/B decision `adopt_candidate` (`score_delta=0.18181818181818182`, output `.tmp/ab-decision-t2680-release-commit-encoding-omitted-count.json`). Selector remains `dirty_worktree_handoff_current`; completion audit remains `incomplete` (`6/15` complete, `9` blocked). Boundary remains blocked-only: no product source edit, real stage, commit, push, revert, live Prisma/T-251 retry, cleanup apply, or `update_goal` was performed. Continue only after explicit scoped staging/commit authorization, explicit push/user push, Supabase credential reset for T-251, or another distinct handoff-only/tooling evidence gap. |

| Field | Value |
|---|---|
| Date | 2026-06-14 |
| Tool | Codex |
| Work | **T-2677 release packet blocker summary**. Reissued the release-packet blocker summary under a collision-free task id after T-2675/T-2676 collided with concurrent browser QA log evidence artifacts. The launch prompt checklist now adds `Release packet blockers`, promoting the direct launch blockers from the detailed section into the Current Gate Summary: dirty worktree paths `457`, current-head Actions unavailable until explicit push/user push, and external/user-owned blocker `T-251`. |
| Next Priorities | Verification passed refresh-current-evidence focused pytest (`121 passed` with `-o addopts=`), Ruff check, Ruff format check (`2 files already formatted`), `py_compile`, live `refresh_current_evidence.py --root . --timeout 360 --json` with all steps `ok`, checklist evidence showing `Release packet blockers: dirty worktree paths 457; current-head Actions unavailable until explicit push/user push; external/user-owned blocker(s) T-251.`, and T-2677 A/B decision `adopt_candidate` (`score_delta=0.2222222222222222`, output `.tmp/ab-decision-t2677-release-packet-blocker-summary.json`). Selector remains `dirty_worktree_handoff_current`; completion audit remains `incomplete` (`6/15` complete, `9` blocked). Boundary remains blocked-only: no product source edit, real stage, commit, push, revert, live Prisma/T-251 retry, cleanup apply, or `update_goal` was performed. Continue only after explicit scoped staging/commit authorization, explicit push/user push, Supabase credential reset for T-251, or another distinct handoff-only/tooling evidence gap. |

| Field | Value |
|---|---|
| Date | 2026-06-14 |
| Tool | Codex |
| Work | **T-2676 browser QA log evidence summary**. Continued under the blocked dirty-handoff boundary after T-2674 and a local T-2675 task-id collision. The launch prompt checklist now adds `Browser QA log evidence`, showing project-level verified browser-click/log evidence counts beside screenshot coverage: `hanwoo-dashboard=verified-logs90/118`, `knowledge-dashboard=verified-logs15/16`, `suika-game-v2=verified-logs4/4`, and `word-chain=verified-logs13/13`. |
| Next Priorities | Verification passed refresh-current-evidence focused pytest (`121 passed` with `-o addopts=`), Ruff check, Ruff format check (`2 files already formatted`), `py_compile`, live `refresh_current_evidence.py --root . --timeout 360 --json` with all steps `ok`, checklist evidence showing the new `Browser QA log evidence` line, and T-2676 browser-log A/B decision `adopt_candidate` (`score_delta=0.2222222222222222`, output `.tmp/ab-decision-t2676-browser-qa-log-evidence-summary.json`). Note: separate release-packet blocker manifests/decisions also occupy T-2675/T-2676, so checklist latest-decision summary may mention `decision files 2`; use the explicit browser-log artifact paths above for this slice. Selector remains `dirty_worktree_handoff_current`; completion audit remains `incomplete` (`6/15` complete, `9` blocked). Boundary remains blocked-only: no product source edit, real stage, commit, push, revert, live Prisma/T-251 retry, cleanup apply, or `update_goal` was performed. Continue only after explicit scoped staging/commit authorization, explicit push/user push, Supabase credential reset for T-251, or another distinct handoff-only/tooling evidence gap. |

| Field | Value |
|---|---|
| Date | 2026-06-14 |
| Tool | Codex |
| Work | **T-2674 release actions boundary summary**. Continued under the blocked dirty-handoff boundary after T-2673. The launch prompt checklist now appends the current-head boundary to `Release actions` when no current-head runs exist, so the same line explains that required workflows are missing while the branch is still `ahead 924/dirty 457`. Successful Actions summaries remain unchanged when runs exist. |
| Next Priorities | Verification passed refresh-current-evidence focused pytest (`118 passed` with `-o addopts=`), Ruff check, Ruff format check (`2 files already formatted`), `py_compile`, live `refresh_current_evidence.py --root . --timeout 360 --json` with all steps `ok`, checklist evidence showing `Release actions: ... current-head boundary ahead 924/dirty 457`, and T-2674 A/B decision `adopt_candidate` (`score_delta=0.2222222222222222`, output `.tmp/ab-decision-t2674-release-actions-boundary-summary.json`). Selector remains `dirty_worktree_handoff_current`; completion audit remains `incomplete` (`6/15` complete, `9` blocked). Boundary remains blocked-only: no product source edit, real stage, commit, push, revert, live Prisma/T-251 retry, cleanup apply, or `update_goal` was performed. Continue only after explicit scoped staging/commit authorization, explicit push/user push, Supabase credential reset for T-251, or another distinct handoff-only/tooling evidence gap. |

| Field | Value |
|---|---|
| Date | 2026-06-14 |
| Tool | Codex |
| Work | **T-2673 release commit encoding examples**. Continued under the blocked dirty-handoff boundary after T-2672. The launch prompt checklist now adds bounded non-ASCII commit examples to `Release commit encoding`, so Korean/ahead commit subject preservation is inspectable without opening the release packet while keeping health counts and compact example limits. Current checklist evidence shows `subjects 35, non-ascii 18, replacement chars 0, mojibake markers 0` plus five concrete non-ASCII commit examples with Korean text preserved. |
| Next Priorities | Verification passed refresh-current-evidence focused pytest (`116 passed` with `-o addopts=`), Ruff check, Ruff format check (`2 files already formatted`), `py_compile`, live `refresh_current_evidence.py --root . --timeout 360 --json` with all steps `ok`, checklist evidence showing `Release commit encoding` non-ASCII examples, and T-2673 A/B decision `adopt_candidate` (`score_delta=0.2`, output `.tmp/ab-decision-t2673-release-commit-encoding-examples.json`). Selector remains `dirty_worktree_handoff_current`; completion audit remains `incomplete` (`6/15` complete, `9` blocked). Boundary remains blocked-only: no product source edit, real stage, commit, push, revert, live Prisma/T-251 retry, cleanup apply, or `update_goal` was performed. Continue only after explicit scoped staging/commit authorization, explicit push/user push, Supabase credential reset for T-251, or another distinct handoff-only/tooling evidence gap. |

| Field | Value |
|---|---|
| Date | 2026-06-14 |
| Tool | Codex |
| Work | **T-2672 code review detail omitted preview wider**. Continued under the blocked dirty-handoff boundary after T-2671. The launch prompt checklist now keeps ten primary changed/test-gap files and expands code-review detail omitted previews to thirty entries before `omitted-more`, while preserving explicit small-limit omission behavior. Current checklist evidence shows the changed-file omitted preview through `projects/blind-to-x/scrapers/crawl4ai_extractor.py` and the gap-file omitted preview through `workspace/execution/smart_router.py`. |
| Next Priorities | Verification passed refresh-current-evidence focused pytest (`115 passed` with `-o addopts=`), Ruff check, Ruff format check (`2 files already formatted`), `py_compile`, live `refresh_current_evidence.py --root . --timeout 360 --json` with all steps `ok`, checklist evidence showing the wider `Code review gate detail` omitted previews, and T-2672 A/B decision `adopt_candidate` (`score_delta=0.2222222222222222`, output `.tmp/ab-decision-t2672-code-review-detail-omitted-preview-wider.json`). Selector remains `dirty_worktree_handoff_current`; completion audit remains `incomplete` (`6/15` complete, `9` blocked). Boundary remains blocked-only: no product source edit, real stage, commit, push, revert, live Prisma/T-251 retry, cleanup apply, or `update_goal` was performed. Continue only after explicit scoped staging/commit authorization, explicit push/user push, Supabase credential reset for T-251, or another distinct handoff-only/tooling evidence gap. |

| Field | Value |
|---|---|
| Date | 2026-06-14 |
| Tool | Codex |
| Work | **T-2671 release commit preview wider**. Continued under the blocked dirty-handoff boundary after T-2667/T-2670 evidence refreshes. The release authorization packet and launch prompt checklist now use a 35-commit default ahead-commit preview instead of 25, while preserving explicit compact limit behavior. Current checklist evidence shows `Release commits: shown 35/924` with ten more concrete ahead commits before `omitted 889 more`. |
| Next Priorities | Verification passed release authorization + refresh-current-evidence focused pytest (`137 passed` with `-o addopts=`), Ruff check, Ruff format check (`4 files already formatted`), `py_compile`, live `refresh_current_evidence.py --root . --timeout 360 --json` with all steps `ok`, checklist evidence showing `Release commits: shown 35/924`, and T-2671 A/B decision `adopt_candidate` (`score_delta=0.2`, output `.tmp/ab-decision-t2671-release-commit-preview-wider.json`). Selector remains `dirty_worktree_handoff_current`; completion audit remains `incomplete` (`6/15` complete, `9` blocked). Boundary remains blocked-only: no product source edit, real stage, commit, push, revert, live Prisma/T-251 retry, cleanup apply, or `update_goal` was performed. Continue only after explicit scoped staging/commit authorization, explicit push/user push, Supabase credential reset for T-251, or another distinct handoff-only/tooling evidence gap. |

| Field | Value |
|---|---|
| Date | 2026-06-14 |
| Tool | Codex |
| Work | **T-2667 code review detail omitted preview wider**. Continued under the blocked dirty-handoff boundary after T-2666. The launch prompt checklist now keeps ten primary changed/test-gap files in `Code review gate detail:` and expands omitted changed/gap examples to twenty before `omitted-more`, while preserving explicit small-limit omission behavior. Current evidence shows changed omitted preview through `projects/blind-to-x/pipeline/cli.py`, gap omitted preview through `workspace/execution/bgm_downloader.py`, and latest A/B manifest/decision T-2667. |
| Next Priorities | Verification passed current refresh-current-evidence focused pytest (`114 passed` with `-o addopts=`), Ruff check, Ruff format check (`2 files already formatted`), `py_compile`, live `refresh_current_evidence.py --root . --timeout 360 --json` with all steps `ok`, checklist evidence showing expanded `Code review gate detail` omitted previews, latest A/B decision T-2667 `adopt_candidate` (`score_delta=0.2`, output `.tmp/ab-decision-t2667-code-review-detail-omitted-preview-wider.json`), and next A/B id T-2668. Selector remains `dirty_worktree_handoff_current`; completion audit remains `incomplete` (`6/15` complete, `9` blocked). Boundary remains blocked-only: no product source edit, real stage, commit, push, revert, live Prisma/T-251 retry, cleanup apply, or `update_goal` was performed. Continue only after explicit scoped staging/commit authorization, explicit push/user push, Supabase credential reset for T-251, or another distinct handoff-only/tooling evidence gap. |

| Field | Value |
|---|---|
| Date | 2026-06-14 |
| Tool | Codex |
| Work | **T-2666 A/B collision omitted preview wider**. Continued under the blocked dirty-handoff boundary after T-2665. The launch prompt checklist now keeps ten primary A/B manifest collision groups and expands the omitted collision-group examples to twenty before `omitted-more`, while preserving explicit small-limit omission behavior. Current evidence shows the omitted preview continuing through T-2143; a later refresh also generated T-2667 as the latest A/B manifest, newer than the effective handoff. |
| Next Priorities | Verification passed current refresh-current-evidence focused pytest (`114 passed` with `-o addopts=`), Ruff check, Ruff format check (`2 files already formatted`), `py_compile`, live `refresh_current_evidence.py --root . --timeout 360 --json` with all steps `ok`, checklist evidence showing expanded `A/B manifest collisions` omitted preview through T-2143, T-2666 A/B decision `adopt_candidate` (`score_delta=0.2`, output `.tmp/ab-decision-t2666-ab-collision-omitted-preview-wider.json`), and latest checklist A/B decision T-2667 `adopt_candidate` (`score_delta=0.2`, output `.tmp/ab-decision-t2667-code-review-detail-omitted-preview-wider.json`) with next A/B id T-2668. Selector remains `dirty_worktree_handoff_current`; completion audit remains `incomplete` (`6/15` complete, `9` blocked). Boundary remains blocked-only: no product source edit, real stage, commit, push, revert, live Prisma/T-251 retry, cleanup apply, or `update_goal` was performed. Continue only after explicit scoped staging/commit authorization, explicit push/user push, Supabase credential reset for T-251, or another distinct handoff-only/tooling evidence gap. |

| Field | Value |
|---|---|
| Date | 2026-06-14 |
| Tool | Codex |
| Work | **T-2665 A/B collision summary wider preview**. Continued under the blocked dirty-handoff boundary after T-2664. The launch prompt checklist now shows ten A/B manifest collision groups in the primary `A/B manifest collisions:` line instead of three, while preserving explicit small-limit omission behavior. Current evidence shows `shown 10/59` with concrete collision filenames and latest A/B manifest/decision T-2665. |
| Next Priorities | Verification passed current refresh-current-evidence focused pytest (`113 passed` with `-o addopts=`), Ruff check, Ruff format check (`2 files already formatted`), `py_compile`, live `refresh_current_evidence.py --root . --timeout 360 --json` with all steps `ok`, checklist evidence showing `A/B manifest collisions: shown 10/59`, latest A/B decision T-2665 `adopt_candidate` (`score_delta=0.2`, output `.tmp/ab-decision-t2665-ab-collision-summary-wider-preview.json`), and next A/B id T-2666. Selector remains `dirty_worktree_handoff_current`; completion audit remains `incomplete` (`6/15` complete, `9` blocked). Boundary remains blocked-only: no product source edit, real stage, commit, push, revert, live Prisma/T-251 retry, cleanup apply, or `update_goal` was performed. Continue only after explicit scoped staging/commit authorization, explicit push/user push, Supabase credential reset for T-251, or another distinct handoff-only/tooling evidence gap. |

| Field | Value |
|---|---|
| Date | 2026-06-14 |
| Tool | Codex |
| Work | **T-2664 completion blocker action full preview**. Continued under the blocked dirty-handoff boundary after T-2663. The launch prompt checklist now shows all nine current completion blocker actions in the primary `Completion blocker actions:` line instead of pushing target-project actions behind `omitted 4`. Explicit small-limit omission behavior remains covered by focused tests. Current evidence shows the full action list and latest A/B manifest/decision T-2664. |
| Next Priorities | Verification passed current refresh-current-evidence focused pytest (`111 passed` with `-o addopts=`), Ruff check, Ruff format check (`2 files already formatted`), `py_compile`, live `refresh_current_evidence.py --root . --timeout 360 --json` with all steps `ok`, checklist evidence showing full `Completion blocker actions` with no omitted action tail, latest A/B decision T-2664 `adopt_candidate` (`score_delta=0.2`, output `.tmp/ab-decision-t2664-completion-blocker-action-full-preview.json`), and next A/B id T-2665. Selector remains `dirty_worktree_handoff_current`; completion audit remains `incomplete` (`6/15` complete, `9` blocked). Boundary remains blocked-only: no product source edit, real stage, commit, push, revert, live Prisma/T-251 retry, cleanup apply, or `update_goal` was performed. Continue only after explicit scoped staging/commit authorization, explicit push/user push, Supabase credential reset for T-251, or another distinct handoff-only/tooling evidence gap. |

| Field | Value |
|---|---|
| Date | 2026-06-14 |
| Tool | Codex |
| Work | **T-2663 code review impact wider preview**. Continued under the blocked dirty-handoff boundary after T-2662. The launch prompt checklist now shows ten impacted files and ten impacted nodes in the primary `Code review gate impact:` line instead of three each, while preserving explicit small-limit omission behavior. Current evidence shows `impacted file preview shown 10/166`, `impacted node preview shown 10/500`, and latest A/B manifest/decision T-2663. |
| Next Priorities | Verification passed current refresh-current-evidence focused pytest (`110 passed` with `-o addopts=`), Ruff check, Ruff format check (`2 files already formatted`), `py_compile`, live `refresh_current_evidence.py --root . --timeout 360 --json` with all steps `ok`, checklist evidence showing `Code review gate impact: ... impacted file preview shown 10/166 ... impacted node preview shown 10/500`, latest A/B decision T-2663 `adopt_candidate` (`score_delta=0.2`, output `.tmp/ab-decision-t2663-code-review-impact-wider-preview.json`), and next A/B id T-2664. Selector remains `dirty_worktree_handoff_current`; completion audit remains `incomplete` (`6/15` complete, `9` blocked). Boundary remains blocked-only: no product source edit, real stage, commit, push, revert, live Prisma/T-251 retry, cleanup apply, or `update_goal` was performed. Continue only after explicit scoped staging/commit authorization, explicit push/user push, Supabase credential reset for T-251, or another distinct handoff-only/tooling evidence gap. |

| Field | Value |
|---|---|
| Date | 2026-06-14 |
| Tool | Codex |
| Work | **T-2662 code review detail wider preview**. Continued under the blocked dirty-handoff boundary after T-2661. The launch prompt checklist now shows ten changed files and ten test-gap files in the primary `Code review gate detail:` line instead of three each, while preserving explicit small-limit omission behavior. Current evidence shows `changed top shown 10/113`, `gap files shown 10/42`, and latest A/B manifest/decision T-2662. |
| Next Priorities | Verification passed current refresh-current-evidence focused pytest (`109 passed` with `-o addopts=`), Ruff check, Ruff format check (`2 files already formatted`), `py_compile`, live `refresh_current_evidence.py --root . --timeout 360 --json` with all steps `ok`, checklist evidence showing `Code review gate detail: ... changed top shown 10/113 ... gap files shown 10/42`, latest A/B decision T-2662 `adopt_candidate` (`score_delta=0.2`, output `.tmp/ab-decision-t2662-code-review-detail-wider-preview.json`), and next A/B id T-2663. Selector remains `dirty_worktree_handoff_current`; completion audit remains `incomplete` (`6/15` complete, `9` blocked). Boundary remains blocked-only: no product source edit, real stage, commit, push, revert, live Prisma/T-251 retry, cleanup apply, or `update_goal` was performed. Continue only after explicit scoped staging/commit authorization, explicit push/user push, Supabase credential reset for T-251, or another distinct handoff-only/tooling evidence gap. |

| Field | Value |
|---|---|
| Date | 2026-06-14 |
| Tool | Codex |
| Work | **T-2661 code review untracked full preview**. Continued under the blocked dirty-handoff boundary after T-2660. The launch prompt checklist now shows all current graph-relevant untracked file paths in the primary `Code review gate untracked:` line by raising the default preview limit to the current 16-file scale. Explicit small-limit omission behavior remains covered by focused tests. Current evidence shows `shown 16/16` and latest A/B manifest/decision T-2661. |
| Next Priorities | Verification passed current refresh-current-evidence focused pytest (`108 passed` with `-o addopts=`), Ruff check, Ruff format check (`2 files already formatted`), `py_compile`, path-limited `git diff --check` with CRLF warnings only, live `refresh_current_evidence.py --root . --timeout 360 --json` with all steps `ok`, checklist evidence showing `Code review gate untracked: shown 16/16`, latest A/B decision T-2661 `adopt_candidate` (`score_delta=0.2`, output `.tmp/ab-decision-t2661-code-review-untracked-full-preview.json`), and next A/B id T-2662. Selector remains `dirty_worktree_handoff_current`; completion audit remains `incomplete` (`6/15` complete, `9` blocked). Boundary remains blocked-only: no product source edit, real stage, commit, push, revert, live Prisma/T-251 retry, cleanup apply, or `update_goal` was performed. Continue only after explicit scoped staging/commit authorization, explicit push/user push, Supabase credential reset for T-251, or another distinct handoff-only/tooling evidence gap. |

| Field | Value |
|---|---|
| Date | 2026-06-14 |
| Tool | Codex |
| Work | **T-2660 code review priority full preview**. Continued under the blocked dirty-handoff boundary after T-2659. The launch prompt checklist now shows all current code-review priority symbols in the primary `Code review gate priorities:` line by raising the default preview limit to the current 10-priority scale. Explicit small-limit omission behavior remains covered by focused tests. Current evidence shows `shown 10/10` and latest A/B manifest/decision T-2660. |
| Next Priorities | Verification passed current refresh-current-evidence focused pytest (`107 passed` with `-o addopts=`), Ruff check, Ruff format check (`2 files already formatted`), `py_compile`, path-limited `git diff --check`, live `refresh_current_evidence.py --root . --timeout 360 --json` with all steps `ok`, checklist evidence showing `Code review gate priorities: shown 10/10`, latest A/B decision T-2660 `adopt_candidate` (`score_delta=0.2`, output `.tmp/ab-decision-t2660-code-review-priority-full-preview.json`), and next A/B id T-2661. Selector remains `dirty_worktree_handoff_current`; completion audit remains `incomplete` (`6/15` complete, `9` blocked). Boundary remains blocked-only: no product source edit, real stage, commit, push, revert, live Prisma/T-251 retry, cleanup apply, or `update_goal` was performed. Continue only after explicit scoped staging/commit authorization, explicit push/user push, Supabase credential reset for T-251, or another distinct handoff-only/tooling evidence gap. |

> T-1570 relay note: `f3f376a6` is the verified code baseline before this documentation relay. After this relay is committed, use live `python execution/session_orient.py --json` for the exact current HEAD/ahead count; the remaining boundaries should still be publish/current-head Actions plus user-owned Hanwoo T-251.

> T-1404 verification note: staged code-review gate returned advisory WARN (`risk_score=0.35`) from test-gap heuristics, covered by focused source-browser tests, CLI preflight tests, live click-through evidence, and blind-to-x project QC.

## Notes

- **T-251 (active blocker)**: Supabase database password desynchronization. User must reset password via Supabase Dashboard (Project Settings > Database), then update `projects/hanwoo-dashboard/.env`.
- **Origin sync**: Use live `python execution/session_orient.py --json` before acting. Current relay state has `main` ahead of origin and a dirty worktree; do not push without explicit authorization.
- Older addenda archived in `.ai/archive/HANDOFF_archive_2026-05-15.md` and `.ai/archive/HANDOFF_archive_2026-05-19.md`.
