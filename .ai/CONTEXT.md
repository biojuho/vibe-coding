# Vibe Coding Context

> Local-only workspace. Do not push, pull, or deploy from this repo unless the user explicitly changes that policy.

## Workspace Summary

- Name: `Vibe Coding (Joolife)`
- Purpose: shared AI tooling plus multiple product projects
- Root runtime: Python 3.14, `pytest`, `ruff`, `venv`, `.env`
- Canonical path contract:
  - `workspace/...` for root-owned automation and docs
  - `projects/<name>/...` for product repos
  - `infrastructure/...` for MCP/services

## Active Projects

| Project | Status | Stack | Canonical Path |
|---|---|---|---|
| `blind-to-x` | Active | Python pipeline, Notion, Cloudinary | `projects/blind-to-x` |
| `shorts-maker-v2` | Active | Python, MoviePy, Edge TTS, OpenAI, Google GenAI, Pillow | `projects/shorts-maker-v2` |
| `hanwoo-dashboard` | Active | Next.js, React, Prisma, Tailwind | `projects/hanwoo-dashboard` |
| `knowledge-dashboard` | Maintenance | Next.js, TypeScript, Tailwind | `projects/knowledge-dashboard` |
| `suika-game-v2` | Frozen | Vite, Vanilla JS, Matter.js | `projects/suika-game-v2` |
| `word-chain` | Frozen | React, Vite, Tailwind | `projects/word-chain` |

## Canonical Structure

```text
Vibe coding/
├── .ai/
├── .agents/
├── .claude/
├── .github/
├── .tmp/
├── _archive/
├── infrastructure/
├── projects/
│   ├── blind-to-x/
│   ├── hanwoo-dashboard/
│   ├── knowledge-dashboard/
│   ├── shorts-maker-v2/
│   ├── suika-game-v2/
│   └── word-chain/
├── workspace/
│   ├── directives/
│   ├── execution/
│   │   └── pages/
│   ├── scripts/
│   └── tests/
└── venv/
```

## Current State

> ⚠️ [상태 이전 및 분리 알림]
> - 매일 변동되는 작업 상태(진행 중인 이슈, 테스트 커버리지)
> - 일시적인 버그나 회피 패턴(Minefield)
> - 최신 품질 및 배포 로그 (Quality Notes)
> 
> 해당 내용들은 이제 토큰 최적화를 위해 **`.ai/STATUS.md`** 파일에서 관리됩니다.
> (※ 관련결정사항: [ADR-018 in DECISIONS.md])
> 최근 `blind-to-x` staged-pipeline cleanup 상태(`T-091`, 2026-03-30)도 `STATUS.md`와 `HANDOFF.md`를 우선 참조하세요.

## Shared Services

- MCP servers are configured via `.mcp.json` and related files at repo root.
- Telegram bot and other external providers use root `.env`.
- Shared operator ladder on `2026-03-31`: `workspace/scripts/doctor.py` = `FAST` readiness, `workspace/scripts/quality_gate.py` = `STANDARD` local validation, `workspace/execution/qaqc_runner.py` = `DEEP` shared approval, and `workspace/execution/health_check.py` = `DIAGNOSTIC` drill-down. `workspace/directives/operator_workflow.md` is the canonical guide.
- Shared control-plane health is checked through `workspace/execution/health_check.py`, with governance-specific validation implemented in `workspace/execution/governance_checks.py` and surfaced in `workspace/execution/qaqc_runner.py`.
- `.github/workflows/full-test-matrix.yml` and `.github/workflows/root-quality-gate.yml` were realigned on `2026-04-01` to the live repo layout: workspace checks come from `workspace/`, Python project jobs run from `projects/blind-to-x` and `projects/shorts-maker-v2`, and frontend jobs run from `projects/hanwoo-dashboard` plus `projects/knowledge-dashboard`.
- `workspace/execution/vibe_debt_auditor.py` now walks all parent `tests/` directories when estimating `test_gap`, which avoids false positives for modules under `workspace/execution/**` whose matching tests live in `workspace/tests/`.
- `workspace/execution/repo_map.py` and `workspace/execution/context_selector.py` now provide deterministic repo-map scoring plus budgeted context selection for `workspace/execution/graph_engine.py`. Repo-map summaries are persisted in `.tmp/repo_map_cache.db` so unchanged files can be reused across builder instances. The selector defaults to `workspace/` unless a prompt explicitly targets `projects/` or `infrastructure/`.
- `workspace/execution/pr_triage_worktree.py` now provides a local-only PR-style isolation primitive: it creates disposable linked worktrees under `.tmp/pr_triage_worktrees/`, records `manifest.json` plus `conflict-state.json`, and avoids implicit remote GitHub side effects.
- `workspace/execution/pr_triage_orchestrator.py` now wraps that isolation helper with repo-specific validation profiles, per-command logs, and a durable `triage-report.json` artifact while defaulting to cleanup that removes only the linked worktree and keeps the session folder for review.
- `infrastructure/` remains top-level and is not part of `workspace/`.
- The active audit-owned coverage follow-up is still `T-100`: `projects/blind-to-x` improved to **71%** on `2026-03-31`, while `projects/shorts-maker-v2` remains above its floor at **91%**.
- `projects/shorts-maker-v2` has a dual package shape: repo-root `shorts_maker_v2/` is a namespace bridge in front of `src/shorts_maker_v2/`. Tests import the bridge first, so package-level exports like `run_cli` must be kept aligned there.
- `projects/blind-to-x/pipeline/draft_cache.py` now applies SQLite `busy_timeout` plus a best-effort WAL checkpoint after commit so cached draft writes are more visible to fresh connections in follow-up reads. `T-119` is closed in the current worktree after sequential reruns.
- The former `T-116` root import-pollution blocker no longer reproduces in the targeted `workspace/tests` rerun on `2026-04-01`, but the next full shared QC should still confirm the end-to-end root baseline.
- A new local-only follow-up `T-121` tracks `projects/blind-to-x/tests/unit/test_main.py` hitting `KeyboardInterrupt` under the current terminal wrapper. Treat it as a harness/verification issue until a clean reproduction proves a product regression.
- Roadmap-style directives are reference context by default; active execution priority is expected to come from `.ai/TASKS.md` and `.ai/HANDOFF.md`.
