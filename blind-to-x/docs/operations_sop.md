# 🔧 Blind-to-X 운영 SOP 매뉴얼

> 비개발자를 위한 파이프라인 운영 가이드

## 1. 일일 운영 체크리스트

### 아침 (09:00)

1. **Notion DB 확인**: `📋 발행 워크플로우` Board 뷰 열기
2. **신규 콘텐츠 확인**: `검토필요` 컬럼의 카드 수 확인
3. **에러 확인**: 터미널에서 실행 로그 확인

```powershell
cd blind-to-x
type logs\pipeline.log | Select-String "ERROR" | Select-Object -Last 10
```

### 콘텐츠 리뷰 (10:00 ~ 11:00)

1. Board 뷰에서 `검토필요` 카드 클릭
2. 트윗 본문 / Threads 본문 품질 확인
3. 승인 시: `승인 상태` → `승인됨`으로 변경
4. 반려 시: `승인 상태` → `반려`로 변경 (사유 코멘트)

### 발행 (11:00 ~ 12:00)

1. `🎴 X 트윗 큐` Gallery 뷰 열기
2. 승인된 카드의 `트윗 본문` 복사
3. X (twitter.com)에 붙여넣기 → 발행
4. 발행된 URL을 `트윗 링크` 속성에 기록
5. `승인 상태` → `발행완료`로 변경
6. 필요 시 `🧵 Threads 큐`에서 동일 작업 반복

---

## 2. 파이프라인 실행

### 수동 실행 (필요 시)

```powershell
cd blind-to-x
python main.py --dry-run          # 테스트 모드 (Notion 업로드 없이)
python main.py                     # 실제 실행
python main.py --topic "연봉"      # 특정 토픽만 실행
```

### 자동 실행 (크론)

- 크론 스케줄: 매일 08:00 KST
- 설정 파일: `config.yaml` > `newsletter.schedule`

### 실행 결과 확인

```powershell
type logs\pipeline.log | Select-Object -Last 30
```

---

## 3. A/B 테스트 위너 선택

### 자동 판정

- 파이프라인이 14일간의 성과 데이터를 분석하여 자동으로 위너 판정
- 결과: `data/tuned_image_styles.json`에 저장

### 수동 오버라이드

1. Notion DB에서 해당 콘텐츠 페이지 열기
2. `A/B 위너` select 속성에서 원하는 드래프트 타입 선택
   - 공감형 / 논쟁형 / 정보전달형 / 유머형 / 스토리형
3. 다음 파이프라인 실행 시 수동 선택이 자동 판정보다 우선 적용됨

---

## 4. 장애 대응

### 증상별 대응

| 증상 | 가능한 원인 | 대응 |
|------|------------|------|
| 파이프라인 중단 | API 키 만료 | `.env` 파일에서 키 확인 |
| Notion 업로드 실패 | Notion API 한도 초과 | 30분 후 재시도 |
| 스크래핑 실패 | 사이트 차단 | 1시간 후 재시도 |
| 이미지 생성 실패 | API 쿼터 초과 | 다음 날 재시도 (자동 Fallback 있음) |
| 빈 트윗 본문 | LLM 응답 오류 | `--dry-run`으로 재실행 |

### 로그 확인 방법

```powershell
# 마지막 에러 확인
type logs\pipeline.log | Select-String "ERROR" | Select-Object -Last 5

# 특정 날짜 로그
type logs\pipeline.log | Select-String "2026-03-09"
```

### 긴급 연락

- 개발팀 채널에 에러 로그 공유
- `.env` 파일이나 API 키를 절대 공유하지 않도록 주의

---

## 5. 비용 모니터링

### 일일 예산 목표

| 서비스 | 일일 예산 | 확인 방법 |
|--------|----------|-----------|
| Gemini API | $1.00 | Google AI Studio 대시보드 |
| Pollinations | 무료 | N/A |
| DALL-E (Fallback) | $0.50 | OpenAI 대시보드 |
| Notion API | 무료 | N/A |

### 비용 초과 시

1. `config.yaml` > `llm.daily_budget_usd` 확인
2. 초과 시 파이프라인이 자동 중단됨
3. 다음 날 자동 재개

---

## 6. Notion 뷰 활용

자세한 뷰 설정 방법은 `docs/notion_view_setup_guide.md`를 참조하세요.

| 뷰 | 용도 | 주 사용 시점 |
|----|------|-------------|
| 📊 전체 파이프라인 | 전체 데이터 관리 | 디버깅, 일괄 수정 |
| 📋 발행 워크플로우 | 상태 관리 (Kanban) | 아침 체크 |
| 🎴 X 트윗 큐 | 트윗 복사/발행 | 발행 시 |
| 🧵 Threads 큐 | Threads 복사/발행 | 발행 시 |
| 🗓️ 콘텐츠 캘린더 | 일정 조율 | 주간 계획 |
