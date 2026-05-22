# HANDOFF.md

## Last Session (2026-05-22 / Claude — goal 이어하기)

- **Goal this session**: 개발된 스킬 대비 코드가 부족한 부분을 찾아 제품 완성도를 끌어올린다.
- **Completed (2 commits)**:
  - **T-408 `c9d1493f`** — T-407 TTS 팩토리 리팩터링 회귀 수정. T-407이 `tts_factory.py`의
    edge-tts 분기와 `_generate_edge_tts_fallback`에서 `channel_key`를 누락시켜, edge-tts를
    직접 쓰거나 chatterbox/cosyvoice/openvoice → edge-tts 폴백 시 채널별 prosody
    (`_CHANNEL_PROSODY`, `pitch_hook_map`)가 전부 기본값으로 무력화됐다 — `shorts-tts-quality`
    스킬 위반. edge-tts 경로 전체에 `channel_key`를 다시 연결. 또한 T-407이 `EdgeTTSClient`
    사용을 `tts_factory`의 함수 내부 import로 옮기면서 깨진 테스트 패치 타깃
    (`media_step.EdgeTTSClient` / `media.audio_mixin.EdgeTTSClient` → 정의 모듈
    `providers.edge_tts_client.EdgeTTSClient`)을 5개 파일에서 복구. 이미지 폴백 체인이
    `media/fallback_mixin.py`로 이동했으므로 `retry_with_backoff` 패치 타깃도 정정.
    깨져 있던 단위 테스트 8개 복구.
  - **T-409 `d775a360`** — 스킬↔설정 정합성. `shorts-tts-quality` 스킬의 채널 음성 표가
    `channel_profiles.yaml`보다 뒤처져 5채널 중 4채널이 불일치했다(SSOT는 스킬이 스스로
    명시한 YAML). 음성 표를 YAML 기준으로 정정, `tts_voice_roles` 역할별 오버라이드 문서화,
    코드에 이미 있던 `closing` 역할을 prosody 표에 추가. 재발 방지로
    `tests/unit/test_skill_config_consistency.py` 신설 — 스킬의 음성 표 / `_CHANNEL_PROSODY`
    / `pitch_hook_map`이 YAML·`edge_tts_client.py`와 어긋나면 CI 실패. `freesound_client.py`의
    거짓 주석("channel_profiles.yaml와 동기") 정정.
- **Verification**: `pytest --no-cov tests/unit tests/integration` — 단위 1542 passed / 12 skipped,
  통합 7 passed, 0 failed. `ruff check` + `ruff format --check` — 변경 파일 전부 clean.
- **주의 (지뢰밭)**:
  - 이 워크스페이스에는 git 작업 사이에 `.ai/*` 및 다른 프로젝트 파일을 인덱스에 자동
    스테이징하는 외부 프로세스가 있다. 깨끗한 단일-프로젝트 커밋은
    `git commit --only -- <명시적 경로>` 로 인덱스를 우회할 것 (`-m`은 `--` 앞에 둘 것).
  - **T-407 리팩터링이 단위 테스트 8개를 깨진 채로 남겼다.** 모듈을 옮기는 리팩터링 시
    그 심볼을 patch/monkeypatch 하는 테스트의 타깃 경로도 함께 갱신해야 한다. patch는
    "정의된 곳"이 아니라 "조회되는 곳"을 노려야 하며, 함수 내부 import의 경우 정의 모듈을
    패치하는 게 안전하다.

## Next Steps

1. 리텐션 시뮬레이터를 실제 LLM 으로 1회 E2E 실행해 예측 곡선 품질을 눈으로 검증
   (`retention_sim_enabled: true`, 영상 1편 생성, `runs/<job>/retention_report.md` 확인).
   — 유료 토큰 사용이므로 사용자 승인 필요.
2. `gate_safe_zone` 의 자막 높이 추정이 `len(narration)//20` 문자 수 기반 —
   `shorts-subtitle-safezone` 스킬이 금지하는 안티패턴. 픽셀 측정 기반으로 정밀화 여지.
3. T-407 같은 리팩터링 회귀를 더 빨리 잡으려면 pre-commit `--cov-fail-under=65` 외에
   PR 단위 full 단위/통합 테스트 게이트 도입 검토.

## Previous Sessions

- **2026-05-22 / Claude** — T-321 리텐션 시뮬레이터 출하(`e194784b`), T-322 미디어 실패
  레코드 `scene_id` 각인(`ce5808a2`), T-323 safe-zone QC 매니페스트 표면화(`9e8531da`).
- **2026-05-20 / Antigravity** — T-320 OpenVoice v2 + MeloTTS 로컬 voice cloning 통합.
  `test_openvoice_client.py` 전역 moviepy mock 오염을 `importlib.util.find_spec` 격리로 해결.
