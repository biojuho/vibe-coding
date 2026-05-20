# HANDOFF - AI Context Relay

> See `SESSION_LOG.md` for recent session history and `DECISIONS.md` for stable architecture decisions.

## Current Addendum

| Field | Value |
|---|---|
| Date | 2026-05-20 |
| Tool | Codex |
| Work | **T-383 completed**: continued Hanwoo product-completeness work by preventing raw client-side cattle mutation exceptions from leaking through operator-facing toasts. `handleAddCattle` and `handleUpdateCattle` now log diagnostics and show a safe Korean fallback description instead of `error.message`. `home-market-copy.test.mjs` guards the fallback and rejects `showError(errorTitle, error.message)`. Code commit `dd2bff4`. |
| Next Priorities | Verification passed: focused home/component tests passed (`127 passed`), targeted ESLint passed, full `project_qc_runner --project hanwoo-dashboard --json` passed (`test` 127, lint, build), path-limited `git diff --check` passed, and direct graph risk `0.00`. Staged/commit graph gate WARN came from dirty-WIP/test-gap heuristics while direct tests covered the committed files. Active Hanwoo goal remains open; T-251 remains external/user-owned Supabase control-plane resync. Preserve unrelated root monorepo/package-lock/shorts WIP plus dirty Hanwoo `package.json` unless explicitly authorized. |

| Field | Value |
|---|---|
| Date | 2026-05-20 |
| Tool | Codex |
| Work | **T-382 completed**: continued Hanwoo product-completeness work by replacing the financial chart header's broken `?` placeholder glyph with a real lucide `BarChart3` icon. The icon is decorative (`aria-hidden`) and `analysis-copy.test.mjs` now guards against the placeholder glyph returning. Code commit `ba1f757`. |
| Next Priorities | Verification passed: focused analysis/component tests passed (`126 passed`), targeted ESLint passed, full `project_qc_runner --project hanwoo-dashboard --json` passed (`test` 126, lint, build), path-limited `git diff --check` passed, and direct graph risk `0.00`. Staged/commit graph gate WARN came from dirty-WIP/test-gap heuristics while direct tests covered the committed files. Active Hanwoo goal remains open; T-251 remains external/user-owned Supabase control-plane resync. Preserve unrelated root monorepo/package-lock/shorts WIP plus dirty Hanwoo `package.json` unless explicitly authorized. |

| Field | Value |
|---|---|
| Date | 2026-05-20 |
| Tool | Codex |
| Work | **T-381 completed**: continued Hanwoo product-completeness work by preventing raw runtime/Prisma exception messages from leaking through tab action toast failures. `recordFeed`, `addInventoryItem`, `updateInventoryQuantity`, `createScheduleEvent`, and `toggleEventCompletion` now log diagnostics and return Korean product fallback copy for user-facing failures. `actions-copy.test.mjs` guards the Korean fallbacks and rejects raw `e.message`/`error.message` returns in these actions. Code commit `517daef`. |
| Next Priorities | Verification passed: focused action/component tests passed (`126 passed`), targeted ESLint passed, full `project_qc_runner --project hanwoo-dashboard --json` passed (`test` 126, lint, build), path-limited `git diff --check` passed, direct graph risk `0.00`, and staged code-review gate PASS. Commit hook WARN came from dirty-WIP/test-gap heuristics while direct tests covered the committed files. Active Hanwoo goal remains open; T-251 remains external/user-owned Supabase control-plane resync. Preserve unrelated root monorepo/package-lock/shorts WIP plus dirty Hanwoo `package.json` unless explicitly authorized. |

| Field | Value |
|---|---|
| Date | 2026-05-20 |
| Tool | Codex |
| Work | **T-380 completed**: continued Hanwoo product-completeness work by replacing the broken `?` glyph in the cattle Excel export button with a real lucide `Download` icon. The icon is decorative (`aria-hidden`) and the button now exposes `aria-busy` while preparing the export. Added `excel-export-button-copy.test.mjs` to prevent the placeholder glyph from returning. Code commit `a65c6ed`. |
| Next Priorities | Verification passed: focused Excel export/component tests passed (`126 passed`), targeted ESLint passed, full `project_qc_runner --project hanwoo-dashboard --json` passed (`test` 126, lint, build), path-limited `git diff --check` passed, direct graph risk `0.00`, and staged code-review gate PASS. Commit hook WARN came from dirty-WIP/test-gap heuristics while direct tests covered the committed files. Active Hanwoo goal remains open; T-251 remains external/user-owned Supabase control-plane resync. Preserve unrelated root monorepo/package-lock/shorts WIP plus dirty Hanwoo `package.json` unless explicitly authorized. |

| Field | Value |
|---|---|
| Date | 2026-05-20 |
| Tool | Codex |
| Work | **T-379 completed**: continued Hanwoo product-completeness work by localizing Settings server-action failure fallbacks. `createBuilding`, `deleteBuilding`, and `updateFarmSettings` no longer return raw `e.message` to user-facing toast paths; they now log diagnostics and return Korean product copy. `actions-copy.test.mjs` guards the Korean fallbacks and rejects `message: e.message` in these actions. Code commit `6c91449`. |
| Next Priorities | Verification passed before commit: Hanwoo tests passed (`125 passed`), targeted ESLint passed, full `project_qc_runner --project hanwoo-dashboard --json` passed (`test` 125, lint, build), path-limited `git diff --check` passed, and direct graph risk `0.00`. Staged/commit graph gate WARN came from dirty-WIP/test-gap heuristics while direct tests covered the committed files. Active Hanwoo goal remains open; T-251 is still external/user-owned Supabase control-plane resync. Preserve unrelated root monorepo/package-lock/shorts WIP plus dirty Hanwoo `package.json` unless explicitly authorized. |

| Field | Value |
|---|---|
| Date | 2026-05-20 |
| Tool | Codex |
| Work | **T-378 completed**: continued Hanwoo product-completeness work by making global feedback toasts announce reliably to assistive-tech users. `FeedbackProvider.js` now marks error/warning toasts as `role="alert"` with assertive live updates, success/info toasts as `role="status"` with polite live updates, uses `aria-atomic="true"`, hides the decorative accent dot, and gives each dismiss button a Korean toast-specific label. Added `feedback-provider-copy.test.mjs`. Code commit `980bfb7`. |
| Next Priorities | Verification passed: focused feedback/component tests passed, targeted ESLint passed, full `project_qc_runner --project hanwoo-dashboard --json` passed (`test` 125, lint, build), path-limited `git diff --check` passed, and direct graph risk `0.00`. Commit hook WARN came from graph dirty-WIP/test-gap heuristics while direct tests covered the committed files. Active Hanwoo goal remains open; T-251 is still external/user-owned Supabase control-plane resync. Preserve unrelated root monorepo/package-lock/shorts WIP plus dirty Hanwoo action/package changes unless explicitly authorized. |

| Field | Value |
|---|---|
| Date | 2026-05-20 |
| Tool | Codex |
| Work | **T-377 completed**: continued Hanwoo accessibility cleanup. `DashboardClient` now marks home notification/add/back icons and the critical notification badge as decorative with `aria-hidden`, while preserving Korean button labels. `SettingsTab` theme/widget toggles now expose `role="switch"`, `aria-checked`, Korean `aria-label`/`title`, and decorative thumb `aria-hidden`. Added `settings-tab-accessibility.test.mjs`; extended `home-market-copy.test.mjs`. Code commit `4d8fcf6`; context commit pending/this addendum records it. |
| Next Priorities | Verification passed: Hanwoo `npm test` (`124 passed`), targeted ESLint, full Hanwoo QC test/lint plus build retry pass, path-limited `git diff --check`, and direct graph risk `0.00`. Active Hanwoo goal remains open only because T-251 is still external/user-owned Supabase control-plane resync. Preserve unrelated root monorepo/package-lock/shorts WIP plus dirty Hanwoo `package.json` postinstall removal unless explicitly authorized. |

| Field | Value |
|---|---|
| Date | 2026-05-20 |
| Tool | Claude Code (Opus 4.7 1M) |
| Work | **T-367 false positive로 종결 (코드 변경 없음)**. 사용자 "T-367 진행해" 지시 → `formSchemas.js` enum 영어 값 조사. 결론: 영어 enum 값(스케줄 `type`, 재고 `category`)은 표준 **내부 코드**이고 `ScheduleTab.TYPE_STYLES`·`InventoryTab.categories` 맵 + `<option>` 라벨이 전부 코드→한글로 변환 — 운영자는 영어를 한 번도 안 봄. 양 `<select>`에 `Other`(기타) 옵션도 이미 존재. "운영자 노출 영어 카피 누수"라는 원 전제(서브에이전트 감사의 HIGH 분류)가 오탐. enum 한글화는 이득 0 + 전 DB 행 마이그레이션 위험 + Supabase 다운(T-251)으로 불가 → 코드 변경 없이 TASKS.md DONE에 판정 기록. |
| Next Priorities | 이번 `/goal` 세션 누적: **T-365**(profitability 영어 에러 카피 한글화, `172e998`) + **T-366**(고아 profitability 위젯 마운트, `1047f01`) 완료, **T-367** false-positive 종결. hanwoo-dashboard 제품 완성도 goal에서 자율 처리 가능한 in-scope 작업은 모두 소진 — 남은 건 T-251(사용자가 Supabase 비번 재설정해야 하는 외부 차단)뿐. T-372(모노레포 마이그레이션)는 `pnpm install` 로컬 exit 127 블로커로 보류 중. 감사(서브에이전트 3개 전수) 결과 추가 미완 기능/empty-catch 0건. goal은 사용자 판단(`/goal complete` 또는 `/goal clear`)을 기다리며 일시정지 권장. |

| Field | Value |
|---|---|
| Date | 2026-05-20 |
| Tool | Claude Code (Opus 4.7 1M) |
| Work | **T-376 완료**: `/goal "뭐라도 제대로 완성 해봐"` — AskUserQuestion으로 대상=shorts-maker-v2 렌더 최적화 선택. T-337(색보정)·T-350(켄번즈) 후속. `bench_render.py --profile`로 핫스팟 재측정 → 핸드오프 가설(compose_on/transform 오버헤드)과 달리 실제 1·2위는 `astype`(5.1s)·MoviePy `compose_mask`(4.6s). 근본 원인: `RenderStep._render_single_scene`의 씬 `CompositeVideoClip`이 기본 `transparent=True`라 매 프레임 알파 마스크(compose_mask + astype + 별도 is_mask 클립그래프)를 계산하지만 **결과는 폐기**됨 — 최종 Shorts는 완전 불투명, `frame_function`이 알파 채널을 버림. 씬 base 클립은 `_fit_vertical` cover-fit으로 풀프레임 불투명 → `use_bgclip=True` 전달 시 MoviePy가 base를 배경으로 직접 사용하고 마스크 파이프라인 전체를 건너뜀(픽셀 동일, 캡션 알파는 compose_on이 처리). 씬 컴포지트 4곳(karaoke/karaoke fallback/static/B-roll PiP) 적용. concat은 크로스페이드 전환이 씬을 겹치므로 `method="compose"` 유지. **측정: render 147.0s→96.4s, 34% 단축**(per-video-sec 16.3→10.7s). commit `42f6434`. |
| Next Priorities | 검증 완료: 전체 스위트 `1471 passed / 0 failed / 12 skipped`(206s), 렌더 단위 243 pass, ruff 클린, `git diff --check` 클린. 커밋훅 WARN은 그래프 test-gap 휴리스틱이 무관한 dirty Hanwoo WIP를 함께 스캔한 잡음(test gap 목록이 DashboardClient/SettingsTab 등 내 변경 외 파일). **렌더 최적화 후속**: 남은 #1 비용은 `color_grading._grade_inplace`(이미 T-337에서 2.7배 최적화됨)와 ken-burns `resize`(T-350 완료). concat 레벨 compose_mask 1×/frame은 크로스페이드 때문에 불가피. `python scripts/bench_render.py --profile`이 회귀 게이트. 병렬 도구(Codex)가 Hanwoo goal 진행 중 — T-376 커밋 전 분석 로컬라이즈 WIP를 Codex가 `666ddf3`로 선점 커밋함(경합 정상). T-251은 여전히 외부/사용자 차단. |

| Field | Value |
|---|---|
| Date | 2026-05-20 |
| Tool | Codex |
| Work | **T-374 completed**: continued the active Hanwoo quality goal by finishing notification-system trigger accessibility. `NotificationSystem.js` and the tracked `NotificationSystem.tsx` mirror now compute Korean unread-count-aware trigger labels, expose them through `aria-label`/`title`, and hide decorative bell/badge visuals from assistive tech. Added `notification-system-copy.test.mjs`. Code commit `56e1e9e`; context commit pending/this addendum records it. |
| Next Priorities | Verification passed: Hanwoo `npm test` (`123 passed`), targeted ESLint, full `project_qc_runner --project hanwoo-dashboard --json` (`test` 123, lint, build), path-limited `git diff --check`, and direct graph risk `0.00`. Staged/commit graph gate WARN came from heuristic test-gap/dirty-WIP noise while direct tests covered the committed files. Active Hanwoo goal remains open. Remaining TODOs are approval/user-blocked: T-251 Supabase control-plane resync, T-367 DB enum migration, T-372 monorepo migration, and T-320 shorts OSS adoption. Preserve unrelated root monorepo/package-lock/shorts WIP plus dirty Hanwoo `package.json` postinstall removal unless explicitly authorized. |

| Field | Value |
|---|---|
| Date | 2026-05-20 |
| Tool | Codex |
| Work | **T-373 completed**: continued the active Hanwoo product-completeness goal by labeling remaining calendar/market icon actions. `ScheduleTab` now labels previous/next month controls as `이전 달 보기` / `다음 달 보기`, and `MarketPriceWidget` labels the refresh button as `한우 시세 새로고침` / `시세 갱신 중`. `home-market-copy.test.mjs` guards both surfaces. Commit `4609453`. |
| Next Priorities | Verification passed: focused Hanwoo home/market tests passed (`7 passed`), targeted ESLint passed, full Hanwoo QC test/lint passed and build passed on retry after a concurrent Next build lock (`test` 121), path-limited `git diff --check` passed, and direct UTF-8 graph risk `0.00`. Full `git diff --check` is still blocked by unrelated dirty shorts-maker-v2 whitespace; staged/commit graph gate WARN came from dirty WIP heuristics while direct checks covered the committed files. T-366 profitability widget mount also completed in commit `1047f01` and is recorded. Remaining TODOs are approval/user-blocked: T-251 Supabase control-plane resync, T-367 DB enum migration, T-372 monorepo migration, and T-320 shorts OSS adoption. Preserve unrelated root monorepo/package-lock/shorts WIP. |

| Field | Value |
|---|---|
| Date | 2026-05-20 |
| Tool | Claude Code (Opus 4.7 1M) |
| Work | **T-366 완료** (고아 위젯 마운트). 사용자가 `/goal resume` 후 진행. `ProfitabilityWidget` + `getProfitabilityData`(서버 액션) + `getProfitabilityEstimates`(서비스)가 다 구현됐고 `WIDGET_REGISTRY`에 `defaultOn:true`로 등록됐지만 `<ProfitabilityWidget />`이 어디에도 렌더 안 되던 미완 기능. SSR 데이터 흐름에 연결: `app/page.js`가 `Promise.all`에 `getProfitabilityData()` 추가 → `initialProfitability` prop → `DashboardClient`가 `widgetSettings.visible.profitability` 게이트로 위젯 렌더. (주의: DashboardClient는 자체 `WIDGET_REGISTRY`를 쓰며 `lib/hooks/useWidgetSettings.js`의 동명 레지스트리와 별개 — 이번에 DashboardClient 쪽 레지스트리에도 profitability 항목이 들어가야 `visible.profitability`가 truthy가 됨.) `profitability-copy.test.mjs`에 마운트 회귀 가드 추가. 커밋 `1047f01`. |
| Next Priorities | 검증 통과: profitability 테스트 3/3, full `project_qc_runner --project hanwoo-dashboard --json` 통과(test/lint/build). 이번 세션 누적: T-365(profitability 영어 에러 카피 한글화, `172e998`) + T-366(`1047f01`). 남은 Hanwoo TODO는 T-367(formSchemas enum, DB 마이그레이션 동반, approval)뿐 — T-251은 외부/사용자 차단. **모노레포 마이그레이션은 T-372로 재번호**(구 T-368이 DONE의 Codex T-368과 ID 충돌) — `pnpm install` 로컬 exit 127 블로커로 보류, TASKS.md T-372 참조. Active Hanwoo goal 유지. 무관한 root monorepo/package-lock/shorts WIP 보존. |

| Field | Value |
|---|---|
| Date | 2026-05-20 |
| Tool | Codex |
| Work | **T-371 completed**: continued the active Hanwoo product-completeness goal by finishing another accessibility polish pass. `CattleForm` and `CattleDetailModal` now expose `role="dialog"`, `aria-modal`, visible-title `aria-labelledby`, and Korean icon-button labels; `AIChatWidget` now labels the icon-only send button as `질문 보내기` / `답변 생성 중`. Commit `001621d`. |
| Next Priorities | Verification passed: focused Hanwoo cattle/AI/component tests passed (`119 passed`), targeted ESLint passed, full `project_qc_runner --project hanwoo-dashboard --json` passed (`test` 119, lint, build), `git diff --check` passed, direct UTF-8 graph risk `0.00`, and staged code-review gate PASS. Commit hook emitted the known component test-gap WARN while direct source regression coverage and full QC passed. Active Hanwoo goal remains open because T-251 is still external/user-owned Supabase password/control-plane resync. Remaining Hanwoo TODOs T-366/T-367 are approval-gated; preserve unrelated root monorepo/package-lock/shorts WIP. |

| Field | Value |
|---|---|
| Date | 2026-05-20 |
| Tool | Claude Code (Opus 4.7 1M) |
| Work | **T-368 진단 (모노레포 마이그레이션 마무리 시도)**. 사용자가 `/goal` 후속으로 모노레포 마이그레이션(pnpm+turbo+biome+uv) 마무리를 선택. 조사 결과 마이그레이션 WIP가 예상보다 덜 끝났고 **로컬 환경 하드 블로커** 발견: `pnpm install`(full, with scripts)이 이 머신(Windows 11 + 한글 홈 `박주호`)에서 linking 단계에 `exit 127`·에러 출력 없이 **6회 연속 중단**. `--ignore-scripts`는 exit 0이나 node_modules 불완전, `--lockfile-only`(linking 없음)만 정상 exit 0. 한글 경로 툴링 취약성(메모리 `windows_korean_path_encode_strict`)과 일치. → 로컬에서 `turbo`/`biome`/`pnpm lint` 검증 불가. **성과**: 부재했던 `pnpm-lock.yaml`을 `pnpm install --lockfile-only`로 생성(루트, 336KB, untracked) — `.gitignore`에 lockfile 제외 없음. **미커밋**: 로컬 검증 불가 + 미해결 설계 결정 때문에 마이그레이션 관련 파일은 일절 커밋하지 않음. WIP 전부 untracked 보존. |
| Next Priorities | **T-368** TASKS.md에 상세 등록(approval). 미해결 결정: (a) `biome.json` `recommended` + 전 코드베이스 `biome check .` → `pnpm lint` 적색 가능성(blast radius 미측정 — 로컬 install 불가로 못 잼), biome 채택 범위/advisory 결정 필요. (b) hanwoo `package.json` `postinstall: prisma generate` 제거됨 → CI fresh build prisma client 미생성 위험, 복원 또는 turbo/CI에 `prisma generate` 단계 추가 필요. 잔존 정리: suika-game-v2·word-chain `package-lock.json` 미삭제, CI `actions/setup-node@v6→v4` 다운그레이드. **권장 경로**: 마이그레이션 검증은 CI(ubuntu-latest, exit 127은 Windows 한정일 가능성 큼)에서 진행하거나, 로컬 검증이 필요하면 비한글 경로 작업 디렉터리 사용. 이번 세션에서 별도로 **T-365 완료**(profitability widget 영어 에러 카피 한글화, 커밋 `172e998`). Active Hanwoo goal 유지. |

| Field | Value |
|---|---|
| Date | 2026-05-20 |
| Tool | Codex |
| Work | **T-370 completed**: continued the active Hanwoo product-completeness goal by labeling home-screen icon-only actions for assistive-tech users. `DashboardClient.js` now gives the notification-center, add-cattle, building-back, and pen-back icon buttons Korean `aria-label`/`title` copy; `home-market-copy.test.mjs` guards the labels. Commit `082537c`. |
| Next Priorities | Verification passed: focused Hanwoo home/component tests passed (`118 passed`), targeted ESLint passed, full Hanwoo QC test/lint passed and build passed on retry after a concurrent Next build lock, `git diff --check` passed, direct UTF-8 graph risk `0.00`, and staged code-review gate PASS. Commit hook emitted the known component test-gap WARN, but direct regression coverage and full QC passed. Active Hanwoo goal remains open because T-251 is still external/user-owned Supabase password/control-plane resync. Only approval TODOs remain for Hanwoo (T-366/T-367); preserve unrelated dirty root monorepo migration WIP. |

| Field | Value |
|---|---|
| Date | 2026-05-20 |
| Tool | Codex |
| Work | **T-369 completed**: continued the active Hanwoo product-completeness goal by making `components/ui/NotificationModal.js` expose real dialog semantics. The modal container now has `role="dialog"`, `aria-modal="true"`, and `aria-labelledby="notification-modal-title"`, with the visible `알림 센터` title carrying that id. `notification-modal-copy.test.mjs` now guards both the Korean close label and dialog semantics. Code commit: `6647522`. |
| Next Priorities | Verification passed: focused notification modal tests passed (`117 passed`), targeted ESLint passed, full `project_qc_runner --project hanwoo-dashboard --json` passed (`test` 117, lint passed, build passed), source confirmation passed, `git diff --check` passed, and direct graph risk `0.00`. Staged/commit code-review gate emitted WARN because unrelated staged/dirty WIP was present (`DashboardClient.js`, `home-market-copy.test.mjs`, shorts render work), but direct focused/full checks covered the two-file modal change. Preserve unrelated staged WIP unless the user authorizes committing it. Active Hanwoo goal remains open; T-251 is still external/user-owned Supabase password/control-plane resync, and T-366/T-367 remain approval-gated. |

| Field | Value |
|---|---|
| Date | 2026-05-20 |
| Tool | Codex |
| Work | **T-368 completed**: continued the active Hanwoo product-completeness goal with a safe accessibility polish. `components/ui/NotificationModal.js` now labels the icon-only `×` close button with Korean `aria-label="닫기"` and `title="닫기"`, and `notification-modal-copy.test.mjs` guards against English close labels returning. Code commit: `aa80799`. |
| Next Priorities | Verification passed: focused Hanwoo notification modal copy test passed (`116 passed`), targeted ESLint passed, full `project_qc_runner --project hanwoo-dashboard --json` passed (`test` 116, lint passed, build passed), source confirmation passed, `git diff --check` passed, direct graph risk `0.00`. The commit hook/staged gate emitted the known graph test-gap WARN for `NotificationModal`, but the new source-level regression test and full QC cover the two-file accessibility change. Active Hanwoo goal remains open; T-251 is still external/user-owned Supabase password/control-plane resync. Remaining `.ai/TASKS.md` TODO entries are approval-gated (T-251, T-320, T-366, T-367), so ask before executing those unless the user explicitly authorizes one. Preserve unrelated monorepo/package-lock/setup WIP. |

| Field | Value |
|---|---|
| Date | 2026-05-20 |
| Tool | Codex |
| Work | **T-362 completed**: continued the active Hanwoo product-completeness goal by localizing admin diagnostics database status values. `lib/actions/system.js` now returns Korean status copy (`정상`, `연결 실패`, `확인 불가`) instead of `Online`, `Offline`, and `N/A`, and `diagnostics-copy.test.mjs` guards against those English status values returning. Commit `6efaeba`. |
| Next Priorities | Verification passed: focused Hanwoo diagnostics/action/component tests passed (`115 passed`), targeted ESLint passed, full Hanwoo QC test/lint passed and build passed on retry after a concurrent Next build lock, source scan found no live `Online`/`Offline`/`N/A` diagnostics status usage, `git diff --check` passed, direct UTF-8 graph risk `0.00`, and staged code-review gate PASS. Active Hanwoo goal remains open because T-251 is still external/user-owned Supabase password/control-plane resync. Preserve unrelated dirty root monorepo migration WIP and approval-only TODOs T-366/T-367. |

| Field | Value |
|---|---|
| Date | 2026-05-20 |
| Tool | Claude Code (Opus 4.7 1M) |
| Work | **T-365 completed** + 제품 완성도 감사. 사용자가 `/goal` 호출 시 이 세션 goal 텍스트가 DB(`~/.claude/goal/goals.sqlite`)에 손상된 채(`���� ����� �ϼ� �غ�`) 저장돼 있었음 — HANDOFF 문맥상 "Hanwoo product-completeness goal"임을 확인하고 DB objective를 정상 한국어로 복구(목표 자체는 유지). 병렬 서브에이전트 3개로 hanwoo-dashboard 전체 감사: (1) 영어 카피 누수 HIGH 2/MEDIUM 5/LOW 18, (2) 미완 기능 — TODO/stub/empty-catch 0건, (3) 모노레포 마이그레이션 WIP(pnpm+turbo+biome+uv) 70~80%. 감사 중 MEDIUM 후보 검증: `kape.js` throw는 같은 함수 catch에서 잡혀 사용자 미노출(스킵), `FeedbackProvider`/`queue.js`는 dev/infra(스킵). `profitability-service.js`만 실제 노출 확정 — `error: err.message`가 `ProfitabilityWidget`의 `{error}`로 렌더됨. **T-365**: 영어 throw 2건 + console 진단 한글화, `profitability-copy.test.mjs` 회귀 가드 추가. 커밋 `172e998`. |
| Next Priorities | 검증 통과: 신규 profitability-copy 테스트 2/2, full `project_qc_runner --project hanwoo-dashboard --json` 통과(test 115 / lint / build — build 1차는 `Another next build process is already running` 동시잠금으로 실패, 재시도 통과). **신규 TODO**: T-366 = `ProfitabilityWidget`이 컴포넌트/액션/서비스 다 있고 `WIDGET_REGISTRY`에 `defaultOn:true`인데 어디에도 마운트 안 됨(고아 위젯) — 연결 필요(approval). T-367 = `formSchemas.js` enum 값 영어이나 DB 저장값이라 데이터 마이그레이션 동반(approval). LOW 18건(서버 액션 `console.error` 영어 진단)은 가치 낮아 미등록 — 필요 시 일괄 처리. **모노레포 마이그레이션 WIP**: 루트 `package.json`/`pnpm-workspace.yaml`/`turbo.json`/`biome.json`/`pyproject.toml`/`uv.lock`/`.npmrc` 등 untracked — `pnpm-log.txt`는 에러 없음. 미완 위험: hanwoo `postinstall: prisma generate` 제거됨(CI에서 처리되는지 확인 필요), suika/word-chain `package-lock.json` 잔존, 워크플로 end-to-end 미검증. 이 WIP는 보존할 것. Active Hanwoo goal 유지(T-251 외부/사용자 차단). |

| Field | Value |
|---|---|
| Date | 2026-05-20 |
| Tool | Codex |
| Work | **T-361 completed**: continued the active Hanwoo product-completeness goal by localizing the shared dialog close label for screen-reader users. The Radix dialog close control in `components/ui/dialog.js` now exposes `닫기` instead of `Close`, and `dialog-copy.test.mjs` guards against the English sr-only label returning. |
| Next Priorities | Verification passed: focused Hanwoo dialog-copy tests passed (`113 passed`), targeted ESLint passed, full `project_qc_runner --project hanwoo-dashboard --json` passed (`test` 113 passed, lint passed, build passed), accessibility-copy source scan passed, `git diff --check` passed, direct UTF-8 graph risk `0.00`, and staged code-review gate PASS before commit. Commit hook emitted an advisory graph WARN polluted by unrelated dirty `system`/`profitability` WIP, but direct focused/full checks cover the two-file dialog change. Active Hanwoo goal remains open because T-251 is still external/user-owned Supabase password/control-plane resync. Preserve unrelated dirty WIP in root package/workflow files, Hanwoo `package.json`, system/profitability files, package locks, and setup scripts. |

| Field | Value |
|---|---|
| Date | 2026-05-20 |
| Tool | Codex |
| Work | **T-360 completed**: continued the active Hanwoo product-completeness goal by localizing remaining user-facing server action fallback errors. `getCattleList()` now throws `개체 목록을 불러오지 못했습니다.`, `getSalesRecords()` now throws `판매 기록을 불러오지 못했습니다.`, and admin raw-data validation now returns `지원하지 않는 데이터 유형입니다.` instead of `Failed to fetch cattle data.`, `Failed to fetch sales records.`, and `Invalid model name`. Added `actions-copy.test.mjs` to guard these server-action fallback strings. |
| Next Priorities | Verification passed: focused Hanwoo server-action copy tests passed (`112 passed`), targeted ESLint passed, full `project_qc_runner --project hanwoo-dashboard --json` passed (`test` 112 passed, lint passed, build passed), `git diff --check` passed, direct UTF-8 graph risk `0.00`, and staged code-review gate PASS before commit. Commit hook emitted an advisory graph WARN from broad heuristics, but direct focused/full checks cover the four-file change. Active Hanwoo goal remains open because T-251 is still external/user-owned Supabase password/control-plane resync. Preserve unrelated dirty WIP in root package/workflow files, Hanwoo `package.json`, package locks, and setup scripts. |

| Field | Value |
|---|---|
| Date | 2026-05-20 |
| Tool | Codex |
| Work | **T-359 completed**: continued the active Hanwoo product-completeness goal by localizing the financial analysis surface. `AnalysisTab` no longer renders English section labels (`Financial Analysis`, `Monthly Flow`, `Cost Mix`, `Top Sales`), and `FinancialChartWidget` no longer renders `Farm Financial Overview`, `Recent 6-month revenue, expense, and profit`, `Unit: KRW`, or English chart legend labels. Added `analysis-copy.test.mjs` to guard this financial-analysis copy. |
| Next Priorities | Verification passed: focused Hanwoo analysis-copy tests passed (`111 passed`), targeted ESLint passed, full `project_qc_runner --project hanwoo-dashboard --json` passed (`test` 111 passed, lint passed, build passed), source scan passed, `git diff --check` passed, direct UTF-8 graph risk `0.00`, and staged code-review gate PASS before commit. Commit hook emitted an advisory graph WARN from component test-gap heuristics, but direct focused/full checks cover the three-file copy change. Active Hanwoo goal remains open because T-251 is still external/user-owned Supabase password/control-plane resync. Preserve unrelated dirty WIP in root package/workflow files, Hanwoo `package.json`, package locks, and setup scripts. |

| Field | Value |
|---|---|
| Date | 2026-05-20 |
| Tool | Codex |
| Work | **T-358 completed**: continued the active Hanwoo product-completeness goal by localizing the shared authentication fallback. `AuthenticationError` now defaults to `로그인이 필요합니다.` instead of `Authentication required.`, so authenticated API routes that pass through `requireAuthenticatedSession()` do not leak English auth copy when no route-specific override is provided. |
| Next Priorities | Verification passed in the same Hanwoo pass: focused payment/auth source tests passed (`110 passed`), targeted ESLint passed, full `project_qc_runner --project hanwoo-dashboard --json` passed (`test` 110 passed, lint passed, build passed), `git diff --check` passed, direct UTF-8 graph risk `0.00`, and staged code-review gate PASS before commit. Commit hook emitted a graph test-gap WARN for the tiny constructor copy change, but the route/source regression test covers the user-facing fallback string. Active Hanwoo goal remains open because T-251 is still external/user-owned Supabase password/control-plane resync. Preserve unrelated dirty WIP in root package/workflow files, Hanwoo `package.json`, package locks, and setup scripts. |

| Field | Value |
|---|---|
| Date | 2026-05-20 |
| Tool | Codex |
| Work | **T-357 completed**: continued the active Hanwoo product-completeness goal by localizing payment API fallback responses. `/api/payments/prepare` now returns Korean operator-facing messages for customer-key mismatches, amount mismatches, generic preparation failures, and the customer-name fallback (`Joolife 사용자`). `/api/payments/confirm` now returns Korean messages for missing confirmation fields, wrong-user orders, amount mismatches, missing Toss configuration, timeout diagnostics, retryable gateway deferrals, and generic verification failures instead of leaking English fallback/API text. Extended `payment-ux-copy.test.mjs` to guard these route-level fallback strings. |
| Next Priorities | Verification passed: focused Hanwoo payment tests passed (`110 passed`), targeted ESLint passed, full `project_qc_runner --project hanwoo-dashboard --json` passed (`test` 110 passed, lint passed, build passed), `git diff --check` passed, direct UTF-8 graph risk `0.00`, and staged code-review gate PASS before commit. Commit hook emitted an advisory graph WARN polluted by an unrelated dirty `auth-guard.js` change, but direct focused/full checks cover the committed three-file payment change. Active Hanwoo goal remains open because T-251 is still external/user-owned Supabase password/control-plane resync. Preserve unrelated dirty WIP in root package/workflow files, Hanwoo `package.json` and `auth-guard.js`, package locks, and setup scripts. |

| Field | Value |
|---|---|
| Date | 2026-05-20 |
| Tool | Codex |
| Work | **T-356 completed**: continued the active Hanwoo product-completeness goal by polishing the AI chat widget fallback surface. `AIChatWidget` now treats the localized Gemini configuration messages from `/api/ai/chat` as setup errors, so missing setup still shows the guided fallback instead of a generic failure. The closed floating launcher now uses a lucide `Bot` icon with explicit accessible label/title instead of a bare `AI` text button. Added `ai-chat-widget-copy.test.mjs` to guard the Korean setup-error patterns and accessible launcher wiring. |
| Next Priorities | Verification passed: focused Hanwoo AI chat/widget tests passed (`109 passed`), targeted ESLint passed, full `project_qc_runner --project hanwoo-dashboard --json` passed (`test` 109 passed, lint passed, build passed), `git diff --check` passed, and UTF-8 graph risk `0.00`. Active Hanwoo goal remains open because T-251 is still external/user-owned Supabase password/control-plane resync. Preserve unrelated dirty WIP in root package/workflow files, Hanwoo `package.json`, package locks, and setup scripts. |

| Field | Value |
|---|---|
| Date | 2026-05-20 |
| Tool | Codex |
| Work | **T-355 completed**: continued the active Hanwoo product-completeness goal by localizing the subscription entry page. `/subscription` now uses Korean product copy for the page title, monthly price/value description, and customer-name fallback (`Joolife 사용자`) instead of `Joolife Premium Subscription`, `Start smarter farm management for KRW 9,900 per month.`, and `Joolife User`. Extended `payment-ux-copy.test.mjs` to cover the entry page as well as checkout/result pages. |
| Next Priorities | Verification passed: focused Hanwoo payment/subscription tests passed (`108 passed`), targeted ESLint passed, full `project_qc_runner --project hanwoo-dashboard --json` passed (`test` 109 passed, lint passed, build passed), `git diff --check` passed, source English subscription scan passed, and UTF-8 graph risk `0.00`. Active Hanwoo goal remains open because T-251 is still external/user-owned Supabase password/control-plane resync. Preserve unrelated dirty WIP in root package/workflow files, Hanwoo `package.json`, package locks, and setup scripts. |

| Field | Value |
|---|---|
| Date | 2026-05-20 |
| Tool | Codex |
| Work | **T-354 completed**: continued the active Hanwoo product-completeness goal by localizing AI chat API error/fallback copy. `/api/ai/chat` validation, authentication, missing Gemini configuration, provider SSE errors, and start-chat failures now return Korean operator-facing messages instead of English API/debug text. The AI farm-context payload also avoids English fallback labels such as `unknown`, `No recent sales records`, `Current farm context`, and `man KRW`. Added/updated regression coverage in `ai-chat-api.test.mjs`. |
| Next Priorities | Verification passed: focused Hanwoo AI chat tests passed (`108 passed`), targeted ESLint passed, full `project_qc_runner --project hanwoo-dashboard --json` passed (`test` 108 passed, lint passed, build passed), `git diff --check` passed, source English fallback scan passed, and UTF-8 graph risk `0.00`. Active Hanwoo goal remains open because T-251 is still external/user-owned Supabase password/control-plane resync. Preserve unrelated dirty WIP in root package/workflow files, Hanwoo `package.json`, package locks, and setup scripts. |

| Field | Value |
|---|---|
| Date | 2026-05-20 |
| Tool | Codex |
| Work | **T-353 completed**: continued the active Hanwoo product-completeness goal by localizing cattle tag lookup (MTRACE) fallback copy. `lookupCattleByTag()` now returns Korean operator-facing messages for missing API key, invalid tag number, rate limits, upstream failures, unreadable responses, no-match results, timeouts, and generic lookup errors; the default breed fallback is now `한우` instead of `Hanwoo`, and the internal API diagnostic label is Korean. Added mocked MTRACE behavior/source coverage in `mtrace.test.mjs`. |
| Next Priorities | Verification passed: focused Hanwoo mtrace/import tests passed (`107 passed`), targeted ESLint passed, full `project_qc_runner --project hanwoo-dashboard --json` passed (`test` 107 passed, lint passed, build passed), `git diff --check` passed, and UTF-8 graph risk `0.00`. `npm test` prints the existing Node `MODULE_TYPELESS_PACKAGE_JSON` warning for JS ESM test imports, but all checks pass. Active Hanwoo goal remains open because T-251 is still external/user-owned Supabase password/control-plane resync. Preserve unrelated dirty WIP in root package/workflow files, Hanwoo `package.json`, package locks, and setup scripts. |

| Field | Value |
|---|---|
| Date | 2026-05-20 |
| Tool | Codex |
| Work | **T-352 completed**: continued the active Hanwoo product-completeness goal by localizing dashboard API fallback/error copy. `DashboardClient` now uses Korean timeout/failure messages for dashboard list loads, Korean console diagnostics for summary/notification/list refresh failures, and a Korean footer rights line. `/api/dashboard/{summary,cattle,sales}` now return Korean default 500 fallback messages when the app-authored fallback path is used. |
| Next Priorities | Verification passed: focused Hanwoo home/import tests passed (`103 passed`), targeted ESLint passed, full `project_qc_runner --project hanwoo-dashboard --json` passed (`test` 103 passed, lint passed, build passed), `git diff --check` passed, and direct Hanwoo graph risk `0.00`. Active Hanwoo goal remains open because T-251 is still external/user-owned Supabase password/control-plane resync. Preserve unrelated dirty WIP in root package/workflow files, Hanwoo `package.json`, package locks, and setup scripts. |

| Field | Value |
|---|---|
| Date | 2026-05-20 |
| Tool | Codex |
| Work | **T-351 completed**: continued the active Hanwoo product-completeness goal by localizing the printed cattle QR label footer. The QR print window already used `QR 출력` / `QR 라벨 인쇄`; the printed tag footer now uses `Joolife 한우 스마트팜` instead of `Joolife Smart Farm`, and `qr-widget-copy.test.mjs` guards against the English footer returning. |
| Next Priorities | Verification passed: focused Hanwoo QR/import tests passed (`102 passed`), targeted ESLint passed, full `project_qc_runner --project hanwoo-dashboard --json` passed (`test` 102 passed, lint passed, build passed), `git diff --check` passed, staged code-review gate PASS, and UTF-8 graph risk `0.00`. Commit hook emitted an advisory WARN from graph test-gap heuristics, but the direct focused/full checks cover the two-file copy change. Active Hanwoo goal remains open because T-251 is still external/user-owned Supabase password/control-plane resync. Preserve unrelated dirty WIP in root package/workflow files, Hanwoo `package.json`, package locks, and setup scripts. |

| Field | Value |
|---|---|
| Date | 2026-05-20 |
| Tool | Claude Code (Opus 4.7 1M) |
| Work | **T-350 완료**: 사용자 요청 "ken-burns 모션도 최적화" (T-337 렌더 최적화 후속). `bench_render.py` micro-bench 로 `_ken_burns` ~70ms/frame 격리 측정 → 원인은 5개 줌 효과의 `clip.resized(시간함수)` 가 MoviePy `Resize.py` 의 하드코딩 `LANCZOS` 로 매 프레임 전체 리샘플(LANCZOS 68ms vs BICUBIC 53). 신규 헬퍼 `_zoom_crop` 이 per-frame 줌을 PIL `Image.resize(box=..., BICUBIC)` 단일 호출로 수행(중심 줌에서 crop↔resize 순서 항등). 5개 효과를 `_zoom_crop`+scale_fn 람다로 재작성. **micro-bench: `_ken_burns` 72.5→54.9 ms/frame(-24%).** 검증: 렌더 단위 240 pass, ruff 클린. commit `352880d`(perf)+`020edd7`(id fix). |
| Next Priorities | **렌더 최적화 후속**: 색보정(T-337)·Ken Burns(T-350) 완료. 남은 후보는 `CompositeVideoClip.compose_on` 레이어 합성 + MoviePy `transform`/`get_frame` 디코레이터 오버헤드. `python scripts/bench_render.py --profile` 로 측정. **git 경합 심함**: 이 세션에서 perf 커밋 `7f350a2` 가 병렬 도구 git 작업으로 orphan 되고 task ID 가 T-339→T-346 두 번 선점당함 — 부분 커밋은 `git commit -- <pathspec>`, amend 는 `git rev-parse HEAD` 가드, task ID 는 현재 max+여러 칸 위로(T-350 사용). 줌 필터는 BICUBIC; 더 빠른 BILINEAR 도 `_ZOOM_RESAMPLE` 한 줄로 전환 가능하나 약간 더 부드러워짐. T-251 은 여전히 외부/사용자 차단. |

| Field | Value |
|---|---|
| Date | 2026-05-20 |
| Tool | Codex |
| Work | **T-346 completed**: continued the active Hanwoo product-completeness goal by localizing remaining fallback surface copy. Login, route-error, global-error, and not-found screens now use `Joolife 한우 운영` instead of `Joolife Operations`; weather fallback location labels now default to `서울` instead of `Seoul` across `DashboardClient`, `WeatherWidget`, `useWeather`, and `weather-state.mjs`. |
| Next Priorities | Verification passed: focused Hanwoo tests passed (`102 passed`), targeted ESLint passed, full `project_qc_runner --project hanwoo-dashboard --json` passed (`test` 102 passed, lint passed, build passed), `git diff --check` passed, staged code-review gate PASS, and UTF-8 graph risk `0.00`. Commit hook emitted advisory WARN from broad dirty-worktree graph heuristics, but the committed path set was only the fallback surface copy files. Active Hanwoo goal remains open because T-251 is still external/user-owned Supabase password/control-plane resync. Preserve unrelated dirty WIP in root package/workflow files, Hanwoo `package.json`, package locks, shorts-maker-v2 render effects files, and setup scripts. |

| Field | Value |
|---|---|
| Date | 2026-05-20 |
| Tool | Codex |
| Work | **T-345 completed**: continued the active Hanwoo product-completeness goal by polishing the cattle QR print action. `QRCodeWidget` now uses a lucide `Printer` icon, Korean print-document title suffix (`QR 출력`), and Korean button/title copy (`QR 라벨 인쇄`) instead of a bare emoji label and English `QR Code` print title. Added source-copy regression coverage in `qr-widget-copy.test.mjs`. |
| Next Priorities | Verification passed: focused Hanwoo tests passed (`100 passed`), targeted ESLint passed, full `project_qc_runner --project hanwoo-dashboard --json` passed (`test` 100 passed, lint passed, build passed), and UTF-8 graph risk `0.00`. Active Hanwoo goal remains open because T-251 is still external/user-owned Supabase password/control-plane resync. Preserve unrelated dirty WIP in root package/workflow files, Hanwoo `package.json`, package locks, and setup scripts. |

| Field | Value |
|---|---|
| Date | 2026-05-20 |
| Tool | Codex |
| Work | **T-344 completed**: continued the active Hanwoo product-completeness goal by localizing the Sales tab missing-cattle fallback path. `SalesTab` now renders `개체명 미등록` and `이력번호 미등록` instead of `Unknown` / `000-0000-0000` when a sale record references missing cattle metadata, so charts and sale cards stay operator-facing. Added source-copy regression coverage in `home-market-copy.test.mjs`. |
| Next Priorities | Verification passed: focused Hanwoo tests passed (`99 passed`), targeted ESLint passed, full `project_qc_runner --project hanwoo-dashboard --json` passed (`test` 99 passed, lint passed, build passed), `git diff --check` passed, staged code-review gate PASS, and UTF-8 graph risk `0.00`. Commit hook emitted advisory WARN from graph test-gap heuristics, but direct focused/full checks cover the change. Active Hanwoo goal remains open because T-251 is still external/user-owned Supabase password/control-plane resync. Preserve unrelated dirty WIP in root package/workflow files, Hanwoo `package.json`, package locks, and setup scripts. |

| Field | Value |
|---|---|
| Date | 2026-05-20 |
| Tool | Codex |
| Work | **T-343 completed**: hardened the Hanwoo cattle CSV export after the Korean-header localization. `cattle-csv-export.mjs` now uses fully Korean headers (`개체 번호`, `축사 번호` instead of mixed `ID` labels), quotes CSV cells containing commas/quotes/newlines, and preserves normalized memo text. Added regression coverage for quoted names such as `복"실,이`. |
| Next Priorities | Verification passed: focused CSV tests passed (`98 passed`), targeted ESLint passed, full Hanwoo project QC passed for test/lint and build passed on retry after a transient concurrent Next build lock, `git diff --check` passed, and UTF-8 graph risk `0.00`. Active Hanwoo goal remains open because T-251 is still external/user-owned Supabase password/control-plane resync. Preserve unrelated dirty WIP in root package/workflow files, Hanwoo `package.json`, package locks, and setup scripts. |

| Field | Value |
|---|---|
| Date | 2026-05-20 |
| Tool | Codex |
| Work | **T-342 completed**: continued the active Hanwoo quality goal by localizing the cattle Excel/CSV export result. `ExcelExportButton` now delegates CSV generation to `src/lib/cattle-csv-export.mjs`; the exported spreadsheet keeps the UTF-8 BOM, uses Korean headers (`이름`, `이력번호`, `생년월일`, `성별`, `상태`, `축사 ID`, `칸 번호`, `메모`), and normalizes memo commas/extra whitespace. |
| Next Priorities | Verification passed: focused export/import tests passed (`97 passed`), targeted ESLint passed, full `project_qc_runner --project hanwoo-dashboard --json` passed (`test` 97 passed, lint passed, build passed), `git diff --check` passed, and UTF-8 graph risk `0.00`. Active Hanwoo goal remains open because T-251 is still external/user-owned Supabase password/control-plane resync. Preserve unrelated dirty WIP in root package/workflow files, Hanwoo `package.json`, package locks, and setup scripts. |

| Field | Value |
|---|---|
| Date | 2026-05-20 |
| Tool | Codex |
| Work | **T-341 completed**: continued the active Hanwoo quality goal by localizing payment confirmation fallback copy. `payment-confirmation.mjs` now returns Korean pending, failure, amount-mismatch, and malformed gateway-response messages while still preserving explicit gateway-provided messages. Added direct behavior coverage and source-copy coverage so `Payment confirmation`, `Payment verification`, `Confirmed payment amount`, and `Gateway response:` do not return as app-authored user-facing fallback copy. Commit `535839a`. |
| Next Priorities | Verification passed: Hanwoo node tests `96 passed`, `npm.cmd run lint`, `npm.cmd run build`, `git diff --check`, staged code-review gate PASS, and direct Hanwoo graph risk `0.00`. Commit hook emitted advisory WARN from graph heuristics that also mentioned concurrent dirty `ExcelExportButton.js`, but the committed path set was only payment confirmation files. Active Hanwoo goal remains open because T-251 is still external/user-owned Supabase password/control-plane resync. Preserve unrelated dirty WIP in root package/workflow files, Hanwoo `package.json`, `ExcelExportButton.js` / `cattle-csv-export.mjs`, package locks, and setup scripts. |

| Field | Value |
|---|---|
| Date | 2026-05-20 |
| Tool | Codex |
| Work | **T-340 completed**: continued the active Hanwoo quality goal by localizing the remaining weather fallback path. `weather-state.mjs` now emits Korean unavailable, stale, and partial-forecast messages plus Korean source labels (`실시간 Open-Meteo`, `부분 예보`, `이전 날씨`, `확인 불가`), and `WeatherWidget` no longer renders `Weather Unavailable` / `Weather data is temporarily unavailable` fallback copy. Extra state regression coverage also blocks stale/partial English labels from returning. |
| Next Priorities | Verification passed: Hanwoo node tests `94 passed`, `npm.cmd run lint`, `npm.cmd run build`, `git diff --check`, and UTF-8 graph risk `0.00`. Active Hanwoo goal remains open because T-251 is still external/user-owned Supabase password/control-plane resync. Preserve unrelated dirty WIP in root package/workflow files, Hanwoo `package.json`, package locks, and setup scripts. |

| Field | Value |
|---|---|
| Date | 2026-05-20 |
| Tool | Codex |
| Work | **T-339 completed**: continued the active Hanwoo quality goal by localizing the remaining visible English copy on the home surface and market price widget. The home fallback farm name now reads `Joolife 한우 농장`, home panel eyebrows use Korean labels (`오늘 요약`, `빠른 기록`, `운영 준비`), and `MarketPriceWidget` now renders Korean loading, unavailable, source, heading, grade, updated, and KAPE source labels. Commit `cd99fb8`. |
| Next Priorities | Verification passed on current HEAD after the adjacent T-338 market-state fallback work: Hanwoo test suite `92 passed`, `npm.cmd run lint`, `npm.cmd run build`, `git diff --check`, and direct Hanwoo graph risk `0.00`. Active Hanwoo goal remains open because T-251 is still external/user-owned Supabase password/control-plane resync. Preserve unrelated dirty WIP in root package/workflow files, Hanwoo `package.json`, package locks, and setup scripts. |

| Field | Value |
|---|---|
| Date | 2026-05-20 |
| Tool | Codex |
| Work | **T-338 completed**: continued the active Hanwoo quality goal and fixed a remaining English fallback-copy path in the market price state layer. `market-price-state.mjs` now emits Korean product copy for unavailable market prices, stale-cache notices, and live/cache/unavailable source labels, so degraded KAPE states cannot surface English fallback text in `MarketPriceWidget`. |
| Next Priorities | Verification passed: focused market-price tests passed, targeted ESLint passed, full `project_qc_runner --project hanwoo-dashboard --json` passed (`test` 92 passed, lint passed, build passed), `git diff --check` passed, and graph risk `0.00`. Active Hanwoo goal remains open because T-251 is still external/user-owned Supabase password/control-plane resync. Preserve unrelated dirty WIP in root package/workflow files, Blind-to-X locks, Hanwoo `package.json`, shorts-maker-v2 render/bench files, package locks, and setup scripts. |

| Field | Value |
|---|---|
| Date | 2026-05-20 |
| Tool | Claude Code (Opus 4.7 1M) |
| Work | **T-337 완료**: `/goal "최적화 시켜줘"` — AskUserQuestion으로 대상=shorts-maker-v2, 방향=실행/렌더 성능. run manifest `step_timings` 분석으로 렌더가 전체 wall time의 85~89%(990/1110초) 확인, `detect_hw_encoder('auto')`로 이 머신은 h264_qsv 하드웨어 인코딩 사용 확정 → 990초는 인코딩이 아닌 MoviePy 프레임별 Python 합성. 신규 `scripts/bench_render.py`(합성 에셋 결정론적 렌더 핫패스 벤치마크/cProfile, LLM 불필요)로 측정: `color_grade_clip`이 렌더의 ~40%. micro-bench로 `_grade_inplace`가 1080×1920 numpy elementwise 패스 ~10회로 163.5 ms/frame임을 확인 → 패스 ~10→~5로 재작성(밝기+대비 affine 융합 / 채도 3→2패스 / 틴트 strided 3회→벡터 1회 / 프레임당 uint8↔float32 왕복 제거). **`_grade_inplace` 163.5→61.0 ms/frame(2.7배), end-to-end 렌더 ~10% 단축**, 출력 6채널 전부 naive 레퍼런스 대비 max abs diff ≤0.0001(수학적 동일). 검증: color_grading 29 pass(회귀 2건 신규) + 렌더 단위 210 pass + ruff. commit `0930e4a`+`504c709`. |
| Next Priorities | **렌더 최적화 후속(다음 우선순위)**: 컬러 그레이딩 외 잔여 ~65초(4초 벤치)는 ken-burns 모션 per-frame 리샘플 + `CompositeVideoClip.compose_on` 레이어 합성 + MoviePy `transform`/`get_frame` 디코레이터 오버헤드. `python scripts/bench_render.py --scenes N --duration S --profile`로 재현·측정 가능 — 이 벤치마크가 향후 렌더 최적화의 검증 게이트다. 후보: (a) MoviePy `transform` 디코레이터 체인 오버헤드(프레임당 ~35 디코레이터 콜), (b) 캡션 합성 레이어 수 축소, (c) `write_videofile`에 `threads` 전달(qsv엔 무효, libx264 CPU 폴백 경로엔 유효). 경합 주의: 병렬 도구와 공유 인덱스 경합이 잦으므로 부분 커밋은 `git commit -- <pathspec>` 사용. T-251은 여전히 사용자 소유 외부 차단. |

| Field | Value |
|---|---|
| Date | 2026-05-20 |
| Tool | Claude Code (Opus 4.7 1M) |
| Work | **T-305 완료**: blind-to-x `openai` 1.59.9 → 2.37.0 마이그레이션. 탐색 결과 PR #39 triage 당시의 "4개 mock fixture 갱신 필요" 추정은 보수적이었음 — 실제로는 (a) 코드가 `chat.completions.create` / `images.generate` / `AsyncOpenAI` 생성자 등 openai 2.x에서 **변경 없는 안정 API**만 사용하고 `getattr` 방어 접근까지 되어 있으며, (b) 테스트 mock은 클라이언트 생성자를 fake로 교체하는 방식이라 SDK 버전 무관. openai 2.0.0의 실제 breaking change는 Responses API tool-call output 형태뿐인데 blind-to-x는 미사용. **결과: 코드/테스트 변경 0건, 버전 핀만 변경.** `pyproject.toml` openai 핀 갱신 + `projects/blind-to-x/uv.lock` 재생성(openai 항목만 1.59.9→2.37.0, transitive 변화 없음). 검증: openai 2.37.0 설치 후 단위+통합 전체 `1626 passed, 1 skipped, 0 failed`(241s), `ruff check .` 통과. |
| Next Priorities | 라이브 스모크(실 LLM fallback 체인 호출)는 유료 API라 미실행 — mock 기반 1626 테스트 + 안정 API 사용 사실로 갈음. 필요 시 사용자가 `OPENAI_API_KEY` 설정 후 `python main.py --limit 1 --dry-run`으로 확인 가능. **주의**: 로컬에 워크스페이스 uv 마이그레이션 WIP(루트 `pyproject.toml`+`uv.lock`, 둘 다 untracked)가 있어 `projects/blind-to-x`에서 `uv lock` 실행 시 루트 워크스페이스 락이 대상이 됨 — blind-to-x 단독 락 재생성은 루트 `pyproject.toml`을 일시 숨긴 뒤 실행함(복원 완료). 커밋은 `projects/blind-to-x/pyproject.toml`+`uv.lock`+`.ai/*`만 선택 스테이징. T-251은 여전히 사용자 소유 외부 차단. |

| Field | Value |
|---|---|
| Date | 2026-05-20 |
| Tool | Codex |
| Work | **T-336 completed**: closed the last safe `shorts-maker-v2` T-318 Phase 3 item by fixing channel-specific TTS tuning propagation. `MediaStep` now stores `AppConfig._channel_key` and passes it into direct Edge TTS, Chatterbox/CosyVoice premium calls, and Edge fallback calls. This lets `EdgeTTSClient` apply channel-specific prosody instead of silently falling back to default jitter/pitch. |
| Next Priorities | Verification passed: focused TTS routing tests `5 passed`, full `python -m pytest --no-cov tests/unit tests/integration -q --tb=short --maxfail=1 --basetemp .tmp/pytest-tts-channel-key-full-final` passed, targeted Ruff/check/format passed, `project_qc_runner --project shorts-maker-v2 --check lint --json` passed, and graph risk `0.00`. T-318 is now closed. Remaining shorts-maker-v2 backlog is approval-gated T-320 OSS integration. Preserve unrelated dirty WIP in root package/workflow files, Blind-to-X `pyproject.toml`, Hanwoo `package.json`, shorts-maker-v2 `render/color_grading.py` and `scripts/bench_render.py`, package locks, and setup scripts. |

| Field | Value |
|---|---|
| Date | 2026-05-20 |
| Tool | Codex |
| Work | **T-335 completed**: continued the active Hanwoo product-completeness goal by localizing app-level metadata and PWA install copy. `src/app/layout.js` and `public/manifest.json` now use Korean product-ready title/description/short name for browser title, install prompt, and app metadata instead of `Joolife Dashboard` / `Premium Hanwoo Farm Management System`. Commit `62020ec`. |
| Next Priorities | Verification passed: Hanwoo test suite `90 passed`, `npm.cmd run lint`, `npm.cmd run build` (first sandboxed run failed only because Google Fonts fetch was blocked; approved rerun passed), `git diff --check`, direct Hanwoo graph risk `0.00`, and staged `code_review_gate --json` PASS. Commit hook emitted advisory WARN from graph heuristics/unrelated shorts-maker WIP, but direct Hanwoo checks cover the change. Active Hanwoo goal remains open; T-251 is still user-owned Supabase password/control-plane resync. Preserve unrelated dirty WIP in root package/workflow files, Blind-to-X `pyproject.toml`, Hanwoo `package.json`, shorts-maker-v2 media_step files, package locks, and setup scripts. |

| Field | Value |
|---|---|
| Date | 2026-05-20 |
| Tool | Codex |
| Work | **T-334 completed**: continued T-318 for `shorts-maker-v2` and fixed a strict `scene_qc` retry routing bug. Before this pass, any scene with `audio_ok=True` retried as `component="visual"`, so duration/CPS/audio-volume failures reused the same old audio checkpoint and could waste retries without addressing the failing check. `PipelineOrchestrator` now derives the retry component from failed QC checks: audio integrity/timing/volume routes to `audio` or `both`, visual failures route to `visual`, and script-only failures skip media retry and remain surfaced as unresolved. Retry counts now reflect actual regeneration attempts. |
| Next Priorities | Verification passed: focused `test_orchestrator_unit.py + test_qc_step.py` `115 passed`, targeted Ruff and format checks passed, full `python -m pytest --no-cov tests/unit tests/integration -q --tb=short --maxfail=1 --basetemp .tmp/pytest-scene-qc-routing-full` passed, `project_qc_runner --project shorts-maker-v2 --check lint --json` passed, and graph risk `0.00`. Remaining T-318 item is channel TTS speed/voice role tuning. Preserve unrelated dirty WIP in `.ai/GOAL.md`, root package/workflow files, Blind-to-X `pyproject.toml`, Hanwoo `package.json`, package locks, and setup scripts. |

| Field | Value |
|---|---|
| Date | 2026-05-20 |
| Tool | Codex |
| Work | **T-333 completed**: continued the active Hanwoo product-completeness goal by localizing the admin diagnostics surface. `DiagnosticsPageClient` now uses Korean operations copy for loading, errors, status cards, database ledger, raw-data inspector, model selector labels, and dashboard return action instead of English placeholders like `System Diagnostics`, `Database Status`, `Loading records.`, and `Please try again in a moment.` Commit `c0113d9`. |
| Next Priorities | Verification passed: Hanwoo test suite `89 passed`, `npm.cmd run lint`, `npm.cmd run build`, `git diff --check`, direct Hanwoo graph risk `0.00`, and staged `code_review_gate --json` PASS. Commit hook emitted advisory WARN from graph heuristics/unrelated shorts-maker WIP, but direct Hanwoo checks cover the change. Active Hanwoo goal remains open; T-251 is still user-owned Supabase password/control-plane resync. Preserve unrelated dirty WIP in root package/workflow files, Hanwoo `package.json`, shorts-maker-v2 orchestrator files, package locks, and setup scripts. |

| Field | Value |
|---|---|
| Date | 2026-05-20 |
| Tool | Codex |
| Work | **T-332 completed**: continued the active Hanwoo product-completeness goal by polishing checkout/subscription UX copy. `PaymentWidget` now uses Korean product copy for checkout title, widget loading, payment preparing, button amount, timeout, and fallback errors. Subscription success/fail pages no longer expose bare `Loading...`, `Processing...`, `Payment confirmed`, or `Code:` strings; they now render Korean status/fallback copy aligned with the app tone. Commit `8937eb1`. |
| Next Priorities | Verification passed: Hanwoo test suite `88 passed`, `npm.cmd run lint`, `npm.cmd run build`, `git diff --check`, direct Hanwoo graph risk `0.00`, and staged `code_review_gate --json` PASS. Commit hook emitted advisory WARN from graph heuristics, but direct Hanwoo checks cover the change. Active Hanwoo goal remains open; T-251 is still user-owned Supabase password/control-plane resync. Preserve unrelated dirty WIP in root package/workflow files, Hanwoo `package.json`, package locks, and setup scripts. |

| Field | Value |
|---|---|
| Date | 2026-05-20 |
| Tool | Codex |
| Work | **T-331 completed**: continued T-318 for `shorts-maker-v2` and fixed the Gate 4 file-size boundary that held otherwise valid Shorts renders at 50.4MB. `QCStep.gate4_final` now uses named final-size policy bounds `[2,60]MB` instead of a hard-coded 50MB ceiling, aligning QC with the existing standard/premium renderer bitrate caps while still holding oversized files. Added regressions for a 50.4MB pass and a 60.1MB hold. |
| Next Priorities | Verification passed: `python -m pytest --no-cov tests/unit/test_qc_step.py -q --tb=short --maxfail=1 --basetemp .tmp/pytest-qc-size-policy` (`60 passed`), targeted Ruff passed, full `python -m pytest --no-cov tests/unit tests/integration -q --tb=short --maxfail=1 --basetemp .tmp/pytest-qc-size-full` passed, `project_qc_runner --project shorts-maker-v2 --check lint --json` passed, and `PYTHONUTF8=1 python -m code_review_graph detect-changes --repo projects/shorts-maker-v2 --brief` risk `0.00`. Remaining T-318 items are scene_qc strict-default safety analysis and channel TTS voice/speed tuning. Preserve unrelated dirty WIP in root package/workflow files, Hanwoo `package.json`, package locks, and setup scripts. |

| Field | Value |
|---|---|
| Date | 2026-05-20 |
| Tool | Codex |
| Work | **T-330 completed**: continued the active Hanwoo product-completeness goal with a cattle-detail UX polish. Replaced the two browser `prompt()` flows in `CattleDetailModal` for 발정 기록 / 수정 기록 with an in-app date form, explicit cancel/save controls, inline validation, pending save state, lucide action icons, and existing feedback/offline queue handling through `handleUpdateCattle`. Commit `b92249d`. |
| Next Priorities | Verification passed: Hanwoo test suite `86 passed`, `npm.cmd run lint`, `npm.cmd run build`, `git diff --check`, direct Hanwoo graph risk `0.00`, and staged `code_review_gate --json` PASS. The commit hook emitted advisory WARN from stale graph heuristics / unrelated dirty WIP, but direct Hanwoo checks cover the change. Active Hanwoo goal remains open; T-251 is still user-owned Supabase password/control-plane resync. Preserve unrelated dirty WIP in root package/workflow files, Hanwoo `package.json`, shorts-maker-v2 QC files, package locks, and setup scripts. |

| Field | Value |
|---|---|
| Date | 2026-05-20 |
| Tool | Codex |
| Work | **T-328 completed**: continued the active Hanwoo product-completeness goal after confirming T-251 is still external. `npm.cmd run db:prisma7-test -- --live` passed local Prisma/client/adapter checks (`15 passed`) but live health still failed with the same `P2010 / XX000 / (ENOTFOUND) tenant/user postgres.fuemeqmigptwfzqvrpjf not found`. Then tightened the first-run setup flow: the Farm Setup / 운영 준비도 missing-building item now emits `add-building`, `DashboardClient` forwards that quick-action intent, and `SettingsTab` opens the 축사 registration form immediately on arrival. Commit `cc32b52`. |
| Next Priorities | Verification passed: focused Hanwoo tests `85 passed`, `npm.cmd run lint`, `npm.cmd run build`, and direct Hanwoo graph risk `0.00`. Staged code-review gate emitted advisory WARN from broad graph heuristics/unrelated dirty WIP, but direct Hanwoo checks are green. Active Hanwoo goal remains open; T-251 still requires user-owned Supabase password/control-plane resync. Preserve unrelated dirty WIP in root package/workflow files, Hanwoo `package.json`, package locks, shorts-maker-v2 files, and setup scripts. |

| Field | Value |
|---|---|
| Date | 2026-05-20 |
| Tool | Codex |
| Work | **T-327 completed**: continued the "프로젝트 하나 디버깅" goal by selecting the safe `shorts-maker-v2` Phase 3 hook-score issue from T-318. Root cause: `PipelineOrchestrator` calculated `manifest.hook_score` but weak hooks only emitted `hook_score_weak` warnings, so Gate 4 PASS could still mark the job `success`. Added a retryable non-blocking `hook_score` degraded step whenever `score_hook(...).passed` is false, so weak-hook renders no longer enter the upload-ready success path. Full-suite verification exposed two weak test fixtures; preserved the stricter gate by updating fixture hook narration, and extended `hook_scorer` with narrow English contrast/tech specificity support for valid hooks like `Tiny chips, big savings`. |
| Next Priorities | Verification passed: `test_hook_scorer.py + test_orchestrator_unit.py + test_renderer_mode_manifest.py + i18n smoke` `63 passed`; targeted Ruff passed; `project_qc_runner --project shorts-maker-v2 --check lint --json` passed; `PYTHONUTF8=1 python -m code_review_graph detect-changes --repo projects/shorts-maker-v2 --brief` risk `0.00`; full `python -m pytest --no-cov tests/unit tests/integration -q --tb=short --maxfail=1 --basetemp .tmp/pytest-hook-score-full-3` passed. Remaining T-318 items are file-size boundary policy/bitrate, scene_qc strict-default safety analysis, and channel TTS voice/speed tuning. Preserve unrelated dirty WIP in root package/workflow files, Hanwoo files, package locks, and setup scripts. |

| Field | Value |
|---|---|
| Date | 2026-05-20 |
| Tool | Claude Code (Opus 4.7 1M) |
| Work | **T-325 완료** + 미푸시 12커밋 push. 활성 goal(`hanwoo-dashboard` 제품완성형) 진행: App Router에 `error.js`/`not-found.js`/`global-error.js`가 전무해 런타임 에러·잘못된 URL이 Next.js 기본 디버그 화면으로 노출되던 갭을 해소. 로그인 디자인 토큰을 재사용한 브랜디드 상태 페이지 3종(404 서버 컴포넌트 / route error 클라이언트 boundary, retry=`reset()` / global-error 루트 레이아웃 boundary, 인라인 스타일) + `globals.css` `Status Pages` 블록(44줄) + empty-state 패턴 본뜬 source-wiring 테스트. 검증: `npm test` 84 passed/0 fail, `npm run lint` pass, `npm run build` pass(`/_not-found` 정적 프리렌더 확인). commit `c00712d`. 세션 시작 시 `session_orient`로 origin 대비 ahead 12 확인 → 사용자 승인 후 `git push`(`7962830..85b5d31`). |
| Next Priorities | **경합 주의(중요)**: 병렬 도구와 동시 git 작업 시 공유 인덱스 경합이 두 번 발생. (1) 첫 commit `b56592e`가 빈 커밋이 됨(`git apply --cached`와 `git commit` 사이 인덱스 클리어, "PASS (no staged files)"가 단서) → `c00712d`로 재커밋. (2) `[ai-context]` 커밋 `a5fa474`는 의도한 `.ai/*` 4파일 외에 **Codex의 T-326 Farm Setup 피처 코드**(`setup-progress.mjs`/`.test.mjs`, `DashboardClient.js`, `globals.css` setup-progress 블록 168줄)도 함께 담김 — Codex의 `git add`가 내 `git add`↔`git commit` 사이에 끼어듦. **결과적으로 Codex의 T-326 orphan WIP가 `a5fa474`에 정상 커밋됨**(해당 코드는 Codex가 `npm test 84 passed`+build로 이미 검증). 교훈: 부분 커밋은 `git commit -- <pathspec>` 형태(인덱스 무시, 워킹트리에서 해당 경로만)를 쓰면 경합 면역. `b56592e` 빈 커밋은 rebase 위험으로 그대로 둠. hanwoo goal은 계속 진행 중, T-251은 여전히 외부/사용자 소유 차단. |

| Field | Value |
|---|---|
| Date | 2026-05-20 |
| Tool | Claude Code (Opus 4.7 1M) |
| Work | **T-324 완료**: `/goal "제품완성형으로 만들어봐"` — AskUserQuestion으로 대상=blind-to-x, 완료기준=테스트·CI 통과 + 문서·온보딩으로 좁힘. 완성도 감사(completion audit) 수행: blind-to-x는 T-304(2026-05-16)에서 이미 release-ready였고 이번 세션은 검증 + 온보딩 갭 1건 보완. **검증 전부 green**: 단위 `1562 passed, 1 skipped`(247s), 통합 `64 passed`(test_curl_cffi 제외 — CI와 동일), `ruff check .` All checks passed. CI(`full-test-matrix.yml`의 `blind-to-x-tests` 잡)는 동일 unit+integration 커맨드를 main push/PR마다 실행 — 워크스페이스 pnpm WIP diff는 `node-apps` 잡만 수정하고 `blind-to-x-tests`(Python) 잡 무손상 확인. **갭 보완**: `.env.example`이 README "관측성" 섹션이 문서화한 토글 3개(`OPENAI_IMAGE_ENABLED`, `LANGFUSE_ENABLED`, `BTX_USAGE_FORWARD`)를 누락 → 주석과 함께 추가(+5줄). 문서는 이미 충실(README 257 + ops-runbook 204 + operations_sop 97 + notion_view_setup_guide 137 + external-review/). |
| Next Priorities | blind-to-x는 선택 기준(테스트·CI·문서·온보딩) 기준 제품완성형 충족. 비차단 후속: README/ops-runbook의 LLM fallback 목록이 `Moonshot/ZhipuAI`를 포함하나 `pipeline/draft_providers.py`는 anthropic/openai/gemini/xai/ollama만 실제 wiring(DeepSeek은 editorial_reviewer fallback에만 존재) — 문서 정확도 nuance라 범위 밖. 커밋은 `.env.example` + `.ai/*`만 선택 스테이징(루트 pnpm/turbo 마이그레이션 WIP·다른 프로젝트 dirty 파일 손대지 말 것). `.ai/GOAL.md`의 hanwoo 목표는 Codex 소유로 유지. |

| Field | Value |
|---|---|
| Date | 2026-05-20 |
| Tool | Codex |
| Work | **T-326 completed**: continued the active Hanwoo product-completeness goal. Added `src/lib/dashboard/setup-progress.mjs` + tests and rendered a home-screen Farm Setup / 운영 준비도 panel in `DashboardClient.js`. The panel tracks 농장 기본 정보, 축사 구조, 개체 등록, 재고 기준, and 첫 일정, shows progress, and routes incomplete items directly to Settings, cattle add, Inventory, or Schedule. Also corrected the home empty 축사 CTA so it opens Settings instead of the cattle modal. |
| Next Priorities | Verification passed: Hanwoo `npm.cmd test` (`84 passed`), `npm.cmd run lint`, `npm.cmd run build`, `PYTHONUTF8=1 python -m code_review_graph detect-changes --repo projects/hanwoo-dashboard --base HEAD --brief` risk `0.00`, `git diff --check` passed, dev server `/login` returned `200`, and `/manifest.json` returned `application/json`. Active Hanwoo goal remains open; T-251 is still external/user-owned Supabase credential resync. Preserve unrelated dirty WIP in root package/workflow files, package locks for other projects, `setup.bat`, and the pre-existing Hanwoo `package.json` postinstall removal. Note: `globals.css` already contained unrelated status-page styles before/alongside this pass, so review hunks before staging. |

| Field | Value |
|---|---|
| Date | 2026-05-19 |
| Tool | Codex |
| Work | **T-321 completed**: continued from TODO and fixed the safest `shorts-maker-v2` Phase 3 issue. Root cause from `runs/20260519-014816-a37f7826`: `ai_tech` profile used scalar `target_duration_sec: 35`, and `ChannelRouter` converted that into hard QC bounds `[35,35]`, so the otherwise valid 49.8s render was held for duration. Updated `ChannelRouter` so scalar duration remains a generation target while QC uses `qc_min_duration_sec`/`qc_max_duration_sec` or a default ±10s tolerance. Added explicit `ai_tech` QC window `[38,52]` and unit coverage for explicit bounds plus default tolerance. |
| Next Priorities | Verification: focused `test_channel_router.py + test_qc_step.py` `65 passed`; `ai_tech` applied config prints `(38, 52)`; `python -m ruff check .` passed; `project_qc_runner --project shorts-maker-v2 --check lint --json` passed; full `python -m pytest --no-cov tests/unit tests/integration -q --tb=short --maxfail=1 --basetemp .tmp/pytest-t318-20260519` passed. `project_qc_runner --check test` failed only on Windows temp permission lock at `.tmp/project-qc-temp/.../pytest-of-박주호`; same command body passed with explicit basetemp. Remaining T-318 items are hook-score blocking/regeneration, file-size boundary policy or bitrate, scene_qc default safety, and TTS voice/speed tuning. Preserve unrelated dirty WIP in root package/workflow files, package locks for other projects, and `projects/hanwoo-dashboard/package.json`. |

| Field | Value |
|---|---|
| Date | 2026-05-19 |
| Tool | Claude Code (Opus 4.7 1M) |
| Work | **T-320 backlog 등록**: 사용자 "GitHub의 다른 아이디어 중 도움될 것들 검색해서 고도화하자" 요청으로 6개 영역(숏폼 자동화/TTS/자막·word-timing/이미지/비디오/BGM) GitHub OSS 리서치 + 사용자 환경(Intel Iris Xe iGPU, NVIDIA 없음, RAM 15.75GB) 호환성 평가 + Replicate API 클라우드 옵션 결정. **로컬 가능**: WhisperX(BSD-2, CPU int8+medium, T-19 직접 해결) + OpenVoice v2(MIT, 한국어 native). **Replicate 필요**: LTX-Video(Apache 2.0, ~$0.05/clip) + ACE-Step v1.5(Apache 2.0, ~$0.10/track). **제외**: Fish Speech("FISH AUDIO RESEARCH LICENSE" 위반 시 조치 경고). 같은 세션에서 영상 1건(`20260519-013539-134a5783`) 추가 생성·검증으로 내 commit `49668c8`(해상도 1080x1920 강제) 효과 확인 — status hold→pass, scene_qc 7/8→8/8, sentiment neutral→awe i=3, audio_peak 정상. 잔존 약점은 Hook curiosity 0.0(non-blocking). 사용자 결정: 원 goal 달성으로 보고 OSS 도입은 새 goal로, Replicate 소액 테스트 $1~5/월 OK. |
| Next Priorities | T-320 우선순위 (다음 세션): (1) WhisperX `pip install whisperx` → `pipeline/media/audio_mixin.py`의 OpenAI Whisper transcribe_audio() drop-in 교체 → 영상 1건으로 karaoke 정상 검증(T-19 자동 해소). (2) OpenVoice v2 providers cascade `edge-tts → openvoice → openai` 추가. (3) Replicate 가입 후 LTX-Video 1건 테스트($0.05) → hook/closing 씬만 영상화 cascade. (4) ACE-Step BGM Lyria cascade에 추가. 메모리 `shorts_v2_oss_shortlist_20260519`에 4개 OSS 디테일(install/license/통합 패턴/한계) 보존. 내 이번 세션 commit `49668c8`는 다른 도구 commit과 분리되어 origin 대비 ahead 상태(push 사용자 승인 별도). 같은 세션 다른 도구 작업: Codex T-319 Hanwoo empty states, Claude T-317 shorts-maker-v2 Phase 1+2 — 모두 commit + ai-context 정착됨. |

| Field | Value |
|---|---|
| Date | 2026-05-19 |
| Tool | Codex |
| Work | **T-319 completed**: continued the active Hanwoo quality goal with a low-risk first-run UX pass. Added `components/ui/empty-state.js`, replaced passive empty messages in Sales/Schedule/Inventory tabs with icon-led CTA states (`매출 기록`, `일정 추가`, `재고 등록`), and added `src/lib/empty-state-wiring.test.mjs` so the wiring stays covered without browser-only assumptions. |
| Next Priorities | Verification passed: Hanwoo `npm.cmd test` (`79 passed`), `npm.cmd run lint`, `npm.cmd run build`, code-review graph risk `0.00`, and dev server `/login` returned `200` at `http://127.0.0.1:3001/login`. `node_modules` had to be repaired with `npm.cmd ci --ignore-scripts`; npm reported existing audit warnings (6 moderate, 2 high). A locked broken install folder was moved under `.tmp/node_modules.broken-20260519110922` and may disappear after the OS releases the native Tailwind binary lock. Preserve unrelated dirty WIP in root package files, `.github/workflows/full-test-matrix.yml`, package locks for other projects, and `projects/hanwoo-dashboard/package.json`. |

| Field | Value |
|---|---|
| Date | 2026-05-19 |
| Tool | Claude Code (Opus 4.7 1M) |
| Work | **shorts-maker-v2 Phase 1+2 품질 개선 완료** (commits `2b09759` feat + `8c90b36` ai-context). `/goal "shorts-maker-v2 결과물이 바로 유튜브에 올릴 수 있을 정도 고퀄"` 진행. 2회 실험 run 으로 8개 갭 식별 후 6개 해소. 해소된 갭: (#5) hook hard cap 15→40자 + 단어 경계 트림, (#3) Structure Gate 2 가 한국어 조사 stem + core_message/visual_keywords 다중 신호로 chronic 실패 해소, (#6) 4개 image entry-point에 "No text/letters" negative 자동 부착, (#1) TTS provider openai→edge-tts 전환으로 모든 채널 Azure-voice 호환 + 무료 + _words.json 자동 생성, (#2) 5개 채널 topic 50개 사실 기반 재설계, (#4+#8) Whisper/karaoke/color/audio post silent-fail이 manifest.degraded_steps 로 drain. **Validation run 완료** (`runs/20260519-014816-a37f7826`, 1110s total, $0.04): pipeline FAIL이지만 영상·썸네일·SRT·manifest 전부 생성. Before/After 비교 — scene_qc_results null→8/8 pass, audio_peak_probe_ok false→true, caption_fallback 8→0, karaoke kc_*.png 0→25, structure intent 보일러플레이트→LLM-quality, tone generic→rich. 썸네일에 영어 텍스트 artifact 없음. 잔여 hold 원인은 ship 차단 임계(Duration 49.8s vs channel target [35,35] + 파일크기 50.4MB vs [2,50]MB) — Phase 3 영역. |
| Next Priorities | (1) shorts-maker-v2 commits `2b09759` + `8c90b36` push 사용자 승인 필요(local main 2 ahead). (2) Phase 3 후보 (T-318): gate3/gate4 duration 임계 완화(channel target ±10초 마진), file size 상한 60MB로 올리거나 bitrate 조정, hook_score<0.6 시 재생성 강제 게이트(현재 advisory만), 채널별 TTS 속도 미세조정. (3) 다른 도구의 미커밋 WIP 보존: `.github/workflows/full-test-matrix.yml`, `projects/hanwoo-dashboard/**` (package.json/lock + InventoryTab/SalesTab/ScheduleTab + middleware/manifest), `projects/blind-to-x/uv.lock`. |

| Field | Value |
|---|---|
| Date | 2026-05-19 |
| Tool | Codex |
| Work | **T-316 완료**: user requested GitHub idea search + blind-to-x 고도화. Checked comparable public workflows: `langchain-ai/social-media-agent` emphasizes human-in-the-loop review/scheduling, and NotionToTwitter keeps post date/status/error/URL tracking inside Notion. Applied that pattern to blind-to-x instead of adding risky auto-posting: added X publishing operation metadata (`X Publish Status`, `X Scheduled At`, `X Published At`, `X Post URL`, `X Publish Error`) to the Notion schema resolver/sync script, future upload payloads, the `X 업로드 카드` `게시 운영` checklist, and backfill defaults. Live Notion schema was patched from 43 to 48 properties, latest 5 pages were backfilled to `Ready to Post`, then schema sync returned NOOP and backfill dry-run returned candidates 0. |
| Next Priorities | Verification passed: `test_notion_upload.py + test_backfill_notion_review_columns.py` 44 passed, targeted Ruff passed, `PYTHONUTF8=1 python -m code_review_graph detect-changes --repo projects/blind-to-x --brief` risk 0.00. This was Notion read/write plus deterministic tests, not a live X posting run. Preserve unrelated current dirty WIP in `projects/shorts-maker-v2/**`, root package files, and `projects/hanwoo-dashboard/package.json`. |

| Field | Value |
|---|---|
| Date | 2026-05-19 |
| Tool | Codex |
| Work | **T-315 완료**: active thread goal `blind-to-x 의 결과물이 좀더 x에 업로드에 적합한 형태로 출력되어 노션에 업로드 되었으면 좋겠어`의 live Notion 반영까지 진행. Notion doctor PASS, `sync_notion_review_schema.py --config config.yaml` NOOP로 실제 DB가 43개 속성과 `X` multi-select 옵션을 이미 갖춘 것을 확인. 최근 Notion 5개 페이지를 read-only 점검했더니 모두 과거 `숏폼`/`채널 초안` 구조라서 `scripts/backfill_notion_review_columns.py`에 `--append-x-upload-card` 옵션을 추가하고, 최근 5개 페이지에 `publish_platforms=['X']`와 copy-ready `X 업로드 카드`/`X 본문`/`첫 답글 / 출처 메모` 블록을 실제 append. 재검증에서 최근 5개 모두 `platforms=['X']; has_x_card=True; has_x_body=True; has_reply=True`, `verified_x_ready=5/5`. |
| Next Priorities | 새 backfill 옵션 검증 통과: `test_notion_upload.py + test_backfill_notion_review_columns.py` 44 passed, targeted Ruff passed, graph risk 0.00. Live LLM 생성은 하지 않았고 Notion read/write만 수행. 현재 unrelated dirty WIP는 `projects/shorts-maker-v2/**` 여러 파일과 신규 `_prompt_filters.py`/`test_prompt_filters.py`; 이번 blind-to-x 작업과 섞지 말 것. |

| Field | Value |
|---|---|
| Date | 2026-05-19 |
| Tool | Codex |
| Work | **Hanwoo PWA asset routing polish**. While validating the new quick-action UX, Playwright surfaced a login-page console error: `/manifest.json` was being routed through the auth proxy and returned login HTML instead of JSON. Updated `projects/hanwoo-dashboard/src/proxy.js` so manifest/icons/service-worker assets bypass auth before login. |
| Next Priorities | Verification passed: Hanwoo `npm.cmd test` (`77 passed`), `npm.cmd run lint`, `npm.cmd run build`; direct `Invoke-WebRequest http://127.0.0.1:3001/manifest.json` returns `200 application/json`. Quick Action Panel itself is already committed and pushed in `e0c80d1`. Remaining Hanwoo blocker is still T-251, user-owned Supabase credential resync. |

| Field | Value |
|---|---|
| Date | 2026-05-19 |
| Tool | Gemini (Antigravity) |
| Work | **Shorts Maker V2 + Hanwoo Dashboard 고도화**. (1) shorts-maker-v2: scene QC 활성화(`scene_qc_enabled: true`, strict 모드), 영상 길이 완화(`[38,52]`초), 한국어 훅 품질 가이드라인 강화(조건부 `hook_rules_ko`), 감정 키워드 5도메인 확장 → 커밋 `f119b30`. (2) hanwoo-dashboard: Quick Action Panel(개체등록/출하/일정/재고 퀵액션) + 탭 연동(`quickActionIntent`) → 커밋 `e0c80d1`. (3) 전체 검증 통과(shorts pytest OK, hanwoo test 77 passed + lint + build). (4) `git push origin main` 완료(`7913df0..e0c80d1`). |
| Next Priorities | Git worktree 깨끗, origin/main 완전 동기화(`e0c80d1`). 남은 TODO: T-251(Supabase 비밀번호 — 사용자 조치), T-305(openai 2.x — 저우선). IN_PROGRESS 없음. |

| Field | Value |
|---|---|
| Date | 2026-05-19 |
| Tool | Codex |
| Work | Completed second Hanwoo UX/UI pass in commit `94d043e` (`feat(hanwoo-dashboard): polish operator login ux`). Reworked `/login` into a clearer operator-first flow: labelled fields, lucide field icons, password visibility toggle, disabled/pending submit states, friendlier error message, mobile-safe card layout, status chips, and favicon fallback to remove `/favicon.ico` 404. Also replaced bottom tab emoji navigation in `components/widgets/widgets.js` with lucide icons and `aria-current` for steadier cross-platform UI. Preserved unrelated `blind-to-x` and Claude `.ai` WIP. |
| Next Priorities | Verification passed: Hanwoo `npm.cmd test` (`77 passed`), `npm.cmd run lint`, `npm.cmd run build`; Playwright CLI mobile/desktop login visual check passed with console errors 0 after favicon fix. Pre-commit graph gate emitted advisory WARN risk=0.50, partly polluted by unrelated dirty `blind-to-x` WIP, but commit succeeded and direct Hanwoo checks are green. Continue active Hanwoo goal with authenticated dashboard visual QA once DB/auth access is available; T-251 remains external Supabase credential reset. |

| Field | Value |
|---|---|
| Date | 2026-05-19 |
| Tool | Codex |
| Work | **T-310 완료**: active thread goal `blind-to-x 의 결과물이 좀더 x에 업로드에 적합한 형태로 출력되어 노션에 업로드 되었으면 좋겠어` 방향으로 Notion 리뷰/업로드 표면을 X-first로 정리. `pipeline/notion/_upload.py`가 `숏폼` 플랫폼 라벨 대신 `X`를 쓰고, 페이지 본문에 `X 업로드 카드`를 추가해 `X 본문`, `첫 답글 / 출처 메모`, 280자 글자 수, 링크/해시태그 분리, 업로드 순서를 바로 보이게 함. 기존 Twitter 초안 중복 노출은 제거하고 Threads/뉴스레터/블로그는 `보조 채널 초안`으로 밀어냄. `scripts/backfill_notion_review_columns.py`와 `scripts/sync_notion_review_schema.py`도 새 `X` 라벨을 인식/생성하되 기존 `숏폼`은 과거 데이터 호환용으로 유지. README/ops-runbook/Notion view guide도 `X 업로드 카드`와 `X 후보` 기준으로 갱신. |
| Next Priorities | 실제 Notion DB에 새 multi-select 옵션을 반영하려면 필요 시 `py -3 scripts/sync_notion_review_schema.py --config config.yaml --apply`를 `projects/blind-to-x`에서 실행. 검증은 focused unit/ruff/graph까지 통과했지만 live Notion 업로드는 API를 쓰므로 이번 세션에서는 실행하지 않음. 현재 별도 변경으로 `projects/blind-to-x/uv.lock`, `projects/hanwoo-dashboard/src/app/globals.css`, `projects/hanwoo-dashboard/src/app/login/page.js`, `.playwright-cli/`, `output/`가 보이며 이번 Codex 작업으로 되돌리지 말 것. |

| Field | Value |
|---|---|
| Date | 2026-05-19 |
| Tool | Claude Code (Opus 4.7 1M) |
| Work | **T-309 완료**: `/goal "blind-to-x 이거 생성물 퀄리티 올리기로 했 별로고 왜 작동안해/"` — 4시간 스케줄러가 매번 모든 아이템을 quality gate fail로 떨어뜨려 Notion 발행 0건. 캐시된 노션 드래프트는 (a) 3안 묶음 강제 (b) 매번 "~에서 봤는데" 도입 강박 (c) "여러분 생각은?" CTA 마무리 (d) 이모지 폭격 (e) "시그널/민낯/끝판왕" 인플루언서 어휘 — `user_shorts_philosophy` 메모리(CTA 금지, 조용한 이야기, 여운으로 끝남)와 정면 충돌. 5계층 강제(`prompts.yaml` + `editorial.yaml` + `examples.yaml` + `draft_quality_gate.py` PLATFORM_RULES + `draft_prompts.py` 하드코딩 fallback/selection_brief)를 한 번에 정비. `PLATFORM_RULES.*.require_cta` True→False로 풀고 `_has_generic_cta`는 require_cta 가드 밖으로 빼서 "여러분 생각은?"류는 항상 error로 차단. `topic_hooks.*.cta`와 `threads_cta_mapping` 모두 빈 문자열, `golden_examples_threads`를 여운 마무리로 재작성, `cliche_watchlist`에 인플루언서 어휘 13개 추가, `system_role`을 "조용한 해설자"로 재정의, 모든 twitter/threads/naver_blog 템플릿을 1안 + CTA 금지 + 도입 강박 해제로 교체. 영향 받는 단위 테스트 4개 정비(`test_quality_gate_and_scenes`, `test_draft_quality_gate_deep`, `test_draft_generator_multi_provider`, `test_quality_improvements`). 검증: `pytest --no-cov tests/unit` → **1560 passed, 1 skipped, 0 failed**. LLM dry-run(anthropic) 1회 + 수동 스케줄러 `python main.py --limit 2 --dry-run` 실행 → 이전 13:00 결과(`Exit 1: All 4 items failed, Quality Score 0.0`)에서 **`OK 2 / FAIL 0, Quality Score 85.0`** 으로 회복. 실제 새 톤 드래프트 2건 캐시 확인 — CTA 없음, 이모지 0개, 1개 안, "~에서 봤는데" 도입 없음, 인플루언서 어휘 없음, 여운 마무리, creator_take 포함 100% 통과. 커밋: `4628bb8 feat(blind-to-x): shorts 철학 적용 — 조용한 해설자 톤으로 전환` (10 files +202/-172). 첫 commit 시 ruff format 실패로 abort된 직후 hook이 자동으로 .ai/* 만 stage해서 `81b36db`가 의도와 달리 ai-context만 포함됐고, 코드 변경분을 별도 `4628bb8`로 다시 commit한 형태. push는 사용자 승인 별도. |
| Next Priorities | 사용자 승인 시 `git push` (현재 origin 대비 4 commits ahead: `b94c66c` `32269c2` `81b36db` `4628bb8`). 다음 자동 스케줄(17:00) 결과 로그(`projects/blind-to-x/.tmp/logs/scheduled_*.log`)에서 새 톤이 Notion에 실제로 발행되는지 확인 권장. 별개 이슈로 남은 것: (1) `MLScorer: training failed: y contains 1 class` (yt_views 0건 cold-start, 학습 데이터 누적 전까지 발생) — `pipeline/ml_scorer.py`에서 1-class 가드 추가하면 해소. (2) `uv.lock` 미커밋 변경분(이전 세션부터 남은 dirty). (3) T-251 Supabase 비밀번호 리셋은 여전히 사용자 액션 대기. |

| Field | Value |
|---|---|
| Date | 2026-05-18 |
| Tool | Codex |
| Work | Activated the new `/goal` in `.ai/GOAL.md`: `hanwoo-dashboard` quality uplift so other people would want to use it. Completed first safe UX/product pass as **T-307** in commit `f222385`. Added `projects/hanwoo-dashboard/src/lib/dashboard/today-focus.mjs` and tests, then rendered a home-screen Today Brief panel in `DashboardClient.js` with CSS in `globals.css`. The panel prioritizes offline sync state, critical breeding/calving alerts, next open schedule item, low-stock inventory, and monthly sales into clickable actions. Preserved unrelated dirty `projects/blind-to-x/uv.lock`. |
| Next Priorities | Active goal remains open for additional Hanwoo polish. New safe TODO **T-308**: browser visual QA of Today Brief, then consider replacing remaining emoji-heavy navigation/widget affordances with lucide icons where it improves polish. Verification passed: `npm.cmd test` (`77 passed`), `npm.cmd run lint`, `npm.cmd run build`. Pre-commit graph gate emitted advisory WARN risk=0.35 for `DashboardClient` test-gap heuristics despite direct helper coverage and full Hanwoo checks. Dev server is running at `http://127.0.0.1:3001`. T-251 remains user-owned external Supabase password/pooler blocker; do not retry live Prisma until credentials are reset/resynced. |

| Field | Value |
|---|---|
| Date | 2026-05-18 |
| Tool | Claude Code (Opus 4.7 1M) |
| Work | **T-306 completed**: open-PR audit + cleanup. With `T-251` the only TODO and IN_PROGRESS empty, signal was 20 Dependabot PRs all `BLOCKED` (REVIEW_REQUIRED, not CI) plus weekly `pip in /.` Dependabot run failing with `dependency_file_not_found: No files found in /`. Triaged into Tier A (11 safe minors/patches, all CI green), Tier B (#51/#54 React pair where the FAIL was only the `dependabot` auto-merge workflow, not the build), Tier C (#50 typescript 5→6 MAJOR + #52 react-dom solo bump diverging from react peer — both real build failures), Tier D (#37/#39/#41 MAJOR risk), Grouped (#48 next-ecosystem). User approved: squash-merge Tier A+B+#48 via `--admin`, close Tier C, diagnose root pip failure. Squash-merged 14 PRs in 3 project-disjoint batches; #47 (word-chain tailwindcss) and #54 (hanwoo react) hit lockfile drift after sibling merges → `@dependabot rebase` + 60 s wait + re-merge worked. Picked up the missed #44 pyyaml after. Closed 5 PRs with sourced rationale (#37/#41 frozen word-chain MAJOR not worth migration; #39 backlogged as T-305 epic — `pipeline/draft_providers.py` + `pipeline/image_generator.py` already use v1+ `AsyncOpenAI` so v2 migration is feasible but needs 4 mock-file refresh + live smoke, ~½–1 day). Root pip Dependabot diagnosis: `.github/dependabot.yml` entry 1 had `directory: "/"` but no Python manifest at repo root — the intended workspace is `workspace/pyproject.toml`. Fixed to `directory: "/workspace"` (PEP 621 project) in commit `32269c2`. Local main now `ahead 2` of `origin/main` (`b94c66c` prior-session ai-context + `32269c2` dependabot.yml fix); push not performed pending user approval. |
| Next Priorities | Push pending: `b94c66c` + `32269c2` + this session's ai-context commit need explicit user approval before `git push`. T-305 (openai 2 migration epic) is the only new TODO. T-251 remains the lone external blocker (user-owned Supabase password reset). Code-review gate PASSed risk=0.00 on the dependabot.yml change; the 15 merged Dependabot PRs' CIs ran on `origin/main` post-merge. |

| Field | Value |
|---|---|
| Date | 2026-05-18 |
| Tool | Gemini (Antigravity) |
| Work | **전체 QC 재검증 완료**. 4개 프로젝트 전수 검증: blind-to-x (1560 passed, 1 skipped), shorts-maker-v2 (1422 passed, 12 skipped), hanwoo-dashboard (ESLint 0 warnings + Build OK), knowledge-dashboard (ESLint 0 warnings + Build OK). code_review_gate.py PASS (risk=0.00). PowerShell stderr NativeCommandError로 인한 shorts-maker false negative 현상 확인 및 정리. |
| Next Priorities | T-251 사용자 조치 대기 (Supabase 비밀번호 리셋). 기술 부채: google.generativeai→google.genai 마이그레이션, Pydantic V1 Python 3.14 호환성. |

| Field | Value |
|---|---|
| Date | 2026-05-18 |
| Tool | Codex |
| Work | Re-oriented the workspace after the user asked to understand and proceed. Confirmed `main` is clean and synchronized with `origin/main` (`ahead=0`, `behind=0`, no dirty files), no active goal, one TODO, and product readiness `94 / blocked` only because `hanwoo-dashboard` T-251 is still open. Retried `projects/hanwoo-dashboard` live Prisma E2E with `npm.cmd run db:prisma7-test -- --live`; local Prisma/client/adapter checks passed, but live connection health still failed with `P2010` / `XX000` / `(ENOTFOUND) tenant/user postgres.fuemeqmigptwfzqvrpjf not found`. |
| Next Priorities | No repo-side fix is available for T-251. User must reset/resync the Supabase database password in the Supabase Dashboard, update `projects/hanwoo-dashboard/.env` if the connection string changes, then rerun `npm.cmd run db:prisma7-test -- --live`. |

| Field | Value |
|---|---|
| Date | 2026-05-16 |
| Tool | Claude Code (Opus 4.7 1M) |
| Work | **T-304 completed**: blind-to-x promoted to release-ready state per `/goal "프로젝트 하나 고도화된 완성품으로 만들어놔"` (scope narrowed via AskUserQuestion to blind-to-x, release-ready criterion). Five release criteria audited: (1) E2E pipeline already shipping, (2) CI green per `session_orient` + `full-test-matrix.yml` `blind-to-x-tests` job (20-min budget, paths verified), (3) docs refreshed below, (4) regression tests confirmed for viral boost / NLM enricher / image upload, (5) **closed**: added opt-in `BTX_USAGE_FORWARD=1`-gated `_maybe_forward_to_workspace_usage` in `projects/blind-to-x/pipeline/cost_tracker.py`, called from both `add_text_generation_cost` (Anthropic cache tokens included) and `add_dalle_cost` (model=`dall-e-3`, `endpoint=blind-to-x.dalle_image`). Mirrors blind-to-x text+image costs into workspace `.tmp/workspace.db` `api_calls` so `api_usage_tracker alerts` (fallback rate / cost spike / dead provider) finally covers blind-to-x (was 16 rows total before). Added 3 regression tests in `tests/unit/test_cost_tracker_extended.py` (forwarder invocation, env-gate disabled/enabled, error swallowing — linter auto-corrected the fake-module pattern from `type("M", ...)()` to `types.SimpleNamespace` to keep `log_api_call` unbound). Docs refresh: fixed `tests_unit` → `tests/unit` in README + ops-runbook; `pip install -r requirements.txt` → `pip install -e .[dev]` (pyproject-only project); rewrote stale "3시간마다 GitHub Actions" claim to point at `full-test-matrix.yml`; added Observability section; updated external-review README + file-manifest to reference `rules/` (D-031 5-file split) instead of removed `classification_rules.yaml`. |
| Next Priorities | Verification: `py_compile` + targeted `ruff check` PASS on `pipeline/cost_tracker.py` + `tests/unit/test_cost_tracker_extended.py`; lint pass confirmed earlier by `project_qc_runner.py --check lint`. Local pytest streaming was blocked by a session-specific subshell capture issue (CMD `cd /d` fails with `CD_EXIT=123` on Korean path; matches `windows_korean_path_encode_strict` minefield) — CI on push will execute the 3 new tests. To enable the new forwarder in production, set `BTX_USAGE_FORWARD=1` in `.env` (off by default to preserve hermetic tests). Remaining external blocker is still T-251 (user-owned Supabase password reset). |

## Notes

- **T-251 (active blocker)**: Supabase database password desynchronization. User must reset password via Supabase Dashboard (Project Settings > Database), then update `projects/hanwoo-dashboard/.env`.
- **Origin sync**: As of 2026-05-19, `main` is synchronized with `origin/main` and the worktree is clean.
- Older addenda archived in `.ai/archive/HANDOFF_archive_2026-05-15.md` and `.ai/archive/HANDOFF_archive_2026-05-19.md`.
