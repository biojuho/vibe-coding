# ?쭬 Vibe Coding (Joolife) ??留덉뒪??而⑦뀓?ㅽ듃

> **?좑툘 濡쒖뺄 ?꾩슜 ?꾨줈?앺듃 ???먭꺽 push/pull/deploy 湲덉?**
> ???꾨줈?앺듃??濡쒖뺄?먯꽌留??댁쁺?⑸땲?? ?대뼡 AI ?꾧뎄???먭꺽 ??μ냼??push, pull, deploy瑜??섑뻾?섏? 留덉꽭??

## ?꾨줈?앺듃 媛쒖슂

- **?꾨줈?앺듃紐?*: Vibe Coding (Joolife)
- **??以??ㅻ챸**: ?곗뒪?ы넲 ?쒖뼱, ?쇱씪 釉뚮━?? YouTube Shorts ?먮룞?? ?ъ씠???꾨줈?앺듃瑜??ы븿?섎뒗 ?ъ씤??AI ?댁떆?ㅽ꽩???뚰겕?ㅽ럹?댁뒪
- **?쇱씠?좎뒪**: MIT

---

## 湲곗닠 ?ㅽ깮

### Root ?뚰겕?ㅽ럹?댁뒪
| ??ぉ | 湲곗닠 | 踰꾩쟾 |
|------|------|------|
| ?몄뼱 | Python | 3.14 |
| ?뚯뒪??| pytest | 8.x+ |
| 由고듃 | ruff | - |
| CI | GitHub Actions (`root-quality-gate.yml`) | - |
| ?섍꼍 愿由?| venv + `.env` | - |

### ?섏쐞 ?꾨줈?앺듃蹂??ㅽ깮

| ?꾨줈?앺듃 | ?좏삎 | ?듭떖 湲곗닠 | 二쇱슂 踰꾩쟾 |
|----------|------|-----------|-----------|
| **hanwoo-dashboard** | ?뱀빋 | Next.js, React, Prisma, TailwindCSS, Radix UI, Recharts | Next 16, React 19, Prisma 6, TW 4 |
| **blind-to-x** | ?뚯씠?꾨씪??| Python, Notion API, Cloudinary, YAML ?ㅼ젙 | Python 3.x |
| **shorts-maker-v2** | CLI/?뚯씠?꾨씪??| Python, MoviePy, Edge TTS, OpenAI, Google GenAI, Pillow | Python 3.10+, MoviePy 2.1 |
| **knowledge-dashboard** | ?뱀빋 | Next.js, TypeScript, React, TailwindCSS, Recharts | Next 16, React 19, TS 5, TW 4 |
| **suika-game-v2** | 寃뚯엫 | Vanilla JS, Matter.js, Vite | Matter.js 0.20, Vite 6 |
| **word-chain** | 寃뚯엫 | React, Vite, Framer Motion, TailwindCSS | React 19, Vite 7, TW 4 |

### 怨듭쑀 ?명봽??

- **MCP ?쒕쾭** (10媛? `.mcp.json` ?듯빀 愿由?:
  - 怨듭떇: Notion, Filesystem, Brave Search, GitHub
  - 而ㅼ뒪?: SQLite Multi-DB, YouTube Data, Telegram, n8n Workflow, System Monitor, Cloudinary
- **?뚮┝**: Telegram Bot
- **?몃? API**: OpenAI, Google Gemini, Anthropic, DeepSeek, Moonshot, Zhipu AI, xAI, Xiaomi MiMo

---

## ?붾젆?좊━ 援ъ“

```
Vibe coding/                      # Root ?뚰겕?ㅽ럹?댁뒪
?쒋?? .ai/                          # ?넅 AI ?꾧뎄 怨듭쑀 而⑦뀓?ㅽ듃
??  ?쒋?? CONTEXT.md                # 留덉뒪??而⑦뀓?ㅽ듃 (???뚯씪)
??  ?쒋?? SESSION_LOG.md            # ?몄뀡 濡쒓렇
??  ?붴?? DECISIONS.md              # ?꾪궎?띿쿂 寃곗젙 湲곕줉
?쒋?? .agents/                      # AI ?먯씠?꾪듃 ?ㅼ젙
??  ?쒋?? rules/                    # ?꾨줈?앺듃 洹쒖튃
??  ?쒋?? skills/                   # 33醫?而ㅼ뒪? ?ㅽ궗
??  ?붴?? workflows/                # ?뚰겕?뚮줈??(/start, /end, /organize)
?쒋?? directives/                   # SOP 吏移⑥꽌 (16+ markdown)
??  ?붴?? personas/                 # AI ?섎Ⅴ?뚮굹 ?뺤쓽
?쒋?? execution/                    # 寃곗젙濡좎쟻 Python ?ㅽ겕由쏀듃 (27+)
??  ?붴?? pages/                    # Streamlit UI ?섏씠吏
?쒋?? scripts/                      # ?좏떥由ы떚 ?ㅽ겕由쏀듃
?쒋?? tests/                        # 猷⑦듃 ?뚯뒪???ㅼ쐞??(30+)
?쒋?? infrastructure/               # MCP ?쒕쾭, ?쒖뒪??紐⑤땲??
??
?쒋?? hanwoo-dashboard/             # ?쒖슦 ??쒕낫??(Next.js)
??  ?쒋?? src/                      # 硫붿씤 ?뚯뒪
??  ?붴?? prisma/                   # DB ?ㅽ궎留?
?쒋?? blind-to-x/                   # 釉붾씪?몃뱶 ?ㅽ겕?덉씠????Notion
??  ?쒋?? pipeline/                 # 泥섎━ ?뚯씠?꾨씪??
??  ?쒋?? scrapers/                 # ?ㅽ겕?덉씠??紐⑤뱢
??  ?붴?? tests/                    # ?뚯뒪??
?쒋?? shorts-maker-v2/              # YouTube Shorts ?먮룞??
??  ?쒋?? src/shorts_maker_v2/      # 硫붿씤 ?⑦궎吏
??  ??  ?붴?? pipeline/             # ?ㅼ??ㅽ듃?덉씠??
??  ?쒋?? assets/                   # 誘몃뵒???먯뀑
??  ?붴?? tests/                    # ?뚯뒪??
?쒋?? knowledge-dashboard/          # 吏????쒕낫??(Next.js/TS)
??  ?붴?? src/                      # 硫붿씤 ?뚯뒪
?쒋?? suika-game-v2/                # ?섎컯 寃뚯엫 (Matter.js)
??  ?붴?? src/                      # 硫붿씤 ?뚯뒪
?쒋?? word-chain/                   # ?앸쭚?뉕린 寃뚯엫 (React/Vite)
??  ?붴?? src/                      # 硫붿씤 ?뚯뒪
??
?쒋?? _archive/                     # ?꾩뭅?대툕???꾨줈?앺듃
?쒋?? .tmp/                         # ?꾩떆 ?뚯씪 (??젣 媛??
?붴?? venv/                         # Python 媛?곹솚寃?
```

---

## ?꾩옱 吏꾪뻾 ?곹솴

### ???꾨즺
- 猷⑦듃 ?뚰겕?ㅽ럹?댁뒪 3怨꾩링 ?꾪궎?띿쿂 (directives ??orchestration ??execution)
- hanwoo-dashboard: Next.js 16, Prisma 6, TailwindCSS 4 留덉씠洹몃젅?댁뀡 ?꾨즺
- blind-to-x: Notion ?곕룞 ?뚯씠?꾨씪???댁쁺 以?
- shorts-maker-v2: 5梨꾨꼸 而⑦뀗痢??꾨왂 諛??뚯씠?꾨씪??援ъ텞 (3-?섎Ⅴ?뚮굹 ?쒖뒪??
- shorts-maker-v2: 媛?쇱삤耳 ?깊겕 v2, FFmpeg HW 媛?? 梨꾨꼸蹂??명듃濡??꾩썐?몃줈
- knowledge-dashboard: Next.js 16, TypeScript 鍮뚮뱶 ?꾨즺
- suika-game-v2: Matter.js 湲곕컲 寃뚯엫 ?꾩꽦
- word-chain: React 19 + Vite 7 鍮뚮뱶 ?꾨즺
- YouTube Analytics ??Notion ?먮룞 ?섏쭛 援ы쁽
- Telegram ?뚮┝ ?쒖뒪??援ъ텞
- QA/QC 4?④퀎 ?먮룞??寃利??뚰겕?뚮줈???듯빀 (project-rules 諛?session_workflow ?곕룞)
- blind-to-x: 媛꾪뿉???뚯씠?꾨씪??exit 媛肄붾뱶 1 ?좊컻 Silent Error 諛⑹? 諛?濡쒓퉭 媛뺥솕
- shorts-maker-v2: ?곸긽 ?덉쭏 理쒖쟻??(Phase 2 湲곗닠 ?낃렇?덉씠??- Neon Cyberpunk, VS 鍮꾧탳 ??
- shorts-maker-v2: 5梨꾨꼸 ?좏뵿 ?먮룞 ?앹꽦 諛??몃젋??二쇱젣 媛깆떊 ?꾨꼍 ?곕룞
- blind-to-x: P6 硫???뚮옯??珥덉븞 ?앹꽦 (Threads + ?ㅼ씠踰?釉붾줈洹? ?뚯씠?꾨씪???꾩꽦
- blind-to-x: P6 ?뚮옯?쇰퀎 ??理쒖쟻??(classification_rules.yaml ?뺤옣 530以?
- blind-to-x: P6 ?깃낵 ?쇰뱶諛?猷⑦봽 紐⑤뱢 (`performance_tracker.py`) 援ы쁽 ??QC ?뱀씤
- blind-to-x: 戮먮퓣 ?먮낯 ?대?吏 蹂댁〈 ?뚯씠?꾨씪??(AI ?대?吏 ?앹꽦 ?고쉶) 援ы쁽 ??QC ?뱀씤
- blind-to-x: ?뚯뒪蹂?scrape limit ?좊떦??援ы쁽 (?낆떇 諛⑹?) ??QC ?뱀씤
- blind-to-x: NOTION_DATABASE_ID ?섍꼍 遺꾨━ 紐낇솗??(root vs blind-to-x 二쇱꽍 異붽?)
- blind-to-x: Gemini/xAI API ?명솚??寃利??꾨즺 (4 provider fallback ?뺤긽 ?숈옉)
- blind-to-x: ?ㅼ?以꾨윭 S4U 紐⑤뱶 ?꾪솚 ??PC ?좉툑/濡쒓렇?꾩썐 ?쒖뿉???먮룞 ?ㅽ뻾 蹂댁옣
- blind-to-x: ?뚯뒪蹂??대?吏 ?꾨왂 3-way 遺꾧린 (釉붾씪?몃뱶=Pixar ?좊땲/戮먮퓣,?먰렓=?먮낯 吏?湲고?=湲곗〈) ??QC ?뱀씤
- blind-to-x: ?섏쭛???섎（ ~30嫄?議곗젙 (scrape_limit 3, ?뚯뒪蹂?1) + Newsletter ?쒖뒪???쒓굅 ??QC ?뱀씤
- ?쒖뒪??紐⑤땲?곕쭅: `pipeline_watchdog.py` 援ъ텞 ???뚯씠?꾨씪???ㅼ?以꾨윭/Notion/?붿뒪??諛깆뾽 7媛???ぉ ?먮룞 媛먯떆 + Telegram ?뚮┝
- OneDrive ?먮룞 諛깆뾽: `backup_to_onedrive.py` 援ъ텞 ???듭떖 ?뚯씪 3,702媛?1.5GB) 留ㅼ씪 ?먮룞 諛깆뾽, 理쒓렐 7??蹂닿?
- blind-to-x: `run_scheduled.py`??watchdog + backup ?꾩냽 ?쒖뒪???듯빀
- n8n Phase 1: Docker Desktop + n8n 而⑦뀒?대꼫 援ъ텞, HTTP 釉뚮┸吏 ?쒕쾭, ?뚰겕?뚮줈??2媛?(BTX ?ㅼ?以꾨쭅 + ?ъ뒪泥댄겕)
- ?ㅽ궗 媛먯궗 ?뺣━: 45媛???23媛?(22媛??꾩뭅?대툕: 誘몄궗??18媛?+ 以묐났 4媛? `_archive/` ?대룞)
- GitHub Private Repo ?ㅼ젙: `biojuho/vibe-coding` (641 files, .env ?쒖쇅), 珥덇린 push ?꾨즺
- n8n ??Task Scheduler ?댁쨷 ?ㅽ뻾 諛⑹? ?꾨즺: BlindToX_0500~2100 5媛??쒖뒪??Disabled
- YouTube Analytics: 肄섑뀗痢?寃곌낵 異붿쟻 ?쒖뒪??援ъ텞 (result_tracker_db.py + result_dashboard.py) ??QC ?뱀씤
- shorts-maker-v2: ShortsFactory v1.2~v2.5 ?꾩껜 援ы쁽 + QC ?뱀씤
  - v1.2: BaseTemplate ?꾪솚 (10媛??좉퇋 ?쒗뵆由? 珥?17醫?
  - v1.3: Notion Bridge ?곕룞 (notion_bridge.py)
  - v1.5: AI ?ㅽ겕由쏀듃 ?먮룞 ?앹꽦 (script_gen.py)
  - v2.0: 5遺?梨꾨꼸 ?ㅼ틦?대뵫 (scaffold.py)
  - v2.5: A/B ?뚯뒪??+ 遺꾩꽍 (ab_test.py)
  - CountdownMixin 異붿텧: 4媛?移댁슫?몃떎???쒗뵆由?怨듯넻 濡쒖쭅 Mixin??(肄붾뱶 60% 媛먯냼)
  - scaffold ?낅젰 寃利?媛뺥솕: display_name/category/palette_style/first_template YAML injection 諛⑹뼱

- ?쒖뒪??怨좊룄??v2 Phase 0~3 ?꾨즺 (15媛??쒖뒪?? 2026-03-11):
  - P0: LLM 罹먯떆 72h ?쒖꽦?? OneDrive n8n 諛깆뾽, Debug DB TTL 90??
  - P1: YT Analytics n8n, ?ㅽ???Thompson Sampling, ML ?곗뼱??Cold Start, KPI ??쒕낫??
  - P2: ?좏뵿 ?ъ쟾 寃利? ??됲꽣 ?먭? 蹂듦뎄, 肄섑뀗痢?罹섎┛?? Notion 諛깆삤??
  - P3: ?낇???紐⑤땲?? CI ?뚯뒪??留ㅽ듃由?뒪, ?먮윭 遺꾩꽍湲? API ??寃利?

- MCP & Skill ?뺤옣 Phase 1~2 ?꾨즺 + QC ?뱀씤 (2026-03-12):
  - Phase 1: ?듯빀 `.mcp.json` ?앹꽦, 怨듭떇 MCP 5媛?(Notion, SQLite, Filesystem, Brave Search, GitHub)
  - Phase 2: 而ㅼ뒪? MCP 3媛?(YouTube Data, Telegram, n8n Workflow) + Skill 3媛?(pipeline-runner, daily-brief, cost-check)
  - Phase A+B+C (Antigravity): 而ㅼ뒪? MCP 3媛?異붽? (SQLite Multi-DB, System Monitor v2, Cloudinary) + Skill 5媛?異붽?
  - QC: npm ?⑦궎吏紐??섏젙, YouTube ?쒕퉬??罹먯떛, ?먮윭 諛섑솚 ?듭씪, TOCTOU ?쒓굅, Session ?留???15嫄??섏젙
  - mcp ?⑦궎吏 ?ㅼ튂 (`mcp[cli]>=1.0.0`), FastMCP 湲곕컲 ?쒕쾭 ?⑦꽩 ?듭씪
  - `.env.example` ?낅뜲?댄듃 (Telegram, GitHub, Brave, n8n Bridge ??異붽?)
  - QC 2李?(Antigravity): SQL Injection 諛⑹뼱(`_validate_table_name`), Docker ??꾩븘??3珥?OSError 諛⑹뼱 ??17/17 ?뚯뒪???듦낵, ?뱀씤

- shorts-maker-v2: ShortsFactory Quick Win + Phase 1 ?꾪궎?띿쿂 ?듯빀 (2026-03-12)
  - deprecated config ?대뜑 ??젣, 而щ윭 ?꾨━???댁옣 留덉씠洹몃젅?댁뀡
  - scaffold 4?④퀎 ?먮룞?깅줉, _mock_metrics ?쒓굅, channel 留ㅺ컻蹂?섑솕
  - Pipeline ??ShortsFactory ?듯빀 ?명꽣?섏씠??(`RenderAdapter`) ?뺤쓽
  - QC: 228 passed, 0 failed

- shorts-maker-v2: ?곸긽 湲몄씠 珥덇낵 + 移대씪?ㅼ? ?먮쭑 Critical 踰꾧렇 2嫄??섏젙 (2026-03-17)
  - CPS 4.2??.8 蹂댁젙 (SSML prosody/emphasis/break ?ㅻ쾭?ㅻ뱶 諛섏쁺)
  - orchestrator: 珥??ㅻ뵒??43珥?珥덇낵 ??body ???먮룞 ?몃┝ (hook/cta 蹂댁〈)
  - edge_tts_client: WordBoundary 誘몄닔????洹쇱궗 ??대컢 fallback ?앹꽦
  - render_step: 移대씪?ㅼ? ?곗씠???묎렐 dict?뭪uple ?섏젙
  - QC: 382 passed, 0 failed, ?ㅼ젣 ?곸긽 56.3s??4.0s, words_json 0/7??/7

- 시스템 고도화 v2 Phase 4 완료 + QC 승인 (2026-03-17):
  - T4-1: YouTube Channel Growth Tracker (channel_growth_tracker.py, pages/channel_growth.py)
  - T4-2: Content ROI Calculator (roi_calculator.py, pages/roi_dashboard.py)
  - T4-3: Content Series Engine (series_engine.py)
  - T4-4: X Analytics (x_analytics.py)
  - v3.0 로드맵 문서 작성 (directives/roadmap_v3.md)
  - QC: 753 tests passed, AST 11/11 OK, 보안 스캔 CLEAR
- NotebookLM-py 도입 완료 (2026-03-18):
  - v0.3.4 환경 구축, 노트북/문서 리스트/생성 CLI 래퍼 구현
  - 팟캐스트(Audio Overview) 기능 제외 후 운영 SOP 작성
  - auto_research_and_generate() 추가: 자동 웹 리서치 → 인포그래픽/슬라이드/마인드맵 생성
- NotebookLM × Blind-to-X 소셜 자산 자동 연동 완료 (2026-03-18):
  - notebooklm_enricher.py 신규 생성: 주제 기반 딥리서치 + 인포그래픽/슬라이드 자동 생성 + Cloudinary CDN 업로드
  - process.py 수정: draft 생성 직후 enricher 비동기 병렬 실행, 인포그래픽 → fallback 이미지로 활용
  - notion/_upload.py 수정: 🔬 NotebookLM 리서치 자산 섹션 Notion 페이지에 자동 삽입
  - NOTEBOOKLM_ENABLED=true 환경변수 가드로 기존 파이프라인 Zero Impact 보장
- Knowledge Dashboard 고도화 및 QA/QC 자동화 완료 (2026-03-18):
  - 3-탭 구조(지식현황/QA·QC/타임라인) UI 개편
  - `qaqc_runner.py` 기반 1-command 통합 테스팅(pytest, AST, 보안, 인프라) 구축
  - SQLite 히스토리 DB 연동 및 Dashboard 시각화
- shorts-maker-v2: SSML 태그 누출 버그 수정 + MiMo V2-Flash LLM 프로바이더 통합 (2026-03-20):
  - edge_tts_client: SSML 이중 래핑 제거, base_rate 파라미터 추가, hook/CTA 키워드 강조 스킵
  - config.yaml: MiMo 프로바이더 추가, llm_per_job .002→.001 (50% 절감)
  - QC: 537 passed, 12 skipped, 0 failed, MiMo API 라이브 테스트 성공

### 현재 진행 중

- blind-to-x: 스케줄러 자동 실행 모니터링 (S4U 전환 후 1주간)
- blind-to-x: 신규 영입 LLM 초안 품질 모니터링 (1주간 manual review)
- shorts-maker-v2: Phase 1 렌더링 → 메인 파이프라인 render_step↔RenderAdapter 연동

### 향후 예정

- 시스템 고도화 v2 Phase 5 실행 (고급 최적화 + 문서화)
- shorts-maker-v2: v3.0 Multi-language + SaaS 전환 (향후)
### ?좑툘 ?뚮젮吏??댁뒋
- ?섏쐞 ?꾨줈?앺듃(blind-to-x, hanwoo-dashboard, knowledge-dashboard)??`.git` ?대뜑媛 ?낅┰ repo ??root git push ???꾩떆濡?`.git.bak` 蹂寃??꾩슂

---

## ?듭떖 肄붾뵫 而⑤깽??

### TypeScript / React
- **而댄룷?뚰듃**: ?⑥닔??而댄룷?뚰듃 + ?붿궡???⑥닔
- **Props**: 蹂꾨룄 `interface` ?뺤쓽
- **???*: `any` 湲덉? ??`unknown` + ??낃???
- **鍮꾩쫰?덉뒪 濡쒖쭅**: 而ㅼ뒪? ?낆쑝濡?遺꾨━
- **?ㅼ씠諛?*: `camelCase`(?⑥닔/蹂??, `PascalCase`(而댄룷?뚰듃)
- **Import ?쒖꽌**: React ???몃? ?쇱씠釉뚮윭由????대? 紐⑤뱢 ????????????ㅽ???

### Python
- **????뚰듃**: 紐⑤뱺 ?⑥닔???꾩닔
- **Docstring**: Google ?ㅽ???
- **臾몄옄??*: f-string ?ъ슜
- **?곗씠??寃利?*: Pydantic ?쒖슜
- **?ㅼ씠諛?*: `snake_case`(?⑥닔/蹂??, `PascalCase`(?대옒??
- **Import ?쒖꽌**: ?쒖? ?쇱씠釉뚮윭由????쒕뱶?뚰떚 ??濡쒖뺄

### 怨듯넻 洹쒖튃
- ?먮윭 ?몃뱾留??꾩닔, 鍮?`catch`/`except` 湲덉?
- ?섍꼍蹂??異붽? ??`.env.example`?먮룄 ??異붽?
- 而ㅻ컠 硫붿떆吏: ?쒓뎅?? `[?곸뿭] ?묒뾽?댁슜` ?뺤떇
- 蹂寃쎌궗??? ?묒? ?⑥쐞濡??먯＜ commit

---

## ?슙 吏猶곕강 (AI 諛섎났 ?ㅼ닔 湲곕줉)

> AI ?꾧뎄媛 諛섎났?곸쑝濡??ㅼ닔?섎뒗 遺遺꾩쓣 ?ш린??湲곕줉?⑸땲??

| ?좎쭨 | ?꾧뎄 | ?댁슜 | ?닿껐 諛⑸쾿 |
|------|------|------|-----------|
| 2026-03-06 | 珥덇린 ?명똿 | (珥덇린?? | - |
| 2026-03-09 | Antigravity | Windows Task Scheduler?먯꽌 `Register-ScheduledTask`濡??쒓뎅??寃쎈줈(`諛뺤＜??)瑜??깅줉?섎㈃ XML??`獄쏅벡竊??`濡?源⑥쭚 ???ㅼ?以꾨윭 ?ㅽ뙣 | ASCII-only 寃쎈줈(`C:\btx\`)??launcher瑜??먭퀬 ?섍꼍蹂??`%LOCALAPPDATA%`, `%USERPROFILE%`)濡??고????댁꽍 |
| 2026-03-09 | Antigravity | Notion API `rich_text` 2000???쒗븳?먯꽌 ?좊땲肄붾뱶 ?쒓뎅??臾몄옄?댁씠 ?뺥솗??2000?먯뿬??API媛 嫄곕??섎뒗 寃쎌슦 諛쒖깮 | ?덉쟾 留덉쭊 10?먮? ?먭퀬 1990?먮줈 truncate |
| 2026-03-12 | Claude Code | FastMCP 1.26?먯꽌 `description` kwarg 誘몄?????`instructions`濡?蹂寃??꾩슂 | `FastMCP("name", instructions="...")` ?⑦꽩 ?ъ슜 |
| 2026-03-12 | Antigravity | SQLite 荑쇰━?먯꽌 ?뚯씠釉붾챸??f-string?쇰줈 吏곸젒 ?쎌엯?섎㈃ SQL Injection 踰≫꽣 諛쒖깮 | `_validate_table_name()` ?뺢퇋??寃利??⑥닔濡?蹂댄샇 (`^[a-zA-Z_][a-zA-Z0-9_]*$`) |
| 2026-03-16 | Antigravity | `channel_router.py`?먯꽌 `Path(__file__).parents[4]`濡??꾨줈??寃쎈줈 ?먯깋 ???ㅼ젣 ?꾨줈?앺듃 猷⑦듃??`parents[3]`. ?꾨줈?앺듃 ?앹꽦 ?댄썑 梨꾨꼸 ?꾨줈?꾩씠 ??踰덈룄 濡쒕뱶?섏? ?딆븯??(寃쎈줈 depth 怨꾩궛 ?ㅼ닔) | `parents[3]`?쇰줈 ?섏젙 + 二쇱꽍??depth ?ㅻ챸 異붽?. 寃쎈줈 depth 蹂寃???諛섎뱶???ㅼ젣 ?ㅽ뻾 ?꾩튂?먯꽌 `resolve()` 寃利??꾩닔 |
| 2026-03-16 | Antigravity | frozen dataclass??`copy.deepcopy()` ??吏곸젒 ?띿꽦 ?좊떦 ??`FrozenInstanceError`. 湲곗〈 肄붾뱶媛 dead code?ъ꽌 諛쒓껄 ????| `dataclasses.replace()` ?ъ슜?쇰줈 蹂寃? frozen=True ?대옒?ㅼ뿉????긽 `replace()` ?⑦꽩 ?곸슜 |
| 2026-03-17 | Claude Code | edge-tts SSMLCommunicate ?ъ슜 ??`stream()`?먯꽌 WordBoundary ?대깽??誘몄닔????`_words.json` 誘몄깮????移대씪?ㅼ? ?먮쭑 ?꾩껜 遺덈뒫 | `_approximate_word_timings()` fallback 異붽?. WordBoundary媛 鍮꾩뼱?덉쑝硫??ㅻ뵒??湲몄씠 湲곕컲 洹쇱궗 ??대컢 ?먮룞 ?앹꽦 |
| 2026-03-17 | Claude Code | `group_into_chunks()` 諛섑솚 ??낆씠 `list[tuple[float, float, str]]`?몃뜲, render_step?먯꽌 `chunk["text"]`, `chunk["words"]` ??dict ?묎렐?쇰줈 ?ъ슜 ???고??꾩뿉????긽 except濡?鍮좎졇 ?뺤쟻 ?먮쭑 ?대갚 | tuple ?명뙣??`for start, end, text in chunks` ?⑦꽩?쇰줈 ?섏젙. ?곗씠??援ъ“ 蹂寃????몄텧遺??諛섎뱶???뺤씤 |
| 2026-03-17 | Claude Code | `script_step.py` CPS 4.2??plain text 湲곗??댁뿀?쇰굹, SSML prosody/emphasis/break媛 TTS 諛쒗솕 ?쒓컙??1.5諛?利앷??쒗궡 (異붿젙 34.7s ???ㅼ젣 53s) | CPS 2.8濡??섑뼢 + orchestrator?먯꽌 43珥?珥덇낵 ??body ???먮룞 ?몃┝ |

---

*留덉?留??낅뜲?댄듃: 2026-03-17 13:00 KST (Claude Code ??shorts-maker-v2 ?곸긽 湲몄씠 + 移대씪?ㅼ? Critical 踰꾧렇 2嫄??섏젙 + QC ?뱀씤)*

## 2026-03-17 Codex Update

### shorts-maker-v2
- Renderer selection is now explicit in config/CLI/orchestrator: `native`, `auto`, `shorts_factory`.
- Native caption quality improved with real word timings, keyword highlight wiring, style override behavior, and channel-specific safe-area/motion tuning for `ai_tech` and `psychology`.
- ShortsFactory plan rendering now separates visual media from text overlay assets through `Scene.text_image_path`, so auto mode can be used for real visual comparison without losing subtitles.
- Representative renders completed successfully:
  - `output/qa_ai_tech_native.mp4`
  - `output/qa_psychology_native.mp4`
  - `output/qa_ai_tech_auto.mp4`
  - `output/qa_psychology_auto.mp4`
- Latest auto manifests recorded `ab_variant.renderer = shorts_factory`:
  - `output/20260317-065508-93e4a3c1_manifest.json`
  - `output/20260317-070555-013d38de_manifest.json`

### Known risks / landmines
- Edge TTS Korean voices `SoonBokNeural` and `BongJinNeural` can intermittently return `No audio was received`; the client now retries with plain text and default-voice fallback, but upstream instability remains.
- Fresh shells running MoviePy-related tests still need `IMAGEIO_FFMPEG_EXE` and `FFMPEG_BINARY` exported first.
- Visual regression baselines for subtitle PNG checks are currently generated under `.tmp/visual_baselines_quality` rather than committed goldens.

## 2026-03-17 Codex Re-QC Update

### shorts-maker-v2
- The previous `auto`/ShortsFactory silent-output issue is fixed: `audio_paths` now reach `Scene.extra["audio_path"]`, and real rerender output includes AAC audio.
- Subtitle visual regression tests are now hash-gated instead of auto-creating baselines on first run.
- Verified rerender artifact:
  - `output/qa_ai_tech_auto_rerun.mp4`
  - `output/20260317-081721-617444d2_manifest.json`

### Known risks / landmines
- Visual regression hashes are environment-sensitive by design; if fonts or rendering stack change intentionally, the approved hashes must be regenerated consciously.

## 2026-03-17 Codex UI Update

### hanwoo-dashboard
- The dashboard design system has been shifted to a claymorphism theme: warm cream/cocoa palettes, dual-shadow surfaces, softer tabs/modals/cards, and serif-accented headings.
- Tailwind/shadcn tokens and the legacy dashboard `--color-*` variables are now aligned, so shared primitives and custom screens read from the same theme source.
- Theme toggling now synchronizes both `data-theme` and the `.dark` class. This fixes the previous mismatch where legacy CSS changed but shadcn/Tailwind primitives stayed in light mode.
- Public-route visual verification artifact: `hanwoo-dashboard/hanwoo-login-clay.png`

### Known risks / landmines
- Protected `hanwoo-dashboard` routes redirect unauthenticated users to `/login`, so browser-based visual QA without credentials is limited to public pages unless someone signs in manually.
- The public route still logs manifest/favicon console noise during Playwright verification; it was not introduced by the claymorphism refresh.

## 2026-03-19 Antigravity QC Update

### blind-to-x (NotebookLM Integration + Scheduler WinError 6)

- `notebooklm_enricher.py` 신규 생성 — 주제 기반 딥 리서치 + 인포그래픽/슬라이드 자동 생성 + Cloudinary CDN 업로드
- `process.py` 수정 — enricher 비동기 병렬 실행
- `notion/_upload.py` 수정 — NotebookLM 리서치 자산 섹션 추가
- `execution/scheduler_engine.py` 수정 — subprocess WinError 6 방어 (Popen + communicate + OSError 처리)
- `pytest.ini` 수정 — `--capture=no` 추가 (Windows subprocess 핸들 안전 보장)
- `tests/conftest.py` 신규 — Windows capture disable autouse fixture

### Known risks / landmines

- **Windows pytest + subprocess PIPE → WinError 6**: pytest stdout 캡처 활성화 상태에서 `subprocess.PIPE`가 Windows 핸들 무효화 → `[WinError 6]`. `pytest.ini`에 `--capture=no` 필수. `scheduler_engine.py`에서 `subprocess.run(capture_output=True)` 사용 금지.
- **`update_context.py` 무한 루프**: `.tmp/update_context.py`가 장시간 실행되면 git lock 점유 → `git add/commit` block. 18시간 이상 실행된 사례 있음. 주기적으로 확인 필요.


## 2026-03-19 Codex UI Polish Update

### hanwoo-dashboard
- Secondary clay polish now covers the remaining obvious non-themed surfaces: `admin/diagnostics`, legal pages (`/terms`, `/privacy`), market/notification widgets, and the `analysis`, `feed`, `calving`, `schedule` tabs.
- Added reusable page-level clay helpers in `src/app/globals.css` (`.clay-shell`, `.clay-page-card`, `.clay-page-section`, `.clay-console`, etc.) plus shared clay chart palette variables (`--chart-clay-*`).
- Status/THI color maps in `src/lib/constants.js` and `src/lib/utils.js` were shifted from generic bright primaries to warmer clay-compatible accents so badges, rows, and weather states stay visually consistent.
- Legal pages now share `src/components/layout/LegalDocumentLayout.js` instead of inline one-off styles.

### Verification
- `npm run build` for `hanwoo-dashboard` passed after the polish pass.
- Playwright re-verified `/login` on a local dev server (`http://127.0.0.1:3002/login`) and saved `hanwoo-login-clay-refresh.png`.

### Known risks / landmines
- During this session, `/terms` navigation in the browser ended up on `/login`, so visual QA for the new legal layout is still limited by the current auth/middleware behavior.
- The dev server still reports the existing manifest/favicon console noise on public pages; this session did not change that.

## 2026-03-20 Codex QC Follow-up

### hanwoo-dashboard
- Calving processing is now atomic: `src/lib/actions.js` exposes `recordCalving()` and updates the mother record, calf creation, and history writes inside one Prisma transaction.
- `DashboardClient` and `CalvingTab` now use the single `recordCalving` path, and `src/lib/syncManager.js` can replay the same action from the offline queue.
- The lint toolchain has been migrated to ESLint 9 flat config (`eslint.config.mjs`), so `npm run lint` works again without the deprecated `next lint` path.
- New lint findings were cleaned up in `src/app/admin/diagnostics/page.js`, `src/lib/useTheme.js`, `src/lib/useOnlineStatus.js`, and the dashboard widget-settings initialization flow.

### Verification
- `npm run lint` passes in `hanwoo-dashboard`
- `npm run build` passes in `hanwoo-dashboard`

### Known risks / landmines
- `src/app/layout.js` still loads Google Fonts via page-level `<link>` tags, so lint emits one non-blocking `@next/next/no-page-custom-font` warning.
## Recent Update — 2026-03-21

- Root QA gate restored on Windows:
  - `scripts/quality_gate.py` now forces UTF-8 subprocess I/O to avoid CP949 decode/print failures.
  - Root pytest collection now includes `execution/tests` via `pytest.ini` and `execution/qaqc_runner.py`.
- Root test status:
  - `venv\Scripts\python.exe -m pytest -q` => `815 passed, 1 skipped`
  - coverage recovered to `81.05%` (`pytest.ini` threshold: 80%)
  - `venv\Scripts\python.exe scripts\quality_gate.py` passes end-to-end
- New root coverage tests added for execution scripts:
  - `tests/test_content_writer.py`
  - `tests/test_gdrive_pdf_extractor.py`
  - `tests/test_notion_article_uploader.py`
  - `tests/test_backup_to_onedrive.py`
  - `tests/test_qaqc_runner_extended.py`
- Known non-blocking warnings still present:
  - `ResourceWarning: unclosed database` in some pytest paths
  - `datetime.utcnow()` deprecation warning in `execution/content_writer.py`
