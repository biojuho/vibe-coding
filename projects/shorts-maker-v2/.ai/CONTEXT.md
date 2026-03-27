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

## Current Coverage State (2026-03-27)

- Verified V2 package coverage for `src/shorts_maker_v2`: `82%`
- Verified pipeline-only coverage for `src/shorts_maker_v2/pipeline`: `87%`
- Key targeted modules:
  - `pipeline/script_step.py`: `93%`
  - `pipeline/orchestrator.py`: `97%`
  - `pipeline/render_step.py`: `88%`
  - `pipeline/media_step.py`: `90%`

## Important Module Snapshot

- `cli.py`: `65%`
- `providers/edge_tts_client.py`: `94%`
- `providers/google_client.py`: `98%`
- `providers/llm_router.py`: `81%`
- `providers/pexels_client.py`: `44%`
- `providers/stock_media_manager.py`: `87%`
- `render/caption_pillow.py`: `76%`
- `render/karaoke.py`: `44%`
- `render/video_renderer.py`: `62%`
- `utils/content_calendar.py`: `86%`
- `utils/dashboard.py`: `73%`
- `utils/media_cache.py`: `84%`
- `utils/retry.py`: `85%`

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

## Landmines

- The worktree is very dirty at the monorepo level. Do not revert unrelated files.
- `pytest-cov` is less reliable here than plain `coverage run` because duplicate root/project paths can confuse path mapping.
- `tests/legacy/__pycache__/` may still exist as an untracked cache directory, but archived V1 tests are no longer collected by default.
