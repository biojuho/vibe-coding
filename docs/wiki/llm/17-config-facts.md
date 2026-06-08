# 17 · Config Facts Manifest
> LLM Wiki가 YAML 설정의 provider 순서와 default model을 수동 기억에 의존하지 않도록 만든 config fact manifest 운영 문서다. 관련: [README](README.md), [06-per-project](06-per-project.md), [14-maintenance-verification](14-maintenance-verification.md), [16-code-facts](16-code-facts.md), [18-runtime-wiring-checks](18-runtime-wiring-checks.md).

## 목적

`docs/wiki/llm/config-facts.json`은 현재 tracked YAML config에서 다음 사실을 추출한다.

| 대상 | 추출 범위 |
|------|-----------|
| `projects/shorts-maker-v2/config.yaml` | `providers.llm`, `providers.llm_providers`, `providers.llm_models`, 단일 `llm_model` |
| `projects/blind-to-x/config.example.yaml` | `llm.strategy`, `llm.providers`, retry/timeout, pricing provider, provider별 enabled/model |
| `projects/blind-to-x/config.ci.yaml` | CI용 LLM provider 순서와 provider별 enabled/model |

`projects/blind-to-x/config.yaml`은 로컬 비밀값을 포함할 수 있으므로 manifest 대상에서 제외한다. 운영 문서에 인용할 기준은 tracked `config.example.yaml`/`config.ci.yaml`이다.

## 생성/감사 명령

```bash
# 현재 tracked YAML config에서 config-facts.json 재생성 후 wiki 감사
py -3.13 execution/llm_wiki_audit.py --write-config-facts --json

# source/code/config manifest를 모두 갱신해야 할 때
py -3.13 execution/llm_wiki_audit.py --write-source-inventory --write-code-facts --write-config-facts --json

# 쓰기 없이 drift만 확인
py -3.13 execution/llm_wiki_audit.py --json
```

감사 실패 코드:

| 코드 | 의미 | 조치 |
|------|------|------|
| `missing_config_facts` | wiki가 config 사실을 언급하지만 manifest가 없음 | `--write-config-facts` 실행 |
| `invalid_config_facts` | JSON 파싱 또는 root 타입 오류 | manifest 재생성 |
| `config_facts_schema_mismatch` | schema version 불일치 | 감사 도구와 manifest를 같이 갱신 |
| `config_facts_drift` | 현재 tracked YAML config와 manifest가 다름 | manifest 재생성 후 관련 wiki 문장 검토 |

## 현재 확인된 config 사실

| 프로젝트 | provider 순서 | model coverage |
|----------|---------------|----------------|
| shorts-maker-v2 | `google → groq → mimo → deepseek → moonshot → zhipuai → openai → xai → anthropic` | 9/9 provider에 `llm_models` 있음 |
| blind-to-x example | `gemini → deepseek → xai → moonshot → zhipuai → openai → anthropic` | 7/7 provider에 model과 pricing 있음. `openai.enabled=false` |
| blind-to-x CI | `gemini → deepseek → xai → moonshot → zhipuai → openai → anthropic` | 7/7 provider에 model과 pricing 있음. `openai.enabled=true` |

이 표는 runtime wiring을 보장하지 않는다. T-1580 이후 `config-facts.json`은 [18-runtime-wiring-checks](18-runtime-wiring-checks.md)의 cross-manifest check도 포함한다. 현재 blind-to-x config에는 `deepseek`, `moonshot`, `zhipuai`가 있지만 `DraftProvidersMixin`에는 해당 `_generate_with_*` helper가 없고, `ollama` helper는 tracked config 밖에 있다. 이 mismatch는 [06-per-project](06-per-project.md)의 지뢰밭과 manifest warning 둘 다로 유지한다.

## A/B 판단

| 기준 | A. YAML을 수동으로 읽어 문서 갱신 | B. `safe_load` 기반 config manifest |
|------|-----------------------------------|-------------------------------------|
| provider 순서 drift | 리뷰어가 놓치기 쉬움 | `config_facts_drift` 자동 감지 |
| 모델 coverage | 표를 수동 대조해야 함 | provider/model/pricing coverage check 가능 |
| 비밀값 노출 위험 | 실제 로컬 config를 열면 위험 | tracked config만 읽고 API key 계열은 추출하지 않음 |
| 구현 비용 | 낮음 | 낮음. 이미 PyYAML 의존성이 있음 |
| 한계 | 반복 실수 큼 | runtime wiring은 code-facts와 함께 봐야 함 |

**결론:** B를 기본 gate로 둔다. config drift는 자동으로 잡고, 실제 provider 실행 가능 여부는 `code-facts.json`과 코드 검토로 확인한다.

## 출처

- 공식: PyYAML documentation, `safe_load` and `SafeLoader`: <https://pyyaml.org/wiki/PyYAMLDocumentation>
- 공식: YAML 1.2.2 specification, mappings/sequences/scalars: <https://yaml.org/spec/1.2.2/>
- 코드 근거: `execution/llm_wiki_audit.py`, `workspace/tests/test_llm_wiki_audit.py`, `docs/wiki/llm/config-facts.json`

*외부 자료 검증일: 2026-06-08 · config 검증: 현재 HEAD*
