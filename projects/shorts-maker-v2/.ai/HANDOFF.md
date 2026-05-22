# HANDOFF.md

## Last Session (2026-05-23 / Claude — goal 이어하기)

- **Goal this session**: 개발된 스킬 대비 코드가 부족한 부분을 찾아 제품 완성도를 끌어올린다.
- **Completed (1 commit)**:
  - **T-410 `1aeb9eaa`** — safe-zone QC 자막 높이 측정을 문자 수 추정 → 픽셀 측정으로 교체.
    `gate_safe_zone` 이 자막 높이를 `len(narration_ko)//20` 줄로 추정했는데, 이는
    `shorts-subtitle-safezone` 스킬이 안티패턴으로 명시 금지하는 문자 수 기반 방식이다
    (한글·영문 글자 폭이 달라 같은 글자 수도 줄 수가 다름). 또 자막 mode 를 무시해
    karaoke 모드의 긴 나레이션(청크 단위 한 줄 렌더)을 다줄 세로 오버플로우로 오탐했다.
    `caption_pillow.py` 에 `estimate_caption_height()` 신설 — `render_caption_image`
    (static) / `render_karaoke_image` (karaoke) 의 레이아웃 산식을 2x 슈퍼샘플링 +
    `//scale` 다운샘플까지 그대로 재현해 실제 렌더 PNG 와 픽셀 단위로 일치한다.
    `gate_safe_zone` 에 `canvas_width` + 역할별 `styles` 인자 추가, orchestrator 가
    RenderStep 의 hook/body/cta/closing 스타일과 config 해상도를 넘겨 QC 가 실제
    폰트·여백·글로우·모드로 측정하게 함.
- **Verification**: `pytest --no-cov tests/unit tests/integration` — exit 0 (전부 통과,
  회귀 없음). `ruff check` + `ruff format --check` — 변경 파일 전부 clean.
- **주의 (지뢰밭)**:
  - 이 워크스페이스에는 git 작업 사이에 `.ai/*` 및 다른 프로젝트 파일을 인덱스에 자동
    스테이징하는 외부 프로세스가 있다. 깨끗한 단일-프로젝트 커밋은
    `git commit --only -- <명시적 경로>` 로 인덱스를 우회할 것 (`-m`은 `--` 앞에 둘 것).
  - **`estimate_caption_height` 는 렌더 함수 산식의 복제다.** `render_caption_image` /
    `render_karaoke_image` 의 패딩·스케일·spacing 산식을 바꾸면 `estimate_caption_height`
    도 함께 고칠 것. `test_caption_pillow.py::TestEstimateCaptionHeight` 가 렌더 PNG 와
    `==`(정확 일치)로 비교하므로 드리프트는 CI 가 잡지만, 렌더 수정 시 같이 손볼 것.
  - pre-commit code-review-gate 가 FAIL 로 떠도 advisory 라 커밋은 통과한다. 보고된
    "test gap" 다수는 본 변경과 무관한 다른 워크스페이스 파일(confidence.ts 등)이다.

## Next Steps

1. 리텐션 시뮬레이터를 실제 LLM 으로 1회 E2E 실행해 예측 곡선 품질을 눈으로 검증
   (`retention_sim_enabled: true`, 영상 1편 생성, `runs/<job>/retention_report.md` 확인).
   — 유료 토큰 사용이므로 사용자 승인 필요.
2. T-410 같은 회귀를 더 빨리 잡으려면 pre-commit `--cov-fail-under=65` 외에
   PR 단위 full 단위/통합 테스트 게이트 도입 검토.
3. `gate_safe_zone` 은 static/karaoke 자막 높이를 픽셀 측정한다. word-highlight 모드
   (`render_karaoke_highlight_image`, 활성 단어 1.15x 확대)는 청크 단위라 현재
   karaoke 측정과 근사하지만, 확대 폰트까지 반영하는 정밀화 여지가 있다.

## Previous Sessions

- **2026-05-22 / Claude** — T-408 edge-tts `channel_key` 회귀 수정(`c9d1493f`),
  T-409 `shorts-tts-quality` 스킬↔YAML 정합 정정 + drift guard 신설(`d775a360`).
- **2026-05-22 / Claude** — T-321 리텐션 시뮬레이터 출하(`e194784b`), T-322 미디어 실패
  레코드 `scene_id` 각인(`ce5808a2`), T-323 safe-zone QC 매니페스트 표면화(`9e8531da`).
- **2026-05-20 / Antigravity** — T-320 OpenVoice v2 + MeloTTS 로컬 voice cloning 통합.
  `test_openvoice_client.py` 전역 moviepy mock 오염을 `importlib.util.find_spec` 격리로 해결.
