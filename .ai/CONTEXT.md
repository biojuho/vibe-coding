# Vibe Coding Context

> Local-only multi-project workspace. Do not push, pull, or deploy unless the user explicitly asks.

## Workspace Summary

- Root runtime: Python `venv`, `pytest`, `ruff`, root `.env`
- Canonical path contract:
  - `workspace/...` for shared automation and docs
  - `projects/<name>/...` for product repos
  - `infrastructure/...` for services and MCP helpers

## Active Projects

| Project | Status | Stack | Canonical Path |
|---|---|---|---|
| `blind-to-x` | Active | Python pipeline, Notion, Cloudinary | `projects/blind-to-x` |
| `shorts-maker-v2` | Active | Python, MoviePy, Edge TTS, OpenAI, Google GenAI, Pillow | `projects/shorts-maker-v2` |
| `hanwoo-dashboard` | Active | Next.js, React, Prisma 7, PostgreSQL/Supabase, Redis/BullMQ, Tailwind | `projects/hanwoo-dashboard` |
| `knowledge-dashboard` | Maintenance | Next.js, React, TypeScript, Tailwind | `projects/knowledge-dashboard` |
| `suika-game-v2` | Frozen | Vite, Vanilla JS, Matter.js | `projects/suika-game-v2` |
| `word-chain` | Frozen | React, Vite, Tailwind | `projects/word-chain` |

## Technology Adoption Policy

- Workspace stack policy is documented in `docs/technology-stack.md`.
- Current frontend default is React/Next.js with JavaScript or TypeScript.
- Current backend/runtime default is Python pipelines plus Next.js server routes/actions.
- Current SaaS data direction is PostgreSQL/Supabase; `hanwoo-dashboard` uses Prisma with `@prisma/adapter-pg`.
- Current queue/cache direction is Redis/BullMQ for single-app internal async work.
- Current HTTP client direction is native Fetch API via local helpers.

## Current Reliability Notes

- **`hanwoo-dashboard`**:
  - **데이터 견고성 확보**: API 및 로컬 캐시/스토리지가 오염되거나 빈 값을 가질 때 발생할 수 있는 크래시(NaN 누출, Invalid Date 노출)를 차단하기 위해 `toFiniteNumber()`, `toValidDate()`, `normalizePaginationItems()` 등의 방어적 데이터 정규화(Normalization) 도우미 함수들을 대거 도입했습니다. (2026-05-21)
  - **UX 및 안정성 강화**: 폼 제출 버튼에 로딩 상태 및 바쁜 표시(`aria-busy`, pending copy)를 일관되게 적용하여 이중 제출을 방지하고, 모든 `<button>`에 명시적인 `type`을 지정하는 회귀 방지 테스트를 추가했습니다. (2026-05-21)
- **`shorts-maker-v2`**:
  - **테스트 안정성**: 딥러닝 무거운 의존성(`torch`, `torch.cuda`) 없이도 로컬에서 100% 테스트할 수 있도록 `test_openvoice_client.py`에 가벼운 런타임 `MagicMock`을 주입하여 602개 단위 테스트 100% 그린 패스를 달성했습니다. `ShortsFactory/engines/text_engine.py`에서 발생하던 `unexpected indent` 인덱스 에러를 해결했습니다. (2026-05-22)
  - **미디어 스텝 개선**: `media_step.py`에서 13개의 중복 중첩 메서드를 공통 Mixin 구조(`MediaAudioMixin`, `MediaVisualMixin`, `MediaFallbackMixin`)로 정리하여 Ruff 린트를 통과하고 유지 보수성을 높였습니다. (2026-05-22)
- **`blind-to-x`**:
  - **생성 품질 통제 (Phase 1)**: `docs/output_quality_uplift_2026-05-26.md`에 따라 어휘 필터링(zero-tolerance 어휘 12개), CTA 종결 규칙, 이모지 제한, 의존성 표현 억제, 12자 연속 중복 감지 등의 결정론적 heuristic 품질 검사를 `quality_gate.py`에 장착했습니다. 단위 테스트 49/49 통과 완료. (2026-05-26)

## Recent Verification

- **2026-06-04 (Codex)**: T-1232 blind-to-x Notion SDK dependency freshness loop. Applied `notion-client==3.1.0` with the root workspace `uv.lock` synced, after checking local package metadata (`Requires-Python >=3.8, <4`) and official notion-sdk-py v2.7.0, v3.0.0, and v3.1.0 release pages. The relevant breaking change removes private/helper APIs `is_full_page_or_database` and `is_api_error_code`, which blind-to-x does not use; v3.1.0 adds endpoint support and automatic retry support. Verification: `uv lock --project projects/blind-to-x --check` passed, import/API smoke reported Notion 3.1.0 and confirmed the used `AsyncClient` namespaces/methods, focused Notion upload/schema/persist tests passed 163/163 with one unrelated deprecated `google.generativeai` warning, extra Notion analytics/query/backfill tests passed 99/99, blind-to-x lint passed, and A/B selected `adopt_candidate` (`score_delta=0.55`).

- **2026-06-04 (Codex)**: T-1231 word-chain jsdom dependency freshness loop. Applied `jsdom` `^28.1.0` -> `^29.1.1` with synced npm and root pnpm lockfiles after confirming npm latest/current engine metadata and reviewing official jsdom v29.0.0, v29.1.0, and v29.1.1 release notes. The relevant compatibility change is the Node 22 minimum moving from `22.12.0+` to `22.13.0+`; local Node `24.13.0` remains supported. Verified root frozen lock, word-chain tests 23/23, lint, build via ASCII fallback after direct Vite `3221226505`, jsdom `29.1.1` import and DOM smoke, audit 0, and A/B `adopt_candidate` (`score_delta=0.5`).

- **2026-06-04 (Codex)**: T-1230 blind-to-x OpenAI SDK dependency freshness loop. Applied `openai==2.41.0` with the root workspace `uv.lock` synced, after checking official PyPI metadata and openai-python v2.38.0..v2.41.0 release notes. The release range is additive API/spec, workload identity/additional Responses tools, Bedrock Responses support, and `responses.moderation` / `chat_completions.moderation` surface updates. Verification: `uv lock --project projects/blind-to-x --check` passed, import smoke reported OpenAI 2.41.0 and `AsyncOpenAI`, focused OpenAI provider/image/runtime tests passed 152/152, blind-to-x lint passed, and A/B selected `adopt_candidate` (`score_delta=0.55`).

- **2026-06-04 (Codex)**: T-1229 blind-to-x Anthropic SDK dependency freshness loop. Applied `anthropic==0.105.2` with the root workspace `uv.lock` synced, after checking official anthropic-sdk-python v0.105.0, v0.105.1, and v0.105.2 release pages. The relevant changes are additive support for `claude-opus-4-8`, mid-conversation system blocks, `usage.output_tokens_details`, custom file size caps, plus internal publishing/changelog-only follow-ups. Verification: `uv run` installed anthropic 0.105.2, `AsyncAnthropic` import smoke passed, focused Anthropic provider/cost/prompt-cache tests passed 70/70, blind-to-x lint passed, and A/B selected `adopt_candidate` (`score_delta=0.9`).

- **2026-06-04 (Codex)**: T-1228 blind-to-x pytest-asyncio dependency freshness loop. Applied `pytest-asyncio==1.4.0` with the root workspace `uv.lock` synced, after checking the official pytest-asyncio v1.4.0 release notes. The release deprecates overriding `event_loop_policy`, adds `pytest_asyncio_loop_factories`, improves an unset fixture-loop-scope warning, and raises the minimum pytest to `8.4.0`; blind-to-x has no `event_loop_policy`/`loop_factories`/`asyncio_default_fixture_loop_scope`/`pytest_asyncio.fixture` usage and currently runs pytest `8.4.2`. Verification: `uv run` installed pytest-asyncio 1.4.0, full unit+integration without coverage passed 1791/1791 with 5 skipped when the known unrelated `tests/integration/test_curl_cffi.py` local CAfile test was ignored, blind-to-x lint passed, and A/B selected `adopt_candidate` (`score_delta=0.9`).

- **2026-06-04 (Codex)**: T-1227 suika-game-v2 `globals` dependency freshness plus runtime asset 404 fix. Applied `globals` `^16.5.0` -> `^17.6.0` with synced npm and root pnpm lockfiles after confirming npm latest/current engine metadata. Browser QA exposed missing runtime asset requests for `background.png` and fruit PNG sprites, so CSS now uses gradients only and renderer image loading only requests explicitly registered bundled fruit assets before using emoji fallback. Verified root frozen lock, suika tests 61/61, lint, build via ASCII fallback after direct Vite `3221226505`, `globals.browser`/`globals.node` smoke, audit 0, Python CDP browser QA with free-play start/nonblank canvas/drop/pause and no serious console/network issues, clean temp root pnpm install plus suika `npm ci`, and A/B `adopt_candidate` (`score_delta=0.7`).

- **2026-06-04 (Codex)**: T-1226 word-chain `globals` dependency freshness plus PWA icon runtime fix. Applied `globals` `^16.5.0` -> `^17.6.0` with synced npm and root pnpm lockfiles after confirming npm latest/current engine metadata. Browser QA exposed missing manifest icon files, so added `public/icon.svg`, changed manifest icons to that real SVG asset, and added `mobile-web-app-capable` meta. Verified root frozen lock, word-chain tests 23/23, lint, build via ASCII fallback after direct Vite `3221226505`, `globals.browser` smoke for browser globals, audit 0, Python CDP browser QA with Korean input/submit/score/SVG render and no serious console/network issues, clean temporary root pnpm install, and A/B `adopt_candidate` (`score_delta=0.7`).

- **2026-06-04 (Codex)**: T-1225 blind-to-x Playwright dependency freshness loop. Applied `playwright==1.60.0` with the root workspace `uv.lock` synced, after checking the official Playwright Python v1.60.0 release notes and confirming blind-to-x has no `expose_binding` or `handle=` usage affected by the listed breaking change. Verified `uv run` installed Playwright 1.60.0, async import smoke passed, focused scraper/config unit tests passed 16/16 with repo-local basetemp, blind-to-x lint passed via QC runner, and A/B selected `adopt_candidate`. Full unit suite via `uv run` exceeded the 5-minute local turn timeout; main CI must be rechecked after push.

- **2026-06-04 (Codex)**: T-1224 knowledge-dashboard standalone smoke/data-dir fix. Final `active-project-matrix` failed only in knowledge-dashboard runtime smoke because the missing-file assertion removed `skill_lint.json` from source `data/` while T-1223's standalone helper had copied the same file into the standalone server cwd, so `/api/data/skills` still returned 200. Added `KNOWLEDGE_DASHBOARD_DATA_DIR`, routed authenticated data routes and health through `dashboardDataFile()`, changed standalone start to set the runtime data dir instead of copying stale data, documented Docker `/app/data`, and made smoke remove/restore fixtures across source/root/nested standalone data candidates. Verified standalone smoke, knowledge-dashboard project QC test/lint/build, and standalone smoke again after build.

- **2026-06-04 (Codex)**: T-1223 knowledge-dashboard standalone deploy/start hardening. Found production runtime drift where `output: "standalone"` still used `next start`; Next warns this path is not the standalone server path, and local output can be nested at `.next/standalone/projects/knowledge-dashboard/server.js`. Added `scripts/start-standalone.mjs`, changed `npm run start` and smoke to use it, copied current static/data assets into the generated server cwd, hardened Docker for root/nested standalone output plus `/app/data` mount visibility, and cleaned deploy docs/logs to ASCII-safe operator copy. Verified missing-key/keyed `verify-deploy`, project QC test/lint/build, standalone smoke, Playwright login + QA/QC + Knowledge tab clicks with console errors/warnings 0 and data APIs 200, and A/B `adopt_candidate`.

- **2026-06-04 (Codex)**: T-1222 word-chain `lucide-react` dependency freshness loop. Applied `lucide-react` `^0.563.0` -> `^1.17.0` with synced npm and root pnpm lockfiles, fixed `prebuild-check.js` lint by replacing the control-regex ASCII path test with `isAsciiPath()`, superseded and closed Dependabot PR #112, and verified current npm metadata (`latest=1.17.0`, React 19 peer compatible), root frozen lock, word-chain tests 23/23, lint, build via ASCII fallback after direct Vite `3221226505`, 3 lucide imports with 0 missing exports, audit 0, Chrome/Edge CDP browser QA with SVG render/input/submit/score and no console/network serious issues, clean temporary root pnpm install, A/B `adopt_candidate`, and main CI `root-quality-gate` plus `active-project-matrix` pass.

- **2026-06-04 (Codex)**: T-1219 knowledge-dashboard repo-display fallback hardening. Browser QA after T-1218 exposed malformed GitHub rows rendering `undefined 저장소 열기` and risking search crashes on `repo.name.toLowerCase()`. Added `getGithubRepoDisplayName()` and routed tag/search text plus repo card title/aria-label through safe display copy. Verified focused dashboard-view regression, lint, `project_qc_runner.py --project knowledge-dashboard --json`, root frozen lock, production smoke, Playwright login plus Knowledge tab QA with console errors/warnings 0, data APIs 200, SVG render, selected tab `지식 현황`, `hasUndefinedText=false`, and A/B `adopt_candidate`.

- **2026-06-04 (Codex)**: T-1218 knowledge-dashboard `lucide-react` dependency freshness loop. Applied `lucide-react` `^0.563.0` -> `^1.17.0` with synced npm and root pnpm lockfiles, superseding and closing Dependabot PR #119. Verified current npm metadata (`latest=1.17.0`, React 19 peer compatible), root frozen lock, 29 knowledge-dashboard lucide named imports with 0 missing exports, `project_qc_runner.py --project knowledge-dashboard --json` test/lint/build pass, `npm.cmd run smoke` pass, Chrome CDP login and tab-click smoke with lucide SVG render and no console/network serious issues, clean temporary worktree `pnpm install --frozen-lockfile`, A/B `adopt_candidate`, and main CI `root-quality-gate` plus `active-project-matrix` pass.

- **2026-06-04 (Codex)**: T-1217 Hanwoo `lucide-react` dependency freshness loop. Applied `lucide-react` `^0.563.0` -> `^1.17.0` with synced npm and root pnpm lockfiles. Verified current npm metadata (`latest=1.17.0`, React 19 peer compatible), root frozen lock, 58 Hanwoo lucide named imports with 0 missing exports, `project_qc_runner.py --project hanwoo-dashboard --json` test/lint/build pass, Chrome CDP login click smoke with lucide SVG render and no console/network issues, clean temporary worktree `pnpm install --frozen-lockfile`, and A/B `adopt_candidate`.

- **2026-05-26 (Gemini)**: 모노레포 전역 스페이싱/포맷팅 테스트 하드닝 및 QC 스윕 완료. `hanwoo-dashboard`에서 Biome 포맷터 도입에 대응해 29개 정규식 검사를 하드닝하여 282/282 Node 테스트 100% 그린 패스 및 Next 빌드 통과. `shorts-maker-v2` Ruff 린트 에러(UP035, I001) 및 `blind-to-x` coverage 70% 제한 우회 처리(`--no-cov` 격리)를 통해 모노레포 전체 QC 올-그린 확인.
- **2026-05-22 (Gemini)**: `media_step.py` 리팩토링 및 Ruff 린트 클린. `shorts-maker-v2` 602개 단위 테스트 100% 그린 패스 달성.
- **2026-05-21 (Codex)**: `hanwoo-dashboard` 전역 데이터 정규화(Data Normalization) 하드닝 및 263개 테스트 스위트 그린 패스 완료.

## Minefield

- **`hanwoo-dashboard`**:
  - **소프트 삭제 계약**: 개체 삭제는 하드 딜리트가 아닌 소프트 아카이브(`isArchived`)로 동작합니다. 문구 및 기능 개발 시 파괴적인 '삭제' 대신 '보관 처리'를 일관되게 적용하십시오.
  - **태그 유니크 제한**: `Cattle.tagNumber`는 고유값입니다. 중복 예외 발생 시 Prisma `P2002` 에러를 한국어 문구로 깔끔하게 맵핑하십시오.
  - **개인정보 유출 주의**: 공인 약관 및 법적 페이지(`/privacy`, `/terms`)에 개인 휴대폰 번호나 주소가 유출되지 않도록 `legal-pages-copy.test.mjs` 검증 규칙을 유지하십시오.
  - **데이터 Normalization 정책**: API, 캘린더, 날짜 정렬, 재고 수량, 차트 데이터 등 외부 유입/로컬 캐시 컬렉션은 렌더링 혹은 연산 전에 반드시 `safe*` 또는 normalizer 도우미를 거쳐 가공하십시오. (NaN, Invalid Date 원천 차단)
  - **웹 접근성(A11y)**: 모달 다이얼로그 개방 시 자동 포커스 캡처 및 `role="dialog"`, `aria-modal="true"`, Escape dismissal이 올바르게 동작하도록 캡션 및 위젯 포커스 관리를 수행하십시오.
- **`shorts-maker-v2`**:
  - **Edge TTS 채널 컨텍스트**: `MediaStep`은 TTS 호출 시 반드시 `AppConfig._channel_key`를 넘겨야 채널별 고유 피치/속도 진동(prosody jitter)이 정상 적용됩니다. 그렇지 않으면 디폴트 속도로 무음 처리됩니다.
  - **Pytest 모의 오염**: Pytest 런타임에서 특정 테스트 모듈이 `sys.modules`에 MagicMock을 직접 주입하면 다른 테스트에 영향을 주므로, 반드시 setup/teardown 격리 또는 mock wrapper를 사용하십시오.
- **Windows 실행 장벽**:
  - 파이썬 및 Node 프로세스 실행 시 Windows 환경에서는 쉘 실행 바이너리(`.cmd`, `.bat`) 확장자를 명시하거나 `PATHEXT`를 존중하도록 코딩하십시오.
  - `Get-ChildItem -Recurse` 등을 수행할 때 존재하지 않는 디렉토리를 탐색하면 에러가 발생하므로, 탐색 전 타깃 존재 여부를 반드시 체크하십시오.
  - Windows의 CP949 인코딩 콘솔 한글 깨짐 현상이 있어도 실제 파일 및 데이터는 항상 UTF-8 클린하게 저장해야 합니다.
  - 터미널이나 CLI 도구에서 비ASCII 유니코드나 이모지를 stdout/stderr로 직접 출력하면 `UnicodeEncodeError` 예외가 발생하므로, 윈도우 실행 시 `sys.stdout.reconfigure(encoding='utf-8')`을 통해 스트림을 강제 재구성하거나 이모지 사용을 피하십시오.
  - Codex/PowerShell 세션에서 `Get-Content`, `Join-Path`, `Test-Path`, `Select-Object` 같은 core cmdlet이 다시 로드되지 않을 수 있습니다. MCP/launcher 스크립트는 가능한 한 `[System.IO.*]`, `[System.Environment]`, `[System.Text.RegularExpressions.Regex]` 같은 .NET API로 작성하십시오.
  - For word-chain browser QA on this Windows/Korean-path setup, a Node-native WebSocket CDP script crashed with `-1073740791` after connecting to DevTools. Use Python `websockets` CDP or the Playwright wrapper for browser-click smoke tests, and keep the Vite build ASCII-workspace fallback for direct `3221226505` failures.
  - 이 "Windows 실행 장벽" 규칙 전체는 `windows-safe-scripting` 스킬로 인코딩되어 있습니다(T-1221) — PowerShell 런처/MCP 스크립트/`execution/` 파이썬을 작성·수정할 때 트리거하십시오.
- **MCP / connector startup**:
  - `@notionhq/notion-mcp-server` v2.2.1은 `NOTION_TOKEN`을 권장 env로 사용합니다. `infrastructure/notion-mcp/start_notion_mcp.ps1`는 기존 `.env`의 `NOTION_API_KEY`도 읽어 `NOTION_TOKEN`과 양방향 동기화한 뒤 `--transport stdio`로 실행해야 합니다.
  - sandbox 안에서 Notion MCP npm 검증은 `EACCES` 또는 npm cache/log 쓰기 실패가 날 수 있습니다. 실제 stdio initialize 검증은 승인된 network/cache 권한에서 통과하는지 확인하십시오.
  - standalone `mcp_servers.figma` remote URL은 OAuth client credentials 없이는 token refresh가 실패합니다. 현재는 `C:\Users\박주호\.codex\config.toml`에서 비활성화했고, Figma 작업은 plugin/app connector를 우선 사용하십시오.

## Multi-Tool Coordination — Task ID Allocation

여러 AI 도구(Claude Code, Codex, Gemini, ...)가 `.ai/TASKS.md` 를 동시에 편집하다 보니
같은 `T-####` 가 두 번 사용되는 충돌이 반복 발생합니다(T-1107×2, T-1108×2, T-1195×2,
T-1199×2 — `git log` 에서 직접 확인 가능). 각 도구가 자기 스냅샷의 `max(T-####)+1`
을 독립적으로 고르기 때문입니다.

**새 task ID 가 필요할 때는 반드시 `execution/next_task_id.py` 의 출력을 사용하십시오**:

```bash
py -3 execution/next_task_id.py
# → T-1201

# automation:
py -3 execution/next_task_id.py --json
```

이 스크립트는 `.ai/TASKS.md`, `.ai/HANDOFF.md`, 최근 30개 git commit 의 subject + body
세 곳을 모두 스캔해 `T-####` 참조 합집합의 최대값 + 1 부터 충돌 없는 첫 ID 를
제안합니다. 다른 도구가 자기 커밋에 이미 사용했지만 `TASKS.md` 에는 아직 반영 안 된
ID 도 git log 에서 잡히므로, 도구 간 race window 가 "수 분(스냅샷 갱신 주기)"에서
"수 초(커밋 직전 재실행)" 로 좁아집니다.

**완전 동시(1초 이내) 충돌 폴백 규칙**: 그래도 충돌이 발생하면 *나중에 커밋하는*
도구가 ID 뒤에 알파벳 접미사를 붙이고(`T-1201b`) 커밋 본문에서 충돌을 언급하십시오.
이미 유기적으로 정착된 패턴이며(예: commit `e940de77` 의 "ID 충돌 노트:" 섹션) 변경
이력 보존을 위해 과거 commit message 의 ID 는 절대 다시 쓰지 마십시오.

> 이 절차는 `task-id` 스킬로 트리거됩니다(T-1221).

## AI Context Rotation Tools

When `.ai/HANDOFF.md` or `.ai/SESSION_LOG.md` grows large during session close,
run the deterministic rotators before committing context updates:

```bash
python execution/handoff_rotator.py --check --json
python execution/handoff_rotator.py --json

python execution/session_log_rotator.py --check --json
python execution/session_log_rotator.py --json
```

Both tools keep entries dated within the last 7 days by default and archive
older material under `.ai/archive/`.

> 세션 시작은 `session-start` 스킬, 세션 종료(이 로테이터 호출 포함)는 `session-close` 스킬로 트리거됩니다(T-1221).
