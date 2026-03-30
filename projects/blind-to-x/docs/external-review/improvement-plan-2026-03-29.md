# blind-to-x 개선안

외부 리뷰 리포트를 기준으로, 이번 라운드는 "규칙 추가"보다 "계약과 책임 정리"를 우선합니다.

## 이번 턴에서 바로 적용한 것

1. `draft contract` 기준을 코드로 명시했습니다.
   - 게시용 초안: `twitter`, `threads`, `newsletter`, `naver_blog`, `twitter_thread`
   - 보조 산출물: `reply_text`
   - 리뷰 메타데이터: `creator_take`

2. 품질 레이어를 게시용 초안 중심으로 정리했습니다.
   - `DraftQualityGate.validate_all()`은 게시용 초안만 검사
   - `EditorialReviewer.review_and_polish()`는 게시용 초안만 리뷰/폴리싱
   - `draft_validator.validate_and_fix_drafts()`도 게시용 초안만 재검증
   - `process.py`의 fact-check/readability 집계도 게시용 초안만 대상으로 축소

3. 생성 성공 조건에서 `creator_take`를 분리했습니다.
   - `creator_take`는 계속 파싱하고 Notion 메모에도 남기지만
   - 이제 생성 성공을 좌우하는 필수 태그에서는 제외됩니다.

4. 골든 예시 선택을 랜덤에서 결정적 선택으로 바꿨습니다.
   - 같은 입력이면 같은 예시 조합이 나오도록 고정
   - seed는 `topic_cluster + title + selection_summary` 기반

## 바로 다음 추천 작업

1. `process_single_post()`를 stage 단위로 쪼개기
   - `fetch`
   - `filter`
   - `profile`
   - `generate`
   - `review`
   - `persist`

2. `classification_rules.yaml` 분리
   - `rules/classification.yaml`
   - `rules/prompt_templates.yaml`
   - `rules/editorial_policy.yaml`
   - `rules/platform_policy.yaml`

3. `PromptAssembler`와 `ProviderGateway` 분리
   - 프롬프트 수정이 provider fallback / parser / retry 정책과 덜 얽히게 정리

4. `creator_take`와 `reply_text`를 Notion 표시 레이어에서도 구분
   - publishable 본문 1개
   - 보조 reply
   - reviewer memo

## 의도

이번 슬라이스의 목적은 "더 많은 규칙"이 아니라 "같은 규칙을 덜 겹치게" 만드는 것입니다.
이 기준이 잡히면 이후 리팩터링에서도 사람 검토 흐름을 덜 흔들고 구조를 재배치할 수 있습니다.
