# Sample Cases — Blind-to-X External Review

> 실제 파이프라인 실행 케이스를 익명화한 샘플입니다.  
> 외부 리뷰어가 콘텐츠 생성 품질과 파이프라인 판단 로직을 평가하는 데 사용합니다.

---

## Case A — 공감형 성공 사례

> **파이프라인 verdict:** `approved` / `published`

### Input

- **Source:** blind (익명 직장인 커뮤니티)
- **Feed mode:** trending
- **Title (sanitized):** "연봉 6800에서 5000으로 이직한 사람 있나요?"
- **Raw content summary (sanitized):** 상위권 연봉을 받던 직장인이 워라밸을 이유로 낮은 연봉의 회사로 이직. 댓글에서 "후회 안 하냐"는 질문에 "솔직히 조금은요 ㅋㅋ"라는 원글주 답변. 댓글 반응은 양분 — 공감 vs '돈이 답이다' 진영.
- **Why this looked promising:** 좋아요 247개 / 댓글 89개 / 첫 댓글 반응 속도 빠름. '연봉 + 이직 + 워라밸' 3중 키워드 조합.

### Deterministic Profile

- **topic_cluster:** 이직/연봉
- **hook_type:** 공감형
- **emotion_axis:** 공감+불안
- **audience_fit:** 2030 직장인
- **recommended_draft_type:** empathetic_question
- **scrape_quality_score:** 0.82
- **publishability_score:** 0.78
- **performance_score:** 0.91
- **final_rank_score:** 0.84

### Generated Drafts

- **twitter:**  
  ```
  연봉 1800 깎고 이직한 사람 블라인드에서 찾았는데…
  "솔직히 조금은 후회해요"라는 한 마디가 댓글 난리 ㅋㅋ
  
  여러분은 워라밸 vs 연봉, 어느 쪽이요?
  ```

- **threads:**  
  ```
  연봉 6800 → 5000, 이직 후기 읽었는데 생각보다 솔직했음 ㅋㅋ
  "덜 벌고 덜 힘들면 된다고 생각했는데… 솔직히 가끔은 그 연봉이 그리워요"
  
  댓글 89개가 '공감파' vs '돈이 답파'로 나뉜 거 너무 현실적ㅋㅋ
  여러분은 어느 쪽이에요?
  ```

- **newsletter:**  
  ```
  [이번 주 블라인드 요약] "연봉 1,800 줄이고 이직한 결과는?"
  
  실제 이직자 왈: "후회 조금 해요". 그런데 돌아갈 생각은 없다고.
  이 한 마디가 댓글을 두 진영으로 가른 이유가 뭔지 — 오늘 브리핑에서 풀어봅니다.
  ```

- **image_prompt:**  
  `Pixar-style illustration of a Korean office worker at a crossroads, one path has a large coin stack, the other has a clock showing 5pm and a smiling person. Warm lighting, cinematic composition. No text, no watermark.`

### Post-processing

- **editorial_scores:**  
  `{hook: 8.2, specificity: 7.5, voice: 8.0, engagement: 8.5, readability: 8.1}`
- **editorial_avg_score:** 8.06
- **quality_gate_summary:** passed — 클리셰 0건 / 구체 장면 있음 (연봉 수치) / CTA 포함
- **retry_happened:** No (1st draft 통과)

### Human Judgment

- **final decision:** approved ✅
- **why:** 도입부에서 숫자("1800 깎고")로 즉시 구체화됐고, 원글주 인용("솔직히 조금은 후회")이 공감을 유발하는 훅으로 잘 작동함.
- **what felt strong:** 인용구가 실제 사람 목소리처럼 느껴져 신뢰도 높음. 질문형 CTA가 자연스럽게 토론을 유도함.
- **what felt weak:** threads 버전 마지막 문장("어느 쪽이에요?")이 twitter와 다소 겹침 — 플랫폼별 차별화 필요.

### What you want the reviewer to answer

- **structural question:** 트위터 도입부의 "…"(말줄임표) 사용이 훅 효과를 높이는지, 아니면 낚시성 느낌을 주는지?
- **content-quality question:** 원글주 인용이 실제 글 내용과 tone을 잘 보존했는가? 과장 또는 왜곡은 없는가?

---

## Case B — 품질 게이트 실패 → 재생성 사례

> **파이프라인 verdict:** `retry → approved` / `published`

### Input

- **Source:** blind
- **Feed mode:** category:직장인
- **Title (sanitized):** "신입인데 팀장이 퇴근하기 전에 먼저 퇴근하면 안 된다고 함"
- **Raw content summary (sanitized):** 신입사원이 팀장보다 먼저 퇴근한 날 팀장에게 불려가 "분위기 파악을 하라"는 말을 들음. 댓글에서는 "이직하라" vs "어쩔 수 없다"로 양분. 공감 반응이 많음.
- **Why this looked promising:** 좋아요 312개 / 댓글 143개 / 직장 갑질/문화 키워드 포함.

### Deterministic Profile

- **topic_cluster:** 직장문화/갑질
- **hook_type:** 논쟁형
- **emotion_axis:** 분노+공감
- **audience_fit:** 2030 신입/주니어
- **recommended_draft_type:** controversy_hook
- **scrape_quality_score:** 0.88
- **publishability_score:** 0.81
- **performance_score:** 0.93
- **final_rank_score:** 0.87

### Generated Drafts — 1차 (실패)

> **Quality gate verdict:** FAILED — 클리셰 3건 / 구체 장면 없음 (일반적 서술)

- **twitter (1st attempt):**  
  ```
  직장생활 정말 쉽지 않죠. 신입사원의 퇴근이 팀장 눈치 봐야 하는 문화,
  많은 한국 직장인들이 공감할 것 같아요. 여러분 어떻게 생각하세요?
  ```
  > ❌ 클리셰 감지: "직장생활 정말 쉽지 않죠" / "공감할 것 같아요"  
  > ❌ 구체 장면 없음 (팀장에게 불려갔다는 사건 미포함)  
  > ❌ 훅 강도 미달 — 첫 문장에 숫자/장면/직접 인용 없음  

### Retry Instructions (Auto-generated)

```
다음 항목을 수정하세요:
1. 클리셰 제거: "쉽지 않죠", "공감할 것 같아요" 사용 금지
2. 훅 수정: 첫 문장에 구체 사건 또는 직접 인용을 넣을 것
   - 예시: 팀장 발언 직접 인용, 또는 "퇴근하다 팀장에게 불려갔다"는 장면
3. 감정 톤: 분노/논쟁형으로 리포커스할 것
```

### Generated Drafts — 2차 (성공)

- **twitter (2nd attempt):**  
  ```
  신입이 팀장보다 먼저 퇴근하자 "분위기 파악 좀 하세요"
  
  받은 것도 없는데 눈치까지 봐야 하냐고 블라인드에서 난리 ㅋㅋ
  댓글 143개 중 절반이 "이직해"인 거 레전드
  ```

- **threads:**  
  ```
  "팀장보다 먼저 퇴근하면 안 된다"는 말 실화임?
  
  신입한테 "분위기 파악하라"고 했다는데 — 댓글 반응이 이직 권유 파티 ㅋㅋ
  
  2026년에도 이런 직장 문화가 있다는 게 더 슬픔...
  여러분 팀은 어떤가요?
  ```

- **newsletter:**  
  ```
  [직장 갑질 레이더] 신입의 조기 퇴근 → 팀장 호출 → 블라인드 폭발
  
  이번 주 가장 뜨거웠던 글. "분위기 파악" 한 마디가 댓글 143개를 만들었습니다.
  왜 이 말이 이렇게 쌓이는지, 실제 제보를 바탕으로 풀어봅니다.
  ```

- **image_prompt:**  
  `Pixar-style illustration of a young Korean office worker looking at the clock showing 6pm, while a suit-wearing manager watches disapprovingly. Tense office atmosphere with fluorescent lighting. No text, no watermark.`

### Post-processing

- **editorial_scores:**  
  `{hook: 9.0, specificity: 8.5, voice: 8.2, engagement: 9.1, readability: 8.3}`
- **editorial_avg_score:** 8.62
- **quality_gate_summary:** passed — 클리셰 0건 / 구체 장면 있음 (팀장 발언 인용) / 댓글 수 구체 수치 사용 / CTA 포함
- **retry_happened:** Yes (1회 재생성 후 통과)

### Human Judgment

- **final decision:** approved ✅
- **why:** 2차 draft는 "분위기 파악 좀 하세요"라는 팀장 발언 직접 인용으로 훅이 훨씬 강해졌고, "댓글 143개 중 절반이 이직해"라는 구체 수치가 사실 기반 신뢰도를 높임.
- **what felt strong:** 인용구 + 구체 수치 조합이 논쟁형 훅의 정석. 재생성 지침이 명확해서 2차 draft가 1차보다 확연히 개선됨.
- **what felt weak:** newsletter 버전이 트위터/threads 대비 다소 관찰자적 어조라 직장인 공감을 덜 끌 수 있음.

### What you want the reviewer to answer

- **structural question:** 1차 → 2차 재생성에서 품질 게이트 기준(클리셰 3건, 훅 강도 미달)이 적절했는가? 너무 엄격하거나 너무 관대한 부분은?
- **content-quality question:** "댓글 143개 중 절반이 이직해"라는 표현이 원문 데이터(댓글 반응 패턴)에서 과도하게 추론된 것은 아닌가? 팩트 경계선이 적절한지 평가해주세요.

---

## 리뷰어 주의사항

1. 위 케이스는 **실제 블라인드 원글을 익명화·추상화**한 것입니다. 원문 텍스트는 포함하지 않습니다.
2. 생성된 draft의 연봉 수치·댓글 수는 **원글 기준으로 정규화**된 값입니다.
3. Human Judgment 섹션의 "final decision"은 **파이프라인 자동화 결과가 아닌** 사람이 최종 확인한 판단입니다.
