---
name: blind-to-x
description: 블라인드 인기글 스크래핑 → AI 트윗 초안 생성 → Notion 업로드 자동화 파이프라인. Playwright + Claude API + Imgur/Cloudinary + Notion API 연동. 트리거: "블라인드", "blind scraper", "트윗 초안", "tweet draft", "콘텐츠 큐레이션", "content curation".
---

# Blind to X

블라인드(teamblind.com) 인기 게시글을 스크래핑하여 X(트위터) 멘션 초안을 AI로 생성하고, 모바일 뷰 스크린샷과 함께 Notion 데이터베이스에 업로드하는 자동화 파이프라인입니다.

## 파이프라인 흐름

1. **스크래핑**: Playwright로 블라인드 인기글 수집 (iPhone 14 Pro 에뮬레이션)
2. **스크린샷**: UI 클렌징 후 모바일 해상도 캡처 (Retina @2x)
3. **이미지 업로드**: Imgur 또는 Cloudinary에 업로드
4. **AI 초안 생성**: Claude API로 3가지 톤(공감/유머/정보)의 트윗 초안 생성
5. **Notion 업로드**: 이미지, 원문, 초안을 Notion 데이터베이스에 저장

## 사전 요구사항

`blind-to-x/config.yaml` 또는 `.env` 파일에 키 설정:
- `ANTHROPIC_API_KEY`: Claude API (현재 모델: `claude-sonnet-4-20250514`)
- `NOTION_API_KEY` + `NOTION_DATABASE_ID`: Notion 연동
- `CLOUDINARY_*` 또는 Imgur Client ID: 이미지 호스팅

## 사용법

```bash
# 인기글 5개 자동 수집
python blind-to-x/blind_scraper.py --trending --limit 5

# 특정 URL 수집
python blind-to-x/blind_scraper.py --urls "URL1" "URL2"
```

## 기술 스택

- Python 3.12
- Playwright Async API (브라우저 자동화)
- Anthropic Claude API (트윗 초안 생성)
- Notion API (데이터베이스 저장)
- Imgur / Cloudinary (이미지 호스팅)

## 스케줄링

GitHub Actions로 3시간마다 자동 실행 가능 (cron: `0 */3 * * *`).
또는 Hub의 Scheduler 대시보드에서 등록하여 로컬 실행.

## 주의사항

- 블라인드 공식 API 없음 — 스크래핑 제한/차단 가능
- `delay_seconds` 설정으로 속도 제어 권장
- 저작권/개인정보 관련 주의 필요
