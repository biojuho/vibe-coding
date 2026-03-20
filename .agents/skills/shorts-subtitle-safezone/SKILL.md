---
name: shorts-subtitle-safezone
description: >
  Shorts Maker V2 자막 안전 영역(Safe Zone) 관리. YouTube Shorts 9:16 비율에서
  UI 오버랩을 방지하는 자막 배치 규칙, 픽셀 기반 줄바꿈, 동적 폰트 크기 조정을 정의한다.
  caption_pillow.py / karaoke.py 수정 시 참조.
---

# Shorts Subtitle Safe Zone Skill

## Shorts UI 안전 영역 (1920×1080 기준)

```
┌─────────────────────┐  ← 상단 채널명/제목 오버레이 영역
│   ← 상단 15%       │  (288px @1920 high)
│   (UI 오버랩 위험)  │
├─────────────────────┤  ← 자막 배치 가능 구역 시작
│                     │
│   자막 안전 구역     │  65% 영역 (캔버스 중앙)
│   (safe_area_top    │
│    ~ safe_area_bot) │
│                     │
├─────────────────────┤  ← 자막 배치 가능 구역 종료
│   ← 하단 20%       │  (384px @1920 high)
│   (좋아요/댓글/공유  │
│    버튼 오버랩 위험)  │
└─────────────────────┘
```

## calculate_safe_position() 로직
```python
top_safe    = int(canvas_height * 0.15)   # 288px @1920
bottom_safe = int(canvas_height * 0.20)   # 384px @1920
safe_area_top    = top_safe
safe_area_bottom = canvas_height - bottom_safe
# 기본: safe zone 내 수직 중앙 배치
y = safe_area_top + (safe_area_height - caption_height) // 2
y = max(safe_area_top, y)  # 절대 상단 초과 방지
```

## 픽셀 기반 줄바꿈 (_wrap_text)
- ❌ 문자 수 기반 줄바꿈: 영문자·한글 폭이 달라 부정확
- ✅ `draw.textbbox()`로 실제 픽셀 너비 측정 후 줄바꿈
- CJK (공백 없는 텍스트): `_char_level_wrap()`으로 글자 단위 폭 측정

## 동적 폰트 크기 (_auto_scale_font)
- 텍스트 픽셀 너비 > 캔버스 너비 → 4px씩 줄여 맞춤
- 최소 폰트: `max(24, base_size // 2)`
- 적용 대상: `render_karaoke_image()`, `render_karaoke_highlight_image()`

## 자막 스타일 아키텍처
```
CaptionStyle (dataclass, frozen)
├── safe_zone_enabled: bool   ← True로 유지할 것
├── center_hook: bool         ← Hook 씬은 중앙 배치
├── font_size: int            ← base size (동적 조정의 기준)
├── margin_x: int             ← 좌우 여백 (픽셀)
├── glow_enabled: bool        ← 채널별 네온 효과
└── line_spacing_factor: 1.3  ← 멀티라인 간격 배수
```

## 카라오케 하이라이트 (render_karaoke_highlight_image)
- 활성 단어: 1.15× 확대 폰트 + 글로우 효과 + highlight_color
- 비활성 단어: 흰색 dim (alpha 255, 유지 가시성)
- 키워드: `keyword_colors` dict로 특정 단어에 별도 색상 적용 가능

## 채널별 자막 스타일 프리셋

| 채널 | body 스타일 | hook 스타일 |
|------|-----------|-----------|
| ai_tech | neon_tech | neon_tech_highlight |
| psychology | dreamy_purple | dreamy_purple_highlight |
| history | vintage_sepia | vintage_sepia_highlight |
| space | deep_space | deep_space_highlight |
| health | clean_medical | clean_medical_highlight |

## 안티패턴
- ❌ `bottom_offset` 기반 고정 위치 → 해상도 변경 시 UI 오버랩
- ❌ 문자 수 기반 줄바꿈 → 한글/영문 혼재 시 오버플로우
- ❌ safe_zone_enabled=False → YouTube UI에 자막 가림
