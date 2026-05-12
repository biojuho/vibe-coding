# GOAL - Active Workspace Goal

> Shared current goal for Claude Code, Codex, Gemini, and other AI tools.

## Active Goal

- Status: active
- Goal: Keep the user's current goal visible at session start and across handoffs.
- Owner: Codex
- Started: 2026-05-12
- Success: `python execution/session_orient.py` reports this active goal, and future tools can update this file when the goal changes.

## Notes

- Keep exactly one active goal here.
- Move completed goals into `.ai/SESSION_LOG.md` during session closeout.
- If no goal is active, set `Status: inactive` instead of deleting the file.
