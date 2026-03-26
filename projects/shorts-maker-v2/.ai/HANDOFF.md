# HANDOFF.md

## 마지막 세션 요약 (2026-03-26 / Antigravity)
- **작업 내용**: shorts-maker-v2 파이프라인에 자동 주제 발굴(`TrendDiscoveryStep`)과 제목 생성(`TopicAngleGenerator`) 로직 추가
- **테스트 결과**: 1107 passed, 0 failed. 커버리지 76.34%.
- **특이사항**: `TopicAngleGenerator` 내 시스템 프롬프트에서 JSON 템플릿에 `str.format` 사용 시 중괄호 이스케이프가 필요했음을 확인하고 반영함. `--auto-topic`과 `--resume` 명령어의 동시 실행 제한.

## 다음 할 일
1. 트렌드 수집(RSS, Google Trends) 안정성 추가 모니터링
2. 커버리지 80% 상향을 위한 엣지 케이스 테스트 보강
3. `tests/legacy/` 디렉토리 내 옛날 테스트들 호환성 점검/정리

## 주의 사항
- LLM 프롬프트 템플릿 내에 JSON 형식이 들어갈 때는 이중 중괄호 `{{`, `}}`를 사용해야 `str.format()` 사용 시 KeyError를 방지할 수 있습니다.
- CLI 변경 시, `tests/unit/test_cli.py`에서 테스트하는 에러 메시지와 정확히 일치해야 합니다.
