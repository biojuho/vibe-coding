# HANDOFF - AI Context Relay

> See `SESSION_LOG.md` for recent session history and `DECISIONS.md` for stable architecture decisions.

## Current Addendum

| Field | Value |
|---|---|
| Date | 2026-06-18 (hanwoo lint fix) |
| Tool | Claude Code (Opus 4.8) |
| Work | **hanwoo-dashboard React 19 lint 에러 7건 수정 (commit 5a9946c6, 10파일)** — 의존성 업그레이드(62685046)가 react-hooks 7.1.1로 surface한 기존 main lint red 정리. set-state-in-effect ×5(login/Inventory/Sales/Schedule/Diagnostics)는 `queueMicrotask` 디퍼([[react19_setstate_in_effect_rule]]) + Diagnostics는 기존 deferDiagnosticsTask 재사용. React Compiler memoization ×2(DashboardClient handleTabChange/handleQuickAction)는 useCallback deps에 안정 setter `setActiveTab` 추가. source-grep 테스트 4건(empty-state-wiring/home-market-copy/tab-header-accessibility/error-pages-wiring) 디퍼 패턴으로 정합화. **검증: eslint 0 errors(잔여 3건 의도된 exhaustive-deps isLoading 경고), node --test 2419 pass/0 fail.** 잔여 warning 3건은 isLoading 의도적 deps 제거(render loop 회피)라 미수정. |
| Next Priorities | hanwoo 이제 lint+test green. next build는 CI(Postgres 서비스 필요)에서 검증. 의존성 업그레이드 보류 2건(eslint10/pnpm11)은 업스트림/CI 조정 대기. |

| Field | Value |
|---|---|
| Date | 2026-06-18 (쥬팍식 X 본문) |
| Tool | Claude Code (Opus 4.8) |
| Work | **blind-to-x X 본문 쥬팍식 4단 전환 (/goal)**. X 본문 = 훅(hot)/팩트본문(cold)/요약한줄(cold)/느낌점(hot,펀치라인) 4단 블록 강제. 3계층 동시 정비: ① 프롬프트 `rules/prompts.yaml` twitter.standard 재작성(thread 키 제거, draft_formats=standard만), system_role "여운/의견 안 밀기" 제거; `draft_prompts.py` `_build_twitter_block_from_request`(thread 분기 삭제→항상 standard), `_format_research_context_block`(가치선언/보편환원 강제→금지), selection_brief·fallback·CTA fix instruction 여운→펀치라인. ② 게이트 `draft_quality_gate.py` `_add_jupak_structure_checks`(twitter 한정, 4단블록·'~다'종결·추상어동어반복=**warning**; 280초과·CTA=기존 **error 차단**). ③ 노션 `notion/_upload.py` `_build_upload_children` 재정렬: X카드+원문만 펼침, 검토요약·보조채널·진단·부가산출물 접힘 토글. 지시문 `directives/x_content_curation.md` §4 쥬팍 4단으로 교체. 신규 `tests/unit/test_jupak_x_body.py`(10), 기존 13개 테스트 갱신. |
| Verify | blind-to-x unit **3100 passed / 15 skipped / 0 failed** (maxfail 없이), ruff clean, project_qc_runner passed. 미커밋(사용자 커밋 미요청). |
| Next Priorities | (1) 원하면 pathspec 한정 커밋(위 6파일+테스트, [[multi_tool_git_index_race]]). (2) "threads 없애"=X thread 포맷으로 해석 — Meta Threads SNS 채널 전체 제거 필요시 별도 확인. (3) 실제 LLM dry-run으로 4단 산출 확인 권장. |

| Field | Value |
|---|---|
| Date | 2026-06-18 (의존성 업그레이드) |
| Tool | Claude Code |
| Work | **/goal "최신버전 업그레이드" → 워크스페이스 전체 의존성 최신화 (commit 62685046, 12파일 pathspec 한정)**. Node 6개 매니페스트 + Python(blind-to-x) 핀 4건. **검증환경 발견**: 이 PC에서 `npm install`(full)은 정상(게임 from-scratch 236pkg/29s) — 한글경로 깨짐은 pnpm 전용. blind-to-x: anthropic 0.105→0.109, openai 2.41→2.43, aiohttp 3.13→3.14, bs4 4.14→4.15 + root uv.lock 재생성 + 4종 import-smoke green. word-chain(25t)/suika(63t) vitest+eslint+vite build green. hanwoo(2419t)/knowledge(73t+lint) green. root biome 2.5.0/turbo 2.9.18. pnpm-lock.yaml(프론트 CI 권위 lock, pnpm-workspace=projects/*) `--lockfile-only` 재생성(v9.0 유지). **CI 모델**: Python은 pyproject 직접 pip 설치(uv.lock 미사용), 프론트는 `pnpm install` 루트 lock(per-project package-lock.json은 Dependabot 전용 = 이중 lock). **보류**: eslint hanwoo/knowledge 9.39.4 유지(eslint-config-next 16의 ts-eslint 8.x가 eslint10 scopeManager.addGlobals 미지원→런타임 크래시 재현); pnpm 9→11 메이저(CI+lockfile 동시조정). |
| Next Priorities | (1) **hanwoo lint 7건**(set-state-in-effect×5+memoization×2)은 react-hooks 7.1.1 기존 main 이슈 — `queueMicrotask`로 별도 수정. (2) push 후 CI(blind-to-x 3.12 pytest)로 Python 4핀 전체 검증. 상세 TASKS.md TODO 최상단. |

| Field | Value |
|---|---|
| Date | 2026-06-18 |
| Tool | Claude Code |
| Work | **blind-to-x "노션 발행 안 됨" 근본원인 = Playwright Chromium 바이너리 소실 (Notion 아님)**. `ms-playwright`가 ~06-11 비워져 매 스케줄 스크랩이 `BrowserUnavailableError: ...chromium_headless_shell-1208...`로 죽음 → 0 posts → 노션 업로드 0건, ~7일 silent(TELEGRAM_BOT_TOKEN 미설정이라 무알림). Notion 경로는 전부 정상(notion_doctor PASS / 격리 pages.create OK / 실제 `NotionUploader.upload()`+children OK) — red herring. 수리: `py -3 -m playwright install chromium`(글로벌 3.14/pw1.58→build1208) + 루트 `.venv`(3.11/pw1.60→build1223) 둘 다 설치. 자가치유: `run_scheduled.py`에 `build_preflight_tasks()` 추가(스크랩 전 idempotent `playwright install chromium`, non-fatal, sys.executable 기준) + 회귀테스트 `workspace/tests/test_auto_schedule_paths.py::test_run_scheduled_installs_playwright_browser_preflight`. 검증: 실제 `main.py --trending` 재실행 → Blind 15/Ppomppu 15 수집, 노션 카드 2건 업로드(요약 OK 2/FAIL 3 — 품질게이트 정상). |
| Next Priorities | (1) 다음 스케줄 런(매 4h) 로그에서 "Uploading to Notion" 재확인. (2) 부수 미수정: NotebookLM enricher 1차 모델 `gemini-2.0-flash` 404(폐기)→claude 폴백되나 모델명 갱신 권장. (3) 7일 silent의 근인은 알림 부재 — TELEGRAM_BOT_TOKEN 설정 또는 watchdog가 "노션 업로드 N일 없음" 감지하도록 강화 검토. (4) `run_scheduled.py`+테스트 커밋 미실행(dirty 멀티툴 트리, main 브랜치) — 사용자 승인 시 pathspec 한정 커밋. |

| Field | Value |
|---|---|
| Date | 2026-06-17 (5차) |
| Tool | Claude Code |
| Work | **자율 품질 루프 5차 — 렌더 파이프라인 7건 + hanwoo 4건 수정 (commits f9de0935, 341a4759)**. shorts-maker-v2: bookend clip.duration=None → min() TypeError (RC-BBC001). video clip.duration=None 시 with_duration() 미호출 (RS-BBC001). BGM 0.5초 미만 클립 루프 누락 (>= 0.5 조건 제거). all_clips 비었을 때 concat 전 조기 ValueError. zip(scene_plans, scene_assets) strict=False → True. zip(scene_roles, scene_durations) strict=False → True. 회귀 테스트 4건 (RC-BBC001, RS-BBC001, RS-BGM001, RA-SFX003). hanwoo-dashboard: cattle.js 이력 문자열 data.* → payload.* (3곳). useCattlePagination/useSalesPagination/useCursorPagination isLoading useCallback deps 제거. |
| Next Priorities | (1) knowledge-dashboard, blind-to-x 남은 버그 수정 계속. (2) 자율 루프 유지 — 다음 스캔 배치 시작. |

| Field | Value |
|---|---|
| Date | 2026-06-17 (4차) |
| Tool | Claude Code |
| Work | **자율 품질 루프 4차 — HIGH/MED 버그 8건 수정 (commit d365e94c)**. shorts-maker-v2: `media_step._process_one_scene` audio/image 실패 시 `raise` → `(None, failures)` 반환 (구조적 실패정보 보존); `run()` None asset 감지 후 raise; `run_parallel` None asset 처리. `script_step` `channel_duration_override=0` 거짓 판단 수정 (`is not None`). `render_effects._pan_horizontal` x1 우측 경계 overflow 클램프. `orchestrator` Gate3 미디어 QC 실패 → `manifest.degraded_steps` 추가. `audio_mixin` pending warnings에 `scene_id` 키 추가. `fallback_mixin` `scene_id` str→int. blind-to-x: `persist_stage` `update_page_properties()` 반환값 캡처 + errors[] 갱신. `notion/_cache` url_prop 접근 try 블록 내부로 이동 (KeyError→None). `notion/_query` `_db_properties[prop_name]` → `.get()` 기본값 "select". 회귀 테스트 6개(MS-ANA001/002/003, SS-CDO001, NQM-PBS001, NC-IDC001). shorts-maker-v2 1982 green, blind-to-x 3083 passed. |

| Field | Value |
|---|---|
| Date | 2026-06-16 |
| Tool | Claude Code |
| Work | **자율 품질 루프 3차 — 구조적·프로덕션 버그 9건 수정 (2 commits, fb717608, 912f9975)**. shorts-maker-v2: planning `blocking=True→False` (주석과 일치), ResearchStep에 항상 실제 `llm_router` 전달, QC Gate4 `ffprobe` 미설치 시 false-positive HOLD 방지, fallback `closing` 씬 `scene_id` 중복(scene_count≤2), thumbnail 임시 파일 누수 수정 + QC4-FP001/002 + SS-SID001~003. blind-to-x: tweet URL 하드코딩 `/user/`→`/i/status/`, quality_gate `None` 진입 방어, dedup `strict=True` ValueError→`0.0`, editorial `avg_score` CT axes 이중계산, process.py `ERROR_FILTERED_EDITORIAL` upload 분모 왜곡 수정 + DEDUP-DIM001/002 + QG-ND001 + PROC-EF001/002 + TP-URL001. shorts-maker-v2 1936+ green, blind-to-x 3078 passed. |
| Next Priorities | (계속 진행 중) |

| Date | 2026-06-14 (2차) |
| Tool | Claude Code |
| Work | **자율 품질 루프 — NaN/Inf 방어 2차 강화 (8 commits, e6c4cc80..c1337514)**. `trend_discovery_step.py`: LLM 브레인스토밍 mock dict format 수정 + TD-NI001~004 (4 tests). `blind-to-x scoring_6d.py`: `_safe_db_float()` 헬퍼 신설, per-field NaN 폴백 + `_pearson` 7 unit tests (PC-001~007) + S6D-NI001~004. `publish_optimizer.py`/`feedback_loop.py`: `_sf()` 헬퍼, NaN views/likes/scores 가드. `render_effects.py`: `_fit_vertical` 0-dimension guard + `_zoom_crop` NaN scale + RE-NI001~003. `media_step.py`: mutagen Inf duration 폴백 + MS-NI001~003. `render_audio.py`: RMS NaN/Inf 필터링 + RA-NI001~003. `performance_prompt_adapter.py`: `_sf()`/`_safe_rate()` 헬퍼, NaN impression/sort + PPA-NI001~003. `render_step.py`: BGM 0.5s minimum guard (OOM 방지), video_duration None guard. `growth/feedback_loop.py`: watch_quality NaN/Inf + FL-NI001~002. shorts-maker-v2 1936 passed, blind-to-x 3063 passed. |
| Next Priorities | (1) 백그라운드 에이전트 (ac7ff2c8c50797f35) 스캔 완료 대기 — orchestrator/script/tts/subtitle/bgm/qc (s-m-v2) + publisher/draft_quality_gate/content_generator/notion_upload/x_publisher (btx). (2) non-NaN 버그 (silent data loss, empty list guard, 잘못된 boolean, 미닫힌 리소스) 수정 후 커밋. (3) .ai/HANDOFF.md/TASKS.md 업데이트 커밋. |

| Date | 2026-06-14 (1차) |
| Tool | Claude Code |
| Work | **자율 품질 루프 — NaN/Inf 방어 강화 (5 commits, 8e04dbd1..bc579c4e)**. `structure_step.py`: LLM NaN target_sec → duration gate bypass 수정 + 8 regression tests. `blind-to-x` 6파일: viral_filter `_clamp()` midpoint 폴백, ab_feedback_loop `_safe_float()`, style_bandit reward, scoring_6d likes/comments, scoring_performance views + 10 tests. `script_prompts.py`: tts_speed NaN/Inf fix + 4 tests. `scoring_6d.py`: 29 unit tests 신설 (first coverage). `render_captions.py`: font_candidates null guard. `render_step.py`: BGM `_load_audio_clip()` try-except 래핑. `express_draft.py`: cost_usd NaN/Inf guard. |
| Next Priorities | (계속 진행 중) |

| Field | Value |
|---|---|
| Date | 2026-06-15 |
| Tool | Codex |
| Work | **T-2724 code review count source labels**. Continued the auto-research loop under the dirty-handoff boundary after T-2723. Found that the launch prompt checklist showed live launch-audit code-review counts next to broader detail-artifact counts, but the `Code review gate count sources` line did not make the source roles explicit. Updated `refresh_current_evidence.py` so the line now labels launch-audit values as `primary` and detail artifact rows as `reference`, including `primary/reference risk score` when they differ. Updated refresh-current-evidence regression expectations. |
| Next Priorities | Verification passed refresh-current-evidence focused pytest (`139 passed`), refresh+launch-audit pytest (`208 passed`), Ruff, `py_compile`, full `refresh_current_evidence.py --root . --timeout 360 --json` (`all steps ok`; debug inventory exit `1` expected), scoped authorization menu exact check, path-limited diff-check with CRLF warnings only, and A/B `adopt_candidate` (`score_delta=1.0`, `.tmp/ab-decision-t2724-code-review-count-source-labels.json`). Current checklist selects latest A/B manifest T-2724 and shows `Code review gate count sources: primary launch-audit counts ... reference detail artifact rows ... primary/reference risk score ...`. Completion remains incomplete and selector remains `blocked / dirty_worktree_handoff_current`; no stage, commit, push, revert, product source edit, live Prisma/T-251 retry, cleanup apply, or `update_goal` was performed. |

| Field | Value |
|---|---|
| Date | 2026-06-15 |
| Tool | Codex |
| Work | **T-2723 latest A/B task file summary**. Continued the auto-research loop under the dirty-handoff boundary after T-2722. Found that launch-objective A/B evidence listed older task-id collisions and selected the latest manifest, but did not directly state whether the latest selected task id itself was collision-free. Added `_ab_manifest_task_file_summary()` to `launch_objective_audit.py` so A/B evidence now reports `Latest A/B task id T-2723 is collision-free with 1 manifest file.` or lists the selected latest task's colliding files. Added launch-audit regressions for both collision-free latest tasks and latest-task duplicate manifests. |
| Next Priorities | Verification passed launch-objective focused pytest (`69 passed`), launch-objective+refresh pytest (`208 passed`), Ruff, `py_compile`, explicit T-2723 launch-audit smoke, full `refresh_current_evidence.py --root . --timeout 360 --json` (`all steps ok`; debug inventory exit `1` expected), scoped authorization menu exact check, path-limited diff-check with CRLF warnings only, and A/B `adopt_candidate` (`score_delta=1.0`, `.tmp/ab-decision-t2723-latest-ab-task-file-summary.json`). Current checklist selects latest A/B manifest T-2723 and includes the collision-free latest task file summary. Completion remains incomplete and selector remains `blocked / dirty_worktree_handoff_current`; no stage, commit, push, revert, product source edit, live Prisma/T-251 retry, cleanup apply, or `update_goal` was performed. |

| Field | Value |
|---|---|
| Date | 2026-06-15 |
| Tool | Codex |
| Work | **T-2722 direction alignment selector guardrail fixture**. Continued the auto-research loop under the dirty-handoff boundary after T-2721. Found that current direction-alignment evidence already showed selector guardrails with `explicit push authorization or user push`, but the direction-alignment regression fixture still used stale `Do not push without explicit user authorization.` Updated `workspace/tests/test_auto_research_direction_alignment_audit.py` so the fixture uses the current selector publish-boundary wording and added an assertion that the boundary pillar evidence contains `explicit push authorization or user push`. |
| Next Priorities | Verification passed direction-alignment+refresh+launch-audit pytest (`213 passed`), Ruff, `py_compile`, full `refresh_current_evidence.py --root . --timeout 360 --json` (`all steps ok`; debug inventory exit `1` expected), path-limited diff-check with CRLF warnings only, and A/B `adopt_candidate` (`score_delta=0.5`, `.tmp/ab-decision-t2722-direction-alignment-selector-guardrail-fixture.json`). Completion remains incomplete and selector remains `blocked / dirty_worktree_handoff_current`; no stage, commit, push, revert, product source edit, live Prisma/T-251 retry, cleanup apply, or `update_goal` was performed. |

| Field | Value |
|---|---|
| Date | 2026-06-15 |
| Tool | Codex |
| Work | **T-2721 launch audit push guard failure wording**. Continued the auto-research loop under the dirty-handoff boundary after T-2720. Found that launch-objective audit failure blockers still said `release authorization packet did not enforce explicit user authorization` when a packet allowed pushing without authorization, while current release packet and selector guardrails use `explicit push authorization or user push`. Patched `launch_objective_audit.py` so the failure blocker now says `release authorization packet did not enforce explicit push authorization or user push`, and updated launch-audit regression fixtures. |
| Next Priorities | Verification passed launch-audit+refresh+selector pytest (`234 passed`), Ruff, `py_compile`, full `refresh_current_evidence.py --root . --timeout 360 --json` (`all steps ok`; debug inventory exit `1` expected), path-limited diff-check with CRLF warnings only, and A/B `adopt_candidate` (`score_delta=0.5`, `.tmp/ab-decision-t2721-launch-audit-push-guard-failure-wording.json`). Completion remains incomplete and selector remains `blocked / dirty_worktree_handoff_current`; no stage, commit, push, revert, product source edit, live Prisma/T-251 retry, cleanup apply, or `update_goal` was performed. |

| Field | Value |
|---|---|
| Date | 2026-06-15 |
| Tool | Codex |
| Work | **T-2720 selector publish guardrail wording**. Continued the auto-research loop under the dirty-handoff boundary after T-2719. Found that selector dirty-handoff-current guardrails were already aligned to `explicit push authorization or user push`, but publish-only and stale handoff-generation candidate paths still used `Do not push without explicit user authorization.` Patched `next_experiment_selector.py` so those publish-relevant selector guardrails use `Do not push without explicit push authorization or user push.` and updated selector regression tests. |
| Next Priorities | Verification passed selector+launch-audit+refresh pytest (`234 passed`), Ruff, `py_compile`, full `refresh_current_evidence.py --root . --timeout 360 --json` (`all steps ok`; debug inventory exit `1` expected), path-limited diff-check with CRLF warnings only, and A/B `adopt_candidate` (`score_delta=0.5`, `.tmp/ab-decision-t2720-selector-publish-guardrail-wording.json`). Current selector/checklist evidence shows selector guardrails with `explicit push authorization or user push`. Completion remains incomplete and selector remains `blocked / dirty_worktree_handoff_current`; no stage, commit, push, revert, product source edit, live Prisma/T-251 retry, cleanup apply, or `update_goal` was performed. |

| Field | Value |
|---|---|
| Date | 2026-06-15 |
| Tool | Codex |
| Work | **T-2719 release packet blocker push-boundary wording**. Continued the auto-research loop under the dirty-handoff boundary after T-2718. Found that release authorization guardrails used `explicit push authorization or user push`, but release packet blocker summaries still used slash-compressed `explicit push/user push` or `explicit push authorization/user push`. Patched `release_authorization_packet.py` and `refresh_current_evidence.py` so release packet blockers and checklist summaries use `current-head Actions unavailable until explicit push authorization or user push`, and updated release/launch-audit/refresh regression tests. |
| Next Priorities | Verification passed release+launch-audit+refresh pytest (`229 passed`), Ruff, `py_compile`, full `refresh_current_evidence.py --root . --timeout 360 --json` (`all steps ok`; debug inventory exit `1` expected), path-limited diff-check with CRLF warnings only, and A/B `adopt_candidate` (`score_delta=0.5`, `.tmp/ab-decision-t2719-release-blocker-push-boundary-wording.json`). Current checklist, release packet, and launch audit now show `current-head Actions unavailable until explicit push authorization or user push`. Completion remains incomplete and selector remains `blocked / dirty_worktree_handoff_current`; no stage, commit, push, revert, product source edit, live Prisma/T-251 retry, cleanup apply, or `update_goal` was performed. |

| Field | Value |
|---|---|
| Date | 2026-06-15 |
| Tool | Codex |
| Work | **T-2718 release guardrail push boundary wording**. Continued the auto-research loop under the dirty-handoff boundary after T-2717. Found that release authorization guardrails still said `Do not push without explicit user authorization.` while selector, release blockers, and handoff-only packets use `explicit push authorization or user push`. Patched `release_authorization_packet.py` so release packet guardrails use the same publish-boundary wording and updated release/refresh regression tests. |
| Next Priorities | Verification passed release+refresh pytest (`161 passed`), Ruff, `py_compile`, full `refresh_current_evidence.py --root . --timeout 360 --json` (`all steps ok`; debug inventory exit `1` expected), path-limited diff-check with CRLF warnings only, and A/B `adopt_candidate` (`score_delta=0.5`, `.tmp/ab-decision-t2718-release-guardrail-push-boundary-wording.json`). Current checklist/release packet now show `Do not push without explicit push authorization or user push.` Completion remains incomplete and selector remains `blocked / dirty_worktree_handoff_current`; no stage, commit, push, revert, product source edit, live Prisma/T-251 retry, cleanup apply, or `update_goal` was performed. |

| Field | Value |
|---|---|
| Date | 2026-06-15 |
| Tool | Codex |
| Work | **T-2717 authorization packet push boundary split**. Continued the auto-research loop under the dirty-handoff boundary after T-2716. Found that AI-context relay and session-log rotator authorization packet guardrails still collapsed stage, commit, push, and revert under the scoped packet token, while selector/release evidence already separates local scoped authorization from publish permission. Patched `refresh_current_evidence.py` so both handoff-only packet JSON/Markdown guardrails separate local stage/commit/revert authorization from explicit push authorization or user push. Updated refresh-current-evidence regression tests. |
| Next Priorities | Verification passed focused refresh-current-evidence pytest (`139 passed`), Ruff, `py_compile`, full `refresh_current_evidence.py --root . --timeout 360 --json` (`all steps ok`; debug inventory exit `1` expected), path-limited diff-check with CRLF warnings only, and A/B `adopt_candidate` (`score_delta=0.5`, `.tmp/ab-decision-t2717-authorization-packet-push-boundary-split.json`). Current `.tmp/ai-context-aic1-scoped-authorization-current.md` now says `Do not stage, commit, or revert without explicit APPROVE_AI_CONTEXT_RELAY_UPDATE authorization.` plus `Do not push without explicit push authorization or user push.` Current `.tmp/session-log-rotator-authorization-current.md` has the same split for `APPROVE_SESSION_LOG_ROTATOR`. Completion remains incomplete and selector remains `blocked / dirty_worktree_handoff_current`; no stage, commit, push, revert, product source edit, live Prisma/T-251 retry, cleanup apply, or `update_goal` was performed. |

| Field | Value |
|---|---|
| Date | 2026-06-15 |
| Tool | Codex |
| Work | **T-2716 authorization packet selector blocked-count visibility**. Continued the auto-research loop under the dirty-handoff boundary after T-2715. Found that the AI-context relay packet and session-log rotator authorization packet showed selector status/kind/adoptable count but omitted `blocked_candidate_count`, so operators had to open selector JSON to confirm that the packet was handoff-only evidence rather than an adoptable local experiment. Patched `refresh_current_evidence.py` so both packet JSON and Markdown include selector blocked count alongside adoptable count, and updated refresh-current-evidence regression tests. |
| Next Priorities | Verification passed focused refresh-current-evidence pytest (`139 passed`), Ruff, `py_compile`, full `refresh_current_evidence.py --root . --timeout 360 --json` (`all steps ok`; debug inventory exit `1` expected), path-limited diff-check with CRLF warnings only, and A/B `adopt_candidate` (`score_delta=0.5`, `.tmp/ab-decision-t2716-authorization-packet-selector-blocked-count.json`). Current `.tmp/ai-context-aic1-scoped-authorization-current.md` and `.tmp/session-log-rotator-authorization-current.md` now show `Selector: blocked / dirty_worktree_handoff_current / adoptable 0 / blocked 2`, and both packet JSON files include `blocked_candidate_count=2`. Completion remains incomplete and selector remains `blocked / dirty_worktree_handoff_current`; no stage, commit, push, revert, product source edit, live Prisma/T-251 retry, cleanup apply, or `update_goal` was performed. |

| Field | Value |
|---|---|
| Date | 2026-06-15 |
| Tool | Codex |
| Work | **T-2715 selector guardrail boundary split**. Continued the auto-research loop under the dirty-handoff boundary after T-2714. Found that selector action/blocker evidence already named `APPROVE_AI_CONTEXT_RELAY_UPDATE` and the push boundary, but selector guardrails still collapsed stage, commit, push, and revert into generic `explicit user authorization`. Patched `next_experiment_selector.py` so the dirty-handoff-current guardrail separates local scoped authorization from publish permission: `Do not stage, commit, or revert without explicit scoped authorization; do not push without explicit push authorization or user push.` Updated selector and launch-audit regression tests. |
| Next Priorities | Verification passed selector/launch-audit pytest (`95 passed`), related selector/launch-audit/refresh pytest (`234 passed` with `-o addopts=`), Ruff, `py_compile`, full `refresh_current_evidence.py --root . --timeout 360 --json` (`all steps ok`; debug inventory exit `1` expected), scoped authorization menu check (`rendered_matches=true`, `exact_rendered_matches=true`, `coverage_stale=false`, current dirty `25`), path-limited diff-check with CRLF warnings only, and A/B `adopt_candidate` (`score_delta=0.5`, `.tmp/ab-decision-t2715-selector-guardrail-boundary-split.json`). Current selector JSON and checklist detail now show the split guardrail. Completion remains incomplete and selector remains `blocked / dirty_worktree_handoff_current`; no stage, commit, push, revert, product source edit, live Prisma/T-251 retry, cleanup apply, or `update_goal` was performed. |

| Field | Value |
|---|---|
| Date | 2026-06-15 |
| Tool | Codex |
| Work | **T-2714 release detail push boundary explicitness**. Continued the auto-research loop under the dirty-handoff boundary after T-2713. Found that first-screen release blockers said `current-head Actions unavailable until explicit push/user push`, but detailed release packet and launch-audit packet blocker evidence still said `push authorization/user push` without `explicit`. Patched `release_authorization_packet.py` so detailed packet blockers now say `explicit push authorization/user push`, and updated release packet plus launch-audit regression tests. |
| Next Priorities | Verification passed release/audit pytest (`90 passed`), related release/audit/refresh pytest (`229 passed` with `-o addopts=`), Ruff, `py_compile`, full `refresh_current_evidence.py --root . --timeout 360 --json` (`all steps ok`; debug inventory exit `1` expected), scoped authorization menu check (`rendered_matches=true`, `exact_rendered_matches=true`, `coverage_stale=false`, current dirty `25`), path-limited diff-check with CRLF warnings only, and A/B `adopt_candidate` (`score_delta=0.5`, `.tmp/ab-decision-t2714-release-detail-push-explicit.json`). Current release packet and launch audit detailed packet blockers now show `current-head Actions unavailable until explicit push authorization/user push`. Completion remains incomplete and selector remains `blocked / dirty_worktree_handoff_current`; no stage, commit, push, revert, product source edit, live Prisma/T-251 retry, cleanup apply, or `update_goal` was performed. |

| Field | Value |
|---|---|
| Date | 2026-06-15 |
| Tool | Codex |
| Work | **T-2713 release completion action boundary token visibility**. Continued the auto-research loop under the dirty-handoff boundary after T-2712. Found that `Completion blocker actions` still collapsed no-push release authorization into `explicit stage/commit/push authorization`, while surrounding release evidence separately treats scoped stage/commit approval and explicit push/user-push permission. Patched `refresh_current_evidence.py` so the release completion action now says `stage/commit via APPROVE_AI_CONTEXT_RELAY_UPDATE and explicit push authorization or user push`, and updated refresh-current-evidence regression coverage. |
| Next Priorities | Verification passed focused refresh-current-evidence pytest (`139 passed`), related refresh/audit pytest (`207 passed` with `-o addopts=`), Ruff, `py_compile`, full `refresh_current_evidence.py --root . --timeout 360 --json` (`all steps ok`; debug inventory exit `1` expected), scoped authorization menu check (`rendered_matches=true`, `exact_rendered_matches=true`, `coverage_stale=false`, current dirty `25`), path-limited diff-check with CRLF warnings only, and A/B `adopt_candidate` (`score_delta=0.5`, `.tmp/ab-decision-t2713-release-action-boundary-token.json`). Current checklist `Completion blocker actions` now separates local stage/commit approval from publish permission: `keep no-push packet current until stage/commit via APPROVE_AI_CONTEXT_RELAY_UPDATE and explicit push authorization or user push`. Completion remains incomplete and selector remains `blocked / dirty_worktree_handoff_current`; no stage, commit, push, revert, product source edit, live Prisma/T-251 retry, cleanup apply, or `update_goal` was performed. |

| Field | Value |
|---|---|
| Date | 2026-06-15 |
| Tool | Codex |
| Work | **T-2712 selector blocker approval token visibility**. Continued the auto-research loop under the dirty-handoff boundary after T-2711. Found that selector `action` evidence now named `APPROVE_AI_CONTEXT_RELAY_UPDATE`, but the adjacent selector blocker still said only `explicit scoped staging/commit authorization is required before product changes` without the token. Patched `next_experiment_selector.py` so the dirty-handoff-current blocker names `APPROVE_AI_CONTEXT_RELAY_UPDATE`, and updated selector regression coverage. |
| Next Priorities | Verification passed selector pytest (`27 passed`), combined focused pytest (`234 passed` with `-o addopts=`), Ruff, `py_compile`, full `refresh_current_evidence.py --root . --timeout 360 --json` (`all steps ok`; debug inventory exit `1` expected), scoped authorization menu check (`rendered_matches=true`, `exact_rendered_matches=true`, `coverage_stale=false`, current dirty `25`), path-limited diff-check with CRLF warnings only, and A/B `adopt_candidate` (`score_delta=0.6`, `.tmp/ab-decision-t2712-selector-blocker-token.json`). Current `.tmp/next-experiment-current.json` blocker text now shows `explicit scoped staging/commit authorization via APPROVE_AI_CONTEXT_RELAY_UPDATE is required before product changes.` Completion remains incomplete and selector remains `blocked / dirty_worktree_handoff_current`; no stage, commit, push, revert, product source edit, live Prisma/T-251 retry, cleanup apply, or `update_goal` was performed. |

| Field | Value |
|---|---|
| Date | 2026-06-15 |
| Tool | Codex |
| Work | **T-2711 selector action approval token visibility**. Continued the auto-research loop under the dirty-handoff boundary after T-2710. Found that selector JSON and detailed launch-audit `Selected action` evidence still said only `Wait for explicit scoped staging/commit authorization...` without naming `APPROVE_AI_CONTEXT_RELAY_UPDATE`, while debug/menu/checklist summaries already did. Patched `next_experiment_selector.py` so the dirty-handoff candidate action names `APPROVE_AI_CONTEXT_RELAY_UPDATE`, and updated selector plus launch-objective audit regression tests. |
| Next Priorities | Verification passed combined focused pytest (`234 passed` with `-o addopts=`), Ruff, `py_compile`, full `refresh_current_evidence.py --root . --timeout 360 --json` (`all steps ok`; debug inventory exit `1` expected), scoped authorization menu check (`rendered_matches=true`, `exact_rendered_matches=true`, `coverage_stale=false`, current dirty `25`), path-limited diff-check with CRLF warnings only, and A/B `adopt_candidate` (`score_delta=0.7142857142857143`, `.tmp/ab-decision-t2711-selector-action-token.json`). Current selector JSON, launch audit, and checklist now show `Wait for explicit scoped staging/commit authorization via APPROVE_AI_CONTEXT_RELAY_UPDATE or keep the current dirty handoff plan.` Completion remains incomplete and selector remains `blocked / dirty_worktree_handoff_current`; no stage, commit, push, revert, product source edit, live Prisma/T-251 retry, cleanup apply, or `update_goal` was performed. |

| Field | Value |
|---|---|
| Date | 2026-06-15 |
| Tool | Codex |
| Work | **T-2710 release detail blocker approval token visibility**. Continued the auto-research loop under the dirty-handoff boundary after T-2709. Found that first-screen release blocker summaries named `APPROVE_AI_CONTEXT_RELAY_UPDATE`, but detailed release authorization packet evidence still said only `dirty worktree paths: N` and `release authorization packet blocked by dirty worktree paths: N`. Patched `release_authorization_packet.py` so the packet artifact blockers name `APPROVE_AI_CONTEXT_RELAY_UPDATE`, and patched `launch_objective_audit.py` so detailed audit blockers render the same tokenized dirty-worktree release boundary. Updated focused regression coverage for release packet, launch audit, LLM Wiki release summary, and refresh-current-evidence consumers. |
| Next Priorities | Verification passed focused pytest (`239 passed` with `-o addopts=`), Ruff, `py_compile`, full `refresh_current_evidence.py --root . --timeout 360 --json` twice (`all steps ok`; debug inventory exit `1` expected), scoped authorization menu check (`rendered_matches=true`, `exact_rendered_matches=true`, `coverage_stale=false`, current dirty `23`), path-limited diff-check with CRLF warnings only, and A/B `adopt_candidate` (`score_delta=0.7142857142857143`, `.tmp/ab-decision-t2710-release-detail-token.json`). Current release packet, launch audit, and checklist now show detailed dirty release blockers with `until APPROVE_AI_CONTEXT_RELAY_UPDATE scoped authorization`. Completion remains incomplete and selector remains `blocked / dirty_worktree_handoff_current`; no stage, commit, push, revert, product source edit, live Prisma/T-251 retry, cleanup apply, or `update_goal` was performed. |

| Field | Value |
|---|---|
| Date | 2026-06-15 |
| Tool | Codex |
| Work | **T-2709 GitHub detail blocker approval token visibility**. Continued the auto-research loop under the dirty-handoff boundary after T-2708. Found that the first-screen `GitHub recommendations` summary included `APPROVE_AI_CONTEXT_RELAY_UPDATE`, but the detailed launch-audit blocker evidence still inherited source GitHub inventory wording that said only `after explicit scoped authorization`. Patched `github_project_inventory.py` so source recommendations now name `APPROVE_AI_CONTEXT_RELAY_UPDATE`, and patched `refresh_current_evidence.py` detailed evidence rewriting so stale `stage and commit...` detail rows gain both explicit authorization and the token before dirty-group normalization. Updated focused regression coverage in GitHub inventory, launch-objective audit, and refresh-current-evidence tests. |
| Next Priorities | Verification passed combined focused pytest (`230 passed` with `-o addopts=`), Ruff, `py_compile`, full `refresh_current_evidence.py --root . --timeout 360 --json` twice (`all steps ok`; debug inventory exit `1` expected), scoped authorization menu check (`rendered_matches=true`, `exact_rendered_matches=true`, `coverage_stale=false`), path-limited diff-check with CRLF warnings only, and A/B `adopt_candidate` (`score_delta=0.5`, `.tmp/ab-decision-t2709-github-detail-token.json`). Current checklist and launch audit now show detailed GitHub blocker evidence with `after explicit scoped authorization using APPROVE_AI_CONTEXT_RELAY_UPDATE...`. Completion remains incomplete and selector remains `blocked / dirty_worktree_handoff_current`; no stage, commit, push, revert, product source edit, live Prisma/T-251 retry, cleanup apply, or `update_goal` was performed. |

| Field | Value |
|---|---|
| Date | 2026-06-15 |
| Tool | Codex |
| Work | **T-2708 release packet blocker approval token visibility**. Continued the auto-research loop under the dirty-handoff boundary after T-2707. Found that the first-screen `Release packet blockers` line still reported only `dirty worktree paths N` without naming the current recommended scoped authorization token, even though adjacent blocker/action/menu evidence now points to `APPROVE_AI_CONTEXT_RELAY_UPDATE`. Patched `refresh_current_evidence.py` so dirty release blockers now render as `dirty worktree paths N until APPROVE_AI_CONTEXT_RELAY_UPDATE scoped authorization`, preserving current-head Actions and external T-251 blocker wording. Updated focused regression coverage in `workspace/tests/test_auto_research_refresh_current_evidence.py`. |
| Next Priorities | Verification passed focused refresh-current-evidence pytest (`139 passed` with `-o addopts=`), Ruff, `py_compile`, full `refresh_current_evidence.py --root . --timeout 360 --json` twice (`all steps ok`; debug inventory exit `1` expected), scoped authorization menu check (`rendered_matches=true`, `exact_rendered_matches=true`, `coverage_stale=false`), path-limited diff-check with CRLF warnings only, and A/B `adopt_candidate` (`score_delta=0.5`, `.tmp/ab-decision-t2708-release-blocker-token.json`). Current checklist now shows `Release packet blockers: dirty worktree paths 19 until APPROVE_AI_CONTEXT_RELAY_UPDATE scoped authorization; current-head Actions unavailable until explicit push/user push; external/user-owned blocker(s) T-251.` Completion remains incomplete and selector remains `blocked / dirty_worktree_handoff_current`; no stage, commit, push, revert, product source edit, live Prisma/T-251 retry, cleanup apply, or `update_goal` was performed. |

| Field | Value |
|---|---|
| Date | 2026-06-15 |
| Tool | Codex |
| Work | **T-2707 GitHub recommendation approval token visibility**. Continued the auto-research loop under the dirty-handoff boundary after T-2706. Found that the first-screen `GitHub recommendations` line still said `after explicit scoped authorization` without naming the currently recommended token, even though adjacent completion/debug/action summaries now show `APPROVE_AI_CONTEXT_RELAY_UPDATE`. Patched `refresh_current_evidence.py` so GitHub dirty-worktree recommendations now rewrite to `after explicit scoped authorization using APPROVE_AI_CONTEXT_RELAY_UPDATE...`, preserving dirty-group rewriting and avoiding duplicate token insertion. Updated focused regression coverage in `workspace/tests/test_auto_research_refresh_current_evidence.py`. |
| Next Priorities | Verification passed focused refresh-current-evidence pytest (`139 passed` with `-o addopts=`), Ruff, `py_compile`, full `refresh_current_evidence.py --root . --timeout 360 --json` twice (`all steps ok`; debug inventory exit `1` expected), scoped authorization menu check (`rendered_matches=true`, `exact_rendered_matches=true`, `coverage_stale=false`), path-limited diff-check with CRLF warnings only, and A/B `adopt_candidate` (`score_delta=0.5`, `.tmp/ab-decision-t2707-github-recommendation-token.json`). Current checklist now shows `GitHub recommendations: Worktree is dirty; after explicit scoped authorization using APPROVE_AI_CONTEXT_RELAY_UPDATE...`. Completion remains incomplete and selector remains `blocked / dirty_worktree_handoff_current`; no stage, commit, push, revert, product source edit, live Prisma/T-251 retry, cleanup apply, or `update_goal` was performed. |

| Field | Value |
|---|---|
| Date | 2026-06-15 |
| Tool | Codex |
| Work | **T-2706 completion action approval token visibility**. Continued the auto-research loop under the dirty-handoff boundary after T-2705. Found that the first-screen `Completion blocker actions` line still said `via explicit scoped authorization` for GitHub/workflow and next-experiment selector dirty boundaries without naming the currently recommended token. Patched `refresh_current_evidence.py` so those completion actions now say `using APPROVE_AI_CONTEXT_RELAY_UPDATE`, while preserving existing Shorts Maker V2 token guidance, release packet guidance, and external T-251 guidance. Updated focused regression coverage in `workspace/tests/test_auto_research_refresh_current_evidence.py`. |
| Next Priorities | Verification passed focused refresh-current-evidence pytest (`138 passed` with `-o addopts=`), Ruff, `py_compile`, full `refresh_current_evidence.py --root . --timeout 360 --json` twice (`all steps ok`; debug inventory exit `1` expected), scoped authorization menu check (`rendered_matches=true`, `exact_rendered_matches=true`, `coverage_stale=false`), path-limited diff-check with CRLF warnings only, and A/B `adopt_candidate` (`score_delta=0.7142857142857143`, `.tmp/ab-decision-t2706-completion-action-token.json`). Current checklist now shows `Completion blocker actions` for GitHub and selector dirty boundaries with `using APPROVE_AI_CONTEXT_RELAY_UPDATE`. Completion remains incomplete and selector remains `blocked / dirty_worktree_handoff_current`; no stage, commit, push, revert, product source edit, live Prisma/T-251 retry, cleanup apply, or `update_goal` was performed. |

| Field | Value |
|---|---|
| Date | 2026-06-15 |
| Tool | Codex |
| Work | **T-2705 debug next-action approval token visibility**. Continued the auto-research loop under the dirty-handoff boundary after T-2704. Found that `Debug blocker next actions` still said `Wait for explicit scoped staging/commit authorization...` without naming the currently recommended token, even though the authorization menu recommends `APPROVE_AI_CONTEXT_RELAY_UPDATE`. Patched `debug_loop_inventory.py` so the dirty-handoff debug next action now says `via APPROVE_AI_CONTEXT_RELAY_UPDATE`, and updated debug inventory plus refresh-current-evidence regression coverage. |
| Next Priorities | Verification passed combined focused pytest (`207 passed` with `-o addopts=`), Ruff, `py_compile`, full `refresh_current_evidence.py --root . --timeout 360 --json` (`all steps ok`; debug inventory exit `1` expected), scoped authorization menu check (`rendered_matches=true`, `exact_rendered_matches=true`, `coverage_stale=false`), path-limited diff-check with CRLF warnings only, and A/B `adopt_candidate` (`score_delta=0.7142857142857143`, `.tmp/ab-decision-t2705-debug-next-action-token.json`). Current checklist and debug markdown now show `Wait for explicit scoped staging/commit authorization via APPROVE_AI_CONTEXT_RELAY_UPDATE...`. Completion remains incomplete and selector remains `blocked / dirty_worktree_handoff_current`; no stage, commit, push, revert, product source edit, live Prisma/T-251 retry, cleanup apply, or `update_goal` was performed. |

| Field | Value |
|---|---|
| Date | 2026-06-15 |
| Tool | Codex |
| Work | **T-2704 completion action explicit authorization wording**. Continued the auto-research loop under the dirty-handoff boundary after T-2703. Found that the first-screen `Completion blocker actions` line still said `resolve dirty worktree boundary` / `clear the dirty handoff boundary` without naming the required explicit scoped authorization, even though lower-level authorization/menu evidence is current. Patched `refresh_current_evidence.py` so GitHub/workflow and next-experiment selector dirty-boundary completion actions now say `via explicit scoped authorization`, while preserving existing release packet, Shorts source token, and external T-251 guidance. Updated focused regression coverage in `workspace/tests/test_auto_research_refresh_current_evidence.py`. |
| Next Priorities | Verification passed focused refresh-current-evidence pytest (`138 passed` with `-o addopts=`), Ruff, `py_compile`, full `refresh_current_evidence.py --root . --timeout 360 --json` (`all steps ok`; debug inventory exit `1` expected), scoped authorization menu check (`rendered_matches=true`, `exact_rendered_matches=true`, `coverage_stale=false`), path-limited diff-check with CRLF warnings only, and A/B `adopt_candidate` (`score_delta=0.7142857142857143`, `.tmp/ab-decision-t2704-completion-action-explicit-authorization.json`). Current checklist now shows `Completion blocker actions` for GitHub and selector dirty boundaries with `via explicit scoped authorization`. Completion remains incomplete and selector remains `blocked / dirty_worktree_handoff_current`; no stage, commit, push, revert, product source edit, live Prisma/T-251 retry, cleanup apply, or `update_goal` was performed. |

| Field | Value |
|---|---|
| Date | 2026-06-15 |
| Tool | Codex |
| Work | **T-2703 GitHub inventory authorization source wording**. Continued the auto-research loop under the dirty-handoff boundary after T-2702. Found that T-2702 fixed the top-level launch checklist `GitHub recommendations` summary, but the detailed launch-audit blocker under `Find GitHub-related projects...` still inherited the source `github_project_inventory.py` recommendation text `stage and commit only files owned by the current experiment` without the explicit scoped authorization precondition. Patched the source GitHub inventory recommendation to say `after explicit scoped authorization, stage and commit...`, and updated focused inventory/launch-audit regression coverage. |
| Next Priorities | Verification passed focused pytest (`91 passed` with `-o addopts=`), Ruff, `py_compile`, full `refresh_current_evidence.py --root . --timeout 360 --json` (`all steps ok`; debug inventory exit `1` expected), scoped authorization menu check (`rendered_matches=true`, `exact_rendered_matches=true`, `coverage_stale=false`), path-limited diff-check with CRLF warnings only, and A/B `adopt_candidate` (`score_delta=0.7142857142857143`, `.tmp/ab-decision-t2703-github-inventory-authorization-source.json`). Current checklist now shows both the top-level GitHub recommendation and the detailed blocker evidence with `after explicit scoped authorization`. Completion remains incomplete and selector remains `blocked / dirty_worktree_handoff_current`; no stage, commit, push, revert, product source edit, live Prisma/T-251 retry, cleanup apply, or `update_goal` was performed. |

> T-1570 relay note: `f3f376a6` is the verified code baseline before this documentation relay. After this relay is committed, use live `python execution/session_orient.py --json` for the exact current HEAD/ahead count; the remaining boundaries should still be publish/current-head Actions plus user-owned Hanwoo T-251.

> T-1404 verification note: staged code-review gate returned advisory WARN (`risk_score=0.35`) from test-gap heuristics, covered by focused source-browser tests, CLI preflight tests, live click-through evidence, and blind-to-x project QC.

## Notes

- **T-251 (active blocker)**: Supabase database password desynchronization. User must reset password via Supabase Dashboard (Project Settings > Database), then update `projects/hanwoo-dashboard/.env`.
- **Origin sync**: Use live `python execution/session_orient.py --json` before acting. Current relay state has `main` ahead of origin and a dirty worktree; do not push without explicit authorization.
- Older addenda archived in `.ai/archive/HANDOFF_archive_2026-05-15.md` and `.ai/archive/HANDOFF_archive_2026-05-19.md`.
