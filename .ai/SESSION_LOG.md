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
