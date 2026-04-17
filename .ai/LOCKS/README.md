# .ai/LOCKS/ — AI 세션 파일 경쟁 완화 컨벤션

> 목적: 다수 AI 에이전트(Claude Code·Codex·Gemini Antigravity)가 `.ai/` 공유 문서(`HANDOFF.md`, `TASKS.md`, `SESSION_LOG.md`)를 동시 편집할 때 발생하는 경쟁 상태(race)·커밋 흡수·diff 충돌을 최소화하는 **소프트 락(advisory lock)** 체계. 강제력은 없으며, 세션별로 자발적으로 따르는 합의다.

## 동기 — 2026-04-14~15 세션 실측

| 관찰 | 빈도 | 비용 |
|---|---|---|
| 내 워킹트리 수정이 다른 세션 `[ai-context]` 커밋에 흡수됨 | 4회 | 커밋 메시지·의도 소실 |
| `package.json` 스필오버로 save→reset→edit→restore 5단계 댄스 | 1회 | 세션 시간 ~20분 |
| pre-commit 훅이 타인 수정 archive 파일을 자동 수정해서 커밋 반복 실패 | 3회 | 상호 diff 오염 |
| 타 세션 untracked WIP 파일(`__qc_negative_probe.js`)이 smoke test 오염 | 1회 | 파서·hook 재설계 유발 |

T-206 `ai_context_guard.py`는 `[ai-context]` 커밋의 파일 스코프만 지키며, 실시간 편집 동시성은 해결하지 않는다.

## 사용법 (세션 시작 시)

```bash
# 1. 현재 활성 락 확인
ls .ai/LOCKS/*.lock 2>/dev/null

# 2. 자신의 락 파일 생성
TOOL=claude-opus  # 또는 codex, gemini-antigravity
echo "pid=$$" > .ai/LOCKS/${TOOL}.lock
echo "started=$(date -Iseconds)" >> .ai/LOCKS/${TOOL}.lock
echo "branch=$(git branch --show-current)" >> .ai/LOCKS/${TOOL}.lock

# 3. 작업
```

## 사용법 (세션 종료 시)

```bash
rm -f .ai/LOCKS/${TOOL}.lock
```

## 공유 문서 편집 전 확인

`.ai/HANDOFF.md`, `.ai/TASKS.md`, `.ai/SESSION_LOG.md` 를 편집하려 할 때:

```bash
python execution/session_lock_check.py --tool claude-opus --files .ai/HANDOFF.md .ai/TASKS.md
```

스크립트는:
- 다른 활성 락이 있으면 `WARN:` 출력 후 `exit 0` (진행은 허용)
- 자기 락이 없으면 `HINT:` 출력하여 락 생성 권장
- 완전한 충돌은 막지 않음 — 어디까지나 어드바이저리

## 락 파일 포맷

```
pid=12345
started=2026-04-15T18:30:00+09:00
branch=codex/dashboard-refresh
tool=claude-opus
```

`.ai/LOCKS/*.lock` 파일은:
- `.gitignore`되지 않음 (의도적) — 브랜치 간 락 상태 공유 가능
- 세션 크래시 후에도 남을 수 있음 → 1시간 이상 오래된 락은 무시해도 OK
- 순수 정보용, 잠금 매카니즘 아님

## 권장 합의 규칙

1. **동시 편집 감지 시 나중 시작한 세션이 양보**: 다른 락이 더 오래됐으면 편집 1분 지연
2. **커밋 전 `git fetch && git log HEAD..origin/<branch>` 확인**: 원격이 앞서있으면 pull 후 재시도
3. **`[ai-context]` 커밋은 최소 단위로 스테이지**: `git add` 시 파일별로 명시, 전역 `-A` 금지
4. **크로스 세션 스필오버 방지**: 본인 작업 외 untracked/modified 파일은 건드리지 않고 `git restore --staged` 로 unstage

## 한계 (이 컨벤션이 못 하는 일)

- Git push 경쟁 (원격 충돌 시 `git pull --rebase`로 해결)
- `git stash` 꼬임 (세션별로 구분된 stash 이름 쓰는 것 권장: `git stash push -m "session:<tool>:<timestamp>"`)
- pre-commit 훅이 수정한 타인 파일 (해당 파일은 별도 커밋으로 분리)

## 향후 개선 여지

- session_lock_check.py 스크립트를 `.githooks/pre-commit` 에 선택적으로 통합
- `execution/ai_context_guard.py`와 통합하여 `[ai-context]` 커밋 시 락 체크 강제
- IDE 확장으로 락 상태를 실시간 표시
