# NotebookLM 운영 SOP (팟캐스트 제외)

> **도입일**: 2026-03-18
> **도구**: `notebooklm-py` v0.3.4 (비공식)
> **제외 기능**: Audio Overview (팟캐스트) — 향후 필요 시 확장

## 인증 관리

```bash
# 인증 확인
notebooklm status
notebooklm auth check --test

# 재인증 (세션 만료 시)
notebooklm login
```

- 인증 파일: `~/.notebooklm/storage_state.json` (쿠키 기반)
- 만료 시 브라우저 로그인 필요

## 사용 가능 기능

### 리서치 & 소스 관리

| 작업 | 명령어 |
|------|--------|
| 노트북 생성 | `notebooklm create "제목"` |
| URL 추가 | `notebooklm source add "https://..."` |
| PDF 추가 | `notebooklm source add ./file.pdf` |
| YouTube 추가 | `notebooklm source add "https://youtube.com/..."` |
| **자동 소스 탐색 (권장)** | `notebooklm source add-research "쿼리" --mode deep --import-all` |
| 빠른 리서치 | `notebooklm source add-research "쿼리" --mode fast` |
| 비동기 리서치 | `notebooklm source add-research "쿼리" --mode deep --no-wait` |
| 질의응답 | `notebooklm ask "질문"` |

> **소스 자동 연동 (신규)**: `--import-all` 옵션 사용 시 Deep Research가 웹에서 찾은 고품질 소스를 노트북에 자동으로 임포트합니다. 위키피디아만 수동으로 지정할 필요 없습니다.

### 콘텐츠 생성 (팟캐스트 제외)

| 유형 | 명령어 | 다운로드 |
|------|--------|----------|
| 비디오 | `notebooklm generate video` | `.mp4` |
| 슬라이드 | `notebooklm generate slide-deck` | `.pptx` |
| 퀴즈 | `notebooklm generate quiz` | `.json/.md` |
| 플래시카드 | `notebooklm generate flashcards` | `.json/.md` |
| 인포그래픽 | `notebooklm generate infographic` | `.png` |
| 마인드맵 | `notebooklm generate mind-map` | `.json` |
| 데이터 테이블 | `notebooklm generate data-table "설명"` | `.csv` |
| 리포트 | `notebooklm generate report` | `.md` |

### 언어 설정

```bash
notebooklm language set ko  # 한국어 설정
```

## 파이프라인 연계

### 자동 소스 연동 워크플로우 (권장)

```bash
# 주제만 넣으면 딥 리서치 → 소스 자동 수집 → 마인드맵+리포트 생성까지 원스톱
python workspace/execution/notebooklm_integration.py auto-research "2026년 AI 최신 트렌드"

# 또는 세부 설정
python workspace/execution/notebooklm_integration.py research "노트북 제목" \
  --query "검색하고 싶은 주제" \
  --search-mode deep
```

### Blind-to-X 리서치 보강

1. 스크래핑 후 데이터를 NotebookLM에 임포트
2. `ask` 명령으로 심층 분석 추출
3. 마인드맵/리포트 자동 생성

### Shorts Maker V2 스크립트 리서치

1. `research_workflow(title, query="주제", search_mode="deep")` 호출로 자동 소스 연동
2. `ask`로 스크립트 초안 소재 추출
3. 마인드맵/리포트 자동 생성

## 에러 대응

| 에러 | 원인 | 조치 |
|------|------|------|
| Auth 에러 | 세션 만료 | `notebooklm login` |
| Rate Limiting | Google 제한 | 5-10분 대기 후 재시도 |
| RPC 에러 | API 변경 | `pip install --upgrade notebooklm-py` |

## 주의사항

- **비공식 API**: Google이 언제든 변경 가능. 핵심 의존 금지
- **Rate Limit**: Video/Quiz/Flashcards/Infographic/Slide Deck은 빈번 제한
- **안정 기능**: Notebook, Source, Chat, Mind-map, Report, Data-table은 항상 동작
