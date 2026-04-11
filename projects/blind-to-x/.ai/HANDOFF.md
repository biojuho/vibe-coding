# HANDOFF.md — Blind-to-X AI 릴레이 메모

## 마지막 세션 (2026-04-11 | Antigravity)

| 항목 | 내용 |
|---|---|
| 작업 | Notion API 에러 안정화, 파이프라인 타임아웃 예외처리 픽스, status 쿼리 안정화 |
| 상태 | ✅ 완료 |
| 테스트 | 1481개 유닛 테스트 100% 통과, 커버리지 75.92% (70% 기준 초과) |

### 완료된 변경

- `pipeline/notion/_upload.py`: `NotionUploader._safe_notion_call`을 추가하여 Notion API 429 및 5xx 에러에 대해 지수 백오프로 재시도 수행.
- `pipeline/process.py`: `process_single_post`의 타임아웃 예외(`TimeoutError`) 처리 방식을 보완하고 내포된 `asyncio.wait_for` 상황에서도 안정적으로 에러를 잡도록 수정.
- `tests/unit/test_process.py`: 전체 타임아웃 래핑 도입에 맞추어 mock 로직(`_patched_wait_for`)을 `_call_count`가 아닌 `timeout` 지속시간 파라미터를 기반으로 정상 동작하게 조정함. 
- `pipeline/notion/_query.py`: `get_pages_by_status` 내부에서 필터 구조가 잘못되어 400 에러를 반환할 때 전체 파이프라인이 중단되지 않도록 `try-except` 블록으로 래핑함(`Exception` 처리 후 Warning 로그).
- `tests/unit/test_notion_upload.py`: 다른 테스트에서 `NOTION_DATABASE_ID` 환경 변수 누수 영향을 받지 않도록 `patch.dict(os.environ, clear=True)`를 추가.

- (완료) `pipeline/notion_upload.py`의 `_list_accessible_sources` 및 `pipeline/notion/_query.py`의 `get_recent_pages` 내 `self.client.search` 호출부도 `_safe_notion_call` 래핑 적용 완료
- (완료) `test_quality_improvements.py` 테스트 케이스 검증 결과, 모두 정상 통과됨(FAIL 없음 확인)

### 주의사항

- `pipeline.process.process_single_post`는 `asyncio.wait_for`가 2번 중첩되어 있습니다(전체 timeout + 외부 Fetch timeout). Mock 작성 시 `timeout`의 값(`timeout <= 1` 등)으로 구분해야 안전합니다.
- `pipeline/notion_upload.py` 테스트 시 `os.environ` 누수 여부를 잘 격리해야 합니다.
