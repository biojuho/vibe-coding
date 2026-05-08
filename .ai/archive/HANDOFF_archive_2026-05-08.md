## Rotation 2026-05-08 (archived addenda older than 2026-05-01)

| Field | Value |
|---|---|
| Date | 2026-04-30 |
| Tool | Gemini (Antigravity) |
| Work | **Workspace cleanup completed**: (1) Merged Dependabot PRs #28 (actions/setup-node 4→6) and #29 (dependabot/fetch-metadata 2→3) — both CI all-green, squash-merged. (2) Synced local `main` with origin — resolved 5 ahead commits by `git reset --hard origin/main` since all feature changes were already in origin via PR #30 squash merge. (3) Confirmed 0 open PRs remain. (4) Branch protection verified working: required review + required status checks (`root-quality-gate`, `test-summary`) enforced. (5) TASKS.md updated: T-232→DONE, T-233 created for Dependabot merge. |
| Next Priorities | 1. T-231 (User): Decide whether to install Playwright browser binaries for `blind-to-x` or continue with HTML-only fallback. 2. No active TODO items requiring immediate AI work — workspace is clean. |

| Field | Value |
|---|---|
| Date | 2026-04-21 |
| Tool | Codex |
| Work | **`blind-to-x` reliability pass completed locally**: investigated the user's report that Blind collection/output quality had degraded. Recent scheduler logs showed the immediate runtime failure was missing Playwright browser binaries, and historical generation logs showed brittle draft parsing plus a broken retry path. Added `BrowserUnavailableError` handling in `projects/blind-to-x/scrapers/base.py` and HTML-only fallbacks in `scrapers/blind.py` so feed collection and post extraction can still proceed when Chromium/Camoufox is unavailable. Hardened `pipeline/draft_validation.py` to accept JSON/plaintext drift, preserve single-platform outputs, and allow partial draft bundles in review-only mode; restored retry generation by implementing `TweetDraftGenerator._call_llm_with_fallback()` and wiring the platform-specific retry call in `pipeline/draft_validator.py`; passed `allow_partial=review_only` through `pipeline/process_stages/generate_review_stage.py`. Added focused unit coverage for the browser-unavailable and flexible-output paths. Verification passed with `python -m ruff check ...`, `python -m py_compile ...`, and a direct smoke script covering JSON parsing, partial outputs, retry fallback, and Blind HTML-only scraping. Focused `python -m pytest --no-cov tests/unit/test_scrapers_blind.py tests/unit/test_draft_generator_multi_provider.py -q` remained blocked in this environment by temp-dir permission failures (`%LOCALAPPDATA%\\Temp\\pytest-of-user` and project-local `.tmp/pytest-temp`). |
| Next Priorities | 1. If full browser behavior/screenshots are required again, provision the missing Playwright browser binaries for `projects/blind-to-x` (`playwright install` or equivalent). 2. Fix the local Windows pytest temp-dir permission issue before relying on full in-environment pytest verification for `blind-to-x`. |

| Field | Value |
|---|---|
| Date | 2026-04-18 |
| Tool | Codex |
| Work | **Local CI stabilization committed on `main`**: `python3.13 -m code_review_graph status` still reports an empty graph (`Nodes: 0`, `Edges: 0`, `Files: 0`, `Last updated: never`), so this session stayed on direct file inspection. Pulled the failed GitHub Actions logs that were originally attached to PR `#27`, then fixed the corresponding local issues: `blind-to-x` scraper parse handling/tests, `shorts-maker-v2` dependency/test-path verification, and `hanwoo-dashboard`'s missing `@google/generative-ai` dependency. Verification passed with `python -m pytest tests/unit -q --tb=short --maxfail=1 -o addopts=` in `projects/blind-to-x` (`1527 passed, 1 skipped`), `python -m pytest tests/unit tests/integration -q --tb=short --maxfail=1 -o addopts=` in `projects/shorts-maker-v2` (`1300 passed, 12 skipped`), and `npm run build`, `npm run lint`, `node scripts/smoke.mjs` in `projects/hanwoo-dashboard` (all exit `0`). Feature commit: `7c56a15` (`fix(ci): stabilize project test and build expectations`). PR `#27` is now `CLOSED` / unmerged (`closedAt: 2026-04-17T23:33:00Z`), and `git ls-remote --heads origin fix/pr25-post-merge-stabilization` returns no branch head. No push was performed. |
| Next Priorities | 1. User decision: either push local `main` (`7c56a15`, plus the latest `[ai-context]` commit) or create/open a new PR, because PR `#27` is closed and its head branch is gone on the remote. 2. Rebuild/reindex `code-review-graph` before relying on graph-first exploration again. |

| Field | Value |
|---|---|
| Date | 2026-04-17 |
| Tool | Codex |
| Work | **T-215 decision recorded**: revalidated the public-readiness path before any visibility change. `python execution/remote_branch_cleanup.py --repo biojuho/vibe-coding --local-repo .tmp/public-history-rewrite` still reports 3 remote-only branches, all blocked by open dependabot PRs `#1`, `#2`, `#3`. `python execution/github_branch_protection.py --check-live` still returns `status: blocked` because `biojuho/vibe-coding` is `PRIVATE` on GitHub Free. Decision: if the repository is ever made public, it must use the rewritten history from `.tmp/public-history-rewrite`; do not expose the current unre-written history. |
| Next Priorities | 1. T-223 (User): resolve or close dependabot PRs `#1`, `#2`, `#3`, then approve the destructive rewritten-history push / visibility flip from `.tmp/public-history-rewrite`. 2. T-199 (User): once the repo is public or GitHub Pro is enabled, run `python execution/github_branch_protection.py --apply` and `--check-live`. |

| Field | Value |
|---|---|
| Date | 2026-04-17 |
| Tool | Gemini (Antigravity) |
| Work | **T-222 완료**: `hanwoo-dashboard` 프론트엔드 모듈화 및 폴리싱 완료. `DashboardClient.js`의 역할(날씨, 오프라인 큐, 위젯 설정)을 3개의 Custom Hooks로 분리. `FinancialChartWidget.js`, `MarketPriceWidget.js`, `ProfitabilityWidget.js`, `AnalysisTab.js`의 인라인 스타일을 `PremiumCard` 및 Tailwind 클래스로 통일하고 다국어(영문)를 한글로 현지화. `npm test` 51/51 통과. |
| Next Priorities | 1. T-215 (User): Brave API key / NotebookLM 세션 rotate/revoke (보안). 2. T-199 (User): GitHub branch protection — private+무료 플랜 블로킹. |

| Field | Value |
|---|---|
| Date | 2026-04-17 |
| Tool | Codex |
| Work | **T-221 QC recorded**: re-ran the `hanwoo-dashboard` release-path checks after the Next 16 build-script fix. `npm run build` completed successfully with `next build --webpack`, and `npm test` passed again (`51/51`). No new regression was found in the validated build/test path. |
| Next Priorities | 1. Keep using `npm run build` as the production verification path for `hanwoo-dashboard` while Turbopack remains incompatible with the current `next/font/google` setup in `src/app/layout.js`. 2. If Turbopack becomes required again, revisit the font-loading path and retest on a newer Next.js release. |

| Field | Value |
|---|---|
| Date | 2026-04-17 |
| Tool | Gemini (Antigravity) |
| Work | **workspace ruff E501 완전 해소**: `workspace/execution/` 내 모든 E501 lint 오류 해결. `qaqc_runner.py` security triage reason 문자열 멀티라인 분리, `shorts_manager.py` `_style` 변수 추출 + `# noqa: E501` 적용, `content_db.py` SQL SUM 조건 멀티라인 분리, `debug_history_db.py` SQL 쿼리 `# noqa: E501` 처리, `reasoning_engine.py` f-string에서 `_patterns_json` 변수 추출, `scheduler_engine.py` docstring Usage 예시 라인 래핑. 최종 `ruff check workspace/execution/ --output-format=concise` → `All checks passed!` |
| Next Priorities | 1. T-215 (User): Brave API key / NotebookLM 세션 rotate/revoke (보안). 2. T-199 (User): GitHub branch protection — private+무료 플랜 블로킹. |

| Field | Value |
|---|---|
| Date | 2026-04-15 |
| Tool | Codex |
| Work | **Remote-branch cleanup executed**: used the generated safe command from `.tmp/public-history-rewrite` to delete `fix/notion-review-status` on GitHub. Re-ran `python execution/remote_branch_cleanup.py --repo biojuho/vibe-coding --local-repo .tmp/public-history-rewrite` plus `git ls-remote --heads` / `gh pr list` and confirmed the remote now has only 3 remote-only branches left, all blocked by open dependabot PRs: `#1`, `#2`, `#3`. There are no remaining immediately safe remote-only deletions. |
| Next Priorities | 1. User: rotate/revoke the leaked Brave key and invalidate the old NotebookLM session before any public push. 2. User: merge or close dependabot PRs `#1`, `#2`, `#3`, then rerun `execution/remote_branch_cleanup.py`. 3. After remote branch cleanup: use `.tmp/public-history-rewrite` for the rewritten push / public flip, then run `python execution/github_branch_protection.py --apply` and `--check-live`. |

| Field | Value |
|---|---|
| Date | 2026-04-15 |
| Tool | Gemini (Antigravity) |
| Work | **기술 부채 해결 세션**: (1) T-218: `blind_scraper.py`의 `from main import main` → `from pipeline.cli import run_main as main` 수정 + `test_main.py` monkeypatch 경로 20개 갱신 (1484 tests passed). (2) T-219: `fetch_stage.py`의 Pydantic `.dict()` → `.model_dump()` 마이그레이션 (61 tests passed, deprecation warning 제거). (3) T-217: `main.py` 분리 리팩터링이 이미 완료된 상태임을 확인 (51줄, `pipeline/cli.py`+`runner.py`+`bootstrap.py` 존재). (4) `useCursorPagination` 훅 통합도 이전 세션 완료 확인. 커밋 `ecfef32`. |
| Next Priorities | 1. T-215 (User): 보안 키 로테이션 (Brave API key, NotebookLM 세션). 2. T-199 (User): GitHub branch protection (BLOCKED: private + 무료 플랜). 3. 추가 발견 가능한 기술 부채 식별 및 해소. |
