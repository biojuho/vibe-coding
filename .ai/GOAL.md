# GOAL - Active Workspace Goal

> Shared current goal for Claude Code, Codex, Gemini, and other AI tools.

## Active Goal

- Status: active
- Goal: hanwoo-dashboard quality uplift so other people would want to use it.
- Owner: Codex
- Started: 2026-05-18
- Success: Hanwoo quality uplift is progressing through focused UX passes. 2026-05-18: added a home-screen Today Brief panel that turns critical alerts, next schedules, low-stock items, offline state, and monthly sales into immediate actions. 2026-05-19: polished the operator login flow, replaced bottom-tab emoji navigation with lucide icons, added the Quick Action Panel for one-tap cattle/sales/schedule/inventory recording, fixed pre-auth PWA asset routing so the login page has no manifest parse error, and upgraded Sales/Schedule/Inventory empty states into action-oriented CTAs for first-run users. 2026-05-20: added a home-screen Farm Setup / 운영 준비도 panel so first-run users can close 농장 정보, 축사, 개체, 재고, and 일정 setup gaps from one place; corrected the empty 축사 CTA to open Settings instead of the cattle modal; added branded App Router error boundaries (`error.js`, `not-found.js`, `global-error.js`); connected the missing-building setup step so Settings opens the 축사 registration form immediately; replaced cattle-detail 발정/수정 browser prompts with an in-app date form; localized checkout/subscription loading, success, error, and payment button states; localized payment confirmation fallback messages; localized the admin diagnostics surface; localized app metadata/PWA install copy; localized home fallback/panel labels; localized market-price widget + degraded fallback copy; localized weather widget degraded fallback copy; localized/hardened cattle CSV export headers/result formatting; and localized Sales tab missing-cattle fallback labels. Goal remains active for additional Hanwoo polish; keep T-251 separate.

## Progress Notes

- 2026-05-20: T-345 polished the cattle QR print action with Korean `QR 출력` / `QR 라벨 인쇄` copy and a lucide `Printer` icon. Verification passed with Hanwoo tests `100 passed`, targeted ESLint, full Hanwoo QC, and graph risk `0.00`.

## Notes

- Keep exactly one active goal here.
- Move completed goals into `.ai/SESSION_LOG.md` during session closeout.
- If no goal is active, set `Status: inactive` instead of deleting the file.
