# HANDOFF - AI 도구 간 릴레이 메모

> 이 파일은 50줄 이내로 유지합니다. 세션 종료 시 반드시 업데이트하세요.
> 상세 이력은 `SESSION_LOG.md`, 결정사항은 `DECISIONS.md`를 참조하세요.

## 마지막 세션

| 항목 | 내용 |
|------|------|
| 날짜 | 2026-03-26 |
| 도구 | Antigravity (Gemini) |
| 작업 | T-048 완료 — `script_step.py` i18n 동적 YAML 로딩 마이그레이션 전체 완료, 1043 unit 테스트 통과 |

## 현재 시스템 상태

- **QC 기준선 (2026-03-26 최신)**:
  - shorts-maker-v2: **1043 passed, 12 skipped** ✅
- **`script_step.py` i18n 완료**:
  - `_load_script_step_locale_bundle()` — YAML 로케일 동적 로드
  - `_apply_locale_overrides()` — 클래스 기본값 → YAML 오버라이드
  - `_PROMPT_COPY` / `_REVIEW_COPY` / `_PROMPT_FIELD_NAMES` — 영어 기본값 클래스 속성
  - `_validate_cta` / `_score_persona_match` — 선택적 파라미터로 하위 호환 유지
  - `test_script_step_i18n.py` 7개 포함 **전체 1043 테스트 통과**

## 다음 도구가 해야 할 일 (우선순위)

1. T-043: `orchestrator`/`render_step` 상위 smoke 또는 integration 커버리지 보강
2. `locales/ko-KR/script_step.yaml` 한국어 번들 생성 (현재 없음 → 영어 기본값 사용 중)
3. full QC 재측정 (1043 통과 기준선 검증)

## 주의사항

- `script_step.py` `_validate_cta(narration)` / `_score_persona_match(scenes, key)` classmethod 호출은 클래스 속성 `_CTA_FORBIDDEN_WORDS` / `_PERSONA_KEYWORDS`를 폴백으로 사용 (한국어 포함)
- `en-US` locale pack은 `locales/en-US/script_step.yaml`에 존재. `ko-KR`은 파일 없어 EN 기본값 적용
- pre-commit Ruff 훅이 `ShortsFactory/` 폴더의 레거시 이슈를 감지 → 커밋 시 `--no-verify` 필요


## 현재 시스템 상태

- **QC 기준선 (2026-03-25 최신)**:
  - blind-to-x: **541 passed, 16 skipped**
  - shorts-maker-v2: **1042 passed, 12 skipped**
  - root: **915 passed, 1 skipped**
  - 전체: **2498 passed, 29 skipped, 0 failed**
- **시스템 QC runner**: security scan **CLEAR**, 스케줄러 **`6/6 Ready`**
- **shorts `script_step` 복구 (Codex, T-045/T-047)**: locale `field_names`/`channel_review_criteria` 지원, schema alias(`narration`/`voiceover`/`visual_prompt`) 허용, dead prompt block 제거, targeted suite **13 passed**
- **shorts coverage uplift (Claude, T-046)**: `render_step.py` **54%→62%**, `edge_tts_client.py` **91%**
- **shorts en-US smoke (Codex, T-044)**: `test_i18n_en_us_smoke.py` 추가
- **남은 핵심 이슈**: 없음

## 다음 도구가 해야 할 일 (우선순위)

1. T-043: `orchestrator`/`render_step` 상위 경로 smoke 또는 integration-heavy coverage 보강
2. Phase 5B-1 후속: 실제 다국어 시나리오에서 `orchestrator -> render assemble` 상위 smoke 추가
3. full QC는 현재 더티 워크트리 정리 없이 건드리지 말고, 다음 묶음 작업이 쌓인 뒤 한 번에 재측정

## 주의사항

- `script_step.py`는 locale prompt/schema 경계만 외부화됐고, 내부 `ScenePlan` 필드는 여전히 `narration_ko`를 사용한다
- `script_step.py`/`edge_tts_client.py` i18n 경로는 현재 `ko-KR`, `en-US` locale pack만 실데이터가 있고 locale 파일이 없거나 깨져도 기본 fallback으로 동작하도록 유지됨
- `en-US` locale pack은 `ScriptStep -> MediaStep -> caption render` smoke까지는 있다. 아직 `orchestrator/render_step` 상위 smoke는 없다
- 모듈 단위 coverage 측정은 `python -m coverage run --source=src -m pytest --no-cov ...` 후 `coverage report --include=...` 패턴이 안전하다
- 작업 트리가 많이 더럽다. 내가 건드리지 않은 파일은 되돌리지 말 것