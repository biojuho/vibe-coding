# 14 · 유지보수·검증 게이트

> 이 페이지는 LLM Wiki를 **읽을 만한 문서**에서 **다음 작업자가 믿고 수정할 수 있는 문서**로 유지하기 위한 운영 기준이다.
> 관련: [README](README.md), [02-providers](02-providers.md), [10-structured-outputs](10-structured-outputs.md), [13-model-selection](13-model-selection.md), [15-source-inventory](15-source-inventory.md), [16-code-facts](16-code-facts.md), [17-config-facts](17-config-facts.md), [18-runtime-wiring-checks](18-runtime-wiring-checks.md).

## 왜 필요한가

LLM Wiki는 두 종류의 사실을 섞는다.

| 사실 종류 | 예 | 실패 양상 |
|-----------|----|-----------|
| repo 내부 사실 | `LLMClient` fallback 순서, `DEFAULT_MODELS`, 비용 DB, harness 상태 | 코드가 바뀌었는데 문서 file\:line·지뢰밭이 낡음 |
| 외부 사실 | 모델 가격·폐기일·구조화 출력 API·OWASP 항목 | provider 문서가 바뀌었는데 이전 결론을 계속 사용 |

그래서 위키 변경은 **문서 편집**이 아니라 작은 검증 작업으로 취급한다. 새 항목을 쓰면 최소한 로컬 링크, README 색인, 외부 출처, 검증일이 깨지지 않아야 한다.

## 결정론적 감사 도구

도구: [`execution/llm_wiki_audit.py`](../../../execution/llm_wiki_audit.py)

테스트: [`workspace/tests/test_llm_wiki_audit.py`](../../../workspace/tests/test_llm_wiki_audit.py)

```bash
py -3.13 execution/llm_wiki_audit.py --json
py -3.13 execution/llm_wiki_audit.py --write-code-facts --json
py -3.13 execution/llm_wiki_audit.py --write-config-facts --json
# Release/current-head evidence artifact for the strict gate
py -3.13 execution/llm_wiki_audit.py --write-strict-release-evidence --json
# Surface the same evidence in the release authorization packet
py -3.13 .agents/skills/auto-research/scripts/release_authorization_packet.py --root . --output .tmp/release-authorization-packet.json --json
# Render the packet evidence as a GitHub reviewer summary/checklist
py -3.13 .agents/skills/auto-research/scripts/llm_wiki_release_summary.py --root . --packet .tmp/release-authorization-packet.json --output .tmp/llm-wiki-release-summary.md --artifact-dir release-evidence/llm-wiki --json
py -3.13 -m pytest workspace/tests/test_llm_wiki_audit.py --no-cov
```

### 현재 gate가 보는 것

| 검사 | 실패 기준 | 이유 |
|------|-----------|------|
| README 색인 | `NN-*.md` 페이지가 있는데 `README.md` index에 없음 | 새 페이지가 발견되지 않음 |
| 로컬 링크 | 상대 markdown 링크 대상이 없음 | 다음 작업자가 끊긴 문맥을 따라감 |
| 외부 출처 표시 | 외부 URL이 있는데 `## 출처` 또는 `공식:` 근거가 없음 | "어디서 확인했는지"가 사라짐 |
| 외부 검증일 | 외부 URL이 있는데 `외부 자료 검증일: YYYY-MM-DD`가 없음 | 시간 민감한 정보의 나이를 판단할 수 없음 |
| 외부 검증일 age | 기본 120일 초과 | 모델·가격·API 문서는 분기 단위로 흔들림 |
| source inventory | markdown URL과 `source-inventory.json`의 URL/page/review 기한이 다름 | 재검증 대상 목록이 문서와 표류 |
| code facts manifest | Python 코드와 `code-facts.json`의 schema/facts/checks가 다름 | provider 순서, default model, 함수/클래스 이름이 문서와 표류 |
| config facts manifest | tracked YAML config/runtime wiring과 `config-facts.json`의 schema/facts/checks가 다름 | config provider 순서, default model, pricing coverage, runtime helper coverage가 문서와 표류 |

### 보지 않는 것

- 외부 URL HTTP 생존 여부. 네트워크, 403, 지역 제한이 있어 감사 도구는 로컬 일관성만 본다.
- 외부 문서 내용의 최신성. 가격·모델·폐기일·API 파라미터를 바꾸기 전에는 반드시 웹으로 공식 문서를 다시 확인한다.
- 문서의 의미적 정확성. Python literal 코드 사실(`DEFAULT_PROVIDER_ORDER`, `DEFAULT_MODELS`, 함수/클래스 이름 등)은 `code-facts.json` drift로, tracked YAML config 사실은 `config-facts.json` drift로 확인하지만, 문장 의미와 file\:line 설명은 작업자가 실제 파일/공식 문서를 읽어 확인해야 한다.

## A/B — 수동 리뷰 vs 감사 도구

| 기준 | A. 수동 wiki 리뷰만 | B. 감사 도구 + 수동 의미 검증 |
|------|--------------------|-------------------------------|
| 링크/색인 회귀 | 놓치기 쉬움 | 자동 fail |
| 외부 출처·검증일 | 작업자 습관에 의존 | 자동 fail |
| provider API 의미 | 사람이 판단 | 사람이 판단 |
| 실행 비용 | 낮음 | 낮음(로컬 파일만 읽음) |
| 신뢰도 | 편집자마다 흔들림 | 구조적 회귀는 고정, 의미는 수동 |

**권장:** B. `llm_wiki_audit.py`를 wiki 변경의 기본 gate로 두고, 의미 판단은 기존 auto-research 루프처럼 공식 문서/코드 근거로 보강한다.

## A/B: strict artifact only vs release packet integration

| 기준 | A. `.tmp/llm-wiki-strict-audit-current.json`만 생성 | B. release packet + launch audit에서 소비 |
|------|------------------------------------------------------|------------------------------------------|
| 리뷰어 가시성 | artifact를 직접 열어야 함 | packet summary와 completion manifest에 status/head/unexpected count가 보임 |
| current HEAD 검증 | artifact 내부 값에 의존 | packet이 현재 HEAD와 비교해 mismatch를 blocker로 표시 |
| 실패 전파 | strict audit exit/status를 따로 해석 | missing/fail/head mismatch가 release blocker로 승격 |
| GitHub Actions 표면 | upload artifact로 보존 가능 | artifact 보존 + `GITHUB_STEP_SUMMARY` 요약으로 리뷰 가능 |

**권장:** B. artifact는 원본 증거로 보존하고, `release_authorization_packet.py`와 `launch_objective_audit.py`가 같은 evidence를 요약해야 release 리뷰어가 current-head LLM Wiki gate를 놓치지 않는다.

## A/B: manual job-summary echo vs helper-generated checklist

| Criterion | A. Manually echo packet fields in YAML | B. Generate summary from the release packet |
|-----------|----------------------------------------|--------------------------------------------|
| Field drift | Easy to forget new packet keys | Helper reads the same `llm_wiki_strict_evidence` object used by release authorization |
| Reviewer clarity | Free-form text varies by workflow author | Stable Markdown table plus checklist |
| Artifact safety | Direct `.tmp/...` upload can be skipped by current hidden-file defaults | Helper can copy JSON and Markdown into `release-evidence/llm-wiki` |
| CI portability | Shell-specific quoting is repeated in every workflow | Python CLI works locally and in GitHub Actions |

**Decision:** use B. `llm_wiki_release_summary.py` renders the release packet into Markdown, appends to `GITHUB_STEP_SUMMARY` when available, and prepares a visible artifact directory for `actions/upload-artifact@v7`.

T-1594 locks this workflow contract inside `llm_wiki_audit.py`: docs that mention the release-summary path must keep `llm_wiki_release_summary.py`, `GITHUB_STEP_SUMMARY`, `release-evidence/llm-wiki`, and `actions/upload-artifact@v7` visible, and the audit fails stale `upload-artifact` versions, direct `.tmp` upload paths, or manual `GITHUB_STEP_SUMMARY` shell echo examples.

## 최신성 재검증 절차

1. `py -3.13 execution/llm_wiki_audit.py --json`로 현재 로컬 구조가 깨지지 않았는지 본다.
2. 변경하려는 페이지가 외부 사실을 다루면 공식 문서를 연다. 예: [02](02-providers.md)는 provider models/pricing/rate limits, [10](10-structured-outputs.md)은 structured output API, [11](11-reasoning-models.md)은 reasoning/thinking API, [13](13-model-selection.md)은 deprecation/retirement.
3. 공식 문서에서 확인한 사실만 반영한다. 날짜·모델 ID·가격·지원 여부가 불명확하면 **불확실**로 적고, 추정으로 migration 권고를 확정하지 않는다.
4. `외부 자료 검증일`을 갱신하고, 출처 섹션에 공식 URL을 남긴다.
5. 코드 사실을 바꿨다면 관련 파일을 다시 읽고 file\:line 또는 함수명을 갱신한 뒤 `--write-code-facts`로 manifest drift를 해소한다.
6. tracked YAML config 사실이나 provider runtime helper/model coverage를 바꿨다면 `--write-config-facts`로 manifest drift를 해소한다. 비밀값을 담을 수 있는 로컬 `projects/blind-to-x/config.yaml`은 기준 manifest에 넣지 않는다.
7. 텍스트 감사 출력의 `audit warnings`와 `manifest warnings`를 구분해서 본다. JSON을 쓰는 자동화는 `summary.manifest_check_warning_count`, `summary.config_fact_check_status_counts`, `summary.manifest_check_warning_classification_counts`, `summary.manifest_check_unexpected_warning_count`, `summary.manifest_check_warnings`를 함께 본다. Manifest 경고는 기본 non-failing policy로 유지하지만, `accepted_known`은 기록된 runtime wiring debt이고 `unexpected`는 새 drift로 검토한다.
8. 릴리스 전/CI 성격의 검증은 `py -3.13 execution/llm_wiki_audit.py --strict-manifest-warnings --json`을 추가로 실행해 unexpected manifest warning을 실패로 승격한다.
9. focused test와 감사 도구를 다시 실행한다.

## 공식 출처 우선순위

| 주제 | 1차 출처 |
|------|----------|
| OpenAI structured outputs | <https://developers.openai.com/api/docs/guides/structured-outputs> |
| Anthropic structured outputs | <https://platform.claude.com/docs/en/build-with-claude/structured-outputs> |
| Gemini structured outputs | <https://ai.google.dev/gemini-api/docs/structured-output> |
| LLM 보안 기준 | <https://genai.owasp.org/llm-top-10/> |
| release/current-head evidence artifact | <https://docs.github.com/en/actions/concepts/workflows-and-actions/workflow-artifacts>, <https://github.com/actions/upload-artifact> |
| release reviewer summary | <https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-commands> |
| provider 모델·가격·한도 | 각 provider 공식 models/pricing/rate-limit 페이지([02](02-providers.md)) |

## 이번 사이클의 적용 범위

- 새 감사 도구와 테스트를 추가해 wiki의 **형식·링크·출처 freshness**를 검증 가능하게 했다.
- product code는 변경하지 않았다.
- 외부 문서 내용 자체의 최신성은 감사 도구가 아니라 auto-research 단계의 웹 확인으로 유지한다.

## 지뢰밭

- `http://127.0.0.1` 같은 로컬 예시는 외부 출처가 아니다. 감사 도구는 fenced code와 localhost URL을 source freshness 요구에서 제외한다.
- 외부 URL을 본문에 직접 쓰면 출처·검증일 요구가 걸린다. 의도한 외부 근거라면 좋고, 단순 예시라면 code fence 안에 넣어라.
- README 색인을 빼먹으면 새 페이지가 존재해도 실패한다. 페이지 추가 시 README를 먼저 갱신한다.
- 이 gate가 pass여도 "모델 가격이 최신"이라는 뜻은 아니다. pass는 **문서 구조가 검증 가능한 상태**라는 뜻이다.

## 출처 (1차 우선, 2026-06-08 확인)

- OpenAI, *Structured model outputs*: <https://developers.openai.com/api/docs/guides/structured-outputs>
- Anthropic, *Structured outputs*: <https://platform.claude.com/docs/en/build-with-claude/structured-outputs>
- Google, *Gemini structured outputs*: <https://ai.google.dev/gemini-api/docs/structured-output>
- OWASP, *2025 Top 10 Risk & Mitigations for LLMs and Gen AI Apps*: <https://genai.owasp.org/llm-top-10/>
- Python, *json standard library documentation*: <https://docs.python.org/3/library/json.html>
- Python, *argparse standard library documentation*: <https://docs.python.org/3/library/argparse.html>
- Python, *sys standard library documentation*: <https://docs.python.org/3/library/sys.html>
- Python, *warnings standard library documentation*: <https://docs.python.org/3/library/warnings.html>
- GitHub Docs, *Workflow artifacts*: <https://docs.github.com/en/actions/concepts/workflows-and-actions/workflow-artifacts>
- GitHub, *actions/upload-artifact*: <https://github.com/actions/upload-artifact>
- GitHub Docs, *Workflow commands / job summaries*: <https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-commands>
- 코드 근거: `execution/llm_wiki_audit.py`, `workspace/tests/test_llm_wiki_audit.py` (2026-06-08 현재 HEAD)

*외부 자료 검증일: 2026-06-08 · 코드 검증: 현재 HEAD*
