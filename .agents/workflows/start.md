---
description: 세션 시작 — Knowledge Base에서 이전 히스토리 확인 후 현재 상태 요약
---

# /start — 세션 시작 워크플로우

// turbo-all

## 실행 절차

1. Knowledge Base(`C:\Users\박주호\.gemini\antigravity\knowledge\`)에서 관련 KI를 확인한다.
   - 특히 `vibe_coding_workspace` KI의 overview와 maintenance 아티팩트를 읽는다.

2. 최근 대화 이력(conversation summaries)을 확인하여 마지막 세션의 작업 내용과 TODO를 파악한다.

3. **[Explore 단계]** 오늘 작업할 프로젝트가 있다면:
   - 해당 프로젝트의 `projects/<name>/CLAUDE.md`를 읽는다 (프로젝트별 지침, 지뢰밭 확인).
   - `.ai/HANDOFF.md`를 읽어 이전 AI 도구의 릴레이 메모를 파악한다.
   - `.ai/TASKS.md`에서 IN_PROGRESS 항목을 확인한다.
   - **조사 없이 코드 수정 금지** — Explore 완료 후 Plan 단계로 진입.

4. 사용자에게 다음을 보고한다:
   - 마지막 세션 요약 (한줄)
   - 미완성 TODO 항목 (있으면)
   - 알려진 이슈/버그 (있으면)
   - 오늘 추천 작업 (선택)

5. 사용자가 오늘 할 작업을 말하면, `Explore → Plan → Code → Verify` 4단계 워크플로우로 진행한다.
   - **Plan**: Implementation Plan 작성 후 사용자 승인 대기
   - **Code**: 계획 실행, 테스트 함께 작성
   - **Verify**: 해당 프로젝트 `CLAUDE.md`의 "검증 커맨드" 실행

