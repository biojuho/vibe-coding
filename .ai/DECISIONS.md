# 🏗️ 아키텍처 결정 기록 (Architecture Decision Records)

> **⚠️ 아래 결정사항은 확정됨. AI 도구는 임의로 변경 금지.**
> **변경이 필요한 경우, 사용자에게 제안만 할 것.**

---

## ADR-001: 3계층 아키텍처 (Directive → Orchestration → Execution)

| 항목 | 내용 |
|------|------|
| **날짜** | 2026년 초 |
| **상태** | ✅ 확정 |
| **맥락** | LLM은 확률적이지만 비즈니스 로직은 결정론적. 5단계 연속 실행 시 성공률이 59%로 하락하는 문제 |
| **결정** | 지침(Markdown SOP) → AI 오케스트레이션(의사결정) → Python 스크립트(실행) 3계층 분리 |
| **대안** | AI가 모든 것을 직접 처리 / 단순 스크립트만 사용 |
| **선택 이유** | 복잡성을 결정론적 코드로 밀어내고 AI는 의사결정에 집중 → 신뢰성 극대화 |

---

## ADR-002: 로컬 전용 프로젝트 정책

| 항목 | 내용 |
|------|------|
| **날짜** | 2026년 초 |
| **상태** | ✅ 확정 |
| **맥락** | API 키와 개인 데이터가 포함된 프로젝트로 원격 유출 방지 필요 |
| **결정** | 원격 push/pull/deploy 절대 금지. Git은 로컬 버전 관리용으로만 사용 |
| **대안** | Private 원격 저장소 사용 |
| **선택 이유** | 보안 리스크 최소화, 로컬 머신에서 완결적 운영 |

---

## ADR-003: TailwindCSS v4 마이그레이션

| 항목 | 내용 |
|------|------|
| **날짜** | 2026-03-04 |
| **상태** | ✅ 확정 (적용 완료) |
| **맥락** | hanwoo-dashboard, knowledge-dashboard, word-chain에서 TailwindCSS 사용 중 |
| **결정** | TailwindCSS 3 → 4로 마이그레이션 완료 |
| **대안** | TailwindCSS 3 유지 |
| **선택 이유** | 최신 기능 활용, `@tailwindcss/postcss` 플러그인 방식 채택 |

---

## ADR-004: Prisma 6 + Next.js 16 스택

| 항목 | 내용 |
|------|------|
| **날짜** | 2026-03-04 |
| **상태** | ✅ 확정 (적용 완료) |
| **맥락** | hanwoo-dashboard에서 Prisma 5→6, Next.js 15→16 업그레이드 |
| **결정** | Prisma 6 + Next.js 16 + React 19 조합으로 확정 |
| **대안** | 이전 버전 유지 |
| **선택 이유** | 최신 안정 버전 활용, 성능 및 호환성 개선 |

---

## ADR-005: MoviePy 2.x + Edge TTS 조합

| 항목 | 내용 |
|------|------|
| **날짜** | 2026-03-04 |
| **상태** | ✅ 확정 (적용 완료) |
| **맥락** | shorts-maker-v2에서 영상 생성 및 TTS 처리 |
| **결정** | MoviePy 1.x → 2.1로 마이그레이션, Edge TTS 활용 |
| **대안** | MoviePy 1.x 유지 / Google Cloud TTS 사용 |
| **선택 이유** | MoviePy 2.x의 개선된 API, Edge TTS의 무료 + 고품질 한국어 음성 |

---

## ADR-006: 5채널 YouTube Shorts 전략

| 항목 | 내용 |
|------|------|
| **날짜** | 2026-03-05 |
| **상태** | ✅ 확정 |
| **맥락** | YouTube Shorts 자동 생성 파이프라인 운영 |
| **결정** | AI 테크, 심리학, 역사, 건강, 우주 5개 채널별 전용 프로필 및 스타일 운영 |
| **대안** | 단일 채널 운영 |
| **선택 이유** | 채널별 최적화된 콘텐츠 생산, 유기적 성장 극대화 |

---

## ADR-007: AI 도구 공유 컨텍스트 시스템 (.ai/ 폴더)

| 항목 | 내용 |
|------|------|
| **날짜** | 2026-03-06 |
| **상태** | ✅ 확정 |
| **맥락** | Claude Code, Codex, Gemini/Antigravity, Cursor 등 여러 AI 도구가 번갈아 작업하며 맥락 유실 발생 |
| **결정** | `.ai/` 폴더에 CONTEXT.md, SESSION_LOG.md, DECISIONS.md 3개 파일로 공유 컨텍스트 시스템 운영 |
| **대안** | 각 도구 고유 컨텍스트만 사용 / README.md에 통합 |
| **선택 이유** | 도구 전환 시 맥락 끊김 방지, 결정사항 보존, 세션 간 인수인계 체계화 |

---

## ADR-008: QA/QC 4단계 자동화 검증 워크플로우 통합

| 항목 | 내용 |
|------|------|
| **날짜** | 2026-03-08 |
| **상태** | ✅ 확정 |
| **맥락** | 작업 퀄리티 보장 및 버그 수정 반복에 따른 리소스 낭비를 방지하기 위해 품질 검증의 공식화 필요 |
| **결정** | 개발 → QA 리뷰 → 코드 수정 → QC 리포트의 4단계 워크플로우를 도입하고, `project-rules.md` 및 `session_workflow.md`에 의무화 |
| **대안** | 수동으로 리뷰 요청 시에만 진행 / 간단한 1-step 코드 리뷰 프롬프트만 사용 |
| **선택 이유** | 체계적이고 객관적인 품질 검증(QA)과 최종 승인(QC) 과정을 오케스트레이션 단계(2계층) 및 지침(1계층)에 내재화하여 일관된 고품질 코드 생산 보장 |

---

## ADR-009: MCP 서버 에러 반환 패턴 통일

| 항목 | 내용 |
|------|------|
| **날짜** | 2026-03-12 |
| **상태** | ✅ 확정 |
| **맥락** | 커스텀 MCP 서버(YouTube, Telegram, n8n 등)에서 에러 처리가 raise/dict 혼재하여 클라이언트 측 핸들링이 복잡 |
| **결정** | 모든 MCP 도구 함수는 예외를 raise하지 않고 `{"error": "..."}` dict를 반환 |
| **대안** | 예외를 raise하여 FastMCP 프레임워크가 처리 / 서비스별 독자 패턴 |
| **선택 이유** | 클라이언트(LLM)가 에러 메시지를 인라인으로 파싱 가능, 서비스 간 일관성 확보, `requests.Session` 싱글톤과 함께 작동 최적화 |

---

## ADR-010: blind-to-x 멘션 생성 자연스러움 우선 원칙

| 항목 | 내용 |
|------|------|
| **날짜** | 2026-03-21 |
| **상태** | 확정 |
| **맥락** | LLM이 생성하는 X(Twitter) 멘션이 부자연스럽고 매번 수동 편집 필요. 12개 지시 블록, 3-part formula 강제, 과도한 품질 게이트가 원인 |
| **결정** | 캡션은 "편집 없이 바로 게시 가능한 자연스러움"을 최우선 가치로 하고, 규칙 엄격성보다 톤 자연스러움을 우선함 |
| **구체 조치** | 프롬프트 formula 제거, 품질게이트 훅강도를 info로, 에디토리얼 임계값 6.0->5.0, TextPolisher twitter/threads 스킵, 금지표현 10->6개 |
| **대안** | 기존 엄격한 규칙 유지 + 후처리로 자연스러움 보정 |
| **선택 이유** | LLM은 제약이 적을수록 자연스러운 출력을 생성하며, 과도한 후처리(polisher+editorial 2중)가 오히려 품질 저하를 유발 |

---

## ADR-011: blind-to-x 링크-인-리플라이 전략

| 항목 | 내용 |
|------|------|
| **날짜** | 2026-03-21 |
| **상태** | 확정 |
| **맥락** | X 알고리즘이 본문 내 외부 링크 포함 트윗의 도달률을 30-50% 감소시킴 |
| **결정** | 본문 트윗에는 링크/해시태그를 넣지 않고, 첫 번째 답글(reply)에 분리하여 게시 |
| **구체 조치** | draft_generator가 `<reply>` 태그로 답글 텍스트 생성, process.py에서 URL 주입, Notion에 reply_text 필드 저장 |
| **대안** | 기존대로 본문에 링크 포함 |
| **선택 이유** | 2025-2026 X 알고리즘 연구에 따르면 텍스트 전용 포스트가 37% 높은 참여율, 답글+저자응답이 150배 가중치 |

---

<!--
## ADR 템플릿 (복사해서 사용)

## ADR-XXX: [결정 제목]

| 항목 | 내용 |
|------|------|
| **날짜** | YYYY-MM-DD |
| **상태** | ✅ 확정 / 🔄 검토 중 / ❌ 폐기 |
| **맥락** | (왜 이 결정이 필요했는지) |
| **결정** | (무엇을 결정했는지) |
| **대안** | (고려했던 다른 방안) |
| **선택 이유** | (왜 이 방안을 선택했는지) |
-->

## ADR-010: Explicit renderer mode with native default

| 항목 | 내용 |
|------|------|
| **날짜** | 2026-03-17 |
| **상태** | ✅ 확정 |
| **맥락** | shorts-maker-v2 had an implicit native-vs-ShortsFactory branch controlled by a boolean flag, which made rollout, fallback policy, and manifest verification ambiguous. |
| **결정** | Introduce explicit renderer modes: `native`, `auto`, `shorts_factory`. Keep `native` as the default. `auto` means ShortsFactory first with native fallback. `shorts_factory` means fail fast if the ShortsFactory path fails. |
| **대안** | Keep boolean `use_shorts_factory`; silently switch the default renderer to ShortsFactory. |
| **선택 이유** | The explicit mode makes rollout safe, keeps production default stable, and gives testable manifest semantics for fallback behavior. |

---

## ADR-011: MiMo V2-Flash as Default LLM Provider

| 항목 | 내용 |
|------|------|
| **날짜** | 2026-03-20 |
| **상태** | ✅ 확정 |
| **맥락** | shorts-maker-v2의 LLM 비용 절감 필요. 기존 Google Gemini/Groq 프로바이더 대비 동등 품질에서 비용 50% 절감 가능한 대안 발견 |
| **결정** | Xiaomi MiMo V2-Flash를 기본 LLM 프로바이더로 채택. OpenAI 호환 API 사용. 9단계 폴백 체인 유지 (MiMo → Google → Groq → ...) |
| **대안** | Google Gemini Flash 유지 / DeepSeek V3 사용 |
| **선택 이유** | 비용 효율 ($0.001/job), OpenAI 호환 API로 통합 용이, 롤백은 config.yaml에서 `mimo` 제거만으로 가능 |

---

## ADR-012: OpenAI TTS (tts-1-hd) Premium Stack + SFX 비활성화

| 항목 | 내용 |
|------|------|
| **날짜** | 2026-03-21 |
| **상태** | ✅ 확정 |
| **맥락** | edge-tts의 TTS 품질이 부족하고, 중간 효과음(SFX)이 영상 몰입도를 저해. 사용자가 "돈을 투자하자"고 결정 |
| **결정** | TTS를 edge-tts → OpenAI tts-1-hd로 전환, SFX 비활성화, Whisper-1 단어 동기화 활성화 |
| **비용** | TTS $0.0008/초 (영상당 ~$0.008 ≈ 12원), 7씬 기준 총 $0.0086 |
| **대안** | edge-tts 유지 (무료) / Google Cloud TTS |
| **선택 이유** | OpenAI tts-1-hd는 자연스러운 숨소리와 억양으로 팟캐스트 수준 품질. 비용 대비 품질 향상 효과가 큼 |

---

## ADR-013: Local-First SaaS 하이브리드 아키텍처

| 항목 | 내용 |
|------|------|
| **날짜** | 2026-03-22 |
| **상태** | ✅ 확정 |
| **맥락** | roadmap_v3.md의 SaaS 전환 계획과 ADR-002 로컬 전용 정책이 상충. 개인 데이터·API 키 보호는 유지하면서 수익화 가능한 구조 필요 |
| **결정** | "Local-First SaaS" 패턴 채택. 핵심 연산(렌더링·스크래핑·LLM 호출)은 로컬 워커에서 실행, 웹 UI와 사용자 관리만 Vercel/Supabase에 배포. 두 계층은 Adapter 인터페이스로 분리 |
| **대안** | (A) 기존 로컬 전용 유지 (수익화 불가) / (B) 전면 클라우드 전환 (ADR-002 위반, 보안 리스크) |
| **선택 이유** | ADR-002의 보안 원칙 존중 + SaaS 수익화 경로 확보. 로컬 워커는 Cloudflare Tunnel 또는 n8n Webhook으로 웹 껍데기와 연동하며, API 키는 로컬에만 존재 |
| **ADR-002 관계** | ADR-002를 **폐기하지 않고 범위를 재해석**: "핵심 데이터·키는 로컬"이라는 정신은 유지, "원격 인터페이스 금지"는 "읽기 전용 웹 뷰 + 인증된 작업 트리거"로 완화 |
| **상세 설계** | `directives/local_first_saas_design.md` 참조 |
