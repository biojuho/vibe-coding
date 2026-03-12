# YouTube Data MCP Server

YouTube Data API v3 기반 MCP 서버입니다.

## 제공 도구

| 도구 | 설명 |
|------|------|
| `get_channel_stats` | 채널 구독자 수, 총 조회수, 영상 수 조회 |
| `get_recent_videos` | 채널 최신 영상 목록 + 통계 조회 |
| `get_video_analytics` | 영상 상세 통계 (조회수, 좋아요, 댓글, 참여율, 길이) |
| `search_trending` | 키워드 기반 트렌딩 영상 검색 |

## 설치

```bash
cd infrastructure/youtube-mcp
pip install -r requirements.txt
```

## 사전 요구사항

프로젝트 루트에 `token.json` 파일이 필요합니다 (Google OAuth 토큰).
기존 `youtube_uploader.py` 인증 흐름으로 생성된 토큰을 사용합니다.

필요한 OAuth 스코프:
- `youtube.readonly`
- `yt-analytics.readonly`

## 실행

```bash
python server.py
```

## Claude Desktop 설정

`claude_desktop_config.json`에 추가:

```json
{
  "mcpServers": {
    "youtube-data": {
      "command": "python",
      "args": ["C:/Users/박주호/Desktop/Vibe coding/infrastructure/youtube-mcp/server.py"]
    }
  }
}
```

## 환경 변수 (선택)

| 변수 | 설명 | 기본값 |
|------|------|--------|
| `YOUTUBE_TOKEN_PATH` | OAuth 토큰 파일 경로 | `../../token.json` (서버 기준 상대 경로) |
