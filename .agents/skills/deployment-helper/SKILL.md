---
name: deployment-helper
description: Firebase/Supabase 배포, DB 검증, 환경 설정 점검이 필요한 작업에 사용.
---

# 🚀 Deployment Helper Skill

> Firebase Hosting + Supabase DB 관리를 통해 웹앱 배포를 자동화합니다

## 목적

hanwoo-dashboard, knowledge-dashboard 등 프로젝트의 빌드/배포/DB 관리를
Antigravity에 내장된 Firebase MCP와 Supabase MCP를 활용하여 자동화합니다.

## 사전 요구사항

- **Firebase MCP** (Antigravity 내장)
- **Supabase MCP** (Antigravity 내장)
- 대상 프로젝트의 빌드 설정 완료

## ⚠️ 주의

> 현재 프로젝트 정책(ADR-002)에 따라 **로컬 전용 프로젝트**입니다.
> 배포는 **사용자 명시적 요청 시에만** 수행합니다.
> 배포 전 반드시 사용자 확인을 받습니다.

## 사용법

### 1. Firebase 프로젝트 상태 확인

```
사용자: Firebase 프로젝트 현황 알려줘
```

**에이전트 동작:**
1. Firebase MCP → `firebase_get_environment()` 호출
2. `firebase_list_projects()` → 프로젝트 목록 조회
3. `firebase_list_apps()` → 등록된 앱 목록
4. 현재 설정 상태 요약

### 2. Supabase DB 스키마 확인

```
사용자: hanwoo-dashboard DB 테이블 확인해줘
```

**에이전트 동작:**
1. Supabase MCP → `list_tables(project_id, schemas=["public"], verbose=True)`
2. 테이블 구조, PK, FK 관계 시각화
3. TypeScript 타입 생성 (`generate_typescript_types`)

### 3. 마이그레이션 적용

```
사용자: hanwoo DB에 새 컬럼 추가해줘
```

**에이전트 동작:**
1. 변경 DDL 작성
2. Supabase MCP → `apply_migration(project_id, name, query)` 실행
3. 보안 어드바이저 실행 → `get_advisors(project_id, "security")`
4. RLS 정책 누락 여부 확인

### 4. Firebase Hosting 배포 (사용자 확인 필수)

```
사용자: knowledge-dashboard Firebase에 배포해줘
```

**에이전트 동작:**
1. ⚠️ 사용자 확인 요청: "Firebase Hosting에 배포하시겠습니까? (ADR-002: 로컬 전용 정책)"
2. 승인 시:
   a. `npm run build` 실행
   b. Firebase MCP → `firebase_init(features: {hosting: {public_directory: "out"}})`
   c. 배포 상태 확인

### 5. Edge Function 배포

```
사용자: Supabase Edge Function 만들어줘
```

**에이전트 동작:**
1. 함수 코드 작성 (Deno TypeScript)
2. Supabase MCP → `deploy_edge_function(project_id, name, files)`
3. JWT 인증 설정 확인

## 사용 가능한 MCP 도구

### Firebase MCP
| 도구 | 설명 |
|------|------|
| `firebase_get_environment` | 환경 설정 확인 |
| `firebase_list_projects` | 프로젝트 목록 |
| `firebase_list_apps` | 앱 목록 |
| `firebase_get_sdk_config` | SDK 설정 |
| `firebase_init` | 서비스 초기화 |
| `firebase_get_security_rules` | 보안 규칙 조회 |

### Supabase MCP
| 도구 | 설명 |
|------|------|
| `list_projects` | 프로젝트 목록 |
| `list_tables` | 테이블 목록/상세 |
| `execute_sql` | SQL 실행 |
| `apply_migration` | DDL 마이그레이션 |
| `deploy_edge_function` | Edge Function 배포 |
| `get_advisors` | 보안/성능 어드바이저 |
| `generate_typescript_types` | TS 타입 생성 |

## 배포 체크리스트

- [ ] 빌드 성공 확인 (`npm run build` exit 0)
- [ ] 환경변수 `.env` 검증 (배포 대상에 민감정보 미포함)
- [ ] 보안 규칙/RLS 검토
- [ ] 사용자 최종 승인
- [ ] 배포 후 헬스체크
