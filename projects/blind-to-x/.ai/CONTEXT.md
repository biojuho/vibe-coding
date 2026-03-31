# Blind-to-X 프로젝트 컨텍스트

## 프로젝트 개요
Blind-to-X는 직장인 커뮤니티(Blind, FMKorea, JobPlanet 등)에서 인기 게시물을 수집하여 X(Twitter), Threads, 네이버 블로그용 콘텐츠를 자동 생성하는 파이프라인입니다.

## 기술 스택
- **언어**: Python 3.14
- **스크래핑**: Playwright + playwright-stealth 2.0.2
- **LLM**: Gemini (주), DeepSeek/xAI/Moonshot/ZhipuAI/OpenAI/Anthropic (Fallback)
- **이미지 생성**: Gemini → Pollinations → DALL-E (Fallback 체인)
- **데이터 저장**: Notion API (37개 속성)
- **설정**: config.yaml + rules/*.yaml + classification_rules.yaml(compat snapshot) + pipeline/rules_loader.py

## 디렉토리 구조
```
projects/blind-to-x/
├── scrapers/          # 스크래퍼 (base, blind, fmkorea, jobplanet, ppomppu)
├── pipeline/          # 핵심 파이프라인 모듈
│   ├── process.py     # 메인 프로세싱
│   ├── draft_generator.py  # LLM 초안 생성
│   ├── image_generator.py  # 이미지 생성 (시멘틱 씬 매핑 70+ 조합)
│   ├── draft_quality_gate.py # Post-LLM 초안 품질 게이트
│   ├── image_upload.py     # 이미지 업로드 (Cloudinary)
│   ├── image_ab_tester.py  # A/B 테스트
│   ├── ab_feedback_loop.py # A/B 피드백 루프
│   ├── notion_upload.py    # Notion 업로드 (Mixin 분리)
│   ├── cross_source_insight.py  # 크로스소스 트렌드 감지 + 인사이트 생성
│   ├── trend_monitor.py    # Google Trends + Naver DataLab 모니터
│   └── ...
├── tests/unit/        # 유닛 테스트
├── tests/integration/ # 통합 테스트
├── docs/              # 운영 문서
├── scripts/           # 유틸리티 스크립트
├── rules/             # 규칙 소스 오브 트루스 (classification/examples/prompts/platforms/editorial)
├── config.yaml        # 메인 설정
└── classification_rules.yaml  # 레거시 호환 스냅샷/폴백
```

## 현재 진행 상황
- ✅ P0~P6 파이프라인 완성 (스크래핑 → 분류 → 초안 → 이미지 → Notion 업로드)
- ✅ 멀티 플랫폼 지원 (X, Threads, 네이버 블로그, 뉴스레터)
- ✅ playwright-stealth context-level 마이그레이션 (2026-03-09)
- ✅ A/B 테스트 수동 위너 선택 UI (2026-03-09)
- ✅ 운영 SOP 매뉴얼 작성 (2026-03-09)
- ✅ 품질 고도화 Phase 1: Post-LLM 품질 게이트 + 시멘틱 씬 매핑 (2026-03-15)
- ✅ 프로젝트 정리: tests_unit→tests/unit 마이그레이션, 불필요 파일·모듈 삭제 (2026-03-16)
- ✅ Per-source limit, classification_rules 외부화, image_upload 모듈 분리 (2026-03-16)
- ✅ A-1: 깨진 테스트 전건 수정 → 307 passed 올그린 복원 (2026-03-17)
- ✅ A-3: Dead code 정리 — newsletter_formatter 참조 완전 제거 (2026-03-17)
- ✅ B-5: 품질 게이트 불통과 → LLM 자동 재생성 루프 (최대 2회) (2026-03-17)
- ✅ 크로스소스 인사이트: 3+건 2+소스 동일 토픽 → LLM 트렌드 분석 초안 자동 생성 (2026-03-17)
- ✅ 실시간 트렌드: Google Trends + Naver DataLab → trend_boost(0-30) 6D 스코어 반영 (2026-03-17)
- ✅ **실운영 정착**: Task Scheduler 5개 정상 작동 확인 (0500~2100, 오늘 3회 실행) (2026-03-19)
- ✅ **config 개선**: naver_blog output_format 활성화, LLM 폴백 DeepSeek 1순위 변경 (2026-03-19)
- ✅ **Gemini API 키 교체**: blind-to-x 전용 키로 교체 완료 (2026-03-19)
- ✅ **OSS 5종 도입**: kiwipiepy, trafilatura, datasketch, camoufox, KOTE (2026-03-20)
- ✅ **4대 업그레이드**: Crawl4AI LLM 폴백, 감성 트래커, AI 바이럴 필터, 일일 다이제스트 (2026-03-20)
- ✅ **X 큐레이션/초안 품질 리디자인**: pre-editorial score, X 편집 브리프, fail-closed 초안 차단, few-shot 승인/YAML 폴백 구현 (2026-03-26)
- ✅ **외부 리뷰 팩 정리**: 외부 LLM 공유용 문서/체크리스트/프롬프트/zip 번들 준비 (2026-03-29)
- ✅ **드래프트 계약 정리 1차**: publishable vs auxiliary vs review_meta 분리, publishable-only quality/review flow 적용 (2026-03-29)
- ✅ **process.py stage 오케스트레이션**: `process_single_post()` staged flow + `review_only` queue-threshold override 적용 (2026-03-29)
- ✅ **규칙 분리 1차**: `rules/*.yaml` + `pipeline/rules_loader.py` 도입, 주요 runtime/script consumer 마이그레이션 (2026-03-29)
- ✅ **최종 targeted QC 재확인**: `ruff`/`py_compile` clean, rules bundle 56 pass, broader regression bundle 92 pass 확인 (2026-03-29)
- 🔲 **다음 단계**: `_process_single_post_legacy()` 제거, stage helper 파일 분리, 레거시 `classification_rules.yaml` 소비 경로 정리

## 지뢰밭 (주의사항)
1. **playwright-stealth**: context 레벨에서만 적용. page 레벨 stealth 호출 추가 금지.
2. **notion-client 버그**: v2.2.1의 `databases.query`가 404 반환. httpx 직접 호출로 우회 중.
3. **Python 3.14 + Pydantic V1**: anthropic 패키지에서 호환 경고 발생 (기능 영향 없음).
4. **config.yaml 속성 동기화**: Notion 속성 추가 시 `config.yaml`과 `test_notion_accuracy.py`의 `build_default_config()` 동시 업데이트 필요.
5. **scratch 파일**: `tests/scratch_*.py`는 pytest 수집 대상이 아님. 수동 실행 전용.
6. **tests_unit 폐기**: 구 `tests_unit/` 폴더 삭제됨. 모든 테스트는 `tests/unit/`에 위치.
7. **newsletter 모듈 삭제**: `newsletter_formatter.py`, `newsletter_scheduler.py` 제거됨. 참조 금지.
8. **B-5 재생성 루프**: `generate_drafts(quality_feedback=[...])` 인터페이스 유지. 최대 2회 재시도. `should_retry=True`(error severity)인 플랫폼만 대상.
9. **Gemini API 패턴**: `genai.configure()` 사용 금지. 반드시 `google.genai.Client(api_key=)` 인스턴스 사용 (D-025).
10. **Crawl4AI 폴백**: CSS→자동수리→trafilatura→Crawl4AI 순서. crawl4ai 미설치 시 자동 스킵.
11. **ViralFilter 싱글톤**: `process.py`의 `_viral_filter_instance`는 모듈 global. 매 호출 생성 금지.
12. **X 드래프트 fail-closed**: `draft_generator.py`는 `<twitter>`, `<reply>` 태그 누락·영문 에러문·낮은 한글 비율 응답을 성공으로 취급하지 않음. `creator_take`는 이제 선택적 review metadata.
13. **2단계 에디토리얼 필터 (D-029)**: `feed_collector.py`는 제목전용 `min_pre_editorial_score`(35)로 사전 스크리닝. `hard_reject`는 제목만으로는 신뢰할 수 없으므로 사전 단계에서 무시. 본문 포함 전체 검증(`min_editorial_score` 60)은 scrape 후 `process.py`에서 수행.
14. **FMKorea/JobPlanet get_feed_candidates (D-030)**: 4개 스크래퍼 모두 `get_feed_candidates()` 오버라이드 완료. base의 URL-only 구현은 `title=""`을 반환하므로 editorial scoring 최저점 문제 유발. FMKorea는 실패 시 URL-only fallback 포함.
15. **staged process shadowing**: `pipeline/process.py`에는 active staged `process_single_post()`와 참조용 `_process_single_post_legacy()`가 함께 있다. 수정 시 active entrypoint 또는 `_run_*_stage()` helper만 건드릴 것.
16. **규칙 소스 오브 트루스**: 편집/분류/프롬프트/플랫폼 규칙은 `rules/*.yaml`이 기준이다. 루트 `classification_rules.yaml`은 호환용 스냅샷/폴백이므로 직접 수정 시 드리프트가 날 수 있다. 가능하면 `pipeline.rules_loader`와 업데이트 스크립트를 통해 동기화할 것.
