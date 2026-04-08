---
description: 검증 워크플로우 — 프로젝트별 검증 커맨드 실행, 실패 시 자동 수정
---

# /verify — 검증 워크플로우

// turbo-all

## 목적

코드 변경 후 반드시 실행하는 검증 단계. Anthropic의 "Give Claude a way to verify its work" 원칙 적용.
**검증 없이 완료 선언 금지.**

## 실행 절차

1. **프로젝트 감지** — 현재 작업 중인 프로젝트 디렉터리 확인.
   - 해당 프로젝트 `CLAUDE.md`의 "검증 커맨드" 섹션을 열어 확인한다.

2. **Lint 실행**
   - Python 프로젝트: `ruff check . --fix`
   - Next.js 프로젝트: `npm run lint`

3. **테스트 실행**
   - Python: `python -m pytest --no-cov tests/unit/ -x`
   - Next.js: `npm test`
   - 실패 시: 에러 메시지 읽고 자동 수정 → 재실행 (최대 3회)

4. **결과 보고**
   - 통과 수, 실패 수, 경고 항목 요약
   - 실패가 남아 있으면 사용자에게 보고 후 중단

5. **TASKS.md 업데이트** — 검증 완료 항목을 DONE으로 이동

## 프로젝트별 검증 커맨드 빠른 참조

| 프로젝트 | Lint | Test |
|---------|------|------|
| `blind-to-x` | `ruff check . --fix` | `python -m pytest --no-cov tests/unit/ -x` |
| `hanwoo-dashboard` | `npm run lint` | `npm test` |
| `shorts-maker-v2` | `ruff check . --fix` | `python -m pytest --no-cov tests/unit/ -x` |
| `knowledge-dashboard` | `npm run lint` | (해당 없음) |

## 자가 수정 루프

```
테스트 실패 → 에러 읽기 → 수정 → 재실행
               (최대 3회 반복)
               3회 후에도 실패 → 사용자에게 보고, /debug 워크플로우 시작
```
