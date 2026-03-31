# Local-First SaaS 하이브리드 아키텍처 설계

> ADR-013 상세 설계 | 작성: 2026-03-22

---

## 1. 핵심 원칙

| 원칙 | 설명 |
|------|------|
| **Keys Stay Local** | API 키, .env, credentials.json은 절대 원격에 올라가지 않음 |
| **Compute Stays Local** | 렌더링, 스크래핑, LLM 호출은 로컬 워커에서 실행 |
| **Web Is a Shell** | 웹 UI는 상태 조회 + 작업 트리거만 담당 (비즈니스 로직 없음) |
| **Adapter Boundary** | 로컬/원격 전환은 Adapter 인터페이스 교체로만 발생 |

---

## 2. 배포 토폴로지

```
[사용자 브라우저]
      │
      ▼
┌─────────────────────────┐
│  Web Shell (Vercel)     │  ← Next.js SSR, Supabase Auth
│  - 대시보드 UI          │
│  - 사용자/구독 관리      │
│  - 작업 트리거 API       │
└──────────┬──────────────┘
           │ HTTPS (인증된 Webhook)
           ▼
┌─────────────────────────┐
│  Tunnel / Bridge        │  ← Cloudflare Tunnel 또는 n8n Webhook
│  (로컬 → 인터넷 연결)    │
└──────────┬──────────────┘
           │ localhost only
           ▼
┌─────────────────────────┐
│  Local Worker           │  ← 현재 시스템 그대로
│  - scheduler_engine.py  │
│  - shorts-maker-v2      │
│  - blind-to-x           │
│  - .env, API keys       │
│  - SQLite DBs           │
└─────────────────────────┘
```

### 연동 방식 비교

| 방식 | 장점 | 단점 | 추천 |
|------|------|------|------|
| **Cloudflare Tunnel** | 무료, 안정적, zero-trust | 데몬 필요 | 프로덕션 |
| **n8n Webhook** | 이미 구축됨, 유연 | n8n 의존 | 즉시 가용 |
| **Tailscale Funnel** | P2P, 낮은 레이턴시 | 대역폭 제한 | 소규모 |

**권장**: Phase B 초기에는 기존 n8n Webhook 활용, 프로덕션 전환 시 Cloudflare Tunnel로 이관.

---

## 3. Adapter 인터페이스

3계층 아키텍처(ADR-001) 위에 Adapter 레이어를 추가하여, 로컬 구현과 SaaS 구현을 교체 가능하게 만듦.

### 3.1 StorageAdapter

```python
from abc import ABC, abstractmethod
from typing import Any

class StorageAdapter(ABC):
    """결과물 저장소 추상화."""

    @abstractmethod
    def save_result(self, key: str, data: bytes, metadata: dict) -> str:
        """결과 저장. 반환: 접근 가능한 URL 또는 경로."""

    @abstractmethod
    def get_result(self, key: str) -> bytes | None:
        """결과 조회."""

    @abstractmethod
    def list_results(self, prefix: str = "", limit: int = 100) -> list[dict]:
        """결과 목록."""

# 로컬 구현: .tmp/ 폴더 + Cloudinary CDN (현재)
# SaaS 구현: Supabase Storage 또는 GCS
```

### 3.2 SchedulerAdapter

```python
class SchedulerAdapter(ABC):
    """작업 스케줄링 추상화."""

    @abstractmethod
    def schedule_job(self, job_id: str, command: str, cron: str) -> bool:
        """크론 작업 등록."""

    @abstractmethod
    def cancel_job(self, job_id: str) -> bool:
        """작업 취소."""

    @abstractmethod
    def list_jobs(self) -> list[dict]:
        """등록된 작업 목록."""

    @abstractmethod
    def get_job_status(self, job_id: str) -> dict:
        """작업 상태 조회."""

# 로컬 구현: Windows Task Scheduler (현재 scheduler_engine.py)
# SaaS 구현: Supabase Edge Functions + pg_cron 또는 Cloud Run Jobs
```

### 3.3 NotifierAdapter

```python
class NotifierAdapter(ABC):
    """알림 추상화."""

    @abstractmethod
    def send_alert(self, severity: str, title: str, body: str) -> bool:
        """알림 전송. severity: P1/P2/P3."""

    @abstractmethod
    def send_digest(self, items: list[dict]) -> bool:
        """일일 다이제스트 전송."""

# 로컬 구현: Telegram Bot (현재 telegram_notifier.py)
# SaaS 구현: 이메일 (Resend) + 인앱 알림 (Supabase Realtime)
```

### 3.4 AuthAdapter (SaaS 전용)

```python
class AuthAdapter(ABC):
    """사용자 인증 추상화. SaaS 모드에서만 활성."""

    @abstractmethod
    def verify_token(self, token: str) -> dict | None:
        """JWT 검증. 반환: user_id, role, tenant_id."""

    @abstractmethod
    def check_quota(self, tenant_id: str, action: str) -> bool:
        """사용량 한도 확인."""

# SaaS 구현: Supabase Auth + RLS
# 로컬 구현: 항상 True 반환하는 NoOpAuth
```

---

## 4. 구현 로드맵 (roadmap_v3.md 수정안)

### Phase B 수정: Local-First SaaS MVP

| 단계 | 내용 | ADR-002 준수 |
|------|------|-------------|
| B-0 | Adapter 인터페이스 정의 + 로컬 구현체 | 기존 코드 래핑만 |
| B-1 | Web Shell (Next.js + Supabase Auth) | 읽기 전용 뷰만 |
| B-2 | n8n Webhook → Web Shell 연동 | 인증된 트리거만 |
| B-3 | Stripe 결제 + 쿼터 관리 | Web Shell 내부 |
| B-4 | Cloudflare Tunnel 전환 | 로컬 워커 노출 최소화 |

### Phase C 수정: 선택적 클라우드 오프로드

| 단계 | 내용 | 조건 |
|------|------|------|
| C-1 | GPU 렌더링 오프로드 (Cloud Run Jobs) | Pro/Enterprise 사용자 전용 |
| C-2 | SaaS 사용자용 API 키 관리 | 사용자 자체 키 입력 방식 |
| C-3 | CDN 배포 자동화 | Cloudinary → GCS 전환 |

**핵심 변경**: 클라우드는 "필수"가 아닌 "선택적 확장". 로컬 워커만으로도 완전 운영 가능한 상태 유지.

---

## 5. 보안 경계

```
┌────────────────────────────────────────┐
│  Trust Boundary                        │
│  ┌──────────────────────────────────┐  │
│  │  로컬 워커 (신뢰 영역)           │  │
│  │  - .env.llm / .env.social        │  │
│  │  - SQLite DBs                    │  │
│  │  - credentials.json              │  │
│  └──────────────────────────────────┘  │
│            ▲ Tunnel (인증 필수)         │
│  ┌──────────────────────────────────┐  │
│  │  Web Shell (DMZ)                 │  │
│  │  - Supabase RLS                  │  │
│  │  - Rate limiting                 │  │
│  │  - 작업 트리거만 (실행 불가)      │  │
│  └──────────────────────────────────┘  │
└────────────────────────────────────────┘
```

**규칙**:
- Web Shell → 로컬 워커: 작업 ID + 파라미터만 전달 (명령어 주입 불가)
- 로컬 워커 → Web Shell: 결과 상태 + 공개 가능한 메타데이터만 반환
- API 키는 절대 Tunnel을 통과하지 않음
- SaaS 사용자는 자신의 API 키를 Supabase Vault에 저장 (로컬 워커 불사용)

---

## 6. 마이그레이션 체크리스트

- [ ] `execution/adapters/` 폴더 생성
- [ ] `StorageAdapter` + `LocalStorageAdapter` 구현
- [ ] `SchedulerAdapter` + `LocalSchedulerAdapter` 구현
- [ ] `NotifierAdapter` + `TelegramNotifierAdapter` 구현
- [ ] 기존 직접 호출을 Adapter 경유로 점진 전환
- [ ] n8n Webhook에 JWT 인증 추가
- [ ] Web Shell 프로토타입 (Vercel 배포)
- [ ] Cloudflare Tunnel PoC
- [ ] ADR-002 범위 재해석 공식화 (이 문서로 완료)
