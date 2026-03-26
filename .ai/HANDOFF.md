# HANDOFF - AI 컨텍스트 릴레이 메모

> 이 파일은 50줄 이내로 유지합니다. 상세 작업 이력은 `SESSION_LOG.md`, 확정 결정은 `DECISIONS.md`를 확인합니다.

## 마지막 세션

| 항목 | 내용 |
|------|------|
| 날짜 | 2026-03-26 |
| 도구 | Codex |
| 작업 | T-052 완료: 루트 구조를 `workspace/` + `projects/` 기준으로 재편하고 경로 계약/문서/QAQC 허브를 새 레이아웃에 맞게 정리 |

## 현재 상태

- Canonical layout is now active: root control plane + `workspace/` + `projects/` + `infrastructure/`.
- Root-owned folders moved to `workspace/`: `directives/`, `execution/`, `scripts/`, `tests/`.
- Product folders moved to `projects/`: `blind-to-x`, `shorts-maker-v2`, `hanwoo-dashboard`, `knowledge-dashboard`, `suika-game-v2`, `word-chain`.
- Shared path resolver lives in `workspace/path_contract.py`; repo automation accepts both legacy root project paths and canonical `projects/<name>` during transition.
- `workspace/scripts/smoke_check.py`, `workspace/scripts/doctor.py`, `workspace/execution/qaqc_runner.py`, `workspace/execution/joolife_hub.py` all run against the new layout.

## 다음 우선순위

1. T-053: 다른 프로세스가 점유 중인 빈 루트 `shorts-maker-v2/` 잔여 디렉터리 정리
2. T-049: `thumbnail_step.py` Pillow deprecation warning 정리
3. T-050: `projects/shorts-maker-v2` 기준 full QC 재실행 및 기준값 갱신 필요 여부 확인

## 주의사항

- 현재 `git status`의 대량 삭제는 실제 삭제가 아니라 `workspace/`와 `projects/`로 이동된 구조 변경이다.
- 루트 `shorts-maker-v2/`는 비어 있지만 다른 프로세스가 잡고 있어 이동/삭제가 실패했다. 내용은 이미 `projects/shorts-maker-v2/`에 있다.
- 역사성 문서(`SESSION_LOG.md`)에는 과거 루트 경로 표기가 남아 있을 수 있다. 새 문서와 새 명령은 canonical 경로만 사용한다.
