---
description: 검증 워크플로우 — 프로젝트별 검증 커맨드 실행, 실패 시 자동 수정
---

# /verify — 검증 워크플로우

// turbo-all

## 목적

코드 변경 후 반드시 실행하는 검증 단계. Anthropic의 "Give Claude a way to verify its work" 원칙 적용.
**검증 없이 완료 선언 금지.**

## 실행 절차

> 표준 검증은 워크스페이스 루트에서 `execution/project_qc_runner.py`로 실행한다.
> 프로젝트 루트의 직접 커맨드는 `projects/<name>/CLAUDE.md`의 보조 경로로만 사용한다.

1. **프로젝트 감지** — 현재 작업 중인 프로젝트 디렉터리 확인.
   - 해당 프로젝트 `projects/<name>/CLAUDE.md`의 "검증 커맨드" 섹션을 읽는다.
   - 워크스페이스 루트에서 다음 중 하나를 실행한다.

   ```bash
   python execution/project_qc_runner.py --project <name> --json
   python execution/project_qc_runner.py --project <name> --check test --json
   python execution/project_qc_runner.py --project <name> --check lint --json
   python execution/project_qc_runner.py --project <name> --check build --json
   ```

2. **Check 선택**
   - Python 프로젝트: `test`, `lint`
   - Next.js 프로젝트: `test`, `lint`, `build`
   - 시간이 중요한 경우 `--check`로 좁히고, 완료 선언 전에는 해당 변경 범위에 필요한 check를 모두 실행한다.

3. **실패 시 자가 수정**
   - 에러 메시지와 스택 트레이스를 읽는다.
   - `ruff check . --fix`처럼 코드를 자동 수정하는 명령은 변경사항을 확인한 뒤 프로젝트 루트에서 실행한다.
   - 수정 후 같은 `project_qc_runner.py` 명령을 재실행한다. 최대 3회 반복 후에도 실패하면 사용자에게 보고한다.

4. **결과 보고**
   - 통과 수, 실패 수, 경고 항목 요약
   - 실패가 남아 있으면 사용자에게 보고 후 중단

5. **Impact Radius 확인** — 코드 그래프 활용 (Python 프로젝트)
   ```bash
   # 예시: pipeline/express_draft.py 수정 후
   $env:PYTHONUTF8='1'; python3.13 -m code_review_graph impact pipeline/express_draft.py
   ```
   - 영향받는 파일 목록 자동 파악
   - 해당 파일에 대한 테스트가 `/verify` 실행 목록에 포함되었는지 확인
   - **참고**: `hanwoo-dashboard`는 JS flow detection이 제한적, IMPORTS_FROM 엣지만 활용

6. **`.ai/TASKS.md` 업데이트** — 검증 완료 항목을 DONE으로 이동 (파일 위치: `c:\Users\박주호\Desktop\Vibe coding\.ai\TASKS.md`)

## 프로젝트별 검증 커맨드 빠른 참조

| 프로젝트 | 상태 | 표준 check | 직접 실행 커맨드 |
|---------|------|-----------|----------------|
| `blind-to-x` | active | `test`, `lint` | `python -m pytest --no-cov tests/unit -q --tb=short --maxfail=1`; `python -m ruff check .` |
| `shorts-maker-v2` | active | `test`, `lint` | `python -m pytest --no-cov tests/unit tests/integration -q --tb=short --maxfail=1`; `python -m ruff check .` |
| `hanwoo-dashboard` | active | `test`, `lint`, `build` | `npm test`; `npm run lint`; `npm run build` |
| `knowledge-dashboard` | maintenance | `test`, `lint`, `build` | `npm test`; `npm run lint`; `npm run build` |

## 자가 수정 루프

```
테스트 실패 → 에러 읽기 → 수정 → 재실행
               (최대 3회 반복)
               3회 후에도 실패 → 사용자에게 보고, /debug 워크플로우 시작
```

## 주의사항

- `execution/project_qc_runner.py --list --json`으로 현재 등록된 프로젝트/check를 확인할 수 있다.
- `ruff check . --fix`는 **코드를 자동 수정**한다. 실행 전 스테이지 확인 권장.
- E2E 테스트(`test_escalation_e2e.py` 등)는 **실제 API 호출**이 발생할 수 있음. 해당 프로젝트 CLAUDE.md의 주의사항 확인 후 실행.
- `npm run build`는 `hanwoo-dashboard`, `knowledge-dashboard`의 표준 검증 check에 포함된다.
