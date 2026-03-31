# Local Inference (Ollama) 운영 가이드

## 개요

**Self-Hosted 추론 엔진** — Ollama를 이용해 로컬에서 LLM 추론을 실행합니다.
상용 API 비용 없이 SIMPLE/MODERATE 쿼리를 처리하며, 기존 7개 클라우드 프로바이더의 fallback 체인과 통합됩니다.
또한 이 레이어는 단순 모델 호출만이 아니라, 추론 보강(`ReasoningEngine`)과 에이전트형 코딩 오케스트레이션(`graph_engine.py`, `workers.py`, `code_evaluator.py`)의 기반 계층 역할도 담당합니다.

## 아키텍처

```
사용자 쿼리
    ↓
SmartRouter (결정론적 분류, LLM 호출 없음)
    ├── SIMPLE   → Ollama (로컬) → Gemini → DeepSeek ...
    ├── MODERATE → Ollama (로컬) → Gemini → DeepSeek ...
    └── COMPLEX  → Google/Anthropic/OpenAI → Ollama (fallback)
    ↓
ReasoningEngine
    ├── ReasoningChain    (다중 샘플 합의)     [선택]
    ├── ThoughtDecomposer (서브태스크 분해)    [자동]
    └── ConfidenceVerifier (SAGE 자기-검증)   [선택]
    ↓
VibeCodingGraph
    ├── graph_engine.py   (코딩 오케스트레이터)
    ├── workers.py        (coder/tester/reviewer/debugger worker)
    └── code_evaluator.py (구조화된 코드 평가)
```

## 환경 변수

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama 서버 주소 |
| `OLLAMA_DEFAULT_MODEL` | `gemma3:4b` | 기본 모델 |
| `OLLAMA_TIMEOUT` | `120` | 요청 타임아웃 (초) |
| `REASONING_CHAIN_SAMPLES` | `3` | 다중 추론 샘플 수 |
| `CONFIDENCE_THRESHOLD` | `0.7` | SAGE 검증 임계값 |
| `THOUGHT_DECOMPOSER_MAX_DEPTH` | `3` | 서브태스크 분해 최대 깊이 |

## 설치 및 설정

### 1. Ollama 설치 확인
```bash
ollama --version     # v0.18.2 이상
ollama list          # 설치된 모델 확인
```

### 2. 모델 설치
```bash
# 권장 모델 (VRAM별)
ollama pull gemma3:4b              # 4GB VRAM (현재 설치됨)
ollama pull qwen3-coder:8b         # 8GB VRAM (코드 특화)
ollama pull qwen3-coder:30b-a3b-q4_K_M  # 16GB+ VRAM (최고 성능)
```

### 3. 서버 시작
```bash
ollama serve    # 기본 포트 11434에서 시작
```

### 4. 연결 확인
```bash
curl http://localhost:11434/api/tags    # 모델 목록 반환 확인
python workspace/execution/llm_client.py status  # 프로바이더 활성 상태
```

## 모듈 사용법

### OllamaClient (직접 사용)
```python
from execution.local_inference import OllamaClient

client = OllamaClient()
if client.is_available():
    content, in_tok, out_tok = client.generate(
        system_prompt="You are a coder.",
        user_prompt="Write a fibonacci function.",
    )
    print(content)
```

### LLMClient 통합 (자동 fallback)
```python
from execution.llm_client import LLMClient

# Ollama가 최우선 프로바이더 (비용 0)
client = LLMClient()
result = client.generate_text(system_prompt="...", user_prompt="...")
```

### SmartRouter (복잡도 기반 라우팅)
```python
from execution.smart_router import SmartRouter

router = SmartRouter()
result = router.classify("print hello world")
# result.complexity = SIMPLE, result.providers = ["ollama", "google", ...]
```

### 고급 추론
```python
from execution.reasoning_engine import ReasoningAdapter

adapter = ReasoningAdapter(llm_client)
result = adapter.run_full_reasoning(
    content="복잡한 아키텍처 분석...",
    use_chain=True,      # 다중 샘플 합의
    use_verifier=True,   # SAGE 자기-검증
)
```

### 에이전트형 코딩 오케스트레이션
```python
from execution.graph_engine import VibeCodingGraph

graph = VibeCodingGraph(max_iterations=3)
result = graph.run("Build a Python fibonacci function")
print(result["final_output"])
```

관련 실행 모듈:
- `workspace/execution/graph_engine.py`
- `workspace/execution/workers.py`
- `workspace/execution/code_evaluator.py`
- `workspace/execution/repo_map.py`
- `workspace/execution/context_selector.py`
- `workspace/execution/smart_router.py`
- `workspace/execution/reasoning_engine.py`
- `workspace/execution/reasoning_chain.py`
- `workspace/execution/thought_decomposer.py`
- `workspace/execution/confidence_verifier.py`
- `workspace/execution/benchmark_local.py`

## 벤치마크

```bash
# 전체 벤치마크 (기본 모델)
python workspace/execution/benchmark_local.py

# 특정 모델 지정
python workspace/execution/benchmark_local.py --model qwen3-coder:8b
```

결과는 `workspace/.tmp/benchmark_results.json`에 저장됩니다.

## 모델 선택 가이드

| VRAM | 모델 | 용도 | 예상 속도 |
|------|------|------|----------|
| 4GB | `gemma3:4b` | 단순 코드, 번역, 요약 | 빠름 |
| 8GB | `qwen3-coder:8b` | 중급 코딩, 리팩토링 | 보통 |
| 16GB+ | `qwen3-coder:30b` | 아키텍처 설계, 복잡 디버깅 | 느림 |

## 트러블슈팅

### Ollama 서버 연결 실패
```
ConnectionError: Ollama 서버 연결 실패
```
→ `ollama serve`가 실행 중인지 확인. Windows 방화벽에서 11434 포트 허용.

### 모델 로드 실패
```
RuntimeError: model not found
```
→ `ollama pull <model-name>`으로 모델 설치.

### VRAM 부족
```
Error: insufficient VRAM
```
→ 더 작은 양자화 모델 사용: `ollama pull gemma3:4b` (Q4_K_M)

### 느린 응답
- `OLLAMA_TIMEOUT`을 늘리세요 (기본 120초)
- 다른 GPU 작업을 종료하세요
- 모델 양자화 레벨을 낮추세요 (q4 → q8 비추천, q4가 속도 최적)

## Fallback 체인 (업데이트됨)

Ollama 추가 후 전체 프로바이더 체인 (9개):

| 순위 | 프로바이더 | 비용 | 조건 |
|------|-----------|------|------|
| 1 | **Ollama (로컬)** | **$0** | `OLLAMA_BASE_URL` 설정 & 서버 실행 |
| 2 | Google Gemini | 무료 tier | `GOOGLE_API_KEY` |
| 3 | ZhipuAI (GLM) | 무료 | `ZHIPUAI_API_KEY` |
| 4 | DeepSeek | 매우 저렴 | `DEEPSEEK_API_KEY` |
| 5 | Moonshot | 저렴 | `MOONSHOT_API_KEY` |
| 6 | OpenAI | 중간 | `OPENAI_API_KEY` |
| 7 | xAI (Grok) | 중간 | `XAI_API_KEY` |
| 8 | Anthropic | 높음 | `ANTHROPIC_API_KEY` |

> Ollama 서버가 중단되면 자동으로 Google Gemini로 fallback됩니다.

## 보안 참고사항

- Ollama 서버는 **로컬 전용**으로 실행 (외부 네트워크 노출 금지)
- API 키가 외부로 유출되지 않도록 `.env`는 `.gitignore`에 포함
- 프로덕션 배포 시 네트워크 방화벽으로 11434 포트 내부 전용 설정
