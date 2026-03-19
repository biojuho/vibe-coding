# 🏗️ Vibe Coding 프로젝트 규칙

> 이 파일은 매 세션마다 자동으로 로드되는 패시브 가이드라인입니다.

## 프로젝트 개요

- **워크스페이스**: Vibe Coding (다중 서브프로젝트 통합 환경)
- **주요 프로젝트**: shorts-maker-v2, hanwoo-dashboard, blind-to-x, knowledge-dashboard, word-chain, suika-game-v2
- **OS**: Windows 11
- **에이전트 아키텍처**: 3계층 (Directive → Orchestration → Execution)

## 기술 스택

| 영역 | 기술 |
|------|------|
| 프론트엔드 | React / Next.js + TypeScript/JavaScript |
| 스타일링 | Tailwind CSS (프로젝트별 상이할 수 있음) |
| 백엔드/DB | Supabase, Python 3.10+ |
| 자동화 | Batch scripts (.bat), Python scripts |
| AI/LLM | Gemini, Edge TTS |

## 폴더 구조 규칙

```
Vibe coding/                    # 워크스페이스 루트
├── .agents/                    # 에이전트 설정
│   ├── rules/                  # 패시브 가이드라인 (이 파일)
│   ├── skills/                 # 커스텀 스킬 (44+)
│   └── workflows/              # 워크플로우 정의
├── directives/                 # SOP (표준운영절차)
├── execution/                  # 결정론적 Python 스크립트
├── .tmp/                       # 임시 파일 (절대 커밋 금지)
│
├── hanwoo-dashboard/           # 한우 시세 대시보드 (Next.js)
├── shorts-maker-v2/            # YouTube Shorts 자동 생성 (Python)
├── blind-to-x/                 # 블라인드 스크래퍼 (Python)
├── knowledge-dashboard/        # 지식 대시보드 (Next.js)
├── suika-game-v2/              # 수박 게임 (Vite + React)
├── word-chain/                 # 끝말잇기 게임 (Vite + React)
│
├── _archive/                   # 더 이상 활성화되지 않은 프로젝트
├── infrastructure/             # MCP 서버 등 공통 인프라
├── tests/                      # 통합/단위 테스트
└── scripts/                    # 유틸리티 스크립트
```

## 코딩 컨벤션

### 공통
- **UTF-8 인코딩** 필수 (Windows: `chcp 65001`)
- **환경변수**: `.env` 파일에 관리, 절대 하드코딩 금지
- **비밀 값**: `YOUR_PASSWORD`, `secret` 등의 플레이스홀더 잔존 금지
- **로그/임시파일**: `.tmp/` 또는 `logs/`에 저장, 프로젝트 루트 오염 금지

### JavaScript/TypeScript (프론트엔드)
- **함수형 컴포넌트** 사용 (Class 컴포넌트 금지)
- **파일 하나에 컴포넌트 하나** 원칙
- **컴포넌트 파일명**: PascalCase (예: `TodoItem.tsx`)
- **훅 파일명**: `use-` 접두사 + camelCase (예: `useAuth.ts`)
- **서비스 파일명**: camelCase (예: `apiClient.ts`)

### Python (백엔드/자동화)
- **snake_case** 파일명 및 함수명
- **타입 힌트** 가능한 한 사용
- **Linter**: `ruff` 사용 (`ruff.toml` 참고)
- **테스트**: `pytest` 프레임워크

## 🔄 자동 세션 관리 (필수 자동 실행)

> **중요**: 아래 행동들은 사용자가 별도로 요청하지 않아도 **에이전트가 자동으로** 수행해야 합니다.

### 세션 시작 시 (자동)
사용자가 첫 메시지를 보내면, 작업 요청에 응답하기 **전에** 반드시:
1. Knowledge Base에서 관련 KI를 확인하여 이전 작업 히스토리를 파악한다
2. 최근 대화 이력에서 미완성 TODO나 알려진 버그를 식별한다
3. 사용자에게 간단히 현재 상태를 보고한 뒤 작업에 착수한다

### 세션 종료 시 (자동)
사용자가 "마무리", "끝", "종료", "오늘은 여기까지" 등의 신호를 보내면 자동으로:
1. 이번 세션에서 변경된 파일 목록과 변경 이유를 정리한다
2. 미완성 작업이나 발견된 버그를 목록화한다
3. 다음 세션에서 이어할 TODO 항목을 작성한다
4. 위 내용을 Knowledge Base에 저장한다

### 작업 중 (상시)
- 이 Rules의 폴더 구조와 코딩 컨벤션을 **반드시** 따를 것
- 새 파일/기능 개발 시 **반드시** 4단계 QA/QC 워크플로우(`/qa-qc` 또는 `directives/qa_qc_workflow.md`)를 거친 후 커밋할 것
- 새 파일 생성 시 반드시 위 폴더 구조에 맞는 위치에 생성할 것
- 반복 작업은 `directives/` 폴더의 SOP를 우선 확인한 뒤 수행할 것
- 스크립트 작성 전 `execution/` 폴더에서 기존 도구를 먼저 확인할 것

## 3계층 아키텍처 준수

| 계층 | 역할 | 위치 |
|------|------|------|
| 1계층 - 지침 | 무엇을 할지 정의 | `directives/*.md` |
| 2계층 - 오케스트레이션 | 의사결정 및 라우팅 | 에이전트 (AI) |
| 3계층 - 실행 | 결정론적 작업 수행 | `execution/*.py` |

> ⚠️ 스크립트 작성 전 반드시 `execution/` 폴더에서 기존 도구를 먼저 확인하세요.

---

## 🚀 gstack 스프린트 구조 (공식 채택)

> **출처:** [garrytan/gstack](https://github.com/garrytan/gstack) 철학 선별 도입 (2026-03-19)

모든 기능 개발은 아래 순서를 따른다:

```
Think → Plan → Build → Review → Test → Ship → Reflect
```

| 단계 | 워크플로우 | 설명 |
|------|-----------|------|
| Think | `/office-hours` | 기능 개발 전 6가지 강제 질문으로 방향 재정의 |
| Plan | Implementation Plan | 아키텍처, 엣지 케이스, 테스트 계획 수립 |
| Build | `/qa-qc` STEP 1 | 코드 작성 + 유닛 테스트 |
| Review | `/qa-qc` STEP 2 | 보안/기능/품질 자동 검토 |
| Test | `/qa-qc` STEP 3 | 수정 + **회귀 테스트 필수 작성** |
| Ship | git commit + push | QC 승인 후 커밋 |
| Reflect | `/retro` (주 1회) | 주간 회고 및 기술 부채 파악 |

### 강제 규칙

- **새 기능 개발 시** `/office-hours` 먼저 실행할 것을 **강력 권고**
  (긴급 버그 수정, 1시간 이내 단순 작업은 생략 가능)
- **버그 발생 시** `/debug` 워크플로우 사용 (Iron Law: 조사 없이 수정 금지)
- **버그 수정 시** 회귀 테스트 의무 작성 (1 fix = 1 regression test)
- **주 1회** `/retro` 실행 권장
