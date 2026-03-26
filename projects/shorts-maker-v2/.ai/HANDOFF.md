# HANDOFF.md

## 마지막 세션 요약 (2026-03-27 / Antigravity)

- **작업 내용**: shorts-maker-v2 커버리지 향상을 위해 `karaoke.py` 모듈 유닛 테스트 보강(97% 커버리지 달성). TDD 관점의 폰트 스케일링, 청킹 로직 테스트 작성(`test_karaoke_chunking.py` 신규).
- **테스트 결과**: `test_karaoke_render.py` 내 Windows PermissionError 및 폰트 목업 오류 해결 완료.
- **특이사항**: 전체 커버리지 향상을 막고 있던 레거시(`tests/legacy/`) 테스트들에 대해 삭제/격리를 결정함.

## 다음 할 일

1. V2 핵심 파이프라인 모듈(`render_step.py`, `script_step.py`, `orchestrator.py` 등) 유닛 테스트 우선 작성
2. `pyproject.toml`에 지정된 `fail-under=45%`를 충족하기 위해 전역 커버리지 확대
3. `tests/legacy/` 디렉토리 제거 확정 및 삭제

## 주의 사항

- 렌더링이나 폰트 처리 등을 테스트할 때 실제 환경(Windows vs Linux)에 따른 파일 I/O 에러나 폰트 경로 에러가 자주 발생하므로 가급적 `unittest.mock`을 적극 활용할 것.
- 레거시 테스트는 V1(ShortsFactory) 코드베이스에 의존하고 있어 V2 파이프라인 커버리지에 기여하지 못함.
