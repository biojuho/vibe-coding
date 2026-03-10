# n8n 워크플로우 자동화 시스템

## 아키텍처

```
n8n (Docker:5678) ──HTTP──> Bridge Server (Host:9876) ──subprocess──> Python 파이프라인
```

- **n8n**: Docker 컨테이너에서 워크플로우 오케스트레이션
- **Bridge Server**: 호스트 Windows에서 실행되는 FastAPI 서버 (보안 게이트웨이)
- **파이프라인**: 기존 Blind-to-X / Shorts Maker Python 스크립트 (변경 없음)

## 빠른 시작

```bash
# 1. 의존성 설치 (최초 1회)
pip install fastapi uvicorn

# 2. n8n 시스템 시작
start_n8n.bat

# 3. n8n UI 접속
# http://localhost:5678 (admin / n8n-vibe-2026)

# 4. 워크플로우 import
# n8n UI → Settings → Import → workflows/ 폴더의 JSON 파일 선택
```

## 종료

```bash
stop_n8n.bat
```

## 파일 구조

```
infrastructure/n8n/
├── docker-compose.yml     # n8n 컨테이너 설정
├── bridge_server.py       # HTTP 브릿지 서버
├── healthcheck.py         # 시스템 헬스체크 스크립트
├── start_n8n.bat          # 원클릭 시작
├── stop_n8n.bat           # 원클릭 종료
├── logs/                  # 실행 로그 (자동 생성)
└── workflows/
    ├── btx_pipeline_schedule.json   # BTX 스케줄링 워크플로우
    └── system_healthcheck.json      # 헬스체크 워크플로우
```

## 보안

- Bridge Server: Bearer 토큰 인증 (`n8n-bridge-secret-2026`)
- n8n UI: 기본 인증 (`admin` / `n8n-vibe-2026`)
- 커맨드 화이트리스트: 사전 등록된 명령어만 실행 가능
- localhost 전용: 외부 접근 불가

## n8n 최초 설정

1. n8n UI 접속 → 계정 생성
2. **Settings → Credentials**: `Header Auth` 추가
   - Name: `Bridge Auth`
   - Header Name: `Authorization`
   - Header Value: `Bearer n8n-bridge-secret-2026`
3. **Settings → Import**: `workflows/` 폴더의 JSON 파일 import
4. 각 워크플로우 활성화
