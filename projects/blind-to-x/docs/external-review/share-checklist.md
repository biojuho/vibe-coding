# External Share Checklist

외부 LLM에게 보내기 전에 아래 항목을 체크하세요.

## 1. 프로젝트 맥락

- [ ] 프로젝트의 한 줄 설명을 포함했다
- [ ] 현재 운영 모델이 `자동 수집 + 사람 검토 + 수동 발행` 중심이라는 점을 설명했다
- [ ] 핵심 목표가 `구조 개선`과 `콘텐츠 질 개선` 두 가지라는 점을 명시했다

## 2. 구조 리뷰용 자료

- [ ] `main.py`
- [ ] `pipeline/process.py`
- [ ] `pipeline/content_intelligence.py`
- [ ] `pipeline/review_queue.py`
- [ ] `pipeline/feed_collector.py`
- [ ] `pipeline/notion/_upload.py`

## 3. 콘텐츠 품질 리뷰용 자료

- [ ] `classification_rules.yaml`
- [ ] `pipeline/draft_generator.py`
- [ ] `pipeline/editorial_reviewer.py`
- [ ] `pipeline/draft_quality_gate.py`
- [ ] `pipeline/draft_validator.py`
- [ ] `directives/x_content_curation.md`

## 4. 운영/설정 자료

- [ ] `README.md`
- [ ] `config.example.yaml`
- [ ] 필요하면 `docs/ops-runbook.md`

## 5. 실제 품질 판단용 샘플

규칙만 보내면 외부 LLM이 추상적인 조언만 줄 가능성이 큽니다.

- [ ] 익명화한 실제 입력 샘플 1~3건
- [ ] 각 샘플의 생성 초안
- [ ] 품질 게이트 결과 또는 에디토리얼 점수
- [ ] 사람의 최종 판단과 이유

샘플이 없으면 `sample-case-template.md`를 사용해 최소 1건은 채우는 것이 좋습니다.

## 6. 함께 묻는 질문

- [ ] 구조상 가장 먼저 쪼개야 할 모듈은 무엇인가?
- [ ] 규칙 기반 시스템과 LLM 기반 시스템의 경계가 적절한가?
- [ ] 콘텐츠 품질을 높인다는 명분으로 규칙이 과도하게 많아지지는 않았는가?
- [ ] 테스트는 충분해 보여도 실제 질적 품질 관점에서 빠진 검증은 무엇인가?
- [ ] 2주 안에 할 수 있는 개선과 2개월짜리 리팩터링을 구분해 달라고 요청했다

## 7. 절대 제외할 것

- [ ] 실제 `.env`
- [ ] 실제 `config.yaml`
- [ ] 실제 API 키 / 토큰 / DB ID
- [ ] 실제 Notion 페이지 링크 전체
- [ ] 개인 식별 정보가 들어간 원문, 스크린샷, 로그
- [ ] 내부 운영 URL, 계정명, 이메일, 전화번호

## 8. 공유 방식

### 짧게 보고 싶을 때

- `project-brief.md`
- `review-prompt.md`
- 핵심 코드 6~10개

### 깊게 보고 싶을 때

- 위 자료 전부
- 테스트 파일 3~5개
- 익명화 샘플 케이스 1~3개

### 가장 좋은 방식

- 먼저 Quick Review를 받고
- 그 피드백 중 맞는 지점만 골라
- Deep Review에 필요한 추가 파일을 2차로 보내는 방식
