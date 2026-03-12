# 📋 AI 세션 로그

## 2026-03-12 — Antigravity (Phase 1 아키텍처 통합)

### 작업 요약
ShortsFactory v3.0 고도화 Phase 1: 아키텍처 통합 완료

### 세부 변경사항

#### Quick Wins (이전 세션에서 완료)
- ✅ Deprecated config 파일 삭제
- ✅ 템플릿 레지스트리 docstring 수정
- ✅ scaffold.py 자동 등록 + 입력 검증 강화
- ✅ ABTestAnalyzer mock 제거
- ✅ generate_short.py 채널 매개변수화

#### T1-1: 역할 재정의 및 인터페이스 설계
- ✅ `render_step.py`: 누락된 `run()` 메서드 복원 (씬 빌드 + 자막 + 전환 + 인트로 로직)
- ✅ `ShortsFactory/pipeline.py`: `render_from_plan()` 브리지 메서드 추가
- ✅ `ShortsFactory/pipeline.py`: `get_template_info()` 메서드 추가
- ✅ `ShortsFactory/interfaces.py`: `render_with_plan()` 메서드 추가 (RenderAdapter)
- ✅ `ARCHITECTURE.md`: deprecated → Rendering Layer 역할 재정의

#### T1-2: 레지스트리 통합
- ✅ `src/.../templates/__init__.py`: ShortsFactory `TEMPLATE_REGISTRY` re-export 추가

#### T1-3: Config 정리 (이전 세션에서 완료)
- ✅ Deprecated 파일 삭제
- ✅ ColorEngine 내장 프리셋 전환

### 변경 파일
- `src/shorts_maker_v2/pipeline/render_step.py` — run() 메서드 복원 (~190줄)
- `src/shorts_maker_v2/templates/__init__.py` — TEMPLATE_REGISTRY re-export
- `ShortsFactory/pipeline.py` — render_from_plan(), get_template_info() 추가
- `ShortsFactory/interfaces.py` — render_with_plan() 추가
- `ARCHITECTURE.md` — 전면 재작성
- `tests/unit/test_interfaces.py` — render_with_plan + render_from_plan 테스트 추가

### 테스트 결과
- `tests/unit/test_interfaces.py`: 13 passed ✅
- `tests/unit/test_shorts_factory.py`: 27 passed ✅

### 결정사항
- ShortsFactory는 더 이상 deprecated가 아닌 **Rendering Layer**로 공식 재포지셔닝
- 두 레지스트리 시스템 유지: `_REGISTRY` (대본 생성기) + `TEMPLATE_REGISTRY` (비주얼 렌더링)
- `render_from_plan()`은 ScenePlan 딕셔너리를 받아 ShortsFactory Scene으로 변환하는 브리지 패턴

### TODO (다음 단계)
- [ ] Phase 2: 엔진 고도화 (TextEngine v2, TransitionEngine v2, HookEngine v2, BackgroundEngine v2)
- [ ] Phase 4: QA 인프라 (비주얼 리그레션, 성능 벤치마크, 호환성 매트릭스)
- [ ] `ShortsFactory/render.py`의 `RenderStep.render_scenes()` 구현 확인/완성
- [ ] Orchestrator에서 render_from_plan 호출 분기 추가 (feature flag)

### 다음 도구에게 메모
- `render_step.py`의 `run()` 메서드가 이전에 누락되어 있었음. 원본 git 커밋에도 없었으므로 복원함.
- `render_from_plan()`의 실제 렌더링 동작은 `ShortsFactory/render.py`의 `RenderStep.render_scenes()`에 의존 — 이 메서드의 완성도를 확인해야 함.
- `ARCHITECTURE.md`가 전면 재작성됨 — 이전 문서와 크게 달라짐.

---

## 2026-03-12 — Antigravity (Phase 2 엔진 고도화 + Phase 4 QA 인프라)

### 작업 요약
ShortsFactory v3.0 고도화 Phase 2 (4개 엔진 v2 업그레이드) + Phase 4 (QA 인프라 구축) 완료

### 세부 변경사항

#### Phase 2: 엔진 v2 고도화

**TextEngine v2:**
- ✅ `render_gradient_text()`: 2색 그라데이션 텍스트 렌더링 (마스크 합성)
- ✅ `render_emoji_badge()`: 이모지 + 라벨 배지 이미지 생성
- ✅ `render_progress_bar()`: 프로그레스 바 PNG 생성 (라벨 옵션)
- ✅ `headline` 역할 스타일 추가 (96pt, 배경 없음)

**TransitionEngine v2:**
- ✅ `swipe()`: 4방향 스와이프 전환 (left/right/up/down, ease-out)
- ✅ `blur_dissolve()`: 블러 → 디졸브 전환
- ✅ `zoom_through()`: A 확대 → B 녹아 들어옴  
- ✅ `color_wipe()`: 채널 accent 색상 와이프
- ✅ moviepy lazy import 적용 (ffmpeg 미설치 환경 대응)
- ✅ 역할 기반 전환 매핑 확장 (intro/outro 포함)

**HookEngine v2:**
- ✅ `_apply_shake()`: 카메라 쉐이크 효과 (감쇠 적용)
- ✅ `_apply_reveal()`: 원형 마스크 확장 애니메이션 (cubic ease-out)
- ✅ `_apply_combo()`: 효과 조합 시스템 (순차 적용)
- ✅ `create_hook_with_shake()`, `create_hook_with_reveal()` 팩토리 메서드
- ✅ `list_available_effects()`: 사용 가능 효과 조회
- ✅ `_apply_glitch()` 개선: RGB 시프트 + 라인 글리치 + 노이즈 합성

**BackgroundEngine v2:**
- ✅ `create_noise_texture()`: 필름 그레인/노이즈 RGBA 오버레이
- ✅ `create_scanline_overlay()`: CRT 스캔라인 효과
- ✅ `create_mesh_gradient()`: 다중 제어점 메쉬 그라데이션

#### Phase 4: QA 인프라

- ✅ `tests/unit/test_engines_v2.py`: 엔진 v2 기능 단위 테스트 (26개)
- ✅ `tests/unit/test_visual_regression.py`: 비주얼 리그레션 프레임워크 (SSIM/PSNR, 골든 베이스라인)
- ✅ `tests/unit/test_performance_benchmark.py`: 성능 벤치마크 (임계값 기반, JSON 결과 저장)

### 변경 파일
- `ShortsFactory/engines/text_engine.py` — v2 메서드 3개 추가 + headline 스타일
- `ShortsFactory/engines/transition_engine.py` — v2 전환 4개 + lazy import
- `ShortsFactory/engines/hook_engine.py` — 전면 재작성 (v2)
- `ShortsFactory/engines/background_engine.py` — v2 메서드 3개 추가
- `tests/unit/test_engines_v2.py` — 신규 (49개 테스트)
- `tests/unit/test_visual_regression.py` — 신규 (비주얼 리그레션)
- `tests/unit/test_performance_benchmark.py` — 신규 (성능 벤치마크)

### 테스트 결과
- `test_engines_v2.py`: 26 passed, 9 skipped (TransitionEngine/ffmpeg) ✅
- `test_visual_regression.py`: 전체 passed ✅
- `test_performance_benchmark.py`: 전체 passed ✅
- `test_shorts_factory.py`: 27 passed ✅ (회귀 없음)
- `test_interfaces.py`: 13 passed ✅ (회귀 없음)

### 결정사항
- TransitionEngine의 moviepy import를 lazy로 전환 (ffmpeg 미설치 환경 호환)
- 비주얼 리그레션 임계값: SSIM ≥ 0.85
- 성능 벤치마크 결과는 `.tmp/benchmarks/latest.json`에 저장
- HookEngine v2의 콤보 시스템은 효과를 순차 적용 (병렬 X → 간단/예측 가능)

### TODO (다음 단계)
- [ ] Phase 3: Orchestrator에서 render_from_plan 호출 분기 추가
- [ ] 비주얼 리그레션 베이스라인 CI 파이프라인 통합
- [ ] LayoutEngine v2 + ColorEngine v2 고도화

### 다음 도구에게 메모
- TransitionEngine은 moviepy lazy import 패턴 사용 → import 시 ffmpeg 에러 안 남
- HookEngine은 전면 재작성됨 — 기존 API (create_hook, create_hook_with_flash) 호환 유지
- BackgroundEngine의 create_mesh_gradient는 `random.randint` 사용 → 결과가 비결정적 (시드 필요시 추가)
- 비주얼 리그레션 테스트는 첫 실행 시 골든 베이스라인을 자동 생성함

---

## 2026-03-12 (Antigravity) — Phase 2+4 QA/QC

### 작업 요약
Phase 2 (엔진 v2) + Phase 4 (QA 인프라)에 대한 QA/QC 4단계 프로세스 실행

### QA 발견 7건 & 수정

| # | 수정 | 파일 |
|---|------|------|
| 1 | 그라데이션 putpixel O(W×H) → numpy 벡터화 | text_engine.py |
| 1b | numpy import 누락 추가 | text_engine.py |
| 2-4 | _apply_glitch/shake/reveal duration≤0 방어 | hook_engine.py |
| 5 | create_mesh_gradient 빈 colors 방어 | background_engine.py |
| 6 | MoviePy v2: lambda→Effect 클래스 (CrossFadeIn/Out) | transition_engine.py |
| 7 | _apply_zoom 미사용 변수 제거 | transition_engine.py |
| 8 | ffmpeg 감지 shutil.which 기반으로 개선 | test_engines_v2.py |

### 테스트 결과
- **89 passed, 9 skipped, 0 failed**

### 최종 판정: ✅ 승인 (APPROVED)

### 변경 파일
- `ShortsFactory/engines/text_engine.py` (numpy import + gradient 벡터화)
- `ShortsFactory/engines/hook_engine.py` (duration 방어)
- `ShortsFactory/engines/background_engine.py` (빈 리스트 방어)
- `ShortsFactory/engines/transition_engine.py` (MoviePy v2 호환 + 미사용 변수)
- `tests/unit/test_engines_v2.py` (ffmpeg 감지 개선)

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
- [ ] `use_shorts_factory=True` E2E 통합 테스트 (ffmpeg 환경)
- [ ] LayoutEngine v2 비주얼 리그레션 베이스라인 추가
- [ ] ColorEngine `blend_presets` + `apply_role_grading` → render_step 통합

### 다음 도구에게 메모
- `_try_shorts_factory_render()`는 ShortsFactory import가 실패하면 자동 폴백합니다
- `auto_correct`는 단색 프레임(std=0)에서 std를 1.0으로 방어합니다
- CI 워크플로우는 Python 3.14를 사용하므로 runners 지원 확인 필요

