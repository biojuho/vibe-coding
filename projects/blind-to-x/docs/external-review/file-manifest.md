# File Manifest

이 문서는 외부 LLM 리뷰용으로 어떤 파일을 어떤 목적에 맞춰 보내면 좋은지 정리합니다.

## Tier 0: 반드시 먼저 보내기

이 파일들만으로도 외부 LLM이 전체 방향을 꽤 정확하게 잡을 수 있습니다.

- `projects/blind-to-x/docs/external-review/project-brief.md`
- `projects/blind-to-x/docs/external-review/review-prompt.md`
- `projects/blind-to-x/docs/external-review/share-checklist.md`
- `projects/blind-to-x/README.md`
- `projects/blind-to-x/directives/x_content_curation.md`
- `projects/blind-to-x/config.example.yaml`

## Tier 1: 구조 리뷰 핵심 파일

- `projects/blind-to-x/main.py`
  - CLI 진입점, 런 오케스트레이션, budget/lock/review-only 흐름
- `projects/blind-to-x/pipeline/process.py`
  - 포스트 단위 처리의 핵심 조립 지점
- `projects/blind-to-x/pipeline/feed_collector.py`
  - 수집 소스와 후보 정리 책임
- `projects/blind-to-x/pipeline/content_intelligence.py`
  - 결정론적 분류와 점수화
- `projects/blind-to-x/pipeline/review_queue.py`
  - 검토 큐 이동 기준
- `projects/blind-to-x/pipeline/notion/_upload.py`
  - 업로드/스키마 경계

## Tier 2: 콘텐츠 품질 리뷰 핵심 파일

- `projects/blind-to-x/classification_rules.yaml`
  - 토픽/감정/오디언스 규칙, 골든 예시, 안티 예시, 브랜드 보이스, 편집 규칙
- `projects/blind-to-x/pipeline/draft_generator.py`
  - 초안 프롬프트 생성과 LLM fallback
- `projects/blind-to-x/pipeline/editorial_reviewer.py`
  - 에디토리얼 점수화와 리라이트
- `projects/blind-to-x/pipeline/draft_quality_gate.py`
  - 플랫폼별 최소 품질 기준
- `projects/blind-to-x/pipeline/draft_validator.py`
  - 게이트 실패 시 retry 프롬프트
- `projects/blind-to-x/pipeline/cross_source_insight.py`
  - 단일 게시글이 아닌 합성형 인사이트 초안

## Tier 3: 증거용 테스트 파일

이 파일들은 “의도한 품질 기준이 무엇인지”를 외부 LLM이 읽어내는 데 매우 유용합니다.

- `projects/blind-to-x/tests/unit/test_draft_generator_multi_provider.py`
- `projects/blind-to-x/tests/unit/test_quality_improvements.py`
- `projects/blind-to-x/tests/unit/test_quality_gate_retry.py`
- `projects/blind-to-x/tests/unit/test_pipeline_flow.py`
- `projects/blind-to-x/tests/unit/test_review_queue.py`
- `projects/blind-to-x/tests/unit/test_cross_source_insight.py`

## Tier 4: 실제 사례

가능하면 아래를 1~3건 정도 같이 보내세요.

- 익명화한 원문 제목/본문 요약
- 계산된 콘텐츠 프로파일
- 생성된 초안
- 에디토리얼 점수
- 품질 게이트 결과
- 사람의 최종 판단

실제 사례는 `sample-case-template.md` 형식으로 정리하면 충분합니다.

## Quick Review 추천 조합

- Tier 0 전부
- Tier 1에서 `main.py`, `process.py`, `content_intelligence.py`
- Tier 2에서 `classification_rules.yaml`, `draft_generator.py`, `editorial_reviewer.py`, `draft_quality_gate.py`

## Deep Review 추천 조합

- Quick Review 전부
- Tier 1 나머지
- Tier 2 나머지
- Tier 3에서 테스트 3~6개
- 실제 사례 1~3건

## 보내지 않아도 되는 것

- `.env`
- 실제 `config.yaml`
- 전체 테스트 폴더 덤프
- `.tmp` 산출물
- 원본 스크린샷 대량 묶음
- 운영 중 생성된 전체 Notion export
