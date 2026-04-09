# blind-to-x 프로젝트 지침

> 이 파일은 `projects/blind-to-x/` 작업 시 자동 로드됩니다.
> 전역 지침 (`../../CLAUDE.md`)과 함께 적용됩니다.
>
> | 도구 | 자동 로드 | 조치 |
> |------|----------|------|
> | Claude Code | ✅ 자동 | 없음 |
> | Gemini (Antigravity) | ❌ 수동 | 세션 시작 시 이 파일 먼저 읽기 |
> | Codex | ❌ 수동 | 세션 시작 시 이 파일 먼저 읽기 |

## 프로젝트 개요

- **목적**: Blind (앱) → X(Twitter), Threads, Naver Blog 자동 콘텐츠 변환 파이프라인
- **스택**: Python 3.11+, Notion API, Cloudinary, OpenAI GPT-4o
- **핵심 파일**: `pipeline/`, `escalation_runner.py`, `main.py`

## 검증 커맨드

```bash
# 빠른 단위 테스트 (현재 작업 파일 중심)
python -m pytest --no-cov tests/unit/test_<current>.py -x

# 전체 단위 테스트
python -m pytest --no-cov tests/unit/ -x

# Lint
ruff check . --fix

# E2E 테스트 (주의: 실제 Notion API 호출 발생 가능)
python -m pytest tests/test_escalation_e2e.py -x --no-cov
```

> ⚠️ 모든 커맨드는 `projects/blind-to-x/` 에서 실행할 것.

## 코드 컨벤션

- **import 스타일**: 절대 경로 (`from pipeline.xxx import yyy`)
- **비동기**: `asyncio` 기반, `async/await` 패턴
- **타입**: 모든 함수에 타입 힌트 필수
- **에러 처리**: `{"error": "..."}` dict 반환 (ADR-009)
- **Notion API**: `notion_client` 라이브러리 사용 (직접 requests 금지)

## 지뢰밭 (Minefield)

- **Notion 커서 무한 루프**: `daily_digest.py`에 커서 가드 있음. 커서 없이 페이지네이션 하지 말 것
- **escalation runner 폴링**: `escalation_runner.py`에 breaker/backoff 있음. sleep 직접 삽입 금지
- **Cloudinary URL**: 변환 파라미터는 URL 생성 함수 통해서만
- **coverage 기본값**: `pytest --no-cov` 없이 실행하면 전체 커버리지 측정으로 느려짐
- **PerformancePromptAdapter**: `pipeline/performance_prompt_adapter.py` - XAnalytics 연동, 의존성 주의

## Explore 시 반드시 읽을 파일

신규 기능 추가 전:

1. `pipeline/` 디렉터리 구조 파악
2. `tests/unit/conftest.py` — mock 설정 패턴 확인
3. `.ai/DECISIONS.md` — ADR-015~019 확인 (아카이빙된 draft contract, review_only bypass 등)

## 컴팩션 보존 컨텍스트

이 프로젝트 관련 컴팩션 발생 시 추가로 보존:

- `PerformancePromptAdapter` 연동 상태
- 현재 작업 중인 pipeline 단계
- 마지막으로 통과한 테스트 파일 목록
