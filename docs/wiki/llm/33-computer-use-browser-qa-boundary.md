# 33 - Computer Use - Browser QA Boundary

> Provider-native computer-use agents and deterministic browser QA are different operating surfaces.
> Code facts were checked on 2026-06-08 from `.agents/skills/auto-research/scripts/browser_qa_inventory.py`, `.agents/skills/auto-research/scripts/next_experiment_selector.py`, `projects/blind-to-x/scripts/source_browser_probe.py`, `projects/blind-to-x/scrapers/base.py`, `projects/blind-to-x/scrapers/browser_pool.py`, and `workspace/tests/test_auto_research_browser_qa_inventory.py`.

## Why This Is Separate

[23-tool-calling-harness-boundary](23-tool-calling-harness-boundary.md) already separates tool calls from tool execution. Computer-use adds another layer: a model can inspect screenshots and request mouse/keyboard actions. That is not the same thing as Playwright tests proving a UI works.

Use this boundary:

| Surface | Input | Actor | Output | Trust level |
|---|---|---|---|---|
| Provider computer-use | screenshot plus task | model suggests UI actions | action loop transcript, screenshots, safety checks | exploratory / supervised |
| Deterministic Playwright QA | fixed app URL, locators, assertions | test code executes actions | pass/fail, console/network evidence, screenshot artifact | release evidence |
| Scraper browser probe | target source URL | Playwright/patchright code | classification, screenshot, click-through report | source availability evidence |
| Human app-click review | local app plus user workflow | operator or agent-controlled Playwright | observed UX evidence | reviewer evidence |

Operating rule: do not use provider computer-use as proof that a release works. It can explore or propose a workflow, but release evidence needs deterministic browser-click QA, stable assertions, retained screenshots, and console/network inspection.

## Current Code Facts

### 1) Auto-Research Browser QA Is Deterministic Evidence

`.agents/skills/auto-research/scripts/browser_qa_inventory.py` identifies browser projects from dependencies and scripts (`next`, `vite`, React, Playwright, Vitest browser support). It scans `.ai/TASKS.md`, `.ai/HANDOFF.md`, and `.ai/SESSION_LOG.md` for verified direct-QA terms, and scans `output/playwright` for retained images.

It does more than check that a file exists:

- screenshots older than `14` days are stale;
- invalid PNG signatures do not cover a browser app;
- blank screenshots do not cover a browser app;
- nonblank PNGs record width/height and image validity;
- projects covered only by log lines still get a recommendation to retain a screenshot.

`next_experiment_selector.py` treats browser QA as complete only when every browser project has fresh, usable, nonblank screenshot coverage. Otherwise it emits `browser_qa_refresh` with required gates for the browser inventory, direct app-click QA, and console/network inspection.

### 2) Blind-to-X Browser Probes Are Source Evidence, Not LLM Computer Use

`projects/blind-to-x/scripts/source_browser_probe.py` uses Playwright to classify source availability. It records statuses such as `browser_unavailable`, `blocked`, `login_wall`, `empty`, `click_error`, and `ready`; it collects console errors, page errors, screenshots, and click-through evidence.

This is deterministic source probing. It does not ask an LLM to decide where to click. When Playwright is missing or browsers are not installed, it classifies that as `browser_unavailable` and suggests the exact install/runtime remediation.

### 3) Blind-to-X Scrapers Use Browser Automation As An Ingestion Tool

`projects/blind-to-x/scrapers/base.py` and `browser_pool.py` use Playwright or patchright, mobile-like contexts, Korean locale, stealth, selector timeouts, screenshot helpers, and explicit context/browser cleanup. Screenshots can time out, fail, or be cleaned by retention policy.

This is not provider computer-use either. It is a scraper/browser runtime with deterministic selectors and failure reasons. Its evidence should feed source availability and scraping quality reports, not agent autonomy claims.

### 4) There Is No Provider Computer-Use Integration In The Common LLM Path

The current common `LLMClient` path still has no computer-use tool surface. Existing browser evidence is produced by local scripts and tests, not by OpenAI `computer-use-preview` or Anthropic computer-use beta tools.

Operational conclusion: adding provider computer-use later should be a new supervised agent experiment with sandboxing, action allowlists, safety-check handling, and retained transcripts. It should not be slipped into the existing browser QA or scraper evidence paths.

## Official Boundaries

### OpenAI Computer Use

OpenAI's computer-use guide describes a loop where the model returns actions such as click, type, scroll, wait, and screenshot; application code executes the action in a browser or VM and sends back an updated screenshot. The guide says the feature is available through the Responses API, is not available on Chat Completions, is beta, and should be used with sandboxing and risk controls. The docs also describe pending safety checks and recommend human oversight when they fire.

Repo implication: if this repo adopts OpenAI computer-use, it needs a dedicated sandboxed environment, domain/action allowlists, `pending_safety_check` handling, and a transcript artifact. Do not route it through `LLMClient.generate_text()` or count it as browser QA pass/fail evidence.

### Anthropic Computer Use

Anthropic's computer-use docs describe a beta tool family that lets Claude interact with a developer-supplied environment through screenshots and tool actions. The docs require the relevant beta tool setup and describe screenshot/action request processing as part of the API call.

Repo implication: Anthropic computer-use belongs behind the same local harness boundary as other side-effecting agent tools. The model can request UI actions, but local code must still own sandbox, authentication, sensitive data, and approval policy.

### Playwright

Playwright's best practices emphasize user-visible behavior, isolated tests, locators, and keeping browser dependencies current. Its isolation docs explain that browser contexts are clean-slate environments with separate cookies/local storage/session storage. The screenshots docs define screenshot capture as an explicit artifact surface.

Repo implication: deterministic browser QA should stay Playwright-first. For release evidence, prefer stable locators, explicit assertions, isolated contexts, console/page/network capture, retained screenshots, and freshness checks.

## A/B Operating Choice

| Choice | Upside | Risk | Repo decision |
|---|---|---|---|
| A. Treat provider computer-use as browser QA | Flexible exploration, fewer hand-written locators | Non-deterministic, safety-check driven, hard to reproduce, can click the wrong thing | Reject |
| B. Keep deterministic Playwright QA as release evidence | Reproducible, assertion-driven, aligns with current inventory/gates | Requires writing and maintaining tests/scripts | Adopt |
| C. Use provider computer-use only for supervised exploration | Can discover flows before hardening tests | Needs sandbox, allowlists, transcript retention, HITL | Conditional |
| D. Use manual screenshots only | Fast for one-off visual checks | Weak coverage, no console/network/action evidence | Reject |

**Decision:** adopt B as the release-evidence path. Allow C only as a separate supervised prototype surface that must later be converted into deterministic Playwright evidence before release claims.

## Minimum Browser-Evidence Artifact

For browser-facing LLM or product workflows, preserve these fields where practical:

| Field | Meaning |
|---|---|
| `artifact_id` | Stable id for the browser QA run or probe |
| `surface` | app, source probe, scraper, provider computer-use prototype |
| `driver` | Playwright, patchright, provider computer-use, manual |
| `environment` | browser/channel, viewport, locale, authenticated state policy |
| `action_trace` | deterministic steps or provider-requested actions |
| `assertions` | user-visible assertions, source classification, or expected UI state |
| `console_errors` | captured console/page errors |
| `network_errors` | failed request list or unavailable marker |
| `screenshot` | retained path plus freshness, validity, nonblank status |
| `safety_checks` | provider pending safety checks or local HITL approvals |
| `decision` | pass, hold, refresh_required, source_ready, source_blocked, prototype_only |
| `retention_class` | whether screenshots may contain private/authenticated data |

## Routing Rules

1. Provider computer-use output is a prototype transcript until converted into deterministic tests or explicit reviewer evidence.
2. A browser QA pass needs user-visible behavior checks, not just a screenshot.
3. A retained screenshot must be fresh, valid, and nonblank before it counts toward launch evidence.
4. Console, page, and network failures should be recorded even when the UI appears usable.
5. Authenticated browser contexts require a retention decision before screenshots or traces are kept.
6. Scraper source probes should report source readiness and failure reasons, not LLM autonomy.
7. Computer-use safety checks require human acknowledgement or a hold; they are not ordinary retry signals.
8. Provider computer-use should never run in a fully authenticated or high-stakes environment without a separate approval experiment.

## Implementation Checklist

1. Keep `browser_qa_inventory.py` as the deterministic launch evidence gate for browser apps.
2. When a provider computer-use experiment is added, put it behind a dedicated sandbox wrapper, not common `LLMClient`.
3. Require action/domain allowlists and HITL for any authenticated or side-effecting computer-use action.
4. Store computer-use transcripts separately from release QA artifacts and mark them `prototype_only` until hardened.
5. Convert useful CUA discoveries into Playwright locators/assertions before using them for launch readiness.
6. Extend browser QA evidence with console/page/network summaries when a current script only stores screenshots.
7. Keep Blind-to-X source probes under source availability evidence; do not report them as app QA.
8. Add tests proving stale, invalid, or blank screenshots cannot satisfy browser release evidence.

## Pitfalls

- A model successfully clicking through a page is not a reproducible test.
- A screenshot without assertions can hide broken controls below the fold.
- A nonblank screenshot can still show an error page, login wall, or blocked-source page.
- Computer-use traces can contain private UI data; retention must be explicit.
- Safety checks and domain allowlists are part of the run contract, not optional logging.
- Scraper stealth or anti-bot workarounds should not be generalized into user-facing browser QA.
- Passing browser QA does not prove platform publish compliance; keep [32-safety-moderation-publish-gates](32-safety-moderation-publish-gates.md) separate.

## 출처

- 공식: OpenAI API Docs, *Computer use*: <https://platform.openai.com/docs/guides/tools-computer-use>
- 공식: OpenAI API Docs, *computer-use-preview model*: <https://platform.openai.com/docs/models/computer-use-preview>
- 공식: Claude API Docs, *Computer use tool*: <https://platform.claude.com/docs/en/build-with-claude/computer-use>
- 공식: Playwright, *Best Practices*: <https://playwright.dev/docs/best-practices>
- 공식: Playwright, *Isolation*: <https://playwright.dev/docs/browser-contexts>
- 공식: Playwright, *Screenshots*: <https://playwright.dev/docs/screenshots>
- Code evidence: `.agents/skills/auto-research/scripts/browser_qa_inventory.py`, `.agents/skills/auto-research/scripts/next_experiment_selector.py`, `projects/blind-to-x/scripts/source_browser_probe.py`, `projects/blind-to-x/scrapers/base.py`, `projects/blind-to-x/scrapers/browser_pool.py`, `workspace/tests/test_auto_research_browser_qa_inventory.py`.

*외부 자료 검증일: 2026-06-08. Code verified against current HEAD.*
