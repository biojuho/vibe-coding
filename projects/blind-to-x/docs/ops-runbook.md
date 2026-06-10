# Blind-to-X Ops Runbook

이 문서는 `자동 수집 + 수동 검토 + 수동 발행` 운영 모델 기준 런북입니다.

## 1. Notion 데이터베이스 구성

핵심 검토용 속성:

- `콘텐츠`
- `메모`
- `상태`
- `생성일`
- `원본 URL`
- `운영자 해석`
- `검토 포인트`
- `피드백 요청`
- `위험 신호`
- `근거 앵커`
- `반려 사유`
- `트윗 본문`
- `Threads 본문`
- `블로그 본문`
- `발행 플랫폼`
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

페이지 본문 원칙:

- 상단에서는 `검토 요약`과 `X 업로드 카드`만 먼저 확인합니다.
- `X 업로드 카드`의 `X 본문`을 복사해 게시하고, 원문 링크/해시태그는 `첫 답글 / 출처 메모`로 분리합니다.
- `진단 펼치기`, `원문 펼치기`, `부가 산출물 펼치기`는 필요할 때만 엽니다.
- 보드에는 긴 원문/진단 컬럼보다 검토 판단용 컬럼을 우선 노출합니다.

권장 상태값:

- `검토필요`
- `승인됨`
- `보류`
- `반려`
- `발행완료`

## 2. 권장 뷰

### 검토 큐

- 필터: `상태 = 검토필요`
- 정렬 1: `최종 랭크 점수` 내림차순
- 정렬 2: `발행 적합도 점수` 내림차순
- 표시 권장 컬럼:
- `콘텐츠`
- `원본 소스`
- `토픽 클러스터`
- `감정 축`
- `근거 앵커`
- `검토 포인트`
- `피드백 요청`
- `위험 신호`
- `최종 랭크 점수`
- `트윗 본문`
- `발행 플랫폼`
- `반려 사유`

### 승인 대기

- 필터: `상태 = 승인됨`
- 정렬: `생성일` 내림차순
- 용도: 사람이 실제 발행 전 마지막 확인

### 보류/반려

- 필터: `상태 IN (보류, 반려)`
- 정렬: `생성일` 내림차순
- 용도: 어떤 `반려 사유`와 `위험 신호`가 반복되는지 회고

### 성과 회고

- 필터: `트윗 링크 is not empty`
- 정렬 1: `24h 조회수` 내림차순
- 정렬 2: `24h 좋아요` 내림차순
- 용도: 잘 된 조합과 안 된 조합 파악

## 3. 일간 운영 절차

### 오전

검토 큐 적재:

```powershell
py -3 main.py --source auto --popular --review-only --limit 5
```

`review-only` 실행은 텍스트 초안과 점수 계산까지만 수행합니다. AI 이미지는 승인 이후 발행 단계에서만 생성하도록 비용을 늦춥니다.

검토할 때 보는 기준:

- `검토 포인트`에 적힌 판단 기준이 실제 초안과 맞는지
- `근거 앵커`가 초안에 자연스럽게 살아 있는지
- `운영자 해석`이 과장 없이 납득되는지
- `위험 신호`가 실제 문제인지, 아니면 과한 경고인지
- 반려할 경우 `반려 사유`에 이유를 태그로 남겼는지

처리 기준:

- 바로 쓸 만하면 `승인됨`
- 소재는 괜찮지만 다듬어야 하면 `보류`
- 소재 자체가 약하면 `반려`

### 오후

- `승인됨` 항목만 원하는 채널에 수동으로 올립니다.
- 올린 뒤 아래 속성을 사람이 채웁니다.
  - `트윗 링크`
  - `발행 플랫폼`
  - `발행 시각`
  - `상태 = 발행완료`

## 4. 주간 운영 절차

리포트 생성:

```powershell
py -3 scripts/build_weekly_report.py --days 7
```

점수 재계산:

```powershell
py -3 scripts/recompute_scores.py --days 30
```

리포트에서 보는 포인트:

- 어떤 `토픽 클러스터`가 자주 살아남는지
- 어떤 `훅 타입`이 승인률이 높은지
- 어떤 `감정 축`이 너무 과하거나 약한지
- `최종 랭크 점수`와 실제 체감 품질이 계속 맞는지
- `반려 사유`가 특정 토픽/훅에 몰리는지

## 5. 조정 규칙

검토 큐가 너무 많이 쌓이면:

- `ranking.final_rank_min`을 올립니다.
- `review.queue_limit_per_run`을 줄입니다.

검토 큐가 너무 적으면:

- `ranking.final_rank_min`을 조금 내립니다.
- `review.queue_limit_per_run`을 늘립니다.

LLM 품질이 흔들리면:

- `config.yaml`의 `llm.providers` 순서를 바꿉니다.
- 예: `gemini -> deepseek -> xai -> moonshot -> zhipuai -> openai -> anthropic`

## 6. 점검 명령

Notion 스키마 점검:

```powershell
py -3 scripts/notion_doctor.py --config config.yaml
```

실패하면 `credential_check`를 먼저 봅니다. `missing_credentials`가 있으면 `NOTION_API_KEY`와 `NOTION_DATABASE_ID`를 프로젝트 `.env`, `BLIND_TO_X_ENV_PATH`가 가리키는 파일, 또는 `config.yaml`에 채운 뒤 다시 실행합니다. `credentials_present: true`인데 실패하면 토큰보다 Notion DB/Data Source ID가 맞는지, 그리고 대상 DB가 integration에 공유되어 있는지부터 확인합니다.

자동화에서 읽어야 하면 JSON 모드를 사용합니다.

```powershell
py -3 scripts/notion_doctor.py --config config.yaml --json
```

`status`, `ok`, `credential_check`, `error_code`, `error_message`, `accessible_objects`, `actions`를 보고 실패 원인을 분기합니다. 출력에는 원본 토큰 대신 `token_masked`만 포함됩니다.

검토용 컬럼/옵션 동기화:

```powershell
py -3 scripts/sync_notion_review_schema.py --config config.yaml --apply
```

기존 카드 리뷰 컬럼 백필:

```powershell
py -3 scripts/backfill_notion_review_columns.py --config config.yaml --apply
```

소스 preflight 실패 증거 확인:

```powershell
py -3 scripts/source_browser_probe.py --source all --click-through --output .tmp/source_browser_probe.json --screenshot-dir screenshots/source_probe --failure-dir .tmp/failures/source_preflight
```

Pipeline gate runs should pass the same evidence directory explicitly with `--source-preflight-failure-dir .tmp/failures/source_preflight` when using `main.py --require-source-ready`.

더 무거운 Playwright trace 증거가 필요할 때만 `--trace-dir .tmp/traces/source_preflight` 또는 `main.py --source-preflight-trace-dir .tmp/traces/source_preflight`를 명시합니다. trace zip은 문제 source가 있을 때만 보존되며, `.tmp/traces/`는 커밋하지 않습니다.

캡처된 증거가 완전한지 먼저 검증합니다. 이 명령은 브라우저, Notion, X/Threads/블로그를 호출하지 않고 JSON과 참조된 로컬 증거 파일만 읽습니다.

```powershell
py -3 scripts/source_preflight_evidence_doctor.py --input .tmp/source_browser_probe.json --base-dir . --fail-on-warning
```

여러 로컬 preflight 리포트에서 반복되는 실패 유형을 보려면 trend report를 생성합니다. 출력은 `.tmp/`에 두고 커밋하지 않습니다.

```powershell
py -3 scripts/source_preflight_trend_report.py --input-dir .tmp --glob "source_browser_preflight*.json" --base-dir . --output .tmp/source_preflight_trend.json --json
```

`summary.problem_actions[].evidence`를 먼저 확인합니다. `failure_report_path`, `screenshot_path`, `html_snapshot_path`, `error`, `click_screenshot_path`, `click_error`가 있으면 그 증거를 보고 원인과 다음 조치를 판단합니다. 증거 확인 전에는 timeout을 늘리거나 selector를 바꾸지 말고, `recommended_source`나 `recommended_command`가 있으면 준비된 fallback source로 이번 실행을 진행합니다.

`failure_report_path`가 가리키는 JSON에는 `failure_report.schema_version`, `failure_report.tool`, `failure_report.captured_at`, `operator.action_required`, `operator.action`, `operator.evidence`가 포함됩니다. `classification.status`가 `browser_unavailable`이고 `operator.action`에 Playwright Chromium 설치가 나오면 같은 Python 환경에서 `py -3 -m playwright install chromium`을 실행하거나, 프로젝트 venv를 쓰는 운영자는 `.venv\Scripts\python.exe -m playwright install chromium`으로 설치한 뒤 preflight를 다시 실행합니다. `.tmp/failures/`와 screenshot/html snapshot 출력은 증거 확인용이며 커밋하지 않습니다.

전체 테스트:

```powershell
py -3 -m pytest --no-cov -q tests/unit
```

검토 카드 A/B dry-run:

```powershell
py -3 scripts/review_experiment_dry_run.py --input-mode review-records --input .tmp/review_queue_report_sample.json --min-items 1 --max-missing-rate 0.8 --summary-only
```

이 명령은 Notion, X, Threads, 블로그에 쓰지 않고 콘솔에 rollout gate만 출력합니다. 빠른 운영 판단에는 `--summary-only`를 쓰고, 자동화가 구조화 결과를 읽어야 하면 `--summary-only --json`을 같이 사용합니다.

```powershell
py -3 scripts/review_experiment_dry_run.py --input-mode review-records --input .tmp/review_queue_report_sample.json --min-items 1 --max-missing-rate 0.8 --summary-only --json
```

JSON stdout에서 `output.write_suppressed = true`이면 리포트 파일 쓰기가 억제된 실행입니다. `output.suppression_flags`는 `summary_only` 또는 `no_write`처럼 어떤 플래그가 쓰기를 막았는지 기록합니다.

주간 리포트 A/B 섹션만 로컬에서 확인하려면 Notion을 호출하지 않는 payload smoke를 사용합니다. 입력 JSON은 `.tmp/`에 두고 커밋하지 않습니다.

```powershell
py -3 scripts/build_weekly_report.py --payload-input .tmp/weekly_report_payload_smoke.json --review-experiment-input .tmp/weekly_report_experiment_smoke.json --source-preflight-trend-input .tmp/source_preflight_trend.json --output .tmp/weekly_report_smoke.md
```

이 명령은 `--payload-input`에 있는 주간 리포트 payload를 그대로 렌더링하고, `--review-experiment-input`의 dry-run 결과를 `Review Experiment A/B Summary (dry-run)` 섹션에, `--source-preflight-trend-input`의 로컬 증거 집계를 `Source Preflight Trend (dry-run)` 섹션에 붙입니다. Notion 조회, Notion 쓰기, X/Threads/블로그 발행, 브라우저 실행은 하지 않습니다. 출력에서 `Safety: read_only=true`, `notion_writes=false`, `x_posts=false`, `manual_publish_required=true`, `Top source action`, `Top source checklist`, `Next manual action`을 먼저 확인합니다.

> 경로는 `tests/unit/` 입니다. 워크스페이스 표준 검증은 루트에서:
>
> ```powershell
> py -3 execution\project_qc_runner.py --project blind-to-x --json
> ```

## 7. 현재 범위 밖

- 특정 채널 자동 발행
- Twitter 성과 자동 수집
- 별도 관리자 대시보드

이 세 가지는 현재 기본 운영 범위가 아닙니다.
