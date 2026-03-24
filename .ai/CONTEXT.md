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
│   ├── HANDOFF.md                # 릴레이 핸드오프 (세션 시작 시 가장 먼저 읽을 것)
│   ├── TASKS.md                  # 칸반 보드 (TODO/IN_PROGRESS/DONE)
│   ├── TOOL_MATRIX.md            # 도구별 역량 매트릭스
│   ├── CONTEXT.md                # 마스터 컨텍스트 (이 파일)
│   ├── DECISIONS.md              # 아키텍처 결정 기록
│   ├── SESSION_LOG.md            # 세션 로그 (최근 7일)
│   └── archive/                  # 로테이션된 과거 로그
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
│   └── tests/                    # 테스트
├── shorts-maker-v2/              # YouTube Shorts 자동화
│   ├── src/shorts_maker_v2/      # 메인 패키지
│   ├── assets/                   # 미디어 자원
│   └── tests/                    # 테스트
├── knowledge-dashboard/          # 지식 대시보드 (Next.js/TS)
├── suika-game-v2/                # 수박 게임 (Matter.js)
├── word-chain/                   # 끝말잇기 게임 (React/Vite)
│
├── _archive/                     # 아카이브된 프로젝트
├── .tmp/                         # 임시 파일 (삭제 가능)
└── venv/                         # Python 가상환경
```

---

## 현재 진행 상황

> 세부 이력은 `.ai/SESSION_LOG.md`를 참조하세요.

### 완료 — 주요 마일스톤

| 시기 | 항목 |
|------|------|
| 기반 | 루트 3계층 아키텍처, MCP 10개, Skill 23개, GitHub Private Repo |
| 2026-03-11 | 시스템 고도화 v2 Phase 0~4 완료 (KPI 대시보드, YT Analytics, ROI 분석 등) |
| 2026-03-12 | MCP & Skill 확장 + QC 승인 (공식 5개 + 커스텀 5개), SQLite/Cloudinary/System Monitor |
| 2026-03-17 | shorts-maker-v2 카라오케 자막 Critical 버그 수정 + QC (382 passed) |
| 2026-03-18 | NotebookLM-py 도입 + Blind-to-X 소셜 자산 자동 연동 + Knowledge Dashboard QA/QC |
| 2026-03-20 | shorts-maker-v2 SSML 태그 누출 수정 + MiMo LLM 통합 (537 passed) |
| 2026-03-21 | Root QA gate Windows 복구 (815 passed, coverage 81%) |
| 2026-03-23 | blind-to-x main.py 모노리스 분리, shorts-maker-v2 `render_step`↔`RenderAdapter` 연동, LLM fallback/로깅 안정화 |

### 현재 진행 중

- blind-to-x: 스케줄러 자동 실행 모니터링 (S4U 전환 후 1주간)
- blind-to-x: 라이브 URL 필터 검증 + Notion 검토 큐 레거시 unsafe 1건 정리 완료. 전체 `--review-only` 배치 스모크는 사용자 승인 대기
- 시스템 QC 최신 기준(2026-03-24): `execution/qaqc_runner.py`가 **`APPROVED`** 복구. blind-to-x `534 passed, 16 skipped`, shorts-maker-v2 `776 passed, 8 skipped`, root `913 passed, 1 skipped`, 총 `2223 passed`
- `execution/qaqc_runner.py`는 이제 project-local `pytest.ini`/`pyproject`의 coverage/capture `addopts`를 `-o addopts=`로 비활성화하고, root는 `tests/`와 `execution/tests/`를 분리 실행함
- blind-to-x의 `tests/integration/test_curl_cffi.py`는 Windows 한글 경로 환경의 known CA Error 77 재현용에 가까워 system QC runner에서만 ignore 처리
- security scan 6건 triage 완료: line-level `# noqa`와 explicit triage metadata를 runner가 인식하도록 보강되어 **CLEAR**. 남은 관찰 포인트는 intermittent `test_golden_render_moviepy` 재발 여부
- 시스템 고도화 v2 Phase 5: coverage 목표 상향과 후속 문서 정리
- coverage 기준선(2026-03-23): shorts-maker-v2 54.98%, blind-to-x 51.72%; shorts targeted tests 29건 추가 후 전체 재측정 대기

### 향후 예정

- 시스템 고도화 v2 Phase 5 (고급 최적화 + 문서화)
- shorts-maker-v2: v3.0 Multi-language + SaaS 전환

### 지뢰밭 (AI 반복 실수 기록)

> AI 도구가 반복적으로 실수하는 부분을 여기에 기록합니다.

| 일자 | 도구 | 내용 | 대응 방법 |
|------|------|------|-----------|
| 2026-03-09 | Antigravity | Windows Task Scheduler 한국어 경로 XML 깨짐 | ASCII-only 경로(`C:\\btx\\`) + 환경변수 참조 |
| 2026-03-09 | Antigravity | Notion `rich_text` 2000자 제한에서 한국어도 거부 | 안전 마진 1990자로 truncate |
| 2026-03-12 | Claude Code | FastMCP 1.26 `description` kwarg 미지원 | `FastMCP("name", instructions="...")` 패턴 |
| 2026-03-12 | Antigravity | SQLite 테이블명 f-string → SQL Injection | `_validate_table_name()` 화이트리스트 |
| 2026-03-16 | Antigravity | `Path(__file__).parents[N]` depth 오계산 | 실행 위치에서 `resolve()` 검증 필수 |
| 2026-03-16 | Antigravity | frozen dataclass에 `copy.deepcopy()` → FrozenInstanceError | `dataclasses.replace()` 사용 |
| 2026-03-17 | Claude Code | WordBoundary 미수신 시 karaoke 자막 전체 불능 | `_approximate_word_timings()` fallback |
| 2026-03-17 | Claude Code | `group_into_chunks()` 반환형 tuple인데 dict 접근 | `for start, end, text in chunks` 패턴 |
| 2026-03-17 | Claude Code | SSML prosody가 TTS 발화시간 1.5배 증가 미반영 | CPS 2.8 하향 + 43초 초과시 자동 트림 |
| 2026-03-23 | Codex | Windows cp949 콘솔에서 이모지 `print()`가 `UnicodeEncodeError`를 유발 | 상태 출력은 `_safe_console_print()` 또는 logger 사용 |
| 2026-03-23 | Codex | Windows 한글 사용자 경로에서 `curl_cffi`가 CA 파일 경로를 읽지 못해 Error 77 발생 | Blind 스크래퍼는 세션 fetch 실패 시 Playwright 직접 탐색 폴백 유지 |
| 2026-03-23 | Codex | PowerShell heredoc의 한글 문자열로 Notion select 값을 직접 PATCH하면 `??` 옵션이 생성될 수 있음 | live Notion 수정은 select option ID 또는 `\\u` escape 문자열 사용 |
| 2026-03-23 | Codex | `execution/qaqc_runner.py`가 shorts `tests/legacy/`까지 수집해 legacy 실험 테스트로 QC를 깨뜨림 | shorts QC는 `tests/unit tests/integration` 경로만 대상으로 분리 |
| 2026-03-23 | Codex | root에서 `tests`와 `execution/tests`를 동시에 수집하면 동일 basename 테스트가 import mismatch를 일으킴 | root QC는 두 디렉터리를 분리 실행하거나 import mode를 조정 |
| 2026-03-23 | Codex | `tests/test_qaqc_history_db.py`가 2026-03-22 고정 타임스탬프를 써서 날짜가 지나면 `days=1` 조회가 0건이 됨 | 테스트 fixture를 상대시간 기준으로 바꿔야 안정적 |
| 2026-03-24 | Codex | `shorts-maker-v2`에서 `pytest --collect-only`만 돌려도 프로젝트 coverage 설정 때문에 실패처럼 보일 수 있음 | 수집 디버깅은 `--no-cov`를 함께 쓰거나 coverage gate를 명시적으로 끈다 |
| 2026-03-24 | Codex | system QC runner가 프로젝트별 `addopts`를 그대로 먹으면 root `.coverage` PermissionError, shorts coverage gate, Windows capture 충돌로 오탐이 커짐 | runner는 `-o addopts=`로 고정하고 필요한 인자만 명시적으로 넣는다 |

---

*마지막 업데이트: 2026-03-24 KST (Codex — security triage 반영, full QC `APPROVED` 복구)*
