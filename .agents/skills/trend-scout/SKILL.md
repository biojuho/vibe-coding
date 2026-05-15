---
name: trend-scout
description: 실시간 트렌드를 탐지하고 Shorts/블로그용 콘텐츠 토픽을 자동 제안할 때 사용.
---

# 🔍 Trend Scout Skill

> Brave Search + 커뮤니티 트렌드 분석 → 채널별 최적 토픽 자동 제안

## 목적

실시간 검색 트렌드와 커뮤니티 인기 글을 분석하여
shorts-maker-v2의 5채널에 최적화된 토픽을 자동 제안합니다.

## 사전 요구사항

- **Brave Search 스킬** 또는 웹 검색 도구
- **Notion MCP** 연결 (토픽 큐 등록)
- `channel_profiles.yaml` (채널 설정)
- `community_trend_scraper.py` (커뮤니티 트렌드 수집)

## 사용법

### 1. 트렌드 기반 토픽 제안

```
사용자: AI 채널용 이번 주 트렌드 토픽 찾아줘
```

**에이전트 동작:**
1. Brave Search로 최근 1주 AI/기술 트렌드 키워드 검색
2. YouTube Shorts에서 높은 조회수를 기록한 유사 토픽 분석
3. channel_profiles.yaml의 topic_pool과 매칭
4. 중복 체크 (최근 30일 내 유사 토픽 필터링)
5. 상위 5개 토픽 후보 제안 (제목 + 예상 매력도 점수)

### 2. 커뮤니티 핫 토픽 발굴

```
사용자: 커뮤니티에서 뜨는 주제 뭐 있어?
```

**에이전트 동작:**
1. `community_trend_scraper.py` 결과 분석
2. blind-to-x가 수집한 최근 인기 글 토픽 클러스터링
3. Shorts 콘텐츠로 변환 가능한 토픽 필터링
4. 채널별 매핑 제안

### 3. 경쟁 분석

```
사용자: 우리 채널과 비슷한 채널들 요즘 뭐 올려?
```

**에이전트 동작:**
1. YouTube MCP로 경쟁 채널 최신 영상 조회
2. 제목/태그 키워드 빈도 분석
3. 미다룬 주제 갭 분석
4. 차별화 토픽 제안

### 4. 자동 토픽 큐 등록

```
사용자: 추천 토픽 중 상위 3개 캘린더에 등록해줘
```

**에이전트 동작:**
1. 선택된 토픽을 Notion 콘텐츠 캘린더에 등록
2. 채널별 적절한 날짜 자동 배정
3. Status: "draft"로 설정
4. 등록 완료 확인

## 트렌드 소스

| 소스 | 채널 매핑 | 설명 |
|------|-----------|------|
| Brave Search "AI news" | ai_tech | AI/기술 최신 뉴스 |
| Brave Search "psychology facts" | psychology | 심리학 팩트/연구 |
| Brave Search "history mysteries" | history | 역사 미스터리/반전 |
| Brave Search "health myths" | health | 건강 상식/실험 |
| Brave Search "space discoveries" | space | 우주 발견/탐사 |
| 블라인드/에펨코리아 | 전 채널 | 커뮤니티 핫 토픽 |

## 토픽 평가 기준

| 기준 | 가중치 | 설명 |
|------|--------|------|
| 검색량 트렌드 | 30% | 최근 7일 검색 상승률 |
| YouTube 경쟁도 | 25% | 유사 토픽 영상 수 (적을수록 좋음) |
| 채널 적합도 | 25% | topic_pool 매칭 + 톤 적합성 |
| 시각화 가능성 | 20% | Shorts 60초에 시각화 가능 여부 |

## 주의사항

- 중복 토픽 제안 방지: Notion 기존 항목 + result_tracker 과거 토픽 교차 체크
- 민감한 토픽 필터: 혐오/갈등 유발 주제 자동 제외 (classification_rules.yaml 연동)
- 토픽 제안 시 **근거 제시** (검색 트렌드 URL, 참고 영상 등)
