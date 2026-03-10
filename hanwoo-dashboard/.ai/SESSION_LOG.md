# Session Log — hanwoo-dashboard

## 2026-03-08 (Antigravity/Gemini)

### 작업: Prisma 6 → 7 마이그레이션

**작업 요약:**
- Prisma 6.19.2 → 7.4.2 업그레이드
- `@prisma/adapter-pg` 드라이버 어댑터 도입
- `schema.prisma`: `prisma-client` provider + output 경로 + `url` 제거
- `db.js`: `PrismaPg` 어댑터 패턴으로 전면 재작성
- `prisma generate` 성공 (`src/generated/prisma/` 생성)

**변경 파일:**
- `package.json`
- `prisma/schema.prisma`
- `src/lib/db.js`
- `src/generated/prisma/` (자동 생성)

**트러블슈팅:**
- `--legacy-peer-deps` 필요 (eslint-config-next peer dep 충돌)
- Prisma 7에서 `datasource.url` 제거 필수
- import 경로: `@/generated/prisma/client` (not `@/generated/prisma`)

**미완료:**
- `npm run build` 빌드 검증 (시간 초과로 중단)
- `npm run dev` 기능 테스트

**다음 도구에게 메모:**
- 빌드 실행 시 `--legacy-peer-deps` 플래그 기억
- SSL 설정: `rejectUnauthorized: false` (Supabase pooler 필수)
- `.gitignore`에 `src/generated/` 추가 검토 필요
