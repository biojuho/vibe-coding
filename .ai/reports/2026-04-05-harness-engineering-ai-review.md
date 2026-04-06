# [Harness AI 도입 검토 보고서]

> **작성일:** 2026-04-05  
> **작성자:** Chief AI Architect (Claude)  
> **대상 시스템:** Vibe Coding 워크스페이스 — Python 기반 3계층 자동화 파이프라인  
> **검토 배경:** Harness Engineering AI 패러다임 도입을 통한 LLM 에이전트 신뢰성·제어력 향상

---

## 배경: Harness Engineering AI란?

### 핵심 공식: `Agent = Model + Harness`

**Harness**란 LLM 모델을 감싸는 모든 코드·설정·실행 로직을 의미한다. 모델이 엔진이라면, Harness는 **차체·브레이크·계기판·핸들**이다. Harness 없이는 아무리 강력한 엔진도 승객을 안전하게 운반할 수 없다.

**핵심 원칙** (Mitchell Hashimoto, 2026.02):
> "에이전트가 실수할 때마다, 그 실수가 구조적으로 반복 불가능하도록 시스템을 변경하라."

### 3세대 진화: Prompt → Context → Harness

| 세대 | 시기 | 비유 | 핵심 |
|------|------|------|------|
| **1세대: Prompt Engineering** | 2022-2024 | "완벽한 이메일 작성" | 단일 입력 최적화 (Few-shot, CoT) |
| **2세대: Context Engineering** | 2025 | "첨부파일 잘 붙이기" | 동적 컨텍스트 구성 (RAG, Tool definitions) |
| **3세대: Harness Engineering** | 2026 | "사무실 전체 설계" | 워크플로우·제약·피드백 루프·샌드박싱·권한 시스템 |

각 세대는 이전을 포함한다. Harness Engineering은 좋은 프롬프트와 컨텍스트를 **전제**로 하되, 거기에 **구조적 제약**, **결정론적 검증**, **인간 승인 게이트**를 추가한다.

### 정량적 근거: Harness가 모델보다 중요하다

| 실험 | 결과 |
|------|------|
| **Meta-Harness** (Stanford/MIT) | 동일 LLM에 harness만 교체 → **6배 성능 차이** |
| **보험 청구 PoC** (Nayak) | Harness 추가만으로 정확도 50% → **100%** (모델 변경 없음) |
| **Hashline 실험** | 편집 포맷(harness 요소) 변경만으로 벤치마크 6.7% → **68.3%** |

### 주요 출처

- [Martin Fowler: Harness Engineering for Coding Agent Users](https://martinfowler.com/articles/harness-engineering.html)
- [LangChain Blog: The Anatomy of an Agent Harness](https://blog.langchain.com/the-anatomy-of-an-agent-harness/)
- [Anthropic: Effective Harnesses for Long-Running Agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
- [OpenAI: Harness Engineering — Leveraging Codex](https://openai.com/index/harness-engineering/)

---

## Step 1: 시스템 요구사항 및 후보군 비교 분석

### 우리 시스템의 현재 상태

| 항목 | 현재 |
|------|------|
| **아키텍처** | 3계층 (Directives SOP → AI Orchestration → Execution Python) — **이미 Harness 패턴** |
| **LLM** | 7개 프로바이더 fallback 체인 |
| **파이프라인** | blind-to-x (SNS 자동화), shorts-maker-v2 (영상), hanwoo-dashboard |
| **런타임** | Python 3.14, Local-First (ADR-002) |
| **자동화** | n8n, MCP 서버, Telegram bot |
| **테스트** | 3,513 passed, ruff, Bandit 보안 스캔 |

### 5개 후보 오픈소스 비교표

| 항목 | **OpenHarness** | **AutoHarness** | **DeepAgents** | **HarnessKit** | **Etienne** |
|------|----------------|----------------|---------------|---------------|-------------|
| **GitHub** | [HKUDS/OpenHarness](https://github.com/HKUDS/OpenHarness) | [aiming-lab/AutoHarness](https://github.com/aiming-lab/AutoHarness) | [langchain-ai/deepagents](https://github.com/langchain-ai/deepagents) | [deepklarity/harness-kit](https://github.com/deepklarity/harness-kit) | [BulloRosso/etienne](https://github.com/BulloRosso/etienne) |
| **Stars** | 3,503 | ~181 | **19,162** | 32 | 19 |
| **언어** | Python | Python | Python | Python | **TypeScript** (Node+React) |
| **라이선스** | MIT | MIT | MIT | MIT | MIT |
| **생성일** | 2026-04-01 (4일) | 2026-04-02 (3일) | 2025-07-27 (9개월) | 2026-03-01 | 2025-09-30 |
| **최근 커밋** | 2026-04-04 | 2026-04-02 | 2026-04-04 | 2026-03-01 | 2026-04-03 |
| **핵심 철학** | Claude Code 오픈소스 재구현 | YAML 기반 거버넌스 프레임워크 | LangGraph 네이티브 범용 에이전트 | TDD 기반 DAG 오케스트레이션 | 기업 환경 코딩 에이전트 harness |
| **도구 수** | 43+ | 제한적 (거버넌스 중심) | ~10 (핵심 도구) | 미공개 | 미공개 |
| **멀티 에이전트** | O (서브에이전트 스폰, 팀 조율) | O (멀티 에이전트 프로필) | O (task 기반 위임) | O (DAG 기반 병렬화) | O (Claude Agent SDK 기반) |
| **권한 시스템** | O (3단계, 경로별 규칙) | O (YAML 헌법, 위험 분류) | △ (도구/샌드박스 레벨) | O (체크포인트별 HITL) | O (RBAC) |
| **메모리** | O (CLAUDE.md + MEMORY.md) | △ (세션 지속성) | O (컨텍스트 자동 요약) | O (문제 해결 기록 축적) | O (워크스페이스 모델) |
| **LLM 호환** | Anthropic + OpenAI 호환 다수 | OpenAI 호환 | **전체** (Provider-agnostic) | 미명시 | Anthropic only |
| **생태계** | 독립 | 독립 | **LangChain/LangGraph** | 독립 | Claude Agent SDK |

### 후보별 장단점 (Pros & Cons)

#### 1. OpenHarness (HKUDS)

| Pros | Cons |
|------|------|
| Claude Code와 거의 동일한 아키텍처 — 학습곡선 최소 | **4일밖에 안 된 프로젝트** — 프로덕션 안정성 미검증 |
| 43+ 도구, 54 슬래시 커맨드로 가장 풍부한 기능셋 | 릴리스 태그 없음 (v0.1.0 미출시) |
| MCP 클라이언트 내장 — 우리 MCP 서버와 즉시 연동 가능 | 기여자 6명 — 장기 유지보수 불확실 |
| MIT 라이선스, Python, 멀티 프로바이더 | React TUI 의존 — 서버사이드 파이프라인에 불필요한 오버헤드 |
| 우리의 CLAUDE.md 패턴과 직접 호환 | HKU 연구실 프로젝트 — 커뮤니티 지속성 리스크 |

#### 2. AutoHarness (aiming-lab)

| Pros | Cons |
|------|------|
| **거버넌스 특화** — YAML 헌법으로 정책 선언적 관리 | **3일 된 프로젝트**, Stars ~181, 사실상 알파 |
| 2줄 통합으로 기존 LLM 클라이언트 래핑 가능 | 도구 생태계·문서 거의 없음 |
| 3단계 파이프라인 (Core/Standard/Enhanced) | 커뮤니티 거의 없음, 포크 5개 |
| Google DeepMind 논문(arXiv:2603.03329) 기반 개념 검증 | 논문의 자동 harness 합성과 이 구현체는 **별개** |
| 비용 추적, 세션 지속성 | 우리의 7-프로바이더 fallback과 통합 검증 필요 |

#### 3. DeepAgents (LangChain)

| Pros | Cons |
|------|------|
| **19K+ Stars**, LangChain 공식 — 가장 큰 커뮤니티 | LangChain 생태계에 **강하게 종속** (langchain-core, langgraph) |
| Harrison Chase(CEO) 직접 참여, 일일 커밋 | 의존성 체인 무거움 (langchain-core → langsmith → langgraph) |
| Provider-agnostic (모든 LLM) | 우리 3계층 구조와 철학적 충돌 가능 (자체 루프를 가짐) |
| SDK + CLI 이중 제공, 평가 harness 내장 | Python >=3.11 요구 (호환 OK, 하위 호환 아님) |
| LangSmith 관측성, 체크포인터 등 프로덕션 기능 | 라이선스는 MIT지만 LangSmith(SaaS)로 수익 모델 유도 |
| 서브에이전트, 파일시스템, 쉘, 플래닝 통합 | 기존 execution/ 스크립트를 LangGraph 도구로 래핑하는 작업 필요 |

#### 4. HarnessKit (deepklarity)

| Pros | Cons |
|------|------|
| TDD 기반 설계 — 우리 테스트 문화와 맞음 (3,513 테스트) | **커밋 2개**, 2026-03-01 이후 활동 없음 |
| 비용 인식 에이전트 배정 — 우리 LLM fallback 체인과 시너지 | Stars 32, 포크 2 — 사실상 개인 프로젝트 |
| 7단계 근본 원인 분석 프레임워크 | 문서만 있고 실제 구현체 미확인 |
| DAG 병렬화 — 파이프라인 최적화 가능 | 장기 지원 가능성 **매우 낮음** |
| 지식 축적 패턴 — 우리 self-annealing 루프와 유사 | 독립 생태계, 통합 사례 없음 |

#### 5. Etienne (BulloRosso)

| Pros | Cons |
|------|------|
| 기업 환경 고려 (RBAC, Git 버전 관리, 컴플라이언스) | **TypeScript** — 우리 Python 스택과 언어 불일치 |
| 자가 패칭 + 인간 감독 모델 — 안전한 자동 수정 | Stars 19, 개인 프로젝트 |
| Agent Definition Package (ADP) — 선언적 에이전트 정의 | Claude Agent SDK에 강하게 종속 |
| 자율 온보딩 (에이전트가 스스로 인터뷰·자료 요청) | Node.js + React 런타임 추가 필요 |
| 스킬 = Markdown + 코드 조합 — 우리 directives 패턴과 유사 | 멀티 프로바이더 미지원 (Anthropic only) |

---

## Step 2: 기술 검토 회의 시뮬레이션

> 내부 기술 검토 회의록 — 2026-04-05 가상 진행

### 2-1. 보안 및 샌드박스 (Security)

#### 논의 사항

**[보안 리드]** "우리 시스템은 Local-First(ADR-002)로 운영 중입니다. 외부 harness 프레임워크를 도입하면 파일시스템 접근 범위가 넓어질 수 있습니다. 특히 OpenHarness의 43+ 도구가 Bash 실행을 포함하고 있어, 우리의 기존 `execution/` 스크립트 격리 원칙과 충돌할 수 있습니다."

**[아키텍트]** "동의합니다. 하지만 OpenHarness와 DeepAgents 모두 권한 시스템을 내장하고 있습니다. OpenHarness는 3단계 모드(Default/Auto/Plan)와 경로별 규칙, command deny list를 제공합니다. 우리가 직접 구현하는 것보다 성숙할 수 있습니다."

**[보안 리드]** "AutoHarness의 YAML 헌법 접근은 흥미롭습니다. `execution/governance_checks.py`에서 이미 하고 있는 보안 검증을 선언적으로 관리할 수 있다면 유지보수가 용이해질 겁니다. 하지만 3일 된 프로젝트를 보안 경계에 넣을 수는 없습니다."

**[인프라 엔지니어]** "Docker/E2B 같은 샌드박스 없이 LLM이 파일 시스템에 직접 접근하는 것은 위험합니다. 현재 우리 시스템이 Windows 로컬에서 돌아가고 있어서, E2B나 Modal 같은 클라우드 샌드박스 도입은 Local-First 원칙과 충돌합니다."

#### 합의점

1. **현재 보안 경계를 유지한다.** 외부 harness의 Bash 도구를 그대로 도입하지 않고, 우리 `execution/` 스크립트를 도구로 래핑하는 방식을 채택한다.
2. **최소 권한 원칙 적용.** 도입 시 에이전트가 접근할 수 있는 경로를 `workspace/`, `projects/`, `.tmp/`로 명시 제한한다.
3. **AutoHarness의 YAML 거버넌스 패턴은 개념만 차용**하여 자체 구현한다 (프로젝트 자체 도입은 시기상조).
4. **샌드박스는 Windows 네이티브 프로세스 격리**(subprocess + 제한된 환경변수)로 시작하고, 필요 시 WSL2 컨테이너 격리를 단계적으로 도입한다.

---

### 2-2. 확장성 및 제어 (Scalability & Control)

#### 논의 사항

**[백엔드 리드]** "DeepAgents는 LangGraph 네이티브입니다. 장점은 체크포인터(상태 저장), 스트리밍, LangSmith 관측성이 바로 사용 가능한 것입니다. 하지만 우리의 3계층 아키텍처(ADR-001)는 이미 '지침 → 의사결정 → 실행' 분리를 하고 있어서, DeepAgents를 전면 도입하면 **중복 오케스트레이션 레이어**가 생깁니다."

**[아키텍트]** "맞습니다. 비유하자면, 우리가 이미 '부엌에서 요리사가 레시피(directives)를 보고 도구(execution)를 사용하는' 시스템을 만들었는데, DeepAgents는 '이 부엌 전체를 내 부엌으로 교체하자'고 말하는 것과 같습니다. 우리가 필요한 것은 부엌 교체가 아니라 **더 좋은 조리 도구 몇 개**입니다."

**[백엔드 리드]** "OpenHarness의 서브에이전트 스폰, 플러그인 시스템은 확장성 면에서 매력적입니다. MCP 클라이언트도 내장되어 있어 우리 MCP 서버들(sqlite-multi, system-monitor, telegram)과 바로 연결됩니다."

**[아키텍트]** "하지만 4일 된 프로젝트의 API가 안정될 때까지 기다리는 것이 현명합니다. 그 사이에 OpenHarness의 **미들웨어 패턴**(관측성, 호출 예산, 루프 감지)을 벤치마킹하여 우리 시스템에 선택적으로 이식할 수 있습니다."

**[QA]** "멀티 에이전트 확장에 대해서는 HarnessKit의 DAG 기반 병렬화와 비용 인식 에이전트 배정이 우리 fallback 체인과 잘 맞습니다. 문제는 HarnessKit 자체가 사실상 죽은 프로젝트라는 것입니다."

#### 합의점

1. **전면 교체가 아닌 선택적 패턴 차용.** 외부 프레임워크를 통째로 도입하기보다, 핵심 패턴(미들웨어 스택, 루프 감지, 관측성)을 우리 3계층 구조 내에 구현한다.
2. **DeepAgents SDK를 부분 활용.** 전체 에이전트 루프가 아닌 `create_deep_agent()`를 특정 태스크(예: 리서치, 코드 리뷰)에만 사용하는 **하이브리드 모델**을 검토한다.
3. **멀티 에이전트 확장은 우리 기존 구조 위에 구축.** `execution/` 스크립트 각각을 독립 에이전트가 호출하는 도구로 노출하는 방식으로 확장한다.
4. **HarnessKit의 비용 인식 라우팅 개념을 자체 구현**한다 (`llm_fallback_system`에 비용 가중치 추가).

---

### 2-3. 유지보수성 (Maintainability)

#### 논의 사항

**[테크 리드]** "5개 후보 중 유지보수 가능한 것은 **DeepAgents뿐**입니다. 19K Stars, LangChain 공식 지원, Harrison Chase 직접 참여, 일일 커밋. 나머지 4개는 모두 1개월 미만이거나 사실상 비활성 프로젝트입니다."

**[아키텍트]** "LangChain 생태계 종속성은 양날의 검입니다. LangChain은 과거에 급격한 API 변경으로 많은 프로젝트를 깨뜨린 전력이 있습니다. langchain-core → langgraph → langsmith 의존성 체인이 무겁고, 우리의 '결정론적 코드 우선' 원칙과 충돌합니다."

**[테크 리드]** "OpenHarness는 4일 만에 3,500 stars를 얻었는데, 이는 Claude Code 클론에 대한 시장 수요를 보여줍니다. 하지만 HKU 연구실의 장기 커밋먼트는 불확실합니다. 유사 프로젝트(FastHarness, deepagentsjs)가 이미 포크되고 있어 생태계가 파편화될 수 있습니다."

**[아키텍트]** "가장 안전한 접근은 **'관찰자 모드'**입니다. 우리 시스템이 이미 Harness 패턴을 따르고 있으므로, 외부 의존성을 급히 추가하기보다 우리 자체 harness를 **공식화**하는 것이 우선입니다."

**[보안 리드]** "동의합니다. Anthropic이 발표한 3-에이전트 harness 디자인(Planner/Generator/Evaluator)도 프레임워크가 아닌 **패턴**으로 제공됩니다. 우리도 패턴을 채택하되 구현은 자체적으로 하는 것이 유지보수에 유리합니다."

#### 합의점

1. **DeepAgents만 유일한 유지보수 가능 후보**로 인정하되, 전면 도입은 의존성 리스크 때문에 보류한다.
2. **우리 자체 harness를 공식화**한다 — 현재 3계층 구조에 Harness Engineering 모범 사례(미들웨어, 관측성, 루프 감지)를 체계적으로 추가한다.
3. **외부 프로젝트 모니터링 체계를 구축**한다 — OpenHarness, DeepAgents의 GitHub을 주기적으로 관찰하여 안정화 시점을 판단한다.
4. **패턴 차용 > 프레임워크 도입** 원칙을 확립한다.

---

## Step 3: 최종 도입 의사결정

### 결론: **조건부 도입 찬성 — "패턴 우선, 프레임워크 보류"**

#### 근거

1. **우리는 이미 Harness를 갖고 있다.** 3계층 아키텍처(ADR-001), self-annealing 루프, `.ai/` 컨텍스트 시스템, `execution/` 결정론적 스크립트 — 이것들이 바로 Harness의 핵심 요소다. 외부 프레임워크를 통째로 도입하는 것은 **기존 투자를 버리는 것**과 같다.

2. **5개 후보 중 프로덕션 준비가 된 것은 없다.**
   - DeepAgents(19K Stars)만이 유일하게 성숙하지만, LangChain 종속성이 우리 아키텍처 원칙과 충돌한다.
   - 나머지 4개는 모두 1개월 미만이거나 비활성 상태다.

3. **Harness Engineering은 프레임워크가 아니라 디시플린이다.** Mitchell Hashimoto, Anthropic, OpenAI 모두 특정 프레임워크가 아닌 **엔지니어링 원칙**을 제안한다.

#### 선정 결과

| 역할 | 선정 | 이유 |
|------|------|------|
| **PoC용 (빠른 검증)** | **DeepAgents SDK** (`deepagents` 패키지) | 가장 성숙한 생태계, `create_deep_agent()` 한 줄로 시작 가능, 우리 파이프라인의 특정 태스크(예: 리서치 서브에이전트)에 격리 도입 가능. 전체 오케스트레이션이 아닌 **도구 하나**로 활용. |
| **프로덕션 메인** | **자체 Harness 공식화** (OpenHarness 패턴 참조) | 우리 3계층 구조를 유지하면서, OpenHarness의 미들웨어 스택·루프 감지·관측성 패턴을 선택적으로 이식. 외부 의존성 없이 자체 통제 유지. |

#### 추가 검토 필요 사항 (정보 불확실)

| 항목 | 불확실 요인 | 권장 조치 |
|------|------------|----------|
| OpenHarness 장기 유지보수 | HKU 연구실의 커밋먼트 불명확, 4일 된 프로젝트 | 2-3개월 관찰 후 재평가 |
| AutoHarness의 YAML 헌법 실효성 | 실제 프로덕션 적용 사례 없음 | 우리 `governance_checks.py`와 비교 PoC 진행 |
| DeepAgents의 LangChain 의존성 안정성 | LangChain의 역사적 breaking change 패턴 | 버전 핀닝 + 격리 환경에서만 사용 |
| HarnessKit의 DAG 엔진 실재 여부 | 문서만 있고 코드 미확인 | 도입 불가, 개념만 참고 |

---

## Step 4: 단계별 도입 로드맵 및 가이드라인

### 비유: "자동차 튜닝, 차량 교체 아님"

우리의 접근은 차를 새로 사는 것이 아니라, **기존 차에 계기판(관측성), ABS 브레이크(루프 감지), 크루즈 컨트롤(미들웨어)을 장착**하는 것이다. 엔진(LLM)과 차체(3계층 구조)는 그대로 유지한다.

### Phase 1: 자체 Harness 공식화 (Week 1-2)

**목표:** 기존 3계층 구조를 Harness Engineering 용어로 재정의하고, 부족한 부분을 식별한다.

```
현재 구조                          Harness 용어 매핑
──────────────────────────────────────────────────────────
directives/                    →  Knowledge & Memory Layer
  ├── *.md (SOP)                   (AGENTS.md 패턴과 동일)
  └── config.yaml                  (Agent 행동 경계 정의)

AI Orchestration               →  Agent Loop
  ├── CLAUDE.md 읽기                (System Prompt Assembly)
  ├── 지침 기반 의사결정              (Intelligent Routing)
  └── 오류 → 자가 수정               (Self-Annealing = Harness 핵심)

execution/                     →  Deterministic Tool Layer
  ├── *.py 스크립트                  (Permission-Gated Tools)
  ├── governance_checks.py          (Middleware: Claims Verification)
  └── qaqc_runner.py               (Middleware: Quality Gate)

[부족한 부분 - 신규 구현 대상]
  ├── 🆕 관측성 미들웨어             (토큰 사용량, 레이턴시, 도구 호출 로그)
  ├── 🆕 루프 감지 미들웨어           (반복 호출 감지 & 개입)
  ├── 🆕 호출 예산 미들웨어           (토큰/비용 상한선)
  └── 🆕 공식 권한 매트릭스           (에이전트별 도구·경로 접근 규칙)
```

**구현 태스크:**

| # | 태스크 | 파일 | 설명 |
|---|--------|------|------|
| 1 | Harness 미들웨어 기본 골격 | `execution/harness_middleware.py` | 모든 LLM 호출을 감싸는 데코레이터/컨텍스트 매니저 |
| 2 | 관측성 미들웨어 | (위 파일 내) | 호출별 토큰 수, 레이턴시, 도구명 로깅 → `workspace.db` |
| 3 | 루프 감지 미들웨어 | (위 파일 내) | 최근 N회 도구 호출 슬라이딩 윈도우, 3회 동일 패턴 시 경고 |
| 4 | 호출 예산 미들웨어 | (위 파일 내) | 세션당 최대 토큰/비용 제한, 초과 시 인간 승인 요청 |
| 5 | 권한 매트릭스 YAML | `directives/agent_permissions.yaml` | 에이전트별 허용 도구·경로 선언적 정의 |

**보안 가이드라인 — 최소 권한 원칙 적용:**

```yaml
# directives/agent_permissions.yaml 예시 구조
agents:
  blind-to-x-pipeline:
    allowed_paths:
      - "projects/blind-to-x/**"
      - ".tmp/**"
    denied_paths:
      - ".env"
      - "credentials.json"
      - "token.json"
    allowed_tools:
      - "execution/pipeline/*.py"
      - "execution/content_intelligence.py"
    max_tokens_per_session: 500000
    max_cost_per_session_usd: 2.0
    require_human_approval:
      - file_delete
      - external_api_post
      - git_push

  shorts-maker-v2-pipeline:
    allowed_paths:
      - "projects/shorts-maker-v2/**"
      - ".tmp/**"
    allowed_tools:
      - "execution/youtube_*.py"
      - "execution/content_db.py"
    max_tokens_per_session: 300000
    max_cost_per_session_usd: 5.0  # 이미지/TTS 비용 포함
```

### Phase 2: DeepAgents PoC (Week 3-4)

**목표:** DeepAgents SDK를 격리된 환경에서 시험하여, 우리 파이프라인의 특정 태스크에 부분 적용 가능한지 검증한다.

**범위 제한:** blind-to-x의 "콘텐츠 리서치" 단계에만 적용 (전체 파이프라인이 아님).

```python
# PoC 구조: execution/harness_poc_deepagents.py

"""
DeepAgents SDK PoC — blind-to-x 리서치 서브에이전트
Phase 2 검증 목적. 프로덕션 도입 전 평가용.
"""
from deepagents import create_deep_agent

def run_research_subagent(topic: str, config: dict) -> dict:
    """
    DeepAgents를 서브에이전트로 활용하여 주제 리서치 수행.
    우리 3계층 구조의 execution/ 레이어에서 '도구'로 호출됨.
    
    비유: 우리 요리사(오케스트레이션)가 재료 조사를
    전문 조사원(DeepAgents)에게 위탁하는 것.
    요리 자체는 우리 부엌(execution/)에서 한다.
    """
    agent = create_deep_agent(
        model=config.get("model", "claude-sonnet-4-6"),
        # 최소 도구만 부여 (최소 권한 원칙)
        tools=["web_search", "read_file"],
        # 파일시스템 접근 제한
        workspace=".tmp/deepagents_sandbox/",
        # 비용 상한
        max_tokens=100000,
    )
    
    result = agent.invoke({
        "messages": [{
            "role": "user",
            "content": f"Research the following topic and provide a structured summary: {topic}"
        }]
    })
    
    return {
        "summary": result["messages"][-1]["content"],
        "tokens_used": result.get("usage", {}).get("total_tokens", 0),
        "cost_usd": result.get("usage", {}).get("cost", 0),
    }
```

**PoC 평가 기준:**

| 기준 | 통과 조건 |
|------|----------|
| 기능성 | 리서치 결과 품질이 현재 직접 LLM 호출 대비 동등 이상 |
| 격리성 | `.tmp/deepagents_sandbox/` 외부 파일 접근 없음 |
| 비용 | 세션당 $0.50 미만 |
| 의존성 | `pip install deepagents`만으로 설치 완료, 다른 서비스 불필요 |
| 안정성 | 10회 연속 실행 시 오류율 10% 미만 |

### Phase 3: 미들웨어 고도화 + 패턴 이식 (Week 5-8)

**목표:** OpenHarness에서 검증된 패턴을 우리 시스템에 선택적으로 이식한다.

| 이식 대상 패턴 | 출처 | 우리 구현 위치 | 설명 |
|---------------|------|---------------|------|
| **컨텍스트 자동 압축** | OpenHarness, DeepAgents | `execution/harness_middleware.py` | 컨텍스트 윈도우 80% 도달 시 이전 대화 요약 |
| **도구 결과 파일 오프로드** | DeepAgents | `execution/harness_middleware.py` | 5KB 초과 도구 출력을 `.tmp/` 파일로 저장, 참조만 반환 |
| **Generator-Evaluator 분리** | Anthropic 3-agent 패턴 | `execution/harness_eval.py` | 생성 결과를 별도 평가 에이전트가 검증 |
| **YAML 거버넌스** | AutoHarness | `directives/agent_permissions.yaml` | 위험 분류 + 정책 선언적 관리 |
| **비용 인식 라우팅** | HarnessKit 개념 | `execution/llm_router.py` | 기존 fallback 체인에 비용/할당량 가중치 추가 |

### Phase 4: 외부 프레임워크 재평가 (Month 3+)

**목표:** OpenHarness, DeepAgents의 안정화 상태를 재평가하고, 필요 시 부분 도입을 확대한다.

| 재평가 기준 | OpenHarness | DeepAgents |
|------------|-------------|------------|
| GitHub Stars 추이 | 10K+ 달성? | 25K+ 유지? |
| 릴리스 안정성 | v1.0 출시? | v1.0 출시? (현재 0.5.0a4) |
| 기여자 다양성 | 20명+ 기여자? | 유지 중? |
| Breaking changes | Major breaking 없음? | LangChain 호환성 유지? |
| 우리 PoC 결과 | Phase 2 통과? | Phase 2 통과? |

**재평가 시점에 가능한 시나리오:**

- **시나리오 A:** 자체 Harness가 충분히 성숙 → 외부 도입 불필요
- **시나리오 B:** DeepAgents가 안정화 → 리서치/평가 서브에이전트로 확대 적용
- **시나리오 C:** OpenHarness가 안정화 + MCP 생태계 성숙 → 우리 MCP 서버와 통합 검토

---

## 전체 로드맵 타임라인

```
Week 1-2        Week 3-4         Week 5-8          Month 3+
─────────────────────────────────────────────────────────────
[Phase 1]       [Phase 2]        [Phase 3]         [Phase 4]
자체 Harness     DeepAgents       패턴 이식          재평가
공식화           PoC              고도화

 ┌──────────┐   ┌──────────┐    ┌──────────┐     ┌──────────┐
 │미들웨어   │   │리서치     │    │컨텍스트   │     │외부 FW   │
 │골격 구현  │   │서브에이전트│    │압축 구현  │     │재평가    │
 │          │   │격리 테스트 │    │          │     │          │
 │관측성     │   │          │    │평가자 분리│     │도입 확대 │
 │루프 감지  │   │비용/성능  │    │          │     │or 자체   │
 │예산 제한  │   │벤치마크   │    │비용 라우팅│     │유지 결정 │
 │          │   │          │    │          │     │          │
 │권한 YAML │   │통과/탈락  │    │YAML 거버 │     │          │
 │정의      │   │판정      │    │넌스      │     │          │
 └──────────┘   └──────────┘    └──────────┘     └──────────┘
```

---

## 부록: 참고 자료

### 핵심 문헌

| 자료 | 저자/조직 | 핵심 기여 |
|------|----------|----------|
| [Harness Engineering for Coding Agent Users](https://martinfowler.com/articles/harness-engineering.html) | Birgitta Bockeler (Martin Fowler 사이트) | Guides/Sensors 프레임워크, 컴퓨테이셔널 vs 추론적 제어 |
| [The Anatomy of an Agent Harness](https://blog.langchain.com/the-anatomy-of-an-agent-harness/) | Vivek Trivedy (LangChain) | "Agent = Model + Harness" 공식화, 컴포넌트 분류 |
| [Effective Harnesses for Long-Running Agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) | Anthropic Engineering | 초기화/코딩 2-에이전트 harness 패턴 |
| [Harness Design for Long-Running Apps](https://www.anthropic.com/engineering/harness-design-long-running-apps) | Anthropic Engineering | Planner/Generator/Evaluator 3-에이전트 패턴 |
| [Harness Engineering — Leveraging Codex](https://openai.com/index/harness-engineering/) | OpenAI | AGENTS.md 패턴, 재현 가능 환경, 기계적 불변량 |
| [Meta-Harness (arXiv:2603.28052)](https://arxiv.org/html/2603.28052v1) | Stanford/MIT/KRAFTON | Harness 자동 최적화, 6x 성능 차이 실증 |
| [AutoHarness (arXiv:2603.03329)](https://arxiv.org/abs/2603.03329) | Google DeepMind | 자동 harness 합성, 소형 모델이 대형 모델 능가 실증 |

### 관련 프레임워크 생태계

| Tier | 프레임워크 | 용도 |
|------|----------|------|
| **Tier 1** (성숙) | LangGraph, CrewAI, OpenAI Agents SDK | 프로덕션 에이전트 오케스트레이션 |
| **Tier 2** (성장) | Pydantic AI, Google ADK, Strands (AWS), Agno | 특화 에이전트 빌딩 |
| **샌드박싱** | E2B (Firecracker microVM), Modal (gVisor) | 에이전트 코드 실행 격리 |

---

> **최종 요약:**  
> Harness Engineering AI 도입은 **찬성**하되, 외부 프레임워크 전면 교체가 아닌 **"패턴 차용 + 자체 Harness 공식화"** 전략을 취한다. 우리의 3계층 아키텍처는 이미 Harness의 핵심을 구현하고 있으며, 부족한 미들웨어(관측성, 루프 감지, 예산 제한)를 체계적으로 보강하는 것이 가장 높은 ROI를 제공한다. DeepAgents SDK는 격리된 PoC로 부분 검증하고, OpenHarness는 2-3개월 관찰 후 재평가한다.
