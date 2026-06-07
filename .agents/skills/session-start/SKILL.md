---
name: session-start
description: "세션 시작 시 멀티툴 동시작업 현황을 오리엔트한다. Use when Vibe Coding 워크스페이스에서 작업을 시작하고 편집하기 전에 다른 도구가 무엇을 했는지 파악이 필요할 때 사용한다."
---

# Session Start Orientation

여러 AI 도구가 병렬로 같은 repo를 편집하기 때문에 "방금 누가 뭘 했는지"가 모호하다.
이 스킬은 편집을 시작하기 전에 현황을 한 번에 파악하는 결정론적 절차다.

## When to Use This Skill

- 새 세션을 시작해 처음 작업에 들어갈 때
- 다른 도구가 동시에/직전에 편집했을 가능성이 있을 때
- 컨텍스트 압축 후 작업을 이어받을 때

## 절차

1. **스냅샷 확보** — git 브랜치/ahead-behind/워킹트리, 오픈 PR, HANDOFF 드리프트, TASKS 카운트를 한 화면에 본다:

```bash
python execution/session_orient.py
python execution/session_orient.py --json   # 자동화용
```

2. **`.ai/` 필독 (이 순서대로)**:
   - `.ai/HANDOFF.md` — 이전 도구의 릴레이 메모 (가장 먼저)
   - `.ai/TASKS.md` — 칸반 보드 (TODO / IN_PROGRESS / DONE)
   - `.ai/PROJECTS.md` — 프로젝트별 상태, 현재 초점, 출력 품질 기준
   - `.ai/CONTEXT.md` — 구조·스택·컨벤션·지뢰밭
   - `.ai/DECISIONS.md` — 확정된 아키텍처 결정 (임의 변경 금지)
   - `.ai/TOOL_MATRIX.md` — 도구별 역량 매트릭스

3. **체크포인트** — IN_PROGRESS 태스크, 프로젝트별 현재 초점, 관련 지뢰밭, 로테이션 권장 플래그(`session_orient.py`가 보고)를 확인한 뒤 작업을 시작한다. 세션 종료 시에는 `session-close` 스킬을 쓴다.

## 주의

- 산문 백틱 참조 파일: `execution/session_orient.py`, `.ai/HANDOFF.md`, `.ai/TASKS.md`, `.ai/PROJECTS.md`, `.ai/CONTEXT.md`, `.ai/DECISIONS.md`, `.ai/TOOL_MATRIX.md`.
- 각 섹션은 독립이라 `gh` 미설치·그래프 미빌드 같은 부분 실패는 해당 섹션만 unavailable로 표시된다.
