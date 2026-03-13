---
name: daily-brief
description: 시스템 전체 일일 브리핑을 생성하는 스킬. API 비용, 스케줄러, YouTube 성과, 에러 요약, 시스템 헬스를 한번에 확인. 트리거: "브리핑", "daily brief", "오늘 상태", "시스템 요약", "일일 리포트".
---

# 📊 Daily Brief (v2 — MCP 통합)

매일 시스템 전체 상태를 종합 브리핑으로 생성합니다.

## 브리핑 생성 절차

사용자가 브리핑을 요청하면 아래 순서로 데이터를 수집하여 요약합니다.

### 1. 시스템 헬스 (System Monitor MCP)

**MCP 연결 시:**
System Monitor MCP의 `get_system_stats`, `check_service_health` 도구 호출.

**MCP 미연결 시:**
```bash
PYTHONIOENCODING=utf-8 python infrastructure/system-monitor/server.py
```

> CPU, 메모리, 디스크 사용률 + 핵심 서비스(n8n, Docker, Streamlit) 생존 여부 확인

### 2. API 비용 요약 (SQLite Multi-DB MCP)

**MCP 연결 시:**
SQLite Multi-DB MCP → `query_database("api_usage", sql)` 호출:

```sql
-- 오늘 프로바이더별 비용
SELECT provider, COUNT(*) as calls, SUM(cost) as total_cost
FROM api_calls
WHERE date(timestamp) = date('now')
GROUP BY provider
ORDER BY total_cost DESC;
```

```sql
-- 이번 달 누적 비용
SELECT ROUND(SUM(cost), 4) as monthly_cost
FROM api_calls
WHERE strftime('%Y-%m', timestamp) = strftime('%Y-%m', 'now');
```

**MCP 미연결 시:**
```bash
PYTHONIOENCODING=utf-8 python execution/api_usage_tracker.py summary
```

### 3. 스케줄러 실행 결과 (SQLite Multi-DB MCP)

```sql
-- 오늘 실행된 태스크 결과
SELECT task_name, status, started_at, finished_at
FROM task_logs
WHERE date(started_at) = date('now')
ORDER BY started_at DESC;
```

### 4. YouTube 채널 성과

```bash
PYTHONIOENCODING=utf-8 python execution/youtube_analytics_collector.py
```

**SQLite 연동 시 보충 쿼리 (result_tracker DB):**
```sql
-- 최근 7일 채널별 조회수 변동
SELECT channel, SUM(views) as total_views, COUNT(*) as videos
FROM results
WHERE date >= date('now', '-7 days')
GROUP BY channel;
```

### 5. 에러/경고 요약 (SQLite + error-debugger Skill)

```sql
-- 최근 24시간 에러 (debug_history.db)
SELECT category, COUNT(*) as count, MAX(timestamp) as latest
FROM errors
WHERE timestamp >= datetime('now', '-24 hours')
GROUP BY category
ORDER BY count DESC;
```

> **참조**: `error-debugger` 스킬을 호출하면 더 상세한 에러 분석/복구 제안 가능

### 6. Notion 미완료 태스크 (Notion MCP)

**Notion MCP 연결 시:**
Notion MCP → 콘텐츠 캘린더 DB에서 Status = "진행 중" 조회.

**MCP 미연결 시:**
```bash
PYTHONIOENCODING=utf-8 python execution/notion_client.py list --status "진행 중"
```

### 7. 네트워크 상태 (System Monitor MCP)

System Monitor MCP → `get_network_status()` 호출.
> 외부 API 엔드포인트(Notion, OpenAI, Google, Pexels 등) 연결 가능 여부 확인

## 출력 형식

```markdown
# 📊 일일 브리핑 (YYYY-MM-DD)

## 🖥 시스템 상태
- CPU: XX% | 메모리: XX% (XX GB 사용) | 디스크: XX%
- 서비스: n8n ✅ | Docker ✅ | Streamlit ❌
- 네트워크: 7/7 엔드포인트 연결 가능

## 💰 API 비용
- 오늘: $X.XX (프로바이더별 breakdown)
- 이번 달 누적: $XX.XX / 예산 $40

## ⚙️ 스케줄러
- 성공: N건 / 실패: N건
- 실패 태스크: [목록]

## 📺 YouTube 성과
- 총 조회수 (7일): X,XXX
- 최고 성과 영상: [제목] (X,XXX views)

## 🐛 에러 요약
- 최근 24시간: N건 (카테고리별)

## 📝 미완료 태스크
- [태스크 목록]
```

## MCP 연동 매트릭스

| 섹션 | 1순위 MCP | 2순위 (폴백) |
|------|-----------|-------------|
| 시스템 헬스 | System Monitor MCP | Python 스크립트 |
| API 비용 | SQLite Multi-DB MCP | api_usage_tracker.py |
| 스케줄러 | SQLite Multi-DB MCP | scheduler.db 직접 |
| YouTube 성과 | YouTube MCP + SQLite | youtube_analytics_collector.py |
| 에러 요약 | SQLite (debug_history) + error-debugger Skill | error_analyzer.py |
| Notion 태스크 | Notion MCP | notion_client.py |
| 네트워크 | System Monitor MCP | - |

## 자동 실행

스케줄러에 등록하면 매일 아침 자동 생성 + Telegram 발송 가능:
```bash
PYTHONIOENCODING=utf-8 python execution/daily_report.py
```
