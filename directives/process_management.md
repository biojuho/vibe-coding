# 프로세스 관리 지침 (Process Management Directive)

> Hub에서 실행한 서브 프로세스의 생명주기를 추적하고 관리합니다.

## 1. 목표
서브 프로세스 실행, 상태 모니터링, 종료를 안전하게 관리합니다.

## 2. 도구
- `execution/process_manager.py` — ProcessManager 클래스

## 3. 프로세스
1. Hub에서 `launch_process()` 호출 시 PID를 `.tmp/hub_processes.json`에 등록
2. Hub 로드 시 `get_alive_processes()`로 생존 프로세스 확인 (psutil 사용)
3. 죽은 프로세스는 자동으로 목록에서 제거
4. 개별 종료: `kill_process(pid)` — 자식 프로세스까지 재귀 종료
5. 전체 종료: `kill_all()` — 등록된 모든 프로세스 일괄 종료

## 4. 데이터 구조
```json
{
  "pid": 12345,
  "name": "Personal Agent",
  "command": "streamlit run app.py",
  "cwd": "projects/personal-agent",
  "launched_at": "2026-02-24T10:30:00",
  "port": 8501
}
```

## 5. 예외 상황
| 상황 | 처리 |
|------|------|
| 프로세스가 이미 종료됨 | psutil.NoSuchProcess → 목록에서 제거 |
| 접근 권한 없음 | psutil.AccessDenied → 건너뛰기 + 경고 |
| Hub 재시작 | JSON 파일에서 PID 복원 후 생존 확인 |
| 좀비 프로세스 | STATUS_ZOMBIE → 죽은 것으로 처리 |
