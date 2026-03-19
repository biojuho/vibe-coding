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

