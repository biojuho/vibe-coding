---
name: pipeline-runner
description: >-
  blind-to-x + shorts-maker-v2 파이프라인을 통합 실행하는 스킬 (MCP 연동). 조건부 실행, 비용 가드, 시스템 헬스 사전 검증 포함. 트리거: "파이프라인 실행", "pipeline run", "btx 실행", "shorts 생성", "파이프라인 상태".
---

# 🏭 Pipeline Runner (v2 — MCP 통합)

blind-to-x와 shorts-maker-v2 파이프라인을 통합 관리하는 스킬입니다.
v2에서는 실행 전 자동 검증과 MCP 연동이 추가되었습니다.

## 사용법

### 실행 전 자동 검증 (Pre-flight Check)

파이프라인 실행 요청 시, 아래 검증을 **자동으로** 수행합니다:

1. **시스템 헬스** (System Monitor MCP)
   - CPU < 90%, 메모리 < 85%, 디스크 < 95% 확인
   - 리소스 부족 시 경고 후 사용자 확인 요청

2. **비용 가드** (cost-check Skill + SQLite Multi-DB MCP)
   ```sql
   SELECT ROUND(SUM(cost), 4) as monthly_cost
   FROM api_calls
   WHERE strftime('%Y-%m', timestamp) = strftime('%Y-%m', 'now');
   ```
   - 월 예산 90% 초과 시 실행 차단 (사용자 오버라이드 가능)

3. **Lock 파일 확인**
   - `.tmp/.running.lock` 존재 시 중복 실행 방지
   - 1시간 초과 stale lock은 `error-debugger` 스킬로 자동 처리

4. **서비스 의존성** (System Monitor MCP)
   - n8n/브릿지 서버 생존 확인 (MCP 경유 파이프라인 시)

### blind-to-x 파이프라인

```bash
# 전체 실행 (병렬 3)
cd blind-to-x && PYTHONIOENCODING=utf-8 python main.py --parallel 3

# 드라이런 (데이터 변경 없음)
cd blind-to-x && PYTHONIOENCODING=utf-8 python main.py --dry-run

# 특정 소스만
cd blind-to-x && PYTHONIOENCODING=utf-8 python main.py --sources blind fmkorea
```

### shorts-maker-v2 파이프라인

```bash
# 특정 채널 + 토픽으로 Shorts 생성
cd shorts-maker-v2 && PYTHONIOENCODING=utf-8 python -m shorts_maker_v2.cli generate --channel "AI 테크" --topic "주제"

# 일일 자동 생성 (전 채널)
PYTHONIOENCODING=utf-8 python workspace/execution/shorts_daily_runner.py
```

### n8n 경유 실행 (n8n MCP)

```
n8n MCP → trigger_workflow("btx_pipeline")
n8n MCP → trigger_workflow("btx_dry_run")
```

### 상태 확인

**n8n MCP 연결 시:**
```
n8n MCP → check_bridge_health()
n8n MCP → get_execution_history(limit=5)
n8n MCP → get_available_commands()
```

**MCP 미연결 시:**
```bash
curl -s http://localhost:9876/health
curl -s http://localhost:9876/history?limit=5
curl -s http://localhost:9876/commands
```

## 실행 전 체크리스트 (자동)

| # | 체크 항목 | MCP 도구 | 폴백 |
|---|-----------|----------|------|
| 1 | CPU/메모리 여유 | System Monitor → `get_system_stats()` | `psutil` 직접 |
| 2 | 디스크 공간 | System Monitor → `get_disk_breakdown()` | `shutil.disk_usage()` |
| 3 | 월 예산 잔여 | SQLite Multi-DB → `query_database("api_usage", sql)` | `api_usage_tracker.py` |
| 4 | Lock 파일 상태 | Filesystem MCP 또는 `os.path.exists()` | 직접 확인 |
| 5 | n8n 브릿지 생존 | n8n MCP → `check_bridge_health()` | `curl` |
| 6 | 에러 히스토리 | SQLite Multi-DB → `query_database("debug_history", sql)` | `error_analyzer.py` |

## 비용 주의사항

- blind-to-x: 무료 운영 (Gemini + Pollinations)
- shorts-maker-v2: 이미지 생성 시 DALL-E 사용 가능 (유료)
- LLM: 7-provider cascade로 비용 최소화
- **실행 전 cost-check 스킬이 자동 호출됩니다**

## 오류 처리

1. 실행 실패 시 → **error-debugger** 스킬 자동 호출
2. 에러 분류 (NETWORK/TIMEOUT/AUTH/COST/SELECTOR/CODE/RESOURCE)
3. 안전한 자동 복구 시도 (stale lock 삭제, 캐시 정리 등)
4. 텔레그램 알림 자동 발송 (Telegram MCP 연결 시)
5. 로그: `.tmp/` 디렉토리 및 `infrastructure/n8n/logs/`

## 관련 스킬

- **cost-check**: 실행 전 비용 가드
- **error-debugger**: 실패 시 자동 진단
- **daily-brief**: 실행 결과가 브리핑에 포함
- **trend-scout**: 토픽 자동 제안 → 파이프라인 실행
