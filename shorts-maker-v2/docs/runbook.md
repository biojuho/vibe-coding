# 운영 Runbook

## 1. 사전 준비

1. `python -m pip install -r requirements.txt`
2. `.env` 파일에 `OPENAI_API_KEY`, `GEMINI_API_KEY` 설정
3. `python -m shorts_maker_v2 doctor --config config.yaml` 실행

## 2. 생성 실행

```bash
python -m shorts_maker_v2 run --topic "오늘의 주제" --config config.yaml --out my_short.mp4
```

## 3. 실패 대응

- `logs/<job_id>.jsonl`에서 실패 스텝 확인
- `output/<job_id>_manifest.json`의 `failed_steps` 확인
- `visual_primary` 실패 시 자동으로 이미지 폴백되는지 확인

## 4. 비용 관리

- `config.yaml`의 `limits.max_cost_usd`로 상한 제어
- `costs.*` 값을 실제 요금 체계에 맞게 주기적으로 보정
- 상한 초과 예상 시 Veo는 자동 제한되고 이미지 모드로 전환

## 5. 스모크 검증(20회)

```bash
python tests/smoke/run_20_jobs.py --config config.yaml --topic "과학 상식" --iterations 20
```

성공 기준:

- 20회 중 18회 이상 성공(90%+)
- 생성물 MP4 존재
- 길이 35~45초 범위

