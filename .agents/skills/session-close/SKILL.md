---
name: session-close
description: "Vibe Coding 워크스페이스 세션 종료 체크리스트를 한 번에 수행한다. Use when 세션을 마무리하거나 ai-context 커밋 직전, 또는 사용자가 '마무리 / 세션 종료 / 끝내자'라고 할 때 사용한다."
---

# Session Close

Vibe Coding 워크스페이스는 여러 AI 도구(Claude Code, Codex, Gemini)가 번갈아 작업한다.
세션 종료 의식이 빠지면 `.ai/HANDOFF.md`가 비대해지고, 다음 도구가 맥락을 잃는다.
이 스킬은 루트 `CLAUDE.md`의 "세션 종료 시 반드시" 절차를 결정론적 순서로 강제한다.

## When to Use This Skill

- 작업을 마치고 세션을 종료할 때
- `[ai-context]` 커밋을 만들기 직전
- 사용자가 "마무리", "세션 종료", "끝내자", "정리하고 커밋"이라고 할 때
- 컨텍스트 압축(compaction)으로 핸드오프가 필요할 때

## 절차 (이 순서대로)

1. **`.ai/HANDOFF.md` 갱신** — 마지막 세션 테이블 한 줄(날짜·도구·요약) + "다음 할 일" + 주의사항을 추가한다.
2. **`.ai/TASKS.md` 갱신** — 완료 항목은 DONE으로, 신규 발견은 TODO로 옮기고 담당 도구를 지정한다. **새 태스크 ID는 직접 고르지 말고 `task-id` 스킬(=`next_task_id.py`)로 발급**한다.
3. **`.ai/SESSION_LOG.md`에 기록 추가** — 날짜, 도구명, 작업 요약, 변경된 파일 전체 목록.
4. **`.ai/CONTEXT.md` 업데이트** — 진행 상황이 바뀌었거나, 새 지뢰밭(반복 실수/API 제약/타이밍 이슈)을 발견했으면 "Minefield" 섹션에 추가한다.
5. **`.ai/DECISIONS.md` 기록** — 새 아키텍처 결정(ADR)이 있으면 추가한다. 기존 결정은 임의 변경 금지.
6. **로테이터 실행** — HANDOFF/TASKS/SESSION_LOG가 커졌으면 커밋 전에 정리한다. 모두 멱등이라 반복 실행해도 안전하다:

```bash
python execution/handoff_rotator.py --check --json
python execution/handoff_rotator.py        # 기본 --max-lines 200 으로 자동 트림 (7일 초과 + 200줄 초과 모두 강제)
python execution/tasks_done_rotator.py --check --json
python execution/tasks_done_rotator.py     # DONE 을 최신 5개로 유지 (--keep-count N 으로 조정)
python execution/session_log_rotator.py --check --json
python execution/session_log_rotator.py    # 권장(1000줄 초과) 시 인자 없이 재실행
```

> 주의: `handoff_rotator`는 더 이상 날짜만으로 판단하지 않는다. 자동 루프가 하루에 수십 개의 addendum을 쌓아도 `--max-lines`(기본 200)/`--keep-count`가 날짜와 무관하게 파일 크기를 잡아준다. `tasks_done_rotator`는 `## DONE (Latest N)` 섹션만 건드리고 TODO/IN_PROGRESS는 손대지 않는다.

7. **커밋** — `[ai-context]` 태그로 스테이징 후 커밋한다:

```bash
git commit -m "[ai-context] <세션 요약>"
```

8. **멀티툴 레이스 검증** — 병렬 도구의 `git add -A`가 다른 도구의 미커밋 변경을 흡수할 수 있다. 커밋 직후 확인한다:

```bash
git log -1 -- .ai/HANDOFF.md
```

## 주의

- 산문 백틱 참조 파일: `.ai/HANDOFF.md`, `.ai/TASKS.md`, `.ai/SESSION_LOG.md`, `.ai/CONTEXT.md`, `.ai/DECISIONS.md`.
- 로테이터는 멱등이다. 반복 실행해도 안전하다.
- 이 스킬은 새 스크립트를 만들지 않는다. 기존 `execution/` 도구를 제때 부르기 위한 SOP다.
