# hanwoo-dashboard 적대적 비판 & 해결 리포트 (2026-06-12)

8개 렌즈(보안/인증, 정확성, 데이터 무결성, 테스트 품질, 아키텍처, 성능, UX, 운영)로
적대적 멀티에이전트 감사를 수행하고, 각 발견을 독립 검증한 뒤 안전하게 고칠 수 있는
항목을 실제로 수정했습니다. 검증 단계가 세션 한도에 걸려 일부는 자체 코드 정독으로
재검증했습니다.

- **원시 발견**: 53건 (8개 렌즈)
- **검증/자체검증으로 실재 확인**: 23건+ (1건은 검증기에서 기각: auth-guard infra 에러 → 의도된 설계)
- **이번에 수정**: 17개 항목 (아래 ✅)
- **DBA/마이그레이션 게이트 필요로 문서화만**: 3개 항목 (아래 ⏭)
- **검증 게이트**: `npm test` 541 pass / 0 fail, `npm run lint` clean, `npm run build` 통과

> 진단 도구로 **베이스라인 자체가 거짓 그린**이었음을 발견: `node_modules`가 깨져
> (`bullmq`/`@next` swc 누락) `npm test`가 502 pass **4 fail**, `eslint`가 실행 불가였습니다.
> `rm -rf node_modules && npm ci`로 복구하니 539 pass가 됐고, 그 위에서 작업했습니다.
> 이 프로젝트의 메모리(`hanwoo_biome_test_regression`)가 경고한 "그린을 신뢰하지 말 것"
> 패턴의 또 다른 사례입니다.

---

## ✅ 수정 완료 (17)

### CRITICAL — 돈 손실

**1. 결제 승인 재시도가 성공한 결제를 FAILED로 뒤집음** · `src/app/api/payments/confirm/route.js`, `src/lib/payment-confirmation.mjs`
- **트리거**: Toss 승인은 됐지만 응답이 유실(15s timeout/5xx) → 라우트가 202 pending 반환 →
  클라이언트가 설계대로 재시도 → Toss가 `400 ALREADY_PROCESSED_PAYMENT` 응답 →
  기존 코드는 모든 4xx를 terminal `failed`로 분류 → `markPaymentLogFailed`가 DONE을
  FAILED로 덮어쓰고 구독 활성화 트랜잭션은 실행 안 됨. **결제는 됐는데 구독 없음.**
- **해결**: ① 승인 전 `findUnique`로 DONE이면 멱등 `{success:true}` 즉시 반환 ②
  `ALREADY_PROCESSED_PAYMENT`는 새 `already_processed` 종류로 분류 → Toss
  `GET /v1/payments/{key}`로 재조회해 orderId/amount/status=DONE 확인 후 동일 성공
  트랜잭션 실행, 조회 실패 시 FAILED 아님 pending(재시도 가능) ③ `markPaymentLogFailed`를
  `updateMany({where:{orderId, status:{not:"DONE"}}})`로 바꿔 **DONE은 절대 강등 안 함**.
- 성공 트랜잭션을 `persistConfirmedPayment` 헬퍼로 추출해 정상/재조회 경로가 동일 멱등 상태 생성.
- 회귀 테스트 2건 추가(`already_processed` 분류 + 다른 4xx는 여전히 failed).

### HIGH — 정확성 / 데이터 무결성 / UX

**2. 수익성 위젯이 출시 이래 죽어 있었음** · `src/lib/dashboard/profitability-service.js`
- 쿼리가 `where: { status: "ACTIVE" }`인데 앱은 status를 한국어
  (`송아지/육성우/번식우/임신우/비육우/씨수소`)로만 저장 → **항상 0행** →
  default-on 위젯("출하 수익성 예측")이 영구 빈 화면. 게다가 가격 산정이
  `cattle.gender === "FEMALE"`인데 실제 저장값은 `"암"/"수"` → **모든 암소를 수소 시세로 계산.**
- **해결**: 불가능한 status 필터 제거 + `salesRecords: { none: {} }`로 미판매 개체만 후보화
  (24개월 게이트는 유지), gender 비교를 `"암"`으로 수정.

**3. 서버 액션이 트랜잭션 없이 row→history→outbox 순차 기록** · `src/lib/actions/{cattle,sales,expense}.js`, `_helpers.js`
- row가 커밋된 뒤 outbox insert가 실패(커넥션 드롭/풀 고갈)하면 catch가 `{success:false}`
  반환 → 사용자는 "실패"로 알지만 row는 존재. 재시도 시 `createSalesRecord`/
  `createExpenseRecord`는 unique 제약이 없어 **중복 판매/비용 레코드** 생성.
- **해결**: `createCattle/updateCattle/recordCalving/deleteCattle/createSalesRecord/
  createExpenseRecord`를 `prisma.$transaction`으로 감싸고 `recordCattleHistory`·
  `createOutboxEvent`에 `tx` 전달(둘 다 이미 client 파라미터 지원). 캐시 무효화는 트랜잭션 밖 유지.

**4. dead-letter 오프라인 쓰기가 조용히 사라짐 + 잘못된 토스트** · `src/components/DashboardClient.js`
- 3회 재시도(혹은 즉시 영구실패 패턴) 실패 시 쓰기가 `joolife-offline-dead-letter`로
  이동하지만 이를 읽는 UI가 없음. 토스트는 `failed`에 dead-letter를 합산해 "다시 시도해
  주세요"라 안내하지만 자동 재시도 경로가 없음. 게다가 전부 실패하면 무피드백.
- **해결**: 토스트를 transient(`failed - deadLettered`, 자동 재시도)와 dead-letter
  ("자동 재시도가 중단되었습니다. 설정 > 동기화에서 확인해 주세요")로 분리하고, 동기화
  실패가 0건 동기화여도 피드백을 표시(무피드백 침묵 제거).

**5. /api/health가 프로덕션에서 raw DB 에러를 익명 노출 + 서버 로깅은 끔** · `src/app/api/health/route.js`
- 가드가 역전: 프로덕션에서 **운영자에겐 로그 없음**, 익명 클라이언트에겐 Prisma/pg
  raw 에러(호스트/리전/인증 문자열) 노출.
- **해결**: 항상 `console.error`로 서버 로깅하고, 프로덕션 응답 body는 일반 메시지로
  폴백(`warning: isProductionLike ? undefined : error`).

**6. KST 날짜가 하루 밀림 (달력 + 폼 기본값)** · `src/lib/utils.js`, `src/components/tabs/ScheduleTab.js`
- `toInputDate`/달력 셀 키가 `toISOString()`(UTC) 사용 → KST 00:00–08:59에 "오늘"이
  어제로, 달력 셀이 하루 전 키로 렌더되어 일정이 잘못된 칸에 표시되고 셀 클릭 시
  전날로 prefill.
- **해결**: `toLocalInputDate`(로컬 연/월/일) 도입, `toInputDate`·`ScheduleTab.toDateKey`·
  "오늘" 하이라이트를 로컬 키로 통일. UTC-자정 저장값은 KST에서 동일 문자열이라 무영향.
  소스-grep 테스트 1건을 수정된 동작에 맞게 갱신.

### MEDIUM — 운영/보안/리질리언스/UX

**7. 보안 헤더 전무** · `next.config.mjs`
- 결제 처리 SaaS인데 클릭재킹/HSTS/스니핑 보호 없음.
- **해결**: 전 경로에 `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`,
  `Referrer-Policy`, `Strict-Transport-Security`, `Permissions-Policy` 추가.
  (CSP는 인라인 스타일/Toss 위젯 때문에 잘못 적용 시 결제 깨짐 → 별도 경로별 작업으로 명시.)

**8. Dockerfile이 빌드 불가** · `Dockerfile`, `next.config.mjs`
- `.next/standalone`을 COPY하는데 `output: "standalone"` 미설정 → COPY 단계 실패.
  node:20 vs `engines >=22` 불일치.
- **해결**: `output: "standalone"` 추가, 3개 FROM을 node:22-alpine로.

**9. DB TLS 검증 비활성(하드코딩) — MITM 위험** · `src/lib/db.js`, `scripts/outbox-worker.mjs`
- `rejectUnauthorized: false` 무조건 적용 → 농장 데이터/비번 해시/결제 로그 운반 연결이
  암호화됐지만 인증 안 됨.
- **해결**: `buildDbSslConfig`로 `DB_SSL_CA`/`DB_SSL_REJECT_UNAUTHORIZED` env 기반 설정화
  (기존 배포 호환 위해 기본값은 유지, 프로덕션에서 켤 수 있는 안전 경로 제공 + `.env.example` 문서화).

**10. outbox 워커: 크래시 시 PROCESSING 영구 잔류 + 비원자적 claim** · `scripts/outbox-worker.mjs`
- PENDING만 폴링, PROCESSING 재큐 코드 없음 → 크래시 시 영구 유실. SELECT-then-UPDATE가
  비원자적이라 두 워커(daemon+cron)가 같은 이벤트 중복 처리/attempts 이중 증가.
- **해결**: 폴 시작 시 5분 초과 PROCESSING을 PENDING으로 reap, 이벤트당
  `updateMany({where:{id,status:"PENDING"}})` 원자적 claim(count===0이면 skip).

**11. AI 채팅 스트림 타임아웃 없음 (클라+서버)** · `src/components/widgets/AIChatWidget.js`, `src/lib/ai-chat-api.mjs`
- Gemini가 스트림 중 멈추면 위젯은 "답변 생성 중"으로 입력 잠긴 채 영구 대기, 서버는
  커넥션 보유.
- **해결**: 클라에 청크마다 리셋되는 30s idle 워치독(만료 시 `reader.cancel()` →
  연결 에러 폴백으로 입력 재활성), 서버 SSE에 청크별 idle 레이스 deadline(만료 시 에러
  프레임 후 close, sync/async iterable 모두 지원). 서버 타임아웃 회귀 테스트 추가.

**12. 결제 확인 네트워크 실패 = 막다른 길** · `src/app/subscription/success/page.js`
- 결제 직후 confirm 호출이 timeout/네트워크 에러면 정적 메시지만 표시, 재시도/버튼 없음.
- **해결**: catch 경로도 bounded 재시도 루프에 포함, 재시도 소진 시 "결제 다시 확인하기"
  버튼(멱등 confirm 재실행 — fix #1 덕분에 안전)으로 재확인 가능.

**13. 미래 날짜/비현실적 체중 통과** · `src/lib/formSchemas.js`, `src/lib/action-validation.mjs`
- 생년월일/출하일/분만일에 상한 없음(2027 오타 통과 → getMonthAge가 1개월로 가려 데이터
  오염), 체중 상한 없음(4500kg 오타).
- **해결**: 클라(로컬 달력일 비교)·서버(1일 TZ skew 허용) 양쪽에 미래일 거부 추가,
  체중 max 2000kg(한우 ~1100kg). 샘플 테스트는 모두 과거/2000 미만이라 무영향.

**14. Redis 캐시 fail-closed → dashboard 전체 가용성 위험** · `src/lib/dashboard/cache.js`
- `getCachedJson`/`setCachedJson`/`deleteCached*`에 try/catch 없음 → Redis가 설정됐는데
  다운되면 `redis.get` reject가 read-models를 거쳐 summary/cattle/sales API를 전부 500.
  **Redis 장애 = 대시보드 전체 다운.**
- **해결**: 네 helper 모두 fail-OPEN으로 변경 — read 에러는 캐시 미스(→DB 직접),
  write/무효화 에러는 best-effort(로그 후 진행, stale은 TTL로 소멸). Redis 장애가
  "캐시 없음"으로 degrade될 뿐 요청은 계속 처리.

### 정리(LOW)

**15. 죽은 bullmq 큐 인프라 제거** · `src/lib/queue.js`(삭제), `package.json`
- `queue.js`(bullmq 래퍼)는 자기 테스트 외 importer 0. 무거운 `bullmq` 의존성이 프로덕션
  의존성으로 잔류.
- **해결**: `queue.js`/`queue.test.mjs` 삭제, `package.json`에서 `bullmq` 제거, lockfile 동기화.
  (`ioredis`는 `redis.js`가 직접 쓰므로 유지.) 부수적으로
  `redis-env-wrapper-async-restore-footgun` 발견도 해소.

> #7~#13의 검증기 정제 의견(예: 모듈 레벨 `endOfToday` 캐시 staleness 회피, AIChat
> `requestOptions` 위치 인자, Toss 식별자 재검증 등)을 구현에 반영했습니다.

---

## ⏭ DBA/마이그레이션 게이트 — 적용 보류, 문서화 (3)

공유 프로덕션 DB에 블라인드로 적용하면 파괴적일 수 있어 **의도적으로 보류**합니다.
정확한 변경안을 남깁니다.

**A. 마이그레이션 시스템 사망 — `db:push`가 핫 인덱스를 드롭할 위험** (실재 confirmed)
- `migration_lock.toml`은 `provider=sqlite`인데 datasource는 postgresql → 모든
  `prisma migrate`가 provider-switch 에러로 실패 → `db:push`만 동기화 경로.
- 프로덕션 핵심 인덱스 10개가 `prisma/manual/*.sql`에만 존재(부분 인덱스 `where
  isArchived=false` 포함 — Prisma 스키마로 표현 불가). `db push`는 이들을 인지 못해
  드롭하거나, 같은 컬럼에 Prisma 이름의 중복 인덱스를 만들 수 있음.
- **권장(라이브 DB 필요)**: sqlite 마이그레이션/lock 삭제 → `prisma migrate diff
  --from-empty --to-schema-datamodel`로 Postgres init 생성 → `prisma/manual/*.sql` 병합 →
  `prisma migrate resolve --applied`로 프로덕션 baseline → `db:migrate: prisma migrate
  deploy` 추가, `db:push` 사용 중단. 비부분 인덱스는 schema.prisma에 `@@index([...(sort:
  Desc)])`로 선언하되 **기존 수동 인덱스명과 충돌 점검 후** 적용.

**B. Subscription.userId에 FK/unique/index 없음** (실재 confirmed, low)
- per-user 유일성이 `customerKey = user_${id}` 관례에만 의존. 직접 쓰기/유저 삭제 시
  고아·중복 구독 가능.
- **권장**: `userId String @unique` + `@relation(onDelete: Restrict)` + User 역관계.
  단 `String?` → `String` 전환은 기존 null 행 백필이 선행돼야 하므로 마이그레이션으로.

**C. 죽은 추출 훅 3종 (useWeather/useOfflineSyncQueue/useCursorPagination)** (실재 confirmed)
- importer 0이지만 라이브 인라인 코드(DashboardClient)와 드리프트. **각 훅의 소스-grep
  테스트가 그 훅 파일을 직접 읽음** → 단순 삭제 시 카피 회귀 커버리지 손실.
- 런타임 비용은 0(트리셰이킹). **권장**: 인라인 코드로 테스트를 재타겟하는 전용 PR에서
  훅+테스트를 함께 정리(이번엔 커버리지 손실 위험으로 보류).

---

## 기각 (검증기 판단)

- `auth-guard-swallows-infra-errors-unlogged`: 인증 누락 인프라 에러를 401로 변환하는 것은
  의도된 폴백 설계(ADR-022 정합)로 판단되어 not-an-issue.

---

## 검증 증거

```
npm test   → tests 541, pass 541, fail 0   (베이스라인 깨진 node_modules 복구 후)
npm run lint → eslint . clean (exit 0)
npm run build → 통과 (standalone + 보안 헤더 포함)
```

변경 파일(25 M / 2 D): payments/confirm, payment-confirmation(.mjs/.test), profitability-service,
actions/{cattle,sales,expense,_helpers}, DashboardClient, ScheduleTab, utils(.js/-date.test),
AIChatWidget, ai-chat-api(.mjs/.test), action-validation, formSchemas, health/route,
next.config, Dockerfile, db, outbox-worker, subscription/success/page, .env.example,
package.json/lock; 삭제 queue.js/queue.test.mjs.
