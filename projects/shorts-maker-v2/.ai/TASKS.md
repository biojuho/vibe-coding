# TASKS.md

## TODO

- [ ] Track upstream `google-genai` `_UnionGenericAlias` DeprecationWarning on Python 3.14/3.17; current 1.69.0 and latest 2.8.0 both reproduce it, official issue googleapis/python-genai#1640 is open, and fix PR #1939 is not merged, so no project-side root fix was applied. Owner: TBD
- [ ] Run the retention simulator E2E once with a real LLM to eyeball predicted-curve quality (paid tokens — needs user approval). Owner: TBD

## IN_PROGRESS

- [ ] None

## DONE (Latest 5)

- [x] T-2374 Continue shared rendering-helper refactor loop: convert `history_timeline.py` and `psychology_quiz.py` to `tools/_rendering_helpers.py` with focused warning-as-error render tests, standalone `--help` smoke, Ruff, diff-check, and project QC green (2026-06-12, Codex)
- [x] T-2373 Continue shared rendering-helper refactor loop: convert `health_mental_message.py` and `history_mystery.py` to `tools/_rendering_helpers.py` with focused warning-as-error render tests, standalone smoke, Ruff, diff-check, and project QC green (2026-06-12, Codex)
- [x] T-2372 Continue the refactor loop with font/rendering helper consolidation: add `tools/_rendering_helpers.py`, convert `space_scale.py`, `space_fact_bomb.py`, `health_do_vs_dont.py`, `health_medical_study.py`, and finish `history_fact_shorts.py` local font helper extraction while keeping project QC green (2026-06-12, Codex)
- [x] T-2371 Continue behavior-preserving Pillow/renderer refactor loop after user approval: extract explicit RGB/RGBA array-to-image helpers across generated tools, extend warning-as-error renderer coverage to health mental message and space scale, and keep project QC green (2026-06-11, Codex)
- [x] T-2370 Refresh `/goal` debug-loop inventory with realistic helper timeout: classify the earlier 5s input-evidence failure as an execution-timeout artifact, regenerate `.tmp/debug-loop-known-bugs-current.{json,md}`, and confirm no actionable local project bug remains outside authorization/external blockers (2026-06-11, Codex)
