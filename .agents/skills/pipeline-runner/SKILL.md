---
name: pipeline-runner
description: blind-to-x + shorts-maker-v2 파이프라인을 통합 실행하는 스킬. 트리거: "파이프라인 실행", "pipeline run", "btx 실행", "shorts 생성", "파이프라인 상태".
---

# Pipeline Runner

blind-to-x와 shorts-maker-v2 파이프라인을 통합 관리하는 스킬입니다.

## 사용법

사용자가 파이프라인 실행을 요청하면 아래 명령어를 사용합니다.

### blind-to-x 파이프라인

```bash
# 전체 실행 (병렬 3)
cd blind-to-x && PYTHONIOENCODING=utf-8 python main.py --parallel 3

# 드라이런 (데이터 변경 없음)
cd blind-to-x && PYTHONIOENCODING=utf-8 python main.py --dry-run

# 특정 소스만
cd blind-to-x && PYTHONIOENCODING=utf-8 python main.py --sources blind fmkorea
```

### shorts-maker-v2 파이프라인

```bash
# 특정 채널 + 토픽으로 Shorts 생성
cd shorts-maker-v2 && PYTHONIOENCODING=utf-8 python -m shorts_maker_v2.cli generate --channel "AI 테크" --topic "주제"

# 일일 자동 생성 (전 채널)
PYTHONIOENCODING=utf-8 python execution/shorts_daily_runner.py
```

### 상태 확인

```bash
# n8n 브릿지 서버 상태
curl -s http://localhost:9876/health

# 최근 실행 이력
curl -s http://localhost:9876/history?limit=5

# 사용 가능한 명령어 목록
curl -s http://localhost:9876/commands
```

## 실행 전 체크리스트

1. `.env` 파일에 필요한 API 키가 설정되어 있는지 확인
2. `python execution/health_check.py`로 시스템 상태 점검
3. API 비용 예산 확인: `python execution/api_usage_tracker.py summary`

## 비용 주의사항

- blind-to-x: 무료 운영 (Gemini + Pollinations)
- shorts-maker-v2: 이미지 생성 시 DALL-E 사용 가능 (유료)
- LLM: 7-provider cascade로 비용 최소화

## 오류 처리

- 실행 실패 시 `execution/error_analyzer.py`로 원인 분석
- 텔레그램 알림 자동 발송 (TELEGRAM_ENABLED=true 시)
- 로그: `.tmp/` 디렉토리 및 `infrastructure/n8n/logs/`
