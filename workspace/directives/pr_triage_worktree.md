# PR Triage Worktree

Prepare an isolated git worktree for PR-style review, validation, and conflict
checks without touching the user's active checkout.

## Why

Use this when:

- the main repo is dirty and we still need a safe validation lane
- we want to compare a candidate branch against a base branch
- we need a reproducible JSON artifact that downstream orchestration can read

This directive intentionally adopts only the safe isolation layer from ACPX's
`pr-triage` example. The local-first Vibe Coding workspace does not enable
remote side effects by default, so this flow does not fetch, push, comment on
GitHub PRs, close PRs, or approve CI workflow runs.

## Inputs

- `repo_path`: local git repo path, for example `projects/hanwoo-dashboard`
- `head_ref`: branch, tag, or commit to triage
- `base_ref`: optional base branch for merge-conflict preflight
- `label`: optional stable identifier such as `pr-123`
- `metadata_json`: optional JSON object with extra PR metadata

## Execution Tool

- `workspace/execution/pr_triage_worktree.py`

## Output

The helper creates a session under:

- `.tmp/pr_triage_worktrees/<repo-name>/<label>-<timestamp>/`

Artifacts:

- `manifest.json`: repo path, refs, SHAs, worktree path, and metadata
- `conflict-state.json`: merge preflight result and conflicted files
- `repo/`: linked git worktree checked out at the requested head ref

## Standard Flow

1. Prepare the isolated worktree.

```bash
python workspace/execution/pr_triage_worktree.py prepare \
  --repo-path projects/hanwoo-dashboard \
  --head-ref feature/my-branch \
  --base-ref main \
  --label pr-123
```

2. Read `manifest.json` and `conflict-state.json`.

- If `conflict_check.status` is `clean`, proceed with validation or review.
- If `conflict_check.status` is `conflicted`, keep all write-heavy work inside
  the isolated worktree and decide whether the conflict is mechanical or needs
  human judgment.
- If `conflict_check.status` is `skipped`, no base merge preflight was run.

3. Run the next lane inside the isolated `repo/` path.

- local tests
- repo-specific lint or typecheck
- code review or manual investigation
- optional higher-level orchestration that reads the JSON artifacts

4. Clean up the session when done.

```bash
python workspace/execution/pr_triage_worktree.py cleanup \
  --session-dir .tmp/pr_triage_worktrees/hanwoo-dashboard/pr-123-20260331T120000Z
```

## Guardrails

- Treat the session directory as an intermediate artifact under `.tmp/`.
- Do not treat this helper as permission to fetch, push, merge, or close PRs.
- Keep GitHub API write actions in a separate, explicitly approved directive if
  they are ever added later.
- If a repo is outside the Vibe Coding root, the helper still works, but the
  session artifacts remain under this workspace's `.tmp/` folder.

## Edge Cases

- `head_ref` or `base_ref` missing: fix the local refs first, then rerun.
- Base merge has conflicts: the helper records them and restores the worktree to
  the original detached HEAD state.
- Cleanup after partial manual edits: `cleanup` uses `git worktree remove
  --force`, so treat the isolated worktree as disposable.
