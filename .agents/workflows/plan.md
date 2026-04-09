---
description: Plan Mode 워크플로우 — Explore 완료 후 Implementation Plan 작성, 사용자 승인 후 Code 단계 진입
---

# /plan — Plan Mode 워크플로우

// turbo-all

## 목적

`Explore → Plan → Code → Verify` 4단계 워크플로우에서 **Plan 단계**를 공식화한다.

- Explore(조사)가 완료된 시점에 이 워크플로우를 실행한다.
- Implementation Plan 작성 → 사용자 승인 대기 → Code 단계 진입.
- **사용자 승인 없이 코드 수정 시작 금지.**

---

## 실행 절차

### 1. Explore 완료 확인
아래 항목이 모두 충족되었는지 확인한다:

- [ ] 변경할 파일 목록 파악 완료
- [ ] 기존 패턴/컨벤션 파악 완료 (코드 스타일, 네이밍, 테스트 위치)
- [ ] 영향 범위(impact radius) 파악 완료
- [ ] 알려진 지뢰밭 확인 완료 (`CONTEXT.md` → "지뢰밭" 섹션)
- [ ] Investigator 결과 수신 완료 (병렬 탐색한 경우)

> 위 항목 미충족 시: Explore 계속 실행, Plan 진입 금지.

---

### 2. Implementation Plan 작성

아래 템플릿을 사용해 `implementation_plan.md` 아티팩트를 작성한다.

```markdown
# [목표 설명]

## 배경
(문제 상황, 현재 상태, 변경 이유)

## 사용자 검토 필요 사항
(파괴적 변경, 아키텍처 결정, ADR 영향 — IMPORTANT/WARNING 알럿 사용)

## 변경 계획

### [컴포넌트명]
#### [MODIFY] 파일명
- 변경 내용 요약

#### [NEW] 파일명
- 신규 파일 목적

#### [DELETE] 파일명
- 삭제 이유

## 미결 질문
(구현에 영향을 주는 불확실한 사항)

## 검증 계획
- 실행할 커맨드
- 확인할 항목
```

---

### 3. 사용자 승인 대기

Plan 작성 후 반드시 다음을 명시하고 대기한다:

```
✅ Implementation Plan 작성 완료.
승인하시면 Code 단계를 시작합니다.
수정이 필요하면 피드백 주세요.
```

> **Code 단계는 사용자의 명시적 승인(예: "진행", "ok", "continue") 후에만 시작.**

---

### 4. ADR/DECISIONS 검토 (필수)

Plan 내용이 기존 아키텍처 결정(`.ai/DECISIONS.md`)과 충돌하는지 확인:

| 체크 항목 | 확인 방법 |
|-----------|-----------|
| 3계층 구조(ADR-001) 준수 | Directive→Orchestration→Execution 흐름 유지 |
| 로컬 우선 정책(ADR-002) | API 키/민감 데이터 로컬 유지 |
| 결정론적 스크립트 선호 | 복잡 로직은 `execution/` Python 스크립트로 |

충돌 발견 시: Plan에 명시하고 사용자 결정 요청.

---

### 5. Code 단계 진입 조건

모두 충족 시 진입:

- [ ] Implementation Plan 작성 완료
- [ ] 사용자 승인 확인
- [ ] ADR 충돌 없음 (또는 사용자 인지 후 진행 결정)
- [ ] 테스트 작성 계획 포함

---

## 관련 워크플로우

- `/start` — Explore 단계 진입점
- `/verify` — Code 완료 후 검증
- `/debug` — Code 중 예상치 못한 오류 발생 시

## 관련 파일

- `.agents/agents/investigator.md` — Explore 단계 병렬 탐색 에이전트
- `.ai/DECISIONS.md` — 확정된 아키텍처 결정 (변경 금지)
- `AGENTS.md` / `GEMINI.md` — 탐색-계획-코드-검증 전체 워크플로우
