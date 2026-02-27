# 스케줄러 지침 (Scheduler Directive)

> cron 기반 태스크를 등록/실행/모니터링하는 표준 운영 절차입니다.

## 1. 목표
- 반복 작업(백업, 리포트 생성, 데이터 수집)을 자동화합니다.
- 실행 결과를 구조화 로그로 남겨 장애를 추적합니다.
- 실패 누적 시 자동 비활성화로 연쇄 장애를 방지합니다.

## 2. 도구
- `execution/scheduler_engine.py` : SQLite 기반 스케줄러 엔진
- `execution/scheduler_worker.py` : due-task 폴링 워커(중복 실행 방지 lock 포함)
- `pages/scheduler_dashboard.py` : Streamlit 관리 UI

## 3. 핵심 인터페이스
- `add_task(name, executable, args, cwd, cron_expression, timeout_sec=300)`
- `run_task(task_id, trigger_type="manual")`
- `run_due_tasks()`
- `get_logs(task_id=None, limit=50)`
- `get_scheduler_kpis(days=7)`

## 4. DB 스키마
- 위치: `.tmp/scheduler.db`
- 테이블:
  - `tasks`
    - `executable`, `args_json`, `cwd`, `cron_expression`, `timeout_sec`
    - `failure_count`, `enabled`, `last_run`, `next_run`
  - `task_logs`
    - `stdout`, `stderr`, `exit_code`
    - `duration_ms`, `trigger_type(manual|schedule)`, `error_type`

## 5. 실행 흐름
1. 태스크 등록 시 cron을 검증하고 `next_run`을 계산합니다.
2. 워커(`scheduler_worker.py`)가 10~60초 간격으로 `run_due_tasks()`를 호출합니다.
3. 엔진은 `shell=False`로 안전 실행합니다.
4. 실행 완료 후 로그를 기록하고 다음 실행 시각을 갱신합니다.
5. 실패가 연속 5회 이상이면 자동 비활성화합니다.

## 6. 예외 처리
- 잘못된 `cwd`: `error_type=cwd_not_found`, `exit_code=-3`
- 실행 파일 없음: `error_type=exec_not_found`, `exit_code=-4`
- 타임아웃: `error_type=timeout`, `exit_code=-1`
- 비정상 종료: `error_type=non_zero_exit`
- 예외: `error_type=exception`

## 7. CLI 예시
```bash
python execution/scheduler_engine.py add --name "Backup" --exec python --args "scripts/backup_data.py --with-env" --cwd . --cron "0 9 * * *" --timeout 300
python execution/scheduler_engine.py run-due
python execution/scheduler_engine.py logs --limit 30
python execution/scheduler_engine.py kpis --days 7
python execution/scheduler_worker.py --interval 30
```
