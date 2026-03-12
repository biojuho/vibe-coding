---
name: cost-check
description: API 비용 실시간 확인 및 예산 알림 스킬. 프로바이더별 사용량, 월간 추세, 예산 초과 경고 제공. 트리거: "비용 확인", "cost check", "API 비용", "얼마 썼어", "예산".
---

# Cost Check

API 비용을 실시간으로 확인하고 예산 대비 사용량을 분석합니다.

## 데이터 소스

- **메인 DB**: `.tmp/api_usage.db` (execution/api_usage_tracker.py)
- **BTX DB**: `blind-to-x/.tmp/cost.db` (pipeline/cost_db.py)

## 조회 방법

### 방법 1: SQLite MCP 직접 쿼리 (권장)

```sql
-- 오늘 프로바이더별 비용
SELECT provider,
       COUNT(*) as calls,
       SUM(input_tokens) as input_tokens,
       SUM(output_tokens) as output_tokens,
       ROUND(SUM(cost), 4) as total_cost
FROM api_calls
WHERE date(timestamp) = date('now')
GROUP BY provider
ORDER BY total_cost DESC;

-- 이번 주 일별 비용 추세
SELECT date(timestamp) as day,
       ROUND(SUM(cost), 4) as daily_cost
FROM api_calls
WHERE timestamp >= date('now', '-7 days')
GROUP BY date(timestamp)
ORDER BY day;

-- 이번 달 누적 비용
SELECT ROUND(SUM(cost), 4) as monthly_cost
FROM api_calls
WHERE strftime('%Y-%m', timestamp) = strftime('%Y-%m', 'now');

-- 프로바이더별 월간 비용 비교
SELECT provider,
       strftime('%Y-%m', timestamp) as month,
       COUNT(*) as calls,
       ROUND(SUM(cost), 4) as total_cost
FROM api_calls
WHERE timestamp >= date('now', '-90 days')
GROUP BY provider, month
ORDER BY month DESC, total_cost DESC;
```

### 방법 2: Python 스크립트

```bash
PYTHONIOENCODING=utf-8 python execution/api_usage_tracker.py summary
```

## 예산 기준

| 프로바이더 | 월 예산 | 단가 (input/1M tokens) |
|-----------|---------|----------------------|
| Google Gemini | 무료 | $0 (무료 tier) |
| ZhipuAI | 무료 | $0 (무료 tier) |
| DeepSeek | $5 | $0.14 |
| Moonshot | $5 | ~$0.20 |
| Groq | 무료 | $0 (무료 tier) |
| OpenAI | $10 | $0.15 (gpt-4o-mini) |
| xAI | $10 | ~$0.50 |
| Anthropic | $10 | $0.80 (Sonnet) |

**월 총 예산 목표**: $40 이하

## 알림 기준

- **주의**: 월 예산 70% 도달
- **경고**: 월 예산 90% 도달
- **차단**: 월 예산 100% 초과 시 유료 프로바이더 비활성화 권장

## 비용 최적화 팁

1. Gemini/ZhipuAI/Groq 무료 tier 최대 활용
2. LLM 캐시 72시간 활성화 확인 (llm_cache.db)
3. blind-to-x: Gemini 이미지 생성 (500장/일 무료)
4. shorts-maker-v2: edge-tts 무료 TTS 사용
