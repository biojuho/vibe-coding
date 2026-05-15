---
name: content-calendar
description: 5채널 YouTube Shorts 콘텐츠 캘린더를 관리하고 예약 콘텐츠 흐름을 점검할 때 사용.
---

# 📅 Content Calendar Skill

> 5채널 YouTube Shorts 콘텐츠 캘린더 관리, 토픽 중복 방지, 주간 밸런싱, 업로드 최적 시간 추천

## 목적

shorts-maker-v2의 5채널(AI Tech, Psychology, History, Health, Space) 콘텐츠 스케줄을
체계적으로 관리합니다. Notion 콘텐츠 캘린더 DB와 연동하여 토픽 제안/등록/상태 관리를 자동화합니다.

## 사전 요구사항

- **Notion MCP** 연결 (Notion DB CRUD)
- `NOTION_TRACKING_DB_ID` 환경변수 설정
- `projects/shorts-maker-v2/channel_profiles.yaml` 존재

## 사용법

### 1. 이번 주 캘린더 조회

```
사용자: 이번 주 Shorts 업로드 계획 보여줘
```

**에이전트 동작:**
1. Notion `content_calendar` DB에서 이번 주 예정 항목 조회 (Status = "scheduled")
2. 채널별 그룹핑하여 요약 표시
3. 비어있는 슬롯 감지 → 토픽 제안

### 2. 토픽 등록

```
사용자: AI 채널에 "GPT-5가 바꿀 5가지" 추가해줘
```

**에이전트 동작:**
1. 중복 토픽 검사 (최근 30일 내 유사 토픽 존재 여부)
2. 채널 적합도 검증 (channel_profiles.yaml의 topic_pool 확인)
3. Notion DB에 새 항목 생성 (Status: "draft", Channel: "ai_tech")

### 3. 주간 밸런싱 검토

```
사용자: 이번 주 채널 밸런스 확인해줘
```

**에이전트 동작:**
1. 채널별 예정 개수 집계
2. 불균형 감지 (특정 채널 3+건 vs 다른 채널 0건)
3. 밸런싱 제안 (부족한 채널의 고성과 토픽 유형 추천)

### 4. 최적 업로드 시간 추천

```
사용자: AI 채널 최적 업로드 시간 알려줘
```

**에이전트 동작:**
1. SQLite `result_tracker.db`에서 채널별 과거 성과 조회
2. 시간대별 평균 조회수/참여율 집계
3. 상위 3개 시간대 추천

## 데이터 소스

| 소스 | 용도 |
|------|------|
| Notion DB (NOTION_TRACKING_DB_ID) | 캘린더 항목 CRUD |
| `result_tracker.db` | 성과 기반 최적 시간 분석 |
| `channel_profiles.yaml` | 채널별 설정/토픽 풀 |
| `content_calendar.py` | 기존 캘린더 유틸리티 모듈 |

## Notion DB 스키마 (필수 속성)

| 속성 | 타입 | 설명 |
|------|------|------|
| Name | title | 토픽 제목 |
| Channel | select | 채널 (ai_tech, psychology, history, health, space) |
| Status | select | draft → scheduled → rendering → uploaded → published |
| Scheduled Date | date | 예정 업로드 날짜 |
| Priority | number | 우선순위 (1=최우선) |

## 주의사항

- 동일 토픽을 **30일 이내에 재등록하지 않습니다** (유사도 체크)
- 채널당 **일일 최대 2건** 업로드 제한 준수
- `Status: "published"` 항목은 수정하지 않습니다
