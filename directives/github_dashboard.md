# GitHub 대시보드 지침 (GitHub Dashboard Directive)

> GitHub 활동 통계를 수집하여 대시보드로 시각화합니다.

## 1. 목표
커밋 히트맵, PR 통계, 언어 분포, 레포 목록 등 GitHub 활동을 한눈에 파악합니다.

## 2. 사전 요구사항
`infrastructure/.env`에 `GITHUB_PERSONAL_ACCESS_TOKEN` 설정 필요.

## 3. 도구
- `execution/github_stats.py` — GitHub REST API v3 클라이언트
- `pages/github_dashboard.py` — Streamlit 대시보드

## 4. 수집 항목
| 항목 | API 엔드포인트 | 설명 |
|------|---------------|------|
| 사용자 프로필 | GET /user | 아바타, 이름, 바이오 |
| 레포 목록 | GET /user/repos | 이름, 언어, 스타 |
| 커밋 | GET /repos/:owner/:repo/commits | 최근 N일 커밋 |
| PR 통계 | GET /search/issues | open/closed/merged |
| 언어 분포 | 레포 메타데이터에서 집계 | 레포별 주 언어 |

## 5. 제한사항
- API Rate limit: 5000 requests/hour (인증 시)
- 커밋 수집 시 상위 30개 레포만 조회 (성능 고려)
- 히트맵은 최근 365일까지 지원

## 6. CLI 사용법
```bash
python execution/github_stats.py user
python execution/github_stats.py repos
python execution/github_stats.py commits --days 30
python execution/github_stats.py prs
python execution/github_stats.py languages
```
