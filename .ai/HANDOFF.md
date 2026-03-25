# HANDOFF - AI 도구 간 릴레이 핸드오프

> 이 파일은 50줄 이내로 유지합니다. 세션 종료 시 반드시 업데이트하세요.
> 상세 이력은 `SESSION_LOG.md`, 결정사항은 `DECISIONS.md`를 참조하세요.

## 마지막 세션

| 항목 | 내용 |
|------|------|
| 날짜 | 2026-03-25 |
| 도구 | Codex |
| 작업 | T-038 완료 — shorts `render_step.py`/`edge_tts_client.py` coverage uplift (`54%`/`97%`), 관련 targeted suite `170 passed` |

## 현재 시스템 상태

- **QC 기준선 (2026-03-25 최신)**:
  - blind-to-x: **541 passed, 16 skipped**
  - shorts-maker-v2: **906 passed, 12 skipped**
  - root: **915 passed, 1 skipped**
  - 전체: **2362 passed, 29 skipped, 0 failed**
- **시스템 QC runner**: security scan **CLEAR**, full suite **`APPROVED`**, 스케줄러 **`6/6 Ready`**
- **shorts coverage uplift (Codex, T-038)**: `render_step.py` **28% → 54%**, `edge_tts_client.py` **65% → 97%**, 신규 `test_render_step_phase5.py` 18건 + `test_edge_tts_phase5.py` 9건
- **shorts coverage uplift (Claude, T-030)**: `animations.py` **100%**, `broll_overlay.py` **100%**, `openai_client.py` **100%**, `google_client.py` **98%**
- **blind-to-x commands/ (Claude, T-031)**: `dry_run.py`/`one_off.py`/`reprocess.py` 전체 **100%** (신규 `test_reprocess_command.py`)
- **Phase 5 문서화 (T-033)**: `enhancement_plan_v2.md`에 Phase 5A(품질 강화)/5B(차세대) 확장 완료. i18n 분리 대상 7개 영역 명세
- **T-036 결론**: `video_renderer_backend`는 dead code가 아님 — MoviePy+FFmpeg 듀얼 렌더러, 테스트에서 사용
- **T-037 결론**: `tests/legacy/` (5파일)는 ShortsFactory 모듈 테스트, QC 범위 외 유지
- **남은 핵심 이슈**: 없음

## 다음 도구가 해야 할 일 (우선순위)

1. Phase 5A-3: `.ai/CONTEXT.md` 지뢰밭 정리 (해결된 항목 아카이브 후보 선별 + 중복 압축)
2. Phase 5B-1: i18n PoC 착수 — `locales/ko-KR/` 디렉터리 생성, `script_step.py` 프롬프트 YAML 추출
3. Phase 5A-4: shorts `render_step.py`의 integration-heavy 분기(`run`, transitions/BGM/SFX) 추가 coverage 검토

## 주의사항

- render_step.py의 커스텀 이펙트(ken_burns, 전환효과, 카라오케)는 MoviePy 전용 유지
- `shorts-maker-v2` 모듈 단위 coverage 측정 시 `--cov=shorts_maker_v2.pipeline.render_step` 또는 `coverage --source=shorts_maker_v2...`는 Python 3.14 + numpy에서 import 충돌/무수집이 날 수 있음. `python -m coverage run --source=src -m pytest --no-cov ...` 후 `coverage report --include=...` 패턴 사용
- `.githooks/pre-commit`에 `ruff format --check` 추가됨 — 커밋 전 포맷 확인 필요
- Windows cp949 콘솔 이모지 크래시 주의 — llm_router.py는 `_safe_console_print()` 우회
- `execution/qaqc_runner.py`는 Windows에서 `schtasks` CSV를 읽을 때 `locale.getpreferredencoding(False)` 대신 `locale.getencoding()`을 써야 `-X utf8` 모드에서도 `준비` 상태가 깨지지 않음
- Windows 한글 사용자 경로 + `curl_cffi` 조합은 여전히 민감하므로, CA 경로 수정 시 `certifi.where()`를 그대로 넣지 말고 ASCII-safe 번들 전략을 유지할 것
- `security_scan.status`는 기계 판정용 필드라서 `CLEAR`/`WARNING` 같은 안정 enum만 유지하고, 부가 문구는 `status_detail`에 넣어야 소비자 호환이 안 깨짐
- `execution/qaqc_runner.py`는 `-o addopts=`로 프로젝트별 coverage/capture addopts를 비활성화하고, security scan에서 line-level `# noqa`와 triage metadata 문자열을 무시함
- `shorts-maker-v2` 카드/자막 렌더 테스트는 Windows 폰트(`malgun.ttf`/`arial.ttf`/`seguiemj.ttf`)가 있어야 안정적이다. 기본 폰트만으로는 한글/이모지 렌더가 깨질 수 있음
- `shorts-maker-v2` `audio_postprocess.py` 테스트는 실제 `pydub` 설치 여부에 기대지 말고 fake `pydub` module 주입으로 커버해야 skip 없이 안정적이다
- 작업 트리에 기존 미정리 변경이 많음. 무관한 파일은 되돌리지 말 것

## 규칙

- 세션 종료 시 "마지막 세션" 테이블과 "다음 도구가 해야 할 일"을 반드시 갱신
- 50줄 초과 시 오래된 주의사항을 제거하여 유지
- 긴급 이슈는 맨 위에 `> URGENT:` 블록으로 표시
