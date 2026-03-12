---
name: daily-brief
description: 시스템 전체 일일 브리핑을 생성하는 스킬. API 비용, 스케줄러, YouTube 성과, 에러 요약을 한번에 확인. 트리거: "브리핑", "daily brief", "오늘 상태", "시스템 요약", "일일 리포트".
---

# Daily Brief

매일 시스템 전체 상태를 종합 브리핑으로 생성합니다.

## 브리핑 생성 절차

사용자가 브리핑을 요청하면 아래 순서로 데이터를 수집하여 요약합니다.

### 1. API 비용 요약

```bash
# api_usage.db에서 오늘/이번 주/이번 달 비용 조회
PYTHONIOENCODING=utf-8 python execution/api_usage_tracker.py summary
```

SQLite MCP가 연결되어 있다면 직접 쿼리:
```sql
-- 오늘 프로바이더별 비용
SELECT provider, COUNT(*) as calls, SUM(cost) as total_cost
FROM api_calls
WHERE date(timestamp) = date('now')
GROUP BY provider
ORDER BY total_cost DESC;
```

### 2. 스케줄러 실행 결과

```sql
-- 오늘 실행된 태스크 결과
SELECT task_name, status, started_at, finished_at
FROM task_logs
WHERE date(started_at) = date('now')
ORDER BY started_at DESC;
```

### 3. YouTube 채널 성과

```bash
PYTHONIOENCODING=utf-8 python execution/youtube_analytics_collector.py
```

```sql
-- 최근 7일 채널별 조회수 변동
SELECT channel, SUM(views) as total_views, COUNT(*) as videos
FROM content
WHERE upload_date >= date('now', '-7 days')
GROUP BY channel;
```

### 4. 에러/경고 요약

```sql
-- 최근 24시간 에러
SELECT category, COUNT(*) as count, MAX(timestamp) as latest
FROM errors
WHERE timestamp >= datetime('now', '-24 hours')
GROUP BY category
ORDER BY count DESC;
```

### 5. Notion 미완료 태스크

Notion MCP가 연결되어 있다면 직접 조회, 아니면:
```bash
PYTHONIOENCODING=utf-8 python execution/notion_client.py list --status "진행 중"
```

## 출력 형식

```markdown
# 📊 일일 브리핑 (YYYY-MM-DD)

## API 비용
- 오늘: $X.XX (프로바이더별 breakdown)
- 이번 달 누적: $XX.XX / 예산 $XX

## 스케줄러
- 성공: N건 / 실패: N건
- 실패 태스크: [목록]

## YouTube 성과
- 총 조회수 (7일): X,XXX
- 최고 성과 영상: [제목] (X,XXX views)

## 에러 요약
- 최근 24시간: N건 (카테고리별)

## 미완료 태스크
- [태스크 목록]
```

## 자동 실행

스케줄러에 등록하면 매일 아침 자동 생성 + Telegram 발송 가능:
```bash
PYTHONIOENCODING=utf-8 python execution/daily_report.py
```
