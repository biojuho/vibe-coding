# LLM Fallback 시스템 지침

## 개요
모든 프로젝트에서 9개 LLM 프로바이더를 자동 fallback 체인으로 사용합니다.
하나의 프로바이더가 실패하면 자동으로 다음 프로바이더로 전환됩니다.

## 지원 프로바이더 (7개)

| 프로바이더 | 환경변수 | 기본 모델 | 비용 | 비고 |
|-----------|---------|----------|------|------|
| **Ollama (로컬)** | `OLLAMA_BASE_URL` | gemma3:4b | **$0** | **최우선** (서버 실행 필요) |
| Google Gemini | `GOOGLE_API_KEY` | gemini-2.5-flash | 무료 tier | 클라우드 1순위 |
| DeepSeek | `DEEPSEEK_API_KEY` | deepseek-chat | 매우 저렴 | OpenAI-compatible |
| Moonshot (Kimi) | `MOONSHOT_API_KEY` | moonshot-v1-8k | 저렴 | OpenAI-compatible |
| ZhipuAI (GLM) | `ZHIPUAI_API_KEY` | glm-4-flash | 무료 | OpenAI-compatible |
| OpenAI | `OPENAI_API_KEY` | gpt-4o-mini | 중간 | 표준 |
| xAI (Grok) | `XAI_API_KEY` | grok-3-mini-fast | 중간 | OpenAI-compatible |
| Anthropic | `ANTHROPIC_API_KEY` | claude-sonnet-4 | 높음 | 최후 fallback |

> Ollama 설정 및 모델 설치는 `directives/local_inference.md` 참고

## 통합 클라이언트 사용법

### 기본 사용 (execution/ 내부)
```python
from execution.llm_client import LLMClient

client = LLMClient()  # 기본 우선순위 (비용 효율 순)
result = client.generate_json(system_prompt="...", user_prompt="...")
text = client.generate_text(system_prompt="...", user_prompt="...")
safe_result = client.generate_json_bridged(system_prompt="...", user_prompt="...")
```

### 우선순위 커스텀
```python
client = LLMClient(providers=["openai", "deepseek", "google"])
```

### 간편 함수
```python
from execution.llm_client import generate_json, generate_text

data = generate_json(system_prompt="...", user_prompt="...", caller_script="my_script")
```

## 프로젝트별 적용 현황

| 프로젝트 | 파일 | fallback 방식 |
|---------|------|-------------|
| execution/ | `llm_client.py` | 통합 클라이언트 (7개) |
| execution/ | `topic_auto_generator.py` | `LLMClient` 사용 (7개 fallback) |
| shorts-maker-v2 | `providers/llm_router.py` | 자체 라우터 (7개 fallback) |
| shorts-maker-v2 | `pipeline/script_step.py` | `LLMRouter` (7개 fallback) |
| shorts-maker-v2 | `pipeline/media_step.py` | 프롬프트 정화: `LLMRouter` (7개), 이미지: DALL-E → Gemini → placeholder |
| shorts-maker-v2 | `pipeline/render_step.py` | BGM 무드 분류: `LLMRouter` (7개) → OpenAI 폴백 → 키워드 폴백 |
| shorts-maker-v2 | `providers/google_client.py` | Gemini 이미지 생성 (무료 500/일) |
| blind-to-x | `pipeline/draft_generator.py` | 자체 async 라우터 (7개 fallback) |
| blind-to-x | `pipeline/image_generator.py` | Gemini → Pollinations → DALL-E (3단계) |

## Fallback 동작 원리

1. 우선순위 순서대로 프로바이더 시도
2. 각 프로바이더당 `max_retries` 회 재시도 (기본 2회)
3. 재시도 간 exponential backoff (`min(2^attempt, 10)` 초)
4. 복구 불가 에러 (invalid key, unauthorized 등)는 즉시 다음 프로바이더로 전환
5. 모든 프로바이더 실패 시 `RuntimeError` 발생

## 비용 절감 전략

- **기본 우선순위**: 무료/저가 프로바이더 우선 (Gemini → DeepSeek → GLM)
- **API 사용 추적**: `api_usage_tracker.py` 자동 연동
- **API 키 없는 프로바이더**: 자동 스킵 (에러 없음)

## CLI 도구

```bash
# 전체 프로바이더 연결 테스트
python workspace/execution/llm_client.py test

# 특정 프로바이더만 테스트
python workspace/execution/llm_client.py test --provider deepseek

# 활성화 상태 확인
python workspace/execution/llm_client.py status
```

## 새 프로바이더 추가 시

1. `.env`에 API 키 추가
2. `execution/llm_client.py`의 상수들에 프로바이더 정보 추가
3. 필요 시 각 프로젝트 라우터에도 반영
4. `health_check.py`의 `API_CHECKS`에 추가
5. 이 지침 업데이트

## 주의사항

- OpenAI-compatible 프로바이더 (DeepSeek, Moonshot, ZhipuAI, xAI)는 `openai` SDK로 `base_url`만 변경하여 사용
- Anthropic은 독자 SDK 사용 (`anthropic` 패키지)
- Google Gemini는 `google-genai` SDK 사용
- 크레딧이 부족한 프로바이더는 `credit balance is too low` 에러로 자동 감지 → 다음 프로바이더로 전환
- DeepSeek 한국어 브릿지가 필요한 자동화 파이프라인은 `generate_json_bridged` / `generate_text_bridged`를 우선 사용
- 브릿지 상세 정책은 `directives/deepseek_ko_bridge.md` 참고
