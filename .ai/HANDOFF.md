# HANDOFF - AI Context Relay

> See `SESSION_LOG.md` for detailed history and `DECISIONS.md` for settled architecture decisions.

## Last Session

| Field | Value |
|------|------|
| Date | 2026-03-26 |
| Tool | Codex |
| Work | Implemented Blind-to-X X curation and draft quality redesign |

## Current State

- Blind-to-X redesign is now live under `projects/blind-to-x`.
  - Candidate selection now uses `pre_editorial_score`
  - X editorial brief fields now include `selection_summary`, `emotion_lane`, `empathy_anchor`, and `spinoff_angle`
  - Draft generation is fail-closed on provider errors, missing tags, and low-Korean outputs
  - few-shot fallback order is now `performance -> approved -> YAML`
- Verification for this change:
  - Blind-to-X targeted unit suite: `103 passed, 1 warning`
  - OpenAI draft generation was aligned to the current SDK via `chat.completions`
- Shared QC status from earlier today is still the baseline:
  - root: `919 passed, 1 skipped`
  - blind-to-x: standalone unit/integration pass, shared runner timeout still unresolved
  - shorts-maker-v2: full-suite flaky failure still unresolved
- Canonical layout remains `workspace/` + `projects/` + `infrastructure/`

## Next Priorities

1. T-057: fix blind-to-x false-negative timeout in `workspace/execution/qaqc_runner.py`
2. T-058: investigate `shorts-maker-v2` full-suite order-dependent failure
3. T-059: fix `knowledge-dashboard` lint errors
4. T-056: verify next natural Blind-to-X scheduled run creates `scheduled_*.log` and `LastTaskResult=0`
5. T-060: clean up remaining Ruff issues after canonical refactor

## Notes

- Most of `git status` is still structural churn from the canonical move to `workspace/` and `projects/`.
- Blind-to-X work must be reviewed under `projects/blind-to-x`; do not treat deleted root `blind-to-x/` paths as regressions.
- The blind-to-x `TIMEOUT` in shared QC is more likely a runner budget issue than a confirmed code regression.
- `shorts-maker-v2` failures reproduce only in full-suite runs and pass in isolated reruns; suspect leaked global state first.
