# 📋 세션 로그 (SESSION LOG)

> 각 AI 도구가 작업할 때마다 아래 형식으로 기록합니다.
> 최신 세션이 파일 상단에 위치합니다 (역순).

---

## 2026-03-08 09:40 KST — Gemini/Antigravity

### 작업 요약
QA/QC 4단계 워크플로우 프롬프트 모음 생성 (개발→QA→수정→QC)

### 변경한 파일
| 파일 | 변경 내용 |
|------|-----------|
| `.agents/workflows/qa-qc.md` | 🆕 생성 — `/qa-qc` 슬래시 커맨드용 워크플로우 요약 |
| `directives/qa_qc_workflow.md` | 🆕 생성 — 전체 SOP (4단계 프롬프트 원문 포함 + 마스터 프롬프트) |
| `.agents/rules/project-rules.md` | `작업 중 (상시)` 섹션에 QA/QC 통과 의무화 규칙 추가 |
| `directives/session_workflow.md` | 작업 중 절차 및 세션 종료 절차에 QA/QC 단계 연동 |
| `.agents/workflows/end.md` | 작업 요약 시 QA/QC 통과 여부 검증 항목 추가 |

### 핵심 결정사항
- 3계층 아키텍처에 맞게 워크플로우(2계층)와 지침(1계층) 양쪽에 파일 생성
- 워크플로우 파일은 실행 절차 요약, 지침 파일은 각 STEP 프롬프트 원문 포함
- 자동화 세션 훅(`project-rules`, `start`, `end`) 및 `session_workflow` SOP에 QA/QC 검증 절차를 편입시켜, 별도의 수동 실행 없이도 코드 변경 시 자연스럽게 품질 검증 루프를 타도록 강제함

### 미완료 TODO
- 없음

### 다음 도구에게 전달할 메모
- `/qa-qc` 슬래시 커맨드로 워크플로우 실행 가능
- 상세 프롬프트는 `directives/qa_qc_workflow.md` 참조
- 노드 분리 실행 시 STEP 1~4 각각, 통합 실행 시 마스터 프롬프트 사용

---

## 2026-03-08 08:17 KST — Gemini/Antigravity

### 작업 요약
blind-to-x 전체 현황 점검 + 4개 이슈 일괄 해결 (Notion DB 스키마 정렬, 테스트 수정, 환경 확인, E2E 검증)

### 변경한 파일
| 파일 | 변경 내용 |
|------|-----------|
| Notion DB `2d8d6f4c` | 21개 속성 추가 (10개 → 31개): 분석 메트릭(4), 인텔리전스(4), 운영(5), 콘텐츠(4), 추적(4) |
| `blind-to-x/tests_unit/test_notion_accuracy.py` | `test_exact_duplicate_check_uses_equals`, `test_duplicate_query_error_returns_none` — `query_collection` 직접 mock으로 변경 |
| `blind-to-x/tests_unit/test_notion_connection_modes.py` | `test_duplicate_check_uses_data_source_query` — 동일 패턴 수정 |

### 핵심 결정사항
- Notion DB에 파이프라인 설계에 맞는 전체 속성 추가 (축소 대신 확장 선택)
- 테스트 mock 전략: `databases.query()` library mock → `uploader.query_collection` 직접 mock (httpx 직접 호출 구조에 맞춤)

### 미완료 TODO
- 없음 (모든 이슈 해결 완료)

### 다음 도구에게 전달할 메모
- Notion DB 31개 속성 존재, 실제 업로드 검증 완료 (`Total: 1 | OK 1 | FAIL 0`)
- 유닛 테스트 105/105 통과
- MS Store Python shim 비활성화 완료 → `python` 명령 정상
- `run_scheduled.bat`은 venv Python 절대 경로 사용
- Windows 작업 스케줄러 5개 시간대 등록 확인 (BlindToX_0500/0900/1300/1700/2100)

---

## 2026-03-07 21:51 KST — Gemini/Antigravity

### 작업 요약
blind-to-x Notion 업로드 문제 해결 (2일간 장애 복구) + 로컬 스케줄러 등록 + Gemini API 키 전체 교체

### 변경한 파일
| 파일 | 변경 내용 |
|------|-----------|
| `blind-to-x/.env` | `NOTION_DATABASE_ID` 수정 (`7253f1ef...` → `2d8d6f4c...`), `GEMINI_API_KEY` 추가 |
| `blind-to-x/pipeline/notion_upload.py` | `_retrieve_collection`에 httpx 폴백 추가 (notion-client 2.2.1 properties 버그 우회), `query_collection`에서 httpx 직접 REST API 호출로 변경 (databases.query 메서드 제거 대응), `_page_parent_payload`를 `database_id`로 복원 |
| `shorts-maker-v2/.env` | `GEMINI_API_KEY` 새 키로 교체 |
| `hanwoo-dashboard/.env` | `GEMINI_API_KEY` 추가 |
| `infrastructure/.env` | `GEMINI_API_KEY` 추가 |
| `.env` (루트) | `GEMINI_API_KEY` 추가 |

### 핵심 결정사항
- `notion-client 2.2.1` 자체 버그 우회: 라이브러리가 `databases.retrieve`에서 properties를 빈 딕셔너리로 반환하고, `databases.query` 메서드가 제거됨 → `httpx`로 Notion REST API 직접 호출하여 해결
- 올바른 Notion DB ID: `2d8d6f4c-9757-4aa8-9fcb-2ae548ed6f9a` (📋 X 콘텐츠 파이프라인)
- Windows 작업 스케줄러에 5개 시간대 등록 (05/09/13/17/21시, 각 3건)
- Gemini API 키 전체 프로젝트 통일: `AIzaSyARsRAGjc4oVom2JK9kZILl9x9ZvFvn-Eo`

### 미완료 TODO
- Windows 앱 실행 별칭 해제 후 **새 터미널 열면** python PATH 문제 해결됨 (현재 터미널에서는 전체 경로 필요)
- 파이프라인 exit code 1 원인 추가 조사 (Notion 업로드는 성공하나 이미지 관련 부차적 에러 가능)

### 다음 도구에게 전달할 메모
- `notion-client 2.2.1`은 현재 Notion API와 호환 불량 → `notion_upload.py`에 httpx 폴백이 적용됨. 라이브러리 업그레이드 시 폴백 제거 가능
- `run_scheduled.bat`은 `venv/Scripts/python.exe` 사용 → venv에 의존성 설치 상태 유지 필요
- 스케줄러는 "대화형만" 모드 → PC 로그인 상태에서만 실행됨

---

## 2026-03-07 — Claude Code (Opus 4.6)

### 작업 요약
execution/ 테스트 커버리지 84% → 100% 달성 (705 tests, 3630 statements, 0 missing)

### 변경한 파일
| 파일 | 변경 내용 |
|------|-----------|
| `tests/test_llm_client.py` | +902줄: bridged repair loop, unsupported provider, test_all_providers 등 전체 미커버 경로 테스트 |
| `tests/test_api_usage_tracker.py` | +278줄: JSONDecodeError 핸들링, bridge 통계 등 |
| `tests/test_content_db.py` | +382줄: youtube stats, failure items, bgm_missing 경로 등 |
| `tests/test_joolife_hub.py` | +411줄: Streamlit 모듈 모킹, kill_all 버튼 side_effect 등 |
| `tests/test_youtube_uploader.py` | +447줄: upload_pending_items, OAuth flow 등 |
| `tests/test_language_bridge.py` | +225줄: empty content validation, jamo/mojibake 감지 등 |
| `tests/test_topic_auto_generator.py` | +217줄: Notion 연동, 중복 토픽 필터 등 |
| `tests/test_selector_validator.py` | +202줄: curl_cffi cp949 인코딩, euc-kr 폴백 등 |
| `tests/test_debug_history_db.py` | +175줄: SQLite CRUD, 검색, 통계 |
| `tests/test_scheduler_engine.py` | +171줄: setup_required status, disabled task 등 |
| `tests/test_health_check.py` | +146줄: venv 미활성화, git 미존재 등 |
| `tests/test_shorts_daily_runner.py` | +112줄: 스케줄 실행, 에러 핸들링 |
| `tests/test_yt_analytics_to_notion.py` | +111줄: YT→Notion 동기화 |
| `tests/test_community_trend_scraper.py` | +54줄: 스크래핑 결과 파싱 |
| `tests/test_telegram_notifier.py` | +53줄: 알림 전송 경로 |
| `tests/test_youtube_analytics_collector.py` | +44줄: 수집기 경로 |
| `execution/llm_client.py` | pragma: no cover (line 349, dead code) |
| `execution/content_db.py` | pragma: no cover (line 390, dead code) |
| `execution/youtube_uploader.py` | pragma: no cover (lines 304-305, sys.path guard) |
| `execution/community_trend_scraper.py` | pragma: no cover (line 34, conditional import) |
| `execution/topic_auto_generator.py` | pragma: no cover (line 35, conditional import) |
| `directives/session_workflow.md` | 세션 워크플로우 업데이트 |

### 핵심 결정사항
- 도달 불가능한 dead code 4건에 `# pragma: no cover` 적용 (aggregate SQL always returns row, _get_client raises first 등)
- Streamlit 테스트: module-level MagicMock 패턴 사용 (import 전에 sys.modules 패치)
- curl_cffi 테스트: patch.dict("sys.modules") 패턴 사용

### 미완료 TODO
- 없음

### 다음 도구에게 전달할 메모
- 21개 execution 파일 전체 100% 커버리지 달성
- 705 tests passed, 1 skipped, 3630 statements, 0 missing
- pytest.ini에 `--cov-fail-under=80` 설정되어 있으므로 새 코드 추가 시 테스트 필수

---

## 2026-03-06 — Claude Code (Opus 4.6)

### 작업 요약
blind-to-x 품질 최적화 + 비용 최적화 4-Phase 고도화

### 변경한 파일
| 파일 | 변경 내용 |
|------|-----------|
| `blind-to-x/pipeline/draft_generator.py` | DraftCache 연동 (SHA256 캐시키), provider 스킵 (circuit breaker), 성공 시 circuit close, 비복구 에러 시 failure 기록, 차등 타임아웃 (유료 45s/무료 30s), Anthropic 모델 haiku로 다운그레이드 |
| `blind-to-x/pipeline/image_generator.py` | ImageCache 연동 (topic+emotion), 프롬프트 품질 검증 (5단어 미만 스킵), Gemini 실패 시 Pollinations 자동 폴백 |
| `blind-to-x/pipeline/content_intelligence.py` | publishability 기본점수 35→25 하향, 토픽 감지 가중 8→15, 직장인 관련성 12→18, 컨텍스트 길이 차등, LLM viral boost 보더라인(50-70점)에서만 실행 + 최대 10점 캡, performance 무데이터 50→45 |
| `blind-to-x/pipeline/cost_tracker.py` | Anthropic 가격 haiku 기준 ($0.80/$4.00), 포스트당 평균 비용 요약에 추가 |
| `blind-to-x/pipeline/cost_db.py` | `get_cost_per_post()` 메서드 추가 (30일 평균 비용/포스트) |
| `blind-to-x/pipeline/process.py` | 드래프트 품질 검증 (트윗 길이, 뉴스레터 최소 단어수) |
| `blind-to-x/main.py` | dry-run 시 이미지 생성 스킵 |
| `blind-to-x/config.example.yaml` | anthropic 모델 haiku, 가격 업데이트, image/ranking 새 설정 추가 |
| `blind-to-x/config.ci.yaml` | config.example.yaml과 동기화 |
| `blind-to-x/tests_unit/conftest.py` | `_DRAFT_CACHE` 참조 제거 → DraftCache/provider_failures 초기화 |
| `blind-to-x/tests_unit/test_cost_controls.py` | cache hit 테스트 수정 (call_count 2→1) |
| `blind-to-x/tests_unit/test_optimizations.py` | DraftCache import 수정, DALL-E 플래그 테스트 수정, call_count 4→2 |
| `blind-to-x/tests_unit/test_draft_generator_multi_provider.py` | fallback 테스트 call_count 2→1, bridge 테스트 지원 provider로 변경 |
| `blind-to-x/tests_unit/test_scrapers.py` | ImageGenerator 테스트 프롬프트 5단어 이상으로 변경 |

### 핵심 결정사항
- Anthropic 모델 `claude-sonnet-4` → `claude-haiku-4-5` (비용 4-5x 절감)
- DraftCache (SQLite 72h TTL) + ImageCache (SQLite 48h TTL) 파이프라인 연동
- LLM viral boost: 전수 → 보더라인(50-70점)만 + 최대 10점 캡
- publishability 기본점수 하향 (35→25): 저품질 컨텐츠 더 엄격히 필터링
- provider circuit breaker: 비복구 에러 시 자동 스킵 등록 + 성공 시 해제

### 미완료 TODO
- 없음

### 다음 도구에게 전달할 메모
- 전체 105개 테스트 통과
- config.yaml에 새 키 추가됨: `ranking.llm_viral_boost`, `image.provider`, `image.min_prompt_words`
- `_DRAFT_CACHE` 모듈 레벨 딕셔너리는 완전 제거됨 → SQLite DraftCache로 대체

---

## 2026-03-06 14:13 KST — Gemini/Antigravity

### 작업 요약
AI 도구 공유 컨텍스트 시스템 초기 세팅

### 변경한 파일
| 파일 | 변경 내용 |
|------|-----------|
| `.ai/CONTEXT.md` | 🆕 생성 — 프로젝트 분석 결과 기반 마스터 컨텍스트 |
| `.ai/SESSION_LOG.md` | 🆕 생성 — 세션 로그 템플릿 (이 파일) |
| `.ai/DECISIONS.md` | 🆕 생성 — 아키텍처 결정 기록 |

### 핵심 결정사항
- `.ai/` 폴더를 프로젝트 루트에 생성하여 모든 AI 도구가 공유하는 컨텍스트 허브로 사용
- 세션 로그는 역순(최신 상단) 기록 방식 채택

### 미완료 TODO
- 없음

### 다음 도구에게 전달할 메모
- 작업 시작 전 반드시 이 3개 파일(`CONTEXT.md`, `SESSION_LOG.md`, `DECISIONS.md`)을 먼저 읽을 것
- `DECISIONS.md`의 결정사항은 임의 변경 금지
- 세션 종료 시 반드시 이 파일에 작업 기록 추가할 것

---

<!--
## 세션 기록 템플릿 (복사해서 사용)

## YYYY-MM-DD HH:MM KST — [도구명]

### 작업 요약
(한 줄로 작성)

### 변경한 파일
| 파일 | 변경 내용 |
|------|-----------|
| `파일경로` | 변경 설명 |

### 핵심 결정사항
- (결정 내용)

### 미완료 TODO
- (미완료 항목 또는 "없음")

### 다음 도구에게 전달할 메모
- (인수인계 사항)
-->
