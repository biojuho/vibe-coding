---
description: 세션 시작 — Knowledge Base에서 이전 히스토리 확인 후 현재 상태 요약
---

# /start — 세션 시작 워크플로우

// turbo-all

## 실행 절차

1. Knowledge Base(`C:\Users\박주호\.gemini\antigravity\knowledge\`)에서 관련 KI를 확인한다.
   - 특히 `vibe_coding_workspace` KI의 overview와 maintenance 아티팩트를 읽는다.

2. 최근 대화 이력(conversation summaries)을 확인하여 마지막 세션의 작업 내용과 TODO를 파악한다.

3. 사용자에게 다음을 보고한다:
   - 마지막 세션 요약 (한줄)
   - 미완성 TODO 항목 (있으면)
   - 알려진 이슈/버그 (있으면)
   - 오늘 추천 작업 (선택)

4. 사용자가 오늘 할 작업을 말하면, `.agents/rules/project-rules.md`의 규칙을 준수하며 Implementation Plan을 세운다.
