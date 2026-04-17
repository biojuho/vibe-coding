# 📋 AI 세션 로그

## 2026-04-17 | Gemini (Antigravity) | Phase 2 test split import fix (T-220)

### 작업 요약
`test_render_step_*.py` 4개 파일의 `ModuleNotFoundError` 수정. `tests/unit/` 디렉토리에 `__init__.py`가 없어 pytest가 `tests` 패키지를 인식하지 못하는 문제였음. `from tests.unit.conftest_render import ...` → `from conftest_render import ...` 로 직접 import 수정.

### 주요 작업
- `test_render_step_core.py:11` import 수정
- `test_render_step_captions.py:9` import 수정
- `test_render_step_effects.py:8` import 수정
- `test_render_step_audio_mix.py:13` import 수정
- `python -m ruff format` 4개 파일 포맷 적용

### 검증
- `python -m pytest tests/unit/ --no-cov -q` → **1293 passed, 12 skipped** (exit 0)

### 변경 파일
- `tests/unit/test_render_step_core.py`
- `tests/unit/test_render_step_captions.py`
- `tests/unit/test_render_step_effects.py`
- `tests/unit/test_render_step_audio_mix.py`

### 커밋
- `24a4434` `[shorts-maker-v2] Phase 2 test split 완료 (T-220): conftest_render.py import fix, 1293 tests passed`

---

## 2026-03-29 | Codex | render-step hook placement regression

### Summary
Closed the follow-up gap after the `center_hook` behavior change by adding a regression at the `RenderStep` call path.

### Key Changes
- `tests/unit/test_render_step.py`
  - Added a regression test that uses actual `RenderStep`-built styles to verify non-centered hook captions land in the safe lower-third path.
  - The same test also locks that body captions remain centered even though the shared base style still carries `center_hook=False`.
- No implementation change was needed in this pass; the goal was to prove the routing semantics outside the direct helper tests.

### Verification
- `..\..\venv\Scripts\python.exe -m pytest tests/unit/test_render_step.py -k "caption_y or safe_zone" -q -o addopts=` -> `3 passed, 104 deselected, 1 warning`
- `..\..\venv\Scripts\python.exe -m pytest tests/unit/test_render_step_phase5.py -k "render_static_caption or caption_y" -q -o addopts=` -> `4 passed, 14 deselected, 1 warning`
- `..\..\venv\Scripts\python.exe -m pytest tests/unit/test_caption_pillow.py -q -o addopts=` -> `10 passed, 1 warning`
- `..\..\venv\Scripts\python.exe -m ruff check tests/unit/test_render_step.py tests/unit/test_render_step_phase5.py tests/unit/test_caption_pillow.py src/shorts_maker_v2/render/caption_pillow.py` -> clean

### Changed Files
- `tests/unit/test_render_step.py`

## 2026-03-29 | Codex | center_hook safe-zone wiring

### Summary
Wired `center_hook` into `calculate_safe_position()` so hook captions can opt into lower-third placement without leaving the Shorts safe zone.

### Key Changes
- `src/shorts_maker_v2/render/caption_pillow.py`: `role="hook"` with `center_hook=True` stays centered in the safe area, while `center_hook=False` uses the legacy lower-third intent clamped inside the safe area.
- `tests/unit/test_caption_pillow.py`: added regression coverage for centered hook placement and safe lower-third hook placement.
- Non-hook roles intentionally keep the existing centered safe-zone behavior to avoid a broader visual shift.

### Verification
- `..\\..\\venv\\Scripts\\python.exe -m pytest tests/unit/test_caption_pillow.py -q -o addopts=` -> `10 passed, 1 warning`
- `..\\..\\venv\\Scripts\\python.exe -m pytest tests/unit/test_render_step_phase5.py -k "caption_y" -q -o addopts=` -> `2 passed, 16 deselected, 1 warning`
- `..\\..\\venv\\Scripts\\python.exe -m ruff check src/shorts_maker_v2/render/caption_pillow.py tests/unit/test_caption_pillow.py` -> clean

### Changed Files
- `src/shorts_maker_v2/render/caption_pillow.py`
- `tests/unit/test_caption_pillow.py`

## 2026-03-27 — Antigravity (테스트 커버리지 향상: Karaoke)

### 작업 요약
shorts-maker-v2 파이프라인의 카라오케 렌더링 모듈(`karaoke.py`)에 대한 유닛 테스트를 집중적으로 보강하여 해당 모듈의 커버리지를 97% 달성하고 버그를 해결했습니다.

### 주요 작업 내용
1.  **테스트 보강 및 버그 수정**:
    *   `src/shorts_maker_v2/render/karaoke.py`: 폰트 스케일링 로직(`_auto_scale_font`)을 테스트하기 위해 `unittest.mock.patch`를 사용하여 PIL 의존성 및 실제 폰트 파일 없이 검증하도록 개선.
    *   `tests/unit/test_karaoke_render.py`: Windows 환경의 `PermissionError`를 파일 컨텍스트 매니저 사용으로 해결.
    *   `tests/unit/test_karaoke_chunking.py`: 문장 분할, SSML 휴지 보정, 단어 청킹 로직에 대한 포괄적인 유닛 테스트 신규 작성.

2.  **레거시 테스트 정리 전략**:
    *   `tests/legacy/` 경로의 테스트가 V1 프레임워크(`ShortsFactory`) 기반임을 확인하고, 이를 V2 커버리지 목표에서 제외하기 위한 격리/삭제 전략 수립.

### 변경 파일
* `tests/unit/test_karaoke_render.py`
* `tests/unit/test_karaoke_chunking.py` (신규)

### 다음 단계
* `render_step.py` 또는 `script_step.py` 등 핵심 V2 파이프라인 모듈 테스트 보강
* 커버리지 45% (pyproject.toml `fail-under`) 목표 우선 달성, 이후 80% 상향
* `tests/legacy/` 디렉토리 완전 삭제 또는 아카이브 처리

---

## 2026-03-26 — Antigravity (유닛 테스트 오류 해결 및 QC 진행)

### 작업 요약
shorts-maker-v2 파이프라인의 잔여 유닛 테스트 실패 2건 및 린터 경고를 해결하고, 누락된 `pydub` 패키지를 설치하여 스킵되는 테스트를 복구했습니다.

### 주요 작업 내용
1.  **버그/오류 수정**:
    *   `src/shorts_maker_v2/pipeline/trend_discovery_step.py`: `ET.ParseError` 대신 `Exception`을 포괄적으로 캐치하도록 변경하여 예외 발생 시의 `UnboundLocalError` 해결.
    *   `tests/unit/test_render_step_phase5.py`, `tests/unit/test_render_utils.py`: `RenderStep._CAPTION_COMBOS`에 `closing` 요소가 추가되면서 튜플 길이가 3에서 4로 변경된 점을 반영하여 테스트 Assertions 수정.
    
2.  **의존성 및 코드 품질(QC)**:
    *   `pydub` 누락으로 인한 의도치 않은 테스트 스킵 방지를 위해 의존성 추가 설치.
    *   `ruff check --fix`를 실행하여 6건의 코드 컨벤션(Import 순서 및 미사용 모듈) 이슈 수정.
    *   전체 `pytest` 테스트 스위트 재실행을 통한 검증 수행.

### 변경 파일
* `src/shorts_maker_v2/pipeline/trend_discovery_step.py`
* `tests/unit/test_render_step_phase5.py`
* `tests/unit/test_render_utils.py`

### 다음 단계
* 운영 환경에서 트렌드 수집 소스의 API 응답 안정성 모니터링
* 76.34% 커버리지를 80% 이상으로 상향하기 위한 테스트 보강
* 레거시 테스트(`tests/legacy/`) 호환성 정리 (테스트 실행 시간 최적화 필요)

---

## 2026-03-26 — Antigravity (자동 주제 발굴 파이프라인 통합)

### 작업 요약
shorts-maker-v2 파이프라인에 트렌드 기반 주제 자동 발굴 및 인지 부조화 훅 제목 생성 기능을 통합. `--auto-topic` 옵션을 통한 직접 실행 지원 및 검증 완료.

### 주요 작업 내용
1.  **기능 구현**:
    *   `TrendDiscoveryStep`: Google Trends 및 RSS 피드를 활용하여 채널별 트렌드 키워드를 수집하고 스코어링하는 파이프라인 단계 구현.
    *   `TopicAngleGenerator`: LLM을 통해 채널별 '인지 부조화 훅 패턴'을 적용한 숏츠 제목 생성기 구현.
    *   `cli.py`: `--auto-topic` 및 `--auto-topic-list` 플래그 추가하여 파이프라인 연동.
    *   `execution/trend_scout.py`: 스탠드얼론 실행 스크립트 추가.

2.  **테스트 및 검증**:
    *   `test_trend_discovery_step.py`, `test_topic_angle_generator.py` 신규 작성 (총 64개 단위 테스트).
    *   전체 유닛 테스트: **1107 passed, 12 skipped, 0 failed** (커버리지 76.34%).

3.  **수정 사항**:
    *   `TopicAngleGenerator` 시스템 프롬프트의 JSON 템플릿 내 중괄호 이스케이프 처리하여 KeyError 해결.
    *   `trend_scout.py` AppConfig 로드 버그 수정.
    *   CLI 예외 메시지 업데이트 (`--resume` or `--auto-topic`).

### 변경 파일
* `src/shorts_maker_v2/pipeline/trend_discovery_step.py`
* `src/shorts_maker_v2/pipeline/topic_angle_generator.py`
* `src/shorts_maker_v2/cli.py`
* `execution/trend_scout.py`
* `tests/unit/test_trend_discovery_step.py`
* `tests/unit/test_topic_angle_generator.py`
* `tests/unit/test_cli.py`

### 다음 단계
* 운영 환경에서 트렌드 수집 소스의 API 응답 안정성 모니터링
* 76.34% 커버리지를 80% 이상으로 상향하기 위한 테스트 보강
* 레거시 테스트(`tests/legacy/`) 호환성 정리

---

## 세션 5: Phase 3 Orchestrator 분기 + Engine v2 고도화 + CI

- **날짜**: 2026-03-12
- **도구**: Antigravity (Gemini)
- **작업 요약**: Phase 3 Orchestrator render_from_plan() 호출 분기 추가, LayoutEngine v2 + ColorEngine v2 고도화, 비주얼 리그레션 CI 파이프라인 통합

### Phase 3: Orchestrator ShortsFactory 렌더링 분기

- `orchestrator.py`에 `use_shorts_factory` kwarg 추가 (기본: False)
- `_try_shorts_factory_render()` 정적 메서드: RenderAdapter → ShortsFactory 호출
- 실패 시 기존 `render_step.run()`으로 자동 폴백
- `ab_variant["renderer"]`에 "shorts_factory" | "native" 기록 (A/B 테스트용)

### LayoutEngine v2 (6개 신규 메서드)

| 메서드 | 설명 |
|--------|------|
| `numbered_list_layout` | 원형 넘버 배지 + 리스트 |
| `image_text_overlay` | 반투명 텍스트 버블 (RGBA) |
| `metric_dashboard` | KPI 대시보드 카드 (2열 그리드) |
| `step_by_step_layout` | 커넥터 라인 + 단계별 가이드 |
| `quote_card` | 좌측 악센트 바 + 큰따옴표 인용문 |
| `comparison_table` | 비교표 (교대 행 배경) |

### ColorEngine v2 (4개 신규 메서드)

| 메서드 | 설명 |
|--------|------|
| `apply_lut` | 1D LUT 기반 채널별 컬러 매핑 |
| `apply_role_grading` | 씬 역할별 자동 그레이딩 (hook/body/cta) |
| `blend_presets` | 두 프리셋 블렌딩 (비율 기반) |
| `auto_correct` | 프레임 휘도 분석 → 자동 밝기/대비 보정 |

### CI 파이프라인

- `.github/workflows/visual-regression.yml` 생성
- ShortsFactory 엔진/템플릿 변경 시 자동 실행
- 베이스라인 캐싱 + SSIM 요약 리포트 + HTML 아티팩트

### 테스트 결과
- **309 passed, 5 skipped, 2 failed** (기존 실패: media_fallback API키 / backward_compat ffmpeg 미설치)
- 신규 테스트 20개 전부 통과

### 변경 파일
- `src/shorts_maker_v2/pipeline/orchestrator.py` (Phase 3 분기)
- `ShortsFactory/engines/layout_engine.py` (v2: +6 메서드)
- `ShortsFactory/engines/color_engine.py` (v2: +4 메서드)
- `.github/workflows/visual-regression.yml` (신규: CI)
- `tests/unit/test_engines_v2_extended.py` (신규: 20 테스트)

### TODO
- [x] `use_shorts_factory=True` E2E 통합 테스트 (ffmpeg 환경) ← 완료 (2026-03-16)
- [ ] LayoutEngine v2 비주얼 리그레션 베이스라인 추가
- [x] ColorEngine `blend_presets` + `apply_role_grading` → render_step 통합 ← 완료 (2026-03-16)

### 다음 도구에게 메모
- `_try_shorts_factory_render()`는 ShortsFactory import가 실패하면 자동 폴백합니다
- `auto_correct`는 단색 프레임(std=0)에서 std를 1.0으로 방어합니다
- CI 워크플로우는 Python 3.14를 사용하므로 runners 지원 확인 필요

---

## 2026-03-26 — Antigravity (TrendDiscoveryStep 신규 모듈 작성 및 파이프라인 QC)

### 작업 요약
- `shorts-maker-v2`의 Phase 2 (트렌드 발굴) 파이프라인 구성 및 적용 완료.
- `TrendDiscoveryStep` 구현 및 `YouTubeTrendSource`, `GoogleTrendSource` 연동.
- CLI `--auto-topic` 플래그 통합 및 `TopicAngleGenerator` 파이프라인 연결.
- 잔여 유닛 테스트 버그(UnboundLocalError, _CAPTION_COMBOS tuple 길이 관련 Assertion) 해결 후 전체 QC(Quality Control) 진행.

### 세부 변경사항
- 파이프라인 `TrendDiscoveryStep` 모듈 작성.
- 프롬프트 템플릿의 JSON 렌더링 중 발생하는 `KeyError` 문제(중괄호 이스케이핑) 해결.
- `_CAPTION_COMBOS`의 튜플 요소가 3개에서 4개(hook, body, cta, closing)로 늘어난 부분 테스트 코드에 반영.
- `test_render_step_phase5.py`, `test_render_utils.py` 테스트 케이스 수정 및 통과.

### 테스트 결과
- **유닛 테스트**: pytest 통과 확인.
- **Ruff 코드 린터**: --fix 플래그를 통한 자동 수정(6건 반영).
- **최종 판정**: ✅ 승인 (APPROVED)

### 다음 도구에게 메모
- `_CAPTION_COMBOS` 길이 주의 필요 (4개 요소).
- 템플릿 프롬프트에서 JSON 포맷 활용 시 이중 중괄호 `{{`, `}}` 문법 유지할 것.

## 2026-03-27 / Codex (coverage aggregation + legacy archive)

### Summary
- Expanded the V2 coverage measurement from pipeline-only to a broader package suite by appending existing provider, render, CLI, and utils tests.
- Verified `src/shorts_maker_v2` total coverage at `82%`.
- Archived the old `tests/legacy/test_*.py` V1 files into `archive/tests_legacy_v1/`.
- Updated `pytest.ini` with `testpaths = tests` so the archived files are excluded from default collection.

### Files Changed
- `tests/unit/test_script_step.py`
- `tests/unit/test_orchestrator_unit.py`
- `tests/unit/test_render_step.py`
- `tests/unit/test_media_step_branches.py`
- `pytest.ini`
- `archive/tests_legacy_v1/README.md`
- `archive/tests_legacy_v1/test_ai_news_generator.py`
- `archive/tests_legacy_v1/test_edge_client.py`
- `archive/tests_legacy_v1/test_future_countdown.py`
- `archive/tests_legacy_v1/test_ssml.py`
- `archive/tests_legacy_v1/test_tech_vs.py`

### Validation
- `coverage run` pipeline chunk: `411 passed, 1 warning`
- `coverage run --append` provider/utils chunk: `294 passed, 1 warning`
- `coverage run --append` render/audio chunk: `176 passed, 12 skipped`
- `coverage report -m`: `src/shorts_maker_v2 TOTAL 82%`
- `pytest --collect-only -q -o addopts=` returned no archived legacy file paths

### Notes
- Use plain `coverage run` instead of `pytest-cov` on this machine when path mapping matters.

## 2026-03-27 / Codex (remove remaining ShortsFactory default footprint)

### Summary
- Removed `--cov=ShortsFactory` from the default `pytest.ini` coverage configuration.
- Archived the remaining direct ShortsFactory tests from `tests/unit/` and `tests/integration/` into `archive/tests_legacy_v1/`.
- Kept only the V2 bridge/fallback tests that intentionally patch or exercise ShortsFactory integration points.

### Files Changed
- `pytest.ini`
- `archive/tests_legacy_v1/README.md`
- `archive/tests_legacy_v1/unit/test_engines_v2.py`
- `archive/tests_legacy_v1/unit/test_engines_v2_extended.py`
- `archive/tests_legacy_v1/unit/test_interfaces.py`
- `archive/tests_legacy_v1/unit/test_performance_benchmark.py`
- `archive/tests_legacy_v1/unit/test_shorts_factory.py`
- `archive/tests_legacy_v1/unit/test_shorts_factory_plan_overlay.py`
- `archive/tests_legacy_v1/unit/test_visual_regression.py`
- `archive/tests_legacy_v1/unit/test_visual_regression_quality.py`
- `archive/tests_legacy_v1/integration/test_shorts_factory_e2e.py`

### Validation
- `rg -l "from ShortsFactory|import ShortsFactory|ShortsFactory\\." tests -g "*.py"` now returns only:
  - `tests/unit/test_render_step.py`
  - `tests/unit/test_render_step_phase5.py`
- `pytest tests/unit/test_render_step.py tests/unit/test_render_step_phase5.py tests/unit/test_orchestrator_unit.py -q -o addopts=` -> `161 passed, 1 warning`

### Notes
- Default pytest discovery is now focused on V2 tests and default coverage semantics are V2-only.
- Archived ShortsFactory suites can still be run explicitly by path if we need legacy compatibility checks later.
- Cleanup commit: `b90b393`

## 2026-03-27 / Codex (commit expanded V2 coverage tests)

### Summary
- Committed the major mock-heavy coverage expansion tests for `script_step`, `orchestrator`, `render_step`, and `media_step`.
- This is the main test bundle that pushed the V2 pipeline coverage work into committed state.

### Files Changed
- `tests/unit/test_script_step.py`
- `tests/unit/test_orchestrator_unit.py`
- `tests/unit/test_render_step.py`
- `tests/unit/test_media_step_branches.py`

### Validation
- `pytest tests/unit/test_script_step.py tests/unit/test_script_step_i18n.py tests/unit/test_orchestrator_unit.py tests/unit/test_render_step.py tests/unit/test_render_step_phase5.py tests/unit/test_parallel_media.py tests/unit/test_media_step_branches.py tests/integration/test_media_fallback.py -q -o addopts=` -> `218 passed, 1 warning`

### Notes
- Coverage expansion commit: `95b3421`
- Follow-up AI context relay after this commit: `4364164`

## 2026-03-29 | Codex | caption_pillow static caption quality pass

### Work Summary

Continued the post-thumbnail quality pass by tightening static subtitle rendering in `caption_pillow.py`.

- `render_caption_image()` now draws the configured background box instead of silently ignoring `bg_color`, `bg_opacity`, and `bg_radius`.
- The background layer and text/glow layer are composed separately, so glow styles bloom around text without bleeding around the full caption box.
- Horizontal placement now compensates for Pillow bbox `left` offsets, reducing off-center placement and clipped stroke edges on some glyphs.
- `tests/unit/test_caption_pillow.py` was refreshed and now includes a regression check that samples the padded region to prove the background box is present.

### Changed Files

- `src/shorts_maker_v2/render/caption_pillow.py`
- `tests/unit/test_caption_pillow.py`

### Verification

- `..\..\venv\Scripts\python.exe -m pytest tests/unit/test_caption_pillow.py -q -o addopts=` -> **4 passed, 1 warning**
- `..\..\venv\Scripts\python.exe -m pytest tests/unit/test_i18n_en_us_smoke.py -q -o addopts=` -> **1 passed, 1 warning**
- `..\..\venv\Scripts\python.exe -m pytest tests/unit/test_render_step_phase5.py -k "render_static_caption or caption_y" -q -o addopts=` -> **4 passed, 14 deselected, 1 warning**
- `..\..\venv\Scripts\python.exe -m ruff check src/shorts_maker_v2/render/caption_pillow.py tests/unit/test_caption_pillow.py` -> clean

---

## 2026-03-29 | Codex | caption_pillow safe-zone stress tests

### Work Summary

Extended `tests/unit/test_caption_pillow.py` so the recent static-caption quality changes are protected by explicit edge-case coverage.

- Added a long single-token wrap test to ensure character-level fallback keeps each line inside the width budget.
- Added direct `calculate_safe_position()` checks for normal centering and top-clamp behavior with oversized captions.
- Added a tall multiline render case to confirm static captions grow vertically under tighter widths instead of failing silently.

### Changed Files

- `tests/unit/test_caption_pillow.py`

### Verification

- `..\..\venv\Scripts\python.exe -m pytest tests/unit/test_caption_pillow.py -q -o addopts=` -> **8 passed, 1 warning**
- `..\..\venv\Scripts\python.exe -m ruff check tests/unit/test_caption_pillow.py` -> clean

---
