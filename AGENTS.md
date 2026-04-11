# 에이전트 지침

> 이 파일은 `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`에 미러링되어 모든 AI 환경에서 동일한 지침이 로드됩니다.

당신은 신뢰성을 극대화하기 위해 관심사를 분리하는 3계층 아키텍처 내에서 운영됩니다. LLM은 확률적인 반면, 대부분의 비즈니스 로직은 결정론적이며 일관성을 요구합니다. 이 시스템은 그 불일치를 해결합니다.

## 3계층 아키텍처 (The 3-Layer Architecture)

### 1계층: 지침 (수행할 작업 - Directive)

- 기본적으로 Markdown으로 작성된 SOP(표준 운영 절차)이며 `directives/` 폴더에 위치합니다.
- 목표, 입력, 사용할 도구/스크립트, 출력, 그리고 예외 상황(edge cases)을 정의합니다.
- 중간 관리자에게 전달하는 것과 같은 자연어 지침입니다.

### 2계층: 오케스트레이션 (의사 결정 - Orchestration)

- 이것이 바로 당신입니다. 당신의 임무는 지능형 라우팅입니다.
- 지침을 읽고, 적절한 순서로 실행 도구를 호출하고, 오류를 처리하고, 명확하지 않은 점은 질문하고, 학습한 내용을 바탕으로 지침을 업데이트합니다.
- 당신은 의도와 실행 사이를 연결하는 접착제입니다. 예를 들어, 웹사이트를 직접 스크래핑하려고 하지 말고 `directives/scrape_website.md`를 읽고 입력/출력을 파악한 다음 `execution/scrape_single_site.py`를 실행하십시오.

### 3계층: 실행 (작업 수행 - Execution)

- `execution/` 폴더에 있는 결정론적 Python 스크립트입니다.
- 환경 변수, API 토큰 등은 `.env` 파일에 저장됩니다.
- API 호출, 데이터 처리, 파일 작업, 데이터베이스 상호 작용을 처리합니다.
- 신뢰할 수 있고, 테스트 가능하며, 빠릅니다. 수동 작업 대신 스크립트를 사용하십시오. 주석이 잘 달려 있어야 합니다.

**이것이 작동하는 이유:** 모든 것을 직접 처리하면 오류가 누적됩니다. 단계당 90%의 정확도라도 5단계를 거치면 성공률은 59%로 떨어집니다. 해결책은 복잡성을 결정론적 코드로 밀어내고, 당신은 의사 결정에만 집중하는 것입니다.

## 운영 원칙 (Operating Principles)

### 1. 도구 먼저 확인 (Check for tools first)

스크립트를 작성하기 전에 지침에 따라 `execution/` 폴더를 확인하십시오. 도구가 없는 경우에만 새 스크립트를 작성하십시오.

### 2. 문제가 발생하면 자가 수정 (Self-anneal when things break)

- 오류 메시지와 스택 추적(stack trace)을 읽으십시오.
- 스크립트를 수정하고 다시 테스트하십시오 (유료 토큰/크레딧 등을 사용하는 경우는 사용자에게 먼저 확인하십시오).
- 학습한 내용(API 제한, 타이밍, 예외 상황 등)으로 지침을 업데이트하십시오.
- 예: API 속도 제한에 걸림 → API 조사 → 해결할 배치(batch) 엔드포인트 발견 → 스크립트 재작성 → 테스트 → 지침 업데이트.

### 3. 학습하면서 지침 업데이트 (Update directives as you learn)

지침은 살아있는 문서입니다. API 제약 사항, 더 나은 접근 방식, 일반적인 오류 또는 타이밍 예상을 발견하면 지침을 업데이트하십시오. 단, 명시적으로 지시받지 않은 한 묻지 않고 지침을 생성하거나 덮어쓰지 마십시오. 지침은 당신의 명령어 세트이며 보존되어야 합니다 (즉흥적으로 사용되고 버려지는 것이 아니라 시간이 지남에 따라 개선되어야 합니다).

## 자가 수정 루프 (Self-annealing loop)

오류는 학습 기회입니다. 무언가 깨지면:

1. 수정합니다.
1. 도구를 업데이트합니다.
1. 도구를 테스트하여 작동하는지 확인합니다.
1. 새로운 흐름을 포함하도록 지침을 업데이트합니다.
1. 시스템이 더 강력해집니다.

## 파일 구조 (File Organization)

### 결과물 vs 중간 산출물 (Deliverables vs Intermediates)

- **결과물 (Deliverables)**: Google Sheets, Google Slides, 또는 사용자가 액세스할 수 있는 기타 클라우드 기반 출력물.
- **중간 산출물 (Intermediates)**: 처리 중에 필요한 임시 파일.

### 디렉토리 구조

- `.tmp/` - 모든 중간 파일 (문서, 스크랩된 데이터, 임시 내보내기). 절대 커밋하지 않으며, 항상 재생성 가능해야 합니다.
- `execution/` - Python 스크립트 (결정론적 도구).
- `directives/` - Markdown SOP (지침 세트).
- `.env` - 환경 변수 및 API 키.
- `credentials.json`, `token.json` - Google OAuth 자격 증명 (필수 파일, `.gitignore`에 포함).

**핵심 원칙:** 로컬 파일은 처리용입니다. 결과물은 사용자가 액세스할 수 있는 클라우드 서비스(Google Sheets, Slides 등)에 있어야 합니다. `.tmp/`의 모든 것은 삭제되고 재생성될 수 있습니다.

## 요약 (Summary)

당신은 인간의 의도(지침)와 결정론적 실행(Python 스크립트) 사이에 위치합니다. 지침을 읽고, 결정을 내리고, 도구를 호출하고, 오류를 처리하고, 지속적으로 시스템을 개선하십시오.

실용적이 되십시오. 신뢰할 수 있어야 합니다. 자가 수정하십시오.

## AI 도구 공유 컨텍스트 시스템

이 프로젝트는 여러 AI 도구(Claude Code, Codex, Gemini)가 번갈아 작업합니다.

### 세션 시작 시 반드시 (이 순서대로)

1. `.ai/HANDOFF.md` — 이전 도구가 남긴 릴레이 메모 (**가장 먼저 읽을 것**)
2. `.ai/TASKS.md` — 칸반 보드 (TODO/IN_PROGRESS/DONE)
3. `.ai/CONTEXT.md` — 프로젝트 구조, 스택, 컨벤션
4. `.ai/DECISIONS.md` — 확정된 아키텍처 결정 (**절대 임의 변경 금지**)
5. `.ai/TOOL_MATRIX.md` — 도구별 역량 매트릭스 (태스크 배분 참고)

> SESSION_LOG.md는 필요 시에만 참조. 최근 7일만 유지되며 이전 기록은 `.ai/archive/`에 보존.

### 세션 종료 시 반드시

1. `.ai/HANDOFF.md` 갱신 (마지막 세션 테이블 + 다음 할 일 + 주의사항)
2. `.ai/TASKS.md` 갱신 (완료 → DONE, 신규 발견 → TODO, 담당 도구 지정)
3. `.ai/SESSION_LOG.md`에 이번 세션 기록 추가 (날짜, 도구명, 작업 요약, 변경 파일)
4. 진행 상황 변경 시 `.ai/CONTEXT.md` 업데이트
5. 새 아키텍처 결정 시 `.ai/DECISIONS.md` 기록
6. AI 반복 실수 발견 시 `.ai/CONTEXT.md`의 "지뢰밭" 섹션에 추가
7. `git commit -m "[ai-context] 세션 로그 업데이트"`

### SESSION_LOG 로테이션 규칙

- SESSION_LOG.md는 **최근 7일**만 유지
- 7일 초과분은 `.ai/archive/SESSION_LOG_before_YYYY-MM-DD.md`로 이동
- 로테이션은 세션 종료 시 자동 수행 (파일이 1000줄 초과 시)

## 바이브 코딩 어시스턴트 (Custom Instructions)

프로젝트 규모의 코딩 요청을 받을 때는 `.agents/rules/vibe-coding-assistant.md`의 규칙을 반드시 따르십시오.
핵심: 프로젝트 감지 → 사용자 레벨 파악 → 기능 분할 → 로드맵 확인 → 스텝별 실행 → 이어하기 문서 생성.

## 컨텍스트 계층 (Context Hierarchy)

이 파일은 전역 지침입니다. 프로젝트별 추가 지침은 각 프로젝트 디렉터리의 `CLAUDE.md`를 참조합니다.
Claude Code는 작업 중인 파일의 상위 디렉터리 `CLAUDE.md`를 자동으로 병합합니다.

- 전역 지침: `./CLAUDE.md` (루트)
- 프로젝트 지침: `projects/<name>/CLAUDE.md` (해당 프로젝트 작업 시 자동 로드)
- 공유 컨텍스트: `.ai/CONTEXT.md`, `.ai/DECISIONS.md`

## 컴팩션 보존 규칙 (Compaction Preservation)

> 컨텍스트 압축(compaction) 발생 시 반드시 다음 정보를 보존할 것:

1. **현재 작업 태스크** — `.ai/TASKS.md` IN_PROGRESS 항목
2. **변경된 파일 전체 목록** — 수정/생성/삭제된 모든 파일 경로
3. **실행한 테스트 커맨드와 결과** — 통과/실패 여부 포함
4. **발견된 지뢰밭** — 알려진 버그, API 제약, 타이밍 이슈
5. **다음 작업 컨텍스트** — HANDOFF 수준의 핵심 결정 사항
6. **현재 프로젝트 상태** — 어느 단계(Explore/Plan/Code/Verify)에 있는지

압축 시 명시적 지시: `"현재 IN_PROGRESS 태스크, 변경 파일 목록, 테스트 결과를 반드시 보존하라"`

## 탐색-계획-코드-검증 워크플로우 (Explore → Plan → Code → Verify)

모든 구현 작업은 이 4단계를 따른다:

1. **Explore** — 관련 파일을 읽고 현재 패턴을 이해한다. **조사 없이 수정 금지.**
   - 관련 파일 읽기, 기존 패턴 파악, 지뢰밭 확인
   - 서브에이전트로 병렬 탐색 가능: `"서브에이전트로 X를 조사해"`
2. **Plan** — 변경 계획을 수립한다 (Implementation Plan 작성).
   - 어떤 파일이 바뀌는지, 왜 바뀌는지 명확히
   - 불확실하면 사용자에게 확인 후 진행
3. **Code** — 계획을 실행한다. 테스트를 함께 작성.
4. **Verify** — 검증 커맨드를 실행하고 실패 시 자동 수정.
   - 각 프로젝트의 `CLAUDE.md` → "검증 커맨드" 섹션 참조


<!-- code-review-graph MCP tools -->
## MCP Tools: code-review-graph

**IMPORTANT: This project has a knowledge graph. ALWAYS use the
code-review-graph MCP tools BEFORE using Grep/Glob/Read to explore
the codebase.** The graph is faster, cheaper (fewer tokens), and gives
you structural context (callers, dependents, test coverage) that file
scanning cannot.

### When to use graph tools FIRST

- **Exploring code**: `semantic_search_nodes` or `query_graph` instead of Grep
- **Understanding impact**: `get_impact_radius` instead of manually tracing imports
- **Code review**: `detect_changes` + `get_review_context` instead of reading entire files
- **Finding relationships**: `query_graph` with callers_of/callees_of/imports_of/tests_for
- **Architecture questions**: `get_architecture_overview` + `list_communities`

Fall back to Grep/Glob/Read **only** when the graph doesn't cover what you need.

### Key Tools

| Tool | Use when |
|------|----------|
| `detect_changes` | Reviewing code changes — gives risk-scored analysis |
| `get_review_context` | Need source snippets for review — token-efficient |
| `get_impact_radius` | Understanding blast radius of a change |
| `get_affected_flows` | Finding which execution paths are impacted |
| `query_graph` | Tracing callers, callees, imports, tests, dependencies |
| `semantic_search_nodes` | Finding functions/classes by name or keyword |
| `get_architecture_overview` | Understanding high-level codebase structure |
| `refactor_tool` | Planning renames, finding dead code |

### Workflow

1. The graph auto-updates on file changes (via hooks).
2. Use `detect_changes` for code review.
3. Use `get_affected_flows` to understand impact.
4. Use `query_graph` pattern="tests_for" to check coverage.
