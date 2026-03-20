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
