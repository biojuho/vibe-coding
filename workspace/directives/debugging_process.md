# 디버깅 프로세스 SOP (Debugging Process Standard Operating Procedure)

> 기획: 아라 기획왕(Ara, Principal Product Planner)
> 바이브 코딩 기반 3계층 아키텍처 전용 디버깅 워크플로우

---

## 1. 한 줄 비전 & 사용자 가치

1.1 **한 줄 비전(Why now):** "버그를 만나면 당황하지 말고, 흐름을 따라가면 답이 보인다" — 체계적 디버깅으로 해결 시간을 절반으로 줄인다.

1.2 **타겟 사용자:**
- (A) 바이브 코딩 프로젝트를 직접 운영하는 1인 개발자(주호님)
- (B) 이 프로젝트에 참여하는 AI 에이전트(Claude, Gemini 등)

1.3 **핵심 가치:**
- (1) **재현성**: 버그를 100% 재현 가능한 상태로 격리
- (2) **속도**: 계층별 체크리스트로 원인 탐색 시간 단축
- (3) **학습 루프**: 해결한 버그를 지침/도구에 반영하여 같은 버그 재발 방지

1.4 우리 디버깅 프로세스, 한번 제대로 잡아놓으면 프로젝트 속도가 완전 달라진다.

---

## 2. 문제정의 & 범위(Scope)

2.1 **해결하려는 문제:**
- 증상: 버그 발생 시 어디서부터 봐야 할지 모름 → 산발적 디버깅 → 시간 낭비
- 원인: 3계층(지침/오케스트레이션/실행) 중 어느 계층 문제인지 분류 기준 부재
- 영향: 동일 유형 버그 반복, 수정 후 회귀, 디버깅 지식 유실

2.2 **이번 범위(In-Scope):**
- (a) 3계층별 디버깅 체크리스트
- (b) 에러 분류 체계(Triage Matrix)
- (c) 로깅/추적 표준
- (d) 해결 후 피드백 루프(지침 업데이트, 테스트 추가)
- (e) 주요 모듈별 디버깅 가이드(workspace/execution/, workspace/execution/pages/, projects/blind-to-x, projects/shorts-maker-v2)

2.3 **제외 범위(Out-of-Scope):**
- 외부 서비스 장애 대응(Google API, Notion API 다운 등) → 별도 SOP
- 인프라/서버 수준 디버깅(Docker, 클라우드 배포 등)
- 성능 프로파일링(별도 지침으로 분리)

2.4 **핵심 가정:**
- (1) 모든 execution/ 스크립트는 종료 코드(0/1/2)를 반환한다
- (2) `.env` 환경변수가 올바르게 세팅되어 있다
- (3) Python venv 환경이 활성화된 상태에서 실행한다
- (4) 테스트 스위트(pytest)가 존재하며 현재 통과 상태이다
- (5) git이 초기화되어 있고 변경 이력 추적이 가능하다

2.5 문제를 구조화하면 절반은 이미 해결된 거다. 범위를 딱 잡고 가자.

---

## 3. 디버깅 워크플로우(MVP 설계)

### 3.1 Step 0 — 증상 기록 (30초)

```
[증상 기록 템플릿]
- 무엇이 깨졌나: (에러 메시지 / 예상과 다른 동작)
- 언제부터: (마지막 정상 시점 / 최근 변경사항)
- 어디서: (파일 경로 / 모듈명 / URL)
- 재현 방법: (실행 명령어 / 입력값)
- 영향 범위: (이 기능만 / 다른 기능도 / 전체 앱)
```

### 3.2 Step 1 — 계층 분류 (1분)

| 질문 | Yes → 계층 | 확인 방법 |
|------|-----------|-----------|
| 지침(directive)이 틀렸나? (잘못된 순서, 누락된 단계) | 1계층 | directive .md 파일 검토 |
| 오케스트레이션(라우팅/판단)이 잘못됐나? | 2계층 | AI 에이전트 응답 로그 검토 |
| 실행 스크립트가 에러를 뱉나? | 3계층 | `python workspace/execution/xxx.py` 직접 실행 |

**판단 기준:**
- 에러 메시지에 Python traceback이 있다 → **3계층(실행)** 우선
- 스크립트는 정상인데 결과가 이상하다 → **2계층(오케스트레이션)** 의심
- 프로세스 자체가 정의되지 않았다 → **1계층(지침)** 문제

### 3.3 Step 2 — 격리 & 재현 (5분 이내)

- (a) **최소 재현 케이스** 만들기: 관련 없는 코드/데이터 제거
- (b) **단독 실행 테스트**: `python workspace/execution/문제스크립트.py` 직접 실행
- (c) **환경 확인**: `.env` 변수, venv 활성화, 의존성 버전
- (d) **git diff 확인**: `git diff HEAD~3` — 최근 변경이 원인인지

### 3.4 Step 3 — 원인 탐색 (계층별 체크리스트)

#### 3계층(실행) 체크리스트:
- [ ] 스택 트레이스의 마지막 라인(실제 에러 위치) 확인
- [ ] 입력값 타입/형식 검증 (None, 빈 문자열, 인코딩)
- [ ] API 응답 상태 코드 확인 (401=인증, 429=레이트리밋, 500=서버)
- [ ] 파일/DB 경로 존재 여부 확인
- [ ] import 에러 → 의존성 설치 확인 (`pip list | grep 패키지명`)
- [ ] 환경변수 누락 → `.env` 파일 확인

#### 2계층(오케스트레이션) 체크리스트:
- [ ] AI가 올바른 도구/스크립트를 호출했는가
- [ ] 인자(arguments) 전달이 정확한가
- [ ] 호출 순서가 지침과 일치하는가
- [ ] AI가 에러를 무시하고 계속 진행하지 않았는가

#### 1계층(지침) 체크리스트:
- [ ] 지침 파일(directives/*.md)에 해당 시나리오가 존재하는가
- [ ] 입력/출력 형식이 현재 스크립트와 일치하는가
- [ ] 예외 상황(edge cases)이 문서화되어 있는가
- [ ] 지침이 최신 상태인가 (API 변경, 스키마 변경 등 반영)

### 3.5 Step 4 — 수정 & 검증

- (a) **수정 전**: 실패하는 테스트를 먼저 작성 (가능한 경우)
- (b) **수정**: 최소한의 변경으로 원인 제거
- (c) **검증**:
  - `pytest` 전체 실행 (179개 테스트 통과 확인)
  - `ruff check` 린트 통과 확인
  - 직접 시나리오 재실행으로 증상 해소 확인

### 3.6 Step 5 — 피드백 루프 (자가 수정)

- (a) 관련 **지침 업데이트** (새로운 edge case, API 제약 등)
- (b) 관련 **테스트 추가** (같은 버그 재발 방지)
- (c) **MEMORY.md 업데이트** (패턴 학습)
- (d) **커밋 메시지**에 근본 원인 기록: `fix(모듈): 원인 설명`

3.6 이 프로젝트는 대박 날 거야! 디버깅도 체계가 잡히면 개발 속도가 폭발적으로 올라간다.

---

## 4. 에러 분류 체계(Triage Matrix)

### 4.1 심각도 분류

| 등급 | 기준 | 대응 시한 | 예시 |
|------|------|-----------|------|
| **P0 (Critical)** | 앱 전체 중단, 데이터 손실 위험 | 즉시 | DB 커넥션 실패, 인증 토큰 만료 |
| **P1 (High)** | 핵심 기능 불가, 우회 없음 | 당일 | 스케줄러 실행 안됨, API 호출 실패 |
| **P2 (Medium)** | 기능 저하, 우회 가능 | 2~3일 | UI 깨짐, 통계 수치 부정확 |
| **P3 (Low)** | 미관/편의, 기능 정상 | 다음 스프린트 | 로그 메시지 오타, 정렬 미스 |

### 4.2 에러 유형별 빠른 대응표

| 에러 유형 | 첫 번째 확인 | 도구 |
|-----------|-------------|------|
| `ImportError` | `pip list`, `venv` 활성화 | 터미널 |
| `KeyError` / `AttributeError` | 입력 데이터 구조 확인 | `print()`, 디버거 |
| `ConnectionError` | 네트워크, API 엔드포인트 | `curl`, `.env` |
| `FileNotFoundError` | 경로, `.tmp/` 존재 여부 | `ls`, `os.path.exists` |
| `TimeoutError` | API 레이트리밋, 네트워크 지연 | 로그, 재시도 로직 |
| `PermissionError` | 파일 권한, OAuth 토큰 | `credentials.json`, `token.json` |
| Streamlit 에러 | 세션 상태, 위젯 key 중복 | `st.session_state` 검사 |
| Playwright 에러 | 브라우저 설치, 타임아웃 | `playwright install`, `wait_for` |

4.2 에러를 만나면 당황하지 말고 이 표부터 펴라. 답이 거기 있다.

---

## 5. 모듈별 디버깅 가이드

### 5.1 execution/ 스크립트

| 모듈 | 주요 의존성 | 흔한 에러 | 디버깅 팁 |
|------|------------|-----------|-----------|
| `scheduler_engine.py` | `croniter`, `sqlite3` | DB 락, cron 표현식 파싱 | `shell=False` + `shlex.split()` 확인 |
| `notion_client.py` | `notion_client` | 속성명 불일치, 401 | config.yaml 속성 매핑 확인 |
| `content_db.py` | `sqlite3` | 마이그레이션 누락, 컬럼 없음 | `_migrate()` 실행 확인 |
| `telegram_notifier.py` | `requests` | 토큰 만료, chat_id 오류 | `.env` TELEGRAM_* 확인 |
| `github_stats.py` | `requests` | 레이트리밋(60/hr) | `GITHUB_TOKEN` 설정 확인 |
| `youtube_uploader.py` | `google-api-python-client` | OAuth 만료, 일일 할당량 | `credentials.json`/`token.json` + `videos.insert` body 확인 |

### 5.2 workspace/execution/pages/ (Streamlit)

- **공통 패턴**: `try/except ImportError` + `_MODULE_OK` / `_MODULE_ERR` 플래그
- **디버깅 순서**: (1) import 가드 확인 → (2) `st.session_state` 검사 → (3) 위젯 key 중복 확인
- **핫 리로드 주의**: Streamlit은 전체 스크립트를 재실행하므로 상태 초기화 문제 주의

### 5.3 blind-to-x

- **Playwright 리소스 누수**: `async with scraper` 패턴 사용 확인
- **스크린샷 무한 대기**: `asyncio.wait_for(timeout=30)` 적용 확인
- **Notion 중복**: `is_duplicate()` 메서드로 URL 기반 중복 체크 확인
- **Imgur 응답**: `response.json()`을 `try/except ValueError`로 감싸기

### 5.4 shorts-maker-v2

- **파이프라인 순서**: script → media → render → upload
- **병렬 미디어 처리**: `ThreadPoolExecutor` 스레드 안전성(`CostGuard._lock`) 확인
- **채널 설정 우선순위**: CLI 플래그 > DB `channel_settings` > config.yaml 기본값
- **FFmpeg 에러**: 코덱/해상도 호환성, 파일 경로 공백
- **채널 설정 반영**: `--channel` 전달 여부 확인, `channel_settings`와 실제 렌더 결과 비교
- **브랜드 에셋 생성**: 채널별 `assets/channels/<channel>` 생성 실패는 warning으로 처리되는지 확인
- **BGM 폴더 비어 있음**: `assets/bgm`이 비어 있어도 렌더가 계속 진행되는지 확인
- **업로드 재시도**: `youtube_error`가 별도 컬럼에 저장되고 `notes`를 덮어쓰지 않는지 확인
- **YouTube 정책**: 미검증 API 프로젝트는 private 업로드 제한 가능성 고려

5.4 모듈마다 함정이 있다. 미리 알면 안 빠진다.

---

## 6. 로깅 & 추적 표준

### 6.1 로그 레벨 규칙

| 레벨 | 용도 | 예시 |
|------|------|------|
| `DEBUG` | 개발 중 상세 추적 | 변수 값, 루프 카운터 |
| `INFO` | 정상 실행 흐름 | "API 호출 성공", "파일 저장 완료" |
| `WARNING` | 비정상이지만 계속 가능 | "레이트리밋 접근", "폴백 사용" |
| `ERROR` | 기능 실패 | "API 호출 실패: 401", "파일 미존재" |
| `CRITICAL` | 앱 중단 수준 | "DB 연결 불가", "인증 토큰 없음" |

### 6.2 로그 포맷 표준

```python
import logging
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)
```

### 6.3 디버깅용 임시 로그 규칙

- `# DEBUG:` 접두사 주석으로 임시 print/log 표시
- 수정 완료 후 반드시 제거 (커밋 전 `grep -r "# DEBUG:" .` 확인)

6.3 로그는 미래의 나에게 보내는 편지다. 깔끔하게 남기자.

---

## 7. 리스크 & 대응

7.1 **리스크 Top 5:**

| # | 리스크 | 확률 | 영향 | 완화 전략 |
|---|--------|------|------|-----------|
| 1 | API 키/토큰 만료로 전체 기능 중단 | 중 | 상 | `.env` 만료일 추적, 갱신 알림 자동화 |
| 2 | DB 스키마 변경으로 기존 데이터 깨짐 | 중 | 상 | `_migrate()` 패턴 준수, 백업 후 마이그레이션 |
| 3 | 외부 API 변경(Notion, YouTube, Telegram) | 중 | 중 | 버전 고정, CHANGELOG 모니터링 |
| 4 | 디버깅 중 의도치 않은 프로덕션 데이터 수정 | 하 | 상 | `.tmp/` 격리, 테스트 DB 분리 |
| 5 | 디버깅 기록 유실 | 중 | 중 | MEMORY.md + git commit 메시지 활용 |

7.2 **"망하면 안 되는 것" 3가지:**
- (1) `.env`, `credentials.json`, `token.json`이 git에 올라가면 안 된다
- (2) 프로덕션 Notion DB 데이터를 디버깅 중 삭제하면 안 된다
- (3) 디버깅 핫픽스가 기존 테스트를 깨뜨리면 안 된다

7.2 리스크는 숨기지 말고 드러내야 관리할 수 있다.

---

## 8. 디버깅 완료 체크리스트

```
[디버깅 완료 확인]
- [ ] 증상이 완전히 해소되었는가
- [ ] pytest 전체 통과 (179개+)
- [ ] ruff check 린트 통과
- [ ] 관련 지침(directives/*.md) 업데이트 했는가
- [ ] 테스트 케이스 추가 했는가 (재발 방지)
- [ ] MEMORY.md에 패턴/교훈 기록 했는가
- [ ] 임시 디버깅 코드(print, # DEBUG:) 제거 했는가
- [ ] 커밋 메시지에 근본 원인 기록 했는가
```

8 체크리스트를 다 채우면 그 버그는 다시는 안 온다. 끝까지 마무리하자.

---

## 9. 의사소통 & 운영

9.1 **버그 리포트 템플릿:**
```
제목: [P등급] 모듈명 - 증상 한 줄
환경: Python 버전 / OS / venv 여부
재현: 실행 명령어 + 입력값
기대: 예상 동작
실제: 실제 동작 + 에러 메시지
스크린샷/로그: (해당 시)
```

9.2 **이슈 분류 규칙:**
- `bug/critical` → P0-P1: 즉시 수정
- `bug/normal` → P2: 현재 스프린트 내 수정
- `bug/minor` → P3: 백로그
- `improvement` → 버그 아닌 개선 → 별도 관리

9.3 **변경관리:** 디버깅 중 발견한 개선점은 별도 이슈로 분리. 디버깅 PR에 기능 추가 금지.

9.3 디버깅은 디버깅만, 개선은 개선으로. 섞으면 둘 다 실패한다.

---

## 10. 다음 액션

10.1 **완료된 액션:**
- (1) 이 SOP를 `directives/debugging_process.md`로 저장 완료 ✅
- (2) execution/ 스크립트 로깅 표준 점검 완료 ✅ (4개 logging 적용, 나머지 CLI-only print 준수)
- (3) `execution/health_check.py` 제작 완료 ✅ (31개 항목: env, api, filesystem, database, environment)
- (4) `execution/debug_history_db.py` 제작 완료 ✅ (이력 CRUD + 에러 패턴 매핑 + 19개 패턴 시드)
- (5) 기존 버그 이력 20건 시드 등록 완료 ✅

10.2 **도구 사용법:**

```bash
# 시스템 헬스 체크
python workspace/execution/health_check.py               # 전체 점검
python workspace/execution/health_check.py --category api # API만
python workspace/execution/health_check.py --json         # JSON 출력

# 디버깅 이력 기록
python workspace/execution/debug_history_db.py add --severity P1 --module 모듈명 \
    --symptom "증상" --cause "원인" --solution "해결"
python workspace/execution/debug_history_db.py search "키워드"
python workspace/execution/debug_history_db.py stats
python workspace/execution/debug_history_db.py lookup "에러메시지"  # 패턴 자동 매칭
```

10.3 **선택적 다음 단계:**

- Streamlit 대시보드에 헬스 체크 탭 추가
- 스케줄러에 주기적 헬스 체크 + Telegram 알림 연동
- 디버깅 이력에서 반복 패턴 자동 감지 (top N 에러 분석)

10.3 체계가 잡히면 버그가 와도 무섭지 않다. 하나씩 단단하게 만들어가자.
