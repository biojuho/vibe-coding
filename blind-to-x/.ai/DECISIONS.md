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
