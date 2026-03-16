# 🧠 Vibe Coding (Joolife) — 마스터 컨텍스트

> **⚠️ 로컬 전용 프로젝트 — 원격 push/pull/deploy 금지**
> 이 프로젝트는 로컬에서만 운영됩니다. 어떤 AI 도구도 원격 저장소에 push, pull, deploy를 수행하지 마세요.

## 프로젝트 개요

- **프로젝트명**: Vibe Coding (Joolife)
- **한 줄 설명**: 데스크톱 제어, 일일 브리핑, YouTube Shorts 자동화, 사이드 프로젝트를 포함하는 올인원 AI 어시스턴트 워크스페이스
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

### 하위 프로젝트별 스택

| 프로젝트 | 유형 | 핵심 기술 | 주요 버전 |
|----------|------|-----------|-----------|
| **hanwoo-dashboard** | 웹앱 | Next.js, React, Prisma, TailwindCSS, Radix UI, Recharts | Next 16, React 19, Prisma 6, TW 4 |
| **blind-to-x** | 파이프라인 | Python, Notion API, Cloudinary, YAML 설정 | Python 3.x |
| **shorts-maker-v2** | CLI/파이프라인 | Python, MoviePy, Edge TTS, OpenAI, Google GenAI, Pillow | Python 3.10+, MoviePy 2.1 |
| **knowledge-dashboard** | 웹앱 | Next.js, TypeScript, React, TailwindCSS, Recharts | Next 16, React 19, TS 5, TW 4 |
| **suika-game-v2** | 게임 | Vanilla JS, Matter.js, Vite | Matter.js 0.20, Vite 6 |
| **word-chain** | 게임 | React, Vite, Framer Motion, TailwindCSS | React 19, Vite 7, TW 4 |

### 공유 인프라

- **MCP 서버** (10개, `.mcp.json` 통합 관리):
  - 공식: Notion, Filesystem, Brave Search, GitHub
  - 커스텀: SQLite Multi-DB, YouTube Data, Telegram, n8n Workflow, System Monitor, Cloudinary
- **알림**: Telegram Bot
- **외부 API**: OpenAI, Google Gemini, Anthropic, DeepSeek, Moonshot, Zhipu AI, xAI

---

## 디렉토리 구조

```
Vibe coding/                      # Root 워크스페이스
├── .ai/                          # 🆕 AI 도구 공유 컨텍스트
│   ├── CONTEXT.md                # 마스터 컨텍스트 (이 파일)
│   ├── SESSION_LOG.md            # 세션 로그
│   └── DECISIONS.md              # 아키텍처 결정 기록
├── .agents/                      # AI 에이전트 설정
│   ├── rules/                    # 프로젝트 규칙
│   ├── skills/                   # 33종 커스텀 스킬
│   └── workflows/                # 워크플로우 (/start, /end, /organize)
├── directives/                   # SOP 지침서 (16+ markdown)
│   └── personas/                 # AI 페르소나 정의
├── execution/                    # 결정론적 Python 스크립트 (27+)
│   └── pages/                    # Streamlit UI 페이지
├── scripts/                      # 유틸리티 스크립트
├── tests/                        # 루트 테스트 스위트 (30+)
├── infrastructure/               # MCP 서버, 시스템 모니터
│
├── hanwoo-dashboard/             # 한우 대시보드 (Next.js)
│   ├── src/                      # 메인 소스
│   └── prisma/                   # DB 스키마
├── blind-to-x/                   # 블라인드 스크레이퍼 → Notion
│   ├── pipeline/                 # 처리 파이프라인
│   ├── scrapers/                 # 스크레이퍼 모듈
│   └── tests/                    # 테스트
├── shorts-maker-v2/              # YouTube Shorts 자동화
│   ├── src/shorts_maker_v2/      # 메인 패키지
│   │   └── pipeline/             # 오케스트레이터
│   ├── assets/                   # 미디어 에셋
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

### ✅ 완료
- 루트 워크스페이스 3계층 아키텍처 (directives → orchestration → execution)
- hanwoo-dashboard: Next.js 16, Prisma 6, TailwindCSS 4 마이그레이션 완료
- blind-to-x: Notion 연동 파이프라인 운영 중
- shorts-maker-v2: 5채널 컨텐츠 전략 및 파이프라인 구축 (3-페르소나 시스템)
- shorts-maker-v2: 가라오케 싱크 v2, FFmpeg HW 가속, 채널별 인트로/아웃트로
- knowledge-dashboard: Next.js 16, TypeScript 빌드 완료
- suika-game-v2: Matter.js 기반 게임 완성
- word-chain: React 19 + Vite 7 빌드 완료
- YouTube Analytics → Notion 자동 수집 구현
- Telegram 알림 시스템 구축
- QA/QC 4단계 자동화 검증 워크플로우 통합 (project-rules 및 session_workflow 연동)
- blind-to-x: 간헐적 파이프라인 exit 가코드 1 유발 Silent Error 방지 및 로깅 강화
- shorts-maker-v2: 영상 품질 최적화 (Phase 2 기술 업그레이드 - Neon Cyberpunk, VS 비교 등)
- shorts-maker-v2: 5채널 토픽 자동 생성 및 트렌딩 주제 갱신 완벽 연동
- blind-to-x: P6 멀티 플랫폼 초안 생성 (Threads + 네이버 블로그) 파이프라인 완성
- blind-to-x: P6 플랫폼별 톤 최적화 (classification_rules.yaml 확장 530줄)
- blind-to-x: P6 성과 피드백 루프 모듈 (`performance_tracker.py`) 구현 — QC 승인
- blind-to-x: 뽐뿌 원본 이미지 보존 파이프라인 (AI 이미지 생성 우회) 구현 — QC 승인
- blind-to-x: 소스별 scrape limit 할당제 구현 (독식 방지) — QC 승인
- blind-to-x: NOTION_DATABASE_ID 환경 분리 명확화 (root vs blind-to-x 주석 추가)
- blind-to-x: Gemini/xAI API 호환성 검증 완료 (4 provider fallback 정상 동작)
- blind-to-x: 스케줄러 S4U 모드 전환 — PC 잠금/로그아웃 시에도 자동 실행 보장
- blind-to-x: 소스별 이미지 전략 3-way 분기 (블라인드=Pixar 애니/뽐뿌,에펨=원본 짤/기타=기존) — QC 승인
- blind-to-x: 수집량 하루 ~30건 조정 (scrape_limit 3, 소스별 1) + Newsletter 태스크 제거 — QC 승인
- 시스템 모니터링: `pipeline_watchdog.py` 구축 — 파이프라인/스케줄러/Notion/디스크/백업 7개 항목 자동 감시 + Telegram 알림
- OneDrive 자동 백업: `backup_to_onedrive.py` 구축 — 핵심 파일 3,702개(1.5GB) 매일 자동 백업, 최근 7회 보관
- blind-to-x: `run_scheduled.py`에 watchdog + backup 후속 태스크 통합
- n8n Phase 1: Docker Desktop + n8n 컨테이너 구축, HTTP 브릿지 서버, 워크플로우 2개 (BTX 스케줄링 + 헬스체크)
- 스킬 감사 정리: 45개 → 23개 (22개 아카이브: 미사용 18개 + 중복 4개, `_archive/` 이동)
- GitHub Private Repo 설정: `biojuho/vibe-coding` (641 files, .env 제외), 초기 push 완료
- n8n ↔ Task Scheduler 이중 실행 방지 완료: BlindToX_0500~2100 5개 태스크 Disabled
- YouTube Analytics: 콘텐츠 결과 추적 시스템 구축 (result_tracker_db.py + result_dashboard.py) — QC 승인
- shorts-maker-v2: ShortsFactory v1.2~v2.5 전체 구현 + QC 승인
  - v1.2: BaseTemplate 전환 (10개 신규 템플릿, 총 17종)
  - v1.3: Notion Bridge 연동 (notion_bridge.py)
  - v1.5: AI 스크립트 자동 생성 (script_gen.py)
  - v2.0: 5분 채널 스캐폴딩 (scaffold.py)
  - v2.5: A/B 테스트 + 분석 (ab_test.py)
  - CountdownMixin 추출: 4개 카운트다운 템플릿 공통 로직 Mixin화 (코드 60% 감소)
  - scaffold 입력 검증 강화: display_name/category/palette_style/first_template YAML injection 방어

- 시스템 고도화 v2 Phase 0~3 완료 (15개 태스크, 2026-03-11):
  - P0: LLM 캐시 72h 활성화, OneDrive n8n 백업, Debug DB TTL 90일
  - P1: YT Analytics n8n, 스타일 Thompson Sampling, ML 티어드 Cold Start, KPI 대시보드
  - P2: 토픽 사전 검증, 셀렉터 자가 복구, 콘텐츠 캘린더, Notion 백오프
  - P3: 업타임 모니터, CI 테스트 매트릭스, 에러 분석기, API 키 검증

- MCP & Skill 확장 Phase 1~2 완료 + QC 승인 (2026-03-12):
  - Phase 1: 통합 `.mcp.json` 생성, 공식 MCP 5개 (Notion, SQLite, Filesystem, Brave Search, GitHub)
  - Phase 2: 커스텀 MCP 3개 (YouTube Data, Telegram, n8n Workflow) + Skill 3개 (pipeline-runner, daily-brief, cost-check)
  - Phase A+B+C (Antigravity): 커스텀 MCP 3개 추가 (SQLite Multi-DB, System Monitor v2, Cloudinary) + Skill 5개 추가
  - QC: npm 패키지명 수정, YouTube 서비스 캐싱, 에러 반환 통일, TOCTOU 제거, Session 풀링 등 15건 수정
  - mcp 패키지 설치 (`mcp[cli]>=1.0.0`), FastMCP 기반 서버 패턴 통일
  - `.env.example` 업데이트 (Telegram, GitHub, Brave, n8n Bridge 키 추가)
  - QC 2차 (Antigravity): SQL Injection 방어(`_validate_table_name`), Docker 타임아웃 3초+OSError 방어 — 17/17 테스트 통과, 승인

- shorts-maker-v2: ShortsFactory Quick Win + Phase 1 아키텍처 통합 (2026-03-12)
  - deprecated config 폴더 삭제, 컬러 프리셋 내장 마이그레이션
  - scaffold 4단계 자동등록, _mock_metrics 제거, channel 매개변수화
  - Pipeline ↔ ShortsFactory 통합 인터페이스 (`RenderAdapter`) 정의
  - QC: 228 passed, 0 failed

### 🔄 진행 중

- blind-to-x: 스케줄러 자동 실행 모니터링 (S4U 전환 후 1주간)
- blind-to-x: 실 운영 LLM 초안 품질 모니터링 (1주간 manual review)
- 시스템 고도화 v2 Phase 4~5 (고급 최적화, 문서화) 미실행
- shorts-maker-v2: Phase 1 나머지 — 메인 파이프라인 render_step에 RenderAdapter 연동

### 📋 예정

- 시스템 고도화 v2 Phase 4~5 실행
- shorts-maker-v2: v3.0 Multi-language + SaaS 전환 (향후)

### ⚠️ 알려진 이슈
- 하위 프로젝트(blind-to-x, hanwoo-dashboard, knowledge-dashboard)의 `.git` 폴더가 독립 repo → root git push 시 임시로 `.git.bak` 변경 필요

---

## 핵심 코딩 컨벤션

### TypeScript / React
- **컴포넌트**: 함수형 컴포넌트 + 화살표 함수
- **Props**: 별도 `interface` 정의
- **타입**: `any` 금지 → `unknown` + 타입가드
- **비즈니스 로직**: 커스텀 훅으로 분리
- **네이밍**: `camelCase`(함수/변수), `PascalCase`(컴포넌트)
- **Import 순서**: React → 외부 라이브러리 → 내부 모듈 → 훅 → 타입 → 스타일

### Python
- **타입 힌트**: 모든 함수에 필수
- **Docstring**: Google 스타일
- **문자열**: f-string 사용
- **데이터 검증**: Pydantic 활용
- **네이밍**: `snake_case`(함수/변수), `PascalCase`(클래스)
- **Import 순서**: 표준 라이브러리 → 서드파티 → 로컬

### 공통 규칙
- 에러 핸들링 필수, 빈 `catch`/`except` 금지
- 환경변수 추가 시 `.env.example`에도 키 추가
- 커밋 메시지: 한국어, `[영역] 작업내용` 형식
- 변경사항은 작은 단위로 자주 commit

---

## 🚧 지뢰밭 (AI 반복 실수 기록)

> AI 도구가 반복적으로 실수하는 부분을 여기에 기록합니다.

| 날짜 | 도구 | 내용 | 해결 방법 |
|------|------|------|-----------| 
| 2026-03-06 | 초기 세팅 | (초기화) | - |
| 2026-03-09 | Antigravity | Windows Task Scheduler에서 `Register-ScheduledTask`로 한국어 경로(`박주호`)를 등록하면 XML에 `諛뺤＜??`로 깨짐 → 스케줄러 실패 | ASCII-only 경로(`C:\btx\`)에 launcher를 두고 환경변수(`%LOCALAPPDATA%`, `%USERPROFILE%`)로 런타임 해석 |
| 2026-03-09 | Antigravity | Notion API `rich_text` 2000자 제한에서 유니코드 한국어 문자열이 정확히 2000자여도 API가 거부하는 경우 발생 | 안전 마진 10자를 두고 1990자로 truncate |
| 2026-03-12 | Claude Code | FastMCP 1.26에서 `description` kwarg 미지원 → `instructions`로 변경 필요 | `FastMCP("name", instructions="...")` 패턴 사용 |
| 2026-03-12 | Antigravity | SQLite 쿼리에서 테이블명을 f-string으로 직접 삽입하면 SQL Injection 벡터 발생 | `_validate_table_name()` 정규식 검증 함수로 보호 (`^[a-zA-Z_][a-zA-Z0-9_]*$`) |
| 2026-03-16 | Antigravity | `channel_router.py`에서 `Path(__file__).parents[4]`로 프로필 경로 탐색 → 실제 프로젝트 루트는 `parents[3]`. 프로젝트 생성 이후 채널 프로필이 한 번도 로드되지 않았음 (경로 depth 계산 실수) | `parents[3]`으로 수정 + 주석에 depth 설명 추가. 경로 depth 변경 시 반드시 실제 실행 위치에서 `resolve()` 검증 필수 |
| 2026-03-16 | Antigravity | frozen dataclass에 `copy.deepcopy()` 후 직접 속성 할당 시 `FrozenInstanceError`. 기존 코드가 dead code여서 발견 안 됨 | `dataclasses.replace()` 사용으로 변경. frozen=True 클래스에는 항상 `replace()` 패턴 적용 |

---

*마지막 업데이트: 2026-03-16 14:46 KST (Antigravity — shorts-maker-v2 영상 길이 최적화 + Critical Bug Fix + QC 통과)*
