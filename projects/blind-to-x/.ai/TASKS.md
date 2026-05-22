# 칸반 보드

## DONE (이번 세션)
- 선별 정확도 게이트 (D-032): 본문 포함 편집 적합도 게이트 `_check_editorial_fit` 구현
  - D-029가 명시했으나 미구현이던 `min_editorial_score`/`hard_reject` 후처리 검증을 실제로 강제
  - `FILTERED_EDITORIAL` 에러 코드 추가, `feed_filter.editorial_gate_enabled` 토글 추가
  - `TestEditorialGate` 7개 테스트 추가 + 파이프라인 e2e 픽스처 현실화
- 수집 정확도 게이트 (D-033): 스크레이프 무결성 분류기 구현
  - `pipeline/scrape_integrity.py` + `fetch_stage._check_scrape_integrity` — 로그인 월·삭제 글·봇 차단 페이지를 수집 실패로 분류
  - `scrape_quality.integrity_check_enabled` / `min_article_chars` 설정 추가
  - `test_scrape_integrity.py` 14개 + `TestFetchStage` 3개 테스트 추가

## IN_PROGRESS
- 없음

## TODO
- `_process_single_post_legacy()` 제거 (D-032 게이트는 active staged 경로에만 적용됨)
- stage helper 파일 분리, 레거시 `classification_rules.yaml` 소비 경로 정리
- 선별 정확도 후속: 운영 데이터 누적 후 `min_editorial_score` 임계값 튜닝, Notion 카드에 `editorial_fit` 진단 노출 검토
