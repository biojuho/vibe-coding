# blind-to-x 생성물 품질 개선 제안 (2026-05-26)

## 1. 배경 — 현재 출력 품질 게이트 지형

blind-to-x 는 LLM 생성 직후 7층 검증을 거친다:

1. `DraftQualityGate` (platform 별) — 길이, 한글 비율, hashtag 상하한, scene anchor, hook 강도, 상투 오프닝, 반복 문장, 모호 표현, 클리셰 ≥ 3개
2. `QualityGate` (multi-axis) — toxic/PII, 클리셰, forbidden_expressions, 반복, 원문 fidelity (숫자)
3. `FactChecker` — 숫자/수치 결정론적 검증
4. `EditorialReviewer` — LLM 5축 (hook/specificity/voice/engagement/readability) + 최대 2회 리라이트
5. `RegulationChecker` — 의료/금융/광고 규제
6. `ViralFilter` + `MLScorer` — 발행 적합도
7. Notion 사람 승인 단계 (`review_only`)

깔린 게이트는 풍부하지만, **톤을 결정짓는 핵심 결함 5개**가 빠져 있다. 모두 **결정론적·비용 0·즉시 적용 가능**이라 ROI 가 가장 높다.

## 2. 핵심 결함 (출력 표본을 검토해 도출)

| # | 결함 | 현재 상태 | 영향 |
|---|------|----------|------|
| D1 | **인플루언서 어휘 zero-tolerance 미적용** | `cliche_watchlist` 에 "끝판왕/민낯/시그널/지뢰/쓴맛/기절할 뻔" 들어있지만, 같은 항목이 **3개 이상** 등장해야 차단. 1~2개는 통과 → 톤 파괴 | 인플루언서 톤·자극적 명사화는 ADR 기준 "한 번도 등장하면 안 됨" |
| D2 | **마무리 여운 정책 미감시** | `_has_generic_cta` 는 "여러분 생각은?" 류만 감지. `?` 로 끝나거나 "댓글로/저장해두세요/공감하면 RT" 단발은 통과 | 브랜드 보이스 핵심 ("여운으로 끝낼 것") 깨짐 |
| D3 | **이모지 무한 허용** | voice_traits "이모지 기본 없음, 1개 이하" 인데 카운트 검사 자체가 없음 | 4-5개씩 박혀도 게이트 통과 |
| D4 | **출처 도입 강박** | "블라인드에서 봤는데/~에서 본 글인데" 매번 시작은 yaml 금지인데 매칭 없음 | 매 글마다 같은 어조 → 단조로움 |
| D5 | **원문 베끼기 (paraphrase 부족)** | `FactChecker` 는 숫자만, 본문 문장 그대로 복붙은 검출 0 | 저작권 + 큐레이션이 아닌 복제 콘텐츠로 전락 |

추가로 **D6 (AI 접속사 과다: "즉/다시 말해/결국/한편/또한")**, **D7 (creator_take 누락)** 이 있지만 D1-D5 보다 1티어 낮음.

## 3. 개선안

### Phase 1 — Deterministic Hardening (이번 이터레이션)

| ID | 개선 | 위치 | 임계 | 심각도 |
|----|------|------|------|--------|
| P1-A | **인플루언서 어휘 zero-tolerance** — 1회 등장만으로 `error` | `draft_quality_gate.py` 신규 검사 + 상수 `_INFLUENCER_VOCAB` | ≥ 1 → error | 높음 |
| P1-B | **마무리 여운 검증** — 마지막 문장이 `?`/CTA 단어로 끝나면 error | `draft_quality_gate.py` `_ends_with_cta_or_question` | 매칭 1개 → error (twitter/threads 만) | 높음 |
| P1-C | **이모지 카운트 제한** — twitter/threads 1개 초과 warning, 3개 초과 error | `draft_quality_gate.py` `_count_emojis` | > 1 warning, > 3 error | 중 |
| P1-D | **도입 강박 차단** — "(블라인드\|뽐뿌\|에펨\|잡플래닛)에서 (봤는데\|본 글)" 첫 문장 매칭 시 warning | `draft_quality_gate.py` `_has_lead_dependency` | 매칭 1개 → warning | 중 |
| P1-E | **원문 N-gram 베끼기** — 원문과 12자 연속 일치가 2개 이상이면 warning, 4개 이상이면 error | `quality_gate.py` `_check_originality` | ≥ 2 → warning, ≥ 4 → error | 높음 |

모두 결정론적, LLM 호출 0, p99 < 5ms 추정.

### Phase 2 — LLM Side + 결정론적 무색무취 (2026-05-26 추가 출하)

**목표**: "이유 없는 생성물" → "댓글이 달리는 글" 로 전환.

| ID | 개선 | 위치 | 종류 |
|----|------|------|------|
| P2-A | **댓글 트리거 프레임워크** 4축 (식별감/입장/오픈루프/구체 앵커) 을 트위터/스레드 생성 프롬프트에 주입 | `draft_prompts.py` `_build_comment_trigger_block` | Prompt |
| P2-B | **에디토리얼 4축 점수** — twitter/threads 한정. 5축 평균 통과해도 4축 평균 < 6이면 리라이트 | `editorial_reviewer.py` `_build_review_prompt` / routing / `EditorialResult.comment_trigger_scores` | LLM 평가 |
| P2-C | **creator_take 무색무취 결정론적 검출** — hedge ≥ 2 또는 (일반화 어휘 + 입장 0) | `draft_quality_gate.py` `_is_colorless_take`, `_extract_creator_take` | Deterministic |
| P2-D | naver_blog `<creator_take>` 태그 누락/무색무취 warning | `draft_quality_gate.py` validate() | Deterministic |

**보수성**: golden 예시 7개 모두 false-positive 없음 (의도적으로 짧고 함축적
표현이라 단순 "stance == 0" 만으로는 못 잡음. 무색무취 트리거는 hedge 누적
또는 "자주/다양/많은" 같은 일반화 어휘 동반 시에만 발화).

**라우팅 변경**: 기존 5축 평균 임계 + 4축 평균 임계 (기본 6.0) 를 AND 로 묶음.
한쪽이라도 미달이면 최대 2회 리라이트. 둘 다 통과해야 END.

신규 회귀 테스트: `tests/unit/test_comment_trigger_uplift.py` 40 케이스 (block
주입 6, prompt 4축 5, EditorialResult 2, 라우팅 2, colorless 검출기 12,
태그 추출 5, gate 통합 5).

### Phase 3 — Product (다음 이터레이션)

### Phase 3 — Product (다음 이터레이션)

- creator persona 토픽별 voice 사전을 학습 데이터로 작은 LoRA 어댑터 운영 (현재 시점 비용/가치 불일치 가능성)
- Notion 검토 단계에서 "마무리 여운 점수" Top 3 + 댓글 트리거 4축 표시
- **Best-of-2 셀렉터** (생성 시점에 2안 → 4축 점수 비교 후 선정) — LLM 비용
  ~2배, 사용자 결정 필요 (`editorial.best_of_n.twitter=true` opt-in 설계됨)
- 같은 토픽 클러스터 최근 5건 캡션 의미 유사도 ≥ 0.85 시 reroll
  (n-gram 기준, 비용 0)

## 4. 수용 기준 (이번 PR)

- `draft_quality_gate.py` 의 새 검사 5종이 통과하지 않은 초안을 명확히 식별
- 기존 1500+ 단위 테스트 모두 그린 유지
- 신규 검사 각각 최소 4 테스트 (양성·음성·경계 포함)
- `project_qc_runner.py --project blind-to-x --check test --json` 전부 green
- 사람이 읽는 한 줄 요약은 `format_summary` 에 자연스럽게 포함

## 5. 위험과 완화

- **위험**: 새 검사가 기존 골든 예시까지 차단 → 골든 예시는 사람이 손으로 다듬은 것이라 통과해야 함.
  **완화**: 골든 예시 (`rules/examples.yaml`) 로 회귀 테스트 추가.
- **위험**: 마무리 여운 검사가 "?" 가 본문 중간에 있는 자연스러운 경우까지 잡음.
  **완화**: 마지막 문장 (정규식 `[.!?\n]` split 의 마지막) 한정으로만 검사.
- **위험**: zero-tolerance 가 너무 빡빡해 발행 정체.
  **완화**: error 라도 사람 검토는 막지 않음 (review_only 기본 true). 자동 발행 모드에서만 차단.
