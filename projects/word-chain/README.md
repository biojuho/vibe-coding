# 🎮 Word Chain (AI 끝말잇기) - Web Edition

> **React와 Vite로 구현된 사이버펑크 스타일의 끝말잇기 웹 게임입니다.**
> © 2026 Joolife (쥬라프). All rights reserved.

이 프로젝트는 기존 Pygame 버전의 Word Chain 게임을 브라우저 환경(React + Tailwind CSS)으로 포팅하고 고도화한 풀스택 미니게임입니다.

## ✨ 🇬🇧 Key Features / 🇰🇷 주요 기능
*   **🤖 🇬🇧 AI Opponent / 🇰🇷 AI 상대**: 🇬🇧 룰 기반의 로컬 AI 액션 시뮬레이션. / 🇰🇷 로컬 단어 풀을 이용한 끝말잇기 AI 대결.
*   **🎨 🇬🇧 Cyberpunk UI / 🇰🇷 사이버펑크 UI**:
    *   **🇬🇧 Neon Aesthetics / 🇰🇷 네온 테마**: 🇬🇧 동적인 글리치(Glitch) 효과와 핑크/블루 네온 테마 지원. / 🇰🇷 동적인 네온 효과와 Tailwind 기반의 반응형 레이아웃.
    *   **🇬🇧 Framer Motion / 🇰🇷 프레이머 모션**: 🇬🇧 Smooth animations. / 🇰🇷 채팅 및 UI 전환을 위한 부드러운 애니메이션 탑재.
*   **🔥 🇬🇧 Gameplay / 🇰🇷 게임 플레이**:
    *   **🇬🇧 Timer System / 🇰🇷 타이머 압박**: 🇬🇧 10초 제한 타이머 바. / 🇰🇷 10초 제한의 극적인 타이머 시스템(초읽기 시 붉은색 경고).
    *   **🇬🇧 History & LocalStorage / 🇰🇷 히스토리 및 저장**: 🇬🇧 High Score saving. / 🇰🇷 로컬 스토리지를 이용한 최고 점수(High score) 저장 기능.

## 🚀 🇬🇧 Getting Started / 🇰🇷 시작하기

### 🇬🇧 Prerequisites / 🇰🇷 필수 조건
*   Node.js 18+
*   npm (or yarn/pnpm)

### 🇬🇧 Installation / 🇰🇷 설치
```bash
# 의존성 패키지를 설치합니다.
npm install
```

### 🇬🇧 Development & Build / 🇰🇷 실행 및 빌드
```bash
# 로컬 개발 서버(HMR 지원)를 실행합니다.
npm run dev

# 프로덕션용 소스를 빌드합니다. (dist/ 폴더 생성)
npm run build
```

## ⚠️ Known Issue (Windows Path) / 알려진 문제 (윈도우 경로)
일부 Windows 환경에서는 프로젝트 경로에 영문/숫자 외의 문자(한글 등)가 포함되어 있을 때 `vite build`가 충돌할 수 있습니다. 
만약 에러가 발생한다면, 소스코드를 영문 경로(예: `C:\temp\word-chain`)로 복사한 뒤 빌드해주세요.

## 📄 🇬🇧 License / 🇰🇷 라이선스
이 프로젝트는 Joolife 자체 라이선스 조항을 따릅니다. 무단 복제 및 배포를 금합니다.
