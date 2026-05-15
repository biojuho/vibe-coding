---
name: error-debugger
description: 파이프라인 에러를 자동 진단, 분류하고 복구 제안과 안전한 자가 수정을 수행할 때 사용.
---

# 🔧 Error Debugger Skill

> 파이프라인 에러를 자동으로 진단하고, 패턴을 분류하며, 복구 방안을 제시합니다

## 목적

blind-to-x 및 shorts-maker-v2 파이프라인에서 발생하는 에러를 자동으로 분석하고,
반복 패턴을 감지하여 자가 복구 또는 수동 개입 요청을 결정합니다.

## 사전 요구사항

- **SQLite Multi-DB MCP** 연결 (debug_history.db 접근)
- **Telegram MCP** 연결 (CRITICAL 알림)
- **System Monitor MCP** 연결 (시스템 상태 확인)

## 사용법

### 1. 최근 에러 진단

```
사용자: 최근 파이프라인 에러 분석해줘
```

**에이전트 동작:**
1. SQLite `debug_history.db`에서 최근 24시간 에러 조회
2. 에러 분류: API 타임아웃 / 셀렉터 실패 / 비용 초과 / 인증 만료 / 네트워크 / 코드 버그
3. `.tmp/failures/` 디렉토리의 스냅샷 분석
4. 에러별 복구 방안 제시

### 2. 반복 에러 감지

```
사용자: 반복되는 에러 패턴 있어?
```

**에이전트 동작:**
1. 최근 7일간 에러 히스토리 분석
2. 동일 에러 3회 이상 반복 패턴 감지
3. 근본 원인(Root Cause) 분석
4. 방지책 제안 (directive 업데이트, 코드 수정 등)

### 3. 실시간 파이프라인 진단

```
사용자: blind-to-x 파이프라인 왜 실패했어?
```

**에이전트 동작:**
1. 최근 실행 로그 확인 (`.tmp/logs/`)
2. exit code 분석 (0=성공, 1=부분실패, 2=전체실패)
3. lock 파일 상태 확인 (`.tmp/.running.lock`)
4. System Monitor MCP로 시스템 리소스 확인 (메모리/디스크 부족 여부)
5. 원인 및 즉시 조치 방안 제시

### 4. 자동 복구 시도

일부 에러 유형은 자동 복구를 시도합니다:

| 에러 유형 | 자동 복구 |
|-----------|-----------|
| Stale lock 파일 | 1시간 초과 시 자동 삭제 |
| API 토큰 갱신 | OAuth refresh 시도 |
| 디스크 부족 | `.tmp/` 내 7일 이상 파일 정리 |
| __pycache__ 충돌 | 캐시 디렉토리 삭제 |

**자동 복구 불가 시:**
- CRITICAL 알림 발송 (Telegram MCP)
- 수동 개입 필요 항목 Notion에 태스크 등록

## 에러 분류 체계

```
📁 에러 카테고리
├── 🌐 NETWORK: 네트워크 연결 실패, DNS 해석 실패
├── ⏰ TIMEOUT: API 응답 타임아웃
├── 🔑 AUTH: 인증 만료, 토큰 갱신 실패, API 키 무효
├── 💰 COST: 일일 예산 초과, rate limit 도달
├── 🎯 SELECTOR: CSS 셀렉터 변경, HTML 구조 변경
├── 🐛 CODE: 코드 버그, import 오류, 타입 에러
├── 💾 RESOURCE: 메모리 부족, 디스크 공간 부족
└── ❓ UNKNOWN: 미분류 에러
```

## 데이터 소스

| 소스 | 용도 |
|------|------|
| `debug_history.db` | 에러 히스토리 조회 |
| `.tmp/failures/` | 에러 스냅샷 파일 |
| `.tmp/logs/` | 실행 로그 |
| `error_analyzer.py` | 기존 에러 분석기 활용 |
| `pipeline_watchdog.py` | 워치독 상태 참조 |

## 주의사항

- **자동 복구는 안전한 작업만 수행합니다** (파일 삭제, 캐시 정리 수준)
- 코드 수정이 필요한 경우 항상 **사용자 확인 후** 진행합니다
- CRITICAL 에러는 즉시 Telegram 알림을 발송합니다
- 에러 분석 결과는 [`directives/`에 학습 내용으로 업데이트](#)를 제안합니다
