# 📐 프로젝트 컨텍스트

## 프로젝트: shorts-maker-v2
AI 기반 YouTube Shorts 자동 생성 파이프라인

## 스택
- Python 3.14
- MoviePy 2.x + FFmpeg (렌더링)
- Edge TTS (무료 TTS)
- LLM Router (8개 provider fallback)
- Pexels/Gemini/DALL-E (비주얼)

## 아키텍처 (v3.0)
- `src/shorts_maker_v2/pipeline/` — E2E 오케스트레이터
- `ShortsFactory/` — **전문 렌더링 레이어** (6대 엔진 + 18종 템플릿)
- `ShortsFactory/interfaces.py` — Main Pipeline ↔ ShortsFactory 통합 인터페이스

## 현재 진행 상황
- ✅ Phase 1: 아키텍처 통합 완료
  - render_step.py run() 메서드 복원
  - RenderAdapter + render_from_plan() 구현
  - 레지스트리 통합 (re-export)
  - ARCHITECTURE.md 재작성
- ✅ Phase 2: 엔진 v2 고도화 (QA/QC 승인 완료)
  - TextEngine v2: gradient text, emoji badge, progress bar, headline style
  - TransitionEngine v2: swipe, blur_dissolve, zoom_through, color_wipe
  - HookEngine v2: shake, reveal, combo system
  - BackgroundEngine v2: noise, scanline, mesh gradient
- ✅ Phase 4: QA 인프라 (QA/QC 승인 완료)
  - 비주얼 리그레션 (SSIM/PSNR)
  - 성능 벤치마크 (JSON 결과)
  - 전체 89 passed, 9 skipped, 0 failed
- ⬜ Phase 3: Orchestrator 통합 (render_from_plan 호출 분기)

## 컨벤션
- 테스트: `tests/unit/`, `tests/integration/`
- 설정: `config.yaml` + `channel_profiles.yaml` (Single Source of Truth)
- 채널: ai_tech, psychology, history, space, health

## 지뢰밭 ⚠️
- `render_step.py`의 `run()` 메서드가 원본 git 커밋에서 이미 누락되어 있었음
- ffmpeg 미설치 환경에서 moviepy import 시 에러 발생 → 통합 테스트 건너뜀
- ShortsFactory의 `_get_template_registry()`는 `src/.../templates`의 `_REGISTRY`를 사용 (tools/ 기반)
- ShortsFactory의 `TEMPLATE_REGISTRY`는 `ShortsFactory/templates/`의 BaseTemplate 기반
- **MoviePy v2.x**: `with_effects()`에 lambda 사용 불가 → Effect 클래스(CrossFadeIn/Out) 사용 필수
- **TextEngine gradient**: putpixel은 O(W×H) 병목 → numpy 벡터화 필수

