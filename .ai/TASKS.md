# TASKS - AI Kanban Board

> Read this file at session start and update it before ending the session.

## TODO

| ID | Task | Owner | Priority | Created |
|----|------|-------|----------|---------|
| T-124 | Add frontend smoke coverage for `projects/hanwoo-dashboard` and `projects/knowledge-dashboard` so CI validates auth, payment, and dashboard flows instead of only `lint` and `build`. | Codex | High | 2026-04-01 |
| T-123 | Replace `projects/knowledge-dashboard/public/*.json` data exposure with authenticated server/API delivery and separate internal-only telemetry from public dashboard data. | Codex | High | 2026-04-01 |
| T-121 | Investigate the local-only `KeyboardInterrupt` / runner interruption when `projects/blind-to-x/tests/unit/test_main.py` runs under this terminal wrapper, and confirm whether it is a harness artifact or a real `main.py` regression. | Codex | Medium | 2026-04-01 |
| T-120 | Fix `test_auto_schedule_paths.py::test_n8n_bridge_defaults_use_canonical_paths` failing due to `ModuleNotFoundError: No module named 'fastapi'`; apply `pytest.importorskip("fastapi")` or add `fastapi` to the workspace dev dependencies. | Antigravity | Medium | 2026-04-01 |
| T-116 | Confirm and, if still needed, fix the former root QC blocker in `workspace/tests` where `test_shorts_manager_helpers.py` polluted `sys.modules["path_contract"]`; the targeted rerun is green in the current worktree, so the next shared QC should verify whether this is already resolved. | Codex | High | 2026-04-01 |

## IN_PROGRESS

| ID | Task | Owner | Started | Notes |
|----|------|-------|---------|-------|
| T-100 | Raise the remaining project coverage follow-up from the system audit so `shorts-maker-v2` and `blind-to-x` reach their documented target floors. | Claude | 2026-03-31 | `shorts-maker-v2` coverage still pending. |

## DONE (Latest 5)

| ID | Task | Completed By | Completed |
|----|------|--------------|-----------|
| T-122 | Hardened `projects/hanwoo-dashboard` auth and payment boundaries: real server-side auth guards now protect dashboard/actions/payment routes, the proxy delegates to `Auth.js` session authorization, checkout uses a server-prepared order, and payment confirm transactionally upserts `PaymentLog` plus `Subscription`. | Codex | 2026-04-01 |
| T-119 | Closed the latent `blind-to-x` CI regression follow-up: `test_cost_tracker_uses_persisted_daily_totals` now passes in the current worktree, `DraftCache` now uses `busy_timeout` plus a best-effort WAL checkpoint for deterministic fresh-connection reads, and the previously failing cache test / verified blind unit slices pass sequentially. | Codex | 2026-04-01 |
| T-critical | Resolved 2 critical issues from the third-party code review: the pytest collection name collision around `test_lyria_bgm_generator.py`, and the SQLite connection-leak pattern in `execution/content_db.py`. | Antigravity | 2026-04-01 |
| T-118 | Restored active-project CI coverage for the live repo layout by rewriting `.github/workflows/full-test-matrix.yml` and `.github/workflows/root-quality-gate.yml`, narrowing the workspace lint gate to the real control-plane files, fixing `shorts-maker-v2` lazy pydub/test import behavior, and mirroring the `run_cli` lazy export in the root bridge package. | Codex | 2026-04-01 |
| T-117 | Completed the `blind-to-x` draft/runtime refactor QA pass and closed the related approval follow-up after the final runtime and draft-generator hardening fixes. | Antigravity | 2026-04-01 |

## Rules

- Use IDs in the form `T-XXX`
- Move tasks from TODO -> IN_PROGRESS when started
- Move tasks from IN_PROGRESS -> DONE when completed
- Keep only the latest 5 items in DONE
- Add newly discovered follow-up work to TODO
