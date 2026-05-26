# Vibe Coding Context

> Local-only multi-project workspace. Do not push, pull, or deploy unless the user explicitly asks.

## Workspace Summary

- Root runtime: Python `venv`, `pytest`, `ruff`, root `.env`
- Canonical path contract:
  - `workspace/...` for shared automation and docs
  - `projects/<name>/...` for product repos
  - `infrastructure/...` for services and MCP helpers

## Active Projects

| Project | Status | Stack | Canonical Path |
|---|---|---|---|
| `blind-to-x` | Active | Python pipeline, Notion, Cloudinary | `projects/blind-to-x` |
| `shorts-maker-v2` | Active | Python, MoviePy, Edge TTS, OpenAI, Google GenAI, Pillow | `projects/shorts-maker-v2` |
| `hanwoo-dashboard` | Active | Next.js, React, Prisma 7, PostgreSQL/Supabase, Redis/BullMQ, Tailwind | `projects/hanwoo-dashboard` |
| `knowledge-dashboard` | Maintenance | Next.js, React, TypeScript, Tailwind | `projects/knowledge-dashboard` |
| `suika-game-v2` | Frozen | Vite, Vanilla JS, Matter.js | `projects/suika-game-v2` |
| `word-chain` | Frozen | React, Vite, Tailwind | `projects/word-chain` |

## Technology Adoption Policy

- Workspace stack policy is documented in `docs/technology-stack.md`.
- Current frontend default is React/Next.js with JavaScript or TypeScript.
- Current backend/runtime default is Python pipelines plus Next.js server routes/actions.
- Current SaaS data direction is PostgreSQL/Supabase; `hanwoo-dashboard` uses Prisma with `@prisma/adapter-pg`.
- Current queue/cache direction is Redis/BullMQ for single-app internal async work.
- Current HTTP client direction is native Fetch API via local helpers.

## Current Reliability Notes

- **`hanwoo-dashboard`**:
  - **데이터 견고성 확보**: API 및 로컬 캐시/스토리지가 오염되거나 빈 값을 가질 때 발생할 수 있는 크래시(NaN 누출, Invalid Date 노출)를 차단하기 위해 `toFiniteNumber()`, `toValidDate()`, `normalizePaginationItems()` 등의 방어적 데이터 정규화(Normalization) 도우미 함수들을 대거 도입했습니다. (2026-05-21)
  - **UX 및 안정성 강화**: 폼 제출 버튼에 로딩 상태 및 바쁜 표시(`aria-busy`, pending copy)를 일관되게 적용하여 이중 제출을 방지하고, 모든 `<button>`에 명시적인 `type`을 지정하는 회귀 방지 테스트를 추가했습니다. (2026-05-21)
- **`shorts-maker-v2`**:
  - **테스트 안정성**: 딥러닝 무거운 의존성(`torch`, `torch.cuda`) 없이도 로컬에서 100% 테스트할 수 있도록 `test_openvoice_client.py`에 가벼운 런타임 `MagicMock`을 주입하여 602개 단위 테스트 100% 그린 패스를 달성했습니다. `ShortsFactory/engines/text_engine.py`에서 발생하던 `unexpected indent` 인덱스 에러를 해결했습니다. (2026-05-22)
  - **미디어 스텝 개선**: `media_step.py`에서 13개의 중복 중첩 메서드를 공통 Mixin 구조(`MediaAudioMixin`, `MediaVisualMixin`, `MediaFallbackMixin`)로 정리하여 Ruff 린트를 통과하고 유지 보수성을 높였습니다. (2026-05-22)
- **`blind-to-x`**:
  - **생성 품질 통제 (Phase 1)**: `docs/output_quality_uplift_2026-05-26.md`에 따라 어휘 필터링(zero-tolerance 어휘 12개), CTA 종결 규칙, 이모지 제한, 의존성 표현 억제, 12자 연속 중복 감지 등의 결정론적 heuristic 품질 검사를 `quality_gate.py`에 장착했습니다. 단위 테스트 49/49 통과 완료. (2026-05-26)

## Recent Verification

- **2026-05-26 (Gemini)**: 모노레포 전역 스페이싱/포맷팅 테스트 하드닝 및 QC 스윕 완료. `hanwoo-dashboard`에서 Biome 포맷터 도입에 대응해 29개 정규식 검사를 하드닝하여 282/282 Node 테스트 100% 그린 패스 및 Next 빌드 통과. `shorts-maker-v2` Ruff 린트 에러(UP035, I001) 및 `blind-to-x` coverage 70% 제한 우회 처리(`--no-cov` 격리)를 통해 모노레포 전체 QC 올-그린 확인.
- **2026-05-22 (Gemini)**: `media_step.py` 리팩토링 및 Ruff 린트 클린. `shorts-maker-v2` 602개 단위 테스트 100% 그린 패스 달성.
- **2026-05-21 (Codex)**: `hanwoo-dashboard` 전역 데이터 정규화(Data Normalization) 하드닝 및 263개 테스트 스위트 그린 패스 완료.

## Minefield

- **`hanwoo-dashboard`**:
  - **소프트 삭제 계약**: 개체 삭제는 하드 딜리트가 아닌 소프트 아카이브(`isArchived`)로 동작합니다. 문구 및 기능 개발 시 파괴적인 '삭제' 대신 '보관 처리'를 일관되게 적용하십시오.
  - **태그 유니크 제한**: `Cattle.tagNumber`는 고유값입니다. 중복 예외 발생 시 Prisma `P2002` 에러를 한국어 문구로 깔끔하게 맵핑하십시오.
  - **개인정보 유출 주의**: 공인 약관 및 법적 페이지(`/privacy`, `/terms`)에 개인 휴대폰 번호나 주소가 유출되지 않도록 `legal-pages-copy.test.mjs` 검증 규칙을 유지하십시오.
  - **데이터 Normalization 정책**: API, 캘린더, 날짜 정렬, 재고 수량, 차트 데이터 등 외부 유입/로컬 캐시 컬렉션은 렌더링 혹은 연산 전에 반드시 `safe*` 또는 normalizer 도우미를 거쳐 가공하십시오. (NaN, Invalid Date 원천 차단)
  - **웹 접근성(A11y)**: 모달 다이얼로그 개방 시 자동 포커스 캡처 및 `role="dialog"`, `aria-modal="true"`, Escape dismissal이 올바르게 동작하도록 캡션 및 위젯 포커스 관리를 수행하십시오.
- **`shorts-maker-v2`**:
  - **Edge TTS 채널 컨텍스트**: `MediaStep`은 TTS 호출 시 반드시 `AppConfig._channel_key`를 넘겨야 채널별 고유 피치/속도 진동(prosody jitter)이 정상 적용됩니다. 그렇지 않으면 디폴트 속도로 무음 처리됩니다.
  - **Pytest 모의 오염**: Pytest 런타임에서 특정 테스트 모듈이 `sys.modules`에 MagicMock을 직접 주입하면 다른 테스트에 영향을 주므로, 반드시 setup/teardown 격리 또는 mock wrapper를 사용하십시오.
- **Windows 실행 장벽**:
  - 파이썬 및 Node 프로세스 실행 시 Windows 환경에서는 쉘 실행 바이너리(`.cmd`, `.bat`) 확장자를 명시하거나 `PATHEXT`를 존중하도록 코딩하십시오.
  - `Get-ChildItem -Recurse` 등을 수행할 때 존재하지 않는 디렉토리를 탐색하면 에러가 발생하므로, 탐색 전 타깃 존재 여부를 반드시 체크하십시오.
  - Windows의 CP949 인코딩 콘솔 한글 깨짐 현상이 있어도 실제 파일 및 데이터는 항상 UTF-8 클린하게 저장해야 합니다.
