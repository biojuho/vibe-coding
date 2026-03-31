# Vibe Coding Status & Activity

> 이 파일은 현재 시스템 구조와 활성 Minefield만 저장합니다.
> 테스트 결과/Coverage는 `qaqc_history.db` 또는 `qaqc_result.json`을 참조하세요.

## Current State

- Canonical layout: `workspace/` (root automation), `projects/` (product repos), `infrastructure/` (MCP servers)
- QA/QC output: `projects/knowledge-dashboard/public/qaqc_result.json`
- `blind-to-x`: staged pipeline (`pipeline/process_stages/`), rules under `rules/`, X-first editorial filtering
- `shorts-maker-v2`: 91% coverage, MoviePy + FFmpeg dual backend, golden render verification
- `hanwoo-dashboard`: Next.js 16, Prisma 7.6, 0 npm vulnerabilities
- Governance gate: `governance_checks.py` validates `.ai` files, relay claims, directive mapping, task backlog
- Windows Task Scheduler: ASCII-safe `C:\btx\...` wrappers
- Security: all f-string SQL validated (allowlist/regex), triaged as false positives

## Minefield

| Risk | Details | Safe Pattern |
| --- | --- | --- |
| Windows console encoding | cp949 paths/terminals에서 non-ASCII 출력 실패 | ASCII-safe logging 사용 |
| Windows CA path + `curl_cffi` | Non-ASCII 경로에서 Error 77 | cert bundle을 ASCII 경로로 복사 + `CURL_CA_BUNDLE` 설정 |
| pytest `addopts` conflicts | 프로젝트별 pytest 설정 충돌 | shared runner에서 `-o addopts=` 사용 |
| Relay claim drift | HANDOFF.md가 실제 코드와 불일치할 수 있음 | `health_check.py --category governance --json` 실행 |
| Dirty nested repos | 서브 프로젝트에 사용자 WIP 존재 가능 | 관련 없는 변경사항 절대 revert 금지 |
| PowerShell ScheduledTasks | `Register-ScheduledTask` Access denied 가능 | `schtasks` fallback 사용 |
| BTX draft contract | twitter `reply` 태그 필수, `creator_take`는 optional metadata | `draft_contract.py` helpers 사용 |
| BTX `CostDatabase._connect()` | 일부 모듈이 `_connect()` alias 사용 중 | 마이그레이션 완료까지 alias 유지 |
| Health check root split | workspace 디렉토리와 repo-root 파일 혼합 의도적 | `execution/`, `directives/`는 workspace, `.env` 등은 repo root |
| Shared provider test mocks | TTS provider 테스트 공유 mock 누수 | 테스트별 mock reset |
| Duplicate project roots | `projects/shorts-maker-v2`와 레거시 root 디렉토리 공존 | `projects/` 경로에서 실행 |
| Hanwoo install peers | next-auth@5 beta가 Next 16 peer 미선언 | `npm install --legacy-peer-deps` |

## Recent Quality Notes

- 테스트 통계/커버리지는 `workspace/execution/qaqc_history_db.py`로 쿼리하세요.
