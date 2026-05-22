# Blind-to-X 아키텍처 결정 기록

## [D-001] 3계층 아키텍처
- **일자**: 2026-03-07
- **결정**: Directive(지침) → Orchestration(AI) → Execution(Python) 분리
- **이유**: LLM의 확률적 특성을 결정론적 코드로 보완하여 신뢰성 극대화

## [D-002] 로컬 전용 정책
- **일자**: 2026-03-07
- **결정**: 모든 개발은 로컬에서만 실행. 원격 배포 금지.
- **이유**: API 키 및 개인 데이터 유출 방지

## [D-003] LLM 멀티 프로바이더 Fallback
- **일자**: 2026-03-08
- **결정**: Gemini → DeepSeek → xAI → Moonshot → ZhipuAI → OpenAI → Anthropic
- **이유**: 비용 최적화 + 가용성 보장

## [D-004] Notion httpx 우회
- **일자**: 2026-03-08
- **결정**: notion-client의 databases.query 대신 httpx 직접 호출 사용
- **이유**: notion-client v2.2.1 버그 (404/속성 누락)

## [D-005] 이미지 생성 Fallback 체인
- **일자**: 2026-03-08
- **결정**: Gemini → Pollinations → DALL-E
- **이유**: 비용 제어 (Pollinations 무료) + 안정성

## [D-006] playwright-stealth Context-level 적용
- **일자**: 2026-03-09
- **결정**: `Stealth().apply_stealth_async(context)` 방식으로 통일
- **이유**: playwright-stealth 2.0.2 권장 API, 중복 적용 경고 해소, page 자동 상속

## [D-007] A/B 위너 수동 오버라이드
- **일자**: 2026-03-09
- **결정**: Notion UI의 `A/B 위너` select 속성이 자동 판정보다 우선
- **이유**: 운영자의 도메인 지식 반영, 자동 판정의 한계 보완

## [D-008] Notion 뷰 가이드 방식 제공
- **일자**: 2026-03-09
- **결정**: API가 뷰 생성을 미지원하므로 설정 가이드 문서 + 속성 검증 스크립트 제공
- **이유**: Notion API 제약사항

## [D-009] 품질 게이트 자동 재생성 루프 (B-5)
- **일자**: 2026-03-17
- **결정**: `DraftQualityGate.should_retry=True` (error severity) 시 실패 사유를 LLM에 피드백하여 최대 2회 자동 재작성
- **이유**: LLM의 확률적 출력을 결정론적 품질 검증으로 보정. 글자 수, CTA, 한글 비율 등 규칙 위반 시 구체적 피드백과 함께 재생성하여 초안 품질 향상
- **인터페이스**: `generate_drafts(quality_feedback=[{platform, score, issues}])`

## [D-010] 크로스소스 인사이트 (opt-in)
- **일자**: 2026-03-17
- **결정**: 3+건 2+소스가 동일 topic_cluster를 공유하면 LLM으로 비교 분석 초안 자동 생성
- **이유**: 기존 멀티소스 데이터를 활용한 차별화 콘텐츠. 단순 요약이 아닌 관점 비교 인사이트
- **설정**: `cross_source_insight.enabled`, `min_posts`, `min_sources`

## [D-011] 실시간 트렌드 모니터 (opt-in)
- **일자**: 2026-03-17
- **결정**: Google Trends + Naver DataLab로 트렌딩 키워드 감지, trend_boost(0-30)로 6D 스코어 반영
- **이유**: 트렌드 시의성 반영으로 콘텐츠 적시성 향상. 무료 API로 비용 부담 없음
- **설정**: `trends.enabled`, `spike_threshold: 80.0`, `cache_ttl_minutes: 10`

## [D-021] Crawl4AI LLM 추출 폴백
- **일자**: 2026-03-20
- **결정**: CSS 셀렉터 전부 실패 시 Crawl4AI LLM 추출을 최종 폴백으로 사용
- **이유**: 사이트 레이아웃 변경에 대한 근본적 내성. Gemini Flash(무료)로 비용 $0
- **폴백 체인**: CSS 셀렉터 → 자동 수리 → trafilatura → Crawl4AI LLM
- **설정**: `crawl4ai.provider`, `crawl4ai.timeout_seconds`

## [D-022] AI 바이럴 필터 (P2.7)
- **일자**: 2026-03-20
- **결정**: 드래프트 생성 전 Gemini Flash로 5차원 바이럴 잠재력 스코어링, threshold 미만 자동 필터링
- **이유**: 노이즈 글에 대한 LLM 드래프트 비용 절감. 10초 타임아웃 + 실패 시 permissive default
- **설정**: `viral_filter.enabled`, `viral_filter.threshold: 40.0`

## [D-023] 감성 분석 트래커
- **일자**: 2026-03-20
- **결정**: 10개 감정 카테고리 × 90+ 한국어 키워드로 감정 신호 SQLite 영속, 시간 윈도우 vs 베이스라인 spike 감지
- **이유**: "지금 뜨는 감정" 실시간 감지 → 콘텐츠 전략 데이터 제공
- **설정**: `sentiment.enabled`, `sentiment.retention_days: 30`

## [D-024] 일일 다이제스트 자동 발송
- **일자**: 2026-03-20
- **결정**: RSSbrew 스타일 일일 다이제스트 — Notion 집계 → Gemini AI 요약 → Telegram 발송
- **이유**: 수집 결과를 자동 정리하여 운영자에게 일일 브리핑 제공
- **설정**: `digest.enabled`, `digest.max_entries: 10`, `digest.telegram_enabled`

## [D-025] Gemini API 호출 패턴: genai.Client() 인스턴스
- **일자**: 2026-03-20
- **결정**: `genai.configure()` (글로벌 상태) 대신 `genai.Client(api_key=)` 인스턴스 패턴 사용
- **이유**: 동시 실행 시 API 키 경합 방지. QC에서 발견된 thread safety 이슈

## [D-026] Editorial Reviewer Multi-Provider Fallback
- **일자**: 2026-03-20
- **결정**: editorial_reviewer.py에 Gemini/DeepSeek/xAI 3-provider fallback 적용. config.yaml의 `llm.providers` 순서를 존중하되, 지원 provider만 필터
- **이유**: Gemini 무료 쿼타 소진 시 editorial review 전체 스킵되는 문제. 별도 유료 플랜 전환 불필요

## [D-027] kiwipiepy Non-ASCII 경로: shutil.copytree 재귀 복사
- **일자**: 2026-03-20
- **결정**: 모델 디렉토리를 `shutil.copytree`로 재귀 복사 (기존 `os.listdir` + `copy2`는 하위 디렉토리 누락)
- **이유**: `extract.mdl` 등이 하위 디렉토리에 있을 수 있어 평면 복사로는 불충분

## [D-028] X 큐레이션/초안 품질 리디자인
- **일자**: 2026-03-26
- **결정**: 후보 선정은 engagement 단독이 아니라 `pre_editorial_score`(독자 욕구 30 / 공감·웃음 25 / 파생각 20 / 구체성 15 / 직장인 적합성 10)로 1차 필터링하고, 드래프트 생성은 X 편집 브리프(`selection_summary`, `emotion_lane`, `empathy_anchor`, `spinoff_angle`)를 필수 입력으로 사용한다.
- **이유**: 좋아요가 높아도 추상적이고 파생각 없는 글이 X 초안 품질을 무너뜨렸다. 직장인 공감층이 왜 반응할지를 먼저 보장해야 한다.
- **추가 계약**:
  - `draft_generator.py`는 `<twitter>`, `<reply>`, `<creator_take>` 태그 누락, 429/SDK 에러문, 낮은 한글 비율 응답을 성공 초안으로 인정하지 않는다.
  - `process.py`는 모든 provider가 실패하면 Notion 업로드 전에 `DRAFT_GENERATION_FAILED`로 종료한다.
  - few-shot 예시는 `성과 기반 -> 최근 승인됨 -> YAML golden_examples` 순으로 폴백한다.

## [D-029] 제목전용 사전 스크리닝 분리
- **일자**: 2026-03-29
- **결정**: `feed_collector.py`는 `hard_reject`를 무시하고 `min_pre_editorial_score`(기본 35)만으로 사전 필터링. 본문 포함 전체 editorial 검증(`min_editorial_score` 60)은 scrape 후 `process.py`에서 수행.
- **이유**: D-028 리디자인 이후 `hard_reject`의 specificity/spinoff/workplace_fit 임계값이 제목만으로는 충족 불가하여 3/26부터 100% 차단이 발생. 제목전용 단계에서는 낮은 bar로 통과시키고 본문 확보 후 엄격 필터링하는 2단계 구조가 적합.

## [D-030] FMKorea/JobPlanet get_feed_candidates 구현
- **일자**: 2026-03-29
- **결정**: base의 URL-only `get_feed_candidates()`를 FMKorea(셀렉터 제목 추출)와 JobPlanet(JSON API 제목/좋아요/댓글/조회수 추출)에서 오버라이드. FMKorea는 실패 시 URL-only fallback 포함.
- **이유**: base 구현은 `title=""`을 반환하여 editorial scoring이 항상 최저점. Blind/Ppomppu는 이미 구현 완료였으나 FMKorea/JobPlanet이 누락.

## [D-031] Split rule files + shared loader
- **일자**: 2026-03-29
- **결정**: 규칙 소스 오브 트루스를 단일 `classification_rules.yaml`에서 `rules/classification.yaml`, `rules/examples.yaml`, `rules/prompts.yaml`, `rules/platforms.yaml`, `rules/editorial.yaml`로 분리하고, 런타임은 `pipeline/rules_loader.py`를 통해만 로드한다. 루트 `classification_rules.yaml`은 마이그레이션 동안 호환 스냅샷/폴백으로 유지한다.
- **이유**: taxonomy, prompt, editorial policy, platform regulation이 한 파일에 섞여 있으면 책임이 너무 크고, 작은 수정이 다른 레이어에 예상치 않게 영향을 줄 수 있다. shared loader를 두면 runtime 호환성을 유지하면서도 점진적으로 분리할 수 있다.

## [D-032] 본문 포함 편집 적합도 게이트 (선별 정확도)
- **일자**: 2026-05-22
- **결정**: 스크레이프 후 `filter_profile_stage._check_editorial_fit`가 본문까지 포함한 `evaluate_candidate_editorial_fit`를 실행하여 `hard_reject`(추상적·파생각 부족·직장인 맥락 약함·갈등 낚시 과다) 또는 편집 적합도 점수 < `feed_filter.min_editorial_score`(기본 60)인 후보를 검토 큐 적재 전에 차단한다. `feed_filter.editorial_gate_enabled`(기본 true)로 토글, `daily_queue_floor` 활성 시에는 다른 필터와 동일하게 override 한다.
- **배경**: D-029는 "본문 포함 전체 editorial 검증(min_editorial_score 60)은 scrape 후 process.py에서 수행"한다고 명시했고 `config.yaml`에도 `min_editorial_score` 키가 있었지만, 실제 코드 경로는 한 번도 구현되지 않았다. `hard_reject` 신호는 계산만 되고 스크레이프 이후 전 구간에서 폐기되고 있었다.
- **이유**: `final_rank_score`는 `scrape_quality*0.35 + publishability*0.40 + performance*0.25` 가중합이라, 스크랩 품질·성과 휴리스틱이 높으면 편집 적합도가 낮은(추상적이고 파생각 없는) 글도 60 임계값을 넘겨 검토 큐에 적재됐다. 편집 적합도를 독립 축으로 강제해 선별 정확도를 높인다. 게이트는 LLM 바이럴 필터보다 먼저 실행되어 편집 약한 글에 대한 LLM 호출 비용도 절감한다.
- **에러 코드**: `FILTERED_EDITORIAL`. 실패 사유는 `editorial_hard_reject` / `editorial_score_below_threshold`로 구분 기록. 진단용 `editorial_fit`은 통과·비활성 여부와 무관하게 `post_data`에 보존된다.

## [D-033] 스크레이프 콘텐츠 무결성 게이트 (수집 정확도)
- **일자**: 2026-05-22
- **결정**: `fetch_stage._check_scrape_integrity`가 `pipeline/scrape_integrity.py`의 결정론적 분류기로, 추출된 title/content가 실제 게시물이 아니라 로그인 월·삭제/없는 글·봇 차단/캡차 페이지인 경우를 감지해 수집 실패로 분류한다. `scrape_quality.integrity_check_enabled`(기본 true)로 토글, `scrape_quality.min_article_chars`(기본 220)로 임계 조정.
- **배경**: Blind처럼 콘텐츠를 로그인 뒤로 가두는 사이트는 세션 쿠키 만료 시 로그인 월 HTML을 그대로 반환한다. 스크래퍼는 이를 '성공'으로 보고 한국어 텍스트를 추출하며, 그 텍스트는 한국어 비율·길이 검사(`assess_quality`)를 통과해 검토 큐를 오염시킨다.
- **이유**: `evaluate_candidate_editorial_fit`·`assess_quality`는 '진짜 게시물'의 품질을 보지만, 추출한 것이 애초에 게시물이 맞는지는 아무도 검증하지 않았다. 이를 명시적 레이어로 분리해 수집 정확도를 높인다.
- **시그니처 2계층**: 하드(봇 차단·캡차 — 정상 글에 사실상 없음, 길이 무관 차단) / 소프트(로그인·삭제 — 정상 글이 인용 가능, 본문 < `min_article_chars`일 때만 차단). 본문 길이 가드로 거짓 양성을 억제한다.
- **분류**: `blocked` → `SCRAPE_FAILED`, `non_article` → `SCRAPE_PARSE_FAILED`. 실패 사유 `scrape_blocked_page` / `scrape_login_wall` / `scrape_deleted_post`로 구분 기록되어 실패 분석에 잡힌다.
