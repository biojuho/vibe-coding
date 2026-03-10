# Blind-to-X 프로젝트 컨텍스트

## 프로젝트 개요
Blind-to-X는 직장인 커뮤니티(Blind, FMKorea, JobPlanet 등)에서 인기 게시물을 수집하여 X(Twitter), Threads, 네이버 블로그용 콘텐츠를 자동 생성하는 파이프라인입니다.

## 기술 스택
- **언어**: Python 3.14
- **스크래핑**: Playwright + playwright-stealth 2.0.2
- **LLM**: Gemini (주), DeepSeek/xAI/Moonshot/ZhipuAI/OpenAI/Anthropic (Fallback)
- **이미지 생성**: Gemini → Pollinations → DALL-E (Fallback 체인)
- **데이터 저장**: Notion API (37개 속성)
- **설정**: config.yaml + classification_rules.yaml

## 디렉토리 구조
```
blind-to-x/
├── scrapers/          # 스크래퍼 (base, blind, fmkorea, jobplanet, ppomppu)
├── pipeline/          # 핵심 파이프라인 모듈
│   ├── process.py     # 메인 프로세싱
│   ├── draft_generator.py  # LLM 초안 생성
│   ├── image_generator.py  # 이미지 생성
│   ├── image_ab_tester.py  # A/B 테스트
│   ├── ab_feedback_loop.py # A/B 피드백 루프
│   ├── notion_upload.py    # Notion 업로드
│   └── ...
├── tests_unit/        # 유닛 테스트 (238개)
├── tests/             # 스크래치/통합 테스트
├── docs/              # 운영 문서
├── scripts/           # 유틸리티 스크립트
├── config.yaml        # 메인 설정
└── classification_rules.yaml  # 토픽/감정/톤 규칙
```

## 현재 진행 상황
- ✅ P0~P6 파이프라인 완성 (스크래핑 → 분류 → 초안 → 이미지 → Notion 업로드)
- ✅ 멀티 플랫폼 지원 (X, Threads, 네이버 블로그, 뉴스레터)
- ✅ playwright-stealth context-level 마이그레이션 (2026-03-09)
- ✅ A/B 테스트 수동 위너 선택 UI (2026-03-09)
- ✅ 운영 SOP 매뉴얼 작성 (2026-03-09)
- ✅ 유닛 테스트 238개 통과

## 지뢰밭 (주의사항)
1. **playwright-stealth**: context 레벨에서만 적용. page 레벨 stealth 호출 추가 금지.
2. **notion-client 버그**: v2.2.1의 `databases.query`가 404 반환. httpx 직접 호출로 우회 중.
3. **Python 3.14 + Pydantic V1**: anthropic 패키지에서 호환 경고 발생 (기능 영향 없음).
4. **config.yaml 속성 동기화**: Notion 속성 추가 시 `config.yaml`과 `test_notion_accuracy.py`의 `build_default_config()` 동시 업데이트 필요.
5. **scratch 파일**: `tests/scratch_*.py`는 pytest 수집 대상이 아님. 수동 실행 전용.
