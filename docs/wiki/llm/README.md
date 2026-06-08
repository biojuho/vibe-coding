# LLM Wiki — Vibe Coding 워크스페이스

> 이 프로젝트가 **LLM을 어떻게 쓰는지** 한곳에 모은 지식 베이스다.
> 운영 절차(SOP)는 `workspace/directives/`에 있고, 이 위키는 그 위에서
> **전체 구조 + 검증된 외부 레퍼런스 + 작업 플레이북**을 제공한다.
>
> - 코드 사실(file\:line)은 2026-06-08 기준 `workspace/execution/llm_client.py` 등 실제 소스에서 검증했다.
> - 외부 프로바이더 데이터(모델/가격/한도)는 2026-06-08에 공식 문서를 웹으로 확인했다. 가격은 수시로 바뀌므로 **과금 직전 공식 페이지 재확인**이 원칙이다.

## 한 줄 요약

워크스페이스의 모든 LLM 호출은 **`execution.llm_client.LLMClient`** (9-프로바이더 비용효율 순 자동 fallback)을 통하는 것이 표준이다. 한국어 자동화 파이프라인은 `*_bridged` 변형을 쓰고, 비용·캐싱·관측·평가는 별도 계층으로 분리돼 있다.

## 색인

| # | 페이지 | 내용 |
|---|--------|------|
| 01 | [아키텍처](01-architecture.md) | 9-프로바이더 fallback, `LLMClient` 호출 흐름, 언어 브릿지, 2종 캐시, 3개 로깅 싱크 |
| 02 | [프로바이더 레퍼런스](02-providers.md) | 9개 프로바이더의 **검증된** 모델·가격·한도·공식 문서 표 + 노후 default 모델 정비 권고 |
| 03 | [비용 · 캐싱](03-cost-caching.md) | 로컬 응답 캐시 vs Anthropic 프롬프트 캐시, 비용 가중치, 비용 DB, 이상 알림, 예산 |
| 04 | [관측 (Langfuse)](04-observability.md) | Langfuse v3 셀프호스트, opt-in, 5단계 preflight |
| 05 | [품질 평가 (promptfoo)](05-eval.md) | 골든/부정셋 회귀 평가, 주간 실행, judge 모델 |
| 06 | [프로젝트별 라우터](06-per-project.md) | workspace `LLMClient` vs shorts-maker-v2 `LLMRouter` vs blind-to-x async |
| 07 | [플레이북](07-playbooks.md) | "LLM 기능 추가/디버깅/비용 절감" 등 자주 하는 작업 단계 |
| 08 | [보안](08-security.md) | OWASP LLM Top 10(2025) 매핑, 프롬프트 인젝션 표면, 시크릿/PII, 출력 처리, A/B 완화 비교 |
| 09 | [에이전트 하네스](09-agent-harness.md) | `harness_*` 6모듈(도구권한·샌드박스·예산/루프·컨텍스트압축·생성-평가), ADR-025, 구현됐으나 미배선 |
| 10 | [구조화 출력](10-structured-outputs.md) | JSON 강제 3단계, provider별 실태(tier 0~1), 스키마 강제 업그레이드 A/B, 실패 모드 |
| 11 | [추론/사고](11-reasoning-models.md) | 프로바이더 네이티브 thinking(adaptive/effort/level) vs repo 오케스트레이션 추론(분해·검증·반증) |
| 12 | [기능 인벤토리](12-llm-features.md) | `LLMClient` 소비처 전수(생성·추론·하네스), caller_script 라벨, "AI"인데 LLM 미배선인 것 |
| 13 | [모델 선택·폐기 캘린더](13-model-selection.md) | 작업→모델 결정표, 확정 폐기 일정과 노후화 리스크 분리, repo 핀한 노후 ID |
| 14 | [유지보수·검증 게이트](14-maintenance-verification.md) | README 색인, 로컬 링크, 외부 출처, 검증일 freshness를 감사하는 deterministic gate |
| 15 | [외부 출처 인벤토리](15-source-inventory.md) | wiki 외부 URL, 사용 페이지, volatility, 재검증 기한을 한 manifest로 추적 |
| 16 | [코드 사실 manifest](16-code-facts.md) | `LLMClient`, provider 순서, default model, 함수/클래스 이름 drift를 AST 기반 manifest로 추적 |
| 17 | [Config 사실 manifest](17-config-facts.md) | tracked YAML config의 provider 순서, default model, pricing coverage drift를 추적 |
| 18 | [Runtime wiring checks](18-runtime-wiring-checks.md) | config provider 목록과 runtime helper/model coverage의 cross-manifest gap을 추적 |
| 19 | [Objective loop audit](19-objective-loop-audit.md) | 사용자의 자율 보강 루프 프롬프트를 completion-audit manifest로 매핑 |
| 20 | [Rate limit · retry · reliability](20-rate-limit-reliability.md) | 429/Retry-After, provider bucket, retry/backoff/fallback, circuit-breaker gap의 운영 기준 |
| 21 | [Token budget · context window](21-token-budget-context.md) | pre-call token budget, context/output cap, post-call usage와 preflight gap의 운영 기준 |
| 22 | [Embeddings · semantic dedup · RAG boundary](22-embeddings-rag-dedup.md) | Gemini/Ollama/OpenAI/Voyage embedding 기준, Blind-to-X semantic dedup, RAG 미도입 경계 |
| 23 | [Tool calling · function calling · harness boundary](23-tool-calling-harness-boundary.md) | provider-native tool/function calling, Gemini Search Grounding, MCP, local ToolRegistry/HITL 경계 |
| 24 | [Batch · async · latency · concurrency boundary](24-batch-async-latency.md) | Provider Batch API, repo-local async fallback, streaming, timeout/race/concurrency 경계 |
| 25 | [Multimodal · vision · audio · media boundary](25-multimodal-audio-media-boundary.md) | Vision input, image generation, TTS/STT, video generation, local rendering 경계 |
| 26 | [Prompt provenance · versioning · cache/eval contract](26-prompt-provenance-versioning.md) | Prompt template identity, rendered prompt hashes, cache invalidation, eval evidence 경계 |
| 27 | [Data retention · privacy · logging boundary](27-data-retention-privacy-logging.md) | Provider retention controls, local caches/logs, Langfuse, product artifact privacy 경계 |
| 28 | [Grounding · citation · source attribution boundary](28-grounding-citation-source-attribution.md) | Provider Search/File/URL citations, app-owned source attribution, fact-check evidence 경계 |
| 29 | [Error taxonomy · refusal · fallback boundary](29-error-taxonomy-refusal-fallback-boundary.md) | Provider/API errors, model refusals, structured-output failures, product gates, retry/fallback routing 경계 |
| 30 | [Fine-tuning · custom model · local scorer boundary](30-fine-tuning-custom-model-boundary.md) | Provider fine-tuning, managed agents, prompt/RAG/eval, Blind-to-X local ML scorer 경계 |
| 31 | [Generation parameters · reproducibility · replay boundary](31-generation-parameters-reproducibility.md) | Temperature/top-p/top-k/output caps/seed, retries, fallback, cache, and eval replay evidence 경계 |
| 32 | [Safety · moderation · publish gate boundary](32-safety-moderation-publish-gates.md) | Provider safety, LLM moderation, product quality, platform policy, and human approval 경계 |
| 33 | [Computer use · browser QA boundary](33-computer-use-browser-qa-boundary.md) | Provider computer-use agents, deterministic Playwright QA, source probes, and retained screenshot evidence 경계 |
| 34 | [Language bridge - locale - i18n boundary](34-language-bridge-locale-i18n-boundary.md) | Korean bridge validation, BCP-47 locale tags, Shorts locale packs, TTS locale, and language evidence boundary |
| 35 | [Local inference - hardware - quantization boundary](35-local-inference-hardware-quantization-boundary.md) | Ollama server/model health, hardware fit, quantization, OpenAI-compatible API, privacy, and cloud fallback boundary |
| 36 | [Evaluation dataset - LLM judge - rubric boundary](36-evaluation-dataset-llm-judge-rubric-boundary.md) | Promptfoo datasets, deterministic assertions, LLM-as-judge rubrics, baselines, runtime evaluators, and human review boundary |
| 37 | [API surface - SDK compatibility - OpenAI-compatible boundary](37-api-surface-sdk-compatibility-boundary.md) | Chat Completions, Responses, Anthropic Messages, Gemini GenerateContent, OpenAI-compatible adapters, parser shape, and SDK compatibility boundary |
| 38 | [Conversation state - memory - handoff boundary](38-conversation-state-memory-handoff-boundary.md) | Provider conversation state, SDK sessions, LangGraph checkpoints, MCP context, `.ai` handoff, `.tmp` evidence, and product state boundary |
| 39 | [Credentials - secrets - API key boundary](39-credentials-secrets-api-key-boundary.md) | Provider keys, CI secrets, OAuth tokens, Supabase/Postgres URLs, browser-public keys, redacted readiness artifacts, and live side-effect authorization boundary |
| 40 | [Side effect - idempotency - replay boundary](40-side-effect-idempotency-replay-boundary.md) | Notion/X/Cloudinary live writes, operation keys, retry-safe side effects, provider idempotency, and replay recovery boundary |

## 빠른 시작

```python
# 워크스페이스 내부(execution/)에서 — 표준 사용법
from execution.llm_client import LLMClient

client = LLMClient()                       # 비용효율 순 기본 우선순위
data = client.generate_json(system_prompt="...", user_prompt="...")
text = client.generate_text(system_prompt="...", user_prompt="...")

# 한국어 출력 강제가 필요한 자동화 파이프라인
safe = client.generate_json_bridged(system_prompt="...", user_prompt="...")
```

```bash
# 프로바이더 연결/키 상태 점검 (실제 API 호출)
py -3.13 workspace/execution/llm_client.py test
py -3.13 workspace/execution/llm_client.py status        # API 호출 없이 키/모델/순서만

# 사용량·비용 요약 (JSONL + SQLite 병합, 기본 최근 7일)
py -3.13 workspace/execution/llm_usage_summary.py
# 비용/폴백/dead-provider 이상 알림 (cron/n8n용, 알림 있으면 exit 1)
py -3.13 workspace/execution/api_usage_tracker.py alerts
# rate limit/retry/fallback 장애 대응 기준
py -3.13 workspace/execution/api_usage_tracker.py alerts --expected-providers google,deepseek,openai,anthropic
py -3.13 workspace/execution/llm_usage_summary.py --by provider
# 위키 구조/출처 freshness 감사 (외부 HTTP 호출 없음)
py -3.13 execution/llm_wiki_audit.py --json
# 사용자 프롬프트 요구사항 ↔ repo evidence 매핑 manifest 생성
py -3.13 execution/llm_wiki_objective_audit.py --output .tmp/llm-wiki-objective-audit-current.json --json
py -3.13 .agents/skills/auto-research/scripts/completion_audit.py .tmp/llm-wiki-objective-audit-current.json --json --allow-incomplete
# CI/strict: accepted_known은 허용하되 unexpected manifest warning은 실패
py -3.13 execution/llm_wiki_audit.py --strict-manifest-warnings --json
# Release/current-head evidence artifact for the same strict gate
py -3.13 execution/llm_wiki_audit.py --write-strict-release-evidence --json
# Reviewer-visible release summary/checklist from the release packet
py -3.13 .agents/skills/auto-research/scripts/llm_wiki_release_summary.py --root . --packet .tmp/release-authorization-packet.json --output .tmp/llm-wiki-release-summary.md --artifact-dir release-evidence/llm-wiki --json
# markdown URL에서 source-inventory.json 재생성 후 감사
py -3.13 execution/llm_wiki_audit.py --write-source-inventory --json
# Python 코드 사실에서 code-facts.json 재생성 후 감사
py -3.13 execution/llm_wiki_audit.py --write-code-facts --json
# tracked YAML config 사실과 runtime wiring check에서 config-facts.json 재생성 후 감사
py -3.13 execution/llm_wiki_audit.py --write-config-facts --json
```

감사 결과의 `summary.status`가 `pass`여도 manifest warning을 함께 확인한다. 텍스트 출력은 `audit warnings`와 `manifest warnings`를 분리해서 보여주고, JSON 출력은 `summary.manifest_check_warning_count`, `summary.manifest_check_warning_classification_counts`, `summary.manifest_check_unexpected_warning_count`, `summary.manifest_check_warnings`를 제공한다. `accepted_known` manifest warning은 기록된 config/runtime wiring debt이고, `unexpected` warning은 새 drift로 검토해야 한다. 기본 로컬 감사에서는 둘 다 non-failing이지만, CI나 릴리스 전 검증에서는 `--strict-manifest-warnings`로 unexpected warning을 exit 1로 승격한다.

`--write-strict-release-evidence`는 같은 strict gate를 실행하면서 `.tmp/llm-wiki-strict-audit-current.json`을 쓴다. GitHub Actions에서는 이 파일을 workflow artifact로 업로드해 current-head release evidence로 남긴다. GitHub 공식 문서는 artifacts를 workflow run이 만든 파일을 job 완료 후에도 보존·공유하는 용도로 설명하고, `actions/upload-artifact`는 `name`, `path`, `retention-days`, digest output을 제공한다.

이 artifact는 auto-research release surface에도 연결된다. `.agents/skills/auto-research/scripts/release_authorization_packet.py`는 `llm_wiki_strict_evidence` 섹션에 artifact status, current HEAD 일치 여부, unexpected warning count, source inventory count를 요약하고, missing/fail/head mismatch를 release blocker로 남긴다. `.agents/skills/auto-research/scripts/launch_objective_audit.py`는 같은 packet 필드를 completion manifest evidence로 노출한다. GitHub Actions에서 사람이 바로 볼 요약이 필요하면 GitHub 공식 `GITHUB_STEP_SUMMARY` job summary에 packet의 `llm_wiki_strict_evidence` 요약을 추가하고, JSON 원본은 workflow artifact로 보존한다.

T-1593 adds a deterministic reviewer summary helper for that last step: `.agents/skills/auto-research/scripts/llm_wiki_release_summary.py` reads `.tmp/release-authorization-packet.json`, writes a Markdown checklist, appends it to `GITHUB_STEP_SUMMARY` when available, and can copy the raw strict JSON plus Markdown summary into `release-evidence/llm-wiki`. Prefer uploading that visible directory with `actions/upload-artifact@v7` instead of uploading `.tmp/...` directly, because the current upload-artifact defaults ignore hidden files and files inside dot-prefixed folders unless explicitly overridden.

## 관련 운영 SOP (workspace/directives/)

이 위키는 아래 SOP를 **대체하지 않고 묶는다**. 절차 세부는 각 directive를 본다.

- [`llm_fallback.md`](../../../workspace/directives/llm_fallback.md) — fallback 체인 운영
- [`local_inference.md`](../../../workspace/directives/local_inference.md) — Ollama 로컬 추론 + SmartRouter/Reasoning
- [`deepseek_ko_bridge.md`](../../../workspace/directives/deepseek_ko_bridge.md) — 한국어 브릿지가 필요한 이유
- [`anthropic_prompt_caching.md`](../../../workspace/directives/anthropic_prompt_caching.md) — 프롬프트 캐싱 비용 절감
- [`llm_observability_langfuse.md`](../../../workspace/directives/llm_observability_langfuse.md) — Langfuse 관측
- [`llm_eval_promptfoo.md`](../../../workspace/directives/llm_eval_promptfoo.md) — promptfoo 회귀 평가
- [`api_monitoring.md`](../../../workspace/directives/api_monitoring.md) — API 사용량/헬스체크

## 핵심 코드 위치

| 역할 | 파일 |
|------|------|
| 통합 클라이언트(표준) | `workspace/execution/llm_client.py` |
| 언어 브릿지 정책 | `workspace/execution/language_bridge.py` |
| 사용량/비용 추적 | `workspace/execution/api_usage_tracker.py` |
| JSONL 메트릭 | `workspace/execution/llm_metrics.py` |
| 사용량 리포터 | `workspace/execution/llm_usage_summary.py` |
| Langfuse preflight | `execution/langfuse_preflight.py` (루트 execution) |
| Shorts 전용 라우터 | `projects/shorts-maker-v2/src/shorts_maker_v2/providers/llm_router.py` |
| blind-to-x async 생성 | `projects/blind-to-x/pipeline/draft_generator.py`, `draft_providers.py` |
| promptfoo 평가 러너 | `execution/run_eval_blind_to_x.py` (루트 execution) |

> ⚠️ 디렉터리 2개 주의: LLM **코어**(`llm_client.py`/`api_usage_tracker.py`/`language_bridge.py`/`llm_metrics.py`/`llm_usage_summary.py`)는 **`workspace/execution/`**에, **eval·preflight**(`run_eval_blind_to_x.py`/`blind_to_x_eval_extract.py`/`ai_batch_runner.py`/`langfuse_preflight.py`)는 **루트 `execution/`**에 있다. 둘은 서로 다른 폴더다.

## 이 위키 유지보수

- 코드가 바뀌면(프로바이더 추가, default 모델 변경, 비용 가중치 조정) 해당 페이지의 **file\:line 인용과 표를 갱신**한다.
- 외부 프로바이더 데이터는 분기마다 또는 과금 영향이 큰 작업 전에 [02-providers](02-providers.md)의 "재검증" 절차로 갱신한다.
- 외부 URL을 추가·삭제하면 `source-inventory.json`도 `--write-source-inventory`로 재생성하고 audit drift가 없는지 확인한다.
- provider 순서, default model, `LLMClient`/`LLMRouter`/`draft_providers.py` 사실을 바꾸면 `code-facts.json`도 `--write-code-facts`로 재생성하고 관련 문장을 재검토한다.
- tracked YAML config의 provider 순서, default model, pricing coverage, runtime wiring coverage를 바꾸면 `config-facts.json`도 `--write-config-facts`로 재생성하고 관련 문장을 재검토한다.
- 큰 사실 변경은 `.ai/SESSION_LOG.md`에 기록하고, 메모리 인덱스(`MEMORY.md`)와 충돌하면 메모리를 갱신한다.

*최종 작성: 2026-06-08 · 코드 검증 기준 커밋: `f94a25e9` 계열 현재 HEAD*
*확장(자율 보강 루프, 2026-06-08): 08-보안 · 09-에이전트 하네스 · 10-구조화 출력 · 11-추론/사고 · 12-기능 인벤토리 · 13-모델 선택·폐기 캘린더 · 14-유지보수·검증 게이트 · 15-외부 출처 인벤토리 · 20-rate-limit/retry/reliability · 21-token-budget/context · 22-embedding/semantic-dedup/RAG-boundary · 23-tool/function-calling/harness-boundary · 24-batch/async/latency/concurrency-boundary · 25-multimodal/vision/audio/media-boundary · 26-prompt-provenance/versioning/cache-eval-contract · 27-data-retention/privacy/logging-boundary · 28-grounding/citation/source-attribution-boundary · 29-error/refusal/fallback-taxonomy · 30-fine-tuning/custom-model/local-scorer-boundary · 35-local-inference/hardware/quantization-boundary · 36-evaluation-dataset/LLM-judge/rubric-boundary · 37-api-surface/SDK-compatibility/OpenAI-compatible-boundary · 38-conversation-state/memory/handoff-boundary 추가. 외부 1차 출처(OWASP LLM Top 10 2025, Anthropic agent/context/prompt/eval/state 엔지니어링, OpenAI/Gemini/Anthropic 구조화·추론/tool/batch/streaming/multimodal/media/prompt/data-retention/search/file/document citation/API/evals/conversation-state, fine-tuning/model-optimization API, Groq Batch API, MCP spec, 모델 폐기/노후화 일정, OpenAI/Anthropic/Gemini rate limit/token count/model limits, RFC 429/Retry-After, OpenAI/Gemini/Ollama/Claude embedding docs, Ollama local inference/model state docs, Hugging Face quantization docs, Promptfoo eval/prompt config/model-graded docs, Langfuse retention/masking docs, LangGraph persistence docs, provider API surface/SDK compatibility docs) + 코드 재검증 기반.*
