# Architecture Decisions — hanwoo-dashboard

## ADR-001: Prisma 7 Driver Adapter Pattern (2026-03-08)

**결정:** Prisma 7 마이그레이션 시 `@prisma/adapter-pg` + `PrismaPg` 사용

**이유:**
- Prisma 7부터 Driver Adapter 필수
- Rust 쿼리 엔진 제거 → 더 가벼운 번들
- Supabase pooler와 직접 연결

**구현:**
- `db.js`에서 `PrismaPg({ connectionString, ssl })` 으로 연결
- `schema.prisma`에서 `prisma-client` provider + custom output path
- 환경변수는 `prisma.config.ts`에서 관리

**제약:**
- `--legacy-peer-deps` 필요 (eslint-config-next 호환성)
- Supabase pooler는 `ssl: { rejectUnauthorized: false }` 필수
