# 커뮤니티 트렌드 수집 지침

## 목적
한국 커뮤니티(에펨코리아, 뽐뿌) 인기 게시글 제목을 수집하여 Shorts 토픽 자동 생성의 추가 시그널로 활용.

## 수집 대상

| 소스 | URL | 특성 |
|------|-----|------|
| **에펨코리아** | `fmkorea.com/index.php?mid=best` | 포텐 터짐 (조회수/추천 기반 인기글) |
| **뽐뿌** | `ppomppu.co.kr/hot.php` | HOT 게시글 (자유게시판 인기글) |

## 실행 방법

### 라이브러리 호출
```python
from execution.community_trend_scraper import get_community_trends, get_community_trend_titles

# 전체 메타데이터 (title, source, views, recommendations, link)
trends = get_community_trends(sources=["fmkorea", "ppomppu"], limit=10)

# 제목만 (GPT 프롬프트 주입용)
titles = get_community_trend_titles(limit=5)
```

### CLI
```bash
python execution/community_trend_scraper.py                    # 전체 수집
python execution/community_trend_scraper.py --source fmkorea   # 에펨코리아만
python execution/community_trend_scraper.py --limit 5 --json   # JSON 출력
```

## 통합 구조
```
topic_auto_generator.py → check_and_replenish()
  ├── get_trending_topics()        # Google Trends (pytrends)
  ├── get_community_trend_titles() # 커뮤니티 트렌드 (dopamine-bot)
  └── generate_topics()            # GPT가 두 소스 모두 참고하여 토픽 생성
```

- `_COMMUNITY_TRENDS_OK` 플래그로 import 가드 — dopamine-bot 미설치 시 자동 스킵
- 커뮤니티 트렌드는 Google Trends 결과에 병합되어 `trending_keywords` 파라미터로 GPT에 전달

## 설정
`dopamine-bot/config.yaml`:
- `enabled`: 소스별 활성화/비활성화
- `post_limit`: 소스당 최대 수집 수
- `filters.min_views`, `filters.min_recommendations`: 필터 기준 (현재 미적용, 추후 확장)

## 주의사항
- **Cloudflare**: 에펨코리아는 Cloudflare 보호 가능. `requests.get()`으로 차단 시 빈 리스트 반환 (정상 동작)
- **인코딩**: 뽐뿌는 `euc-kr` 인코딩 사용. 스크래퍼 내부에서 처리됨
- **장애 격리**: 한 소스 실패 시 다른 소스는 정상 수집 계속 (try/except per source)
- **호출 빈도**: `check_and_replenish()` 실행 시에만 호출 (일 1-2회). 별도 rate limit 불필요
