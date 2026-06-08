# 15 · 외부 출처 인벤토리

> 이 페이지는 LLM Wiki의 외부 URL을 `source-inventory.json` 한 곳에서 추적해, 모델·가격·폐기·보안 기준 같은 시간 민감한 항목을 재검증할 때 누락을 줄이기 위한 운영 규칙이다.
> 관련: [02-providers](02-providers.md), [13-model-selection](13-model-selection.md), [14-maintenance-verification](14-maintenance-verification.md).

## 왜 필요한가

14번 게이트는 "외부 URL이 있고 검증일이 있는가"를 확인하지만, 다음 문제는 아직 남는다.

| 문제 | 증상 | 이번 사이클의 보강 |
|---|---|---|
| URL 분산 | provider·security·reasoning 페이지마다 공식 링크가 흩어져 있음 | [`source-inventory.json`](source-inventory.json)으로 URL·사용 페이지·재검증일을 집계 |
| 최신성 우선순위 부재 | 모델/가격 링크와 논문 링크가 같은 주기로 취급됨 | high/medium/low volatility와 `review_after`를 분리 |
| 드리프트 감지 부족 | 문서에서 URL을 삭제하거나 추가해도 manifest가 남거나 빠질 수 있음 | `llm_wiki_audit.py`가 markdown URL과 manifest URL을 비교 |

## 결정

**A. 페이지별 수동 출처 섹션만 유지**

- 장점: 작성이 빠르고 문서 안에서 맥락을 바로 볼 수 있다.
- 단점: "어느 URL을 언제 다시 봐야 하는가"를 전체 관점에서 알기 어렵다.

**B. 페이지별 출처 + 중앙 manifest**

- 장점: 재검증 대상, 사용 페이지, volatility, `review_after`가 한 파일에 모인다.
- 단점: manifest를 갱신하지 않으면 새 관리 표면이 하나 더 생긴다.

**권장:** B. 단, manifest는 수동 편집보다 감사 도구의 `--write-source-inventory` 출력으로 재생성하고, 사람이 검증 메모만 필요한 경우에만 보강한다.

## 파일과 명령

| 파일 | 역할 |
|---|---|
| [`source-inventory.json`](source-inventory.json) | 외부 URL, host, 사용 페이지, source type, volatility, cadence, `last_verified`, `review_after` |
| [`execution/llm_wiki_audit.py`](../../../execution/llm_wiki_audit.py) | markdown URL과 manifest URL을 비교하고 재검증 기한을 fail 처리 |
| [`workspace/tests/test_llm_wiki_audit.py`](../../../workspace/tests/test_llm_wiki_audit.py) | manifest 생성·드리프트·기한초과 회귀 테스트 |

```bash
# 현재 markdown 외부 URL에서 manifest 재생성 후 전체 감사
py -3.13 execution/llm_wiki_audit.py --write-source-inventory --json

# CI/로컬 검증에서는 쓰기 없이 감사만 실행
py -3.13 execution/llm_wiki_audit.py --json
```

## 재검증 등급

| 등급 | 기본 주기 | 예시 |
|---|---:|---|
| high | 45일 | provider models/pricing/rate limits, OpenAI deprecations, DeepSeek release/deprecation notes |
| medium | 90일 | structured output, reasoning/thinking, agent/context engineering 문서 |
| low | 180일 | OWASP 표준 페이지, 논문/PDF처럼 자주 바뀌지 않는 기준 |

`review_after`가 현재 날짜보다 과거이면 감사가 실패한다. 이때는 해당 공식 문서를 다시 확인하고, 관련 wiki 페이지와 manifest를 함께 갱신한다.

## 이번 적용 범위

- `docs/wiki/llm/*.md`의 외부 URL을 전수 스캔해 manifest로 모은다.
- fenced code와 localhost 예시는 외부 출처에서 제외한다.
- MiMo base URL처럼 코드에 박힌 endpoint는 `code-config`로 표시하고, 가격/모델 지원의 공식 출처로 취급하지 않는다.
- manifest는 URL 존재 확인 도구가 아니다. HTTP 생존성이나 provider 문서 내용의 의미 검증은 매 사이클의 외부 조사에서 별도로 한다.

## 출처 (1차 우선, 2026-06-08 확인)

- OpenAI, *Models*: <https://developers.openai.com/api/docs/models>
- OpenAI, *Pricing*: <https://developers.openai.com/api/docs/pricing>
- OpenAI, *Deprecations*: <https://developers.openai.com/api/docs/deprecations>
- Anthropic, *Models overview*: <https://platform.claude.com/docs/en/about-claude/models/overview>
- Google, *Gemini API models*: <https://ai.google.dev/gemini-api/docs/models>
- DeepSeek, *Models & Pricing*: <https://api-docs.deepseek.com/quick_start/pricing>
- DeepSeek, *V4 Preview Release*: <https://api-docs.deepseek.com/news/news260424>
- OWASP, *LLM Top 10*: <https://genai.owasp.org/llm-top-10/>

*외부 자료 검증일: 2026-06-08 · 코드 검증: 현재 HEAD*
