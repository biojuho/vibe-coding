# 📋 세션 로그 (SESSION LOG)

> 각 AI 도구가 작업할 때마다 아래 형식으로 기록합니다.
> 최신 세션이 파일 상단에 위치합니다 (역순).

---

## 2026-03-06 — Claude Code (Opus 4.6)

### 작업 요약
blind-to-x 품질 최적화 + 비용 최적화 4-Phase 고도화

### 변경한 파일
| 파일 | 변경 내용 |
|------|-----------|
| `blind-to-x/pipeline/draft_generator.py` | DraftCache 연동 (SHA256 캐시키), provider 스킵 (circuit breaker), 성공 시 circuit close, 비복구 에러 시 failure 기록, 차등 타임아웃 (유료 45s/무료 30s), Anthropic 모델 haiku로 다운그레이드 |
| `blind-to-x/pipeline/image_generator.py` | ImageCache 연동 (topic+emotion), 프롬프트 품질 검증 (5단어 미만 스킵), Gemini 실패 시 Pollinations 자동 폴백 |
| `blind-to-x/pipeline/content_intelligence.py` | publishability 기본점수 35→25 하향, 토픽 감지 가중 8→15, 직장인 관련성 12→18, 컨텍스트 길이 차등, LLM viral boost 보더라인(50-70점)에서만 실행 + 최대 10점 캡, performance 무데이터 50→45 |
| `blind-to-x/pipeline/cost_tracker.py` | Anthropic 가격 haiku 기준 ($0.80/$4.00), 포스트당 평균 비용 요약에 추가 |
| `blind-to-x/pipeline/cost_db.py` | `get_cost_per_post()` 메서드 추가 (30일 평균 비용/포스트) |
| `blind-to-x/pipeline/process.py` | 드래프트 품질 검증 (트윗 길이, 뉴스레터 최소 단어수) |
| `blind-to-x/main.py` | dry-run 시 이미지 생성 스킵 |
| `blind-to-x/config.example.yaml` | anthropic 모델 haiku, 가격 업데이트, image/ranking 새 설정 추가 |
| `blind-to-x/config.ci.yaml` | config.example.yaml과 동기화 |
| `blind-to-x/tests_unit/conftest.py` | `_DRAFT_CACHE` 참조 제거 → DraftCache/provider_failures 초기화 |
| `blind-to-x/tests_unit/test_cost_controls.py` | cache hit 테스트 수정 (call_count 2→1) |
| `blind-to-x/tests_unit/test_optimizations.py` | DraftCache import 수정, DALL-E 플래그 테스트 수정, call_count 4→2 |
| `blind-to-x/tests_unit/test_draft_generator_multi_provider.py` | fallback 테스트 call_count 2→1, bridge 테스트 지원 provider로 변경 |
| `blind-to-x/tests_unit/test_scrapers.py` | ImageGenerator 테스트 프롬프트 5단어 이상으로 변경 |

### 핵심 결정사항
- Anthropic 모델 `claude-sonnet-4` → `claude-haiku-4-5` (비용 4-5x 절감)
- DraftCache (SQLite 72h TTL) + ImageCache (SQLite 48h TTL) 파이프라인 연동
- LLM viral boost: 전수 → 보더라인(50-70점)만 + 최대 10점 캡
- publishability 기본점수 하향 (35→25): 저품질 컨텐츠 더 엄격히 필터링
- provider circuit breaker: 비복구 에러 시 자동 스킵 등록 + 성공 시 해제

### 미완료 TODO
- 없음

### 다음 도구에게 전달할 메모
- 전체 105개 테스트 통과
- config.yaml에 새 키 추가됨: `ranking.llm_viral_boost`, `image.provider`, `image.min_prompt_words`
- `_DRAFT_CACHE` 모듈 레벨 딕셔너리는 완전 제거됨 → SQLite DraftCache로 대체

---

## 2026-03-06 14:13 KST — Gemini/Antigravity

### 작업 요약
AI 도구 공유 컨텍스트 시스템 초기 세팅

### 변경한 파일
| 파일 | 변경 내용 |
|------|-----------|
| `.ai/CONTEXT.md` | 🆕 생성 — 프로젝트 분석 결과 기반 마스터 컨텍스트 |
| `.ai/SESSION_LOG.md` | 🆕 생성 — 세션 로그 템플릿 (이 파일) |
| `.ai/DECISIONS.md` | 🆕 생성 — 아키텍처 결정 기록 |

### 핵심 결정사항
- `.ai/` 폴더를 프로젝트 루트에 생성하여 모든 AI 도구가 공유하는 컨텍스트 허브로 사용
- 세션 로그는 역순(최신 상단) 기록 방식 채택

### 미완료 TODO
- 없음

### 다음 도구에게 전달할 메모
- 작업 시작 전 반드시 이 3개 파일(`CONTEXT.md`, `SESSION_LOG.md`, `DECISIONS.md`)을 먼저 읽을 것
- `DECISIONS.md`의 결정사항은 임의 변경 금지
- 세션 종료 시 반드시 이 파일에 작업 기록 추가할 것

---

<!--
## 세션 기록 템플릿 (복사해서 사용)

## YYYY-MM-DD HH:MM KST — [도구명]

### 작업 요약
(한 줄로 작성)

### 변경한 파일
| 파일 | 변경 내용 |
|------|-----------|
| `파일경로` | 변경 설명 |

### 핵심 결정사항
- (결정 내용)

### 미완료 TODO
- (미완료 항목 또는 "없음")

### 다음 도구에게 전달할 메모
- (인수인계 사항)
-->
