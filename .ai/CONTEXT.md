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
- **MCP 서버**: Supabase, Firebase, Notion
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
│   ├── skills/                   # 28종 커스텀 스킬
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

### 🔄 진행 중
- shorts-maker-v2: 영상 품질 최적화 (Phase 2 기술 업그레이드)
- 5채널 토픽 자동 생성 및 트렌딩 주제 갱신

### 📋 예정
- (사용자가 결정)

### ⚠️ 알려진 이슈
- (발견 시 기록)

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

---

*마지막 업데이트: 2026-03-08 KST (Gemini/Antigravity)*
