# Suika Daily

매일 **전 세계가 똑같은 퍼즐**에 도전하는 데일리 과일 합치기 게임.

여느 수박 게임과 달리 Suika Daily는 `Math.random()`을 쓰지 않습니다. 그날의
날짜(UTC)에서 시드를 뽑아 **모든 플레이어가 동일한 과일·폭탄 순서**를 받습니다 —
Wordle처럼 매일 한 판, 연속 기록(streak)을 쌓고 스포일러 없는 결과 카드를
공유하세요.

> v2까지는 Matter.js 기반의 평범한 수박 클론이었습니다. v3에서 **결정론적 시드
> 시뮬레이션 · PWA · Web Share**를 도입해 "데일리 챌린지"라는 정체성을 가진
> 완성형 제품으로 재설계했습니다.

## 핵심 특징

- **데일리 챌린지** — UTC 날짜를 시드로 사용. 같은 날 = 같은 퍼즐. (`Daily #N`)
- **결정론적 시뮬레이션** — 시드 기반 PRNG(mulberry32)가 과일 생성·폭탄·회전을
  모두 재현 가능하게 만듭니다. 같은 시드 + 같은 플레이 = 같은 결과.
- **연속 기록(streak)** — 매일 도전하면 streak 증가, 하루 빠지면 1로 리셋.
  `localStorage`에 영구 저장.
- **결과 카드 공유** — Web Share API로 PNG 카드를, 미지원 환경에선 스포일러 없는
  텍스트를 클립보드로. (`src/sharecard.js`)
- **통계 화면** — 현재/최고 연속, 플레이 수, 최고 점수, 최근 7개 기록.
- **프리 플레이** — 매 판 새로운 무작위 시드의 무한 모드.
- **PWA** — 설치 가능, 서비스 워커로 오프라인 플레이.
- **접근성** — `prefers-reduced-motion` 존중(애니메이션·화면 흔들림 비활성화),
  키보드 포커스 관리, 다이얼로그 ARIA 역할.
- 콤보 점수, 난이도 프리셋(Casual/Normal/Hard), no-merge 구제 가중치,
  폭탄, 햅틱 피드백.

### 결정론에 대한 정직한 한계

데일리 시드는 **무작위 결정**(과일 순서, 폭탄, 초기 회전)을 완전히 고정합니다.
물리 엔진(Matter.js)의 부동소수점 적분은 기기마다 미세하게 다를 수 있어, "전
세계가 픽셀 단위로 동일한 결과"를 보장하지는 않습니다. 보장하는 것은 — *같은
시드에서 동일하게 플레이하면 동일한 결과* 라는 공정한 퍼즐 정체성입니다.

## 실행

```bash
npm install      # 의존성 설치
npm run dev      # 개발 서버 (Vite)
npm run build    # 프로덕션 빌드 -> dist/
npm run preview  # 빌드 결과 미리보기
```

## 검증 커맨드

```bash
npm test           # 단위 테스트 (Vitest) — PRNG 결정론 + 데일리 로직
npm run test:coverage
npm run lint       # ESLint
npm run build      # 빌드 (prebuild-check 포함)
```

단위 테스트(61개)는 결정론적 모듈(`prng.js`, `daily.js`, `spawn.js`)을
대상으로 합니다 — 같은 시드가 같은 수열을 내는지, streak 전이, 구제 가중치
계산이 올바른지 등. 물리/렌더/DOM 통합 코드는 브라우저 스모크 테스트로 검증합니다.

## 조작

- 이동: 마우스 / 터치 드래그 / `←` `→`
- 드롭: 마우스 업 / 터치 엔드 / `Space` / `Enter`
- 일시정지: `P` 또는 Pause 버튼
- 게임오버 후 재시작: `R` 또는 다시 도전

## 구조

```
index.html              앱 진입점 (Vite 엔트리)
src/
  main.js               오케스트레이션: 게임 모드, 입력, 상태
  physics.js            Matter.js 물리 (충돌, 병합, 게임오버)
  renderer.js           Canvas 커스텀 렌더링, 파티클
  config.js             과일 데이터, 난이도 프리셋, 상수
  ui.js                 DOM 헬퍼
  prng.js               결정론적 시드 PRNG + 데일리 시드        [tested]
  daily.js              streak/통계/history, 결과 카드 텍스트    [tested]
  spawn.js              과일 생성 가중치 + no-merge 구제 로직    [tested]
  sharecard.js          Canvas 결과 카드 이미지 렌더링
  style.css             스타일
  *.test.js             Vitest 단위 테스트
public/
  manifest.webmanifest  PWA 매니페스트
  sw.js                 서비스 워커 (오프라인 캐시)
  icon.svg              앱 아이콘
scripts/
  prebuild-check.js     빌드 전 비-ASCII 경로 경고
  generate_ppt.js       개요 PPT 생성 (npm run gen:ppt)
```

## 스택

Vanilla JS (ES Modules) · Matter.js 0.20 · Vite 7 · Vitest 4 · ESLint 9 · PWA
