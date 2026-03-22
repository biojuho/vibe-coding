# MCP 서버 리소스 프로파일링 결과

> 측정일: 2026-03-22 20:00 KST | 시스템: 15.75GB RAM, 94.4% 사용

---

## 1. 핵심 발견: 4배 중복 실행

각 MCP 서버가 **4개 인스턴스**로 중복 실행 중. AI 도구(Claude Code, Cursor 등) 별로 독립 MCP 프로세스 생성이 원인.

### Node.js 기반 MCP 서버 (npx 실행)

| 서버 | 인스턴스 | 프로세스 수 | 프로세스당 메모리 | 총 메모리 추정 |
|------|---------|-----------|-----------------|--------------|
| @notionhq/notion-mcp-server | 4 | 8 (npx+node) | ~35MB | ~280MB |
| @modelcontextprotocol/server-filesystem | 4 | 8 | ~35MB | ~280MB |
| @modelcontextprotocol/server-brave-search | 4 | 8 | ~35MB | ~280MB |
| @modelcontextprotocol/server-github | 4 | 8 | ~35MB | ~280MB |
| @playwright/mcp | 1 | 2 | ~60MB | ~120MB |
| firebase-tools mcp | 1 | 2 | ~40MB | ~80MB |
| @supabase/mcp-server-supabase | 1 | 2 | ~40MB | ~80MB |
| Amazon Q language server | 1 | 1 | ~143MB | ~143MB |

### Python 기반 MCP 서버 (커스텀)

| 서버 | 인스턴스 | 프로세스 수 | 프로세스당 메모리 | 총 메모리 추정 |
|------|---------|-----------|-----------------|--------------|
| sqlite-multi-mcp | 4 | 8 | ~70MB | ~560MB |
| youtube-mcp | 4 | 8 | ~70MB | ~560MB |
| telegram-mcp | 4 | 8 | ~70MB | ~560MB |
| n8n-mcp | 4 | 8 | ~70MB | ~560MB |
| system-monitor | 4 | 8 | ~70MB | ~560MB |
| cloudinary-mcp | 4 | 8 | ~70MB | ~560MB |

### 합계

- **총 프로세스**: ~90개 (node 42 + python 48)
- **총 메모리 추정**: ~4.9GB (전체 RAM의 31%)
- **중복 제거 시 절감**: ~3.7GB (1세트로 줄이면)

---

## 2. 사용 빈도 분류

### Tier 1: 상시 필수 (Always-On)

| 서버 | 근거 |
|------|------|
| sqlite-multi-mcp | 대시보드 + 모든 세션에서 DB 조회 |
| system-monitor | 프로파일링 + 헬스체크 |
| telegram-mcp | 알림 전송 (스케줄러 연동) |

### Tier 2: 세션 중 필요 (Session-Active)

| 서버 | 근거 |
|------|------|
| notion-mcp-server | 세션 중 태스크 조회 시 |
| server-github | PR/이슈 작업 시 |
| server-brave-search | 웹 검색 필요 시 |
| server-filesystem | 파일 탐색 시 (Read/Glob으로 대체 가능) |

### Tier 3: 드물게 사용 (On-Demand)

| 서버 | 근거 | 권장 |
|------|------|------|
| youtube-mcp | 영상 분석 시에만 | on-demand |
| cloudinary-mcp | 이미지 업로드 시에만 | on-demand |
| n8n-mcp | 워크플로우 트리거 시에만 | on-demand |
| playwright-mcp | 브라우저 자동화 시에만 | on-demand |
| firebase-tools | Firebase 작업 시에만 | on-demand |
| supabase-mcp | Supabase 작업 시에만 | on-demand |
| notebooklm-mcp | 팟캐스트 생성 시에만 | on-demand |

---

## 3. 즉시 조치 권장

### 3-A. AI 도구 동시 실행 제한

현재 4개 AI 도구가 동시에 MCP 서버를 생성. 사용하지 않는 AI 도구 창을 닫으면 즉시 ~3.7GB 확보.

### 3-B. Tier 3 서버 on-demand 전환

`settings.json`에서 Tier 3 서버를 제거하고, 필요 시 수동 활성화.
절감 효과: 인스턴스당 ~420MB (youtube + cloudinary + n8n + playwright + firebase + supabase + notebooklm)

### 3-C. server-filesystem 제거 검토

Claude Code의 Read/Write/Glob/Grep 도구가 filesystem MCP와 완전 중복.
제거 시 인스턴스당 ~70MB 추가 절감.

---

## 4. 중기 개선안

- **MCP 프록시 서버**: 단일 프로세스로 모든 MCP 요청을 라우팅 (mcp-proxy 패턴)
- **lazy-start 래퍼**: 첫 요청 시에만 서버 프로세스 시작, 10분 유휴 시 종료
- **Docker Compose profile**: `always` / `on-demand` 프로필로 분리
