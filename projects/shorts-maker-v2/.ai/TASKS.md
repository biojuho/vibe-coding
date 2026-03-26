# 프로젝트 칸반 보드 (TASKS.md)

## TODO

- [ ] V2 파이프라인 주요 모듈 (`render_step.py`, `script_step.py` 등) 단위 테스트 보강 및 커버리지(최소 45% 확보 후 80% 상향) (담당: TBD)
- [ ] 운영 환경에서 트렌드 수집 소스의 API 응답 안정성 모니터링 (담당: TBD)

## IN_PROGRESS

- [/] 레거시 테스트(`tests/legacy/`) 호환성 정리 (ShortsFactory 기반 코드 추려냄, 삭제 대기 단계) (담당: Antigravity)

## DONE

- [x] 카라오케 하이라이트 렌더링(`karaoke.py`) 유닛 테스트 보강 및 97% 커버리지 달성 (2026-03-27, Antigravity)
- [x] TrendDiscoveryStep 신규 모듈 작성 및 파이프라인 QC 통합 (2026-03-26, Antigravity)
- [x] TrendDiscoveryStep, RenderStep 오류 수정 및 파이프라인 QC 안정화 (2026-03-26, Antigravity)
- [x] TrendDiscoveryStep, TopicAngleGenerator 연동 및 테스트 통과 (2026-03-26, Antigravity)
- [x] CLI `--auto-topic` 플래그 통합 (2026-03-26, Antigravity)
- [x] 프롬프트 템플릿 KeyError 및 설정 버그 수정 (2026-03-26, Antigravity)
- [x] 스크립트 품질 강화 Phase 2 (2026-03-22, Antigravity)
