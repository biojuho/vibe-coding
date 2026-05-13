# FEATURE: Scene-Level QC strictness + configurable retries

## Background

shorts-maker-v2 의 Scene-Level QC 인프라(`gate_scene_qc`, `scene_qc_enabled`,
orchestrator 자동 재생성 루프, `SceneQCResult` 모델, role-based duration 체크 등)는
이미 출하되어 있다. 하지만 운영자가 QC를 "엄격하게" 또는 "느슨하게" 조정할 수
없고, 재시도 한도가 코드(`MAX_SCENE_RETRIES = 2`)에 박혀 있다.

## Scope (좁은 갭만)

이 변경의 **유일한** 목적은:

1. `project.qc_strictness` 설정 도입 — `"strict" | "lenient" | "off"`
   - `strict` (기본값): 현재 동작 유지 — 이슈 1개라도 있으면 `verdict = "fail_retry"`.
   - `lenient`: 모든 체크를 그대로 돌리지만 **essential check**(파일 존재 = `audio_ok` / `visual_ok`)
     만 실패해야 `fail_retry`로 판정. duration / hook 길이 / CTA 단어 같은 비-essential 이슈는
     `verdict = "pass"`로 통과시키되 `issues` 리스트에는 남겨 manifest로 보존.
   - `off`: orchestrator가 scene QC 블록 자체를 건너뜀 (`scene_qc_enabled=False`와 동등 효과지만,
     기존 `scene_qc_enabled=True` + `qc_strictness="off"` 조합으로도 비활성화 가능).
2. `project.scene_qc_max_retries: int = 2` 설정 도입 — orchestrator의 하드코딩 상수를 대체.

기존 외부 API/매니페스트 스키마는 그대로 둔다. `SceneQCResult` 필드 추가 없음.
`gate_scene_qc()`에는 `strictness` 키워드 인자(기본 `"strict"`)만 추가.

## Non-goals

- Abrupt transition 감지(시각 연속성), 씬별 RMS 오디오 검사, LLM 기반 QC 등은 이 변경에서 **다루지 않는다**.
- 기존 Gate 3 / Gate 4 / Safe-zone QC 로직은 변경하지 않는다.

## Acceptance criteria

- [ ] `ProjectSettings`에 `qc_strictness: str = "strict"` 와 `scene_qc_max_retries: int = 2` 추가.
- [ ] `load_config()` 가 `config.yaml.project.qc_strictness` / `scene_qc_max_retries` 를 읽고,
      `qc_strictness` 가 허용값(`strict`/`lenient`/`off`) 외이면 `ConfigError` 발생.
- [ ] `QCStep.gate_scene_qc(plan, asset, prev, next, *, strictness="strict")` 시그니처.
      - `strictness="strict"`: 현재 동작 그대로(기존 테스트 100% 통과).
      - `strictness="lenient"`: essential check(`audio_ok`/`visual_ok`) 모두 True 면 `verdict="pass"`,
        이슈가 있어도 통과. essential 실패면 기존대로 `fail_retry`.
      - `strictness="off"`: 모든 check 스킵하고 `verdict="pass"`, `checks={}`, `issues=[]` 반환.
- [ ] `Orchestrator` 가 `scene_qc_max_retries` 와 `qc_strictness` 를 사용하여 루프를 돌고,
      `qc_strictness="off"` 면 scene_qc 블록을 진입하지 않는다.
- [ ] `test_qc_step.py` 에 strictness 동작 회귀 테스트 추가(strict/lenient/off 각 1개 이상,
      essential vs non-essential 분기 포함).
- [ ] `test_config.py`(또는 기존 config 테스트 모듈) 에 새 필드 파싱/검증 테스트 추가.
- [ ] `python -m ruff check .` clean, `python -m pytest --no-cov tests/unit -q` 그대로 통과.

## Rollback

`qc_strictness` 기본값이 `"strict"` 이고 `scene_qc_max_retries` 기본값이 `2` 라
기존 `config.yaml` 파일은 변경 없이 그대로 동작한다. 변경한 모듈은
`config.py`, `pipeline/qc_step.py`, `pipeline/orchestrator.py`, 그리고 테스트뿐이다.
