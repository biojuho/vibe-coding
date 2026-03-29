# CONTEXT.md

## Project

- Name: `shorts-maker-v2`
- Goal: AI-driven YouTube Shorts generation pipeline
- Active V2 code: `src/shorts_maker_v2`
- Legacy/V1 renderer still present: `ShortsFactory`

## Stack

- Python 3.14
- MoviePy 2.x + FFmpeg
- Edge TTS
- Provider router with Google/OpenAI/other fallbacks
- Image/video providers such as Pexels, Gemini, DALL-E

## Current Coverage State (2026-03-29)

- Latest full-package baseline for `src/shorts_maker_v2`: **`91%`**
  - Verified on `2026-03-28` with `coverage run --source=src/shorts_maker_v2 -m pytest tests/unit tests/integration -q -o addopts=`
  - Result: `1217 passed, 13 skipped, 1 warning`
- Key targeted modules already remeasured in the latest uplift:
  - `pipeline/script_step.py`: `93%`
  - `pipeline/orchestrator.py`: `97%`
  - `pipeline/render_step.py`: `87%`
  - `pipeline/media_step.py`: `90%`
  - `utils/dashboard.py`: `97%`
  - `providers/google_music_client.py`: `99%`
  - `providers/pexels_client.py`: `95%`
  - `providers/unsplash_client.py`: `100%`
  - `render/video_renderer.py`: `100%`
  - `utils/style_tracker.py`: `100%`
- Thumbnail hardening revalidation on `2026-03-29`:
  - `tests/unit/test_thumbnail_step.py`: `39 passed, 1 warning`
  - Isolated `thumbnail_step.py`: `88%`
  - Thumbnail-focused orchestrator subset: `2 passed, 35 deselected, 1 warning`
- Static caption rendering follow-up on `2026-03-29`:
  - `tests/unit/test_caption_pillow.py`: `10 passed, 1 warning`
  - `tests/unit/test_i18n_en_us_smoke.py`: `1 passed, 1 warning`
  - `tests/unit/test_render_step_phase5.py -k "render_static_caption or caption_y"`: `4 passed, 14 deselected, 1 warning`
  - `tests/unit/test_render_step_phase5.py -k "caption_y"`: `2 passed, 16 deselected, 1 warning`

## Important Module Snapshot

- `pipeline/thumbnail_step.py`
  - Temp frame / DALL-E / Gemini / Canva artifacts now derive from the final thumbnail filename.
  - Background-image selection is passed through method calls instead of mutable instance state.
  - Long single-token titles now fall back to char-level wrapping.
  - Canva downloads now fail fast on HTTP errors.
- `render/caption_pillow.py`
  - Static captions now render their configured background box (`bg_color`, `bg_opacity`, `bg_radius`).
  - Glow compositing is isolated to the text layer so neon styles do not bloom around the whole box.
  - Horizontal placement now compensates for Pillow bbox `left` offsets to reduce clipping on stroked glyphs.
  - `center_hook` is now wired for hook scenes: centered safe-zone placement when enabled, safe-zone-clamped lower-third placement when disabled.
  - Stress-test coverage now includes long single-token wrapping, safe-zone centering, hook center/lower-third semantics, top clamp for oversized captions, and tall multiline rendering.
- `tests/unit/test_tts_providers.py`
  - Shared `torch` / `torchaudio` MagicMocks are reset per test to reduce cross-test leakage.

## Test Layout

- Default pytest collection is now limited to `tests/` via `pytest.ini`:
  - `testpaths = tests`
- Default coverage target in `pytest.ini` is now V2-only:
  - `--cov=src/shorts_maker_v2`
- Archived V1 legacy tests live in:
  - `archive/tests_legacy_v1/`
- Important caveat:
  - Most direct ShortsFactory tests have been archived out of `tests/`
  - Intentional ShortsFactory references still remain in V2 bridge/fallback tests such as `tests/unit/test_render_step.py`, `tests/unit/test_render_step_phase5.py`, and `tests/unit/test_orchestrator_unit.py`

## Reliable Coverage Commands

- Set:
  - `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`
- Prefer:
  - `python -m coverage run --source=src/shorts_maker_v2 -m pytest ... -o addopts=`
- For aggregate package coverage, append known passing suites in chunks with:
  - `coverage run --append ...`
- On this Windows machine, direct-file coverage reports can misbehave; safer fallback:
  - `coverage report -m --include="*module_name.py"`

## Current High-Value Test Files Added/Expanded

- `tests/unit/test_script_step.py`
- `tests/unit/test_orchestrator_unit.py`
- `tests/unit/test_render_step.py`
- `tests/unit/test_media_step_branches.py`
- `tests/unit/test_thumbnail_step.py`
- `tests/unit/test_caption_pillow.py`

## Landmines

- The worktree is very dirty at the monorepo level. Do not revert unrelated files.
- `pytest-cov` is less reliable here than plain `coverage run` because duplicate root/project paths can confuse path mapping.
- Duplicate project roots exist on this machine (`projects/shorts-maker-v2` and a legacy root-level copy). Run tests from `projects/shorts-maker-v2`.
- When `coverage report` shows a direct Windows file path as `0%`, use `coverage report -m --include="*module_name.py"` instead.
- Thumbnail generation used to create fixed-name temp files in shared output directories; keep temp artifacts derived from the final output stem for repeatability.
- `tests/legacy/__pycache__/` may still exist as an untracked cache directory, but archived V1 tests are no longer collected by default.
