# HANDOFF - AI 도구 간 릴레이 핸드오프

> 이 파일은 50줄 이내로 유지합니다. 세션 종료 시 반드시 업데이트하세요.
> 상세 이력은 `SESSION_LOG.md`, 결정사항은 `DECISIONS.md`를 참조하세요.

## 마지막 세션

| 항목 | 내용 |
|------|------|
| 날짜 | 2026-03-25 |
| 도구 | Codex |
| 작업 | T-044 완료 — shorts `en-US` config smoke 추가 (`ScriptStep -> MediaStep -> caption render`), 관련 targeted suite `34 passed` |

## 현재 시스템 상태

- **QC 기준선 (2026-03-25 최신)**:
  - blind-to-x: **541 passed, 16 skipped**
  - shorts-maker-v2: **906 passed, 12 skipped**
  - root: **915 passed, 1 skipped**
  - 전체: **2362 passed, 29 skipped, 0 failed**
- **시스템 QC runner**: security scan **CLEAR**, full suite **`APPROVED`**, 스케줄러 **`6/6 Ready`**
- **shorts en-US smoke (Codex, T-044)**: 실제 `en-US` config 로드 후 `ScriptStep` prompt, `MediaStep` Edge TTS language 전달, caption render fallback까지 한 번에 검증하는 `test_i18n_en_us_smoke.py` 추가
- **shorts i18n 실사용 경로 (Codex, T-041)**: `locales/en-US/`에 `script_step.yaml`, `edge_tts.yaml`, `captions.yaml` 추가. `config.py`는 `captions.font_candidates` 미지정 시 locale 기본 폰트를 읽고, `whisper_aligner.py`는 `en-US` 같은 locale을 `en`으로 정규화해 faster-whisper에 전달함
- **shorts i18n PoC 2차 (Codex, T-040)**: `script_step.py` locale bundle이 tone/persona/CTA 금지어/system+user prompt copy뿐 아니라 `persona_keywords`/review prompt copy까지 override 가능. `edge_tts_client.py`도 `locales/<lang>/edge_tts.yaml`에서 alias voice/default voice를 읽고 `MediaStep`이 `project.language`를 전달함
- **shorts i18n PoC 1차 (Codex, T-039)**: `script_step.py`가 `language` 기반 locale bundle을 읽어 tone/persona/CTA 금지어/system+user prompt copy를 override 가능, 신규 `test_script_step_i18n.py` 4건
- **shorts coverage uplift (Codex, T-038)**: `render_step.py` **28% → 54%**, `edge_tts_client.py` **65% → 97%**
- **shorts coverage uplift (Claude, T-030)**: `animations.py` **100%**, `broll_overlay.py` **100%**, `openai_client.py` **100%**, `google_client.py` **98%**
- **blind-to-x commands/ (Claude, T-031)**: `dry_run.py`/`one_off.py`/`reprocess.py` 전체 **100%**
- **남은 핵심 이슈**: 없음

## 다음 도구가 해야 할 일 (우선순위)

1. Phase 5B-1 후속: `script_step.py`의 `_CHANNEL_REVIEW_CRITERIA` extra copy와 legacy 필드명(`narration_ko`)까지 i18n 범위에 포함할지 결정
2. Phase 5A-3: `.ai/CONTEXT.md` 지뢰밭 정리 (해결된 항목 아카이브 후보 선별 + 중복 압축)
3. Phase 5A-4: shorts `render_step.py` integration-heavy 분기 coverage 추가 검토

## 주의사항

- `script_step.py`/`edge_tts_client.py` i18n 경로는 현재 `ko-KR`, `en-US` locale pack만 실데이터가 있고 locale 파일이 없거나 깨져도 기본 하드코딩 fallback으로 동작하도록 유지됨
- `en-US` locale pack은 최소 smoke까지 추가됐지만 아직 orchestrator/render_step 전체 통합 스모크는 없다. 기본 언어 전환 전에는 한 번 더 상위 경로를 확인할 것
- 새 `EdgeTTSClient.generate_tts()` 호출부를 추가할 때는 `language=self.config.project.language` 전달을 잊지 말 것. alias voice(`alloy` 등)는 언어 정보가 없으면 기본 `ko-KR` 매핑으로 떨어짐
- `whisper_aligner.py`는 locale(`ko-KR`, `en-US`)를 short code(`ko`, `en`)로 정규화해 faster-whisper에 넘긴다. 새 locale 추가 시 이 전제가 깨지지 않는지 확인할 것
- `render_step.py`의 커스텀 이펙트(ken_burns, 전환효과, 카라오케)는 MoviePy 전용 유지
- `shorts-maker-v2` 모듈 단위 coverage 측정 시 `python -m coverage run --source=src -m pytest --no-cov ...` 후 `coverage report --include=...` 패턴이 가장 안전함
- `.githooks/pre-commit`에 `ruff format --check` 추가됨 — 커밋 전 포맷 확인 필요
- Windows cp949 콘솔 이모지 크래시 주의 — llm_router.py는 `_safe_console_print()` 우회
- `execution/qaqc_runner.py`는 Windows scheduler CSV를 `locale.getencoding()`으로 읽어야 `-X utf8` 모드에서도 `준비` 상태가 안 깨짐
- Windows 한글 사용자 경로 + `curl_cffi` 조합은 여전히 민감하므로 CA 경로 수정 시 ASCII-safe 번들 전략 유지
- `security_scan.status`는 안정 enum(`CLEAR`/`WARNING`)만 유지하고 부가 문구는 `status_detail`에 넣어야 소비자 호환이 안 깨짐
- `shorts-maker-v2` 카드/자막 렌더 테스트는 Windows 폰트(`malgun.ttf`/`arial.ttf`/`seguiemj.ttf`)가 있어야 안정적
- `shorts-maker-v2` `audio_postprocess.py` 테스트는 fake `pydub` module 주입 패턴을 유지할 것
- 작업 트리에 기존 미정리 변경이 많음. 무관한 파일은 되돌리지 말 것
