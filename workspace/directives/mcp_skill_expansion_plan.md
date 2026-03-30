# MCP & Skill 확장 기획안

> **작성일**: 2026-03-12
> **목표**: AI 오케스트레이션 계층의 도구 접근성 강화 — 현재 수동 스크립트 호출 → MCP/Skill 통합으로 전환

---

## 현재 상태 요약

### 기존 MCP 서버 (3개)
| MCP 서버 | 상태 | 비고 |
|----------|------|------|
| NotebookLM | 설치 완료 | Google OAuth, infrastructure/notebooklm-mcp/ |
| GitHub | 런처만 존재 | @modelcontextprotocol/server-github, npx 기반 |
| System Monitor | 스캐폴드 | infrastructure/system-monitor/, 미완성 |

### 기존 Skill (23개)
- MCP 관련: mcp-builder, mcp-integration
- 페르소나: 7개 (백엔드, 프론트, DevOps, 디자이너, PM, 법률, QA)
- 기타: brave-search, confidence-check, pptx, pdf, seaborn 등

### 누락 사항
- 통합 `.mcp.json` 없음 (개별 배치 스크립트로 실행)
- 핵심 서비스(Notion, YouTube, Telegram, SQLite) MCP 미연동
- n8n 워크플로우 트리거 자동화 미연동

---

## Phase 1: 즉시 도입 (MCP 서버 4개)

### 1-1. Notion MCP Server ⭐ 최우선

**현재 문제**: `notion_client.py`를 Bash로 호출해야 Notion 접근 가능. AI가 직접 DB를 조회/수정 불가.

**도입 효과**:
- AI가 직접 Notion DB 3개(Tasks, Shorts Queue, YouTube Tracking) CRUD
- "오늘 할일 뭐야?" → MCP로 즉시 조회
- Shorts 큐 관리, 콘텐츠 결과 확인 등 실시간 오케스트레이션

**구현 방법**:
```json
// .mcp.json
{
  "mcpServers": {
    "notion": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-notion"],
      "env": {
        "NOTION_API_KEY": "${NOTION_API_KEY}"
      }
    }
  }
}
```

**예상 작업량**: 설정 10분 (공식 MCP 서버 존재)

---

### 1-2. SQLite MCP Server ⭐ 최우선

**현재 문제**: `.tmp/` 내 6개 SQLite DB(api_usage, scheduler, content, finance, debug_history, result_tracker)를 조회하려면 Python 스크립트 실행 필요.

**도입 효과**:
- AI가 직접 SQL 쿼리로 데이터 분석
- "이번 주 API 비용 얼마야?" → `SELECT SUM(cost) FROM api_calls WHERE date >= ...`
- 스케줄러 로그, 에러 히스토리, 콘텐츠 성과 즉시 조회
- 디버깅 시 DB 상태 직접 확인

**구현 방법**:
```json
{
  "sqlite": {
    "type": "stdio",
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-sqlite", ".tmp/api_usage.db"]
  }
}
```

> 참고: DB가 6개이므로 multi-DB 접근을 위해 커스텀 래퍼 또는 DB별 서버 인스턴스 필요

**예상 작업량**: 설정 30분 (DB별 인스턴스 또는 커스텀 래퍼)

---

### 1-3. Filesystem MCP Server

**현재 문제**: `.tmp/`, `execution/`, 로그 파일 접근 시 Read/Glob 도구에 의존. 파일 목록 조회, 로그 모니터링 등 제한적.

**도입 효과**:
- `.tmp/` 중간 산출물 관리 (정리, 용량 확인)
- 로그 파일 실시간 모니터링
- 에셋 파일(projects/shorts-maker-v2/assets/) 관리

**구현 방법**:
```json
{
  "filesystem": {
    "type": "stdio",
    "command": "npx",
    "args": [
      "-y", "@modelcontextprotocol/server-filesystem",
      "c:/Users/박주호/Desktop/Vibe coding/.tmp",
      "c:/Users/박주호/Desktop/Vibe coding/execution",
      "c:/Users/박주호/Desktop/Vibe coding/infrastructure/n8n/logs"
    ]
  }
}
```

**예상 작업량**: 설정 10분

---

### 1-4. Brave Search MCP Server

**현재 문제**: `brave-search` 스킬은 존재하나 MCP 서버 미연결. 트렌드 조사, 기술 검색 시 WebSearch에만 의존.

**도입 효과**:
- 트렌딩 토픽 실시간 검색 (shorts-maker-v2 토픽 생성 보조)
- 기술 문서 검색, API 변경사항 확인
- community_trend_scraper.py 보조

**구현 방법**:
```json
{
  "brave-search": {
    "type": "stdio",
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-brave-search"],
    "env": {
      "BRAVE_API_KEY": "${BRAVE_API_KEY}"
    }
  }
}
```

**예상 작업량**: 설정 10분 + Brave API 키 발급 (무료 tier 2,000 req/mo)

---

## Phase 2: 단기 도입 (MCP 서버 3개 + Skill 3개)

### 2-1. YouTube Data MCP Server (커스텀)

**현재 문제**: YouTube 업로드/분석은 `youtube_uploader.py`, `youtube_analytics_collector.py`를 Bash 실행해야 함. AI가 직접 채널 성과를 조회하거나 업로드 상태를 확인할 수 없음.

**도입 효과**:
- "어제 업로드한 영상 조회수 어때?" → MCP로 즉시 확인
- 채널별 성과 비교, 트렌드 분석
- Shorts 큐 우선순위 결정 시 성과 데이터 참조

**구현 방법**: `infrastructure/scripts/mcp-manager.py`로 스캐폴딩 후 커스텀 구현
```
infrastructure/youtube-mcp/
├── server.py          # YouTube Data API v3 래퍼
├── requirements.txt   # google-api-python-client, oauth2client
└── README.md
```

**제공 도구 (Tools)**:
- `get_channel_stats(channel_id)` — 구독자, 총 조회수
- `get_recent_videos(channel_id, limit)` — 최근 영상 목록 + 성과
- `get_video_analytics(video_id)` — 개별 영상 상세 (조회수, CTR, 시청 지속시간)
- `search_trending(query, region)` — 트렌딩 검색

**예상 작업량**: 개발 2-3시간

---

### 2-2. Telegram MCP Server (커스텀)

**현재 문제**: `telegram_notifier.py`를 Bash로 호출해야 알림 전송 가능.

**도입 효과**:
- AI가 작업 완료/오류 시 직접 Telegram 알림
- "텔레그램으로 오늘 리포트 보내줘" → MCP 직접 호출
- 대화형 봇 명령 수신 (향후)

**제공 도구 (Tools)**:
- `send_message(text)` — 텍스트 메시지
- `send_photo(image_path, caption)` — 이미지 + 캡션
- `get_updates(limit)` — 최근 메시지 조회

**예상 작업량**: 개발 1-2시간

---

### 2-3. n8n Workflow MCP Server (커스텀)

**현재 문제**: n8n 워크플로우 트리거는 bridge_server.py HTTP 호출 필요. AI가 직접 파이프라인을 실행하거나 상태를 확인할 수 없음.

**도입 효과**:
- "blind-to-x 파이프라인 돌려줘" → MCP로 n8n 워크플로우 트리거
- 워크플로우 실행 상태 모니터링
- 실패 시 자동 재시도 오케스트레이션

**제공 도구 (Tools)**:
- `trigger_workflow(workflow_name)` — 워크플로우 실행
- `get_workflow_status(execution_id)` — 실행 상태 조회
- `list_workflows()` — 활성 워크플로우 목록
- `get_execution_history(limit)` — 최근 실행 이력

**구현 방법**: Bridge Server(localhost:9876) HTTP API 래핑

**예상 작업량**: 개발 2시간

---

### 2-4. Skill: `pipeline-runner` (신규)

**목적**: blind-to-x + shorts-maker-v2 파이프라인을 하나의 스킬로 통합 실행

**기능**:
- `/pipeline btx` → blind-to-x 전체 파이프라인 실행
- `/pipeline shorts <channel> <topic>` → 특정 채널 Shorts 생성
- `/pipeline status` → 모든 파이프라인 현재 상태
- 실행 전 비용 예상 표시 (cost_guard 연동)

**예상 작업량**: 개발 1시간

---

### 2-5. Skill: `daily-brief` (신규)

**목적**: 매일 시스템 전체 브리핑을 AI가 자동 생성

**기능**:
- `/brief` → 오늘의 종합 브리핑 생성
  - API 비용 요약 (api_usage.db)
  - 스케줄러 실행 결과 (scheduler.db)
  - YouTube 성과 변동 (content.db)
  - 에러/경고 요약 (debug_history.db)
  - Notion 미완료 태스크
- SQLite MCP + Notion MCP 연동

**예상 작업량**: 개발 1-2시간

---

### 2-6. Skill: `cost-check` (신규)

**목적**: API 비용 실시간 확인 및 예산 알림

**기능**:
- `/cost` → 이번 달 프로바이더별 비용 요약
- `/cost weekly` → 주간 비용 트렌드
- `/cost alert` → 예산 초과 경고 확인
- SQLite MCP 연동 (api_usage.db 직접 쿼리)

**예상 작업량**: 개발 30분

---

## Phase 3: 중기 도입 (고급 통합)

### 3-1. Cloudinary MCP Server (커스텀)

**도입 효과**: 이미지 에셋 관리 자동화 (업로드, 변환, CDN URL 생성)

**제공 도구**:
- `upload_image(path)` — 이미지 업로드 + CDN URL 반환
- `list_assets(folder)` — 에셋 목록
- `transform_image(public_id, options)` — 이미지 변환 (리사이즈, 포맷)

**예상 작업량**: 개발 2시간

---

### 3-2. Google Calendar MCP Server

**도입 효과**: 콘텐츠 캘린더 연동 (shorts-maker-v2 업로드 스케줄 관리)

**구현**: 공식 MCP 서버 존재 가능 → 확인 후 적용

**예상 작업량**: 설정 30분 ~ 개발 2시간

---

### 3-3. System Monitor MCP 완성

**현재**: 스캐폴드만 존재 (`infrastructure/system-monitor/`)

**완성 시 기능**:
- CPU/메모리/디스크 실시간 모니터링
- 프로세스 상태 확인 (Streamlit, n8n Docker 등)
- 네트워크 연결 상태 (API 엔드포인트 핑)

**예상 작업량**: 개발 2시간

---

### 3-4. Skill: `content-calendar` (신규)

**목적**: 5채널 Shorts 콘텐츠 캘린더 관리

**기능**:
- `/calendar` → 이번 주 업로드 계획 표시
- `/calendar add <channel> <topic> <date>` → 스케줄 추가
- `/calendar optimize` → 채널별 최적 업로드 시간 추천 (YouTube 분석 기반)

---

## 통합 .mcp.json 구성 (Phase 1 완료 시)

```json
{
  "mcpServers": {
    "notion": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@notionhq/notion-mcp-server"],
      "env": {
        "OPENAPI_MCP_HEADERS": "{\"Authorization\":\"Bearer ${NOTION_API_KEY}\",\"Notion-Version\":\"2022-06-28\"}"
      }
    },
    "sqlite": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-sqlite", ".tmp/api_usage.db"]
    },
    "filesystem": {
      "type": "stdio",
      "command": "npx",
      "args": [
        "-y", "@modelcontextprotocol/server-filesystem",
        ".tmp", "execution", "infrastructure/n8n/logs"
      ]
    },
    "brave-search": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-brave-search"],
      "env": {
        "BRAVE_API_KEY": "${BRAVE_API_KEY}"
      }
    },
    "github": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_PERSONAL_ACCESS_TOKEN}"
      }
    }
  }
}
```

---

## 우선순위 로드맵

```
Phase 1 (즉시, ~1시간)
├── ⭐ Notion MCP (공식 서버, 설정 10분)
├── ⭐ SQLite MCP (공식 서버, 설정 30분)
├── Filesystem MCP (공식 서버, 설정 10분)
├── Brave Search MCP (공식 서버, 설정 10분)
└── 통합 .mcp.json 생성

Phase 2 (단기, ~1주)
├── YouTube Data MCP (커스텀 개발, 2-3시간)
├── Telegram MCP (커스텀 개발, 1-2시간)
├── n8n Workflow MCP (커스텀 개발, 2시간)
├── Skill: pipeline-runner (1시간)
├── Skill: daily-brief (1-2시간)
└── Skill: cost-check (30분)

Phase 3 (중기, ~2주)
├── Cloudinary MCP (커스텀 개발, 2시간)
├── Google Calendar MCP (설정 or 개발, 30분~2시간)
├── System Monitor MCP 완성 (2시간)
└── Skill: content-calendar (2시간)
```

---

## 기대 효과

| 지표 | 현재 | Phase 1 후 | Phase 2 후 |
|------|------|-----------|-----------|
| AI 직접 접근 가능 서비스 | 3개 (GitHub, NotebookLM, Monitor) | **8개** (+Notion, SQLite, FS, Brave, GitHub 통합) | **11개** (+YouTube, Telegram, n8n) |
| 데이터 조회 방식 | Bash → Python → 결과 파싱 | MCP 직접 쿼리 | MCP 직접 쿼리 + 스킬 자동화 |
| 평균 작업 단계 수 | 3-4단계 (스크립트 찾기→실행→파싱→응답) | **1단계** (MCP 호출) | **0단계** (스킬 자동 실행) |
| 오케스트레이션 효율 | ~60% (수동 개입 필요) | ~85% | **~95%** |

---

## 비용 영향

- **Phase 1**: 무료 (공식 MCP 서버, npm 패키지)
  - Brave Search만 API 키 필요 (무료 2,000 req/mo)
- **Phase 2**: 무료 (커스텀 개발, 기존 API 키 재사용)
- **Phase 3**: 무료 (기존 인프라 활용)

> 전체 확장에 추가 비용 $0. 기존 API 키와 인프라만 활용.
