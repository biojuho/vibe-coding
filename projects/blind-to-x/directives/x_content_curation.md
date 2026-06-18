# X(Twitter) 콘텐츠 큐레이션 SOP

> blind-to-x 파이프라인의 핵심 지침. 수집 → 초안 → 수동 게시 워크플로우.

## 1. 목표

외부 커뮤니티(블라인드, 뽐뿌, 에펨코리아, 잡플래닛)에서 X에 공유하기 좋은 콘텐츠를 수집하고, **편집 없이 바로 게시할 수 있는 수준**의 자연스러운 멘션(캡션)을 생성한다.

## 2. 절대 규칙

- **자동 포스팅 절대 금지** — 이 툴은 수집 + 초안까지만. 최종 게시는 반드시 사람이 한다.
- **링크는 본문에 넣지 않는다** — 답글(reply)에 분리. X 알고리즘이 외부 링크 포함 트윗을 30-50% 도달 감소시킴.
- **해시태그 1-2개 이하** — 3개 이상 시 -40% 페널티. 중간 위치 배치가 최적.
- **멘션은 편집 없이 사용 가능한 수준** — AI스러운 표현, 상투적 오프닝/클로징 완전 배제.

## 3. X 알고리즘 핵심 규칙 (2025-2026)

### 3.1 참여 신호 가중치
| 신호 | 가중치 (Like=1x) | 전략 |
|------|------------------|------|
| 답글 + 저자 응답 | 150x | 답글이 달릴 만한 구체적 디테일(숫자·장면) 제공 → 직접 응답 (CTA 질문 없이) |
| 인용 RT | 25x | 인용하기 좋은 느낌점 펀치라인 |
| RT | 20x | 공유욕구를 자극하는 팩트 |
| 답글 | 13.5x | 느낌점의 1인칭 입장으로 자연스러운 반응 유발 (CTA 금지) |
| 북마크 | 10x | "나중에 다시 볼" 가치 있는 정보 |
| 체류 시간 (2분+) | 10x | 스레드 형식으로 읽기 시간 확보 |
| Like | 1x | 기본 |

### 3.2 콘텐츠 포맷 순위
1. **텍스트 전용**: 영상보다 30%, 이미지보다 37% 높은 참여율 (X만의 특성)
2. **네이티브 영상**: 자동재생으로 높은 노출
3. **이미지/GIF**: 적당한 부스트
4. **외부 링크**: 심각한 페널티 (30-50% 도달 감소)

### 3.3 최적 포스팅 조건
- **최적 길이**: 71-100자 (17% 높은 참여율), 최대 좋아요: 240-259자
- **최적 시간**: 화-목 오전 8-10시, 점심 12-1시, 저녁 7-9시 (KST)
- **빈도**: 하루 2-3개 양질의 포스트, 포스트 간 30-60분 간격
- **속도가 핵심**: 첫 30-60분 참여 속도가 알고리즘 결정
- **시간 감쇠**: 6시간마다 ~50% 도달 감소, 24시간 후 최소

### 3.4 페널티 요소
- 외부 링크 (본문에 포함 시)
- 해시태그 3개 이상
- 10분 내 연속 게시
- "like하면 OO" 같은 engagement farming
- 같은 문구 24시간 내 3회 이상 반복

## 4. X 본문 작성 공식 — 쥬팍식 4단 구조

> 2026-06-18 결정: X 본문은 **단일 280자(X 가중) 하나만** 생성한다. 단문(short)·스레드(thread) 포맷은 폐기.

4개 블록을 순서대로 빈 줄로 구분해서 쓴다 (블록 라벨은 적지 않는다):

```
[훅 (hot)]    한 줄. 원문의 핵심 숫자·고유명사로 놀라움/반전.

[팩트 본문 (cold)]  결론 먼저. 한 줄에 정보 하나. 추상어·평가어 대신 숫자·고유명사. 감정 배제.

[요약 한 줄 (cold)]  본문 팩트를 한 문장으로 압축. 라벨·감정 없이.

[느낌점 (hot)]  3문장 이내. 1인칭 직설 구어체. 마지막 줄은 펀치라인.
```

### 공통 규칙
- 반말로 쓰고, 블록 구조(빈 줄 구분)를 지킨다.
- **'~다' 문어체 종결 금지** — 구어체 반말(~음/~네/~지/~함).
- **CTA 금지**: "여러분 ~?", "댓글로 ~", "공감하면 RT", "저장해두세요", 질문으로 끝내기 모두 금지.
- **원문 보존**: 핵심 숫자·고유명사를 그대로 살린다 (예: 1200만원, 2.7억, 뉴욕 닉스). 추상화·일반화·반올림 금지.
- **추상어 동어반복 금지**: "이건 ~가 아니라 ~입니다" 가치 선언, 같은 추상어("문제/기준/본질") 반복 금지.
- 링크/해시태그는 본문이 아닌 별도 첫 답글에 배치. 이모지는 기본 없음.
- 페르소나: 30대 직장인이 친구에게 톡하듯, 인플루언서 톤 금지.

### 구조 예시 (참고)
```
뉴욕 닉스 홈경기 최저가 티켓이 1200만원

제일 비싼 자리는 2.7억
이것도 없어서 못 가는 사람 수두룩

1200만원짜리가 매진인 도시에 호텔방은 비어 있음

제일 싼 게 1200만원인 것도 비현실적인데, 그걸 못 구해 안달인 사람이 그렇게 많다는 게 더 신기하네. 돈 도는 동네는 따로 있구나 싶음. 나는 중계나 봐야지.
```

## 5. 링크-인-리플라이 전략

본문 트윗에는 링크를 넣지 않고, 별도의 **첫 번째 답글(reply)**에 링크를 배치한다.

### 답글 형식
```
원문 보기: {url}
#직장인 #연봉
```

### 이유
- 본문 링크 페널티 (30-50% 도달 감소) 회피
- 해시태그를 답글에 모아 본문 가독성 향상
- 답글이 있으면 스레드로 인식되어 체류 시간 증가

## 6. 수동 게시 워크플로우 (Notion 기반)

```
1. 파이프라인 실행 → Notion DB에 초안 생성
2. Notion에서 review_status = "검토필요" 확인
3. 사람이 멘션 검토/수정 (필요 시)
4. review_status = "승인됨"으로 변경
5. 사람이 직접 X에 게시
   - 본문 트윗 복사 → X에 게시
   - 답글 텍스트 복사 → 즉시 답글로 게시 (링크+해시태그)
6. review_status = "발행완료"로 변경
```

## 7. 실행 도구

| 단계 | 스크립트 | 설명 |
|------|----------|------|
| 수집 | `scrapers/*.py` | 외부 사이트 크롤링 |
| 분석 | `pipeline/content_intelligence.py` | 6D 스코어카드 분류 |
| 초안 | `pipeline/draft_generator.py` | LLM 멀티 프로바이더 초안 |
| 품질 | `pipeline/draft_quality_gate.py` | 자동 품질 검증 |
| 업로드 | `pipeline/notion/_upload.py` | Notion DB 저장 |
| 리뷰 | Notion UI | 사람이 직접 검토/승인 |

## 8. 참고 오픈소스 패턴

- **Postiz** (gitroomhq/postiz-app): AI 캡션 생성 + 큐 관리 + 팀 승인 워크플로우
- **gh-projects-content-queue**: GitHub Issues = 포스트, 컬럼 = 워크플로우 단계 패턴
- **n8n + Notion**: Notion을 콘텐츠 DB로, n8n을 자동화 백본으로 사용하는 패턴
- **RSS-GPT**: 수집 → 중복제거 → AI 요약 → 배포 파이프라인 아키텍처

## 9. Browser source QA note

- Before a live run, use source preflight from the project virtualenv: `.\.venv\Scripts\python.exe main.py --source <source> --source-preflight --source-preflight-output .tmp/source_preflight_<task>.json --source-preflight-screenshot-dir screenshots/source_preflight_<task>`. `main.py --source all` is an explicit alias for all configured `input_sources`.
- For the standalone browser preflight helper, run from `projects/blind-to-x` and use the project virtualenv on Windows: `.\.venv\Scripts\python.exe scripts/source_browser_probe.py --source all ...`. `auto` and `multi` are accepted aliases, and omitting `--source` still probes every known source.
- Before a paid/LLM run, add `--source-preflight-click-through` so the preflight verifies the first post detail, not only that the listing page loaded. HTML sources click a visible post and fall back to the canonical detail URL if mobile overlays or ads obstruct the click; API-backed JobPlanet verifies the first post detail endpoint.
- For guarded multi-source runs where at least one source is still blocked, add `--source-preflight-use-recommended` with `--require-source-ready --source-preflight-click-through` to continue with `summary.recommended_source` instead of aborting the whole run.
- Read `summary.viewport`, `summary.ready_sources`, `summary.problem_sources`, `summary.problem_actions`, `summary.recommended_source`, and `summary.recommended_command` in the preflight JSON before choosing the source for a paid/LLM run. `summary.recommended_source` prefers the ready source with the strongest successful detail evidence, and `summary.recommended_command` gives the guarded pipeline command for that source using the active Python interpreter plus explicit project/config paths. Non-default source preflight viewports are preserved in `summary.recommended_command`.
- For manual click QA, reuse the same browser context assumptions as `scripts/source_browser_probe.py`: `locale=ko-KR`, desktop viewport, and the configured desktop Chrome user agent. A vanilla Chromium context can return false 403/empty results on Ppomppu.
- If a page looks readable in source preflight but manual click QA fails, first compare context options before changing scraper selectors.
