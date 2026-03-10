# 📊 Joolife Knowledge Dashboard (지식 관리)

> **GitHub & NotebookLM Integration Dashboard.**
> © 2026 Joolife (쥬라프). All rights reserved.

🇬🇧 A personalized dashboard that integrates GitHub repositories and NotebookLM notebooks in one place.
🇰🇷 GitHub 리포지토리와 NotebookLM의 노트북을 한곳에서 모아보는 개인화 대시보드입니다.

## 🚀 🇬🇧 Getting Started / 🇰🇷 시작하기

### 1. 🇬🇧 Data Synchronization / 🇰🇷 데이터 동기화
🇬🇧 Run the script below to fetch the latest data from GitHub and NotebookLM.
(Requires NotebookLM security token, so it uses `notebooklm-mcp`'s virtual environment)
🇰🇷 GitHub와 NotebookLM의 최신 데이터를 가져오려면 아래 스크립트를 실행하세요.
(NotebookLM 보안 토큰이 필요하므로, `notebooklm-mcp`의 가상환경을 사용합니다)

```bash
# 🇬🇧 Quick run (Execute batch file in project root) / 🇰🇷 간편 실행 (프로젝트 루트의 배치 파일 실행)
./sync.bat
```

> **🇬🇧 Note / 🇰🇷 참고**: 🇬🇧 This script automatically uses `notebooklm-mcp`'s venv to fetch data securely. / 🇰🇷 이 스크립트는 `notebooklm-mcp`의 가상환경(venv)을 자동으로 사용하여 데이터를 안전하게 가져옵니다.

### 2. 🇬🇧 Run Dashboard / 🇰🇷 대시보드 실행
🇬🇧 Start the web dashboard. / 🇰🇷 웹 대시보드를 실행합니다.

```bash
npm run dev
```
🇬🇧 Access `http://localhost:3000` in your browser! / 🇰🇷 브라우저에서 `http://localhost:3000` 접속!

## 🛠️ 🇬🇧 Tech Stack / 🇰🇷 기술 스택
- **Framework**: Next.js 14
- **Styling**: Tailwind CSS
- **Icons**: Lucide React
- **Data Bridge**: Python script (linking with MCPs)

## 📁 🇬🇧 Folder Structure / 🇰🇷 폴더 구조
- `scripts/`: 🇬🇧 Data sync Python script / 🇰🇷 데이터 동기화 Python 스크립트
- `src/app/`: 🇬🇧 Web page source code / 🇰🇷 웹 페이지 소스 코드
- `public/dashboard_data.json`: 🇬🇧 Synced data file (auto-generated) / 🇰🇷 동기화된 데이터 파일 (자동 생성됨)
- `sync.bat`: 🇬🇧 Quick run data sync script / 🇰🇷 데이터 동기화 간편 실행 스크립트

## ✨ 🇬🇧 Key Features / 🇰🇷 주요 기능
- **🔍 🇬🇧 Smart Search / 🇰🇷 스마트 검색**: 🇬🇧 Real-time filtering by project name, notebook title, language, etc. / 🇰🇷 프로젝트명, 노트북 제목, 언어 등으로 실시간 필터링
- **📊 🇬🇧 Knowledge Status Stats / 🇰🇷 지식 현황 통계**: 🇬🇧 Visualize total integrated assets, language distribution, ref file counts. / 🇰🇷 연동된 총 자산 수, 언어 분포, 참조 파일 수 등을 시각화
- **📝 🇬🇧 Detail View Modal / 🇰🇷 상세 보기 모달**: 🇬🇧 Click notebook cards to view included source files. / 🇰🇷 노트북 카드를 클릭하여 포함된 소스 파일 목록 확인
- **🏷️ 🇬🇧 Auto Tags / 🇰🇷 자동 태그**: 🇬🇧 Keyword-based auto classification ('Research', 'Development', 'Planning'). / 🇰🇷 '연구', '개발', '기획' 등 키워드 기반 자동 분류
- **🌐 🇬🇧 Unified View / 🇰🇷 통합 뷰**: 🇬🇧 Manage GitHub and NotebookLM data in a single screen. / 🇰🇷 GitHub와 NotebookLM 데이터를 한 화면에서 관리
