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

---

## ADR-015: blind-to-x publishable drafts vs review metadata separation

| ??목 | 내용 |
|------|------|
| **날짜** | 2026-03-29 |
| **상태** | 확정 |
| **문맥** | `blind-to-x` external review found that `reply_text` and `creator_take` were being treated like publishable drafts across generation validation, quality gates, editorial review, and reviewer-facing output, which increased coupling and review fatigue. |
| **결정** | Introduce an explicit draft contract in `projects/blind-to-x/pipeline/draft_contract.py`: publishable drafts (`twitter`, `threads`, `newsletter`, `naver_blog`, `twitter_thread`) are handled separately from auxiliary outputs (`reply_text`) and review metadata (`creator_take`). Quality/review loops operate on publishable drafts only. |
| **대안** | Keep the flat draft dict contract and rely on per-module skip lists; fully refactor to nested DTOs immediately. |
| **선택 이유** | This reduces coupling immediately without a risky full DTO migration, clarifies ownership for quality layers, and creates a safer path for the later `process_single_post()` stage split. |

---

## ADR-016: blind-to-x `review_only` bypasses queue-threshold gating

| ??紐?| ?댁슜 |
|------|------|
| **?좎쭨** | 2026-03-29 |
| **?곹깭** | ?뺤젙 |
| **臾몃㎘** | `blind-to-x` manual review runs were expected to keep generating drafts, images, Notion rows, and analytics even when the ranking-based review queue threshold would normally skip automation. A targeted regression sweep exposed that `review_only=True` was still being blocked by `final_rank_below_threshold`. |
| **寃곗젙** | When `review_only=True`, the queue-threshold decision is overridden to continue through generation and persistence with `review_status="검토필요"`. Earlier hard filters such as spam, inappropriate content, low scrape quality, rejected emotion axes, and budget limits still apply. |
| **???* | Keep the final-rank queue threshold as a hard stop even in `review_only`; introduce a separate force flag for manual review. |
| **?좏깮 ?댁쑀** | This preserves the automation guardrails for normal runs while making reviewer-driven inspection and reprocessing paths practical and testable without weakening the upstream quality filters. |

---

## ADR-014: Canonical Workspace and Projects Layout

| 항목 | 내용 |
|------|------|
| **날짜** | 2026-03-26 |
| **상태** | 확정 |
| **맥락** | Root-owned automation folders and product folders were mixed at repo root, causing path drift in scripts, docs, and launch tooling. |
| **결정** | Canonical root-owned content moves under `workspace/`, product repositories move under `projects/`, and `infrastructure/` remains top-level. |
| **세부 규칙** | `workspace/directives`, `workspace/execution`, `workspace/scripts`, `workspace/tests` are canonical. Product repos live at `projects/<name>`. `.ai/`, `.agents/`, `.claude/`, `.github/`, `.mcp*.json`, `.tmp/`, `venv/`, and `_archive/` stay at repo root. |
| **호환성** | Internal automation may resolve both legacy root project paths and canonical `projects/<name>` paths during migration. New docs and commands must use canonical paths only. |
| **선택 이유** | The split reduces root clutter, makes ownership obvious, and preserves the AI/tooling control plane where existing session bootstrap expects it. |

---

## ADR-017: blind-to-x split rule files with a shared loader

| 항목 | 내용 |
|------|------|
| **날짜** | 2026-03-29 |
| **상태** | 확정 |
| **맥락** | `projects/blind-to-x/classification_rules.yaml` had grown into a single mixed source for taxonomy, examples, prompt templates, editorial policy, and platform regulations. That made ownership blurry and raised the risk of unrelated edits colliding in one file. |
| **결정** | Move the rule source of truth to split files under `projects/blind-to-x/rules/` and load them through `projects/blind-to-x/pipeline/rules_loader.py`. Keep the root `classification_rules.yaml` as a compatibility snapshot/fallback during the migration instead of deleting it immediately. |
| **대안** | Keep one god YAML file; remove the legacy root YAML immediately and force a big-bang migration. |
| **선택 이유** | The shared loader preserves runtime compatibility while reducing merge risk, narrowing file ownership, and making later cleanup safer. It also lets scripts and runtime modules migrate incrementally without blocking current operations. |

---

## ADR-019: blind-to-x staged process compatibility bridge

| 항목 | 내용 |
|------|------|
| **날짜** | 2026-03-30 |
| **상태** | ✅ 확정 |
| **맥락** | `blind-to-x`의 staged `process_single_post()` 분해 과정에서 `pipeline/process.py`는 slim orchestrator로 줄었지만, 기존 테스트와 명령 경로는 여전히 `pipeline.process`와 `pipeline.stages.*`를 직접 import/monkeypatch하고 있었다. 추출 중간 산출물까지 섞이면서 stage 파일 일부가 깨져 호환성과 안정성이 동시에 필요해졌다. |
| **결정** | `projects/blind-to-x/pipeline/process.py`를 공개 오케스트레이션 표면으로 유지하고, 실제 stage 동작은 `projects/blind-to-x/pipeline/process_stages/`에 둔다. `projects/blind-to-x/pipeline/stages/`는 이 구현을 가리키는 호환 브리지로 유지한다. 또한 `pipeline.process`는 `SPAM_KEYWORDS`, `extract_preferred_tweet_text`, `build_content_profile`, `build_review_decision`, `_ViralFilterCls`, `_sentiment_tracker`, `_nlm_enrich` 같은 기존 monkeypatch/import 표면을 계속 노출한다. |
| **대안** | `process_stages/`만 남기고 모든 호출부/테스트를 일괄 수정 / 다시 monolithic `process.py`로 회귀 |
| **선택 이유** | staged architecture 이점을 유지하면서도, 기존 테스트·명령·호출 계약을 깨지 않고 점진적으로 리팩터를 마무리할 수 있다. 호환 브리지 덕분에 이후 정리는 내부 구현에 집중할 수 있다. |

---

## ADR-018: 상태(State)와 규칙(Context)의 물리적 분리 및 Fast-path 도입

| 항목 | 내용 |
|------|------|
| **날짜** | 2026-03-30 |
| **상태** | ✅ 확정 |
| **맥락** | `CONTEXT.md` 파일에 매일 변동되는 테스트 커버리지, 임시 버그(Minefield) 등이 축적되어 토큰 오버헤드(Context Bloat)가 발생함. 단순한 코드 수정, 질문 답변 시에도 시스템 절차(SESSION_LOG 등 4~5개 파일 업데이트)로 인해 생산성이 저하됨. |
| **결정** | 1. `CONTEXT.md`에서 현재 상태, 품질 노트, 지뢰밭(Minefield)을 제거하여 `STATUS.md`로 분리. `CONTEXT.md`는 고정된 아키텍처/폴더 구조 유지. <br>2. 1~2줄 수정, 단순 코드 리뷰 등에는 복잡한 업데이트를 생략하는 경량화(Fast-path) 워크플로우 도입. (`AGENTS.md` 반영) |
| **대안** | 1. 상태 로그 전체 삭제 (히스토리 추적 불가) <br>2. 별도 디렉토리 아카이빙 (가시성 저하) |
| **선택 이유** | 아키텍처 규칙과 매일 변동되는 상태 데이터를 분리하여 에이전트 구동에 들어가는 시스템 유지보수 오버헤드를 줄이면서 본래의 철학(3-Layer Architecture)은 고수하기 위함. |
