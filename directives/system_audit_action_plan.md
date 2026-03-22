# 시스템 점검 종합 액션 플랜

> 작성: 2026-03-22 | 기반: 3개 독립 LLM 감사 보고서 교차 분석
> 상태: 즉시 조치 4건 완료, 나머지 진행 중

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
- **현황**: Root 84.72% 측정됨, shorts-maker-v2·blind-to-x 미측정
- **조치**:
  - [ ] `shorts-maker-v2/pyproject.toml`에 `--cov=src` 추가
  - [ ] `blind-to-x/pytest.ini`에 `--cov=pipeline,scrapers` 추가
  - [ ] 목표: shorts ≥ 80%, blind-to-x ≥ 75%
- **예상 소요**: 2~3시간

### P1-2. 워치독 이중화 (heartbeat + 자동 재시작)
- **심각도**: HIGH (3곳 합의)
- **현황**: `pipeline_watchdog.py`가 7개 작업 감시, 자체 헬스체크 없음
- **조치**:
  - [ ] `.tmp/watchdog_heartbeat.json` (pid, last_scan, last_alert) 생성
  - [ ] Task Scheduler에 10분 주기 heartbeat freshness 체크 작업 등록
  - [ ] 워치독 미응답 시 Telegram 알림 + 자동 재시작
- **예상 소요**: 2~3시간

### P1-3. OneDrive 백업 복원 테스트 스크립트
- **심각도**: HIGH (2곳 합의)
- **현황**: 3,702 파일 백업 존재, 복원 테스트 미실시
- **조치**:
  - [ ] `execution/backup_restore_test.py` 작성
  - [ ] SQLite DB 3개 → `.tmp/restore_test/`로 복사 → `PRAGMA integrity_check`
  - [ ] 월 1회 Task Scheduler 등록
- **예상 소요**: 2~3시간

### P1-4. 9단계 LLM 폴백 체인 E2E 테스트
- **심각도**: HIGH (2곳 합의)
- **현황**: stage 2~9가 실제 검증된 적 있는지 불확실
- **조치**:
  - [ ] `tests/test_llm_fallback_chain.py` 작성
  - [ ] `httpx.MockTransport`로 각 stage 순차 실패 시뮬레이션
  - [ ] timeout, retry, 에러 매핑 검증
- **예상 소요**: 4~6시간

### P1-5. pre-commit hook 설정 (ruff)
- **심각도**: MEDIUM (2곳 합의)
- **현황**: pre-commit이 `/bin/sh` 의존으로 Windows에서 깨짐
- **조치**:
  - [ ] `.pre-commit-config.yaml` Windows 호환 설정
  - [ ] `ruff check` + `ruff format --check` 훅
  - [ ] UTF-8 인코딩 검사 훅 추가
- **예상 소요**: 1~2시간

### P1-6. n8n 바인딩 주소 127.0.0.1 고정
- **심각도**: HIGH (보고서2 단독)
- **현황**: n8n이 0.0.0.0에 바인딩될 수 있음
- **조치**:
  - [ ] n8n Docker Compose에 `N8N_HOST=127.0.0.1` 명시
  - [ ] Windows 방화벽 인바운드 차단 규칙 추가
- **예상 소요**: 30분

---

## Phase 2: 중기 (1개월 이내)

### P2-1. 구조화 로깅 도입 (structlog/loguru)
- **심각도**: MEDIUM (3곳 합의)
- **현황**: print() 혼재, 로그 로테이션 없음
- **조치**:
  - [ ] `loguru` 채택 (structlog 대비 설정 간결)
  - [ ] `.tmp/logs/<project>/<date>.jsonl` 출력
  - [ ] 7일 로테이션, 500MB 상한
  - [ ] Telegram에는 ERROR/CRITICAL만 전송
- **예상 소요**: 3~4시간

### P2-2. Telegram 알림 티어링
- **심각도**: MEDIUM (2곳 합의)
- **현황**: 모든 알림이 같은 채널로 전송 → alert fatigue
- **조치**:
  - [ ] P1 (즉시), P2 (30분 digest), P3 (일일 요약) 3단계
  - [ ] `telegram_notifier.py`에 severity 파라미터 추가
- **예상 소요**: 2~3시간

### P2-3. 비용 통합 대시보드
- **심각도**: MEDIUM (2곳 합의)
- **현황**: `api_usage_tracker.py` 존재하나 전체 LLM 통합 뷰 없음
- **조치**:
  - [ ] 비용 이벤트 스키마 통일: provider, model, task, tokens, cost_usd, fallback_stage
  - [ ] Streamlit 페이지 `pages/cost_dashboard.py` 신규
  - [ ] 예산 알림 50%/80%/95% 3단계
  - [ ] MiMo V2-Flash 절감 효과 30일 rolling 측정
- **예상 소요**: 4~6시간

### P2-4. directives ↔ execution 매핑 인덱스
- **심각도**: MEDIUM (2곳 합의)
- **현황**: 28 SOP vs 39 스크립트 — 고아 파일 가능성
- **조치**:
  - [ ] `directives/INDEX.md` 작성: SOP → execution 매핑
  - [ ] 미매핑 스크립트를 utility/watchdog/adapter로 분류
  - [ ] 검증 스크립트 `scripts/check_mapping.py` 추가
- **예상 소요**: 1~2시간

### P2-5. SQLite 백업 방식 개선
- **심각도**: HIGH (보고서3 단독)
- **현황**: OneDrive가 live WAL DB를 직접 동기화 → 손상 가능성
- **조치**:
  - [ ] `backup_to_onedrive.py`에 `VACUUM INTO` snapshot 방식 추가
  - [ ] live DB 폴더와 snapshot 폴더 분리
  - [ ] OneDrive는 snapshot 폴더만 동기화
- **예상 소요**: 2~3시간

### P2-6. Task Scheduler S4U 적합성 감사
- **심각도**: CRITICAL (보고서3 단독)
- **현황**: S4U 모드는 네트워크 접근 없음이 문서 사양 — Playwright/외부 API와 충돌 가능
- **조치**:
  - [ ] `schtasks /query /xml` 전수 export
  - [ ] 각 작업에 needs_network/needs_gui 태그 부여
  - [ ] S4U 부적합 작업은 TASK_LOGON_PASSWORD 또는 TASK_LOGON_INTERACTIVE_TOKEN으로 전환
- **예상 소요**: 4시간

---

## Phase 3: 장기 (분기 이내)

### P3-1. SaaS 로드맵 vs ADR-002 조화
- **심각도**: HIGH (3곳 합의)
- **현황**: roadmap_v3.md SaaS 전환 vs "로컬 전용" 정책 모순
- **조치**:
  - [ ] "local-first SaaS" 하이브리드 아키텍처 설계
  - [ ] StorageAdapter / SchedulerAdapter / NotifierAdapter 인터페이스 정의
  - [ ] 로컬 실행은 유지, 웹 껍데기만 SaaS(Vercel) 배포
  - [ ] Cloudflare Tunnel 또는 n8n Webhook으로 로컬 워커 연동
- **예상 소요**: 2~3주

### P3-2. MCP 서버 리소스 프로파일링 + on-demand 전환
- **심각도**: MEDIUM (2곳 합의)
- **현황**: 10개 MCP 서버 상시 가동 → 로컬 리소스 부하 우려
- **조치**:
  - [ ] System Monitor MCP로 1주간 리소스 측정
  - [ ] 사용 빈도 낮은 서버 on-demand 시작으로 전환
  - [ ] Docker Compose profile 또는 startup script 분리
- **예상 소요**: 1주

### P3-3. MoviePy 탈출 경로 확보
- **심각도**: MEDIUM (보고서2)
- **현황**: MoviePy 2.x 메인테이너 부족, 성능 변동성 보고
- **조치**:
  - [ ] `video_renderer.py` 추상화 레이어 도입
  - [ ] FFmpeg subprocess 직접 호출 대안 경로 구현
  - [ ] golden render test (30초 샘플, 해상도/오디오 sync 검사)
- **예상 소요**: 1주

### P3-4. 키 로테이션 알림 자동화
- **심각도**: MEDIUM (보고서2)
- **현황**: API 키 로테이션 전략 없음
- **조치**:
  - [ ] `.env.meta` 파일에 각 키의 마지막 로테이션 일자 기록
  - [ ] `scripts/key_rotation_checker.py`: 90일 경과 시 Telegram 알림
  - [ ] 분기별 SOP(`directives/security_rotation.md`) 작성
- **예상 소요**: 2~3시간

### P3-5. 프로젝트 운영 등급화
- **심각도**: MEDIUM (보고서3)
- **현황**: 6개 서브프로젝트 모두 동일 수준으로 유지보수
- **조치**:
  - [ ] Active: blind-to-x, shorts-maker-v2, hanwoo-dashboard
  - [ ] Maintenance: knowledge-dashboard
  - [ ] Frozen: suika-game-v2, word-chain
  - [ ] Frozen 프로젝트는 테스트/업데이트 빈도 최소화
- **예상 소요**: 1시간 (문서 작업)

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
