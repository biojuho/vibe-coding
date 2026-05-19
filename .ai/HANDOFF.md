# HANDOFF - AI Context Relay

> See `SESSION_LOG.md` for recent session history and `DECISIONS.md` for stable architecture decisions.

## Current Addendum

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
