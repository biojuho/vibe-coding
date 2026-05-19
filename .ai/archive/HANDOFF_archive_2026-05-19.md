## Rotation 2026-05-19 (archived addenda older than 2026-05-16)

| Field | Value |
|---|---|
| Date | 2026-05-15 |
| Tool | Gemini (Antigravity) |
| Work | **워크스페이스 위생 심화 정비**. 사용자 `/goal` 요청으로 추가 필요 작업 탐색 후 즉시 실행. (1) HANDOFF 심층 정리: 이전 Codex 로테이션(→160줄) 이후에도 남아있던 4월 old addenda + 중복 5/15 addenda를 아카이브하여 **192줄→32줄**로 압축. (2) Dirty 파일 정리: `blind-to-x/_upload.py`(EOL-only), `knowledge-dashboard/qaqc_result.json`(내용 diff 없음) 2개를 `git checkout --`로 정리. (3) 시스템 헬스 전수 검증: 제품 준비도 92/100 (blocked=hanwoo T-251만), Skill 헬스 100/100 (42/42), QC 아티팩트 5개 프로젝트 포함 확인. (4) 새 blind-to-x WIP 6파일(다른 도구 작업) 발견 → 미간섭 원칙 준수. |
| Next Priorities | T-251 사용자 승인 대기(Supabase 비밀번호 리셋). `main`이 `origin/main` 대비 82커밋 ahead — 사용자 승인 후 push 필요. blind-to-x 6파일 WIP는 해당 도구가 커밋할 때까지 대기. |

| Field | Value |
|---|---|
| Date | 2026-05-15 |
| Tool | Codex |
| Work | Re-ran the only remaining TODO after the user said "complete everything". `projects/hanwoo-dashboard/scripts/prisma7-runtime-test.mjs` now prints Prisma error `name`, `code`, `meta`, and nested `cause` details so live DB blockers are actionable instead of blank. |
| Next Priorities | Verification: `npm.cmd run db:prisma7-test` passed offline (`14 passed, 0 failed, 1 skipped`). `npm.cmd run db:prisma7-test -- --live` was retried with escalated network access and still failed at connection health with `P2010` / `XX000` / `(ENOTFOUND) tenant/user postgres.fuemeqmigptwfzqvrpjf not found`. T-251 remains user-owned: reset/resync the Supabase database password in the Supabase Dashboard, then rerun the live command. No push was performed. |

| Field | Value |
|---|---|
| Date | 2026-05-15 |
| Tool | Codex |
| Work | **T-302 + T-303 completed after user said "다 처리해"**. Finished the remaining local WIP and workspace hygiene goal. `projects/shorts-maker-v2/tests/unit/test_orchestrator_unit.py` now covers SemanticQC orchestration: disabled path, pass manifest persistence, degraded non-blocking degraded-step metadata, error verdict persistence, and exception swallowing. Applied HANDOFF size cleanup with `python execution/handoff_rotator.py --json --keep-days 0`, moving 44 older addenda into `.ai/archive/HANDOFF_archive_2026-05-15.md` and reducing HANDOFF to 160 lines. Cleared the EOL-only dirty state in `projects/blind-to-x/pipeline/notion/_upload.py` without content changes. Closed `.ai/GOAL.md` back to inactive. |
| Next Priorities | Verification passed: `python -m pytest --no-cov tests/unit/test_orchestrator_unit.py -q --tb=short --maxfail=1 --basetemp ../../.tmp/pytest-shorts-orchestrator-unit` -> `49 passed, 2 warnings`; targeted Ruff passed for the SemanticQC/orchestrator slice; `python execution/handoff_rotator.py --check --json --keep-days 0` predicted 44 archivable addenda before rotation; SESSION_LOG is 396 lines, under the 1000-line limit. Remaining blocker is still T-251, which requires the user to reset/resync the Supabase DB password before live Prisma E2E can run. No push was performed. |

| Field | Value |
|---|---|
| Date | 2026-05-15 |
| Tool | Codex |
| Work | **T-301 knowledge-dashboard readiness/QC signal repair completed**. Fixed the signal path by registering `knowledge-dashboard` in `workspace/execution/qaqc_runner.py`, removing the `root → knowledge-dashboard` fallback in `execution/product_readiness_score.py`, preserving existing project results when a default targeted deep QA/QC run updates the canonical artifact, and adding focused regression coverage. |
| Next Priorities | Verification passed: focused tests `31 passed`; targeted Ruff clean; `python workspace/execution/qaqc_runner.py --skip-infra --skip-debt` -> `APPROVED`, `4646 passed`. Readiness: overall `92 / blocked` only because T-251 is user-owned. |
