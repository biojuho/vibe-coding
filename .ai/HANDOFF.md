# HANDOFF - AI Context Relay

> See `SESSION_LOG.md` for recent session history and `DECISIONS.md` for stable architecture decisions.

## Current Addendum

| Field | Value |
|---|---|
| Date | 2026-06-18 (deptry CI + knip 대시보드 확장) |
| Tool | Claude Code (Opus 4.8) |
| Work | **deptry 후속 "둘다 진행" → (1) deptry를 CI advisory로 연결 + (2) JS 절반에 `knip` 도입(폴리글랏 위생 통일)**. **(1)** `root-quality-gate.yml`에 `deptry` 설치 + "Dependency hygiene audit (advisory)" step(`continue-on-error: true`, 비차단 — 보안audit/code_review_gate와 동일 정책. blocking 원하면 continue-on-error 제거 or `--strict`). **(2)** [`knip`](https://github.com/webpro-nl/knip)(ISC, Python=deptry의 JS 등가물) hanwoo/knowledge 대시보드 도입. **워크플로(13 에이전트)로 병렬 조사+적대적 검증**: Analyze(대시보드별 최소 knip.json 도출→재실행) → Verify(제거후보 dep마다 import grep 적대 검증). hanwoo `knip.json`(paths `@/*→./src/*`[jsconfig는 knip 기본 미독해] + entry sw/scripts/prisma-seed + ignore workbox) **허위 162건 제거**(99파일/68unresolved→0). knowledge `knip.json`(ignoreBinaries python + ignoreDependencies postcss). **bs4 교훈 JS판 적중**: hanwoo "미사용 dep" 9개 중 **7개는 `src/components/ui/*.js` shadcn 래퍼가 실제 import**(데드 섬)→무작정 제거 시 파괴. 적대검증+자체 grep으로 진짜 고아 dep 4개만 제거: hanwoo `react-toast`·`react-dropdown-menu`, knowledge `react-separator`·`react-tooltip`(소스 사용 0). 각 package.json에 `knip>=6.17.1` devDep + `"knip"` script. 데드 UI 프리미티브 섬 + 미사용 export/type 은 백로그로 노출 유지(숨기지 않음). |
| Verify | hanwoo **lint 0 error(3 known isLoading warn)** + **node --test 2419 pass/0 fail**. knowledge **lint clean + 73 pass/0 fail**. knip 6 양쪽 config 정상(hanwoo 0 false-file, 잔여 7 데드섬 dep+2 unlisted+39 export; knowledge 0 dep/0 file, 잔여 10 export+7 type). root-quality-gate.yml YAML 유효 + workflow-hygiene 3 test pass. deptry 감사 여전히 0(타툴이 google-api map 추가). **미커밋**(멀티툴 트리). |
| Next Priorities | (1) 원하면 pathspec 한정 커밋: `.github/workflows/root-quality-gate.yml`, `projects/hanwoo-dashboard/{knip.json,package.json,package-lock.json}`, `projects/knowledge-dashboard/{knip.json,package.json,package-lock.json}`, `directives/dependency_hygiene_audit.md`. (2) **데드 UI 백로그**: hanwoo `src/components/ui/{avatar,label,progress,scroll-area,select,tabs,tooltip}.js` + hooks 3개 + knowledge 미사용 shadcn export/type — 정리할지 보존할지 결정(현재 knip이 계속 노출). (3) 선택: 대시보드 CI(full-test-matrix/deploy-hanwoo)에 knip advisory step. |

| Field | Value |
|---|---|
| Date | 2026-06-18 (deptry 의존성 위생 게이트) |
| Tool | Claude Code (Opus 4.8) |
| Work | **/goal "github OSS 가져와 시스템 최적화" → 시스템/워크스페이스 전반 선택 → `deptry` 도입 (의존성 위생 감사)**. 기존 게이트 빈틈을 메움: pip-audit=CVE, freshness inventory=outdated, **deptry=선언-vs-import 정확성**(DEP001 missing/DEP002 unused/DEP003 transitive/DEP004 misplaced-dev). ① 루트 `pyproject.toml`에 `deptry>=0.23` 추가. ② 신규 `execution/dependency_hygiene_audit.py` — `dependency_security_audit.py` 패턴 미러(Rich TUI, CP949-safe, `--json`, `--project`, advisory exit 0/1/2/3). ③ 3프로젝트 `[tool.deptry]` 설정으로 의도적 패턴 인코딩(known_first_party / package_module_name_map / pep621_dev_dependency_groups / per_rule_ignores / extend_exclude). ④ 신규 `directives/dependency_hygiene_audit.md` SOP + `workspace/tests/test_dependency_hygiene_audit.py`(21 test, deptry subprocess mock). **첫 스캔 raw ~168건 → 0건**. 발견·수정한 진짜 결함: **(a) workspace `code_evaluator.py`가 pydantic 무가드 hard import 하나 dev 그룹에만 선언 → 런타임 deps로 이동**, **(b) workspace `yaml` 미선언 직접 import → PyYAML 런타임 선언 추가**, **(c) blind-to-x `beautifulsoup4`/`google-genai` 이름불일치 이중오탐 → package_module_name_map 정정**(bs4는 실사용 — 제거했으면 스크래퍼 깨질 뻔, 사용처 검증 후 보존). shorts `pydub`는 전부 try/except 가드된 선택 백엔드라 수용. |
| Verify | `dependency_hygiene_audit.py --json` 3프로젝트 **0 findings, exit 0**. 신규 21 test pass. ruff clean. 4개 pyproject.toml tomllib 파싱 OK. `check_mapping.py` no drift. governance+project_qc 36 test pass. **미커밋**(멀티툴 dirty 트리, 사용자 커밋 미요청 — pathspec 한정 권장 [[multi_tool_git_index_race]]). |
| Next Priorities | (1) 원하면 pathspec 한정 커밋: `pyproject.toml`, `execution/dependency_hygiene_audit.py`, `directives/dependency_hygiene_audit.md`, `workspace/tests/test_dependency_hygiene_audit.py`, `workspace/pyproject.toml`, `projects/blind-to-x/pyproject.toml`, `projects/shorts-maker-v2/pyproject.toml`. (2) 선택: root-quality-gate CI에 advisory step 추가. (3) 의존성 업그레이드 직후 루틴으로 실행 권장. |

| Field | Value |
|---|---|
| Date | 2026-06-18 (전체 QC 스윕) |
| Tool | Claude Code (Opus 4.8) |
| Work | **/goal "전체 QC 진행 + 전체 프로젝트/시스템 개선" — 4개 활성 프로젝트 + 시스템 테스트 전체 QC 후 shorts-maker-v2 회귀 3건 수정 (미커밋).** 멀티툴 dirty 트리(47파일)를 클러스터별로 트리아지: ① blind-to-x 쥬팍식 X본문(검증완료·미커밋), ② knowledge-dashboard null-safety 하드닝(+테스트), ③ shorts-maker-v2 gate3 silent-drop 버그픽스, ④ Codex auto-research 루프 WIP(T-2717..2724 wording), ⑤ nature-skills 서브모듈. **버그픽스 미완 전파 발견**: ③의 `orchestrator.py`가 gate3 degraded 항목을 `manifest.degraded_steps.append`(line 1358서 덮어써져 소실) → `degraded_steps.append`로 고쳐 degradation을 올바르게 표면화했는데, unit 테스트만 갱신하고 **integration 테스트 3건은 미갱신** → `--maxfail=1`이 1건만 노출([[qc_maxfail_wip_masking]]). `--maxfail` 없이 전수 실행해 3건 전부 발견: `test_orchestrator_manifest::test_orchestrator_writes_manifest` + `test_renderer_mode_manifest::{native_on_sf_failure, sf_on_success}`. 셋 다 `assert 'degraded'=='success'` — 4바이트 stub 미디어가 진짜 gate를 통과 못 하는데 silent-drop 버그 덕에 success였던 것. 수정: unit 해피패스 선례대로 gate3/gate4를 pass mock(렌더모드 테스트는 `_passing_media_gates()` contextmanager로). degraded 경로는 신규 unit ORC-G3-001이 커버. |
| Verify | **전체 QC 그린**: blind-to-x test 3116p/10s + ruff clean. shorts-maker-v2 **1988p/12s/0f**(--maxfail 없이 전수) + ruff clean. hanwoo test 2419p + lint 0err(3 known `isLoading` warn). knowledge test 73p + lint + **build OK(63.5s) + smoke OK(25.3s)**. 시스템: auto-research workspace 테스트 396p. **미실행**: hanwoo build/smoke = Postgres 필요 CI 전용(기존 결정). 내 변경 파일: `tests/integration/test_orchestrator_manifest.py`, `tests/integration/test_renderer_mode_manifest.py`(2파일, 미커밋). |
| Next Priorities | (1) shorts-maker-v2 gate3 클러스터(orchestrator.py + edge_tts_client.py + pyproject.toml + test_orchestrator_unit.py + 내 integration 테스트 2건)는 코히어런트 단위 — 사용자 승인 시 pathspec 한정 커밋([[multi_tool_git_index_race]]). (2) blind-to-x 쥬팍식 + knowledge null-safety는 별도 코히어런트 클러스터(각각 검증완료). (3) Codex auto-research 루프가 dirty-handoff에 막혀 T-2700+ 마이크로 wording만 반복 — 트리 정리(클러스터별 커밋)가 그 루프도 풀어줌. |

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

> T-1570 relay note: `f3f376a6` is the verified code baseline before this documentation relay. After this relay is committed, use live `python execution/session_orient.py --json` for the exact current HEAD/ahead count; the remaining boundaries should still be publish/current-head Actions plus user-owned Hanwoo T-251.

> T-1404 verification note: staged code-review gate returned advisory WARN (`risk_score=0.35`) from test-gap heuristics, covered by focused source-browser tests, CLI preflight tests, live click-through evidence, and blind-to-x project QC.

## Notes

- **T-251 (active blocker)**: Supabase database password desynchronization. User must reset password via Supabase Dashboard (Project Settings > Database), then update `projects/hanwoo-dashboard/.env`.
- **Origin sync**: Use live `python execution/session_orient.py --json` before acting. Current relay state has `main` ahead of origin and a dirty worktree; do not push without explicit authorization.
- Older addenda archived in `.ai/archive/HANDOFF_archive_2026-05-15.md` and `.ai/archive/HANDOFF_archive_2026-05-19.md`.
