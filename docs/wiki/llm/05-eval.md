# 05 · 품질 평가 (promptfoo)

> 프롬프트/모델 변경으로 **드래프트 품질이 회귀했는지** 오프라인으로 정량 측정.
> 운영 SOP: [llm_eval_promptfoo.md](../../../workspace/directives/llm_eval_promptfoo.md).
> 인용은 `execution/run_eval_blind_to_x.py`(루트 execution) / `tests/eval/blind-to-x/promptfooconfig.yaml` 기준, 2026-06-08 검증.

## 무엇인가

- **promptfoo**(npx, MIT) — YAML 1개로 다중 모델 × 다중 프롬프트 격자 평가.
- 대상: blind-to-x 드래프트 생성(현재 구현됨). shorts-maker-v2 script 생성은 골든셋 축적 후 별도 SOP로 예정.
- 용도: **오프라인 회귀**. A/B 트래픽 분기나 runtime 게이팅이 아니다.

## 실제 구성 (구현 확인됨)

| 파일 | 역할 | 상태 |
|------|------|------|
| `execution/run_eval_blind_to_x.py` | 실행 래퍼 (환경 검증 → 예산 가드 → `npx promptfoo eval` → baseline 비교 → 회귀 알림) | ✅ 존재 |
| `execution/blind_to_x_eval_extract.py` | Notion `발행승인`→golden / `발행거부`+memo→rejected 셋 추출 | ✅ 존재 |
| `tests/eval/blind-to-x/promptfooconfig.yaml` | providers·prompts·assertions 정의 | ✅ 존재 |
| `tests/eval/blind-to-x/golden_cases.yaml` · `rejected_cases.yaml` | 평가 데이터셋 | ⏳ **.gitignore, 매주 Notion에서 자동 생성** (추출 전엔 없음) |
| `.tmp/eval/blind-to-x/last_run.json` · `baseline.json` | 결과/기준선 | 실행 시 생성 |

## 평가 설정 (promptfooconfig.yaml)

- **prompts**: `prompts/draft_v_current.txt` (새 버전 비교 시 `draft_v_next.txt` 추가 등록).
- **providers** 3종 비교: `anthropic:messages:claude-haiku-4-5-20251001`, `openai:chat:gpt-4o-mini`, `deepseek:deepseek-chat` (각 temp 0.4 / max_tokens 600).
- **assertions** (defaultTest):
  - `output.length <= 280` — 플랫폼 길이 가드(X/Threads 280자).
  - `not-contains` "확정 수익" / "보장된" — 규제 위반 표현 차단.
  - `llm-rubric` (threshold 0.7): 원문 의도 유지 + 자연스러운 한국어 + 200자 이하 + **CTA(구매·클릭 유도) 미포함**.
- 길이/CTA 금지 규칙은 이 프로젝트의 콘텐츠 철학과 직접 연결된다(조용한 해설자, CTA 금지).

## 실행

```bash
# 환경만 검증 (config/데이터셋/ npx 존재)
py -3.13 execution/run_eval_blind_to_x.py --dry-run
# 빠른 실행 (golden 5건, 1 provider, 5분 내)
py -3.13 execution/run_eval_blind_to_x.py --quick
# 전체 평가
py -3.13 execution/run_eval_blind_to_x.py
# promptfoo 직접
npx promptfoo eval -c tests/eval/blind-to-x/promptfooconfig.yaml
```

흐름(run_eval): config+데이터셋 존재 검증 → 일일 비용 가드(`PROMPTFOO_DAILY_BUDGET_USD`) → `npx promptfoo eval` → 직전 `baseline.json` 비교 → **평균 점수 -10% 이상 하락 시 비-zero exit + (옵션) 텔레그램 알림**.

## 회귀 정책

- 임계: `REGRESSION_THRESHOLD = -0.10` (run_eval L40).
- judge 모델은 fallback의 비싼 슬롯 1개 고정(예: anthropic). 편향 점검 위해 분기마다 anthropic↔google 교체 검토.
- 평가 결과는 [llm_fallback.md](../../../workspace/directives/llm_fallback.md)의 provider 우선순위 재조정 근거로 쓴다.

## 데이터셋 수확 (Notion → YAML)

- `blind_to_x_eval_extract.py`: Notion `발행승인` 페이지 → `golden_cases.yaml`, `발행거부`+`reviewer_memo` → `rejected_cases.yaml`.
- 매주 일요일 새벽 n8n 트리거(별도 워크플로). Notion 한도 대비 cursor 100건 페이징, 실패 시 직전 주 yaml 재사용.

## 주의

- golden/rejected 셋은 .gitignore라 **clone 직후엔 없다** → `--dry-run`이 "데이터셋 누락"을 보고하면 먼저 extract를 돌린다.
- `npx`(Node.js)가 PATH에 있어야 한다.
- 비용 폭주 방지: provider별 `PROMPTFOO_DAILY_BUDGET_USD` 강제.

## 관련: 배치 실행

- `execution/ai_batch_runner.py` — 다건 LLM 작업 배치 러너(평가/대량 생성용). 평가와 별개 도구지만 같은 fallback 클라이언트를 공유한다.
