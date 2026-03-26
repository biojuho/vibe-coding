# Vibe Coding (Joolife) 마스터 컨텍스트

> **로컬 전용 프로젝트 — 원격 push/pull/deploy 금지**
> 이 프로젝트는 로컬에서만 운영됩니다. 어떤 AI 도구도 원격 저장소에 push, pull, deploy를 실행하지 마세요.

## 프로젝트 개요

- **프로젝트명**: Vibe Coding (Joolife)
- **핵심 설명**: 데이터 사이언스 기반, 일일 브리핑, YouTube Shorts 자동화, 사이드 프로젝트를 포함하는 개인용 AI 어시스턴트 워크스페이스
- **라이선스**: MIT

---

## 기술 스택

### Root 워크스페이스
| 항목 | 기술 | 버전 |
|------|------|------|
| 언어 | Python | 3.14 |
| 테스트 | pytest | 8.x+ |
| 린트 | ruff | - |
| CI | GitHub Actions (`root-quality-gate.yml`) | - |
| 환경 관리 | venv + `.env` | - |

### 서브 프로젝트별 스택

| 프로젝트 | 등급 | 유형 | 핵심 기술 | 주요 버전 |
|----------|------|------|-----------|-----------|
| **blind-to-x** | Active | 파이프라인 | Python, Notion API, Cloudinary, YAML 설정 | Python 3.x |
| **shorts-maker-v2** | Active | CLI/파이프라인 | Python, MoviePy, Edge TTS, OpenAI, Google GenAI, Pillow | Python 3.10+, MoviePy 2.1 |
| **hanwoo-dashboard** | Active | 웹앱 | Next.js, React, Prisma, TailwindCSS, Radix UI, Recharts | Next 16, React 19, Prisma 6, TW 4 |
| **knowledge-dashboard** | Maintenance | 웹앱 | Next.js, TypeScript, React, TailwindCSS, Recharts | Next 16, React 19, TS 5, TW 4 |
| **suika-game-v2** | Frozen | 게임 | Vanilla JS, Matter.js, Vite | Matter.js 0.20, Vite 6 |
| **word-chain** | Frozen | 게임 | React, Vite, Framer Motion, TailwindCSS | React 19, Vite 7, TW 4 |

### 공유 인프라

- **MCP 서버** (10개, `.mcp.json` 통합 관리):
  - 공식: Notion, Filesystem, Brave Search, GitHub
  - 커스텀: SQLite Multi-DB, YouTube Data, Telegram, n8n Workflow, System Monitor, Cloudinary
- **알림**: Telegram Bot
- **외부 API**: OpenAI, Google Gemini, Anthropic, DeepSeek, Moonshot, Zhipu AI, xAI, Xiaomi MiMo

---

## 디렉터리 구조

```
Vibe coding/                      # Root 워크스페이스
├── .ai/                          # 전 AI 도구 공유 컨텍스트
│   ├── HANDOFF.md                # 릴레이 핸드오프 (세션 시작 시 가장 먼저 읽을 것)
│   ├── TASKS.md                  # 칸반 보드 (TODO/IN_PROGRESS/DONE)
│   ├── TOOL_MATRIX.md            # 도구별 역량 매트릭스
│   ├── CONTEXT.md                # 마스터 컨텍스트 (이 파일)
│   ├── DECISIONS.md              # 아키텍처 결정 기록
│   ├── SESSION_LOG.md            # 세션 로그 (최근 7일)
│   └── archive/                  # 로테이션된 과거 로그
├── .agents/                      # AI 에이전트 설정
│   ├── rules/                    # 프로젝트 규칙
│   ├── skills/                   # 33종 커스텀 스킬
│   └── workflows/                # 워크플로우 (/start, /end, /organize)
├── directives/                   # SOP 지침서 (28개 markdown)
│   └── personas/                 # AI 페르소나 정의
├── execution/                    # 결정론적 Python 스크립트 (39개)
│   └── pages/                    # Streamlit UI 페이지
├── scripts/                      # 유틸리티 스크립트
├── tests/                        # 루트 테스트 스위트 (37개)
├── infrastructure/               # MCP 서버, 시스템 모니터링
│
├── hanwoo-dashboard/             # 한우 대시보드 (Next.js)
│   ├── src/                      # 메인 소스
│   └── prisma/                   # DB 스키마
├── blind-to-x/                   # 블라인드 스크래핑 → Notion
│   ├── pipeline/                 # 처리 파이프라인
│   └── tests/                    # 테스트
├── shorts-maker-v2/              # YouTube Shorts 자동화
│   ├── src/shorts_maker_v2/      # 메인 패키지
│   ├── assets/                   # 미디어 자원
│   └── tests/                    # 테스트
├── knowledge-dashboard/          # 지식 대시보드 (Next.js/TS)
├── suika-game-v2/                # 수박 게임 (Matter.js)
├── word-chain/                   # 끝말잇기 게임 (React/Vite)
│
├── _archive/                     # 아카이브된 프로젝트
├── .tmp/                         # 임시 파일 (삭제 가능)
└── venv/                         # Python 가상환경
```

---

## 현재 진행 상황

> 세부 이력은 `.ai/SESSION_LOG.md`를 참조하세요.

### 완료 — 주요 마일스톤

| 시기 | 항목 |
|------|------|
| 기반 | 루트 3계층 아키텍처, MCP 10개, Skill 23개, GitHub Private Repo |
| 2026-03-11 | 시스템 고도화 v2 Phase 0~4 완료 (KPI 대시보드, YT Analytics, ROI 분석 등) |
| 2026-03-12 | MCP & Skill 확장 + QC 승인 (공식 5개 + 커스텀 5개), SQLite/Cloudinary/System Monitor |
| 2026-03-17 | shorts-maker-v2 카라오케 자막 Critical 버그 수정 + QC (382 passed) |
| 2026-03-18 | NotebookLM-py 도입 + Blind-to-X 소셜 자산 자동 연동 + Knowledge Dashboard QA/QC |
| 2026-03-20 | shorts-maker-v2 SSML 태그 누출 수정 + MiMo LLM 통합 (537 passed) |
| 2026-03-21 | Root QA gate Windows 복구 (815 passed, coverage 81%) |
| 2026-03-23 | blind-to-x main.py 모노리스 분리, shorts-maker-v2 `render_step`↔`RenderAdapter` 연동, LLM fallback/로깅 안정화 |

### 현재 진행 중
- blind-to-x: 라이브 URL 필터 검증 + Notion 검색어/비속어 unsafe 1건 정리 완료. 전체 `--review-only` 배치 스모크는 사용자 확인 대기
- 시스템 QC 최신 기준선(2026-03-25): `execution/qaqc_runner.py`가 **`APPROVED`** 상태. blind-to-x `541 passed, 16 skipped`, shorts-maker-v2 `1042 passed, 12 skipped`, root `915 passed, 1 skipped`, 총 `2498 passed, 29 skipped`
- `execution/qaqc_runner.py`는 project-local `pytest.ini`/`pyproject`의 coverage/capture `addopts`를 `-o addopts=`로 비활성화하고, root는 `tests/`와 `execution/tests/`를 분리 실행함
- `execution/qaqc_runner.py`는 Windows `schtasks` CSV를 `locale.getencoding()`으로 읽어 `-X utf8` 모드에서도 Scheduler 상태를 `6/6 Ready`로 안정 집계함
- `blind-to-x/config.py`의 `load_env()`는 `certifi` CA 번들을 ASCII-only 경로(`%PUBLIC%`/`%ProgramData%`)로 복사하고 `CURL_CA_BUNDLE`로 연결해 Windows 한글 경로 + `curl_cffi` Error 77을 우회함
- `execution/qaqc_runner.py`는 `security_scan.status`를 machine-readable enum(`CLEAR`/`WARNING`)으로 유지하고, 상세 문구는 `status_detail`로 분리함. `knowledge-dashboard/src/components/QaQcPanel.tsx`도 그 계약을 반영함
- shorts-maker-v2 coverage uplift 진행 중: `tests/unit/test_end_cards.py` 7건으로 `render/ending_card.py` 94%, `render/outro_card.py` 93%, `tests/unit/test_srt_export.py` 12건으로 `render/srt_export.py` 95% 확보
- shorts-maker-v2 coverage uplift 진행 중: `tests/unit/test_cli.py` 12건으로 `cli.py` 67%, `tests/unit/test_audio_postprocess.py` 29건으로 `render/audio_postprocess.py` 85% 확보. 관련 targeted suite는 총 `60 passed, 12 skipped`
- shorts-maker-v2 coverage uplift(2026-03-25, Codex): 신규 `tests/unit/test_render_step_phase5.py` 18건 + `tests/unit/test_edge_tts_phase5.py` 9건으로 `render_step.py` **28% → 54%**, `edge_tts_client.py` **65% → 97%** 확보. 관련 targeted suite는 총 `170 passed, 2 warnings`
- shorts-maker-v2 coverage uplift(2026-03-25, Claude): `tests/unit/test_render_step.py` 44건 추가로 `render_step.py` **54% → 62%**, `edge_tts_client.py` **91%** 유지. 전체 QC는 `2498 passed, 0 failed`
- shorts-maker-v2 i18n PoC 1차(2026-03-25, Codex): `locales/ko-KR/script_step.yaml` + locale loader로 `script_step.py`의 tone/persona/CTA 금지어/system+user prompt copy를 `project.language` 기준으로 override 가능. 관련 targeted suite는 총 `37 passed, 2 warnings`
- shorts-maker-v2 i18n PoC 2차(2026-03-25, Codex): `script_step.py` locale bundle이 `persona_keywords`/review prompt copy까지 확장되었고, `locales/ko-KR/edge_tts.yaml` + `edge_tts_client.py` locale loader로 alias voice/default voice를 언어별로 분리 가능. `MediaStep`이 `project.language`를 Edge TTS에 전달하도록 연결되었고 관련 targeted suite는 총 `86 passed, 2 warnings`
- shorts-maker-v2 i18n 실사용 경로 1차(2026-03-25, Codex): `locales/en-US/script_step.yaml`, `locales/en-US/edge_tts.yaml`, `locales/en-US/captions.yaml` 추가. `config.py`는 `captions.font_candidates` 미지정 시 locale 기본 폰트를 읽고, `whisper_aligner.py`는 locale(`en-US`)를 short code(`en`)로 정규화해 faster-whisper에 전달. 관련 targeted suite는 총 `78 passed, 2 warnings`
- shorts-maker-v2 en-US smoke(2026-03-25, Codex): 실제 `en-US` config를 로드해 `ScriptStep` locale prompt, `MediaStep`의 Edge TTS `language` 전달, `caption_pillow.render_caption_image()` fallback까지 연결되는 `test_i18n_en_us_smoke.py` 추가. 관련 smoke suite는 총 `34 passed, 2 warnings`
- shorts-maker-v2 orchestrator 상위 en-US smoke(2026-03-26, Codex): 신규 `tests/integration/test_orchestrator_i18n_smoke.py`로 실제 `ScriptStep`, 실제 `RenderStep.run()`, stub media, mocked encode/QC를 조합해 `ScriptStep -> Orchestrator -> RenderStep -> SRT export` 경로를 검증. 같은 세션에서 `script_step.py` `_validate_script_schema()` alias 정규화와 `render_step.py`의 cp949-safe benchmark print도 함께 보강했고 관련 묶음은 총 `17 passed, 8 warnings`
- shorts-maker-v2 `script_step` 복구(2026-03-25, Codex): locale `field_names`/`channel_review_criteria` 외부화, schema alias(`narration`/`voiceover`/`visual_prompt`) 허용, dead prompt block 정리까지 마쳤고 targeted suite는 총 `13 passed, 2 warnings`
- blind-to-x의 `tests/integration/test_curl_cffi.py`는 Windows 한글 경로 환경의 known CA Error 77 재현에 가까워 system QC runner에서만 ignore 처리
- security scan 6건 triage 완료: line-level `# noqa`와 explicit triage metadata를 runner가 인식하도록 보강되어 **CLEAR**. `test_golden_render_moviepy`는 2026-03-25 full QC에서 재발하지 않았고 이후 full QC에서 관찰만 유지
- 테스트 고도화 v2 Phase 5: coverage 목표 상향과 문서 정리 진행 중

### 향후 예정
- 테스트 고도화 v2 Phase 5 (고급 최적화 + 문서)
- shorts-maker-v2: v3.0 Multi-language + SaaS 전환

### 지뢰밭 (AI 반복 실수 기록)

> AI 도구가 반복적으로 실수하는 부분을 여기에 기록합니다. 해결되었거나 재발 가능성이 낮아진 이슈는 `.ai/archive/CONTEXT_MINEFIELD_ARCHIVE.md`로 이동합니다.

| 현상 / 도구 | 내용 | 대응 방법 (도구 조치) |
|------|------|-----------------------|
| 1. Windows 인코딩 이슈 | cp949 콘솔에서 emoji/특수기호 출력 시 `UnicodeEncodeError` 발생. 2026-03-26에 `render_step.py` benchmark print도 같은 이유로 수정 | 콘솔 출력은 ASCII-safe 문자열, `_safe_console_print()`, 또는 logger 경로를 우선 사용 |
| 2. Windows 한글 경로 + `curl_cffi` | 한글/비ASCII 경로 때문에 CA 파일 인식 불가 (Error 77) | `certifi.where()`를 그대로 쓰지 말고, `%PUBLIC%` 등 ASCII 경로 복사본 + `CURL_CA_BUNDLE`을 사용 |
| 3. pytest / coverage 옵션 충돌 | `qaqc_runner.py`가 하위 디렉터리 `pytest.ini`의 `addopts`와 겹치며 수집/측정 오류 발생 | runner 실행 시 `-o addopts=`로 덮어써서 하위 coverage 통합 설정을 무시 |
| 4. 모듈 단위 coverage 측정 함정 | Python 3.14+numpy 환경에선 `--cov=module` 패턴이 import 충돌을 일으키기도 함 | 모듈 측정은 `python -m coverage run --source=src -m pytest --no-cov ...` 후 `coverage report --include=...` 사용 |
| 5. CSV + `schtasks` 인코딩 | `qaqc_runner.py`에서 `locale.getpreferredencoding(False)`가 UTF-8로 잡히면 `준비` 상태 파싱 실패 | Windows Scheduler CSV는 `locale.getencoding()`으로 명시 인코딩 |
| 6. security scan 상태 텍스트 오염 | `status`에 설명 문구를 섞으면 `CLEAR` 같은 machine-readable 판정이 깨짐 | `status`는 enum(`CLEAR`/`WARNING`/`ERROR`)만 유지하고, 부가 설명은 `status_detail`로 분리 |
| 7. 특수 환경 테스트 의존성 | 폰트/`pydub` 같은 로컬 환경 차이로 테스트가 흔들림 | `sys.modules` fake module 주입, 폰트 fallback, 환경 독립 fixture를 먼저 고려 |
| 8. 부분 i18n 리팩토링 드리프트 | `script_step.py`를 건드릴 때 locale 정의와 호출부가 반쯤만 바뀌면 `_prompt_copy`/`_review_copy`/`field_names`/`channel_review_criteria`가 어긋나기 쉬움 | `script_step.py` 수정 시 locale bundle 정의, `_apply_locale_overrides()`, prompt builder, schema validation을 한 묶음으로 검증 |
| 9. Root / Legacy 테스트 분리 | root에서 legacy가 섞이면 basename 중복과 import 충돌이 다시 생김 | Root QC는 `tests/`와 `execution/tests/`를 분리 실행하고, `legacy/`는 명시적으로 분리 관리 |

---

*마지막 업데이트: 2026-03-25 KST (Codex — T-042/T-045/T-047 완료, `script_step` locale review criteria/alias 복구, targeted suite `13 passed`)*
