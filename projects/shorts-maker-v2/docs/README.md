# shorts-maker-v2

한국어 유튜브 쇼츠를 `CLI + YAML` 기반으로 원클릭 생성하는 MVP 프로젝트입니다.

## 목표

- 단일 주제 입력으로 35~45초 길이의 쇼츠 MP4 생성
- OpenAI + Google 혼합 프로바이더 사용
- 실패 시 재시도 후 이미지 합성으로 자동 폴백

## 빠른 시작

```bash
cd shorts-maker-v2
python -m pip install -r requirements.txt
copy .env.example .env
```

`.env`에 API 키를 설정합니다.

```env
OPENAI_API_KEY=...
GEMINI_API_KEY=...
```

## 실행

사전 점검:

```bash
python -m shorts_maker_v2 doctor --config config.yaml
```

영상 생성:

```bash
python -m shorts_maker_v2 run --topic "블랙홀 미스터리 5가지" --config config.yaml --out shorts_output.mp4
```

## 산출물

- `output/<파일명>.mp4`
- `output/<job_id>_manifest.json`
- `logs/<job_id>.jsonl`
- `runs/<job_id>/media/...`

## 테스트

```bash
python -m pytest -q tests
```

실 API 스모크 테스트(선택):

```bash
set SHORTS_LIVE_SMOKE=1
python -m pytest -q tests/smoke/test_live_smoke.py
```

