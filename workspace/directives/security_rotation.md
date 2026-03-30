# API Key Rotation SOP

> 주기: 분기별 (90일) | 담당: 프로젝트 운영자

---

## 1. 자동 체크

`key_rotation_checker.py`가 90일 초과 키를 감지하면 Telegram WARNING 알림 전송.

```bash
# 수동 체크
python workspace/scripts/key_rotation_checker.py --dry-run

# Task Scheduler 등록 (매주 월요일 09:00)
# 작업: python workspace/scripts/key_rotation_checker.py
```

---

## 2. 로테이션 절차

### 2.1 일반 API 키 (OpenAI, Anthropic, Google, DeepSeek 등)

1. 해당 프로바이더 콘솔에서 새 키 생성
2. `.env.llm` (또는 해당 .env 파일)에서 키 교체
3. 서비스 재시작 없이 작동 확인 (대부분 요청 시 읽음)
4. 구 키 비활성화 (즉시 삭제하지 말고 24시간 대기)
5. `.env.meta` 업데이트:
   ```bash
   python workspace/scripts/key_rotation_checker.py --update OPENAI_API_KEY
   ```

### 2.2 Notion API 키

1. https://www.notion.so/my-integrations 에서 새 Internal Integration 생성
2. 기존 Integration의 데이터베이스 접근 권한을 새 Integration에 부여
3. `.env.social`에서 `NOTION_API_KEY` 교체
4. `blind-to-x` 파이프라인 dry-run 테스트
5. 구 Integration 비활성화

### 2.3 Telegram Bot Token

1. @BotFather에서 `/revoke` → 새 토큰 발급
2. `.env.social`에서 `TELEGRAM_BOT_TOKEN` 교체
3. `python -c "from execution.telegram_notifier import send_message; send_message('rotation test')"` 확인

### 2.4 GitHub PAT

1. GitHub Settings > Developer settings > Personal access tokens
2. Fine-grained token 새로 생성 (동일 scope)
3. `.env.project`에서 교체
4. `gh auth status` 확인
5. 구 토큰 삭제

### 2.5 Cloudinary API Key

1. Cloudinary Console > Settings > Access Keys
2. 새 API key/secret 생성
3. `.env.social`에서 교체
4. 구 키 비활성화

---

## 3. 검증 체크리스트

로테이션 후 아래를 반드시 확인:

- [ ] `python workspace/scripts/key_rotation_checker.py --dry-run` — 경고 없음
- [ ] `python workspace/execution/api_usage_tracker.py check-keys` — 모든 키 Configured
- [ ] blind-to-x dry-run 통과
- [ ] Telegram 테스트 메시지 성공
- [ ] 헬스체크 대시보드 정상

---

## 4. 비상 절차

키 유출이 의심되는 경우:

1. 즉시 해당 프로바이더에서 키 비활성화/삭제
2. 새 키 생성 후 `.env.*`에 교체
3. `.env.meta` 업데이트
4. git history에 키가 노출되었는지 확인 (ADR-002에 의해 원격 push 없으므로 로컬만 확인)
5. 프로바이더 사용량 대시보드에서 비정상 사용 확인
