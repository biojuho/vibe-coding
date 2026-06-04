---
name: task-id
description: "충돌 없는 T-#### 태스크 ID를 결정론적으로 할당한다. Use when TASKS 보드나 커밋 메시지에 새 태스크 ID가 필요할 때 사용한다. 스냅샷 max+1 수기 선택은 금지한다."
---

# Task ID Allocation

여러 AI 도구가 `.ai/TASKS.md`를 동시에 편집하면서 같은 `T-####`가 두 번 쓰이는
충돌이 반복 발생했다(T-1107×2, T-1108×2, T-1195×2, T-1199×2 — `git log`에서 확인 가능).
각 도구가 자기 스냅샷의 `max(T-####)+1`을 독립적으로 고르기 때문이다.
이 스킬은 충돌 없는 ID를 결정론적으로 발급하게 강제한다.

## When to Use This Skill

- 새 태스크를 만들어 `.ai/TASKS.md`에 추가할 때
- 커밋 메시지 / 브랜치 / HANDOFF에 새 `T-####`를 적기 직전
- 여러 태스크를 한꺼번에 등록할 때 (각 ID를 순서대로 발급)

## 절차

1. **항상 스크립트 출력을 사용한다.** 자기 스냅샷의 `max+1`을 손으로 고르지 않는다:

```bash
py -3 execution/next_task_id.py
# -> T-1209

# 자동화용
py -3 execution/next_task_id.py --json
```

2. **왜 신뢰할 수 있나** — 이 스크립트는 `.ai/TASKS.md` + `.ai/HANDOFF.md` + 최근 30개 git commit(subject+body) 세 곳을 모두 스캔해 `T-####` 합집합의 최대값 다음부터 충돌 없는 첫 ID를 제안한다. 다른 도구가 커밋엔 썼지만 TASKS.md엔 아직 없는 ID도 git log에서 잡혀, race window가 "수 분"에서 "수 초"로 좁아진다.

3. **커밋 직전 재실행** — 발급과 커밋 사이 시간이 벌어졌으면 커밋 직전 다시 실행해 그사이 다른 도구가 쓴 ID를 흡수한다.

4. **동시 충돌 폴백** — 그래도 1초 이내 동시 충돌이 나면, *나중에 커밋하는* 도구가 ID 뒤에 알파벳 접미사를 붙이고(`T-1209b`) 커밋 본문에 충돌을 명시한다. 변경 이력 보존을 위해 **과거 커밋의 ID는 절대 다시 쓰지 않는다.**

## 주의

- 근거와 정책 전문은 `.ai/CONTEXT.md`의 "Multi-Tool Coordination — Task ID Allocation" 절에 있다.
- 산문 백틱 참조 파일: `execution/next_task_id.py`, `.ai/TASKS.md`, `.ai/HANDOFF.md`, `.ai/CONTEXT.md`.
