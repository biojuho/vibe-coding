# Shorts Maker V2 — v3.0 다국어 + SaaS 전환 로드맵

> 작성: 2026-03-17 | 상태: 탐색적 (Exploratory)

---

## 비전

단일 언어(한국어) 로컬 파이프라인에서 **다국어 멀티 채널 SaaS 플랫폼**으로 전환.

---

## Phase A: 다국어 확장 (3~4주)

### A-1. 번역 파이프라인
- LLM 기반 대본 번역 (ko → en/ja)
- 문화적 맥락 적응: 한국 밈/유머 → 타겟 문화 적합화
- 번역 품질 검증: back-translation + 유사도 점수 ≥ 0.85

### A-2. 다국어 TTS
- Edge TTS 다국어 음성 풀 활용 (en-US, ja-JP)
- 언어별 prosody 최적화 (발화 속도, 강조 패턴)
- 자막 언어 자동 전환

### A-3. 멀티 채널 배포
- 동일 토픽 → 3개 언어 버전 동시 생성
- 채널별 독립 성과 추적 (channel_growth_tracker 확장)
- 언어별 RPM 차이 반영한 ROI 분석

### 기술 스택
| 컴포넌트 | 기술 |
|----------|------|
| 번역 | Gemini 2.5 Flash / GPT-4o-mini |
| TTS | Edge TTS (무료) |
| 자막 | 기존 카라오케 엔진 + 언어별 폰트 |
| 검증 | Sentence-BERT 유사도 |

---

## Phase B: SaaS 전환 (6~8주)

### B-1. 사용자 인증
- Supabase Auth (Google/GitHub OAuth)
- 역할: Free / Pro / Enterprise
- API Key 관리 (사용자별 LLM key)

### B-2. 멀티 테넌시
- 사용자별 설정 격리 (config per tenant)
- 채널 프로필 · 브랜딩 커스터마이징
- 사용량 제한 (Free: 5건/일, Pro: 50건/일)

### B-3. 결제 시스템
- Stripe 연동 (구독 기반)
- Tier별 기능 Gate:

| 기능 | Free | Pro ($19/m) | Enterprise ($99/m) |
|------|------|-------------|---------------------|
| 월 생성 수 | 30 | 300 | 무제한 |
| 다국어 | ❌ | 2개 | 5개+ |
| 시리즈 엔진 | ❌ | ✅ | ✅ |
| ROI 대시보드 | 기본 | 전체 | 전체 + API |
| ShortsFactory 템플릿 | 기본 3개 | 전체 | 커스텀 |

### B-4. Web Dashboard
- Next.js 14 + Supabase
- 실시간 파이프라인 상태 (WebSocket)
- 드래그앤드롭 씬 편집기

---

## Phase C: 클라우드 마이그레이션 (4~6주)

### C-1. 렌더링 서버
- GPU 인스턴스 (GCP L4/T4) for MoviePy 렌더링
- Cloud Run Jobs for batch processing
- CDN 배포 (Cloud Storage + CloudFront)

### C-2. 비용 추정
| 항목 | 예상 월 비용 |
|------|-------------|
| GPU 렌더링 (on-demand) | $50~150 |
| Supabase Pro | $25 |
| Stripe 수수료 | 2.9% + 30¢/건 |
| CDN/Storage | $10~30 |
| **합계** | **~$115~235/m** |

### C-3. 손익분기점
- Pro 구독 7~13명 확보 시 인프라 비용 커버
- Enterprise 2명 확보 시 수익 구간 진입

---

## 마일스톤

| 마일스톤 | 예상 일정 | 전제조건 |
|----------|-----------|----------|
| A 완료 (다국어 MVP) | +4주 | Phase 4 완료, Gemini API 다국어 검증 |
| B 완료 (SaaS MVP) | +10주 | Phase A 완료, Supabase 프로젝트 설정 |
| C 완료 (클라우드 배포) | +14주 | Phase B 완료, GCP 계정 설정 |
| 퍼블릭 런칭 | +16주 | 베타 테스트 완료, 문서화 |

---

## 리스크

| 리스크 | 영향 | 완화 |
|--------|------|------|
| 번역 품질 | 시청자 이탈 | back-translation 검증 + 수동 리뷰 |
| GPU 비용 | 수익성 악화 | on-demand + spot instance |
| X API 제한 강화 | 성과 추적 불가 | YouTube 중심 전략으로 피벗 |
| 경쟁 SaaS 출현 | 시장 점유율 | 5채널 자동화 노하우 차별화 |

---

*이 로드맵은 Phase 4 완료 후 구체적 일정과 기술 선택을 확정합니다.*
