# 22 · Embeddings · Semantic Dedup · RAG Boundary

> 임베딩, semantic dedup, RAG 도입 경계를 분리해 보는 운영 문서.
> 코드 위치는 2026-06-08 현재 `projects/blind-to-x/pipeline/dedup.py`, `projects/shorts-maker-v2/src/shorts_maker_v2/providers/google_client.py`, `docs/wiki/llm/02-providers.md`, `docs/wiki/llm/08-security.md` 기준이다.

## 왜 따로 보나

임베딩은 텍스트 생성이 아니라 입력을 숫자 벡터로 바꾸는 경로다. 그래서 [01-architecture](01-architecture.md)의 생성용 `LLMClient` fallback, [03-cost-caching](03-cost-caching.md)의 생성 호출 비용, [21-token-budget-context](21-token-budget-context.md)의 출력 토큰 예산과 다른 장애면을 가진다.

현재 repo에는 production vector store나 사용자 질의형 RAG 서비스가 없다. 하지만 **임베딩 표면이 아예 없는 것도 아니다.** Blind-to-X는 Gemini 임베딩을 optional semantic dedup에 쓰고, Shorts Maker V2에는 Gemini multimodal embedding helper가 있다. 따라서 [08-security](08-security.md)의 LLM08은 "해당 없음"이 아니라 **제한적 표면 있음**으로 다뤄야 한다.

## 현재 구현 사실

| 범위 | 현재 동작 | 근거 |
|---|---|---|
| Blind-to-X semantic dedup | Gemini `models/gemini-embedding-001`로 title embedding을 계산하고 cosine similarity로 Jaccard가 놓친 중복을 보조 탐지 | `dedup.py` L115-L145, L253-L270 |
| Blind-to-X cache | `.tmp/embedding_cache.db` SQLite에 `text_hash` 기준 embedding JSON을 저장 | `dedup.py` L36-L96 |
| Blind-to-X key/fallback | `GOOGLE_API_KEY`가 없거나 embedding 호출이 실패하면 `None`을 반환하고 Jaccard fallback으로 계속 진행 | `dedup.py` L122-L138, L144-L151 |
| Blind-to-X Notion 후보 | Notion title 후보를 좁힌 뒤 `use_semantic=True`, `semantic_threshold=0.82`일 때 semantic second pass 수행 | `dedup.py` L190-L270 |
| Blind-to-X cross-source 후보 | datasketch `MinHashLSH`가 있으면 LSH/Jaccard를 먼저 쓰고, semantic second pass로 추가 중복을 찾음 | `dedup.py` L295-L376 |
| Blind-to-X quality gate | 최근 초안과의 `_max_semantic_similarity`가 0.70 이상이면 warning, 0.85 이상이면 fail | `quality_gate.py`, `test_output_quality_uplift.py` |
| Shorts Maker V2 helper | `GoogleClient.embed_content()`가 `gemini-embedding-2-preview` 기본값으로 text/image/audio embedding을 만들고 `compute_similarity()`가 cosine similarity를 계산 | `google_client.py` L167-L218 |
| Ollama local 후보 | `embeddinggemma:300m`은 로컬 RAG 임베딩 후보로 문서화되어 있으나 workspace 표준 vector store로 배선되어 있지 않음 | [02-providers](02-providers.md), [13-model-selection](13-model-selection.md) |
| Workspace core | 생성용 `LLMClient`에는 provider-neutral embedding API 추상화가 없음 | `workspace/execution/llm_client.py` 공개 경로 기준 |

현재 결론: **semantic dedup과 품질 측정에는 임베딩을 이미 쓰지만, corpus chunking, vector DB, retrieval evaluation, prompt augmentation까지 묶인 RAG 제품 경로는 없다.**

## 공식 기준

- OpenAI는 embedding을 float vector로 설명하고, 두 vector 사이의 distance가 relatedness를 나타낸다고 설명한다. 주 사용처는 search, clustering, recommendations, anomaly detection, diversity measurement, classification이다.
- Gemini API는 `embedContent`로 text embedding vector를 만들고, `SEMANTIC_SIMILARITY`, `RETRIEVAL_DOCUMENT`, `RETRIEVAL_QUERY`, `CLASSIFICATION`, `CLUSTERING`, `FACT_VERIFICATION` 같은 task type을 제공한다. Gemini embedding guide는 RAG를 embedding의 흔한 use case로 설명한다.
- Ollama는 `/api/embed`와 CLI로 local embedding을 만들 수 있고, embeddinggemma, qwen3-embedding, all-minilm을 추천한다. `/api/embed` 응답 vector는 L2-normalized라고 설명한다.
- Anthropic의 Claude API 문서는 Anthropic이 자체 embedding model을 제공하지 않으며, embedding provider 선택과 Voyage AI 사용을 안내한다.

## A/B 비교

| 기준 | A. 문자열/Jaccard dedup만 사용 | B. Managed embedding semantic dedup | C. Local embedding/RAG 후보 |
|---|---|---|---|
| 정확도 | 표현이 조금만 바뀌면 놓치기 쉬움 | 의미가 같은 제목/초안을 더 잘 잡음 | corpus 검색까지 확장 가능 |
| 비용/키 의존성 | 낮음, 외부 키 없음 | Gemini/OpenAI/Voyage 등 API key와 과금 필요 | 로컬 모델/스토리지/운영 비용 필요 |
| 개인정보/데이터 경계 | 외부 전송 없음 | 입력 텍스트가 provider로 전송됨 | 로컬 처리 가능하나 vector DB 보호 필요 |
| 지연/캐시 | 빠름 | embedding 호출 지연이 있어 cache 필요 | 모델 로드/검색 index 지연 관리 필요 |
| 실패 모드 | recall 낮음 | provider 장애, cache stale, threshold drift | chunking/poisoning/index freshness/retrieval 품질 문제 |
| 현재 repo 적합도 | baseline으로 필요 | **현재 채택된 선택**: Blind-to-X optional dedup | 별도 실험 후보. 아직 product RAG 아님 |

**현재 채택:** B를 제한적으로 쓴다. Blind-to-X는 `GOOGLE_API_KEY`가 있으면 semantic dedup을 보강하고, 실패하면 Jaccard로 계속 진행한다.

**보류:** C는 local/private RAG나 대규모 지식검색 요구가 생길 때 별도 실험으로 둔다. chunking, corpus ownership, freshness, vector poisoning, retrieval eval, privacy policy가 먼저 정의되어야 한다.

## 운영 절차

### 1. semantic dedup threshold를 바꾸기 전

1. `semantic_threshold=0.82`와 Jaccard threshold를 동시에 본다. 한쪽만 낮추면 중복 제거가 과해질 수 있다.
2. `projects/blind-to-x/tests/unit/test_dedup_extended.py`와 semantic similarity quality gate 테스트를 먼저 돌린다.
3. `GOOGLE_API_KEY`가 없는 환경에서도 fallback이 깨지지 않는지 확인한다.
4. `.tmp/embedding_cache.db`를 테스트/운영 판단의 단일 근거로 보지 않는다. cache hit는 모델 최신성이나 threshold 품질을 증명하지 않는다.

### 2. embedding cache가 의심될 때

1. 같은 제목인데 결과가 이상하면 cache stale, text normalization drift, 모델 변경, threshold 변경을 분리한다.
2. cache는 `.tmp/` 아래 재생성 가능한 중간 산출물로 본다. 필요하면 삭제 후 재생성할 수 있어야 한다.
3. cache 크기, TTL, 모델명 metadata가 필요해지는 순간에는 현재 단순 `text_hash -> embedding` 구조를 확장해야 한다.

### 3. RAG를 새로 붙이려면

RAG는 "embedding API 호출"만으로 끝나지 않는다. 최소한 다음 항목을 먼저 문서화하고 실험한다.

- corpus owner와 freshness: 어떤 문서를 누가 최신으로 유지하는가
- chunking 정책: chunk 크기, overlap, metadata, 삭제/수정 반영
- retrieval evaluation: 어떤 query set과 relevance metric으로 품질을 볼 것인가
- poisoning 방어: 외부 문서가 prompt context에 들어올 때 LLM01/LLM08을 함께 막는가
- privacy boundary: provider embedding으로 보낼 수 있는 text와 local-only text를 나누는가
- failure fallback: vector store가 없거나 비었을 때 generation을 막을지, keyword/Jaccard로 계속 갈지

## 지뢰밭

- "RAG를 안 쓴다"와 "임베딩을 안 쓴다"는 다르다. 현재 repo는 전자는 대체로 맞지만 후자는 틀리다.
- embedding vector는 원문이 아니어도 민감 정보 경계 밖으로 보내는 파생 데이터다. Blind-to-X title/body 계열 text를 provider로 보내는지 확인해야 한다.
- semantic dedup threshold는 product 품질값이다. 0.82를 provider/model 변경 후 그대로 유지하면 recall/precision이 흔들릴 수 있다.
- `.tmp/embedding_cache.db`에는 모델명/차원/TTL이 없다. 모델을 바꾸면 cache invalidation 정책이 필요하다.
- `embeddinggemma:300m`이 [02-providers](02-providers.md)에 있어도, 자동으로 local vector store나 RAG가 켜져 있다는 뜻은 아니다.
- LLM08은 prompt injection과 별개지만 RAG를 붙이는 순간 LLM01과 결합된다. 검색된 untrusted document가 prompt context가 되기 때문이다.

## 구현 후보 체크리스트

1. Blind-to-X embedding cache에 `model`, `dimension`, `created_at`, optional TTL/cleanup을 명시한다.
2. semantic dedup threshold 변경은 테스트 fixture와 A/B manifest로 precision/recall을 같이 남긴다.
3. `task_type="SEMANTIC_SIMILARITY"`를 Gemini 호출 config로 명시할지 실험한다. 현재 호출은 모델 기본값에 맡긴다.
4. provider-neutral embedding abstraction은 두 개 이상 product가 같은 semantic workflow를 공유할 때만 도입한다.
5. local RAG 실험은 `embeddinggemma` + 작은 corpus + retrieval eval부터 시작하고, 생성 prompt 연결은 마지막 단계로 둔다.
6. [08-security](08-security.md)의 LLM08 평가는 production vector store 유무가 아니라 실제 embedding/cache/retrieval 표면으로 업데이트한다.

## 출처

- 공식: OpenAI API Docs, *Vector embeddings*: <https://developers.openai.com/api/docs/guides/embeddings>
- 공식: OpenAI API Reference, *Create embeddings*: <https://developers.openai.com/api/docs/api-reference/embeddings/create>
- 공식: Google AI for Developers, *Embeddings guide*: <https://ai.google.dev/gemini-api/docs/embeddings>
- 공식: Google AI for Developers, *Embeddings API*: <https://ai.google.dev/api/embeddings>
- 공식: Ollama Docs, *Embeddings*: <https://docs.ollama.com/capabilities/embeddings>
- 공식: Ollama API Docs, *Generate embeddings*: <https://docs.ollama.com/api/embed>
- 공식: Claude API Docs, *Embeddings*: <https://platform.claude.com/docs/en/build-with-claude/embeddings>
- 코드 근거: `projects/blind-to-x/pipeline/dedup.py`, `projects/blind-to-x/pipeline/quality_gate.py`, `projects/shorts-maker-v2/src/shorts_maker_v2/providers/google_client.py`, `projects/shorts-maker-v2/src/shorts_maker_v2/config.py`

*외부 자료 검증일: 2026-06-08 · 코드 검증: 현재 HEAD*
