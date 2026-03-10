# Shorts Maker V2 — Architecture Guide

## Two-Module Architecture

```
shorts-maker-v2/
├── src/shorts_maker_v2/          # 🎯 MAIN: E2E Orchestrator (이것을 사용하세요!)
│   ├── pipeline/
│   │   ├── orchestrator.py       # 전체 파이프라인 조율
│   │   ├── script_step.py        # LLM 대본 생성 (7-provider fallback)
│   │   ├── media_step.py         # TTS + Image/Video 생성
│   │   ├── render_step.py        # MoviePy/FFmpeg 렌더링
│   │   └── thumbnail_step.py     # 썸네일 생성
│   ├── providers/                # API 클라이언트들
│   │   ├── llm_router.py         # 8개 LLM 자동 fallback
│   │   ├── openai_client.py      # DALL-E + TTS
│   │   ├── google_client.py      # Gemini Image + Veo + Imagen
│   │   ├── edge_tts_client.py    # 무료 Microsoft TTS
│   │   └── pexels_client.py      # 무료 스톡 비디오
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
├── ShortsFactory/                # 🔧 LEGACY: FFmpeg 렌더링 라이브러리
│   ├── pipeline.py               # FFmpeg filter_complex 빌더
│   ├── templates/                # 레이아웃 템플릿
│   └── config/channels.yaml      # ⚠ DEPRECATED → channel_profiles.yaml 사용
│
├── config.yaml                   # 전역 설정
├── channel_profiles.yaml         # 5채널 맞춤 설정
└── topics_*.txt                  # 채널별 주제 파일
```

## When to Use What

| Task | Module | Command |
|------|--------|---------|
| **영상 생성** | `src/shorts_maker_v2` | `python -m shorts_maker_v2 run --topic "..." --channel ai_tech` |
| **배치 생성** | `src/shorts_maker_v2` | `python -m shorts_maker_v2 batch --topics-file topics_ai.txt` |
| **시스템 점검** | `src/shorts_maker_v2` | `python -m shorts_maker_v2 doctor` |
| **비용 확인** | `src/shorts_maker_v2` | `python -m shorts_maker_v2 costs` |
| ~~FFmpeg 직접 렌더~~ | ~~`ShortsFactory`~~ | ~~`python -m ShortsFactory`~~ (deprecated) |

## Data Flow

```
Topic → [ScriptStep] → LLM Router (8 providers) → Script JSON
Script → [MediaStep] → TTS (Edge TTS) + Image (Gemini/Pexels/DALL-E) → Assets
Assets → [RenderStep] → MoviePy + FFmpeg → MP4
MP4 → [ThumbnailStep] → Pillow → PNG
```

## Key Configuration Files

- **`config.yaml`**: Global settings (video, providers, costs, captions, audio)
- **`channel_profiles.yaml`**: Per-channel customization (TTS voice, visual style, hook pattern)
- **`.env`**: API keys (OpenAI, Gemini, Pexels, Notion, etc.)

> ⚠ **Do NOT modify `ShortsFactory/config/channels.yaml`** — it is deprecated.
> All channel settings should go into `channel_profiles.yaml`.
