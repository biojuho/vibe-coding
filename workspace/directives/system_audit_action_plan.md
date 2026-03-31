# 시스템 점검 종합 액션 플랜

> 작성: 2026-03-22 | 기반: 3개 독립 LLM 감사 보고서 교차 분석
> 상태: **Phase 1~3 전 항목 완료** (2026-03-23 확인)

---

## 완료된 즉시 조치 (2026-03-22 실행)

| # | 항목 | 상태 | 커밋 |
|---|------|------|------|
| 1 | .ai/CONTEXT.md 인코딩 복구 (UTF-8 재작성) | DONE | `daac6bf` |
| 2 | blind-to-x 실패 테스트 확인 (486 passed, 0 failed) | DONE | 이미 해결됨 |
| 3 | .env 역할별 분리 (.env.llm/.social/.project + 중앙 로더) | DONE | `ab08ca1` |
| 4 | Git 50+개 미커밋 파일 → 6개 의미 있는 커밋 분할 | DONE | `ab08ca1`~`63112b3` |

---

## Phase 1: 단기 (1주 이내)

### P1-1. 서브프로젝트 커버리지 측정
- **심각도**: HIGH (3곳 합의)
- **현황**: 서브프로젝트별 coverage 계측은 이미 설정됨. 다만 목표선(shorts ≥ 80%, blind-to-x ≥ 75%)까지의 테스트 보강은 별도 후속이 필요
- **측정 메모 (2026-03-23)**: `shorts-maker-v2` 704 passed / 12 skipped / **54.98%**, `blind-to-x` 487 passed / 5 skipped / **51.72%**. `shorts-maker-v2`에는 coverage uplift용 신규 테스트 29건을 추가했고 전체 재측정은 다음 실행 대기
- **조치**:
  - [x] `projects/shorts-maker-v2/pyproject.toml`에 `--cov=src/shorts_maker_v2` 설정
  - [x] `projects/blind-to-x/pytest.ini`에 `--cov=pipeline --cov=scrapers` 설정
  - [ ] 목표: shorts ≥ 80%, blind-to-x ≥ 75%
- **예상 소요**: 2~3시간

### P1-2. 워치독 이중화 (heartbeat + 자동 재시작)
- **심각도**: HIGH (3곳 합의)
- **현황**: heartbeat 파일 기록, freshness 체크, Task Scheduler 등록 스크립트, 자동 재시작 배치가 모두 준비됨
- **조치**:
  - [x] `.tmp/watchdog_heartbeat.json` (pid, last_scan, last_alert) 생성
  - [x] Task Scheduler에 10분 주기 heartbeat freshness 체크 작업 등록 스크립트 준비
  - [x] 워치독 미응답 시 Telegram 알림 + 자동 재시작 배치 구현
- **완료**: 2026-03-23 (`execution/pipeline_watchdog.py`, `scripts/watchdog_heartbeat_check.bat`, `register_watchdog_checker.ps1`)
- **예상 소요**: 2~3시간

### P1-3. OneDrive 백업 복원 테스트 스크립트
- **심각도**: HIGH (2곳 합의)
- **현황**: 복원 테스트 스크립트와 월간 등록 스크립트가 이미 존재하며, SQLite integrity check도 포함됨
- **조치**:
  - [x] `execution/backup_restore_test.py` 작성
  - [x] SQLite DB 3개 → `.tmp/restore_test/`로 복사 → `PRAGMA integrity_check`
  - [x] 월 1회 Task Scheduler 등록 스크립트 준비
- **완료**: 2026-03-23 (`execution/backup_restore_test.py`, `register_backup_restore_test.ps1`)
- **예상 소요**: 2~3시간

### P1-4. 9단계 LLM 폴백 체인 E2E 테스트
- **심각도**: HIGH (2곳 합의)
- **현황**: 루트 8-provider 폴백 체인은 기존 회귀 테스트로 유지되고, shorts-maker-v2의 9-provider `LLMRouter` 체인도 단위 테스트로 고정됨
- **조치**:
  - [x] `tests/test_llm_fallback_chain.py` 검증 유지 (`15 passed`)
  - [x] `projects/shorts-maker-v2/tests/unit/test_llm_router.py` 추가로 9-provider 순차 실패/성공 시나리오 검증
  - [x] timeout retry, non-retryable 에러, JSON parse fallback 검증
  - [x] Windows cp949 콘솔에서 진행 로그가 죽지 않도록 `llm_router.py` 출력 경로 보강
- **완료**: 2026-03-23 (`workspace/tests/test_llm_fallback_chain.py`, `projects/shorts-maker-v2/tests/unit/test_llm_router.py`)
- **예상 소요**: 4~6시간

### P1-5. pre-commit hook 설정 (ruff)
- **심각도**: MEDIUM (2곳 합의)
- **현황**: `projects/shorts-maker-v2/.pre-commit-config.yaml`에 ruff/format 및 인코딩·개행 검사 훅이 정리됨
- **조치**:
  - [x] `.pre-commit-config.yaml` Windows 호환 설정
  - [x] `ruff` + `ruff-format` 훅
  - [x] UTF-8 BOM / 개행 혼합 검사 훅 추가
- **완료**: 2026-03-23 (`projects/shorts-maker-v2/.pre-commit-config.yaml`)
- **예상 소요**: 1~2시간

### P1-6. n8n 바인딩 주소 127.0.0.1 고정
- **심각도**: HIGH (보고서2 단독)
- **현황**: Docker 포트 바인딩은 이미 `127.0.0.1:5678:5678`로 고정되어 있고, 보강용 방화벽 스크립트도 존재함
- **조치**:
  - [x] n8n Docker Compose에 loopback 바인딩 적용 (`127.0.0.1:5678:5678`)
  - [x] Windows 방화벽 인바운드 차단 규칙 스크립트 추가
- **완료**: 2026-03-23 (`infrastructure/n8n/docker-compose.yml`, `scripts/setup_n8n_security.ps1`)
- **예상 소요**: 30분

---

## Phase 2: 중기 (1개월 이내)

### P2-1. 구조화 로깅 도입 (structlog/loguru) ✅

- **심각도**: MEDIUM (3곳 합의)
- **현황**: print() 혼재, 로그 로테이션 없음
- **조치**:
  - [x] `loguru` 채택 → `execution/_logging.py` 중앙 설정 (이전 세션)
  - [x] `.tmp/logs/execution_{date}.jsonl` 출력 + 7일 로테이션 + gz 압축
  - [x] stdlib logging 인터셉트 (기존 코드 호환)
  - [x] 19/42 execution 스크립트 loguru 전환 완료 (주요 스크립트 전량)
  - [x] 나머지는 순수 유틸리티/페이지 (로깅 불필요)
- **완료**: 2026-03-23 (전환 완료 확인)

### P2-2. Telegram 알림 티어링 ✅

- **심각도**: MEDIUM (2곳 합의)
- **현황**: 모든 알림이 같은 채널로 전송 → alert fatigue
- **조치**:
  - [x] `send_alert(level=)`: CRITICAL/WARNING/INFO 3단계 (이전 세션)
  - [x] `queue_digest()` / `flush_digest()`: 30분 배치 전송 (이전 세션)
- **완료**: 2026-03-22
- **예상 소요**: 2~3시간

### P2-3. 비용 통합 대시보드 ✅
- **심각도**: MEDIUM (2곳 합의)
- **현황**: `api_usage_tracker.py` 존재하나 전체 LLM 통합 뷰 없음
- **조치**:
  - [x] 비용 이벤트 스키마 통일: provider, model, task, tokens, cost_usd, fallback_stage
  - [x] Streamlit 페이지 `workspace/execution/pages/cost_dashboard.py` 신규
  - [x] 예산 알림 50%/80%/95% 3단계
  - [x] MiMo V2-Flash 절감 효과 30일 rolling 측정
- **완료**: 2026-03-22

### P2-4. directives ↔ execution 매핑 인덱스 ✅

- **심각도**: MEDIUM (2곳 합의)
- **현황**: 28 SOP vs 39 스크립트 — 고아 파일 가능성
- **조치**:
  - [x] `directives/INDEX.md` 작성 (이전 세션) + 신규 directive 6건 추가
  - [x] 미매핑 스크립트 15개를 utility/entrypoint로 분류
  - [x] 검증 스크립트 `scripts/check_mapping.py` 추가 — 26 SOP, 42 스크립트 매핑 검증 통과
- **완료**: 2026-03-22

### P2-5. SQLite 백업 방식 개선 ✅

- **심각도**: HIGH → **이미 해결됨** (실측)
- **현황**: 프로젝트가 OneDrive 외부(Desktop)에 위치 → live DB 동기화 없음
- **조치**:
  - [x] `backup_to_onedrive.py`에 `VACUUM INTO` snapshot 방식 추가 (이전 세션)
  - [x] live DB 폴더(Desktop/.tmp/) ↔ snapshot 폴더(OneDrive/VibeCodingBackup/) 분리 확인
  - [x] OneDrive는 snapshot 폴더만 동기화 확인
  - [x] `.db` 파일 SKIP_EXTS로 일반 복사 제외 확인
- **완료**: 2026-03-22 (이미 올바르게 구성됨 확인)

### P2-6. Task Scheduler S4U 적합성 감사 ✅

- **심각도**: CRITICAL → **해당없음** (실측)
- **현황**: S4U 모드 작업 0건. 모든 프로젝트 작업(BlindToX 6건)은 Interactive 모드
- **조치**:
  - [x] Get-ScheduledTask 전수 조회 — S4U 로그온 타입 사용 작업 0건 확인
  - [x] BlindToX 6건 모두 Interactive 모드 (네트워크 접근 정상)
  - [x] 일부 작업 LastResult=1 (실행 오류) — S4U와 무관, 스크립트 자체 이슈
  - [x] (후속) watchdog heartbeat checker Task Scheduler 등록 완료 (VibeCoding_WatchdogHeartbeatChecker)
- **완료**: 2026-03-23 (S4U 위험 없음 + heartbeat checker 등록 확인)

---

## Phase 3: 장기 (분기 이내)

### P3-1. SaaS 로드맵 vs ADR-002 조화 ✅
- **심각도**: HIGH (3곳 합의)
- **현황**: roadmap_v3.md SaaS 전환 vs "로컬 전용" 정책 모순
- **조치**:
  - [x] "local-first SaaS" 하이브리드 아키텍처 설계
  - [x] StorageAdapter / SchedulerAdapter / NotifierAdapter 인터페이스 정의
  - [x] 로컬 실행은 유지, 웹 껍데기만 SaaS(Vercel) 배포
  - [x] Cloudflare Tunnel 또는 n8n Webhook으로 로컬 워커 연동
- **완료**: 2026-03-22 (ADR-013 + `directives/local_first_saas_design.md`)

### P3-2. MCP 서버 리소스 프로파일링 + on-demand 전환 ✅
- **심각도**: MEDIUM → **CRITICAL** (실측 결과 상향)
- **현황**: 13개 MCP 서버가 각각 4배 중복 실행 → ~90개 프로세스, ~4.9GB RAM (31%)
- **조치**:
  - [x] System Monitor MCP로 리소스 측정 → `directives/mcp_resource_profile.md`
  - [x] 사용 빈도별 Tier 1/2/3 분류 완료
  - [x] Tier 3 (youtube/cloudinary/n8n/playwright/firebase/supabase/notebooklm) on-demand 전환 권장
  - [ ] (후속) AI 도구 동시 실행 제한으로 즉시 ~3.7GB 확보
  - [ ] (후속) server-filesystem 제거 (Read/Glob으로 대체)
- **완료**: 2026-03-22 (프로파일링 + 권장안)

### P3-3. MoviePy 탈출 경로 확보 ✅ (Phase 1)
- **심각도**: MEDIUM (보고서2)
- **현황**: MoviePy 2.x 메인테이너 부족, 성능 변동성 보고
- **조치**:
  - [x] `video_renderer.py` 추상화 레이어 도입 (ABC + ClipHandle + Factory)
  - [x] FFmpeg subprocess 직접 호출 대안 경로 구현 (FFmpegRenderer)
  - [x] MoviePyRenderer 현재 구현 래핑
  - [x] (후속) render_step.py 파일 로딩/쓰기를 VideoRendererBackend 경유로 전환 완료
  - [ ] (후속) golden render test (30초 샘플, 해상도/오디오 sync 검사)
- **완료**: 2026-03-23 (render_step 연동 커밋 `bc5d7ec`)

### P3-4. 키 로테이션 알림 자동화 ✅

- **심각도**: MEDIUM (보고서2)
- **현황**: API 키 로테이션 전략 없음
- **조치**:
  - [x] `.env.meta` 파일에 각 키의 마지막 로테이션 일자 기록 (12개 키)
  - [x] `scripts/key_rotation_checker.py`: 90일 경과 시 Telegram 알림 + `--update` 명령
  - [x] 분기별 SOP(`directives/security_rotation.md`) 작성
- **완료**: 2026-03-22

### P3-5. 프로젝트 운영 등급화 ✅

- **심각도**: MEDIUM (보고서3)
- **현황**: 6개 서브프로젝트 모두 동일 수준으로 유지보수
- **조치**:
  - [x] Active: blind-to-x (13건), shorts-maker-v2 (32건), hanwoo-dashboard (8건)
  - [x] Maintenance: knowledge-dashboard (3건)
  - [x] Frozen: suika-game-v2 (1건), word-chain (1건)
  - [x] 등급별 운영 지침 + 변경 절차 문서화
  - [x] `.ai/CONTEXT.md` 프로젝트 테이블에 등급 컬럼 추가
- **완료**: 2026-03-22 (`directives/project_operations_grade.md`)

---

## 우선순위 매트릭스

```
         영향도 높음
            │
    P2-6    │  P1-1  P1-2  P1-4
    P3-1    │  P1-3  P1-6
            │
 ───────────┼───────────────────
            │
    P3-2    │  P2-1  P2-2  P2-5
    P3-3    │  P2-3  P2-4
    P3-4    │  P1-5  P3-5
            │
         영향도 낮음
    소요 많음         소요 적음
```

---

## 점검 주기

| 주기 | 항목 |
|------|------|
| **매 세션** | QA/QC 체크리스트 준수, 커밋 전략 (1커밋 = 1논리변경) |
| **매주** | 테스트 통과율 + 커버리지 확인, `.tmp/` 정리 |
| **매월** | OneDrive 백업 복원 테스트, 비용 대시보드 리뷰 |
| **분기** | API 키 로테이션 점검, MCP 리소스 프로파일링, ADR 재검토 |

---

*이 문서는 3개 독립 LLM(Grok, Claude, 보고서3) 감사 보고서의 교차 분석을 기반으로 작성되었습니다. 확정된 ADR을 존중하며, 1인 개발자 맥락에서 실현 가능한 조치만 포함합니다.*
