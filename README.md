# Vibe Coding: Personal Agent (Jarvis)

[![root-quality-gate](https://github.com/<OWNER>/<REPO>/actions/workflows/root-quality-gate.yml/badge.svg)](https://github.com/<OWNER>/<REPO>/actions/workflows/root-quality-gate.yml)

🇬🇧 Your all-in-one AI assistant for desktop control, daily briefings, and fun.
🇰🇷 데스크톱 제어, 일일 브리핑, 엔터테인먼트를 위한 올인원 AI 어시스턴트입니다.

## Features (주요 기능)
- **Daily Briefing (일일 브리핑)**: Weather, news, and voice synthesis (TTS). / 날씨, 뉴스 및 음성 합성(TTS) 제공.
- **Desktop Control (데스크톱 제어)**: Launch apps, open websites, and monitor system stats. / 앱 실행, 웹사이트 열기 및 시스템 상태 모니터링.
- **RAG Brain (RAG 브레인)**: Chat with your local documents using Gemini/OpenAI providers. / Gemini/OpenAI 모델을 활용해 로컬 문서와 대화.
- **Word Chain Game (끝말잇기 게임)**: Play a game of word chain with the AI. / AI와 함께하는 끝말잇기 게임.

## Installation (설치 방법)
1. 🇬🇧 Run `setup.bat` (Windows) to install dependencies. / 🇰🇷 `setup.bat` (Windows) 파일을 실행하여 의존성 패키지를 설치합니다.
2. 🇬🇧 Configure required API keys in `.env`. / 🇰🇷 `.env` 파일에 필요한 API 키를 설정합니다.

## Usage (사용법)
```bash
venv\Scripts\activate
venv\Scripts\python.exe -m streamlit run projects/personal-agent/app.py
```

🇬🇧 **Readiness check (준비 상태 확인)**: / 🇰🇷 **준비 상태 확인**:
```bash
venv\Scripts\python.exe scripts\doctor.py
```

🇬🇧 **Run tests (테스트 실행)**: / 🇰🇷 **테스트 실행**:
```bash
venv\Scripts\python.exe -m pip install -r requirements-dev.txt
venv\Scripts\python.exe -m pytest -q tests
```

🇬🇧 **Quality gate (single command) / 🇰🇷 품질 검사 (단일 명령어)**:
```bash
venv\Scripts\python.exe scripts\quality_gate.py
```

🇬🇧 **CI uses the same command / 🇰🇷 CI 서버에서도 동일한 명령어를 사용합니다**:
```bash
python scripts/quality_gate.py
```

## Root Repository Bootstrap (루트 저장소 초기화)
🇬🇧 Initialize and connect this workspace as the root Joolife repository:
🇰🇷 이 워크스페이스를 Joolife 루트 저장소로 초기화하고 연결합니다:

```bash
git init
git branch -M main
git remote add origin https://github.com/<OWNER>/<REPO>.git
git push -u origin main
```

🇬🇧 **Root tracking policy / 🇰🇷 루트 저장소 추적 정책**:
- Included (포함 항목): `execution/`, `scripts/`, `tests/`, `pages/`, `directives/`, `_archive/personal-agent/`, and root config/docs files.
- Excluded (제외 항목): nested independent repos (`blind-to-x/`, `hanwoo-dashboard/`, `knowledge-dashboard/`) and side projects via `.gitignore`. (독립된 하위 저장소 및 사이드 프로젝트는 제외됨)

## CI Quality Gate (CI 품질 검사)
- **Workflow file (워크플로우 파일)**: `.github/workflows/root-quality-gate.yml`
- **Trigger (트리거 조건)**: `push` / `pull_request` on `main`
- **Runtime (실행 환경)**: `ubuntu-latest`, Python `3.14`
- **Command (실행 명령어)**: `python scripts/quality_gate.py`

🇬🇧 **Recommended repository rollout / 🇰🇷 권장 저장소 설정**:
1. Enable branch protection for `main` (PR merge only). / `main` 브랜치 보호 활성화 (PR 병합만 허용).
2. Add `root-quality-gate` as a required status check. / `root-quality-gate`를 필수 상태 확인 항목으로 추가.
3. Triage failures by phase in logs: `smoke_check`, `pytest`, `static analysis`. / 로그의 단계별(`smoke_check`, `pytest`, `static analysis`) 실패 원인 분류.

🇬🇧 **Recommended initial commits / 🇰🇷 권장 초기 커밋 메시지**:
1. `chore(repo): bootstrap root joolife repository skeleton`
2. `ci(quality): add root quality gate workflow and dependencies`

## Maintenance Scripts (유지보수 스크립트)
🇬🇧 **Upgrade nested repositories safely / 🇰🇷 하위 저장소 안전 업데이트**:
```bash
venv\Scripts\python.exe scripts\update_all.py --list-only
venv\Scripts\python.exe scripts\update_all.py --strategy ff-only
```

🇬🇧 **Create data backups / 🇰🇷 데이터 백업 생성**:
```bash
venv\Scripts\python.exe scripts\backup_data.py --with-env
venv\Scripts\python.exe scripts\backup_data.py --dry-run --with-env
```

## Telegram Notifications
🇬🇧 Configure a Telegram Bot for scheduler alerts and daily report delivery.
🇰🇷 스케줄러 알림과 일일 리포트 전송을 위한 텔레그램 봇 설정입니다.

```bash
python execution/telegram_notifier.py check
python execution/telegram_notifier.py updates --limit 10
python execution/telegram_notifier.py send --message "hello from Joolife"
python execution/daily_report.py --format markdown --telegram
```

- `TELEGRAM_BOT_TOKEN`: BotFather token
- `TELEGRAM_CHAT_ID`: target chat ID
- `TELEGRAM_NOTIFY_SCHEDULER`: `none`, `failures`, or `all`

## Legal and Privacy Disclaimer (법적 및 개인정보 보호 고지)
1. **Local Execution (로컬 실행)**: 🇬🇧 This software runs on your local machine. The developer does not collect or store your data. / 🇰🇷 이 소프트웨어는 로컬 컴퓨터에서 실행됩니다. 개발자는 사용자의 데이터를 수집하거나 저장하지 않습니다.
2. **API Usage (API 사용)**: 🇬🇧 User prompts may be processed by external model providers according to your configuration. / 🇰🇷 사용자 프롬프트는 설정에 따라 외부 모델 제공자가 처리할 수 있습니다.
3. **No Liability (면책 조항)**: 🇬🇧 The user assumes all responsibility for use of this software. / 🇰🇷 소프트웨어 사용으로 인한 모든 책임은 사용자에게 있습니다.
4. **Copyright (저작권)**: 🇬🇧 External content summaries are for informational purposes. / 🇰🇷 외부 콘텐츠 요약은 정보 제공 목적으로만 사용됩니다.

## License (라이선스)
MIT License.
