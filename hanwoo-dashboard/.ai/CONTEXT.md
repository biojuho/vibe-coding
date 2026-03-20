# AI Shared Context — hanwoo-dashboard

## 프로젝트 개요
한우 농장 관리 대시보드 (Next.js 16 + Prisma + Supabase PostgreSQL)

## 현재 스택
- Next.js 16.1.6 (App Router, Turbopack)
- React 19
- Prisma 7.4.2 (Driver Adapter: @prisma/adapter-pg)
- PostgreSQL (Supabase pooler, port 6543)
- Auth.js v5 (NextAuth.js)
- Tailwind CSS 4

## 최근 변경 (2026-03-08)
- Prisma 6 → 7 마이그레이션 진행 중
- 코드 변경 완료, 빌드 검증 미완
## 최근 변경 (2026-03-20)
- `react-hook-form`, `@hookform/resolvers`, `zod` 도입
- `src/lib/formSchemas.js`로 공통 폼 검증 스키마 분리
- `CattleForm`, `InventoryTab`, `ScheduleTab`를 RHF + Zod 기반 인라인 검증으로 전환
- `npm run build` 통과
## 최근 변경 (2026-03-20, 2차)
- `DashboardClient`의 전역 액션 피드백을 `FeedbackProvider` 기반 토스트/확인 다이얼로그로 정리
- `CalvingTab`를 RHF + Zod 기반으로 전환하고 `calvingRecordSchema` 추가
- `ExcelExportButton`까지 브라우저 기본 `alert()`를 제거해 컴포넌트 계층 피드백을 통일
- `handleAddCattle` / `handleUpdateCattle`는 후속 플로우 제어를 위해 boolean 결과와 커스텀 피드백 옵션을 지원
- `npm run build` 재통과
