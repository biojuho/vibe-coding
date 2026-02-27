# Notion 연동 지침 (Notion Integration Directive)

> Notion 태스크 데이터베이스를 Hub에서 직접 조회하고 관리합니다.

## 1. 목표
Notion에 저장된 태스크를 Hub UI에서 조회/생성/상태 변경합니다.

## 2. 사전 요구사항
`.env` 파일에 다음 변수 추가:
```
NOTION_API_KEY=ntn_your_integration_token
NOTION_TASK_DATABASE_ID=your_database_id
```

속성은 자동 감지됩니다:
- title 타입 속성(필수)
- status 또는 select 타입 속성(선택)
- date 타입 속성(선택)

필요 시 속성명을 환경변수로 강제 지정:
```
NOTION_TASK_TITLE_PROPERTY=Name
NOTION_TASK_STATUS_PROPERTY=Status
NOTION_TASK_DUE_PROPERTY=Due Date
```

## 3. 도구
- `execution/notion_client.py` — Notion REST API 클라이언트
- `pages/notion_tasks.py` — 칸반 스타일 Streamlit UI

## 4. 프로세스
1. DB 메타를 조회해 title/status/date 속성을 자동 매핑
2. `list_tasks(status_filter)` — 태스크 목록 조회(상태 속성 타입에 맞는 필터 자동 적용)
3. `create_task(title, status, due_date)` — 새 태스크 생성(존재하는 속성만 사용)
4. `update_task_status(page_id, new_status)` — 상태 변경(status/select 타입 모두 지원)

## 5. API 제한
- Notion API 버전: 2022-06-28
- Rate limit: 3 requests/second
- 페이지 사이즈: 100
