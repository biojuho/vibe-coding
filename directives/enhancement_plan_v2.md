# 시스템 고도화 기획안 v2 (2026-03-11)

> **현재 상태**: 백로그 소진, 전 프로젝트 안정 운영 중
> **목표**: 운영 자동화 완성 + 콘텐츠 품질 피드백 루프 + 수익화 기반 구축

---

## Phase 0: 운영 안정성 긴급 보완 (즉시, 1일)

> 현재 운영 중 발견된 크리티컬 갭 해소

### T0-1. LLM 캐시 활성화
- **현황**: `llm_cache.db` 0바이트 (비활성 상태), 모든 LLM 호출이 full API 비용 발생
- **작업**: `execution/llm_client.py`에서 캐시 레이어 활성화 (SHA256 해시 기반, 72h TTL)
- **기대 효과**: 반복 호출 30~50% 절감 → 월 $5~10 절약
- **파일**: `execution/llm_client.py`

### T0-2. OneDrive 백업 n8n 자동화
- **현황**: 마지막 백업 3/9 (3일 전), 수동 트리거만 가능
- **작업**: n8n에 주 2회(월/목 03:00) 백업 워크플로우 추가
- **파일**: `infrastructure/n8n/workflows/backup_schedule.json`, `execution/backup_to_onedrive.py`

### T0-3. Debug History DB TTL 도입
- **현황**: `debug_history.db` 68K, 무한 증가 중
- **작업**: 90일 초과 레코드 자동 아카이브 + VACUUM
- **파일**: `execution/debug_history_db.py`

---

## Phase 1: 데이터 기반 피드백 루프 (단기, 3~5일)

> 콘텐츠 성과 → 자동 학습 → 품질 향상 순환 구조 구축

### T1-1. YouTube Analytics 자동 수집 파이프라인
- **현황**: `result_tracker_db.py` 수동 등록 방식, YouTube 통계 자동 수집 미연동
- **작업**:
  1. n8n 워크플로우: 매일 09:00 KST YouTube Data API v3 통계 수집 트리거
  2. `result_tracker_db.py`의 `collect_youtube_stats()` → n8n HTTP 호출 연동
  3. 수집 결과 → Notion 대시보드 자동 반영
- **파일**: `execution/result_tracker_db.py`, `infrastructure/n8n/workflows/yt_analytics_daily.json`

### T1-2. shorts-maker-v2 성과 피드백 루프
- **현황**: 6개 캡션 콤보 + 5개 비주얼 스타일이 job_index 순환 (성과 무관)
- **작업**:
  1. `style_tracker.py` 확장: YouTube 조회수/좋아요 데이터 → 캡션 콤보별 성과 집계
  2. Laplace-smoothed 가중 선택: 고성과 콤보 자동 우선 배치
  3. 채널별 독립 가중치 (ai_tech vs psychology 등 분리)
- **의존**: T1-1 (YouTube 통계 수집) 완료 후
- **파일**: `shorts-maker-v2/src/shorts_maker_v2/utils/style_tracker.py`, `pipeline/render_step.py`

### T1-3. blind-to-x ML 스코어러 Cold Start 해소
- **현황**: GradientBoosting 활성화에 100+ 라벨 필요, 현재 데이터 부족
- **작업**:
  1. `cost_db.py`의 `draft_analytics` 테이블에서 기존 데이터 마이그레이션
  2. Notion DB에서 과거 발행 콘텐츠 역추출 → 학습 데이터 보강
  3. 50건 이상 시 간이 모델 활성화 (LogisticRegression → 100건 이상 시 GBR 전환)
- **파일**: `blind-to-x/pipeline/ml_scorer.py`, `blind-to-x/pipeline/cost_db.py`

### T1-4. 크로스 프로젝트 성과 대시보드
- **현황**: blind-to-x, shorts-maker-v2 성과가 각각 분리 추적
- **작업**:
  1. `execution/pages/performance_overview.py` 신규: 통합 KPI 대시보드
  2. 지표: 일일 발행수, 플랫폼별 도달률, API 비용/콘텐츠당 비용, 트렌드 차트
  3. 데이터 소스: `result_tracker.db` + blind-to-x `cost_db` + shorts `cost_tracker`
- **파일**: `execution/pages/performance_overview.py` (신규)

---

## Phase 2: 파이프라인 지능화 (중기, 5~7일)

> AI 파이프라인의 자율 판단 능력 강화

### T2-1. shorts-maker-v2 토픽 사전 검증
- **현황**: TopicUnsuitableError가 전체 파이프라인 실행 후에야 발생 → 리소스 낭비
- **작업**:
  1. `pipeline/topic_validator.py` 신규: 토픽 입력 시 사전 검증 (LLM 1회 호출)
  2. 검증 항목: 시각화 가능성, 팩트 검증 가능성, 60초 포맷 적합성, 채널 적합도
  3. orchestrator.py에서 ScriptStep 전에 validator 호출
- **기대 효과**: 부적합 토픽 사전 필터 → LLM/TTS/이미지 비용 절감
- **파일**: `shorts-maker-v2/src/shorts_maker_v2/pipeline/topic_validator.py` (신규)

### T2-2. blind-to-x 스크래퍼 자가 복구
- **현황**: 셀렉터 변경 시 수동 업데이트 필요, `selector_failures.json`에 실패만 기록
- **작업**:
  1. `scrapers/base.py`에 `_auto_repair_selector()` 메서드 추가
  2. 실패 시 HTML 구조 분석 → 후보 셀렉터 3개 추출 → 검증 → 자동 적용
  3. 수리 성공 시 `config.yaml` 셀렉터 자동 업데이트 + Telegram 알림
  4. 수리 실패 시 CRITICAL 알림 → 수동 개입 요청
- **파일**: `blind-to-x/scrapers/base.py`, `execution/selector_validator.py`

### T2-3. 콘텐츠 캘린더 자동화
- **현황**: `content_calendar.py` 존재하나 수동 관리, shorts-maker-v2 토픽이 txt 파일 기반
- **작업**:
  1. Notion 콘텐츠 캘린더 DB → shorts-maker-v2 토픽 자동 공급
  2. blind-to-x 트렌드 → 캘린더 자동 제안 (승인 대기열)
  3. 채널별 주간 토픽 밸런싱 (같은 주제 반복 방지)
- **파일**: `shorts-maker-v2/src/shorts_maker_v2/utils/content_calendar.py`, `execution/topic_auto_generator.py`

### T2-4. Notion API 적응형 백오프
- **현황**: 루트 `execution/notion_client.py`에 rate limiting 미적용 (429 리스크)
- **작업**:
  1. Token bucket 패턴 도입 (3 req/sec Notion 제한 준수)
  2. 429 응답 시 지수 백오프 (1s → 2s → 4s → 8s → fail)
  3. 재시도 횟수/대기 시간 로깅
- **파일**: `execution/notion_client.py`

---

## Phase 3: 인프라 강건화 (중기, 3~5일)

> 무인 운영 안정성 보장

### T3-1. n8n 프로세스 업타임 모니터링
- **현황**: Docker 컨테이너/브릿지 서버 크래시 시 알림 없음
- **작업**:
  1. n8n에 5분 간격 self-health 워크플로우 추가
  2. 브릿지 서버에 `/health` 엔드포인트 추가 (응답 시간, 메모리, 큐 상태)
  3. 3회 연속 실패 시 Telegram CRITICAL 알림
  4. Docker restart policy 검증 (`unless-stopped` → `always` 전환 검토)
- **파일**: `infrastructure/n8n/bridge_server.py`, `infrastructure/n8n/workflows/uptime_monitor.json` (신규)

### T3-2. 통합 CI 테스트 러너
- **현황**: 프로젝트별 테스트 개별 실행, 루트 레벨 통합 CI 없음
- **작업**:
  1. `.github/workflows/full-test-matrix.yml` 신규
  2. 매트릭스: root(705) + blind-to-x(238) + shorts-maker-v2(224)
  3. 커버리지 리포트 병합 + 뱃지 생성
  4. PR 생성 시 자동 트리거
- **파일**: `.github/workflows/full-test-matrix.yml` (신규)

### T3-3. 에러 분석 자동화
- **현황**: `.tmp/failures/` 스냅샷 수집만, 분석/집계 없음
- **작업**:
  1. `execution/error_analyzer.py` 신규: 에러 패턴 자동 분류
  2. 카테고리: API 타임아웃 / 셀렉터 실패 / 비용 초과 / 인증 만료 / 네트워크
  3. 주간 에러 트렌드 리포트 → Telegram 발송
  4. 반복 에러 감지 시 자동 지침(directive) 업데이트 제안
- **파일**: `execution/error_analyzer.py` (신규)

### T3-4. 시크릿 로테이션 알림
- **현황**: API 키 만료/변경 시 수동 발견
- **작업**:
  1. `execution/health_check.py` 확장: API 키 유효성 사전 검증
  2. 키별 만료일 추적 (가능한 경우) + 7일 전 사전 알림
  3. `.env` 파일 무결성 체크 (필수 키 누락 감지)
- **파일**: `execution/health_check.py`

---

## Phase 4: 수익화 기반 구축 (장기, 5~7일)

> 콘텐츠 → 수익 연결 파이프라인

### T4-1. YouTube 채널 성장 트래커
- **현황**: 개별 영상 조회수만 추적, 채널 레벨 성장 미추적
- **작업**:
  1. `execution/channel_growth_tracker.py` 신규
  2. 지표: 구독자 증감, 총 조회수 추세, 평균 시청 시간, 구독 전환율
  3. 채널별(5채널) 독립 추적 + 비교 분석
  4. Streamlit 페이지 연동
- **파일**: `execution/channel_growth_tracker.py` (신규), `execution/pages/channel_growth.py` (신규)

### T4-2. 콘텐츠 ROI 계산기
- **현황**: API 비용 추적 존재, 수익 대비 비용 분석 없음
- **작업**:
  1. 콘텐츠당 비용 (LLM + TTS + 이미지 + 인프라) 자동 산출
  2. YouTube AdSense RPM 연동 (수동 입력 → 자동 수집)
  3. 채널별 ROI 대시보드: 비용 vs 예상 수익 vs 손익분기점
  4. 비용 효율 최적화 제안 (무료 provider 비율 조정 등)
- **파일**: `execution/pages/roi_dashboard.py` (신규)

### T4-3. 콘텐츠 시리즈화 엔진
- **현황**: 개별 토픽 1회성 생산, 시리즈 연속성 없음
- **작업**:
  1. `shorts-maker-v2/src/shorts_maker_v2/pipeline/series_engine.py` 신규
  2. 고성과 토픽 자동 감지 → 시리즈 후속편 제안 (Part 2, 3...)
  3. 시리즈 간 내러티브 연결 (이전 편 요약 인트로)
  4. 시리즈별 성과 추적 + 중단/계속 자동 판단
- **파일**: `shorts-maker-v2/src/shorts_maker_v2/pipeline/series_engine.py` (신규)

### T4-4. X(Twitter) 성과 자동 수집
- **현황**: blind-to-x가 X에 포스팅하나 성과(노출/좋아요/리포스트) 미추적
- **작업**:
  1. X API v2 Free Tier로 자체 트윗 성과 수집
  2. 발행 24h/48h/7d 시점 성과 스냅샷
  3. 토픽/시간대/스타일별 성과 분석 → ML 스코어러 피드백
- **제약**: X API Free Tier 제한 (월 1,500 읽기) → 우선순위 기반 샘플링
- **파일**: `blind-to-x/pipeline/x_analytics.py` (신규)

---

## Phase 5: 고급 최적화 & 차세대 기능 (2026-03-25~)

> Phase 0~4 완료 (2026-03-11). Phase 5는 품질 기반 강화(5A)와 차세대 기능(5B)으로 이원화.
> QC 기준선: 2362 passed, 0 failed, APPROVED (2026-03-25)

### Phase 5A: 품질 기반 강화 (즉시 실행, ~5일)

#### T5A-1. Coverage 목표 상향 (완료)
- **목표**: shorts 주요 모듈 80%+, blind-to-x commands/ 100%
- **결과 (2026-03-25)**:
  - shorts: `animations.py` 100%, `broll_overlay.py` 100%, `openai_client.py` 100%, `google_client.py` 98%, `edge_tts_client.py` 65%
  - blind-to-x: `commands/` 전체 100% (dry_run, one_off, reprocess)
  - 전체 테스트: 2224 → 2362 (+138)
- **상태**: ✅ 완료

#### T5A-2. 남은 저커버리지 모듈 보강
- **현황**: shorts `render_step.py` 28%, `edge_tts_client.py` 65% (비동기 함수 미커버)
- **작업**: render_step의 주요 분기 테스트, edge_tts 비동기 함수 모킹 테스트
- **파일**: `shorts-maker-v2/tests/unit/test_render_step.py`, `test_edge_tts_timing.py`

#### T5A-3. 지뢰밭 정리 및 문서 최신화
- **현황**: `.ai/CONTEXT.md` 지뢰밭 18건 누적, 일부는 이미 해결됨
- **작업**: 해결된 항목 아카이브, 미해결 항목만 유지, SESSION_LOG 로테이션
- **파일**: `.ai/CONTEXT.md`, `.ai/SESSION_LOG.md`

#### T5A-4. Dead Code / Legacy 정리
- **T-036 결론**: `video_renderer_backend`는 dead code가 아님 — MoviePy(합성) + FFmpeg(인코딩) 듀얼 렌더러 설계. 프로덕션 config 미노출이나 테스트에서 사용 중. → 정리 불필요
- **T-037 결론**: `tests/legacy/` (5개 파일)는 ShortsFactory 템플릿 시스템 테스트. import 호환되나 별도 모듈이므로 QC 범위 외 유지 → 현상 유지
- **상태**: ✅ 조사 완료, 조치 불필요

### Phase 5B: 차세대 기능 (탐색적, 6~12주)

#### T5B-1. 멀티 언어 Shorts 확장 (i18n)
- **현황**: 한국어 100% 하드코딩 상태에서 locale 기반 구조로 이행 중
- **진행 상태 (2026-03-25)**:
  - PoC 1차 완료: `script_step.py`의 tone/persona/CTA 금지어/system+user prompt copy를 `locales/ko-KR/script_step.yaml`로 외부화
  - PoC 2차 완료: `script_step.py`의 `persona_keywords`/review prompt copy, `edge_tts_client.py`의 alias voice/default voice를 locale 파일(`locales/ko-KR/edge_tts.yaml`)로 외부화
  - 실사용 경로 1차 완료: `locales/en-US/` locale pack(`script_step.yaml`, `edge_tts.yaml`, `captions.yaml`) 추가, `config.py` locale caption font 기본값 로딩, `whisper_aligner.py` locale→short code 정규화
  - smoke 완료: `test_i18n_en_us_smoke.py`로 실제 `en-US` config 기준 `ScriptStep -> MediaStep -> caption render` 최소 경로 확인
  - 후속 복구 완료: locale `field_names`/`channel_review_criteria`가 다시 적용되도록 `script_step.py`를 정리했고, schema alias(`narration`/`voiceover`/`visual_prompt`) 검증도 복구함
  - **남은 상위 경로 과제**: 내부 `ScenePlan` 필드는 여전히 `narration_ko`를 유지하며, `orchestrator/render assemble` 수준 상위 smoke는 아직 없음
- **i18n 분리 대상**:
  | 영역 | 파일 | 난이도 |
  |------|------|--------|
  | 프롬프트 | `script_step.py` (시스템 프롬프트 120줄+) | 높음 |
  | 톤 프리셋 | `script_step.py` (5개 톤 정의) | 중간 |
  | 채널 페르소나 | `script_step.py` (5채널 × 역할/금지/필수) | 높음 |
  | TTS 음성 매핑 | `edge_tts_client.py` (10개 매핑) | 낮음 |
  | CTA 금지어 | `script_step.py` (9개 키워드) | 낮음 |
  | 자막 폰트 | `config.py` (malgunbd.ttf 등) | 낮음 |
  | 품질 검증 규칙 | `script_step.py` (맞춤법/리뷰 섹션) | 높음 |
- **마이그레이션 경로**: `locales/<lang>/*.yaml` → `config.yaml`의 `language` 기반 로딩
- **첫 지원 언어**: en-US (확정 대기)
- **상세**: `directives/roadmap_v3.md` Phase A 참조

#### T5B-2. 숏폼 → 롱폼 자동 확장
- **현황**: 60초 Shorts만 생산
- **구상**: 고성과 Shorts 3~5편 → 10분 종합편 자동 편집
- **고려사항**: 내러티브 연결, 전환 효과, 추가 배경 설명 삽입

#### T5B-3. 커뮤니티 감성 실시간 대시보드
- **현황**: blind-to-x `sentiment_tracker.py` + `emotion_analyzer.py` 기반 존재
- **구상**: 시간대별 감성 흐름 시각화, 급상승 토픽 실시간 감지, 바이럴 예측

#### T5B-4. 자동 A/B 테스트 프레임워크
- **현황**: shorts `style_tracker.py`에 Laplace-smoothed 가중 선택 존재, blind-to-x `style_bandit.py`에 Thompson Sampling 존재
- **구상**: 동일 토픽 2개 변형 생산 → 동시 배포 → 48h 후 자동 승자 분석 → 패배 변형 비공개 처리

#### T5B-5. SaaS 전환 (Local-First)
- **상태**: ADR-013 확정 (Local-First SaaS 하이브리드)
- **상세**: `directives/roadmap_v3.md` Phase B, `directives/local_first_saas_design.md` 참조

---

## 실행 우선순위 매트릭스

| Phase | 예상 소요 | 임팩트 | 복잡도 | 의존성 |
|-------|-----------|--------|--------|--------|
| **P0** 운영 긴급 | 1일 | 높음 | 낮음 | 없음 |
| **P1** 피드백 루프 | 3~5일 | 매우 높음 | 중간 | P0 완료 |
| **P2** 파이프라인 지능화 | 5~7일 | 높음 | 높음 | P1 부분 완료 |
| **P3** 인프라 강건화 | 3~5일 | 중간 | 중간 | 독립 (P1과 병렬 가능) |
| **P4** 수익화 기반 | 5~7일 | 높음 | 중간 | P1 완료 |
| **P5A** 품질 강화 | 3~5일 | 높음 | 낮음 | P0~P4 완료 |
| **P5B** 차세대 | 탐색적 (6~12주) | 매우 높음 | 매우 높음 | P5A 완료 |

---

## 비용 영향 분석

| 항목 | 현재 | 고도화 후 |
|------|------|-----------|
| **blind-to-x 일일 비용** | ~$0.60 | ~$0.40 (캐시 + ML 최적화) |
| **shorts-maker-v2 영상당** | ~$0.10 | ~$0.07 (토픽 사전검증 + 캐시) |
| **인프라 비용** | $0 (로컬) | $0 (로컬 유지) |
| **YouTube API** | 무료 tier | 무료 tier 유지 |
| **X API** | 무료 tier | 무료 tier (1,500 reads/월) |
| **신규 API 비용** | - | +$0 (무료 tier 활용) |

---

## 성공 지표 (KPI)

| 지표 | 현재 | 목표 (P1~P3 완료 후) | 목표 (P4 완료 후) |
|------|------|---------------------|-------------------|
| 일일 콘텐츠 발행수 | ~30건/일 | 30건/일 (유지) | 30건/일 (유지) |
| 콘텐츠당 API 비용 | ~$0.02 | ~$0.013 (-35%) | ~$0.013 |
| 파이프라인 무인 가동률 | ~90% | 99%+ | 99%+ |
| 부적합 토픽 낭비율 | ~15% | ~3% | ~3% |
| YouTube 평균 조회수 | N/A | 측정 시작 | 전월 대비 +20% |
| X 평균 노출수 | N/A | 측정 시작 | 전월 대비 +15% |
| 에러 자동 복구율 | 0% | 60%+ | 80%+ |
| 백업 자동화율 | 0% | 100% | 100% |

---

## 기술 부채 정리 (P1~P3와 병행)

| 항목 | 현황 | 조치 |
|------|------|------|
| ShortsFactory 레거시 테스트 | 8 failed, 7 errors | 테스트 삭제 또는 모듈 완전 제거 |
| `gpt-4.1-mini` 모델명 | config에 잔존 | `gpt-4o-mini`로 일괄 수정 |
| notion-client 2.2.1 버그 | httpx 우회 중 | 라이브러리 업데이트 후 우회 코드 제거 |
| Vite 한국어 경로 빌드 실패 | suika-game, word-chain | 프로젝트를 ASCII 경로로 이동 또는 환경변수 우회 |
| `.tmp/` 자동 정리 | 수동 | 7일 이상 임시 파일 자동 삭제 cron |

---

*작성: Claude Code (Opus 4.6) | 2026-03-11*
*검토 대기: 사용자 승인 후 Phase 순서대로 실행*
