# HANDOFF.md — Blind-to-X AI 릴레이 메모

## 마지막 세션 (2026-05-22 | Claude Code)

| 항목 | 내용 |
|---|---|
| 작업 | 수집·선별 정확도 고도화 — 편집 적합도 게이트 (D-032) + 스크레이프 무결성 게이트 (D-033) |
| 상태 | ✅ 완료 |
| 테스트 | 유닛 테스트 전건 통과, ruff clean |

### D-033 — 스크레이프 콘텐츠 무결성 게이트 (수집 정확도)

문제: Blind처럼 콘텐츠를 로그인 뒤로 가두는 사이트는 세션 쿠키 만료 시 로그인 월 HTML을
반환한다. 스크래퍼는 이를 '성공'으로 보고 한국어 텍스트를 추출하고, 그 텍스트는
`assess_quality`(한국어 비율·길이)를 통과해 검토 큐를 오염시킨다. 추출한 것이 게시물이
맞는지 검증하는 레이어가 없었다.

해결:
- `pipeline/scrape_integrity.py` 신규 — 하드(봇 차단·캡차, 길이 무관)/소프트(로그인·삭제,
  본문 짧을 때만) 2계층 시그니처로 비-게시물을 결정론 분류.
- `fetch_stage._check_scrape_integrity()` — `assess_quality` 직전에 실행. 모든 소스 공통
  chokepoint. `blocked`→`SCRAPE_FAILED`, `non_article`→`SCRAPE_PARSE_FAILED`.
- 설정: `scrape_quality.integrity_check_enabled`(기본 true), `min_article_chars`(기본 220).
- 테스트: `test_scrape_integrity.py` 14개 + `TestFetchStage` 통합 3개.

### D-032 — 본문 포함 편집 적합도 게이트 (선별 정확도)

### 배경 — 발견한 결함

D-029는 "본문 포함 전체 editorial 검증(`min_editorial_score` 60)은 scrape 후 `process.py`에서
수행"한다고 명시했고 `config.yaml`에도 `feed_filter.min_editorial_score` 키가 주석과 함께
존재했다. 그러나 **실제 코드 경로는 한 번도 구현되지 않았다.** `hard_reject` 신호는 계산만
되고 스크레이프 이후 전 구간에서 폐기되고 있었다.

결과: `final_rank_score = scrape_quality*0.35 + publishability*0.40 + performance*0.25` 가중합
때문에, 스크랩 품질·성과 휴리스틱이 높으면 편집 적합도가 낮은(추상적·파생각 없는) 글도
60 임계값을 넘겨 검토 큐에 적재됐다. → 선별 정확도 누수.

### 완료된 변경

- `pipeline/process_stages/filter_profile_stage.py`: `_check_editorial_fit()` 신규 추가.
  `_build_profile_and_decision` 뒤·`_check_viral_and_calendar`(LLM) 앞에 배치.
  `hard_reject` 또는 점수 < `min_editorial_score`면 `FILTERED_EDITORIAL`로 차단.
  `daily_queue_floor` 활성 시 override. 진단용 `editorial_fit`을 `post_data`에 보존.
- `config.py` / `blind_scraper.py`: `ERROR_FILTERED_EDITORIAL` 에러 코드 추가/재노출.
- `config.yaml` / `config.example.yaml` / `config.ci.yaml`: `feed_filter.editorial_gate_enabled: true`
  추가, `min_editorial_score` 주석 정정(`process.py` → `filter_profile_stage`).
- `tests/unit/test_process_stages.py`: `TestEditorialGate` 7개 테스트 추가, `_ctx_with_content`
  픽스처 본문을 현실화.
- `tests/unit/test_cost_controls.py` / `test_pipeline_flow.py`: 파이프라인 e2e 스텁 본문을
  편집 게이트를 통과하는 현실적인 글로 교체.
- `.ai/DECISIONS.md` D-032, `.ai/CONTEXT.md` 지뢰밭 #13/#17 갱신.

### 주의사항

- `_check_editorial_fit`이 기본 활성이다. 파이프라인 전체를 도는 신규 테스트의 스텁 본문은
  숫자·인용·장면·직장 맥락이 있어야 게이트를 통과한다. 추상적 본문은 `editorial_hard_reject`.
- `feed_filter` 키는 `config.example.yaml`/`config.ci.yaml`과 동기화 유지
  (`test_config_workflow_sync.py`가 keyset 검증).
- 게이트는 active staged `process_single_post()`에만 적용된다. `_process_single_post_legacy()`는
  미적용 — 레거시 제거 시 함께 정리.

### 다음 AI에게

- 선별 정확도 후속 작업 후보: 운영 데이터 누적 후 `min_editorial_score` 임계값 튜닝,
  Notion 검토 카드에 `editorial_fit` 진단(점수·차원·하드리젝 사유) 노출.
- 게이트 차단율이 너무 높으면 `feed_filter.min_editorial_score`를 낮추거나
  `editorial_gate_enabled: false`로 임시 비활성 가능.
