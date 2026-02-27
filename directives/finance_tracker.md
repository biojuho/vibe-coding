# 재무 트래커 지침 (Finance Tracker Directive)

> 개인 수입/지출을 추적하고 예산 관리 및 추세 분석을 제공합니다.

## 1. 목표
월별 수입/지출 기록, 카테고리별 분석, 예산 초과 알림을 관리합니다.

## 2. 도구
- `execution/finance_db.py` — SQLite CRUD 작업
- `pages/finance_tracker.py` — Streamlit 대시보드

## 3. 카테고리
**수입:** 급여, 부업, 투자수익, 기타수입
**지출:** 식비, 교통, 주거, 통신, 쇼핑, 의료, 교육, 여가, 구독, 기타지출

## 4. 기능
| 기능 | 설명 |
|------|------|
| 거래 추가/삭제 | 수입 또는 지출 기록 |
| 월별 요약 | 수입/지출/순잔액 |
| 카테고리 분석 | 파이 차트로 비중 시각화 |
| 6개월 추세 | 라인 차트로 월별 변화 |
| 예산 설정 | 카테고리별 월 한도 설정 |
| 예산 알림 | 80% 이상 사용 시 경고, 초과 시 에러 |
| CSV 내보내기 | 거래 내역 다운로드 |

## 5. 데이터베이스
- 위치: `.tmp/finance.db`
- 테이블: `transactions`, `budgets`
- 통화: KRW (원화)

## 6. CLI 사용법
```bash
python execution/finance_db.py init
python execution/finance_db.py add --type expense --amount 15000 --category "식비" --desc "점심"
python execution/finance_db.py summary --month 2026-02
python execution/finance_db.py export --format csv
```
