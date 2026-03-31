---
description: YouTube Analytics를 Notion Shorts 생산 트래킹 DB에 자동 수집하는 방법
---

# YouTube Analytics → Notion 자동화 SOP

## 목적

YouTube에 업로드된 Shorts 영상의 조회수/좋아요/댓글을 자동으로
Notion `Shorts 생산 트래킹` DB에 수집하여 퍼포먼스를 추적한다.

## 필요 환경변수 (.env)

```bash
NOTION_API_KEY=ntn_xxxxx
NOTION_TRACKING_DB_ID=31790544-c198-81c3-9536-da232ab6d22d
```

## 최초 1회 세팅: YouTube OAuth

1. [Google Cloud Console](https://console.cloud.google.com) → "YouTube Data API v3" 활성화
2. OAuth 2.0 클라이언트 ID 생성 → `credentials.json` 다운로드
3. 루트 폴더에 `credentials.json` 저장
4. 인증 실행:

   ```bash
   venv\Scripts\python execution\youtube_uploader.py --auth-only
   ```

5. 브라우저에서 Google 계정으로 로그인 → `token.json` 자동 생성

## 수동 실행

```bash
# 전체 업로드된 영상 수집
venv\Scripts\python execution\yt_analytics_to_notion.py

# 특정 채널만
venv\Scripts\python execution\yt_analytics_to_notion.py --channel "의학/건강"

# 최근 7일 이내 영상만
venv\Scripts\python execution\yt_analytics_to_notion.py --days 7

# 테스트 (Notion 업데이트 없이)
venv\Scripts\python execution\yt_analytics_to_notion.py --dry-run
```

## 자동 실행 (Windows Task Scheduler)

```bash
# 관리자 권한으로 실행 (매일 오전 9시)
scripts\schedule_yt_analytics.bat
```

## Notion에서 확인하는 방법

`Shorts 생산 트래킹` DB → 필터: `유튜브 상태 = 업로드됨` → 아래 컬럼 확인

- **조회수**: 현재 조회수
- **좋아요**: 좋아요 수
- **댓글 수**: 댓글 수
- **마지막 수집**: 가장 최근 수집 일시

## 에러 처리

| 에러 | 원인 | 해결책 |
| ---- | ---- | ------ |
| `FileNotFoundError: token.json` | OAuth 미인증 | 최초 1회 세팅 수행 |
| `OAuth 토큰 만료` | refresh_token 만료 | `youtube_uploader.py --auth-only` 재실행 |
| `NOTION_TRACKING_DB_ID 없음` | .env 미설정 | .env에 키 추가 |
| Notion 업데이트 실패 | Rate limit | 자동 재시도 (0.35s 딜레이) |

## YouTube Video ID 설정 방법

`Shorts 생산 트래킹` DB에서 영상별 `YouTube Video ID` 컬럼을 직접 입력하거나,
`유튜브 URL`이 있으면 스크립트가 자동 파싱합니다.

지원 URL 형식:

- `https://youtu.be/VIDEO_ID`
- `https://youtube.com/shorts/VIDEO_ID`
- `https://youtube.com/watch?v=VIDEO_ID`

## 알려진 제약사항

- YouTube Data API v3: 일 10,000 유닛 무료 (영상 1개 수집 = 1 유닛)
- 최대 하루 10,000개 영상 수집 가능 (실제 사용량에 비해 충분)
- Notion API: 초당 3 요청 제한 → 자동 딜레이(0.35s) 적용
