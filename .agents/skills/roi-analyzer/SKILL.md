---
name: roi-analyzer
description: 콘텐츠 ROI 분석 — API 비용 vs 수익 대비, 채널별 손익분기점 산출
---

# 💰 ROI Analyzer Skill

> 콘텐츠별 비용/수익 분석, 채널별 ROI 계산, 최적화 제안

## 목적

API 호출 비용 데이터와 YouTube 콘텐츠 성과 데이터를 결합하여
프로젝트의 투자 대비 수익률(ROI)을 분석하고 최적화 방안을 제시합니다.

## 사전 요구사항

- **SQLite Multi-DB MCP** (api_usage.db, result_tracker.db 접근)
- **Notion MCP** (콘텐츠 상태 조회)
- `execution/api_usage_tracker.py` (비용 추적 모듈)
- `execution/result_tracker_db.py` (결과 추적 모듈)

## 사용법

### 1. 월간 비용 요약

```
사용자: 이번 달 API 비용 분석해줘
```

**에이전트 동작:**
1. `api_usage.db`에서 이번 달 프로바이더별 호출 횟수/비용 집계
   ```sql
   SELECT provider, COUNT(*) as calls, SUM(cost) as total_cost 
   FROM api_calls WHERE date >= date('now', 'start of month')
   GROUP BY provider ORDER BY total_cost DESC
   ```
2. 프로젝트별 비용 분배 (blind-to-x, shorts-maker-v2, 기타)
3. 전월 대비 증감 분석
4. 프로바이더별 비용 효율 비교 (건당 비용)

### 2. 콘텐츠당 ROI 계산

```
사용자: YouTube Shorts 콘텐츠당 ROI 알려줘
```

**에이전트 동작:**
1. 콘텐츠별 생산 비용 산출:
   - LLM 스크립트 생성 비용
   - TTS 비용 (Edge TTS = $0, 무료)
   - 이미지 생성 비용 (Gemini = $0, DALL-E = ~$0.04)
   - 인프라 비용 (전기/네트워크, 무시 가능)
2. 콘텐츠별 수익 추정:
   - YouTube AdSense RPM 기반 (사용자 입력 또는 추정)
   - 조회수 × RPM = 예상 수익
3. ROI = (수익 - 비용) / 비용 × 100%

### 3. 채널별 손익분기점

```
사용자: 채널별 손익분기점 분석해줘
```

**에이전트 동작:**
1. 채널별 월간 집계:
   - 발행 영상 수
   - 총 비용 (API 호출)
   - 총 조회수
   - 추정 수익 (RPM 기반)
2. 손익분기 조회수 계산: 비용 / RPM × 1000
3. 현재 평균 조회수 대비 달성률 표시

### 4. 비용 최적화 제안

```
사용자: 비용 줄일 방법 있어?
```

**에이전트 동작:**
1. 비용 구조 분석 (어느 단계에서 비용이 많이 발생하는지)
2. 무료 대안 활용도 체크:
   - Gemini (무료) vs DALL-E ($0.04/장) 비율
   - Edge TTS (무료) vs 다른 TTS
   - 캐시 적중률 (llm_cache.db)
3. 구체적 절감 방안 제시

## 핵심 지표

| 지표 | 계산식 | 목표 |
|------|--------|------|
| 콘텐츠당 비용 | 총 API 비용 / 발행 건수 | ≤ $0.015 |
| 무료 프로바이더 비율 | 무료 호출 / 전체 호출 | ≥ 70% |
| 캐시 적중률 | 캐시 히트 / 전체 LLM 호출 | ≥ 30% |
| YouTube RPM | AdSense 수익 / 조회수 × 1000 | 모니터링 |
| 채널별 ROI | (수익 - 비용) / 비용 × 100 | ≥ 0% (손익분기) |

## 비용 데이터 소스

| DB | 테이블 | 필드 |
|----|--------|------|
| `api_usage.db` | `api_calls` | provider, model, cost, tokens, date |
| `result_tracker.db` | `contents` | platform, views, likes, url |
| `finance.db` | (있으면) | 수익 데이터 |

## 주의사항

- YouTube RPM은 계정마다 다르므로 **사용자 입력이 필요**합니다 (없으면 한국 평균 $1~3 추정)
- blind-to-x 비용과 shorts-maker-v2 비용은 **분리 추적**합니다
- 비용 최적화 제안 시 **품질 저하 리스크**도 함께 언급합니다
