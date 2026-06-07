# PROJECTS - 프로젝트 중심 대시보드

> 세션 시작 때 빠르게 읽는 프로젝트별 현황판이다. 상세 릴레이는 `HANDOFF.md`,
> 작업 보드는 `TASKS.md`, 고정 아키텍처 결정은 `DECISIONS.md`를 본다.
> 이 파일은 프로젝트 상태가 바뀔 때만 갱신하고, 긴 작업 로그는 넣지 않는다.

| 프로젝트 | 상태 | 경로 | 스택 | 현재 초점 |
|---|---|---|---|---|
| blind-to-x | Active | `projects/blind-to-x` | Python, Notion, Cloudinary | Notion/X reviewer output 품질, weighted length, edit plan |
| shorts-maker-v2 | Active | `projects/shorts-maker-v2`, `workspace/execution/pages/` | Python, MoviePy, Edge TTS, Streamlit | Shorts Manager/Analytics 운영 UI와 최종 업로드 메타데이터 품질 |
| hanwoo-dashboard | Active | `projects/hanwoo-dashboard` | Next.js 16, React 19, Prisma 7, Supabase | 모바일 현장 UX, 접근성, degraded DB 상태에서도 쓸 수 있는 대시보드 |
| knowledge-dashboard | Maintenance | `projects/knowledge-dashboard` | Next.js, TypeScript, Tailwind | 인증된 내부 지식 대시보드 유지보수 |
| workspace automation | Active | `workspace/`, `execution/`, `.agents/skills/` | Python, Streamlit, MCP | QC, readiness, session relay, 로테이션 도구 |
| suika-game-v2 | Frozen | `projects/suika-game-v2` | Vite, Vanilla JS, Matter.js | 보안/의존성 유지보수만 |
| word-chain | Frozen | `projects/word-chain` | React, Vite, Tailwind | 보안/의존성 유지보수만 |
| landing-page | Static | `projects/landing-page` | HTML, CSS, JS | 정적 자산 유지 |

## 공통 릴리스 경계

- 현재 로컬 `main`은 `origin/main`보다 앞서 있다. 명시적 push 승인 전에는 push하지 않는다.
- push 후에는 정확한 current HEAD에서 `root-quality-gate`와 `active-project-matrix`가 통과해야 한다.
- Hanwoo `T-251`은 사용자 소유 Supabase credential reset/live Prisma CRUD E2E blocker다. credential reset 전에는 live check를 재시도하지 않는다.

## 프로젝트별 메모

### blind-to-x

- 목적: Blind/Ppomppu/JobPlanet 등에서 후보 글을 수집해 X/Notion 검토용 초안을 만든다.
- 좋은 output 기준: X weighted length, 출처/선정 이유, reviewer edit plan, copy-ready 여부가 바로 보여야 한다.
- 최근 품질 축: Notion review row에 selection quality, readiness verdict, edit plan을 노출했다.
- 검증 기준: `projects/blind-to-x` unit tests, Ruff, Notion upload focused tests, 필요 시 source browser preflight.

### shorts-maker-v2

- 목적: 5개 채널 YouTube Shorts의 대본, TTS, BGM, 렌더, 업로드 운영을 관리한다.
- 좋은 output 기준: 최종 영상/메타데이터/업로드 카드가 바로 검수와 게시에 쓸 수 있어야 한다.
- 최근 품질 축: Shorts Manager/Analytics의 모바일 터치 타깃, 한국어 라벨, 업로드 메타데이터를 개선했다.
- 검증 기준: project QC, `workspace` Streamlit page tests, browser QA, Ruff.

### hanwoo-dashboard

- 목적: 한우 농장 운영자가 모바일/현장에서 개체, 급이, 번식, 매출, 알림을 관리한다.
- 좋은 output 기준: 작은 화면에서도 주요 액션이 눌리고, degraded Supabase read 상태에서도 운영자가 다음 행동을 알 수 있어야 한다.
- 최근 품질 축: 대시보드/설정/스캐너/AI 위젯의 44px 터치 타깃, tabbar-safe layout, PWA metadata.
- 주의: `T-251`은 외부 Supabase credential reset 전까지 사용자 소유 blocker로 분리한다.
- 검증 기준: Hanwoo source tests, lint, build, smoke, browser-click QA.

### knowledge-dashboard

- 목적: 내부 리포지토리, NotebookLM, QA/QC, readiness 데이터를 인증된 대시보드로 보여준다.
- 좋은 output 기준: 민감 JSON을 `public/`에 노출하지 않고, stale/invalid data를 명확히 표시한다.
- 상태: Maintenance. 새 기능보다 안전한 인증/데이터 경계 유지가 우선이다.
- 검증 기준: npm test, lint, build, smoke.

### workspace automation

- 목적: 여러 AI 도구가 같은 workspace에서 이어 작업할 수 있도록 session relay, QC, readiness, rotator를 제공한다.
- 좋은 output 기준: 세션 시작 때 읽는 문서가 짧고 최신이며, 자동화 결과가 바로 의사결정에 쓸 수 있어야 한다.
- 최근 품질 축: `handoff_rotator.py`가 날짜뿐 아니라 줄 수/개수 상한으로 HANDOFF bloat를 막고, `tasks_done_rotator.py`가 DONE section을 최신 N개로 유지한다.
- 검증 기준: focused workspace pytest, Ruff, `session_orient.py --json`, `product_readiness_score.py --json`.
