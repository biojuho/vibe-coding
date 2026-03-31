# VibeDebt Audit - 기술 부채 정량화 및 추적

> 바이브 코딩 프로젝트의 기술 부채를 자동 진단, 정량화, 추이 추적하는 SOP.

## 목적

바이브 코딩(Vibe Coding)은 AI 중심의 빠른 반복 개발로 속도를 극대화하지만,
코드 맥락 이해 부족, 반복 수정, 체계적 설계 미비로 기술 부채가 누적됩니다.

이 지침은 기술 부채를 **정량화**하여 관리 가능한 자산으로 전환합니다.

## 핵심 지표

### 1. TDR (Technical Debt Ratio)
```
TDR = (수정 비용 / 개발 비용) × 100
```
- 5% 미만: 건강 (GREEN)
- 5~10%: 주의 (YELLOW)
- 10% 초과: 위험 (RED)

### 2. 파일별 부채 점수 (0-100)
6개 차원의 가중 합산:
| 차원 | 가중치 | 측정 기준 |
|------|--------|----------|
| 복잡도 (Complexity) | 25% | Cyclomatic complexity, 함수 길이 |
| 중복도 (Duplication) | 20% | 유사 코드 블록 비율 |
| 테스트 결핍 (Test Gap) | 20% | 해당 모듈의 테스트 커버리지 역수 |
| 부채 마커 (Debt Markers) | 15% | TODO/FIXME/HACK/XXX 밀도 |
| 모듈화 (Modularity) | 10% | import 깊이, 파일 크기 |
| 문서 동기화 (Doc Sync) | 10% | directive-execution 매핑 상태 |

### 3. 원금/이자 모델
- **원금**: 부채 해소에 필요한 추정 시간 (분)
- **이자**: 부채로 인한 월별 추가 유지보수 비용 추정

## 입력

- 프로젝트 코드베이스 (workspace/, projects/)
- 기존 qaqc_runner.py 결과 (qaqc_result.json)
- 테스트 커버리지 데이터

## 실행 스크립트

| Script | 역할 |
|--------|------|
| `vibe_debt_auditor.py` | 부채 스캔 + TDR 계산 + JSON 리포트 생성 |
| `debt_history_db.py` | SQLite 시계열 저장 + 추이 조회 |

## 출력

1. **JSON 리포트**: `.tmp/debt_audit_result.json`
2. **SQLite 이력**: `.tmp/debt_history.db`
3. **Streamlit 대시보드**: `pages/debt_dashboard.py`

## 실행 방법

```bash
# 전체 스캔
python workspace/execution/vibe_debt_auditor.py

# 특정 프로젝트만
python workspace/execution/vibe_debt_auditor.py --project blind-to-x

# JSON 출력
python workspace/execution/vibe_debt_auditor.py --format json
```

## QA/QC 통합

`qaqc_runner.py`에 선택적 단계로 통합:
- TDR > 10% 시 REVIEW 판정에 경고 추가
- 부채 추이가 3회 연속 증가 시 Telegram 알림

## 자가 수정 루프

1. 새로운 부채 패턴 발견 → 탐지 규칙 추가
2. 오탐(false positive) 발생 → 제외 패턴 업데이트
3. 프로젝트 추가 시 → 스캔 대상 자동 확장

---

*생성: 2026-03-31*
