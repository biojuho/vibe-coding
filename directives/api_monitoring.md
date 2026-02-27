# API 모니터링 지침 (API Monitoring Directive)

> API 사용량을 추적하고 비용을 추정하여 대시보드로 제공합니다.

## 1. 목표
각 LLM 프로바이더의 API 호출 수, 토큰 사용량, 예상 비용을 모니터링합니다.

## 2. 도구
- `execution/api_usage_tracker.py` — 사용량 로거 + 대시보드 데이터
- `pages/api_monitor.py` — Streamlit 대시보드

## 3. 지원 프로바이더
| 프로바이더 | 환경 변수 | 상태 |
|-----------|----------|------|
| OpenAI | OPENAI_API_KEY | 키 확인만 |
| Anthropic | ANTHROPIC_API_KEY | 키 확인만 |
| Google | GOOGLE_API_KEY | 키 확인만 |
| DeepSeek | DEEPSEEK_API_KEY | 키 확인만 |
| Moonshot | MOONSHOT_API_KEY | 키 확인만 |
| Zhipu AI | ZHIPUAI_API_KEY | 키 확인만 |
| X AI | XAI_API_KEY | 키 확인만 |
| GitHub | GITHUB_PERSONAL_ACCESS_TOKEN | 키 확인만 |
| Notion | NOTION_API_KEY | 키 확인만 |

## 4. 사용량 기록 방법
execution 스크립트에서 API 호출 후 다음과 같이 기록:
```python
from execution.api_usage_tracker import log_api_call

log_api_call(
    provider="anthropic",
    model="claude-sonnet-4",
    tokens_input=500,
    tokens_output=200,
    caller_script="blind_scraper.py"
)
```

## 5. 비용 추정
내장 가격표 기반 자동 계산 (토큰 수 × 단가). 실제 청구 금액과 차이가 있을 수 있음.

## 6. 데이터베이스
- 위치: `.tmp/api_usage.db`
- 테이블: `api_calls`
- 필드: provider, model, endpoint, tokens_input, tokens_output, cost_usd, caller_script, timestamp

## 7. 운영 KPI
`pages/api_monitor.py`에서 다음 KPI를 함께 모니터링:
- `scheduler_success_rate`
- `scheduler_backlog`
- `api_calls_per_day`
- `agent_startup_failures`

## 8. CLI 사용법
```bash
python execution/api_usage_tracker.py check-keys
python execution/api_usage_tracker.py summary --days 30
python execution/api_usage_tracker.py daily
python execution/api_usage_tracker.py providers
```
