# 기술 부채 리뷰 회의록 — 2026-04-15

> 작성: Claude Code (Opus 4.6 1M context)
> 조사 범위: `.ai/` 문서 일체, `projects/*/CLAUDE.md` 지뢰밭, `execution/`/`workspace/`, 2026-04-14~15 세션 실측 관찰
> 목적: 누적 기술 부채 재정리 → 우선순위 → 실행 가능 개선안 제안

---

## 1. 참석 관점 (Perspectives)

| 관점 | 주요 시선 |
|---|---|
| QA/테스트 | 파서 프래질리티, 스킵 테스트, silent failure, smoke test 비대칭 |
| DevOps/협업 | 병렬 AI 세션 경쟁, pre-commit hook 마찰, 워크트리 스필오버 |
| 아키텍처 | 금지 영역 확산, 500줄 `main.py`, LLM fallback 체인 복잡도 |
| 보안/인프라 | 과거 커밋 시크릿, GitHub Pro 블로커, Korean path 워크어라운드 |

---

## 2. 의제 (Agenda)

1. 2026-04-15 기준 누적 부채 인벤토리 검토
2. 근본 원인별 군집화 및 우선순위 합의
3. 3주 내 실행 가능한 개선안 확정
4. 블로커/승인 필요 항목 사용자 결정 요청 목록 작성

---

## 3. 현황 요약

### 3.1 인벤토리 집계

- **문서화된 부채**: 24건 (블로커 4 / 심각 9 / 중간 8 / 경미 3)
- **코드 내 미해결 마커/silent failure**: 25건 (블로커 3 / 심각 13 / 중간 7 / 경미 2)
- **이번 세션 실측 관찰**: 5건 (병렬 세션 경쟁, 파서 regex 반복 패치, 스캐너 비대칭, 훅 마찰, 픽스처 오염)

### 3.2 근본 원인 분류

| 군집 | 건수 | 공통 원인 |
|---|---|---|
| A. 협업/워크플로우 부채 | 9 | 다수 AI 에이전트 병렬 실행, 경쟁 상태 방지 메커니즘 부족 |
| B. Silent failure / 관찰 불가 부채 | 13 | `except Exception: pass` 관행, 로깅 누락, cost/timezone 오류 소실 |
| C. 하드코딩/환경 결합 부채 | 4 | localhost URI 복사, env override 미도입 |
| D. 피처 미완성 부채 | 3 | Naver blog, Telegram 승인 버튼, LLM 직접 API fallback |
| E. 테스트 인프라 부채 | 5 | 스킵된 테스트, 파서 regex 취약성, Python/Node 스캐너 비대칭 |
| F. 보안/규정 부채 | 3 | 과거 커밋 시크릿, GitHub Pro 블로커, `.secrets.baseline` 과거 커버리지 한계 |
| G. 플랫폼/환경 부채 | 5 | Korean path, cp949, 로컬 site-packages 패치, LSP 1.63.0 lock-in |
| H. 구조 부채 | 3 | blind-to-x `main.py` 500줄+, LLM fallback 체인 7 프로바이더, dual-sqlite 잔재 |

---

## 4. 토의 사항 (Discussion)

### 🔴 A. 블로커 — 사용자 결정 필요

| 항목 | 출처 | 현황 | 블로커 이유 |
|---|---|---|---|
| **T-215** 과거 커밋 시크릿 로테이션/리라이트 | `.ai/TASKS.md:9` | 브레이브 API키, NotebookLM 세션이 git history에 잔존. `.secrets.baseline`은 현재만 커버 | 리포 public 전환 시 노출. history rewrite는 파괴적 작업 — 사용자 결정 필수 |
| **T-199** main 브랜치 보호 설정 | `.ai/TASKS.md:10`, `.ai/HANDOFF.md:63` | HTTP 403: "Upgrade to GitHub Pro or make this repository public" | 계정 플랜 업그레이드 or public 전환 결정 필요 |
| **blind-to-x express_draft:270** LLM fallback 미구현 | 코드 스캔 | 전 프로바이더 실패 시 `RuntimeError` raise, graceful degradation 없음 | Surge 파이프라인 단일점 장애 |
| **blind-to-x escalation_runner:115, :169** | 코드 스캔 | `content_preview` 비어있는 채로 파이프라인 진입 + Telegram 승인 버튼 미구현 | Phase 2 기능 반쪽 상태 |

### 🟠 B. Silent Failure 13건 — 감사 경로 소실

가장 심각한 패턴: `except Exception: pass` without logging.

| 위치 | 잃는 정보 |
|---|---|
| `pipeline/content_intelligence/classifiers.py:38` | 감정 분류 실패 → fallback keywords로 넘어감 |
| `pipeline/content_intelligence/rules.py:120, :197` | KST 시간 계산 + 월별 시즈널 규칙 실패 소실 |
| `pipeline/content_intelligence/scoring_6d.py:59` | 6D 알고리즘 freshness score 실패 소실 |
| `pipeline/analytics_tracker.py:113` | timezone 버그 |
| `pipeline/cost_tracker.py:56` (3회) | 프로바이더 cost 실패 누적 |
| `pipeline/cost_db.py:96` | 손상된 cost 레코드 |
| `config.py:55` | Windows 인증서 경로 resolve 실패 |

**영향**: 프로덕션에서 이상 동작해도 로그에 아무것도 안 남음. 재현 불가.

### 🟠 C. 하드코딩된 localhost URI 4건

| 위치 | URI |
|---|---|
| `pipeline/draft_providers.py:84` | `localhost:11434` (Ollama) |
| `pipeline/db_backend.py:63` | `redis://localhost:6379/0` |
| `pipeline/observability.py:42` | `http://localhost:4317` (OTEL) |
| `pipeline/task_queue.py:124` | `redis://localhost:6379/0` 중복 |

**영향**: 컨테이너/클라우드 배포 시 전부 끊김. env override 패턴 없음.

### 🟡 D. 협업/워크플로우 부채 (이번 세션 실측)

이번 세션에서 **실제로 겪은** 문제들:

1. **package.json 스필오버 문제**: Gemini의 T-193 `@google/generative-ai` dep 추가가 워크트리에 uncommitted 상태로 머무름. 내 test 스크립트 수정을 분리하기 위해 save→reset→re-edit→commit→restore 5단계 댄스 필수
2. **병렬 커밋 흡수**: Gemini가 내 워크트리 수정을 자신의 `[ai-context]` 커밋으로 흡수 (`8743179`, `98cec1e`). 내 의도한 커밋 메시지가 사라짐
3. **Pre-commit hook 마찰**: 의도한 파일 외에 `mixed-line-ending`이 archive 파일을, `detect-secrets`가 baseline을 수정해서 commit 3번 연속 실패
4. **`__qc_negative_probe.js` 픽스처 오염**: Gemini가 src/components/에 음성 probe를 두어서 일반 스캔이 깨짐. 양쪽 스캐너에 `__*` prefix 제외 추가 필요
5. **파서 regex 5차 패치**: 세미콜론 강요, destructuring 미지원, `__` prefix, dynamic import, Python dedup — 하루에 5번 fix. 근본 원인: **regex 기반 파싱의 한계**

### 🟡 E. 테스트 인프라 부채

| 항목 | 상세 |
|---|---|
| `tests/unit/test_multi_platform.py:241` | `@pytest.mark.skip` — naver_blog dead feature flag |
| `tests/unit/test_phase3.py:68` | `pytest.skip` — KOTE 모델 선택적이나 테스트는 필수 가정 |
| T-120 (auto-memory) | `test_auto_schedule_paths.py` fastapi dev 의존성만, CI에서 ModuleNotFoundError |
| T-121 (auto-memory) | `test_main.py` KeyboardInterrupt — Windows Python 3.14 `logging.shutdown()` 충돌 의심 |
| Python/Node smoke scanner asymmetry | 이번 세션에 4회 정렬 필요 (커버리지, `__` 제외, dynamic import, dedup) |

### 🔵 F. 환경 부채

| 항목 | 워크어라운드 | 재발 위험 |
|---|---|---|
| `code-review-graph` Python 3.13 site-packages UTF-8 패치 | 로컬 사본만 | 재설치 시 조용히 소실 |
| Amazon Q LSP 1.64.0 크래시 → 1.63.0 lock-in | `state.vscdb` 편집 | Antigravity 업데이트 시 manifest overwrite 재발 가능 |
| Korean 경로에서 Python/SQLite 실패 | `C:\Temp\pjh` junction | 스크립트별로 반복 조치 필요 |
| Windows cp949 콘솔 | `PYTHONUTF8=1` 개별 설정 | 새 터미널 세션마다 |

### 🟢 G. 구조 부채

- **blind-to-x `main.py`** (T-217): 500+줄 모놀리스. runner/CLI/bootstrap 분리 제안됨 (승인 대기)
- **LLM fallback 체인**: 7 프로바이더 (Groq/Moonshot/DeepSeek/OpenAI/Anthropic/Together/...). 관리 비용 高. 실측: Google Gemini 403 중
- **dual sqlite DB 잔재**: workspace DB로 통합 완료(2026-04-04)됐으나 btx_cost 별도 유지

---

## 5. 우선순위 합의 (Priority Matrix)

| 우선순위 | 카테고리 | 이유 |
|---|---|---|
| **P0 (이번 주)** | Silent failure 로깅 주입 | 관찰 불가 상태 → 어떤 이슈도 재현 불가. 최소 위험, 최대 가치 |
| **P0** | localhost 하드코딩 env override | 컨테이너 배포 불가. 4곳 복붙 제거 + `BTX_*_URL` env var 도입 |
| **P1 (2주 내)** | 파서 AST 이관 or pre-commit fixture isolation | regex 기반 반복 패치 종식. `typescript` 컴파일러 API or `@babel/parser` |
| **P1** | Python/Node smoke scanner 단일화 | 비대칭 제거 → 한 곳만 유지. 이번 세션에 4회 정렬 발생 |
| **P1** | 병렬 AI 세션 파일 경쟁 방지 | `.ai/` lockfile 도입 or sequential 전환 정책 |
| **P2 (3주 내)** | T-217 `main.py` 분해 | 승인 블록, 사용자 결정 후 진행 |
| **P2** | 테스트 스킵 청소 | 5건 스킵 제거 (feature flag 삭제 or 조건부 로드) |
| **P3 (결정 대기)** | **T-215 시크릿 리라이트** | 사용자 결정: history rewrite vs public 연기 |
| **P3** | **T-199 GitHub 계정 플랜** | 사용자 결정: Pro 업그레이드 vs public |
| **P4 (장기)** | LLM fallback 체인 감축 | 7→3 프로바이더. 실제 사용 패턴 계측 후 축소 |

---

## 6. 진행 방안 (Action Plan)

### Phase 1 — 관찰 가능성 복구 (1주)

**목표**: Silent failure 13건을 로깅으로 교체. 프로덕션 이슈 재현성 확보.

**방법**:
1. 신규 유틸 `projects/blind-to-x/pipeline/_debt_log.py` 생성
   ```python
   logger = logging.getLogger("btx.silent_fallback")
   def log_silent_fallback(component: str, exc: Exception, *, fallback: str):
       logger.warning("silent-fallback %s: %s → %s", component, type(exc).__name__, fallback)
   ```
2. 13곳의 `except Exception: pass`를 `except Exception as exc: log_silent_fallback(...)`로 교체
3. `workspace/execution/health_check.py`에 silent fallback 카운터 집계 추가

**위험**: 낮음. 행동 변경 없이 로깅만 추가.
**승인 필요**: 아니오 (🟢 safe, 같은 모듈 경계, 13 파일 내 touch)

### Phase 2 — localhost env override (1주)

**목표**: 4건 하드코딩 → env var 기반 설정.

**방법**:
1. `BTX_OLLAMA_URL`, `BTX_REDIS_URL`, `BTX_OTEL_ENDPOINT` env var 정의
2. `config.py`에 기본값 포함 `resolve_service_url(name: str, fallback: str)` 헬퍼 추가
3. 4곳 하드코딩 → 헬퍼 경유로 전환
4. `.env.example` 업데이트

**위험**: 낮음. 기본값 유지로 기존 동작 호환.
**승인 필요**: 아니오 (새 env var = 기본값 있으면 🟢 safe)

### Phase 3 — smoke test 인프라 개선 (2주)

**목표**: Python/Node 스캐너 이중화 해소. 파서 AST 기반 이관 평가.

**방법**:
1. **옵션 A (빠른 정리)**: Python 스캐너 사용 중단 공지 → Node만 유지. Node가 named export까지 더 엄격 검증
2. **옵션 B (근본 해결)**: `@babel/parser` 도입 → regex 파서 제거. 세미콜론/destructuring/dynamic/re-export 전부 AST에서 무료
3. Fixture 관리: `src/__fixtures__/` 디렉토리 표준화 + SKIP_NAMES에 추가
4. CI에서 양쪽 스캐너 동일 결과 검증하는 meta-test 추가 (옵션 A 선택 시 삭제)

**위험**: 중간. AST 이관은 새 의존성(`@babel/parser`)이라 🔴 approval.
**승인 필요**: **예** — 옵션 B 진행 시 `@babel/parser` 추가 승인 필요

### Phase 4 — 협업 워크플로우 가드레일 (1주, 병렬)

**목표**: 병렬 AI 세션의 파일 경쟁 최소화.

**방법**:
1. `.ai/LOCKS/` 디렉토리 + 간단한 파일 lock 컨벤션 (세션 시작 시 `touch .ai/LOCKS/<tool>.lock`, 종료 시 삭제)
2. `HANDOFF.md`, `TASKS.md`, `SESSION_LOG.md` 편집 전 lock 파일 확인 → 경고 출력
3. `execution/ai_context_guard.py`가 이미 `[ai-context]` 스필오버 방지 중 → 영역 확대 검토
4. 기록용 문서화: "동시 편집 시 나중 시작 세션이 양보한다" 규칙 명문화

**위험**: 낮음. 컨벤션 + 스크립트, 강제력 없음.
**승인 필요**: 아니오 (🟢 safe)

### Phase 5 — 승인 대기 항목 일괄 결정 요청

사용자 결정이 필요한 **4개 블로커**:

1. **T-215** 과거 커밋 시크릿
   - 옵션 α: `git filter-repo`로 history rewrite (파괴적, 공동 작업자 재클론 필요)
   - 옵션 β: 리포 public 전환 연기, 현상 유지
   - 옵션 γ: 새 리포로 truncated history 마이그레이션

2. **T-199** GitHub branch protection
   - 옵션 α: GitHub Pro 업그레이드 ($4/월)
   - 옵션 β: 리포 public 전환 (T-215와 충돌)
   - 옵션 γ: self-hosted GitLab or Gitea 이전

3. **T-217** blind-to-x `main.py` 분해 — Owner는 Any AI, 사용자 GO 사인만 필요

4. **blind-to-x 피처 미완성 3건** — Phase 2 작업 재개 여부

---

## 7. 개선안 (Proposals)

### 제안 1: `debt_log.py` 유틸 도입 (Phase 1 선행)

```python
# projects/blind-to-x/pipeline/_debt_log.py
"""
Silent failure → observable degradation.
기존 `except Exception: pass` 패턴 일괄 교체용.
"""
from __future__ import annotations
import logging

_logger = logging.getLogger("btx.silent_fallback")

def swallowed(component: str, exc: BaseException, *, fallback: str = "", action: str = "") -> None:
    """Log a swallowed exception without re-raising."""
    _logger.warning(
        "silent-fallback component=%s err=%s fallback=%s action=%s",
        component, type(exc).__name__, fallback, action,
        extra={"exc_info": exc},
    )
```

13곳 교체 예시:
```python
# Before
try:
    return datetime.now(tz=ZoneInfo("Asia/Seoul")).hour
except Exception:
    pass
return 12

# After
try:
    return datetime.now(tz=ZoneInfo("Asia/Seoul")).hour
except Exception as exc:
    swallowed("rules.kst_hour", exc, fallback="12")
return 12
```

### 제안 2: service URL 헬퍼 (Phase 2)

```python
# projects/blind-to-x/config.py (추가)
import os

_SERVICE_URL_DEFAULTS = {
    "ollama": "http://localhost:11434",
    "redis":  "redis://localhost:6379/0",
    "otel":   "http://localhost:4317",
}

def resolve_service_url(name: str) -> str:
    env_key = f"BTX_{name.upper()}_URL"
    return os.environ.get(env_key) or _SERVICE_URL_DEFAULTS[name]
```

### 제안 3: smoke test AST 이관 (Phase 3, 옵션 B)

현재 정규식 기반 파서는 5차례 패치 이력:
- v1: 세미콜론 강요 버그 (30건 false positive)
- v2: destructuring export 미지원
- v3: `__` prefix 필터 추가
- v4: dynamic import 감지 추가
- v5: Python dedup

→ **`@babel/parser`** 도입 시 전부 무료. 비용: ~3MB 의존성, 테스트 실행시간 +200ms 추정.

### 제안 4: AI 세션 lock 컨벤션 (Phase 4)

```bash
# 세션 시작
mkdir -p .ai/LOCKS && echo "$$" > .ai/LOCKS/$TOOL_NAME.lock
trap 'rm -f .ai/LOCKS/$TOOL_NAME.lock' EXIT

# 편집 전 충돌 확인
for lock in .ai/LOCKS/*.lock; do
  [ "$lock" = ".ai/LOCKS/$TOOL_NAME.lock" ] && continue
  echo "WARN: concurrent session: $lock"
done
```

강제력 없음 — 순수 컨벤션. pre-commit hook으로 경고만 표출.

---

## 8. 다음 회의 의제

- [ ] Phase 1 진척도 (silent failure 13 → 0)
- [ ] 블로커 4건 중 사용자 결정 결과
- [ ] AST 이관 옵션 B GO/NO-GO
- [ ] 2026-04-15 ~ 2026-04-22 사이 신규 발견 debt 추가

---

## 9. 회의 결론 요약

**즉시 착수 (승인 불필요)**:
1. Phase 1 — silent failure 로깅 (13 파일)
2. Phase 2 — localhost env override (4 파일 + config.py)
3. Phase 4 — `.ai/LOCKS/` 컨벤션 (문서 + 스크립트)

**사용자 결정 대기**:
1. T-215 시크릿 리라이트 방식
2. T-199 GitHub 계정 플랜
3. T-217 `main.py` 분해 GO
4. Phase 3 옵션 B (`@babel/parser` 의존성 추가)

**장기 과제**:
- LLM fallback 체인 감축 (7→3)
- `code-review-graph` upstream 패치 제출
- Korean path junction 표준화

---

*이 문서는 다음 회의에서 업데이트되어야 합니다. 블로커 해제 순서대로 섹션 4의 체크박스를 업데이트하세요.*
