# 🤖 Dopamine Bot

> **경량 커뮤니티 트렌드 스크래퍼** — requests + BeautifulSoup 기반으로 한국 커뮤니티 인기 게시글을 수집합니다.

## 📊 지원 사이트

| 사이트 | 스크래퍼 | 대상 |
|--------|----------|------|
| **FMKorea** | `scrapers/fmkorea.py` | 포텐 터짐 베스트 |
| **Ppomppu** | `scrapers/ppomppu.py` | HOT 게시글 |

## 🚀 사용법

```bash
# 의존성 설치
pip install -r requirements.txt

# FMKorea 스크래핑 테스트
python main.py --test-scraper fmkorea

# Ppomppu 스크래핑 테스트
python main.py --test-scraper ppomppu
```

## ⚙️ 설정

`config.yaml`에서 사이트별 활성화/비활성화, 수집 수, 필터(조회수/추천수 최소값)를 설정합니다.

```yaml
dopamine_bot:
  scrapers:
    fmkorea:
      enabled: true
      post_limit: 5
      filters:
        min_views: 10000
        min_recommendations: 100
```

## 🏗️ 구조

```
dopamine-bot/
├── main.py              # CLI 엔트리포인트
├── config.yaml          # 스크래퍼 설정
├── requirements.txt     # 의존성
└── scrapers/
    ├── fmkorea.py       # FMKorea 스크래퍼
    └── ppomppu.py       # Ppomppu 스크래퍼
```

## 📌 참고

- **blind-to-x**와의 차이: blind-to-x는 Playwright(헤드리스 브라우저) 기반, dopamine-bot은 requests(HTTP) 기반입니다.
  - dopamine-bot = 경량·빠름 (JS 렌더링 불필요한 사이트용)
  - blind-to-x = 무거움·강력 (로그인/JS 렌더링 필요한 사이트용)

## 📄 라이선스

이 프로젝트는 Joolife 자체 라이선스 조항을 따릅니다.
