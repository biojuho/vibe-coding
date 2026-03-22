# Vibe Coding (Joolife) 마스터 컨텍스트

> **로컬 전용 프로젝트 — 원격 push/pull/deploy 금지**
> 이 프로젝트는 로컬에서만 운영됩니다. 어떤 AI 도구도 원격 저장소에 push, pull, deploy를 실행하지 마세요.

## 프로젝트 개요

- **프로젝트명**: Vibe Coding (Joolife)
- **핵심 설명**: 데이터 사이언스 기반, 일일 브리핑, YouTube Shorts 자동화, 사이드 프로젝트를 포함하는 개인용 AI 어시스턴트 워크스페이스
- **라이선스**: MIT

---

## 기술 스택

### Root 워크스페이스
| 항목 | 기술 | 버전 |
|------|------|------|
| 언어 | Python | 3.14 |
| 테스트 | pytest | 8.x+ |
| 린트 | ruff | - |
| CI | GitHub Actions (`root-quality-gate.yml`) | - |
| 환경 관리 | venv + `.env` | - |

### 서브 프로젝트별 스택

| 프로젝트 | 등급 | 유형 | 핵심 기술 | 주요 버전 |
|----------|------|------|-----------|-----------|
| **blind-to-x** | Active | 파이프라인 | Python, Notion API, Cloudinary, YAML 설정 | Python 3.x |
| **shorts-maker-v2** | Active | CLI/파이프라인 | Python, MoviePy, Edge TTS, OpenAI, Google GenAI, Pillow | Python 3.10+, MoviePy 2.1 |
| **hanwoo-dashboard** | Active | 웹앱 | Next.js, React, Prisma, TailwindCSS, Radix UI, Recharts | Next 16, React 19, Prisma 6, TW 4 |
| **knowledge-dashboard** | Maintenance | 웹앱 | Next.js, TypeScript, React, TailwindCSS, Recharts | Next 16, React 19, TS 5, TW 4 |
| **suika-game-v2** | Frozen | 게임 | Vanilla JS, Matter.js, Vite | Matter.js 0.20, Vite 6 |
| **word-chain** | Frozen | 게임 | React, Vite, Framer Motion, TailwindCSS | React 19, Vite 7, TW 4 |

### 공유 인프라

- **MCP 서버** (10개, `.mcp.json` 통합 관리):
  - 공식: Notion, Filesystem, Brave Search, GitHub
  - 커스텀: SQLite Multi-DB, YouTube Data, Telegram, n8n Workflow, System Monitor, Cloudinary
- **알림**: Telegram Bot
- **외부 API**: OpenAI, Google Gemini, Anthropic, DeepSeek, Moonshot, Zhipu AI, xAI, Xiaomi MiMo

---

## 디렉터리 구조

```
Vibe coding/                      # Root 워크스페이스
├── .ai/                          # 전 AI 도구 공유 컨텍스트
│   ├── CONTEXT.md                # 마스터 컨텍스트 (이 파일)
│   ├── SESSION_LOG.md            # 세션 로그
│   └── DECISIONS.md              # 아키텍처 결정 기록
├── .agents/                      # AI 에이전트 설정
│   ├── rules/                    # 프로젝트 규칙
│   ├── skills/                   # 33종 커스텀 스킬
│   └── workflows/                # 워크플로우 (/start, /end, /organize)
├── directives/                   # SOP 지침서 (28개 markdown)
│   └── personas/                 # AI 페르소나 정의
├── execution/                    # 결정론적 Python 스크립트 (39개)
│   └── pages/                    # Streamlit UI 페이지
├── scripts/                      # 유틸리티 스크립트
├── tests/                        # 루트 테스트 스위트 (37개)
├── infrastructure/               # MCP 서버, 시스템 모니터링
│
├── hanwoo-dashboard/             # 한우 대시보드 (Next.js)
│   ├── src/                      # 메인 소스
│   └── prisma/                   # DB 스키마
├── blind-to-x/                   # 블라인드 스크래핑 → Notion
│   ├── pipeline/                 # 처리 파이프라인
│   ├── scrapers/                 # 스크래핑 모듈
│   └── tests/                    # 테스트
├── shorts-maker-v2/              # YouTube Shorts 자동화
│   ├── src/shorts_maker_v2/      # 메인 패키지
│   │   └── pipeline/             # 4스테이지 파이프라인
│   ├── assets/                   # 미디어 자원
│   └── tests/                    # 테스트
├── knowledge-dashboard/          # 지식 대시보드 (Next.js/TS)
│   └── src/                      # 메인 소스
├── suika-game-v2/                # 수박 게임 (Matter.js)
│   └── src/                      # 메인 소스
├── word-chain/                   # 끝말잇기 게임 (React/Vite)
│   └── src/                      # 메인 소스
│
├── _archive/                     # 아카이브된 프로젝트
├── .tmp/                         # 임시 파일 (삭제 가능)
└── venv/                         # Python 가상환경
```

---

## 현재 진행 상황

### 완료
- 루트 워크스페이스 3계층 아키텍처 (directives → orchestration → execution)
- hanwoo-dashboard: Next.js 16, Prisma 6, TailwindCSS 4 마이그레이션 완료
- blind-to-x: Notion 연동 파이프라인 운영 중
- shorts-maker-v2: 5채널 콘텐츠 기획 및 파이프라인 구축 (3-페르소나 시스템)
- shorts-maker-v2: 카라오케 캡션 v2, FFmpeg HW 가속, 채널별 인트로/아웃트로
- knowledge-dashboard: Next.js 16, TypeScript 빌드 완료
- suika-game-v2: Matter.js 기반 게임 완성
- word-chain: React 19 + Vite 7 빌드 완료
- YouTube Analytics → Notion 자동 연동 구현
- Telegram 알림 시스템 구축
- QA/QC 4단계 자동화 검증 워크플로우 통합 (project-rules 및 session_workflow 연동)
- blind-to-x: 각 커뮤니티 파이프라인 exit 코드 1 Silent Error 방지 및 로깅 강화
- shorts-maker-v2: 영상 품질 최적화 (Phase 2 기술 업그레이드 - Neon Cyberpunk, VS 비교 등)
- shorts-maker-v2: 5채널 콘텐츠 자동 생성 및 이전에 알림 개선 자동 경험 연동
- blind-to-x: P6 멘션 플랫폼 초안 생성 (Threads + 다이버 블로그 파이프라인 완성)
- blind-to-x: P6 플랫폼별 톤 최적화 (classification_rules.yaml 확장 530줄)
- blind-to-x: P6 성과 피드백 루프 모듈 (`performance_tracker.py`) 구현 및 QC 승인
- blind-to-x: 커뮤니티 원본 이미지 보존 파이프라인 (AI 이미지 생성 병행) 구현 및 QC 승인
- blind-to-x: 커뮤니티별 scrape limit 할당량 구현 (형식 반영) 및 QC 승인
- blind-to-x: NOTION_DATABASE_ID 환경 분리 명확화 (root vs blind-to-x 주석 추가)
- blind-to-x: Gemini/xAI API 효율적 검증 완료 (4 provider fallback 정상 동작)
- blind-to-x: 스케줄러 S4U 모드 전환 및 PC 절전/로그아웃 시에도 자동 실행 보장
- blind-to-x: 커뮤니티별 이미지 기획 3-way 분기 (블라인드=Pixar 애니/커뮤니티,디시=원본 사진/기생충=기존) 및 QC 승인
- blind-to-x: 운영 안정화 ~30건 조정 (scrape_limit 3, 커뮤니티별 1) + Newsletter 시스템 제거 및 QC 승인
- 시스템 모니터링: `pipeline_watchdog.py` 구축 — 파이프라인 스케줄러/Notion/테스트/백업 7개 항목 자동 감시 + Telegram 알림
- OneDrive 자동 백업: `backup_to_onedrive.py` 구축 — 핵심 파일 3,702개(1.5GB) 매일 자동 백업, 최대 7일 보관
- blind-to-x: `run_scheduled.py`에 watchdog + backup 후속 시스템 통합
- n8n Phase 1: Docker Desktop + n8n 컨테이너 구축, HTTP 브릿지 서버, 워크플로우 2개(BTX 스케줄링 + 헬스체크)
- 스킬 감사 정리: 45개 → 23개(22개 아카이브: 미사용 18개 + 중복 4개, `_archive/` 이동)
- GitHub Private Repo 설정: `biojuho/vibe-coding` (641 files, .env 제외), 초기 push 완료
- n8n 및 Task Scheduler 이중 실행 방지 완료: BlindToX_0500~2100 5개 시스템 Disabled
- YouTube Analytics: 콘텐츠 결과 추적 시스템 구축 (result_tracker_db.py + result_dashboard.py) 및 QC 승인
- shorts-maker-v2: ShortsFactory v1.2~v2.5 전체 구현 + QC 승인
  - v1.2: BaseTemplate 확장 (10개 템플릿 스플릿, 총 17종)
  - v1.3: Notion Bridge 연동 (notion_bridge.py)
  - v1.5: AI 스크립트 자동 생성 (script_gen.py)
  - v2.0: 5분기 채널 스캐폴딩 (scaffold.py)
  - v2.5: A/B 테스트 + 분석 (ab_test.py)
  - CountdownMixin 추출: 4개 카운트다운 템플릿 공통 로직 Mixin화 (코드 60% 감소)
  - scaffold 입력 검증 강화: display_name/category/palette_style/first_template YAML injection 방어

- 시스템 고도화 v2 Phase 0~3 완료 (15개 시스템, 2026-03-11):
  - P0: LLM 캐시 72h 선적용, OneDrive n8n 백업, Debug DB TTL 90일
  - P1: YT Analytics n8n, 스케줄 Thompson Sampling, ML 데이터 Cold Start, KPI 대시보드
  - P2: 콘텐츠 사전 검증, 필터 강도 분리, 콘텐츠 캘린더, Notion 발주 연동
  - P3: 통합 모니터링, CI 테스트 매트릭스, 에러 분석기, API 사용 검증

- MCP & Skill 확장 Phase 1~2 완료 + QC 승인 (2026-03-12):
  - Phase 1: 통합 `.mcp.json` 생성, 공식 MCP 5개 (Notion, SQLite, Filesystem, Brave Search, GitHub)
  - Phase 2: 커스텀 MCP 3개 (YouTube Data, Telegram, n8n Workflow) + Skill 3개 (pipeline-runner, daily-brief, cost-check)
  - Phase A+B+C (Antigravity): 커스텀 MCP 3개 추가 (SQLite Multi-DB, System Monitor v2, Cloudinary) + Skill 5개 추가
  - QC: npm 패키지명 수정, YouTube 서비스 캐싱, 에러 반환 통일, TOCTOU 제거, Session 제한 등 15건 수정
  - mcp 패키지 설치 (`mcp[cli]>=1.0.0`), FastMCP 기반 서버 패턴 통일
  - `.env.example` 업데이트 (Telegram, GitHub, Brave, n8n Bridge 등 추가)
  - QC 2차(Antigravity): SQL Injection 방어(`_validate_table_name`), Docker 미실행시 3초 OSError 방어 등 17/17 테스트 통과, 승인

- shorts-maker-v2: ShortsFactory Quick Win + Phase 1 아키텍처 통합 (2026-03-12)
  - deprecated config 에러 제거, 컬러 프리셋 마이그레이션
  - scaffold 4단계 자동 등록, _mock_metrics 제거, channel 매핑별 변환
  - Pipeline ↔ ShortsFactory 통합 인터페이스(`RenderAdapter`) 정의
  - QC: 228 passed, 0 failed

- shorts-maker-v2: 영상 길이 초과 + 카라오케 자막 Critical 버그 2건 수정 (2026-03-17)
  - CPS 4.2→2.8 보정 (SSML prosody/emphasis/break 오버헤드 반영)
  - orchestrator: 총 오디오 43초 초과 시 body 씬 자동 트림 (hook/cta 보존)
  - edge_tts_client: WordBoundary 미수신 시 근사 타이밍 fallback 생성
  - render_step: 카라오케 데이터 타입 dict→tuple 수정
  - QC: 382 passed, 0 failed, 실제 영상 56.3s→54.0s, words_json 0/7→7/7

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
- NotebookLM x Blind-to-X 소셜 자산 자동 연동 완료 (2026-03-18):
  - notebooklm_enricher.py 신규 생성: 주제 기반 딥리서치 + 인포그래픽/슬라이드 자동 생성 + Cloudinary CDN 업로드
  - process.py 수정: draft 생성 직후 enricher 비동기 병렬 실행, 인포그래픽 → fallback 이미지로 활용
  - notion/_upload.py 수정: NotebookLM 리서치 자산 섹션 Notion 페이지에 자동 삽입
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

### 지뢰밭 (AI 반복 실수 기록)

> AI 도구가 반복적으로 실수하는 부분을 여기에 기록합니다.

| 일자 | 도구 | 내용 | 대응 방법 |
|------|------|------|-----------|
| 2026-03-06 | 초기 설정 | (초기화) | - |
| 2026-03-09 | Antigravity | Windows Task Scheduler에서 `Register-ScheduledTask`로 한국어 경로(`박주호`)를 등록하면 XML이 `&#xBCF5;` 등으로 깨져 스케줄러 실패 | ASCII-only 경로(`C:\btx\`)에 launcher를 두고 환경변수(`%LOCALAPPDATA%`, `%USERPROFILE%`)로 참조하여 해석 |
| 2026-03-09 | Antigravity | Notion API `rich_text` 2000자 제한에서 유니코드 한국어 문자열이 정확히 2000자여도 API가 거부하는 경우 발생 | 안전 마진 10자를 두고 1990자로 truncate |
| 2026-03-12 | Claude Code | FastMCP 1.26에서 `description` kwarg 미지원 → `instructions`로 변경 필요 | `FastMCP("name", instructions="...")` 패턴 사용 |
| 2026-03-12 | Antigravity | SQLite 쿼리에서 테이블명을 f-string으로 직접 삽입하면 SQL Injection 벡터 발생 | `_validate_table_name()` 화이트리스트 검증 함수로 보호 (`^[a-zA-Z_][a-zA-Z0-9_]*$`) |
| 2026-03-16 | Antigravity | `channel_router.py`에서 `Path(__file__).parents[4]`로 프로젝트 경로 탐색 시 실제 프로젝트 루트는 `parents[3]`. 프로젝트 생성 이후 채널 프로필이 한 번도 로드되지 않았음 (경로 depth 계산 실수) | `parents[3]`으로 수정 + 주석에 depth 설명 추가. 경로 depth 변경 시 반드시 실제 실행 위치에서 `resolve()` 검증 필수 |
| 2026-03-16 | Antigravity | frozen dataclass에 `copy.deepcopy()` 시 직접 속성 할당에서 `FrozenInstanceError`. 기존 코드가 dead code여서 발견 안 됨 | `dataclasses.replace()` 사용으로 변경. frozen=True 클래스에는 항상 `replace()` 패턴 적용 |
| 2026-03-17 | Claude Code | edge-tts SSMLCommunicate 사용 시 `stream()`에서 WordBoundary 이벤트 미수신 시 `_words.json` 미생성으로 카라오케 자막 전체 불능 | `_approximate_word_timings()` fallback 추가. WordBoundary가 비어있으면 오디오 길이 기반 근사 균등 타이밍 자동 생성 |
| 2026-03-17 | Claude Code | `group_into_chunks()` 반환 타입이 `list[tuple[float, float, str]]`인데, render_step에서 `chunk["text"]`, `chunk["words"]` 등 dict 접근으로 사용 → TypeError에서도 항상 except로 빠져 적발 어려움 | tuple 언패킹 `for start, end, text in chunks` 패턴으로 수정. 데이터 구조 변경 시 소비부를 반드시 확인 |
| 2026-03-17 | Claude Code | `script_step.py` CPS 4.2를 plain text 기준 계산했으나, SSML prosody/emphasis/break가 TTS 발화 시간을 1.5배 증가시켜 초과 (추정 34.7s → 실제 53s) | CPS 2.8로 하향 + orchestrator에서 43초 초과 시 body 씬 자동 트림 |

---

*마지막 업데이트: 2026-03-17 13:00 KST (Claude Code — shorts-maker-v2 영상 길이 + 카라오케 Critical 버그 2건 수정 + QC 승인)*

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
