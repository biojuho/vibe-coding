# Blind-to-X

Blind 게시글을 수집해서 점수화하고, Notion 검토 큐에 적재하는 운영 파이프라인입니다.

현재 기본 운영 모델은 `자동 수집 + 수동 검토 + 수동 발행`입니다. 특정 채널 자동 발행은 기본 전제가 아니며, 검토자가 Notion에서 먼저 판단하고 수동으로 결정하는 흐름을 우선합니다.

## 현재 운영 흐름

1. Blind 인기글 또는 트렌딩 글을 수집합니다.
2. 게시글 본문, 메타데이터, 스크린샷을 생성합니다.
3. 콘텐츠 인텔리전스가 아래 항목을 계산합니다.
   - `토픽 클러스터`
   - `훅 타입`
   - `감정 축`
   - `대상 독자`
   - `스크랩 품질 점수`
   - `발행 적합도 점수`
   - `성과 예측 점수`
   - `최종 랭크 점수`
4. LLM이 초안을 생성합니다.
   - 기본 fallback 순서: `Gemini -> DeepSeek -> xAI -> Moonshot -> ZhipuAI -> OpenAI -> Anthropic`
5. 상위 후보만 Notion `검토필요` 상태로 적재합니다.
6. 운영자가 Notion에서 승인 여부와 초안 타입을 결정합니다.
7. 발행은 사람이 직접 원하는 채널에 수동으로 올립니다.

## 현재 엔트리포인트

실행 진입점은 `blind_scraper.py`가 아니라 `main.py`입니다.

주요 명령:

```bash
# 검토 큐 적재
py -3 main.py --source blind --popular --review-only --limit 5

# 승인된 항목 재처리용 경로
py -3 main.py --reprocess-approved --limit 5

# Notion 연결 및 스키마 진단
py -3 scripts/notion_doctor.py --config config.yaml

# 최근 항목 점수 재계산
py -3 scripts/recompute_scores.py --days 30

# 주간 리포트 생성
py -3 scripts/build_weekly_report.py --days 7

# 전체 단위 테스트
py -3 -m pytest -q tests_unit
```

## 설치

```bash
pip install -r requirements.txt
playwright install chromium
```

## 설정

1. `config.example.yaml`을 복사해서 `config.yaml`을 만듭니다.
2. `.env.example`을 복사해서 `.env`를 만들고 운영 키를 넣습니다.
3. 키 파일은 절대 커밋하지 않습니다. 이미 노출된 키가 있다면 공급자 콘솔에서 즉시 폐기 후 재발급합니다.
4. 먼저 아래 명령으로 Notion 연결을 확인합니다.

```bash
py -3 scripts/notion_doctor.py --config config.yaml
```

## 필수 환경 변수

최소 운영 기준:

```env
NOTION_API_KEY=...
NOTION_DATABASE_ID=...
```

Blind 로그인까지 자동화하려면:

```env
BLIND_EMAIL=...
BLIND_PASSWORD=...
```

LLM 초안 생성을 위해 최소 1개 이상 필요:

```env
ANTHROPIC_API_KEY=...
GOOGLE_API_KEY=...
XAI_API_KEY=...
DEEPSEEK_API_KEY=...
MOONSHOT_API_KEY=...
ZHIPUAI_API_KEY=...
OPENAI_API_KEY=...
```

이미지 생성까지 사용하려면:

```env
OPENAI_IMAGE_ENABLED=true
OPENAI_API_KEY=...
```

Cloudinary 업로드를 권장합니다:

```env
CLOUDINARY_CLOUD_NAME=...
CLOUDINARY_API_KEY=...
CLOUDINARY_API_SECRET=...
```

X 자동 발행은 선택 사항입니다. 쓰지 않는다면 Twitter 키는 없어도 됩니다.

## Notion 운영 규칙

권장 상태값:

- `수집됨`
- `검토필요`
- `승인됨`
- `보류`
- `반려`
- `발행완료`
- `성과반영완료`

권장 속성:

- `콘텐츠`
- `Source URL`
- `운영자 해석`
- `검토 포인트`
- `피드백 요청`
- `위험 신호`
- `근거 앵커`
- `반려 사유`
- `트윗 본문`
- `뉴스레터 초안`
- `원본 소스`
- `피드 모드`
- `토픽 클러스터`
- `훅 타입`
- `감정 축`
- `대상 독자`
- `스크랩 품질 점수`
- `발행 적합도 점수`
- `성과 예측 점수`
- `최종 랭크 점수`
- `승인 상태`
- `검토 메모`
- `선택 초안 타입`
- `트윗 링크`
- `발행 플랫폼`
- `24h 조회수`
- `24h 좋아요`
- `24h 리트윗`
- `성과 등급`

Notion 뷰 구성은 [`docs/ops-runbook.md`](docs/ops-runbook.md) 기준으로 맞추는 것을 권장합니다.

리뷰용 컬럼을 실제 Notion DB에 추가하려면:

```bash
py -3 scripts/sync_notion_review_schema.py --config config.yaml --apply
```

기존 카드까지 새 리뷰 컬럼으로 채우려면:

```bash
py -3 scripts/backfill_notion_review_columns.py --config config.yaml --apply
```

## 추천 일간 운영

1. 검토 큐 적재

```bash
py -3 main.py --source blind --popular --review-only --limit 5
```

`review-only` 단계에서는 AI 이미지 생성을 미루고 텍스트 초안과 스코어링만 수행합니다. 비용은 승인 이후에 집행하는 것이 기본 정책입니다.

2. Notion에서 `승인 상태 = 검토필요` 뷰를 확인합니다.
3. `검토 포인트`, `피드백 요청`, `위험 신호`, `반려 사유` 컬럼 기준으로 판단합니다.
4. 괜찮은 항목만 `승인됨`으로 바꾸고 초안을 편집합니다.
5. 실제 발행은 사람이 수동으로 진행합니다.

## 추천 주간 운영

1. 최근 7일 리포트 생성

```bash
py -3 scripts/build_weekly_report.py --days 7
```

2. 최근 30일 점수 재계산

```bash
py -3 scripts/recompute_scores.py --days 30
```

3. 리포트를 보고 `ranking.final_rank_min`, `review.queue_limit_per_run`, `llm.providers` 순서를 조정합니다.

## GitHub Actions

현재 GitHub Actions 워크플로는 3시간마다 아래 명령을 실행합니다.

```bash
python main.py --source blind --popular --review-only --limit 5
```

즉, 기본 자동화 범위는 `검토 큐 적재`까지입니다.

## 장애 대응

`scripts/notion_doctor.py`가 실패하면:

- `NOTION_API_KEY`
- `NOTION_DATABASE_ID`
- Notion 속성명

을 먼저 확인합니다.

Blind 수집 실패가 늘어나면:

- `.tmp/app_debug.log`
- `.tmp/failures`

를 확인해서 사이트 구조 변경 또는 차단 여부를 봅니다.

LLM 호출이 실패하면:

- `Gemini -> DeepSeek -> xAI -> Moonshot -> ZhipuAI -> OpenAI -> Anthropic` 순서로 자동 fallback 됩니다.
- 특정 공급자를 우선으로 쓰고 싶다면 `config.yaml`의 `llm.providers` 순서를 바꾸면 됩니다.

## 테스트 현황

최근 기준으로 아래가 검증된 상태입니다.

- Notion 스키마 진단 통과
- `review-only` 실배치 성공
- Anthropic 잔액 부족 시 Gemini fallback 성공
- 검토 큐 적재 성공
- 환경변수 기반 런타임 fallback 테스트 통과

자동 발행은 현재 기본 운영 범위가 아니므로, 특정 채널 키가 없어도 검토 큐 운영은 정상적으로 가능합니다.
