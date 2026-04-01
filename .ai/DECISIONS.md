# 아키텍처 결정 기록 (Architecture Decision Records)

> **아래 결정사항은 확정됨. AI 도구는 임의로 변경 금지.**
> **변경이 필요한 경우, 사용자에게 제안만 할 것.**

---

## ADR-001: 3계층 아키텍처 (Directive → Orchestration → Execution)

| 항목 | 내용 |
|------|------|
| **날짜** | 2026년 초 |
| **상태** | 확정 |
| **결정** | 지침(Markdown SOP) → AI 오케스트레이션(의사결정) → Python 스크립트(실행) 3계층 분리 |
| **선택 이유** | 복잡성을 결정론적 코드로 밀어내고 AI는 의사결정에 집중 → 신뢰성 극대화 |

---

## ADR-002: 로컬 전용 프로젝트 정책 (+ ADR-013 확장)

| 항목 | 내용 |
|------|------|
| **날짜** | 2026년 초 (2026-03-22 확장) |
| **상태** | 확정 |
| **결정** | 핵심 데이터/API 키는 로컬에만 존재. Git은 로컬 버전 관리용. 읽기 전용 웹뷰 + 인증된 작업 트리거는 허용 (Local-First SaaS 패턴) |
| **상세 설계** | `directives/local_first_saas_design.md` 참조 |
| **선택 이유** | 보안 원칙 존중 + SaaS 수익화 경로 확보. 로컬 워커는 Cloudflare Tunnel / n8n Webhook으로 웹 껍데기와 연동 |

---

## ADR-009: MCP 서버 에러 반환 패턴 통일

| 항목 | 내용 |
|------|------|
| **날짜** | 2026-03-12 |
| **상태** | 확정 |
| **결정** | 모든 MCP 도구 함수는 예외를 raise하지 않고 `{"error": "..."}` dict를 반환 |
| **선택 이유** | 클라이언트(LLM)가 에러 메시지를 인라인으로 파싱 가능, 서비스 간 일관성 확보 |

---

## ADR-010: blind-to-x 멘션 생성 자연스러움 우선 원칙

| 항목 | 내용 |
|------|------|
| **날짜** | 2026-03-21 |
| **상태** | 확정 |
| **결정** | 캡션은 "편집 없이 바로 게시 가능한 자연스러움"을 최우선 가치로, 규칙 엄격성보다 톤 자연스러움 우선 |
| **선택 이유** | LLM은 제약이 적을수록 자연스러운 출력 생성, 과도한 후처리가 오히려 품질 저하 유발 |

---

## ADR-011: blind-to-x 링크-인-리플라이 전략

| 항목 | 내용 |
|------|------|
| **날짜** | 2026-03-21 |
| **상태** | 확정 |
| **결정** | 본문 트윗에는 링크/해시태그 없이 텍스트만, 첫 번째 답글에 분리 게시 |
| **선택 이유** | 텍스트 전용 포스트가 37% 높은 참여율, 답글+저자응답이 150배 가중치 |

---

## ADR-012: OpenAI TTS (tts-1-hd) Premium Stack

| 항목 | 내용 |
|------|------|
| **날짜** | 2026-03-21 |
| **상태** | 확정 |
| **결정** | TTS를 edge-tts → OpenAI tts-1-hd로 전환, SFX 비활성화, Whisper-1 단어 동기화 |
| **비용** | 영상당 ~$0.008 (≈12원) |
| **선택 이유** | 팟캐스트 수준 품질, 비용 대비 향상 효과가 큼 |

---

## ADR-014: Canonical Workspace/Projects Layout

| 항목 | 내용 |
|------|------|
| **날짜** | 2026-03-26 |
| **상태** | 확정 |
| **결정** | Root-owned → `workspace/`, Product repos → `projects/`, Infrastructure → top-level `infrastructure/` |
| **선택 이유** | root 혼잡 해소, 소유권 명확화, AI/tooling 제어 평면 유지 |

---

## ADR-020: Governance checks gate shared control-plane approval

| 항목 | 내용 |
|------|------|
| **날짜** | 2026-03-31 |
| **상태** | 확정 |
| **결정** | `governance_checks.py`가 `.ai` 파일, relay claim, directive mapping, task backlog를 검증. governance 실패 시 APPROVED 불가 |
| **선택 이유** | 문서 드리프트와 세션 상태 드리프트를 기계적으로 감지 |

---

## ADR-021: Repo-map selective context loading in VibeCodingGraph

| ??ぉ | ?댁슜 |
|------|------|
| **?좎쭨** | 2026-03-31 |
| **?곹깭** | ?뺤젙 |
| **寃곗젙** | `workspace/execution/repo_map.py` + `workspace/execution/context_selector.py` are the first adoption layer for agentic-coding optimization. `graph_engine.py` now injects ranked, budget-limited repo context instead of broad whole-repo context. |
| **?좏깮 ?댁쑀** | Captures the practical value of selective context loading without importing a heavier external runtime, while preserving the existing 3-layer architecture and the `workspace/` vs `projects/` path contract. |

---

<!--
아카이빙된 ADR (구현 상세/버전 업그레이드):
- ADR-003: TailwindCSS v4 마이그레이션 (2026-03-04, 적용 완료)
- ADR-004: Prisma 6 + Next.js 16 스택 (2026-03-04, 적용 완료)
- ADR-005: MoviePy 2.x + Edge TTS (2026-03-04, 적용 완료)
- ADR-006: 5채널 YouTube Shorts 전략 (2026-03-05)
- ADR-011-shorts: MiMo V2-Flash 기본 LLM (2026-03-20, shorts 전용)
- ADR-010-shorts: Explicit renderer mode (2026-03-17, shorts 전용)
- ADR-015: blind-to-x draft contract separation (2026-03-29)
- ADR-016: blind-to-x review_only bypass (2026-03-29)
- ADR-017: blind-to-x split rule files (2026-03-29)
- ADR-018: State/Context 물리적 분리 + Fast-path (2026-03-30)
- ADR-019: blind-to-x staged process bridge (2026-03-30, 브리지 제거 완료 2026-03-31)
-->

## ADR-022: Hanwoo Dashboard auth and payment ownership must be enforced server-side

| Item | Value |
|------|------|
| **Date** | 2026-04-01 |
| **Status** | Accepted |
| **Decision** | `projects/hanwoo-dashboard` must not rely on cookie-presence checks or client-generated order metadata for trust boundaries. Auth is enforced with `requireAuthenticatedSession()` on server pages/actions/routes plus `Auth.js` proxy authorization, while subscription checkout uses a server-prepared order and a transactional payment-confirm step that upserts both `PaymentLog` and `Subscription`. |
| **Rationale** | The previous shape allowed logged-in UX without a durable authorization boundary and left payment ownership too loose. Moving trust decisions to server-side session checks and server-issued order data closes the easiest bypass paths and aligns the payment ledger with the subscription state. |

<!--
## ADR 템플릿 (복사해서 사용)

## ADR-XXX: [결정 제목]

| 항목 | 내용 |
|------|------|
| **날짜** | YYYY-MM-DD |
| **상태** | 확정 / 검토 중 / 폐기 |
| **결정** | (무엇을 결정했는지) |
| **선택 이유** | (왜 이 방안을 선택했는지) |
-->
