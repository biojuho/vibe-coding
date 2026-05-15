# Joolife Dashboard (쥬라프 대시보드)

## 🐮 🇬🇧 Premium Hanwoo Farm Management System / 🇰🇷 프리미엄 한우 농장 관리 시스템

🇬🇧 **Joolife** is an all-in-one management dashboard for modern Hanwoo (Korean Native Cattle) farms.
It provides an optimized experience for both PC and mobile (PWA) environments.
🇰🇷 **Joolife(쥬라프)**는 현대적인 한우 농장을 위한 올인원 관리 대시보드입니다.
PC와 모바일(PWA) 환경 모두에서 최적화된 경험을 제공합니다.

### ✨ Key Features (주요 기능)

1.  **📊 🇬🇧 Farm Status Dashboard / 🇰🇷 농장 현황 대시보드**
    *   🇬🇧 Provides real-time head count, shipment status, and weather information. / 🇰🇷 실시간 사육 두수, 출하 현황, 날씨 정보 제공
    *   🇬🇧 Visualizes cattle placement status by barn and pen. / 🇰🇷 축사 및 칸별 소 배치 현황 시각화

2.  **💰 🇬🇧 Real-time Market Price Widget / 🇰🇷 실시간 시세 위젯**
    *   🇬🇧 Real-time sync with national wholesale market Hanwoo auction prices (KAPE API). / 🇰🇷 전국 도매시장 한우 경락 가격 실시간 연동 (축산물품질평가원 API)
    *   🇬🇧 Check average price and fluctuation trends by grade (1++, 1+, 1). / 🇰🇷 등급별(1++, 1+, 1) 평균 가격 및 변동 추이 확인

3.  **🔔 🇬🇧 Smart Notification System / 🇰🇷 스마트 알림 시스템**
    *   **🇬🇧 Heat Notification / 🇰🇷 발정 알림**: 🇬🇧 Automatically calculates estrus dates and provides D-Day alerts. / 🇰🇷 예상 발정일 자동 계산 및 D-Day 알림
    *   **🇬🇧 Calving Notification / 🇰🇷 분만 알림**: 🇬🇧 Urgent alerts for impending calving dates (D-5). / 🇰🇷 임신우 분만 예정일 임박(D-5) 긴급 알림

4.  **📈 🇬🇧 Financial Analysis / 🇰🇷 경영 분석**
    *   🇬🇧 Monthly revenue/expense/net profit trend charts. / 🇰🇷 월별 매출/비용/순이익 트렌드 차트
    *   🇬🇧 Cost structure analysis (feed costs, medicine costs, etc.). / 🇰🇷 비용 구조 분석 (사료비, 약품비 등)
    *   🇬🇧 Top revenue generating cattle (Super Cow) rankings. / 🇰🇷 최고 매출우(Super Cow) 랭킹

5.  **📱 🇬🇧 Mobile App (PWA) / 🇰🇷 모바일 앱**
    *   🇬🇧 Install the app directly to the home screen without an App Store/Play Store. / 🇰🇷 앱스토어/플레이스토어 없이 홈 화면에 앱 설치 가능
    *   🇬🇧 Provides a full-screen experience identical to native apps. / 🇰🇷 네이티브 앱과 동일한 풀스크린 경험 제공

### 🚀 Getting Started (시작하기)

#### 1. 🇬🇧 Installation and Execution / 🇰🇷 설치 및 실행
```bash
# 🇬🇧 Install dependencies / 🇰🇷 의존성 설치
npm install

# 🇬🇧 Start development server / 🇰🇷 개발 서버 실행
npm run dev
# 🇬🇧 Access http://localhost:3001 / 🇰🇷 http://localhost:3001 접속
```

#### 2. 🇬🇧 Production Build / 🇰🇷 프로덕션 빌드
```bash
npm run build
npm start
```

### 📲 🇬🇧 Mobile Installation Guide (PWA) / 🇰🇷 모바일 설치 방법

1.  🇬🇧 Access via mobile Chrome or Safari. / 🇰🇷 모바일 크롬(Chrome) 또는 사파리(Safari)로 접속합니다.
2.  🇬🇧 Press the **Share button** (iOS) or **Menu button** (Android). / 🇰🇷 **공유 버튼** (iOS) 또는 **메뉴 버튼** (Android)을 누릅니다.
3.  🇬🇧 Select **'Add to Home Screen'**. / 🇰🇷 **'홈 화면에 추가'**를 선택합니다.
4.  🇬🇧 You can now access it via the home screen icon like a regular app. / 🇰🇷 이제 앱처럼 아이콘을 통해 접속할 수 있습니다.

---

### 🛠 Tech Stack (기술 스택)

*   **Framework**: Next.js 16 (App Router, Proxy)
*   **Runtime UI**: React 19
*   **Language**: JavaScript with TypeScript available for typed helpers/tests
*   **Database**: PostgreSQL/Supabase-compatible URLs via Prisma ORM + `@prisma/adapter-pg`
*   **Auth**: Auth.js / `next-auth` v5 beta
*   **Cache / Queue**: Redis + BullMQ for scale-hardening paths
*   **HTTP Client**: native Fetch API wrapped by local helpers such as `src/lib/fetchWithTimeout.js`
*   **Styling**: Tailwind CSS v4 + app-level CSS variables
*   **Charts**: Recharts

Not installed here by default: Svelte, TanStack Query, RabbitMQ, Go, Rust, Flutter, or native mobile runtimes. Treat them as candidate-only technologies and document a migration/design note before adoption.

### Backend API Contract

The local API contract lives in [`API_SPEC.md`](./API_SPEC.md). API routes under `src/app/api/` should use the documented response envelope, validate request input before touching external providers, and require `requireAuthenticatedSession()` unless an endpoint is explicitly public.

### Scale-Hardening Infra

```bash
# Optional Redis-backed cache and BullMQ queue
REDIS_URL=redis://127.0.0.1:6379

# Optional BullMQ prefix override
BULLMQ_PREFIX=hd:jobs
```

- Local development still works without Redis.
- Once the real pooled Postgres URL is configured, run `npm run db:verify-indexes` to capture the live index inventory and `EXPLAIN` plans.

---

**Copyright © 2026 Joolife.**
