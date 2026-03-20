# Session Log — hanwoo-dashboard

## 2026-03-20 (Codex)

### 작업: QC 후속 수정 - 분만 원자성 + lint 복구

**작업 요약:**
- QC에서 확인된 분만 처리 부분 성공 문제를 `recordCalving()` 서버 액션으로 통합하고, 어미 상태 변경, 송아지 생성, 이력 기록을 Prisma 트랜잭션 안에서 처리하도록 수정
- 오프라인 큐도 `recordCalving`를 재생할 수 있게 연결해 온라인/오프라인 흐름이 같은 액션을 사용하도록 정리
- `next lint` 기반 스크립트를 제거하고 ESLint 9 flat config로 전환해 `npm run lint`를 복구
- lint 복구 과정에서 `admin/diagnostics`, `useTheme`, `useOnlineStatus`, 위젯 설정 초기화 로직에서 드러난 규칙 위반을 함께 정리

**변경 파일:**
- `src/lib/actions.js`
- `src/lib/syncManager.js`
- `src/components/DashboardClient.js`
- `src/components/tabs/CalvingTab.js`
- `src/app/admin/diagnostics/page.js`
- `src/lib/useTheme.js`
- `src/lib/useOnlineStatus.js`
- `package.json`
- `package-lock.json`
- `eslint.config.mjs`

**검증:**
- `npm run lint` 통과
- `npm run build` 통과

**메모:**
- `src/app/layout.js`의 Google Fonts `<link>` 때문에 lint warning 1건(`@next/next/no-page-custom-font`)은 남아 있지만, 오류는 없다
- `.eslintrc.json`은 제거되고 flat config 기반으로 관리된다

---

## 2026-03-20 (Codex)

### 작업: 전역 피드백 UX 정리 + CalvingTab RHF + Zod 전환

**작업 요약:**
- `DashboardClient`의 남은 브라우저 기본 `alert/confirm`를 `useAppFeedback()` 기반 토스트/확인 다이얼로그로 전환
- cattle CRUD, 일정/재고/급여/판매/축사 액션에 성공/실패/오프라인 토스트 추가
- `CalvingTab`를 RHF + Zod 패턴으로 재작성하고 `calvingRecordSchema` 추가
- `ExcelExportButton`의 빈 데이터 경고도 토스트로 통일
- `npm run build` 통과 확인

**변경 파일:**
- `src/components/DashboardClient.js`
- `src/components/tabs/CalvingTab.js`
- `src/lib/formSchemas.js`
- `src/components/widgets/ExcelExportButton.js`

**메모:**
- `handleAddCattle` / `handleUpdateCattle`는 이제 boolean 결과를 반환하고, 선택적 피드백 옵션을 받음
- `FeedbackProvider`는 `src/app/layout.js`에 이미 연결되어 있어 추가 설정 불필요
- `src/components` 기준 브라우저 기본 `alert()`는 제거 완료

---

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
## 2026-03-20 (Codex)

### 작업: React Hook Form + Zod 1차 도입

**작업 요약:**
- `react-hook-form`, `@hookform/resolvers`, `zod` 직접 의존성 추가
- `src/lib/formSchemas.js` 신규 생성
- `CattleForm`, `InventoryTab`, `ScheduleTab`를 RHF + Zod 기반으로 전환
- 필드별 인라인 에러 메시지 추가
- `npm run build` 통과 확인

**변경 파일:**
- `package.json`
- `package-lock.json`
- `src/lib/formSchemas.js`
- `src/components/forms/CattleForm.js`
- `src/components/tabs/InventoryTab.js`
- `src/components/tabs/ScheduleTab.js`

**메모:**
- 의존성 설치 시 `--legacy-peer-deps` 필요
- 다음 확장 후보: `SalesTab`, `FeedTab`, `SettingsTab`

---
