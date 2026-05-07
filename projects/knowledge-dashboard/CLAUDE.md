# knowledge-dashboard 프로젝트 지침

> 이 파일은 `projects/knowledge-dashboard/` 작업 시 자동 로드됩니다.
> 전역 지침 (`../../CLAUDE.md`)과 함께 적용됩니다.
>
> | 도구 | 자동 로드 | 조치 |
> |------|----------|------|
> | Claude Code | ✅ 자동 | 없음 |
> | Gemini (Antigravity) | ❌ 수동 | 세션 시작 시 이 파일 먼저 읽기 |
> | Codex | ❌ 수동 | 세션 시작 시 이 파일 먼저 읽기 |

## 프로젝트 개요

- **목적**: 지식 관리 대시보드 — 로컬 데이터 시각화 및 인사이트 뷰어
- **스택**: Next.js 16 + React 19 + TypeScript + TailwindCSS v4 + Radix UI + Recharts
- **인증**: signed `httpOnly` session cookie (ADR-023) — `src/lib/dashboard-auth.ts`
- **핵심 경로**: `src/app/` (Next.js App Router), `src/components/`, `src/lib/`
- **데이터**: `data/` 디렉터리 (로컬 JSON/파일) — 절대 Git 커밋 금지

## 검증 커맨드

표준 검증은 워크스페이스 루트에서 `execution/project_qc_runner.py`를 사용한다.

```bash
# 워크스페이스 루트에서 실행
python execution/project_qc_runner.py --project knowledge-dashboard --json
python execution/project_qc_runner.py --project knowledge-dashboard --check test --json
python execution/project_qc_runner.py --project knowledge-dashboard --check lint --json
python execution/project_qc_runner.py --project knowledge-dashboard --check build --json
```

프로젝트 루트에서 직접 실행해야 할 때의 동일 커맨드:

```bash
# 단위 테스트 (Node test runner)
npm test
# → src/lib/dashboard-insights.test.mts 실행

# Lint
npm run lint

# 빌드 검증
npm run build

# 개발 서버
npm run dev

# Smoke 테스트 (로컬 서버 대상)
npm run smoke
# → scripts/smoke.mjs 실행 (서버 먼저 실행 필요)
```

> ⚠️ `project_qc_runner.py`는 워크스페이스 루트에서, 직접 실행 커맨드는 `projects/knowledge-dashboard/`에서 실행할 것.

## 인증 아키텍처 (ADR-023 필수)

**결정**: 브라우저 클라이언트는 `DASHBOARD_API_KEY`를 직접 사용하지 않는다.

```
브라우저 → POST /api/auth/session (API Key 교환)
         → httpOnly signed session cookie 발급
         → 이후 데이터 요청은 쿠키 기반 인증

서버 내부 / scripts / smoke → Bearer 헤더 허용 (ops 용도)
```

**금지 사항:**
- `localStorage`에 `DASHBOARD_API_KEY` 저장 금지
- 클라이언트 컴포넌트에서 직접 `DASHBOARD_API_KEY` 사용 금지
- `src/lib/dashboard-auth.ts` 바이패스 금지

## 코드 컨벤션

- **라우터**: Next.js App Router (`src/app/`) — Pages Router 사용 금지
- **컴포넌트**: `src/components/` — `"use client"` 최소화, 서버 컴포넌트 우선
- **스타일**: TailwindCSS v4 (PostCSS 방식) — inline style 지양
- **타입**: TypeScript strict 모드 — `any` 금지
- **아이콘**: `lucide-react` 단일 출처
- **UI 기본**: `@radix-ui/*` 접근성 컴포넌트 활용
- **차트**: `recharts` — 다른 차트 라이브러리 혼용 금지

## 지뢰밭 (Minefield)

- **`data/` 디렉터리**: 민감 데이터 포함 가능 — `.gitignore` 확인 필수, 절대 커밋 금지
- **Next.js 16 + React 19**: 일부 라이브러리 호환성 이슈 가능. 새 패키지 추가 시 `peerDependencies` 확인
- **TailwindCSS v4**: v3 문법(`.dark:` 등 일부 유틸리티)과 다름. 공식 v4 문서 기준으로 작성
- **`npm run smoke`**: 로컬 서버(`npm run dev`)가 먼저 실행 중이어야 함. 순서를 바꾸면 실패
- **`dashboard-auth.ts` 우회**: 인증 로직을 직접 복사하거나 미들웨어를 우회하는 PR 즉시 거부
- **Recharts + React 19**: SSR에서 `window is not defined` 오류 발생 가능 → `"use client"` 또는 dynamic import 필요

## Explore 시 반드시 읽을 파일

신규 기능 추가 전:

1. `src/app/api/` — 현재 API Route 구조 파악
2. `src/lib/dashboard-auth.ts` — 인증 헬퍼 인터페이스 확인
3. `scripts/smoke.mjs` — 연동 테스트 패턴 파악
4. `.ai/DECISIONS.md` — ADR-023 (인증), ADR-014 (레이아웃 계층) 확인

## 컴팩션 보존 컨텍스트

이 프로젝트 관련 컴팩션 발생 시 추가로 보존:

- 현재 작업 중인 API Route 또는 컴포넌트 경로
- `data/` 디렉터리의 파일 스키마 변경 여부
- smoke 테스트 마지막 통과 여부
