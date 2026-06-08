# 02 · 프로바이더 레퍼런스 (외부 검증 자료)

> 9개 프로바이더의 모델·가격·한도. **2026-06-08에 각 사 공식 문서를 웹으로 확인**했다.
> 가격/모델은 자주 바뀌므로, 과금에 영향 있는 작업 전에는 "재검증 절차"로 공식 페이지를 다시 본다.
> 신뢰도(conf)는 수집 당시 출처의 공식성·최신성 기준.

## ⚠️ 노후 default 모델 정비 권고 (가장 중요)

코드의 `DEFAULT_MODELS`([01-architecture](01-architecture.md))가 가리키는 모델 중 **4개는 이미 레거시/별칭**으로 바뀌었다. 동작은 하지만 의도와 다르게 라우팅되거나 곧 폐기된다.

| provider | 현재 default | 상태 | 권고 |
|----------|--------------|------|------|
| openai | `gpt-4o-mini` | 레거시(메인 가격표에서 빠짐). GPT-5.x 세대가 현행 | `gpt-5.4-mini`(균형) 또는 `gpt-5.4-nano`(최저가)로 이전 검토 |
| xai | `grok-3-mini-fast` | **독립 문서/가격 사라짐**. `grok-4.3`로 resolve되는 별칭으로 추정 → grok-4.3 요율($1.25/$2.50)로 과금될 가능성 | 명시적 `grok-4.3`(또는 코딩용 `grok-build-0.1`)으로 핀 |
| deepseek | `deepseek-chat` | `deepseek-v4-flash`(비사고 모드)로 라우팅되는 호환 별칭. **2026-07-24 폐기 예정** | `deepseek-v4-flash`로 이전 |
| moonshot | `moonshot-v1-8k` | 구세대(아직 서비스됨). Kimi K2 계열이 현행 | 유지 가능하나 `kimi-k2.5`/`kimi-k2.6`(자동 캐싱) 고려 |
| google | `gemini-2.5-flash` | ✅ 여전히 현행/안정 | 유지 OK (Gemini 3.x도 존재) |
| anthropic | `claude-sonnet-4-6` | ✅ 현행/활성 ($3/$15, 1M ctx) | 유지 OK |
| zhipuai | `glm-4-flash` | ✅ 무료 `glm-4-flash-250414`로 resolve | 유지 OK (무료 업그레이드: `glm-4.5-flash`/`glm-4.7-flash`) |
| groq | `llama-3.3-70b-versatile` | ✅ 현행 production (131K ctx) | 유지 OK |
| ollama | `qwen3-coder:30b-a3b-q4_K_M` | ✅ 실재 태그(~22GB VRAM) | 유지하되 **이 PC에선 무거움** → 가벼운 모델 |

> 모델 ID만 바꾸면 되는 일은 [07-playbooks](07-playbooks.md)의 "default 모델 이전" 참고. 다만 `LLMClient`/`LLMRouter`/blind-to-x config 3곳을 함께 봐야 한다([06-per-project](06-per-project.md)).

---

## 가격 표기 규칙

- 별도 표기 없으면 **per 1M tokens**, **USD**.
- Moonshot(.cn 엔드포인트)·ZhipuAI는 **CNY(¥)**로 표기 — 코드가 중국 본토 엔드포인트를 호출하기 때문.
- "cache-hit/cached input"은 프롬프트 캐시 적중 시의 입력 단가.

---

## Anthropic (Claude) · conf=high

- base: `https://api.anthropic.com` · repo default: `claude-sonnet-4-6` ✅현행
- 공식: [models](https://platform.claude.com/docs/en/about-claude/models/overview) · [pricing](https://platform.claude.com/docs/en/about-claude/pricing) · [rate-limits](https://platform.claude.com/docs/en/api/rate-limits)

| 모델 | context | 입력 | 출력 | 비고 |
|------|---------|------|------|------|
| `claude-opus-4-8` | 1M (128k out) | 5.00 | 25.00 | 최상위. cache read $0.50, Batch $2.50/$12.50 |
| `claude-sonnet-4-6` | 1M (64k out) | 3.00 | 15.00 | **repo default**. 5m write $3.75, 1h write $6, cache read $0.30, Batch $1.50/$7.50 |
| `claude-haiku-4-5` | 200k (64k out) | 1.00 | 5.00 | 최속. cache read $0.10, Batch $0.50/$2.50 |

- 프롬프트 캐시 배수(입력 대비): 5분 write ×1.25, 1시간 write ×2.0, read ×0.10. Batch API는 입출력 −50%. **스택 가능**.
- 1M 컨텍스트(Opus 4.x/Sonnet 4.6)는 **롱컨텍스트 추가요금 없이** 표준 단가.
- 한도: 사용량 Tier 1–4(누적 결제로 자동 상향). cache-read 입력 토큰은 ITPM에 미포함. 429에 retry-after 헤더(SDK 자동 재시도).
- 무료 tier 없음(신규 소액 크레딧만).
- 주의: Opus 4.7+ 새 토크나이저는 동일 텍스트에 최대 ~35% 더 많은 토큰. `inference_geo='us'`는 1.1× 가산.

## OpenAI (GPT) · conf=high

- base: `https://api.openai.com/v1` · repo default: `gpt-4o-mini` ⚠️레거시
- 공식: [models](https://developers.openai.com/api/docs/models) · [pricing](https://developers.openai.com/api/docs/pricing) · [rate-limits](https://developers.openai.com/api/docs/guides/rate-limits)

| 모델 | context | 입력 | 출력 | 비고 |
|------|---------|------|------|------|
| `gpt-4o-mini` | 128k | 0.15 | 0.60 | **repo default**, 레거시. 메인 가격표에서 빠짐 |
| `gpt-5.4-nano` | 400k | 0.20 | 1.25 | 최저가 GPT-5.4급. cached in $0.02 |
| `gpt-5.4-mini` | 400k | 0.75 | 4.50 | 균형. cached in $0.075. **default 이전 1순위** |
| `gpt-5.4` | 1M | 2.50 | 15.00 | cached in $0.25 |
| `gpt-5.5` | 1.05M (128k out) | 5.00 | 30.00 | 현행 플래그십. cached in $0.50 |

- 한도: 누적 결제 기반 5-tier(Free~Tier5). RPM/TPM/RPD 등 먼저 도달한 임계 적용.
- cached input은 입력의 약 10%. Batch/Flex/Priority는 별도 요율.

## Google Gemini · conf=high

- base: `https://generativelanguage.googleapis.com` (Vertex AI와 별개) · repo default: `gemini-2.5-flash` ✅현행
- 공식: [models](https://ai.google.dev/gemini-api/docs/models) · [pricing](https://ai.google.dev/gemini-api/docs/pricing) · [rate-limits](https://ai.google.dev/gemini-api/docs/rate-limits)

| 모델 | context(in/out) | 입력 | 출력 | 비고 |
|------|------|------|------|------|
| `gemini-2.5-flash-lite` | 1.05M / 65k | 0.10 | 0.40 | 최저가/최속 멀티모달 |
| `gemini-2.5-flash` | 1.05M / 65k | 0.30 | 2.50 | **repo default**. 가성비. audio 입력 $1.00 |
| `gemini-2.5-pro` | 1.05M / 65k | 1.25 / 2.50(>200k) | 10.00 / 15.00(>200k) | 고난도 추론. 200k 경계 티어드 |
| `gemini-3.5-flash` | 1.05M / 65k | 1.50 | 9.00 | 최신 안정 Flash(더 비쌈) |

- 무료 tier 있음(2.5 Flash/Pro/Flash-Lite). 정확한 RPM/TPM/RPD는 정적표가 사라지고 [AI Studio 대시보드](https://aistudio.google.com/rate-limit)로 안내. 4-tier(Free/T1/T2/T3) 자동 상향. Batch는 표준의 약 절반.
- 참고: Gemini 2.0 Flash는 2026-06-01 종료. 무료/저비용 이미지 생성은 blind-to-x에서 별도 사용(500/일).

## Groq · conf=high

- base: `https://api.groq.com/openai/v1` (OpenAI 호환) · repo default: `llama-3.3-70b-versatile` ✅현행
- 공식: [models](https://console.groq.com/docs/models) · [pricing](https://groq.com/pricing) · [rate-limits](https://console.groq.com/docs/rate-limits)

| 모델 | context | 입력 | 출력 | 비고 |
|------|---------|------|------|------|
| `llama-3.1-8b-instant` | 131k | 0.05 | 0.08 | 최저가/최속. 분류·라우팅 |
| `openai/gpt-oss-20b` | 131k | 0.075 | 0.30 | 최속 추론(~1000 TPS) |
| `openai/gpt-oss-120b` | 131k | 0.15 | 0.60 | 강한 오픈웨이트 추론(브라우저/코드 실행) |
| `llama-3.3-70b-versatile` | 131k (32k out) | 0.59 | 0.79 | **repo default**, production, ~394 TPS |

- 한도: 모델별 RPM/RPD/TPM/TPD. 무료 예: 70b = 30 RPM / 1,000 RPD / 12K TPM. 유료 Developer 플랜에서 상향 + Batch/Flex.
- Batch·프롬프트 캐시 각 ~50% 절감, 스택 가능. `qwen3-32b`/`llama-4-scout`/`kimi-k2`는 Preview(eval 전용, 예고 없이 폐기 가능).

## DeepSeek · conf=high

- base: `https://api.deepseek.com` (Anthropic 포맷은 `/anthropic`) · repo default: `deepseek-chat` ⚠️폐기예정
- 공식: [docs](https://api-docs.deepseek.com/) · [pricing](https://api-docs.deepseek.com/quick_start/pricing) · [rate-limit](https://api-docs.deepseek.com/quick_start/rate_limit)

| 모델 | context | 입력(miss) | 출력 | 비고 |
|------|---------|-----------|------|------|
| `deepseek-v4-flash` | 1M (384k out) | 0.14 | 0.28 | 현행 기본 저가. cache-hit 입력 $0.0028 |
| `deepseek-v4-pro` | 1M (384k out) | 0.435 | 0.87 | 고난도. concurrency 500 |
| `deepseek-chat` | 1M | = v4-flash | | **repo default**, 별칭. **2026-07-24 15:59 UTC 폐기** |

- 한도: RPM 대신 **동시성** 한도(v4-flash 2,500 / v4-pro 500). 초과 시 429. 무료 tier/크레딧 없음(선불 잔액).
- 주의: 비공식 블로그 가격(v4-pro $1.74/$3.48 등)은 공식과 충돌 → **공식 페이지만 신뢰**.

## xAI (Grok) · conf=medium

- base: `https://api.x.ai/v1` (OpenAI 호환) · repo default: `grok-3-mini-fast` ⚠️별칭화
- 공식: [models](https://docs.x.ai/developers/models)

| 모델 | context | 입력 | 출력 | 비고 |
|------|---------|------|------|------|
| `grok-build-0.1` | 256k | 1.00 | 2.00 | 저가 코딩 에이전트 |
| `grok-4.3` | 1M | 1.25 | 2.50 | 현행 플래그십. cached in $0.20. 별칭: grok-latest/grok-4 |

- ⚠️ `grok-3-mini-fast`는 더 이상 독립 문서/가격이 없고 `grok-4.3`로 resolve되는 것으로 보임 → grok-4.3 요율로 과금 추정. **별도 가격 행 없음(추측 금지)**.
- 한도: 누적 지출 기반 6-tier(2026-01-01부터). grok-4.3 ~1.8K RPM/10M TPM(T0) → ~10K RPM/85M TPM(T4). 모든 토큰 유형이 TPM 산입.
- conf=medium 이유: repo default가 독립 문서화 안 됨(별칭 추정), 마케팅 가격 페이지(x.ai/api)는 403으로 미수집 — 가격은 docs.x.ai만 출처.

## Moonshot AI (Kimi) · conf=high · **CNY(¥)**

- base: `https://api.moonshot.cn/v1` (OpenAI 호환) · repo default: `moonshot-v1-8k` (구세대, 서비스 중)
- 공식: [docs/pricing(chat-v1)](https://platform.kimi.com/docs/pricing/chat-v1) · [limits](https://platform.kimi.com/docs/pricing/limits) (platform.moonshot.cn → platform.kimi.com 301)

| 모델 | context | 입력 ¥ | 출력 ¥ | 비고 |
|------|---------|--------|--------|------|
| `moonshot-v1-8k` | 8k | 2.00 | 10.00 | **repo default**, 구세대 |
| `moonshot-v1-128k` | 131k | 10.00 | 30.00 | 장문 |
| `kimi-k2.5` | 262k | 4.00 | 21.00 | 멀티모달. cache-hit 입력 ¥0.70(자동 캐싱) |
| `kimi-k2.6` | 262k | 6.50 | 27.00 | 현행 플래그십. cache-hit 입력 ¥1.10 |

- ⚠️ **CNY 표기** — `.cn` 엔드포인트 기준. 국제판(api.moonshot.ai)은 USD·다른 숫자(여기 미포함).
- 한도: 누적 충전(¥) 기반 tier. 무료 Tier 0(¥0): 1 동시/3 RPM/500K TPM/1.5M TPD. ¥50+에서 Tier 1.

## ZhipuAI (GLM) · conf=medium · **CNY(¥)**

- base: `https://open.bigmodel.cn/api/paas/v4` (OpenAI 호환) · repo default: `glm-4-flash` ✅무료 resolve
- 공식: [models](https://docs.bigmodel.cn/cn/guide/start/model-overview) · [rate-limit](https://docs.bigmodel.cn/cn/api/rate-limit)

| 모델 | context | 입력 ¥ | 출력 ¥ | 비고 |
|------|---------|--------|--------|------|
| `glm-4-flash-250414` | 128k / 16k out | **0 (무료)** | **0** | **repo default**가 resolve되는 무료 모델 |
| `glm-4.5-flash` | 128k / 96k out | **0 (무료)** | **0** | 무료 업그레이드 |
| `glm-4.7-flash` | 200k / 128k out | **0 (무료)** | **0** | 최신 무료(30B), 에이전틱 코딩 강화 |
| `glm-4.6` | 200k / 128k out | (유료) | (유료) | 플래그십. 정확 단가는 JS 렌더 가격표라 미수집 |
| GLM-4.5 계열 | — | ~0.8(floor) | ~2(floor) | 공식 "최저" 표기. 변종별 정확치는 미수집 |

- 무료 모델 다수(`/free/` 경로). 한도: 공개 RPM/TPM 없음 — 콘솔 대시보드/사용자 등급 의존.
- conf=medium 이유: 유료 모델(glm-4.5/4.5-air/4.6) 정확 단가가 JS 렌더 페이지라 미수집 → 추측 대신 공란. 서드파티(OpenRouter USD) 수치는 미사용.

## Ollama (로컬) · conf=medium · 무료(셀프호스트)

- base: `http://localhost:11434` (`/v1`은 OpenAI 호환, 키는 무시됨) · repo default: `qwen3-coder:30b-a3b-q4_K_M`
- 공식: [openai-compat](https://docs.ollama.com/api/openai-compatibility) · [library](https://ollama.com/library)

| 모델 | context | 메모리 | 비고 |
|------|---------|--------|------|
| `gemma3` (4b) | 128k | ~4GB | 단순 코드/번역/요약. local_inference default |
| `gpt-oss:20b` | 128k | ~16GB | ~16GB 시스템용 범용 추론 |
| `qwen3-coder:30b-a3b-q4_K_M` | 256k(→1M) | **~22GB VRAM** | **repo default**. MoE 30B/활성 ~3.3B. 최고 로컬 코딩 |
| `embeddinggemma:300m` | 2k | CPU | 로컬 RAG 임베딩(`/v1/embeddings`) |

- 과금 없음(전기+하드웨어만). 한도 없음 — 하드웨어 한계. 동시성은 `OLLAMA_NUM_PARALLEL`/`OLLAMA_MAX_LOADED_MODELS`.
- 보안: 로컬 전용(11434 외부 노출 금지), 기본 인증 없음.
- **이 워크스테이션 현실**: repo default(~22GB VRAM)는 안 돎(Intel Iris Xe/15.75GB) → `gemma3:4b` 등으로 내리거나 ollama 비활성 수용. 자세히는 [local_inference.md](../../../workspace/directives/local_inference.md).

---

## 재검증 절차

가격/모델이 과금에 직접 영향을 줄 때:

1. 위 표의 공식 링크에서 **현재 가격표/모델 목록**을 연다(웹).
2. 변경분만 표에 반영하고, 본문 상단 날짜를 갱신한다.
3. 코드의 `DEFAULT_MODELS`/`PRICING`([01-architecture](01-architecture.md))이 노후됐으면 [07-playbooks](07-playbooks.md)의 "default 모델 이전" 수행.
4. 큰 변경은 `.ai/SESSION_LOG.md`에 기록.

> 라이브 모델 목록은 대부분 `GET {base}/models`로도 조회 가능(OpenAI 호환 프로바이더). Anthropic은 `GET /v1/models`.

*외부 자료 검증일: 2026-06-08*
