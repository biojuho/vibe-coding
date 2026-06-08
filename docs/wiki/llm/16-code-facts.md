# 16 · Code Facts Manifest
> LLM Wiki가 `LLMClient`, provider fallback 순서, default model, 함수/클래스 이름을 수동 기억에 의존하지 않도록 만든 코드 사실 manifest 운영 문서다. 관련: [README](README.md), [01-architecture](01-architecture.md), [06-per-project](06-per-project.md), [14-maintenance-verification](14-maintenance-verification.md).

## 목적

`docs/wiki/llm/code-facts.json`은 현재 Python 코드에서 다음 사실을 추출한다.

| 대상 | 추출 범위 |
|------|-----------|
| `workspace/execution/llm_client.py` | `PROVIDER_ALIASES`, `DEFAULT_PROVIDER_ORDER`, `DEFAULT_MODELS`, OpenAI-compatible base URL, API key env var, pricing key, `LLMClient` methods |
| `projects/shorts-maker-v2/.../llm_router.py` | provider alias, default model, OpenAI-compatible base URL, `LLMRouter` methods |
| `projects/blind-to-x/pipeline/draft_providers.py` | provider alias, default provider order, class method를 포함한 `_generate_with_*` helper 목록 |

이 manifest는 문서 문장을 자동으로 이해하지 않는다. 대신 "현재 코드가 말하는 사실"을 JSON으로 고정해두고, 코드가 바뀌었는데 wiki가 그대로인 상황을 `code_facts_drift`로 드러낸다.

## 생성/감사 명령

```bash
# 현재 Python 코드에서 code-facts.json 재생성 후 wiki 감사
py -3.13 execution/llm_wiki_audit.py --write-code-facts --json

# source inventory까지 함께 재생성해야 할 때
py -3.13 execution/llm_wiki_audit.py --write-source-inventory --write-code-facts --json

# 쓰기 없이 drift만 확인
py -3.13 execution/llm_wiki_audit.py --json
```

감사 실패 코드:

| 코드 | 의미 | 조치 |
|------|------|------|
| `missing_code_facts` | wiki가 코드 사실을 언급하지만 manifest가 없음 | `--write-code-facts` 실행 |
| `invalid_code_facts` | JSON 파싱 또는 root 타입 오류 | manifest 재생성 |
| `code_facts_schema_mismatch` | schema version 불일치 | 감사 도구와 manifest를 같이 갱신 |
| `code_facts_drift` | 현재 Python 코드와 manifest가 다름 | manifest 재생성 후 관련 wiki 문장 검토 |

## A/B 판단

| 기준 | A. 수동 file:line 점검 | B. AST literal manifest |
|------|------------------------|-------------------------|
| provider 순서 변경 감지 | 리뷰어가 봐야 함 | `DEFAULT_PROVIDER_ORDER` drift 자동 감지 |
| default model 변경 감지 | 문서 검색에 의존 | `DEFAULT_MODELS` drift 자동 감지 |
| 함수/클래스 이름 drift | 깨진 링크가 아니면 놓치기 쉬움 | method/function 목록 변화가 manifest drift로 보임 |
| 외부 의존성 | 없음 | 없음. Python 표준 `ast`, `json`만 사용 |
| 한계 | 누락 위험 큼 | 문장 의미 검증은 여전히 수동 |

**결론:** B를 기본 gate로 둔다. 코드 literal drift는 자동으로 잡고, "이 변경이 문서 결론을 어떻게 바꾸는가"는 auto-research 루프에서 검토한다.

## 현재 한계

- YAML config drift는 [17-config-facts](17-config-facts.md)가 별도로 추적한다. Config provider와 runtime helper/model coverage mismatch는 [18-runtime-wiring-checks](18-runtime-wiring-checks.md)와 `config-facts.json`의 runtime checks가 추적한다.
- `ast.literal_eval`이 읽을 수 있는 module-level literal 상수만 추출한다. 런타임 계산값, env 기반 default, provider API 실제 응답은 범위 밖이다.
- `generated_at`은 기록용이다. drift 비교는 schema, facts, checks에 집중한다.

## 출처

- 공식: Python `ast` standard library documentation: <https://docs.python.org/3/library/ast.html>
- 공식: Python `json` standard library documentation: <https://docs.python.org/3/library/json.html>
- 코드 근거: `execution/llm_wiki_audit.py`, `workspace/tests/test_llm_wiki_audit.py`, `docs/wiki/llm/code-facts.json`

*외부 자료 검증일: 2026-06-08 · 코드 검증: 현재 HEAD*
