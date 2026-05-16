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
py -3 main.py --source auto --popular --review-only --limit 5
py -3 main.py --source blind --popular --review-only --limit 5
py -3 main.py --source multi --popular --review-only --limit 5

# 승인된 항목 재처리용 경로
py -3 main.py --reprocess-approved --limit 5

# Notion 연결 및 스키마 진단
py -3 scripts/notion_doctor.py --config config.yaml

# 최근 항목 점수 재계산
py -3 scripts/recompute_scores.py --days 30

# 주간 리포트 생성
py -3 scripts/build_weekly_report.py --days 7

# 전체 단위 테스트
py -3 -m pytest --no-cov -q tests/unit
```

## 설치

```bash
# 의존성은 pyproject.toml에 정의되어 있습니다. 프로젝트 루트에서:
pip install -e .[dev]
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

핵심 검토용 속성:

- `콘텐츠`
- `원본 URL`
- `메모`
- `운영자 해석`
- `근거 앵커`
- `검토 포인트`
- `피드백 요청`
- `위험 신호`
- `반려 사유`
- `발행 플랫폼`
- `트윗 본문`
- `Threads 본문`
- `블로그 본문`
- `원본 소스`
- `토픽 클러스터`
- `감정 축`
- `최종 랭크 점수`
- `성과 등급`

선택 운영/회고용 속성:

- `트윗 링크`
- `24h 조회수`
- `24h 좋아요`
- `24h 리트윗`

페이지 본문 운영 원칙:

- 상단은 `검토 요약`과 `채널 초안`만 먼저 봅니다.
- `진단 펼치기`, `원문 펼치기`, `부가 산출물 펼치기` 토글은 필요할 때만 엽니다.
- 보드 뷰에 원문/진단용 긴 컬럼을 과하게 노출하지 않는 것을 권장합니다.

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
py -3 main.py --source auto --popular --review-only --limit 5
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

현재 CI는 워크스페이스 매트릭스 워크플로 (`.github/workflows/full-test-matrix.yml`)의 `blind-to-x-tests` 잡으로 통합되어 있으며, `main` 푸시 / PR 시 자동 실행됩니다.

- 단위 테스트: `python -m pytest tests/unit -q --tb=short --maxfail=1`
- 통합 테스트: `python -m pytest tests/integration ... --ignore=tests/integration/test_curl_cffi.py`

크론/스케줄 실행은 현재 활성화되어 있지 않습니다. 정기 적재가 필요하면 별도 스케줄러(예: workspace `execution/scheduler_engine.py`)를 사용합니다.

## 관측성 (Observability)

- **Langfuse 트레이스**: `LANGFUSE_ENABLED=1` 환경변수가 설정되면 `pipeline/draft_providers.py`가 워크스페이스 Langfuse 훅으로 LLM 호출 메타데이터(프로바이더, 모델, 토큰, 지연, 성공 여부)를 전송합니다.
- **워크스페이스 사용량 미러링**: `BTX_USAGE_FORWARD=1` 일 때 `pipeline/cost_tracker.py`가 프로젝트 로컬 `btx_costs.db` 기록과 동시에 워크스페이스 `.tmp/workspace.db`의 `api_calls` 테이블에도 사용량을 미러링합니다. 워크스페이스 알림(`api_usage_tracker alerts` — fallback rate / cost spike / dead provider)이 blind-to-x 호출까지 감지하도록 활성화합니다.
- 프로젝트 로컬 cost db (`btx_costs.db`)는 항상 기록되며 진실의 원천(authoritative source)입니다. 미러링은 부가 관측 채널입니다.

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
