# LLM 품질 회귀 평가 — Promptfoo

> **목적**: blind-to-x 드래프트 품질이 프롬프트 변경/모델 변경에 따라 회귀했는지 매주 정량 측정한다. Notion 운영자 reject 데이터를 negative eval set으로 자동 수확한다.

## 범위 (In/Out)

- **In**: blind-to-x draft 생성(`pipeline/draft_generator.py`), shorts-maker-v2 script 생성(`pipeline/script_step.py`)
- **Out**: A/B 트래픽 분기, runtime 게이팅. 평가는 **오프라인 회귀**용.

## 입력/출력

- **입력**:
  - 골든셋: `tests/eval/blind-to-x/golden_cases.yaml` — 사람 승인 드래프트
  - 부정셋: `tests/eval/blind-to-x/rejected_cases.yaml` — Notion `발행거부` 카드에서 자동 수확
- **출력**:
  - `.tmp/eval/blind-to-x/<YYYY-MM-DD>/results.json`
  - 콘솔 표 + Telegram MCP 요약 알림 (회귀 시만)

## 사용 도구

- **promptfoo** (npx 실행, MIT). YAML 1개로 다중 모델 × 다중 프롬프트 격자 평가.
- **LLM-as-judge**: 평가용 모델은 fallback의 더 비싼 슬롯 1개 고정(예: `claude-sonnet-4`)
- **메트릭**:
  - `contains-not` — regulation 위반 키워드 미포함
  - `length` — 280자 / 500자 등 플랫폼별 한도
  - `llm-rubric` — "원문 의도 보존", "지시 준수", "톤 일관성" 점수화
  - `latency` — provider별 p50/p95

## 단계

### 1. eval 데이터 추출 스크립트

- `execution/blind_to_x_eval_extract.py` 신규.
- Notion `발행승인` 상태 페이지 → `golden_cases.yaml`
- Notion `발행거부` 상태 + `reviewer_memo` 있는 페이지 → `rejected_cases.yaml`
- 매주 일요일 새벽 n8n에서 트리거 (별도 워크플로)

### 2. promptfoo 설정

- `tests/eval/blind-to-x/promptfooconfig.yaml`
  - `prompts`: `pipeline/draft_prompts.py`의 현재 system 프롬프트 두 버전(이전/현재)
  - `providers`: `anthropic`, `google`, `deepseek` 3종 비교
  - `tests`: golden + rejected 두 셋 모두 입력
  - `assertions`: 위 메트릭 4종

### 3. 실행 래퍼

- `execution/run_eval_blind_to_x.py` 신규. promptfoo CLI 호출 + 결과 요약
- 회귀 임계: 골든셋 평균 rubric 점수가 직전 주 대비 -10% 이상 하락 시 Telegram 알림
- 결과 아카이브: `.tmp/eval/blind-to-x/<date>/`

### 4. 검증

- `python execution/run_eval_blind_to_x.py --dry-run` → YAML lint OK, 골든셋 N건/부정셋 M건 카운트 출력
- `python execution/run_eval_blind_to_x.py --quick` → golden 5건만 1 provider로 실행, 5분 내 완료
- `workspace/tests/test_eval_extract.py` — Notion 모킹 + YAML 직렬화 검증

## 예외 상황 (Edge Cases)

- **Notion API 한도**: 추출 시 cursor + 100건씩 페이징, 실패 시 직전 주 yaml 재사용
- **promptfoo cost 폭주**: provider별 daily budget 환경변수(`PROMPTFOO_DAILY_BUDGET_USD=2.0`) 강제
- **judge 편향**: judge 모델은 분기마다 1회 변경 검토 (anthropic ↔ google), 결과 비교

## 파일 매핑

| 파일 | 변경 종류 |
|------|---------|
| `tests/eval/blind-to-x/promptfooconfig.yaml` | 신규 |
| `tests/eval/blind-to-x/golden_cases.yaml` | 자동 생성 |
| `tests/eval/blind-to-x/rejected_cases.yaml` | 자동 생성 |
| `execution/blind_to_x_eval_extract.py` | 신규 |
| `execution/run_eval_blind_to_x.py` | 신규 |
| `workspace/tests/test_eval_extract.py` | 신규 |
| `infrastructure/n8n/workflows/eval_weekly.json` | 신규 |

## 비고

- shorts-maker-v2용 동일 패턴은 골든셋이 모이고 난 뒤 별도 SOP로 분리
- DeepEval 도입 검토는 회귀 메트릭이 안정화된 뒤(>= 4주 누적)
- 평가 결과는 `directives/llm_fallback.md`의 provider 우선순위 재조정 근거로 사용
