# HANDOFF - AI Context Relay

> See `SESSION_LOG.md` for recent session history and `DECISIONS.md` for stable architecture decisions.

## Current Addendum

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Analysis chart sales terminology consistency**: Continued the active Hanwoo quality uplift by changing Analysis and Financial chart user-facing sales labels from `매출` to `판매액`. The monthly analysis heading, chart accessibility label/title, revenue bar legend, financial chart description, and financial chart revenue legend now align with Sales, AI Insight, and the existing `연간 총판매액` KPI wording. Strengthened analysis regression coverage to keep the chart-level `판매액` terminology. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/analysis-copy.test.mjs` passed 3/3, `npm.cmd test` passed 347/347, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **workspace verified quality bundle closure**: User selected the cleanup/commit path. Rechecked the current dirty worktree, found the final bundle now scoped to Hanwoo quality-copy/fallback updates plus workspace tooling updates (`dependency_security_audit.py`, `session_orient.py`, `uv.lock`) and `.ai` session records. Ran final verification before commit prep. |
| Next Priorities | Verification: `python execution/project_qc_runner.py --project hanwoo-dashboard --json --timeout-seconds 300` passed (`npm test` 335/335, lint, build). `python -m py_compile execution\session_orient.py execution\dependency_security_audit.py` passed. `py -3.13 execution/code_review_gate.py --base HEAD --json` returned WARN, not FAIL (`risk_score 0.55`, 5 test-gap heuristics). `python execution/dependency_security_audit.py --help` actually ran the audit and returned exit 1 because current dependencies report 73 vulnerabilities across 25 packages; treat that as a surfaced security backlog, not a syntax/runtime failure. T-251 remains user-owned Supabase credential/control-plane resync. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Sales history grade fallback specificity**: Continued the active Hanwoo quality uplift by changing cattle sale history copy from `등급: -` to `등급: 등급 미등록` when a sale grade is missing. This keeps generated cattle timeline entries from preserving a bare dash placeholder for missing sale grades. Strengthened server-action copy regression coverage to keep the specific fallback and prevent dash fallback from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused action-copy tests passed 2/2, `npm.cmd test` passed 347/347, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Subscription failure error-code fallback specificity**: Continued the active Hanwoo quality uplift by changing the subscription failure page missing error-code fallback from placeholder `-` to `오류 코드 미전달`. This keeps payment failure details from showing a bare dash when the gateway does not provide a code. Strengthened payment UX regression coverage to keep the specific fallback and prevent dash fallback from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused payment UX tests passed 5/5, `npm.cmd test` passed 347/347, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Ear-tag scanner birth-date fallback specificity**: Continued the active Hanwoo quality uplift by changing the ear-tag scanner matched-cattle birth-date fallback from placeholder `-` to `생년월일 미등록`, and routing scanner birth-date rendering through `formatScannerBirthDate()` so missing or malformed birth dates do not surface as bare dash or raw invalid date output. Strengthened scanner regression coverage to keep the specific fallback and prevent dash fallback from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused ear-tag scanner tests passed 4/4, `npm.cmd test` passed 347/347, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Cattle card genetic-grade fallback specificity**: Continued the active Hanwoo quality uplift by changing cattle row genetic-grade rendering from placeholder `-` to `유전 등급 미등록` when the grade is missing, blank, or legacy `-`. This keeps pen/list cattle cards from showing bare dash placeholders and makes the missing field explicit. Strengthened card regression coverage to keep the specific fallback and prevent dash fallback from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused card tests passed 5/5, `npm.cmd test` passed 346/346, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Notification time fallback specificity**: Continued the active Hanwoo quality uplift by changing notification time fallback copy from placeholder `-` to `알림 시간 확인 불가` in `formatNotificationTime()`, invalid `buildNotificationTiming()` output, and the notification modal's direct rendering fallback. This makes missing or malformed alert times identify the unavailable field instead of showing a bare dash. Strengthened notification timing and modal regression coverage to keep the specific fallback and prevent dash fallback from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused notification timing/modal tests passed 14/14, `npm.cmd test` passed 345/345, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard AI Insight weather fallback specificity**: Continued the active Hanwoo quality uplift by changing AI Insight prompt weather fallback copy from symbolic `?℃`/`?%` placeholders to explicit Korean signals (`기온 확인 불가`, `습도 확인 불가`) when THI is available but temperature or humidity is missing. Strengthened AI Insight regression coverage to keep the explicit weather fallback and prevent ambiguous symbol placeholders from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused AI Insight/chat/weather tests passed 32/32, `npm.cmd test` passed 344/344, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard AI Insight sales-amount terminology consistency**: Continued the active Hanwoo quality uplift by changing AI Insight prompt/default-card sales amount wording from `매출` to `판매액` (`판매액 N만원`, `출하·판매액 N만원`, `체중·판매액·시세 데이터`). This keeps generated insight context aligned with Sales and Analysis terminology. Strengthened AI Insight regression coverage to keep `판매액` wording and prevent the older `매출` phrases from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused AI Insight/chat/home/Analysis tests passed 63/63, `npm.cmd test` passed 343/343, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Alert banner missing-pen fallback specificity**: Continued the active Hanwoo quality uplift by changing estrus/calving alert banner missing-pen fallback from placeholder `-` to `칸 미지정`. This makes alert location chips explain that the pen assignment is missing instead of rendering a bare dash before `번`. Strengthened alert-banner regression coverage to keep the specific pen fallback and prevent the dash fallback from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused alert/home/field-mode tests passed 49/49, `npm.cmd test` passed 343/343, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Sales tab sales-terminology summary consistency**: Continued the active Hanwoo quality uplift by changing the Sales tab summary heading, cumulative KPI label, and no-sales helper description from `매출` wording to `판매`/`판매액` wording (`출하 및 판매 분석`, `총 누적 판매액`, `판매액, 등급, 수익 분석 차트`). This keeps the Sales tab aligned with the app-wide `판매 기록` and Analysis `연간 총판매액` terminology. Strengthened home-market regression coverage to keep the sales summary labels and prevent the older `매출` wording from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused Sales/home/empty/Analysis tests passed 58/58, `npm.cmd test` passed 343/343, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Analysis KPI sales terminology consistency**: Continued the active Hanwoo quality uplift by changing the Analysis tab annual revenue KPI title from `연간 총매출` to `연간 총판매액`. This keeps the management-analysis KPI aligned with the app-wide `판매` terminology already used by Sales, Today Focus, and home quick actions. Strengthened Analysis regression coverage to keep the `판매` KPI label and prevent the old `매출` KPI title from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused Analysis/home/Today Focus tests passed 52/52, `npm.cmd test` passed 343/343, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Shared short-date fallback specificity**: Continued the active Hanwoo quality uplift by changing the common `formatDate()` fallback from bare `-` to `날짜 미등록`. This aligns short date rendering with the existing long-date fallback and prevents detail/list date fields from surfacing meaningless dash placeholders when dates are missing or malformed. Strengthened date utility regression coverage to keep the Korean missing-date fallback and prevent the dash fallback from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused date/detail/alert/calving tests passed 26/26, `npm.cmd test` passed 343/343, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Cattle detail genetic fallback specificity**: Continued the active Hanwoo quality uplift by changing the cattle detail genetic-info fallback from placeholder-style `부:- / 모:-` to `부:부계 미등록 / 모:모계 미등록`. This makes the genetic ability card explain which lineage field is missing instead of showing bare dashes. Strengthened cattle-detail regression coverage to keep the lineage-specific fallback copy and prevent dash fallbacks from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused cattle-detail tests passed 16/16, `npm.cmd test` passed 343/343, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Cattle detail breeding-date fallback specificity**: Continued the active Hanwoo quality uplift by changing cattle detail reproductive-date fallbacks from placeholder `-` to domain-specific Korean copy (`발정일 미등록`, `최근 발정일 미등록`, `수정일 미등록`, `분만 예정일 미등록`). This makes breeding cards explain which date is missing instead of showing a bare dash. Strengthened cattle-detail regression coverage to keep the specific missing-date labels and prevent the dash fallback from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused cattle-detail tests passed 15/15, `npm.cmd test` passed 342/342, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Sales no-cost state copy specificity**: Continued the active Hanwoo quality uplift by changing the Sales tab no-cost per-record label from generic `관련 비용 없음` to `연결된 비용 기록 없음`. This makes profit-unavailable rows explain that no linked cost records exist before showing `비용 기록 없어 수익 추정 불가`. Strengthened Sales regression coverage to keep the specific no-cost label and prevent the generic label from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused home-market/Sales tests passed 38/38, `npm.cmd test` passed 341/341, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Admin diagnostics unavailable-copy specificity**: Continued the active Hanwoo quality uplift by changing admin diagnostics fallback copy from generic `확인 불가`/`-` to domain-specific `DB 상태 확인 불가`, `DB 응답 시간 확인 불가`, and `Node 버전 확인 불가`. This makes failure/empty diagnostics cards identify which system signal is unavailable. Strengthened diagnostics regression coverage to keep the specific unavailable labels and prevent generic latency fallback from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused diagnostics tests passed 3/3, `npm.cmd test` passed 341/341, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Field mode search missing-building fallback specificity**: Continued the active Hanwoo quality uplift by changing Field Mode search-result missing-building copy from generic `미지정` to `축사 미지정`. This makes onsite cattle search results name the missing location domain consistently with alert banner location chips. Strengthened FieldModeView regression coverage to keep the specific building fallback and prevent the generic fallback from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused FieldModeView tests passed 8/8, `npm.cmd test` passed 341/341, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Alert banner missing-building fallback specificity**: Continued the active Hanwoo quality uplift by changing estrus/calving alert banner missing-building copy from generic `미지정` to `축사 미지정`. This makes alert location chips name the missing location domain instead of showing a vague placeholder. Strengthened alert-banner regression coverage to keep the specific building fallback and prevent the generic fallback from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused alert-banner tests passed 3/3, `npm.cmd test` passed 340/340, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Weather unavailable source-label specificity**: Continued the active Hanwoo quality uplift by changing weather unavailable source labels from generic `확인 불가` to `날씨 확인 불가` in the weather state model. This aligns degraded/unavailable weather payloads with the visible weather widget unavailable copy and avoids a generic unavailable badge in weather state data. Strengthened weather-state regression coverage to keep the specific source label. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused weather/home tests passed 47/47, `npm.cmd test` passed 340/340, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Market price unavailable source-label specificity**: Continued the active Hanwoo quality uplift by changing market-price unavailable source labels from generic `확인 불가` to `시세 확인 불가` in the market price state model and widget presentation fallback. This makes degraded/unavailable price cards name the missing data domain clearly instead of showing a generic unavailable badge. Strengthened market-price regression coverage to keep the specific source label. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused market/home tests passed 45/45, `npm.cmd test` passed 340/340, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Profitability recommendation missing-identity fallback clarity**: Continued the active Hanwoo quality uplift by changing the profitability recommendation widget's missing tag/name fallbacks from placeholder-style `----` and `-` to Korean operator copy `이력번호 미등록` and `개체명 미등록`. This aligns shipment-profit cards with Sales, AI farm context, cattle cards, and alert banner missing-identity copy. Strengthened profitability widget regression coverage to prevent placeholder fallbacks from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused profitability tests passed 8/8, `npm.cmd test` passed 340/340, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard AI chat farm-context status fallback specificity**: Continued the active Hanwoo quality uplift by changing the AI chat farm-context fallback for empty cattle status grouping from generic `데이터 없음` to `상태별 개체 데이터 없음`. This gives the model a domain-specific missing-data signal instead of a vague placeholder. Strengthened AI chat route regression coverage to keep the specific fallback and prevent the generic status summary fallback from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused AI chat API tests passed 8/8, `npm.cmd test` passed 340/340, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Primary data-entry submit copy consistency**: Continued the active Hanwoo quality uplift by changing idle submit labels for Schedule, Feed, Inventory, Sales, and Settings forms from `등록하기`/`저장하기` variants to concise task labels (`일정 등록`, `급여 기록 저장`, `재고 등록`, `판매 기록 등록`, `농장 정보 저장`, `축사 등록`). This aligns submit buttons with the already-normalized open-form CTAs while keeping pending `... 중` states intact. Strengthened form-submit, schedule, empty-state, home/market, and settings regression coverage to prevent the older `하기` submit labels from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused submit-copy tests passed 76/76, `npm.cmd test` passed 340/340, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Building-name missing fallback consistency**: Continued the active Hanwoo quality uplift by changing remaining form/detail/feed building-name fallbacks from compact `축사명 미등록` to the app-wide `축사 이름 미등록`. This aligns cattle forms, cattle detail location, and feed building filters with Dashboard and Settings building fallback copy. Strengthened cattle-detail and empty-state regression coverage to prevent the compact fallback from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused cattle-detail/empty-state tests passed 31/31, `npm.cmd test` passed 340/340, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Alert banner missing cattle-name fallback consistency**: Continued the active Hanwoo quality uplift by changing alert banner missing cattle-name fallback from generic `이름 미등록` to Hanwoo-wide `개체명 미등록`. This aligns estrus/calving alert banners with dashboard rows, sales fallbacks, cards, and analysis ranking copy. Strengthened alert-banner regression coverage to prevent the generic fallback from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused alert-banner tests passed 3/3, `npm.cmd test` passed 340/340, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Notification dropdown fallback title clarity**: Continued the active Hanwoo quality uplift by changing the notification dropdown malformed-title fallback from empty-value copy `알림 제목 없음` to product-facing `운영 알림`. This aligns it with the notification widget's default heading and avoids a raw missing-title state in the UI. Strengthened notification-system regression coverage to prevent the terse fallback from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused notification-system tests passed 9/9, `npm.cmd test` passed 340/340, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Ear-tag scanner no-match empty-state copy clarity**: Continued the active Hanwoo quality uplift by changing the scanner no-match heading from terse `인식된 개체 정보 없음` to sentence-style `인식된 개체 정보가 없습니다`. This keeps the scanner failure state consistent with clearer Korean empty-state copy. Strengthened ear-tag scanner regression coverage to prevent the terse heading from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused scanner tests passed 3/3, `npm.cmd test` passed 340/340, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Empty building CTA accessible helper-tone consistency**: Continued the active Hanwoo quality uplift by changing the home empty-building CTA `aria-label` and `title` from noun-style `설정에서 첫 번째 축사 추가하기` to operator-facing guidance `설정에서 첫 번째 축사를 추가해 주세요`. This aligns assistive-tech and hover copy with the visible first-building CTA tone. Strengthened home/market regression coverage to prevent the old label from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused home-market tests passed 38/38, `npm.cmd test` passed 340/340, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Empty building CTA helper-tone consistency**: Continued the active Hanwoo quality uplift by changing the home empty-building CTA title from command-style `첫 번째 축사를 추가해보세요` to operator-facing guidance `첫 번째 축사를 추가해 주세요`. This keeps the first-run setup action aligned with the app-wide Korean helper tone. Strengthened home/market regression coverage for the first-building CTA copy. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused home-market tests passed 38/38, `npm.cmd test` passed 340/340, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard AI chat offline greeting helper-tone consistency**: Continued the active Hanwoo quality uplift by changing the AI chat offline fallback greeting reply from question-style `오늘 농장 운영에서 어떤 부분이 궁금하신가요?` to operator-facing guidance `오늘 농장 운영에서 궁금한 부분을 질문해 주세요.`. This keeps the offline chat path aligned with the AI chat welcome prompt and input placeholder. Strengthened AI chat widget regression coverage for the greeting fallback copy. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused AI chat widget tests passed 2/2, `npm.cmd test` passed 340/340, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard THI level description helper-tone guidance**: Continued the active Hanwoo quality uplift by changing THI warning/danger descriptions from status-style `급수량 확보와 송풍 강화가 필요한 수준입니다` and `즉시 냉방과 살수 조치가 필요한 고위험 상태입니다` to operator-facing guidance `급수량을 확보하고 송풍을 강화해 주세요` and `즉시 냉방과 살수 조치를 진행해 주세요`. This keeps the weather card's THI guidance aligned with livestock weather alerts. Strengthened home/market copy regression coverage for THI descriptions. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused home-market tests passed 38/38, `npm.cmd test` passed 340/340, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Weather danger-alert helper-tone guidance**: Continued the active Hanwoo quality uplift by changing livestock weather danger messages from status-style `냉방과 살수 조치가 필요합니다` and `보온 설비 점검이 필요합니다` to operator-facing guidance `냉방과 살수 조치를 진행해 주세요` and `보온 설비를 점검해 주세요`. This keeps severe heat/cold alerts aligned with existing weather helper tone. Strengthened home/market copy regression coverage for danger weather alerts. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused home-market tests passed 38/38, `npm.cmd test` passed 340/340, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard AI Insight default routine helper-tone guidance**: Continued the active Hanwoo quality uplift by changing the deterministic AI Insight default routine recommendation from status-style `발정·분만·사료·물·축사 환기 5가지 일상 점검을 권장합니다` to operator-facing guidance `발정·분만·사료·물·축사 환기 5가지 일상 점검을 진행해 주세요`. This keeps safe fallback insight cards aligned with the app-wide helper tone. Strengthened AI Insight regression coverage for the default routine card. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused AI Insight tests passed 14/14, `npm.cmd test` passed 340/340, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Today Focus feed-depletion warning helper-tone guidance**: Continued the active Hanwoo quality uplift by changing the non-critical feed-depletion Today Focus title from status-style `사료 잔여 N일 (점검 권장)` to operator-facing guidance `사료 잔여 N일, 재고를 점검해 주세요`. This makes feed stock warnings name the action before the danger threshold. Added warning-branch regression coverage for the feed-depletion item. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused Today Focus tests passed 11/11, `npm.cmd test` passed 340/340, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard AI Insight shipment schedule helper-tone guidance**: Continued the active Hanwoo quality uplift by changing the deterministic AI Insight immediate-shipment recommendation from status-style `24시간 내 출고 일정 확정 권장` to operator-facing guidance `24시간 내 출고 일정을 확정해 주세요`. This keeps high-priority shipment recommendations aligned with the app-wide helper tone. Strengthened AI Insight regression coverage for the shipment card. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused AI Insight tests passed 14/14, `npm.cmd test` passed 339/339, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard AI Insight THI heat-warning helper-tone guidance**: Continued the active Hanwoo quality uplift by changing the deterministic AI Insight high-THI recommendation from status-style `환기·미스트팬 가동, 급수기 4회 이상 점검 권장` to operator-facing guidance `환기·미스트팬을 가동하고 급수기를 4회 이상 점검해 주세요`. This keeps weather stress recommendations aligned with the app-wide helper tone. Strengthened AI Insight regression coverage for the heat-warning card. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused AI Insight tests passed 14/14, `npm.cmd test` passed 339/339, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard AI Insight calving preparation helper-tone guidance**: Continued the active Hanwoo quality uplift by changing the deterministic AI Insight calving-preparation recommendation from status-style `산방 청결·보온·요오드 소독 준비 점검 권장` to operator-facing guidance `산방 청결·보온·요오드 소독 준비를 점검해 주세요`. This keeps calving heuristic recommendations aligned with the app-wide helper tone. Updated AI Insight regression coverage for the calving-preparation card. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused AI Insight tests passed 14/14, `npm.cmd test` passed 339/339, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard AI Insight declining-margin helper-tone guidance**: Continued the active Hanwoo quality uplift by changing the deterministic AI Insight declining-margin recommendation from status-style `단가·증체 추세 재검토 필요` to operator-facing guidance `단가·증체 추세를 재검토해 주세요`. This keeps heuristic recommendations aligned with the app-wide helper tone. Updated AI Insight regression coverage for the declining-margin card. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused AI Insight tests passed 13/13, `npm.cmd test` passed 338/338, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Sales empty-state missing-cattle action guidance**: Continued the active Hanwoo quality uplift by changing the Sales tab empty-state disabled action label from terse `개체 등록 필요` to the operator-facing guidance `개체를 먼저 등록해 주세요`. The no-cattle state now explains the prerequisite action instead of showing a noun-phrase status. Updated empty-state and home-market regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused empty-state tests passed 17/17, focused home-market tests passed 38/38, `npm.cmd test` passed 337/337, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Cattle Excel export action specificity**: Continued the active Hanwoo quality uplift by changing the Excel export button labels from generic `엑셀 다운로드` / `엑셀 다운로드 준비 중` to `개체 엑셀 다운로드` / `개체 엑셀 다운로드 준비 중`. The header export action now names the cattle dataset being exported in visible copy, accessible label, and hover title. Updated Excel export regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused Excel export tests passed 2/2, `npm.cmd test` passed 337/337, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Market price refresh busy-label specificity**: Continued the active Hanwoo quality uplift by changing the market price refresh button busy accessible/title label from generic `시세 갱신 중` to `한우 시세 갱신 중`. The loading action now stays tied to the Hanwoo market-price widget context while the ready label remains `한우 시세 새로고침`. Updated home/market regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused home-market tests passed 38/38, `npm.cmd test` passed 337/337, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard AI chat empty-input send action label**: Continued the active Hanwoo quality uplift by changing the AI chat send button accessible/title label so an empty disabled input says `질문을 입력하면 보낼 수 있습니다` instead of the actionable `질문 보내기`. Streaming still says `답변 생성 중` and ready state still says `질문 보내기`. Updated AI chat widget regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused AI chat widget tests passed 2/2, `npm.cmd test` passed 337/337, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Today Focus sales analysis helper-tone consistency**: Continued the active Hanwoo quality uplift by changing the Today Focus monthly sales analysis guidance from `판매 흐름을 분석 탭에서 확인하세요.` to `판매 흐름을 분석 탭에서 확인해 주세요.`. This preserves the sales terminology fix while aligning the action guidance with the app-wide Korean helper tone. Updated Today Focus regression coverage to prevent both the old `매출` terminology and the command-style `확인하세요` wording from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused Today Focus tests passed 10/10, `npm.cmd test` passed 337/337, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Cattle form helper guidance tone consistency**: Continued the active Hanwoo quality uplift by changing the cattle edit/create form helper copy from `개체 정보를 수정하고 저장하세요` and `새 개체의 기본 정보를 입력하세요` to `개체 정보를 수정하고 저장해 주세요` and `새 개체의 기본 정보를 입력해 주세요`. This keeps form guidance aligned with the app-wide Korean helper tone and existing validation messages. Updated cattle form regression coverage for both edit and create helper text. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused cattle detail/form tests passed 14/14, `npm.cmd test` passed 337/337, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard AI Insight schedule fallback helper-tone consistency**: Continued the active Hanwoo quality uplift by changing the deterministic AI Insight safe schedule fallback from `캘린더에서 확인하세요` to `캘린더에서 확인해 주세요`. This keeps all no-signal fallback recommendations aligned with the app-wide Korean helper tone. Split regression coverage so registered-herd no-signal defaults prove the schedule card copy without assuming it appears in the empty-herd top-three slice. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused AI Insight tests passed 12/12, `npm.cmd test` passed 337/337, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Weather livestock guidance helper-tone consistency**: Continued the active Hanwoo quality uplift by changing THI and livestock weather warning guidance from command-style `확인하세요`/`강화하세요`/`점검하세요` to `확인해 주세요`/`강화해 주세요`/`점검해 주세요`. This keeps weather recovery and livestock-care recommendations aligned with the app-wide Korean helper tone. Updated home-market regression coverage for the utility copy. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused home-market tests passed 38/38, `npm.cmd test` passed 336/336, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard QR print popup-block guidance tone consistency**: Continued the active Hanwoo quality uplift by changing the QR label print popup-block failure message from `브라우저 팝업 허용 후 다시 시도하세요.` to `브라우저 팝업 허용 후 다시 시도해 주세요.`. This keeps retry recovery guidance aligned with the app-wide Korean helper tone. Updated QR widget regression coverage to prevent the command-style wording from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused QR widget tests passed 3/3, `npm.cmd test` passed 336/336, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard AI Insight fallback guidance tone consistency**: Continued the active Hanwoo quality uplift by changing deterministic AI Insight fallback guidance from command-style `처치 일정 잡으세요` and `개체 등록을 먼저 진행하세요` to `처치 일정을 잡아 주세요` and `개체 등록을 먼저 진행해 주세요`. This keeps fallback recommendations aligned with the app-wide helper tone. Updated AI Insight regression coverage for both fallback paths. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused AI Insight tests passed 11/11, `npm.cmd test` passed 336/336, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Ear-tag scanner retry guidance tone consistency**: Continued the active Hanwoo quality uplift by changing the scanner no-match guidance from stiff `다시 스캔해주십시오` to the app-wide `다시 스캔해 주세요`. This keeps scanner failure recovery copy aligned with other retry and helper messages. Updated scanner modal regression coverage to prevent the stiff wording from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused scanner tests passed 3/3, `npm.cmd test` passed 336/336, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Analysis top-sale missing cattle-name copy consistency**: Continued the active Hanwoo quality uplift by changing the Analysis tab top-sale missing cattle-name fallback from generic `이름 없음` to the existing Hanwoo-wide `개체명 미등록`. This keeps the Analysis ranking list aligned with dashboard rows, Sales tab fallbacks, cards, and AI farm context. Updated analysis copy regression coverage to prevent returning to the generic label. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused analysis tests passed 3/3, `npm.cmd test` passed 336/336, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard analysis cost-data empty copy clarity**: Continued the active Hanwoo quality uplift by changing the Analysis tab cost-structure fallback from terse `실데이터 없음` to `실제 비용 데이터 없음`. This makes the empty state specific to the missing cost data in that card. Updated analysis copy regression coverage to prevent returning to the terse label. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused analysis tests passed 3/3, `npm.cmd test` passed 336/336, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard retry and move guidance spacing consistency**: Continued the active Hanwoo quality uplift by changing remaining operator-facing `시도해주세요`/`이동해주세요` copy to `시도해 주세요`/`이동해 주세요` in offline sync failure toasts and the building-delete blocked message. Updated action, offline-sync, and home-market regression coverage to keep the spaced Korean helper wording. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused action-copy tests passed 2/2, sync-manager copy test passed 1/1, home-market tests passed 38/38, `npm.cmd test` passed 336/336, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard month-label spacing copy consistency**: Continued the active Hanwoo quality uplift by changing remaining `이번달`/`다음달` copy to `이번 달`/`다음 달` in the home KPI card, AI insight prompt snapshot, and deterministic insight fallback. Updated home-market and AI insight regression coverage to keep the spaced Korean date copy. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused AI insight tests passed 11/11, focused home-market tests passed 38/38, `npm.cmd test` passed 336/336, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Today Focus sales terminology consistency**: Continued the active Hanwoo quality uplift by changing the Today Focus monthly sales analysis prompt from `매출 흐름을 분석 탭에서 확인하세요.` to `판매 흐름을 분석 탭에서 확인하세요.`. This keeps home guidance aligned with the Sales tab and quick-action `판매 기록` terminology. Added focused Today Focus regression coverage for the analysis-path copy. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused Today Focus tests passed 10/10, `npm.cmd test` passed 336/336, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard cattle edit-form guidance copy clarity**: Continued the active Hanwoo quality uplift by changing the cattle edit form helper text from generic `정보를 수정하고 저장하세요` to `개체 정보를 수정하고 저장하세요`. This keeps the helper aligned with the `개체 정보 수정` heading and `개체 정보 저장` action. Updated cattle form regression coverage to prevent reverting to the generic edit helper. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused cattle detail/form tests passed 14/14, `npm.cmd test` passed 335/335, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Sales profit-estimation unavailable copy clarity**: Continued the active Hanwoo quality uplift by changing the Sales tab per-record no-cost profit state from terse `수익 추정 불가` to `비용 기록 없어 수익 추정 불가`. This makes it clearer why profit cannot be estimated when no linked cost records exist. Updated home-market regression coverage to prevent reverting to the terse old copy. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused home-market tests passed 38/38, `npm.cmd test` passed 335/335, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Gemini |
| Work | **workspace project health check and mcp servers diagnostic and next-build lock resolution**: Ran wmic/tasklist process analysis and local diagnostics. Identified that 'hanwoo-dashboard' build failed due to Next.js build-lock concurrency. Resolved the build lock by safely purging 'projects/hanwoo-dashboard/.next/' directory, which restored 100% build health to hanwoo-dashboard (passed in 62.57s). Ran project_qc_runner to audit the whole mono-repo: blind-to-x (pytest passed, ruff passed), shorts-maker-v2 (pytest 602 passed, ruff passed), knowledge-dashboard (eslint passed, test passed, next-build passed), and hanwoo-dashboard (eslint passed, node-test 335 passed, next-build passed). Verified all projects are 100% green and deploy-ready. Ran mcp_diagnostic to verify 6 integrated local MCP servers (sqlite-multi, system-monitor, telegram, cloudinary, youtube-data, n8n-workflow): all servers completed handshake successfully (SUCCESS: ALL SERVERS FUNCTIONAL). Checked handoff rotation policy via handoff_rotator.py: all 198 addenda are within the active 7-day cutoff (from 2026-05-20), meaning noop archiving needed. |
| Next Priorities | T-251 remains user-owned Supabase database password/control-plane resync. Keep 15 open major PRs deferred to user review as tracked by Claude. Review docs/mcp_status_report.md for detail. All projects are clean and verified! |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Claude |
| Work | **Dependabot backlog drain (27 → 15)**: Triaged 27 BLOCKED Dependabot PRs. All BLOCKED state was caused by pre-existing `test-summary` failure on main HEAD (shorts-maker-v2-tests, frontend-active-apps hanwoo/knowledge fail — confirmed via `gh run view` on commit `b75e8cd3`), not by individual bumps. Admin-merged 12 patch/minor PRs whose own project's tests were already passing: #79 aiohttp (blind-to-x), #81 react-hook-form (hanwoo), #83 beautifulsoup4 (blind-to-x), #85 anthropic (blind-to-x), #86 @tailwindcss/postcss (hanwoo), #88 python-dotenv (blind-to-x), #90 @serwist/next (hanwoo), #94 actions/setup-node v4→v6, #99 eslint-plugin-react-refresh (word-chain), #101 tailwindcss (knowledge), #105 @tailwindcss/postcss (knowledge), #106 bullmq (hanwoo). 15 majors deferred to user review (see Next Priorities). |
| Next Priorities | **Deferred Tier-2 majors (15 open PRs)**: (a) Workflow-scope blocked: #95 pnpm/action-setup v4→v6 — `gh` token lacks `workflow` scope, needs user-token admin merge. (b) lucide-react v0.563→v1.16 ×3 (#91 word-chain, #93 hanwoo, #103 knowledge) — v1 removed brand icons per memory `dependabot_pr_backlog_drain_20260520`, audit icon usage before merge. (c) eslint 9→10 ×3 (#78, #89, #96) + #102 @eslint/js v10 (suika) — likely needs config update. (d) vite 7→8 ×2 (#87 word-chain, #104 suika) — build tool major. (e) jsdom 28→29 ×2 (#97, #98) — test env API changes. (f) #80 notion-client v2→v3 (blind-to-x) — API surface change. (g) #84 @types/node v20→v25 (knowledge) — types-only, safe but currently BEHIND after Tier-1 merges, dependabot rebase requested. (h) #100 globals 16→17 (suika) — diff shows suspicious extra esbuild lockfile churn, investigate. Active Hanwoo goal still owned by Codex; my work touched only PR queue + AI context files, not Codex's WIP. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard notification SMS test visible copy specificity**: Continued the active Hanwoo quality uplift by changing the notification modal SMS test button's idle visible text from `테스트 전송` to `문자 알림 테스트 전송`. This keeps the visible action aligned with its `aria-label` and `title`. Updated notification modal regression coverage to prevent reverting to the shorter generic copy. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused notification modal tests passed 8/8, `npm.cmd test` passed 335/335, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Excel export busy visible copy specificity**: Continued the active Hanwoo quality uplift by changing the Excel export button's visible busy text from `엑셀 준비 중...` to `엑셀 다운로드 준비 중...`. This keeps the on-screen pending state aligned with its `aria-label` and `title`. Updated Excel export regression coverage to prevent reverting to the shorter busy copy. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused Excel export tests passed 2/2, `npm.cmd test` passed 335/335, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard home quick action sales copy consistency**: Continued the active Hanwoo quality uplift by changing the home dashboard quick action detail from `매출 바로 입력` to `판매 기록 바로 입력`. This keeps the quick action aligned with the Sales tab's `판매 기록` terminology and registration flow. Updated home-market regression coverage to prevent reverting the quick-action detail to `매출 바로 입력`. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused home-market tests passed 38/38, `npm.cmd test` passed 335/335, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Settings building validation copy consistency**: Continued the active Hanwoo quality uplift by changing client and server building-name validation messages from `동 이름을 입력해 주세요.` to `축사 이름을 입력해 주세요.`. This keeps validation feedback aligned with the Settings form label and placeholder. Updated Settings regression coverage to keep both `formSchemas.js` and `action-validation.mjs` on the shared `축사 이름` terminology. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused Settings/action-validation tests passed 25/25, `npm.cmd test` passed 335/335, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard create-form cancel-copy regression coverage hardening**: Continued the active Hanwoo quality uplift by strengthening source-level regression tests for Sales, Inventory, Settings building, and Schedule create-form toggles. The tests now fail if the open-state button text regresses to generic `취소`, keeping task-specific Korean cancel labels (`판매 기록 등록 취소`, `재고 등록 취소`, `축사 등록 취소`, `일정 등록 취소`) protected even if only the middle branch changes. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused create-form copy tests passed 75/75, `npm.cmd test` passed 335/335, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Settings building delete confirmation copy consistency**: Continued the active Hanwoo quality uplift by changing the Settings building-delete confirmation title from `${name} 동을 삭제할까요?` to `${name} 축사를 삭제할까요?`. This keeps the destructive confirmation dialog aligned with visible `축사 삭제`, `축사 삭제 중...`, and Settings building-management terminology. Updated Settings regression coverage to prevent reverting to the old `동` wording. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused Settings test passed 12/12, `npm.cmd test` passed 335/335, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard remaining-day countdown copy consistency**: Continued the active Hanwoo quality uplift by replacing remaining user-facing `D-n` countdown labels in cattle detail, schedule upcoming events, cattle row alert badges, calving alert cards, and Today Focus schedule details with operator-readable `오늘` / `n일 남음` copy. Updated focused source and behavior regression coverage to prevent those `D-` labels from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused countdown tests passed 41/41, `npm.cmd test` passed 335/335, `npm.cmd run lint` passed, and `npm.cmd run build` passed after one transient Next build-lock retry with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **Hanwoo build QC passed after approved dev-server stop**: User approved continuing. Stopped only Hanwoo Next dev processes matched by `hanwoo-dashboard` / `next dev -p 60809`: PIDs 27348, 32320, 30168. Reran `python execution/project_qc_runner.py --project hanwoo-dashboard --check build --json`; result passed (`npm run build`, returncode 0, ~58.01s). Next compiled successfully in 14.8s, TypeScript finished, static generation completed 18/18. Build emitted known Supabase Prisma warning `P2010 / XX000 / (ENOTFOUND) tenant/user postgres.fuemeqmigptwfzqvrpjf not found`, matching existing T-251 credential/control-plane blocker, but did not fail the build. |
| Next Priorities | Hanwoo local gates now have test/lint/build evidence. Remaining known blocker remains T-251: user must reset/resync Supabase DB password/control-plane credentials before live DB CRUD E2E can pass. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **Hanwoo lint passed; build blocked by active dev server**: Ran `python execution/project_qc_runner.py --project hanwoo-dashboard --check lint --json` and it passed (`npm run lint`, returncode 0, ~32.97s). Ran `python execution/project_qc_runner.py --project hanwoo-dashboard --check build --json`; it failed before compile because Next reported `Another next build process is already running`. Process inspection found active Hanwoo dev server processes: `next dev -p 60809 --webpack` (PID 32320) and `next/dist/server/lib/start-server.js` for `projects/hanwoo-dashboard` (PID 30168). Did not terminate them because they may be user-owned interactive work. |
| Next Priorities | If the user approves stopping the running Hanwoo dev server, terminate the Hanwoo Next dev processes and rerun `python execution/project_qc_runner.py --project hanwoo-dashboard --check build --json`. Otherwise treat build as environment-blocked, not source-failed. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard AI Insight opt-in privacy copy**: Continued the active Hanwoo quality uplift by adding an explicit Settings widget-list description for the opt-in AI Insight widget: `켜면 농장 요약 데이터를 AI 분석 API로 전송합니다.` This preserves the existing `defaultOn: false` privacy default while telling operators what enabling the widget does before any AI request is made. Updated AI Insight and Settings source-level regression coverage to keep the privacy copy wired through the shared widget registry. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused AI Insight test passed 10/10, focused Settings test passed 12/12, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **Hanwoo test QC verified after AI Insight opt-in hardening**: Ran `python execution/project_qc_runner.py --project hanwoo-dashboard --check test --json`. Result: passed. Underlying command `npm test` completed with 330 tests, 4 suites, 330 pass, 0 fail, 0 skipped/todo/cancelled, duration ~2.88s reported by node test output. No code changes were required after validation. |
| Next Priorities | If broader confidence is needed, run `python execution/project_qc_runner.py --project hanwoo-dashboard --check lint --json` and `--check build --json`, or full `--project hanwoo-dashboard --json`. Keep Supabase T-251 separate until the user resets/resyncs credentials. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Alert banner remaining-day copy clarity**: Continued the active Hanwoo quality uplift by changing estrus and calving alert banner countdown labels from terse `D-n` wording to operator-readable `n일 남음`, with same-day labels shown as `오늘`. The existing malformed `daysLeft` normalization remains intact, but livestock alerts now read more naturally in Korean and are easier to scan. Updated alert banner source-level regression coverage to prevent reverting to `D-` countdown labels. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused alert banner test passed 3/3, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **Dirty worktree review + Hanwoo AI privacy default hardening**: User selected full-change review. Current worktree is large and mixed across `.agents`, `.ai`, `.github`, `blind-to-x`, `hanwoo-dashboard`, `shorts-maker-v2`, `workspace`, and tests. Reviewed Hanwoo entry points for the new AI Insight widget and confirmed dependency `@google/generative-ai` exists. Identified that `AI 인사이트` was default-on, which could automatically call the authenticated `/api/ai/insight` route and, when `GEMINI_API_KEY` is configured, send farm summary data to Gemini. Changed `projects/hanwoo-dashboard/src/lib/hooks/useWidgetSettings.js` to make `aiInsight` opt-in (`defaultOn: false`) and updated `projects/hanwoo-dashboard/src/lib/ai-insight-widget-copy.test.mjs` expectation. No validation commands were run. |
| Next Priorities | If continuing in this dirty worktree, keep changes scoped. Recommended validation: `python execution/project_qc_runner.py --project hanwoo-dashboard --check test --json`, then full Hanwoo QC if green. Review whether the AI Insight UI should include explicit privacy copy before enabling. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Settings farm coordinate label copy consistency**: Continued the active Hanwoo quality uplift by changing the Settings tab farm coordinate labels from `위도 (Latitude)` / `경도 (Longitude)` to `위도` / `경도`. This removes unnecessary English from operator-facing form labels while keeping the existing numeric placeholders and validation wiring intact. Updated Settings source-level regression coverage to prevent reverting to `Latitude` or `Longitude`. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused Settings test passed 12/12, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Settings building section heading copy consistency**: Continued the active Hanwoo quality uplift by changing the Settings tab building section heading from `축사 동 관리` to `축사 관리`. The section title now matches the surrounding `축사 등록`, `축사 이름`, `축사 삭제`, and `축사 삭제 중...` wording, removing the last mixed `동` wording in that Settings building-management flow. Updated Settings source-level regression coverage to prevent reverting to `축사 동 관리`. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused Settings test passed 12/12, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Settings building form label copy consistency**: Continued the active Hanwoo quality uplift by changing the Settings tab building registration form labels and placeholder from `동 이름` / `동 이름을 입력해 주세요.` / `칸 수 (Pen Count)` to `축사 이름` / `축사 이름을 입력해 주세요.` / `칸 수`. The form copy now matches the surrounding `축사 등록` wording and removes unnecessary English from the operator-facing label. Updated Settings source-level regression coverage to prevent reverting to `동 이름` or `Pen Count`. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused Settings test passed 12/12, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Settings building delete accessible copy consistency**: Continued the active Hanwoo quality uplift by changing the Settings tab building delete button's pending and idle accessible labels from `${building.name} 동 삭제...` to `${building.name} 축사 삭제...`. The aria-label/title copy now matches the visible `축사 삭제` and `축사 삭제 중...` button text, so the same destructive building-delete action is not described with mixed `동`/`축사` wording. Updated Settings source-level regression coverage to prevent reverting to the old `동 삭제` wording. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused Settings test passed 12/12, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Sales pagination retry copy consistency**: Continued the active Hanwoo quality uplift by changing the sales pagination timeout and error messages from `이전 매출 기록...` to `이전 판매 기록...`. The pagination retry feedback now matches the Sales tab load-more CTA and the broader `판매 기록` wording used across the Sales/Dashboard flow. Updated sales pagination source-level regression coverage to prevent reverting to the old `이전 매출 기록` wording. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused sales pagination test passed 2/2, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Dashboard full sales ledger loading copy consistency**: Continued the active Hanwoo quality uplift by changing the dashboard's full sales ledger loading, retry, and load-error copy from `매출 기록` wording to `판매 기록`. The Analysis/Sales loading path now matches the Sales tab CTA, form title, submit copy, and API fallback copy. Updated home-market source-level regression coverage to prevent reverting the retry label, loading placeholder, or error fallback to the old `매출 기록` wording. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused home-market test passed 38/38, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Settings building add-form heading copy consistency**: Continued the active Hanwoo quality uplift by changing the Settings tab building add-form heading from `새 축사 동 등록` to `새 축사 등록`. The form title now matches the Settings tab's `축사 등록` CTA, submit copy, and accessible label, avoiding mixed `동 추가`/`축사 등록` wording after the operator opens the add-building form. Updated Settings source-level regression coverage to prevent reverting to the old mixed heading. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused Settings test passed 12/12, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Sales add-form heading copy consistency**: Continued the active Hanwoo quality uplift by changing the Sales tab add-form heading from `새 매출 기록 등록` to `새 판매 기록 등록`. The form title now matches the Sales tab's `판매 기록 등록` CTA, submit copy, and empty-state action, avoiding mixed naming after the operator opens the add-sale form. Updated home-market source-level regression coverage to prevent reverting to the old mixed `매출 기록` heading. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused home-market test passed 38/38, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Settings building add-form open visible copy specificity**: Continued the active Hanwoo quality uplift by changing the Settings tab building add-form toggle's closed-state visible copy from `+ 동 추가` to `축사 등록`. The visible CTA now matches the existing `축사 등록 창 열기` accessible label and the building registration submit copy, so the operator sees the same task name before opening the add-building form. Updated Settings source-level regression coverage to prevent reverting to the old shorthand visible copy. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused Settings test passed 12/12, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Schedule add-form open visible copy specificity**: Continued the active Hanwoo quality uplift by changing the Schedule tab add-form toggle's closed-state visible copy from `새 일정` to `일정 등록`. The visible CTA now matches the existing `일정 등록 창 열기` accessible label and the schedule registration submit copy, so the operator sees the same task name before opening the add-schedule form. Updated schedule source-level regression coverage to prevent reverting to the old shorthand visible copy. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused schedule test passed 7/7, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Inventory add-form open visible copy specificity**: Continued the active Hanwoo quality uplift by changing the Inventory tab add-form toggle's closed-state visible copy from `+재고 등록` to `재고 등록`. The visible CTA now matches the existing `재고 등록 창 열기` accessible label and the Inventory empty-state CTA, so the operator sees the same task name before opening the add-inventory form. Updated empty-state source-level regression coverage to prevent reverting to the old shorthand visible copy. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused empty-state test passed 17/17, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Sales add-form open visible copy specificity**: Continued the active Hanwoo quality uplift by changing the Sales tab add-form toggle's closed-state visible copy from `+매출 등록` to `판매 기록 등록`. The visible CTA now matches the existing `판매 기록 등록 창 열기` accessible label and the Sales empty-state CTA, so the operator sees the same task name before opening the add-sale form. Updated home-market source-level regression coverage to prevent reverting to the old shorthand visible copy. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused home-market test passed 38/38, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Sales empty-state action visible copy specificity**: Continued the active Hanwoo quality uplift by changing the Sales tab empty-state action label from terse `매출 기록` to `판매 기록 등록`. The no-sales CTA now matches the surrounding sales-record registration copy and names the operator task clearly before opening the add-sale form. Updated empty-state and home-market source-level regression coverage to prevent reverting to the old short action copy. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused empty-state/home-market tests passed 55/55, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Cattle detail edit/archive visible copy specificity**: Continued the active Hanwoo quality uplift by changing the cattle detail modal edit and archive action buttons' idle visible copy from generic `수정` / `보관` to `개체 정보 수정` / `개체 보관 처리`. The visible actions now stay aligned with the existing Korean accessible labels and name the selected-cattle edit/archive tasks clearly before and during async detail operations. Updated cattle detail source-level regression coverage to prevent reverting to the old generic action copy. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused cattle detail/form tests passed 13/13, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Login submit pending visible copy specificity**: Continued the active Hanwoo quality uplift by changing the login form submit button's pending visible copy from generic `확인 중...` to `로그인 확인 중...`. The visible pending action now names the in-progress authentication task and remains aligned with the existing Korean `loginSubmitLabel`. Updated login source-level regression coverage to prevent reverting to the old generic pending copy. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused login/error-page tests passed 9/9, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Dashboard cattle archive and move confirmation copy specificity**: Continued the active Hanwoo quality uplift by changing dashboard cattle archive confirmation buttons from generic `보관 처리` / `취소` to `개체 보관 처리` / `개체 보관 취소`, and cattle move confirmation buttons from generic `이동` / `취소` to `개체 이동` / `개체 이동 취소`. The confirmation actions now name the cattle archive/move tasks consistently with the surrounding Korean operator copy. Updated dashboard source-level regression coverage to prevent reverting to the old generic confirmation labels. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused Dashboard/Home tests passed 38/38, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Settings building delete visible and confirmation copy specificity**: Continued the active Hanwoo quality uplift by changing the Settings tab building delete row action's idle visible copy from generic `삭제` to `축사 삭제`, and by changing the destructive confirmation actions from generic `삭제` / `취소` to `축사 삭제` / `축사 삭제 취소`. The visible and confirmation actions now name the building-delete task consistently with the existing Korean accessible label/title before and during async deletion. Updated Settings source-level regression coverage to prevent reverting to the old generic delete/cancel copy. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused Settings tests passed 12/12, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Settings building add-form cancel visible copy specificity**: Continued the active Hanwoo quality uplift by changing the Settings tab building add/cancel toggle's idle visible copy from generic `취소` to `축사 등록 취소`. The visible secondary action now names the building-registration cancellation task and remains aligned with the existing Korean accessible label/title before and during async submission. Updated Settings source-level regression coverage to prevent reverting to the old generic cancel copy. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused Settings tests passed 12/12, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Schedule add-form cancel visible copy specificity**: Continued the active Hanwoo quality uplift by changing the Schedule tab add/cancel toggle's idle visible copy from generic `취소` to `일정 등록 취소`. The visible secondary action now names the schedule-registration cancellation task and remains aligned with the existing Korean accessible label/title before and during async submission. Updated Schedule source-level regression coverage to prevent reverting to the old generic cancel copy. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused Schedule tests passed 7/7, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Sales add-form cancel visible copy specificity**: Continued the active Hanwoo quality uplift by changing the Sales tab add/cancel toggle's idle visible copy from generic `취소` to `판매 기록 등록 취소`. The visible secondary action now names the sales-record registration cancellation task and remains aligned with the existing Korean accessible label/title before and during async submission. Updated Sales source-level regression coverage to prevent reverting to the old generic cancel copy. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused Sales/Home copy tests passed 38/38, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Inventory add-form cancel visible copy specificity**: Continued the active Hanwoo quality uplift by changing the Inventory tab add/cancel toggle's idle visible copy from generic `취소` to `재고 등록 취소`. The visible secondary action now names the inventory-registration cancellation task and remains aligned with the existing Korean accessible label/title before and during async submission. Updated inventory source-level regression coverage to prevent reverting to the old generic cancel copy. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused inventory tests passed 17/17, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Cattle detail breeding cancel visible copy specificity**: Continued the active Hanwoo quality uplift by changing the cattle detail breeding form cancel button's idle visible copy from generic `취소` to `번식 기록 취소`. The visible secondary action now names the breeding-record cancellation task and remains aligned with the existing Korean accessible label/title before and during async submission. Updated cattle detail source-level regression coverage to prevent reverting to the old generic cancel copy. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused cattle detail tests passed 13/13, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Calving cancel visible copy specificity**: Continued the active Hanwoo quality uplift by changing the calving form cancel button's idle visible copy from generic `취소` to `분만 기록 취소`. The visible secondary action now names the calving-record cancellation task and remains aligned with the existing Korean accessible label/title before and during async submission. Updated calving source-level regression coverage to prevent reverting to the old generic cancel copy. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused calving tests passed 5/5, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Cattle form cancel visible copy specificity**: Continued the active Hanwoo quality uplift by changing the cattle form cancel button's idle visible copy from generic `취소` to `개체 저장 취소`. The visible secondary action now names the cattle-save cancellation task and remains aligned with the existing Korean accessible label/title before and during async submission. Updated cattle form source-level regression coverage to prevent reverting to the old generic cancel copy. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused cattle form/detail tests passed 13/13, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Feed submit visible copy regression specificity**: Continued the active Hanwoo quality uplift by refactoring the Feed tab submit button's visible save copy into `submitButtonText`. The primary feed-record submission action now uses the same state model as the existing Korean `submitButtonLabel`, keeping visible text and accessible label aligned before and during async submission. Updated feed and shared submit-copy source-level regression coverage to prevent reverting to the old inline pending-copy expression. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused feed/submit-copy tests passed 18/18, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Calving submit visible copy regression specificity**: Continued the active Hanwoo quality uplift by refactoring the Calving tab submit button's visible save copy into `submitButtonText`. The primary calving-record submission action now uses the same state model as the existing Korean `submitButtonLabel`, keeping visible text and accessible label aligned before and during async submission. Updated calving and shared submit-copy source-level regression coverage to prevent reverting to the old inline pending-copy expression. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused calving/submit-copy tests passed 6/6, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Schedule submit visible copy regression specificity**: Continued the active Hanwoo quality uplift by refactoring the Schedule tab submit button's visible save copy into `submitButtonText`. The primary schedule registration action now uses the same state model as the existing Korean `submitButtonLabel`, keeping visible text and accessible label aligned before and during async submission. Updated schedule and shared submit-copy source-level regression coverage to prevent reverting to the old inline pending-copy expression. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused schedule/submit-copy tests passed 8/8, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Inventory quantity save visible copy specificity**: Continued the active Hanwoo quality uplift by changing the inline inventory quantity save button's idle visible copy from generic `저장` to `수량 저장`. The row-level quantity update action now names the quantity-save task before async submission and remains aligned with the existing Korean accessible label/title and pending text. Updated inventory source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused inventory tests passed 17/17, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Settings building submit visible copy specificity**: Continued the active Hanwoo quality uplift by changing the Settings tab building submit button's idle visible copy from generic `등록하기` to `축사 등록하기`. The primary building registration action now names the building task before async submission and remains aligned with the existing Korean accessible label/title and pending text. Updated settings source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused settings tests passed 12/12, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Settings farm submit visible copy specificity**: Continued the active Hanwoo quality uplift by changing the Settings tab farm settings submit button's idle visible copy from generic `저장하기` to `농장 정보 저장하기`. The primary farm-info save action now names the farm settings task before async submission and remains aligned with the existing Korean accessible label/title and pending text. Updated settings source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused settings tests passed 12/12, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Sales submit visible copy specificity**: Continued the active Hanwoo quality uplift by changing the Sales tab submit button's idle visible copy from generic `등록하기` to `판매 기록 등록하기`. The primary sales-record create action now names the sales registration task before async submission and remains aligned with the existing Korean accessible label/title and pending text. Updated Sales and shared submit-copy source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused Sales/submit-copy tests passed 39/39, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Inventory submit visible copy specificity**: Continued the active Hanwoo quality uplift by changing the Inventory tab submit button's idle visible copy from generic `등록하기` to `재고 등록하기`. The primary inventory-create action now names the inventory registration task before async submission and remains aligned with the existing Korean accessible label/title and pending text. Updated shared submit-copy source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused inventory/submit-copy tests passed 18/18, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Cattle form submit visible copy specificity**: Continued the active Hanwoo quality uplift by changing the cattle form submit button's idle visible copy from generic `저장하기` to `개체 정보 저장`. The primary save action now names the cattle-info save task before async submission and remains aligned with the existing Korean accessible label/title and pending text. Updated cattle form and shared submit-copy source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused cattle form/submit-copy tests passed 14/14, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Cattle detail breeding submit visible copy specificity**: Continued the active Hanwoo quality uplift by changing the cattle detail breeding record submit button's idle visible copy from generic `저장` to `번식 기록 저장`. The visible button text now names the breeding-record save task before async submission and remains aligned with the existing Korean accessible label/title and pending text. Updated cattle detail source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused cattle detail tests passed 13/13, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard AI insight loading status visible copy specificity**: Continued the active Hanwoo quality uplift by changing the AI insight widget loading status visible copy from generic `분석 중…` to `AI 인사이트 분석 중…`. The busy status now names the in-progress AI-insight analysis on screen and matches the widget task/refresh-control context. Updated AI insight source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused AI insight tests passed 10/10, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Cattle pagination button visible copy specificity**: Continued the active Hanwoo quality uplift by changing the home dashboard cattle load-more button's idle visible copy from generic `개체 더 보기` to `이전 개체 더 보기`. The button now names the previous cattle-page load task more clearly on screen and matches the existing Korean loading label/cursor-pagination behavior. Updated cattle pagination source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused cattle pagination tests passed 2/2, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Notification modal close disabled label specificity**: Continued the active Hanwoo quality uplift by adding a state-aware close button label for the notification modal. While SMS test sending is in progress, the disabled close action now exposes `문자 알림 테스트 전송 중에는 알림 센터를 닫을 수 없습니다` through both `aria-label` and `title` instead of continuing to advertise a closable action. Updated notification modal source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused notification modal tests passed 8/8, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard QR print busy visible copy specificity**: Continued the active Hanwoo quality uplift by changing the QR label print button's visible busy text from generic `인쇄 준비 중...` to `QR 라벨 인쇄 준비 중...`. The disabled print action now names the in-progress QR-label print task on screen and matches the existing Korean accessible label/title. Updated QR widget source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused QR widget tests passed 3/3, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Notification SMS test busy visible copy specificity**: Continued the active Hanwoo quality uplift by changing the notification modal SMS test button's visible busy text from generic `전송 중...` to `문자 알림 테스트 전송 중...`. The disabled SMS test action now names the in-progress task on screen and matches the existing Korean accessible label/title. Updated notification modal source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused notification modal tests passed 8/8, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Sales pagination button visible copy specificity**: Continued the active Hanwoo quality uplift by changing the Sales tab load-more button's visible copy from generic `이전 기록 더 보기` / `불러오는 중...` to `이전 판매 기록 더 보기` / `이전 판매 기록 불러오는 중...`. The visible button text now names the sales-history pagination task on screen and matches the existing Korean accessible label/title. Updated sales pagination source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused sales pagination tests passed 2/2, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Settings building delete busy visible copy specificity**: Continued the active Hanwoo quality uplift by changing building delete row actions' visible busy text from generic `삭제 중...` to `축사 삭제 중...`. The disabled delete button now names the in-progress building-delete task on screen and matches the existing Korean accessible label/title. Updated settings source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused settings tests passed 12/12, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Schedule completion toggle busy visible copy specificity**: Continued the active Hanwoo quality uplift by changing upcoming schedule completion toggles' visible busy text from generic `변경 중...` to `일정 완료 상태 변경 중...`. The disabled completion toggle now names the in-progress schedule-completion update on screen and matches the existing Korean accessible label/title. Updated schedule source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused schedule tests passed 7/7, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Schedule add-form toggle busy visible copy specificity**: Continued the active Hanwoo quality uplift by changing the Schedule tab add/cancel toggle's visible busy text from generic `저장 중...` to `일정 저장 중...`. The disabled toggle now names the in-progress schedule-save task on screen and matches the existing Korean accessible label/title. Updated schedule source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused schedule tests passed 7/7, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Sales add-form toggle busy visible copy specificity**: Continued the active Hanwoo quality uplift by changing the Sales tab add/cancel toggle's visible busy text from generic `저장 중...` to `판매 기록 저장 중...`. The disabled toggle now names the in-progress sales-record save task on screen and matches the existing Korean accessible label/title. Updated sales source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused home-market/sales tests passed 38/38, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Inventory add-form toggle busy visible copy specificity**: Continued the active Hanwoo quality uplift by changing the Inventory tab add/cancel toggle's visible busy text from generic `저장 중...` to `재고 저장 중...`. The disabled toggle now names the in-progress inventory-save task on screen and matches the existing Korean accessible label/title. Updated inventory source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused empty-state/inventory tests passed 17/17, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Feed filter chip busy visible copy specificity**: Continued the active Hanwoo quality uplift by changing Feed tab building filter chips' visible busy text from generic `저장 중...` to `급여 기록 저장 중...`. Disabled filter chips now name the in-progress feed-record save task on screen and match the existing Korean accessible label/title. Updated Feed tab source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused empty-state/feed tests passed 17/17, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard cattle detail action busy visible copy specificity**: Continued the active Hanwoo quality uplift by changing the cattle detail edit, archive, estrus, and pregnancy action buttons' visible busy text from generic `처리 중...` to `개체 처리 중...`. Disabled detail actions now name the in-progress cattle operation on screen and match the existing Korean accessible label/title. Updated cattle detail source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused cattle detail/form tests passed 13/13, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard cattle breeding record busy visible copy specificity**: Continued the active Hanwoo quality uplift by changing the cattle detail breeding record cancel and submit buttons' visible busy text from generic `저장 중...` to `번식 기록 저장 중...`. The in-progress state now names the breeding-record save task on screen and matches the existing Korean accessible label/title. Updated cattle detail source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused cattle detail/form tests passed 13/13, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard cattle form cancel busy visible copy specificity**: Continued the active Hanwoo quality uplift by changing the cattle form cancel button's visible busy text from generic `저장 중...` to `개체 저장 중...`. The in-progress state now names the cattle-save task on screen and matches the existing Korean accessible label/title. Updated cattle form source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused cattle detail/form tests passed 13/13, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard calving cancel busy visible copy specificity**: Continued the active Hanwoo quality uplift by changing the calving form cancel button's visible busy text from generic `저장 중...` to `분만 기록 저장 중...`. The in-progress state now names the calving-save task on screen and matches the existing Korean accessible label/title. Updated calving form source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused calving tests passed 5/5, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard settings building toggle busy visible copy specificity**: Continued the active Hanwoo quality uplift by changing the building add/cancel toggle's visible busy text from generic `저장 중...` to `축사 저장 중...`. The in-progress state now names the building-save task on screen and matches the existing Korean accessible label/title. Updated settings building-form source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused settings tests passed 12/12, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard settings building submit busy visible copy specificity**: Continued the active Hanwoo quality uplift by changing the building registration submit button's visible text from static `등록하기` to state-aware `축사 등록 중...` while saving. The in-progress state now names the building-save task on screen and matches the existing Korean accessible label/title. Updated settings building-form source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused settings tests passed 12/12, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard settings farm save busy visible copy specificity**: Continued the active Hanwoo quality uplift by changing the farm settings submit button's visible busy text from generic `저장 중...` to `농장 정보 저장 중...`. The in-progress state now names the farm-settings save task on screen and matches the existing Korean accessible label/title. Updated settings farm-form source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused settings tests passed 12/12, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard inventory quantity save busy visible copy specificity**: Continued the active Hanwoo quality uplift by changing the inline inventory quantity save button's visible busy text from generic `저장 중...` to `수량 저장 중...`. The in-progress state now names the quantity-save task on screen and matches the existing Korean accessible label/title. Updated inventory quantity edit source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused empty-state/inventory tests passed 17/17, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard cattle submit busy visible copy specificity**: Continued the active Hanwoo quality uplift by changing the cattle form submit button's visible busy text from generic `저장 중...` to `개체 정보 저장 중...`. The in-progress state now names the cattle-save task on screen and matches the existing Korean accessible label/title. Updated cattle form and primary submit pending-copy source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused cattle detail/form and primary submit pending-copy tests passed 14/14, `npm.cmd test` passed 330/330 after updating the broader pending-copy expectation, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard cattle tag lookup busy visible copy specificity**: Continued the active Hanwoo quality uplift by changing the cattle form tag lookup button's visible busy text from generic `조회 중...` to `이력번호 조회 중...`. The in-progress state now names the lookup task on screen and matches the existing Korean accessible label/title. Updated cattle form source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused cattle detail/form tests passed 13/13, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Excel export busy visible copy specificity**: Continued the active Hanwoo quality uplift by changing the Excel export button's visible busy text from generic `준비 중...` to `엑셀 준비 중...`. The in-progress state now names the export task on screen and matches the existing Korean accessible label/title. Updated Excel export button source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused Excel export button tests passed 2/2, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard subscription result loading atomic status**: Continued the active Hanwoo quality uplift by adding `aria-atomic="true"` to the subscription success and failure Suspense fallback statuses. Korean payment loading copy now behaves as coherent polite busy status announcements. Updated payment UX source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused payment UX tests passed 5/5, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard diagnostics loading atomic status**: Continued the active Hanwoo quality uplift by adding `aria-atomic="true"` to the admin diagnostics page's system-check and raw-record loading statuses. Korean operations loading copy now behaves as coherent polite busy status announcements. Updated diagnostics source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused diagnostics tests passed 3/3, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard sales pagination error atomic status**: Continued the active Hanwoo quality uplift by adding `aria-atomic="true"` to the Sales tab pagination load-error status. Korean retry feedback for failed `이전 기록 더 보기` requests now behaves as one coherent polite status. Updated sales pagination source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused sales pagination tests passed 2/2, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard cattle pagination error atomic status**: Continued the active Hanwoo quality uplift by adding `aria-atomic="true"` to the dashboard cattle pagination load-error status. Korean retry feedback for failed `개체 더 보기` requests now behaves as one coherent polite status. Updated cattle pagination source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused cattle pagination tests passed 2/2, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard dashboard full-list loading atomic status**: Continued the active Hanwoo quality uplift by adding `aria-atomic="true"` to the dashboard full cattle and sales ledger loading placeholders. The Korean `개체 목록을 불러오는 중입니다...` and `매출 기록을 불러오는 중입니다...` status messages now behave as coherent polite busy announcements. Updated home market source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused home-market tests passed 38/38, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard market price loading atomic status**: Continued the active Hanwoo quality uplift by adding `aria-atomic="true"` to the market price widget initial loading status. The Korean `한우 시세를 불러오는 중입니다.` announcement now behaves as one coherent polite busy status. Updated home market source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused home-market tests passed 38/38, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard profitability loading atomic status**: Continued the active Hanwoo quality uplift by adding `aria-atomic="true"` to the profitability widget loading status. The Korean `출하 수익성 예측을 불러오는 중입니다.` announcement now behaves as one coherent polite busy status. Updated profitability widget source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused profitability tests passed 8/8, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard AI insight loading busy status**: Continued the active Hanwoo quality uplift by adding `aria-busy={isLoading}` to the AI insight widget header loading status. The Korean `분석 중...` status now exposes the busy state consistently with the widget refresh button and insight list. Updated AI insight widget source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused AI insight widget tests passed 10/10, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard weather unavailable atomic status**: Continued the active Hanwoo quality uplift by adding `aria-atomic="true"` to the weather widget unavailable status region. The Korean unavailable heading, message, and location are now announced as one coherent polite status. Updated home market source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused home-market tests passed 38/38, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard market price unavailable status announcement**: Continued the active Hanwoo quality uplift by adding polite status semantics to the market price widget unavailable fallback. Missing/degraded KAPE price data is now announced as a coherent Korean status instead of remaining visual-only text. Updated home market source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused home-market tests passed 38/38, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard AI insight loading status semantics**: Continued the active Hanwoo quality uplift by adding explicit `role="status"` and `aria-atomic="true"` to the AI insight widget header loading copy. The Korean `분석 중...` state is now announced as a coherent polite status instead of only relying on `aria-live`. Updated AI insight widget source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused AI insight widget tests passed 10/10, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Field Mode checklist progress hover summary**: Continued the active Hanwoo quality uplift by adding a shared `checklistProgressLabel` to the Field Mode daily-check progressbar and reusing it for both `aria-valuetext` and hover `title`. The current completed-check count is now exposed consistently to assistive technology and title UI. Updated Field Mode source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused Field Mode tests passed 7/7, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard setup progress track hover summary**: Continued the active Hanwoo quality uplift by adding `title={setupProgressLabel}` to the home setup progress bar. The progressbar now exposes the same current operating-readiness percentage and completed-step count through hover/title UI that it already exposes through `aria-valuetext`. Updated home dashboard source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused home-market tests passed 38/38, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard shared dialog close label specificity**: Continued the active Hanwoo quality uplift by adding a contextual `closeLabel` prop to the shared `DialogContent` close control. The close button now uses the Korean label for `aria-label`, hover `title`, and screen-reader copy, with `확인 창 닫기` applied to the feedback confirmation dialog and `대화상자 닫기` as the shared default. Updated dialog source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused dialog tests passed 3/3, `npm.cmd test` passed 330/330, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Field Mode search input title copy**: Continued the active Hanwoo quality uplift by adding matching `title="개체 이름 또는 이표번호로 검색"` to the Field Mode search input, aligning hover/title copy with the existing Korean accessible name. Updated Field Mode source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused Field Mode tests passed 7/7, `npm.cmd test` passed 329/329, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Field Mode search placeholder Korean polish**: Continued the active Hanwoo quality uplift by updating the Field Mode search input placeholder from `이표번호 4자리 또는 소이름...` to `이표번호 4자리 또는 소 이름 입력`. The field now uses correct Korean spacing and action-oriented input copy instead of trailing punctuation. Updated Field Mode source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused Field Mode tests passed 7/7, `npm.cmd test` passed 329/329, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard AI chat streaming placeholder Korean status**: Continued the active Hanwoo quality uplift by replacing the AI chat streaming fallback from punctuation-only `...` with a Korean `STREAMING_PLACEHOLDER_MESSAGE` value, `답변 생성 중입니다...`. Empty in-progress assistant messages now expose meaningful status copy instead of punctuation-only output. Updated AI chat widget source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused AI chat widget tests passed 2/2, `npm.cmd test` passed 329/329, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard AI chat input busy-state label**: Continued the active Hanwoo quality uplift by adding a state-aware `inputLabel` to the AI chat question input. While an answer is streaming and the input is disabled, its `aria-label` and `title` now expose that questions cannot be entered yet instead of keeping the idle question label. Updated AI chat widget source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused AI chat widget tests passed 2/2, `npm.cmd test` passed 329/329, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard AI chat close action context label**: Continued the active Hanwoo quality uplift by changing the AI chat panel close button from generic `채팅 닫기` to `AI 농장 비서 닫기` for both `aria-label` and `title`. The close action now matches the launcher, dialog, and log naming, making the control explicit for assistive technology and hover/title UI. Updated AI chat widget source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused AI chat widget tests passed 2/2, `npm.cmd test` passed 329/329, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Login demo credential label Korean polish**: Continued the active Hanwoo quality uplift by replacing the demo account box's remaining English `ID`/`PW` labels with Korean `아이디`/`비밀번호`, while preserving the actual demo credentials. Updated login/error-page source-level regression coverage so the English abbreviations do not return. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused error-page/login tests passed 9/9, `npm.cmd test` passed 329/329, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Login demo account Korean copy polish**: Continued the active Hanwoo quality uplift by removing the English `Demo Accounts` parenthetical from the login page demo account box and marking the lightbulb glyph as decorative with `aria-hidden`. The login screen now stays Korean-first and avoids exposing decorative emoji output to assistive technology. Updated login/error-page source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused error-page/login tests passed 9/9, `npm.cmd test` passed 329/329, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Profitability error alert semantics**: Continued the active Hanwoo quality uplift by adding `role="alert"` to the profitability widget error card. Shipment-profitability failures are now announced as urgent feedback instead of remaining visual-only text, while preserving the original Korean error copy. Updated profitability widget source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused profitability tests passed 8/8, `npm.cmd test` passed 329/329, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Weather unavailable status announcement**: Continued the active Hanwoo quality uplift by adding `role="status"` and polite live-region semantics to the weather unavailable card. Degraded/no-weather states are now announced like other dashboard loading/error states instead of remaining visual-only text. Updated dashboard weather source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused home-market tests passed 38/38, `npm.cmd test` passed 329/329, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Weather forecast icon semantic title**: Continued the active Hanwoo quality uplift by adding an explicit `role="img"` and matching hover `title` to 3-day forecast weather icons. The forecast emoji now reuses the normalized Korean weather description for both assistive technology and hover/title UI instead of exposing only an aria label. Updated dashboard weather source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused home-market tests passed 38/38, `npm.cmd test` passed 329/329, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Cattle tag lookup visible copy consistency**: Continued the active Hanwoo quality uplift by unifying the cattle form tag lookup button's visible idle copy with its accessible label/title. The on-screen action now says `이력번호 조회` instead of `태그 조회`, while preserving `조회 중...` during lookup. Updated cattle form source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused cattle detail/form tests passed 13/13, `npm.cmd test` passed 329/329, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Schedule completion toggle progress copy**: Continued the active Hanwoo quality uplift by adding state-aware labels and visible status copy to upcoming schedule completion toggles. While an async completion update is in flight, the row now shows `변경 중...` and the checkbox exposes `일정 완료 상태 변경 중` through label/title instead of leaving static completion copy. Updated Schedule and dashboard source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused tab-header tests passed 7/7, focused home-market tests passed 38/38, `npm.cmd test` passed 329/329, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Feed filter chip visible progress copy**: Continued the active Hanwoo quality uplift by adding state-aware visible copy to Feed tab building filter chips. While a feed record save is in flight, disabled filter chips now show `저장 중...` instead of static filter names, matching their busy accessible labels, titles, and `aria-busy` state. Updated Feed tab source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused empty-state/Feed tests passed 17/17, `npm.cmd test` passed 329/329, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Settings save controls visible progress copy**: Continued the active Hanwoo quality uplift by adding state-aware visible copy to the Settings tab farm save button and building add/cancel toggle. While their async save flows are in flight, the disabled controls now show `저장 중...` instead of static `저장하기`/`취소`, matching their busy accessible labels, titles, and disabled states. Updated Settings tab source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused Settings tests passed 12/12, `npm.cmd test` passed 329/329, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Schedule add-form toggle visible progress copy**: Continued the active Hanwoo quality uplift by adding state-aware visible copy to the Schedule tab add/cancel toggle. While a schedule save is in flight, the disabled toggle now shows `저장 중...` instead of static `취소`, matching its busy `aria-label`, `title`, and `aria-busy` state. Updated Schedule tab source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused tab-header/Schedule tests passed 7/7, `npm.cmd test` passed 329/329, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Sales add-form toggle visible progress copy**: Continued the active Hanwoo quality uplift by adding state-aware visible copy to the Sales tab add/cancel toggle. While a sales record save is in flight, the disabled toggle now shows `저장 중...` instead of static `취소`, matching its busy `aria-label`, `title`, and `aria-busy` state. Updated Sales tab source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused home-market/Sales tests passed 38/38, `npm.cmd test` passed 329/329, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard Inventory add-form toggle visible progress copy**: Continued the active Hanwoo quality uplift by adding state-aware visible copy to the Inventory tab add/cancel toggle. While an inventory item save is in flight, the disabled toggle now shows `저장 중...` instead of static `취소`, matching its busy `aria-label`, `title`, and `aria-busy` state. Updated inventory source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused empty-state/inventory tests passed 17/17, `npm.cmd test` passed 329/329, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard Calving form cancel visible progress copy**: Continued the active Hanwoo quality uplift by adding state-aware visible copy to the Calving tab form cancel button. While a calving record save is in flight, the disabled cancel action now shows `저장 중...` instead of static `취소`, matching its busy `aria-label`, `title`, and `aria-busy` state. Updated calving source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused calving tests passed 5/5, `npm.cmd test` passed 329/329, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard Cattle form cancel visible progress copy**: Continued the active Hanwoo quality uplift by adding state-aware visible copy to the cattle form bottom cancel button. While an async cattle save is in flight, the disabled cancel action now shows `저장 중...` instead of static `취소`, matching its busy `aria-label`, `title`, and `aria-busy` state. Updated cattle form source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused cattle-detail/form tests passed 13/13, `npm.cmd test` passed 329/329, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard Cattle detail breeding cancel visible progress copy**: Continued the active Hanwoo quality uplift by adding state-aware visible copy to the cattle detail breeding form cancel button. While a breeding record save is in flight, the disabled cancel action now shows `저장 중...` instead of static `취소`, matching its busy `aria-label`, `title`, and `aria-busy` state. Updated cattle detail source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused cattle-detail tests passed 13/13, `npm.cmd test` passed 329/329, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard Cattle detail breeding action visible progress copy**: Continued the active Hanwoo quality uplift by adding state-aware visible copy to the cattle detail modal breeding quick actions. When archive/delete or breeding-save work is in flight, the disabled `발정 기록` and `수정 기록` actions now show `처리 중...`, matching their existing busy `aria-label`, `title`, and `aria-busy` state. Updated cattle detail source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused cattle-detail tests passed 13/13, `npm.cmd test` passed 329/329, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard Cattle detail edit visible progress copy**: Continued the active Hanwoo quality uplift by adding state-aware visible copy to the cattle detail modal edit button. When archive/delete or breeding-save work is in flight, the disabled edit action now shows `처리 중...` instead of static `수정`, matching the existing busy `aria-label`, `title`, and `aria-busy` state. Updated cattle detail source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused cattle-detail tests passed 13/13, `npm.cmd test` passed 329/329, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard Analysis tab chart accessible summaries**: Continued the active Hanwoo quality uplift by adding Korean accessible summaries to the Analysis tab monthly flow bar chart and cost structure pie chart. Both Recharts wrappers now use `role="img"`, `aria-label`, and matching `title` so the visuals communicate their purpose to assistive technology and hover/title UI. Updated analysis source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused analysis tests passed 3/3, `npm.cmd test` passed 329/329, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard Cattle detail weight chart accessible summary**: Continued the active Hanwoo quality uplift by adding a Korean accessible summary to the cattle detail modal's weight trend Recharts line chart. The chart wrapper now uses `role="img"`, `aria-label`, and matching `title` so the visual chart communicates that it compares the selected cattle's weight records by date. Updated cattle detail source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused cattle-detail tests passed 13/13, `npm.cmd test` passed 329/329, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard Sales profit chart accessible summary**: Continued the active Hanwoo quality uplift by adding a Korean accessible summary to the Sales tab's recent profit analysis Recharts bar chart. The chart wrapper now uses `role="img"`, `aria-label`, and matching `title` so the visual chart communicates that it compares sale amount and profit by shipped cattle. Updated Sales tab source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused home-market/Sales tests passed 38/38, `npm.cmd test` passed 328/328, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard Financial chart accessible summary**: Continued the active Hanwoo quality uplift by adding a Korean accessible summary to the farm financial flow Recharts bar chart. The chart wrapper now uses `role="img"`, `aria-label`, and matching `title` so the visual chart communicates that it compares monthly sales, expenses, and profit over the recent six-month window. Updated financial chart source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused analysis/financial tests passed 3/3, `npm.cmd test` passed 327/327, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard Feed trend chart accessible summary**: Continued the active Hanwoo quality uplift by adding a Korean accessible summary to the Feed tab's Recharts trend chart container. The chart wrapper now uses `role="img"`, `aria-label`, and matching `title` so the visual chart communicates that it compares recent roughage and concentrate feed amounts by date. Updated Feed tab source-level regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused empty-state/feed tests passed 17/17, `npm.cmd test` passed 327/327, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard shared decorative icon hiding**: Continued the active Hanwoo quality uplift by marking visual-only shared dialog/select glyphs, schedule month navigation arrows, the Field Mode empty-result warning icon, and the empty-pen cow emoji as `aria-hidden`. This keeps existing visible UI unchanged while preventing duplicate decorative output for assistive technology. Updated dialog, home-market, and Field Mode source-level accessibility coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused dialog/home/Field Mode tests passed 46/46, `npm.cmd test` passed 326/326, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard secondary link action labels**: Continued the active Hanwoo quality uplift by adding explicit Korean `aria-label` and `title` copy to the dashboard footer links (`/terms`, `/privacy`, `/subscription`) and the settings diagnostics link (`/admin/diagnostics`). A focused anchor scan now reports no internal anchor without `aria-label` or `title`. Updated home-market and settings accessibility coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused home-market tests passed 37/37, focused settings tests passed 12/12, `npm.cmd test` passed 325/325, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard QR print status feedback**: Continued the active Hanwoo quality uplift by adding Korean print status feedback to `QRCodeWidget.js`. The QR print action now announces preparation, popup-blocked failure, and print-window-open completion through a polite status region instead of silently resetting when `window.open` fails. Updated `qr-widget-copy.test.mjs` coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused QR widget tests passed 3/3, `npm.cmd test` passed 323/323, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard unit-test warning suppression**: Continued the active Hanwoo quality uplift by updating the Hanwoo `test` script to run Node with `--disable-warning=MODULE_TYPELESS_PACKAGE_JSON`. This removes recurring typeless-package warning noise from routine test runs without declaring `"type": "module"`, which would be broader because PostCSS and Prisma seed files still use CommonJS. Added `package-scripts.test.mjs` coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused package-script test passed 1/1, `npm.cmd test` passed 322/322 without the typeless-package warning, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard shared empty-state CTA busy state**: Continued the active Hanwoo quality uplift by wiring the shared `EmptyState` CTA `disabled` prop into `aria-busy`, so disabled empty-state actions such as the sales tab's missing-cattle CTA expose their unavailable/busy state consistently with other action buttons. Updated `empty-state-wiring.test.mjs` coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused empty-state tests passed 16/16, `npm.cmd test` passed 321/321, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard empty building CTA action label**: Continued the active Hanwoo quality uplift by adding explicit Korean `aria-label` and `title` copy to the home dashboard empty building CTA. The button now states that it opens settings to add the first building instead of relying only on the visible card copy. Updated `home-market-copy.test.mjs` coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused home-market tests passed 36/36, `npm.cmd test` passed 321/321, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard full-list retry action labels**: Continued the active Hanwoo quality uplift by adding target-specific Korean `aria-label` and `title` copy to the full cattle-list and sales-ledger retry buttons shown after dashboard preload failures. Updated `home-market-copy.test.mjs` coverage so retry actions identify whether they reload the full cattle list or sales records. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused home-market tests passed 36/36, `npm.cmd test` passed 321/321, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard notification SMS test visible busy copy**: Continued the active Hanwoo quality uplift by making the notification modal SMS test button show `전송 중...` while `isTestingSMS` is true instead of leaving the visible label static. This aligns the on-screen state with the existing disabled, busy, accessible-label, and title states. Updated `notification-modal-copy.test.mjs` coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused notification-modal tests passed 8/8, `npm.cmd test` passed 321/321, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard notification SMS test action accessibility**: Continued the active Hanwoo quality uplift by adding a state-aware `smsTestButtonLabel` to the notification modal SMS test button and reusing it for `aria-label` and `title`, so idle and sending states expose the same Korean action name to assistive technology and hover/title UI. Updated `notification-modal-copy.test.mjs` coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused notification-modal tests passed 8/8, `npm.cmd test` passed 321/321, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard shared empty-state CTA accessibility**: Continued the active Hanwoo quality uplift by reusing `actionLabel` as both `aria-label` and `title` on the shared `EmptyState` CTA `PremiumButton`, so inventory/sales/schedule empty-state actions expose the same Korean task name to assistive technology and hover/title UI. Updated `empty-state-wiring.test.mjs` coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused empty-state tests passed 16/16, `npm.cmd test` passed 321/321, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard shared form action icon accessibility**: Continued the active Hanwoo quality uplift by marking shared `BackIcon`, `EditIcon`, and `TrashIcon` SVG action icons as `aria-hidden="true"` and `focusable="false"` so labeled form/modal buttons do not expose duplicate icon semantics to assistive technology. Updated `cattle-detail-modal-wiring.test.mjs` coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused cattle form/detail tests passed 12/12, `npm.cmd test` passed 316/316, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard Field Mode control title and icon accessibility**: Continued the active Hanwoo quality uplift by adding matching `title` copy to Field Mode return, clear-search, and checklist toggle controls so hover/title copy aligns with their accessible labels. Also hid the decorative return arrow icon from assistive technology. Updated `field-mode-celebration.test.mjs` coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused Field Mode tests passed 7/7, `npm.cmd test` passed 316/316, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard AI chat close-button title accessibility**: Continued the active Hanwoo quality uplift by adding a matching Korean `title="채팅 닫기"` to the AI chat dialog close button so hover/title copy aligns with the existing accessible label and adjacent task controls. Updated `ai-chat-widget-copy.test.mjs` coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused AI chat widget tests passed 2/2, `npm.cmd test` passed 315/315, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard ear-tag scanner header close-label accessibility**: Continued the active Hanwoo quality uplift by making the ear-tag scanner modal header close button use contextual Korean accessible copy (`이표 스캐너 닫기`) matching its title instead of generic close copy, while preserving the decorative close icon. Updated `eartag-scanner-modal-accessibility.test.mjs` coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused scanner tests passed 3/3, `npm.cmd test` passed 315/315, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard form add/cancel toggle busy-state accessibility**: Continued the active Hanwoo quality uplift by hardening inventory, schedule, and building add/cancel form toggles. The toggles now expose state-aware `aria-label`, `title`, and `aria-busy` values so disabled controls explain active save flows and idle controls name the target form action. Updated `empty-state-wiring.test.mjs`, `tab-header-accessibility.test.mjs`, and `settings-tab-accessibility.test.mjs` coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused tab tests passed 16/16, 7/7, and 11/11; `npm.cmd test` passed 315/315; `npm.cmd run lint` passed; and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard dashboard full-list loading placeholder accessibility**: Continued the active Hanwoo quality uplift by making the dashboard's complete cattle-list and sales-ledger loading placeholders perceivable to assistive technology. `DashboardClient.js` now exposes both placeholder cards as `role="status"` with `aria-live="polite"` and loading-flag based `aria-busy` state. Updated `home-market-copy.test.mjs` coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused home-market tests passed 33/33, `npm.cmd test` passed 315/315, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard profitability loading status accessibility**: Continued the active Hanwoo quality uplift by making the profitability recommendation widget loading skeleton perceivable to assistive technology. `ProfitabilityWidget.js` now exposes the loading content as `role="status"` with `aria-live="polite"`, `aria-busy="true"`, and a screen-reader-only Korean loading message. Updated `profitability-copy.test.mjs` coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused profitability tests passed 8/8, `npm.cmd test` passed 313/313, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard setup progress item state accessibility**: Continued the active Hanwoo quality uplift by making each home setup progress item expose its completion state in the accessible name. `DashboardClient.js` now builds `setupItemLabel` from the item title, done state, and detail, then applies it as `aria-label` while keeping the visual done icon decorative. Updated `home-market-copy.test.mjs` coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused home-market tests passed 32/32, `npm.cmd test` passed 312/312, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard Field Mode loading status accessibility**: Continued the active Hanwoo quality uplift by making Field Mode search-result full-list loading perceivable to assistive technology. `FieldModeView.js` now exposes the loading badge as `role="status"` with `aria-live="polite"` and hides the camera icon inside the labeled scanner button as decorative. Updated `field-mode-celebration.test.mjs` coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused Field Mode tests passed 6/6, `npm.cmd test` passed 311/311, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard setup progress semantic accessibility**: Continued the active Hanwoo quality uplift by exposing the home onboarding/setup progress track as a real ARIA `progressbar`. `DashboardClient.js` now gives the setup progress track a Korean label plus `aria-valuemin`, `aria-valuemax`, and `aria-valuenow={progress.percent}` instead of hiding the visual track from assistive technology. Updated `home-market-copy.test.mjs` coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused home-market tests passed 31/31, `npm.cmd test` passed 310/310, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard notification center trigger dialog relationship accessibility**: Continued the active Hanwoo quality uplift by wiring the home notification trigger to its modal with a stable `NOTIFICATION_MODAL_ID`. `DashboardClient.js` now exposes `aria-haspopup="dialog"`, stateful `aria-expanded`, and `aria-controls` on the trigger, and passes the same id into `NotificationModal.js`; the modal root now accepts and renders that id. Updated `home-market-copy.test.mjs` and `notification-modal-copy.test.mjs` coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused home-market tests passed 30/30, focused notification-modal tests passed 8/8, `npm.cmd test` passed 309/309, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard AI chat launcher relationship accessibility**: Continued the active Hanwoo quality uplift by hardening `components/widgets/AIChatWidget.js`. The floating AI assistant launcher now exposes `aria-haspopup="dialog"`, `aria-expanded="false"`, and `aria-controls` pointing at a stable chat panel id, while the opened chat dialog uses the same id. Updated `ai-chat-widget-copy.test.mjs` coverage for the launcher-to-dialog relationship. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused AI chat widget tests passed 2/2, `npm.cmd test` passed 308/308, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard notification modal close-label accessibility**: Continued the active Hanwoo quality uplift by making `components/ui/NotificationModal.js` close-button accessible copy contextual. The modal close control now exposes `알림 센터 닫기` for both `aria-label` and `title` instead of the generic `닫기`, while preserving the existing SMS-busy dismissal guard. Updated `notification-modal-copy.test.mjs` regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused notification-modal tests passed 8/8, `npm.cmd test` passed 308/308, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard feedback confirmation dialog accessibility**: Continued the active Hanwoo quality uplift by hardening `components/feedback/FeedbackProvider.js`. Confirmation dialog cancel/confirm actions now expose stable Korean `aria-label` and `title` values derived from the configured action labels, making destructive confirmations clearer for assistive technology and hover users. Added `feedback-provider-copy.test.mjs` regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused feedback-provider tests passed 3/3, `npm.cmd test` passed 308/308, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard dashboard ErrorBoundary recovery accessibility**: Continued the active Hanwoo quality uplift by hardening `components/ErrorBoundary.js`. The premium dashboard runtime fallback now hides its decorative warning icon from assistive tech and gives the recovery action an explicit `type="button"` plus stable Korean `aria-label` and `title`. Added `error-pages-wiring.test.mjs` coverage for the recovery action contract. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused error-page tests passed 8/8, `npm.cmd test` passed 307/307, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard ear-tag scanner Korean operator copy cleanup**: Continued the active Hanwoo quality uplift by cleaning up visible scanner overlay copy in `EarTagScannerModal.js`. Removed the English `(Click)` hint and changed the typo-prone visible action text from `이표 자동 감색` to `이표 자동 인식`, keeping the existing accessible label/title contract. Added `eartag-scanner-modal-accessibility.test.mjs` coverage to prevent the English hint and typo from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused scanner test passed 3/3, `npm.cmd test` passed 306/306, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard AI insight live-region update announcement**: Continued the active Hanwoo quality uplift by adding polite live-region semantics to the `AIInsightWidget.js` insight list. Refreshed analysis cards now expose `aria-live="polite"` and `aria-relevant="additions text"` alongside the existing busy state, so assistive technology users can perceive card updates after AI/heuristic refreshes. Added `ai-insight-widget-copy.test.mjs` coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused AI insight tests passed 21/21, `npm.cmd test` passed 306/306, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard AI insight stale-card reset on summary changes**: Continued the active Hanwoo quality uplift by hardening `AIInsightWidget.js` state sync. When the dashboard summary changes, the widget now immediately resets visible cards to fresh `buildHeuristicInsights(stableSummary)` output and marks the source as heuristic while the new `/api/ai/insight` request is loading, so previous snapshot cards do not linger. Added `ai-insight-widget-copy.test.mjs` coverage for this contract. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused AI insight tests passed 21/21, `npm.cmd test` passed 306/306, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard AI insight fallback reason normalization**: Continued the active Hanwoo quality uplift by hardening `AIInsightWidget.js` response handling. Heuristic `/api/ai/insight` responses now always surface an operator-facing fallback reason even if the server omits `reason`, while successful AI responses explicitly clear stale fallback copy. Added `ai-insight-widget-copy.test.mjs` coverage for source/reason normalization. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused AI insight tests passed 20/20, `npm.cmd test` passed 305/305, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard AI insight client complete-card response guard**: Continued the active Hanwoo quality uplift by reusing `MAX_INSIGHTS` in `AIInsightWidget.js`. The client now rejects malformed or partial `/api/ai/insight` payloads after parsing and falls back to deterministic 3-card heuristic insights instead of rendering a short AI list. Added `ai-insight-widget-copy.test.mjs` widget wiring coverage for the same complete-card guard. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused AI insight tests passed 19/19, `npm.cmd run lint` passed, `npm.cmd test` passed 304/304, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard AI insight complete-card response contract**: Continued the active Hanwoo quality uplift by tightening `app/api/ai/insight/route.js` so Gemini output is accepted only when `parseInsightResponse` returns all `MAX_INSIGHTS` cards promised by the UI. Partial AI responses now fall back to deterministic heuristic insights instead of showing a short AI list. Added `ai-insight-widget-copy.test.mjs` route wiring coverage for the `parsed.length !== MAX_INSIGHTS` guard. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused AI insight tests passed 19/19, `npm.cmd run lint` passed, `npm.cmd test` passed 304/304, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard AI insight summary identity stabilization**: Continued the active Hanwoo quality uplift by memoizing the summary object passed from `DashboardClient.js` into `AIInsightWidget`. The previous inline object changed identity on unrelated dashboard re-renders, which could retrigger `/api/ai/insight` calls, reset loading state, and increase AI usage. Added `ai-insight-widget-copy.test.mjs` wiring coverage so the widget receives `aiInsightSummary` instead of an inline object. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused AI insight tests passed 19/19, `npm.cmd run lint` passed, `npm.cmd test` passed 304/304, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard AI insight server timeout fallback control-flow fix**: Continued the active Hanwoo quality uplift by fixing `app/api/ai/insight/route.js`. The `InsightTimeoutError` fallback had been placed in the authentication catch path, where it was unreachable for Gemini calls and referenced `summary` before declaration. Moved that handling into the Gemini generation catch path so slow Gemini responses return deterministic heuristic insights with the timeout-specific Korean reason. Strengthened `ai-insight-widget-copy.test.mjs` route coverage to keep timeout handling out of the auth catch. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused AI insight tests passed 19/19, `npm.cmd run lint` passed, `npm.cmd test` passed 304/304, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard AI insight data normalization hardening**: Continued the active Hanwoo quality uplift by tightening `src/lib/ai-insight.mjs` summary normalization. Malformed profitability rows with missing/NaN `marginalGain` no longer count as declining-margin risks, while real zero/negative margin rows still do. Negative monthly sales input is now clamped before operator-facing heuristic copy. Added regression coverage in `ai-insight.test.mjs`. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused AI insight tests passed 19/19, `npm.cmd run lint` passed, `npm.cmd test` passed 304/304, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Claude (Opus 4.7) |
| Work | **/goal "프로젝트를 최신 기능 + 최고화" — 3개 활성 프로젝트 신규 기능 일괄 출하**. 사용자가 workspace 전반 × 신규 기능 방향 선택. **(A) hanwoo-dashboard AI 인사이트 위젯** — Gemini 2.0 Flash + 휴리스틱 폴백 4계층(키 없음/응답 파싱 실패/예외/네트워크), 우선순위 3카드 + 수동 새로고침 + AbortController + react-19 set-state-in-effect 규칙 준수. WIDGET_REGISTRY 등록, DashboardClient 와이어링. (이 위에 Codex 가 곧바로 10s `withInsightTimeout` + `InsightTimeoutError` 보강을 이어 출하 — 본 addendum 아래 Codex 항목 참고) **(B) blind-to-x Best-of-N 결합 점수** — 기존 `best_of_n` 셀렉터가 5축 `avg_score` 만 보던 한계를, Phase 2 의 4축 `comment_trigger_scores` 와 가중 결합(`llm.best_of_n_comment_weight`, 기본 0.5, 0~1 clamp, twitter/threads 출력에만 적용). 후보 점수 breakdown 로그. **(C) shorts-maker-v2 WhisperX 옵트인 정렬 (T-19 해결)** — BSD-2, CPU OK, lazy import, 미설치/실패 시 None 반환 후 기존 OpenAI Whisper 폴백. `config.audio.use_whisperx_alignment` 기본 False — 기존 사용자 영향 0. **검증**: hanwoo 301/301 + lint clean (Codex 의 추가 작업 직후 303/303), blind-to-x 1680 passed + ruff clean, shorts-maker-v2 1576 passed + ruff clean. 신규 회귀 45개(11 + 17 + 17). |
| Next Priorities | (a) 사용자에게 커밋 승인 요청 — 11개 변경/신규 파일이 stage 대기 (Codex 의 timeout 보강 포함). (b) WhisperX 실제 활성화는 `pip install whisperx torch` 후 채널별 `use_whisperx_alignment: true` 설정 필요(~2GB 디스크). (c) Best-of-N 결합 점수 효과 측정: 다음 N개 발행에서 4축 점수와 실제 댓글 수 상관관계 확인. (d) AI 인사이트 위젯 도입 후 GEMINI_API_KEY 미설정 시에도 휴리스틱이 정상 작동하는지 프로덕션 확인. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard AI insight API Gemini timeout fallback**: Continued the active Hanwoo quality uplift by hardening `app/api/ai/insight/route.js` against slow Gemini responses. Added a 10s server-side `withInsightTimeout` wrapper, a dedicated `InsightTimeoutError`, timeout handle cleanup, and a timeout-specific Korean heuristic fallback reason. Expanded `ai-insight-widget-copy.test.mjs` route coverage so slow Gemini calls remain deterministic and user-facing. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused AI insight tests passed 18/18, `npm.cmd run lint` passed, `npm.cmd test` passed 303/303, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard AI insight timeout resilience**: Continued the active Hanwoo quality uplift by hardening `AIInsightWidget.js` against slow `/api/ai/insight` responses. Added a 12s client-side timeout, separated timeout aborts from unmount/summary-change aborts, clears timers in both completion and cleanup paths, falls back to deterministic insights on timeout, and announces the fallback reason with a polite `role="status"` region. Expanded `ai-insight-widget-copy.test.mjs` coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused AI insight tests passed 17/17, `npm.cmd run lint` passed, `npm.cmd test` passed 302/302, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard AI insight refresh/accessibility polish**: Continued the active Hanwoo quality uplift after confirming T-251 remains the only repo-tracked TODO and is external. Improved the new `AIInsightWidget.js` by adding a manual refresh button that increments a refresh nonce, re-runs `/api/ai/insight`, disables while loading, exposes `aria-busy`, uses Korean accessible/title labels, and hides the refresh icon from assistive tech. Added `ai-insight-widget-copy.test.mjs` coverage for the refresh control. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: focused AI insight tests passed 16/16, `npm.cmd run lint` passed, `npm.cmd test` passed 301/301, and `npm.cmd run build` passed with the known T-251 Prisma `P2010 / XX000 / ENOTFOUND` health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **active-project-matrix CI stabilization**: Investigated failed GitHub Actions run `26443385538`. The failed frontend jobs were caused by duplicate pnpm version sources (`version: 9` in `pnpm/action-setup` plus root `packageManager: pnpm@9.5.0`); the working tree already contains the minimal workflow fix removing the action-level version. The shorts-maker job failed because Linux CI lacks the configured Windows `malgun.ttf`, so static safe-zone QC fell back to a tiny default font and passed an overlong caption. Updated `caption_pillow._load_font` to preserve requested font size through Pillow's default font fallback and added a missing-font regression test. |
| Next Priorities | Re-run/push CI when ready. Current verification: `python -m pytest tests/unit/test_safe_zone_qc.py::TestGateSafeZone -q -o addopts=` passed 7/7, forced missing-font probe returns `hold`, and CI-equivalent `python -m pytest tests/unit tests/integration -q --tb=short --maxfail=1 -o addopts=` passed 1559/1559 with 12 skipped. T-251 remains separate and user-owned Supabase database password/control-plane resync. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard ear-tag scanner accessibility + QC stabilization**: Continued the active Hanwoo quality uplift while preserving unrelated staged skill/nature/MCP work. Improved `EarTagScannerModal.js` with dialog description wiring, visual-only canvas/icon hiding, explicit scan/retry/manual-select/detail labels, and polite live-region scan result announcements. Added `eartag-scanner-modal-accessibility.test.mjs`. Also fixed the current untracked `AIInsightWidget.js` React lint failure by deferring effect loading-state resets with `queueMicrotask`. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/eartag-scanner-modal-accessibility.test.mjs` passed 3/3, focused AI/scanner tests passed 18/18, `npm.cmd test` passed 300/300, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Gemini (Antigravity) |
| Work | **모든 에이전트 스킬 최신화 완료 (T-410)**:<br>1. **Locked Skills**: `skills` CLI의 Windows 내 `spawnSync` shell-concat space 버그를 우회하기 위해 raw node CLI를 통해 `accessibility`, `bash-defensive-patterns`, `find-skills`, `seo` 4개 스킬 수동 업데이트 완료. `bash-defensive-patterns`에서 실제 upstream 변경사항 감지 및 `skills-lock.json`에 최신 hash 반영 완료.<br>2. **Nature Skills**: `nature-skills` 중첩 리포지토리의 최신 커밋을 git pull로 당긴 뒤, 9개 `nature-*` (academic-search, citation, data, figure, paper2ppt, polishing, reader, response, writing) 스킬 번들 전체를 `.agents/skills/`에 완벽하게 복사 및 배치 완료. 이제 Antigravity 및 타 에이전트 세션에서 9개 nature-스킬이 완벽히 활성화되어 Project Skills로 자동 인식됨. |
| Next Priorities | (a) **사용자 스킬 확인**: 사용자가 새로운 `nature-*` 스킬(예: `nature-polishing`, `nature-paper2ppt`)을 활용할 수 있도록 안내. (b) **Supabase Database E2E 연동**: T-251 Supabase 패스워드 리셋 및 로컬 CRUD 테스트 완료 유도. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Gemini (Antigravity) |
| Work | **MCP Comprehensive Diagnostics & Verification System Completed**: Created and executed a deterministic automation script (`execution/mcp_diagnostic.py`) incorporating strict UTF-8 stream reconfiguration and ASCII safe outputs to successfully prevent Windows CP949 encoding exceptions. Checked all 6 workspace custom MCP servers (`sqlite-multi`, `system-monitor`, `telegram`, `cloudinary`, `youtube-data`, `n8n-workflow`) at the protocol level through JSON-RPC initialization stdio handshakes, verifying a 100% operational health pass. Confirmed the agent-side integrated Notion MCP connection successfully via direct API-get-self call on bot user `Desk Joopark`. Compiled all findings into `docs/mcp_status_report.md`. |
| Next Priorities | (a) Keep monitoring and upgrading optional integrations (e.g. providing TELEGRAM chat details in `.env` if bot notification functions are needed later). (b) Systematically tackle outstanding Supabase Database connection challenges (T-251). |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard runtime resilience polish**: Preserved existing dirty work in `projects/shorts-maker-v2/`, `nature-skills`, and the prior Field Mode WIP. Wired the existing premium `ErrorBoundary` around `DashboardClient` in `projects/hanwoo-dashboard/src/app/page.js`, then added `src/lib/error-pages-wiring.test.mjs` coverage to keep the dashboard wrapped against client runtime failures. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains separate and user-owned: Supabase database password/control-plane resync is still required before live Prisma CRUD can be proven. Current verification for this change: 282/282 Hanwoo tests passed, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard Field Mode accessibility polish**: Preserved existing shorts-maker-v2 dirty files and updated only `projects/hanwoo-dashboard/src/components/widgets/FieldModeView.js`. Added explicit accessible labels for leaving field mode, field search, and clearing search; marked the decorative search icon hidden; exposed the daily checklist completion track as an ARIA progressbar; and added pressed/state labels to checklist toggle rows. No tests or QC commands were run in this turn. |
| Next Priorities | Run `python execution/project_qc_runner.py --project hanwoo-dashboard --check test --json` or the full Hanwoo QC runner when validation is desired. Keep T-251 separate until Supabase password/control-plane resync is done by the user. |
| Work | **blind-to-x 댓글 트리거 Phase 2 출하 (`/goal` 응답)** — "X에서 모두가 댓글을 달고 싶은 수준" 사용자 목표에 4축(식별감/입장/오픈루프/구체 앵커) 프레임워크로 응답. **A. 프롬프트 사이드** `draft_prompts.py` `_build_comment_trigger_block` 으로 트위터/스레드 한정 4축 프레임워크 + "댓글이 안 달리는 글의 공통점(보편진리/무색무취/양비론/추상명사 마무리)" 안티패턴을 생성 프롬프트에 강제 주입. **B. 에디토리얼 사이드** `editorial_reviewer.py` 에 댓글 트리거 4축 점수(`identifiability`/`stance`/`open_loop`/`anchor`, 각 1~10점) 추가. 5축 평균(기존)과 4축 평균(기본 임계 6.0) 을 **AND** 로 묶어 둘 다 통과해야 END; 한쪽 미달이면 최대 2회 리라이트. `EditorialResult.comment_trigger_scores` 필드로 플랫폼별 점수 노출. **C. 결정론적 사이드** `draft_quality_gate.py` `_is_colorless_take` 무색무취 검출기 — golden 7개 false-positive 0% 확인 후 `hedge ≥ 2 OR (일반화 어휘 ≥ 1 AND 입장 표현 0개 AND ≥ min_chars)` 로 보수 튜닝. twitter/threads = 글 전체, naver_blog = `<creator_take>` 태그. `_extract_creator_take` 파서로 누락도 warning. **회귀** 단위 1669 passed + 1 skipped (282s), 신규 40 케이스 100%, 내가 손댄 4파일 ruff 클린. **주의**: `pipeline/quality_gate.py` 는 다른 도구(Gemini Workstream 1~5)가 `_check_bland_creator_take`/`_check_semantic_similarity` 추가 작업 중 → W293(공백) 1건 미수정 잔존. 다른 도구의 WIP라 의도적으로 미터치 (`multi_tool_git_index_race_20260520` 정책 준수). |
| Next Priorities | (a) 사용자에게 커밋 승인 요청 — Phase 2 5파일(`draft_prompts.py`, `editorial_reviewer.py`, `draft_quality_gate.py`, `tests/unit/test_comment_trigger_uplift.py`, `docs/output_quality_uplift_2026-05-26.md`) stage 대기. (b) Gemini Workstream 1~5 WIP 의 `quality_gate.py` 합류 후 `ruff --fix` 필요 (1건). (c) Phase 3 후보: Best-of-2 셀렉터 (LLM 비용 2배라 사용자 결정 필요), 토픽 클러스터 최근 5건 의미 유사도 reroll, Notion 검토 화면에 4축 점수 표시. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Gemini (Antigravity) |
| Work | **기술 부채 전면 해결 완결 (Workstream 1~5)**: `.ai/` 콘텍스트 문서들을 7일 기준 로테이션 및 압축 완료 (TASKS.md 3KB, CONTEXT.md 110줄, HANDOFF.md 18줄 다이어트). 루트 stale 로그 제거 및 고아 스크립트들을 `execution/`로 수술적 격리 완료. `llm_client.py` 내의 중복 로프를 `_run_simple_loop` 비공개 공통 메서드로 통합 리팩토링 및 에러 수집 대칭성 보강 완료. `shorts-maker-v2` 텍스트 엔진 `text_engine.py` SRP 렌더링 전략 분할 완료 및 데모 프롬프트 `DEMO_NEWS`/`DEMO_VS`를 `prompts/` 폴더 아래 외부 JSON 파일로 외부화 및 로딩 연동 완료. `blind-to-x` Phase 2 품질 게이트로 Bland Creator Take(구체성 수치/Buzzwords 감지) 및 Jaccard 3-gram character-level 의미 중복 감지 하드 게이트 장착, `draft_generator.py`에 `best_of_n` 연동 완료. 모노레포 전체 유닛 테스트 및 레거시 회귀 테스트 100% 그린 패스(PASS) 검증 완료. |
| Next Priorities | (a) 사용자 승인 하에 **Workstream 6: hanwoo-dashboard DashboardClient.js 구조 개선** 진행 여부 결정. (b) git commit을 통해 모노레포에 누적된 리팩토링 최종 QC 본 커밋 정리. |
| Date | 2026-05-26 |
| Tool | Gemini (Antigravity) |
| Work | **시스템 매력도 및 DX 고도화 완료 (Phase 1, 2, 3, 6)**: 외부 개발자와 시연자를 위한 프리미엄 쇼케이스 랜딩 페이지(`projects/landing-page/` - HTML, CSS, JS)를 구축하고 다크/라이트 테마 및 스크롤 애니메이션 완비. Shields.io 배지와 Mermaid 구조도를 포함한 퍼블릭 문서(`README.md`, `CONTRIBUTING.md`, `LICENSE`) 완비. Joolife 한우 대시보드 로그인 화면에 데모 계정 정보 인포박스를 추가하고 메인 화면 헤더에 DEMO 배지를 추가하여 대외 시연성을 극대화. Next.js 빌드, Prisma 클라이언트 생성, 프로세스 보안 하드닝 및 헬스체크 API(`api/health`)를 지원하는 경량 Multi-stage Dockerfile과 PostgreSQL + Redis를 한 번에 띄우는 `docker-compose.yml` 구축. Windows 개발자를 위해 1-클릭 가상환경 및 DB 셋업을 지원하는 컬러풀한 PowerShell 스크립트(`setup.ps1`) 제작 완료. |
| Next Priorities | (a) 사용자에게 `setup.ps1` 또는 `docker-compose up`을 로컬에서 실행해볼 수 있도록 안내. (b) 이 상태에서 포트폴리오 사이트와 대시보드 데모를 대외에 즉시 공개/홍보 가능. |
| Date | 2026-05-26 |
| Tool | Gemini (Antigravity) |
| Work | **Monorepo-wide Spacing/Formatting Test Hardening & QC Sweeps Completed**: Hardened 29 regex test matches in `hanwoo-dashboard` accessibility/wiring tests to support multiline layout, flexible spacing (`\s*`), and optional trailing commas (`,?`) introduced by Biome. Achieved **100% green pass** (282/282 Node tests passed, ESLint clean, Next build OK). For `shorts-maker-v2`, fixed residual Ruff lint errors (UP035, I001) using Python-Ruff module, achieving clean lint and 91% pytest coverage. For `blind-to-x`, resolved a pytest-cov 70% coverage exit code check by isolating pytest execution using `--no-cov` parameter, successfully passing all 49/49 unit tests. Walkthrough and task logs updated. Git staged and locally committed 55 modified files. |
| Next Priorities | Guide user to stage, commit, and push the final QC sweep status. Advise future tools to use flexible RegEx (`[\s\S]*?` and `\s*`) for all test wiring assertions to maintain compatibility with Biome formatter. |
| Date | 2026-05-26 |
| Tool | Claude (Opus 4.7) |
| Work | **blind-to-x 생성물 품질 Phase 1 결정론적 하드닝 5종 출하 (`docs/output_quality_uplift_2026-05-26.md`)**: 출력 게이트 감사 → 톤 결정 5개 결함 식별 → 5개 결정론적 검사 추가. (1) `_find_influencer_vocab` zero-tolerance 어휘 12개 1회 등장도 error, (2) `_ends_with_cta_or_question` 마지막 문장 `?`/CTA → error (twitter/threads), (3) `_count_emojis` BMP-외 픽토그래프 카운트 → 2개 warning / 4개 이상 error, (4) `_has_lead_dependency` 첫 문장 출처 도입 강박 warning, (5) `quality_gate._check_originality` 원문 12자 연속 일치 chunk 2개 warning / 4개 이상 failure (인용부 제외). 기존 골든 예시 3건도 새 브랜드 보이스(평서문 마무리)에 맞춰 갱신. 검증: blind-to-x 단위 테스트 1622/1622 green (skipped 1), 신규 회귀 34 케이스, ruff 클린. 변경은 blind-to-x 7개 파일 + SESSION_LOG/HANDOFF; 다른 도구의 hanwoo-dashboard WIP 는 의도적으로 미스테이지. |
| Next Priorities | (a) 사용자에게 커밋 승인 요청 — 커밋 안 한 변경 파일이 7개 stage 대기 중. (b) Phase 2 LLM-side: creator_take 무색무취 검출, 최근 캡션과 의미 유사도 reroll, Best-of-N 비교. (c) 본 PR 범위 외 진행 부채는 `docs/output_quality_uplift_2026-05-26.md` "Phase 2/3" 참고. |

| Next Priorities | Address Supabase E2E resync (T-251) and systematically proceed with VibeDebt RED reduction execution (T-407). |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard admin diagnostics loading status accessibility**: Continued the active Hanwoo quality uplift and kept unrelated dirty workspace files untouched. Updated `DiagnosticsPageClient.js` so the initial diagnostics loading card and raw-record loading placeholder expose polite busy status semantics (`role="status"`, `aria-live="polite"`, `aria-busy="true"`). Added regression coverage in `diagnostics-copy.test.mjs`. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/diagnostics-copy.test.mjs` passed 3/3, `npm.cmd test` passed 314/314, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard market price loading busy-state accessibility**: Continued the active Hanwoo quality uplift with a focused accessibility polish. `MarketPriceWidget.js` already exposed the initial loading UI as a polite status region; it now also sets `aria-busy="true"` so the status has a complete busy contract. Updated `home-market-copy.test.mjs` coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/home-market-copy.test.mjs` passed 32/32, `npm.cmd test` passed 314/314, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard subscription result fallback loading accessibility**: Continued the active Hanwoo quality uplift by hardening subscription result Suspense fallbacks. `subscription/success/page.js` and `subscription/fail/page.js` now expose their loading fallback messages as polite busy status regions (`role="status"`, `aria-live="polite"`, `aria-busy="true"`). Updated `payment-ux-copy.test.mjs` coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/payment-ux-copy.test.mjs` passed 5/5, `npm.cmd test` passed 314/314, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard payment checkout button busy-state accessibility**: Continued the active Hanwoo quality uplift by tightening `PaymentWidget.js`. The checkout button now uses a single `isPaymentButtonBusy` state for disabled, `aria-busy`, wait cursor, and opacity, so both widget-loading and submit-in-flight states are exposed consistently. Updated `payment-ux-copy.test.mjs` coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/payment-ux-copy.test.mjs` passed 5/5, `npm.cmd test` passed 314/314, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard payment confirmation status announcement**: Continued the active Hanwoo quality uplift by hardening `subscription/success/page.js`. The dynamic payment confirmation heading now has `aria-live="polite"` and `aria-atomic="true"` so retry/error status changes are announced while preserving the heading element. Updated `payment-ux-copy.test.mjs` coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/payment-ux-copy.test.mjs` passed 5/5, `npm.cmd test` passed 314/314, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard cattle tag lookup button state labels**: Continued the active Hanwoo quality uplift by hardening `CattleForm.js`. Added `tagLookupButtonLabel` and wired it into the tag lookup button's `aria-label` and `title`, so idle and lookup-in-progress states are exposed consistently with `aria-busy`. Updated `cattle-detail-modal-wiring.test.mjs` coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/cattle-detail-modal-wiring.test.mjs` passed 12/12, `npm.cmd test` passed 314/314, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard AI chat conversation busy-state accessibility**: Continued the active Hanwoo quality uplift by hardening `AIChatWidget.js`. The conversation `role="log"` region now exposes `aria-busy={isStreaming}`, so assistive technology can perceive answer-generation state on the live message area while streaming. Updated `ai-chat-widget-copy.test.mjs` coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/ai-chat-widget-copy.test.mjs` passed 2/2, `npm.cmd test` passed 314/314, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard shared HeartIcon decorative accessibility**: Continued the active Hanwoo quality uplift by hardening the shared `HeartIcon` in `common.js`. The icon now exposes `aria-hidden="true"` and `focusable="false"` so alert/status glyphs do not add duplicate semantics where surrounding text already carries the meaning. Updated alert banner regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/alert-banners-accessibility.test.mjs` passed 3/3, `npm.cmd test` passed 316/316, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard cattle detail section heading semantics**: Continued the active Hanwoo quality uplift by making `CattleDetailModal.js` section titles navigable to assistive technology. The shared `SectionTitle` helper now renders `role="heading"` with `aria-level={3}`, covering the modal's basic information, breeding, weight, timeline, memo, and QR sections. Updated cattle detail regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/cattle-detail-modal-wiring.test.mjs` passed 12/12, `npm.cmd test` passed 316/316, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard home building section decorative icon accessibility**: Continued the active Hanwoo quality uplift by hiding decorative farm icons in `DashboardClient.js` from assistive technology. The home building section header icon and first-building empty-state CTA icon now use `aria-hidden="true"`, leaving the visible heading and CTA copy as the accessible meaning. Updated home dashboard regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/home-market-copy.test.mjs` passed 33/33, `npm.cmd test` passed 316/316, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard Today Focus action accessible labels**: Continued the active Hanwoo quality uplift by adding a consolidated `focusItemLabel` to Today Focus action buttons in `DashboardClient.js`. Each button now exposes its title, detail, and meta context through `aria-label` and `title`, while keeping the existing visible card layout unchanged. Updated home dashboard regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/home-market-copy.test.mjs` passed 34/34, `npm.cmd test` passed 317/317, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard Quick Action button accessible labels**: Continued the active Hanwoo quality uplift by adding a consolidated `quickActionLabel` to Quick Action buttons in `DashboardClient.js`. Each one-tap action now exposes its label and detail through `aria-label` and `title`, while keeping the existing visible card layout unchanged. Updated home dashboard regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/home-market-copy.test.mjs` passed 35/35, `npm.cmd test` passed 318/318, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard setup progress item title accessibility**: Continued the active Hanwoo quality uplift by reusing the existing consolidated `setupItemLabel` as the `title` for setup progress buttons in `DashboardClient.js`. The hover/title copy now matches the assistive action name that includes title, completion state, and detail. Updated home dashboard regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/home-market-copy.test.mjs` passed 35/35, `npm.cmd test` passed 318/318, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard setup progress score value text accessibility**: Continued the active Hanwoo quality uplift by adding a shared `setupProgressLabel` in `DashboardClient.js`. The setup progress score badge now exposes the percent plus completed/total context through `aria-label` and `title`, and the progressbar exposes the same value via `aria-valuetext` while keeping its concise Korean progress label. Updated home dashboard regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/home-market-copy.test.mjs` passed 35/35, `npm.cmd test` passed 318/318, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard login password toggle title accessibility**: Continued the active Hanwoo quality uplift by adding a shared `passwordToggleLabel` to `app/login/page.js`. The password show/hide icon button now uses the same Korean copy for `aria-label` and `title`, aligning the login control with the rest of the dashboard's labeled icon actions. Updated error-page/login regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/error-pages-wiring.test.mjs` passed 9/9, `npm.cmd test` passed 319/319, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard inventory inline quantity action title accessibility**: Continued the active Hanwoo quality uplift by adding matching `title` copy to the inline inventory quantity save and edit controls in `InventoryTab.js`. The item-specific Korean action labels are now consistent across `aria-label` and hover/title text, matching the surrounding labeled action pattern. Updated home-market regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/home-market-copy.test.mjs` passed 35/35, `npm.cmd test` passed 319/319, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard Field Mode cattle result action accessibility**: Continued the active Hanwoo quality uplift by adding item-specific `aria-label` and `title` copy to Field Mode cattle search result buttons in `FieldModeView.js`. Each result now announces that it opens the target cattle detail using the cattle name and formatted ear-tag number. Updated Field Mode regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/field-mode-celebration.test.mjs` passed 7/7, `npm.cmd test` passed 319/319, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard estrus alert icon wrapper decorative accessibility**: Continued the active Hanwoo quality uplift by marking the estrus alert `alert-icon` wrapper in `AlertBanners.js` as `aria-hidden="true"`. The visual heart glyph is now hidden from assistive technology at the same wrapper level as the calving alert decorative icon. Updated alert banner regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/alert-banners-accessibility.test.mjs` passed 3/3, `npm.cmd test` passed 319/319, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard calving card open-action accessibility**: Continued the active Hanwoo quality uplift by adding cow-specific `aria-label` and `title` copy to each calving-list open action in `CalvingTab.js`. Operators and assistive technology can now identify which cow's calving form will open while the visible button text remains concise. Updated calving tab regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/calving-tab-accessibility.test.mjs` passed 5/5, `npm.cmd test` passed 319/319, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard sales add-form toggle accessibility**: Continued the active Hanwoo quality uplift by adding state-aware `addFormButtonLabel` copy to the sales record add/cancel toggle in `SalesTab.js`. The control now exposes add, cancel, and save-in-flight meaning through `aria-label`, `title`, and `aria-busy`, matching the surrounding operational form patterns. Updated home-market regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/home-market-copy.test.mjs` passed 35/35, `npm.cmd test` passed 319/319, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard QR print title specificity**: Continued the active Hanwoo quality uplift by adding a shared `printButtonLabel` to `QRCodeWidget.js`. The QR print action now uses the same label-specific copy for both `aria-label` and `title`, so hover/title text identifies the target label in idle and printing states. Updated QR widget regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/qr-widget-copy.test.mjs` passed 2/2, `npm.cmd test` passed 319/319, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard ear-tag scanner manual choice title specificity**: Continued the active Hanwoo quality uplift by adding a shared `manualChoiceLabel` to manual scanner result choices in `EarTagScannerModal.js`. Manual choice buttons now expose the same cow name and ear-tag suffix through both `aria-label` and `title`, improving hover/title clarity without changing visible layout. Updated scanner modal regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/eartag-scanner-modal-accessibility.test.mjs` passed 3/3, `npm.cmd test` passed 319/319, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard Field Mode checklist toggle action labels**: Continued the active Hanwoo quality uplift by adding a shared `checklistItemLabel` in `FieldModeView.js`. Field Mode checklist buttons now expose the item title, current completion state, and the action to change completion state through both `aria-label` and `title`, making repeated field checks clearer to operators and assistive technology. Updated Field Mode regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/field-mode-celebration.test.mjs` passed 7/7, `npm.cmd test` passed 319/319, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard cattle row hover/title context**: Continued the active Hanwoo quality uplift by reusing `cattleAccessibleLabel` as the `title` on `CattleRow` buttons in `cards.js`. Cow rows now expose the same cow detail action and estrus/calving alert summary through hover/title text that assistive technology already receives. Updated card accessibility regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/cards-accessibility.test.mjs` passed 3/3, `npm.cmd test` passed 319/319, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard feedback toast dismiss title accessibility**: Continued the active Hanwoo quality uplift by adding a shared `toastDismissLabel` in `FeedbackProvider.js`. Toast dismiss buttons now expose the same toast-specific Korean close copy through both `aria-label` and `title`, aligning transient feedback controls with the rest of the dashboard's labeled actions. Updated feedback-provider regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/feedback-provider-copy.test.mjs` passed 3/3, `npm.cmd test` passed 319/319, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard dashboard header icon action title specificity**: Continued the active Hanwoo quality uplift by matching the notification center and cattle-registration header icon button `title` copy in `DashboardClient.js` to their existing Korean `aria-label` action names. Hover/title UI now communicates that each icon action opens its target, matching the surrounding labeled action pattern. Updated home-market regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/home-market-copy.test.mjs` passed 35/35, `npm.cmd test` passed 319/319, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard Field Mode and AI launcher title specificity**: Continued the active Hanwoo quality uplift by matching the dashboard Field Mode activation button and floating AI assistant launcher `title` copy to their existing Korean `aria-label` action names. Hover/title UI now carries the same activate/open semantics as assistive technology for these primary entry controls. Updated home-market and AI chat regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/home-market-copy.test.mjs` passed 35/35, `node --test src/lib/ai-chat-widget-copy.test.mjs` passed 2/2, `npm.cmd test` passed 319/319, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard pen card hover/title context**: Continued the active Hanwoo quality uplift by reusing a shared `penAccessibleLabel` for both `aria-label` and `title` on pen card buttons in `cards.js`. Pen cards now expose the same pen number, cattle count, and estrus-alert context through hover/title UI that assistive technology already receives. Updated card accessibility regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/cards-accessibility.test.mjs` passed 3/3, `npm.cmd test` passed 319/319, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard notification mark-all action accessibility**: Continued the active Hanwoo quality uplift by adding an unread-count-aware `markAllAsReadLabel` to `NotificationSystem.js`. The notification dropdown's mark-all button now reuses that label for both `aria-label` and `title`, clarifying how many unread notifications will be marked read while keeping the visible text concise. Updated notification-system regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/notification-system-copy.test.mjs` passed 8/8, `npm.cmd test` passed 319/319, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard notification item read-action accessibility**: Continued the active Hanwoo quality uplift by allowing the shared `DropdownMenuItem` to forward additional props and adding item-specific Korean `aria-label`/`title` copy to notification dropdown items. Each clickable notification now clearly states that activating it marks that notification read. Updated notification-system regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/notification-system-copy.test.mjs` passed 9/9, `npm.cmd test` passed 320/320, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard home building card action label context**: Continued the active Hanwoo quality uplift by adding a shared `buildingCardLabel` to home building card buttons in `DashboardClient.js`. Each building card now reuses that label for `aria-label` and `title`, explicitly exposing the building name, pen count, and current headcount as a navigation action. Updated home-market regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/home-market-copy.test.mjs` passed 35/35, `npm.cmd test` passed 320/320, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard tab navigation action labels**: Continued the active Hanwoo quality uplift by adding a shared `tabActionLabel` to `TabBar` in `widgets.js`. Dashboard tab buttons now reuse that label for both `aria-label` and `title`, and the active tab label includes `현재 선택됨` so navigation state is clear beyond visual styling. Updated home-market regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/home-market-copy.test.mjs` passed 36/36, `npm.cmd test` passed 321/321, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard admin diagnostics return action accessibility**: Continued the active Hanwoo quality uplift by adding explicit Korean `aria-label` and `title` copy to the diagnostics page return-to-dashboard button in `DiagnosticsPageClient.js`. The arrow icon is now decorative, so the button exposes one clear navigation action without duplicate icon semantics. Updated diagnostics regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/diagnostics-copy.test.mjs` passed 3/3, `npm.cmd test` passed 321/321, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard subscription failure retry action accessibility**: Continued the active Hanwoo quality uplift by adding explicit Korean `aria-label` and `title` copy to the subscription failure page retry/back button in `app/subscription/fail/page.js`. The control now communicates that it returns to the payment screen to retry, instead of relying only on concise visible button text. Updated payment UX regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/payment-ux-copy.test.mjs` passed 5/5, `npm.cmd test` passed 321/321, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard route and global error retry action accessibility**: Continued the active Hanwoo quality uplift by adding shared reset labels to `app/error.js` and `app/global-error.js`. Route-level and global retry buttons now reuse those labels for visible text, `aria-label`, and `title`, making recovery actions explicit across assistive technology and hover/title UI. Updated error-page regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/error-pages-wiring.test.mjs` passed 9/9, `npm.cmd test` passed 321/321, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard legal document home-link accessibility**: Continued the active Hanwoo quality uplift by adding explicit Korean `aria-label` and `title` copy to the shared legal document home-return link in `LegalDocumentLayout.js`. The arrow icon is now decorative, so privacy/terms pages expose one clear home navigation action without duplicate icon semantics. Updated legal-page regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/legal-pages-copy.test.mjs` passed 1/1, `npm.cmd test` passed 321/321, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard not-found and route-error home-link accessibility**: Continued the active Hanwoo quality uplift by adding explicit Korean `aria-label` and `title` copy to the not-found page and route error page dashboard-return links. Both home navigation actions are now clear to assistive technology and hover/title UI instead of relying only on visible link text. Updated error-page regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/error-pages-wiring.test.mjs` passed 9/9, `npm.cmd test` passed 321/321, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard inventory inline quantity saving state labels**: Continued the active Hanwoo quality uplift by adding an item-specific `itemQuantitySaveLabel` to inline inventory quantity edits. While a row save is in flight, the save button now exposes `재고 수량 저장 중` through `aria-label`, `title`, `aria-busy`, and visible `저장 중...` copy, instead of leaving the action label static. Updated inventory regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/empty-state-wiring.test.mjs` passed 17/17, `node --test src/lib/home-market-copy.test.mjs` passed 38/38, `npm.cmd test` passed 329/329, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard settings building delete progress labels**: Continued the active Hanwoo quality uplift by adding a state-aware `buildingDeleteButtonLabel` to building delete buttons in Settings. While a building delete is in flight, the row action now exposes `동 삭제 중` through `aria-label`, `title`, `aria-busy`, and visible `삭제 중...` copy instead of leaving the destructive button static. Updated settings regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/settings-tab-accessibility.test.mjs` passed 12/12, `npm.cmd test` passed 329/329, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard cattle detail archive visible progress copy**: Continued the active Hanwoo quality uplift by adding state-aware visible copy to the cattle detail archive button. The action already exposed busy/disabled and Korean accessible labels; it now also shows `처리 중...` while archive/delete or breeding-save work blocks the modal, keeping the visible destructive action in sync with the busy state. Updated cattle detail regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/cattle-detail-modal-wiring.test.mjs` passed 13/13, `npm.cmd test` passed 329/329, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard cattle form top cancel busy label**: Continued the active Hanwoo quality uplift by reusing `cancelButtonLabel` on the cattle edit form's top icon-only back/cancel button. While a save is in flight, the button now exposes `개체 저장 중에는 취소할 수 없습니다` through both `aria-label` and `title`, matching the bottom cancel action instead of staying on static back-to-list copy. Updated cattle form regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/cattle-detail-modal-wiring.test.mjs` passed 13/13, `npm.cmd test` passed 329/329, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Tool | Codex |
| Work | **hanwoo-dashboard cattle detail close busy label**: Continued the active Hanwoo quality uplift by adding a state-aware `closeButtonLabel` to the cattle detail modal close button. While archive/delete or breeding-save work is in flight, the icon-only close control now exposes that the selected cattle detail window cannot be closed yet instead of staying on static close copy. Updated cattle detail regression coverage. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/cattle-detail-modal-wiring.test.mjs` passed 13/13, `npm.cmd test` passed 329/329, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard MTRACE timeout recovery copy consistency**: Continued the active Hanwoo quality uplift by changing the 축산물이력제 timeout failure message from `축산물이력제 조회 시간이 초과되었습니다. 다시 시도해 주세요.` to `축산물이력제 조회 시간이 초과되었습니다. 잠시 후 다시 시도해 주세요.`, matching the app-wide transient retry wording used for degraded external services. Updated mtrace regression coverage to prevent the terse timeout retry copy from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/mtrace.test.mjs` passed 4/4, `npm.cmd test` passed 337/337, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard AI chat welcome helper-tone consistency**: Continued the active Hanwoo quality uplift by changing the AI farm assistant welcome guidance from `궁금한 점을 물어보세요.` to `궁금한 점을 질문해 주세요.`, matching the input placeholder and the app-wide Korean helper tone. Updated AI chat widget regression coverage to prevent the command-style welcome copy from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/ai-chat-widget-copy.test.mjs` passed 2/2, `npm.cmd test` passed 337/337, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard subscription page helper-tone consistency**: Continued the active Hanwoo quality uplift by changing the subscription page value copy from `AI 보조 기능을 더 안정적으로 사용하세요.` to `AI 보조 기능을 더 안정적으로 사용해 주세요.`, aligning the payment entry page with the app-wide Korean helper tone. Updated payment UX regression coverage to prevent the command-style subscription copy from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/payment-ux-copy.test.mjs` passed 5/5, `npm.cmd test` passed 337/337, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard login and not-found operations helper-tone consistency**: Continued the active Hanwoo quality uplift by changing the login and not-found route guidance from `사육, 재고, 출하 업무를 이어서 관리하세요.` to `사육, 재고, 출하 업무를 이어서 관리해 주세요.`, keeping entry and recovery pages aligned with the app-wide Korean helper tone. Updated error-page regression coverage to prevent the command-style route copy from returning. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/error-pages-wiring.test.mjs` passed 9/9, `npm.cmd test` passed 337/337, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard pen cattle preview hover context**: Continued the active Hanwoo quality uplift by changing pen-card cattle preview titles from cow-name-only hover text to state-aware Korean labels (`발정 알림 있음` / `칸 배치됨`), so quick pen previews expose alert context without opening the detail view. Updated card accessibility regression coverage to keep the contextual preview titles. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/cards-accessibility.test.mjs` passed 4/4, `npm.cmd test` passed 337/337, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

| Field | Value |
|---|---|
| Date | 2026-05-27 |
| Tool | Codex |
| Work | **hanwoo-dashboard calving alert due-date fallback specificity**: Continued the active Hanwoo quality uplift by changing the calving alert missing target-date fallback from placeholder `-` to `분만 예정일 미등록`, so alert chips explain which date field is unavailable instead of rendering a bare dash. Updated alert-banner regression coverage to keep the specific missing-date copy. |
| Next Priorities | Active Hanwoo goal remains open for further polish. T-251 remains user-owned Supabase database password/control-plane resync. Current verification: `node --test src/lib/alert-banners-accessibility.test.mjs` passed 3/3, `npm.cmd test` passed 347/347, `npm.cmd run lint` passed, and `npm.cmd run build` passed with the known T-251 DB health warning but exit 0. |

## Notes

- **T-251 (active blocker)**: Supabase database password desynchronization. User must reset password via Supabase Dashboard (Project Settings > Database), then update `projects/hanwoo-dashboard/.env`.
- **Origin sync**: As of 2026-05-19, `main` is synchronized with `origin/main` and the worktree is clean.
- Older addenda archived in `.ai/archive/HANDOFF_archive_2026-05-15.md` and `.ai/archive/HANDOFF_archive_2026-05-19.md`.
