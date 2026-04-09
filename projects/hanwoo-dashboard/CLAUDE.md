# hanwoo-dashboard 프로젝트 지침

> 이 파일은 `projects/hanwoo-dashboard/` 작업 시 자동 로드됩니다.
> 전역 지침 (`../../CLAUDE.md`)과 함께 적용됩니다.
>
> | 도구 | 자동 로드 | 조치 |
> |------|----------|------|
> | Claude Code | ✅ 자동 | 없음 |
> | Gemini (Antigravity) | ❌ 수동 | 세션 시작 시 이 파일 먼저 읽기 |
> | Codex | ❌ 수동 | 세션 시작 시 이 파일 먼저 읽기 |

## 프로젝트 개요

- **목적**: 한우 농가 관리 대시보드 (SaaS)
- **스택**: Next.js 15, React, Prisma, Auth.js (v5 beta), TailwindCSS v4, Supabase
- **핵심 파일**: `src/app/`, `src/lib/`, `src/components/`

## 검증 커맨드

```bash
# Lint
npm run lint

# 단위 테스트
npm test

# 빌드 검증 (배포 전에만)
npm run build

# 특정 테스트 파일
npx jest src/__tests__/<filename>.test.js
```

> ⚠️ 모든 커맨드는 `projects/hanwoo-dashboard/` 에서 실행할 것.

## 코드 컨벤션

- **모듈 시스템**: ESM (`import/export`), CommonJS(`require`) 금지
- **Node 단위 테스트**: `.mjs` 확장자 사용 (패키지 `"type": "module"` 없음)
- **Server Actions**: `src/lib/actions.js` — 반드시 서버사이드 인증 거침
- **API 라우트**: `src/app/api/` — `requireAuthenticatedSession()` 필수 (ADR-022)
- **한국어 문자열**: 수정 최소화, 인코딩 문제 주의

## 지뢰밭 (Minefield)

- **Auth.js v5 beta**: 세션 쿠키 형식이 v4와 다름. `getServerSession()` → `auth()` 함수 사용
- **페이지네이션 가드**: `src/lib/dashboard/pagination-guard.mjs` — 반복 커서/무한 루프 방지. 직접 루프 구현 금지
- **offlineQueue**: `src/lib/offlineQueue.js` — 재시도 메타데이터 포함, `deadLetter` 키 유지
- **syncManager**: 오프라인 큐 최대 재시도 횟수 초과 시 `joolife-offline-dead-letter` 로 이동
- **한국어 문자열**: 편집 시 인코딩 오염(`?곹깭` 같은 깨짐) 주의 — 가능하면 수정 최소화
- **결제 플로우**: 서버 발급 주문 + 트랜잭션 확인 패턴 유지 (ADR-022)
- **TailwindCSS v4**: v3 문법(`@apply`, `theme()`) 사용 금지

## Explore 시 반드시 읽을 파일

신규 기능 추가 전:

1. `src/lib/actions.js` — 서버 액션 패턴
2. `src/lib/dashboard/pagination-guard.mjs` — 페이지네이션 안전장치
3. `src/app/api/auth/` — 인증 플로우
4. `.ai/DECISIONS.md` — ADR-022, ADR-024 확인

## 컴팩션 보존 컨텍스트

이 프로젝트 관련 컴팩션 발생 시 추가로 보존:

- 마지막 `npm test` 결과 (통과/실패 수)
- 수정 중인 서버 액션 또는 API 라우트
- Auth.js 세션 관련 작업 상태
