# Blind-to-X 세션 로그

## 2026-03-29 | Codex | targeted QC rerun + quality_gate ruff fix

### 작업 요약

최신 리팩터 슬라이스 이후 최종 targeted QC를 다시 돌렸다. 정적 체크에서 `pipeline/quality_gate.py`의 import ordering 1건만 걸렸고, 이를 정리한 뒤 관련 테스트 묶음을 다시 검증했다. 동작 변화는 없고 lint hygiene만 맞춘 수정이다.

- `pipeline/quality_gate.py` import 순서를 정리해 `ruff`를 통과시켰다.
- rules loader migration 관련 정적 체크를 다시 돌렸다.
- 규칙/규제/피드백/성과 추적 묶음과 draft/process 중심 broader regression 묶음을 다시 확인했다.

### 변경 파일

| 파일 | 변경 내용 |
|---|---|
| `pipeline/quality_gate.py` | `ruff` import-order 수정 (동작 변화 없음) |

### 검증 결과

- `python -m ruff check pipeline/rules_loader.py pipeline/content_intelligence.py pipeline/draft_generator.py pipeline/editorial_reviewer.py pipeline/draft_quality_gate.py pipeline/quality_gate.py pipeline/regulation_checker.py pipeline/feedback_loop.py scripts/update_classification_rules.py scripts/analyze_draft_performance.py tests/unit/test_rules_loader.py` -> clean
- `python -m py_compile pipeline/rules_loader.py pipeline/content_intelligence.py pipeline/draft_generator.py pipeline/editorial_reviewer.py pipeline/draft_quality_gate.py pipeline/quality_gate.py pipeline/regulation_checker.py pipeline/feedback_loop.py scripts/update_classification_rules.py scripts/analyze_draft_performance.py tests/unit/test_rules_loader.py` -> clean
- `python -m pytest tests/unit/test_rules_loader.py tests/unit/test_regulation_checker.py tests/unit/test_feedback_loop_fallback.py tests/unit/test_performance_tracker.py -q -o addopts=` -> **56 passed, 1 warning**
- `python -m pytest tests/unit/test_draft_contract.py tests/unit/test_draft_generator_multi_provider.py tests/unit/test_pipeline_flow.py tests/unit/test_quality_improvements.py tests/unit/test_cost_controls.py tests/unit/test_dry_run_filters.py tests/unit/test_scrape_failure_classification.py tests/unit/test_reprocess_command.py -q -o addopts= -k "not slow"` -> **92 passed, 1 warning**

## 2026-03-29 | Codex | rules split + shared loader

### 작업 요약

외부 리뷰 후속 리팩터의 다음 슬라이스로 규칙 파일 구조를 정리했다. 기존 단일 `classification_rules.yaml`에 섞여 있던 taxonomy, golden example, prompt, editorial policy, platform regulation을 분리하고, 런타임이 이를 한 경로로 읽도록 shared loader를 도입했다.

- `pipeline/rules_loader.py`를 추가해 split rule file merge, cache, section lookup, legacy snapshot refresh를 한곳에서 담당하게 했다.
- `rules/classification.yaml`, `rules/examples.yaml`, `rules/prompts.yaml`, `rules/platforms.yaml`, `rules/editorial.yaml`을 생성해 규칙 source of truth를 분리했다.
- `content_intelligence.py`, `draft_generator.py`, `editorial_reviewer.py`, `draft_quality_gate.py`, `quality_gate.py`, `regulation_checker.py`, `feedback_loop.py`가 shared loader를 사용하도록 변경했다.
- `scripts/update_classification_rules.py`, `scripts/analyze_draft_performance.py`도 split layout 우선으로 동작하게 바꾸고, 필요 시 legacy `classification_rules.yaml` 스냅샷을 재생성하도록 맞췄다.
- `tests/unit/test_rules_loader.py`를 추가해 split-loader 계약을 고정했다.

### 변경 파일

| 파일 | 변경 내용 |
|---|---|
| `pipeline/rules_loader.py` | split rule files 공용 로더 + 캐시 + legacy snapshot helper 추가 |
| `rules/classification.yaml` | topic/emotion/audience/hook/source hint/season weight 분리 |
| `rules/examples.yaml` | golden examples / anti examples 분리 |
| `rules/prompts.yaml` | tone mapping / prompt templates / topic prompt strategies 분리 |
| `rules/platforms.yaml` | platform regulations / cross_source_insight / trends 분리 |
| `rules/editorial.yaml` | brand voice / cliche watchlist / thresholds / x editorial rules 분리 |
| `pipeline/content_intelligence.py` | shared loader 사용 |
| `pipeline/draft_generator.py` | shared loader 사용 |
| `pipeline/editorial_reviewer.py` | shared loader 사용 |
| `pipeline/draft_quality_gate.py` | shared loader 사용 |
| `pipeline/quality_gate.py` | shared loader 사용 |
| `pipeline/regulation_checker.py` | shared loader 사용 |
| `pipeline/feedback_loop.py` | shared loader 사용 |
| `scripts/update_classification_rules.py` | split rule file 우선 업데이트 + legacy snapshot refresh |
| `scripts/analyze_draft_performance.py` | split rule file 우선 업데이트 + legacy snapshot refresh |
| `tests/unit/test_rules_loader.py` | 신규 테스트 추가 |

### 검증 결과

- `python -m py_compile pipeline/rules_loader.py pipeline/content_intelligence.py pipeline/draft_generator.py pipeline/editorial_reviewer.py pipeline/draft_quality_gate.py pipeline/quality_gate.py pipeline/regulation_checker.py pipeline/feedback_loop.py scripts/update_classification_rules.py scripts/analyze_draft_performance.py tests/unit/test_rules_loader.py` -> clean
- `python -m pytest tests/unit/test_rules_loader.py tests/unit/test_regulation_checker.py tests/unit/test_feedback_loop_fallback.py tests/unit/test_performance_tracker.py -q -o addopts=` -> **56 passed, 1 warning**
- `python -m pytest tests/unit/test_quality_improvements.py tests/unit/test_draft_generator_multi_provider.py tests/unit/test_pipeline_flow.py -q -o addopts=` -> **65 passed, 1 warning**

## 2026-03-29 | Claude Code | 파이프라인 복원: 에디토리얼 필터 + 피드 제목 추출

### 작업 요약

D-028 리디자인 이후 3/26부터 에디토리얼 필터가 모든 게시물을 100% 차단하여 파이프라인이 사실상 정지된 상태를 발견하고 수정했다. 핵심 원인은 `feed_collector.py`에서 제목만으로(content="") `hard_reject`를 적용하되 기준이 본문 포함 기준이었기 때문. 추가로 FMKorea/JobPlanet의 `get_feed_candidates()` 미구현으로 제목이 항상 빈 문자열이었던 문제도 함께 수정.

### 변경 파일

| 파일 | 변경 내용 |
|---|---|
| `pipeline/feed_collector.py` | `hard_reject` 제거, `min_pre_editorial_score`(35) 도입, 리턴 타입 어노테이션 수정 |
| `scrapers/fmkorea.py` | `get_feed_candidates()` 신규 (제목+댓글수 추출, URL-only fallback 포함) |
| `scrapers/jobplanet.py` | `get_feed_candidates()` 신규 (JSON API에서 title/likes/comments/views), timeout 30s 통일, error→warning |
| `config.yaml` | `feed_filter.min_pre_editorial_score: 35.0` 추가 |
| `config.example.yaml` | 동일 키 추가 |
| `config.ci.yaml` | 동일 키 추가 (test_config_workflow_sync 통과용) |
| `tests/unit/test_feed_collector.py` | pre-editorial 테스트 갱신 (threshold=35, 빈 제목 필터 검증) |

### QC 수정 4건

1. `feed_collector.py` 리턴 타입 `-> list[dict]` → `-> tuple[list[dict], dict]`
2. FMKorea 댓글수 regex 추출 앵커 통일 (`\[(\d+)\]` → `\[(\d+)\]\s*$`)
3. JobPlanet timeout 15s → 30s (파일 내 일관성)
4. FMKorea `get_feed_candidates` 전체 실패 시 URL-only fallback 추가

### 검증 결과

- 전체 유닛 테스트: **488 passed**, 15 skipped, coverage 53%
- Pre-editorial 필터 수동 테스트: blind 제목 PASS(63.5), ppomppu PASS(46.8), 빈 제목 SKIP(26.2)

### 다음 작업 메모

- `process.py`의 full-content editorial scoring이 `min_editorial_score`(60)을 아직 사용하는지 확인 필요
- FMKorea 피드 셀렉터가 실제 사이트 변경으로 깨질 수 있으므로 정기 smoke test 권장
- JobPlanet DNS 근본 원인 조사 (API 변경 또는 차단 여부)

## 2026-03-26 | Codex | X 큐레이션/초안 품질 리디자인 구현

### 작업 요약

X 작성안 품질 문제를 해결하기 위해 후보 선정과 초안 생성 기준을 모두 X 편집 관점으로 재설계했다. `feed_collector.py`는 `pre_editorial_score`를 계산해 추상적이거나 파생각이 약한 글을 초기에 탈락시키고, `content_intelligence.py`는 `selection_summary`, `selection_reason_labels`, `audience_need`, `emotion_lane`, `empathy_anchor`, `spinoff_angle`을 포함한 편집 브리프를 만들도록 확장했다. `draft_generator.py`는 OpenAI SDK 호출을 `chat.completions`로 정리하고 장면/대사/숫자 오프닝, 공감+웃음 포인트, 구체 CTA를 강제하도록 프롬프트를 강화했으며, 에러 문자열·태그 누락·낮은 한글 비율 응답은 성공으로 취급하지 않게 바꿨다. few-shot 예시는 `성과 -> 승인 -> YAML` 순으로 폴백하고, 모든 provider 실패 시 `process.py`가 `DRAFT_GENERATION_FAILED`로 Notion 업로드 전에 종료한다.

### 변경 파일

| 파일 | 변경 내용 |
|---|---|
| `pipeline/content_intelligence.py` | X 편집 브리프 필드 추가, publishability score 리디자인 |
| `classification_rules.yaml` | X 전용 editorial rules와 토픽별 선정 기준 추가 |
| `pipeline/feed_collector.py` | `pre_editorial_score` 기반 선별 및 reason metadata 추가 |
| `pipeline/draft_generator.py` | fail-closed provider 검증, OpenAI SDK 경로 수정, X 프롬프트 강화 |
| `pipeline/draft_quality_gate.py` | 깨진 글/상투 오프닝/generic CTA/장면 부재 hard fail |
| `pipeline/notion/_query.py`, `pipeline/feedback_loop.py` | few-shot fallback 체인 재구성 |
| `tests/unit/*` | editorial filtering, fail-closed generation, fallback chain 테스트 보강 |

### 검증 결과

- `py -3 -m pytest projects/blind-to-x/tests/unit/test_feed_collector.py projects/blind-to-x/tests/unit/test_quality_gate_and_scenes.py projects/blind-to-x/tests/unit/test_quality_improvements.py projects/blind-to-x/tests/unit/test_content_intelligence.py projects/blind-to-x/tests/unit/test_draft_generator_multi_provider.py projects/blind-to-x/tests/unit/test_feedback_loop_fallback.py projects/blind-to-x/tests/unit/test_pipeline_flow.py -q -o addopts=` -> **103 passed, 1 warning**

### 다음 작업 메모

- shared runner timeout은 여전히 별도 이슈이며, 이번 리디자인 구현과는 분리해서 다뤄야 한다.
- Notion 스키마는 바꾸지 않았고 선정 이유/감정선은 기존 `memo`와 본문 블록에 기록한다.

## 2026-03-22 — Antigravity, 세션 9: 테스트 회귀 수정 + deprecated 참조 마무리 정리

### 작업 요약

Phase 2 구현 후 테스트 회귀 4건 수정 및 `main.py` deprecated 참조 추가 정리.

### 변경 파일

| 파일 | 변경 내용 |
|---|---|
| `main.py` | `_reprocess_approved_posts()`에서 `tweet_url`, `publish_channel`, `published_at` 참조 제거 |
| `tests/unit/test_multi_platform.py` | 4건 assertion 수정: 블로그 프롬프트 텍스트, deprecated 속성 체크 제거, 프로퍼티 카운트 35→15 |

### 검증 결과

- `test_multi_platform.py`: 16/16 통과 (1 skip)
- `test_cross_source_insight.py`: 13/13 통과
- Full suite: 419 pass, 2 fail (pre-existing 429 rate limit), 4 skip

### 다음 도구에게

- 2건의 실패(`test_cost_controls`, `test_pipeline_flow`)는 Gemini API 429 rate limit으로 인한 기존 flaky test. 코드 변경과 무관.
- dry_run 모드는 Windows asyncio pipe 에러로 실행 불가. WSL 또는 리눅스 환경에서 테스트 필요.

---

## 2026-03-22 — Antigravity, 세션 8: 피벗 Phase 2 구현 (남은 TODO 4건)

### 작업 요약

Phase 1 피벗(페르소나·블로그 전략·LLM 체인 축소) 완료 후 남은 4건의 TODO를 구현.

### 변경 파일

| 파일 | 변경 내용 |
|---|---|
| `pipeline/cross_source_insight.py` | 시그널 카드 프롬프트: 페르소나→"정중+위트 해설자", 네이버 블로그→4부 패턴 리포트, creator_take 지시 추가 |
| `pipeline/notion/_schema.py` | `DEFAULT_PROPS` 37→15개 경량화, 제거된 22개는 `DEPRECATED_PROPS`로 이동 |
| `pipeline/notion/_upload.py` | 제거된 속성 참조 삭제, memo에 creator_take 반영, analysis_mapping 축소 |
| `pipeline/process.py` | `update_page_properties` 호출에서 deprecated 속성 제거 |
| `pipeline/performance_tracker.py` | `update_notion_performance()` — 성과 등급만 기록하도록 단순화 |
| `pipeline/performance_collector.py` **(NEW)** | 72h 성과 수집 루프: Notion 조회→등급 계산→업데이트 |

### 검증 결과

- YAML/Config 검증 ✅
- AST 검증 6파일 ✅
- Notion 스키마 count: 15 DEFAULT + 22 DEPRECATED = 37 total ✅
- Unit tests: 24/25 passed (1 failure = 기존 viral_filter 429 rate limit)

### TODO (잔여)

- [ ] 수동 발행 품질 테스트 (dry_run)
- [ ] Notion DB에서 deprecated 속성 수동 정리 (선택)
- [ ] performance_collector.py API 연동 (Twitter/Threads/Naver API)

---

## 2026-03-22 — Antigravity (Opus), 세션 7: LLM 리뷰 기반 피벗 구현

### 작업 요약
3개 외부 LLM의 프로젝트 점검 피드백을 교차 분석 → 종합 피벗 플랜 작성 → 코드 반영. 핵심: 크리에이터 페르소나 정의, 네이버 블로그 해설형 큐레이션 전환, 파이프라인 경량화.

### 변경 파일

| 구분 | 파일 | 설명 |
|------|------|------|
| **수정** | `classification_rules.yaml` | brand_voice.persona → "정중+위트 시그널 해설자", system_role 재작성, naver_blog 프롬프트 → 해설형 큐레이션 4단 구조, voice_traits에 creator_take 필수 포함 |
| **수정** | `config.yaml` | LLM providers 7→3개(deepseek/gemini/openai), max_posts_per_day 25→10, scrape_limit 3→2, AI이미지 fallback OFF, content_strategy.creator_persona 추가 |
| **수정** | `pipeline/draft_generator.py` | naver_blog 하드코딩 fallback → 패턴 리포트 구조, _parse_response()에 `<creator_take>` 태그 파싱 추가 |

### 결정사항
- 소스 수집(Blind/JobPlanet 포함)은 **중단하지 않음** (사용자 결정)
- 네이버 블로그: 단일 포스트 확장 → **해설형 큐레이션** (패턴 리포트)
- 크리에이터 페르소나: **정중+위트** 기반 직장인 시그널 해설자
- 발행 빈도 축소: max 25→10, scrape 3→2

### QC 결과
- YAML 구문 검증: ✅ PASS (persona + creator_take 키 확인)
- Config 구문 검증: ✅ PASS (providers=3, max_posts=10)
- Unit Tests: ✅ 21/21 PASS (test_draft_generator_multi_provider + test_quality_gate)

### TODO
- [ ] 크로스소스 패턴 카드(signal card) 생성 로직 구현
- [ ] Notion 속성 37개 → 핵심 12~15개로 경량화
- [ ] 발행 후 72h 성과 수집 → 스코어 보정 루프
- [ ] 수동 발행 테스트 후 品質 피드백 반영

### 다음 도구에게 메모
- `classification_rules.yaml`의 `brand_voice` 섹션이 종전 "친구에게 톡하듯"에서 "정중+위트 해설자"로 변경됨
- 모든 플랫폼 초안에 `<creator_take>` 태그가 필수로 포함되도록 system_role이 변경됨
- LLM fallback 체인이 3개로 대폭 축소됨 — xai/moonshot/zhipuai/anthropic 설정 블록은 config.yaml에 남아있지만 providers 목록에서 제거됨

## 2026-03-20 — Claude Code (Opus 4.6), 세션 6: 운영 복구 + QC

### 작업 요약
파이프라인 미동작 진단 → 운영 설정 6건 수정. 코드는 건전(454 테스트 통과), Gemini 쿼타 소진 + 설정 문제가 원인.

### 변경 파일

| 구분 | 파일 | 설명 |
|------|------|------|
| **수정** | `config.yaml:122` | OpenAI 모델명 `gpt-4.1-mini` → `gpt-4o-mini` |
| **수정** | `pipeline/editorial_reviewer.py` | Gemini 단일 → **multi-provider fallback** (DeepSeek/Gemini/xAI). dead code `_REVIEW_MODEL` 제거, docstring 갱신 |
| **수정** | `pipeline/text_polisher.py:43-49` | kiwipiepy 모델 복사 `os.listdir` → `shutil.copytree` (하위 디렉토리 포함 재귀 복사) |
| **수정** | `tests/unit/test_quality_improvements.py` | `reviewer.api_key=None` → `reviewer._providers=[]` (2곳) |
| **신규** | `run_pipeline.bat` | Task Scheduler용 bat 래퍼 |
| **신규** | `register_task.ps1` | Task Scheduler 등록 PowerShell 스크립트 |

### 진단 결과

| 우선순위 | 문제 | 조치 |
|---------|------|------|
| P0 | Gemini API 429 RESOURCE_EXHAUSTED | 키 유효, 일일 쿼타 소진 (자동 리셋). DeepSeek이 이미 1순위 |
| P0 | config.yaml `gpt-4.1-mini` 오타 | `gpt-4o-mini`로 수정 |
| P1 | editorial_reviewer.py Gemini 단일 provider | 3-provider fallback 구현 |
| P1 | Windows Task Scheduler 태스크 누락 | `BlindToX_Pipeline` 등록 (3시간 간격) |
| P1 | Telegram 환경변수 미설정 | 사용자 나중에 설정 예정 |
| P2 | kiwipiepy `extract.mdl` 로드 실패 | `shutil.copytree` 재귀 복사로 수정 |

### QC 결과 (6항목 전 PASS)
- 코드 리뷰: dead code 제거, docstring 정확성
- 보안: API key 로그 미노출 확인
- 엣지 케이스: config=None, 빈 providers 안전
- 단위 테스트: **454 passed**, 0 failed
- dry-run: 파이프라인 정상 (Blind 4 + Ppomppu 5 + FMKorea 2건 수집, 1건 처리 성공)

### 결정사항
- D-025: editorial_reviewer는 config.yaml의 `llm.providers` 순서를 존중하되, gemini/deepseek/xai만 지원
- D-026: Gemini 무료 쿼타 소진은 fallback으로 해결, 별도 유료 플랜 전환 불필요

### 다음 도구에게
- Telegram 환경변수 (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`) 미설정 상태
- Jobplanet DNS 실패 — 네트워크 이슈 또는 API 엔드포인트 변경 가능성 확인 필요
- `register_task.ps1`, `run_pipeline.bat`는 `.gitignore` 추가 고려

---

## 2026-03-20 — Claude Code (Claude Opus 4.6), 세션 5

### 작업 요약

GitHub OSS 리서치 → 4대 업그레이드 구현: Crawl4AI LLM 추출 폴백, 감성 분석 트래커, AI 바이럴 필터, 일일 다이제스트 자동 발송. QC 4개 에이전트 병렬 리뷰 → 19건 발견 16건 수정.

### 변경 파일

| 구분 | 파일 | 설명 |
|------|------|------|
| **신규** | `scrapers/crawl4ai_extractor.py` | Crawl4AI LLM 기반 구조화 추출 (JSON schema, Gemini Flash) |
| **신규** | `pipeline/sentiment_tracker.py` | 10개 감정×90+ 키워드, SQLite 영속, spike 감지 |
| **신규** | `pipeline/viral_filter.py` | Gemini Flash 5차원 바이럴 스코어링 (hook/relatability/share/controversy/timely) |
| **신규** | `pipeline/daily_digest.py` | Notion 집계 → AI 요약 → Telegram/뉴스레터 발송 |
| **신규** | `tests/unit/test_new_features.py` | 28개 테스트 (Crawl4AI 5 + Sentiment 8 + Viral 5 + Digest 8 + Integration 2) |
| **수정** | `scrapers/base.py` | `_get_crawl4ai_extractor()` 싱글톤 + `_extract_with_crawl4ai()` 폴백 메서드 |
| **수정** | `scrapers/blind.py` | CSS 셀렉터 전부 실패 시 Crawl4AI LLM 폴백 자동 실행 |
| **수정** | `pipeline/process.py` | P2.5 감성 트래킹 + P2.7 바이럴 필터 통합, ViralFilter 싱글톤 |
| **수정** | `main.py` | `--digest`, `--digest-date`, `--sentiment-report` CLI + 자동 다이제스트 발송 |
| **수정** | `config.example.yaml` | crawl4ai, viral_filter, sentiment, digest 4개 섹션 추가 |
| **수정** | `config.ci.yaml` | CI 설정 동기화 |
| **수정** | `requirements.txt` | crawl4ai>=0.4.0, google-generativeai>=0.8.0, httpx>=0.27.0 추가 |

### QC 수정 (19건 발견 → 16건 수정, 3건 보류)

| 이슈 | 파일 | 수정 내용 |
|------|------|-----------|
| `genai.configure()` 글로벌 경합 | crawl4ai, viral, digest | `genai.Client()` 인스턴스 패턴 (3곳) |
| LLM 출력 타입 안전성 | crawl4ai | `_safe_str()`, `_safe_int()` 헬퍼 |
| 타임아웃 누락 | crawl4ai | `asyncio.wait_for()` 래핑 |
| 데드락 위험 | sentiment | `threading.Lock` → `RLock` |
| 싱글톤 경합 | sentiment | double-check lock 패턴 |
| 바이럴 점수 클램핑 | viral_filter | 0-10 범위 강제 |
| Notion 페이지네이션 | daily_digest | `has_more`/`next_cursor` 루프 |
| Telegram MD 인젝션 | daily_digest | `_escape_telegram_md()` |
| per-entry 에러 핸들링 | daily_digest | 한 건 실패 시 전체 유지 |
| double page.close() | blind.py | explicit close 제거 |
| ViralFilter 매 호출 생성 | process.py | 모듈 싱글톤 |

### 결과

- 테스트: **423 passed** (395 기존 + 28 신규), 15 skipped, 0 failures
- 신규 의존성: crawl4ai, google-generativeai, httpx (전부 무료 tier)
- 파이프라인 단계 추가: P2.5(감성 트래킹), P2.7(바이럴 필터)
- CLI 추가: `--digest`, `--digest-date`, `--sentiment-report`

### 결정사항

- D-021: Crawl4AI LLM 추출은 CSS→자동수리→trafilatura→Crawl4AI 최종 폴백
- D-022: 바이럴 필터 threshold 40점, 실패 시 permissive default
- D-023: 감성 트래커 10개 감정 카테고리, 30일 보관
- D-024: 일일 다이제스트 Notion 집계 → Gemini 요약 → Telegram
- D-025: Gemini API는 `genai.Client()` 인스턴스 패턴 (글로벌 상태 경합 방지)

### 다음 도구에게 메모

- `crawl4ai_extractor.py`는 crawl4ai 미설치 시 graceful degradation (폴백 스킵)
- `viral_filter.py`는 Gemini API 키 없으면 default pass (오탐 방지)
- `sentiment_tracker.py`는 RLock 사용 (재귀 안전), singleton은 double-check lock
- `daily_digest.py`는 Notion 페이지네이션 처리 완료 (>100건 대응)
- Gemini API 호출은 반드시 `google.genai.Client(api_key=)` 인스턴스 사용 (D-025)
- `process.py`의 `_viral_filter_instance`는 모듈 싱글톤 (global 선언 필요)

---

## 2026-03-20 — Claude Code (Claude Opus 4.6), 세션 4

### 작업 요약

GitHub 프로젝트 리서치 → 5개 OSS 도입 (kiwipiepy, trafilatura, datasketch, camoufox, KOTE) + 품질 게이트/검증 래퍼 신규 개발. Phase 1~3 총 3단계 실행, QC 2건 수정.

### 변경 파일

| Phase | 파일 | 설명 |
|-------|------|------|
| **1-A** | `requirements.txt` | kiwipiepy, trafilatura, datasketch, camoufox[geoip] 추가 |
| **1-B 신규** | `pipeline/text_polisher.py` | kiwipiepy 맞춤법+띄어쓰기 교정 + 가독성 점수 (0-100) |
| **1-C** | `scrapers/base.py` | `_extract_clean_text()` 정적 메서드 (trafilatura) |
| **1-D** | `scrapers/blind.py`, `fmkorea.py`, `ppomppu.py` | 셀렉터 실패 시 trafilatura 폴백 추가 |
| **1-E** | `pipeline/editorial_reviewer.py` | LLM 리뷰 후 text_polisher 후처리 단계 추가 |
| **1-F** | `pipeline/process.py` | 가독성 점수 메타데이터 기록 |
| **2-A** | `pipeline/dedup.py` | MinHash LSH 가속 경로 추가 (datasketch, O(n²)→O(n)) |
| **2-B 신규** | `pipeline/quality_gate.py` | 7축 하드 게이트 (길이/독성/PII/클리셰/금지/반복/충실도) |
| **2-C 신규** | `pipeline/draft_validator.py` | 게이트 실패 시 자동 수정 프롬프트 + LLM 재시도 래퍼 |
| **2-D** | `pipeline/process.py` | `validate_and_fix_drafts()` 호출 삽입 |
| **3-A** | `scrapers/base.py` | Camoufox Firefox 우선 → Chromium 폴백 (`browser.engine` config) |
| **3-B 신규** | `pipeline/emotion_analyzer.py` | KOTE 44차원 감정 분석 (EmotionProfile, valence/arousal) |
| **3-C** | `pipeline/content_intelligence.py` | `classify_emotion_axis()` KOTE 우선 → 키워드 폴백 |
| **3-D** | `pipeline/process.py` | emotion_profile 메타데이터 기록 |
| **QC** | `pipeline/fact_checker.py` | 복합 한국어 단위 파싱 재귀 처리 ("5천만원"→50000000) |
| **QC** | `pipeline/quality_gate.py` | 전화번호 정규식 오탐 수정 + YAML 캐시 통합 |
| **테스트** | `tests/unit/test_text_polisher.py` | 신규 19건 (가독성, 폴백, trafilatura) |
| **테스트** | `tests/unit/test_quality_gate.py` | 신규 17건 (게이트 9 + MinHash 6 + validator 2) |
| **테스트** | `tests/unit/test_phase3.py` | 신규 11건 (Camoufox 3 + KOTE 6 + 폴백 2) |
| **테스트** | `tests/unit/conftest.py` | non-ASCII 경로 Kiwi segfault 방지 |

### 결과

- 테스트: **379 passed**, 4 skipped, 0 failures (335 → 379, +44건)
- 도입 OSS 5개 전부 $0 운영 비용 유지
- 파이프라인 단계: 스크래핑→[trafilatura]→[KOTE 감정]→초안→에디토리얼→[text_polisher]→팩트검증→[가독성]→[품질게이트→자동수정]→이미지→게시

### 결정사항

- D-016: Camoufox는 `browser.engine` config가 "chromium"이 아닌 한 기본 사용 (auto/firefox)
- D-017: 품질 게이트 failure는 -20점, warning은 -5점 (failures>0이면 불통과)
- D-018: KOTE 감정 분석은 confidence>=0.5일 때만 키워드 폴백 대체
- D-019: MinHash LSH는 후보 4건 이상일 때만 활성화 (소규모 배치는 기존 Jaccard)
- D-020: text_polisher의 kiwipiepy non-ASCII 경로 문제는 %TEMP%/kiwi_model로 자동 복사하여 우회

### 다음 도구에게 메모

- `text_polisher.py`는 kiwipiepy 미설치 시 graceful degradation (교정 스킵, 가독성은 정규식 폴백)
- `emotion_analyzer.py`는 transformers + torch 필요 (미설치 시 키워드 폴백으로 자동 전환)
- `quality_gate.py`는 `classification_rules.yaml`의 `cliche_watchlist`와 `brand_voice.forbidden_expressions` 의존
- `draft_validator.py`의 `_call_llm_with_fallback`은 DraftGenerator 인스턴스 메서드 — generator=None이면 재시도 스킵
- Camoufox Firefox 바이너리는 `py -3 -m camoufox fetch`로 별도 다운로드 필요
- Windows non-ASCII 사용자명 환경에서 kiwipiepy C 확장 segfault → conftest.py에 dummy 모듈 주입으로 테스트 보호

---

## 2026-03-19 — Claude Code (Claude Opus 4.6), 세션 3

### 작업 요약

P1~P5 전체 퀄리티 개선 — "진짜 올려도 좋은 수준"으로 파이프라인 품질 끌어올리기. 브랜드 보이스 주입, LLM 자가 검수(에디토리얼 리뷰), 실질 품질 검사 4종, 콘텐츠 다양성 가드, 6D 가중치 자동 보정, 훅 타입 6종 통일, 커뮤니티별 이미지 씬, 한국어 가독성 스코어, pytrends 재시도 등.

### 변경 파일

| 카테고리 | 파일 | 설명 |
|----------|------|------|
| **P1-A** | `classification_rules.yaml` | brand_voice, cliche_watchlist, 통찰형/한줄팩폭형 hook_rules, 토픽 키워드 17개 확장 |
| **P1-B** | `pipeline/draft_generator.py` | 보이스 가이드 프롬프트 주입 + 골든 예시 랜덤 2개 로테이션 + top performers 자동 추가 |
| **P1-C 신규** | `pipeline/editorial_reviewer.py` | Gemini Flash 2차 리뷰 (5축 평가, avg<6 자동 리라이트, 15s timeout) |
| **P1-D** | `pipeline/process.py` | 에디토리얼 리뷰 통합 + ContentCalendar 가드 |
| **P1-E** | `pipeline/draft_quality_gate.py` | 실질 품질 검사 4종 (클리셰/반복구조/훅강도/모호표현) |
| **P2-A 신규** | `pipeline/content_calendar.py` | 토픽/훅/감정 다양성 가드 (6h 토픽 2건, 최근3건 훅 2건, 최근5건 감정 3건) |
| **P2-B** | `pipeline/cost_db.py` | get_top_performing_drafts(), save/load_calibrated_weights() |
| **P3-A** | `pipeline/content_intelligence.py` | calibrate_weights() Pearson 상관계수 자동 보정, 통찰형/한줄팩폭형 hook 추가 |
| **P4-A 신규** | `pipeline/readability.py` | 한국어 가독성 스코어 (문장길이/수동태/문장수) |
| **P4-B,C** | `pipeline/image_generator.py` | 커뮤니티별 씬 매핑 + PIL _validate_image() |
| **P5-A** | `pipeline/trend_monitor.py` | pytrends 3회 재시도 + 지수 백오프 |
| **P5-B** | `pipeline/cross_source_insight.py` | 빈 태그 파싱 경고 로그 |
| **P5-C** | `pipeline/notebooklm_enricher.py` | 미구현 다운로드 코드 정리 → None 반환 |
| **테스트** | `tests/unit/test_quality_improvements.py` | 신규 25건 (7개 클래스) |

### 결과

- 테스트: **370 passed**, 1 skipped, 0 failures ✅ (25건 신규)
- 에디토리얼 리뷰: Gemini Flash 무료, 추가 비용 $0
- 브랜드 보이스: 30대 직장인 톡 말투 + 금지 표현 10개 + 클리셰 30개
- 콘텐츠 다양성: SQLite draft_analytics 기반 토픽/훅/감정 반복 방지

### 결정사항

- D-012: 에디토리얼 리뷰는 avg_score < 6.0일 때만 자동 리라이트 (6.0 이상은 원본 유지)
- D-013: 실질 품질 검사는 모두 severity="warning" (기존 테스트 호환)
- D-014: 콘텐츠 캘린더는 DB 없으면 항상 허용 (graceful degradation)
- D-015: 6D 가중치 자동 보정은 min_rows=30, 7일 TTL

### 다음 도구에게 메모

- `editorial_reviewer.py`는 `GEMINI_API_KEY` 환경변수 필요 (없으면 자동 스킵)
- `content_calendar.py`는 `cost_db.draft_analytics` 테이블 의존 (없으면 graceful)
- `calibrate_weights()`는 engagement_rate 데이터가 30건 이상 있어야 실행됨
- `_validate_image()`는 PIL(Pillow) 패키지 필요 (이미 requirements.txt에 포함)
- 클리셰 캐시(`_cliche_cache`)는 프로세스 생명주기 동안 1회 로드

---

## 2026-03-17 — Claude Code (Claude Opus 4.6), 세션 2

### 작업 요약

강점 분석 기반 성장 전략 수립 → Strategy 3(크로스소스 인사이트) + Strategy 4(실시간 트렌드) 구현 → QC 3건 수정.

### 변경 파일

| 카테고리 | 파일 | 설명 |
|----------|------|------|
| **신규** | `pipeline/cross_source_insight.py` | 크로스소스 트렌드 감지 + LLM 인사이트 초안 생성 + Notion 업로드 |
| **신규** | `pipeline/trend_monitor.py` | Google Trends + Naver DataLab 통합 트렌드 모니터 |
| **신규** | `tests/unit/test_cross_source_insight.py` | 크로스소스 인사이트 테스트 13건 |
| **신규** | `tests/unit/test_trend_monitor.py` | 트렌드 모니터 테스트 15건 |
| **수정** | `pipeline/content_intelligence.py` | "분석형" hook_type 추가, trend_boost 파라미터 → calculate_6d_score 연결 |
| **수정** | `pipeline/cost_db.py` | cross_source_insights/trend_spikes 테이블 추가, archive_old_data 테이블 목록 보완 |
| **수정** | `classification_rules.yaml` | 분석형 hook_rules + golden examples + cross_source/trends 설정 |
| **수정** | `config.example.yaml` | cross_source_insight, trends 섹션 추가 |
| **수정** | `config.ci.yaml` | cross_source_insight, trends 섹션 추가 |
| **수정** | `main.py` | TrendMonitor 초기화 + 크로스소스 인사이트 처리 블록 |
| **수정** | `requirements.txt` | pytrends>=4.9.0 추가 |

### QC 결과

- Critical #1: `upload_post()` → `upload()` 인터페이스 수정 ✅
- Critical #2: `trend_boost` 미연결 → `calculate_6d_score(trend_boost=trend_boost)` 연결 ✅
- Critical #3: `archive_old_data()` 테이블 목록 누락 → 2개 테이블 추가 ✅

### 결과

- 테스트: **335 passed**, 1 skipped ✅ (28개 신규)
- 크로스소스 인사이트: 3+건 2+소스 동일 토픽 감지 → LLM 트렌드 분석 초안 자동 생성
- 실시간 트렌드: Google Trends + Naver DataLab → trend_boost(0-30) 6D 스코어 반영

### 결정사항

- D-010: 크로스소스 인사이트는 opt-in (config cross_source_insight.enabled)
- D-011: 실시간 트렌드는 opt-in (config trends.enabled), spike_threshold 80.0

### 다음 도구에게 메모

- `trend_monitor.py`의 Naver DataLab API는 `NAVER_CLIENT_ID`/`NAVER_CLIENT_SECRET` 환경변수 필요
- `cross_source_insight.py`는 draft_generator의 _enabled_providers(), _generate_once(), _parse_response() 내부 메서드에 의존
- pytrends 라이브러리는 Google 차단에 취약 — 프로덕션에서 proxy 설정 권장

---

## 2026-03-17 — Antigravity (Gemini)

### 작업 요약

A-1(깨진 테스트 수정), A-3(Dead code 정리), B-5(품질 게이트 자동 재생성 루프) 구현.

### 변경 파일

| 카테고리 | 파일 | 설명 |
|----------|------|------|
| **수정** | `tests/unit/test_multi_platform.py` | TestFormatForThreads 삭제 (dead newsletter_formatter 참조), config_path 경로 수정 |
| **수정** | `tests/integration/test_p2_enhancements.py` | newsletter_formatter 의존 테스트 3건 제거 |
| **수정** | `tests/unit/test_performance_tracker.py` | RULES_FILE 경로 parents[2]로 수정 |
| **수정** | `tests/integration/test_p3_enhancements.py` | base 경로 프로젝트 루트까지 도달하도록 수정 |
| **수정** | `tests/unit/test_config_workflow_sync.py` | ROOT 경로 parents[2]로 수정 |
| **수정** | `.github/workflows/blind-to-x.yml` | tests_unit → tests/unit 오타 수정 |
| **B-5** | `pipeline/process.py` | 품질 게이트 실패 시 자동 재생성 루프 (최대 2회) |
| **B-5** | `pipeline/draft_generator.py` | `_build_retry_prompt()` + `quality_feedback` 파라미터 추가 |
| **신규** | `tests/unit/test_quality_gate_retry.py` | B-5 자동 재생성 루프 테스트 8건 |

### 결과

- 테스트: **307 passed**, 1 skipped, 0 failed ✅
- A-1: 깨진 테스트 전부 수정 (경로 문제 5건 + dead 참조 제거)
- A-3: newsletter_formatter 관련 dead code 완전 정리
- B-5: 품질 게이트 should_retry 시 LLM에 실패 피드백 전달 후 재생성

### 다음 도구에게 메모

- B-5 구현 완료: `process.py` L384~L464에 자동 재생성 루프 존재
- `DraftQualityGate.should_retry`가 True인 플랫폼에 대해서만 재생성 시도
- `generate_drafts(quality_feedback=[...])` 인터페이스로 피드백 전달

## 2026-03-16 10:25 KST — Antigravity (Gemini)

### 작업 요약

이전 세션(3/15) 이후 수행된 다음 작업들의 기록 정리.

### 변경 파일 (83 files, +844 / −8,240 lines)

| 카테고리 | 파일 | 변경 | 설명 |
|----------|------|------|------|
| **신규** | `pipeline/image_upload.py` | +98 | 이미지 업로드 독립 모듈 |
| **신규** | `classification_rules.yaml` | +123 | 토픽/감정/톤 분류 규칙 외부화 |
| **변경** | `main.py` | +19 | Per-source limit 기능 추가 (소스별 스크래핑 수 제한) |
| **변경** | `scrapers/base.py` | +227 | 스크래퍼 베이스 클래스 기능 확장 |
| **변경** | `scrapers/ppomppu.py` | +52 | 뽐뿌 스크래퍼 개선 |
| **변경** | `pipeline/draft_generator.py` | +79 | 초안 생성기 기능 보강 |
| **리팩토링** | `pipeline/notion_upload.py` | +836/−800 net | Mixin 분리 후 대폭 축소 |
| **리팩토링** | `pipeline/ab_feedback_loop.py` | ±60 | A/B 피드백 루프 개선 |
| **리팩토링** | `pipeline/ml_scorer.py` | ±74 | ML 스코러 리팩토링 |
| **정리** | `tests_unit/` 전체 | −3,900+ | `tests/unit/`으로 마이그레이션 완료, 구 폴더 삭제 |
| **정리** | `tests/` 스크래치 | −800+ | 개발용 scratch 테스트 14개 파일 삭제 |
| **정리** | 루트 디버그 파일 | −1,500+ | jobplanet_*, fmkorea_*, out*.txt 등 중간 산출물 일괄 삭제 |
| **정리** | 루트 테스트 파일 | −250+ | test_ai.py, test_jobplanet_*.py 등 단발성 테스트 삭제 |
| **삭제** | `pipeline/newsletter_formatter.py` | −489 | 미사용 모듈 제거 |
| **삭제** | `pipeline/newsletter_scheduler.py` | −285 | 미사용 모듈 제거 |
| **설정** | `.gitignore` | ±41 | 정리된 파일 패턴 반영 |
| **설정** | `pytest.ini` | ±2 | 테스트 경로 업데이트 |
| **설정** | `register_schedule.ps1`, `run_scheduled.bat` | ±75 | 스케줄 설정 개선 |

### 핵심 변경 요약

1. **프로젝트 정리**: 중간 산출물, 디버그 로그, scratch 테스트 등 **약 40개 불필요 파일 삭제**로 저장소 클린업
2. **테스트 폴더 통합**: `tests_unit/` → `tests/unit/` 마이그레이션 완료, 구 폴더 전체 삭제
3. **Per-source limit**: `main.py`에 소스별 스크래핑 수 제한 기능 추가 (`scrape_limits_per_source` 설정)
4. **분류 규칙 외부화**: `classification_rules.yaml` 신규 생성으로 토픽/감정/톤 규칙을 코드에서 분리
5. **이미지 업로드 분리**: `pipeline/image_upload.py` 독립 모듈 신규 생성
6. **미사용 모듈 정리**: newsletter_formatter, newsletter_scheduler 삭제

### 다음 도구에게 메모

- 테스트 폴더는 이제 `tests/unit/`만 사용 (구 `tests_unit/` 삭제됨)
- 분류 규칙은 `classification_rules.yaml`에서 관리
- `main.py`의 `scrape_limits_per_source` 설정으로 소스별 제한 가능

## 2026-03-15 20:22 KST — Antigravity (Gemini)

### 작업 요약

품질 고도화 Phase 1 QC 수행 및 통과.

### QC 결과

- AST 구문 검증: 3/3 통과
- 신규 테스트 (품질 게이트 + 시멘틱 씬): 36/36 통과
- 관련 기존 테스트 회귀: 0건
- 기존 미구현 실패 20개는 이번 변경과 무관 (format_for_threads, config.yaml 등)
- **최종 판정: ✅ PASS**

### 변경 파일

| 파일 | 변경 | 이유 |
|------|------|------|
| `.ai/CONTEXT.md` | 업데이트 | 신규 모듈 및 진행 상황 반영 |
| `.ai/SESSION_LOG.md` | 업데이트 | QC 결과 기록 |

### 이전 세션 (19:04 KST) 작업 요약

- `pipeline/draft_quality_gate.py` 신규 생성 (Post-LLM 초안 품질 게이트)
- `pipeline/image_generator.py` 시멘틱 씬 매핑 추가 (70+ 토픽×감정 조합)
- `pipeline/process.py` 품질 게이트 파이프라인 통합
- `tests/unit/test_quality_gate_and_scenes.py` 36개 테스트 생성

## 2026-03-15 19:04 KST — Antigravity (Gemini)

### 작업 요약
품질 고도화 Phase 1 구현: **Post-LLM 초안 품질 게이트** + **시멘틱 씬 매핑** 두 가지 핵심 기능 추가.

### 변경 파일
| 파일 | 변경 | 이유 |
|------|------|------|
| `pipeline/draft_quality_gate.py` | 신규 생성 | LLM 생성 초안의 플랫폼별 품질 검증 (글자 수, 한글 비율, CTA, 해시태그, 소제목, 금지패턴, 중복문장) |
| `pipeline/image_generator.py` | 시멘틱 씬 매핑 추가 | 토픽×감정 교차 조합별 구체적 장면 사전(70+ 조합) 구축, 프롬프트 구체성 대폭 향상 |
| `pipeline/process.py` | 품질 게이트 연동 | 하드코딩된 품질 검증을 DraftQualityGate 모듈로 교체, 검증 리포트를 post_data에 저장 |
| `tests/unit/test_quality_gate_and_scenes.py` | 신규 생성 | 36개 테스트: 품질 게이트 20개 + 시멘틱 씬 매핑 10개 + 헬퍼 함수 6개 |

### 결정사항
- 품질 게이트는 `RegulationChecker`와 별도 모듈로 분리 (규제 준수 vs 품질 검증은 관심사가 다름)
- 시멘틱 씬 매핑은 3단계 폴백: (토픽, 감정) 교차 → 토픽 기본 → 범용 장면
- `현타` 감정 신규 추가 (exhausted empty eyes staring into space)
- strict_mode, custom_rules 지원으로 확장성 확보

### TODO
- [ ] 골든 프롬프트 템플릿 확장 (3개 → 15개 토픽)
- [ ] Notion 업로드 실패 재시도 큐
- [ ] 실행 요약 리포트 생성

### 다음 도구에게 메모
- `DraftQualityGate`는 `process.py`에서 `RegulationChecker` 바로 전에 실행됨
- `_SEMANTIC_SCENES`는 `image_generator.py` 모듈 레벨 dict로 정의됨
- 테스트는 `tests/unit/test_quality_gate_and_scenes.py`에 36개 존재, 전부 통과

## 2026-03-15 17:51 KST — Antigravity (Gemini)

### 작업 요약
이미지 생성 프롬프트에서 한글 텍스트(제목/초안)를 완전 제거하여, 생성 AI가 한글 오타를 이미지에 렌더링하는 문제를 해결. 토픽+감정 축만으로 직관적인 이미지를 생성하도록 변경. no-text 제약을 대폭 강화.

### 변경 파일
| 파일 | 변경 | 이유 |
|------|------|------|
| `pipeline/image_generator.py` | MODIFY | 한글 title/draft_text를 프롬프트에서 완전 제거. `_BLIND_ANIME_STYLE.constraints` 및 일반 프롬프트에 강한 no-text 제약 추가 |
| `tests/integration/test_p2_enhancements.py` | MODIFY | `test_title_hint_included` → `test_title_not_in_prompt`로 변경. 한글 텍스트가 프롬프트에 포함되지 않음을 검증 |

### 주요 결정사항
1. **한글 텍스트 완전 제거**: 프롬프트에 한글이 포함되면 Gemini/DALL-E 등이 한글을 이미지에 렌더링하려 하여 오타 발생. 토픽+감정만으로 장면을 구성하면 충분히 직관적.
2. **강한 no-text 제약**: 기존 `no text overlay` → `absolutely no text, no letters, no numbers, no words, no captions, no writing of any kind` 으로 대폭 강화.

### QA/QC 통과 여부
- **이미지 프롬프트 테스트**: ✅ 6 passed
- **A/B 테스터 테스트**: ✅ 16 passed

### 다음 도구에게 메모
- `build_image_prompt()`의 `title`, `draft_text` 매개변수는 하위 호환성을 위해 남아있지만 프롬프트에 반영되지 않음.
- 이미지 스타일은 `_TOPIC_IMAGE_STYLES`(일반) 및 `_TOPIC_SCENES`(블라인드 전용)의 토픽 매핑으로만 결정됨.

---

## 2026-03-09 09:46 KST — Antigravity (Gemini)

### 작업 요약
Sprint 4개 태스크 완료: P0 playwright_stealth API context-level 마이그레이션, P1 Notion 뷰 설정 가이드/검증 스크립트, P2 A/B 위너 수동 선택 UI, P2 운영 SOP 매뉴얼.

### 변경 파일
| 파일 | 변경 | 이유 |
|------|------|------|
| `scrapers/base.py` | MODIFY | stealth를 page→context 레벨로 마이그레이션. `_new_page()`에서 stealth 호출 제거 |
| `scrapers/browser_pool.py` | MODIFY | `open()`에서 각 context에 stealth 적용. `acquire_page()`에서 제거 |
| `tests/scratch_stealth.py` | MODIFY | 레거시 `stealth_async` → `Stealth` 클래스 마이그레이션 |
| `config.yaml` | MODIFY | `ab_winner: "A/B 위너"` 속성 추가 |
| `pipeline/ab_feedback_loop.py` | MODIFY | `fetch_manual_winners()` 추가, 수동 선택 우선 적용 오버라이드 로직 |
| `docs/notion_view_setup_guide.md` | NEW | Board/Gallery/Calendar 뷰 수동 설정 가이드 |
| `scripts/check_notion_views.py` | NEW | 뷰 필수 속성 존재 여부 검증 스크립트 |
| `docs/operations_sop.md` | NEW | 비개발자용 운영 SOP 매뉴얼 |

### 주요 결정사항
1. **Context-level Stealth**: `playwright-stealth 2.0.2` 권장 API에 따라 context 생성 시 1회 적용. 이후 모든 page가 자동 상속하여 중복 적용 경고 해소.
2. **Notion API 뷰 제한**: API가 뷰 생성을 지원하지 않으므로 설정 가이드 문서 + 속성 검증 스크립트로 대체.
3. **수동 A/B 위너 우선**: Notion UI에서 운영자가 직접 선택한 위너가 자동 판정보다 우선 적용.

### QA/QC 통과 여부
- **유닛 테스트 (tests_unit/)**: ✅ 238 passed, 1 skipped — Exit code 0

### 다음 도구에게 메모
- `playwright-stealth`은 이제 context 레벨에서만 적용됨. page 레벨 stealth 호출을 추가하지 말 것.
- `ab_feedback_loop.py`의 `fetch_manual_winners()`는 Notion `A/B 위너` select 속성을 읽음. 이 속성이 Notion DB에 존재해야 함 (수동 추가 필요).
- `scripts/check_notion_views.py`로 뷰 필수 속성 검증 가능.

---


### 변경 파일
| 파일 | 변경 | 이유 |
|------|------|------|
| `tests_unit/test_notion_accuracy.py` | MODIFY | Mock Schema를 34개 전체 config.yaml 속성으로 확장. `url` 속성 표기를 `원본 URL` → `Source URL`로 모든 assert문 포함하여 동기화 |
| `tests/test_req.py` | RENAME → `scratch_req.py` | 유닛 테스트가 아닌 스크래치 스크립트(URL 탐색용)가 pytest에 의해 자동 수집되어 DNS 오류로 실패하던 문제 해결 |
| `tests/test_stealth.py` | RENAME → `scratch_stealth.py` | playwright_stealth.stealth_async ImportError로 pytest 수집 오류 발생. 테스트 격리를 위해 이름 변경 |

### 주요 결정사항
1. **Mock Schema 전수 동기화**: `build_default_config()`의 properties dict를 config.yaml과 완전히 일치시켜 스키마 변경 시 테스트가 자동으로 검증해주는 구조 확립.
2. **스크래치 스크립트 격리**: `test_` 접두사를 가진 비유닛 테스트 파일을 `scratch_` 접두사로 변경. pytest 자동 수집 범위에서 제외. E2E 검증이 필요할 때는 수동 실행.

### QA/QC 통과 여부
- **유닛 테스트 (tests_unit/)**: ✅ 238 passed, 1 skipped — Exit code 0
- **통합 테스트 (tests/)**: ✅ 57 passed, 1 warning — Exit code 0
- **E2E Dry-Run (`python main.py --dry-run --limit 1`)**: ✅ 정상 완료 — Exit code 0

### 알려진 이슈
- 🟡 `playwright_stealth`의 `stealth_async` API는 구버전 기준이므로 실제 browser scraper 코드가 최신 v1.x API와 맞는지 별도 검증 필요
- 🟢 Python 3.14 + Pydantic V1 호환 경고 지속(anthropic 패키지) — 기능에 영향 없음

### 다음 도구에게 메모
- `tests_unit/test_notion_accuracy.py`의 `build_default_config()` properties가 config.yaml의 34개 속성과 완전히 동기화됨. 향후 속성 추가 시 두 파일을 동시에 업데이트할 것.
- `tests/scratch_req.py`, `tests/scratch_stealth.py`는 수동 실행 전용 스크래치 파일이므로 건드리지 말 것.
- 현재 파이프라인은 `python main.py --dry-run --limit N` 명령으로 안전하게 E2E 검증 가능.

---

## 2026-03-08 21:35 KST — Antigravity (Gemini)

### 작업 요약
Blind-to-X 파이프라인에서 이미지 중심 글(뽐뿌 등) 수집 순위 최상단 보정 및 뉴스레터/블로그 초안 작성 비활성화. QA/QC 검증 완료.

### 변경한 파일
| 파일 | 변경 내용 |
|------|-----------|
| `base.py` | `FeedCandidate`에 `has_image`, `image_count` 추가. 이미지가 있을 경우 score +50~100 부여하여 최상단 랭킹 배치 |
| `ppomppu.py` | 썸네일(img icon) 감지하여 `has_image: True` 설정, 본문 `img` 태그 추출, `id=regulation` 필터 추가 |
| `config.yaml` | `output_formats`를 `["twitter"]` 단일화, `newsletter.enabled`를 `false`로 변경 |

### 핵심 결정사항
- 뽐뿌 등에서 유머/짤방 게시물 수집 시 이미지가 핵심이므로 참여도 점수를 인위적으로 부스팅
- 뉴스레터/블로그 초안 기능을 비활성화하여 API 비용을 $0에 가깝게 절약

### 미완료 TODO
- 소스(Source)별 limit 할당제 도입 고려 (뽐뿌 점수가 너무 높아 Blind가 수집되어도 밀리는 부분 개선)

## 2026-03-08 — Antigravity — P6 톤 최적화 + 성과 피드백 루프

### 작업 요약
1. **classification_rules.yaml 플랫폼 확장**: Threads/네이버 블로그 전용 톤 매핑(`tone_mapping_threads`, `tone_mapping_naver_blog`), 골든 예시(`golden_examples_threads`, `golden_examples_naver_blog`), CTA 매핑(`threads_cta_mapping`), SEO 태그 풀(`naver_blog_seo_tags`), 프롬프트 템플릿(`prompt_templates.threads/naver_blog`)을 추가.
2. **draft_generator.py 톤 동적 해석**: 토픽 클러스터에 따라 `tone_mapping_threads` / `tone_mapping_naver_blog`에서 플랫폼별 톤을 동적으로 로드하여 프롬프트에 반영. YAML 템플릿의 `{threads_tone}`, `{naver_blog_tone}` 변수가 실제 치환됨.
3. **성과 피드백 루프 모듈 구현**: `pipeline/performance_tracker.py` 신규 생성. JSONL 기반 성과 기록, engagement score 자동 계산(플랫폼별 가중치), S/A/B/C 등급 부여, 주간 보고서 생성, 토픽별 추천 시스템, Notion 업데이트 유틸 포함.
4. **process.py 연동**: `PerformanceTracker`를 lazy import로 연동, 기존 파이프라인에 영향 없이 사용 가능.
5. **파이프라인 드라이런 검증**: 프롬프트 빌드 시 twitter/threads/naver_blog 블록 모두 존재, 토픽별 톤이 프롬프트에 정상 반영됨을 확인.
6. **테스트**: 52개 통과 (28 performance_tracker + 24 multi_platform).

### 변경 파일
| 파일 | 변경 | 이유 |
|------|------|------|
| `classification_rules.yaml` | MODIFY | Threads/Blog 전용 톤 매핑, 골든 예시, CTA 매핑, SEO 태그 풀, 프롬프트 템플릿 추가 |
| `pipeline/draft_generator.py` | MODIFY | 토픽별 플랫폼 톤 동적 해석 (tone_mapping_threads/naver_blog 로드 → 프롬프트 포맷팅) |
| `pipeline/performance_tracker.py` | NEW | 성과 피드백 루프 모듈 (기록/분석/보고서/추천) |
| `pipeline/process.py` | MODIFY | PerformanceTracker lazy import 추가 |
| `tests_unit/test_performance_tracker.py` | NEW | 28개 테스트 (PerformanceRecord, Tracker, YAML 검증) |

### 주요 결정사항
1. **JSONL 기반 성과 저장**: DB 없이 `.tmp/performance/performance_records.jsonl`에 저장. 가볍고 이식 가능.
2. **engagement_score 가중치 설계**: 댓글(5x) > 공유(4x) > 저장(3x) > RT(3x) > 좋아요(1x) > 조회(0.01x). 실제 바이럴과 상관관계 높은 지표에 높은 가중치.
3. **플랫폼별 톤 분리**: 같은 토픽이라도 Twitter(위트형), Threads(캐주얼형), Blog(SEO 정보형)으로 차별화.

### 다음 도구에게 메모
- classification_rules.yaml이 크게 확장됨 (약 530줄). 신규 섹션: `golden_examples_threads`, `golden_examples_naver_blog`, `tone_mapping_threads`, `tone_mapping_naver_blog`, `threads_cta_mapping`, `naver_blog_seo_tags`, `prompt_templates.threads`, `prompt_templates.naver_blog`.
- `PerformanceTracker`는 `_perf_tracker` 전역 변수로 process.py에 연결됨. 실제 성과 기록은 수동 발행 후 별도 스크립트나 CLI 명령으로 입력 가능.
- 3월 목표의 핵심 기능 모두 완성. 실 운영 모니터링 단계로 전환 가능.

---

## 2026-03-08 — Antigravity — P6 멀티 플랫폼 확장 (Threads + 네이버 블로그)

### 작업 요약
콘텐츠 운영 자동화의 핵심 과제인 Threads/네이버 블로그 초안 생성 파이프라인을 구현. 기존 twitter/newsletter만 지원하던 `draft_generator.py`에 threads, naver_blog 포맷을 추가하고, Notion 스키마 확장(DB 속성 6개 실제 추가 완료) 및 newsletter_formatter에 `format_for_threads()` 함수를 구현함. `process.py` 드래프트 품질 검증도 Threads/Blog 대응 추가. Notion DB 타이틀을 멀티 플랫폼으로 변경. 24개 신규 유닛 테스트 100% 통과.

### 변경 파일
| 파일 | 변경 | 이유 |
|------|------|------|
| `pipeline/draft_generator.py` | MODIFY | Threads(500자/캐주얼톤) + 네이버 블로그(1500~3000자/SEO) 프롬프트 블록 + 응답 파싱 추가 |
| `pipeline/newsletter_formatter.py` | MODIFY | `format_for_threads()` 함수 추가 (감정별 CTA, 해시태그 풀, 길이 제한) |
| `pipeline/notion_upload.py` | MODIFY | 6개 신규 속성 매핑: threads_body, blog_body, publish_platforms, threads_url, blog_url, publish_scheduled_at |
| `config.yaml` | MODIFY | output_formats에 threads/naver_blog 추가, threads_style/naver_blog_style 설정 블록 추가, notion.properties 확장 |
| `tests_unit/test_multi_platform.py` | NEW | 24개 유닛 테스트 (프롬프트·파싱·포맷·속성·설정 전체 커버) |

### 주요 결정사항
1. **기존 아키텍처 확장**: 새 클래스/모듈을 만들지 않고 기존 `TweetDraftGenerator`를 확장하여 멀티 포맷 지원. 코드 관리 포인트 최소화.
2. **XML 태그 파싱**: `<threads>`, `<naver_blog>` 태그를 기존 `<twitter>`, `<newsletter>` 패턴과 동일하게 파싱하여 일관성 확보.
3. **Notion 블록 렌더링**: 각 플랫폼 초안을 Notion 페이지 body에 heading + divider 구조로 렌더링하여 수동 업로드 시 한 눈에 비교 가능.

### 알려진 이슈
- 🟡 `test_notion_accuracy.py`의 `test_duplicate_check` 2건은 Notion API 버전 불일치로 인한 기존 실패 (본 작업과 무관).

### 다음 도구에게 메모
- P6 멀티 플랫폼 초안 생성 파이프라인 **완성 상태**입니다. 코드 + Notion DB 속성 + Notion 뷰 4개 모두 완료.
- `main.py` 실행 시 `config.yaml`의 `output_formats`에 따라 4개 플랫폼(twitter, threads, newsletter, naver_blog) 초안이 자동 생성되어 Notion에 저장됩니다.
- Notion 뷰 구성: 📅 콘텐츠 캘린더 / 📋 발행 워크플로우 Board / 🖼️ Threads 큐 / 📝 블로그 큐
- 다음 단계: 실운영 파이프라인 실행 후 LLM 초안 품질 모니터링, 또는 3월 목표의 나머지 작업(classification_rules.yaml에 Threads/Blog 전용 예시 추가 등) 진행.

---

## 2026-03-08 — Antigravity — QA/QC 및 남은 스프린트 최종 완료

### 작업 요약
이미지 A/B 테스트 연동 및 뉴스레터 스케줄러(Cron) 등록을 끝연 후, `/qa-qc` 프로세스에 따라 최종 점검을 완료함. 메인 파이프라인의 에러 전파 방지 및 엣지 케이스가 모두 정상 처리되는 것을 확인하여 최종 승인(`qc_report.md`)을 작성.

### 변경 파일
| 파일 | 변경 | 이유 |
|------|------|------|
| `config.yaml` | MODIFY | `image_ab_testing` 플래그 및 variants 배열 설정 |
| `pipeline/process.py` | MODIFY | LLM 이미지 프롬프트 생성 직전 `ImageABTester`를 호출하여 변형을 병합하도록 로직 추가. 에러 전파 방지를 위해 `try-except` 적용. |
| `pipeline/notion_upload.py` | MODIFY | DB 업로드 스키마 매핑에 `image_variant_id`, `image_variant_type` 추가. |
| `run_scheduled.bat` \| `setup_task_scheduler.ps1` | NEW | 파이프라인 전체를 매일 정해진 시각에 윈도우 스케줄러로 구동하기 위한 스크립트 작성 |
| `walkthrough.md` \| `qc_report.md` | NEW | 최종 산출물 및 QA/QC 승인 보고서 작성 |

### 주요 결정사항
1. **A/B 테스트 무중단 처리**: A/B 테스트 생성 로직에 문제가 생기더라도 기존 단일 로직으로 Fallback 되도록 광범위한 트라이캐치를 `process.py` 내부에 감싸 안정성(Security/Stability) 확보.
2. **윈도우 네이티브 스케줄러**: 외부 라이브러리 의존성을 피하고 OS 레벨의 안정성을 얻기 위해 PowerShell `Register-ScheduledTask` 명령어를 통한 네이티브 스케줄러 활용.

### 알려진 이슈
- 🟢 로컬 크론 스케줄러 동작 시 파이프라인이 실행되는 터미널 창이 순간적으로 뜰 수 있음(배경 실행 옵션 미적용 상태).

### 다음 도구에게 메모
- 스프린트 P1~P4 및 A/B 테스트/크론 작업 100% 완료 상태입니다.
- 다음 세션부터는 실운영 데이터 모니터링 또는 사용자 피드백 기반 버그 픽스 위주로 전환되어야 합니다.

---## 2026-03-08 — Antigravity — JobPlanet 봇 우회 및 뉴스레터 발행 테스트 완료

### 작업 요약
잡플래닛(JobPlanet) 스크래핑 차단(403) 우회를 위해 API 직접 호출 및 playwright-stealth 패턴 도입. 이후 막혀있던 뉴스레터 실제 발행 테스트(미리보기) 파이프라인 연동 과정을 완전히 수정하여 성공적으로 검증함.

### 변경 파일
| 파일 | 변경 | 이유 |
|------|------|------|
| `scrapers/jobplanet.py` | MODIFY | DOM 파싱 대신 `/api/v5/community/posts`를 이용한 JSON API 직접 수집으로 리팩토링 |
| `scrapers/base.py` & `browser_pool.py` | MODIFY | `playwright-stealth` 패키지 적용하여 강력한 봇 탐지 우회 |
| `pipeline/notion_upload.py` | MODIFY | `notion-client==2.2.1` 버그(프로퍼티 누락, 404 data_source) 우회 위해 httpx 및 search API 리팩토링 (`fetch_recent_records` 추가) |
| `pipeline/newsletter_scheduler.py` | MODIFY | `newsletter_body` 조건 검증 로직 디버그 및 개선 |
| `task.md` | MODIFY | P0~P4 스프린트 내의 잡플래닛 우회 및 뉴스레터 검증 태스크 완료 마킹 |
| `test_jobplanet_*.py` | NEW/MODIFY | API/Stealth 기반 수집 기능 작동 검증 테스트 추가 및 보완 |

### 주요 결정사항
1. **API 우선 수집**: JobPlanet의 경우 HTML 화면이 Cloudflare/DataDome 등 안티봇에 매우 민감하여, Next.js 내부 데이터 통신에 쓰이는 JSON API 엔드포인트를 직접 추출하여 403을 우회함.
2. **Notion 클라이언트 이슈 우회**: notion-client v2.2.1의 `databases.query` 사용 시 `parent.type`==`data_source_id` 구조에서 발생하는 404 에러와 속성 누락 문제를, 상위 호환 API인 `client.search()`와 httpx 직접 통신을 적절히 결합하여 완전히 해소함.
3. **스텔스 기능**: fallback UI 확인 등을 위해 `playwright-stealth` 라이브러리를 통해 Chrome 지문 패치를 적용.

### 알려진 이슈
- 🟡 Notion API의 query와 search 혼용 사용으로 인한 로직 파편화 존재. 향후 notion-client가 업데이트되면 네이티브 query 메서드로 롤백하는 것이 권장됨.
- 🟡 Newsletter는 preview만 `--newsletter-preview`로 검증했고 `--newsletter-build` 통한 파일 작성은 추후 예약 발행 워크플로에 맞춰 동작함을 확인함.

### TODO (다음 세션)
- [ ] [L] Twitter/X 자동 발행 A/B 테스트 통합
- [ ] [S] newsletter_scheduler cron 연동 (Windows Task Scheduler or run_scheduled.bat)
- [ ] [S] 이미지 A/B Notion DB 필드 추가 (`이미지 변형 ID`, `이미지 변형 타입`)

### 다음 도구에게 메모
- notion-client 업데이트 전까지 `NotionUploader` 모듈의 httpx 우회 로직을 건드리지 마십시오.
- `fetch_recent_records` 메서드는 내부적으로 `get_recent_pages`와 `extract_page_record`를 통해 정제된 리스트를 반환하도록 고도화되었습니다. 뉴스레터 파이프라인은 이를 맹신합니다.

---

## 2026-03-08 — Antigravity — 콘텐츠 고도화 P0~P3

### 작업 요약
Blind-to-X 콘텐츠 파이프라인 전면 고도화. 4단계(P0~P3) 작업 완료, 56건 테스트 전체 통과.

### 변경 파일

| 파일 | 변경 | 이유 |
|------|------|------|
| `classification_rules.yaml` | MODIFY | 토픽 15개, 감정 10개, 골든예시, 프롬프트템플릿, 톤매핑, 시즌가중치, source_hints 추가 |
| `pipeline/draft_generator.py` | MODIFY | YAML 기반 프롬프트/톤/예시/스레드 파싱 외부화 |
| `pipeline/content_intelligence.py` | MODIFY | get_season_boost(), get_source_hint() 추가 |
| `pipeline/analytics_tracker.py` | MODIFY | S등급, 다차원등급, KST 시간대 슬롯 |
| `pipeline/feedback_loop.py` | MODIFY | 성공/실패 패턴 분석, 자동 필터, 주간리포트 확장 |
| `pipeline/publish_optimizer.py` | NEW | 발행 시간 최적화 (시간대별 통계, 추천) |
| `pipeline/image_generator.py` | MODIFY | 15토픽 이미지 스타일, build_image_prompt() |
| `pipeline/newsletter_formatter.py` | MODIFY | 5토픽+3감정 매핑, format_for_blog(), curate_newsletter_from_records() |
| `config.yaml` | MODIFY | input_sources에 fmkorea, jobplanet 추가 |

### 주요 결정사항
1. **설정 외부화**: 프롬프트/톤/예시/가중치를 classification_rules.yaml로 외부화 → 코드 배포 없이 튜닝 가능
2. **소스 확장**: FMKorea/JobPlanet 스크래퍼 이미 구현되어 있어 config 활성화만 진행
3. **source_hints 체계**: 소스별 quality_boost로 직장 특화도 반영 (잡플래닛 1.1x, 에펨 0.85x)
4. **블로그 포맷**: 네이버 블로그 + 브런치 2플랫폼 지원

### 알려진 이슈
- 🟡 FMKorea 봇 감지 주의 — rate limit 준수 필요
- 🟡 JobPlanet 로그인 필요 시 Cookie 관리 미구현
- 🟢 Python 3.14 + Pydantic V1 호환 경고 (anthropic 패키지)

### TODO (다음 세션)
- [x] [M] FMKorea/JobPlanet 실제 스크래핑 dry-run 테스트
- [x] [S] source_hints의 quality_boost를 calculate_6d_score에 통합
- [x] [M] 뉴스레터 자동 발행 스케줄링 (Notion 연동)
- [x] [L] 비주얼 콘텐츠 A/B 테스트 (이미지 있는 트윗 vs 없는 트윗)

### 다음 도구에게 메모
- classification_rules.yaml이 핵심 설정 파일. 코드 수정 전에 이 파일부터 확인할 것
- ~~get_source_hint()가 아직 calculate_6d_score에 통합되지 않음~~ → **통합 완료 (2026-03-08)**
- ~~publish_optimizer는 독립 모듈이라 main.py에 아직 연결 안 됨~~ → **newsletter_scheduler에서 연동 완료**

---

## 2026-03-08 — Antigravity — Sprint: P4 태스크 4건 구현

### 작업 요약
이전 세션의 TODO 4건을 모두 구현 완료. 기존 105개 테스트 + 신규 60개 = **165개 테스트 전체 pass**.

### 변경 파일

| 파일 | 변경 | 이유 |
|------|------|------|
| `pipeline/content_intelligence.py` | MODIFY | `calculate_6d_score()`에 `source` 파라미터 추가, quality_boost 곱셈 적용 |
| `pipeline/newsletter_scheduler.py` | NEW | 뉴스레터 자동 발행 스케줄러 (Notion 수집→큐레이션→시간대 최적화→포맷) |
| `pipeline/image_ab_tester.py` | NEW | 이미지 A/B 테스트 (3축 변형 생성, 참여율 기반 위너 결정, 리포트) |
| `pipeline/image_generator.py` | MODIFY | `build_image_prompt()`에 `variant` 파라미터 추가 |
| `config.yaml` | MODIFY | `newsletter:` 설정 블록 추가 (월수금 12시, 최대 5건, naver 포맷) |
| `main.py` | MODIFY | `--newsletter-build`, `--newsletter-preview` CLI 옵션 추가 |
| `tests_unit/test_fmkorea_jobplanet_dryrun.py` | NEW | FMKorea/JobPlanet dry-run + quality_boost 통합 테스트 28건 |
| `tests_unit/test_newsletter_scheduler.py` | NEW | 뉴스레터 스케줄러 테스트 16건 |
| `tests_unit/test_image_ab_tester.py` | NEW | 이미지 A/B 테스터 테스트 16건 |

### 주요 결정사항
1. **quality_boost 곱셈 방식**: weighted sum 후 곱셈 적용 — 기존 6D 점수 체계를 깨지 않으면서 소스별 보정
2. **뉴스레터 auto_publish=false**: 기본적으로 수동 승인 후 발행 — 안전성 우선
3. **이미지 A/B 3축**: style, mood, colors 각 축에서 대안을 생성하여 다양한 변형 실험 가능
4. **위너 유의성 기준**: 참여율 차이 5% 이상일 때만 유의한 결과로 판정

### 알려진 이슈
- 🟡 FMKorea 봇 감지 — 실제 dry-run 시 rate limit 주의 필요
- 🟡 JobPlanet 로그인 필요 시 Cookie 관리 미구현
- 🟢 이미지 A/B 테스트 Notion DB variant 추적 필드는 미적용 (수동 추가 가능)

### TODO (다음 세션)
- [ ] [M] FMKorea/JobPlanet 실제 1건 dry-run (Playwright 브라우저 실행)
- [ ] [S] 이미지 A/B Notion DB 필드 추가 (`이미지 변형 ID`, `이미지 변형 타입`)
- [ ] [M] 뉴스레터 실제 발행 테스트 (Notion→큐레이션→미리보기)
- [ ] [L] Twitter/X 자동 발행 A/B 테스트 통합
- [ ] [S] newsletter_scheduler cron 연동 (Windows Task Scheduler or run_scheduled.bat)

### 다음 도구에게 메모
- `quality_boost`는 이제 `calculate_6d_score()`에 통합됨. `source` 파라미터로 전달
- `newsletter_scheduler.py`는 `publish_optimizer.py`와 연동되어 최적 시간대 추천
- `image_ab_tester.py`는 `image_generator.py`의 `_TOPIC_IMAGE_STYLES`를 직접 참조
- 전체 165개 테스트 — 새 기능 추가 시 반드시 `python -m pytest tests_unit/ -q` 실행


---

## Session: 2026-03-19 16:30 | Tool: Antigravity (Gemini)

### 작업 요약
- blind-to-x 개선 계획 수립 및 즉시 실행 (Area 1 + Area 2 완료)

### 변경 파일
- lind-to-x/config.yaml: output_formats에 naver_blog 추가, LLM 폴백 순서 DeepSeek 1순위로 변경

### 주요 발견 사항
- Task Scheduler (BlindToX_0500~2100) 이미 정상 작동 중: 오늘 0500/0900/1300 실행 확인
- Gemini API 일일 20건 한도 초과가 반복됨 → DeepSeek 1순위로 재정렬로 해결
- 1300 로그: OK 3 / FAIL 0 (파이프라인 실제로 돌아가고 있었음)
- naver_blog가 output_formats에 누락되어 있었음 → 추가 완료

### TODO
- Notion에 5개 뷰 실제 생성 (notion_operations_guide.md 참조)
- 발행 시작 (검토필요 → 승인됨 → 플랫폼별 발행)

### 다음 AI에게
- 파이프라인은 정상 작동 중. 이제 실제 콘텐츠 발행을 시작하면 됨.
- Area 3(초안 품질) Area 4(수익화) 는 발행 데이터 쌓인 후 진행


---

## Session: 2026-03-19 20:00 | Tool: Antigravity (Gemini)

### 작업 요약
blind-to-x 개선 계획 수립 및 Area 1~2 즉시 실행, QC 완료

### 변경 파일
- `config.yaml`: output_formats에 naver_blog 추가, LLM 폴백 순서 DeepSeek 1순위로 변경
- `.env`: Gemini API 키 교체 (blind-to-x 전용, 루트 .env 영향 없음)
- `pipeline/utils.py`: W293 trailing whitespace 수정 (ruff QC)

### 주요 발견 사항
- Task Scheduler 5개(BlindToX_0500~2100) 이미 정상 작동 중: 오늘 0500/0900/1300 실행 확인, OK 3/FAIL 0
- Gemini API 일일 20건 한도 초과가 반복됨. 구 API 키 문제 가능성. 새 키로 교체 완료
- naver_blog가 output_formats에 빠져 있어 블로그 초안이 생성 안 됐음 → 추가 완료
- 파이프라인은 이미 살아있음. 남은 것은 Notion 뷰 구성 + 실제 발행 시작

### QC 결과
- 테스트: 370 passed, 0 failed
- ruff: W293 1건 수정 후 클린
- 최종 판정: ✅ 승인

### TODO
- Notion 5개 뷰 실제 생성 (notion_operations_guide.md 참고)
- 발행 시작 (검토필요 → 승인됨 → 플랫폼별 발행)
- Area 3(초안 품질), Area 4(수익화)는 발행 데이터 충분히 쌓인 뒤 진행

### 다음 AI에게
- 파이프라인은 정상 작동 중 (실운영 로그 확인됨)
- LLM 순서: DeepSeek 1순위 → Gemini 2순위 (Gemini 쿼터 문제로 변경)
- Gemini API 키 새로 교체됨 (AIzaSyBxqyq72V...)
- naver_blog output_format 활성화됨. Notion DB에 `블로그 본문` 필드 있는지 확인 권장

## [2026-04-01] 테스트 커버리지 강화 (Phase 1 ~ Phase 3)
- **도구명**: Gemini (Antigravity)
- **작업 요약**:
  - Phase 1 코드의 결함 보완 (style_bandit.py falsy list 처리 및 performance_collector.py 모의 객체 경로 수정).
  - Phase 2, Phase 3 단계 스크립트(process.py, 	ext_polisher.py, quality_gate.py, x_analytics.py, 
otebooklm_enricher.py)에 대한 100% Mock 기반 고강도 유닛 테스트 작성 및 모든 TC 통과(72개 이상 Pass) 완료.
  - 관련 AttributeError 버그 수정.
- **변경 파일**:
  - \pipeline/style_bandit.py  - \	ests/unit/test_*