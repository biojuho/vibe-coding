---
name: shorts-bgm-strategy
description: >
  Shorts Maker V2 BGM 전략. Freesound API 키워드 매핑, 채널별 에너지 레벨,
  BGM 다양성 확보 방법을 정의한다. freesound_client.py 수정 시 참조.
---

# Shorts BGM Strategy Skill

## 핵심 원칙
- **Freesound API 유지**: MusicGen/AudioCraft는 GPU 필요로 배제 (미래 옵션)
- **에너지 → 채널 특성 매핑**: 단순 장르가 아닌 채널 분위기 기반 키워드
- **랜덤 선택으로 다양성**: 상위 3개 중 랜덤 선택 → 매 영상 BGM 반복 방지

## 채널별 BGM 에너지 매핑

| 채널 | 에너지 레벨 | 분위기 |
|------|-----------|--------|
| ai_tech | high | 사이버펑크 미래감 + 구동감 |
| history | medium | 다큐멘터리 오케스트라 + 서사적 긴장 |
| psychology | calm | 따뜻하고 감성적인 피아노 |
| space | epic | 한스 짐머 스타일 웅장함 |
| health | warm_uplifting | 밝고 긍정적인 어쿠스틱 |

## Freesound 검색 키워드 (BGM_ENERGY_TAGS)

```python
BGM_ENERGY_TAGS = {
    "high":          "synthwave electronic driving futuristic cyberpunk upbeat loop",
    "medium":        "cinematic orchestral epic historical documentary tension background",
    "calm":          "calm ambient warm piano emotional gentle healing loop",
    "epic":          "epic orchestral space cosmos wonder cinematic dramatic majestic",
    "warm_uplifting": "upbeat acoustic positive cheerful motivating healthy lifestyle loop",
}
```

## 키워드 최적화 원칙
- **구체 장르 + 분위기**: `synthwave` + `cyberpunk` (vs 단순 `electronic`)
- **용도 명시**: `loop` 태그로 루프 가능한 트랙 우선
- **채널 특성 단어**: `documentary`, `cosmos`, `healing` 등 분위기 정확히 기술

## 다양성 확보
```python
# 상위 3개 중 랜덤 선택 (매번 같은 BGM 반복 방지)
sound = random.choice(results[:min(3, len(results))])
```

## 안티패턴
- ❌ 항상 첫 번째 결과만 사용 → 모든 영상에 같은 BGM 반복
- ❌ 너무 광범위한 키워드 (`music loop`) → 관련 없는 결과 혼입
- ❌ health 채널에 `medium` (오케스트라) → 병원 분위기, 따뜻함 없음

## 새 채널 추가 시 체크리스트
1. `BGM_ENERGY_TAGS`에 새 에너지 레벨 추가 (필요 시)
2. `CHANNEL_BGM_ENERGY`에 채널 → 에너지 매핑 추가
3. `channel_profiles.yaml`의 `bgm_energy` 필드와 동기화

## BGM 볼륨 가이드라인
- BGM 볼륨: 나레이션 대비 -20dB ~ -25dB (말소리 가림 방지)
- SFX 볼륨: BGM 대비 +3dB ~ +5dB (효과음 선명도)
