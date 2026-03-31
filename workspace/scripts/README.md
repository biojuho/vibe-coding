# scripts/ 디렉토리 가이드

> 워크스페이스 전체를 대상으로 한 운영/관리 스크립트 모음

## 역할 구분

| 스크립트 | 역할 | 실행 빈도 |
|----------|------|-----------|
| `doctor.py` | 워크스페이스 헬스체크 (패키지, venv, API 키 등) | 일상/CI |
| `quality_gate.py` | CI 품질 게이트 (smoke → pytest → ruff → static analysis) | 커밋 시 |
| `smoke_check.py` | 핵심 모듈 py_compile + import 검증 | 커밋 시 |
| `backup_data.py` | 프로젝트 데이터 백업 (DB, .env) | 수동/정기 |
| `update_all.py` | 모든 git repo 일괄 pull | 수동 |
| `seed_shorts_topics.py` | Shorts 초기 주제 풀 시딩 | 일회성 |
| `schedule_yt_analytics.bat` | YouTube Analytics 수집 스케줄링 | cron/Task Scheduler |

## `execution/`과의 차이

- **`scripts/`**: 워크스페이스 전체 대상, 인프라/CI 도구
- **`execution/`**: 비즈니스 로직 실행 모듈 (Notion, LLM, 스크래퍼 등)
