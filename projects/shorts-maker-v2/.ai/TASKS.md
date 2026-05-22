# TASKS.md

## TODO

- [ ] Decide whether archived ShortsFactory compatibility tests should live in a separate optional CI/manual lane. Owner: TBD
- [ ] Remove or ignore the leftover `tests/legacy/__pycache__/` directory for tree cleanliness. Owner: TBD
- [ ] Evaluate a PR-level full unit/integration test gate so refactors like T-407 cannot land with broken tests. Owner: TBD
- [ ] Run the retention simulator E2E once with a real LLM to eyeball predicted-curve quality (paid tokens — needs user approval). Owner: TBD

## IN_PROGRESS

- [ ] None

## DONE

- [x] T-410 Replace `gate_safe_zone` char-count caption-height estimation (`len//20`, a `shorts-subtitle-safezone` anti-pattern) with pixel-accurate, mode-aware `estimate_caption_height` that mirrors the renderer; orchestrator passes real RenderStep styles + canvas size; add render-PNG `==` drift-guard tests (2026-05-23, Claude) — `1aeb9eaa`
- [x] T-409 Sync `shorts-tts-quality` skill voice table with `channel_profiles.yaml` SSOT + add `test_skill_config_consistency.py` drift guard + fix misleading `freesound_client` comment (2026-05-22, Claude) — `d775a360`
- [x] T-408 Restore `channel_key` in the edge-tts TTS path and repair 8 stale test patch targets broken by the T-407 refactor (2026-05-22, Claude) — `c9d1493f`
- [x] T-323 Surface `gate_safe_zone` QC HOLD in `manifest.degraded_steps` + add direct `gate_safe_zone` regression tests (2026-05-22, Claude) — `9e8531da`
- [x] T-322 Stamp `scene_id` on media failure records for per-scene traceability in `manifest.failed_steps` (2026-05-22, Claude) — `ce5808a2`
- [x] T-321 Ship synthetic-audience retention simulator with closed-loop auto-fix (`retention_simulator`/`retention_autofix`/`retention_report`) (2026-05-22, Claude) — `e194784b`
- [x] T-320 Integrate OpenVoice v2 local high-fidelity voice cloning backend with MeloTTS, fallback to edge-tts, configure config.py & audio_mixin.py, and add unit tests (2026-05-20, Antigravity)
- [x] T-085 Add a render-step regression check for hook captions when `center_hook=False` so lower-third placement is validated beyond the helper math (2026-03-29, Codex)
- [x] T-084 Wire `center_hook` into `calculate_safe_position()` with safe-zone-aware lower-third hook placement and regression coverage (2026-03-29, Codex)
- [x] T-083 Add stress tests for tall multi-line static captions and safe-zone edge cases in `render/caption_pillow.py` (2026-03-29, Codex)
- [x] T-082 Push the next output-quality pass on `render/caption_pillow.py` and restore static caption background-box rendering (2026-03-29, Codex)
- [x] T-081 Extend `thumbnail_step.py` live-path hardening with Canva OAuth refresh coverage, video-frame extraction cleanup coverage, and fail-fast HTTP download handling (2026-03-29, Codex)
- [x] T-080 Harden `thumbnail_step.py` temp-artifact cleanup and long-title wrapping (2026-03-29, Codex)
- [x] T-072 Commit expanded V2 pipeline coverage tests for `script_step`, `orchestrator`, `render_step`, and `media_step` (`95b3421`) after validating `218 passed, 1 warning` (2026-03-27, Codex)
- [x] T-071 Remove `--cov=ShortsFactory` from default pytest coverage and archive remaining direct ShortsFactory tests from `tests/unit/` and `tests/integration/` (2026-03-27, Codex)
- [x] T-070 Archive `tests/legacy` V1 tests into `archive/tests_legacy_v1` and exclude them from default collection with `testpaths = tests` (2026-03-27, Codex)
- [x] T-069 Broaden overall `src/shorts_maker_v2` coverage using existing provider/render/utils suites; verified `82%` total coverage (2026-03-27, Codex)
- [x] T-068 Raise `pipeline/media_step.py` targeted coverage to `90%` with branch-heavy mock tests (2026-03-27, Codex)
- [x] T-067 Re-measure aggregate coverage for `src/shorts_maker_v2/pipeline`; verified `87%` total pipeline coverage (2026-03-27, Codex)
- [x] T-066 Raise `pipeline/render_step.py` targeted coverage to `88%` (2026-03-27, Codex)
- [x] T-065 Raise `pipeline/orchestrator.py` targeted coverage to `97%` (2026-03-27, Codex)
- [x] T-063 Raise `pipeline/script_step.py` targeted coverage to `93%` (2026-03-27, Codex)
