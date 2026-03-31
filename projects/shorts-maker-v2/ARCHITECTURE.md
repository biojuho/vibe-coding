# Shorts Maker V2 — Architecture Guide

## Integrated Architecture (v3.0)

```
shorts-maker-v2/
├── src/shorts_maker_v2/          # 🎯 MAIN: E2E Orchestrator
│   ├── pipeline/
│   │   ├── orchestrator.py       # 전체 파이프라인 조율
│   │   ├── script_step.py        # LLM 대본 생성 (7-provider fallback)
│   │   ├── media_step.py         # TTS + Image/Video 생성
│   │   ├── render_step.py        # MoviePy/FFmpeg 렌더링 (기본 경로)
│   │   └── thumbnail_step.py     # 썸네일 생성
│   ├── providers/                # API 클라이언트들
│   │   ├── llm_router.py         # 8개 LLM 자동 fallback
│   │   ├── openai_client.py      # DALL-E + TTS
│   │   ├── google_client.py      # Gemini Image + Veo + Imagen
│   │   ├── edge_tts_client.py    # 무료 Microsoft TTS
│   │   └── pexels_client.py      # 무료 스톡 비디오
│   ├── templates/                # 대본 생성기 레지스트리
│   │   └── __init__.py           # _REGISTRY + TEMPLATE_REGISTRY (re-export)
│   ├── render/                   # 렌더링 유틸리티
│   │   ├── karaoke.py            # 카라오케 자막 엔진
│   │   ├── captions.py           # 정적/동적 자막 렌더링
│   │   ├── transition_effects.py # 씬 전환 효과
│   │   └── srt_export.py         # SRT 자막 내보내기
│   └── utils/                    # 유틸리티
│       ├── cost_guard.py         # 실시간 비용 모니터링
│       ├── cost_tracker.py       # 비용 이력 추적
│       └── media_cache.py        # 프롬프트 해시 기반 캐시
│
├── shorts_maker_v2/              # 🔗 BRIDGE: 네임스페이스 브릿지 (src/ → import 연결)
│   ├── __init__.py               # pkgutil.extend_path로 src/ 참조
│   └── __main__.py               # CLI 진입점 + UTF-8 래핑
│
├── ShortsFactory/                # 🎨 RENDERING LAYER: 채널별 비주얼 렌더링 (활성 사용 중)
│   ├── pipeline.py               # ShortsFactory 클래스 (render_from_plan 포함)
│   ├── interfaces.py             # RenderAdapter, RenderRequest, RenderResult
│   ├── templates/                # 비주얼 레이아웃 템플릿 (18종, Single Registry)
│   │   ├── __init__.py           # TEMPLATE_REGISTRY (BaseTemplate 기반)
│   │   ├── base_template.py      # BaseTemplate + Scene 데이터 모델
│   │   └── ...                   # 채널별 템플릿 파일들
│   ├── engines/                  # 6대 렌더링 엔진
│   │   ├── text_engine.py        # 채널별 자막 스타일
│   │   ├── background_engine.py  # 배경 생성
│   │   ├── color_engine.py       # 색상 프리셋 (내장)
│   │   ├── layout_engine.py      # 레이아웃 배치
│   │   ├── hook_engine.py        # Hook 애니메이션
│   │   └── transition_engine.py  # 씬 전환 효과
│   ├── integrations/             # 외부 연동
│   │   ├── notion_bridge.py      # Notion 양방향 연동
│   │   ├── script_gen.py         # AI 스크립트 생성
│   │   └── ab_test.py            # A/B 테스트 분석
│   ├── config/                   # 채널 설정
│   │   └── channel_profiles.yaml # → 프로젝트 루트로 이동됨
│   └── generate_short.py         # 편의 함수 (채널 파라미터화)
│
├── config.yaml                   # 전역 설정
├── channel_profiles.yaml         # 5채널 맞춤 설정 (Single Source of Truth)
└── topics_*.txt                  # 채널별 주제 파일
```

## Two Registry System

| Registry | Location | Purpose | Type |
|----------|----------|---------|------|
| `_REGISTRY` | `src/.../templates/__init__.py` | 대본 생성기 클래스 매핑 | `tools/` module + class name |
| `TEMPLATE_REGISTRY` | `ShortsFactory/templates/__init__.py` | 비주얼 렌더링 템플릿 매핑 | `BaseTemplate` subclass |

`src/.../templates/__init__.py`에서 `TEMPLATE_REGISTRY`를 re-export하여
단일 import 지점에서 두 레지스트리 모두 접근 가능합니다.

## Data Flow

```
Topic → [ScriptStep] → LLM Router (8 providers) → Script JSON
Script → [MediaStep] → TTS (Edge TTS) + Image (Gemini/Pexels/DALL-E) → Assets
Assets → [RenderStep] → MoviePy + FFmpeg → MP4           ← 기본 경로
Assets → [RenderAdapter] → ShortsFactory (6 Engines) → MP4  ← 고급 렌더링 경로
MP4 → [ThumbnailStep] → Pillow → PNG
```

## Integration Points

### RenderAdapter (interfaces.py)
```python
from ShortsFactory import RenderAdapter, RenderRequest, RenderResult

adapter = RenderAdapter()

# 방법 1: 콘텐츠 데이터 기반 (레거시)
result = adapter.render(RenderRequest(...))

# 방법 2: ScenePlan 기반 (Main Pipeline 통합)
result = adapter.render_with_plan(
    channel_id="ai_tech",
    scenes=[scene.to_dict() for scene in scene_plans],
    assets={s.scene_id: s.visual_path for s in scene_assets},
    output_path="output.mp4",
)
```

### ShortsFactory.render_from_plan()
```python
factory = ShortsFactory(channel="ai_tech")
output = factory.render_from_plan(
    scenes=[{"scene_id": 1, "narration_ko": "...", ...}],
    assets={1: "path/to/image.png"},
    output="output.mp4",
    template="ai_news",
)
```

## When to Use What

| Task | Module | Command |
|------|--------|---------|
| **영상 생성** | `src/shorts_maker_v2` | `python -m shorts_maker_v2 run --topic "..." --channel ai_tech` |
| **배치 생성** | `src/shorts_maker_v2` | `python -m shorts_maker_v2 batch --topics-file topics_ai.txt` |
| **시스템 점검** | `src/shorts_maker_v2` | `python -m shorts_maker_v2 doctor` |
| **비용 확인** | `src/shorts_maker_v2` | `python -m shorts_maker_v2 costs` |
| **채널별 스타일 렌더링** | `ShortsFactory` | `RenderAdapter.render_with_plan(...)` |

## Key Configuration Files

- **`config.yaml`**: Global settings (video, providers, costs, captions, audio)
- **`channel_profiles.yaml`**: Per-channel customization (TTS voice, visual style, hook pattern)
- **`.env`**: API keys (OpenAI, Gemini, Pexels, Notion, etc.)

> ⚠ **`ShortsFactory/config/`**: Deprecated 파일들은 모두 제거되었습니다.
> 모든 채널 설정은 `channel_profiles.yaml`을 사용합니다.
