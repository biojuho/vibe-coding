# TASKS - AI 도구 칸반 보드

> 각 도구는 세션 시작 시 이 파일을 읽고, 작업 완료 시 상태를 업데이트합니다.
> 담당 도구가 지정된 태스크는 해당 도구가 우선 처리합니다.

## TODO

| ID | 태스크 | 담당 도구 | 우선순위 | 생성일 |
|----|--------|-----------|----------|--------|
| T-016 | blind-to-x 전체 `--review-only` 배치 스모크 실행 (LLM/이미지 비용 전 사용자 승인 필요) | any | MEDIUM | 2026-03-23 |
| T-019 | blind-to-x Ruff 레거시 이슈 28건 정리 (E402/F401/E741 등) | any | LOW | 2026-03-23 |

## IN_PROGRESS

| ID | 태스크 | 담당 도구 | 시작일 | 메모 |
|----|--------|-----------|--------|------|
| T-004 | blind-to-x 스케줄러 자동 실행 모니터링 | Gemini | 2026-03-23 | S4U 전환 후 1주간 관찰 |

## DONE (최근 5건)

| ID | 태스크 | 완료 도구 | 완료일 |
|----|--------|-----------|--------|
| T-018 | blind-to-x coverage 전체 재측정 (533 passed, QA/QC ✅ 승인) | Gemini | 2026-03-23 |
| T-017 | blind-to-x Notion 검토 큐의 기존 부적절/레거시 항목 점검 및 정리 | Codex | 2026-03-23 |
| T-014 | 서브프로젝트 coverage uplift (thumbnail_step 신규, llm_router 수정, notion_upload 99%) | Claude Code | 2026-03-23 |
| T-015 | blind-to-x 라이브 URL 필터 검증 + Windows curl_cffi 직접 폴백 복구 | Codex | 2026-03-23 |
| T-003 | shorts-maker-v2 v3.0 Multi-language + SaaS 전환 설계 | Gemini | 2026-03-23 |

## 규칙

- ID는 `T-XXX` 형식으로 순번 증가
- 담당 도구: `Claude` / `Codex` / `Gemini` / `any` (누구든 가능)
- 우선순위: `CRITICAL` > `HIGH` > `MEDIUM` > `LOW`
- DONE은 최근 5건만 유지, 오래된 것은 삭제
- 태스크를 시작하면 TODO → IN_PROGRESS로 이동하고 시작일 기입
- 완료하면 IN_PROGRESS → DONE으로 이동하고 완료일 기입
- 새 태스크 발견 시 TODO에 추가 (다음 도구가 판단)
