---
name: shorts-tts-quality
description: >
  Shorts Maker V2 TTS 품질 관리. 채널별 prosody 설정, Edge TTS 음성 매핑,
  자연스러운 억양을 위한 rate/pitch 변주 규칙을 정의한다.
  이 Skill은 edge_tts_client.py 수정 시 참조해야 한다.
---

# Shorts TTS Quality Skill

## 핵심 원칙
- **Edge TTS 유지**: Bark/XTTS는 GPU 필요 + 한국어 지원 미비로 배제
- **AI 티 최소화**: 단일 rate/pitch 고정 → 채널별 변주 폭(±Hz, ±%)으로 생동감
- **역할(role)별 prosody**: hook은 빠르고 임팩트 있게, cta는 느리고 친근하게

## 채널별 音聲 매핑 (channel_profiles.yaml `tts_voice` 기준)

> **SSOT**: `channel_profiles.yaml`의 각 채널 `tts_voice` 키. 아래 표는 그 값을
> 미러링한 것이며, Shorts Maker V2의 TTS unit tests가 표와 YAML의
> 일치를 자동 검증한다. 음성을 바꾸려면 YAML을 고치고 이 표도 함께 갱신할 것.

| 채널 | 음성 (Edge TTS) | 특성 |
|------|----------------|------|
| ai_tech | ko-KR-InJoonNeural | 남성, 강하고 권위적 → 뉴스 앵커 느낌 |
| psychology | ko-KR-SoonBokNeural | 여성, 부드럽고 안정적 |
| history | ko-KR-BongJinNeural | 남성, 따뜻하고 친근한 이야기꾼 |
| space | ko-KR-HyunsuNeural | 남성, 차분하고 지적 → 다큐멘터리 내레이터 |
| health | ko-KR-HyunsuNeural | 남성, 차분하고 지적 → 의사 느낌 |

위 값은 각 채널의 **기본(base) 음성**이다. 채널마다 `tts_voice_roles`로
hook/body/cta/closing 역할별 음성을 따로 지정할 수 있다 (예: `ai_tech`는
body 역할에 `ko-KR-HyunsuNeural`을 사용). 역할별 음성도 SSOT는 YAML이다.

## 채널별 Prosody 변주 폭 (_CHANNEL_PROSODY)

```python
_CHANNEL_PROSODY = {
    # (rate_jitter_pct, pitch_jitter_hz)
    "ai_tech":    (7, 2),   # 빠른 리듬감; rate 변주 ±7%, pitch 소폭
    "history":    (4, 3),   # 서사적 호흡; rate ±4%, pitch ±3Hz
    "psychology": (3, 5),   # 공감·감성; rate 소폭, pitch ±5Hz
    "space":      (5, 4),   # 경이로움; 중간 리듬, pitch ±4Hz
    "health":     (3, 2),   # 신뢰감; 안정적. 변주 최소화
}
```

## 역할별 prosody 고정값 (`_get_role_prosody`)

| role | rate | pitch |
|------|------|-------|
| hook | +15% | 채널별 (+5~+10Hz) |
| cta  | -10% | +5Hz |
| closing | -15% | -2Hz |
| body | base_rate ± jitter | ±jitter Hz |

> `closing`은 여운 있는 마무리용 — 느리고 낮은 pitch로 차분하게 끝난다.

## Hook pitch 채널별 매핑
```python
pitch_hook_map = {
    "psychology": "+6Hz",   # 따뜻한 첫 인상
    "history":    "+7Hz",   # 극적인 시작
    "space":      "+5Hz",   # 경이감
    "ai_tech":    "+10Hz",  # 임팩트
    "health":     "+6Hz",   # 친근한 시작
}
```

## 반드시 피해야 할 안티패턴
- ❌ SSML `<break>` 태그 남용 → Whisper 타임스탬프와 불일치
- ❌ 모든 씬에 동일 rate/pitch 고정 → 기계음 유발
- ❌ 한국어 채널에 `shimmer` / `alloy` 등 영어 특화 음성 사용

## 수정 가이드
1. 음성 변경: `channel_profiles.yaml` → 각 채널의 `tts_voice` 키
2. 기본 속도 변경: `channel_profiles.yaml` → `tts_speed` 키
3. 변주 폭 조정: `edge_tts_client.py` → `_CHANNEL_PROSODY` 딕셔너리
4. 새 채널 추가: `_CHANNEL_PROSODY`, `pitch_hook_map` 모두에 항목 추가

## generate_tts 파라미터 (중요)
```python
client.generate_tts(
    model=...,
    voice=...,
    speed=...,
    text=...,
    output_path=...,
    role="hook",         # hook / body / cta / closing
    channel_key="ai_tech",  # ← 반드시 전달해야 채널 prosody 적용됨
)
```
