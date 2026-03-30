# blind-to-x Project Brief

## 한 줄 설명

`blind-to-x`는 Blind와 직장인 커뮤니티 글을 수집해, 사람이 검토한 뒤 X(Twitter) 중심의 발행 초안으로 전환하는 한국어 콘텐츠 파이프라인입니다.

## 현재 운영 모델

- 기본 운영은 `자동 수집 + 사람 검토 + 수동 발행`입니다.
- 자동 X 발행 경로는 존재하지만 기본 정책은 사람이 마지막 판단을 하도록 두는 쪽입니다.
- 현재 핵심 채널은 X이고, 구조상 `newsletter`, `threads`, `naver_blog`까지 확장 가능한 형태를 일부 갖고 있습니다.

## 핵심 목적

- 직장인/커뮤니티 원문에서 반응 가능성이 높은 주제를 빠르게 선별한다.
- 너무 AI 같거나 클리셰적인 문장을 줄이고, 바로 게시 가능한 한국어 초안을 만든다.
- Notion 기반 human-in-the-loop 큐를 유지하면서 발행 품질을 관리한다.

## 핵심 흐름

```text
Feed Collection
-> Scraper
-> Duplicate / Quality Filter
-> Deterministic Content Profile
-> Review Queue Decision
-> LLM Draft Generation
-> Editorial Review / Rewrite
-> Draft Quality Gate / Retry
-> Image / Screenshot Upload
-> Notion Upload
-> Human Review
-> Optional Manual / Auto Publish
```

## 주요 파일과 책임

- `main.py`
  - CLI 진입점과 런 전체 오케스트레이션
- `pipeline/process.py`
  - 개별 포스트 처리의 중심 오케스트레이터
- `pipeline/feed_collector.py`
  - 입력 소스별 수집 후보 정리
- `pipeline/content_intelligence.py`
  - 결정론적 분류/점수화와 콘텐츠 프로파일 생성
- `pipeline/review_queue.py`
  - Notion 검토 큐로 보낼지 결정
- `pipeline/draft_generator.py`
  - LLM 초안 생성과 multi-provider fallback
- `pipeline/editorial_reviewer.py`
  - LLM 기반 에디토리얼 점수 평가와 리라이트
- `pipeline/draft_quality_gate.py`
  - 플랫폼별 최소 품질 기준 검증
- `pipeline/draft_validator.py`
  - 품질 게이트 실패 시 재시도 프롬프트 구성
- `pipeline/notion/_upload.py`
  - Notion 스키마/업로드 책임
- `classification_rules.yaml`
  - 분류 규칙, 브랜드 보이스, 골든 예시, 안티 예시, 플랫폼별 편집 규칙의 중심 규칙 파일

## 구조적으로 흥미로운 지점

- 결정론적 규칙과 LLM 기반 판단이 함께 섞여 있습니다.
- `classification_rules.yaml` 한 파일에 토픽/감정 분류, 골든 예시, 금지 표현, 브랜드 보이스, 플랫폼별 전략이 함께 들어 있습니다.
- `process.py`가 매우 많은 단계의 조립을 담당하고 있습니다.
- human review를 전제로 하되, 비용/품질/속도 사이에서 자동화를 계속 늘려온 구조입니다.

## 콘텐츠 품질 시스템

- 토픽/감정/오디언스 적합도 분류
- 반응 가능성 점수와 편집 적합도 계산
- 브랜드 보이스와 금지 표현 규칙
- 골든 예시 / 안티 예시 / 토픽별 프롬프트 전략
- 초안 후처리용 editorial reviewer
- 플랫폼별 품질 게이트와 재시도 루프
- 사람이 최종 승인하는 Notion 큐

## 외부 LLM에게 특히 보고 싶은 질문

1. 현재 모듈 경계가 유지보수 가능한가?
2. `process.py`와 `classification_rules.yaml`의 책임이 과도하게 집중되어 있는가?
3. 결정론적 규칙과 LLM 판단의 역할 분리가 적절한가?
4. 현재 프롬프트/골든 예시 체계가 실제 품질을 높이는 구조인가, 아니면 과적합/경직성을 만드는가?
5. 사람이 검토해야 하는 부담을 줄이면서도 품질을 유지하려면 어느 레이어를 먼저 정리해야 하는가?

## 현재 강점

- human-in-the-loop 운영 모델이 명확함
- 다중 provider fallback과 fail-closed 성향이 있음
- 품질 게이트가 초안 후단에도 존재함
- 분류와 점수화 일부가 결정론적이라 재현성이 있음
- 테스트 자산이 비교적 많음

## 현재 의심하는 리스크

이 항목들은 확정 결론이 아니라 외부 리뷰에서 검증받고 싶은 가설입니다.

- 하나의 큰 오케스트레이터에 책임이 몰려 있음
- 규칙 파일이 커지면서 설계 경계가 흐려졌을 가능성
- 품질 게이트, editorial review, prompt strategy가 서로 겹치는 부분이 있을 가능성
- 좋은 문장을 만들기 위한 규칙이 많아질수록 오히려 결과가 경직될 가능성
- 테스트가 많더라도 콘텐츠의 질적 일관성은 별도 검증 체계가 더 필요할 가능성

## 최신 검증 메모

- `.ai/CONTEXT.md` 기준 2026-03-28 공유 QC는 `APPROVED`
- Blind-to-X 기준 `551 passed / 16 skipped`
- 테스트 파일 수는 현재 `130`개

## 리뷰 시 주의해 달라고 할 점

- 한국어 문장 품질은 번역투 여부보다도 `구체성`, `장면성`, `훅`, `CTA`, `클리셰 밀도`, `직장인 관점 적합도`를 기준으로 봐 달라고 요청하는 편이 좋습니다.
- “완전 자동화”보다 “사람이 마지막 승인하는 안정적 운영”을 선호하는 프로젝트라는 점을 알려주는 것이 좋습니다.
