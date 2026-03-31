# 파이프라인 감시 & 백업 지침 (Watchdog & Backup Directive)

> 시스템 상태를 자동 감시하고, 이상 시 Telegram 알림을 보내며, 핵심 파일을 OneDrive로 백업합니다.

## 1. 목표
- 파이프라인이 "조용히 죽는" 것을 방지합니다.
- 시스템 이상을 즉시 감지하여 Telegram으로 알립니다.
- 프로젝트 핵심 파일을 매일 자동 백업하여 데이터 소실을 방지합니다.

## 2. 도구
- `execution/pipeline_watchdog.py` : 시스템 상태 감시 + Telegram 알림
- `execution/backup_to_onedrive.py` : OneDrive 자동 백업
- `execution/health_check.py` : 환경 변수 / API 연결 점검 (기존)

## 3. Watchdog 점검 항목

| 항목 | 무엇을 확인하나 | FAIL 기준 |
|------|-----------------|-----------|
| `btx_pipeline` | blind-to-x 마지막 실행 시각 | 26시간 이상 미실행 |
| `scheduler_tasks` | 내부 스케줄러 태스크 건강 | 연속 실패 3회 이상 |
| `notion_api` | Notion API 연결 | 401/연결실패 |
| `win_task_scheduler` | Windows Task Scheduler 등록 | 태스크 미등록/비활성 |
| `disk_space` | C: 잔여 공간 | 10GB 미만 |
| `telegram` | Telegram 설정 여부 | 미설정 |
| `backup` | 최근 백업 존재 여부 | 7일 이상 미백업 |

## 4. 실행 방법

### 수동 실행
```bash
# 전체 점검 + 이상 시 Telegram 알림
python workspace/execution/pipeline_watchdog.py

# JSON 출력 (스크립트 연동용)
python workspace/execution/pipeline_watchdog.py --json

# 점검만 (알림 없이)
python workspace/execution/pipeline_watchdog.py --no-notify

# 매일 요약 리포트 전송 (상태 무관)
python workspace/execution/pipeline_watchdog.py --daily
```

### 자동 실행
- `projects/blind-to-x/run_scheduled.py`에 통합됨
- 파이프라인 완료 직후 자동으로 watchdog → backup 순서로 실행
- watchdog/backup 실패는 파이프라인 exit code에 영향 없음

## 5. 백업 설정

### 백업 대상
- 코드, 설정 파일, 스킬, 지침, 문서 등 핵심 파일

### 백업 제외
- `venv/`, `node_modules/`, `__pycache__/`, `.next/`, `.tmp/`, `_archive/`, `.git/`
- `.pyc`, `.db`, `.sqlite3`, `.lock` 등 재생성 가능 파일
- 10MB 초과 파일

### 백업 보관 정책
- 최근 7개 백업만 유지, 오래된 것은 자동 삭제

### 백업 실행
```bash
python workspace/execution/backup_to_onedrive.py           # 실제 백업
python workspace/execution/backup_to_onedrive.py --dry-run  # 미리보기
python workspace/execution/backup_to_onedrive.py --status   # 현황 확인
```

## 6. 이력 관리
- Watchdog 이력: `.tmp/watchdog_history.json` (최근 30회)
- 백업 상태: `.tmp/backup_status.json`

## 7. 문제 해결

### Telegram 알림이 안 올 때
1. `.env`에서 `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` 확인
2. `TELEGRAM_ENABLED=true` 확인
3. `python workspace/execution/telegram_notifier.py check`으로 봇 상태 점검

### 백업이 너무 커질 때
1. `backup_to_onedrive.py`의 `SKIP_DIRS`, `SKIP_EXTS` 조정
2. `MAX_FILE_SIZE` 조정 (현재 10MB)
3. `MAX_BACKUPS` 줄이기 (현재 7)
