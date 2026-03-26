
## 2026-03-26 | Codex | T-052 완료, workspace/projects 구조 리팩터링

### 작업 요약

루트 구조를 canonical layout으로 재편했다. 루트 제어면은 유지하고, 루트 소유 작업 영역은 `workspace/`로, 제품 저장소는 `projects/`로 이동했다. 이어서 `workspace/path_contract.py`를 추가해 새 경로 계약을 공통화했고, `qaqc_runner.py`, `joolife_hub.py`, 주요 Streamlit 페이지, doctor/smoke/quality 스크립트, 테스트 설정과 문서를 새 경로에 맞게 갱신했다. 루트 잡파일도 `.tmp/reports/`와 `_archive/`로 정리했다. 마지막으로 활성 skill 문서와 AI 컨텍스트 문서도 canonical 경로 기준으로 맞췄다.

### 변경 파일

| 파일 | 변경 유형 | 내용 |
|------|-----------|------|
| `workspace/` | 이동/신규 | `directives/`, `execution/`, `scripts/`, `tests/`를 루트에서 이동하고 canonical 작업 영역으로 정리 |
| `projects/` | 이동/신규 | `blind-to-x`, `shorts-maker-v2`, `hanwoo-dashboard`, `knowledge-dashboard`, `suika-game-v2`, `word-chain`를 제품 영역으로 이동 |
| `workspace/path_contract.py` | 신규 | canonical workspace/projects 경로 해석기 및 legacy 호환 resolver 추가 |
| `workspace/execution/qaqc_runner.py`, `workspace/execution/joolife_hub.py` | 수정 | QA/QC 및 허브 런처를 새 레이아웃과 경로 계약 기준으로 재작성 |
| `workspace/scripts/*.py`, `workspace/execution/pages/*.py`, `workspace/tests/**` | 수정 | root 경로 가정을 제거하고 `workspace/...` / `projects/...` 기준으로 정리 |
| `README.md`, `setup.bat`, `.gitignore`, `.agents/rules/project-rules.md` | 수정 | 새 canonical 구조, 명령 예시, 보고서/아티팩트 정리 규칙 반영 |
| `.ai/HANDOFF.md`, `.ai/TASKS.md`, `.ai/CONTEXT.md`, `.ai/DECISIONS.md`, `.ai/SESSION_LOG.md` | 수정 | 구조 리팩터링 완료 상태와 후속 작업 반영 |
| `.agents/skills/blind-to-x/SKILL.md`, `.agents/skills/content-calendar/SKILL.md`, `.agents/skills/cost-check/SKILL.md` | 수정 | skill 예시 경로를 canonical layout 기준으로 갱신 |

### 검증 결과

- `venv\Scripts\python.exe workspace\scripts\smoke_check.py` -> PASS
- `venv\Scripts\python.exe workspace\scripts\doctor.py` -> PASS (`PASS=9 WARN=0 FAIL=0`)
- `venv\Scripts\python.exe -X utf8 -m pytest -q workspace\tests\test_doctor.py workspace\tests\test_llm_bridge_integration.py workspace\tests\test_query_rag.py workspace\tests\test_qaqc_runner.py workspace\tests\test_qaqc_runner_extended.py workspace\tests\test_joolife_hub.py --no-cov -o addopts=` -> `78 passed, 1 skipped`
- `venv\Scripts\python.exe -X utf8 -m pytest -q workspace\tests\test_pipeline_watchdog.py workspace\tests\test_shorts_daily_runner.py workspace\tests\test_topic_auto_generator.py --no-cov -o addopts=` -> `62 passed`
- `venv\Scripts\python.exe -X utf8 -m pytest -q workspace\execution\tests --no-cov -o addopts=` -> `25 passed`
- `venv\Scripts\python.exe -X utf8 workspace\execution\qaqc_runner.py --project root --skip-infra --output .tmp\reports\root\qaqc_smoke.json` -> `APPROVED` (`915 passed, 1 skipped`, AST `20/20`, security `CLEAR`)

### 다음 도구에게 메모

- 루트 `shorts-maker-v2/`는 비어 있지만 다른 프로세스가 점유 중이라 이동/삭제가 실패했다. 실제 프로젝트 내용은 `projects/shorts-maker-v2/`에 있다.
- 현재 `git status`의 대량 삭제는 이동 전 루트 경로 기준 diff라서 정상이다. 새 구조 파일은 `workspace/`와 `projects/` 아래에서 확인하면 된다.
- 역사성 로그/아카이브에는 과거 루트 경로 표기가 남아 있을 수 있다. 새 코드와 새 문서는 canonical 경로만 사용한다.


## 2026-03-26 | Claude Code | T-051 완료, orchestrator.py unit tests 31개 추가 (15%→80%)

### 작업 요약

T-043의 후속으로 `orchestrator.py`의 helper 메서드 및 에러 경로를 단위 테스트로 커버했다. `test_orchestrator_unit.py` 31개 테스트 추가: JsonlLogger (info/warning/error, dir creation), renderer_mode 검증 (native/auto/shorts_factory/invalid), _load_channel_profile (missing file, valid, missing key, invalid yaml), _new_job_id (format, uniqueness), _save_manifest (file creation), _cleanup_run_dir (media 삭제, manifest 보존), _smart_retry_strategy (non-retryable abort, retry, max attempts, thumbnail fallback, rate limit backoff), run() 에러 경로 (TopicUnsuitableError, generic exception, media incomplete, resume nonexistent, resume with checkpoint, happy path, step timings), _try_shorts_factory_render delegation, shorts_factory without channel. shorts-maker-v2 전체 1076 passed, 0 failed, coverage 78%.

### 변경 파일

| 파일 | 변경 유형 | 내용 |
|------|-----------|------|
| `shorts-maker-v2/tests/unit/test_orchestrator_unit.py` | 신규 | orchestrator.py unit tests 31개 |
| `.ai/HANDOFF.md`, `.ai/TASKS.md`, `.ai/SESSION_LOG.md` | 수정 | T-051 완료 반영 |

### 검증 결과

- shorts-maker-v2: 1076 passed, 0 failed, 13 skipped
- orchestrator.py coverage: 15%→80%
- shorts-maker-v2 전체 coverage: 78%

---

## 2026-03-26 | Codex | T-043 완료, shorts orchestrator/render 상위 en-US smoke 추가

### 작업 요약

`shorts-maker-v2`의 다음 우선순위였던 `orchestrator`/`render_step` 상위 smoke를 추가했다. 신규 `tests/integration/test_orchestrator_i18n_smoke.py`는 실제 `ScriptStep`, 실제 `RenderStep.run()`, stub `MediaStep`, mocked encode/QC를 조합해 `ScriptStep -> Orchestrator -> RenderStep -> SRT export` 경로를 `en-US` 설정으로 검증한다. 작업 중 실제 버그도 두 개 같이 수정했다: `script_step.py`의 `_validate_script_schema()`가 alias scene fields(`narration`, `voiceover`, `visual_prompt`)를 schema validate 전에 canonical 필드로 정규화하도록 보강했고, `render_step.py`의 benchmark print는 Windows cp949 콘솔에서 깨지지 않도록 emoji를 ASCII-safe 텍스트로 교체했다.

### 변경 파일

| 파일 | 변경 유형 | 내용 |
|------|-----------|------|
| `shorts-maker-v2/tests/integration/test_orchestrator_i18n_smoke.py` | 신규 | `ScriptStep -> Orchestrator -> RenderStep -> SRT export` en-US 상위 smoke 추가 |
| `shorts-maker-v2/src/shorts_maker_v2/pipeline/script_step.py` | 수정 | `_validate_script_schema()`가 alias scene fields를 canonical 필드로 정규화 후 validate |
| `shorts-maker-v2/src/shorts_maker_v2/pipeline/render_step.py` | 수정 | benchmark print의 emoji 제거로 Windows cp949 콘솔 호환성 확보 |
| `.ai/HANDOFF.md` | 수정 | T-043 완료 및 다음 우선순위 반영 |
| `.ai/TASKS.md` | 수정 | T-043 DONE 처리, T-049/T-050 TODO 추가 |
| `.ai/CONTEXT.md` | 수정 | orchestrator 상위 smoke 및 Windows 인코딩 지뢰밭 업데이트 |
| `.ai/SESSION_LOG.md` | 수정 | 현재 세션 기록 추가 |

### 검증 결과

- `python -m ruff check src/shorts_maker_v2/pipeline/script_step.py src/shorts_maker_v2/pipeline/render_step.py tests/integration/test_orchestrator_i18n_smoke.py` -> clean
- `python -m pytest --no-cov tests/unit/test_script_step.py -q -k validate_script_schema_accepts_alias_scene_fields` (`shorts-maker-v2`) -> **1 passed, 2 warnings**
- `python -m pytest --no-cov tests/integration/test_orchestrator_i18n_smoke.py -q` (`shorts-maker-v2`) -> **1 passed, 2 warnings**
- `python -m pytest --no-cov tests/unit/test_script_step.py tests/unit/test_script_step_i18n.py tests/unit/test_i18n_en_us_smoke.py tests/integration/test_orchestrator_manifest.py tests/integration/test_renderer_mode_manifest.py tests/integration/test_orchestrator_i18n_smoke.py -q` (`shorts-maker-v2`) -> **17 passed, 8 warnings**

## 2026-03-26 — Antigravity (Gemini)
- **작업**: T-048 script_step.py i18n 마이그레이션 완료
- **변경 파일**: src/shorts_maker_v2/pipeline/script_step.py, scripts/patch_script_final.py`n- **결과**: 테스트 1043 passed, 12 skipped, unit 전체 통과
- **커밋**: feat(i18n): migrate script_step to dynamic YAML locale loading
## 2026-03-25 | Codex | T-042/T-045/T-047 완료, `script_step` locale 경계 복구 + 문서 정리

### 작업 요약

`shorts-maker-v2`의 `script_step.py`가 반쯤 섞인 i18n 상태로 남아 있던 부분을 정리했다. locale `field_names`와 `channel_review_criteria`가 다시 정상 적용되도록 복구했고, schema alias(`narration`, `voiceover`, `visual_prompt`) 검증을 되살렸다. 이어서 `_build_system_prompt()` / `_build_user_prompt()`에 남아 있던 dead prompt block을 제거하고, `locales/ko-KR/script_step.yaml`의 `korean_rules`도 `{narration_field}` placeholder를 쓰도록 맞췄다. 동시에 `.ai/HANDOFF.md`, `.ai/TASKS.md`, `.ai/CONTEXT.md`, `.ai/SESSION_LOG.md`를 현재 상태로 갱신하고, `SESSION_LOG.md`에서 2026-03-22 섹션을 별도 archive로 로테이션했다.

### 변경 파일

| 파일 | 변경 유형 | 내용 |
|------|-----------|------|
| `shorts-maker-v2/src/shorts_maker_v2/pipeline/script_step.py` | 수정 | locale prompt/review/field-name 경계 복구, schema alias validator 복구, dead prompt block 정리 |
| `shorts-maker-v2/locales/ko-KR/script_step.yaml` | 수정 | `korean_rules`에 `{narration_field}` placeholder 적용 |
| `.ai/HANDOFF.md` | 수정 | T-042/T-045/T-047 반영, 다음 우선순위 갱신 |
| `.ai/TASKS.md` | 수정 | T-042/T-045/T-047 DONE 처리, T-043 TODO 정리 |
| `.ai/CONTEXT.md` | 수정 | QC 기준선/진행 상황/지뢰밭 최신화 |
| `.ai/archive/CONTEXT_MINEFIELD_ARCHIVE.md` | 수정 | 해결된 i18n/locale 관련 지뢰밭 아카이브 추가 |
| `.ai/archive/SESSION_LOG_before_2026-03-23.md` | 신규 | 2026-03-22 세션 로그 로테이션 |
| `directives/enhancement_plan_v2.md` | 수정 | Phase 5B-1 현황 갱신 |

### 검증 결과

- `python -m pytest --no-cov tests/unit/test_script_step.py tests/unit/test_script_step_i18n.py tests/unit/test_i18n_en_us_smoke.py -q` (`shorts-maker-v2`) -> **13 passed, 2 warnings**
- `python -m ruff check src/shorts_maker_v2/pipeline/script_step.py tests/unit/test_script_step.py tests/unit/test_script_step_i18n.py tests/unit/test_i18n_en_us_smoke.py` -> clean

### 다음 도구에게 메모

- `script_step.py`는 이제 locale `field_names`/`channel_review_criteria`와 schema alias가 다시 정상 동작한다. 내부 `ScenePlan` 필드는 계속 `narration_ko`를 사용한다
- 다음 남은 실작업 후보는 `orchestrator -> render_step` 상위 smoke 또는 integration-heavy coverage (`T-043`)

## 2026-03-25 — Claude Code — T-046 완료, shorts coverage uplift (render_step 62%, edge_tts 91%)

### 작업 요약

Phase 5A-2를 이어서 `render_step.py`와 `edge_tts_client.py`의 테스트 커버리지를 추가 상향했다. `test_render_step.py`에 44개 테스트 추가 (mood GPT/classify, style override, caption combo, channel motion, transitions, ducking, Lyria BGM, SFX, fit_vertical 등), `test_edge_tts_timing.py`에 15개 테스트 추가 (_generate_async, _generate_async_with_timing, whisper/approximate fallback, failure cleanup, voice mapping 검증 등). 전체 QC 2498 passed, 0 failed. REJECTED은 `script_step.py` AST 에러 (기존 미정리 변경)가 원인.

### 변경 파일

| 파일 | 변경 유형 | 내용 |
|------|-----------|------|
| `shorts-maker-v2/tests/unit/test_render_step.py` | 수정 | +44 tests, render_step.py 54%→62% |
| `shorts-maker-v2/tests/unit/test_edge_tts_timing.py` | 수정 | +15 tests, edge_tts_client.py 91% 유지 |
| `.ai/HANDOFF.md`, `.ai/TASKS.md`, `.ai/SESSION_LOG.md` | 수정 | T-046 완료 반영, T-047 신규 등록 |

### 검증 결과

- shorts-maker-v2: 1042 passed, 0 failed, 12 skipped
- 전체 QC: 2498 passed, 0 failed, 29 skipped
- Security scan: CLEAR
- AST check: 19/20 OK (script_step.py 기존 에러)

---

## 2026-03-25 ??Codex ??T-038 ?꾨즺, shorts render_step/edge_tts coverage uplift

### ?묒뾽 ?붿빟

Phase 5A-2瑜??댁뼱??`shorts-maker-v2`???⑥? ?而ㅻ쾭由ъ? ?듭떖 紐⑤뱢 ??媛쒕? 吏곸젒 蹂닿컯?덈떎. `render_step.py`??湲곗〈 ?뚯뒪?멸? mood/BGM ?꾩＜??移섏슦爾??덉뼱 helper? 遺꾧린 濡쒖쭅???ш쾶 鍮꾩뼱 ?덉뿀怨? `edge_tts_client.py`??async save/stream, fallback, cleanup 寃쎈줈媛 嫄곗쓽 臾댄뀒?ㅽ듃??? ?좉퇋 `test_render_step_phase5.py` 18嫄댁쑝濡?native renderer passthrough, style override, caption combo/channel motion, safe-zone caption ?꾩튂, TextEngine fallback, intro/outro bookend 鍮뚮뱶 遺꾧린瑜?怨좎젙?덇퀬, ?좉퇋 `test_edge_tts_phase5.py` 9嫄댁쑝濡?`_generate_async`, `_generate_async_with_timing`, whisper/approximate fallback, default-voice retry, failure cleanup??怨좎젙?덈떎. 湲곗〈 `test_edge_tts_timing.py`??`_run_coroutine` ?뚯뒪?몃뒗 coroutine close 濡쒖쭅??異붽???ResourceWarning???쒓굅?덈떎.

### 蹂寃??뚯씪

| ?뚯씪 | 蹂寃??좏삎 | ?댁슜 |
|------|-----------|------|
| `shorts-maker-v2/tests/unit/test_render_step_phase5.py` | ?좉퇋 | `render_step.py` helper/branch coverage ?뚯뒪??18嫄?異붽? |
| `shorts-maker-v2/tests/unit/test_edge_tts_phase5.py` | ?좉퇋 | `edge_tts_client.py` async/fallback/cleanup ?뚯뒪??9嫄?異붽? |
| `shorts-maker-v2/tests/unit/test_edge_tts_timing.py` | ?섏젙 | `_run_coroutine` ?뚯뒪?몄뿉??coroutine close 泥섎━濡?warning ?쒓굅 |
| `.ai/HANDOFF.md`, `.ai/TASKS.md`, `.ai/CONTEXT.md`, `.ai/SESSION_LOG.md` | ?섏젙 | T-038 ?꾨즺 諛?coverage 痢≪젙 吏猶곕강 諛섏쁺 |

### 寃利?寃곌낵

- `python -m pytest --no-cov tests/unit/test_render_step.py tests/unit/test_render_step_phase5.py tests/unit/test_render_utils.py tests/unit/test_edge_tts_timing.py tests/unit/test_edge_tts_phase5.py tests/unit/test_edge_tts_retry.py tests/unit/test_whisper_aligner.py -q` (`shorts-maker-v2`) ??**170 passed, 2 warnings** ??- `python -m coverage run --source=src -m pytest --no-cov tests/unit/test_render_step.py tests/unit/test_render_step_phase5.py tests/unit/test_render_utils.py tests/unit/test_edge_tts_timing.py tests/unit/test_edge_tts_phase5.py tests/unit/test_edge_tts_retry.py tests/unit/test_whisper_aligner.py -q` ???깃났 ??- `python -m coverage report -m --include="src/shorts_maker_v2/pipeline/render_step.py,src/shorts_maker_v2/providers/edge_tts_client.py"` ??`render_step.py` **54%**, `edge_tts_client.py` **97%** ??
### ?ㅼ쓬 ?꾧뎄?먭쾶 硫붾え

- `render_step.py`???⑥? 誘몄빱踰??곸뿭? ?遺遺?`run()` 蹂몄껜, transitions, BGM/SFX, thumbnail 異붿텧 媛숈? integration-heavy 寃쎈줈??
- Python 3.14 ?섍꼍?먯꽌 `pytest --cov=shorts_maker_v2.pipeline.render_step` ?먮뒗 `coverage --source=shorts_maker_v2...`??numpy import 異⑸룎/臾댁닔吏묒씠 ?????덈떎. 紐⑤뱢 媛쒕퀎 痢≪젙? `python -m coverage run --source=src -m pytest --no-cov ...` ??`coverage report --include=...` ?⑦꽩???덉쟾?덈떎.

## 2026-03-25 ??Claude Code ??T-033~T-037 ?꾨즺, Phase 5 臾몄꽌??+ dead code/legacy 議곗궗

### ?묒뾽 ?붿빟

T-033?먯꽌 `directives/enhancement_plan_v2.md`??Phase 5瑜?Phase 5A(?덉쭏 媛뺥솕, 利됱떆)? Phase 5B(李⑥꽭?, ?먯깋??濡??댁썝?뷀븯???뺤옣?덈떎. 5A?먮뒗 coverage 紐⑺몴 ?곹뼢(?꾨즺), ?⑥? ?而ㅻ쾭由ъ? 紐⑤뱢, 吏猶곕강 ?뺣━, dead code 議곗궗瑜??ы븿?섍퀬, 5B?먮뒗 i18n 遺꾨━(7媛??곸뿭 紐낆꽭), ?륂뤌?믩”?? 媛먯꽦 ??쒕낫?? A/B ?뚯뒪?? SaaS ?꾪솚??諛곗튂?덈떎. T-034?먯꽌 shorts i18n ?꾪솴???먯깋???섎뱶肄붾뵫???쒓뎅???꾨＼?꾪듃/???섎Ⅴ?뚮굹/CTA 湲덉???留욎땄踰?洹쒖튃??遺꾨━ ??곸쓣 紐낆꽭?덈떎. T-036?먯꽌 `video_renderer_backend`媛 dead code媛 ?꾨땶 MoviePy+FFmpeg ????뚮뜑???ㅺ퀎?꾩쓣 ?뺤씤?덇퀬, T-037?먯꽌 `tests/legacy/`媛 ShortsFactory ?쒗뵆由??뚯뒪?몃줈??QC 踰붿쐞 ???좎?媛 ?곸젅?⑥쓣 寃곗젙?덈떎.

### 蹂寃??뚯씪

| ?뚯씪 | 蹂寃??좏삎 | ?댁슜 |
|------|-----------|------|
| `directives/enhancement_plan_v2.md` | ?섏젙 | Phase 5 ??5A(?덉쭏媛뺥솕)/5B(李⑥꽭?) ?댁썝?? ?곗꽑?쒖쐞 留ㅽ듃由?뒪 媛깆떊 |
| `.ai/HANDOFF.md`, `.ai/TASKS.md`, `.ai/SESSION_LOG.md` | ?섏젙 | T-033~T-037 ?꾨즺 諛섏쁺 |

### 寃利?寃곌낵

- 臾몄꽌 由щ럭 湲곕컲 ?묒뾽 (肄붾뱶 蹂寃??놁쓬, QC ?곹뼢 ?놁쓬)
- T-036: `video_renderer_backend`??`render_step.py`?먯꽌 ????뚮뜑?щ줈 ?ъ슜, ?뚯뒪??而ㅻ쾭 ?뺤씤
- T-037: `tests/legacy/` 5?뚯씪 紐⑤몢 import ?명솚, ShortsFactory 蹂꾨룄 紐⑤뱢 ?뚯뒪??
---

## 2026-03-25 ??Claude Code ??T-030~T-032 ?꾨즺, shorts+blind-to-x coverage uplift + full QC

### ?묒뾽 ?붿빟

?꾩껜 ?꾨줈?앺듃 濡쒕뱶留듭쓣 ?섎┰????Phase A 利됱떆 ?ㅽ뻾 ??ぉ 3嫄댁쓣 泥섎━?덈떎. T-030?먯꽌 shorts-maker-v2???而ㅻ쾭由ъ? 5媛?紐⑤뱢??蹂닿컯?덈떎: `animations.py` 81%??00% (+4 mask/shift ?뚯뒪??, `broll_overlay.py` 97%??00% (+1 opacity exception), `openai_client.py`???대? 100%, `google_client.py` 21%??8% (?좉퇋 `test_google_client.py` 27嫄?, `edge_tts_client.py` 44%??5% (+13 helper/prosody/coroutine ?뚯뒪??. T-031?먯꽌 blind-to-x `pipeline/commands/` ?꾩껜瑜?100%濡??뚯뼱?щ졇??(?좉퇋 `test_reprocess_command.py` 5嫄?. T-032?먯꽌 full QC瑜??ъ떎?됲빐 **2362 passed, 0 failed, 29 skipped, APPROVED**瑜??뺤씤?덈떎.

### 蹂寃??뚯씪

| ?뚯씪 | 蹂寃??좏삎 | ?댁슜 |
|------|-----------|------|
| `shorts-maker-v2/tests/unit/test_animations.py` | ?섏젙 | mask filter + zero/negative shift ?뚯뒪??4嫄?異붽? |
| `shorts-maker-v2/tests/unit/test_broll_overlay.py` | ?섏젙 | opacity exception fallback ?뚯뒪??1嫄?異붽? |
| `shorts-maker-v2/tests/unit/test_google_client.py` | ?좉퇋 | GoogleClient ??硫붿꽌???뚭? ?뚯뒪??27嫄?|
| `shorts-maker-v2/tests/unit/test_edge_tts_timing.py` | ?섏젙 | prosody/approximate/silence/coroutine ?뚯뒪??13嫄?異붽? |
| `blind-to-x/tests/unit/test_reprocess_command.py` | ?좉퇋 | run_reprocess_approved ?뚭? ?뚯뒪??5嫄?|
| `.ai/HANDOFF.md`, `.ai/TASKS.md`, `.ai/SESSION_LOG.md` | ?섏젙 | T-030~T-032 ?꾨즺 諛?QC 湲곗???媛깆떊 |

### 寃利?寃곌낵

- shorts targeted suite: **107 passed** (animations 28 + broll 16 + openai 12 + google 27 + edge_tts 24)
- blind-to-x commands suite: **15 passed** (dry_run 7 + one_off 3 + reprocess 5)
- full QC: **2362 passed, 29 skipped, 0 failed** ??APPROVED

---

## 2026-03-25 ??Codex ??T-035 ?꾨즺, blind-to-x CA bundle fix + QAQC status contract 蹂듦뎄

### ?묒뾽 ?붿빟

肄붾뱶由щ럭?먯꽌 ?뺤씤????媛吏 ?ㅼ젣 ?뚭?瑜?諛붾줈 ?섏젙?덈떎. `blind-to-x/config.py`??`certifi.where()`瑜?洹몃?濡?`CURL_CA_BUNDLE`???ｋ뜕 諛⑹떇??Windows ?쒓? ?ъ슜??寃쎈줈?먯꽌???ъ쟾??鍮껦SCII 寃쎈줈??`curl_cffi` Error 77 ?고쉶媛 ?섏? ?딆븯?? ?대? `%PUBLIC%` ?먮뒗 `%ProgramData%` ?꾨옒 ASCII-only 寃쎈줈濡?CA 踰덈뱾??蹂듭궗?섍퀬, ?ㅽ뙣 ??short path瑜??곕뒗 諛⑹떇?쇰줈 諛붽엥?? ?숈떆??`execution/qaqc_runner.py`??triaged-only 蹂댁븞 寃곌낵瑜?`"CLEAR (n triaged issue(s))"`濡???뼱??`status === "CLEAR"` ?뚮퉬?먮? 源⑤쑉由ш퀬 ?덉뿀?쇰?濡? machine-readable `status`??`CLEAR`/`WARNING`?쇰줈 ?섎룎由ш퀬 ?쒖떆??`status_detail` 諛?count ?꾨뱶瑜?遺꾨━?덈떎. `knowledge-dashboard/src/components/QaQcPanel.tsx`?????꾨뱶瑜??쎈룄濡?留욎톬??

### 蹂寃??뚯씪

| ?뚯씪 | 蹂寃??좏삎 | ?댁슜 |
|------|-----------|------|
| `blind-to-x/config.py` | ?섏젙 | ASCII-safe CA bundle helper 異붽?, `load_env()`媛 `certifi` 踰덈뱾??`%PUBLIC%`/`%ProgramData%` 寃쎈줈濡?蹂듭궗 ??`CURL_CA_BUNDLE`???곌껐 |
| `blind-to-x/tests/unit/test_env_runtime_fallbacks.py` | ?섏젙 | ASCII 寃쎈줈 蹂듭궗 ?곗꽑, short path fallback 寃利??뚯뒪??異붽? |
| `execution/qaqc_runner.py` | ?섏젙 | `security_scan.status` ?덉젙 enum 蹂듦뎄, `status_detail`/`triaged_issue_count`/`actionable_issue_count` 遺꾨━, 肄섏넄 異쒕젰??`status_detail` ?ъ슜 |
| `tests/test_qaqc_runner_extended.py` | ?섏젙 | triaged-only 蹂댁븞 ?댁뒋媛 ?ъ쟾??`status == "CLEAR"`瑜??좎??섎뒗 ?뚭? ?뚯뒪??異붽? |
| `knowledge-dashboard/src/components/QaQcPanel.tsx` | ?섏젙 | `status_detail` ?뚮퉬, triaged false positive 移댁슫???쒖떆, 湲곗〈 unused import/const ?뺣━ |
| `.ai/HANDOFF.md`, `.ai/TASKS.md`, `.ai/CONTEXT.md`, `.ai/SESSION_LOG.md` | ?섏젙 | T-035 ?꾨즺 諛??꾩냽 TODO/吏猶곕강 媛깆떊 |

### 寃利?寃곌낵

- `venv\\Scripts\\python -X utf8 -m pytest tests/unit/test_env_runtime_fallbacks.py -q -o addopts=` (`blind-to-x`) ??**5 passed** ??- `venv\\Scripts\\python -X utf8 -m pytest tests/test_qaqc_runner.py tests/test_qaqc_runner_extended.py -q -o addopts=` ??**30 passed** ??- `venv\\Scripts\\python -X utf8 -m py_compile blind-to-x/config.py execution/qaqc_runner.py` ???깃났 ??- `venv\\Scripts\\ruff check blind-to-x/config.py execution/qaqc_runner.py blind-to-x/tests/unit/test_env_runtime_fallbacks.py tests/test_qaqc_runner_extended.py` ??clean ??- `npm.cmd exec tsc -- --noEmit` (`knowledge-dashboard`) ???깃났 ??- `npm.cmd run lint -- src/components/QaQcPanel.tsx` (`knowledge-dashboard`) ???깃났 ??- `git diff --check`??**湲곗〈 unrelated ?댁뒋** `execution/_logging.py:120`??blank line at EOF ?뚮Ц???ъ쟾???ㅽ뙣

### ?ㅼ쓬 ?꾧뎄?먭쾶 硫붾え

- `knowledge-dashboard/public/qaqc_result.json`? ?대쾲 ?몄뀡?먯꽌 ?ъ깮?깊븯吏 ?딆븯?? `T-032`濡?full QC瑜??ㅼ떆 ?뚮젮 ??`security_scan` ?꾨뱶瑜?諛섏쁺?섎㈃ ?쒕떎.
- `shorts-maker-v2` 由щ럭?먯꽌 諛쒓껄??`video_renderer_backend` orchestrator 誘몄뿰寃? `tests/legacy/` helper API QC ?쒖쇅 ?댁뒋??媛곴컖 `T-036`, `T-037`濡??깅줉?덈떎.

---

## 2026-03-25 ??Codex ??T-029 ?꾨즺, shorts CLI/audio postprocess coverage uplift

### ?묒뾽 ?붿빟

Phase 5 coverage uplift瑜??댁뼱??`shorts-maker-v2`??`cli.py`? `render/audio_postprocess.py`瑜?蹂닿컯?덈떎. `cli.py`??`_doctor`, `_pick_from_db`, `_run_batch`, `run_cli` 二쇱슂 遺꾧린?ㅼ씠 嫄곗쓽 臾댄뀒?ㅽ듃 ?곹깭?怨? `audio_postprocess.py`???꾨컲遺 `_apply_compression`/`_apply_subtle_reverb`? `compress`/`reverb` 遺꾧린媛 鍮꾩뼱 ?덉뿀?? `cli.py`???좉퇋 `test_cli.py` 12嫄댁쑝濡?batch/topics file/from-db, dashboard/costs, run success/fail, doctor 遺꾧린瑜?怨좎젙?덈떎. `audio_postprocess.py`??湲곗〈 ?뚯뒪?몃? ?뺤옣??private helper? postprocess toggle 遺꾧린源뚯? ?≪븯怨? ?ㅼ젣 `pydub` ?ㅼ튂 ?щ????섏〈?섏? ?딅룄濡?fake `pydub` module 二쇱엯 諛⑹떇??異붽??덈떎.

### 蹂寃??뚯씪

| ?뚯씪 | 蹂寃??좏삎 | ?댁슜 |
|------|-----------|------|
| `shorts-maker-v2/tests/unit/test_cli.py` | ?좉퇋 | `_doctor`, `_pick_from_db`, `_run_batch`, `run_cli` 二쇱슂 遺꾧린 ?뚭? ?뚯뒪??12嫄?異붽? |
| `shorts-maker-v2/tests/unit/test_audio_postprocess.py` | ?섏젙 | compression/reverb helper, toggle 遺꾧린, fake `pydub` module 二쇱엯 ?뚯뒪??異붽? |
| `.ai/HANDOFF.md`, `.ai/TASKS.md`, `.ai/CONTEXT.md`, `.ai/SESSION_LOG.md` | ?섏젙 | T-029 ?꾨즺 諛?理쒖떊 coverage uplift ?곹깭/吏猶곕강 媛깆떊 |

### 寃利?寃곌낵

- `venv\\Scripts\\python.exe -X utf8 -m pytest -o addopts= tests\\unit\\test_cli.py -q` (`shorts-maker-v2`) ??**12 passed** ??- `venv\\Scripts\\python.exe -X utf8 -m pytest -o addopts= tests\\unit\\test_cli.py --cov=shorts_maker_v2.cli --cov-report=term-missing -q` ??`cli.py` **67%** ??- `venv\\Scripts\\python.exe -X utf8 -m pytest -o addopts= tests\\unit\\test_audio_postprocess.py -q` (`shorts-maker-v2`) ??**29 passed, 12 skipped** ??- `venv\\Scripts\\python.exe -X utf8 -m pytest -o addopts= tests\\unit\\test_audio_postprocess.py --cov=shorts_maker_v2.render.audio_postprocess --cov-report=term-missing -q` ??`audio_postprocess.py` **85%** ??- `venv\\Scripts\\python.exe -X utf8 -m pytest -o addopts= tests\\unit\\test_end_cards.py tests\\unit\\test_srt_export.py tests\\unit\\test_cli.py tests\\unit\\test_audio_postprocess.py -q` ??**60 passed, 12 skipped** ??
### ?ㅼ쓬 ?꾧뎄?먭쾶 硫붾え

- ?ㅼ쓬 coverage uplift ?꾨낫??`render/animations.py`, `render/broll_overlay.py`, `providers/openai_client.py`??
- `audio_postprocess.py`??fake `pydub` injection ?⑦꽩???ъ궗?⑺븯硫??섍꼍 ?섏〈 ?놁씠 異붽? 遺꾧린瑜??쎄쾶 硫붿슱 ???덈떎.

---

## 2026-03-25 ??Codex ??T-028 ?꾨즺, shorts render utility coverage uplift

### ?묒뾽 ?붿빟

Phase 5 coverage uplift ?꾩냽?쇰줈 `shorts-maker-v2`?먯꽌 寃곗젙濡좎쟻?대㈃???뚯뒪??怨듬갚?????뚮뜑 ?좏떥 紐⑤뱢??癒쇱? 硫붿썱?? 湲곗〈 coverage XML 湲곗??쇰줈 `render/ending_card.py`? `render/outro_card.py`??0%, `render/srt_export.py`??54% ?섏??댁뿀怨? ?ㅼ젣 ?뚮뜑媛 Windows ?고듃(`malgun.ttf`) ?섍꼍?먯꽌 臾몄젣?놁씠 ?숈옉?섎뒗吏 癒쇱? ?뺤씤?????뚯뒪?몃? 異붽??덈떎. 寃곌낵?곸쑝濡?`test_end_cards.py` ?좉퇋 7嫄? `test_srt_export.py` ?뺤옣 6嫄?珥?12嫄??쇰줈 移대뱶 ?앹꽦/?ъ궗???ㅽ뙣 ?대갚, SRT 泥?겕 蹂묓빀, JSON 湲곕컲 export, narration fallback, ?뚯닔??臾몄옣 遺꾨━源뚯? 怨좎젙?덈떎.

### 蹂寃??뚯씪

| ?뚯씪 | 蹂寃??좏삎 | ?댁슜 |
|------|-----------|------|
| `shorts-maker-v2/tests/unit/test_end_cards.py` | ?좉퇋 | ending/outro 移대뱶 ?뚮뜑, wrapper ?꾩엫, asset ?ъ궗???ㅽ뙣 ?대갚, ?됱긽 helper ?뚭? ?뚯뒪??7嫄?異붽? |
| `shorts-maker-v2/tests/unit/test_srt_export.py` | ?섏젙 | 吏㏃? 泥?겕 蹂묓빀, pending flush, JSON 湲곕컲 export, narration fallback, decimal sentence split ?뚯뒪??異붽? |
| `.ai/HANDOFF.md`, `.ai/TASKS.md`, `.ai/CONTEXT.md`, `.ai/SESSION_LOG.md` | ?섏젙 | T-028 ?꾨즺 諛??ㅼ쓬 coverage ?꾨낫/?고듃 吏猶곕강 諛섏쁺 |

### 寃利?寃곌낵

- `venv\\Scripts\\python.exe -X utf8 -m pytest -o addopts= tests\\unit\\test_end_cards.py -q` (`shorts-maker-v2`) ??**7 passed** ??- `venv\\Scripts\\python.exe -X utf8 -m pytest -o addopts= tests\\unit\\test_end_cards.py --cov=shorts_maker_v2.render.outro_card --cov=shorts_maker_v2.render.ending_card --cov-report=term-missing -q` ??`ending_card.py` **94%**, `outro_card.py` **93%** ??- `venv\\Scripts\\python.exe -X utf8 -m pytest -o addopts= tests\\unit\\test_srt_export.py -q` (`shorts-maker-v2`) ??**12 passed** ??- `venv\\Scripts\\python.exe -X utf8 -m pytest -o addopts= tests\\unit\\test_srt_export.py --cov=shorts_maker_v2.render.srt_export --cov-report=term-missing -q` ??`srt_export.py` **95%** ??
### ?ㅼ쓬 ?꾧뎄?먭쾶 硫붾え

- ?ㅼ쓬 coverage uplift ?꾨낫??`cli.py`(36%), `audio_postprocess.py`(42%), `animations.py`(9.8%) 履쎌씠?? ??以?`cli.py`? `audio_postprocess.py`媛 癒쇱? ?먮?湲??ъ썙 蹂댁씤??
- 移대뱶 ?뚮뜑 ?뚯뒪?몃뒗 Windows ?고듃 寃쎈줈媛 ?꾩슂?섎?濡? 湲곕낯 PIL ?고듃留?媛?뺥븯吏 ?딅뒗 ?몄씠 ?덉쟾?섎떎.

---

## 2026-03-25 ??Codex ??T-027 ?꾨즺, scheduler locale ?뚯떛 ?섏젙 + full QC ?ш?利?
### ?묒뾽 ?붿빟

handoff???⑥븘 ?덈뜕 Task Scheduler `0/6 Ready` 吏묎퀎瑜??ㅼ젣 Windows Task Scheduler? ?議고븳 寃곌낵, ?깅줉??`BlindToX_*` 5媛쒖? `BlindToX_Pipeline` 1媛쒕뒗 紐⑤몢 **Ready**??? ?먯씤? `execution/qaqc_runner.py`媛 `schtasks /query /fo CSV /nh` 異쒕젰??UTF-8 湲곗??쇰줈 ?쎌쑝硫댁꽌 ?쒓뎅???곹깭媛?`以鍮?瑜?`占쌔븝옙`濡?源⑤쑉由????덉뿀?? 1李⑤줈 locale 湲곕컲 ?붿퐫?⑹쓣 ?ｌ뿀吏留? full QC媛 `python -X utf8`濡??ㅽ뻾?섎㈃ `locale.getpreferredencoding(False)`媛 ?ㅼ떆 UTF-8??諛섑솚?섎뒗 ?⑥젙???덉뼱 `locale.getencoding()` 湲곕컲?쇰줈 ?ъ닔?뺥뻽?? ?댄썑 targeted ?뚭? ?뚯뒪?몄? `-X utf8` 吏곸젒 ?몄텧???뺤씤????full QC瑜??ъ떎?됲빐 Scheduler **`6/6 Ready`**, 理쒖쥌 ?먯젙 **`APPROVED`**瑜??뺤씤?덈떎. 媛숈? full QC?먯꽌 `test_golden_render_moviepy` flaky???щ컻?섏? ?딆븯??

### 蹂寃??뚯씪

| ?뚯씪 | 蹂寃??좏삎 | ?댁슜 |
|------|-----------|------|
| `execution/qaqc_runner.py` | ?섏젙 | Windows `schtasks` CSV瑜?`locale.getencoding()`?쇰줈 ?붿퐫?⑺븯怨?CSV 而щ읆 湲곗??쇰줈 `Ready`/`以鍮? ?곹깭瑜?吏묎퀎?섎룄濡??섏젙 |
| `tests/test_qaqc_runner_extended.py` | ?섏젙 | localized scheduler status(`以鍮?)? UTF-8 mode ?뚭? ?뚯뒪??異붽? |
| `knowledge-dashboard/public/qaqc_result.json` | 媛깆떊 | latest full QC 寃곌낵 ???(`APPROVED`, Scheduler `6/6 Ready`) |
| `.ai/HANDOFF.md`, `.ai/TASKS.md`, `.ai/CONTEXT.md`, `.ai/SESSION_LOG.md` | ?섏젙 | T-027 ?꾨즺, 理쒖떊 QC 湲곗???吏猶곕강/?꾩냽 ?묒뾽 諛섏쁺 |

### 寃利?寃곌낵

- `python -m pytest -o addopts= tests/test_qaqc_runner_extended.py -q` ??**6 passed** ??- `venv\\Scripts\\python.exe -X utf8 -c "from execution.qaqc_runner import check_infrastructure; ..."` ??Scheduler **`6/6 Ready`** ??- `venv\\Scripts\\python.exe -X utf8 execution\\qaqc_runner.py` ??**full QC `APPROVED`** / blind-to-x **534 passed, 16 skipped**, shorts-maker-v2 **776 passed, 8 skipped**, root **914 passed, 1 skipped**, total **2224 passed, 25 skipped** / Scheduler **`6/6 Ready`** ??
### ?ㅼ쓬 ?꾧뎄?먭쾶 硫붾え

- `test_golden_render_moviepy`??2026-03-25 full QC?먯꽌 ?щ컻?섏? ?딆븯?? ?댄썑 full QC?먯꽌 愿李곕쭔 ?좎??섎㈃ ?쒕떎.
- Windows?먯꽌 `python -X utf8`濡??ㅽ뻾?섎뒗 CLI??locale-sensitive subprocess 異쒕젰?먯꽌 `locale.getpreferredencoding(False)`瑜?洹몃?濡??곕㈃ ?ㅽ깘???앷만 ???덈떎.

---

## 2026-03-24 ??Codex ??T-026 ?꾨즺, security scan CLEAR + full QC APPROVED

### ?묒뾽 ?붿빟

T-026???댁뼱諛쏆븘 security scan 6嫄댁쓽 ?ㅼ젣 ?먯씤???ㅼ떆 遺꾨쪟?덈떎. `blind-to-x/pipeline/cost_db.py`?먮뒗 留덉씠洹몃젅?댁뀡/?꾩뭅?대툕 ???寃利?媛?쒕? 異붽??덇퀬, `execution/qaqc_runner.py`?먮뒗 line-level `# noqa`? triage metadata 臾몄옄?댁쓣 臾댁떆?섎뒗 security scan ?뺣━ 濡쒖쭅 諛?triage helper瑜??ｌ뿀?? ?댄썑 targeted ?뚭? ?뚯뒪?몄? full QC瑜??ㅼ떆 ?뚮젮 security scan **CLEAR**, 理쒖쥌 ?먯젙 **APPROVED**瑜??뺤씤?덈떎.

### 蹂寃??뚯씪

| ?뚯씪 | 蹂寃??좏삎 | ?댁슜 |
|------|-----------|------|
| `blind-to-x/pipeline/cost_db.py` | ?섏젙 | `_ensure_column()`???덉슜???뚯씠釉?而щ읆/DDL 寃利?異붽?, archive ?뚯씠釉붾챸 寃利?蹂닿컯 |
| `execution/qaqc_runner.py` | ?섏젙 | security triage 洹쒖튃, `# noqa`/`match_preview` 硫뷀??곗씠??臾댁떆, actionable issue 湲곗? ?먯젙 異붽? |
| `tests/test_qaqc_runner.py` | ?섏젙 | triaged security issue媛 `APPROVED`瑜?留됱? ?딅뒗 ?뚭? ?뚯뒪??異붽? |
| `blind-to-x/tests/unit/test_cost_db_security.py` | ?좉퇋 | `CostDatabase._ensure_column()`???덉슜/嫄곕? 寃쎈줈 ?뚯뒪??3嫄?異붽? |
| `knowledge-dashboard/public/qaqc_result.json` | 媛깆떊 | latest full QC 寃곌낵 ???(`APPROVED`) |
| `.ai/HANDOFF.md`, `.ai/TASKS.md`, `.ai/CONTEXT.md`, `.ai/SESSION_LOG.md` | ?섏젙 | T-026 ?꾨즺 諛?理쒖떊 QC 湲곗???諛섏쁺 |

### 寃利?寃곌낵

- `venv\\Scripts\\python.exe -X utf8 -m pytest tests/test_qaqc_runner.py tests/test_qaqc_runner_extended.py tests/test_content_db.py blind-to-x/tests/unit/test_cost_db_security.py -q --tb=short --no-header -o addopts=` ??**69 passed** ??- `venv\\Scripts\\python.exe -X utf8 -c "import json, execution.qaqc_runner as q; print(json.dumps(q.security_scan(), indent=2, ensure_ascii=False))"` ??**`CLEAR`** ??- `venv\\Scripts\\python.exe -X utf8 execution\\qaqc_runner.py --project root --skip-infra --output .tmp\\t026_qaqc.json` ??**`APPROVED`** / root **913 passed, 1 skipped** ??- `venv\\Scripts\\python.exe -X utf8 execution\\qaqc_runner.py` ??**full QC `APPROVED`** / blind-to-x **534 passed, 16 skipped**, shorts-maker-v2 **776 passed, 8 skipped**, root **913 passed, 1 skipped**, total **2223 passed, 25 skipped** ??
### ?ㅼ쓬 ?꾧뎄?먭쾶 硫붾え

- latest `knowledge-dashboard/public/qaqc_result.json`? ?댁젣 `APPROVED` 湲곗??대떎.
- latest infra check?먯꽌 Task Scheduler媛 `0/6 Ready`濡?吏묎퀎?먮떎. ?댁쟾 handoff??`BlindToX_Pipeline Ready`? 李⑥씠媛 ?덉뼱, ?ㅼ?以꾨윭瑜??ㅼ떆 留뚯쭏 ???ㅼ젣 Task Scheduler ?곹깭瑜?癒쇱? ?議고븯???몄씠 ?덉쟾?섎떎.
- ?⑥? 愿李??ъ씤?몃뒗 `test_golden_render_moviepy` flaky ?щ컻 ?щ???

---

## 2026-03-24 ??Claude ??T-026 ?꾨즺, security scan CLEAR

### ?묒뾽 ?붿빟

security scan 6嫄댁쓣 triage??寃곌낵 ?꾧굔 false positive ?뺤씤. 3媛??뚯씪(`cost_db.py`, `content_db.py`, `server.py`)??諛⑹뼱??寃利?蹂닿컯 諛?`# noqa` 留덊궧 異붽?. `qaqc_runner.py`??security scan??`# noqa` 二쇱꽍 ?몄떇 湲곕뒫??異붽??섏뿬 寃利앸맂 SQL f-string???섎룄?곸쑝濡??듭젣?????덈룄濡?媛쒖꽑. 寃곌낵: security scan **CLEAR**.

### 蹂寃??뚯씪

| ?뚯씪 | 蹂寃??좏삎 | ?댁슜 |
|------|-----------|------|
| `blind-to-x/pipeline/cost_db.py` | ?섏젙 | `_ARCHIVE_TABLES` frozenset + assert 諛⑹뼱, 3媛?f-string??noqa 留덊궧 |
| `execution/content_db.py` | ?섏젙 | `update_job` f-string??noqa 留덊궧 (UPDATABLE_COLUMNS ?붿씠?몃━?ㅽ듃 ?ㅻ챸) |
| `infrastructure/sqlite-multi-mcp/server.py` | ?섏젙 | `_validate_table_name` 寃利??꾨즺 2嫄댁뿉 noqa 留덊궧 |
| `execution/qaqc_runner.py` | ?섏젙 | security scan?먯꽌 留ㅼ튂 ?쇱씤??`# noqa` 二쇱꽍???몄떇?섏뿬 ?듭젣?섎뒗 濡쒖쭅 異붽? |

### 寃利?寃곌낵

- security scan: **CLEAR** (6嫄???0嫄?
- `test_qaqc_runner_extended.py`: **5 passed**
- `test_cost_controls.py`: **4 passed**

---

## 2026-03-24 ??Codex ??T-023/T-024 ?꾨즺, system QC 蹂듦뎄

### ?묒뾽 ?붿빟

`execution/qaqc_runner.py`瑜?project-aware runner濡?蹂닿컯?덈떎. root??`tests/`? `execution/tests/`瑜?遺꾨━ ?ㅽ뻾?섍퀬, blind-to-x??Windows ?쒓? 寃쎈줈 ?섍꼍?먯꽌 ?ы쁽?섎뒗 `test_curl_cffi.py`瑜?system QC?먯꽌留?ignore ?섎ŉ, 紐⑤뱺 ?꾨줈?앺듃??`-o addopts=`瑜?媛뺤젣??coverage/capture ?ㅽ깘???쒓굅?덈떎. ?댁뼱??full QC瑜??ъ떎?됲빐 `REJECTED`瑜?`CONDITIONALLY_APPROVED`濡?蹂듦뎄?덈떎.

### 蹂寃??뚯씪

| ?뚯씪 | 蹂寃??좏삎 | ?댁슜 |
|------|-----------|------|
| `execution/qaqc_runner.py` | ?섏젙 | `test_runs` 吏?? root 遺꾨━ ?ㅽ뻾, blind known-env ignore, `-X utf8` + `-o addopts=` 怨좎젙, batch 寃곌낵 吏묎퀎 |
| `tests/test_qaqc_runner_extended.py` | ?섏젙 | split-run 吏묎퀎, `addopts` override, extra args/timeout ?꾨떖 ?뚭? ?뚯뒪??異붽? |
| `knowledge-dashboard/public/qaqc_result.json` | 媛깆떊 | latest runner 寃곌낵 ???(`CONDITIONALLY_APPROVED`) |
| `.ai/HANDOFF.md`, `.ai/TASKS.md`, `.ai/CONTEXT.md`, `.ai/SESSION_LOG.md` | ?섏젙 | T-023/T-024 ?꾨즺, QC 湲곗????꾩냽 TODO 媛깆떊 |

### 寃利?寃곌낵

- `venv\\Scripts\\python.exe -X utf8 -m pytest tests\\test_qaqc_runner.py tests\\test_qaqc_runner_extended.py -q --tb=short --no-header -o addopts=` ??**25 passed** ??- `python -m compileall execution\\qaqc_runner.py` ??而댄뙆???깃났 ??- `venv\\Scripts\\python.exe -X utf8 execution\\qaqc_runner.py` ??**`CONDITIONALLY_APPROVED`** ??  - blind-to-x: **531 passed, 16 skipped**
  - shorts-maker-v2: **776 passed, 8 skipped** / **849.77s**
  - root: **910 passed, 1 skipped**
  - total: **2217 passed, 25 skipped, 0 failed**

### 寃곗젙?ы빆

- shorts-maker-v2 timeout??二쇱썝?몄? golden ?섎굹媛 ?꾨땲??`tests/integration/test_shorts_factory_e2e.py` 怨꾩뿴 ?μ떆媛??뚮뜑 ?뚯뒪?몄씠硫? full suite??no-cov 湲곗? ??13遺?48珥덇? ?꾩슂?섎떎. system runner timeout? 300s媛 ?꾨땲??1200s湲됱씠 ?곸젅?섎떎.
- root QC???⑥씪 pytest ?몄텧蹂대떎 `tests/`? `execution/tests/` 遺꾨━ ?ㅽ뻾???덉젙?곸씠?? ?숈떆???섏쭛?섎㈃ ?숈씪 basename ?뚯뒪?몄뿉??import mismatch媛 ?쒕떎.
- system QC?먯꽌???꾨줈?앺듃蹂?coverage/capture `addopts`瑜??곕Ⅴ吏 留먭퀬 ?꾩슂???몄옄留?紐낆떆?곸쑝濡??ｋ뒗 ?몄씠 ?덉젙?곸씠??

### ?ㅼ쓬 ?꾧뎄?먭쾶 硫붾え

- ?꾩옱 ?⑥? ?꾩냽 ?댁뒋??security scan 6嫄?triage?? 紐⑤몢 SQL 愿??f-string ?⑦꽩?대ŉ ?ㅼ젣 痍⑥빟?먯씤吏 false positive?몄? 遺꾨쪟媛 ?꾩슂?섎떎.
- `test_golden_render_moviepy` flaky???대쾲 full QC?먯꽌???ы쁽?섏? ?딆븯?? ?ㅼ떆 ?섑????뚮쭔 蹂꾨룄 ?쒖뒪?щ줈 ?밴꺽?대룄 ?쒕떎.

---

## 2026-03-24 ??Claude Code ??QC ?꾩껜 ?ъ륫??
### ?묒뾽 ?붿빟

blind-to-x + shorts-maker-v2 QC ?꾩껜 ?ъ륫?? Ruff 0嫄??뺤씤, golden_render flaky 1嫄?諛쒓껄.

### QC 寃곌낵

| ??ぉ | 寃곌낵 | ?댁쟾 |
|------|------|------|
| blind-to-x Ruff | ??0嫄?| 0嫄?|
| blind-to-x pytest | 522 passed, 16 skipped | 522 passed |
| blind-to-x coverage | 53.35% | 53.33% |
| shorts-maker-v2 pytest | 775 passed, 1 failed (flaky), 8 skipped | 776 passed |
| shorts-maker-v2 coverage | 62.58% | 62.45% |

### ?뱀씠?ы빆

- `test_golden_render_moviepy`: ?꾩껜 ?ㅼ쐞?몄뿉??1 failed, ?⑤룆 ?ㅽ뻾 ??2 passed ???먯썝 寃쏀빀 flaky
- shorts ?꾩껜 ?뚯슂 15遺?45珥?(qaqc_runner 300s 珥덇낵 吏??

---

## 2026-03-24 ??Codex ???ъ슜???섏젙 諛섏쁺 QC ?ш?利?
### ?묒뾽 ?붿빟

?ъ슜?먭? blocker瑜??섏젙?덈떎怨??뚮젮 以 ???쒖뒪??QC瑜??ㅼ떆 ?ㅽ뻾?덈떎. ?쒖? ?뷀듃由ы룷?명듃 `python -X utf8 execution/qaqc_runner.py` 湲곗? ?먯젙? ?ъ쟾??**REJECTED**?吏留? ?댁뼱???꾨줈?앺듃蹂?focused ?ш?利앹쓣 ?섑뻾??寃곌낵 blind-to-x? root???ㅼ젣 肄붾뱶 ?뚭????댁냼??寃껋쓣 ?뺤씤?덈떎. ?⑥? 臾몄젣??shorts-maker-v2 full suite timeout, `execution/qaqc_runner.py`???쒖뒪???먯젙 蹂댁젙, 洹몃━怨?Windows ?쒓? ?ъ슜??寃쎈줈?먯꽌 ?ы쁽?섎뒗 `curl_cffi` CA Error 77?대떎.

### 蹂寃??뚯씪

| ?뚯씪 | 蹂寃??좏삎 | ?댁슜 |
|------|-----------|------|
| `.ai/HANDOFF.md`, `.ai/TASKS.md`, `.ai/CONTEXT.md`, `.ai/SESSION_LOG.md` | ?섏젙 | 2026-03-24 QC ?ш?利?寃곌낵, ?좉퇋 TODO(T-024), runner/coverage 吏猶곕강 媛깆떊 |
| `knowledge-dashboard/public/qaqc_result.json` | 媛깆떊 | `execution/qaqc_runner.py` 理쒖떊 ?ш?利?寃곌낵 ???|

### 寃利?寃곌낵

- `python -X utf8 execution/qaqc_runner.py` ??**REJECTED** (`blind-to-x` 99/1/1, `shorts-maker-v2` TIMEOUT 300s, `root` errors 2) ??- `python -X utf8 -m pytest blind-to-x\\tests --ignore=blind-to-x\\tests\\integration\\test_curl_cffi.py -q --tb=short --no-header -x` ??**542 passed, 5 skipped** ??- `python -X utf8 -m pytest tests -q --tb=short --no-header` ??**884 passed, 1 skipped** ??- `python -X utf8 -m pytest execution\\tests -q --tb=short --no-header -o addopts=\"\"` ??**25 passed** ??- `python -X utf8 -m pytest tests/unit tests/integration --collect-only -q` (`shorts-maker-v2`) ??**784 tests collected**, ??coverage gate ?뚮Ц??collect-only???ㅽ뙣泥섎읆 醫낅즺 ?좑툘
- `python -X utf8 -m pytest tests/unit tests/integration -q --maxfail=1 --no-cov` (`shorts-maker-v2`) ??**15遺?珥덇낵 timeout** ??
### 寃곗젙?ы빆

- 2026-03-23 QC?먯꽌 ?≫삍??blind-to-x `test_cost_controls` ?뚭?? root `test_qaqc_history_db` ?뚭????꾩옱 focused ?ш?利?湲곗??쇰줈 ?댁냼?먮떎.
- ?꾩옱 ?쒖뒪??QC `REJECTED`??二쇰맂 ?먯씤? shorts-maker-v2 timeout怨?`execution/qaqc_runner.py`???먯젙/?섏쭛 援ъ“?대ŉ, blind `test_curl_cffi.py`??Windows ?쒓? ?ъ슜??寃쎈줈 ?섍꼍??known issue??媛源앸떎.
- shorts collection debug ??coverage ?ㅼ젙??寃곌낵瑜??쒓끝?????덉쑝誘濡?`--collect-only`留뚯쑝濡??먯젙?섏? 留먭퀬 `--no-cov`瑜??④퍡 怨좊젮?쒕떎.

### ?ㅼ쓬 ?꾧뎄?먭쾶 硫붾え

- ?곗꽑?쒖쐞??`T-023`(shorts timeout)? `T-024`(system QC verdict stabilization)?대떎.
- `knowledge-dashboard/public/qaqc_result.json`? ?ъ쟾??REJECTED瑜?媛由ы궎誘濡? ??쒕낫???댁꽍 ??focused ?ш?利?硫붾え瑜??④퍡 遊먯빞 ?쒕떎.

---

## 2026-03-23 ??Claude Code ??T-019/T-016/Phase5 ?꾨즺

### ?묒뾽 ?붿빟

Ruff 28嫄??뺣━, 諛곗튂 ?ㅻえ??3嫄??깃났, coverage ?ъ륫??

### 蹂寃??뚯씪

| ?뚯씪 | 蹂寃??댁슜 |
|------|----------|
| `pipeline/__init__.py` | F401 ??`X as X` 紐낆떆???ъ텧??10嫄?|
| `pipeline/_archive/newsletter_formatter.py` | E741 `l` ??`line` |
| `pipeline/viral_filter.py` | E731 lambda ??def |
| `pipeline/notion/_cache.py` | F841 `tracking` ??`_tracking` |
| `scrapers/browser_pool.py` | E402 `# noqa` |
| `scrapers/jobplanet.py` | F401 `# noqa`, F841 `views` ??`_views` |
| `scripts/backfill_notion_urls.py` | E402 `# noqa` |
| `scripts/check_notion_views.py` | E402 `# noqa` x2 |
| `tests/integration/test_notebooklm_smoke.py` | E402 `# noqa` |
| `tests/unit/test_cost_controls.py` | E402 `# noqa` |
| `tests/unit/test_image_ab_tester.py` | E402 `# noqa` |
| `tests/unit/test_phase3.py` | E741 `l` ??`lbl` x2 |
| `tests/unit/test_text_polisher.py` | E402 `# noqa` |
| `tests/test_x_analytics.py` | F841 `id_old/id_new` ??`_id_old/_id_new` |

### 寃곌낵

- Ruff: 28嫄???0嫄???- blind-to-x: 522 passed, coverage 53.33% (?댁쟾 51.72%)
- shorts-maker-v2: 776 passed, coverage 62.45% (?댁쟾 62.29%)
- T-016 諛곗튂 ?ㅻえ?? 3/3 Notion ?낅줈???깃났, Gemini 429 ??fallback ?뺤긽

---

## 2026-03-23 ??Claude Code ??T-021/T-022 ?섏젙 ?꾨즺

### ?묒뾽 ?붿빟

T-021, T-022 blocker ?섏젙 ?꾨즺.

### 蹂寃??뚯씪

| ?뚯씪 | 蹂寃??댁슜 |
|------|----------|
| `tests/test_qaqc_history_db.py` | ?섎뱶肄붾뵫 ??꾩뒪?ы봽 `"2026-03-22T12:00:00"` ??`datetime.now()`, ?좎쭨 鍮꾧탳??`datetime.now().strftime` ?ъ슜 |
| `execution/qaqc_runner.py` | `shorts-maker-v2` test_paths瑜?`tests/unit` + `tests/integration`?쇰줈 遺꾨━ (legacy ?쒖쇅) |

### 寃곌낵

- T-021: `tests/test_qaqc_history_db.py` 7/7 all passed
- T-022: shorts 784 tests collected (collection error ?놁쓬)

---

## 2026-03-23 ??Claude Code ??QC ?꾩껜 痢≪젙 + coverage 湲곗???媛깆떊

### ?묒뾽 ?붿빟

?묒そ ?쒕툕?꾨줈?앺듃 ?꾩껜 ?뚯뒪??+ coverage ?ъ륫??(?대쾲 ?몄뀡 異붽? ?뚯뒪??諛섏쁺).

### QC 寃곌낵

| ?꾨줈?앺듃 | ?댁쟾 | ?꾩옱 | 蹂??|
|----------|------|------|------|
| shorts-maker-v2 | 729 passed / 59% | **776 passed / 62.29%** | +47 tests, +3.3% |
| blind-to-x (unit) | 443 passed / 51.7% | **458 passed / 50.4%** | +15 tests, -1.3%* |

\* btx coverage ?뚰룺 ?섎씫: ruff format?쇰줈 ?명븳 ?뚯뒪 ?쇱씤 蹂??(pipeline ???뚯씪 誘명룷??

### 二쇱슂 紐⑤뱢 coverage

| 紐⑤뱢 | ?댁쟾 | ?꾩옱 |
|------|------|------|
| `thumbnail_step.py` | 0% (?뚯뒪???놁쓬) | ?좉퇋 31嫄?|
| `llm_router.py` | 2 failed | 17 passed (100%) |
| `notion_upload.py` | 89% | **99%** |
| `feed_collector.py` | ??| **100%** |
| `commands/dry_run.py` | ??| **100%** |
| `commands/one_off.py` | ??| **100%** |

---

## 2026-03-23 ??Codex ???쒖뒪??QC ?ъ떎??(REJECTED) + blocker triage

### ?묒뾽 ?붿빟

?ъ슜???붿껌?쇰줈 ?쒖뒪??QC瑜??ъ떎?됲뻽?? ?쒖? ?뷀듃由ы룷?명듃 `python -X utf8 execution/qaqc_runner.py` 湲곗? 寃곌낵??**REJECTED**?怨? blind-to-x 98 passed / 1 failed / 1 skipped, shorts-maker-v2 errors 1, root errors 2濡?吏묎퀎?먮떎. ?댄썑 ?꾨줈?앺듃蹂?沅뚯옣 寃쎈줈濡??ш?利앺븳 寃곌낵, ?ㅼ젣 blocker??blind-to-x `tests/unit/test_cost_controls.py` 3嫄? root `tests/test_qaqc_history_db.py` 2嫄댁씠硫? shorts-maker-v2??QAQC runner媛 `tests/legacy/test_ssml.py`源뚯? ?섏쭛?섎뒗 寃쎈줈 臾몄젣? 蹂꾧컻濡?`tests/unit tests/integration --no-cov --maxfail=1`??15遺????꾨즺?섏? ?딆븘 timeout ?먯씤 遺꾨━媛 ?꾩슂?섎떎怨??먮떒?덈떎.

### 蹂寃??뚯씪

| ?뚯씪 | 蹂寃??좏삎 | ?댁슜 |
|------|-----------|------|
| `.ai/HANDOFF.md`, `.ai/TASKS.md`, `.ai/CONTEXT.md`, `.ai/SESSION_LOG.md` | ?섏젙 | QC ?먯젙, blocker, runner 吏猶곕강, ?꾩냽 TODO 湲곕줉 |
| `knowledge-dashboard/public/qaqc_result.json` | 媛깆떊 | `execution/qaqc_runner.py` 理쒖떊 QC 寃곌낵 JSON ???|

### 寃利?寃곌낵

- `python -X utf8 execution/qaqc_runner.py` ??**REJECTED** (`blind-to-x` 98/1/1, `shorts-maker-v2` error 1, `root` errors 2) ??- `python -X utf8 -m pytest blind-to-x\\tests -q --tb=short --no-header -x` ??`test_curl_cffi.py::test_fetch`?먯꽌 known CA Error 77 ?ы쁽 ??- `python -X utf8 -m pytest blind-to-x\\tests --ignore=blind-to-x\\tests\\integration\\test_curl_cffi.py -q --tb=short --no-header` ??**3 failed, 539 passed, 5 skipped** (`tests/unit/test_cost_controls.py`) ??- `python -X utf8 -m pytest tests -q --tb=short --no-header` ??**2 failed, 882 passed, 1 skipped** (`tests/test_qaqc_history_db.py`) ??- `python -X utf8 -m pytest execution\\tests -q --tb=short --no-header` ??**25 passed**, coverage gate ?뚮Ц??command rc??fail?댁?留??뚯뒪???먯껜???듦낵 ?좑툘
- `python -X utf8 -m pytest shorts-maker-v2\\tests -q --tb=short -x` ??`tests/legacy/test_ssml.py` collection error (`edge_tts.Communicate._create_ssml` ?놁쓬) ??- `python -X utf8 -m pytest tests/unit tests/integration -q --maxfail=1 --no-cov` (`shorts-maker-v2`) ??**15遺?珥덇낵 timeout** ??
### 寃곗젙?ы빆

- ?꾩옱 ?쒖뒪??QC???ㅼ젣 肄붾뱶 blocker??blind-to-x 鍮꾩슜 異붿쟻/罹먯떆 ?뚭? 3嫄닿낵 root `qaqc_history_db` ?좎쭨 ?섎뱶肄붾뵫 2嫄댁씠??
- `execution/qaqc_runner.py`??shorts-maker-v2? root?????false fail??留뚮뱾 ???덈뒗 ?섏쭛 寃쎈줈 臾몄젣瑜?媛뽮퀬 ?덈떎.
- 蹂댁븞 ?ㅼ틪 46嫄댁? ?꾩옱 regex媛 `.agents/`, 踰덈뱾 JS, ?쇰컲 f-string 濡쒓렇源뚯? ?≪븘 false positive媛 留롮븘 利됱떆 blocker濡?蹂댁? ?딅뒗??

### ?ㅼ쓬 ?꾧뎄?먭쾶 硫붾え

- ?꾩냽 ?묒뾽 ?곗꽑?쒖쐞??`T-020`(blind-to-x cost controls) ??`T-022/T-023`(runner 寃쎈줈/shorts timeout) ??`T-021`(root timestamp test) ?쒖꽌媛 ?곸젅?섎떎.
- blind-to-x `test_curl_cffi.py`???꾩옱 ?섍꼍??known CA Error 77 ?ы쁽?⑹뿉 媛源뚯썙 ?쒖뒪??QC 湲곗??먯꽌??蹂꾨룄 skip/xfail ?꾨왂??寃?좏븷 留뚰븯??

---

## 2026-03-23 ??Codex ??blind-to-x Notion 寃?????덇굅??unsafe 1嫄??뺣━

### ?묒뾽 ?붿빟

T-017 ?꾩냽?쇰줈 blind-to-x Notion 寃???먮? live audit?덈떎. `notion_doctor.py`? `check_notion_views.py`瑜??ㅼ떆 ?뺤씤????data source ?꾩껜 421?섏씠吏瑜?議고쉶?덇퀬, ?꾩옱 ?꾪꽣 湲곗??쇰줈 遺?곸젅???덇굅????ぉ `移댄럹?먯꽌 ?욎뿉 ?됱??ъ옄 怨⑤컲 援ш꼍以? 1嫄댁씠 ?꾩쭅 `寃?좏븘?? ?곹깭??寃껋쓣 李얠븘 `諛섎젮`濡??꾪솚?섍퀬 媛먯궗 硫붾え瑜??④꼈?? 以묎컙??PowerShell heredoc ?쒓? ?몄퐫???뚮Ц??`?뱀씤 ?곹깭` select??`??` ?듭뀡???앷린??遺?묒슜???덉뿀?쇰굹, 湲곗〈 `諛섎젮` option ID濡??섏씠吏 媛믪쓣 蹂듦뎄?섍퀬 data source ?ㅽ궎留덉뿉??stray ?듭뀡???쒓굅?덈떎.

### 蹂寃??뚯씪

| ?뚯씪 | 蹂寃??좏삎 | ?댁슜 |
|------|-----------|------|
| `.ai/HANDOFF.md`, `.ai/TASKS.md`, `.ai/CONTEXT.md`, `.ai/SESSION_LOG.md` | ?섏젙 | T-017 寃곌낵, ?ㅼ쓬 ?묒뾽, PowerShell?봏otion select ?몄퐫??二쇱쓽?ы빆 湲곕줉 |
| Notion data source `?뱀씤 ?곹깭` | live update | ?덇굅??unsafe ?섏씠吏 1嫄?`寃?좏븘????諛섎젮`, stray `??` select option ?쒓굅 |

### 寃利?寃곌낵

- `python -X utf8 scripts/notion_doctor.py --config config.yaml` ??**PASS** (`data_source`, props resolved) ??- `python -X utf8 scripts/check_notion_views.py` ??**紐⑤뱺 ?꾩닔 ?띿꽦 議댁옱** ??- Notion live audit ??**TOTAL_PAGES=421**, **FLAGGED_TOTAL=1**, **FLAGGED_IN_REVIEW=0** ??- ????섏씠吏 review status raw ?뺤씤 ??`諛섎젮`, memo audit note 議댁옱 ??- `?뱀씤 ?곹깭` select ?듭뀡 raw ?뺤씤 ??`寃?좏븘??, `?뱀씤??, `諛섎젮`, `諛쒗뻾?꾨즺`, `諛쒗뻾?뱀씤`留??⑥쓬 ??
### 寃곗젙?ы빆

- ??뷀삎 PowerShell?먯꽌 live Notion ?섏젙 ???쒓? select option ?대쫫??洹몃?濡?PATCH?섏? 留먭퀬, **option ID** ?먮뒗 `\\u` escape 臾몄옄?댁쓣 ?ъ슜?쒕떎.
- blind-to-x Notion 寃???먯뿉???꾩옱 ?꾪꽣 湲곗???unsafe ?ㅼ썙????ぉ??`寃?좏븘?? ?곹깭濡??⑥븘 ?덉? ?딅떎.

### ?ㅼ쓬 ?꾧뎄?먭쾶 硫붾え

- `--review-only` ?꾩껜 諛곗튂 ?ㅻえ?щ뒗 ?ъ쟾??LLM/?대?吏 鍮꾩슜???곕씪?ㅻ?濡??ъ슜???뱀씤 ?놁씠 ?ㅽ뻾?섏? ?딅뒗??
- live audit ?ъ떎?됱씠 ?꾩슂?섎㈃ no-filter query ??濡쒖뺄 ?먯젙?쇰줈 ?먭??섎뒗 寃쎈줈媛 ?덉쟾?섎떎.

---

## 2026-03-23 ??Claude Code ??coverage uplift: thumbnail_step ?좉퇋 + llm_router 踰꾧렇 ?섏젙 + notion_upload 99%

### ?묒뾽 ?붿빟

T-014 coverage uplift 2李? shorts-maker-v2 `thumbnail_step.py` ?꾩슜 ?뚯뒪??31嫄??좉퇋 ?묒꽦, `llm_router.py` 湲곗〈 ?ㅽ뙣 ?뚯뒪??2嫄?lazy import patch 寃쎈줈 ?ㅻ쪟) ?섏젙, btx `notion_upload.py` 89%??9% (10嫄?異붽?).

### 蹂寃??뚯씪

| ?뚯씪 | 蹂寃??좏삎 | ?댁슜 |
|------|-----------|------|
| `shorts-maker-v2/tests/unit/test_thumbnail_step.py` | **?좉퇋** | thumbnail_step ?꾩껜 而ㅻ쾭: 紐⑤뱶遺꾧린(none/pillow/dalle/gemini/canva/unknown), ?덉쇅, _resolve_ai_prompt, scene_assets 諛곌꼍 異붿텧 (31嫄? |
| `shorts-maker-v2/tests/unit/test_llm_router.py` | ?섏젙 | `_get_client` / `_generate_once` patch 寃쎈줈 `shorts_maker_v2.providers.llm_router.genai` ??`google.genai.Client` / `google.genai.types` 濡??섏젙 (2 failed ??0 failed) |
| `blind-to-x/tests/unit/test_notion_upload.py` | ?섏젙 | limit 珥덇낵, exception, no-client, httpx-fallback ?ㅽ뙣, non-retryable raise, schema exhausted, filter/sorts, data_source endpoint, schema_mismatch, already-ready 12嫄?異붽? |

### ?뚯뒪??寃곌낵

- `shorts-maker-v2` `test_render_step + test_llm_router + test_thumbnail_step` ??**65 passed** ??- `blind-to-x` `test_notion_upload` ??**29 passed** ??(notion_upload.py 99% coverage)
- `feed_collector.py` 100%, `commands/dry_run.py` 100%, `commands/one_off.py` 100%

---

## 2026-03-23 ??Codex ??blind-to-x ?쇱씠釉??꾪꽣 寃利?+ curl_cffi 吏곸젒 ?대갚 蹂듦뎄

### ?묒뾽 ?붿빟

blind-to-x???ㅼ슫??寃利앹쓣 ?댁뼱諛쏆븘, Windows ?쒓? ?ъ슜??寃쎈줈?먯꽌 `curl_cffi`媛 `error setting certificate verify locations`(libcurl error 77)濡??ㅽ뙣?섎뒗 臾몄젣瑜??ы쁽?섍퀬 Blind ?ㅽ겕?섑띁??釉뚮씪?곗? 吏곸젒 ?먯깋 ?대갚??異붽??덈떎. ?④퍡 遺?곸젅 ?쒕ぉ/?먯삤 媛먯젙 ?뚭? ?뚯뒪?몃? 異붽??덇퀬, ?ㅼ젣 Blind URL `移댄럹?먯꽌 ?욎뿉 ?됱??ъ옄 怨⑤컲 援ш꼍以????ㅼ뒪?щ옒?묓븯??`FILTERED_SPAM / inappropriate_content / (skipped-filtered)`濡??낅줈???꾩뿉 李⑤떒?섎뒗 寃껋쓣 ?뺤씤?덈떎.

### 蹂寃??뚯씪

| ?뚯씪 | 蹂寃??좏삎 | ?댁슜 |
|------|-----------|------|
| `blind-to-x/scrapers/blind.py` | ?섏젙 | feed/post ?섏쭛 ??`curl_cffi` ?ㅽ뙣 ??Playwright 吏곸젒 ?먯깋 ?대갚, direct fallback `wait_until='domcontentloaded'`濡??꾪솕 |
| `blind-to-x/tests/unit/test_scrape_failure_classification.py` | ?섏젙 | 遺?곸젅 ?쒕ぉ ?꾪꽣, ?먯삤 媛먯젙 ?꾪꽣, feed session fetch failure fallback ?뚭? ?뚯뒪??3嫄?異붽? |
| `.ai/HANDOFF.md`, `.ai/TASKS.md`, `.ai/CONTEXT.md` | ?섏젙 | ?쇱씠釉?寃利?寃곌낵? ?꾩냽 ?묒뾽 湲곕줉 |

### 寃利?寃곌낵

- `python -m ruff check scrapers/blind.py tests/unit/test_scrape_failure_classification.py` ??- `python -m pytest --no-cov tests/unit/test_scrape_failure_classification.py -q` ??**8 passed** ??- `python -X utf8 scripts/notion_doctor.py --config config.yaml` ??**PASS** (`data_source`, props resolved) ??- `python -X utf8 scripts/check_notion_views.py` ??**紐⑤뱺 ?꾩닔 ?띿꽦 議댁옱** ??- ?ㅼ젣 Notion 理쒓렐 ?섏씠吏 議고쉶: 2026-03-23 ?앹꽦 `移댄럹?먯꽌 ?욎뿉 ?됱??ъ옄 怨⑤컲 援ш꼍以? ?덇굅????ぉ ?붿〈 ?뺤씤
- ?ㅼ젣 Blind URL ?쇱씠釉??ㅽ겕?섑븨 + `process_single_post()` 媛???ㅽ뻾: `FILTERED_SPAM`, `failure_reason='inappropriate_content'`, `notion_url='(skipped-filtered)'` ?뺤씤 ??
### 寃곗젙?ы빆

- ???섍꼍?먯꽌??`curl_cffi`瑜??좊ː 寃쎈줈濡??⑤룆 ?섏〈?섏? ?딄퀬, Blind ?ㅽ겕?섑띁媛 吏곸젒 釉뚮씪?곗? ?먯깋?쇰줈 ?먮룞 ?대갚?댁빞 ??- TeamBlind 吏곸젒 ?먯깋? `networkidle`蹂대떎 `domcontentloaded`媛 ???덉젙?곸엫
- ?꾩껜 `main.py --review-only` 諛곗튂 ?ㅻえ?щ뒗 LLM/?대?吏 鍮꾩슜???곕씪?????덉쑝誘濡??ъ슜???뱀씤 ?놁씠 ?ㅽ뻾?섏? ?딆쓬

### ?ㅼ쓬 ?꾧뎄?먭쾶 硫붾え

- `collect_feed_items()`??cross-source dedup 寃쎈줈?먯꽌 ?꾨쿋??API瑜??몄텧?????덉쑝?? ?⑥닚 ?쇰뱶 ?뺤씤? `BlindScraper.get_feed_candidates()` 吏곸젒 ?몄텧?????덉쟾??- Notion 寃???먯뿉???덇굅??unsafe ?섏씠吏媛 ?⑥븘 ?덈떎. ???꾪꽣媛 留됱븘 二쇰뜑?쇰룄 湲곗〈 ?곗씠???뺣━??蹂꾨룄 ?먮떒???꾩슂
- Windows?먯꽌 subprocess 醫낅즺 ??`BaseSubprocessTransport.__del__` 寃쎄퀬媛 媛꾪뿉?곸쑝濡?李랁엳吏留??대쾲 寃利앹쓽 pass/fail怨쇰뒗 臾닿?

---

## 2026-03-23 ??Claude Code ??blind-to-x ?ㅼ슫???먭? 3醫??섏젙

### ?묒뾽 ?붿빟

blind-to-x ?뚯씠?꾨씪?몄뿉??"肄섑뀗痢??덉쭏 ???? "?대?吏 以묐났" 臾몄젣瑜?吏꾨떒?섍퀬 3醫??섏젙???꾨즺?덈떎.

### 蹂寃??뚯씪

| ?뚯씪 | 蹂寃??좏삎 | ?댁슜 |
|------|-----------|------|
| `blind-to-x/pipeline/image_cache.py` | **?섏젙** | `get()` ??濡쒖뺄 ?뚯씪 寃쎈줈 議댁옱 寃利?異붽?. stale ??ぉ ?먮룞 evict + ?ъ깮???몃━嫄?|
| `blind-to-x/pipeline/process.py` | **?섏젙** | `INAPPROPRIATE_TITLE_KEYWORDS` 12媛?異붽?, `_REJECT_EMOTION_AXES={'?먯삤'}` 異붽?. ?꾪꽣 2怨??쎌엯 |
| `blind-to-x/pipeline/image_generator.py` | **?섏젙** | "湲고?" ?좏뵿 湲곕낯 ?λ㈃ 7醫?? 臾댁옉???좏깮 (?대?吏 以묐났 諛⑹?) |
| `blind-to-x/classification_rules.yaml` | **?섏젙** | 媛??좏뵿 ?ㅼ썙??+5~8媛??뺤옣, `?뗣뀑`/`?롢뀕` ?쒓굅, 吏곸옣媛쒓렇 ?ㅽ깘 諛⑹? |

### ?듭떖 ?섏젙 ?댁슜

1. **ImageCache stale 踰꾧렇**: 48h TTL 罹먯떆媛 Windows ?꾩떆?뚯씪 寃쎈줈瑜??????OS媛 ?뚯씪 ??젣 ?꾩뿉??罹먯떆 HIT ??鍮?寃쎈줈 諛섑솚. `Path.exists()` 泥댄겕 ???놁쑝硫?evict + None 諛섑솚?쇰줈 ?섏젙
2. **遺?곸젅 肄섑뀗痢??꾪꽣**: "移댄럹?먯꽌 ?욎뿉 ?됱??ъ옄 怨⑤컲 援ш꼍以? 瑜?寃뚯떆臾쇱씠 ?ㅽ뙵 ?꾪꽣 ?듦낵. ?쒕ぉ ?ㅼ썙???꾪꽣 + ?먯삤 媛먯젙 ?먮룞 嫄곕? 異붽?
3. **?좏뵿 遺꾨쪟 媛쒖꽑**: `?뗣뀑` ?ㅼ썙?쒓? 吏곸옣媛쒓렇???ы븿?섏뼱 "?섏쑉?뗣뀑"媛 ?섎せ 遺꾨쪟?섎뒗 臾몄젣 ?섏젙. 湲덉쑖/寃쎌젣??`?섏쑉`, `肄붿뒪?? ??異붽?

### 寃利?寃곌낵

- Fix 1: 議댁옱?뚯씪 HIT, ??젣?뚯씪 MISS+evict, URL HIT 紐⑤몢 ?뺤긽
- Fix 2: "怨⑤컲 援ш꼍" ?ㅼ썙???꾪꽣 ?뺤긽, `?먯삤` 媛먯젙 嫄곕? ?뺤긽
- Fix 3: "?섏쑉?뗣뀑" ??"湲덉쑖/寃쎌젣" ?뺤긽, "湲고?" ?대?吏 10??以?6醫??ㅼ뼇???뺤씤

---

## 2026-03-23 ??Codex ??coverage 湲곗????ъ륫??+ targeted test 異붽?

### ?묒뾽 ?붿빟

Phase 5 P1-1 ?꾩냽?쇰줈 `shorts-maker-v2`? `blind-to-x`???꾩옱 coverage 湲곗??좎쓣 ?ㅼ떆 痢≪젙?덈떎. 洹?寃곌낵 shorts??**54.98%**, blind-to-x??**51.72%**?怨? 湲곗????댄썑 `shorts-maker-v2`??`content_calendar`, `planning_step`, `qc_step`, `channel_router`瑜?寃⑤깷???좉퇋 ?⑥쐞 ?뚯뒪??29嫄댁쓣 異붽??덈떎.

### 蹂寃??뚯씪

| ?뚯씪 | 蹂寃??좏삎 | ?댁슜 |
|------|-----------|------|
| `shorts-maker-v2/tests/unit/test_content_calendar_extended.py` | **?좉퇋** | Notion content calendar CRUD / suggestion / recent-topic 濡쒖쭅 ?뚯뒪??|
| `shorts-maker-v2/tests/unit/test_planning_step.py` | **?좉퇋** | Gate 1 怨꾪쉷 ?앹꽦 retry / fallback / parse 寃利?|
| `shorts-maker-v2/tests/unit/test_qc_step.py` | **?좉퇋** | Gate 3/4 QC? ffprobe / volumedetect ?좏떥 寃利?|
| `shorts-maker-v2/tests/unit/test_channel_router.py` | **?좉퇋** | profile load / apply / singleton router 寃利?|
| `.ai/HANDOFF.md`, `.ai/TASKS.md`, `.ai/CONTEXT.md` | ?섏젙 | coverage 湲곗??좉낵 ?좉퇋 ?뚯뒪??硫붾え 湲곕줉 |
| `directives/system_audit_action_plan.md` | ?섏젙 | P1-1 ?ㅼ젣 痢≪젙 ?섏튂? ?꾩옱 媛?湲곕줉 |

### 痢≪젙 諛??뚯뒪??寃곌낵

- `python -m pytest tests/unit tests/integration -q` (`shorts-maker-v2`) ??**704 passed, 12 skipped, coverage 54.98%**
- `python -m pytest -q` (`blind-to-x`) ??**487 passed, 5 skipped, coverage 51.72%**
- `python -m ruff check tests/unit/test_content_calendar_extended.py tests/unit/test_planning_step.py tests/unit/test_qc_step.py tests/unit/test_channel_router.py` ??- `python -m pytest --no-cov tests/unit/test_content_calendar_extended.py tests/unit/test_planning_step.py tests/unit/test_qc_step.py tests/unit/test_channel_router.py -q` ??**29 passed** ??- `shorts-maker-v2` ?꾩껜 coverage ?ъ륫???좉퇋 ?뚯뒪??諛섏쁺)? ?ъ슜???붿껌?쇰줈 以묎컙??以묐떒??
### ?ㅼ쓬 ?꾧뎄?먭쾶 硫붾え

- coverage 紐⑺몴(80/75)? ?꾩옱 湲곗????ъ씠 媛꾧꺽??而ㅼ꽌, ??遺꾧린? 寃곗젙濡좎쟻 ?좏떥???곗꽑 硫붿슦???꾨왂???꾩슂??- `shorts-maker-v2`??湲곕낯 `pytest`媛 `tests/legacy/`??以띻린 ?뚮Ц??coverage 痢≪젙 ??`tests/unit tests/integration` 寃쎈줈瑜?紐낆떆?섎뒗 ?몄씠 ?덉쟾??- ?ㅼ쓬 ?ъ륫?????꾨낫: shorts `render_step`, `thumbnail_step`, `llm_router`, blind-to-x `feed_collector`, `commands`, `notion/_query`

---

## 2026-03-23 ??Codex ??render adapter ?곌껐 + LLM fallback/濡쒓퉭 ?덉젙??
### ?묒뾽 ?붿빟

shorts-maker-v2??`render_step`??RenderAdapter` ?곌껐??留덈Т由ы븯怨? 媛먯궗 ?뚮옖 ?꾩냽?쇰줈 9-provider `LLMRouter` ?대갚 ?뚯뒪?몃? 異붽??덈떎. ?④퍡 `execution/_logging.py`媛 `loguru` 誘몄꽕移??섍꼍?먯꽌??import ??二쎌? ?딅룄濡?stdlib fallback???ｊ퀬, 媛먯궗 臾몄꽌/HANDOFF/TASKS/CONTEXT瑜??꾩옱 ?곹깭??留욊쾶 媛깆떊?덈떎.

### 蹂寃??뚯씪

| ?뚯씪 | 蹂寃??좏삎 | ?댁슜 |
|------|-----------|------|
| `shorts-maker-v2/src/shorts_maker_v2/pipeline/render_step.py` | ?섏젙 | `RenderStep.try_render_with_adapter()` 異붽?, native compose/output backend 遺꾨━ |
| `shorts-maker-v2/src/shorts_maker_v2/pipeline/orchestrator.py` | ?섏젙 | ShortsFactory render 遺꾧린 ?꾩엫 ?⑥닚??|
| `shorts-maker-v2/src/shorts_maker_v2/render/video_renderer.py` | ?섏젙 | FFmpeg backend媛 MoviePy native clip???덉쟾?섍쾶 encode?섎룄濡?蹂닿컯 |
| `shorts-maker-v2/tests/unit/test_render_step.py` | ?섏젙 | adapter ?깃났/?ㅽ뙣 諛?ffmpeg backend native clip 濡쒕뵫 ?뚭? ?뚯뒪??異붽? |
| `shorts-maker-v2/tests/unit/test_video_renderer.py` | ?섏젙 | FFmpeg renderer媛 native clip ?낅젰??諛쏅뒗 寃쎈줈 寃利?|
| `shorts-maker-v2/tests/unit/test_engines_v2_extended.py` | ?섏젙 | orchestrator媛 `RenderStep.try_render_with_adapter()`???꾩엫?섎뒗吏 寃利?|
| `shorts-maker-v2/src/shorts_maker_v2/providers/llm_router.py` | ?섏젙 | Windows cp949 肄섏넄 ?덉쟾 異쒕젰 `_safe_console_print()` 異붽? |
| `shorts-maker-v2/tests/unit/test_llm_router.py` | **?좉퇋** | 9-provider fallback ?쒖꽌 / retry / non-retryable / JSON parse ?뚯뒪??4媛?|
| `execution/_logging.py` | ?섏젙 | `loguru` optional import + stdlib fallback 濡쒓퉭 援ъ꽦 |
| `requirements.txt` | ?섏젙 | `loguru` 紐낆떆 異붽? |
| `directives/system_audit_action_plan.md` | ?섏젙 | Phase 1 ?ㅼ젣 援ы쁽/寃利??곹깭 諛섏쁺 |
| `.ai/HANDOFF.md`, `.ai/TASKS.md`, `.ai/CONTEXT.md` | ?섏젙 | ?꾩옱 吏꾪뻾 ?곹깭? ?ㅼ쓬 ?묒뾽 媛깆떊 |

### ?뚯뒪??寃곌낵

- `python -m ruff check src/shorts_maker_v2/pipeline/render_step.py src/shorts_maker_v2/pipeline/orchestrator.py src/shorts_maker_v2/render/video_renderer.py tests/unit/test_render_step.py tests/unit/test_video_renderer.py tests/unit/test_engines_v2_extended.py` ??- `python -m pytest --no-cov tests/unit/test_render_step.py tests/unit/test_video_renderer.py tests/unit/test_engines_v2_extended.py tests/integration/test_renderer_mode_manifest.py -q` ??**65 passed** ??- `python -m pytest --no-cov tests/integration/test_shorts_factory_e2e.py::TestRenderAdapterPipeline::test_render_with_plan_invalid_channel_returns_failure tests/integration/test_shorts_factory_e2e.py::TestOrchestratorSFBranch::test_renderer_mode_defaults_to_native tests/integration/test_shorts_factory_e2e.py::TestOrchestratorSFBranch::test_sf_branch_fallback_on_import_error -q` ??**3 passed** ??- `python -m pytest --no-cov execution/tests -q` ??**25 passed** ??- `python -m ruff check tests/unit/test_llm_router.py src/shorts_maker_v2/providers/llm_router.py` ??- `python -m pytest --no-cov tests/unit/test_llm_router.py -q` ??**4 passed** ??- `python -m pytest --no-cov tests/test_llm_fallback_chain.py -q` ??**15 passed** ??
### 寃곗젙?ы빆

- `render_step`??clip 議곕┰??怨꾩냽 MoviePy native 寃쎈줈濡??섑뻾?섍퀬, ffmpeg backend??理쒖쥌 encode ?④퀎?먯꽌留??ъ슜
- `execution/_logging.py`??`loguru`媛 ?놁뼱???뚯뒪???좉퇋 ?섍꼍?먯꽌 import 媛?ν빐????- Windows cp949 肄섏넄?먯꽌 ?대え吏 ?곹깭 異쒕젰? 吏곸젒 `print()`?섏? 留먭퀬 safe printer ?먮뒗 logger 寃쎌쑀

### ?ㅼ쓬 ?꾧뎄?먭쾶 硫붾え

- `system_audit_action_plan.md` 湲곗? Phase 1? 臾몄꽌???遺遺??꾨즺 泥섎━?? ?⑥? ?ㅼ쭏 ?꾩냽? P1-1 coverage 紐⑺몴 ?ъ꽦???뚯뒪??蹂닿컯
- `shorts-maker-v2/tests/unit/test_llm_router.py`??`_generate_once`瑜?mock ?댁꽌 ?쇱슦???뺤콉留?寃利앺븿. ?ㅼ젣 SDK ?듯빀 ?뚯뒪?멸? ?꾩슂?섎㈃ 蹂꾨룄 ?쇱씠釉??ㅻえ?щ줈 遺꾨━ 沅뚯옣
- Python 3.14 ?섍꼍?먯꽌 `openai` / `google-genai` 寃쎄퀬???ъ쟾??異쒕젰?섏?留??꾩옱 ?뚯뒪???ㅽ뙣 ?먯씤? ?꾨떂

---

## 2026-03-23 ??Antigravity (Gemini) ??援ъ“??由ы뙥?좊쭅 (main.py 遺꾨━ + 猷⑦듃 ?뺣━ + CONTEXT.md 寃쎈웾??

### ?묒뾽 ?붿빟

blind-to-x `main.py` 紐⑤끂由ъ뒪 遺꾨━, shorts-maker-v2 猷⑦듃 ?뚯씪 ?뺣━, CONTEXT.md 寃쎈웾??3媛吏 ?꾨즺.

### 蹂寃??뚯씪

| ?뚯씪 | 蹂寃??좏삎 | ?댁슜 |
|------|-----------|------|
| `blind-to-x/pipeline/commands/__init__.py` | **?좉퇋** | commands ?⑦궎吏 珥덇린??|
| `blind-to-x/pipeline/commands/dry_run.py` | **?좉퇋** | dry-run 濡쒖쭅 異붿텧 (湲곗〈 main.py L90~179) |
| `blind-to-x/pipeline/commands/reprocess.py` | **?좉퇋** | ?뱀씤 寃뚯떆臾??ъ쿂由?濡쒖쭅 異붿텧 (湲곗〈 L182~230) |
| `blind-to-x/pipeline/commands/one_off.py` | **?좉퇋** | digest/sentiment 由ы룷??濡쒖쭅 異붿텧 (湲곗〈 L302~331) |
| `blind-to-x/pipeline/feed_collector.py` | **?좉퇋** | ?쇰뱶 ?섏쭛쨌?꾪꽣쨌以묐났?쒓굅쨌?뚯뒪蹂??쒗븳 濡쒖쭅 異붿텧 |
| `blind-to-x/main.py` | ?꾩쟾 ?ъ옉??| 714以꾟넂273以??ㅼ??ㅽ듃?덉씠?곕줈 ?щ┝??|
| `shorts-maker-v2/tests/legacy/` | **?좉퇋 ?붾젆?좊━** | ?덇굅???뚯뒪??5媛??대룞 |
| `shorts-maker-v2/assets/topics/` | **?좉퇋 ?붾젆?좊━** | topics_*.txt 5媛??대룞 |
| `shorts-maker-v2/logs/` | **?좉퇋 ?붾젆?좊━** | 濡쒓렇 ?뚯씪 6媛??대룞 |
| `shorts-maker-v2/TEMP_MPY_*.mp4` | **??젣** (3媛? | ?꾩떆 ?곸긽 ?뚯씪 ??젣 |
| `.ai/CONTEXT.md` | 寃쎈웾??| 330以꾟넂??180以? ?꾨즺 ?대젰?믫뀒?대툝 ?붿빟+SESSION_LOG ?꾩엫, Codex 釉붾줉 ?쒓굅 |

### 寃곗젙?ы빆

- blind-to-x commands 紐⑤뱢?? `pipeline/commands/` ?⑦궎吏濡?愿??濡쒖쭅 遺꾨━
- CONTEXT.md ?꾨즺 ?뱀뀡: ?몃? ?대젰? SESSION_LOG.md ?꾩엫, 寃쎈웾 ?뚯씠釉??뺥깭濡??좎?

### ?ㅼ쓬 ?꾧뎄?먭쾶 硫붾え

- `blind-to-x/main.py` import 寃쎈줈媛 `from pipeline.commands import run_dry_run, ...` 諛⑹떇?쇰줈 蹂寃쎈맖
- `pipeline/feed_collector.py`??`collect_feeds()` ?⑥닔媛 main.py ?쇰뱶 ?섏쭛 ??븷 ?대떦
- CONTEXT.md 吏猶곕강 ?뱀뀡? 蹂댁〈??(??젣 湲덉?)
- shorts-maker-v2 topic ?뚯씪 李몄“ 肄붾뱶媛 ?덈떎硫?寃쎈줈 `assets/topics/topics_*.txt`濡??섏젙 ?꾩슂

---

## 2026-03-23 ??Antigravity (Gemini) ??Phase 1 ?꾩쟾 ?곸슜 (Task Scheduler + 諛⑺솕踰?+ LLM ?대갚 ?뚯뒪??


### ?묒뾽 ?붿빟

Phase 1 ?ㅽ겕由쏀듃 6媛?援ы쁽 ?꾨즺 ??愿由ъ옄 沅뚰븳?쇰줈 ?ㅼ젣 ?곸슜. Task Scheduler 2媛??깅줉, Windows 諛⑺솕踰?洹쒖튃 異붽?, LLM ?대갚 E2E ?뚯뒪??23媛??묒꽦쨌?듦낵.

### 蹂寃??뚯씪

| ?뚯씪 | 蹂寃??좏삎 | ?댁슜 |
|------|-----------|------|
| `shorts-maker-v2/tests/unit/test_llm_fallback_chain.py` | **?좉퇋** | 9媛??대옒??23媛?LLM ?대갚 E2E ?뚯뒪??|
| `shorts-maker-v2/pytest.ini` | ?섏젙 | `--cov-report=xml` 異붽?, `fail_under=60` ?곹뼢 |
| `shorts-maker-v2/.pre-commit-config.yaml` | ?섏젙 | BOM 泥댄겕 + CRLF?묹F 媛뺤젣 hook 異붽? |
| `register_watchdog_checker.ps1` | **?좉퇋** ???ㅽ뻾?꾨즺 | ?뚯튂??heartbeat 10遺?二쇨린 Task Scheduler ?깅줉 |
| `register_backup_restore_test.ps1` | **?좉퇋** ???ㅽ뻾?꾨즺 | 諛깆뾽 蹂듭썝 ?뚯뒪??31??二쇨린 Task Scheduler ?깅줉 |
| `scripts/setup_n8n_security.ps1` | **?좉퇋** ???ㅽ뻾?꾨즺 | n8n 諛⑺솕踰??몃컮?대뱶 李⑤떒 洹쒖튃 異붽? (?ы듃 5678) |
| `C:\ProgramData\VibeCoding\backup_restore_test.bat` | **?좉퇋** | schtasks ?쒓? 寃쎈줈 ?고쉶???섑띁 bat |

### ?ㅼ젣 ?곸슜 寃곌낵 (愿由ъ옄 沅뚰븳 ?ㅽ뻾)

| ??ぉ | Task Scheduler ?곹깭 |
|------|---------------------|
| `VibeCoding_WatchdogHeartbeatChecker` | ??Ready (10遺?二쇨린) |
| `VibeCoding_BackupRestoreTest` | ??Ready (31??二쇨린) |
| 諛⑺솕踰? `Block n8n External Access (Port 5678)` | ??Enabled |

### ?뚯뒪??寃곌낵

- `test_llm_fallback_chain.py`: **23 passed**, 2 warnings ??Ruff clean

### 寃곗젙?ы빆

- Windows ?쒓? ?ъ슜?먮챸(`諛뺤＜??) 寃쎈줈??`schtasks /TR` ?몄닔濡?吏곸젒 ?꾨떖 遺덇? ??`C:\ProgramData\VibeCoding\` ?섑띁 bat 寃쎌쑀 諛⑹떇 梨꾪깮
- n8n 諛⑺솕踰? `!LocalSubnet` 誘몄?????`Action Block` (?꾩껜 ?몃컮?대뱶, LocalSubnet??李⑤떒)?쇰줈 ?⑥닚??(n8n ?먯껜媛 127.0.0.1 諛붿씤?⑹씠誘濡??몃????댁감??李⑤떒??
- ?뚯튂??Trigger: Repetition 蹂듭옟 臾몃쾿 ???`-Daily -DaysInterval 31` ?⑥닚 諛⑹떇 ?ъ슜

### TODO (?ㅼ쓬 ?몄뀡)

- [ ] `directives/system_audit_action_plan.md` Phase 1 ?꾨즺 留덊궧
- [ ] `git commit -m "[p1] Phase 1 ????ぉ ?꾨즺"`

### ?ㅼ쓬 ?꾧뎄?먭쾶 硫붾え

- `C:\ProgramData\VibeCoding\backup_restore_test.bat` ???쒖뒪???섑띁, ??젣 湲덉?
- PowerShell ?ㅽ겕由쏀듃 ?ъ떎????`.ps1` ???대え吏/?쒓? 二쇱꽍 ?덉쑝硫??뚯떛 ?ㅻ쪟 諛쒖깮 (ASCII-only ?좎? ?꾩슂)
- Phase 1 ??6媛???ぉ 援ы쁽쨌?곸슜 ?꾨즺. ?ㅼ쓬? `directives/system_audit_action_plan.md` ?뺤씤 ??Phase 2 ?댄썑 ??ぉ 吏꾪뻾

---

## 2026-03-23 ??Antigravity (Gemini) ??blind-to-x coverage 蹂닿컯 + ?쇱씠釉??꾪꽣 寃利?+ QA/QC ?뱀씤

### ?묒뾽 ?붿빟

blind-to-x 4媛?紐⑤뱢???뚯뒪??耳?댁뒪瑜?異붽??섏뿬 而ㅻ쾭由ъ?瑜?蹂닿컯?섍퀬, ?쇱씠釉??꾪꽣 寃利??ㅻえ???뚯뒪?몃? ?ㅽ뻾?덈떎. ?댄썑 ?꾩껜 pytest ?ъ떎??533 passed, 5 skipped) 諛?Ruff --fix ?곸슜 ??QA/QC 理쒖쥌 ?뱀씤 ?꾨즺.

### 蹂寃??뚯씪

| ?뚯씪 | 蹂寃??좏삎 | ?댁슜 |
|------|-----------|------|
| \	ests/unit/test_dry_run_command.py\ | ?섏젙 | scrape_post None 諛섑솚 耳?댁뒪 ?뚯뒪??異붽? |
| \	ests/unit/test_one_off_command.py\ | ?섏젙 | top_emotions / trending_keywords 鍮?媛?耳?댁뒪 異붽? |
| \	ests/unit/test_feed_collector.py\ | ?섏젙 | cross-source dedup 鍮꾪솢?깊솕 + ?뚯뒪 limit ?놁쓬 耳?댁뒪 異붽? |
| \	ests/unit/test_notion_upload.py\ | ?섏젙 | upload() / update_page_properties() 吏곸젒 ?⑥쐞 ?뚯뒪??異붽? |
| \.ai/HANDOFF.md\, \.ai/TASKS.md\ | ?섏젙 | T-018 DONE, T-019 ?좉퇋 ?깅줉, ?몄뀡 湲곕줉 |

### ?뚯뒪??寃곌낵

- \python -m pytest --cov=pipeline\ ??**533 passed, 5 skipped, 0 failed** ??- \python -m ruff check --fix .\ ???먮룞 ?섏젙 ?곸슜, ?덇굅???댁뒋 28嫄??붿〈 (T-019濡?異붿쟻) ??- **理쒖쥌 QC ?먯젙: ???뱀씤** (qc_report.md 李몄“)

### 寃곗젙?ы빆

- Ruff ?덇굅???댁뒋 28嫄?E402/F401/E741 ??? ?듭떖 ?뚯씠?꾨씪??濡쒖쭅 臾닿? ??T-019濡?蹂꾨룄 異붿쟻
- \--review-only\ 諛곗튂 ?ㅻえ??T-016)??LLM/?대?吏 鍮꾩슜 諛쒖깮?쇰줈 ?ъ슜???뱀씤 ?꾩슂

### [2026-03-25 19:59:41] Gemini (Phase 5A-2 Coverage Validation)
- 	ests/unit/test_render_step.py 및 	ests/unit/test_edge_tts_timing.py 117개 테스트 실행 확인 (100% Passed)
- pytest.ini의 전체 coverage 45% fail-under 이슈로 collection 에러 발생 내역 파악하여, 개별 단위 테스트 통과 독립 검증으로 갈음함.
- walkthrough.md 작성 및 작업 상태 업데이트.

## 2026-03-25 | Codex | T-040 완료, shorts i18n PoC 2차 확장

### 작업 요약

`shorts-maker-v2` Phase 5B-1 i18n PoC를 한 단계 더 확장했다. `script_step.py`에서 locale bundle이 tone/persona/CTA 금지어/system+user prompt copy뿐 아니라 `persona_keywords`와 review prompt copy까지 override하도록 넓혔고, `locales/ko-KR/script_step.yaml`도 그 구조에 맞춰 갱신했다. 또한 `edge_tts_client.py`에 `locales/<lang>/edge_tts.yaml` 로더를 추가해 alias voice(`alloy`, `sage` 등)와 default voice를 언어별로 분리할 수 있게 했고, `media_step.py`가 `project.language`를 Edge TTS 호출에 전달하도록 연결했다.

### 변경 파일

| 파일 | 변경 유형 | 내용 |
|------|-----------|------|
| `shorts-maker-v2/src/shorts_maker_v2/pipeline/script_step.py` | 수정 | locale override 대상에 `persona_keywords`, review prompt copy 추가 |
| `shorts-maker-v2/locales/ko-KR/script_step.yaml` | 수정 | `persona_keywords`, `review_copy` 섹션 추가 |
| `shorts-maker-v2/src/shorts_maker_v2/providers/edge_tts_client.py` | 수정 | `edge_tts.yaml` locale loader, 언어별 voice/default voice resolve 추가 |
| `shorts-maker-v2/src/shorts_maker_v2/pipeline/media_step.py` | 수정 | Edge TTS 호출 시 `language=self.config.project.language` 전달 |
| `shorts-maker-v2/locales/ko-KR/edge_tts.yaml` | 신규 | ko-KR alias voice/default voice 매핑 외부화 |
| `shorts-maker-v2/tests/unit/test_script_step_i18n.py` | 수정 | locale persona keywords/review copy 적용 테스트 추가 |
| `shorts-maker-v2/tests/unit/test_edge_tts_i18n.py` | 신규 | locale voice mapping/default fallback 테스트 추가 |

### 검증 결과

- `python -m ruff check shorts-maker-v2/src/shorts_maker_v2/pipeline/script_step.py shorts-maker-v2/src/shorts_maker_v2/providers/edge_tts_client.py shorts-maker-v2/src/shorts_maker_v2/pipeline/media_step.py shorts-maker-v2/tests/unit/test_script_step_i18n.py shorts-maker-v2/tests/unit/test_edge_tts_i18n.py` -> clean
- `python -m pytest --no-cov tests/unit/test_script_step.py tests/unit/test_script_quality.py tests/unit/test_script_step_i18n.py tests/unit/test_edge_tts_timing.py tests/unit/test_edge_tts_phase5.py tests/unit/test_edge_tts_i18n.py tests/unit/test_edge_tts_retry.py -q` (`shorts-maker-v2`) -> **86 passed, 2 warnings**

### 다음 도구에게 메모

- i18n PoC는 아직 `ko-KR` 실데이터만 있음. 다음 확장 후보는 실제 `en-US` locale pack, `captions.font_candidates`, `whisper_aligner.py`의 언어 고정 처리
- `EdgeTTSClient.generate_tts()`는 새 호출부가 생기면 `language`를 직접 받아야 locale voice mapping이 적용됨

## 2026-03-25 | Codex | T-041 완료, shorts `en-US` locale pack + whisper/caption i18n 연결

### 작업 요약

`shorts-maker-v2`의 i18n PoC를 실제 비한국어 locale까지 확장했다. `locales/en-US/`에 `script_step.yaml`, `edge_tts.yaml`, `captions.yaml`을 추가해 프롬프트/페르소나/CTA 금지어, Edge TTS alias voice/default voice, caption font 기본값을 분리했다. 또한 `config.py`는 `captions.font_candidates`가 비어 있으면 locale 기본 폰트를 읽도록 바꾸고, `whisper_aligner.py`는 `en-US` 같은 locale을 `en`처럼 short code로 정규화해 faster-whisper에 전달하도록 보강했다. `edge_tts_client.py`는 whisper fallback 호출에도 `language`를 넘기게 맞췄다.

### 변경 파일

| 파일 | 변경 유형 | 내용 |
|------|-----------|------|
| `shorts-maker-v2/src/shorts_maker_v2/config.py` | 수정 | locale 기반 caption font default 로더 추가 |
| `shorts-maker-v2/src/shorts_maker_v2/providers/whisper_aligner.py` | 수정 | locale → short code 정규화 후 faster-whisper `language` 전달 |
| `shorts-maker-v2/src/shorts_maker_v2/providers/edge_tts_client.py` | 수정 | whisper fallback에도 `language` 전달 |
| `shorts-maker-v2/locales/en-US/script_step.yaml` | 신규 | en-US 프롬프트/페르소나/review copy/CTA 금지어 추가 |
| `shorts-maker-v2/locales/en-US/edge_tts.yaml` | 신규 | en-US voice alias/default voice 매핑 추가 |
| `shorts-maker-v2/locales/en-US/captions.yaml` | 신규 | en-US caption font 기본값 추가 |
| `shorts-maker-v2/locales/ko-KR/captions.yaml` | 신규 | ko-KR caption font 기본값 외부화 |
| `shorts-maker-v2/tests/unit/test_config.py` | 수정 | locale 기본 caption font / explicit override 테스트 추가 |
| `shorts-maker-v2/tests/unit/test_script_step_i18n.py` | 수정 | en-US locale bundle 로드 테스트 추가 |
| `shorts-maker-v2/tests/unit/test_edge_tts_i18n.py` | 수정 | en-US locale bundle / whisper language 전달 테스트 추가 |
| `shorts-maker-v2/tests/unit/test_whisper_aligner.py` | 수정 | locale 언어값 정규화 테스트 추가 |

### 검증 결과

- `python -m ruff check shorts-maker-v2/src/shorts_maker_v2/config.py shorts-maker-v2/src/shorts_maker_v2/providers/whisper_aligner.py shorts-maker-v2/src/shorts_maker_v2/providers/edge_tts_client.py shorts-maker-v2/tests/unit/test_config.py shorts-maker-v2/tests/unit/test_script_step_i18n.py shorts-maker-v2/tests/unit/test_edge_tts_i18n.py shorts-maker-v2/tests/unit/test_edge_tts_phase5.py shorts-maker-v2/tests/unit/test_edge_tts_retry.py shorts-maker-v2/tests/unit/test_whisper_aligner.py` -> clean
- `python -m pytest --no-cov tests/unit/test_config.py tests/unit/test_script_step_i18n.py tests/unit/test_edge_tts_i18n.py tests/unit/test_edge_tts_phase5.py tests/unit/test_edge_tts_retry.py tests/unit/test_edge_tts_timing.py tests/unit/test_whisper_aligner.py -q` (`shorts-maker-v2`) -> **78 passed, 2 warnings**

### 다음 도구에게 메모

- `en-US` locale pack은 들어갔지만 아직 end-to-end pipeline smoke는 없다. 실제 config 샘플 또는 짧은 orchestrator/media/render smoke가 다음 안전한 단계
- 남은 i18n 후보는 `script_step.py`의 `_CHANNEL_REVIEW_CRITERIA` extra copy와 legacy 필드명(`narration_ko`) 정리

## 2026-03-25 | Codex | T-044 완료, shorts `en-US` config smoke 추가

### 작업 요약

실제 `en-US` locale pack이 config 로드부터 캡션 렌더까지 최소 경로로 이어지는지 확인하는 smoke 테스트를 추가했다. 신규 `test_i18n_en_us_smoke.py`는 `load_config()`로 `project.language=en-US` 설정을 읽고, `ScriptStep`가 영어 locale prompt를 쓰는지, `MediaStep`가 `EdgeTTSClient.generate_tts()`에 `language="en-US"`를 전달하는지, `caption_pillow.render_caption_image()`가 locale 기본 font 후보를 들고도 fallback으로 이미지를 만들어내는지 한 번에 검증한다.

### 변경 파일

| 파일 | 변경 유형 | 내용 |
|------|-----------|------|
| `shorts-maker-v2/tests/unit/test_i18n_en_us_smoke.py` | 신규 | 실제 `en-US` config 기준 `ScriptStep -> MediaStep -> caption render` smoke 테스트 추가 |
| `.ai/HANDOFF.md`, `.ai/TASKS.md`, `.ai/CONTEXT.md`, `.ai/SESSION_LOG.md` | 수정 | T-044 완료 및 다음 우선순위 반영 |

### 검증 결과

- `python -m ruff check shorts-maker-v2/tests/unit/test_i18n_en_us_smoke.py` -> clean
- `python -m pytest --no-cov tests/unit/test_i18n_en_us_smoke.py tests/unit/test_config.py tests/unit/test_script_step_i18n.py tests/unit/test_edge_tts_i18n.py tests/unit/test_whisper_aligner.py -q` (`shorts-maker-v2`) -> **34 passed, 2 warnings**

### 다음 도구에게 메모

- 이제 `en-US`는 config/load/prompt/TTS language/caption fallback까지 smoke가 있다. 다음 남은 i18n 후보는 `script_step.py`의 `_CHANNEL_REVIEW_CRITERIA` extra copy와 legacy 필드명 정리
- 아직 `orchestrator.py` 또는 실제 render assemble 전체를 `en-US`로 한 번 돌린 상위 스모크는 없음
