# HANDOFF.md

## Last Session (2026-05-22 / Claude)

- **Goal this session**: 개발된 스킬/품질 기준 대비 부족한 부분을 찾아 제품 완성도를 끌어올린다. 3개 트랙(리텐션 기능 출하 / 에러 가시성 / QC 게이트 강화) 수행.
- **Completed (3 commits)**:
  - **T-321 `e194784b`** — 합성 시청자 리텐션 시뮬레이터 출하. 미커밋 상태였던 `retention_simulator.py` / `retention_autofix.py` / `retention_report.py` + orchestrator 통합 + config 5종을 검증 후 정식 커밋. 5개 페르소나가 씬 경계마다 이탈/잔류를 판단해 예측 리텐션 곡선을 산출, 임계값 미만이면 `degraded_steps` 표면화. LLM 실패 시 휴리스틱 강등. 전부 기본값 False (opt-in).
  - **T-322 `ce5808a2`** — 미디어 실패 추적성 개선. `media_step` 의 폴백/실패 레코드는 `manifest.failed_steps` 에 기록되지만 어느 씬인지 식별 불가였다. `_process_one_scene` 반환 직전 모든 failure 에 `scene_id` 각인(setdefault), Whisper word-sync 경고와 `run_parallel` 예외 catch 에도 `scene_id` 추가, `_sanitize_visual_prompt` 의 침묵 `except: pass` 를 debug 로그로 대체.
  - **T-323 `9e8531da`** — safe-zone QC 결과를 매니페스트에 표면화. `gate_safe_zone` 은 자막이 YouTube Shorts UI 안전 영역을 침범하는지 검출하지만 orchestrator 가 `jlog` 경고로만 남기고 버렸다. HOLD 판정 시 `degraded_steps` 에 `caption_safe_zone_violation` 추가. 그동안 미검증이던 `QCStep.gate_safe_zone` 직접 회귀 테스트 3종 추가.
- **Verification**:
  - `pytest --no-cov` — retention 143 / media 30+2 / safe_zone 16 / orchestrator+qc 128 / 통합 3 전부 통과.
  - `ruff check` + `ruff format --check` — 변경 파일 전부 clean.
- **주의 (지뢰밭)**: 이 워크스페이스에는 git 작업 사이에 `.ai/*` 및 다른 프로젝트 파일을 인덱스에 자동 스테이징하는 외부 프로세스가 있다. 깨끗한 단일-프로젝트 커밋은 `git commit -- <명시적 경로>` (partial commit) 로 인덱스를 우회해야 한다. `git add` 후 `git commit` 는 무관 파일을 휩쓴다.

## Next Steps

1. 리텐션 시뮬레이터를 실제 LLM 으로 1회 E2E 실행해 예측 곡선 품질을 눈으로 검증 (`retention_sim_enabled: true` 로 켜고 영상 1편 생성, `runs/<job>/retention_report.md` 확인).
2. 미선택 트랙 — 스킬↔코드 정합성: `shorts-tts-quality` 스킬의 TTS 음성 매핑과 `channel_profiles.yaml` 이 4/5 채널 불일치, `freesound_client.CHANNEL_BGM_ENERGY`(health=warm_uplifting) ↔ `channel_profiles.yaml`(health=medium) 모순. 어느 쪽을 SSOT 로 할지 결정 필요.
3. `gate_safe_zone` 의 자막 높이 추정이 `len(narration)//20` 문자 수 기반 — `shorts-subtitle-safezone` 스킬이 금지하는 안티패턴. 픽셀 측정 기반으로 정밀화 여지.

## Previous Session (2026-05-20 / Antigravity)

- **Goal**: OpenVoice v2 + MeloTTS 로컬 고품질 voice cloning 통합 (T-320).
- `OpenVoiceTTSClient` (`openvoice_client.py`) 구현, CPU fallback + lazy import. `MediaAudioMixin` cascade 에 `"openvoice"` 라우팅 추가. `test_openvoice_client.py` 8 테스트.
- **[Pollution Fix]** `test_openvoice_client.py` 의 전역 `moviepy` mock 이 다른 테스트를 오염시키던 문제를 `importlib.util.find_spec` 격리 모킹으로 해결.
