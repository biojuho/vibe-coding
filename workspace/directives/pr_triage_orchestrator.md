# PR Triage Orchestrator

Run a higher-level, read-only PR triage lane on top of the isolated worktree
helper when we want validation artifacts, not just a detached checkout.

## Why

Use this when:

- the repo is dirty but we still need a safe PR-style validation lane
- we want repo-specific default checks without hand-picking commands each time
- we need durable JSON + log artifacts for later review or downstream routing

This directive extends `pr_triage_worktree.md`; it does not replace it.
`pr_triage_worktree.py` remains the low-level isolation primitive, while this
orchestrator adds profile selection plus read-only validation.

## Inputs

- `repo_path`: local git repo path, for example `projects/word-chain`
- `head_ref`: branch, tag, or commit to triage
- `base_ref`: optional base branch for merge-conflict preflight
- `label`: optional stable identifier such as `pr-123`
- `profile`: optional override (`auto` by default)
- `metadata_json`: optional JSON object with extra triage metadata
- `keep_worktree`: optional flag to preserve the linked worktree for manual follow-up

## Execution Tool

- `workspace/execution/pr_triage_orchestrator.py`
- lower-level helper: `workspace/execution/pr_triage_worktree.py`

## Output

The orchestrator creates the same session root as the low-level helper:

- `.tmp/pr_triage_worktrees/<repo-name>/<label>-<timestamp>/`

Artifacts:

- `manifest.json`: session metadata from the isolation helper
- `conflict-state.json`: optional merge-conflict preflight result
- `triage-report.json`: selected profile, per-command results, cleanup state
- `logs/*.log`: stdout/stderr logs for each validation command

By default, the linked `repo/` worktree is removed after validation while the
session folder and report artifacts remain. Use `--keep-worktree` only when a
human still needs the isolated checkout.

## Standard Flow

1. Run the triage orchestrator.

```bash
python workspace/execution/pr_triage_orchestrator.py run \
  --repo-path projects/word-chain \
  --head-ref feature/ui-fix \
  --base-ref main \
  --label pr-123
```

2. Read `triage-report.json`.

- `profile.name` tells you which repo-specific validation lane was chosen.
- `validation.status` is the overall result for the command bundle.
- `validation.results[]` contains each command, status, duration, and log path.
- `manifest.conflict_check.status` still reports merge-preflight state.

3. Inspect `logs/*.log` when a command failed or timed out.

4. If `--keep-worktree` was used, clean up later.

```bash
python workspace/execution/pr_triage_orchestrator.py cleanup \
  --session-dir .tmp/pr_triage_worktrees/word-chain/pr-123-20260331T120000Z \
  --keep-session-dir
```

## Default Profile Rules

- `blind-to-x`: unit + integration pytest slices
- `shorts-maker-v2`: pytest + Ruff
- `hanwoo-dashboard`: `npm run lint`, `npm run build`
- `knowledge-dashboard`: `npm run lint`, `npm run build`
- `word-chain`: `npm run lint`, `npm run test`, `npm run build`
- `suika-game-v2`: `npm run build`
- unknown Python repos: generic pytest / Ruff inference
- unknown Node repos: generic `lint` / `test` / `build` script inference

## Guardrails

- Keep this flow local-only and read-only relative to the user's active checkout.
- Do not add GitHub API writes, PR comments, merges, fetches, or pushes here.
- Node-based validation reuses the source repo's installed `node_modules` when
  available. If those dependencies are missing, the orchestrator marks the step
  as `SKIP` rather than mutating the repo to install packages.
- Treat the entire session directory as intermediate state under `.tmp/`.

## Edge Cases

- Unknown repo shape: pass `--profile` explicitly or add a new profile builder.
- Missing `node_modules` in a Node repo: command result becomes `SKIP`.
- Validation timeout: the triage report records `TIMEOUT` and still preserves logs.
- Manual follow-up required: use `--keep-worktree`, then clean up later.
