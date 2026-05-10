# Shorts Maker V2

![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)
![Version](https://img.shields.io/badge/version-1.0.0-green.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

**Shorts Maker V2**는 주제만 입력하면 YouTube Shorts 등 세로형 숏폼 영상을 원클릭으로 생성해주는 자동화 CLI 파이프라인입니다.

대본 작성부터 음성(TTS) 생성, 시각 자료(이미지/비디오) 수집 및 합성, 그리고 최종 렌더링까지 전 과정을 AI(OpenAI, Google Gemini 등)와 FFmpeg를 이용해 매끄럽게 처리합니다.

---

## 🚀 주요 기능

- **원클릭 파이프라인**: 텍스트 입력 한 번으로 35~45초 길이의 Shorts 영상 MP4 최종 생성
- **멀티 AI 프로바이더 지원**: OpenAI(GPT-4o, DALL-E, TTS), Google(Gemini, Veo, Imagen), Edge TTS(무료) 등 상황에 맞게 8개 이상의 Provider 혼합 사용
- **자동 폴백(Fallback) 및 복구**: 이미지 생성 API 제한이나 실패 시, 이전 에셋 재사용 또는 다른 Provider로 자동 전환 (안정성 보장)
- **강력한 템플릿 엔진**: 채널 특성에 맞춘 다양한 영상 템플릿(뉴스, 사이버펑크, 퀴즈 등) 및 커스텀 스타일 지원
- **실시간 비용 추적**: 실행 중 실시간으로 API 호출 비용 내역 제공 (`costs` 커맨드 지원)
- **유연한 배치 처리**: 여러 주제를 텍스트 파일이나 DB에서 읽어와 순차적 또는 병렬로 대량 생성

---

## 📦 설치 (Installation)

### 1. 요구 사항 (Prerequisites)
- Python 3.11 이상
- [FFmpeg](https://ffmpeg.org/) 설치 및 PATH 등록
- (권장) 의존성 관리를 위한 `uv` 또는 `pip`

### 2. 저장소 클론 및 패키지 설치
```bash
git clone https://github.com/your-repo/shorts-maker-v2.git
cd shorts-maker-v2

# 패키지 설치 (의존성 자동 설치)
python -m pip install -e .
```

### 3. 환경 변수 설정
설정 파일 복사 후, 사용하실 API 키를 기입합니다.
```bash
copy .env.example .env
```

**.env 파일 예시:**
```env
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=AIza...
PEXELS_API_KEY=...
# 필요한 키만 설정하면 자동 라우팅을 통해 적합한 모델이 선택됩니다.
```

---

## 🎯 사용 방법 (Quick Start)

### 1. 환경 및 설정 점검
우선 환경 변수 및 의존성, 디렉토리 권한이 정상인지 점검합니다.
```bash
python -m shorts_maker_v2 doctor
```

### 2. 단일 영상 생성 (Run)
`--topic` 파라미터에 원하는 주제를 입력하면 영상 생성을 시작합니다.
```bash
python -m shorts_maker_v2 run --topic "블랙홀 미스터리 5가지" --out shorts_output.mp4
```

### 3. 자동 주제 발굴 기능
최신 트렌드나 알고리즘 추천을 바탕으로 주제를 자동 선택하여 영상을 만듭니다.
```bash
# 트렌드에서 1위를 자동 선택
python -m shorts_maker_v2 run --channel ai_tech --auto-topic

# 후보 리스트를 보고 직접 선택 (대화형 모드)
python -m shorts_maker_v2 run --channel ai_tech --auto-topic-list
```

### 4. 대량 영상 생성 (Batch)
텍스트 파일(`topics.txt`)에 주제를 한 줄씩 적고 일괄 생성할 수 있습니다.
```bash
python -m shorts_maker_v2 batch --topics-file topics.txt --limit 5 --parallel
```

### 5. 성과 대시보드 및 비용 조회
생성된 비디오들의 통계와 API 사용 비용을 확인합니다.
```bash
# 대시보드 HTML 생성
python -m shorts_maker_v2 dashboard --out dashboard.html

# 누적 비용 요약
python -m shorts_maker_v2 costs
```

---

## 📁 주요 산출물 경로

영상을 생성하면 다음 디렉토리에 결과물이 저장됩니다:
- `output/` : 최종 MP4 영상과 메타데이터 JSON
- `logs/` : 실행 상세 로그 및 비용 정보 (디버깅용)
- `runs/` : 씬(Scene) 단위로 생성된 중간 이미지, 음성, 메타데이터 캐시

*(참고: 이 세 폴더는 `.gitignore`에 의해 버전 관리에서 제외됩니다)*

---

## 🔧 아키텍처 개요

Shorts Maker V2는 안정성과 확장성을 위해 철저히 분리된 컴포넌트로 구성되어 있습니다:
- **Orchestrator**: 전체 워크플로우를 관장하며 실패 복구와 캐싱을 담당합니다.
- **Providers Layer**: 각 AI API와의 통신을 캡슐화합니다. (LLM Router, Google Client, OpenAI Client 등)
- **Render Engine**: 자막, 효과음, 이미지 전환, 카라오케(글자별 강조) 스타일을 담당합니다. 기본 내장 렌더러와 확장 팩(`ShortsFactory`)을 모두 지원합니다.

더 자세한 설계 내용은 [ARCHITECTURE.md](ARCHITECTURE.md)를 참고해 주세요.

---

## 🧪 테스트 (Testing)

개발 모드용 의존성 설치 후 Pytest를 실행합니다.
```bash
# 개발 의존성 포함 설치
python -m pip install -e ".[dev]"

# 단위/통합 테스트 실행
python -m pytest tests -q
```
