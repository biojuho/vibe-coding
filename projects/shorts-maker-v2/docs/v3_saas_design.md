# Shorts Maker v3.0 — Multi-language + SaaS 설계 (탐색 문서)

> **문서 목적**: 현재 v2 아키텍처를 기반으로 v3.0의 다국어 + SaaS 전환 가능성을 탐색하는 설계 문서. 즉시 구현이 아닌 방향성 수립용.

---

## 1. Multi-language 전략

### 1-A. 대본 i18n

| 계층 | 현재 (v2) | v3 제안 |
|------|----------|---------|
| 프롬프트 | 한국어 하드코딩 | `locales/{lang}/prompts.yaml`로 분리 |
| TTS 음성 | `ko-KR-SunHiNeural` | 언어별 Edge TTS 음성 매핑 테이블 |
| 자막 폰트 | `NanumSquareNeo` | Google Noto 계열 범용 폰트 + fallback |

### 1-B. TTS 다국어 매핑

```yaml
# locales/tts_voices.yaml
en-US:
  default: en-US-JennyNeural
  energetic: en-US-AriaNeural
ja-JP:
  default: ja-JP-NanamiNeural
ko-KR:
  default: ko-KR-SunHiNeural
```

### 1-C. 자막 Safe Zone

현재 `shorts-subtitle-safezone` 스킬이 한국어 전용 줄바꿈 규칙 사용. v3에서는:
- 영어: 단어 단위 줄바꿈 (word-wrap)
- 일본어/중국어: 문자 단위 (character-wrap) + 금칙처리
- 한국어: 현재 로직 유지

---

## 2. SaaS 아키텍처

### 2-A. 시스템 구성도

```
[Client: Web UI / API] → [FastAPI Gateway]
                              ↓
                    [Celery + Redis Queue]
                              ↓
                    [Worker: shorts-maker-v3]
                              ↓
                    [S3 Compatible Storage]
                              ↓
                    [Webhook / Dashboard]
```

### 2-B. 핵심 컴포넌트

| 컴포넌트 | 기술 스택 | 역할 |
|---------|----------|------|
| API Gateway | FastAPI | 요청 수신, 인증, 큐 삽입 |
| Auth | Supabase Auth | OAuth2 + JWT, 멀티테넌시 |
| Queue | Celery + Redis | 비동기 렌더링 작업 관리 |
| Worker | shorts-maker-v3 | 실제 영상 생성 (현 pipeline) |
| Storage | S3 / Cloudflare R2 | 결과물 저장 + CDN 배포 |
| DB | Supabase (PostgreSQL) | 사용자, 프로젝트, 렌더링 이력 |

### 2-C. 멀티테넌시 모델

- **Org 기반**: 각 조직이 독립 채널/설정/크레딧 보유
- **데이터 격리**: RLS (Row Level Security) by `org_id`
- **크레딧 시스템**: 렌더링 1회 = N 크레딧 소모 (해상도/길이별 차등)

### 2-D. 과금 모델 (초안)

| 플랜 | 월 크레딧 | 가격 | 특징 |
|------|----------|------|------|
| Free | 5 | $0 | 720p, 워터마크 |
| Pro | 50 | $19 | 1080p, 커스텀 브랜딩 |
| Team | 200 | $49 | 팀 협업, 스케줄러, API |

---

## 3. 마이그레이션 경로

### Phase 1: i18n 분리 (v2.x)
- 프롬프트/음성/폰트를 `locales/`로 추출
- `config.yaml`에 `language: ko-KR` 필드 추가
- 기존 기능 100% 유지

### Phase 2: API 래퍼 (v2.x → v3.0-alpha)
- FastAPI 래퍼로 CLI 파이프라인 포장
- Celery worker로 비동기 실행
- `/api/v1/render` 엔드포인트

### Phase 3: 인증 + 멀티테넌시 (v3.0-beta)
- Supabase Auth 연동
- RLS 기반 데이터 격리
- 크레딧 시스템 구현

### Phase 4: SaaS 출시 (v3.0)
- 과금 연동 (Stripe)
- 대시보드 UI (Next.js)
- 모니터링 (Sentry + Prometheus)

---

## 4. 결정 필요 항목

| # | 항목 | 선택지 | 우선순위 |
|---|------|--------|---------|
| D1 | 첫 지원 언어 | en-US → ja-JP → zh-CN | HIGH |
| D2 | 스토리지 | S3 vs Cloudflare R2 | MEDIUM |
| D3 | 대시보드 프레임워크 | Next.js vs Nuxt vs SvelteKit | LOW |
| D4 | 렌더링 인프라 | 자체 GPU vs Modal.com vs RunPod | HIGH |
