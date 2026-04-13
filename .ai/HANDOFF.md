# HANDOFF - AI Context Relay

> See `SESSION_LOG.md` for recent session history and `DECISIONS.md` for stable architecture decisions.

## Latest Update

| Field | Value |
|---|---|
| Date | 2026-04-13 |
| Tool | Gemini (Antigravity) |
| Work | **T-161 QC 완료**: QA 검토에서 critical 버그 발견 — `widgets.js`의 alert 배너 CSS 변수 전환이 dead export에 적용되었고, 실제 운영 파일 `AlertBanners.js`는 하드코딩 상태 유지. `AlertBanners.js`에 CSS 변수 전환 적용, 문자 깨짐(`쨌→·`) 수정, `widgets.js` dead export 89행 + 미사용 import 7개 제거 완료. QC 조건부 승인 (시각 검증 blocked by browser env `0xc0000005`). |
| Next Priorities | 1. `http://localhost:3001`에서 alert 배너/footer 시각 확인 (라이트/다크 모드). 2. 브라우저 자동화 환경 복구 (`0xc0000005` Access Violation). 3. T-161 완전 클로즈 후 다음 태스크 시작. |

## Previous Update

| Field | Value |
|---|---|
| Date | 2026-04-11 |
| Tool | Codex |
| Work | Cleaned up the remaining `blind-to-x` timeout-test worktree diff in `tests/unit/test_process.py` by removing the last unused `asyncio` import, then re-ran the focused process tests plus Ruff. The timeout-targeting edits already present in that file now verify cleanly (`5 passed`), and the `blind-to-x` test trio touched in this session (`test_process.py`, `conftest.py`, `test_notion_query_mixin.py`) is Ruff-clean together. |
| Next Priorities | 1. Leave `hanwoo-dashboard` UX/UI work alone unless the user explicitly redirects the session. 2. If Moonshot or Groq should be re-enabled later, add fresh keys and re-run the shared health check. 3. If Python 3.13 packages are reinstalled on this machine, reapply the local `code-review-graph` UTF-8 patch unless it lands upstream first. |

## Notes

- **T-161 QC 결과 (2026-04-13)**:
  - QA STEP 2에서 FAIL — `DashboardClient.js:32`가 `AlertBanners.js`에서 import하나 CSS 변수 전환은 `widgets.js` dead export에만 적용
  - STEP 3에서 수정: `AlertBanners.js` 전면 재작성, `widgets.js` dead code 제거
  - 커밋: `f2448a4`, `ef02a60`, `46a2349` (3개 T-161 관련)
  - 서버 검증: `200 OK` on `http://localhost:3001`
  - 시각 검증: blocked (`0xc0000005` Playwright)
- The local Python 3.13 `code-review-graph` package on this machine now has an unversioned UTF-8 patch in `site-packages`. If the package is reinstalled or upgraded, the old Windows `cp949` crash can return until the same fix is reapplied upstream.
- `projects/blind-to-x/tests/unit/conftest.py` now clears `NOTION_DATABASE_ID` and any `NOTION_PROP_*` overrides before each unit test.
- UTF-8 markdown files in `.ai/` and `workspace/directives/` are fine on disk; earlier garbling came from the Windows cp949 console path, not file corruption.
- Do not revert unrelated in-progress edits elsewhere in the worktree.
