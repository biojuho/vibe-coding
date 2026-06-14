## Rotation 2026-06-12 (archived DONE rows beyond the newest 5)

- [x] T-2367 Complete the Pillow `Image.fromarray(..., mode)` sweep across demo tool renderers: reproduce seven remaining warning-as-error failures, remove explicit mode arguments from health/history/psychology/space tools, add `tests/unit/test_tool_pillow_deprecations.py`, and confirm no local `Image.fromarray(..., "mode")` pattern remains (2026-06-11, Codex)

## Rotation 2026-06-12 (archived DONE rows beyond the newest 5)

- [x] T-2368 Fix `execution/handoff_rotator.py --repo-root projects/shorts-maker-v2` falsely reporting `Current Addendum heading not found` when the project HANDOFF heading has a date/tool suffix; allow suffixed headings and add workspace rotator regression tests (2026-06-11, Codex)

## Rotation 2026-06-12 (archived DONE rows beyond the newest 5)

- [x] T-2369 Fix `execution/tasks_done_rotator.py --repo-root projects/shorts-maker-v2` ignoring checklist-style DONE entries; support `- [x] T-####` rows, normalize plain `## DONE` headings on rotation, and add workspace regression tests (2026-06-11, Codex)
