# shorts-maker-v2 프로젝트 지침

> 이 파일은 `projects/shorts-maker-v2/` 작업 시 자동 로드됩니다.
> 전역 지침 (`../../CLAUDE.md`)과 함께 적용됩니다.
>
> | 도구 | 자동 로드 | 조치 |
> |------|----------|------|
> | Claude Code | ✅ 자동 | 없음 |
> | Gemini (Antigravity) | ❌ 수동 | 세션 시작 시 이 파일 먼저 읽기 |
> | Codex | ❌ 수동 | 세션 시작 시 이 파일 먼저 읽기 |

## 프로젝트 개요

- **목적**: YouTube Shorts 5채널 자동 생성 파이프라인
- **스택**: Python 3.11+, MoviePy 2.x, OpenAI TTS (tts-1-hd), Whisper-1, Pexels, Freesound
- **핵심 파일**: `src/shorts_maker_v2/pipeline/orchestrator.py`, `src/shorts_maker_v2/pipeline/`

## 검증 커맨드

표준 검증은 워크스페이스 루트에서 `execution/project_qc_runner.py`를 사용한다.

```bash
# 워크스페이스 루트에서 실행
python execution/project_qc_runner.py --project shorts-maker-v2 --json
python execution/project_qc_runner.py --project shorts-maker-v2 --check test --json
python execution/project_qc_runner.py --project shorts-maker-v2 --check lint --json
```

프로젝트 루트에서 직접 실행해야 할 때의 동일 커맨드:

```bash
# 전체 단위/통합 테스트
python -m pytest --no-cov tests/unit tests/integration -q --tb=short --maxfail=1

# Lint
python -m ruff check .

# 빠른 단위 테스트 (현재 작업 파일 중심)
python -m pytest --no-cov tests/unit/test_<current>.py -q --tb=short --maxfail=1

# Lint 자동 수정은 변경사항 확인 후에만
python -m ruff check . --fix
```

> ⚠️ `project_qc_runner.py`는 워크스페이스 루트에서, 직접 실행 커맨드는 `projects/shorts-maker-v2/`에서 실행할 것.

## 코드 컨벤션

- **파이프라인 단계**: 각 단계는 독립 모듈 (`script_step.py`, `tts_step.py` 등)
- **폴백 체인**: Pexels Video → Pexels Photo → Unsplash Photo (ADR-006)
- **TTS**: `openai.audio.speech.create()` — `tts-1-hd` 모델, Whisper-1 동기화 (ADR-012)
- **에러 처리**: `manifest.degraded_steps`에 기록, `status="degraded"` 반환
- **SFX**: 현재 비활성화 (ADR-012)

## 프로젝트 스킬 참조

작업 전 반드시 확인:

- **BGM 전략**: `.agents/skills/shorts-bgm-strategy/SKILL.md`
- **대본 페르소나**: `.agents/skills/shorts-script-persona/SKILL.md`
- **자막 안전 영역**: `.agents/skills/shorts-subtitle-safezone/SKILL.md`
- **TTS 품질**: `.agents/skills/shorts-tts-quality/SKILL.md`

## 지뢰밭 (Minefield)

- **MoviePy 2.x**: 1.x API와 다름. `VideoFileClip`, `AudioFileClip` 생성자 파라미터 변동 주의
- **Orchestrator degraded**: `manifest.degraded_steps` 없이 예외 raise 금지
- **coverage 기본값**: `pytest --no-cov` 없이 실행 금지
- **채널 페르소나**: 5채널(AI/기술, 심리학, 역사, 우주, 건강) 각각 고유 톤 — 혼용 금지
- **Freesound**: 에너지 레벨 매핑 스킬 참조 없이 키워드 임의 수정 금지

## Explore 시 반드시 읽을 파일

신규 기능 추가 전:

1. `src/shorts_maker_v2/pipeline/orchestrator.py` — 전체 파이프라인 플로우
2. `src/shorts_maker_v2/pipeline/` 각 단계 파일
3. 해당 `.agents/skills/shorts-*/SKILL.md`

## 컴팩션 보존 컨텍스트

이 프로젝트 관련 컴팩션 발생 시 추가로 보존:

- 작업 중인 파이프라인 단계 (script/tts/video/subtitle/bgm)
- 변경한 채널 설정
- `manifest.degraded_steps` 관련 수정 사항
