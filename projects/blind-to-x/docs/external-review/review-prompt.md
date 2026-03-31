# Review Prompt

외부 LLM에게 보낼 때는 “좋게 봐줘”가 아니라, 무엇을 어떻게 비평해 달라는지 구체적으로 적는 것이 중요합니다.

## KR Prompt

```text
당신은 코드 구조와 콘텐츠 시스템을 함께 리뷰하는 시니어 아키텍트 겸 에디토리얼 시스템 리뷰어입니다.

제가 공유하는 프로젝트는 `blind-to-x`라는 한국어 콘텐츠 파이프라인입니다.
이 프로젝트는 Blind/커뮤니티 글을 수집해서, 사람이 검토한 뒤 X(Twitter) 중심의 게시 초안으로 전환합니다.
현재 운영 철학은 "완전 자동화"보다 "안전한 human-in-the-loop 운영"에 가깝습니다.

중점적으로 봐야 할 축은 두 가지입니다.

1. 소프트웨어 구조
- 모듈 경계가 적절한지
- 책임이 과도하게 몰린 파일이 있는지
- 규칙 기반 로직과 LLM 기반 로직의 경계가 명확한지
- 지금 구조가 앞으로 확장 가능한지

2. 콘텐츠 질 시스템
- 현재 프롬프트/룰/골든예시/안티예시가 실제로 좋은 한국어 초안을 만드는 구조인지
- 결과가 지나치게 템플릿화되거나 경직될 위험은 없는지
- 사람 검토 부담을 줄이려면 어느 레이어를 먼저 손봐야 하는지
- 클리셰, generic CTA, AI 말투, 과적합된 규칙의 위험이 있는지

중요한 전제:
- 프로젝트의 결과물은 한국어입니다.
- 한국어 표현을 볼 때 번역투 여부만 보지 말고, 구체성, 장면성, 훅, CTA, 클리셰 밀도, 직장인 관점 적합도를 봐주세요.
- "더 자동화하라"보다 "더 안정적이고 유지보수 가능하게 하라" 쪽을 우선해 주세요.

원하는 출력 형식:

1. Executive Summary
- 이 프로젝트의 현재 구조를 한 문단으로 요약
- 가장 먼저 손봐야 할 문제 3개

2. Structural Findings
- 심각도 높은 순서대로 5~10개
- 각 항목마다: 문제 / 왜 문제인지 / 영향 / 권장 수정 방향

3. Content-System Findings
- 심각도 높은 순서대로 5~10개
- 각 항목마다: 문제 / 왜 문제인지 / 예상되는 나쁜 출력 패턴 / 개선 방향

4. Fast Wins
- 1주 안에 가능한 개선 5개

5. Refactor Roadmap
- 2주짜리 정리
- 1~2개월짜리 구조 개선

6. Keep List
- 이 프로젝트에서 유지해야 할 좋은 설계 3~5개

추가 요구:
- 막연한 원칙론보다, 제가 보낸 파일에 근거한 구체적인 지적을 해주세요.
- 가능하면 "어느 파일의 어떤 책임이 너무 크다" 수준으로 말해주세요.
- 코드 전체 재작성 제안보다, 점진적 개선 경로를 우선 제안해주세요.
```

## EN Prompt

```text
You are reviewing a project as both a software architect and an editorial-system critic.

The project is called `blind-to-x`. It is a Korean-language content pipeline that collects workplace/community posts, generates draft content for X(Twitter), and routes items through a human review queue before publishing.

The product philosophy is not “full automation at all costs.” It is closer to “safe human-in-the-loop operations with improving quality.”

Please review the project along two axes:

1. Software structure
- Are module boundaries reasonable?
- Are there orchestration files that own too much responsibility?
- Is the boundary between deterministic logic and LLM-driven logic clear enough?
- Is the system maintainable as it grows?

2. Content-quality system
- Do the prompt/rule/golden-example/anti-example systems actually support high-quality Korean output?
- Is the system at risk of becoming over-templated, rigid, or overfit to its own examples?
- Which layer should be improved first if we want better output quality with less human review burden?
- Are there risks around cliches, generic CTA patterns, AI-sounding prose, or rule sprawl?

Important context:
- The generated outputs are in Korean.
- When you assess Korean content quality, do not focus only on “translation-like phrasing.”
- Instead, evaluate specificity, scene anchoring, hook strength, CTA quality, cliche density, and fit for Korean workplace readers.
- Prefer incremental, maintainable improvements over “rewrite everything” advice.

Desired output format:

1. Executive Summary
- One-paragraph summary of the current system
- Top 3 issues to address first

2. Structural Findings
- 5 to 10 findings ordered by severity
- For each: issue / why it matters / impact / recommended direction

3. Content-System Findings
- 5 to 10 findings ordered by severity
- For each: issue / why it matters / likely bad output pattern / recommended improvement

4. Fast Wins
- 5 improvements that can be done within 1 week

5. Refactor Roadmap
- 2-week cleanup plan
- 1-2 month structural improvement plan

6. Keep List
- 3 to 5 design choices that should be preserved

Please ground your feedback in the files I share, and prefer concrete file-level observations over generic advice.
```

## 같이 보내면 좋은 한 줄 메모

```text
Please optimize for maintainability and real editorial quality, not maximum automation.
```
