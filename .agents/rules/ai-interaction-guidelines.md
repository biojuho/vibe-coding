# AI Interaction Guidelines

이 문서는 AI 에이전트가 대화 타이틀을 생성하고 프로젝트 목표를 요약할 때 지켜야 할 구조화된 프로세스와 응답 원칙을 정의합니다. 모든 AI는 미래의 응답에서 행동 지향적(action-oriented)이고 정확하며 제공된 작업 컨텍스트에 엄격하게 기반을 두어야 합니다.

## 1. 대화 타이틀 생성 (Generating Conversation Titles)
- **간결함 (Concise)**: 대화 타이틀은 3~5단어 내외의 명확하고 간결한 명사형 구문이어야 합니다.
  - 좋은 예: "Refining AI Interaction Guidelines", "Stabilizing CI Pipeline Reliability"
  - 나쁜 예: "사용자가 요청한 AI 상호작용 가이드라인 수정 작업 진행하기"
- **명확성 (Clear)**: 세션의 핵심 목표나 달성하려는 최종 결과를 직관적으로 나타내야 합니다.
- **언어 (Language)**: 프로젝트 관리 및 가독성의 일관성을 위해 Title은 영문 Title Case 형식으로 작성하는 것을 권장합니다.

## 2. 프로젝트 목표 요약 (Summarizing Project Goals)
- **액션 중심 (Action-Oriented)**: 목표는 단순히 상황을 설명하는 것이 아니라, 무엇을 '달성'할 것인지 구체적인 액션 위주로 서술해야 합니다.
- **구조화된 형식 (Structured Format)**: "The user aims to [행동 동사] [핵심 목표] by [구체적인 방법론이나 도구]." 와 같은 구조를 따릅니다.
- **정확성 및 컨텍스트 기반 (Accurate & Grounded)**: 사용자가 제공한 프롬프트, 에러 로그, 현재 프로젝트 상태(HANDOFF, TASKS) 등 주어진 컨텍스트에만 기반해야 하며, 임의로 추측하거나 벗어난 내용을 추가해서는 안 됩니다.

## 3. AI 응답 원칙 (AI Response Principles)
- **행동 지향 (Action-Oriented)**: 불필요한 사족이나 장황한 설명을 생략하고, 즉시 실행 가능한 해결책(코드, 명령어)과 명확한 다음 단계를 제시합니다.
- **정확성 (Accurate)**: 검증되지 않은 정보나 환각(Hallucination)을 피하고, 확신할 수 없을 때는 사용자에게 질문하여 명확히 합니다.
- **컨텍스트 엄수 (Strictly Grounded)**: 모든 응답은 현재 작업 중인 파일 시스템, 설정 파일, 이전 대화 기록 등 명시적인 작업 컨텍스트 내에서 이루어져야 합니다.
