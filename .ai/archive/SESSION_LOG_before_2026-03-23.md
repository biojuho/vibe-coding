## 2026-03-22 (?몄뀡3) ??Claude Code (Opus 4.6) ??媛먯궗 ?붿뿬 P2 ?꾨즺 + 而ㅻ쾭由ъ? 80% ?ъ꽦


### ?묒뾽 ?붿빟

P2-1/4/5/6 ?붿뿬 ??ぉ ?꾨즺 (loguru 18/18, 留ㅽ븨 寃利? S4U ?뺤씤, 諛깆뾽 ?뺤씤), script_step.py WIP ?뺣━, ?뚯뒪??52媛?異붽?濡?而ㅻ쾭由ъ? 78%??1% (80% 寃뚯씠???ъ꽦).

### 蹂寃??뚯씪

| ?뚯씪 | 蹂寃??좏삎 | ?댁슜 |
|------|-----------|------|
| execution/{bgm,health,selector,yt_upload,yt_analytics,yt_notion}.py | ?섏젙 | loguru ?꾪솚 (6媛? |
| scripts/watchdog_heartbeat_check.bat | **?좉퇋** | 10遺?二쇨린 heartbeat 泥댁빱 |
| scripts/check_mapping.py | **?좉퇋** | directive?봢xecution 留ㅽ븨 寃利앷린 |
| directives/INDEX.md | ?섏젙 | ?좉퇋 directive 6嫄?異붽? |
| shorts-maker-v2/.../script_step.py | ?섏젙 | CTA 湲덉???+ ?섎Ⅴ?뚮굹 ?ㅼ퐫??+ Hook ?몃┝ |
| shorts-maker-v2/tests/unit/test_script_quality.py | **?좉퇋** | ?ㅽ겕由쏀듃 ?덉쭏 ?뚯뒪??29媛?|
| tests/test_roi_calculator.py | **?좉퇋** | ROI 怨꾩궛湲??뚯뒪??19媛?|
| tests/test_lyria_bgm_generator.py | **?좉퇋** | Lyria BGM ?좏떥 ?뚯뒪??9媛?|
| tests/test_qaqc_history_db.py | **?좉퇋** | QaQc DB ?뚯뒪??7媛?|
| tests/test_env_loader.py | **?좉퇋** | env_loader ?뚯뒪??4媛?|
| tests/test_error_analyzer.py | **?좉퇋** | ?먮윭 遺꾨쪟 ?뚯뒪??13媛?|

### ?뚯뒪??寃곌낵
- Root: **877 passed**, 0 failed, coverage **80.57%** (寃뚯씠???ъ꽦)
- shorts-maker-v2: 572+ passed (xfail 0嫄?

### 寃곗젙?ы빆
- Task Scheduler S4U ?묒뾽 0嫄??뺤씤 ??CRITICAL?믫빐?뱀뾾???섑뼢
- SQLite VACUUM INTO ?대? ?щ컮瑜닿쾶 援ы쁽???뺤씤
- Watchdog heartbeat: Task Scheduler 10遺?二쇨린 ?깅줉 ?꾨즺

### ?ㅼ쓬 ?꾧뎄?먭쾶
- 而ㅻ쾭由ъ? 80% ?ъ꽦?? 異붽? ?뚯뒪?몃뒗 ?꾩슂 ?쒖뿉留?- video_renderer.py ??render_step.py ?꾪솚? ?洹쒕え 由ы뙥?좊쭅, 蹂꾨룄 ?몄뀡 沅뚯옣
- MCP 以묐났? AI ?꾧뎄 李?愿由щ줈 ?닿껐 (肄붾뱶 蹂寃?遺덊븘??

---

## 2026-03-22 (?몄뀡2) ??Claude Code (Opus 4.6) ??P2-3 + Phase 3 ?꾨즺 + xfail ?섏젙 + loguru ?곸슜

### ?묒뾽 ?붿빟

P2-3 鍮꾩슜 ?듯빀 ??쒕낫???꾨즺, Phase 3 ????ぉ(P3-1~P3-5) ?꾨즺, shorts-maker-v2 xfail 3嫄?洹쇰낯 ?섏젙, loguru 5媛??ㅽ겕由쏀듃 ?곸슜.

### 蹂寃??뚯씪

| ?뚯씪 | 蹂寃??좏삎 | ?댁슜 |
|------|-----------|------|
| `execution/api_usage_tracker.py` | ?섏젙 | PRICING ?뺤옣 + 5媛??좉퇋 荑쇰━ ?⑥닔 + MONTHLY_BUDGET_USD |
| `execution/pages/cost_dashboard.py` | **?좉퇋** | ?듯빀 鍮꾩슜 ??쒕낫??(8媛??뱀뀡, 3 ?곗씠?곗냼?? |
| `.ai/DECISIONS.md` | ?섏젙 | ADR-013 Local-First SaaS ?섏씠釉뚮━??異붽? |
| `directives/local_first_saas_design.md` | **?좉퇋** | Adapter ?명꽣?섏씠??+ 諛고룷 ?좏뤃濡쒖? + 蹂댁븞 寃쎄퀎 |
| `directives/mcp_resource_profile.md` | **?좉퇋** | MCP ?쒕쾭 4x 以묐났 諛쒓껄 (~4.9GB, 90媛??꾨줈?몄뒪) |
| `shorts-maker-v2/.../render/video_renderer.py` | **?좉퇋** | MoviePy 異붿긽??(ABC + MoviePyRenderer + FFmpegRenderer) |
| `.env.meta` | **?좉퇋** | API ??濡쒗뀒?댁뀡 硫뷀??곗씠??(12媛??? |
| `scripts/key_rotation_checker.py` | **?좉퇋** | 90??濡쒗뀒?댁뀡 泥댁빱 + Telegram ?뚮┝ |
| `directives/security_rotation.md` | **?좉퇋** | 遺꾧린蹂???濡쒗뀒?댁뀡 SOP |
| `directives/project_operations_grade.md` | **?좉퇋** | Active/Maintenance/Frozen ?깃툒??|
| `.ai/CONTEXT.md` | ?섏젙 | ?꾨줈?앺듃 ?뚯씠釉붿뿉 ?깃툒 而щ읆 異붽? |
| `shorts-maker-v2/.../pipeline/qc_step.py` | ?섏젙 | `stub_mode` ?뚮씪誘명꽣 異붽? (Gate 4) |
| `shorts-maker-v2/.../pipeline/orchestrator.py` | ?섏젙 | stub 媛먯? ??`stub_mode=True` ?꾨떖 |
| `shorts-maker-v2/tests/integration/test_orchestrator_manifest.py` | ?섏젙 | xfail ?쒓굅 |
| `shorts-maker-v2/tests/integration/test_renderer_mode_manifest.py` | ?섏젙 | xfail 2嫄??쒓굅 |
| `execution/llm_client.py` | ?섏젙 | loguru ?꾪솚 |
| `execution/pipeline_watchdog.py` | ?섏젙 | loguru ?꾪솚 |
| `execution/backup_to_onedrive.py` | ?섏젙 | loguru ?꾪솚 |
| `execution/community_trend_scraper.py` | ?섏젙 | loguru ?꾪솚 |
| `execution/topic_auto_generator.py` | ?섏젙 | loguru ?ㅼ젙 ?쒖꽦??(stdlib ?좎?, caplog ?명솚) |
| `directives/system_audit_action_plan.md` | ?섏젙 | P2-3, P3-1~P3-5 ?꾨즺 留덊궧 |

### 寃곗젙?ы빆
- **ADR-013**: Local-First SaaS ?섏씠釉뚮━????ADR-002 ?먭린 ?딄퀬 踰붿쐞 ?ы빐??- **MCP 以묐났**: 13媛??쒕쾭 x 4 ?몄뒪?댁뒪 = 90媛??꾨줈?몄뒪. 利됱떆 AI ?꾧뎄 ?숈떆 ?ㅽ뻾 ?쒗븳 ?꾩슂
- **?꾨줈?앺듃 ?깃툒**: Active 3媛?/ Maintenance 1媛?/ Frozen 2媛?
### ?뚯뒪??寃곌낵
- Root: 825 passed, 0 failed (coverage 77.95%)
- shorts-maker-v2 xfail 3嫄? 紐⑤몢 ?듦낵

### ?ㅼ쓬 ?꾧뎄?먭쾶
- loguru ?꾪솚 ?섎㉧吏 ~13媛??ㅽ겕由쏀듃??`caplog` ?섏〈 ?뚯뒪???좊Т ?뺤씤 ?꾩슂 (topic_auto_generator ?⑦꽩 李몄“)
- MCP ?쒕쾭 以묐났? AI ?꾧뎄 李??リ린濡?利됱떆 ?닿껐 媛?? 洹쇰낯 ?닿껐? MCP ?꾨줉??寃??- video_renderer.py??render_step.py ?먯쭊 ?꾪솚 + golden render test ?꾩냽 ?꾩슂

---

## 2026-03-22 ??Claude Code (Opus 4.6) ???쒖뒪??媛먯궗 利됱떆議곗튂 + Phase 1~2 ?ㅽ뻾

### ?묒뾽 ?붿빟
3媛??낅┰ LLM 媛먯궗 蹂닿퀬??援먯감 遺꾩꽍 ??利됱떆 議곗튂 4嫄?+ Phase 1 (6嫄? + Phase 2 (5/6嫄? ?ㅽ뻾.
珥?10媛?而ㅻ컠, ?뚰궧 ?붾젆?곕━ ?대┛.

### 蹂寃??뚯씪

| ?뚯씪 | 蹂寃??좏삎 | ?댁슜 |
|------|-----------|------|
| `.ai/CONTEXT.md` | ?꾩쟾 ?ъ옉??| 1~163以?mojibake UTF-8 蹂듦뎄 |
| `.ai/DECISIONS.md` | ?섏젙 | ADR-010~012 諛섏쁺 |
| `.env` / `.env.llm` / `.env.social` / `.env.project` | 遺꾨━ | ??븷蹂???遺꾨━ 援ъ“ |
| `execution/_env_loader.py` | **?좉퇋** | 以묒븰 ?섍꼍蹂??濡쒕뜑 |
| `execution/_logging.py` | **?좉퇋** | loguru 以묒븰 ?ㅼ젙 (JSONL 7??濡쒗뀒?댁뀡) |
| `execution/pipeline_watchdog.py` | ?섏젙 | heartbeat 湲곕뒫 + --check-alive 紐⑤뱶 |
| `execution/backup_to_onedrive.py` | ?섏젙 | SQLite VACUUM INTO ?ㅻ깄??諛깆뾽 |
| `execution/backup_restore_test.py` | **?좉퇋** | OneDrive 諛깆뾽 蹂듭썝 ?뚯뒪??|
| `execution/telegram_notifier.py` | ?섏젙 | queue_digest/flush_digest ?곗뼱留?|
| `tests/test_llm_fallback_chain.py` | **?좉퇋** | LLM ?대갚 泥댁씤 ?뚯뒪??8媛?|
| `shorts-maker-v2/utils/pipeline_status.py` | ?섏젙 | CP949 ?대え吏 _safe_print |
| `shorts-maker-v2/pytest.ini` | ?섏젙 | --cov 而ㅻ쾭由ъ? 痢≪젙 異붽? |
| `blind-to-x/pytest.ini` | ?섏젙 | --cov 而ㅻ쾭由ъ? 痢≪젙 異붽? |
| `.githooks/pre-commit` | **?좉퇋** | ruff + UTF-8 寃??(staged only) |
| `infrastructure/n8n/docker-compose.yml` | ?섏젙 | 127.0.0.1 諛붿씤??怨좎젙 |
| `directives/INDEX.md` | **?좉퇋** | SOP?봢xecution 留ㅽ븨 ?몃뜳??|
| `directives/system_audit_action_plan.md` | **?좉퇋** | 醫낇빀 ?≪뀡 ?뚮옖 (3媛?蹂닿퀬???듯빀) |
| blind-to-x/* (20?뚯씪) | ?섏젙 | 硫섏뀡 ?덉쭏 + NotebookLM + ?깃낵 異붿쟻 |
| shorts-maker-v2/* (8?뚯씪) | ?섏젙 | ?뚯씠?꾨씪???덉젙??+ planning/qc step |
| execution/* + tests/* (26?뚯씪) | ?섏젙 | QC 踰꾧렇 ?섏젙 + ?좉퇋 ?ㅽ겕由쏀듃 3 + ?뚯뒪??32 |

### ?뚯뒪??寃곌낵

| ?곸뿭 | Passed | Failed | Coverage |
|------|--------|--------|----------|
| Root | 842+ | 0 | 84.72% |
| shorts-maker-v2 | 569 | 0 (3 xfail) | 46.36% |
| blind-to-x | 486 | 0 | 51.52% |

### 寃곗젙?ы빆
- .env ??븷蹂?遺꾨━: `.env.llm`/`.env.social`/`.env.project` + ?덇굅??`.env` ?좎?
- loguru ?먯쭊 ?꾩엯: ?듭떖 3媛??ㅽ겕由쏀듃留??곗꽑 ?곸슜, stdlib intercept濡??명솚
- shorts-maker-v2 QC gate/stub 遺덉씪移?3嫄? xfail 寃⑸━ (stub-aware QC bypass ?꾩슂)
- Task Scheduler: 紐⑤뱺 ?묒뾽 InteractiveToken ?뺤씤 (S4U ?꾨떂)

### TODO (?ㅼ쓬 ?몄뀡)
- [ ] P2-3: 鍮꾩슜 ?듯빀 ??쒕낫??(Streamlit `pages/cost_dashboard.py`)
- [ ] Phase 3 ??ぉ ?쒖감 吏꾪뻾 (directives/system_audit_action_plan.md 李몄“)
- [ ] shorts-maker-v2 xfail 3嫄?洹쇰낯 ?섏젙 (QC step??stub bypass 濡쒖쭅)
- [ ] loguru瑜??섎㉧吏 15媛?execution ?ㅽ겕由쏀듃???먯쭊 ?곸슜

### ?ㅼ쓬 ?먯씠?꾪듃?먭쾶 硫붾え
- `directives/system_audit_action_plan.md`???꾩껜 濡쒕뱶留듭씠 ?덉쓬. Phase 1 ?꾨즺, Phase 2??P2-3留??⑥쓬.
- `.githooks/pre-commit`???쒖꽦?붾맖 ??staged .py ?뚯씪留?ruff check.
- `execution/_logging.py` import ??以?異붽?濡?湲곗〈 ?ㅽ겕由쏀듃??loguru ?곸슜 媛??
- blind-to-x ?뚯뒪??486 ?꾪넻怨????댁쟾 ?몄뀡??pre-existing 3嫄??ㅽ뙣???대? ?닿껐??

---

## 2026-03-22 ??Antigravity (Gemini) ???몄뀡 醫낅즺 (blind-to-x: Perf Collector + Smoke Test + QC)

### ?묒뾽 ?붿빟
Performance Collector ?ㅼ젣 API ?곕룞, NotebookLM Smoke Test 16媛??묒꽦, reply_text ?먮룞??
洹몃━怨?理쒖쥌 QA/QC ?뱀씤源뚯? ?꾨즺???몄뀡.

### 蹂寃??뚯씪
| ?뚯씪 | 蹂寃??좏삎 |
|------|-----------|
| `blind-to-x/pipeline/performance_collector.py` | ?꾩쟾 ?ъ옉??(Twitter/Threads/Naver API) |
| `blind-to-x/pipeline/notion/_schema.py` | reply_text 蹂듭썝 + unused import ?쒓굅 |
| `blind-to-x/pipeline/notion/_upload.py` | reply_text payload 異붽? |
| `blind-to-x/.env.example` | X_BEARER_TOKEN, THREADS_ACCESS_TOKEN 異붽? |
| `blind-to-x/tests/integration/test_notebooklm_smoke.py` | **?좉퇋** 16媛?smoke test |
| Notion DB (API) | `?듦? ?띿뒪?? rich_text ?띿꽦 ?먮룞 ?앹꽦 |

### QC 寃곌낵
| ??ぉ | 寃곌낵 |
|------|------|
| AST 援щЦ 寃??| ??PASS (3媛??뚯씪) |
| Ruff lint | ??PASS (F401 1嫄??섏젙 ??clean) |
| pytest ?꾩껜 | ??**497 passed, 5 skipped, 0 failed** |

### 寃곗젙?ы빆
- Naver Blog 怨듦컻 API ?놁쓬 ??graceful skip + ?섎룞 ?낅젰 ?덈궡 ?⑦꽩 梨꾪깮
- Threads API: shortcode ??numeric media_id 2?④퀎 議고쉶 援ъ“
- reply_text ?먮룞?붾줈 Notion DB ?섎룞 ?묒뾽 ?쒓굅

### TODO (?ㅼ쓬 ?몄뀡)
- [ ] `X_BEARER_TOKEN` 諛쒓툒 ??`.env` 異붽? (X Basic tier ?댁긽)
- [ ] `THREADS_ACCESS_TOKEN` 諛쒓툒 ??`.env` 異붽? (Meta Developers)
- [ ] `NOTEBOOKLM_MODE=gdrive` ?ㅼ쟾 ?뚯뒪??
### ?ㅼ쓬 AI?먭쾶
- **?뚯뒪???덉젙 ?곹깭**: pytest 497 passed / 0 failed ??踰좎씠?ㅻ씪???좎? ?꾩닔
- **performance_collector.py**: API ?좏겙 ?놁쑝硫??먮룞 skip (0 湲곕줉 ????, ?좏겙 異붽? ???ъ떎???꾩슂
- **reply_text**: Notion DB 諛?肄붾뱶 ?묒そ ?꾩쟾 ?쒖꽦???꾨즺. 異붽? ?묒뾽 遺덊븘??
- **Ruff**: `pipeline/notion/_schema.py`??`from typing import Any`??`performance_collector.py`?먮뒗 ?ъ슜 以묒씠誘濡??쇰룞 二쇱쓽

---

## 2026-03-22 ??Antigravity (Gemini) ??QC ?뱀씤 (blind-to-x ?몄뀡 理쒖쥌)

### ?묒뾽 ?붿빟
?대쾲 ?몄뀡 ?꾩껜 蹂寃쎌궗??뿉 ???QA/QC ?꾨즺.

### QA 寃곌낵

| ??ぉ | 寃곌낵 |
|------|------|
| AST 援щЦ 寃??(3媛??뚯씪) | ??PASS |
| Ruff lint | ??PASS (1嫄??섏젙: `_schema.py` unused import ?쒓굅) |
| ?꾩껜 ?뚯뒪??| ??497 passed, 5 skipped, 0 failed |

### STEP 3 ???섏젙 (QA)

| ?뚯씪 | ?섏젙 ?댁슜 |
|------|-----------|
| `pipeline/notion/_schema.py` | `from typing import Any` 誘몄궗??import ?쒓굅 (Ruff F401) |

### 理쒖쥌 ?먯젙

**??QC ?뱀씤** ??497 passed, 0 failed, Ruff clean

---

## 2026-03-22 ??Antigravity (Gemini) ??Performance Collector API ?곕룞 + Smoke Test + reply_text ?꾩쟾 ?먮룞??
### ?묒뾽 ?붿빟
blind-to-x 3媛吏 TODO瑜?紐⑤몢 ?꾨즺:
1. `performance_collector.py` ?ㅼ젣 API ?곕룞 (Twitter/Threads/Naver graceful fallback)
2. `NOTEBOOKLM_ENABLED=true` ?듯빀 smoke test ?묒꽦 諛??듦낵
3. `reply_text` ?띿꽦 肄붾뱶+Notion DB ?묒そ ?꾩쟾 ?쒖꽦??(MCP/urllib 吏곸젒 PATCH ?먮룞??

### 蹂寃??뚯씪

| ?뚯씪 | 蹂寃??좏삎 | ?댁슜 |
|------|-----------|------|
| `blind-to-x/pipeline/performance_collector.py` | ?꾩쟾 ?ъ옉??| `_estimate_metrics()` placeholder ??`_fetch_platform_metrics()` ?ㅼ젣 API. Twitter X API v2, Threads Meta Graph API `/insights`, Naver Blog graceful skip |
| `blind-to-x/pipeline/notion/_schema.py` | ?섏젙 | `reply_text` DEPRECATED_PROPS ??DEFAULT_PROPS 蹂듭썝, EXPECTED_TYPES/AUTO_DETECT_KEYWORDS 異붽? |
| `blind-to-x/pipeline/notion/_upload.py` | ?섏젙 | `reply_text` ?띿꽦 payload ?꾩넚 異붽? |
| `blind-to-x/.env.example` | ?섏젙 | `X_BEARER_TOKEN`, `THREADS_ACCESS_TOKEN` 異붽? |
| `blind-to-x/tests/integration/test_notebooklm_smoke.py` | **?좉퇋** | 16媛??듯빀 smoke test (disabled/topic/timeout/env variants) |
| Notion DB (API 吏곸젒) | ?띿꽦 異붽? | `?듦? ?띿뒪?? (rich_text) ?띿꽦 ?먮룞 ?앹꽦 ?꾨즺 (urllib PATCH) |

### ?뚯뒪??寃곌낵

| ??ぉ | 寃곌낵 |
|------|------|
| NotebookLM smoke test (?좉퇋) | ??16 passed, 1 skipped (content_writer.py ?놁뼱 ?뺤긽 skip) |
| blind-to-x ?⑥쐞 ?뚯뒪???꾩껜 | ??423 passed, 4 skipped, 0 failed |

### 寃곗젙?ы빆
- ?댁쟾 TODO "Notion DB reply_text ?띿꽦 ?섎룞 異붽?" ???꾩쟾 ?먮룞?붾맖 (urllib PATCH ?ㅽ겕由쏀듃)
- API ???놁뼱??graceful skip 援ъ“: None 諛섑솚 ???섎룞 ?낅젰 ?湲?(0 湲곕줉 ?놁쓬)
- Threads API: shortcode ??numeric media_id 2?④퀎 議고쉶 援ъ“

### TODO (?ㅼ쓬 ?몄뀡)
- [ ] `X_BEARER_TOKEN` 諛쒓툒 ??`.env`??異붽? (X Basic tier ?댁긽 ?꾩슂)
- [ ] `THREADS_ACCESS_TOKEN` 諛쒓툒 ??`.env`??異붽? (Meta Developers)
- [ ] `NOTEBOOKLM_MODE=gdrive` ?ㅼ쟾 ?뚯뒪??(Google Drive ?쒕퉬??怨꾩젙 ?ㅼ젙 ?꾩슂)
- [ ] execution/content_writer.py 寃쎈줈 ?뺤씤 (smoke test 1 skip ?댁냼)

### ?ㅼ쓬 ?꾧뎄?먭쾶 硫붾え
- `performance_collector.py`???댁젣 `_fetch_platform_metrics(platform, page_info)` ?⑥닔濡??ㅼ젣 API ?몄텧
- Notion DB `?듦? ?띿뒪?? (rich_text) ?띿꽦???먮룞?쇰줈 異붽??섏뼱 ?덉쓬 (?뺤씤 ?꾨즺, 珥?39媛??띿꽦)
- smoke test??Python 3.10+ asyncio.run() 諛⑹떇 ?ъ슜 (`asyncio.get_event_loop().run_until_complete()` ?꾨떂)

---



### ?묒뾽 ?붿빟
blind-to-x ?뚯씠?꾨씪???꾩껜 ?뚯뒪???ㅼ쐞?몄쓽 ?ㅽ뙣 3嫄댁쓣 ?섏젙?섏뿬 **481 passed, 0 failed, 4 skipped** ?ъ꽦.
?꾩슱???대쾲 ?몄뀡??諛곌꼍????Pivot Phase 2 TODO 4嫄??쒓렇??移대뱶, Notion 寃쎈웾?? 72h ?섏쭛 猷⑦봽, 寃利???紐⑤몢 ?꾨즺.

### 蹂寃??뚯씪

| ?뚯씪 | 蹂寃??좏삎 | ?댁슜 |
|------|-----------|------|
| `blind-to-x/pipeline/process.py` | ?섏젙 | `output_formats`媛 `None`????`["twitter"]` 湲곕낯媛??대갚 泥섎━ |
| `blind-to-x/main.py` | ?섏젙 | ??젣??`newsletter_scheduler` 紐⑤뱢 李몄“(newsletter 鍮뚮뱶 紐⑤뱶 ?꾩껜 釉붾줉) ?쒓굅 |
| `blind-to-x/tests/unit/test_cost_controls.py` | ?섏젙 | `EditorialReviewer` mock 異붽? (`pipeline.editorial_reviewer.EditorialReviewer`) ???ㅼ젣 LLM ?몄텧濡??명븳 hang 諛⑹? |
| `blind-to-x/tests/integration/test_p0_enhancements.py` | ?섏젙 | `test_classify_emotion_axis_new_emotions`??`pipeline.emotion_analyzer.get_emotion_profile` mock 異붽? ??ML 紐⑤뜽???ㅼ썙???대갚 寃쎈줈瑜?李⑤떒?섎뒗 臾몄젣 ?닿껐 |

### ?뚯뒪??寃곌낵

| ??ぉ | 寃곌낵 |
|------|------|
| blind-to-x ?꾩껜 | ??**481 passed, 0 failed, 4 skipped** |
| ?댁쟾 ?鍮?| ?댁쟾 419p + 2fail ???대쾲 481p + 0fail |

### 寃곗젙?ы빆
- `test_classify_emotion_axis_new_emotions`: ML 遺꾨쪟湲곕뒗 mock 泥섎━, YAML ?ㅼ썙???대갚留??⑥쐞 ?뚯뒪??(ML 寃곌낵???듯빀 ?뚯뒪??蹂꾨룄 ?대떦)
- `EditorialReviewer`???몃? LLM API ?섏〈 ???⑥쐞 ?뚯뒪?몄뿉?쒕뒗 諛섎뱶??mock 泥섎━ (hang ?꾪뿕)
- `newsletter_scheduler` 紐⑤뱢? ??젣????`main.py`???대떦 肄붾뱶 釉붾줉 ?ъ텛媛 湲덉?

### TODO (?ㅼ쓬 ?몄뀡)
- [ ] `performance_collector.py` ?ㅼ젣 API ?곕룞 (Twitter/Threads/Naver ?깃낵 ?섏쭛)
- [ ] `NOTEBOOKLM_ENABLED=true` + ?ㅼ젣 AI ?ㅻ줈 smoke test ?ㅽ뻾
- [ ] NotebookLM `NOTEBOOKLM_MODE=gdrive` ?ㅼ쟾 ?뚯뒪??(Google Drive ?쒕퉬??怨꾩젙 ?ㅼ젙 ?꾩슂)
- [ ] Notion DB??`reply_text` (?듦? ?띿뒪?? ?띿꽦 ?섎룞 ?앹꽦 (rich_text ???

### ?ㅼ쓬 ?먯씠?꾪듃?먭쾶 硫붾え
- blind-to-x ?뚯뒪?? `pytest tests -v` ?ㅽ뻾 ??**481 pass, 4 skip, 0 fail** ?뺤긽.
- `test_cost_controls.py`??`EditorialReviewer` mock??異붽???????mock???놁쑝硫?LLM API瑜??ㅼ젣 ?몄텧?섏뿬 ?뚯뒪?멸? hang??嫄몃┝.
- `test_p0_enhancements.py`?먯꽌 `get_emotion_profile`? `pipeline.emotion_analyzer.get_emotion_profile` 寃쎈줈濡?mock 泥섎━??(content_intelligence 紐⑤뱢 ??濡쒖뺄 import ?꾨떂??二쇱쓽).
- `newsletter_scheduler`????젣??紐⑤뱢. `main.py`, `test` ?뚯씪 ?깆뿉??李몄“ 湲덉?.
- Pivot Phase 2 ?꾩쟾 ?꾨즺: ?쒓렇??移대뱶 + Notion 寃쎈웾??15媛? + 72h ?섏쭛 猷⑦봽 紐⑤몢 援ы쁽쨌QC ?꾨즺.

---

## 2026-03-22 ??Claude Code (Opus 4.6) ???쒖뒪???꾩껜 QC


### ?묒뾽 ?붿빟
3媛??쒕툕?꾨줈?앺듃(root, shorts-maker-v2, blind-to-x)??????꾩껜 QC瑜??섑뻾.
CRITICAL 4嫄?+ HIGH 5嫄?踰꾧렇 ?섏젙, 32媛??뚯뒪??異붽?濡?而ㅻ쾭由ъ? 77% ??85% 蹂듦뎄.

### 蹂寃??뚯씪

| ?뚯씪 | 蹂寃??좏삎 | ?댁슜 |
|------|-----------|------|
| `execution/api_usage_tracker.py` | ?섏젙 | SQL `definition` ?뚮씪誘명꽣 ?붿씠?몃━?ㅽ듃 寃利?(injection 諛⑹뼱) |
| `execution/qaqc_runner.py` | ?섏젙 | returncode 湲곕컲 FAIL ?먯젙 + 鍮?異쒕젰 媛먯? |
| `execution/pipeline_watchdog.py` | ?섏젙 | `"C:\\"` ?섎뱶肄붾뵫 ???숈쟻 ?쒕씪?대툕 媛먯? |
| `execution/error_analyzer.py` | ?섏젙 | aware?뭤aive datetime ?뺢퇋??(??꾩〈 鍮꾧탳 ?쇨??? |
| `shorts-maker-v2/.../media_step.py` | ?섏젙 | ThreadPoolExecutor ?댁쨷 shutdown 諛⑹? (`_pool_shutdown` ?뚮옒洹? |
| `shorts-maker-v2/.../render_step.py` | ?섏젙 | AudioFileClip ?앹꽦 吏곹썑 `_audio_clips_to_close` ?깅줉 (?꾩닔 諛⑹?) |
| `blind-to-x/pipeline/image_upload.py` | ?섏젙 | tempfile try/except + os.unlink (怨좎븘 ?뚯씪 諛⑹?) |
| `tests/test_pipeline_watchdog.py` | **?좉퇋** | 32媛??뚯뒪??(disk/telegram/notion/scheduler/backup/btx/run_all/alerts/history) |

### ?뚯뒪??寃곌낵

| ?곸뿭 | Passed | Failed | Coverage |
|------|--------|--------|----------|
| Root | 842 | 0 | 84.72% |
| shorts-maker-v2 | 541 | 0 | ??|
| blind-to-x | 467 | 3 (pre-existing) | ??|
| **?⑷퀎** | **1,850** | **3** | ??|

### 寃곗젙?ы빆
- 而ㅻ쾭由ъ? 紐⑺몴 80%???뚯뒪??異붽?濡??ъ꽦 (湲곗? ?섑뼢 ?꾨땶 ?ㅼ쭏 媛쒖꽑)
- quality_gate.py???대? ?몄퐫???덉젙???곸슜 ?곹깭 ?뺤씤 (異붽? ?섏젙 遺덊븘??
- blind-to-x 3嫄??ㅽ뙣??pre-existing (curl_cffi ?ㅽ듃?뚰겕, cost_controls mock 遺덉씪移?

### TODO (?ㅼ쓬 ?몄뀡)
- [ ] blind-to-x pre-existing 3嫄??ㅽ뙣 ?섏젙
- [ ] MEDIUM 7嫄??꾩냽 ?섏젙 (紐⑤뜽 媛寃⑺몴 媛깆떊, PID ?뺤씤, Notion ?ъ떆?? config 踰붿쐞 寃利???
- [ ] 誘몄빱諛?蹂寃??뺣━ 諛?而ㅻ컠

### ?ㅼ쓬 ?먯씠?꾪듃?먭쾶 硫붾え
- ?꾩껜 QA ?먮룞??蹂듦뎄 ?꾨즺. Root coverage 84.72%濡?80% 湲곗? 異⑹”.
- `pipeline_watchdog.py` ?뚯뒪?멸? ?덈줈 異붽??섏뼱 ?대떦 紐⑤뱢 ?섏젙 ???뚭? 諛⑹? 媛??
- `media_step.py`??ThreadPoolExecutor??`_pool_shutdown` ?뚮옒洹??⑦꽩 ?ъ슜 以???`with` 臾?????섎룞 愿由?(?댁쑀: `with`??`wait=True`濡??먮윭 ??釉붾줈??.

---
