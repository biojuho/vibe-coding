# 일일 리포트 지침 (Daily Report Directive)

> 하루 활동(Git 커밋, 파일 변경, 스케줄러 실행)을 수집하여 요약 리포트를 생성합니다.

## 1. 목표
개발 활동을 일별로 정량화하여 생산성 추적 기반을 마련합니다.

## 2. 도구
- `execution/daily_report.py` — 데이터 수집 + 리포트 생성
- `pages/daily_report.py` — Streamlit 뷰어

## 3. 수집 항목
| 항목 | 소스 | 방법 |
|------|------|------|
| Git 커밋 | 워크스페이스 내 모든 .git 레포 | `git log --since --until` |
| 파일 변경 | 파일 시스템 mtime | `os.walk` + stat |
| 스케줄러 로그 | `.tmp/scheduler.db` | `get_logs()` |

## 4. 출력
- JSON: `.tmp/reports/daily_YYYY-MM-DD.json`
- 포함 필드: summary, git_activity, file_changes, scheduler_logs

## 5. CLI 사용법
```bash
python execution/daily_report.py --date 2026-02-24 --format json
python execution/daily_report.py --format markdown
```
