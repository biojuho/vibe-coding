# HANDOFF.md

## 마지막 세션 요약 (2026-03-26 / Antigravity)

- **작업 내용**: shorts-maker-v2 파이프라인 Phase 2(Trend Discovery) 모듈 작성, CLI `--auto-topic` 플래그 통합 완료. 유닛 테스트 잔류 오류(UnboundLocalError, Caption Combo 튜플 수정) 해결.
- **테스트 결과**: Ruff 린팅 오류 자동 수정(6건), 유닛 테스트 전체 통과 확인. `SESSION_LOG.md`에 내역 기록.
- **특이사항**: `_CAPTION_COMBOS`가 (hook, body, cta, closing) 4개 요소로 변경되었습니다. 템플릿 프롬프트 내 JSON 포맷 사용 시 중괄호 이스케이핑(`{{`, `}}`)에 유의해야 합니다.

## 다음 할 일

1. 운영 환경에서 트렌드 수집(RSS, Google Trends) API 응답 패턴 모니터링
2. 커버리지 80% 상향을 위한 엣지 케이스 추가 테스트 작성
3. `tests/legacy/` 디렉토리 내 옛날 테스트들 호환성 점검/정리 (테스트 실행 시간 최적화 필요)

## 주의 사항

- LLM 프롬프트 템플릿 내에 JSON 형식이 들어갈 때는 이중 중괄호 `{{`, `}}`를 사용해야 `str.format()` 사용 시 KeyError를 방지할 수 있습니다.
- CLI 변경 시, `tests/unit/test_cli.py`에서 테스트하는 에러 메시지와 정확히 일치해야 합니다.
- 렌더링 관련 유닛 테스트(`render_step`)는 `MoviePy` 기반이므로 `mock` 처리를 주의하여 작성하세요.
