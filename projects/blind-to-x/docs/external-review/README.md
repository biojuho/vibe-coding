# blind-to-x External Review Pack

이 폴더는 `blind-to-x`를 외부 LLM에게 리뷰받을 때 필요한 맥락을 빠르게 전달하기 위한 공유 패키지입니다.

목표는 두 가지입니다.

1. 구조와 책임 분리가 적절한지 검토받기
2. 콘텐츠 생성 규칙과 초안 품질 시스템이 실제로 좋은 결과를 만들고 있는지 검토받기

## 빠른 공유 순서

외부 LLM에게는 아래 순서로 주는 것이 가장 효율적입니다.

1. `project-brief.md`
2. `review-prompt.md`
3. `file-manifest.md`
4. `share-checklist.md`
5. `sample-case-template.md` 또는 실제로 채운 샘플 케이스 1~3개
6. `file-manifest.md`에 적힌 핵심 코드/규칙 파일

## 추천 공유 세트

### Quick Review

짧은 맥락으로 구조와 방향성만 확인하고 싶을 때:

- `project-brief.md`
- `review-prompt.md`
- `projects/blind-to-x/README.md`
- `projects/blind-to-x/directives/x_content_curation.md`
- `projects/blind-to-x/config.example.yaml`
- `projects/blind-to-x/classification_rules.yaml`
- `projects/blind-to-x/main.py`
- `projects/blind-to-x/pipeline/process.py`
- `projects/blind-to-x/pipeline/content_intelligence.py`
- `projects/blind-to-x/pipeline/draft_generator.py`
- `projects/blind-to-x/pipeline/editorial_reviewer.py`
- `projects/blind-to-x/pipeline/draft_quality_gate.py`

### Deep Review

리팩터링 조언과 콘텐츠 품질 체계까지 깊게 보고 싶을 때:

- Quick Review 전부
- `projects/blind-to-x/pipeline/review_queue.py`
- `projects/blind-to-x/pipeline/draft_validator.py`
- `projects/blind-to-x/pipeline/notion/_upload.py`
- `projects/blind-to-x/pipeline/feed_collector.py`
- `projects/blind-to-x/pipeline/cross_source_insight.py`
- `projects/blind-to-x/tests/unit/test_draft_generator_multi_provider.py`
- `projects/blind-to-x/tests/unit/test_quality_improvements.py`
- `projects/blind-to-x/tests/unit/test_quality_gate_retry.py`
- `projects/blind-to-x/tests/unit/test_pipeline_flow.py`

## 무엇을 절대 보내지 말아야 하나

- 실제 `.env`
- 실제 `config.yaml`
- Notion API 키, DB ID, OAuth 토큰, Cloudinary 키
- 운영 로그의 원본 에러 메시지 중 개인 식별 정보가 섞인 것
- `.tmp/failures/`, 실제 스크린샷, 실제 사용자/작성자 계정 정보
- Notion 페이지 링크 중 내부 식별자가 그대로 드러나는 것
- 원문 게시글을 그대로 대량 전달한 덤프

## 가장 좋은 추가 자료

외부 LLM은 규칙만 봐서는 품질을 과대평가하기 쉽습니다. 아래 자료가 있으면 조언의 질이 크게 올라갑니다.

- 실제 입력 1~3건의 익명화 샘플
- 해당 입력에서 생성된 초안
- 에디토리얼 점수/품질 게이트 결과
- 사람이 최종적으로 승인/보류/반려한 이유

샘플 구조는 `sample-case-template.md`에 정리해 두었습니다.

## 로컬 공유 번들

같은 내용의 로컬 공유 번들은 아래 위치에 만들 수 있습니다.

- `.tmp/blind-to-x-external-review/`

이 위치는 임시 공유/압축용입니다. 문서 원본은 이 `docs/external-review/` 폴더를 기준으로 유지합니다.
